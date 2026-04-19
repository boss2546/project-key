"""MCP Tools — PDB Core API tool implementations for MVP v4.1.

13 tools that expose Project KEY data to external AI connectors.
Read (7) + Search & Graph (2) + Write (3) + System (1).
"""
import json
import time
import logging
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import (
    File, Cluster, FileClusterMap, FileSummary, FileInsight,
    ContextPack, MCPUsageLog, GraphNode, GraphEdge,
    SuggestedRelation, gen_id
)
from .profile import get_profile, update_profile
from .context_packs import list_packs, get_pack, create_pack, delete_pack
from . import vector_search

# Admin password — pass this to unlock all tools
ADMIN_PASSWORD = "1234"

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# TOOL REGISTRY — 21 tools in 4 categories
# ═══════════════════════════════════════════

TOOL_REGISTRY = {
    # ─── 📖 READ & SEARCH (10) ───
    "get_profile": {
        "name": "get_profile",
        "description": "Get the user's profile including identity, goals, working style, and preferences",
        "params": [],
        "category": "read",
    },
    "list_files": {
        "name": "list_files",
        "description": "List all files in the knowledge base with their metadata, tags, and summary snippets",
        "params": [],
        "category": "read",
    },
    "get_file_content": {
        "name": "get_file_content",
        "description": "Get the extracted text content of a specific file (max 5000 chars)",
        "params": [{"name": "file_id", "type": "string", "required": True}],
        "category": "read",
    },
    "get_file_summary": {
        "name": "get_file_summary",
        "description": "Get the AI-generated summary, key topics, and key facts of a specific file",
        "params": [{"name": "file_id", "type": "string", "required": True}],
        "category": "read",
    },
    "list_collections": {
        "name": "list_collections",
        "description": "List all AI-organized collections (clusters) with their files and summaries",
        "params": [],
        "category": "read",
    },
    "list_context_packs": {
        "name": "list_context_packs",
        "description": "List all context packs (distilled knowledge bundles) available",
        "params": [],
        "category": "read",
    },
    "get_context_pack": {
        "name": "get_context_pack",
        "description": "Get a specific context pack by ID with full content",
        "params": [{"name": "pack_id", "type": "string", "required": True}],
        "category": "read",
    },
    "search_knowledge": {
        "name": "search_knowledge",
        "description": "Search the user's knowledge base using semantic + keyword hybrid search. Returns matching files, packs, and graph nodes.",
        "params": [
            {"name": "query", "type": "string", "required": True},
            {"name": "limit", "type": "integer", "required": False, "default": 5},
        ],
        "category": "read",
    },
    "explore_graph": {
        "name": "explore_graph",
        "description": "Explore the knowledge graph. Without a node_id, returns all nodes overview. With a node_id, returns the node's connections and neighborhood.",
        "params": [
            {"name": "node_id", "type": "string", "required": False},
            {"name": "depth", "type": "integer", "required": False, "default": 1},
        ],
        "category": "read",
    },
    "get_overview": {
        "name": "get_overview",
        "description": "Get system overview with counts of files, collections, packs, graph nodes, and edges",
        "params": [],
        "category": "read",
    },

    # ─── ✏️ CREATE & EDIT (5) ───
    "create_context_pack": {
        "name": "create_context_pack",
        "description": "Create a new context pack from selected files. Types: profile, study, work, project.",
        "params": [
            {"name": "title", "type": "string", "required": True},
            {"name": "type", "type": "string", "required": True},
            {"name": "file_ids", "type": "array", "required": True},
        ],
        "category": "edit",
    },
    "add_note": {
        "name": "add_note",
        "description": "Update the summary text for a file. Use this to add notes or improve AI-generated summaries.",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
            {"name": "summary_text", "type": "string", "required": True},
        ],
        "category": "edit",
    },
    "update_file_tags": {
        "name": "update_file_tags",
        "description": "Update tags for a file. Use this to organize and categorize files.",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
            {"name": "tags", "type": "array", "required": True},
        ],
        "category": "edit",
    },
    "upload_text": {
        "name": "upload_text",
        "description": "Upload text content as a new file (Claude can create new knowledge files)",
        "params": [
            {"name": "filename", "type": "string", "required": True},
            {"name": "content", "type": "string", "required": True},
        ],
        "category": "edit",
    },
    "update_profile": {
        "name": "update_profile",
        "description": "Update the user profile (identity, goals, working style, preferences)",
        "params": [
            {"name": "identity_summary", "type": "string", "required": False},
            {"name": "goals", "type": "string", "required": False},
            {"name": "working_style", "type": "string", "required": False},
            {"name": "preferred_output_style", "type": "string", "required": False},
            {"name": "background_context", "type": "string", "required": False},
        ],
        "category": "edit",
    },

    # ─── 🗑️ DELETE (2) ───
    "delete_file": {
        "name": "delete_file",
        "description": "Delete a file and all its related data (summary, insights, clusters)",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
        ],
        "category": "delete",
    },
    "delete_pack": {
        "name": "delete_pack",
        "description": "Delete a context pack",
        "params": [
            {"name": "pack_id", "type": "string", "required": True},
        ],
        "category": "delete",
    },

    # ─── ⚙️ AI PIPELINE (4) ───
    "run_organize": {
        "name": "run_organize",
        "description": "Run the full AI organization pipeline: summarize, cluster, build graph",
        "params": [],
        "category": "pipeline",
    },
    "build_graph": {
        "name": "build_graph",
        "description": "Rebuild the knowledge graph from all data",
        "params": [],
        "category": "pipeline",
    },
    "enrich_metadata": {
        "name": "enrich_metadata",
        "description": "Run AI metadata enrichment on all files (tags, sensitivity, freshness)",
        "params": [],
        "category": "pipeline",
    },
    "admin_login": {
        "name": "admin_login",
        "description": "Verify admin password to bypass disabled tools",
        "params": [{"name": "admin_key", "type": "string", "required": True}],
        "category": "pipeline",
    },
}


# ═══════════════════════════════════════════
# DISPATCHER
# ═══════════════════════════════════════════

async def call_tool(
    db: AsyncSession,
    user_id: str,
    token_id: str,
    tool_name: str,
    params: dict,
) -> dict:
    """Dispatch a tool call and log usage."""
    start_time = time.time()
    status = "success"
    error_msg = ""
    result = {}

    try:
        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {tool_name}")

        # Permissions are enforced by the MCP handler (main.py).
        # Toggle ON = free access. Toggle OFF = blocked unless admin_key is provided.

        # ─── READ ───
        if tool_name == "get_profile":
            result = await _tool_get_profile(db, user_id)
        elif tool_name == "list_files":
            result = await _tool_list_files(db, user_id)
        elif tool_name == "get_file_content":
            result = await _tool_get_file_content(db, user_id, params.get("file_id"))
        elif tool_name == "get_file_summary":
            result = await _tool_get_file_summary(db, user_id, params.get("file_id"))
        elif tool_name == "list_collections":
            result = await _tool_list_collections(db, user_id)
        elif tool_name == "list_context_packs":
            result = await _tool_list_context_packs(db, user_id)
        elif tool_name == "get_context_pack":
            result = await _tool_get_context_pack(db, user_id, params.get("pack_id"))

        # ─── SEARCH & GRAPH ───
        elif tool_name == "search_knowledge":
            result = await _tool_search_knowledge(db, user_id, params.get("query"), params.get("limit", 5))
        elif tool_name == "explore_graph":
            result = await _tool_explore_graph(db, user_id, params.get("node_id"), params.get("depth", 1))

        # ─── WRITE ───
        elif tool_name == "create_context_pack":
            result = await _tool_create_context_pack(db, user_id, params)
        elif tool_name == "add_note":
            result = await _tool_add_note(db, user_id, params)
        elif tool_name == "update_file_tags":
            result = await _tool_update_file_tags(db, user_id, params)

        # ─── SYSTEM ───
        elif tool_name == "get_overview":
            result = await _tool_get_overview(db, user_id)

        # ─── ADMIN ───
        elif tool_name == "admin_login":
            result = _tool_admin_login(params.get("admin_key", ""))
        elif tool_name == "delete_file":
            result = await _tool_delete_file(db, user_id, params.get("file_id"))
        elif tool_name == "delete_pack":
            result = await _tool_delete_pack(db, user_id, params.get("pack_id"))
        elif tool_name == "run_organize":
            result = await _tool_run_organize(db, user_id)
        elif tool_name == "build_graph":
            result = await _tool_build_graph(db, user_id)
        elif tool_name == "enrich_metadata":
            result = await _tool_enrich_metadata(db, user_id)
        elif tool_name == "update_profile":
            result = await _tool_update_profile(db, user_id, params)
        elif tool_name == "upload_text":
            result = await _tool_upload_text(db, user_id, params)

    except Exception as e:
        status = "error"
        error_msg = str(e)
        result = {"error": error_msg}
        logger.error(f"MCP tool '{tool_name}' failed: {e}")

    # Calculate latency
    latency_ms = int((time.time() - start_time) * 1000)

    # Log usage
    log = MCPUsageLog(
        id=gen_id(),
        user_id=user_id,
        token_id=token_id,
        tool_name=tool_name,
        request_summary=json.dumps(params, ensure_ascii=False)[:500],
        status=status,
        latency_ms=latency_ms,
        error_message=error_msg,
    )
    db.add(log)
    await db.commit()

    return {
        "tool": tool_name,
        "status": status,
        "result": result,
        "latency_ms": latency_ms,
    }


# ═══════════════════════════════════════════
# READ Tool Implementations
# ═══════════════════════════════════════════

async def _tool_get_profile(db: AsyncSession, user_id: str) -> dict:
    """Get user profile data."""
    profile = await get_profile(db, user_id)
    if not profile.get("exists"):
        return {"message": "Profile not set up yet"}

    return {
        "identity_summary": profile.get("identity_summary", ""),
        "goals": profile.get("goals", ""),
        "working_style": profile.get("working_style", ""),
        "preferred_output_style": profile.get("preferred_output_style", ""),
        "background_context": profile.get("background_context", ""),
    }


async def _tool_list_files(db: AsyncSession, user_id: str) -> dict:
    """List all files with metadata."""
    result = await db.execute(
        select(File).where(File.user_id == user_id)
        .options(selectinload(File.summary), selectinload(File.insight))
    )
    files = result.scalars().all()

    return {
        "files": [
            {
                "file_id": f.id,
                "filename": f.filename,
                "filetype": f.filetype,
                "text_length": len(f.extracted_text or ""),
                "tags": json.loads(f.tags or "[]"),
                "sensitivity": f.sensitivity or "normal",
                "freshness": f.freshness or "current",
                "source_of_truth": f.source_of_truth or False,
                "importance": f.insight.importance_label if f.insight else "medium",
                "summary_snippet": (f.summary.summary_text[:150] + "...") if f.summary and f.summary.summary_text else "",
                "uploaded_at": f.uploaded_at.isoformat() if f.uploaded_at else "",
            }
            for f in files
        ],
        "count": len(files),
    }


async def _tool_get_file_content(db: AsyncSession, user_id: str, file_id: str) -> dict:
    """Get file extracted text (max 5000 chars)."""
    if not file_id:
        raise ValueError("file_id is required")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}

    text = file.extracted_text or ""
    truncated = len(text) > 5000

    return {
        "filename": file.filename,
        "filetype": file.filetype,
        "content": text[:5000],
        "total_length": len(text),
        "truncated": truncated,
    }


async def _tool_get_file_summary(db: AsyncSession, user_id: str, file_id: str) -> dict:
    """Get the summary of a specific file."""
    if not file_id:
        raise ValueError("file_id is required")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
        .options(selectinload(File.summary), selectinload(File.insight))
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}

    if not file.summary:
        return {"error": "Summary not yet generated for this file"}

    return {
        "filename": file.filename,
        "summary": file.summary.summary_text or "",
        "key_topics": json.loads(file.summary.key_topics or "[]"),
        "key_facts": json.loads(file.summary.key_facts or "[]"),
        "why_important": file.summary.why_important or "",
        "importance_label": file.insight.importance_label if file.insight else "medium",
        "source_of_truth": file.source_of_truth or False,
        "freshness": file.freshness or "current",
    }


async def _tool_list_collections(db: AsyncSession, user_id: str) -> dict:
    """List all clusters with files."""
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.user_id == user_id)
    )
    clusters = clusters_result.scalars().all()

    files_result = await db.execute(
        select(File).where(File.user_id == user_id)
        .options(selectinload(File.cluster_maps))
    )
    files = files_result.scalars().all()

    collections = []
    for c in clusters:
        cluster_files = []
        for f in files:
            for cm in f.cluster_maps:
                if cm.cluster_id == c.id:
                    cluster_files.append({"file_id": f.id, "filename": f.filename})
                    break

        collections.append({
            "collection_id": c.id,
            "title": c.title,
            "summary": c.summary or "",
            "file_count": len(cluster_files),
            "files": cluster_files,
        })

    return {"collections": collections, "count": len(collections)}


async def _tool_list_context_packs(db: AsyncSession, user_id: str) -> dict:
    """List all context packs."""
    packs = await list_packs(db, user_id)
    return {
        "packs": [
            {
                "pack_id": p["id"],
                "title": p["title"],
                "type": p["type"],
                "short_summary": (p.get("summary_text", "") or "")[:200],
                "updated_at": p.get("updated_at", ""),
            }
            for p in packs
        ],
        "count": len(packs),
    }


async def _tool_get_context_pack(db: AsyncSession, user_id: str, pack_id: str) -> dict:
    """Get a single context pack with full content."""
    if not pack_id:
        raise ValueError("pack_id is required")

    pack = await get_pack(db, pack_id, user_id)
    if not pack:
        return {"error": "Context pack not found"}

    return {
        "title": pack["title"],
        "type": pack["type"],
        "summary_text": pack.get("summary_text", ""),
        "source_file_ids": pack.get("source_file_ids", []),
        "source_cluster_ids": pack.get("source_cluster_ids", []),
        "updated_at": pack.get("updated_at", ""),
    }


# ═══════════════════════════════════════════
# SEARCH & GRAPH Tool Implementations
# ═══════════════════════════════════════════

async def _tool_search_knowledge(db: AsyncSession, user_id: str, query: str, limit: int = 5) -> dict:
    """Search knowledge base using hybrid search + graph nodes."""
    if not query:
        raise ValueError("query is required")
    limit = min(max(limit, 1), 10)

    results = []

    # Hybrid search from vector store
    if vector_search.is_available():
        hits = vector_search.hybrid_search(query, n_results=limit)
        for hit in hits:
            results.append({
                "filename": hit.get("filename", ""),
                "file_id": hit.get("file_id", ""),
                "text_snippet": hit.get("text", "")[:300],
                "relevance": round(hit.get("relevance", 0), 3),
                "search_mode": hit.get("search_mode", "hybrid"),
            })

    # Search context packs
    packs = await list_packs(db, user_id)
    query_lower = query.lower()
    matching_packs = [
        {
            "pack_id": p["id"],
            "title": p["title"],
            "type": p["type"],
            "short_summary": (p.get("summary_text", "") or "")[:200],
        }
        for p in packs
        if query_lower in (p.get("title", "") or "").lower()
        or query_lower in (p.get("summary_text", "") or "").lower()
    ]

    # Search graph nodes (NEW in v4.1)
    nodes_result = await db.execute(
        select(GraphNode).where(GraphNode.user_id == user_id)
    )
    all_nodes = nodes_result.scalars().all()
    matching_nodes = [
        {
            "node_id": n.id,
            "label": n.label,
            "type": n.object_type,
            "family": n.node_family,
        }
        for n in all_nodes
        if query_lower in (n.label or "").lower()
    ][:5]

    return {
        "query": query,
        "matched_files": results,
        "matched_packs": matching_packs[:3],
        "matched_nodes": matching_nodes,
    }


async def _tool_explore_graph(db: AsyncSession, user_id: str, node_id: str = None, depth: int = 1) -> dict:
    """Explore knowledge graph — overview or specific node neighborhood."""
    depth = min(max(depth, 1), 3)

    if not node_id:
        # Return overview of all nodes grouped by family
        nodes_result = await db.execute(
            select(GraphNode).where(GraphNode.user_id == user_id)
        )
        nodes = nodes_result.scalars().all()

        edges_result = await db.execute(
            select(GraphEdge).where(GraphEdge.user_id == user_id)
        )
        edges = edges_result.scalars().all()

        # Group by family
        families = {}
        for n in nodes:
            fam = n.node_family or "other"
            if fam not in families:
                families[fam] = []
            families[fam].append({
                "node_id": n.id,
                "label": n.label,
                "type": n.object_type,
                "importance": n.importance_score,
            })

        return {
            "mode": "overview",
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "families": families,
        }
    else:
        # Return neighborhood of a specific node
        node_result = await db.execute(
            select(GraphNode).where(GraphNode.id == node_id)
        )
        node = node_result.scalar_one_or_none()
        if not node:
            return {"error": "Node not found"}

        # Get edges involving this node
        edges_result = await db.execute(
            select(GraphEdge).where(
                (GraphEdge.source_node_id == node_id) | (GraphEdge.target_node_id == node_id)
            )
        )
        edges = edges_result.scalars().all()

        # Get connected node IDs
        connected_ids = set()
        connections = []
        for e in edges:
            other_id = e.target_node_id if e.source_node_id == node_id else e.source_node_id
            connected_ids.add(other_id)
            connections.append({
                "edge_type": e.edge_type,
                "direction": "outgoing" if e.source_node_id == node_id else "incoming",
                "connected_node_id": other_id,
                "weight": e.weight,
                "evidence": e.evidence_text or "",
            })

        # Get connected node labels
        if connected_ids:
            connected_result = await db.execute(
                select(GraphNode).where(GraphNode.id.in_(connected_ids))
            )
            connected_nodes = {n.id: n.label for n in connected_result.scalars().all()}
            for conn in connections:
                conn["connected_label"] = connected_nodes.get(conn["connected_node_id"], "?")

        return {
            "mode": "neighborhood",
            "node": {
                "node_id": node.id,
                "label": node.label,
                "type": node.object_type,
                "family": node.node_family,
                "importance": node.importance_score,
            },
            "connections": connections,
            "connection_count": len(connections),
        }


# ═══════════════════════════════════════════
# WRITE Tool Implementations
# ═══════════════════════════════════════════

async def _tool_create_context_pack(db: AsyncSession, user_id: str, params: dict) -> dict:
    """Create a new context pack."""
    title = params.get("title")
    pack_type = params.get("type")
    file_ids = params.get("file_ids", [])

    if not title:
        raise ValueError("title is required")
    if not pack_type:
        raise ValueError("type is required")
    if pack_type not in {"profile", "study", "work", "project"}:
        raise ValueError("type must be one of: profile, study, work, project")
    if not file_ids:
        raise ValueError("file_ids must contain at least one file ID")

    pack = await create_pack(db, user_id, pack_type, title, file_ids, [])

    return {
        "status": "created",
        "pack_id": pack.get("id", ""),
        "title": title,
        "type": pack_type,
        "file_count": len(file_ids),
    }


async def _tool_add_note(db: AsyncSession, user_id: str, params: dict) -> dict:
    """Update summary text for a file."""
    file_id = params.get("file_id")
    summary_text = params.get("summary_text")

    if not file_id:
        raise ValueError("file_id is required")
    if not summary_text:
        raise ValueError("summary_text is required")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
        .options(selectinload(File.summary))
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}
    if not file.summary:
        return {"error": "File has no summary yet — run 'Organize with AI' first"}

    file.summary.summary_text = summary_text
    await db.commit()

    return {
        "status": "updated",
        "file_id": file_id,
        "filename": file.filename,
        "summary_length": len(summary_text),
    }


async def _tool_update_file_tags(db: AsyncSession, user_id: str, params: dict) -> dict:
    """Update tags for a file."""
    file_id = params.get("file_id")
    tags = params.get("tags")

    if not file_id:
        raise ValueError("file_id is required")
    if tags is None:
        raise ValueError("tags is required")
    if not isinstance(tags, list):
        raise ValueError("tags must be an array of strings")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}

    file.tags = json.dumps(tags, ensure_ascii=False)
    await db.commit()

    return {
        "status": "updated",
        "file_id": file_id,
        "filename": file.filename,
        "tags": tags,
    }


# ═══════════════════════════════════════════
# SYSTEM Tool Implementations
# ═══════════════════════════════════════════

async def _tool_get_overview(db: AsyncSession, user_id: str) -> dict:
    """Get system overview stats."""
    files_count = (await db.execute(
        select(func.count(File.id)).where(File.user_id == user_id)
    )).scalar() or 0

    clusters_count = (await db.execute(
        select(func.count(Cluster.id)).where(Cluster.user_id == user_id)
    )).scalar() or 0

    packs_count = (await db.execute(
        select(func.count(ContextPack.id)).where(ContextPack.user_id == user_id)
    )).scalar() or 0

    nodes_count = (await db.execute(
        select(func.count(GraphNode.id)).where(GraphNode.user_id == user_id)
    )).scalar() or 0

    edges_count = (await db.execute(
        select(func.count(GraphEdge.id)).where(GraphEdge.user_id == user_id)
    )).scalar() or 0

    profile = await get_profile(db, user_id)

    return {
        "files": files_count,
        "collections": clusters_count,
        "context_packs": packs_count,
        "graph_nodes": nodes_count,
        "graph_edges": edges_count,
        "profile_set": profile.get("exists", False),
        "system": "Project KEY v4.1 — Personal Data Bank",
    }


# ═══════════════════════════════════════════
# ADMIN Tool Implementations
# ═══════════════════════════════════════════

def _tool_admin_login(admin_key: str) -> dict:
    """Verify admin password — grants bypass for disabled tools."""
    if admin_key == ADMIN_PASSWORD:
        all_tools = list(TOOL_REGISTRY.keys())
        return {
            "status": "authenticated",
            "message": "Admin verified — you can now use admin_key to bypass any disabled tool",
            "total_tools": len(all_tools),
            "hint": "Pass admin_key in any tool call to bypass its disabled state",
        }
    else:
        return {"status": "denied", "message": "Wrong admin password"}


async def _tool_delete_file(db: AsyncSession, user_id: str, file_id: str) -> dict:
    """Delete a file and all related data."""
    if not file_id:
        raise ValueError("file_id is required")

    import os
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}

    filename = file.filename

    # Delete raw file
    if file.raw_path and os.path.exists(file.raw_path):
        os.remove(file.raw_path)

    await db.delete(file)
    await db.commit()

    return {"status": "deleted", "filename": filename, "file_id": file_id}


async def _tool_delete_pack(db: AsyncSession, user_id: str, pack_id: str) -> dict:
    """Delete a context pack."""
    if not pack_id:
        raise ValueError("pack_id is required")

    deleted = await delete_pack(db, pack_id, user_id)
    if not deleted:
        return {"error": "Pack not found"}

    return {"status": "deleted", "pack_id": pack_id}


async def _tool_run_organize(db: AsyncSession, user_id: str) -> dict:
    """Run the full organization pipeline."""
    from .organizer import organize_files

    result = await organize_files(db, user_id)
    result = result or {}

    return {
        "status": "completed",
        "clusters_created": result.get("clusters_created", 0),
        "files_processed": result.get("files_processed", 0),
        "message": "Organization pipeline completed — summaries, clusters, and graph built",
    }


async def _tool_build_graph(db: AsyncSession, user_id: str) -> dict:
    """Rebuild the knowledge graph."""
    from .graph_builder import build_full_graph

    graph_result = await build_full_graph(db, user_id)
    graph_result = graph_result or {}

    return {
        "status": "completed",
        "nodes": graph_result.get("nodes", 0),
        "edges": graph_result.get("edges", 0),
        "message": "Knowledge graph rebuilt",
    }


async def _tool_enrich_metadata(db: AsyncSession, user_id: str) -> dict:
    """Enrich metadata for all files."""
    from .metadata import enrich_all_files

    result = await enrich_all_files(db, user_id)
    result = result or {}

    return {
        "status": "completed",
        "enriched": result.get("enriched", 0),
        "message": "Metadata enrichment completed",
    }


async def _tool_update_profile(db: AsyncSession, user_id: str, params: dict) -> dict:
    """Update user profile fields."""
    updates = {}
    for key in ["identity_summary", "goals", "working_style", "preferred_output_style", "background_context"]:
        if params.get(key):
            updates[key] = params[key]

    if not updates:
        return {"error": "No profile fields provided to update"}

    result = await update_profile(db, user_id, updates)

    return {
        "status": "updated",
        "updated_fields": list(updates.keys()),
        "message": f"Profile updated: {', '.join(updates.keys())}",
    }


async def _tool_upload_text(db: AsyncSession, user_id: str, params: dict) -> dict:
    """Upload text content as a new file."""
    import os
    from datetime import datetime

    filename = params.get("filename", "")
    content = params.get("content", "")

    if not filename:
        raise ValueError("filename is required")
    if not content:
        raise ValueError("content is required")

    # Ensure .md or .txt extension
    if not filename.endswith((".md", ".txt")):
        filename += ".md"

    file_id = gen_id()

    # Save raw file
    upload_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    safe_filename = f"{file_id}_{filename}"
    raw_path = os.path.join(upload_dir, safe_filename)

    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(content)

    # Determine filetype
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "md"

    # Save to DB
    db_file = File(
        id=file_id,
        user_id=user_id,
        filename=filename,
        filetype=ext,
        raw_path=raw_path,
        extracted_text=content,
        processing_status="uploaded",
    )
    db.add(db_file)
    await db.commit()

    return {
        "status": "uploaded",
        "file_id": file_id,
        "filename": filename,
        "text_length": len(content),
        "message": f"File '{filename}' uploaded — run 'run_organize' to process it",
    }

# ═══════════════════════════════════════════
# USAGE LOGS
# ═══════════════════════════════════════════

async def get_usage_logs(
    db: AsyncSession,
    user_id: str,
    tool_filter: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """Get MCP usage logs with optional filters."""
    query = select(MCPUsageLog).where(MCPUsageLog.user_id == user_id)

    if tool_filter:
        query = query.where(MCPUsageLog.tool_name == tool_filter)
    if status_filter:
        query = query.where(MCPUsageLog.status == status_filter)

    query = query.order_by(MCPUsageLog.created_at.desc()).limit(limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "tool_name": log.tool_name,
            "token_id": log.token_id,
            "request_summary": log.request_summary,
            "status": log.status,
            "latency_ms": log.latency_ms,
            "error_message": log.error_message,
            "created_at": log.created_at.isoformat() if log.created_at else "",
        }
        for log in logs
    ]
