"""Pack Share — v9.3.0

ระบบให้เจ้าของ Context Pack สร้างลิงก์แชร์ให้คนอื่นได้:

Flow:
  1. POST /api/context-packs/{pack_id}/share — สร้างลิงก์ (idempotent)
  2. PATCH /api/context-packs/shares/{share_id} — toggle include_files
  3. DELETE /api/context-packs/shares/{share_id} — revoke
  4. GET /api/shared/pack/{token} — recipient preview (no auth required)
  5. POST /api/shared/pack/{token}/claim — clone เข้า workspace recipient

Token = JWT signed (scope='pack_share') — verify stateless แต่มี DB row check
สำหรับ revocation. Token ไม่มี exp — ลิงก์ใช้ได้ตลอดจนกว่า revoke

Cascade safety:
- File copy on claim ใช้ atomic transaction + rollback ถ้า partial failure
- Vector index ของ cloned pack ผูกกับ recipient.id (NOT owner) — กัน cross-user leak
- JWT scope='pack_share' — payload ไม่มี 'sub' field → กัน abuse as login token
"""
from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from jose import JWTError, jwt
from jose.exceptions import ExpiredSignatureError

from .config import JWT_SECRET_KEY, JWT_ALGORITHM, APP_BASE_URL
from .database import (
    PackShare, ContextPack, File, FileSummary, User, gen_id,
)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# Token signing — JWT scope=pack_share, no exp
# ═══════════════════════════════════════════

SCOPE_PACK_SHARE = "pack_share"


class ShareTokenError(Exception):
    """Raised on token decode failure."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def sign_share_token(share_id: str) -> str:
    """Sign a share token (JWT HS256, scope=pack_share, no exp).

    No expiration — ลิงก์ใช้ได้ตลอดจนกว่า revoke. Verify ผ่าน DB row check
    (revoked_at IS NULL).
    """
    now = datetime.now(timezone.utc)
    payload = {
        "share_id": share_id,
        "scope": SCOPE_PACK_SHARE,
        "iat": now,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_share_token(token: str) -> str:
    """Decode + verify share token. Returns share_id.

    Raises ShareTokenError("INVALID_TOKEN") on any failure (signature, scope,
    missing field). v9.3.0 uses no exp — revocation via DB check at endpoint.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except (JWTError, ExpiredSignatureError):
        raise ShareTokenError("INVALID_TOKEN", "ลิงก์ไม่ถูกต้อง")

    # Scope check — defense-in-depth
    if payload.get("scope") != SCOPE_PACK_SHARE:
        raise ShareTokenError("INVALID_TOKEN", "Token scope ไม่ถูกต้อง")

    share_id = payload.get("share_id")
    if not share_id or not isinstance(share_id, str):
        raise ShareTokenError("INVALID_TOKEN", "Token ไม่มี share_id")

    return share_id


def build_share_url(token: str) -> str:
    """Build full share URL — used in API response."""
    return f"{APP_BASE_URL.rstrip('/')}/p/{token}"


def mask_email(email: str | None) -> str:
    """Mask owner email for privacy: 'tester@example.com' → 'te****@example.com'"""
    if not email:
        return "(ไม่มีอีเมล)"
    parts = email.split("@", 1)
    if len(parts) != 2:
        return email
    local, domain = parts
    if len(local) <= 2:
        return f"{local}****@{domain}"
    return f"{local[:2]}****@{domain}"


# ═══════════════════════════════════════════
# Core operations
# ═══════════════════════════════════════════

async def create_share(
    db: AsyncSession, user: User, pack_id: str, include_files: bool = False
) -> dict:
    """สร้างลิงก์ share (idempotent — ถ้ามี active share อยู่ → return เดิม).

    Pre-check:
      - pack ต้องเป็นของ user (404 ถ้าไม่ใช่)
      - pack ต้องไม่ locked (400 PACK_LOCKED)
      - quota check ที่ caller (endpoint level — ใช้ check_pack_share_create_allowed)

    Returns dict with share_id, share_url, include_files, is_new flag, stats.
    """
    # ตรวจ pack ของ user + ไม่ locked
    pack_res = await db.execute(
        select(ContextPack).where(
            ContextPack.id == pack_id,
            ContextPack.user_id == user.id,
        )
    )
    pack = pack_res.scalar_one_or_none()
    if not pack:
        raise ValueError("PACK_NOT_FOUND")
    if getattr(pack, "is_locked", False):
        raise ValueError("PACK_LOCKED")

    # Idempotent — ถ้ามี active share อยู่ → return เดิม
    existing_res = await db.execute(
        select(PackShare).where(
            PackShare.pack_id == pack_id,
            PackShare.owner_user_id == user.id,
            PackShare.revoked_at.is_(None),
        )
    )
    existing = existing_res.scalar_one_or_none()
    if existing:
        # Update include_files ถ้าต่าง
        if existing.include_files != include_files:
            existing.include_files = include_files
            await db.commit()
        return _serialize_share(existing, is_new=False)

    # Create new
    share = PackShare(
        id=gen_id(),
        pack_id=pack_id,
        owner_user_id=user.id,
        include_files=include_files,
    )
    db.add(share)
    await db.commit()
    return _serialize_share(share, is_new=True)


async def update_share_files(
    db: AsyncSession, user: User, share_id: str, include_files: bool
) -> dict:
    """Toggle include_files. ลิงก์ URL ไม่เปลี่ยน (token เก็บ share_id เดิม)."""
    share_res = await db.execute(
        select(PackShare).where(
            PackShare.id == share_id,
            PackShare.owner_user_id == user.id,
        )
    )
    share = share_res.scalar_one_or_none()
    if not share:
        # ไม่บอกว่ามีหรือไม่มี — กัน enumeration
        raise ValueError("SHARE_NOT_FOUND")

    share.include_files = include_files
    await db.commit()
    return _serialize_share(share, is_new=False)


async def revoke_share(db: AsyncSession, user: User, share_id: str) -> dict:
    """Revoke share. Idempotent (revoke ซ้ำ = no-op)."""
    share_res = await db.execute(
        select(PackShare).where(
            PackShare.id == share_id,
            PackShare.owner_user_id == user.id,
        )
    )
    share = share_res.scalar_one_or_none()
    if not share:
        raise ValueError("SHARE_NOT_FOUND")

    if share.revoked_at is None:
        share.revoked_at = datetime.utcnow()
        await db.commit()
    return {"status": "revoked", "share_id": share.id, "revoked_at": share.revoked_at.isoformat()}


async def list_shares_for_pack(
    db: AsyncSession, user: User, pack_id: str
) -> list[dict]:
    """List shares ของ pack (เฉพาะของ user). Active first."""
    res = await db.execute(
        select(PackShare).where(
            PackShare.pack_id == pack_id,
            PackShare.owner_user_id == user.id,
        ).order_by(PackShare.revoked_at.is_not(None), PackShare.created_at.desc())
    )
    shares = res.scalars().all()
    return [_serialize_share(s, is_new=False) for s in shares]


async def get_preview(db: AsyncSession, token: str) -> dict:
    """Recipient preview (no auth). Verify token + return pack content + file URLs.

    เพิ่ม view_count atomically. ถ้า include_files=true → gen signed download
    URLs ผ่าน existing /d/{token} pattern (BYOS-aware via storage_router).
    """
    share_id = verify_share_token(token)

    share_res = await db.execute(
        select(PackShare).where(PackShare.id == share_id)
    )
    share = share_res.scalar_one_or_none()
    if not share:
        raise ValueError("SHARE_NOT_FOUND")
    if share.revoked_at is not None:
        raise ValueError("SHARE_REVOKED")

    # Lookup pack
    pack_res = await db.execute(
        select(ContextPack).where(ContextPack.id == share.pack_id)
    )
    pack = pack_res.scalar_one_or_none()
    if not pack:
        raise ValueError("PACK_DELETED")

    # Lookup owner (for masked email)
    owner_res = await db.execute(
        select(User).where(User.id == share.owner_user_id)
    )
    owner = owner_res.scalar_one_or_none()
    owner_name = owner.name if owner else "(ผู้ใช้)"
    owner_email_masked = mask_email(owner.email if owner else None)

    # Atomic increment view_count
    await db.execute(
        update(PackShare)
        .where(PackShare.id == share.id)
        .values(view_count=PackShare.view_count + 1)
    )
    await db.commit()

    # Refresh share for current count
    await db.refresh(share)

    # Files (only if include_files=true)
    files_payload: list[dict] = []
    if share.include_files:
        try:
            import json as _json
            file_ids = _json.loads(pack.source_file_ids) if pack.source_file_ids else []
        except (ValueError, TypeError):
            file_ids = []

        if file_ids:
            files_res = await db.execute(
                select(File).where(
                    File.id.in_(file_ids),
                    File.user_id == share.owner_user_id,  # double-check ownership
                )
            )
            files = files_res.scalars().all()
            for f in files:
                # Skip locked files
                if getattr(f, "is_locked", False):
                    continue
                # Sign download URL — use OWNER's user_id (file ownership)
                # F1 fix: signed_urls.sign_download_token(file_id, user_id=owner)
                from .signed_urls import sign_download_token, TTL_DEFAULT_SECONDS
                try:
                    dl_token = sign_download_token(
                        file_id=f.id,
                        user_id=share.owner_user_id,
                        ttl_seconds=TTL_DEFAULT_SECONDS,  # 30 min — recipient re-fetches preview
                    )
                    download_url = f"{APP_BASE_URL.rstrip('/')}/d/{dl_token}"
                except Exception as e:
                    logger.warning(f"Failed to sign download URL for {f.id}: {e}")
                    continue

                size_bytes = 0
                try:
                    if f.raw_path and os.path.exists(f.raw_path):
                        size_bytes = os.path.getsize(f.raw_path)
                except OSError:
                    pass

                files_payload.append({
                    "file_id": f.id,
                    "filename": f.filename,
                    "filetype": f.filetype,
                    "size_bytes": size_bytes,
                    "download_url": download_url,
                })

    # Pack content
    summary_text = pack.summary_text or ""
    SUMMARY_SHORT_CHARS = 300
    summary_short = (
        summary_text[:SUMMARY_SHORT_CHARS] + "…"
        if len(summary_text) > SUMMARY_SHORT_CHARS
        else summary_text
    )

    return {
        "share_id": share.id,
        "pack": {
            "title": pack.title,
            "type": pack.type,
            "intent": getattr(pack, "intent", "") or "",
            "scope": getattr(pack, "scope", "") or "",
            "summary_short": summary_short,
            "summary_full": summary_text,
            "owner_name": owner_name,
            "owner_email_masked": owner_email_masked,
            "source_count": len(files_payload) if share.include_files else 0,
            "created_at": pack.created_at.isoformat() if pack.created_at else "",
            "updated_at": pack.updated_at.isoformat() if pack.updated_at else "",
        },
        "files": files_payload,
        "include_files": share.include_files,
        "view_count": share.view_count,
        "clone_count": share.clone_count,
    }


async def claim_to_workspace(
    db: AsyncSession, current_user: User, token: str
) -> dict:
    """Recipient claim — clone pack เข้า workspace ของ current_user.

    Cascade-safe (per Risk #1):
      - Pre-check ALL local files exist on disk ก่อน start copy
      - Atomic transaction: copy + DB write together; rollback on failure
      - Cloned pack source_file_ids = list of NEW file IDs (recipient's)
      - Vector index ใช้ current_user.id (Risk #2 guard)

    BYOS skip (per F5): owner BYOS files (storage_source != "local") = skip
    + เพิ่ม note ใน intent
    """
    share_id = verify_share_token(token)

    share_res = await db.execute(
        select(PackShare).where(PackShare.id == share_id)
    )
    share = share_res.scalar_one_or_none()
    if not share:
        raise ValueError("SHARE_NOT_FOUND")
    if share.revoked_at is not None:
        raise ValueError("SHARE_REVOKED")

    # Lookup pack
    pack_res = await db.execute(
        select(ContextPack).where(ContextPack.id == share.pack_id)
    )
    pack = pack_res.scalar_one_or_none()
    if not pack:
        raise ValueError("PACK_DELETED")

    # Lookup owner for note
    owner_res = await db.execute(
        select(User).where(User.id == share.owner_user_id)
    )
    owner = owner_res.scalar_one_or_none()
    owner_name = owner.name if owner else "ผู้ใช้"

    # Pack quota check
    from .plan_limits import check_pack_create_allowed, get_storage_used_mb, get_limits
    pack_err = await check_pack_create_allowed(db, current_user)
    if pack_err:
        raise PermissionError(f"PACK_LIMIT_REACHED: {pack_err.get('error', '')}")

    # Build source_files list (only local files) + storage pre-check
    import json as _json
    try:
        owner_file_ids = _json.loads(pack.source_file_ids) if pack.source_file_ids else []
    except (ValueError, TypeError):
        owner_file_ids = []

    skipped_byos_count = 0
    files_to_copy: list[File] = []
    if share.include_files and owner_file_ids:
        files_res = await db.execute(
            select(File).where(
                File.id.in_(owner_file_ids),
                File.user_id == share.owner_user_id,
            ).options(selectinload(File.summary))
        )
        all_owner_files = files_res.scalars().all()
        for f in all_owner_files:
            if getattr(f, "is_locked", False):
                continue
            storage = getattr(f, "storage_source", "local") or "local"
            if storage != "local":
                # F5: skip BYOS files in v9.3.0
                skipped_byos_count += 1
                continue
            # Pre-check: file exists on disk
            if not f.raw_path or not os.path.exists(f.raw_path):
                skipped_byos_count += 1  # treat as skipped
                logger.warning(f"Source file missing on disk: {f.filename} ({f.id})")
                continue
            files_to_copy.append(f)

        # Storage quota pre-check (F8)
        if files_to_copy:
            total_mb = sum(
                os.path.getsize(f.raw_path) / (1024 * 1024) for f in files_to_copy
            )
            limits = get_limits(current_user)
            current_usage = await get_storage_used_mb(db, current_user.id)
            available = limits["storage_limit_mb"] - current_usage
            if total_mb > available:
                raise PermissionError(
                    f"STORAGE_LIMIT_REACHED: ต้องการ {total_mb:.1f} MB แต่เหลือ {available:.1f} MB"
                )

    # Build clone intent with note
    clone_date = datetime.utcnow().strftime("%Y-%m-%d")
    note_th = f"\n\n(เก็บจาก {owner_name} เมื่อ {clone_date}"
    if skipped_byos_count > 0:
        note_th += f" — ไฟล์ {skipped_byos_count} อันใน BYOS ของเจ้าของไม่ได้ copy"
    note_th += ")"
    cloned_intent = (getattr(pack, "intent", "") or "") + note_th

    # ─── Atomic transaction: copy files + create File rows + create pack ───
    copied_paths: list[str] = []
    new_file_records: list[File] = []
    new_file_ids: list[str] = []

    try:
        # 1. Copy files
        from .config import UPLOAD_DIR
        recipient_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
        os.makedirs(recipient_upload_dir, exist_ok=True)

        for f in files_to_copy:
            new_file_id = gen_id()
            ext = f.filetype or "bin"
            new_filename = f.filename  # คงชื่อเดิม (recipient เห็นชื่อตรงกับเจ้าของ)
            new_path = os.path.join(recipient_upload_dir, f"{new_file_id}.{ext}")

            shutil.copy2(f.raw_path, new_path)
            copied_paths.append(new_path)

            # Create File row — minimal metadata; recipient จะ organize ใหม่ทีหลัง
            new_f = File(
                id=new_file_id,
                user_id=current_user.id,
                filename=new_filename,
                filetype=f.filetype,
                raw_path=new_path,
                processing_status="ready",  # ใช้งานได้ทันที (text มาแล้ว)
                extracted_text=f.extracted_text or "",
                file_kind="processed",
                storage_source="local",
            )
            db.add(new_f)
            new_file_records.append(new_f)
            new_file_ids.append(new_file_id)

        # 2. Create new ContextPack pointing to NEW file IDs
        from .context_packs import create_pack
        cloned_pack = await create_pack(
            db,
            user_id=current_user.id,
            pack_type=pack.type,
            title=pack.title,
            source_file_ids=new_file_ids,
            source_cluster_ids=[],  # F: cluster_ids=[] ใน clone (ไม่ link ของ owner)
            intent=cloned_intent,
            scope=getattr(pack, "scope", "") or "",
            created_via="shared_clone",
            override_summary=pack.summary_text,  # ไม่ distill ซ้ำ — ประหยัด LLM
        )

        # 3. Atomic increment clone_count
        await db.execute(
            update(PackShare)
            .where(PackShare.id == share.id)
            .values(clone_count=PackShare.clone_count + 1)
        )

        # 4. log_usage
        from .plan_limits import log_usage
        await log_usage(db, current_user.id, "pack_clone")

        await db.commit()
        return cloned_pack

    except Exception as e:
        # Rollback: delete copied files; DB rolls back automatically on exit
        await db.rollback()
        for p in copied_paths:
            try:
                os.remove(p)
            except OSError:
                pass
        logger.exception(f"Claim failed for token, rolled back: {e}")
        raise


# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════

def _serialize_share(share: PackShare, is_new: bool = False) -> dict:
    """Serialize PackShare to API dict."""
    token = sign_share_token(share.id)
    return {
        "share_id": share.id,
        "share_token": token,
        "share_url": build_share_url(token),
        "pack_id": share.pack_id,
        "include_files": share.include_files,
        "is_new": is_new,
        "view_count": share.view_count,
        "clone_count": share.clone_count,
        "revoked_at": share.revoked_at.isoformat() if share.revoked_at else None,
        "created_at": share.created_at.isoformat() if share.created_at else "",
    }
