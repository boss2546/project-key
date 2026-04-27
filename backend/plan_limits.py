"""Plan limits & usage enforcement — PRD v5.9.3

Single source of truth for Free vs Starter plan quotas.
All endpoints MUST use these helpers to check limits.
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# ═══════════════════════════════════════════
# 1. PLAN DEFINITIONS — the only place limits live
# ═══════════════════════════════════════════

PLAN_LIMITS = {
    "free": {
        "context_pack_limit": 1,
        "file_limit": 5,
        "storage_limit_mb": 50,
        "max_file_size_mb": 10,
        "ai_summary_limit_monthly": 5,
        "export_limit_monthly": 10,
        "refresh_limit_monthly": 0,
        "semantic_search_enabled": False,
        "version_history_days": 0,
        "allowed_file_types": {"pdf", "docx", "txt", "md", "csv"},
    },
    "starter": {
        "context_pack_limit": 5,
        "file_limit": 50,
        "storage_limit_mb": 1024,
        "max_file_size_mb": 20,
        "ai_summary_limit_monthly": 100,
        "export_limit_monthly": 300,
        "refresh_limit_monthly": 10,
        "semantic_search_enabled": True,
        "version_history_days": 7,
        "allowed_file_types": {"pdf", "docx", "txt", "md", "csv", "png", "jpg"},
    },
}


def get_limits(user) -> dict:
    """Return the limits dict for a user based on their effective plan."""
    plan = _effective_plan(user)
    return PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])


def _effective_plan(user) -> str:
    """Determine effective plan considering subscription status.

    starter_active / starter_past_due / starter_canceled (before period end)
    all count as 'starter' access.
    """
    status = getattr(user, "subscription_status", "free") or "free"
    if status == "starter_active":
        return "starter"
    if status == "starter_past_due":
        # Grace period — still starter
        return "starter"
    if status == "starter_canceled":
        # Active until period end
        period_end = getattr(user, "current_period_end", None)
        if period_end and period_end > datetime.utcnow():
            return "starter"
        return "free"
    return "free"


# ═══════════════════════════════════════════
# 2. USAGE QUERY HELPERS
# ═══════════════════════════════════════════

async def get_file_count(db: AsyncSession, user_id: str) -> int:
    from .database import File
    result = await db.execute(
        select(func.count(File.id)).where(File.user_id == user_id)
    )
    return result.scalar() or 0


async def get_storage_used_mb(db: AsyncSession, user_id: str) -> float:
    """Calculate total storage used by user in MB."""
    from .database import File
    import os
    result = await db.execute(
        select(File.raw_path).where(File.user_id == user_id)
    )
    total = 0
    for (path,) in result.fetchall():
        try:
            total += os.path.getsize(path)
        except OSError:
            pass
    return round(total / (1024 * 1024), 2)


async def get_pack_count(db: AsyncSession, user_id: str) -> int:
    from .database import ContextPack
    result = await db.execute(
        select(func.count(ContextPack.id)).where(ContextPack.user_id == user_id)
    )
    return result.scalar() or 0


async def get_monthly_summary_count(db: AsyncSession, user_id: str) -> int:
    """Count AI summaries generated this month by the user."""
    from .database import UsageLog
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user_id,
            UsageLog.action == "ai_summary",
            UsageLog.created_at >= month_start,
        )
    )
    return result.scalar() or 0


async def get_monthly_export_count(db: AsyncSession, user_id: str) -> int:
    """Count exports generated this month by the user."""
    from .database import UsageLog
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user_id,
            UsageLog.action == "export",
            UsageLog.created_at >= month_start,
        )
    )
    return result.scalar() or 0


async def get_monthly_refresh_count(db: AsyncSession, user_id: str) -> int:
    """Count context refreshes this month by the user."""
    from .database import UsageLog
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user_id,
            UsageLog.action == "refresh",
            UsageLog.created_at >= month_start,
        )
    )
    return result.scalar() or 0


async def log_usage(db: AsyncSession, user_id: str, action: str):
    """Record a usage event (ai_summary, export, refresh)."""
    from .database import UsageLog
    entry = UsageLog(user_id=user_id, action=action)
    db.add(entry)
    # Don't commit — caller should commit as part of their transaction


# ═══════════════════════════════════════════
# 3. ENFORCEMENT — check before action
# ═══════════════════════════════════════════

async def check_upload_allowed(db: AsyncSession, user, file_size_bytes: int, file_ext: str) -> dict | None:
    """Return None if allowed, or {"error": "...", "upgrade": True/False}."""
    limits = get_limits(user)

    # File type check
    if file_ext.lower() not in limits["allowed_file_types"]:
        return {"error": f"ไฟล์ .{file_ext} ไม่รองรับในแพลนปัจจุบัน", "upgrade": _effective_plan(user) == "free"}

    # File size check
    max_bytes = limits["max_file_size_mb"] * 1024 * 1024
    if file_size_bytes > max_bytes:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": f"Free plan รองรับไฟล์สูงสุด {limits['max_file_size_mb']}MB — อัปเกรดเป็น Starter เพื่ออัปโหลดไฟล์สูงสุด 20MB", "upgrade": True}
        return {"error": f"Starter รองรับไฟล์สูงสุด {limits['max_file_size_mb']}MB", "upgrade": False}

    # File count check
    count = await get_file_count(db, user.id)
    if count >= limits["file_limit"]:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": f"Free plan จำกัด {limits['file_limit']} ไฟล์ — อัปเกรดเป็น Starter เพื่อเก็บได้ 50 ไฟล์", "upgrade": True}
        return {"error": f"คุณใช้ไฟล์ครบ {limits['file_limit']} ไฟล์แล้ว", "upgrade": False}

    # Storage check
    storage = await get_storage_used_mb(db, user.id)
    new_file_mb = file_size_bytes / (1024 * 1024)
    if storage + new_file_mb > limits["storage_limit_mb"]:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": f"พื้นที่ Free ({limits['storage_limit_mb']}MB) เต็มแล้ว — อัปเกรดเป็น Starter เพื่อพื้นที่ 1GB", "upgrade": True}
        return {"error": "พื้นที่จัดเก็บเต็มแล้ว — ลบไฟล์ที่ไม่ใช้เพื่อเพิ่มพื้นที่", "upgrade": False}

    return None  # Allowed


async def check_pack_create_allowed(db: AsyncSession, user) -> dict | None:
    """Return None if allowed, or error dict."""
    limits = get_limits(user)
    count = await get_pack_count(db, user.id)
    if count >= limits["context_pack_limit"]:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": "Free plan จำกัด 1 Context Pack — อัปเกรดเป็น Starter เพื่อสร้างได้ 5 packs", "upgrade": True}
        return {"error": f"คุณสร้าง Context Pack ครบ {limits['context_pack_limit']} แล้ว", "upgrade": False}
    return None


async def check_summary_allowed(db: AsyncSession, user) -> dict | None:
    """Check if user can generate another AI summary this month."""
    limits = get_limits(user)
    used = await get_monthly_summary_count(db, user.id)
    if used >= limits["ai_summary_limit_monthly"]:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": "สรุป AI เดือนนี้ใช้ครบแล้ว (5/5) — อัปเกรดเป็น Starter เพื่อสรุปได้ 100 ครั้ง/เดือน", "upgrade": True}
        return {"error": "สรุป AI เดือนนี้ใช้ครบแล้ว — โควต้าจะรีเซ็ตรอบบิลถัดไป", "upgrade": False}
    return None


async def check_export_allowed(db: AsyncSession, user) -> dict | None:
    """Check if user can export another prompt this month."""
    limits = get_limits(user)
    used = await get_monthly_export_count(db, user.id)
    if used >= limits["export_limit_monthly"]:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": "Export เดือนนี้ใช้ครบแล้ว (10/10) — อัปเกรดเป็น Starter เพื่อ Export 300 ครั้ง/เดือน", "upgrade": True}
        return {"error": "Export เดือนนี้ใช้ครบแล้ว — โควต้าจะรีเซ็ตรอบบิลถัดไป", "upgrade": False}
    return None


async def check_refresh_allowed(db: AsyncSession, user) -> dict | None:
    """Check if user can refresh context this month."""
    limits = get_limits(user)
    if limits["refresh_limit_monthly"] == 0:
        return {"error": "Context Refresh ใช้ได้ใน Starter — อัปเกรดเพื่อรีเฟรช Context Pack ของคุณ", "upgrade": True}
    used = await get_monthly_refresh_count(db, user.id)
    if used >= limits["refresh_limit_monthly"]:
        return {"error": f"Refresh เดือนนี้ใช้ครบแล้ว ({limits['refresh_limit_monthly']}) — โควต้าจะรีเซ็ตรอบบิลถัดไป", "upgrade": False}
    return None


def check_semantic_search_allowed(user) -> dict | None:
    """Check if user can use semantic search."""
    limits = get_limits(user)
    if not limits["semantic_search_enabled"]:
        return {"error": "Semantic Search ใช้ได้ใน Starter — อัปเกรดเพื่อค้นหาด้วย AI", "upgrade": True}
    return None


# ═══════════════════════════════════════════
# 4. USAGE SUMMARY — for dashboard display
# ═══════════════════════════════════════════

async def get_usage_summary(db: AsyncSession, user) -> dict:
    """Return full usage summary for dashboard display."""
    limits = get_limits(user)
    plan = _effective_plan(user)

    files_count = await get_file_count(db, user.id)
    storage_mb = await get_storage_used_mb(db, user.id)
    packs_count = await get_pack_count(db, user.id)
    summaries_used = await get_monthly_summary_count(db, user.id)
    exports_used = await get_monthly_export_count(db, user.id)
    refreshes_used = await get_monthly_refresh_count(db, user.id)

    return {
        "plan": plan,
        "subscription_status": getattr(user, "subscription_status", "free") or "free",
        "limits": limits,
        "usage": {
            "context_packs": {"used": packs_count, "limit": limits["context_pack_limit"]},
            "files": {"used": files_count, "limit": limits["file_limit"]},
            "storage_mb": {"used": storage_mb, "limit": limits["storage_limit_mb"]},
            "ai_summaries": {"used": summaries_used, "limit": limits["ai_summary_limit_monthly"]},
            "exports": {"used": exports_used, "limit": limits["export_limit_monthly"]},
            "refreshes": {"used": refreshes_used, "limit": limits["refresh_limit_monthly"]},
        },
        "features": {
            "semantic_search": limits["semantic_search_enabled"],
            "version_history_days": limits["version_history_days"],
        },
    }
