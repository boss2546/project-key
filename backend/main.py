"""Project KEY — FastAPI Backend (MVP v0.1)"""
import os
import json
import logging
from datetime import datetime

from fastapi import FastAPI, UploadFile, File as FastAPIFile, Depends, HTTPException, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import (
    init_db, get_db, gen_id,
    User, File, Cluster, FileClusterMap, FileInsight, FileSummary
)
from .extraction import extract_text
from .organizer import organize_files
from .retriever import chat_with_retrieval
from .config import UPLOAD_DIR, BASE_DIR

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# App
app = FastAPI(title="Project KEY", version="0.1.0")

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


# ─── API ROUTES ───

@app.post("/api/upload")
async def upload_files(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Upload one or more files, extract text, save to database."""
    uploaded = []
    allowed_types = {"pdf", "txt", "md", "docx"}

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
    """Run the organization pipeline on all uploaded files."""
    try:
        await organize_files(db, DEFAULT_USER_ID)
        return {"status": "ok", "message": "Organization complete"}
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
    # Get clusters
    clusters_result = await db.execute(
        select(Cluster).where(Cluster.user_id == DEFAULT_USER_ID)
    )
    clusters = clusters_result.scalars().all()

    # Get all files with relationships
    files_result = await db.execute(
        select(File).where(File.user_id == DEFAULT_USER_ID)
        .options(
            selectinload(File.insight),
            selectinload(File.summary),
            selectinload(File.cluster_maps)
        )
    )
    files = files_result.scalars().all()

    # Build response
    cluster_list = []
    for c in clusters:
        # Find files in this cluster
        cluster_files = []
        for f in files:
            for cm in f.cluster_maps:
                if cm.cluster_id == c.id:
                    cluster_files.append(_serialize_file(f))
                    break

        cluster_list.append({
            "id": c.id,
            "title": c.title,
            "summary": c.summary,
            "file_count": len(cluster_files),
            "files": cluster_files
        })

    return {
        "clusters": cluster_list,
        "total_clusters": len(cluster_list),
        "total_files": len(files),
        "total_ready": sum(1 for f in files if f.processing_status == "ready")
    }


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


@app.post("/api/chat")
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """AI Chat with retrieval from user's organized data."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    try:
        result = await chat_with_retrieval(db, DEFAULT_USER_ID, req.question)
        return result
    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get storage/processing stats."""
    files_result = await db.execute(
        select(File).where(File.user_id == DEFAULT_USER_ID)
    )
    files = files_result.scalars().all()

    clusters_result = await db.execute(
        select(Cluster).where(Cluster.user_id == DEFAULT_USER_ID)
    )
    clusters = clusters_result.scalars().all()

    return {
        "total_files": len(files),
        "total_clusters": len(clusters),
        "processed": sum(1 for f in files if f.processing_status == "ready"),
        "processing": sum(1 for f in files if f.processing_status == "processing"),
        "errors": sum(1 for f in files if f.processing_status == "error")
    }


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a file and its related data."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == DEFAULT_USER_ID)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Delete raw file
    if file.raw_path and os.path.exists(file.raw_path):
        os.remove(file.raw_path)

    await db.delete(file)
    await db.commit()
    return {"status": "ok"}


@app.delete("/api/reset")
async def reset_all(db: AsyncSession = Depends(get_db)):
    """Delete all data for the user (for testing)."""
    # Delete all files, clusters, etc.
    files_result = await db.execute(select(File).where(File.user_id == DEFAULT_USER_ID))
    for f in files_result.scalars().all():
        if f.raw_path and os.path.exists(f.raw_path):
            os.remove(f.raw_path)
        await db.delete(f)

    clusters_result = await db.execute(select(Cluster).where(Cluster.user_id == DEFAULT_USER_ID))
    for c in clusters_result.scalars().all():
        await db.delete(c)

    await db.commit()
    return {"status": "ok", "message": "All data cleared"}


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
        "snippet": (f.summary.summary_text[:120] + "...") if f.summary and f.summary.summary_text else ""
    }


# ─── SERVE FRONTEND ───

# Serve frontend static files
@app.get("/")
async def serve_index():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))


@app.get("/{filename}")
async def serve_static(filename: str):
    filepath = os.path.join(BASE_DIR, filename)
    if os.path.exists(filepath) and not os.path.isdir(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404)
