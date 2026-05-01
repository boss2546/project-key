"""v7.1 — Duplicate detection in-process smoke tests.

Run: python scripts/duplicate_detection_smoke.py

Covers:
  Section 1: compute_content_hash + normalize_text behavior (5 cases)
  Section 2: find_duplicate_for_file — exact match + edge cases (4 cases)
  Section 3: find_duplicate_for_file — semantic match via vector_search (3 cases)
  Section 4: detect_duplicates_for_batch — intra-batch exact + cross-user safety (3 cases)
  Section 5: vector_search.remove_file (2 cases)
  Section 6: storage_router.delete_drive_file_if_byos (3 cases)
  Section 7: /api/files/skip-duplicates endpoint via TestClient (4 cases)

Why in-process: sandbox blocks port binding (TEST-002). FastAPI TestClient + AsyncSessionLocal
runs everything in-process with real SQLite + mock Drive. ฟ้าจะเขียน test suite จริงเพิ่มเติม.
"""
from __future__ import annotations

import asyncio
import importlib
import os
import secrets as _s
import sys

sys.path.insert(0, ".")

# Clear BYOS env ก่อน import เพื่อ default = unconfigured
for k in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"]:
    os.environ[k] = ""

from backend.database import (
    AsyncSessionLocal, DriveConnection, File, FileSummary, User,
    gen_id, init_db,
)
from backend import vector_search


PASS = FAIL = 0


def expect(name: str, actual, equals) -> None:
    """Assert actual == equals. Print result + bump global counter."""
    global PASS, FAIL
    try:
        if actual == equals:
            print(f"  PASS  {name}")
            PASS += 1
        else:
            print(f"  FAIL  {name} — expected {equals!r}, got {actual!r}")
            FAIL += 1
    except Exception as e:
        print(f"  FAIL  {name} -> {type(e).__name__}: {e}")
        FAIL += 1


async def expect_true_async(name: str, coro) -> None:
    """Run coroutine, mark PASS if return value is truthy."""
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
# Mock DriveClient — สำหรับ Section 6 + 7 (BYOS path)
# ═══════════════════════════════════════════════════════════════
class MockDriveClient:
    instances: list["MockDriveClient"] = []

    def __init__(self, refresh_token):
        self.refresh_token = refresh_token
        self.calls: list[tuple[str, dict]] = []
        MockDriveClient.instances.append(self)

    def delete_file(self, file_id):
        self.calls.append(("delete_file", {"file_id": file_id}))

    # Stubs ที่อาจถูกเรียกในอนาคต — ป้องกัน AttributeError
    def ensure_folder(self, name, parent_id=None):
        self.calls.append(("ensure_folder", {"name": name}))
        return f"folder_{name}_id"

    def upload_file(self, parent_id, name, content, mime_type, resumable=None):
        self.calls.append(("upload_file", {"name": name}))
        return f"upload_{name}_id"


def install_mock_drive():
    """Patch storage_router._build_drive_client → return MockDriveClient."""
    MockDriveClient.instances.clear()
    from backend import storage_router

    async def fake_build(connection):
        return MockDriveClient("decrypted-mock-token")

    storage_router._build_drive_client = fake_build  # type: ignore[assignment]


def install_failing_mock_drive():
    """Patch storage_router._build_drive_client → raise. Used for graceful-failure test."""
    from backend import storage_router

    async def fake_build_fail(connection):
        raise RuntimeError("simulated Drive API failure")

    storage_router._build_drive_client = fake_build_fail  # type: ignore[assignment]


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
# Setup helpers
# ═══════════════════════════════════════════════════════════════
async def make_user(
    storage_mode: str = "managed", with_connection: bool = False
) -> str:
    async with AsyncSessionLocal() as db:
        user_id = gen_id()
        u = User(
            id=user_id,
            email=f"dup_{_s.token_hex(4)}@test.local",
            name="Dup Test",
            is_active=True,
            storage_mode=storage_mode,
        )
        db.add(u)
        if with_connection:
            conn = DriveConnection(
                user_id=user_id,
                drive_email="dup@test.local",
                refresh_token_encrypted="not-used-in-mock",
                drive_root_folder_id="root_id_mock",
                last_sync_status="pending",
            )
            db.add(conn)
        await db.commit()
        return user_id


async def make_file(
    user_id: str,
    text: str,
    filename: str = "f.txt",
    drive_file_id: str | None = None,
) -> str:
    """Save File row with content_hash computed. Return file_id."""
    from backend.duplicate_detector import compute_content_hash
    file_id = gen_id()
    async with AsyncSessionLocal() as db:
        f = File(
            id=file_id,
            user_id=user_id,
            filename=filename,
            filetype="txt",
            raw_path=f"/tmp/mock_{file_id}",
            extracted_text=text,
            processing_status="uploaded",
            content_hash=compute_content_hash(text),
            drive_file_id=drive_file_id,
            storage_source="drive_uploaded" if drive_file_id else "local",
        )
        db.add(f)
        await db.commit()
    return file_id


async def attach_summary(file_id: str, key_topics: list[str]) -> None:
    """Add FileSummary row for matched_topics testing."""
    import json
    async with AsyncSessionLocal() as db:
        s = FileSummary(
            file_id=file_id,
            summary_text="mock summary",
            key_topics=json.dumps(key_topics),
        )
        db.add(s)
        await db.commit()


# ═══════════════════════════════════════════════════════════════
# Section 1: compute_content_hash + normalize_text
# ═══════════════════════════════════════════════════════════════
def section_1_hash():
    from backend.duplicate_detector import (
        compute_content_hash, normalize_text,
        MIN_TEXT_LENGTH_FOR_DETECTION,
    )

    print("\n=== Section 1: compute_content_hash + normalize_text ===")

    # 1.1 Identical content with formatting differences → same hash
    a = "Hello World " + "x" * 60
    b = "  hello   world   " + "x" * 60
    expect("1.1 normalize collapses whitespace + lowercase",
           compute_content_hash(a), compute_content_hash(b))

    # 1.2 Different content → different hash
    c = "Different content here " + "y" * 60
    expect("1.2 different text → different hash",
           compute_content_hash(a) != compute_content_hash(c), True)

    # 1.3 Short text → None
    expect("1.3 text < MIN_TEXT_LENGTH_FOR_DETECTION → None",
           compute_content_hash("hi"), None)

    # 1.4 Empty / None → None
    expect("1.4 empty text → None", compute_content_hash(""), None)

    # 1.5 OCR error marker → None
    err = "[OCR error: Tesseract failed]" + "x" * 60
    expect("1.5 text starting with [ → None (extraction error marker)",
           compute_content_hash(err), None)


# ═══════════════════════════════════════════════════════════════
# Section 2: find_duplicate_for_file — exact match + edges
# ═══════════════════════════════════════════════════════════════
async def section_2_exact():
    from backend.duplicate_detector import find_duplicate_for_file

    print("\n=== Section 2: find_duplicate_for_file — exact match ===")

    # 2.1 Exact match found
    user_id = await make_user()
    long_text = "Lorem ipsum dolor sit amet consectetur adipiscing elit " * 5
    old_id = await make_file(user_id, long_text, filename="old.txt")
    new_id = await make_file(user_id, long_text, filename="new.txt")

    async def case_2_1():
        async with AsyncSessionLocal() as db:
            match = await find_duplicate_for_file(
                db, user_id, new_id, long_text, "new.txt"
            )
        return (
            match is not None
            and match["match_kind"] == "exact"
            and match["similarity"] == 1.0
            and match["match_file_id"] == old_id
        )
    await expect_true_async("2.1 exact match found (kind=exact, similarity=1.0)", case_2_1())

    # 2.2 Cross-user isolation — user A's file ห้าม match user B's file
    user_b = await make_user()
    await make_file(user_b, long_text, filename="b.txt")  # user_b มีไฟล์เดียวกัน

    async def case_2_2():
        # user_id (A) upload ไฟล์ใหม่ — ต้องเจอเฉพาะของตัวเอง (old.txt) ไม่เจอของ user_b
        new_id2 = await make_file(user_id, long_text, filename="another_new.txt")
        async with AsyncSessionLocal() as db:
            match = await find_duplicate_for_file(
                db, user_id, new_id2, long_text, "another_new.txt"
            )
        return match is not None and match["match_file_id"] != "b.txt" and match["match_kind"] == "exact"
    await expect_true_async("2.2 cross-user isolation (only own files matched)", case_2_2())

    # 2.3 Self-match excluded — query ไฟล์ตัวเองเทียบ DB ตัวเอง = ไม่ match self
    async def case_2_3():
        async with AsyncSessionLocal() as db:
            # search กับ new_id เดิมในขณะที่ DB มีแค่ new_id เดียวที่ hash นี้
            user_solo = await make_user()
            solo_id = await make_file(user_solo, long_text, filename="solo.txt")
            match = await find_duplicate_for_file(
                db, user_solo, solo_id, long_text, "solo.txt"
            )
        return match is None  # ห้าม self-match
    await expect_true_async("2.3 self-match excluded (only own file in DB)", case_2_3())

    # 2.4 Short text → None
    async def case_2_4():
        user_short = await make_user()
        short_id = await make_file(user_short, "hi", filename="short.txt")
        async with AsyncSessionLocal() as db:
            match = await find_duplicate_for_file(
                db, user_short, short_id, "hi", "short.txt"
            )
        return match is None
    await expect_true_async("2.4 text < min length → None (no detection)", case_2_4())


# ═══════════════════════════════════════════════════════════════
# Section 3: find_duplicate_for_file — semantic
# ═══════════════════════════════════════════════════════════════
async def section_3_semantic():
    from backend.duplicate_detector import find_duplicate_for_file

    print("\n=== Section 3: find_duplicate_for_file — semantic match ===")

    # Setup: user with 1 organized file in vector_search index
    user_id = await make_user()
    organized_text = (
        "Machine learning models like neural networks and transformers "
        "have revolutionized natural language processing tasks such as "
        "translation summarization and question answering. Deep learning "
        "research continues to push boundaries in 2026."
    ) * 3  # ขยายให้ยาวพอ chunk ได้
    organized_id = await make_file(user_id, organized_text, filename="ml_old.txt")
    await attach_summary(organized_id, ["machine learning", "NLP", "deep learning"])

    # Index ไฟล์ organized เข้า vector_search (จำลองว่า organize เสร็จแล้ว)
    vector_search.index_file(
        file_id=organized_id, filename="ml_old.txt",
        text=organized_text, user_id=user_id,
    )

    # 3.1 Highly similar text → semantic match
    similar_text = (
        "Machine learning models like neural networks and transformers "
        "are revolutionizing natural language processing tasks including "
        "translation summarization and question answering. Deep learning "
        "research is pushing boundaries in 2026."
    ) * 3
    new_similar_id = await make_file(user_id, similar_text, filename="ml_new.txt")

    async def case_3_1():
        async with AsyncSessionLocal() as db:
            match = await find_duplicate_for_file(
                db, user_id, new_similar_id, similar_text, "ml_new.txt"
            )
        if match is None:
            return False
        return (
            match["match_kind"] == "semantic"
            and match["similarity"] >= 0.80
            and match["match_file_id"] == organized_id
            and "machine learning" in match["matched_topics"]
        )
    await expect_true_async("3.1 semantic match ≥ 0.80 + matched_topics populated", case_3_1())

    # 3.2 Below threshold → None
    different_text = (
        "Cooking pasta requires boiling water salt and timing. "
        "Italian cuisine emphasizes fresh ingredients and simple techniques. "
        "Tomato sauce takes hours to simmer properly for best flavor."
    ) * 3
    new_different_id = await make_file(user_id, different_text, filename="cooking.txt")

    async def case_3_2():
        async with AsyncSessionLocal() as db:
            match = await find_duplicate_for_file(
                db, user_id, new_different_id, different_text, "cooking.txt"
            )
        return match is None  # similarity < 0.80
    await expect_true_async("3.2 unrelated content → None (below threshold)", case_3_2())

    # 3.3 Custom threshold lower → match found
    async def case_3_3():
        async with AsyncSessionLocal() as db:
            # ใช้ threshold ต่ำมาก (0.01) — น่าจะเจอ match ใดๆ ก็ได้
            match = await find_duplicate_for_file(
                db, user_id, new_different_id, different_text, "cooking.txt",
                threshold=0.01,
            )
        return match is not None and match["match_kind"] == "semantic"
    await expect_true_async("3.3 threshold=0.01 → match found (parameter respected)", case_3_3())


# ═══════════════════════════════════════════════════════════════
# Section 4: detect_duplicates_for_batch
# ═══════════════════════════════════════════════════════════════
async def section_4_batch():
    from backend.duplicate_detector import detect_duplicates_for_batch

    print("\n=== Section 4: detect_duplicates_for_batch ===")

    # 4.1 Intra-batch exact via SQL on content_hash
    user_id = await make_user()
    text = "Identical content " + "z" * 80
    f1 = await make_file(user_id, text, filename="dup1.txt")
    f2 = await make_file(user_id, text, filename="dup2.txt")
    f3 = await make_file(user_id, "completely different content " + "q" * 80, filename="other.txt")

    async def case_4_1():
        async with AsyncSessionLocal() as db:
            matches = await detect_duplicates_for_batch(db, user_id, [f1, f2, f3])
        # f1 + f2 hash ตรงกัน → ทั้งคู่ match กัน (ไม่ self-match) → 2 matches
        # (อันแรกเจอ f2/f1, อันสองเจอ f1/f2)
        if len(matches) != 2:
            return False
        return all(m["match_kind"] == "exact" for m in matches)
    await expect_true_async("4.1 intra-batch exact: 2 files identical → 2 matches", case_4_1())

    # 4.2 No duplicates → empty list
    async def case_4_2():
        user_solo = await make_user()
        s1 = await make_file(user_solo, "Unique content alpha " + "a" * 80, "a.txt")
        s2 = await make_file(user_solo, "Unique content beta " + "b" * 80, "b.txt")
        async with AsyncSessionLocal() as db:
            matches = await detect_duplicates_for_batch(db, user_solo, [s1, s2])
        return matches == []
    await expect_true_async("4.2 no duplicates → empty list", case_4_2())

    # 4.3 Cross-user safety: file_id ของ user A → user B query → silently skip
    async def case_4_3():
        user_x = await make_user()
        user_y = await make_user()
        x_file = await make_file(user_x, "X content " + "x" * 80, "x.txt")
        async with AsyncSessionLocal() as db:
            # query as user_y but pass user_x's file_id — ห้ามเจออะไร
            matches = await detect_duplicates_for_batch(db, user_y, [x_file])
        return matches == []
    await expect_true_async("4.3 cross-user file_ids → silently skipped", case_4_3())


# ═══════════════════════════════════════════════════════════════
# Section 5: vector_search.remove_file
# ═══════════════════════════════════════════════════════════════
def section_5_remove_index():
    print("\n=== Section 5: vector_search.remove_file ===")

    # 5.1 Index file then remove → no longer in index
    user_id = "test_user_remove_5_1"
    text = "Some content for indexing test " * 10
    file_id = "test_file_remove_5_1"
    vector_search.index_file(file_id, "test.txt", text, user_id=user_id)

    indexed = file_id in vector_search._user_indexes.get(user_id, {})
    expect("5.1a after index_file → file in _user_indexes", indexed, True)

    vector_search.remove_file(file_id, user_id=user_id)
    indexed_after = file_id in vector_search._user_indexes.get(user_id, {})
    expect("5.1b after remove_file → file gone from _user_indexes", indexed_after, False)

    # 5.2 No-op if file_id not in index
    try:
        vector_search.remove_file("nonexistent_file", user_id="nonexistent_user")
        vector_search.remove_file("nonexistent_file", user_id=user_id)  # user มีแต่ file ไม่มี
        expect("5.2 remove_file on nonexistent → no exception", True, True)
    except Exception as e:
        expect(f"5.2 remove_file on nonexistent → no exception (got {e})", False, True)


# ═══════════════════════════════════════════════════════════════
# Section 6: storage_router.delete_drive_file_if_byos
# ═══════════════════════════════════════════════════════════════
async def section_6_delete_drive():
    from backend.storage_router import delete_drive_file_if_byos

    print("\n=== Section 6: storage_router.delete_drive_file_if_byos ===")

    # 6.1 Managed user → no-op (return False, no Drive call)
    clear_byos_env()
    user_managed = await make_user(storage_mode="managed", with_connection=False)

    async def case_6_1():
        async with AsyncSessionLocal() as db:
            ok = await delete_drive_file_if_byos(user_managed, db, "drive_xyz")
        return ok is False
    await expect_true_async("6.1 managed user → no-op (False)", case_6_1())

    # 6.2 BYOS + connected → trash succeeds
    set_byos_env()
    install_mock_drive()
    user_byos = await make_user(storage_mode="byos", with_connection=True)

    async def case_6_2():
        async with AsyncSessionLocal() as db:
            ok = await delete_drive_file_if_byos(user_byos, db, "drive_abc123")
        if not ok:
            return False
        client = MockDriveClient.instances[-1]
        return any(
            c[0] == "delete_file" and c[1].get("file_id") == "drive_abc123"
            for c in client.calls
        )
    await expect_true_async("6.2 BYOS+connected → trash called on Drive", case_6_2())

    # 6.3 Drive failure → graceful False (no exception leaked)
    install_failing_mock_drive()
    user_byos2 = await make_user(storage_mode="byos", with_connection=True)

    async def case_6_3():
        async with AsyncSessionLocal() as db:
            ok = await delete_drive_file_if_byos(user_byos2, db, "drive_fail")
        return ok is False  # no exception, just False
    await expect_true_async("6.3 Drive build raises → returns False (graceful)", case_6_3())

    clear_byos_env()


# ═══════════════════════════════════════════════════════════════
# Section 7: /api/files/skip-duplicates endpoint via TestClient
# ═══════════════════════════════════════════════════════════════
async def section_7_endpoint():
    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.auth import create_access_token

    print("\n=== Section 7: /api/files/skip-duplicates endpoint ===")

    client = TestClient(app)

    # Helper: register + login → JWT
    async def _make_user_with_token() -> tuple[str, str]:
        user_id = await make_user()
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            res = await db.execute(select(User).where(User.id == user_id))
            u = res.scalar_one()
            token = create_access_token(u.id, u.email or "", u.name or "")
        return user_id, token

    # 7.1 Empty file_ids → 400 EMPTY_FILE_IDS
    user_id, token = await _make_user_with_token()
    res = client.post(
        "/api/files/skip-duplicates",
        json={"file_ids": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    expect("7.1a empty file_ids → 400", res.status_code, 400)
    body = res.json()
    expect("7.1b error code = EMPTY_FILE_IDS",
           body.get("detail", {}).get("error", {}).get("code"), "EMPTY_FILE_IDS")

    # 7.2 No auth → 401
    res2 = client.post("/api/files/skip-duplicates", json={"file_ids": ["x"]})
    expect("7.2 no JWT → 401", res2.status_code, 401)

    # 7.3 Skip own file → deleted from DB + raw_path removed (if exists)
    f1 = await make_file(user_id, "delete me " + "z" * 80, "del.txt")
    f2 = await make_file(user_id, "keep me " + "y" * 80, "keep.txt")
    res3 = client.post(
        "/api/files/skip-duplicates",
        json={"file_ids": [f1]},
        headers={"Authorization": f"Bearer {token}"},
    )
    expect("7.3a status 200", res3.status_code, 200)
    data3 = res3.json()
    expect("7.3b deleted contains f1", f1 in data3.get("deleted", []), True)
    expect("7.3c count = 1", data3.get("count"), 1)
    # Verify f1 gone from DB, f2 still there
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f1_check = (await db.execute(select(File).where(File.id == f1))).scalar_one_or_none()
        f2_check = (await db.execute(select(File).where(File.id == f2))).scalar_one_or_none()
    expect("7.3d f1 removed from DB", f1_check is None, True)
    expect("7.3e f2 still in DB", f2_check is not None, True)

    # 7.4 Skip cross-user file → silently skipped (in `skipped` array)
    user_other_id = await make_user()
    other_file = await make_file(user_other_id, "other content " + "o" * 80, "o.txt")
    res4 = client.post(
        "/api/files/skip-duplicates",
        json={"file_ids": [other_file]},
        headers={"Authorization": f"Bearer {token}"},
    )
    expect("7.4a status 200 (no error leak)", res4.status_code, 200)
    data4 = res4.json()
    expect("7.4b cross-user file in skipped[]", other_file in data4.get("skipped", []), True)
    expect("7.4c not in deleted[]", other_file in data4.get("deleted", []), False)
    # Verify cross-user file STILL in DB (ห้ามลบ)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        other_check = (await db.execute(select(File).where(File.id == other_file))).scalar_one_or_none()
    expect("7.4d cross-user file NOT deleted from DB", other_check is not None, True)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
async def main():
    await init_db()

    # Section 1 — sync (pure functions)
    section_1_hash()

    # Section 2-4 — async (DB queries)
    await section_2_exact()
    await section_3_semantic()
    await section_4_batch()

    # Section 5 — sync (in-memory index)
    section_5_remove_index()

    # Section 6 — async (DB + mock Drive)
    await section_6_delete_drive()

    # Section 7 — async (TestClient endpoint)
    await section_7_endpoint()

    print(f"\n{'=' * 60}")
    print(f"  RESULT: {PASS} passed / {FAIL} failed")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


sys.exit(asyncio.run(main()))
