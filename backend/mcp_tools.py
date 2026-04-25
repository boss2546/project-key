"""MCP Tools — PDB Core API tool implementations for MVP v4.1.

13 tools that expose Project KEY data to external AI connectors.
Read (7) + Search & Graph (2) + Write (3) + System (1).
"""
import os
import json
import time
import base64
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
from .config import ADMIN_PASSWORD
from . import context_memory

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# TOOL REGISTRY — 30 tools in 5 categories
# ═══════════════════════════════════════════

TOOL_REGISTRY = {
    # ─── 📖 READ & SEARCH (12) ───
    "get_profile": {
        "name": "get_profile",
        "description": "Get the user's profile including identity, goals, working style, and preferences",
        "params": [],
        "category": "read",
        "annotations": {"title": "View Profile", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "list_files": {
        "name": "list_files",
        "description": "List all files in the knowledge base with their metadata, tags, and summary snippets",
        "params": [],
        "category": "read",
        "annotations": {"title": "List Files", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "get_file_content": {
        "name": "get_file_content",
        "description": "Get the extracted text content of a specific file. Supports pagination with offset/limit for large files.",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
            {"name": "offset", "type": "integer", "required": False, "default": 0, "description": "Character offset to start from"},
            {"name": "limit", "type": "integer", "required": False, "default": 5000, "description": "Max characters to return (max 10000)"},
        ],
        "category": "read",
        "annotations": {"title": "Read File Content", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "get_file_link": {
        "name": "get_file_link",
        "description": "Get a temporary public download URL for a file. The URL is valid for 30 minutes and requires no authentication. Use this when you need to access the original file (PDF, DOCX, etc.) directly.",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
        ],
        "category": "read",
        "annotations": {"title": "Get Download Link", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "get_file_summary": {
        "name": "get_file_summary",
        "description": "Get the AI-generated summary, key topics, and key facts of a specific file",
        "params": [{"name": "file_id", "type": "string", "required": True}],
        "category": "read",
        "annotations": {"title": "View Summary", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "list_collections": {
        "name": "list_collections",
        "description": "List all AI-organized collections (clusters) with their files and summaries",
        "params": [],
        "category": "read",
        "annotations": {"title": "List Collections", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "list_context_packs": {
        "name": "list_context_packs",
        "description": "List all context packs (distilled knowledge bundles) available",
        "params": [],
        "category": "read",
        "annotations": {"title": "List Packs", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "get_context_pack": {
        "name": "get_context_pack",
        "description": "Get a specific context pack by ID with full content",
        "params": [{"name": "pack_id", "type": "string", "required": True}],
        "category": "read",
        "annotations": {"title": "View Pack", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "search_knowledge": {
        "name": "search_knowledge",
        "description": "Search the user's knowledge base using semantic + keyword hybrid search. Returns matching files, packs, and graph nodes.",
        "params": [
            {"name": "query", "type": "string", "required": True},
            {"name": "limit", "type": "integer", "required": False, "default": 5},
        ],
        "category": "read",
        "annotations": {"title": "Search Knowledge", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "explore_graph": {
        "name": "explore_graph",
        "description": "Explore the knowledge graph. Without a node_id, returns all nodes overview. With a node_id, returns the node's connections and neighborhood.",
        "params": [
            {"name": "node_id", "type": "string", "required": False},
            {"name": "depth", "type": "integer", "required": False, "default": 1},
        ],
        "category": "read",
        "annotations": {"title": "Explore Graph", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "get_overview": {
        "name": "get_overview",
        "description": "Get system overview with counts of files, collections, packs, graph nodes, and edges",
        "params": [],
        "category": "read",
        "annotations": {"title": "System Overview", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
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
        "annotations": {"title": "Create Pack", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    "add_note": {
        "name": "add_note",
        "description": "Update the summary text for a file. Use this to add notes or improve AI-generated summaries.",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
            {"name": "summary_text", "type": "string", "required": True},
        ],
        "category": "edit",
        "annotations": {"title": "Edit Note", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "update_file_tags": {
        "name": "update_file_tags",
        "description": "Update tags for a file. Use this to organize and categorize files.",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
            {"name": "tags", "type": "array", "required": True},
        ],
        "category": "edit",
        "annotations": {"title": "Update Tags", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "upload_text": {
        "name": "upload_text",
        "description": "Upload text content as a new file (Claude can create new knowledge files)",
        "params": [
            {"name": "filename", "type": "string", "required": True},
            {"name": "content", "type": "string", "required": True},
        ],
        "category": "edit",
        "annotations": {"title": "Upload Text", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
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
        "annotations": {"title": "Edit Profile", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },

    # ─── 🗑️ DELETE (2) — ต้องขออนุญาตก่อน (ลบข้อมูลถาวร) ───
    "delete_file": {
        "name": "delete_file",
        "description": "Delete a file and all its related data (summary, insights, clusters)",
        "params": [
            {"name": "file_id", "type": "string", "required": True},
        ],
        "category": "delete",
        "annotations": {"title": "Delete File", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
    },
    "delete_pack": {
        "name": "delete_pack",
        "description": "Delete a context pack",
        "params": [
            {"name": "pack_id", "type": "string", "required": True},
        ],
        "category": "delete",
        "annotations": {"title": "Delete Pack", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
    },

    # ─── ⚙️ AI PIPELINE (5) — ไม่ต้องขออนุญาต (ประมวลผลซ้ำได้) ───
    "run_organize": {
        "name": "run_organize",
        "description": "Run the full AI organization pipeline: summarize, cluster, build graph",
        "params": [],
        "category": "pipeline",
        "annotations": {"title": "Organize Data", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "build_graph": {
        "name": "build_graph",
        "description": "Rebuild the knowledge graph from all data",
        "params": [],
        "category": "pipeline",
        "annotations": {"title": "Build Graph", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "enrich_metadata": {
        "name": "enrich_metadata",
        "description": "Run AI metadata enrichment on all files (tags, sensitivity, freshness)",
        "params": [],
        "category": "pipeline",
        "annotations": {"title": "Enrich Metadata", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "reprocess_file": {
        "name": "reprocess_file",
        "description": "Re-extract text from a file using the latest extraction pipeline (includes OCR fallback + Thai text fix). Use for PDFs that showed no text or had broken spacing.",
        "params": [{"name": "file_id", "type": "string", "required": True}],
        "category": "pipeline",
        "annotations": {"title": "Reprocess File", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "admin_login": {
        "name": "admin_login",
        "description": "Verify admin password to bypass disabled tools",
        "params": [{"name": "admin_key", "type": "string", "required": True}],
        "category": "pipeline",
        "annotations": {"title": "Admin Login", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "export_file_to_chat": {
        "name": "export_file_to_chat",
        "description": "Export the original raw file from the knowledge base as a real file attachment in the chat. Returns the file as a downloadable attachment (PDF, TXT, MD, DOCX). If the platform does not support attachments, falls back to a signed 30-minute download URL.",
        "params": [{"name": "file_id", "type": "string", "required": True}],
        "category": "read",
        "annotations": {"title": "Export File", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },

    # ─── 🧠 CONTEXT MEMORY (6) — v5.5 Cross-Platform Context ───
    "save_context": {
        "name": "save_context",
        "description": "Save conversation context to your personal memory bank. AI SHOULD proactively suggest saving context when: 1) conversation is ending, 2) significant work is completed, 3) user switches topics. Smart Merge: if same title exists within 2 hours, updates existing instead of creating new. User only needs to confirm.",
        "params": [
            {"name": "title", "type": "string", "required": True, "description": "Context title (e.g. 'Project KEY v5.4 progress')"},
            {"name": "content", "type": "string", "required": True, "description": "Full context content (markdown)"},
            {"name": "context_type", "type": "string", "required": False, "default": "conversation", "description": "Type: conversation, project, task, note"},
            {"name": "tags", "type": "array", "required": False, "description": "Tags for categorization"},
            {"name": "related_file_ids", "type": "array", "required": False, "description": "Related file IDs from knowledge base"},
            {"name": "is_pinned", "type": "boolean", "required": False, "default": False, "description": "Pin for auto-load (max 3)"},
        ],
        "category": "context",
        "annotations": {"title": "Save Context", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False},
    },
    "load_context": {
        "name": "load_context",
        "description": "Load context from memory. Without context_id, returns latest context + all pinned contexts automatically. Call this at the start of every new conversation for best UX.",
        "params": [
            {"name": "context_id", "type": "string", "required": False, "description": "Specific context ID (optional — default: latest + pinned)"},
            {"name": "include_pinned", "type": "boolean", "required": False, "default": True, "description": "Include pinned contexts"},
        ],
        "category": "context",
        "annotations": {"title": "Load Context", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "list_contexts": {
        "name": "list_contexts",
        "description": "List all saved contexts with optional filters by type, pin status, or keyword search.",
        "params": [
            {"name": "limit", "type": "integer", "required": False, "default": 10},
            {"name": "context_type", "type": "string", "required": False},
            {"name": "is_pinned", "type": "boolean", "required": False},
            {"name": "search", "type": "string", "required": False},
        ],
        "category": "context",
        "annotations": {"title": "List Contexts", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "update_context": {
        "name": "update_context",
        "description": "Update an existing context (title, content, tags, pin status). Max 3 pinned contexts.",
        "params": [
            {"name": "context_id", "type": "string", "required": True},
            {"name": "title", "type": "string", "required": False},
            {"name": "content", "type": "string", "required": False},
            {"name": "summary", "type": "string", "required": False},
            {"name": "tags", "type": "array", "required": False},
            {"name": "is_pinned", "type": "boolean", "required": False},
            {"name": "is_active", "type": "boolean", "required": False},
        ],
        "category": "edit",
        "annotations": {"title": "Update Context", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
    },
    "delete_context": {
        "name": "delete_context",
        "description": "Permanently delete a saved context from memory.",
        "params": [{"name": "context_id", "type": "string", "required": True}],
        "category": "delete",
        "annotations": {"title": "Delete Context", "readOnlyHint": False, "destructiveHint": True, "idempotentHint": True, "openWorldHint": False},
    },
    "auto_context": {
        "name": "auto_context",
        "description": "Search and recommend relevant contexts matching a query. Uses keyword matching on title, summary, content, and tags.",
        "params": [
            {"name": "query", "type": "string", "required": True},
            {"name": "limit", "type": "integer", "required": False, "default": 3},
        ],
        "category": "context",
        "annotations": {"title": "Auto Context", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False},
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
            result = await _tool_get_file_content(db, user_id, params.get("file_id"), params.get("offset", 0), params.get("limit", 5000))
        elif tool_name == "get_file_link":
            result = await _tool_get_file_link(db, user_id, params.get("file_id"))
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
        elif tool_name == "reprocess_file":
            result = await _tool_reprocess_file(db, user_id, params.get("file_id"))
        elif tool_name == "export_file_to_chat":
            result = await _tool_export_file_to_chat(db, user_id, params.get("file_id"))

        # ─── CONTEXT MEMORY (v5.5) ───
        elif tool_name == "save_context":
            result = await context_memory.save_context(
                db, user_id, params.get("title"), params.get("content"),
                summary=params.get("summary", ""),
                context_type=params.get("context_type", "conversation"),
                platform=params.get("platform", "unknown"),
                tags=params.get("tags"),
                related_file_ids=params.get("related_file_ids"),
                is_pinned=params.get("is_pinned", False),
            )
        elif tool_name == "load_context":
            result = await context_memory.load_context(
                db, user_id,
                context_id=params.get("context_id"),
                include_pinned=params.get("include_pinned", True),
            )
        elif tool_name == "list_contexts":
            result = await context_memory.list_contexts(
                db, user_id,
                limit=params.get("limit", 10),
                context_type=params.get("context_type"),
                is_pinned=params.get("is_pinned"),
                search=params.get("search"),
            )
        elif tool_name == "update_context":
            result = await context_memory.update_context(
                db, user_id, params.get("context_id"),
                title=params.get("title"),
                content=params.get("content"),
                summary=params.get("summary"),
                tags=params.get("tags"),
                is_pinned=params.get("is_pinned"),
                is_active=params.get("is_active"),
            )
        elif tool_name == "delete_context":
            result = await context_memory.delete_context(
                db, user_id, params.get("context_id"),
            )
        elif tool_name == "auto_context":
            result = await context_memory.auto_context(
                db, user_id, params.get("query"), params.get("limit", 3),
            )

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
    """Get user profile data + active contexts (v5.5 bundling)."""
    profile = await get_profile(db, user_id)
    if not profile.get("exists"):
        return {"message": "Profile not set up yet"}

    # v5.5 — Bundle active contexts for zero-effort UX
    active_contexts = await context_memory.get_active_contexts_for_profile(db, user_id)

    result = {
        "identity_summary": profile.get("identity_summary", ""),
        "goals": profile.get("goals", ""),
        "working_style": profile.get("working_style", ""),
        "preferred_output_style": profile.get("preferred_output_style", ""),
        "background_context": profile.get("background_context", ""),
    }

    if active_contexts:
        result["active_contexts"] = active_contexts
        result["active_contexts_count"] = len(active_contexts)
        result["tip"] = "Active contexts are included. Use load_context(context_id) to get full content."

    return result


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
                "has_raw_file": bool(f.raw_path and os.path.exists(f.raw_path)),
            }
            for f in files
        ],
        "count": len(files),
        "tip": "Use get_file_content to preview text, or get_file_link to generate a download URL for any file.",
    }


async def _tool_get_file_content(db: AsyncSession, user_id: str, file_id: str, offset: int = 0, limit: int = 5000) -> dict:
    """Get file extracted text with pagination support."""
    if not file_id:
        raise ValueError("file_id is required")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}

    text = file.extracted_text or ""
    total = len(text)
    limit = min(max(limit, 100), 10000)  # clamp 100-10000
    offset = max(offset, 0)
    
    chunk = text[offset:offset + limit]
    has_more = (offset + limit) < total

    return {
        "filename": file.filename,
        "filetype": file.filetype,
        "content": chunk,
        "total_length": total,
        "offset": offset,
        "returned_length": len(chunk),
        "has_more": has_more,
        "next_offset": offset + limit if has_more else None,
        "has_raw_file": bool(file.raw_path and os.path.exists(file.raw_path)),
        "tip": "Use get_file_link to generate a download URL for the original file." if file.raw_path else None,
    }


async def _tool_get_file_link(db: AsyncSession, user_id: str, file_id: str) -> dict:
    """Generate a temporary public download URL for a file."""
    if not file_id:
        raise ValueError("file_id is required")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}

    if not file.raw_path or not os.path.exists(file.raw_path):
        return {"error": "Original file not available on server"}

    # Generate signed temporary link
    from .shared_links import generate_share_token, build_share_url
    token = generate_share_token(file.id, user_id, file.filename)
    url = build_share_url(token)

    return {
        "filename": file.filename,
        "filetype": file.filetype,
        "download_url": url,
        "expires_in": "30 minutes",
        "note": "This URL can be accessed directly without authentication. Use it to download or view the original file.",
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
    """Search knowledge base using hybrid search + graph nodes + DB fallback."""
    if not query:
        raise ValueError("query is required")
    limit = min(max(limit, 1), 10)

    results = []

    # Hybrid search from vector store
    if vector_search.is_available():
        hits = vector_search.hybrid_search(query, n_results=limit, user_id=user_id)
        for hit in hits:
            results.append({
                "filename": hit.get("filename", ""),
                "file_id": hit.get("file_id", ""),
                "text_snippet": hit.get("text", "")[:300],
                "relevance": round(hit.get("relevance", 0), 3),
                "search_mode": hit.get("search_mode", "hybrid"),
            })

    # Fallback: search directly in DB if vector search returned nothing
    if not results:
        query_lower = query.lower()
        files_res = await db.execute(
            select(File).where(File.user_id == user_id, File.processing_status == "ready")
        )
        all_files = files_res.scalars().all()

        # Search in summaries — v5.1: filter by user's files only
        user_fids = [f.id for f in all_files]
        if user_fids:
            summaries_res = await db.execute(
                select(FileSummary).where(FileSummary.file_id.in_(user_fids))
            )
        else:
            summaries_res = await db.execute(select(FileSummary).where(False))
        all_summaries = {s.file_id: s for s in summaries_res.scalars().all()}

        for f in all_files:
            score = 0
            snippet = ""

            # Check filename match
            if query_lower in f.filename.lower():
                score += 0.5

            # Check summary match
            summary = all_summaries.get(f.id)
            if summary and summary.summary_text:
                if query_lower in summary.summary_text.lower():
                    score += 0.4
                    idx = summary.summary_text.lower().find(query_lower)
                    start = max(0, idx - 50)
                    snippet = summary.summary_text[start:start + 300]

                # Check key_topics
                topics = summary.key_topics or "[]"
                if isinstance(topics, str):
                    import json as _json
                    try:
                        topics = _json.loads(topics)
                    except Exception:
                        topics = []
                if any(query_lower in str(t).lower() for t in topics):
                    score += 0.3

            # Check extracted text
            if not snippet and f.extracted_text and query_lower in f.extracted_text.lower():
                score += 0.3
                idx = f.extracted_text.lower().find(query_lower)
                start = max(0, idx - 50)
                snippet = f.extracted_text[start:start + 300]

            # Check tags
            import json as _json
            try:
                tags = _json.loads(f.tags or "[]") if isinstance(f.tags, str) else (f.tags or [])
            except Exception:
                tags = []
            if any(query_lower in str(tag).lower() for tag in tags):
                score += 0.2

            if score > 0:
                results.append({
                    "filename": f.filename,
                    "file_id": f.id,
                    "text_snippet": snippet[:300] if snippet else f"[{f.filename}]",
                    "relevance": round(min(score, 1.0), 3),
                    "search_mode": "db_fallback",
                })

        results.sort(key=lambda x: x["relevance"], reverse=True)
        results = results[:limit]

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

    # Search graph nodes
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
    """Update summary text for a file. Auto-creates summary record if none exists."""
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

    if file.summary:
        file.summary.summary_text = summary_text
    else:
        # Auto-create summary record so add_note works without organize
        new_summary = FileSummary(
            file_id=file_id,
            summary_text=summary_text,
            md_path="",
            key_topics="[]",
            key_facts="[]",
            why_important="",
            suggested_usage="",
        )
        db.add(new_summary)

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

    enriched = result.get("enriched", 0)
    total = result.get("total", 0)

    if enriched == 0 and total > 0:
        message = f"All {total} files already have metadata, or LLM enrichment was skipped. Try running 'run_organize' first for new files."
    elif enriched == 0:
        message = "No files found to enrich"
    else:
        message = f"Metadata enrichment completed — {enriched}/{total} files updated"

    return {
        "status": "completed",
        "enriched": enriched,
        "total_files": total,
        "message": message,
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


# ═══════════════════════════════════════════
# REPROCESS Tool (v5.2)
# ═══════════════════════════════════════════

async def _tool_reprocess_file(db: AsyncSession, user_id: str, file_id: str) -> dict:
    """Re-extract text from a file using the latest extraction pipeline.
    
    Includes:
    - OCR fallback for image-only PDFs
    - Thai text spacing fix
    - Improved error reporting
    """
    import os
    from .extraction import extract_text

    if not file_id:
        raise ValueError("file_id is required")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"error": "File not found"}

    if not file.raw_path or not os.path.exists(file.raw_path):
        return {"error": "Original file not available on server — cannot reprocess"}

    old_text = file.extracted_text or ""
    old_length = len(old_text)

    # Re-extract with updated pipeline
    raw_text = extract_text(file.raw_path, file.filetype)
    
    # LLM cleanup — fix Thai spacing, Private Use chars
    from .extraction import cleanup_extracted_text
    new_text = await cleanup_extracted_text(raw_text, file.filename)
    
    file.extracted_text = new_text
    file.processing_status = "reprocessed"
    await db.commit()

    return {
        "status": "reprocessed",
        "file_id": file.id,
        "filename": file.filename,
        "old_text_length": old_length,
        "new_text_length": len(new_text),
        "improved": len(new_text) != old_length,
        "extraction_method": "llm_cleanup",
        "preview": new_text[:500] if new_text else "",
    }


# ═══════════════════════════════════════════
# EXPORT FILE TO CHAT Tool (v5.4)
# ═══════════════════════════════════════════

# MIME type mapping
_MIME_MAP = {
    "pdf": "application/pdf",
    "txt": "text/plain",
    "md": "text/markdown",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}

# Max file size for inline embedding (10 MB)
_MAX_INLINE_SIZE = 10 * 1024 * 1024


async def _tool_export_file_to_chat(db: AsyncSession, user_id: str, file_id: str) -> dict:
    """Export the original raw file as an MCP EmbeddedResource (base64 blob).
    
    Returns a special dict with __mcp_content key that the MCP handler
    in main.py will detect and format as proper MCP content array
    (EmbeddedResource + text metadata).
    
    Falls back to a signed download URL if the file is too large
    or if the platform doesn't support attachments.
    """
    if not file_id:
        raise ValueError("file_id is required")

    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == user_id)
    )
    file = result.scalar_one_or_none()
    if not file:
        return {"status": "error", "error": "file_not_found"}

    if not file.raw_path or not os.path.exists(file.raw_path):
        return {"status": "error", "error": "raw_file_not_found"}

    # File metadata
    file_size = os.path.getsize(file.raw_path)
    mime_type = _MIME_MAP.get(file.filetype, "application/octet-stream")

    # Log access for sensitive files
    if file.sensitivity in ("sensitive", "confidential"):
        logger.info(f"SECURITY: export_file_to_chat accessed sensitive file '{file.filename}' "
                     f"(sensitivity={file.sensitivity}) by user={user_id}")

    # Check file size — if too large, fallback to URL
    if file_size > _MAX_INLINE_SIZE:
        from .shared_links import generate_share_token, build_share_url
        token = generate_share_token(file.id, user_id, file.filename)
        url = build_share_url(token)
        return {
            "status": "fallback_url",
            "filename": file.filename,
            "mime_type": mime_type,
            "size_bytes": file_size,
            "download_url": url,
            "expires_in": "30 minutes",
            "reason": "file_too_large_for_inline",
        }

    # Read and encode the file
    try:
        with open(file.raw_path, "rb") as f:
            raw_bytes = f.read()
        blob_b64 = base64.b64encode(raw_bytes).decode("ascii")
    except Exception as e:
        logger.error(f"Failed to read file '{file.filename}': {e}")
        return {"status": "error", "error": "file_read_failed", "detail": str(e)}

    # Also generate a fallback URL (always useful)
    from .shared_links import generate_share_token, build_share_url
    token = generate_share_token(file.id, user_id, file.filename)
    fallback_url = build_share_url(token)

    # Return special __mcp_content format that main.py will detect
    # and convert to MCP EmbeddedResource + text metadata
    return {
        "__mcp_content": [
            {
                "type": "resource",
                "resource": {
                    "uri": f"pdb://files/{file.id}/{file.filename}",
                    "mimeType": mime_type,
                    "blob": blob_b64,
                },
            },
            {
                "type": "text",
                "text": json.dumps({
                    "status": "attached",
                    "filename": file.filename,
                    "mime_type": mime_type,
                    "size_bytes": file_size,
                    "fallback_url": fallback_url,
                    "fallback_expires_in": "30 minutes",
                    "note": "The file has been attached above. If your platform cannot display it, use the fallback_url to download.",
                }, ensure_ascii=False, indent=2),
            },
        ],
    }
