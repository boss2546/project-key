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
from .auth import hash_password

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

    # By effective plan + active count (compute เพราะ effective plan ไม่ใช่แค่ user.plan)
    all_users = (await db.execute(select(User))).scalars().all()
    by_plan = {"free": 0, "starter": 0, "admin": 0}
    active_count = 0
    for u in all_users:
        if u.is_active:
            active_count += 1
        eff = _effective_plan(u)
        if eff in by_plan:
            by_plan[eff] += 1

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

    # Build response (file_count ดึงเร็ว, storage_mb เว้นไว้ — ใน detail จะมี)
    result_list = []
    for u in users:
        f_count = (await db.execute(
            select(func.count(File.id)).where(File.user_id == u.id)
        )).scalar() or 0
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
            "file_count": f_count,
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

    file_count = await get_file_count(db, user.id)
    storage_mb = await get_storage_used_mb(db, user.id)
    pack_count = await get_pack_count(db, user.id)
    summaries = await get_monthly_summary_count(db, user.id, period_start)
    exports = await get_monthly_export_count(db, user.id, period_start)
    refreshes = await get_monthly_refresh_count(db, user.id, period_start)

    # Stripe active = มี subscription_id + status ที่ Stripe ยัง charge ได้
    # canceled (period ยังไม่หมด) = ยัง active เพราะยังไม่หมดสิทธิ์
    stripe_active = bool(
        user.stripe_subscription_id
        and user.subscription_status in ("starter_active", "starter_past_due")
    )
    can_admin_downgrade = not stripe_active
    block_reason = "STRIPE_ACTIVE_SUBSCRIPTION" if stripe_active else None

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

    # Stripe collision guard — ห้าม downgrade user ที่มี active subscription
    stripe_active = bool(
        target.stripe_subscription_id
        and target.subscription_status in ("starter_active", "starter_past_due")
    )
    target_eff = _effective_plan(target)
    is_downgrade_to_free = (
        target_eff in ("starter", "admin")  # demote starter หรือ admin
        and new_plan == "free"
    )
    if stripe_active and is_downgrade_to_free:
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "STRIPE_ACTIVE_SUBSCRIPTION",
                "message": (
                    "ผู้ใช้นี้มี Stripe subscription กำลังใช้งาน — "
                    "ให้ผู้ใช้ไปกดยกเลิกที่ Stripe Customer Portal ของตัวเองก่อน"
                ),
                "hint": "After cancellation, Stripe webhook will downgrade this user to free automatically.",
            }},
        )

    old_plan_effective = target_eff

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

    # Google-only user guard — user ที่สมัครผ่าน Google เท่านั้น (ไม่มี password ในระบบ)
    if not target.password_hash and target.google_sub:
        raise HTTPException(
            status_code=409,
            detail={"error": {
                "code": "GOOGLE_ONLY_USER",
                "message": (
                    "ผู้ใช้นี้สมัครด้วย Google เท่านั้น — ไม่มีรหัสผ่านในระบบ "
                    "ให้ผู้ใช้ login ผ่านปุ่ม Sign in with Google"
                ),
            }},
        )

    target.password_hash = hash_password(new_password)
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
        except Exception:
            pass

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
