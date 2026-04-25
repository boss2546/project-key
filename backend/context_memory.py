"""Context Memory service — v5.5 Cross-Platform Context Persistence.

Zero-Effort Context design:
- Auto-Load: latest + pinned on every platform switch
- Smart Merge: update existing if same title within 2 hours
- Auto-Archive: keep max 20 active contexts per user
- Auto-Summary: generate summary from content if not provided
- Max 3 Pinned: prevent token overload
"""
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession

from .database import ContextMemory, gen_id

logger = logging.getLogger(__name__)

# ── Limits ──────────────────────────────────
MAX_ACTIVE_CONTEXTS = 20
MAX_PINNED_CONTEXTS = 3
SMART_MERGE_HOURS = 2


async def save_context(
    db: AsyncSession,
    user_id: str,
    title: str,
    content: str,
    summary: str = "",
    context_type: str = "conversation",
    platform: str = "unknown",
    tags: list = None,
    related_file_ids: list = None,
    is_pinned: bool = False,
) -> dict:
    """Save a new context or smart-merge with existing one.
    
    Smart Merge: if a context with similar title exists and was updated
    within SMART_MERGE_HOURS, update that one instead of creating new.
    """
    tags = tags or []
    related_file_ids = related_file_ids or []

    # ── Smart Merge Check ───────────────────
    merge_cutoff = datetime.utcnow() - timedelta(hours=SMART_MERGE_HOURS)
    existing = await db.execute(
        select(ContextMemory)
        .where(
            ContextMemory.user_id == user_id,
            ContextMemory.title == title,
            ContextMemory.is_active == True,
            ContextMemory.updated_at >= merge_cutoff,
        )
        .order_by(desc(ContextMemory.updated_at))
        .limit(1)
    )
    merged_ctx = existing.scalar_one_or_none()

    if merged_ctx:
        # Update existing context (smart merge)
        merged_ctx.content = content
        merged_ctx.summary = summary or _auto_summary(content)
        merged_ctx.context_type = context_type
        merged_ctx.platform = platform
        merged_ctx.tags = json.dumps(tags, ensure_ascii=False)
        merged_ctx.related_file_ids = json.dumps(related_file_ids)
        merged_ctx.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(merged_ctx)
        logger.info(f"Smart-merged context {merged_ctx.id} for user {user_id}")
        return _to_dict(merged_ctx, merged=True)

    # ── Pin limit check ─────────────────────
    if is_pinned:
        pin_count = await db.execute(
            select(func.count()).select_from(ContextMemory).where(
                ContextMemory.user_id == user_id,
                ContextMemory.is_pinned == True,
                ContextMemory.is_active == True,
            )
        )
        if pin_count.scalar() >= MAX_PINNED_CONTEXTS:
            is_pinned = False  # Don't pin, will notify in response

    # ── Create new context ──────────────────
    ctx = ContextMemory(
        id=gen_id(),
        user_id=user_id,
        title=title,
        content=content,
        summary=summary or _auto_summary(content),
        context_type=context_type,
        platform=platform,
        tags=json.dumps(tags, ensure_ascii=False),
        related_file_ids=json.dumps(related_file_ids),
        is_pinned=is_pinned,
    )
    db.add(ctx)
    await db.commit()
    await db.refresh(ctx)
    logger.info(f"Saved new context {ctx.id} for user {user_id}")

    # ── Auto-Archive if over limit ──────────
    await _auto_archive(db, user_id)

    return _to_dict(ctx, merged=False)


async def load_context(
    db: AsyncSession,
    user_id: str,
    context_id: str = None,
    include_pinned: bool = True,
) -> dict:
    """Load context(s). Default = latest + pinned."""
    contexts = []

    if context_id:
        # Load specific context
        result = await db.execute(
            select(ContextMemory).where(
                ContextMemory.id == context_id,
                ContextMemory.user_id == user_id,
            )
        )
        ctx = result.scalar_one_or_none()
        if not ctx:
            return {"status": "error", "error": "context_not_found"}
        ctx.last_used_at = datetime.utcnow()
        await db.commit()
        contexts.append(_to_dict(ctx))
    else:
        # Load latest + pinned (default behavior)
        seen_ids = set()

        # 1. Pinned contexts
        if include_pinned:
            pinned = await db.execute(
                select(ContextMemory).where(
                    ContextMemory.user_id == user_id,
                    ContextMemory.is_pinned == True,
                    ContextMemory.is_active == True,
                ).order_by(desc(ContextMemory.updated_at))
            )
            for ctx in pinned.scalars().all():
                ctx.last_used_at = datetime.utcnow()
                contexts.append(_to_dict(ctx))
                seen_ids.add(ctx.id)

        # 2. Latest context (if not already in pinned)
        latest = await db.execute(
            select(ContextMemory).where(
                ContextMemory.user_id == user_id,
                ContextMemory.is_active == True,
            ).order_by(desc(ContextMemory.updated_at)).limit(1)
        )
        latest_ctx = latest.scalar_one_or_none()
        if latest_ctx and latest_ctx.id not in seen_ids:
            latest_ctx.last_used_at = datetime.utcnow()
            contexts.append(_to_dict(latest_ctx))

        await db.commit()

    return {
        "status": "loaded",
        "contexts": contexts,
        "count": len(contexts),
        "tip": "Context loaded. Continue from where you left off." if contexts else "No contexts found. Start fresh!",
    }


async def list_contexts(
    db: AsyncSession,
    user_id: str,
    limit: int = 10,
    context_type: str = None,
    is_pinned: bool = None,
    search: str = None,
) -> dict:
    """List all contexts with optional filters."""
    query = select(ContextMemory).where(
        ContextMemory.user_id == user_id,
        ContextMemory.is_active == True,
    )
    if context_type:
        query = query.where(ContextMemory.context_type == context_type)
    if is_pinned is not None:
        query = query.where(ContextMemory.is_pinned == is_pinned)
    if search:
        query = query.where(
            ContextMemory.title.ilike(f"%{search}%")
            | ContextMemory.summary.ilike(f"%{search}%")
            | ContextMemory.tags.ilike(f"%{search}%")
        )

    query = query.order_by(desc(ContextMemory.updated_at)).limit(min(limit, 50))
    result = await db.execute(query)
    ctxs = result.scalars().all()

    return {
        "contexts": [_to_summary_dict(c) for c in ctxs],
        "count": len(ctxs),
    }


async def update_context(
    db: AsyncSession,
    user_id: str,
    context_id: str,
    **kwargs,
) -> dict:
    """Update an existing context."""
    result = await db.execute(
        select(ContextMemory).where(
            ContextMemory.id == context_id,
            ContextMemory.user_id == user_id,
        )
    )
    ctx = result.scalar_one_or_none()
    if not ctx:
        return {"status": "error", "error": "context_not_found"}

    # Handle pin limit
    if kwargs.get("is_pinned") and not ctx.is_pinned:
        pin_count = await db.execute(
            select(func.count()).select_from(ContextMemory).where(
                ContextMemory.user_id == user_id,
                ContextMemory.is_pinned == True,
                ContextMemory.is_active == True,
            )
        )
        if pin_count.scalar() >= MAX_PINNED_CONTEXTS:
            return {
                "status": "error",
                "error": "max_pinned_reached",
                "message": f"สูงสุด {MAX_PINNED_CONTEXTS} — กรุณาถอด pin อันเก่าก่อน",
            }

    for key in ("title", "content", "summary", "context_type", "is_pinned", "is_active"):
        if key in kwargs and kwargs[key] is not None:
            setattr(ctx, key, kwargs[key])

    if "tags" in kwargs and kwargs["tags"] is not None:
        ctx.tags = json.dumps(kwargs["tags"], ensure_ascii=False)

    ctx.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ctx)

    return {"status": "updated", "context": _to_dict(ctx)}


async def delete_context(
    db: AsyncSession,
    user_id: str,
    context_id: str,
) -> dict:
    """Delete a context permanently."""
    result = await db.execute(
        select(ContextMemory).where(
            ContextMemory.id == context_id,
            ContextMemory.user_id == user_id,
        )
    )
    ctx = result.scalar_one_or_none()
    if not ctx:
        return {"status": "error", "error": "context_not_found"}

    await db.delete(ctx)
    await db.commit()
    return {"status": "deleted", "context_id": context_id}


async def auto_context(
    db: AsyncSession,
    user_id: str,
    query: str,
    limit: int = 3,
) -> dict:
    """Recommend contexts matching a query (keyword search)."""
    result = await db.execute(
        select(ContextMemory).where(
            ContextMemory.user_id == user_id,
            ContextMemory.is_active == True,
            ContextMemory.title.ilike(f"%{query}%")
            | ContextMemory.summary.ilike(f"%{query}%")
            | ContextMemory.content.ilike(f"%{query}%")
            | ContextMemory.tags.ilike(f"%{query}%"),
        )
        .order_by(desc(ContextMemory.updated_at))
        .limit(min(limit, 10))
    )
    ctxs = result.scalars().all()

    return {
        "recommended": [
            {
                "context_id": c.id,
                "title": c.title,
                "summary": c.summary,
                "context_type": c.context_type,
                "relevance": "keyword_match",
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in ctxs
        ],
        "count": len(ctxs),
    }


async def get_active_contexts_for_profile(
    db: AsyncSession,
    user_id: str,
) -> list:
    """Get active contexts to bundle with get_profile response.
    Returns title + summary only (no full content) to save tokens.
    """
    contexts = []
    seen_ids = set()

    # Pinned first
    pinned = await db.execute(
        select(ContextMemory).where(
            ContextMemory.user_id == user_id,
            ContextMemory.is_pinned == True,
            ContextMemory.is_active == True,
        ).order_by(desc(ContextMemory.updated_at))
    )
    for ctx in pinned.scalars().all():
        contexts.append(_to_summary_dict(ctx))
        seen_ids.add(ctx.id)

    # Latest (if not pinned)
    latest = await db.execute(
        select(ContextMemory).where(
            ContextMemory.user_id == user_id,
            ContextMemory.is_active == True,
        ).order_by(desc(ContextMemory.updated_at)).limit(1)
    )
    latest_ctx = latest.scalar_one_or_none()
    if latest_ctx and latest_ctx.id not in seen_ids:
        contexts.append(_to_summary_dict(latest_ctx))

    return contexts


# ── Private helpers ─────────────────────────

def _auto_summary(content: str) -> str:
    """Generate a simple summary from content (first 200 chars).
    For MVP — can be enhanced with LLM later.
    """
    if not content:
        return ""
    clean = content.strip().replace("\n", " ")
    return clean[:200] + ("..." if len(clean) > 200 else "")


async def _auto_archive(db: AsyncSession, user_id: str):
    """Archive oldest contexts if user exceeds MAX_ACTIVE_CONTEXTS."""
    count_result = await db.execute(
        select(func.count()).select_from(ContextMemory).where(
            ContextMemory.user_id == user_id,
            ContextMemory.is_active == True,
        )
    )
    total = count_result.scalar()

    if total <= MAX_ACTIVE_CONTEXTS:
        return

    # Find oldest non-pinned active contexts to archive
    excess = total - MAX_ACTIVE_CONTEXTS
    oldest = await db.execute(
        select(ContextMemory).where(
            ContextMemory.user_id == user_id,
            ContextMemory.is_active == True,
            ContextMemory.is_pinned == False,
        )
        .order_by(ContextMemory.updated_at)
        .limit(excess)
    )
    for ctx in oldest.scalars().all():
        ctx.is_active = False
        logger.info(f"Auto-archived context {ctx.id} for user {user_id}")

    await db.commit()


def _to_dict(ctx: ContextMemory, merged: bool = False) -> dict:
    """Full context dict (for load_context)."""
    return {
        "context_id": ctx.id,
        "title": ctx.title,
        "summary": ctx.summary,
        "content": ctx.content,
        "context_type": ctx.context_type,
        "platform": ctx.platform,
        "tags": _safe_json(ctx.tags),
        "is_active": ctx.is_active,
        "is_pinned": ctx.is_pinned,
        "created_at": ctx.created_at.isoformat() if ctx.created_at else None,
        "updated_at": ctx.updated_at.isoformat() if ctx.updated_at else None,
        "last_used_at": ctx.last_used_at.isoformat() if ctx.last_used_at else None,
        "related_file_ids": _safe_json(ctx.related_file_ids),
        "parent_id": ctx.parent_id,
        "merged": merged,
    }


def _to_summary_dict(ctx: ContextMemory) -> dict:
    """Summary dict (for list/profile bundling — no full content)."""
    return {
        "context_id": ctx.id,
        "title": ctx.title,
        "summary": ctx.summary,
        "context_type": ctx.context_type,
        "platform": ctx.platform,
        "tags": _safe_json(ctx.tags),
        "is_pinned": ctx.is_pinned,
        "updated_at": ctx.updated_at.isoformat() if ctx.updated_at else None,
    }


def _safe_json(text: str) -> list:
    """Safely parse JSON text to list."""
    try:
        return json.loads(text) if text else []
    except (json.JSONDecodeError, TypeError):
        return []
