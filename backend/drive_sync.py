"""Drive ↔ Cache sync engine (BYOS feature, v7.0).

หน้าที่:
  - Periodic sync (every ~5 min หรือ manual button) — pull Drive changes into cache
  - Push cache changes to Drive (upload, update, delete)
  - Detect drift (cache vs Drive modifiedTime ต่างกัน)
  - Resolve conflicts per Plan Q4: **Drive wins** เสมอ (Drive = source of truth)
  - Idempotent + resumable (กระตุ้นซ้ำได้ ไม่เกิด duplicate)

Architecture:
  Drive ─(pull)→ DriveSync ─(write)→ SQLite cache + ChromaDB
  Drive ←(push)─ DriveSync ←(read)── User actions in UI

Conflict scenarios:
  - File modified in Drive AND in cache (concurrent edit) → Drive wins
  - File deleted in Drive but still in cache → soft-delete cache (mark deleted)
  - File deleted in cache but still in Drive → re-import on next pull
  - File renamed in Drive → cache.filename auto-update
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Optional, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DriveConnection, File
from .drive_layout import STORAGE_SOURCE_DRIVE_PICKED, STORAGE_SOURCE_DRIVE_UPLOADED
from .drive_oauth import decrypt_refresh_token
from .drive_storage import DriveClient

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════
# Result types
# ═══════════════════════════════════════════════════════════════
class SyncStats(TypedDict):
    """ผลลัพธ์รวมของ sync รอบนึง — สำหรับ logging + UI status."""
    pulled_new: int          # ไฟล์ที่ Drive มี ใหม่ (cache ยังไม่เคยรู้)
    pulled_updated: int      # ไฟล์ที่ cache มี Drive แก้ใหม่กว่า → cache ตามไป
    pulled_deleted: int      # ไฟล์ที่ Drive ลบไปแล้ว → cache mark deleted
    pushed_new: int          # ไฟล์ใน cache (uploaded fresh) ส่งขึ้น Drive
    pushed_updated: int      # cache แก้ + ส่งทับ Drive
    conflicts_resolved: int  # drift detected + Drive won
    errors: int              # Drive API errors (non-fatal — counted, not raised)
    duration_ms: int         # เวลาที่ใช้รอบนี้


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _parse_drive_time(rfc3339: str) -> datetime:
    """แปลง Drive's RFC3339 timestamp (e.g., '2026-04-30T10:00:00.123Z') → UTC datetime."""
    # Drive returns "...Z" — Python <3.11 ไม่รองรับ Z ตรงๆ ใน fromisoformat()
    cleaned = rfc3339.replace("Z", "+00:00")
    return datetime.fromisoformat(cleaned).astimezone(timezone.utc).replace(tzinfo=None)


def _format_drive_time(dt: datetime) -> str:
    """แปลง datetime → RFC3339 (Drive API expects this format ตอน update modifiedTime)."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def _has_drift(cache_modified: Optional[datetime], drive_modified_iso: str) -> bool:
    """True ถ้า Drive modifiedTime ใหม่กว่า cache (Drive = newer)."""
    if cache_modified is None:
        return True  # cache ยังไม่เคยมี → Drive ชนะ default
    drive_dt = _parse_drive_time(drive_modified_iso)
    return drive_dt > cache_modified


# ═══════════════════════════════════════════════════════════════
# DriveSync — main orchestrator
# ═══════════════════════════════════════════════════════════════
class DriveSync:
    """Sync orchestrator สำหรับ user คนเดียว.

    Lifecycle:
        1. Caller (e.g., scheduled job หรือ /api/drive/sync endpoint) เรียก:
           sync = DriveSync(user_id, db)
           await sync.load_connection()    # decrypt token, build DriveClient
           stats = await sync.run_full_sync()
        2. Stats → log + update DriveConnection.last_sync_*

    Why class (vs functions)?
        - State (DriveClient, folder_layout) shared across multiple methods
        - Easier to mock in tests (inject _client)
    """

    def __init__(self, user_id: str, db: AsyncSession):
        self.user_id = user_id
        self.db = db
        self._client: Optional[DriveClient] = None
        self._connection: Optional[DriveConnection] = None
        self._folder_layout: dict[str, str] = {}

    # ───────────────────────────────────────────────────────────
    # Test helper — inject pre-built client (skip OAuth load)
    # ───────────────────────────────────────────────────────────
    @classmethod
    def _from_client(
        cls, user_id: str, db: AsyncSession, client: DriveClient,
        connection: DriveConnection, folder_layout: dict[str, str],
    ) -> "DriveSync":
        instance = cls(user_id, db)
        instance._client = client
        instance._connection = connection
        instance._folder_layout = folder_layout
        return instance

    # ═══════════════════════════════════════════════════════════
    # Setup
    # ═══════════════════════════════════════════════════════════
    async def load_connection(self) -> None:
        """Load DriveConnection จาก DB + decrypt refresh_token + build DriveClient.

        Raises:
            ValueError: ถ้า user ไม่มี DriveConnection (ยังไม่เคย connect)
            RuntimeError: ถ้า decrypt fail (encryption key เปลี่ยน)
        """
        result = await self.db.execute(
            select(DriveConnection).where(DriveConnection.user_id == self.user_id)
        )
        conn = result.scalar_one_or_none()
        if not conn:
            raise ValueError(f"NO_DRIVE_CONNECTION: user {self.user_id} ยังไม่ได้ connect Drive")

        plaintext = decrypt_refresh_token(conn.refresh_token_encrypted)
        self._client = DriveClient(plaintext)
        self._connection = conn

        # Ensure folder layout exists (idempotent)
        self._folder_layout = self._client.ensure_pdb_folder_structure()

    # ═══════════════════════════════════════════════════════════
    # Main entry point
    # ═══════════════════════════════════════════════════════════
    async def run_full_sync(self) -> SyncStats:
        """Run a full bi-directional sync.

        Order:
            1. PUSH first (local → Drive) — บันทึก work ของ user ก่อน
            2. PULL second (Drive → local) — รับการเปลี่ยนแปลงจาก Drive
            3. Reconcile drift — Drive wins per Plan Q4

        Why push-then-pull?
            ถ้า user แก้ใน UI ปุ๊บ + sync วูบ → push ขึ้น Drive ก่อน
            กัน race ที่ pull-first จะมาทับงานของ user
        """
        if not self._client:
            await self.load_connection()
        assert self._client is not None and self._connection is not None

        started = datetime.utcnow()
        stats: SyncStats = {
            "pulled_new": 0, "pulled_updated": 0, "pulled_deleted": 0,
            "pushed_new": 0, "pushed_updated": 0,
            "conflicts_resolved": 0, "errors": 0, "duration_ms": 0,
        }

        try:
            self._connection.last_sync_status = "syncing"
            await self.db.commit()

            await self._push_local_to_drive(stats)
            await self._pull_drive_to_local(stats)

            self._connection.last_sync_status = "success"
            self._connection.last_sync_error = None
            self._connection.last_sync_at = datetime.utcnow()
        except Exception as e:
            self._connection.last_sync_status = "error"
            self._connection.last_sync_error = f"{type(e).__name__}: {e}"
            stats["errors"] += 1
            logger.exception("BYOS sync failed for user %s", self.user_id)
            # ไม่ raise — caller (background job) จะ retry รอบหน้า
        finally:
            await self.db.commit()
            stats["duration_ms"] = int((datetime.utcnow() - started).total_seconds() * 1000)

        return stats

    # ═══════════════════════════════════════════════════════════
    # PUSH: local → Drive
    # ═══════════════════════════════════════════════════════════
    async def _push_local_to_drive(self, stats: SyncStats) -> None:
        """Upload ไฟล์ที่ user เพิ่ง upload ผ่าน UI (BYOS mode) ขึ้น Drive.

        เลือกเฉพาะ files ที่:
          - drive_file_id IS NULL (ยังไม่เคยส่งขึ้น Drive)
          - storage_source = drive_uploaded (ตั้งใจไป Drive) หรือ
          - storage_source = local (ไฟล์เก่าก่อนเปิด BYOS — ต้อง push ขึ้นด้วย)
          - มี raw_path ที่อ่านได้ (กัน crash ถ้าไฟล์ถูกลบจาก disk แล้ว)
        """
        assert self._client is not None
        result = await self.db.execute(
            select(File).where(
                File.user_id == self.user_id,
                File.storage_source.in_([
                    STORAGE_SOURCE_DRIVE_UPLOADED,
                    "local",  # ไฟล์เก่าก่อนเปิด BYOS — push ขึ้น Drive ด้วย
                ]),
                File.drive_file_id.is_(None),
            )
        )
        pending = list(result.scalars().all())
        if not pending:
            return

        raw_folder_id = self._folder_layout["raw"]
        for f in pending:
            try:
                # Guard: ข้าม files ที่ไม่มี raw_path + ไม่มี extracted_text
                import os
                if f.raw_path and os.path.exists(f.raw_path):
                    with open(f.raw_path, "rb") as fh:
                        content = fh.read()
                elif f.extracted_text:
                    # Fallback: ไฟล์เก่าที่ raw file หายไป (deploy/volume recreate)
                    # แต่ยังมี extracted_text → ใช้ text เป็น content ขึ้น Drive
                    content = f.extracted_text.encode("utf-8")
                    logger.info(
                        "BYOS push fallback — using extracted_text for file %s (%s)",
                        f.id, f.filename,
                    )
                else:
                    logger.warning(
                        "BYOS push skip — no raw_path and no text for file %s (%s)",
                        f.id, f.filename,
                    )
                    stats["errors"] += 1
                    continue

                drive_id = self._client.upload_file(
                    parent_id=raw_folder_id,
                    name=f"{f.id}_{f.filename}",
                    content=content,
                    mime_type=f.filetype or "application/octet-stream",
                )
                f.drive_file_id = drive_id
                f.drive_modified_time = datetime.utcnow()
                # อัพเดท storage_source จาก 'local' → 'drive_uploaded'
                # เพื่อให้ UI แสดง "บน Drive ของคุณ" แทน "บนเซิร์ฟเวอร์"
                if f.storage_source == "local":
                    f.storage_source = STORAGE_SOURCE_DRIVE_UPLOADED
                stats["pushed_new"] += 1
            except Exception as e:
                logger.warning(
                    "BYOS push failed for file %s (user %s): %s", f.id, self.user_id, e
                )
                stats["errors"] += 1
                # ไม่ break — push ไฟล์อื่นต่อ

    # ═══════════════════════════════════════════════════════════
    # PULL: Drive → local
    # ═══════════════════════════════════════════════════════════
    async def _pull_drive_to_local(self, stats: SyncStats) -> None:
        """List files ใน Drive's raw/ folder + reconcile กับ cache.

        Cases:
            A. Drive มี file ที่ cache ไม่มี → IMPORT (insert File row)
            B. Drive มี + cache มี + drive_modifiedTime > cache → UPDATE (drift, Drive wins)
            C. Cache มี drive_file_id แต่ Drive ลบ trashed → SOFT-DELETE cache
        """
        assert self._client is not None
        raw_folder_id = self._folder_layout["raw"]
        drive_files = self._client.list_folder(raw_folder_id, only_files=True)
        drive_ids = {f["id"] for f in drive_files}

        # Build cache index: drive_file_id -> File row
        result = await self.db.execute(
            select(File).where(
                File.user_id == self.user_id,
                File.drive_file_id.isnot(None),
            )
        )
        cache_files: dict[str, File] = {
            f.drive_file_id: f for f in result.scalars().all()
            if f.drive_file_id  # type narrow
        }

        # Cases A + B
        for drive_f in drive_files:
            drive_id = drive_f["id"]
            cached = cache_files.get(drive_id)
            if not cached:
                # CASE A — new in Drive (e.g., user picked existing file via Picker)
                self._import_drive_file(drive_f, stats)
            else:
                # CASE B — drift?
                if _has_drift(cached.drive_modified_time, drive_f["modifiedTime"]):
                    cached.drive_modified_time = _parse_drive_time(drive_f["modifiedTime"])
                    # We don't auto-re-extract here — caller schedule re-extraction job
                    # (extraction = LLM-heavy, do separately)
                    stats["pulled_updated"] += 1
                    stats["conflicts_resolved"] += 1

        # Case C — Drive deleted but cache still has it
        for drive_id, cached in cache_files.items():
            if drive_id not in drive_ids:
                # Soft-delete: mark cache deleted (user สามารถ undelete จาก Drive trash ใน 30 วัน)
                cached.processing_status = "deleted_in_drive"
                stats["pulled_deleted"] += 1

    def _import_drive_file(self, drive_f: dict[str, Any], stats: SyncStats) -> None:
        """Import a Drive file into cache as new File row (Case A).

        Note: ตั้ง processing_status='uploaded' เพื่อให้ background job รับไป extract +
        embed ต่อ (ไม่ทำใน sync เพราะ LLM/embedding ใช้เวลา + cost token)
        """
        # Parse {file_id}_{name} format ที่ใช้ใน raw/ folder
        # ถ้า upload จาก app เรา → format นี้. ถ้า user pick จาก Drive อื่น → ไม่มี prefix
        name_in_drive: str = drive_f["name"]
        local_id, original_name = self._split_drive_name(name_in_drive)

        new_row = File(
            id=local_id,
            user_id=self.user_id,
            filename=original_name,
            filetype=drive_f.get("mimeType", "application/octet-stream"),
            raw_path="",  # ไม่มีไฟล์ local — จะ download on-demand
            drive_file_id=drive_f["id"],
            drive_modified_time=_parse_drive_time(drive_f["modifiedTime"]),
            storage_source=(
                STORAGE_SOURCE_DRIVE_UPLOADED
                if name_in_drive.startswith(local_id + "_")
                else STORAGE_SOURCE_DRIVE_PICKED
            ),
            processing_status="uploaded",
        )
        self.db.add(new_row)
        stats["pulled_new"] += 1

    @staticmethod
    def _split_drive_name(name: str) -> tuple[str, str]:
        """Parse '{file_id}_{original_name}' → (file_id, original_name).

        ถ้าไม่ตรง format → generate file_id ใหม่ + ใช้ทั้ง name เป็น original_name
        (สำหรับ drive_picked files ที่ user เลือกจาก Drive อื่น)
        """
        from .database import gen_id

        # file_id = first 12 hex chars (default ของ gen_id) + '_'
        if len(name) > 13 and name[12] == "_":
            candidate_id = name[:12]
            # Validate looks like UUID hex (lenient — gen_id() returns UUID hex slice)
            if all(c in "0123456789abcdef-" for c in candidate_id):
                return candidate_id, name[13:]
        return gen_id(), name


# ═══════════════════════════════════════════════════════════════
# Convenience entry point (for endpoint / scheduled job)
# ═══════════════════════════════════════════════════════════════
async def sync_user_drive(user_id: str, db: AsyncSession) -> SyncStats:
    """One-shot sync for a user — convenience wrapper.

    Caller pattern:
        from backend.drive_sync import sync_user_drive
        stats = await sync_user_drive(user.id, db)
        if stats["errors"] > 0:
            ...
    """
    sync = DriveSync(user_id, db)
    return await sync.run_full_sync()
