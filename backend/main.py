"""Project KEY — FastAPI Backend (MVP v4 — PDB Connector Layer)"""
import os
import json
import logging
from datetime import datetime

from fastapi import FastAPI, UploadFile, File as FastAPIFile, Depends, HTTPException, BackgroundTasks, Query, Header, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import (
    init_db, get_db, gen_id,
    User, File, Cluster, FileClusterMap, FileInsight, FileSummary,
    ContextPack, GraphNode, GraphEdge, NoteObject, SuggestedRelation, GraphLens,
    MCPToken, MCPUsageLog
)
from .extraction import extract_text
from .organizer import organize_files
from .retriever import chat_with_retrieval
from .profile import get_profile, update_profile, is_profile_complete
from .context_packs import list_packs, get_pack, create_pack, delete_pack, regenerate_pack
from .graph_builder import build_full_graph, get_graph_data, get_node_detail, get_neighborhood
from .relations import get_backlinks, get_outgoing, get_suggestions, accept_suggestion, dismiss_suggestion, generate_suggestions
from .metadata import enrich_file_metadata, enrich_all_files, get_file_metadata, update_file_metadata
from .config import UPLOAD_DIR, BASE_DIR, MAX_FILE_SIZE_MB, MCP_SECRET
from .mcp_tokens import generate_token, validate_token, list_tokens, revoke_token, get_active_token_count
from .mcp_tools import call_tool, get_usage_logs, TOOL_REGISTRY

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App
app = FastAPI(title="Project KEY", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Default user ID for MVP (single user)
DEFAULT_USER_ID = "default-user"


@app.on_event("startup")
async def startup():
    await init_db()
    # Create default user if not exists
    async for db in get_db():
        result = await db.execute(select(User).where(User.id == DEFAULT_USER_ID))
        user = result.scalar_one_or_none()
        if not user:
            db.add(User(id=DEFAULT_USER_ID, name="Personal Workspace"))
            await db.commit()
        break


# ─── REQUEST MODELS ───

class ChatRequest(BaseModel):
    question: str

class ProfileRequest(BaseModel):
    identity_summary: str | None = None
    goals: str | None = None
    working_style: str | None = None
    preferred_output_style: str | None = None
    background_context: str | None = None

class ContextPackRequest(BaseModel):
    type: str  # profile, study, work, project
    title: str
    source_file_ids: list[str] = []
    source_cluster_ids: list[str] = []

class MetadataUpdateRequest(BaseModel):
    tags: list[str] | None = None
    aliases: list[str] | None = None
    sensitivity: str | None = None
    source_of_truth: bool | None = None
    freshness: str | None = None
    version: str | None = None


# ═══════════════════════════════════════════
# FILE APIs (v1 — preserved)
# ═══════════════════════════════════════════

@app.post("/api/upload")
async def upload_files(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Upload one or more files, extract text, save to database."""
    uploaded = []
    allowed_types = {"pdf", "txt", "md", "docx"}
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024

    for upload_file in files:
        # Validate type
        ext = upload_file.filename.rsplit(".", 1)[-1].lower() if "." in upload_file.filename else ""
        if ext not in allowed_types:
            continue

        # Save raw file
        file_id = gen_id()
        safe_filename = f"{file_id}_{upload_file.filename}"
        raw_path = os.path.join(UPLOAD_DIR, safe_filename)

        contents = await upload_file.read()

        # Validate size
        if len(contents) > max_bytes:
            continue

        with open(raw_path, "wb") as f:
            f.write(contents)

        # Extract text
        extracted = extract_text(raw_path, ext)

        # Save to DB
        db_file = File(
            id=file_id,
            user_id=DEFAULT_USER_ID,
            filename=upload_file.filename,
            filetype=ext,
            raw_path=raw_path,
            extracted_text=extracted,
            processing_status="uploaded"
        )
        db.add(db_file)

        uploaded.append({
            "id": file_id,
            "filename": upload_file.filename,
            "filetype": ext,
            "uploaded_at": datetime.utcnow().isoformat(),
            "processing_status": "uploaded",
            "text_length": len(extracted)
        })

    await db.commit()

    return {"uploaded": uploaded, "count": len(uploaded)}


@app.post("/api/organize")
async def organize(db: AsyncSession = Depends(get_db)):
    """Run the organization pipeline on all uploaded files, then build graph."""
    try:
        await organize_files(db, DEFAULT_USER_ID)

        # v3: Auto-build knowledge graph after organizing
        logger.info("Auto-building knowledge graph...")
        await enrich_all_files(db, DEFAULT_USER_ID)
        graph_result = await build_full_graph(db, DEFAULT_USER_ID)
        await generate_suggestions(db, DEFAULT_USER_ID)
        logger.info(f"Graph built: {graph_result}")

        return {"status": "ok", "message": "Organization + graph build complete", "graph": graph_result}
    except Exception as e:
        logger.error(f"Organization failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/files")
async def list_files(db: AsyncSession = Depends(get_db)):
    """List all files for the user."""
    result = await db.execute(
        select(File).where(File.user_id == DEFAULT_USER_ID)
        .options(selectinload(File.insight), selectinload(File.summary))
        .order_by(File.uploaded_at.desc())
    )
    files = result.scalars().all()

    return {"files": [_serialize_file(f) for f in files]}


@app.get("/api/clusters")
async def list_clusters(db: AsyncSession = Depends(get_db)):
    """List all clusters with their files."""
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.user_id == DEFAULT_USER_ID)
    )
    clusters = clusters_result.scalars().all()

    files_result = await db.execute(
        select(File).where(File.user_id == DEFAULT_USER_ID)
        .options(
            selectinload(File.insight),
            selectinload(File.summary),
            selectinload(File.cluster_maps)
        )
    )
    files = files_result.scalars().all()

    # Get context packs for each cluster
    packs_result = await db.execute(
        select(ContextPack).where(ContextPack.user_id == DEFAULT_USER_ID)
    )
    all_packs = packs_result.scalars().all()

    cluster_list = []
    for c in clusters:
        cluster_files = []
        for f in files:
            for cm in f.cluster_maps:
                if cm.cluster_id == c.id:
                    cluster_files.append(_serialize_file(f))
                    break

        # Find packs derived from this cluster
        derived_packs = []
        for p in all_packs:
            source_cluster_ids = json.loads(p.source_cluster_ids) if p.source_cluster_ids else []
            if c.id in source_cluster_ids:
                derived_packs.append({
                    "id": p.id,
                    "type": p.type,
                    "title": p.title
                })

        cluster_list.append({
            "id": c.id,
            "title": c.title,
            "summary": c.summary,
            "file_count": len(cluster_files),
            "files": cluster_files,
            "derived_packs": derived_packs
        })

    return {
        "clusters": cluster_list,
        "total_clusters": len(cluster_list),
        "total_files": len(files),
        "total_ready": sum(1 for f in files if f.processing_status == "ready")
    }


class ClusterUpdateRequest(BaseModel):
    title: str | None = None
    summary: str | None = None

@app.put("/api/clusters/{cluster_id}")
async def update_cluster(cluster_id: str, req: ClusterUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update a cluster title or summary."""
    result = await db.execute(
        select(Cluster).where(Cluster.id == cluster_id, Cluster.user_id == DEFAULT_USER_ID)
    )
    cluster = result.scalar_one_or_none()
    if not cluster:
        raise HTTPException(status_code=404, detail="Cluster not found")
    if req.title is not None:
        cluster.title = req.title
    if req.summary is not None:
        cluster.summary = req.summary
    await db.commit()
    return {"status": "ok", "id": cluster_id, "title": cluster.title, "summary": cluster.summary}


@app.get("/api/summary/{file_id}")
async def get_summary(file_id: str, db: AsyncSession = Depends(get_db)):
    """Get the full markdown summary for a file."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == DEFAULT_USER_ID)
        .options(selectinload(File.summary), selectinload(File.insight), selectinload(File.cluster_maps))
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if not file.summary:
        raise HTTPException(status_code=404, detail="Summary not yet generated")

    # Find cluster name
    cluster_title = "Unclustered"
    if file.cluster_maps:
        for cm in file.cluster_maps:
            cluster_result = await db.execute(select(Cluster).where(Cluster.id == cm.cluster_id))
            cluster = cluster_result.scalar_one_or_none()
            if cluster:
                cluster_title = cluster.title
                break

    return {
        "file_id": file.id,
        "filename": file.filename,
        "filetype": file.filetype,
        "cluster": cluster_title,
        "importance_score": file.insight.importance_score if file.insight else 50,
        "importance_label": file.insight.importance_label if file.insight else "medium",
        "is_primary": file.insight.is_primary_candidate if file.insight else False,
        "summary_text": file.summary.summary_text,
        "key_topics": json.loads(file.summary.key_topics) if file.summary.key_topics else [],
        "key_facts": json.loads(file.summary.key_facts) if file.summary.key_facts else [],
        "why_important": file.summary.why_important,
        "suggested_usage": file.summary.suggested_usage
    }


@app.get("/api/files/{file_id}/content")
async def get_file_content(file_id: str, db: AsyncSession = Depends(get_db)):
    """Get file extracted text content for preview."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == DEFAULT_USER_ID)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return {
        "file_id": file.id,
        "filename": file.filename,
        "filetype": file.filetype,
        "text": file.extracted_text or "",
        "uploaded_at": file.uploaded_at.isoformat() if file.uploaded_at else ""
    }


class SummaryUpdateRequest(BaseModel):
    summary_text: str | None = None
    key_topics: list[str] | None = None
    key_facts: list[str] | None = None
    why_important: str | None = None
    suggested_usage: str | None = None

@app.put("/api/summary/{file_id}")
async def update_summary(file_id: str, req: SummaryUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update the summary for a file."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == DEFAULT_USER_ID)
        .options(selectinload(File.summary))
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if not file.summary:
        raise HTTPException(status_code=404, detail="Summary not yet generated")

    if req.summary_text is not None:
        file.summary.summary_text = req.summary_text
    if req.key_topics is not None:
        file.summary.key_topics = json.dumps(req.key_topics, ensure_ascii=False)
    if req.key_facts is not None:
        file.summary.key_facts = json.dumps(req.key_facts, ensure_ascii=False)
    if req.why_important is not None:
        file.summary.why_important = req.why_important
    if req.suggested_usage is not None:
        file.summary.suggested_usage = req.suggested_usage

    await db.commit()
    return {"status": "ok", "file_id": file_id}


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a file and its related data."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == DEFAULT_USER_ID)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    if file.raw_path and os.path.exists(file.raw_path):
        os.remove(file.raw_path)

    await db.delete(file)
    await db.commit()
    return {"status": "ok"}


# ═══════════════════════════════════════════
# CHAT API (v2 — enhanced with injection)
# ═══════════════════════════════════════════

@app.post("/api/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI Chat with automatic context injection from all layers."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = await chat_with_retrieval(db, DEFAULT_USER_ID, req.question)
        return result
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
# PROFILE APIs (v2)
# ═══════════════════════════════════════════

@app.get("/api/profile")
async def api_get_profile(db: AsyncSession = Depends(get_db)):
    """Get user profile."""
    return await get_profile(db, DEFAULT_USER_ID)

@app.put("/api/profile")
async def api_update_profile(req: ProfileRequest, db: AsyncSession = Depends(get_db)):
    """Create or update user profile."""
    data = req.model_dump(exclude_none=True)
    return await update_profile(db, DEFAULT_USER_ID, data)


# ═══════════════════════════════════════════
# CONTEXT PACK APIs (v2)
# ═══════════════════════════════════════════

@app.get("/api/context-packs")
async def api_list_packs(db: AsyncSession = Depends(get_db)):
    """List all context packs."""
    packs = await list_packs(db, DEFAULT_USER_ID)
    return {"packs": packs, "count": len(packs)}

@app.post("/api/context-packs")
async def api_create_pack(req: ContextPackRequest, db: AsyncSession = Depends(get_db)):
    """Create a new context pack from source files/clusters."""
    valid_types = {"profile", "study", "work", "project"}
    if req.type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Type must be one of: {valid_types}")
    if not req.source_file_ids and not req.source_cluster_ids:
        raise HTTPException(status_code=400, detail="Must provide source_file_ids or source_cluster_ids")
    try:
        pack = await create_pack(db, DEFAULT_USER_ID, req.type, req.title, req.source_file_ids, req.source_cluster_ids)
        return pack
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Pack creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/context-packs/{pack_id}")
async def api_get_pack(pack_id: str, db: AsyncSession = Depends(get_db)):
    """Get a single context pack."""
    pack = await get_pack(db, pack_id, DEFAULT_USER_ID)
    if not pack:
        raise HTTPException(status_code=404, detail="Context pack not found")
    return pack

@app.delete("/api/context-packs/{pack_id}")
async def api_delete_pack(pack_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a context pack."""
    deleted = await delete_pack(db, pack_id, DEFAULT_USER_ID)
    if not deleted:
        raise HTTPException(status_code=404, detail="Context pack not found")
    return {"status": "ok"}

@app.post("/api/context-packs/{pack_id}/regenerate")
async def api_regenerate_pack(pack_id: str, db: AsyncSession = Depends(get_db)):
    """Regenerate a context pack from its original sources."""
    try:
        pack = await regenerate_pack(db, pack_id, DEFAULT_USER_ID)
        if not pack:
            raise HTTPException(status_code=404, detail="Context pack not found")
        return pack
    except Exception as e:
        logger.error(f"Pack regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
# GRAPH APIs (v3 — new)
# ═══════════════════════════════════════════

@app.post("/api/graph/build")
async def api_build_graph(db: AsyncSession = Depends(get_db)):
    """Build/rebuild the knowledge graph from all data."""
    try:
        result = await build_full_graph(db, DEFAULT_USER_ID)
        await generate_suggestions(db, DEFAULT_USER_ID)
        return {"status": "ok", **result}
    except Exception as e:
        logger.error(f"Graph build failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/graph/global")
async def api_global_graph(db: AsyncSession = Depends(get_db)):
    """Get full graph data for global graph visualization."""
    data = await get_graph_data(db, DEFAULT_USER_ID)
    return data


@app.get("/api/graph/nodes")
async def api_list_nodes(
    db: AsyncSession = Depends(get_db),
    family: str | None = None
):
    """List all graph nodes, optionally filtered by family."""
    query = select(GraphNode).where(GraphNode.user_id == DEFAULT_USER_ID)
    if family:
        query = query.where(GraphNode.node_family == family)
    nodes = (await db.execute(query)).scalars().all()
    return {"nodes": [
        {
            "id": n.id,
            "object_type": n.object_type,
            "object_id": n.object_id,
            "label": n.label,
            "node_family": n.node_family,
            "importance": n.importance_score,
            "freshness": n.freshness_score,
        }
        for n in nodes
    ]}


@app.get("/api/graph/nodes/{node_id}")
async def api_get_node(node_id: str, db: AsyncSession = Depends(get_db)):
    """Get detailed info about a single graph node."""
    detail = await get_node_detail(db, node_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Node not found")
    return detail


@app.get("/api/graph/neighborhood/{node_id}")
async def api_neighborhood(
    node_id: str,
    depth: int = Query(1, ge=1, le=3),
    db: AsyncSession = Depends(get_db)
):
    """Get N-hop neighborhood around a node for local graph."""
    data = await get_neighborhood(db, node_id, depth, DEFAULT_USER_ID)
    return data


@app.get("/api/graph/edges")
async def api_list_edges(
    db: AsyncSession = Depends(get_db),
    edge_type: str | None = None
):
    """List all graph edges, optionally filtered by type."""
    query = select(GraphEdge).where(GraphEdge.user_id == DEFAULT_USER_ID)
    if edge_type:
        query = query.where(GraphEdge.edge_type == edge_type)
    edges = (await db.execute(query)).scalars().all()
    return {"edges": [
        {
            "id": e.id,
            "source": e.source_node_id,
            "target": e.target_node_id,
            "edge_type": e.edge_type,
            "weight": e.weight,
            "confidence": e.confidence,
            "evidence": e.evidence_text,
        }
        for e in edges
    ]}


# ═══════════════════════════════════════════
# RELATIONS APIs (v3 — new)
# ═══════════════════════════════════════════

@app.get("/api/relations/backlinks/{node_id}")
async def api_backlinks(node_id: str, db: AsyncSession = Depends(get_db)):
    """Get all backlinks (nodes pointing TO this node)."""
    return {"backlinks": await get_backlinks(db, node_id)}


@app.get("/api/relations/outgoing/{node_id}")
async def api_outgoing(node_id: str, db: AsyncSession = Depends(get_db)):
    """Get all outgoing links (nodes FROM this node)."""
    return {"outgoing": await get_outgoing(db, node_id)}


@app.get("/api/suggestions")
async def api_suggestions(db: AsyncSession = Depends(get_db)):
    """Get pending suggested relations."""
    suggestions = await get_suggestions(db, DEFAULT_USER_ID)
    return {"suggestions": suggestions, "count": len(suggestions)}


@app.post("/api/suggestions/{suggestion_id}/accept")
async def api_accept_suggestion(suggestion_id: str, db: AsyncSession = Depends(get_db)):
    """Accept a suggested relation — creates real edge."""
    result = await accept_suggestion(db, suggestion_id, DEFAULT_USER_ID)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


@app.post("/api/suggestions/{suggestion_id}/dismiss")
async def api_dismiss_suggestion(suggestion_id: str, db: AsyncSession = Depends(get_db)):
    """Dismiss a suggested relation."""
    result = await dismiss_suggestion(db, suggestion_id, DEFAULT_USER_ID)
    if not result:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    return result


# ═══════════════════════════════════════════
# METADATA APIs (v3 — new)
# ═══════════════════════════════════════════

@app.get("/api/metadata/{file_id}")
async def api_get_metadata(file_id: str, db: AsyncSession = Depends(get_db)):
    """Get enriched metadata for a file."""
    meta = await get_file_metadata(db, file_id)
    if not meta:
        raise HTTPException(status_code=404, detail="File not found")
    return meta


@app.put("/api/metadata/{file_id}")
async def api_update_metadata(file_id: str, req: MetadataUpdateRequest, db: AsyncSession = Depends(get_db)):
    """Update file metadata manually."""
    updates = req.model_dump(exclude_none=True)
    result = await update_file_metadata(db, file_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="File not found")
    return result


@app.post("/api/metadata/enrich")
async def api_enrich_metadata(db: AsyncSession = Depends(get_db)):
    """Enrich metadata for all files using LLM."""
    try:
        result = await enrich_all_files(db, DEFAULT_USER_ID)
        return result
    except Exception as e:
        logger.error(f"Metadata enrichment failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ═══════════════════════════════════════════
# LENSES APIs (v3 — new)
# ═══════════════════════════════════════════

@app.get("/api/lenses")
async def api_list_lenses(db: AsyncSession = Depends(get_db)):
    """List saved graph lenses."""
    lenses = (await db.execute(
        select(GraphLens).where(GraphLens.user_id == DEFAULT_USER_ID)
    )).scalars().all()
    return {"lenses": [
        {"id": l.id, "name": l.name, "type": l.type,
         "filter_json": json.loads(l.filter_json or "{}"),
         "layout_json": json.loads(l.layout_json or "{}")}
        for l in lenses
    ]}


# ═══════════════════════════════════════════
# STATS API (v3 — enhanced)
# ═══════════════════════════════════════════

@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get storage/processing stats including v3 graph data and v4 MCP data."""
    files_result = await db.execute(select(File).where(File.user_id == DEFAULT_USER_ID))
    files = files_result.scalars().all()

    clusters_result = await db.execute(select(Cluster).where(Cluster.user_id == DEFAULT_USER_ID))
    clusters = clusters_result.scalars().all()

    packs_result = await db.execute(select(ContextPack).where(ContextPack.user_id == DEFAULT_USER_ID))
    packs = packs_result.scalars().all()

    nodes_result = await db.execute(select(GraphNode).where(GraphNode.user_id == DEFAULT_USER_ID))
    nodes = nodes_result.scalars().all()

    edges_result = await db.execute(select(GraphEdge).where(GraphEdge.user_id == DEFAULT_USER_ID))
    edges = edges_result.scalars().all()

    suggestions_result = await db.execute(
        select(SuggestedRelation).where(
            SuggestedRelation.user_id == DEFAULT_USER_ID,
            SuggestedRelation.status == "pending"
        )
    )
    suggestions = suggestions_result.scalars().all()

    profile = await get_profile(db, DEFAULT_USER_ID)

    # v4 — MCP stats
    active_tokens = await get_active_token_count(db, DEFAULT_USER_ID)

    return {
        "total_files": len(files),
        "total_clusters": len(clusters),
        "processed": sum(1 for f in files if f.processing_status == "ready"),
        "processing": sum(1 for f in files if f.processing_status == "processing"),
        "errors": sum(1 for f in files if f.processing_status == "error"),
        "total_context_packs": len(packs),
        "profile_set": is_profile_complete(profile),
        # v3 — graph stats
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "total_suggestions": len(suggestions),
        "graph_built": len(nodes) > 0,
        # v4 — MCP stats
        "active_tokens": active_tokens,
    }


@app.delete("/api/reset")
async def reset_all(db: AsyncSession = Depends(get_db)):
    """Delete all data for the user (for testing)."""
    from sqlalchemy import delete as sql_delete

    # Clear graph data first (FK dependencies)
    await db.execute(sql_delete(SuggestedRelation).where(SuggestedRelation.user_id == DEFAULT_USER_ID))
    await db.execute(sql_delete(GraphEdge).where(GraphEdge.user_id == DEFAULT_USER_ID))
    await db.execute(sql_delete(GraphNode).where(GraphNode.user_id == DEFAULT_USER_ID))
    await db.execute(sql_delete(NoteObject).where(NoteObject.user_id == DEFAULT_USER_ID))
    await db.execute(sql_delete(GraphLens).where(GraphLens.user_id == DEFAULT_USER_ID))

    files_result = await db.execute(select(File).where(File.user_id == DEFAULT_USER_ID))
    for f in files_result.scalars().all():
        if f.raw_path and os.path.exists(f.raw_path):
            os.remove(f.raw_path)
        await db.delete(f)

    clusters_result = await db.execute(select(Cluster).where(Cluster.user_id == DEFAULT_USER_ID))
    for c in clusters_result.scalars().all():
        await db.delete(c)

    packs_result = await db.execute(select(ContextPack).where(ContextPack.user_id == DEFAULT_USER_ID))
    for p in packs_result.scalars().all():
        if p.md_path and os.path.exists(p.md_path):
            os.remove(p.md_path)
        await db.delete(p)

    await db.commit()
    return {"status": "ok", "message": "All data cleared"}


# ═══════════════════════════════════════════
# MCP / CONNECTOR APIs (v4 — new)
# ═══════════════════════════════════════════

class MCPTokenRequest(BaseModel):
    label: str = "Default Token"

class MCPToolCallRequest(BaseModel):
    tool: str
    params: dict = {}


@app.get("/api/mcp/info")
async def api_mcp_info(request: Request):
    """Get MCP server info and available tools."""
    base_url = str(request.base_url).rstrip('/')
    # Fly.io reverse proxy sends X-Forwarded-Proto
    if request.headers.get("x-forwarded-proto") == "https":
        base_url = base_url.replace("http://", "https://", 1)
    return {
        "mcp_server_url": f"{base_url}/api/mcp/tools/call",
        "mcp_connector_url": f"{base_url}/mcp/{MCP_SECRET}",
        "auth_type": "bearer",
        "scope": "read+write",
        "version": "v4.1",
        "available_tools": list(TOOL_REGISTRY.values()),
        "tool_count": len(TOOL_REGISTRY),
    }


@app.post("/api/mcp/tokens")
async def api_generate_token(
    req: MCPTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate a new MCP Bearer token."""
    result = await generate_token(db, DEFAULT_USER_ID, req.label)
    return result


@app.get("/api/mcp/tokens")
async def api_list_tokens(db: AsyncSession = Depends(get_db)):
    """List all MCP tokens."""
    tokens = await list_tokens(db, DEFAULT_USER_ID)
    return {"tokens": tokens, "count": len(tokens)}


@app.delete("/api/mcp/tokens/{token_id}")
async def api_revoke_token(token_id: str, db: AsyncSession = Depends(get_db)):
    """Revoke an MCP token."""
    revoked = await revoke_token(db, token_id, DEFAULT_USER_ID)
    if not revoked:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "ok", "message": "Token revoked"}


@app.post("/api/mcp/test")
async def api_test_connection(
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Test MCP connection with a Bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        return {"status": "error", "message": "Missing or invalid Authorization header"}

    raw_token = authorization.split(" ", 1)[1]
    token_info = await validate_token(db, raw_token)

    if not token_info:
        return {"status": "error", "message": "Invalid or revoked token"}

    return {
        "status": "success",
        "message": "Connection successful",
        "user_id": token_info["user_id"],
        "scope": token_info["scope"],
        "token_label": token_info["label"],
    }


@app.post("/api/mcp/tools/call")
async def api_mcp_tool_call(
    req: MCPToolCallRequest,
    authorization: str | None = Header(None, alias="Authorization"),
    db: AsyncSession = Depends(get_db)
):
    """Main MCP tool dispatcher — called by Claude custom connector."""
    # Validate token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    raw_token = authorization.split(" ", 1)[1]
    token_info = await validate_token(db, raw_token)

    if not token_info:
        raise HTTPException(status_code=401, detail="Invalid or revoked token")

    # Call tool
    result = await call_tool(
        db=db,
        user_id=token_info["user_id"],
        token_id=token_info["token_id"],
        tool_name=req.tool,
        params=req.params,
    )
    return result


@app.get("/api/mcp/logs")
async def api_mcp_logs(
    tool: str | None = None,
    status: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Get MCP usage logs."""
    logs = await get_usage_logs(db, DEFAULT_USER_ID, tool, status, limit)
    return {"logs": logs, "count": len(logs)}


# ─── MCP TOOL PERMISSIONS ───

# In-memory permissions store (persists until restart, saved per session)
MCP_PERMISSIONS: dict = {}  # tool_name -> bool

@app.get("/api/mcp/permissions")
async def api_get_permissions():
    """Get current tool permissions."""
    return {"permissions": MCP_PERMISSIONS}

@app.put("/api/mcp/permissions")
async def api_set_permissions(request: Request):
    """Set tool permissions (enable/disable individual tools)."""
    body = await request.json()
    perms = body.get("permissions", {})
    MCP_PERMISSIONS.update(perms)
    return {"status": "ok", "permissions": MCP_PERMISSIONS}


# ─── HELPERS ───

def _serialize_file(f: File) -> dict:
    return {
        "id": f.id,
        "filename": f.filename,
        "filetype": f.filetype,
        "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else "",
        "processing_status": f.processing_status,
        "text_length": len(f.extracted_text or ""),
        "importance_score": f.insight.importance_score if f.insight else None,
        "importance_label": f.insight.importance_label if f.insight else None,
        "is_primary": f.insight.is_primary_candidate if f.insight else False,
        "has_summary": f.summary is not None,
        "snippet": (f.summary.summary_text[:120] + "...") if f.summary and f.summary.summary_text else "",
        # v3 — metadata
        "tags": json.loads(f.tags or "[]"),
        "sensitivity": f.sensitivity or "normal",
        "freshness": f.freshness or "current",
        "source_of_truth": f.source_of_truth or False,
    }


# ═══════════════════════════════════════════
# MCP STREAMABLE HTTP TRANSPORT (for Claude Custom Connector)
# ═══════════════════════════════════════════

def _build_mcp_tools_list():
    """Convert our tool registry to MCP-spec tool format."""
    tools = []
    for tool in TOOL_REGISTRY.values():
        # Build JSON Schema for inputSchema
        properties = {}
        required = []
        for p in tool.get("params", []):
            if p["type"] == "array":
                prop = {"type": "array", "items": {"type": "string"}}
            else:
                prop = {"type": p["type"]}
            if "default" in p:
                prop["default"] = p["default"]
            properties[p["name"]] = prop
            if p.get("required"):
                required.append(p["name"])

        tools.append({
            "name": tool["name"],
            "description": tool["description"],
            "inputSchema": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        })
    return tools


@app.post("/mcp/{secret}")
async def mcp_streamable_http(secret: str, request: Request, db: AsyncSession = Depends(get_db)):
    """MCP Streamable HTTP transport — JSON-RPC 2.0 endpoint for Claude Custom Connector."""
    # Validate secret key
    if secret != MCP_SECRET:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Unauthorized"}, "id": None},
            status_code=401,
        )
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            {"jsonrpc": "2.0", "error": {"code": -32700, "message": "Parse error"}, "id": None},
            status_code=400,
        )

    method = body.get("method", "")
    msg_id = body.get("id")
    params = body.get("params", {})

    logger.info(f"MCP request: method={method}, id={msg_id}")

    # ── Notification (no id) — return 202 Accepted ──
    if msg_id is None:
        return JSONResponse(content=None, status_code=202)

    # ── initialize ──
    if method == "initialize":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {},
                },
                "serverInfo": {
                    "name": "project-key",
                    "version": "0.4.1",
                },
            },
        })

    # ── tools/list ──
    elif method == "tools/list":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {
                "tools": _build_mcp_tools_list(),
            },
        })

    # ── tools/call ──
    elif method == "tools/call":
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})

        if tool_name not in TOOL_REGISTRY:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": f"Unknown tool: {tool_name}"},
            })

        # Check if tool is disabled by permissions (admin_key bypasses)
        if MCP_PERMISSIONS.get(tool_name) is False and not arguments.get("admin_key"):
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Tool '{tool_name}' is disabled by the user. Ask them to enable it in MCP Setup."}],
                    "isError": True,
                },
            })

        # Call the tool using our existing dispatcher
        tool_result = await call_tool(db, DEFAULT_USER_ID, "mcp-connector", tool_name, arguments)

        # Format result as MCP content
        if tool_result["status"] == "success":
            text_content = json.dumps(tool_result["result"], ensure_ascii=False, indent=2)
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": text_content}],
                },
            })
        else:
            return JSONResponse({
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "content": [{"type": "text", "text": f"Error: {tool_result['result'].get('error', 'Unknown error')}"}],
                    "isError": True,
                },
            })

    # ── ping ──
    elif method == "ping":
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": {},
        })

    # ── Unknown method ──
    else:
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"},
        })


# ─── SERVE FRONTEND ───

@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/{filename}")
async def serve_static(filename: str):
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.exists(filepath) and not os.path.isdir(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404)
