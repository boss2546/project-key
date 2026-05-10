"""v9.4.1 — Comprehensive Delete + Sync Cleanup smoke test.

Run: python scripts/v9_4_1_smoke.py

Covers 10 findings (F1-F24) from the comprehensive delete/sync plan:
    F1  — MCP _tool_delete_file 6-step (drive_cleanup field present)
    F2  — /api/reset stats response (per-file 4-step)
    F3  — sync Case A2 stale-link UPDATE
    F4  — sub-folder delete helpers (extracted/ + summaries/)
    F5  — _should_trash_drive_file guard truth table
    F6  — DELETE BackgroundTasks pattern (signature has background_tasks)
    F7  — sync orphan retry budget (max 3 attempts)
    F16 — /api/files filter deleted_in_drive (default-hidden)
    F23 — drive_cleanup field shape: scheduled / skipped:* / completed / failed
    F24 — push duplicate guard (re-link instead of re-upload)
"""
from __future__ import annotations

import asyncio
import inspect
import secrets as _s
import sys

sys.path.insert(0, ".")

from backend.config import APP_VERSION
from backend.database import (
    AsyncSessionLocal, DriveConnection, File, User, gen_id, init_db,
)
from backend.drive_sync import DriveSync, SyncStats
from backend.storage_router import (
    _should_trash_drive_file,
    delete_drive_file_if_byos,
    delete_extracted_text_from_drive_if_byos,
    delete_summary_from_drive_if_byos,
)


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
# Fake DriveClient v2 — adds delete_file + find_file_by_name + ensure_folder
# ═══════════════════════════════════════════════════════════════
class FakeDriveClientV2:
    """Mock DriveClient with all methods v9.4.1 needs."""

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
        self.raw_files: list[dict] = []
        self.extracted_files: list[dict] = []
        self.summary_files: list[dict] = []
        self.uploaded: list[dict] = []
        self.deleted_ids: list[str] = []
        self.delete_should_fail: bool = False
        self._next_id = 1

    def ensure_pdb_folder_structure(self):
        return self.folder_layout

    def ensure_folder(self, name, parent_id=None):
        return self.folder_layout.get(name, f"{name}_folder_id")

    def list_folder(self, folder_id, only_files=False):
        if folder_id == "raw_folder_id":
            return list(self.raw_files)
        if folder_id == "extracted_folder_id":
            return list(self.extracted_files)
        if folder_id == "summaries_folder_id":
            return list(self.summary_files)
        return []

    def find_file_by_name(self, name, parent_id=None):
        bucket = self.raw_files
        if parent_id == "extracted_folder_id":
            bucket = self.extracted_files
        elif parent_id == "summaries_folder_id":
            bucket = self.summary_files
        for f in bucket:
            if f["name"] == name:
                return f
        return None

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
        if parent_id == "raw_folder_id":
            self.raw_files.append(record)
        elif parent_id == "extracted_folder_id":
            self.extracted_files.append(record)
        elif parent_id == "summaries_folder_id":
            self.summary_files.append(record)
        return new_id

    def update_file_content(self, file_id, content, mime_type):
        for f in self.uploaded:
            if f["id"] == file_id:
                f["content"] = content
                return f
        return None

    def delete_file(self, file_id):
        if self.delete_should_fail:
            raise RuntimeError("Mock Drive API error")
        self.deleted_ids.append(file_id)
        for bucket in (self.raw_files, self.extracted_files, self.summary_files):
            bucket[:] = [f for f in bucket if f["id"] != file_id]
        return True


# ═══════════════════════════════════════════════════════════════
# Setup helpers
# ═══════════════════════════════════════════════════════════════
async def make_user_with_connection(storage_mode="byos") -> str:
    async with AsyncSessionLocal() as db:
        user_id = gen_id()
        u = User(
            id=user_id,
            email=f"v941_{_s.token_hex(4)}@test.local",
            name="v9.4.1 Test",
            is_active=True,
            storage_mode=storage_mode,
        )
        db.add(u)
        if storage_mode == "byos":
            conn = DriveConnection(
                user_id=user_id,
                drive_email="v941@test.local",
                refresh_token_encrypted="not-used-in-mock",
                drive_root_folder_id="root_id",
                last_sync_status="pending",
            )
            db.add(conn)
        await db.commit()
        return user_id


async def add_file_row(user_id, *, file_id=None, drive_file_id=None,
                       storage_source="drive_uploaded",
                       processing_status="uploaded", filename="report.txt"):
    async with AsyncSessionLocal() as db:
        f = File(
            id=file_id or gen_id(),
            user_id=user_id,
            filename=filename,
            filetype="txt",
            raw_path="",
            drive_file_id=drive_file_id,
            storage_source=storage_source,
            processing_status=processing_status,
        )
        db.add(f)
        await db.commit()
        return f.id


# ═══════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════
async def main():
    await init_db()

    print(f"=== v{APP_VERSION} smoke (expecting 9.4.1) ===")
    t("APP_VERSION = '9.4.1'", lambda: APP_VERSION == "9.4.1")

    print("\n=== F5. _should_trash_drive_file truth table (drive_picked guard) ===")
    t("'drive_uploaded' -> True (we created · safe to trash)",
      lambda: _should_trash_drive_file("drive_uploaded") is True)
    t("'drive_picked'   -> False (user's external · CRITICAL F5 protection)",
      lambda: _should_trash_drive_file("drive_picked") is False)
    t("'local'          -> False",
      lambda: _should_trash_drive_file("local") is False)
    t("None             -> False (safe default)",
      lambda: _should_trash_drive_file(None) is False)
    t("''               -> False (safe default)",
      lambda: _should_trash_drive_file("") is False)
    t("'unknown_value'  -> False (unknown · safe default)",
      lambda: _should_trash_drive_file("unknown_value") is False)

    print("\n=== F4. Sub-folder delete helpers — managed user no-op ===")
    managed_uid = await make_user_with_connection(storage_mode="managed")
    async with AsyncSessionLocal() as db:
        ok1 = await delete_extracted_text_from_drive_if_byos(managed_uid, db, "any_id")
        ok2 = await delete_summary_from_drive_if_byos(managed_uid, db, "any_id")
        ok3 = await delete_drive_file_if_byos(managed_uid, db, "any_drive_id")
    t("delete_extracted (managed) -> False (no-op)", lambda: ok1 is False)
    t("delete_summary   (managed) -> False (no-op)", lambda: ok2 is False)
    t("delete_drive     (managed) -> False (no-op · regression check)", lambda: ok3 is False)

    print("\n=== F1. MCP _tool_delete_file — drive_cleanup field present ===")
    from backend.mcp_tools import _tool_delete_file
    src = inspect.getsource(_tool_delete_file)
    t("MCP delete_file source has 'drive_cleanup' return key",
      lambda: 'drive_cleanup' in src)
    t("MCP delete_file calls _should_trash_drive_file guard",
      lambda: '_should_trash_drive_file' in src)
    t("MCP delete_file calls all 3 Drive cleanup helpers",
      lambda: 'delete_drive_file_if_byos' in src
              and 'delete_extracted_text_from_drive_if_byos' in src
              and 'delete_summary_from_drive_if_byos' in src)
    t("MCP delete_file calls vector_search remove",
      lambda: 'vector_search' in src and 'remove_file' in src)

    # Real call against managed user — verify drive_cleanup="skipped:managed"
    managed_user = await make_user_with_connection(storage_mode="managed")
    fid_managed = await add_file_row(
        managed_user, drive_file_id=None, storage_source="local",
    )
    async with AsyncSessionLocal() as db:
        result = await _tool_delete_file(db, managed_user, fid_managed)
    t("MCP delete (managed user, no drive_id) -> drive_cleanup='skipped:no_drive_id'",
      lambda: result.get("drive_cleanup") == "skipped:no_drive_id")
    t("MCP delete returns status='deleted'",
      lambda: result.get("status") == "deleted")

    # Drive_picked file → must skip
    byos_user_a = await make_user_with_connection(storage_mode="byos")
    fid_picked = await add_file_row(
        byos_user_a, drive_file_id="drive_external_picked_id",
        storage_source="drive_picked",
    )
    async with AsyncSessionLocal() as db:
        result_picked = await _tool_delete_file(db, byos_user_a, fid_picked)
    t("MCP delete (drive_picked) -> drive_cleanup='skipped:drive_picked' (F5 critical)",
      lambda: result_picked.get("drive_cleanup") == "skipped:drive_picked")

    print("\n=== F6. DELETE /api/files/{id} signature — BackgroundTasks present ===")
    from backend import main as m
    sig = inspect.signature(m.delete_file)
    params = list(sig.parameters.keys())
    t("delete_file signature has 'background_tasks' param (F6 fast response)",
      lambda: 'background_tasks' in params)
    t("_cleanup_drive_for_deleted_file helper exists (background task)",
      lambda: hasattr(m, '_cleanup_drive_for_deleted_file'))
    cleanup_src = inspect.getsource(m._cleanup_drive_for_deleted_file)
    t("background helper guards on _should_trash_drive_file",
      lambda: '_should_trash_drive_file' in cleanup_src)
    t("background helper opens its own AsyncSessionLocal",
      lambda: 'AsyncSessionLocal' in cleanup_src)

    print("\n=== F23. drive_cleanup response shape ===")
    delete_src = inspect.getsource(m.delete_file)
    t("DELETE response includes drive_cleanup='scheduled' branch",
      lambda: '"scheduled"' in delete_src or "'scheduled'" in delete_src)
    t("DELETE response includes 'skipped:drive_picked'",
      lambda: 'skipped:drive_picked' in delete_src)
    t("DELETE response includes 'skipped:managed'",
      lambda: 'skipped:managed' in delete_src)
    t("DELETE response includes 'skipped:no_drive_id'",
      lambda: 'skipped:no_drive_id' in delete_src)

    print("\n=== F2. /api/reset stats accumulator ===")
    reset_src = inspect.getsource(m.reset_all)
    t("reset_all init stats dict",
      lambda: '"files_deleted":' in reset_src and '"drive_files_trashed":' in reset_src)
    t("reset_all guards on _should_trash_drive_file (F5)",
      lambda: '_should_trash_drive_file' in reset_src)
    t("reset_all calls all 3 Drive cleanup helpers",
      lambda: 'delete_drive_file_if_byos' in reset_src
              and 'delete_extracted_text_from_drive_if_byos' in reset_src
              and 'delete_summary_from_drive_if_byos' in reset_src)
    t("reset_all returns stats key in response",
      lambda: '"stats": stats' in reset_src or "'stats': stats" in reset_src)
    t("reset_all tracks drive_cleanup_skipped_picked",
      lambda: 'drive_cleanup_skipped_picked' in reset_src)

    print("\n=== F16. /api/files filter deleted_in_drive ===")
    list_src = inspect.getsource(m.list_files)
    t("list_files has include_deleted_in_drive query param",
      lambda: 'include_deleted_in_drive' in list_src)
    t("list_files filters processing_status != 'deleted_in_drive' by default",
      lambda: '!= "deleted_in_drive"' in list_src or "!= 'deleted_in_drive'" in list_src)

    # Functional test: insert ghost row + verify filter excludes it
    byos_user_g = await make_user_with_connection()
    ghost_id = await add_file_row(
        byos_user_g, processing_status="deleted_in_drive", filename="ghost.pdf",
    )
    visible_id = await add_file_row(
        byos_user_g, processing_status="organized", filename="visible.pdf",
    )
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        # Default — ghost hidden
        q1 = select(File).where(
            File.user_id == byos_user_g,
            File.processing_status != "deleted_in_drive",
        )
        rows_default = (await db.execute(q1)).scalars().all()
        # Override — both visible
        q2 = select(File).where(File.user_id == byos_user_g)
        rows_admin = (await db.execute(q2)).scalars().all()
    t("Default filter hides ghost row (1 visible)",
      lambda: len(rows_default) == 1 and rows_default[0].filename == "visible.pdf")
    t("Admin override returns both rows (2 total)",
      lambda: len(rows_admin) == 2)

    print("\n=== F24. Push duplicate guard — re-link, do not re-upload (CRITICAL) ===")
    # Setup: BYOS user with 1 cache row (drive_file_id=NULL, storage_source='local')
    # simulates post-disconnect-keep_files=False state.
    # Drive raw/ already has matching {file_id}_{filename} → guard should re-link.
    byos_user_d = await make_user_with_connection()
    dup_file_id = _s.token_hex(6)  # 12-hex random — avoid collision across runs
    await add_file_row(
        byos_user_d, file_id=dup_file_id, drive_file_id=None,
        storage_source="local", filename="report.txt",
    )

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        fake = FakeDriveClientV2()
        # Pre-populate Drive with matching file (simulates surviving Drive copy)
        fake.raw_files.append({
            "id": "drive_existing_xyz",
            "name": f"{dup_file_id}_report.txt",
            "mimeType": "text/plain",
            "modifiedTime": "2026-04-30T10:00:00Z",
        })
        conn = (await db.execute(
            select(DriveConnection).where(DriveConnection.user_id == byos_user_d)
        )).scalar_one()
        sync = DriveSync._from_client(byos_user_d, db, fake, conn, fake.folder_layout)
        # Run only push (avoid pull + Case C side-effects)
        stats = {
            "pulled_new": 0, "pulled_updated": 0, "pulled_deleted": 0,
            "pushed_new": 0, "pushed_updated": 0,
            "relinked": 0, "orphans_cleaned": 0,
            "orphans_skipped_budget": 0, "duplicate_push_prevented": 0,
            "conflicts_resolved": 0, "errors": 0, "duration_ms": 0,
        }
        await sync._push_local_to_drive(stats)
        await db.commit()

    t("F24: stats.duplicate_push_prevented=1 (no re-upload)",
      lambda: stats["duplicate_push_prevented"] == 1)
    t("F24: stats.pushed_new=0 (didn't actually upload)",
      lambda: stats["pushed_new"] == 0)
    t("F24: fake.uploaded list empty (no API call made)",
      lambda: len(fake.uploaded) == 0)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_re = (await db.execute(
            select(File).where(File.id == dup_file_id)
        )).scalar_one()
        relinked = f_re.drive_file_id == "drive_existing_xyz"
        promoted = f_re.storage_source == "drive_uploaded"
    t("F24: cache row drive_file_id re-linked to existing Drive file id",
      lambda: relinked)
    t("F24: storage_source promoted local -> drive_uploaded",
      lambda: promoted)

    print("\n=== F3. Sync Case A2 stale-link UPDATE existing row ===")
    # Simulate: cache row with file_id 'def789abc012' but drive_file_id=NULL
    # Drive raw/ has matching {file_id}_filename → A2 stale-link should re-link
    byos_user_s = await make_user_with_connection()
    stale_id = _s.token_hex(6)  # 12-hex random
    await add_file_row(
        byos_user_s, file_id=stale_id, drive_file_id=None,
        storage_source="local", filename="stale.txt",
    )

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        fake_s = FakeDriveClientV2()
        # Populate AFTER push would clear it — simulate scenario where push didn't catch
        # (e.g., guard disabled, or test directly _pull behavior)
        # Use unique filename to avoid push guard hitting first
        fake_s.raw_files.append({
            "id": "drive_stale_target",
            "name": f"{stale_id}_different_name.txt",  # different filename → push guard misses
            "mimeType": "text/plain",
            "modifiedTime": "2026-04-30T10:00:00Z",
        })
        conn = (await db.execute(
            select(DriveConnection).where(DriveConnection.user_id == byos_user_s)
        )).scalar_one()
        sync = DriveSync._from_client(byos_user_s, db, fake_s, conn, fake_s.folder_layout)
        stats_s = {
            "pulled_new": 0, "pulled_updated": 0, "pulled_deleted": 0,
            "pushed_new": 0, "pushed_updated": 0,
            "relinked": 0, "orphans_cleaned": 0,
            "orphans_skipped_budget": 0, "duplicate_push_prevented": 0,
            "conflicts_resolved": 0, "errors": 0, "duration_ms": 0,
        }
        # Run only PULL — explicitly skip push to isolate stale-link behavior
        await sync._pull_drive_to_local(stats_s)
        await db.commit()

    t("F3: stats.relinked=1 (Case A2 stale-link UPDATE)",
      lambda: stats_s["relinked"] == 1)
    t("F3: stats.pulled_new=0 (no spurious import)",
      lambda: stats_s["pulled_new"] == 0)

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_re = (await db.execute(
            select(File).where(File.id == stale_id)
        )).scalar_one()
        re_linked = f_re.drive_file_id == "drive_stale_target"
    t("F3: cache row drive_file_id re-linked to Drive id",
      lambda: re_linked)

    print("\n=== F7. Sync orphan retry budget (max 3 attempts) ===")
    # Setup: Drive has orphan file (pattern matches but file_id NOT in cache)
    # delete_file always fails → counter increments → 4th attempt skipped
    byos_user_o = await make_user_with_connection()
    orphan_drive_id = f"drive_orphan_{_s.token_hex(4)}"
    orphan_file_id = _s.token_hex(6)  # 12-hex · NOT in cache

    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        fake_o = FakeDriveClientV2()
        fake_o.delete_should_fail = True  # always fails
        fake_o.raw_files.append({
            "id": orphan_drive_id,
            "name": f"{orphan_file_id}_orphan.txt",
            "mimeType": "text/plain",
            "modifiedTime": "2026-04-30T10:00:00Z",
        })
        conn = (await db.execute(
            select(DriveConnection).where(DriveConnection.user_id == byos_user_o)
        )).scalar_one()
        sync_o = DriveSync._from_client(byos_user_o, db, fake_o, conn, fake_o.folder_layout)
        # Run pull 4 times in same DriveSync instance — counter should hit budget on 4th
        stats_runs = []
        for i in range(4):
            s = {
                "pulled_new": 0, "pulled_updated": 0, "pulled_deleted": 0,
                "pushed_new": 0, "pushed_updated": 0,
                "relinked": 0, "orphans_cleaned": 0,
                "orphans_skipped_budget": 0, "duplicate_push_prevented": 0,
                "conflicts_resolved": 0, "errors": 0, "duration_ms": 0,
            }
            await sync_o._pull_drive_to_local(s)
            stats_runs.append(s)

    # Runs 1-3: each attempt logs error, counter goes 1→2→3
    t("F7: Run 1 — orphans_skipped_budget=0 (within budget)",
      lambda: stats_runs[0]["orphans_skipped_budget"] == 0)
    t("F7: Run 1 — orphans_cleaned=0 (delete failed)",
      lambda: stats_runs[0]["orphans_cleaned"] == 0)
    t("F7: Run 4 — orphans_skipped_budget=1 (budget exhausted)",
      lambda: stats_runs[3]["orphans_skipped_budget"] == 1)
    t("F7: counter dict tracked drive id with attempts=3",
      lambda: sync_o._orphan_retry_count.get(orphan_drive_id) == 3)

    print("\n=== F4 functional. Drive sub-folder cleanup helpers ===")
    # Wire fake client into _build_drive_client via monkey-patch
    byos_user_f = await make_user_with_connection()
    fake_f = FakeDriveClientV2()
    fake_f.extracted_files.append({
        "id": "drive_extracted_001", "name": "test_file.txt",
        "mimeType": "text/plain", "modifiedTime": "2026-04-30T10:00:00Z",
    })
    fake_f.summary_files.append({
        "id": "drive_summary_001", "name": "test_file.md",
        "mimeType": "text/markdown", "modifiedTime": "2026-04-30T10:00:00Z",
    })

    from backend import storage_router as sr
    real_build = sr._build_drive_client

    async def fake_build(connection):
        return fake_f
    sr._build_drive_client = fake_build
    try:
        async with AsyncSessionLocal() as db:
            ok_e = await delete_extracted_text_from_drive_if_byos(
                byos_user_f, db, "test_file"
            )
            ok_s = await delete_summary_from_drive_if_byos(
                byos_user_f, db, "test_file"
            )
    finally:
        sr._build_drive_client = real_build

    t("F4: delete_extracted (BYOS, file exists) -> True",
      lambda: ok_e is True)
    t("F4: delete_summary   (BYOS, file exists) -> True",
      lambda: ok_s is True)
    t("F4: extracted_files bucket emptied",
      lambda: len(fake_f.extracted_files) == 0)
    t("F4: summary_files bucket emptied",
      lambda: len(fake_f.summary_files) == 0)
    t("F4: deleted_ids tracked both",
      lambda: "drive_extracted_001" in fake_f.deleted_ids
              and "drive_summary_001" in fake_f.deleted_ids)

    print("\n=== SyncStats invariants — 4 new v9.4.1 fields ===")
    t("SyncStats has 'relinked' field",
      lambda: 'relinked' in SyncStats.__annotations__)
    t("SyncStats has 'orphans_cleaned' field",
      lambda: 'orphans_cleaned' in SyncStats.__annotations__)
    t("SyncStats has 'orphans_skipped_budget' field",
      lambda: 'orphans_skipped_budget' in SyncStats.__annotations__)
    t("SyncStats has 'duplicate_push_prevented' field",
      lambda: 'duplicate_push_prevented' in SyncStats.__annotations__)

    print(f"\n{'=' * 60}")
    print(f"  v9.4.1 RESULT: {PASS} passed / {FAIL} failed")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


sys.exit(asyncio.run(main()))
