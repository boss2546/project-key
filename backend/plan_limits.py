"""Plan limits & usage enforcement — PRD v5.9.3

Single source of truth for Free vs Starter plan quotas.
All endpoints MUST use these helpers to check limits.
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import func, select, and_
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


def _get_billing_period_start(user) -> datetime | None:
    """Get billing period start for Starter users.
    
    Starter users reset quota based on Stripe billing cycle.
    Free users reset based on calendar month.
    Returns None for Free users (will default to calendar month).
    """
    status = getattr(user, "subscription_status", "free") or "free"
    if status.startswith("starter"):
        period_start = getattr(user, "current_period_start", None)
        if period_start:
            return period_start
    return None  # Free users use calendar month


def _month_start_for_user(user) -> datetime:
    """Get the appropriate month start for counting usage."""
    billing_start = _get_billing_period_start(user)
    if billing_start:
        return billing_start
    return datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)


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


async def get_monthly_summary_count(db: AsyncSession, user_id: str, period_start: datetime | None = None) -> int:
    """Count AI summaries generated this billing period by the user."""
    from .database import UsageLog
    if period_start is None:
        period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user_id,
            UsageLog.action == "ai_summary",
            UsageLog.created_at >= period_start,
        )
    )
    return result.scalar() or 0


async def get_monthly_export_count(db: AsyncSession, user_id: str, period_start: datetime | None = None) -> int:
    """Count exports generated this billing period by the user."""
    from .database import UsageLog
    if period_start is None:
        period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user_id,
            UsageLog.action == "export",
            UsageLog.created_at >= period_start,
        )
    )
    return result.scalar() or 0


async def get_monthly_refresh_count(db: AsyncSession, user_id: str, period_start: datetime | None = None) -> int:
    """Count context refreshes this billing period by the user."""
    from .database import UsageLog
    if period_start is None:
        period_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(UsageLog.id)).where(
            UsageLog.user_id == user_id,
            UsageLog.action == "refresh",
            UsageLog.created_at >= period_start,
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
    """Check if user can generate another AI summary this billing period."""
    limits = get_limits(user)
    period_start = _month_start_for_user(user)
    used = await get_monthly_summary_count(db, user.id, period_start)
    if used >= limits["ai_summary_limit_monthly"]:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": "สรุป AI เดือนนี้ใช้ครบแล้ว (5/5) — อัปเกรดเป็น Starter เพื่อสรุปได้ 100 ครั้ง/เดือน", "upgrade": True}
        return {"error": "สรุป AI เดือนนี้ใช้ครบแล้ว — โควต้าจะรีเซ็ตรอบบิลถัดไป", "upgrade": False}
    return None


async def check_export_allowed(db: AsyncSession, user) -> dict | None:
    """Check if user can export another prompt this billing period."""
    limits = get_limits(user)
    period_start = _month_start_for_user(user)
    used = await get_monthly_export_count(db, user.id, period_start)
    if used >= limits["export_limit_monthly"]:
        plan = _effective_plan(user)
        if plan == "free":
            return {"error": "Export เดือนนี้ใช้ครบแล้ว (10/10) — อัปเกรดเป็น Starter เพื่อ Export 300 ครั้ง/เดือน", "upgrade": True}
        return {"error": "Export เดือนนี้ใช้ครบแล้ว — โควต้าจะรีเซ็ตรอบบิลถัดไป", "upgrade": False}
    return None


async def check_refresh_allowed(db: AsyncSession, user) -> dict | None:
    """Check if user can refresh context this billing period."""
    limits = get_limits(user)
    if limits["refresh_limit_monthly"] == 0:
        return {"error": "Context Refresh ใช้ได้ใน Starter — อัปเกรดเพื่อรีเฟรช Context Pack ของคุณ", "upgrade": True}
    period_start = _month_start_for_user(user)
    used = await get_monthly_refresh_count(db, user.id, period_start)
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
    period_start = _month_start_for_user(user)

    files_count = await get_file_count(db, user.id)
    storage_mb = await get_storage_used_mb(db, user.id)
    packs_count = await get_pack_count(db, user.id)
    summaries_used = await get_monthly_summary_count(db, user.id, period_start)
    exports_used = await get_monthly_export_count(db, user.id, period_start)
    refreshes_used = await get_monthly_refresh_count(db, user.id, period_start)

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


# ═══════════════════════════════════════════
# 5. LOCK / UNLOCK DATA — downgrade / upgrade
# ═══════════════════════════════════════════

async def lock_excess_data(db: AsyncSession, user_id: str, plan: str = "free") -> dict:
    """Lock packs and files that exceed the given plan's limits.
    
    Called when user downgrades. Most-recently-updated items stay unlocked.
    Data is NEVER deleted — only access is restricted.
    """
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    from .database import File, ContextPack

    # Lock excess packs (keep most recently updated unlocked)
    packs_result = await db.execute(
        select(ContextPack).where(ContextPack.user_id == user_id)
        .order_by(ContextPack.updated_at.desc())
    )
    packs = packs_result.scalars().all()
    pack_limit = limits["context_pack_limit"]
    locked_packs = 0

    for i, pack in enumerate(packs):
        if i < pack_limit:
            pack.is_locked = False
            pack.locked_reason = None
        else:
            pack.is_locked = True
            pack.locked_reason = "exceeds_free_plan_limit"
            locked_packs += 1
        db.add(pack)

    # Lock excess files (keep most recently uploaded unlocked)
    files_result = await db.execute(
        select(File).where(File.user_id == user_id)
        .order_by(File.uploaded_at.desc())
    )
    files = files_result.scalars().all()
    file_limit = limits["file_limit"]
    locked_files = 0

    for i, file in enumerate(files):
        if i < file_limit:
            file.is_locked = False
            file.locked_reason = None
        else:
            file.is_locked = True
            file.locked_reason = "exceeds_free_plan_limit"
            locked_files += 1
        db.add(file)

    return {"locked_packs": locked_packs, "locked_files": locked_files}


async def unlock_data_for_plan(db: AsyncSession, user_id: str, plan: str = "starter") -> dict:
    """Unlock items that fit within the given plan's limits.
    
    Called when user upgrades. Items beyond the new plan's limits stay locked.
    """
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["starter"])
    from .database import File, ContextPack

    # Count currently unlocked packs
    unlocked_pack_result = await db.execute(
        select(func.count(ContextPack.id)).where(
            ContextPack.user_id == user_id,
            ContextPack.is_locked == False,  # noqa: E712
        )
    )
    current_unlocked_packs = unlocked_pack_result.scalar() or 0

    # Unlock locked packs up to limit
    locked_packs_result = await db.execute(
        select(ContextPack).where(
            ContextPack.user_id == user_id,
            ContextPack.is_locked == True,  # noqa: E712
        ).order_by(ContextPack.updated_at.desc())
    )
    locked_packs = locked_packs_result.scalars().all()
    unlocked_packs = 0
    for pack in locked_packs:
        if current_unlocked_packs + unlocked_packs < limits["context_pack_limit"]:
            pack.is_locked = False
            pack.locked_reason = None
            db.add(pack)
            unlocked_packs += 1

    # Count currently unlocked files
    unlocked_file_result = await db.execute(
        select(func.count(File.id)).where(
            File.user_id == user_id,
            File.is_locked == False,  # noqa: E712
        )
    )
    current_unlocked_files = unlocked_file_result.scalar() or 0

    # Unlock locked files up to limit
    locked_files_result = await db.execute(
        select(File).where(
            File.user_id == user_id,
            File.is_locked == True,  # noqa: E712
        ).order_by(File.uploaded_at.desc())
    )
    locked_files = locked_files_result.scalars().all()
    unlocked_files = 0
    for file in locked_files:
        if current_unlocked_files + unlocked_files < limits["file_limit"]:
            file.is_locked = False
            file.locked_reason = None
            db.add(file)
            unlocked_files += 1

    return {"unlocked_packs": unlocked_packs, "unlocked_files": unlocked_files}


# ═══════════════════════════════════════════
# 6. AUDIT LOG — track important events
# ═══════════════════════════════════════════

async def log_audit(
    db: AsyncSession,
    user_id: str,
    event_type: str,
    old_value: str = "",
    new_value: str = "",
    triggered_by: str = "system",
):
    """Record an audit event (plan_changed, file_locked, etc.)."""
    from .database import AuditLog
    entry = AuditLog(
        user_id=user_id,
        event_type=event_type,
        old_value=old_value,
        new_value=new_value,
        triggered_by=triggered_by,
    )
    db.add(entry)
    # Don't commit — caller should commit as part of their transaction
