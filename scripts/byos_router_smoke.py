"""BYOS v7.0 — storage_router.py mock smoke test.

Run: python scripts/byos_router_smoke.py

Verifies:
  1. Managed user -> all push helpers no-op (return False)
  2. BYOS but no env vars configured -> no-op
  3. BYOS user without DriveConnection -> no-op
  4. BYOS user fully set up -> push succeeds (mock DriveClient called)
  5. Drive failure during push -> no exception raised, return False
  6. fetch_file_bytes routes correctly: local path vs Drive download
  7. Wired into update_profile -> profile push fires

No real Google API calls; uses monkey-patched DriveClient inside storage_router.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import secrets as _s
import sys
import tempfile

sys.path.insert(0, ".")

# Clear env so default = managed/not-configured (set "" so dotenv doesn't repopulate)
for k in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"]:
    os.environ[k] = ""

from backend.database import (
    AsyncSessionLocal, DriveConnection, File, User, gen_id, init_db,
)


PASS = FAIL = 0


async def expect_true(name, coro):
    """Run coroutine, mark PASS if it returns truthy."""
    global PASS, FAIL
    try:
        ok = await coro
        if ok:
            print(f"  PASS  {name}")
            PASS += 1
        else:
            print(f"  FAIL  {name}")
            FAIL += 1
    except Exception as e:
        print(f"  FAIL  {name} -> {type(e).__name__}: {e}")
        FAIL += 1


# ═══════════════════════════════════════════════════════════════
# Mock DriveClient — captures calls
# ═══════════════════════════════════════════════════════════════
class MockDriveClient:
    instances: list["MockDriveClient"] = []

    def __init__(self, refresh_token):
        self.refresh_token = refresh_token
        self.calls: list[tuple[str, dict]] = []
        MockDriveClient.instances.append(self)

    def ensure_folder(self, name, parent_id=None):
        self.calls.append(("ensure_folder", {"name": name, "parent_id": parent_id}))
        return f"folder_{name}_id"

    def ensure_pdb_folder_structure(self):
        self.calls.append(("ensure_pdb_folder_structure", {}))
        return {
            "_root": "root_id",
            "raw": "raw_id", "extracted": "extracted_id",
            "summaries": "summaries_id", "personal": "personal_id",
            "data": "data_id", "_meta": "meta_id", "_backups": "backups_id",
        }

    def upsert_json_file(self, parent_id, name, data):
        self.calls.append(("upsert_json_file", {"parent_id": parent_id, "name": name}))
        return f"json_{name}_id"

    def find_file_by_name(self, name, parent_id=None):
        self.calls.append(("find_file_by_name", {"name": name, "parent_id": parent_id}))
        return None

    def upload_file(self, parent_id, name, content, mime_type, resumable=None):
        self.calls.append(("upload_file", {"parent_id": parent_id, "name": name}))
        return f"upload_{name}_id"

    def update_file_content(self, file_id, content, mime_type):
        self.calls.append(("update_file_content", {"file_id": file_id}))

    def download_file(self, file_id, mime_type_hint=None):
        self.calls.append(("download_file", {"file_id": file_id}))
        return b"DRIVE_BYTES_FOR_" + file_id.encode()


def install_mock():
    MockDriveClient.instances.clear()
    from backend import storage_router

    async def fake_build(connection):
        return MockDriveClient("decrypted-mock-token")

    storage_router._build_drive_client = fake_build  # type: ignore[assignment]


def install_failing_mock():
    from backend import storage_router

    async def fake_build_fail(connection):
        raise RuntimeError("simulated Drive API failure")

    storage_router._build_drive_client = fake_build_fail  # type: ignore[assignment]


# ═══════════════════════════════════════════════════════════════
# Setup helpers
# ═══════════════════════════════════════════════════════════════
async def make_user(storage_mode: str = "managed", with_connection: bool = False) -> str:
    async with AsyncSessionLocal() as db:
        user_id = gen_id()
        u = User(
            id=user_id,
            email=f"router_{_s.token_hex(4)}@test.local",
            name="Router Test",
            is_active=True,
            storage_mode=storage_mode,
        )
        db.add(u)
        if with_connection:
            conn = DriveConnection(
                user_id=user_id,
                drive_email="router@test.local",
                refresh_token_encrypted="not-used-in-mock",
                drive_root_folder_id="root_id_mock",
                last_sync_status="pending",
            )
            db.add(conn)
        await db.commit()
        return user_id


def set_byos_env():
    from cryptography.fernet import Fernet
    os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test_id"
    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "test_secret"
    os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    from backend import config as _cfg
    importlib.reload(_cfg)


def clear_byos_env():
    for k in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"]:
        os.environ[k] = ""
    from backend import config as _cfg
    importlib.reload(_cfg)


# ═══════════════════════════════════════════════════════════════
# Async test functions (called directly via expect_true)
# ═══════════════════════════════════════════════════════════════
async def case1_unconfigured():
    clear_byos_env()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import push_profile_to_drive_if_byos
        result = await push_profile_to_drive_if_byos(user_id, db, {"identity_summary": "x"})
    return result is False


async def case2_managed_user():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="managed", with_connection=False)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import push_profile_to_drive_if_byos
        result = await push_profile_to_drive_if_byos(user_id, db, {"identity_summary": "x"})
    ok = result is False and len(MockDriveClient.instances) == 0
    clear_byos_env()
    return ok


async def case3_no_connection():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=False)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import push_profile_to_drive_if_byos
        result = await push_profile_to_drive_if_byos(user_id, db, {"identity_summary": "x"})
    ok = result is False and len(MockDriveClient.instances) == 0
    clear_byos_env()
    return ok


async def case4_push_succeeds():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import push_profile_to_drive_if_byos
        result = await push_profile_to_drive_if_byos(
            user_id, db, {"identity_summary": "test", "mbti": {"type": "INTJ"}}
        )
    clear_byos_env()
    if not result:
        return False
    client = MockDriveClient.instances[-1]
    upserts = [c for c in client.calls if c[0] == "upsert_json_file"]
    return len(upserts) == 1 and upserts[0][1]["name"] == "profile.json"


async def case5_drive_failure_graceful():
    set_byos_env()
    install_failing_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import push_profile_to_drive_if_byos
        result = await push_profile_to_drive_if_byos(user_id, db, {"x": 1})
    clear_byos_env()
    return result is False  # no exception, just False


async def case6_helper(push_fn_name, expected_filename, payload):
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend import storage_router
        push_fn = getattr(storage_router, push_fn_name)
        await push_fn(user_id, db, payload)
    clear_byos_env()
    client = MockDriveClient.instances[-1]
    for kind in ("upsert_json_file", "upload_file"):
        for call in client.calls:
            if call[0] == kind and call[1].get("name") == expected_filename:
                return True
    return False


async def case7a_summary():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import push_summary_to_drive_if_byos
        result = await push_summary_to_drive_if_byos(user_id, db, "abc123def456", "# Sum")
    clear_byos_env()
    if not result:
        return False
    client = MockDriveClient.instances[-1]
    return any(c[0] == "upload_file" and c[1]["name"] == "abc123def456.md" for c in client.calls)


async def case7b_extracted_text():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import push_extracted_text_to_drive_if_byos
        result = await push_extracted_text_to_drive_if_byos(user_id, db, "abc123def456", "text")
    clear_byos_env()
    if not result:
        return False
    client = MockDriveClient.instances[-1]
    return any(c[0] == "upload_file" and c[1]["name"] == "abc123def456.txt" for c in client.calls)


async def case8a_fetch_local():
    clear_byos_env()
    tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False)
    tmp.write(b"local file bytes here")
    tmp.close()
    user_id = await make_user(storage_mode="managed", with_connection=False)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import fetch_file_bytes
        f = File(
            id=gen_id(), user_id=user_id, filename="local.txt", filetype="text/plain",
            raw_path=tmp.name, storage_source="local",
        )
        db.add(f)
        await db.commit()
        await db.refresh(f)
        data = await fetch_file_bytes(f, db)
    os.unlink(tmp.name)
    return data == b"local file bytes here"


async def case8b_fetch_drive():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import fetch_file_bytes
        f = File(
            id=gen_id(), user_id=user_id, filename="drive.pdf", filetype="application/pdf",
            raw_path="", drive_file_id="drive_xyz", storage_source="drive_uploaded",
        )
        db.add(f)
        await db.commit()
        await db.refresh(f)
        data = await fetch_file_bytes(f, db)
    clear_byos_env()
    return data == b"DRIVE_BYTES_FOR_drive_xyz"


async def case9_init_layout():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.storage_router import init_drive_folder_layout
        layout = await init_drive_folder_layout(user_id, db)
    clear_byos_env()
    return layout is not None and "_root" in layout and len(layout) == 8


async def case10a_wired_byos():
    set_byos_env()
    install_mock()
    user_id = await make_user(storage_mode="byos", with_connection=True)
    async with AsyncSessionLocal() as db:
        from backend.profile import update_profile
        await update_profile(db, user_id, {"identity_summary": "wired"})
    clear_byos_env()
    for client in MockDriveClient.instances:
        for call in client.calls:
            if call[0] == "upsert_json_file" and call[1].get("name") == "profile.json":
                return True
    return False


async def case10b_wired_managed_no_call():
    set_byos_env()
    install_mock()
    MockDriveClient.instances.clear()
    user_id = await make_user(storage_mode="managed", with_connection=False)
    async with AsyncSessionLocal() as db:
        from backend.profile import update_profile
        await update_profile(db, user_id, {"identity_summary": "managed"})
    clear_byos_env()
    return len(MockDriveClient.instances) == 0


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
async def main():
    await init_db()

    print("=== 1. No-op when BYOS feature not configured ===")
    await expect_true("Push when BYOS env vars empty -> False (no-op)", case1_unconfigured())

    print("\n=== 2. No-op when user is in managed mode ===")
    await expect_true("Push when user.storage_mode=managed -> False, no Drive call", case2_managed_user())

    print("\n=== 3. No-op when BYOS user has no DriveConnection ===")
    await expect_true("Push when byos but no DriveConnection -> False, no Drive call", case3_no_connection())

    print("\n=== 4. Push succeeds for byos+connected user ===")
    await expect_true("Push for byos+connected -> True + upsert profile.json called", case4_push_succeeds())

    print("\n=== 5. Drive failure -> graceful False ===")
    await expect_true("Drive build fails -> push returns False (no exception)", case5_drive_failure_graceful())

    print("\n=== 6. All push helpers route to correct sub-folders ===")
    await expect_true("push_graph_to_drive_if_byos -> graph.json",
                      case6_helper("push_graph_to_drive_if_byos", "graph.json", {"nodes": [], "edges": []}))
    await expect_true("push_clusters_to_drive_if_byos -> clusters.json",
                      case6_helper("push_clusters_to_drive_if_byos", "clusters.json", [{"id": "c1"}]))
    await expect_true("push_relations_to_drive_if_byos -> relations.json",
                      case6_helper("push_relations_to_drive_if_byos", "relations.json", {"backlinks": []}))
    await expect_true("push_contexts_to_drive_if_byos -> contexts.json",
                      case6_helper("push_contexts_to_drive_if_byos", "contexts.json", []))

    print("\n=== 7. Per-file pushes (summary + extracted text) ===")
    await expect_true("push_summary_to_drive_if_byos -> upload {file_id}.md", case7a_summary())
    await expect_true("push_extracted_text_to_drive_if_byos -> upload {file_id}.txt", case7b_extracted_text())

    print("\n=== 8. fetch_file_bytes routing ===")
    await expect_true("fetch_file_bytes(local) -> reads raw_path from disk", case8a_fetch_local())
    await expect_true("fetch_file_bytes(drive) -> downloads via DriveClient", case8b_fetch_drive())

    print("\n=== 9. init_drive_folder_layout ===")
    await expect_true("init_drive_folder_layout -> 8 folder IDs (root + 7 subs)", case9_init_layout())

    print("\n=== 10. Wired into update_profile() ===")
    await expect_true("update_profile() byos -> auto-pushes profile.json", case10a_wired_byos())
    await expect_true("update_profile() managed -> no Drive call (no regression)", case10b_wired_managed_no_call())

    print(f"\n{'=' * 60}")
    print(f"  RESULT: {PASS} passed / {FAIL} failed")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


sys.exit(asyncio.run(main()))
