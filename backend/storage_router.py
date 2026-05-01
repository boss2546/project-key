"""Storage routing — bridges existing services to BYOS Drive when applicable (v7.0).

Used by existing services (profile.py, organizer.py, graph_builder.py, extraction.py)
ที่ต้อง persist data ในรูป JSON / markdown / bytes โดยไม่ต้องรู้ว่า user อยู่ mode ไหน.

Design principles:
  1. **Cache (DB) = source of truth**, Drive = optional mirror projection
     → Reads ALWAYS from DB. Drive writes เป็น "best effort"
  2. **No-op for managed users** — ถ้า user.storage_mode != "byos" → return ทันที
  3. **No-op if BYOS not configured** — ถ้า env vars ว่าง → return ทันที
  4. **Drive failures NEVER raise** — log + continue. ไม่ break user's primary action
     (e.g., update_profile DB commit succeeds even if Drive write fails)
  5. **Lazy DriveClient** — สร้างเมื่อต้องใช้เท่านั้น (per-call) เพื่อกัน stale token

Why this module exists:
  - ตัด coupling — profile.py / organizer.py / graph_builder.py ไม่ต้อง import drive_*
  - Test-friendly — service code test ได้โดย mock ที่ router level
  - Managed-mode safe — ถ้า bug ใน Drive code ก็กระทบเฉพาะ BYOS users
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .config import is_byos_configured
from .database import DriveConnection, File, User
from .drive_layout import (
    CLUSTERS_JSON,
    CONTEXTS_JSON,
    GRAPH_JSON,
    META_VERSION_TXT,
    PROFILE_JSON,
    RELATIONS_JSON,
    STORAGE_MODE_BYOS,
    STORAGE_SOURCE_DRIVE_UPLOADED,
    STORAGE_SOURCE_LOCAL,
    extracted_path_for,
    raw_path_for,
    summary_path_for,
)


# Public URL templates — Drive serves files at stable URLs by file_id / folder_id.
# We construct them client-side instead of storing per-row to avoid extra Drive API calls.
DRIVE_FILE_VIEW_URL = "https://drive.google.com/file/d/{file_id}/view"
DRIVE_FOLDER_VIEW_URL = "https://drive.google.com/drive/folders/{folder_id}"


def drive_file_link(drive_file_id: str | None) -> str | None:
    """Build a public webViewLink for a Drive file ID — None if no ID."""
    if not drive_file_id:
        return None
    return DRIVE_FILE_VIEW_URL.format(file_id=drive_file_id)


def drive_folder_link(drive_folder_id: str | None) -> str | None:
    """Build a public link to a Drive folder."""
    if not drive_folder_id:
        return None
    return DRIVE_FOLDER_VIEW_URL.format(folder_id=drive_folder_id)

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Helper: ดู user ว่า byos หรือเปล่า (ลด boilerplate)
# ═══════════════════════════════════════════════════════════════
async def _get_byos_user_with_connection(
    user_id: str, db: AsyncSession
) -> Optional[tuple[User, DriveConnection]]:
    """Return (user, connection) ถ้า user เป็น byos + connected.
    Else return None — caller short-circuits as no-op.

    Returns None if any of:
      - BYOS feature ไม่ได้ configure (env vars ว่าง)
      - User ไม่มีอยู่ใน DB
      - User อยู่ใน managed mode
      - User ใน byos mode แต่ยังไม่เคย connect Drive
    """
    if not is_byos_configured():
        return None

    user_q = await db.execute(select(User).where(User.id == user_id))
    user = user_q.scalar_one_or_none()
    if not user or user.storage_mode != STORAGE_MODE_BYOS:
        return None

    conn_q = await db.execute(
        select(DriveConnection).where(DriveConnection.user_id == user_id)
    )
    conn = conn_q.scalar_one_or_none()
    if not conn:
        return None

    return user, conn


async def _build_drive_client(connection: DriveConnection):
    """Build DriveClient จาก encrypted refresh_token. Lazy import."""
    # Lazy: ถ้า managed/no-byos ไม่ต้อง import drive_oauth/drive_storage เลย
    from .drive_oauth import decrypt_refresh_token
    from .drive_storage import DriveClient

    plaintext = decrypt_refresh_token(connection.refresh_token_encrypted)
    return DriveClient(plaintext)


async def _get_personal_folder_id(client, root_id: str) -> str:
    """หา (หรือสร้าง) /Personal Data Bank/personal/ — return ID."""
    return client.ensure_folder("personal", parent_id=root_id)


async def _get_data_folder_id(client, root_id: str) -> str:
    """หา (หรือสร้าง) /Personal Data Bank/data/ — return ID."""
    return client.ensure_folder("data", parent_id=root_id)


async def _get_summaries_folder_id(client, root_id: str) -> str:
    return client.ensure_folder("summaries", parent_id=root_id)


# ═══════════════════════════════════════════════════════════════
# Profile JSON projection
# ═══════════════════════════════════════════════════════════════
async def push_profile_to_drive_if_byos(
    user_id: str,
    db: AsyncSession,
    profile_dict: dict[str, Any],
) -> bool:
    """Best-effort: write profile.json ลง Drive ถ้า user อยู่ byos mode.

    Returns:
        True  = pushed สำเร็จ
        False = no-op (managed mode / not configured / not connected) หรือ failed
    """
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair

    try:
        client = await _build_drive_client(conn)
        personal_id = await _get_personal_folder_id(client, conn.drive_root_folder_id)
        # PROFILE_JSON = "personal/profile.json" — ใช้แค่ filename เพราะระบุ parent แล้ว
        filename = PROFILE_JSON.split("/")[-1]
        client.upsert_json_file(personal_id, filename, profile_dict)
        logger.info("BYOS: pushed profile.json to Drive for user %s", user_id)
        return True
    except Exception as e:
        # Best-effort: log แต่ไม่ raise (cache เป็น primary, Drive เป็น mirror)
        logger.warning(
            "BYOS: profile.json push failed for user %s (%s) — "
            "DB still has correct data, will retry next sync",
            user_id, e,
        )
        return False


# ═══════════════════════════════════════════════════════════════
# Graph JSON projection (Knowledge Graph)
# ═══════════════════════════════════════════════════════════════
async def push_graph_to_drive_if_byos(
    user_id: str,
    db: AsyncSession,
    graph_dict: dict[str, Any],
) -> bool:
    """Best-effort: write graph.json ลง Drive."""
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair

    try:
        client = await _build_drive_client(conn)
        data_id = await _get_data_folder_id(client, conn.drive_root_folder_id)
        filename = GRAPH_JSON.split("/")[-1]
        client.upsert_json_file(data_id, filename, graph_dict)
        logger.info("BYOS: pushed graph.json to Drive for user %s", user_id)
        return True
    except Exception as e:
        logger.warning("BYOS: graph.json push failed for user %s (%s)", user_id, e)
        return False


# ═══════════════════════════════════════════════════════════════
# Clusters / Relations JSON
# ═══════════════════════════════════════════════════════════════
async def push_clusters_to_drive_if_byos(
    user_id: str, db: AsyncSession, clusters: list[dict[str, Any]]
) -> bool:
    """Best-effort: write data/clusters.json ลง Drive."""
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair
    try:
        client = await _build_drive_client(conn)
        data_id = await _get_data_folder_id(client, conn.drive_root_folder_id)
        filename = CLUSTERS_JSON.split("/")[-1]
        client.upsert_json_file(data_id, filename, clusters)
        logger.info("BYOS: pushed clusters.json to Drive for user %s", user_id)
        return True
    except Exception as e:
        logger.warning("BYOS: clusters.json push failed for user %s (%s)", user_id, e)
        return False


async def push_relations_to_drive_if_byos(
    user_id: str, db: AsyncSession, relations: dict[str, Any]
) -> bool:
    """Best-effort: write data/relations.json ลง Drive."""
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair
    try:
        client = await _build_drive_client(conn)
        data_id = await _get_data_folder_id(client, conn.drive_root_folder_id)
        filename = RELATIONS_JSON.split("/")[-1]
        client.upsert_json_file(data_id, filename, relations)
        return True
    except Exception as e:
        logger.warning("BYOS: relations.json push failed for user %s (%s)", user_id, e)
        return False


async def push_contexts_to_drive_if_byos(
    user_id: str, db: AsyncSession, contexts: list[dict[str, Any]]
) -> bool:
    """Best-effort: write personal/contexts.json ลง Drive."""
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair
    try:
        client = await _build_drive_client(conn)
        personal_id = await _get_personal_folder_id(client, conn.drive_root_folder_id)
        filename = CONTEXTS_JSON.split("/")[-1]
        client.upsert_json_file(personal_id, filename, contexts)
        return True
    except Exception as e:
        logger.warning("BYOS: contexts.json push failed for user %s (%s)", user_id, e)
        return False


# ═══════════════════════════════════════════════════════════════
# Summary markdown projection (per-file)
# ═══════════════════════════════════════════════════════════════
async def push_summary_to_drive_if_byos(
    user_id: str,
    db: AsyncSession,
    file_id: str,
    markdown: str,
) -> bool:
    """Best-effort: write summaries/{file_id}.md ลง Drive."""
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair

    try:
        client = await _build_drive_client(conn)
        summaries_id = await _get_summaries_folder_id(client, conn.drive_root_folder_id)
        # summary_path_for() returns "summaries/{file_id}.md" — ตัด "summaries/" prefix
        # เพราะระบุ parent_id แล้ว
        filename = summary_path_for(file_id).split("/")[-1]
        # find existing -> update; else create
        existing = client.find_file_by_name(filename, parent_id=summaries_id)
        from .drive_layout import MIME_MARKDOWN
        if existing:
            client.update_file_content(existing["id"], markdown, MIME_MARKDOWN)
        else:
            client.upload_file(summaries_id, filename, markdown, MIME_MARKDOWN)
        logger.info("BYOS: pushed summary %s.md to Drive for user %s", file_id, user_id)
        return True
    except Exception as e:
        logger.warning("BYOS: summary push failed for user %s file %s (%s)", user_id, file_id, e)
        return False


# ═══════════════════════════════════════════════════════════════
# Extracted text projection (per-file) — for full-text rebuild from Drive
# ═══════════════════════════════════════════════════════════════
async def push_extracted_text_to_drive_if_byos(
    user_id: str,
    db: AsyncSession,
    file_id: str,
    text: str,
) -> bool:
    """Best-effort: write extracted/{file_id}.txt ลง Drive."""
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair
    try:
        client = await _build_drive_client(conn)
        extracted_id = client.ensure_folder("extracted", parent_id=conn.drive_root_folder_id)
        filename = extracted_path_for(file_id).split("/")[-1]
        from .drive_layout import MIME_TEXT
        existing = client.find_file_by_name(filename, parent_id=extracted_id)
        if existing:
            client.update_file_content(existing["id"], text, MIME_TEXT)
        else:
            client.upload_file(extracted_id, filename, text, MIME_TEXT)
        return True
    except Exception as e:
        logger.warning(
            "BYOS: extracted text push failed for user %s file %s (%s)",
            user_id, file_id, e,
        )
        return False


# ═══════════════════════════════════════════════════════════════
# Raw file projection (per-file) — push original bytes to Drive raw/
# ═══════════════════════════════════════════════════════════════
async def push_raw_file_to_drive_if_byos(
    user_id: str,
    db: AsyncSession,
    file_id: str,
    filename: str,
    content: bytes,
    mime_type: str,
) -> str | None:
    """Best-effort: upload raw user file to Drive's /raw/ folder + update DB.

    On success, sets file.drive_file_id + file.storage_source='drive_uploaded' so
    future reads route through Drive. On managed/disconnected users → no-op.

    Returns:
        Drive file ID if pushed, None otherwise (managed mode / not configured /
        not connected / Drive failure)
    """
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return None
    _user, conn = pair

    try:
        client = await _build_drive_client(conn)
        raw_id = client.ensure_folder("raw", parent_id=conn.drive_root_folder_id)
        # Format: raw/{file_id}_{original_name} — matches drive_sync expectations
        drive_name = raw_path_for(file_id, filename).split("/", 1)[-1]
        drive_file_id = client.upload_file(raw_id, drive_name, content, mime_type)

        # Update File row so future reads + UI know it's on Drive
        from datetime import datetime as _dt
        file_q = await db.execute(select(File).where(File.id == file_id))
        file_row = file_q.scalar_one_or_none()
        if file_row:
            file_row.drive_file_id = drive_file_id
            file_row.drive_modified_time = _dt.utcnow()
            file_row.storage_source = STORAGE_SOURCE_DRIVE_UPLOADED
            await db.commit()
        logger.info("BYOS: pushed raw file %s to Drive for user %s", file_id, user_id)
        return drive_file_id
    except Exception as e:
        logger.warning(
            "BYOS: raw file push failed for user %s file %s (%s)",
            user_id, file_id, e,
        )
        return None


# ═══════════════════════════════════════════════════════════════
# File bytes routing — read from local OR Drive
# ═══════════════════════════════════════════════════════════════
async def fetch_file_bytes(file: File, db: AsyncSession) -> bytes:
    """Read raw file bytes — auto route based on file.storage_source.

    - storage_source = "local" → read raw_path จาก disk (ไม่เปลี่ยน behavior เดิม)
    - storage_source = "drive_uploaded" / "drive_picked" → download จาก Drive

    Raises:
        FileNotFoundError: ถ้า local file หาย / Drive file ลบไปแล้ว
        RuntimeError: ถ้า byos แต่ user ไม่มี connection (data inconsistency)

    Caller responsibility: user ที่ owns file ต้อง byos + has connection ก่อนเรียก
    """
    if file.storage_source == STORAGE_SOURCE_LOCAL or not file.drive_file_id:
        # Managed mode (default) — read from disk
        with open(file.raw_path, "rb") as f:
            return f.read()

    # BYOS — download from Drive
    pair = await _get_byos_user_with_connection(file.user_id, db)
    if not pair:
        raise RuntimeError(
            f"file {file.id} marked storage_source={file.storage_source} but user {file.user_id} "
            f"has no Drive connection (data inconsistency)"
        )
    _user, conn = pair
    client = await _build_drive_client(conn)
    return client.download_file(file.drive_file_id, mime_type_hint=file.filetype)


# ═══════════════════════════════════════════════════════════════
# Drive file deletion (per-file) — best-effort trash for BYOS
# ═══════════════════════════════════════════════════════════════
async def delete_drive_file_if_byos(
    user_id: str,
    db: AsyncSession,
    drive_file_id: str,
) -> bool:
    """Best-effort: trash a file ใน user's Drive ถ้า user เป็น byos + connected.

    ใช้โดย skip-duplicates endpoint (v7.1) — เมื่อ user เลือกข้ามไฟล์ที่ซ้ำ
    + ไฟล์นั้นถูก mirror ไป Drive แล้ว → ลบจาก Drive ด้วยเพื่อไม่ให้ orphan.

    Behavior:
      - Trash (ไม่ใช่ permanent delete) — recoverable 30 วันใน Drive's bin
      - Best-effort: log warning ถ้า fail แต่ไม่ raise → caller ทำ DB delete ต่อได้
      - No-op สำหรับ managed users / not configured / not connected

    Args:
        user_id: เจ้าของไฟล์ (สำหรับ filter byos status)
        db: async DB session
        drive_file_id: Google Drive file ID ที่จะ trash

    Returns:
        True  = trashed สำเร็จ
        False = no-op (managed/not configured/not connected) หรือ Drive failure
    """
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair
    try:
        client = await _build_drive_client(conn)
        client.delete_file(drive_file_id)
        logger.info(
            "BYOS: trashed Drive file %s for user %s", drive_file_id, user_id
        )
        return True
    except Exception as e:
        logger.warning(
            "BYOS: delete_drive_file failed for user %s file %s (%s)",
            user_id, drive_file_id, e,
        )
        return False


# ═══════════════════════════════════════════════════════════════
# Folder layout init (called by oauth/callback after first connect)
# ═══════════════════════════════════════════════════════════════
async def init_drive_folder_layout(
    user_id: str, db: AsyncSession
) -> dict[str, str] | None:
    """Ensure root + 7 sub-folders exist in user's Drive + write _meta/version.txt.

    Called once per user — typically right after OAuth callback succeeds.
    Idempotent: safe to call multiple times.

    Returns:
        Map ของ {sub_folder: id} สำเร็จ, หรือ None ถ้า managed/not configured/not connected
    """
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return None
    _user, conn = pair

    try:
        client = await _build_drive_client(conn)
        layout = client.ensure_pdb_folder_structure()
        # เขียน _meta/version.txt เพื่อ schema versioning ในอนาคต
        from .drive_layout import DRIVE_SCHEMA_VERSION, MIME_TEXT
        meta_id = layout["_meta"]
        filename = META_VERSION_TXT.split("/")[-1]
        existing = client.find_file_by_name(filename, parent_id=meta_id)
        if not existing:
            client.upload_file(meta_id, filename, DRIVE_SCHEMA_VERSION, MIME_TEXT)
        logger.info("BYOS: folder layout initialized for user %s", user_id)
        return layout
    except Exception as e:
        logger.error("BYOS: folder layout init failed for user %s (%s)", user_id, e)
        return None
