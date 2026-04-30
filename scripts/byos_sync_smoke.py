"""BYOS v7.0 — drive_sync.py mock smoke test (no real Drive API).

Run: python scripts/byos_sync_smoke.py

Strategy:
- Use real SQLite (apply migrations first via init_db)
- Build a fake DriveClient that exposes the methods drive_sync calls
  (ensure_pdb_folder_structure, list_folder, upload_file)
- Inject via DriveSync._from_client (test-only constructor)
- Verify:
    * push: local files (storage_source=drive_uploaded, no drive_file_id)
            get uploaded + drive_file_id assigned
    * pull A: new file in Drive that cache doesn't know -> imported as File row
    * pull B: drift detection (Drive modifiedTime > cache) -> conflicts_resolved
    * pull C: file deleted in Drive -> cache marked deleted_in_drive
    * stats are accurate
"""
from __future__ import annotations

import asyncio
import os
import secrets as _s
import sys
import tempfile
from datetime import datetime, timezone, timedelta

sys.path.insert(0, ".")

# Ensure migration applied (BYOS schema columns/tables)
from backend.database import (
    AsyncSessionLocal, DriveConnection, File, User, gen_id, init_db,
)
from backend.drive_sync import DriveSync, _parse_drive_time, _has_drift


PASS = FAIL = 0


def t(name, fn):
    global PASS, FAIL
    try:
        ok = fn()
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        PASS += int(bool(ok))
        FAIL += int(not ok)
    except Exception as e:
        print(f"  FAIL  {name} -> {type(e).__name__}: {e}")
        FAIL += 1


# ═══════════════════════════════════════════════════════════════
# Fake DriveClient — expose only the surface drive_sync uses
# ═══════════════════════════════════════════════════════════════
class FakeDriveClient:
    """Minimal mock — implements ensure_pdb_folder_structure / list_folder / upload_file."""

    def __init__(self):
        self.folder_layout = {
            "_root": "root_id",
            "raw": "raw_folder_id",
            "extracted": "extracted_folder_id",
            "summaries": "summaries_folder_id",
            "personal": "personal_folder_id",
            "data": "data_folder_id",
            "_meta": "meta_folder_id",
            "_backups": "backups_folder_id",
        }
        # Pre-populate Drive's raw/ folder for pull tests
        self.raw_files: list[dict] = []
        self.uploaded: list[dict] = []
        self._next_id = 1

    def ensure_pdb_folder_structure(self):
        return self.folder_layout

    def list_folder(self, folder_id, only_files=False):
        if folder_id == "raw_folder_id":
            return list(self.raw_files)
        return []

    def upload_file(self, parent_id, name, content, mime_type, resumable=None):
        new_id = f"drive_id_{self._next_id:04d}"
        self._next_id += 1
        record = {
            "id": new_id,
            "name": name,
            "mimeType": mime_type,
            "modifiedTime": "2026-04-30T00:00:00Z",
            "content": content,
        }
        self.uploaded.append(record)
        # Also add to raw_files so subsequent list_folder sees it
        self.raw_files.append(record)
        return new_id


# ═══════════════════════════════════════════════════════════════
# Setup helpers
# ═══════════════════════════════════════════════════════════════
async def make_user_with_connection() -> tuple[str, DriveConnection]:
    """Create a fresh test user + DriveConnection row."""
    async with AsyncSessionLocal() as db:
        user_id = gen_id()
        u = User(
            id=user_id,
            email=f"sync_{_s.token_hex(4)}@test.local",
            name="Sync Test",
            is_active=True,
            storage_mode="byos",
        )
        db.add(u)
        conn = DriveConnection(
            user_id=user_id,
            drive_email="sync@test.local",
            refresh_token_encrypted="not-used-in-mock",
            drive_root_folder_id="root_id",
            last_sync_status="pending",
        )
        db.add(conn)
        await db.commit()
        return user_id, conn


async def add_local_file(user_id: str, with_drive_id: bool = False) -> File:
    """Create a File row with raw bytes on disk (for push test)."""
    async with AsyncSessionLocal() as db:
        # Write actual bytes to a temp path so push can read them
        tmp = tempfile.NamedTemporaryFile(
            mode="wb", suffix=".txt", delete=False, prefix="byos_test_"
        )
        tmp.write(b"file content for sync test")
        tmp.close()
        f = File(
            id=gen_id(),
            user_id=user_id,
            filename="report.txt",
            filetype="text/plain",
            raw_path=tmp.name,
            storage_source="drive_uploaded",
            processing_status="uploaded",
        )
        if with_drive_id:
            f.drive_file_id = "preset_drive_id"
            f.drive_modified_time = datetime(2026, 4, 30, 9, 0, 0)
        db.add(f)
        await db.commit()
        await db.refresh(f)
        return f


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════
async def main():
    await init_db()  # ensure BYOS migrations applied

    print("=== 1. Time helpers ===")
    t("_parse_drive_time handles RFC3339 with Z",
      lambda: _parse_drive_time("2026-04-30T10:00:00Z").year == 2026)
    t("_parse_drive_time handles fractional seconds",
      lambda: _parse_drive_time("2026-04-30T10:00:00.123Z").year == 2026)
    t("_has_drift: cache None -> True (Drive wins by default)",
      lambda: _has_drift(None, "2026-04-30T10:00:00Z") is True)
    t("_has_drift: Drive newer than cache -> True",
      lambda: _has_drift(datetime(2026, 4, 30, 9, 0, 0), "2026-04-30T10:00:00Z") is True)
    t("_has_drift: cache newer than Drive -> False",
      lambda: _has_drift(datetime(2026, 4, 30, 11, 0, 0), "2026-04-30T10:00:00Z") is False)
    t("_has_drift: equal -> False",
      lambda: _has_drift(_parse_drive_time("2026-04-30T10:00:00Z"), "2026-04-30T10:00:00Z") is False)

    print("\n=== 2. PUSH: local files (no drive_file_id) -> Drive ===")

    user_id, conn = await make_user_with_connection()
    f = await add_local_file(user_id, with_drive_id=False)

    async with AsyncSessionLocal() as db:
        fake_client = FakeDriveClient()
        # Re-fetch conn in this session
        from sqlalchemy import select
        conn_re = (await db.execute(select(DriveConnection).where(DriveConnection.user_id == user_id))).scalar_one()
        sync = DriveSync._from_client(user_id, db, fake_client, conn_re, fake_client.folder_layout)
        stats = await sync.run_full_sync()

    def t2a():
        return stats["pushed_new"] == 1 and stats["errors"] == 0
    t("Push 1 file -> stats.pushed_new=1, errors=0", t2a)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_re = (await db.execute(select(File).where(File.id == f.id))).scalar_one()
        has_id = f_re.drive_file_id is not None
        modified_set = f_re.drive_modified_time is not None
    t("After push: file.drive_file_id is set", lambda: has_id)
    t("After push: file.drive_modified_time is set", lambda: modified_set)

    # Cleanup tmp file
    try:
        os.unlink(f.raw_path)
    except OSError:
        pass

    print("\n=== 3. PULL Case A: New Drive file -> imported into cache ===")
    user_id2, _ = await make_user_with_connection()

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        fake_client2 = FakeDriveClient()
        # Pre-populate Drive with a file the cache doesn't know about
        fake_client2.raw_files.append({
            "id": "drive_external_001",
            "name": "abc123def456_picked.pdf",
            "mimeType": "application/pdf",
            "modifiedTime": "2026-04-30T11:00:00Z",
        })
        conn_re = (await db.execute(select(DriveConnection).where(DriveConnection.user_id == user_id2))).scalar_one()
        sync2 = DriveSync._from_client(user_id2, db, fake_client2, conn_re, fake_client2.folder_layout)
        stats2 = await sync2.run_full_sync()

    t("Pull Case A: stats.pulled_new=1", lambda: stats2["pulled_new"] == 1)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(select(File).where(File.user_id == user_id2))
        rows = list(result.scalars().all())
    t("Pull Case A: File row inserted with drive_file_id",
      lambda: len(rows) == 1 and rows[0].drive_file_id == "drive_external_001")
    t("Pull Case A: storage_source detected from name format",
      lambda: rows[0].storage_source in ("drive_uploaded", "drive_picked"))
    t("Pull Case A: processing_status='uploaded' (queued for extraction)",
      lambda: rows[0].processing_status == "uploaded")

    print("\n=== 4. PULL Case B: Drift detection (Drive newer) ===")
    user_id3, _ = await make_user_with_connection()

    # Pre-create cache row that already links to a Drive file
    async with AsyncSessionLocal() as db:
        cached_file = File(
            id=gen_id(),
            user_id=user_id3,
            filename="report.pdf",
            filetype="application/pdf",
            raw_path="",
            drive_file_id="drive_drifted_001",
            drive_modified_time=datetime(2026, 4, 30, 9, 0, 0),  # 9am
            storage_source="drive_uploaded",
            processing_status="organized",
        )
        db.add(cached_file)
        await db.commit()
        cached_id = cached_file.id

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        fake_client3 = FakeDriveClient()
        # Drive shows the same file with a NEWER modifiedTime (11am)
        fake_client3.raw_files.append({
            "id": "drive_drifted_001",
            "name": "report.pdf",
            "mimeType": "application/pdf",
            "modifiedTime": "2026-04-30T11:00:00Z",  # 11am (newer than cache 9am)
        })
        conn_re = (await db.execute(select(DriveConnection).where(DriveConnection.user_id == user_id3))).scalar_one()
        sync3 = DriveSync._from_client(user_id3, db, fake_client3, conn_re, fake_client3.folder_layout)
        stats3 = await sync3.run_full_sync()

    t("Pull Case B: stats.pulled_updated=1, conflicts_resolved=1",
      lambda: stats3["pulled_updated"] == 1 and stats3["conflicts_resolved"] == 1)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_re = (await db.execute(select(File).where(File.id == cached_id))).scalar_one()
        new_time = f_re.drive_modified_time
    t("Pull Case B: cache.drive_modified_time updated to Drive's value (11am)",
      lambda: new_time and new_time.hour == 11)

    print("\n=== 5. PULL Case C: Drive deleted -> cache soft-delete ===")
    user_id4, _ = await make_user_with_connection()

    async with AsyncSessionLocal() as db:
        cached_doomed = File(
            id=gen_id(),
            user_id=user_id4,
            filename="ghost.pdf",
            filetype="application/pdf",
            raw_path="",
            drive_file_id="drive_doomed_001",
            drive_modified_time=datetime(2026, 4, 30, 9, 0, 0),
            storage_source="drive_uploaded",
            processing_status="organized",
        )
        db.add(cached_doomed)
        await db.commit()
        doomed_id = cached_doomed.id

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        fake_client4 = FakeDriveClient()
        # Drive's raw/ folder is EMPTY — cache file's drive_file_id won't be in drive_ids
        conn_re = (await db.execute(select(DriveConnection).where(DriveConnection.user_id == user_id4))).scalar_one()
        sync4 = DriveSync._from_client(user_id4, db, fake_client4, conn_re, fake_client4.folder_layout)
        stats4 = await sync4.run_full_sync()

    t("Pull Case C: stats.pulled_deleted=1", lambda: stats4["pulled_deleted"] == 1)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_re = (await db.execute(select(File).where(File.id == doomed_id))).scalar_one()
        new_status = f_re.processing_status
    t("Pull Case C: cache row marked processing_status='deleted_in_drive'",
      lambda: new_status == "deleted_in_drive")

    print("\n=== 6. Connection state updates after sync ===")
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        conn_re = (await db.execute(select(DriveConnection).where(DriveConnection.user_id == user_id4))).scalar_one()
        status = conn_re.last_sync_status
        last_at = conn_re.last_sync_at
    t("DriveConnection.last_sync_status='success' after run", lambda: status == "success")
    t("DriveConnection.last_sync_at is populated", lambda: last_at is not None)

    print("\n=== 7. Drive name parsing ===")
    t("'abc123def456_report.pdf' -> ('abc123def456', 'report.pdf')",
      lambda: DriveSync._split_drive_name("abc123def456_report.pdf") == ("abc123def456", "report.pdf"))
    t("'no_prefix_file.pdf' -> generated id + full name",
      lambda: (lambda r: len(r[0]) == 12 and r[1] == "no_prefix_file.pdf")(
          DriveSync._split_drive_name("no_prefix_file.pdf")))
    t("'short.pdf' -> generated id + 'short.pdf'",
      lambda: (lambda r: len(r[0]) == 12 and r[1] == "short.pdf")(
          DriveSync._split_drive_name("short.pdf")))

    print("\n=== 8. SyncStats invariants ===")
    t("All stats are non-negative integers",
      lambda: all(isinstance(stats4[k], int) and stats4[k] >= 0
                  for k in ("pulled_new", "pulled_updated", "pulled_deleted",
                            "pushed_new", "pushed_updated", "conflicts_resolved",
                            "errors", "duration_ms")))
    t("duration_ms > 0 (sync took some time)",
      lambda: stats4["duration_ms"] > 0)

    print(f"\n{'=' * 60}")
    print(f"  RESULT: {PASS} passed / {FAIL} failed")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


sys.exit(asyncio.run(main()))
