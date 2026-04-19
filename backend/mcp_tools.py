"""MCP Tools — PDB Core API tool implementations for MVP v4.

Read-only tools that expose Project KEY data to external AI connectors.
These wrap existing services (profile, context_packs, retriever)
rather than duplicating logic.
"""
import json
import time
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import (
    File, Cluster, FileClusterMap, FileSummary, FileInsight,
    ContextPack, MCPUsageLog, gen_id
)
from .profile import get_profile
from .context_packs import list_packs, get_pack
from . import vector_search

logger = logging.getLogger(__name__)

# Available tools registry
TOOL_REGISTRY = {
    "get_profile": {
        "name": "get_profile",
        "description": "Get the user's profile including identity, goals, working style, and preferences",
        "params": [],
    },
    "list_context_packs": {
        "name": "list_context_packs",
        "description": "List all context packs (distilled knowledge bundles) available",
        "params": [],
    },
    "get_context_pack": {
        "name": "get_context_pack",
        "description": "Get a specific context pack by ID with full content",
        "params": [{"name": "pack_id", "type": "string", "required": True}],
    },
    "search_knowledge": {
        "name": "search_knowledge",
        "description": "Search the user's knowledge base using semantic + keyword hybrid search",
        "params": [
            {"name": "query", "type": "string", "required": True},
            {"name": "limit", "type": "integer", "required": False, "default": 5},
        ],
    },
    "get_file_summary": {
        "name": "get_file_summary",
        "description": "Get the AI-generated summary of a specific file",
        "params": [{"name": "file_id", "type": "string", "required": True}],
    },
}


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

        if tool_name == "get_profile":
            result = await _tool_get_profile(db, user_id)
        elif tool_name == "list_context_packs":
            result = await _tool_list_context_packs(db, user_id)
        elif tool_name == "get_context_pack":
            pack_id = params.get("pack_id")
            if not pack_id:
                raise ValueError("pack_id is required")
            result = await _tool_get_context_pack(db, user_id, pack_id)
        elif tool_name == "search_knowledge":
            query = params.get("query")
            if not query:
                raise ValueError("query is required")
            limit = params.get("limit", 5)
            result = await _tool_search_knowledge(db, user_id, query, limit)
        elif tool_name == "get_file_summary":
            file_id = params.get("file_id")
            if not file_id:
                raise ValueError("file_id is required")
            result = await _tool_get_file_summary(db, user_id, file_id)

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
# Tool Implementations
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


async def _tool_search_knowledge(db: AsyncSession, user_id: str, query: str, limit: int = 5) -> dict:
    """Search the knowledge base using hybrid search."""
    limit = min(max(limit, 1), 10)  # Clamp 1-10

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

    # Also search context packs by title
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

    return {
        "query": query,
        "matched_files": results,
        "matched_packs": matching_packs[:3],
    }


async def _tool_get_file_summary(db: AsyncSession, user_id: str, file_id: str) -> dict:
    """Get the summary of a specific file."""
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
        "importance_label": file.insight.importance_label if file.insight else "medium",
        "source_of_truth": file.source_of_truth or False,
        "freshness": file.freshness or "current",
    }


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

    # Resolve token labels
    from .database import MCPToken
    token_labels = {}

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
