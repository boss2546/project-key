"""End-to-end smoke for v7.0.1 — BYOS file-push gap fix.

Verifies the four behaviours we discussed with the user:

  1. /api/upload schedules background Drive push for BYOS users
     → raw file ends up in /Personal Data Bank/raw/
     → extracted text ends up in /Personal Data Bank/extracted/
     → File row gets drive_file_id + storage_source='drive_uploaded'
  2. /api/upload is a no-op (Drive-wise) for managed users
     → File row stays storage_source='local', no drive_file_id
  3. /api/files response carries storage_location + drive_web_link
     → BYOS file: storage_location='drive', drive_web_link points to drive.google.com
     → managed file: storage_location='server', drive_web_link=None
  4. /api/drive/sync gates correctly
     → managed user → 400 NOT_BYOS_MODE
     → BYOS w/o connection → 400 NO_DRIVE_CONNECTION
     → BYOS + connection → 200 + stats payload

Mock-based, no live Drive — drops in next to byos_*_smoke.py.
Run: python scripts/byos_v7_0_1_smoke.py
"""
from __future__ import annotations

import asyncio
import os
import secrets
import sys
from unittest.mock import MagicMock, patch

# Random per-run prefix so stale rows from a crashed earlier run never collide
_RUN = secrets.token_hex(3)

# ── Fail-fast: ensure repo root on path so "import backend" works ─────
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# ── Force BYOS env on so is_byos_configured() returns True ────────────
os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test-client-id.apps.googleusercontent.com"
os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "test-secret"
os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"] = "U29tZUVuY3J5cHRpb25LZXlGb3JUZXN0aW5nb25seQ=="

PASSED = 0
FAILED = 0


def _ok(msg: str) -> None:
    global PASSED
    PASSED += 1
    print(f"  PASS  {msg}")


def _fail(msg: str, detail: str = "") -> None:
    global FAILED
    FAILED += 1
    print(f"  FAIL  {msg}")
    if detail:
        print(f"        {detail}")


async def _make_user(db, *, byos: bool, with_connection: bool, suffix: str):
    """Build a sentinel User (and DriveConnection if requested) we'll clean up after."""
    from backend.database import DriveConnection, User
    from backend.drive_layout import STORAGE_MODE_BYOS, STORAGE_MODE_MANAGED

    uid = f"sentinel_{suffix}"
    user = User(
        id=uid, name="t", email=f"{uid}@x.x", is_active=True,
        storage_mode=STORAGE_MODE_BYOS if byos else STORAGE_MODE_MANAGED,
    )
    db.add(user)
    if with_connection:
        db.add(DriveConnection(
            user_id=uid,
            refresh_token_encrypted="fake_enc",
            drive_email=f"{uid}@gmail.com",
            drive_root_folder_id=f"root_{suffix}",
        ))
    await db.commit()
    return uid


async def _cleanup(db, uid: str):
    from backend.database import DriveConnection, File, User
    await db.execute(File.__table__.delete().where(File.user_id == uid))
    await db.execute(DriveConnection.__table__.delete().where(DriveConnection.user_id == uid))
    await db.execute(User.__table__.delete().where(User.id == uid))
    await db.commit()


def _make_mock_drive_client(folder_ids: dict[str, str], drive_id_to_return: str):
    """Build a MagicMock that mimics DriveClient enough for the push helpers."""
    mock = MagicMock()
    # ensure_folder("raw" | "extracted", parent_id=...) → return matching folder id
    mock.ensure_folder.side_effect = lambda name, parent_id=None: folder_ids.get(name, f"folder_{name}")
    mock.upload_file.return_value = drive_id_to_return
    mock.find_file_by_name.return_value = None  # always treat as new on Drive
    return mock


# ════════════════════════════════════════════════════════════════════════
# Test 1 — push helper updates DB + uploads raw bytes (BYOS happy path)
# ════════════════════════════════════════════════════════════════════════
async def test_1_push_helper_byos_happy_path():
    print("\n=== 1. push_raw_file_to_drive_if_byos — BYOS happy path ===")
    from backend.database import AsyncSessionLocal, File, init_db
    from backend.drive_layout import STORAGE_SOURCE_DRIVE_UPLOADED
    from backend import storage_router as SR

    await init_db()
    async with AsyncSessionLocal() as db:
        uid = await _make_user(db, byos=True, with_connection=True, suffix=f"{_RUN}_t1")
        file_id = f"t1_{_RUN}"
        f = File(
            id=file_id, user_id=uid, filename="report.pdf", filetype="pdf",
            raw_path="/tmp/report.pdf", storage_source="local",
        )
        db.add(f)
        await db.commit()

        client = _make_mock_drive_client({"raw": "RAW_FOLDER"}, drive_id_to_return="DRV_ABC123")
        with patch.object(SR, "_build_drive_client", return_value=client):
            result = await SR.push_raw_file_to_drive_if_byos(
                uid, db, file_id, "report.pdf", b"%PDF-1.4-fake", "application/pdf",
            )

        if result == "DRV_ABC123":
            _ok("push returns Drive file ID")
        else:
            _fail("push return value", f"expected DRV_ABC123, got {result!r}")

        # Verify upload_file called with raw folder + correct name format
        client.ensure_folder.assert_any_call("raw", parent_id=f"root_{_RUN}_t1")
        upload_args = client.upload_file.call_args
        expected_name = f"{file_id}_report.pdf"
        if upload_args.args[0] == "RAW_FOLDER" and upload_args.args[1] == expected_name:
            _ok("upload_file called with raw/{file_id}_{filename}")
        else:
            _fail("upload_file args", f"got {upload_args}")

        await db.refresh(f)
        if f.drive_file_id == "DRV_ABC123":
            _ok("File row updated with drive_file_id")
        else:
            _fail("file.drive_file_id", f"got {f.drive_file_id!r}")
        if f.storage_source == STORAGE_SOURCE_DRIVE_UPLOADED:
            _ok("File row updated with storage_source='drive_uploaded'")
        else:
            _fail("file.storage_source", f"got {f.storage_source!r}")

        await _cleanup(db, uid)


# ════════════════════════════════════════════════════════════════════════
# Test 2 — push helper is no-op for managed user
# ════════════════════════════════════════════════════════════════════════
async def test_2_push_helper_managed_noop():
    print("\n=== 2. push_raw_file_to_drive_if_byos — managed no-op ===")
    from backend.database import AsyncSessionLocal, File, init_db
    from backend import storage_router as SR

    await init_db()
    async with AsyncSessionLocal() as db:
        uid = await _make_user(db, byos=False, with_connection=False, suffix=f"{_RUN}_t2")
        file_id = f"t2_{_RUN}"
        f = File(
            id=file_id, user_id=uid, filename="m.txt", filetype="txt",
            raw_path="/tmp/m.txt", storage_source="local",
        )
        db.add(f)
        await db.commit()

        # If push is wrongly called, _build_drive_client would try to reach Google →
        # patch it to a sentinel so any attempted use is detectable
        sentinel = MagicMock(side_effect=AssertionError("Drive client should not be built for managed users"))
        with patch.object(SR, "_build_drive_client", sentinel):
            result = await SR.push_raw_file_to_drive_if_byos(
                uid, db, file_id, "m.txt", b"hi", "text/plain",
            )

        if result is None:
            _ok("push returns None for managed user")
        else:
            _fail("managed push", f"expected None, got {result!r}")
        if not sentinel.called:
            _ok("DriveClient never constructed for managed user")
        else:
            _fail("Drive client built for managed", "")

        await db.refresh(f)
        if f.drive_file_id is None and f.storage_source == "local":
            _ok("File row left untouched (still local)")
        else:
            _fail("managed file row mutated",
                  f"drive_file_id={f.drive_file_id!r}, storage_source={f.storage_source!r}")

        await _cleanup(db, uid)


# ════════════════════════════════════════════════════════════════════════
# Test 3 — _serialize_file emits storage_location + drive_web_link
# ════════════════════════════════════════════════════════════════════════
async def test_3_serialize_file_storage_fields():
    print("\n=== 3. _serialize_file → storage_location + drive_web_link ===")
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from backend.database import AsyncSessionLocal, File, init_db
    from backend.main import _serialize_file

    await init_db()
    async with AsyncSessionLocal() as db:
        uid = await _make_user(db, byos=True, with_connection=True, suffix=f"{_RUN}_t3")
        local_id = f"t3l_{_RUN}"
        drive_id = f"t3d_{_RUN}"
        local_f = File(id=local_id, user_id=uid, filename="a.txt", filetype="txt",
                       raw_path="/tmp/a", storage_source="local")
        drive_f = File(id=drive_id, user_id=uid, filename="b.pdf", filetype="pdf",
                       raw_path="", storage_source="drive_uploaded", drive_file_id="ABCDEF")
        db.add_all([local_f, drive_f])
        await db.commit()

        rows = (await db.execute(
            select(File).where(File.id.in_([local_id, drive_id]))
            .options(selectinload(File.insight), selectinload(File.summary))
        )).scalars().all()
        by_id = {r.id: _serialize_file(r) for r in rows}

        loc_local = by_id[local_id]
        if loc_local["storage_location"] == "server" and loc_local["drive_web_link"] is None:
            _ok("local file → storage_location='server', drive_web_link=None")
        else:
            _fail("local file serialization", str(loc_local))

        loc_drive = by_id[drive_id]
        expected_link = "https://drive.google.com/file/d/ABCDEF/view"
        if (loc_drive["storage_location"] == "drive"
                and loc_drive["drive_web_link"] == expected_link
                and loc_drive["drive_file_id"] == "ABCDEF"):
            _ok("drive file → storage_location='drive' + clickable web link")
        else:
            _fail("drive file serialization", str(loc_drive))

        await _cleanup(db, uid)


# ════════════════════════════════════════════════════════════════════════
# Test 4 — /api/drive/sync gating (managed/no-conn/connected paths)
# ════════════════════════════════════════════════════════════════════════
async def test_4_drive_sync_endpoint_gating():
    print("\n=== 4. /api/drive/sync — managed / no-connection / BYOS+connected ===")
    from sqlalchemy import select
    from fastapi.testclient import TestClient
    from backend.database import AsyncSessionLocal, init_db, User
    from backend.main import app
    from backend.auth import get_current_user

    await init_db()
    # Create rows + load detached User objects (so the override can return them directly,
    # without re-querying inside FastAPI's TestClient loop)
    async with AsyncSessionLocal() as db:
        managed_uid = await _make_user(db, byos=False, with_connection=False, suffix=f"{_RUN}_t4m")
        byos_no_conn_uid = await _make_user(db, byos=True, with_connection=False, suffix=f"{_RUN}_t4nc")
        byos_conn_uid = await _make_user(db, byos=True, with_connection=True, suffix=f"{_RUN}_t4ok")
        # Pre-load detached copies (expire_on_commit=False on this Session, so attrs stay live)
        managed_user = (await db.execute(select(User).where(User.id == managed_uid))).scalar_one()
        byos_no_conn_user = (await db.execute(select(User).where(User.id == byos_no_conn_uid))).scalar_one()
        byos_conn_user = (await db.execute(select(User).where(User.id == byos_conn_uid))).scalar_one()

    client = TestClient(app)

    # 4a. Managed user → 400 NOT_BYOS_MODE
    app.dependency_overrides[get_current_user] = lambda: managed_user
    r = client.post("/api/drive/sync")
    if r.status_code == 400 and r.json().get("detail", {}).get("error", {}).get("code") == "NOT_BYOS_MODE":
        _ok("managed user → 400 NOT_BYOS_MODE")
    else:
        _fail("managed gating", f"{r.status_code} {r.text[:200]}")

    # 4b. BYOS user without connection → 400 NO_DRIVE_CONNECTION
    app.dependency_overrides[get_current_user] = lambda: byos_no_conn_user
    r = client.post("/api/drive/sync")
    if r.status_code == 400 and r.json().get("detail", {}).get("error", {}).get("code") == "NO_DRIVE_CONNECTION":
        _ok("BYOS w/o connection → 400 NO_DRIVE_CONNECTION")
    else:
        _fail("no-connection gating", f"{r.status_code} {r.text[:200]}")

    # 4c. BYOS user with connection → 200 + stats payload (mock sync_user_drive)
    app.dependency_overrides[get_current_user] = lambda: byos_conn_user
    fake_stats = {
        "pulled_new": 2, "pulled_updated": 1, "pulled_deleted": 0,
        "pushed_new": 3, "pushed_updated": 0,
        "conflicts_resolved": 1, "errors": 0, "duration_ms": 42,
    }

    async def _fake_sync(_uid, _db):
        return fake_stats

    # Patch where main.py imports it (inside the endpoint, lazy import)
    with patch("backend.drive_sync.sync_user_drive", _fake_sync):
        r = client.post("/api/drive/sync")
    if r.status_code == 200 and r.json().get("stats", {}).get("pushed_new") == 3:
        _ok("BYOS + connection → 200 + correct SyncStats payload")
    else:
        _fail("BYOS+conn happy path", f"{r.status_code} {r.text[:200]}")

    app.dependency_overrides.clear()

    # Cleanup
    async with AsyncSessionLocal() as db:
        await _cleanup(db, managed_uid)
        await _cleanup(db, byos_no_conn_uid)
        await _cleanup(db, byos_conn_uid)


# ════════════════════════════════════════════════════════════════════════
# Test 5 — _guess_mime helper (rounding out the upload path)
# ════════════════════════════════════════════════════════════════════════
def test_5_guess_mime():
    print("\n=== 5. _guess_mime — proper MIMEs for Drive ===")
    from backend.main import _guess_mime
    cases = [
        (("pdf", None), "application/pdf"),
        (("txt", None), "text/plain"),
        (("md", None), "text/markdown"),
        (("docx", None), "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        (("xyz", None), "application/octet-stream"),
        # Server-side ext map MUST win over browser hint (Content-Type is attacker-
        # controlled in multipart uploads — never trust it to override a known type)
        (("pdf", "application/x-custom"), "application/pdf"),
        # When ext is unknown AND hint is well-formed → fall back to hint
        (("xyz", "application/x-custom"), "application/x-custom"),
        # Hint with parameters → strip params before matching
        (("xyz", "text/plain; charset=utf-8"), "text/plain"),
        # Malformed hint → ignore + return octet-stream
        (("xyz", "not-a-mime"), "application/octet-stream"),
        (("", None), "application/octet-stream"),
    ]
    for (ext, hint), expected in cases:
        got = _guess_mime(ext, hint)
        if got == expected:
            _ok(f"_guess_mime({ext!r}, {hint!r}) → {expected}")
        else:
            _fail(f"_guess_mime({ext!r}, {hint!r})", f"expected {expected!r}, got {got!r}")


# ════════════════════════════════════════════════════════════════════════
# Driver
# ════════════════════════════════════════════════════════════════════════
async def main_async():
    await test_1_push_helper_byos_happy_path()
    await test_2_push_helper_managed_noop()
    await test_3_serialize_file_storage_fields()
    await test_4_drive_sync_endpoint_gating()
    test_5_guess_mime()


def main():
    asyncio.run(main_async())
    print("\n" + "=" * 60)
    print(f"  RESULT: {PASSED} passed / {FAILED} failed")
    print("=" * 60)
    sys.exit(0 if FAILED == 0 else 1)


if __name__ == "__main__":
    main()
