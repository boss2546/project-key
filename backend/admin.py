"""Admin module for Personal Data Bank (PDB) — v8.2.0.

จัดการ user, plan, password, audit log สำหรับเจ้าของระบบ + ทีม.
ทุกฟังก์ชันใน module นี้คาดหวังว่า caller (route handler) ผ่าน require_admin
มาแล้ว — ไม่เช็ค admin role ซ้ำใน function level.

Architecture:
- get_admin_stats() — dashboard counts
- list_users() / get_user_detail() — user discovery
- change_user_plan() — plan mutation พร้อม Stripe-aware downgrade guard
- reset_user_password() — admin set new password (return ครั้งเดียว, no email)
- set_user_active() / set_user_admin() — toggle flags พร้อม self-guards
- list_audit_logs() — audit trail viewer

ทุก mutation function:
  1. Validate input
  2. Check business rules (self-guards / Stripe collision / etc.)
  3. Apply changes ใน DB
  4. log_audit() event
  5. db.commit()
  6. Return result พร้อม audit_log_id
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from .database import (
    User, File, ContextPack, AuditLog, LineUser,
)
from .plan_limits import (
    _effective_plan, get_limits, lock_excess_data, unlock_data_for_plan,
    log_audit, _month_start_for_user,
    get_file_count, get_storage_used_mb, get_pack_count,
    get_monthly_summary_count, get_monthly_export_count, get_monthly_refresh_count,
)
from .auth import ahash_password

logger = logging.getLogger(__name__)


VALID_PLANS = {"free", "starter", "admin"}


# ═══════════════════════════════════════════
# 1. Stats / Dashboard
# ═══════════════════════════════════════════

async def get_admin_stats(db: AsyncSession) -> dict:
    """Aggregate dashboard counts สำหรับหน้า /admin Dashboard tab.

    Performance note: storage scan ใช้ os.path.getsize ทุกไฟล์ — slow ถ้า users >1000.
    ปัจจุบัน <50 users → acceptable. Defer caching ไป v8.3+ ถ้าต้องการ
    """
    # Total users
    total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0

    # v10.0.0 -- compute plan + active counts without loading every user row.
    # Was: select(User) -> N users in memory. Now: targeted aggregates.
    active_count = (await db.execute(
        select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
    )).scalar() or 0

    # _effective_plan() respects is_admin DB flag + ADMIN_EMAILS env override,
    # both unrelated to subscription_status. So we still need a small scan to
    # honor the ADMIN_EMAILS legacy fallback -- but only stream the columns we use.
    admin_rows = (await db.execute(
        select(User.id, User.email, User.is_admin, User.subscription_status, User.current_period_end)
    )).all()
    by_plan = {"free": 0, "starter": 0, "admin": 0}
    for u in admin_rows:
        # Build a minimal duck-typed object for _effective_plan
        class _U:
            pass
        ux = _U()
        ux.is_admin = u.is_admin
        ux.email = u.email
        ux.subscription_status = u.subscription_status
        ux.current_period_end = u.current_period_end
        eff = _effective_plan(ux)
        if eff in by_plan:
            by_plan[eff] += 1
    all_users = admin_rows  # kept for the subscription block below

    # Signups (UTC) — today / this week (Mon start) / this month
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=now.weekday())
    month_start = today_start.replace(day=1)

    signups_today = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= today_start)
    )).scalar() or 0
    signups_week = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= week_start)
    )).scalar() or 0
    signups_month = (await db.execute(
        select(func.count(User.id)).where(User.created_at >= month_start)
    )).scalar() or 0

    # Files + storage
    total_files = (await db.execute(select(func.count(File.id)))).scalar() or 0
    storage_total_mb = 0.0
    file_paths = (await db.execute(select(File.raw_path))).fetchall()
    for (path,) in file_paths:
        try:
            if path and os.path.exists(path):
                storage_total_mb += os.path.getsize(path) / (1024 * 1024)
        except OSError:
            pass

    # Subscription breakdown
    sub_active = sum(1 for u in all_users if u.subscription_status == "starter_active")
    sub_past_due = sum(1 for u in all_users if u.subscription_status == "starter_past_due")
    sub_canceled = sum(1 for u in all_users if u.subscription_status == "starter_canceled")

    # LINE bot
    from .config import is_line_configured
    line_stats = {
        "feature_available": is_line_configured(),
        "linked_users": 0,
        "push_quota_used": 0,
        "push_quota_limit": 200,
        "push_quota_percent": 0,
    }
    if is_line_configured():
        from . import line_quota
        linked = (await db.execute(
            select(func.count(LineUser.id)).where(LineUser.line_user_id.isnot(None))
        )).scalar() or 0
        try:
            usage = line_quota.get_current_usage()
            line_stats = {
                "feature_available": True,
                "linked_users": linked,
                "push_quota_used": usage.get("pushes_used", 0),
                "push_quota_limit": usage.get("limit", 200),
                "push_quota_percent": usage.get("percent", 0),
            }
        except Exception as e:
            logger.warning(f"line_quota.get_current_usage failed: {e}")
            line_stats["linked_users"] = linked

    # System
    from .config import APP_VERSION, DATA_DIR
    db_size_mb = 0.0
    db_path = os.path.join(DATA_DIR, "projectkey.db")
    try:
        if os.path.exists(db_path):
            db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)
    except OSError:
        pass

    return {
        "users": {
            "total": total_users,
            "by_plan": by_plan,
            "active": active_count,
            "inactive": total_users - active_count,
            "signups_today": signups_today,
            "signups_this_week": signups_week,
            "signups_this_month": signups_month,
        },
        "files": {
            "total": total_files,
            "total_storage_mb": round(storage_total_mb, 2),
        },
        "subscriptions": {
            "starter_active": sub_active,
            "starter_past_due": sub_past_due,
            "starter_canceled": sub_canceled,
        },
        "line": line_stats,
        "system": {
            "app_version": APP_VERSION,
            "db_size_mb": db_size_mb,
            "checked_at": now.isoformat() + "Z",
        },
    }


# ═══════════════════════════════════════════
# 2. User List + Detail
# ═══════════════════════════════════════════

async def list_users(
    db: AsyncSession,
    q: Optional[str] = None,
    plan_filter: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Paginated user list with optional search + filter.

    Args:
        q: Email substring (case-insensitive).
        plan_filter: "free" / "starter" / "admin" / "inactive" / None.
        page: 1-based page number.
        page_size: 1-100 items per page.

    Note: plan_filter "free/starter/admin" ใช้ _effective_plan() post-process
    (ไม่ filter ใน SQL) เพราะ effective plan ขึ้นกับหลาย field. Total count
    ใน response อาจ overcount — frontend ตรวจ result list length ได้
    """
    if page < 1:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_PAGE", "message": "page ต้อง >= 1"}},
        )
    if page_size < 1 or page_size > 100:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_PAGE", "message": "page_size ต้อง 1-100"}},
        )

    base_query = select(User)
    if q:
        # ilike → case-insensitive substring match
        base_query = base_query.where(User.email.ilike(f"%{q}%"))

    # SQL-level filter (เฉพาะ inactive — ที่ filter ได้ใน DB ตรงๆ)
    if plan_filter == "inactive":
        base_query = base_query.where(User.is_active == False)  # noqa: E712

    # Count total (before plan post-filter)
    total_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(total_query)).scalar() or 0

    # Paginate + order
    offset = (page - 1) * page_size
    paged_query = base_query.order_by(desc(User.created_at)).offset(offset).limit(page_size)
    users = (await db.execute(paged_query)).scalars().all()

    # Post-filter by effective plan (ถ้า filter เป็น free/starter/admin)
    if plan_filter in {"free", "starter", "admin"}:
        users = [u for u in users if _effective_plan(u) == plan_filter]

    # v10.0.0: fixed N+1 -- was 1 file-count query per user; now single GROUP BY.
    user_ids = [u.id for u in users]
    file_counts: dict[str, int] = {}
    if user_ids:
        rows = await db.execute(
            select(File.user_id, func.count(File.id))
            .where(File.user_id.in_(user_ids))
            .group_by(File.user_id)
        )
        for uid, cnt in rows.all():
            file_counts[uid] = cnt

    result_list = []
    for u in users:
        result_list.append({
            "id": u.id,
            "email": u.email,
            "name": u.name,
            "is_admin": bool(u.is_admin),
            "is_active": bool(u.is_active),
            "plan": u.plan or "free",
            "subscription_status": u.subscription_status or "free",
            "effective_plan": _effective_plan(u),
            "manual_plan_override": bool(getattr(u, "manual_plan_override", False)),
            "stripe_customer_id": u.stripe_customer_id,
            "stripe_subscription_id": u.stripe_subscription_id,
            "current_period_end": u.current_period_end.isoformat() + "Z" if u.current_period_end else None,
            "created_at": u.created_at.isoformat() + "Z" if u.created_at else None,
            "file_count": file_counts.get(u.id, 0),
        })

    return {
        "users": result_list,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
    }


async def get_user_detail(db: AsyncSession, user_id: str) -> dict:
    """User + usage + Stripe + downgrade-block info สำหรับหน้า user detail."""
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}},
        )

    period_start = _month_start_for_user(user)
    limits = get_limits(user)

    # v10.0.0: gather 6 independent COUNT queries in parallel (latency: sum -> max)
    import asyncio as _asyncio
    (file_count, storage_mb, pack_count,
     summaries, exports, refreshes) = await _asyncio.gather(
        get_file_count(db, user.id),
        get_storage_used_mb(db, user.id),
        get_pack_count(db, user.id),
        get_monthly_summary_count(db, user.id, period_start),
        get_monthly_export_count(db, user.id, period_start),
        get_monthly_refresh_count(db, user.id, period_start),
    )

    # v9.6.0 — Stripe ถูกลบ; admin downgrade ไม่ถูก block แล้ว
    stripe_active = False
    can_admin_downgrade = True
    block_reason = None

    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "is_admin": bool(user.is_admin),
            "is_active": bool(user.is_active),
            "plan": user.plan or "free",
            "subscription_status": user.subscription_status or "free",
            "effective_plan": _effective_plan(user),
            "manual_plan_override": bool(getattr(user, "manual_plan_override", False)),
            "stripe_customer_id": user.stripe_customer_id,
            "stripe_subscription_id": user.stripe_subscription_id,
            "current_period_start": user.current_period_start.isoformat() + "Z" if user.current_period_start else None,
            "current_period_end": user.current_period_end.isoformat() + "Z" if user.current_period_end else None,
            "cancel_at_period_end": bool(user.cancel_at_period_end),
            "created_at": user.created_at.isoformat() + "Z" if user.created_at else None,
            "updated_at": user.updated_at.isoformat() + "Z" if user.updated_at else None,
            "google_sub": user.google_sub,
            "has_password": bool(user.password_hash),
            "storage_mode": user.storage_mode or "managed",
        },
        "usage": {
            "context_packs": {"used": pack_count, "limit": limits["context_pack_limit"]},
            "files": {"used": file_count, "limit": limits["file_limit"]},
            "storage_mb": {"used": storage_mb, "limit": limits["storage_limit_mb"]},
            "ai_summaries": {"used": summaries, "limit": limits["ai_summary_limit_monthly"]},
            "exports": {"used": exports, "limit": limits["export_limit_monthly"]},
            "refreshes": {"used": refreshes, "limit": limits["refresh_limit_monthly"]},
        },
        "stripe_active": stripe_active,
        "can_admin_downgrade": can_admin_downgrade,
        "downgrade_block_reason": block_reason,
    }


# ═══════════════════════════════════════════
# 3. Mutations
# ═══════════════════════════════════════════

async def _last_audit_id(db: AsyncSession, user_id: str, event_type: str) -> Optional[int]:
    """Helper — ดึง id ของ audit log ล่าสุดสำหรับ user+event (เพื่อ return ใน response)."""
    row = (await db.execute(
        select(AuditLog)
        .where(AuditLog.user_id == user_id, AuditLog.event_type == event_type)
        .order_by(desc(AuditLog.created_at))
        .limit(1)
    )).scalar_one_or_none()
    return row.id if row else None


async def change_user_plan(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    new_plan: str,
    reason: str,
) -> dict:
    """Change plan with Stripe-aware downgrade guard + self-demote guard + audit log.

    Decision matrix:
      - new_plan = "admin"   → set is_admin=True, ไม่แตะ user.plan (admin = role over plan)
      - new_plan = "starter" → set plan="starter", subscription_status="starter_active",
                                manual_plan_override=True (กัน Stripe webhook ล้าง)
      - new_plan = "free"    → set plan="free", subscription_status="free",
                                manual_plan_override=False (กลับไปใช้ Stripe sync)
                                + lock_excess_data ถ้ามีไฟล์/pack เกิน Free quota
    """
    if new_plan not in VALID_PLANS:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_PLAN", "message": f"plan ต้องเป็น {sorted(VALID_PLANS)}"}},
        )

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}},
        )

    # Self-demote guard — admin เปลี่ยน plan ของตัวเองออกจาก admin = lock-out risk
    if target.id == admin_user.id and new_plan != "admin":
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "CANNOT_DEMOTE_SELF",
                "message": "เปลี่ยน plan ของตัวเองออกจาก admin ไม่ได้ — ให้แอดมินอื่นเป็นคนทำ",
            }},
        )

    # v9.6.0 — Stripe collision guard removed (billing system ถูกลบ).
    # Admin downgrade ทำได้อิสระ; ไม่มี active Stripe subscription ให้กังวลแล้ว.
    old_plan_effective = _effective_plan(target)

    # Apply changes ตาม decision matrix
    if new_plan == "admin":
        target.is_admin = True
        # Admin = role over plan — คง user.plan เดิม (free/starter) ไว้
        # ถ้า user เคยมี Stripe sub อยู่ ก็ปล่อยให้ Stripe จัดการต่อ
        # manual_plan_override คงเดิม (ถ้าเป็น False = Stripe sync ปกติ)
    elif new_plan == "starter":
        target.is_admin = False
        target.plan = "starter"
        target.subscription_status = "starter_active"
        target.manual_plan_override = True  # กัน Stripe webhook ล้าง (admin manual upgrade)
    else:  # free
        target.is_admin = False
        target.plan = "free"
        target.subscription_status = "free"
        target.manual_plan_override = False  # กลับไปใช้ Stripe sync ปกติ

    # Lock/unlock data ตาม plan ใหม่
    unlocked = {"unlocked_packs": 0, "unlocked_files": 0}
    locked = {"locked_packs": 0, "locked_files": 0}
    if new_plan in ("starter", "admin"):
        # Upgrade — unlock items ที่เคยถูก lock ตอน downgrade
        unlocked = await unlock_data_for_plan(
            db, target.id, "starter" if new_plan == "starter" else "admin"
        )
    elif new_plan == "free" and old_plan_effective != "free":
        # Downgrade — lock items ที่เกิน Free quota
        locked = await lock_excess_data(db, target.id, "free")

    target.updated_at = datetime.utcnow()
    db.add(target)

    # Audit log
    await log_audit(
        db, target.id, "admin_changed_plan",
        old_value=old_plan_effective,
        new_value=f"{new_plan} (reason: {reason})",
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    audit_id = await _last_audit_id(db, target.id, "admin_changed_plan")

    logger.info(
        f"Admin {admin_user.email} changed plan of {target.email}: "
        f"{old_plan_effective} → {new_plan} (reason: {reason[:80]})"
    )

    return {
        "status": "ok",
        "user_id": target.id,
        "old_plan": old_plan_effective,
        "new_plan": new_plan,
        "manual_override": bool(target.manual_plan_override),
        "unlocked_packs": unlocked["unlocked_packs"],
        "unlocked_files": unlocked["unlocked_files"],
        "locked_packs": locked["locked_packs"],
        "locked_files": locked["locked_files"],
        "audit_log_id": audit_id,
    }


async def reset_user_password(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    new_password: str,
    reason: str,
) -> dict:
    """Set new password for user — return ครั้งเดียว, ไม่ส่ง email, ไม่ store raw.

    Trade-off:
      - ⚠️ admin จะเห็น password ใหม่ของ user — ต้องส่งให้ user อย่างปลอดภัย
        (LINE / โทร / face-to-face) ห้าม screenshot / save ใน chat
      - ✅ ไม่ต้องการ email working ของ user (ต่างจาก reset link flow)
      - ⚠️ JWT เดิมของ user ยังใช้ได้จนหมดอายุ (24 ชม.) — acceptable trade-off
        ถ้าต้องการ kill session ทันที ต้องเพิ่ม password_changed_at + JWT iat check
        (defer ไป v8.3+)
    """
    if len(new_password) < 6:
        raise HTTPException(
            status_code=400,
            detail={"error": {
                "code": "PASSWORD_TOO_SHORT",
                "message": "รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร",
            }},
        )

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}},
        )

    # v9.5.0 — Google login removed. Admin reset password กับ Google-only user
    # (password_hash IS NULL) ได้ตามปกติ — หลัง reset แล้ว user จะ login ด้วย
    # email/password ปกติ ไม่ต้องผ่าน Google.
    target.password_hash = await ahash_password(new_password)
    # v10.0.30-hotfix — plaintext_password write REMOVED (PDPA risk · column will DROP in Phase 3)
    target.updated_at = datetime.utcnow()
    db.add(target)

    # Audit — old_value เก็บ reason, new_value เก็บ user_email
    # (raw password ไม่ log — เห็นได้แค่ใน response ครั้งเดียว)
    await log_audit(
        db, target.id, "admin_reset_password",
        old_value=reason,
        new_value=target.email or "",
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    audit_id = await _last_audit_id(db, target.id, "admin_reset_password")

    logger.info(
        f"Admin {admin_user.email} reset password for {target.email} "
        f"(reason: {reason[:80]}) — password not logged"
    )

    return {
        "status": "ok",
        "user_id": target.id,
        "user_email": target.email,
        "new_password_shown_once": new_password,  # show ครั้งเดียวใน response — ไม่ persist
        "warning": "รหัสนี้แสดงครั้งเดียว — ส่งให้ user ทันที. ไม่บันทึกลงระบบ.",
        "audit_log_id": audit_id,
    }


async def set_user_active(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    is_active: bool,
    reason: str,
) -> dict:
    """Toggle is_active flag. ห้าม deactivate ตัวเอง (lock-out guard)."""
    if target_user_id == admin_user.id and not is_active:
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "CANNOT_DEACTIVATE_SELF",
                "message": "ห้าม deactivate ตัวเอง",
            }},
        )

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}},
        )

    target.is_active = bool(is_active)
    target.updated_at = datetime.utcnow()
    db.add(target)

    event_type = "admin_reactivated_user" if is_active else "admin_deactivated_user"
    await log_audit(
        db, target.id, event_type,
        old_value=reason,
        new_value=target.email or "",
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    audit_id = await _last_audit_id(db, target.id, event_type)

    logger.info(
        f"Admin {admin_user.email} {'reactivated' if is_active else 'deactivated'} "
        f"{target.email} (reason: {reason[:80]})"
    )

    return {
        "status": "ok",
        "user_id": target.id,
        "is_active": bool(target.is_active),
        "audit_log_id": audit_id,
    }


async def set_user_admin(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    is_admin: bool,
    reason: str,
) -> dict:
    """Toggle is_admin flag. Self-guard + last-admin guard."""
    # Self-demote guard
    if target_user_id == admin_user.id and not is_admin:
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "CANNOT_DEMOTE_SELF",
                "message": "ห้าม demote ตัวเอง — ให้แอดมินอื่นทำ",
            }},
        )

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}},
        )

    # Last-admin guard — ก่อน demote ตรวจว่ายังมี admin อื่นที่ active เหลือหรือไม่
    # (ทั้ง DB-driven is_admin + ADMIN_EMAILS env fallback)
    if not is_admin:
        # นับ DB admin คนอื่น (active + ไม่ใช่ตัว target)
        other_db_admins = (await db.execute(
            select(func.count(User.id)).where(
                User.is_admin == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
                User.id != target_user_id,
            )
        )).scalar() or 0

        # นับ env admin ที่มี user row + active + ไม่ใช่ตัว target
        # v10.0.0: log on unexpected failure -- this affects last-admin guard.
        env_admins_active = 0
        try:
            from .config import ADMIN_EMAILS
            for env_email in ADMIN_EMAILS:
                u = (await db.execute(
                    select(User).where(
                        User.email == env_email.lower(),
                        User.is_active == True,  # noqa: E712
                    )
                )).scalar_one_or_none()
                if u and u.id != target_user_id:
                    env_admins_active += 1
        except Exception as e:
            logger.warning("ADMIN_EMAILS count failed in last-admin guard: %s", e)

        if other_db_admins + env_admins_active == 0:
            raise HTTPException(
                status_code=409,
                detail={"error": {
                    "code": "LAST_ADMIN_GUARD",
                    "message": (
                        "ไม่สามารถ demote — จะไม่มี admin ที่ active เหลือเลย "
                        "ตั้งคนใหม่ก่อน"
                    ),
                }},
            )

    target.is_admin = bool(is_admin)
    target.updated_at = datetime.utcnow()
    db.add(target)

    event_type = "admin_promoted" if is_admin else "admin_demoted"
    await log_audit(
        db, target.id, event_type,
        old_value=reason,
        new_value=target.email or "",
        triggered_by=admin_user.email or "admin",
    )
    await db.commit()

    audit_id = await _last_audit_id(db, target.id, event_type)

    logger.info(
        f"Admin {admin_user.email} {'promoted' if is_admin else 'demoted'} "
        f"{target.email} (reason: {reason[:80]})"
    )

    return {
        "status": "ok",
        "user_id": target.id,
        "is_admin": bool(target.is_admin),
        "audit_log_id": audit_id,
    }


# ═══════════════════════════════════════════
# 3.4 View user password (v10.0.x · TEST PHASE ONLY)
# ═══════════════════════════════════════════

# v10.0.30-hotfix — get_user_password() REMOVED (feature deleted, PDPA compliance)
# Caller endpoint /api/admin/users/{user_id}/view-password also removed.
# Column users.plaintext_password to be DROPped 24h after deploy.


# ═══════════════════════════════════════════
# 3.5 Delete user (v10.0.x)
# ═══════════════════════════════════════════

async def delete_user(
    db: AsyncSession,
    admin_user: User,
    target_user_id: str,
    reason: str,
) -> dict:
    """Hard-delete user + cascade ทุก data ของเขา (irreversible).

    Guards:
      - CANNOT_DELETE_SELF — admin ลบตัวเองไม่ได้
      - LAST_ADMIN_GUARD — ถ้า target เป็น admin คนสุดท้าย active → block

    Cascade deletes (อ้างจาก decisions.md + database.py FK map):
      - files (+ raw_path/md_path on disk · cascade FileInsight/FileSummary/FileClusterMap)
      - clusters · graph_nodes/edges · suggested_relations · note_objects
      - context_packs · context_memories · canvas_objects · chat_queries (+ injection_logs cascade)
      - personality_history · usage_logs · mcp_tokens · mcp_usage_logs
      - drive_connections (encrypted refresh_token) · user_profiles · line_users
    Audit logs: **KEEP** (historical trail · references deleted user is OK · `user_id` not FK to users)
    """
    from sqlalchemy import delete as sql_delete
    from .database import (
        Cluster, FileInsight, FileSummary, FileClusterMap,
        ChatQuery, ContextInjectionLog, NoteObject,
        GraphNode, GraphEdge, SuggestedRelation, GraphLens, CanvasObject,
        UserProfile, PersonalityHistory, UsageLog, MCPToken, MCPUsageLog,
        DriveConnection,
    )

    # ─── Guard 1: cannot delete self ───
    if target_user_id == admin_user.id:
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "CANNOT_DELETE_SELF",
                "message": "ห้ามลบบัญชีตัวเอง — ให้แอดมินอื่นทำ",
            }},
        )

    target = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one_or_none()
    if not target:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "USER_NOT_FOUND", "message": "User not found"}},
        )

    # ─── Guard 2: last-admin guard (เหมือน set_user_admin) ───
    if target.is_admin:
        other_db_admins = (await db.execute(
            select(func.count(User.id)).where(
                User.is_admin == True,  # noqa: E712
                User.is_active == True,  # noqa: E712
                User.id != target_user_id,
            )
        )).scalar() or 0
        env_admins_active = 0
        try:
            from .config import ADMIN_EMAILS
            for env_email in ADMIN_EMAILS:
                u = (await db.execute(
                    select(User).where(
                        User.email == env_email.lower(),
                        User.is_active == True,  # noqa: E712
                    )
                )).scalar_one_or_none()
                if u and u.id != target_user_id:
                    env_admins_active += 1
        except Exception as e:
            logger.warning("ADMIN_EMAILS count failed in delete_user guard: %s", e)
        if other_db_admins + env_admins_active == 0:
            raise HTTPException(
                status_code=409,
                detail={"error": {
                    "code": "LAST_ADMIN_GUARD",
                    "message": "ไม่สามารถลบ — จะไม่มี admin ที่ active เหลือเลย ตั้งคนใหม่ก่อน",
                }},
            )

    target_email = target.email or "(no-email)"
    stats = {
        "files_deleted": 0,
        "files_disk_removed": 0,
        "summaries_disk_removed": 0,
        "tables_purged": [],
    }

    # ─── Step 1: Disk cleanup (files + summaries .md ก่อน DB cascade) ───
    files_res = await db.execute(
        select(File.id, File.raw_path).where(File.user_id == target_user_id)
    )
    files_to_remove = list(files_res.all())
    stats["files_deleted"] = len(files_to_remove)
    for fid, raw_path in files_to_remove:
        if raw_path and os.path.exists(raw_path):
            try:
                os.remove(raw_path)
                stats["files_disk_removed"] += 1
            except OSError as e:
                logger.warning("delete_user: remove raw_path %s failed: %s", raw_path, e)

    summary_res = await db.execute(
        select(FileSummary.md_path).where(
            FileSummary.file_id.in_(select(File.id).where(File.user_id == target_user_id))
        )
    )
    for (md_path,) in summary_res.all():
        if md_path and os.path.exists(md_path):
            try:
                os.remove(md_path)
                stats["summaries_disk_removed"] += 1
            except OSError as e:
                logger.warning("delete_user: remove md_path %s failed: %s", md_path, e)

    # ─── Step 2: Bulk SQL DELETE (order matters · FK respect) ───
    # Graph layer first (ไม่มี FK ondelete CASCADE)
    purge_order = [
        # (table_class, scope_filter)
        (SuggestedRelation, SuggestedRelation.user_id == target_user_id),
        (GraphEdge,         GraphEdge.user_id == target_user_id),
        (GraphNode,         GraphNode.user_id == target_user_id),
        (GraphLens,         GraphLens.user_id == target_user_id),
        (NoteObject,        NoteObject.user_id == target_user_id),
        (CanvasObject,      CanvasObject.user_id == target_user_id),
        (ContextPack,       ContextPack.user_id == target_user_id),
        (ChatQuery,         ChatQuery.user_id == target_user_id),  # cascade ContextInjectionLog
        (PersonalityHistory, PersonalityHistory.user_id == target_user_id),
        (UsageLog,          UsageLog.user_id == target_user_id),
        (MCPUsageLog,       MCPUsageLog.user_id == target_user_id),
        (MCPToken,          MCPToken.user_id == target_user_id),
        (DriveConnection,   DriveConnection.user_id == target_user_id),
        (UserProfile,       UserProfile.user_id == target_user_id),
        (LineUser,          LineUser.user_id == target_user_id),
        # context_memories / line_quota_logs / รายการอื่นที่ optional
    ]
    # Optional tables (ไม่มีในทุก deployment · skip ถ้า import error)
    try:
        from .database import ContextMemory  # type: ignore
        purge_order.insert(-3, (ContextMemory, ContextMemory.user_id == target_user_id))
    except (ImportError, AttributeError):
        pass

    for cls, scope in purge_order:
        try:
            r = await db.execute(sql_delete(cls).where(scope))
            n = r.rowcount or 0
            if n:
                stats["tables_purged"].append(f"{cls.__tablename__}={n}")
        except Exception as e:
            logger.warning("delete_user: purge %s failed: %s", cls.__tablename__, e)

    # Files + cascade (FileInsight/FileSummary/FileClusterMap via ORM cascade · ใช้ SQL delete + manual children)
    # SQL-level delete won't trigger ORM cascade · ลบ children explicit ก่อน
    file_ids_subq = select(File.id).where(File.user_id == target_user_id)
    for cls in (FileInsight, FileSummary, FileClusterMap):
        try:
            r = await db.execute(sql_delete(cls).where(cls.file_id.in_(file_ids_subq)))
            n = r.rowcount or 0
            if n:
                stats["tables_purged"].append(f"{cls.__tablename__}={n}")
        except Exception as e:
            logger.warning("delete_user: child purge %s failed: %s", cls.__tablename__, e)

    # Then files themselves
    try:
        r = await db.execute(sql_delete(File).where(File.user_id == target_user_id))
        stats["tables_purged"].append(f"files={r.rowcount or 0}")
    except Exception as e:
        logger.warning("delete_user: files purge failed: %s", e)

    # Empty clusters (file_cluster_map ถูกลบไปแล้ว · cluster ที่เคย map อาจเหลือว่าง)
    try:
        r = await db.execute(sql_delete(Cluster).where(Cluster.user_id == target_user_id))
        if r.rowcount:
            stats["tables_purged"].append(f"clusters={r.rowcount}")
    except Exception as e:
        logger.warning("delete_user: clusters purge failed: %s", e)

    # ─── Step 3: Audit log (BEFORE deleting user · trigger_by ยังอยู่) ───
    await log_audit(
        db, target_user_id, "admin_deleted_user",
        old_value=reason or "(no reason given)",
        new_value=target_email,
        triggered_by=admin_user.email or "admin",
    )

    # ─── Step 4: Finally delete User row ───
    try:
        r = await db.execute(sql_delete(User).where(User.id == target_user_id))
        stats["tables_purged"].append(f"users={r.rowcount or 0}")
    except Exception as e:
        logger.error("delete_user: FINAL user delete failed: %s", e)
        await db.rollback()
        raise HTTPException(status_code=500, detail={"error": {
            "code": "USER_DELETE_FAILED",
            "message": f"ลบ user row ไม่สำเร็จ: {str(e)[:200]}",
        }})

    await db.commit()

    logger.warning(
        "Admin %s DELETED user %s (id=%s · reason: %s) · stats=%s",
        admin_user.email, target_email, target_user_id, reason[:80], stats,
    )

    return {
        "status": "ok",
        "deleted_user_id": target_user_id,
        "deleted_user_email": target_email,
        "stats": stats,
    }


# ═══════════════════════════════════════════
# 4. Audit log viewer
# ═══════════════════════════════════════════

async def list_audit_logs(
    db: AsyncSession,
    event_type: Optional[str] = None,
    user_id: Optional[str] = None,
    triggered_by: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    """List audit logs with optional filters. Most recent first.

    JOIN user_email best-effort — ถ้า user ถูกลบ → user_email = null
    """
    if limit < 1 or limit > 200:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_LIMIT", "message": "limit ต้อง 1-200"}},
        )
    if offset < 0:
        raise HTTPException(
            status_code=400,
            detail={"error": {"code": "INVALID_OFFSET", "message": "offset ต้อง >= 0"}},
        )

    base_query = select(AuditLog)
    if event_type:
        base_query = base_query.where(AuditLog.event_type == event_type)
    if user_id:
        base_query = base_query.where(AuditLog.user_id == user_id)
    if triggered_by:
        base_query = base_query.where(AuditLog.triggered_by == triggered_by)

    total_query = select(func.count()).select_from(base_query.subquery())
    total = (await db.execute(total_query)).scalar() or 0

    paged_query = base_query.order_by(desc(AuditLog.created_at)).offset(offset).limit(limit)
    rows = (await db.execute(paged_query)).scalars().all()

    # JOIN email — cache เพื่อลด query ซ้ำ
    email_cache: dict[str, Optional[str]] = {}
    result_logs = []
    for r in rows:
        if r.user_id not in email_cache:
            email = (await db.execute(
                select(User.email).where(User.id == r.user_id)
            )).scalar_one_or_none()
            email_cache[r.user_id] = email
        result_logs.append({
            "id": r.id,
            "user_id": r.user_id,
            "user_email": email_cache.get(r.user_id),
            "event_type": r.event_type,
            "old_value": r.old_value or "",
            "new_value": r.new_value or "",
            "triggered_by": r.triggered_by,
            "created_at": r.created_at.isoformat() + "Z" if r.created_at else None,
        })

    return {
        "logs": result_logs,
        "total": total,
        "limit": limit,
        "offset": offset,
    }
