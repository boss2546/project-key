"""v7.1 — End-to-end verification (ad-hoc deep test สำหรับเขียวก่อนส่งฟ้า).

Run: python scripts/dedupe_e2e_verify.py

Coverage ที่ smoke test ของจริง (duplicate_detection_smoke.py) ยังไม่ครอบคลุม:
  Section A: Schema verification — content_hash + indexes มีจริงใน DB
  Section B: APP_VERSION runtime visibility (Swagger/MCP info)
  Section C: End-to-end /api/upload via TestClient — multipart + duplicates_found field
  Section D: Cascade FK delete — file → summary/insight/cluster_map ลบตาม
  Section E: i18n parity — TH + EN ครบทุก dup.* key
  Section F: HTML modal structure check — element + button IDs ครบ
  Section G: Stress — batch ใหญ่ (10 ไฟล์) ทำงานได้ + performance
"""
from __future__ import annotations

import asyncio
import io
import os
import re
import sys
import time

sys.path.insert(0, ".")

# Clear BYOS env ก่อน import
for k in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"]:
    os.environ[k] = ""

from backend.database import (
    AsyncSessionLocal, File, FileSummary, FileInsight, FileClusterMap,
    Cluster, User, gen_id, init_db, engine,
)
from backend import vector_search


PASS = FAIL = 0


def expect(name: str, actual, equals) -> None:
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


def expect_true(name: str, condition: bool) -> None:
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name}")
        FAIL += 1


# ═══════════════════════════════════════════════════════════════
# Section A: Schema verification (raw SQLite query via aiosqlite)
# ═══════════════════════════════════════════════════════════════
async def section_a_schema():
    print("\n=== Section A: Schema verification ===")

    import aiosqlite
    from backend.config import DATABASE_URL
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")

    async with aiosqlite.connect(db_path) as db:
        # A.1: content_hash column exists
        cursor = await db.execute("PRAGMA table_info(files)")
        cols = {row[1]: row[2] for row in await cursor.fetchall()}
        expect_true("A.1 files.content_hash column exists", "content_hash" in cols)
        expect("A.2 content_hash type = TEXT", cols.get("content_hash"), "TEXT")

        # A.3: idx_files_content_hash exists
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='files'"
        )
        indexes = {row[0] for row in await cursor.fetchall()}
        expect_true("A.3 idx_files_content_hash created", "idx_files_content_hash" in indexes)

        # A.4: Migration idempotent — re-run init_db ไม่ break
        await init_db()
        cursor = await db.execute("PRAGMA table_info(files)")
        cols2 = {row[1]: row[2] for row in await cursor.fetchall()}
        expect_true("A.4 migration idempotent (re-run safe)", "content_hash" in cols2)


# ═══════════════════════════════════════════════════════════════
# Section B: APP_VERSION runtime visibility
# ═══════════════════════════════════════════════════════════════
async def section_b_version():
    print("\n=== Section B: APP_VERSION runtime visibility ===")

    from backend.config import APP_VERSION
    expect("B.1 config.APP_VERSION = '7.1.0'", APP_VERSION, "7.1.0")

    # B.2: FastAPI app instance reads from APP_VERSION
    from backend.main import app
    expect("B.2 FastAPI app.version = '7.1.0'", app.version, "7.1.0")

    # B.3: index.html shows v7.1.0 (no leftover 7.0.1)
    with open("legacy-frontend/index.html", encoding="utf-8") as f:
        html = f.read()
    expect_true("B.3a index.html contains 'v7.1.0'", "v7.1.0" in html)
    expect_true("B.3b index.html no leftover 'v7.0.1'", "v7.0.1" not in html)
    expect_true("B.3c index.html no leftover 'v=7.0.1' (cache buster)", "v=7.0.1" not in html)


# ═══════════════════════════════════════════════════════════════
# Section C: End-to-end /api/upload via TestClient
# ═══════════════════════════════════════════════════════════════
async def section_c_upload_e2e():
    print("\n=== Section C: End-to-end /api/upload + skip flow ===")

    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.auth import create_access_token

    client = TestClient(app)

    # Setup user with token
    async def _make_user():
        user_id = gen_id()
        async with AsyncSessionLocal() as db:
            u = User(
                id=user_id, email=f"e2e_{user_id[:6]}@test.local",
                name="E2E Test", is_active=True, plan="free",
                subscription_status="free", storage_mode="managed",
            )
            db.add(u)
            await db.commit()
        token = create_access_token(user_id, f"e2e_{user_id[:6]}@test.local", "E2E Test")
        return user_id, token

    user_id, token = await _make_user()
    headers = {"Authorization": f"Bearer {token}"}

    # ── C.1: Upload 1 file → no duplicates_found ────
    file_content = b"This is unique content for E2E test alpha. " * 5
    res = client.post(
        "/api/upload",
        files=[("files", ("alpha.txt", io.BytesIO(file_content), "text/plain"))],
        headers=headers,
    )
    expect("C.1a status 200", res.status_code, 200)
    data = res.json()
    expect_true("C.1b 'duplicates_found' field exists", "duplicates_found" in data)
    expect("C.1c no duplicates", len(data.get("duplicates_found", [])), 0)
    expect("C.1d 1 file uploaded", data.get("count"), 1)
    first_file_id = data["uploaded"][0]["id"]

    # Verify content_hash actually populated in DB (not NULL)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f = (await db.execute(select(File).where(File.id == first_file_id))).scalar_one()
    expect_true("C.1e content_hash populated in DB (not NULL)", f.content_hash is not None)
    expect("C.1f content_hash is 64-char hex", len(f.content_hash or ""), 64)

    # ── C.2: Upload identical content (different filename) → 1 exact match ────
    res2 = client.post(
        "/api/upload",
        files=[("files", ("alpha_copy.txt", io.BytesIO(file_content), "text/plain"))],
        headers=headers,
    )
    expect("C.2a status 200", res2.status_code, 200)
    data2 = res2.json()
    dups = data2.get("duplicates_found", [])
    expect("C.2b duplicates_found has 1 match", len(dups), 1)
    if dups:
        expect("C.2c match_kind = 'exact'", dups[0].get("match_kind"), "exact")
        expect("C.2d similarity = 1.0", dups[0].get("similarity"), 1.0)
        expect("C.2e match_filename = 'alpha.txt'", dups[0].get("match_filename"), "alpha.txt")

    second_file_id = data2["uploaded"][0]["id"]

    # ── C.3: detect_duplicates=false → skip detection ────
    res3 = client.post(
        "/api/upload?detect_duplicates=false",
        files=[("files", ("alpha_no_check.txt", io.BytesIO(file_content), "text/plain"))],
        headers=headers,
    )
    expect("C.3a status 200", res3.status_code, 200)
    data3 = res3.json()
    expect("C.3b detect_duplicates=false → empty duplicates_found",
           len(data3.get("duplicates_found", [])), 0)

    third_file_id = data3["uploaded"][0]["id"]

    # ── C.4: Skip-duplicates → file removed ────
    res4 = client.post(
        "/api/files/skip-duplicates",
        json={"file_ids": [second_file_id]},
        headers=headers,
    )
    expect("C.4a status 200", res4.status_code, 200)
    expect("C.4b file in deleted[]", second_file_id in res4.json().get("deleted", []), True)

    # Verify gone from DB + raw_path removed (was created at /tmp/uploads/...)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_check = (await db.execute(select(File).where(File.id == second_file_id))).scalar_one_or_none()
    expect_true("C.4c file gone from DB", f_check is None)

    # First file still exists (didn't accidentally delete neighbor)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f1_check = (await db.execute(select(File).where(File.id == first_file_id))).scalar_one_or_none()
    expect_true("C.4d original file still in DB", f1_check is not None)

    # ── C.5: Intra-batch — 3 identical files in same upload ────
    user_id5, token5 = await _make_user()
    same_content = b"Identical content for intra-batch test " * 10
    res5 = client.post(
        "/api/upload",
        files=[
            ("files", ("dup1.txt", io.BytesIO(same_content), "text/plain")),
            ("files", ("dup2.txt", io.BytesIO(same_content), "text/plain")),
            ("files", ("dup3.txt", io.BytesIO(same_content), "text/plain")),
        ],
        headers={"Authorization": f"Bearer {token5}"},
    )
    expect("C.5a status 200", res5.status_code, 200)
    data5 = res5.json()
    expect("C.5b 3 files uploaded", data5.get("count"), 3)
    intra_dups = data5.get("duplicates_found", [])
    # ทุกไฟล์ที่ 2-3 จะมี content_hash เดียวกับไฟล์ที่ 1 → exact match ผ่าน SQL
    # → ผลคือ 2 หรือ 3 matches (ขึ้นกับว่า DB เห็นไฟล์ก่อนหรือหลังตัวเอง)
    # อย่างน้อยต้องมี ≥ 2 matches (ไฟล์ที่ 2 + ไฟล์ที่ 3 เจอ ไฟล์ที่ 1)
    expect_true(f"C.5c intra-batch matches ≥ 2 (got {len(intra_dups)})",
                len(intra_dups) >= 2)
    if intra_dups:
        all_exact = all(d["match_kind"] == "exact" for d in intra_dups)
        expect_true("C.5d all intra-batch matches are exact", all_exact)


# ═══════════════════════════════════════════════════════════════
# Section D: Cascade FK delete (skip-duplicates flow)
# ═══════════════════════════════════════════════════════════════
async def section_d_cascade():
    print("\n=== Section D: Cascade FK delete via skip-duplicates ===")

    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.auth import create_access_token

    client = TestClient(app)

    # Setup user + file with insight + summary + cluster_map
    user_id = gen_id()
    file_id = gen_id()
    cluster_id = gen_id()

    async with AsyncSessionLocal() as db:
        u = User(id=user_id, email=f"casc_{user_id[:6]}@t.local",
                name="Cascade", is_active=True, plan="free",
                subscription_status="free", storage_mode="managed")
        db.add(u)

        # Cluster
        cl = Cluster(id=cluster_id, user_id=user_id, title="Test cluster")
        db.add(cl)

        # File
        from backend.duplicate_detector import compute_content_hash
        text = "Cascade test content " + "x" * 100
        f = File(
            id=file_id, user_id=user_id, filename="cascade.txt",
            filetype="txt", raw_path=f"/tmp/cascade_{file_id}",
            extracted_text=text, processing_status="ready",
            content_hash=compute_content_hash(text),
        )
        db.add(f)
        await db.flush()

        # Summary + Insight + ClusterMap
        s = FileSummary(file_id=file_id, summary_text="sum", key_topics='["t1"]')
        ins = FileInsight(file_id=file_id, importance_score=80)
        cm = FileClusterMap(file_id=file_id, cluster_id=cluster_id, relevance_score=0.9)
        db.add_all([s, ins, cm])
        await db.commit()

    # Verify all 4 rows exist before delete
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_pre = (await db.execute(select(File).where(File.id == file_id))).scalar_one_or_none()
        s_pre = (await db.execute(select(FileSummary).where(FileSummary.file_id == file_id))).scalar_one_or_none()
        ins_pre = (await db.execute(select(FileInsight).where(FileInsight.file_id == file_id))).scalar_one_or_none()
        cm_pre = (await db.execute(select(FileClusterMap).where(FileClusterMap.file_id == file_id))).scalar_one_or_none()
    expect_true("D.0a setup: File row exists", f_pre is not None)
    expect_true("D.0b setup: FileSummary row exists", s_pre is not None)
    expect_true("D.0c setup: FileInsight row exists", ins_pre is not None)
    expect_true("D.0d setup: FileClusterMap row exists", cm_pre is not None)

    # Call skip-duplicates
    token = create_access_token(user_id, f"casc_{user_id[:6]}@t.local", "Cascade")
    res = client.post(
        "/api/files/skip-duplicates",
        json={"file_ids": [file_id]},
        headers={"Authorization": f"Bearer {token}"},
    )
    expect("D.1 skip-duplicates status 200", res.status_code, 200)

    # Verify cascade — File + dependent rows ทั้งหมดต้องหาย
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f_post = (await db.execute(select(File).where(File.id == file_id))).scalar_one_or_none()
        s_post = (await db.execute(select(FileSummary).where(FileSummary.file_id == file_id))).scalar_one_or_none()
        ins_post = (await db.execute(select(FileInsight).where(FileInsight.file_id == file_id))).scalar_one_or_none()
        cm_post = (await db.execute(select(FileClusterMap).where(FileClusterMap.file_id == file_id))).scalar_one_or_none()
    expect_true("D.2a File row removed", f_post is None)
    expect_true("D.2b FileSummary cascaded (removed)", s_post is None)
    expect_true("D.2c FileInsight cascaded (removed)", ins_post is None)
    expect_true("D.2d FileClusterMap cascaded (removed)", cm_post is None)

    # Cluster row itself ต้อง KEEP (cascade ไป cluster_map ไม่ใช่ cluster)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        cl_post = (await db.execute(select(Cluster).where(Cluster.id == cluster_id))).scalar_one_or_none()
    expect_true("D.3 Cluster row preserved (cascade only ClusterMap)", cl_post is not None)


# ═══════════════════════════════════════════════════════════════
# Section E: i18n parity check (TH + EN ทุก dup.* key)
# ═══════════════════════════════════════════════════════════════
def section_e_i18n():
    print("\n=== Section E: i18n parity (TH + EN) ===")

    with open("legacy-frontend/app.js", encoding="utf-8") as f:
        js = f.read()

    # หา block ของ th: { ... } และ en: { ... }
    # ใช้ regex หา dup.* keys ใน TH section vs EN section
    # โครงสร้าง: const I18N = { th: { ... }, en: { ... } };

    # Split โดยหา "th: {" และ "en: {"
    th_start = js.find(" th: {")
    en_start = js.find(" en: {", th_start)
    en_end = js.find("\n};", en_start)

    th_block = js[th_start:en_start]
    en_block = js[en_start:en_end]

    # หา dup.* keys ใน 2 block
    dup_re = re.compile(r"'(dup\.[a-zA-Z]+)'\s*:")
    th_keys = set(dup_re.findall(th_block))
    en_keys = set(dup_re.findall(en_block))

    expect_true(f"E.1 TH dup.* keys ≥ 5 (got {len(th_keys)})", len(th_keys) >= 5)
    expect_true(f"E.2 EN dup.* keys ≥ 5 (got {len(en_keys)})", len(en_keys) >= 5)
    expect("E.3 TH and EN have same set of dup.* keys (parity)", th_keys, en_keys)

    # Show keys for confirmation
    print(f"     keys: {sorted(th_keys)}")


# ═══════════════════════════════════════════════════════════════
# Section F: HTML modal structure
# ═══════════════════════════════════════════════════════════════
def section_f_html():
    print("\n=== Section F: HTML modal structure ===")

    with open("legacy-frontend/index.html", encoding="utf-8") as f:
        html = f.read()

    expect_true("F.1 modal overlay element exists", 'id="dup-modal-overlay"' in html)
    expect_true("F.2 modal body container exists", 'id="dup-list"' in html)
    expect_true("F.3 skip button exists", 'id="dup-skip-btn"' in html)
    expect_true("F.4 keep button exists", 'id="dup-keep-btn"' in html)
    expect_true("F.5 modal title with i18n", 'data-i18n="dup.title"' in html)
    expect_true("F.6 modal hidden by default", 'class="dup-modal-overlay hidden"' in html)


# ═══════════════════════════════════════════════════════════════
# Section G: Stress — batch ใหญ่ + performance
# ═══════════════════════════════════════════════════════════════
async def section_g_stress():
    print("\n=== Section G: Stress (10-file batch + performance) ===")

    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.auth import create_access_token

    client = TestClient(app)

    # Setup user
    user_id = gen_id()
    async with AsyncSessionLocal() as db:
        u = User(id=user_id, email=f"stress_{user_id[:6]}@t.local",
                name="Stress", is_active=True, plan="free",
                subscription_status="free", storage_mode="managed")
        db.add(u)
        await db.commit()
    token = create_access_token(user_id, f"stress_{user_id[:6]}@t.local", "Stress")

    # Pre-seed 5 ไฟล์ใน DB ก่อน
    from backend.duplicate_detector import compute_content_hash
    seed_texts = [f"Seed file content number {i} " + "x" * 100 for i in range(5)]
    async with AsyncSessionLocal() as db:
        for i, text in enumerate(seed_texts):
            f = File(
                id=gen_id(), user_id=user_id, filename=f"seed_{i}.txt",
                filetype="txt", raw_path=f"/tmp/seed_{i}",
                extracted_text=text, processing_status="ready",
                content_hash=compute_content_hash(text),
            )
            db.add(f)
        await db.commit()

    # Upload 10 ไฟล์: 3 ตรงกับ seed + 7 unique
    files_payload = []
    # 3 duplicates of existing
    for i in range(3):
        files_payload.append(
            ("files", (f"dup_seed_{i}.txt",
                       io.BytesIO(seed_texts[i].encode()), "text/plain"))
        )
    # 7 unique
    for i in range(7):
        unique_text = f"Stress unique content {i} " + "y" * 100
        files_payload.append(
            ("files", (f"unique_{i}.txt",
                       io.BytesIO(unique_text.encode()), "text/plain"))
        )

    start = time.time()
    res = client.post(
        "/api/upload",
        files=files_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    elapsed = time.time() - start

    expect("G.1 status 200", res.status_code, 200)
    data = res.json()
    expect("G.2 10 files uploaded", data.get("count"), 10)
    dups = data.get("duplicates_found", [])
    expect_true(f"G.3 found 3 duplicates (got {len(dups)})", len(dups) == 3)
    if dups:
        all_exact = all(d["match_kind"] == "exact" for d in dups)
        expect_true("G.4 all 3 are exact matches", all_exact)
    expect_true(f"G.5 batch detection completed in < 5s (took {elapsed:.2f}s)",
                elapsed < 5.0)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
async def main():
    await init_db()

    await section_a_schema()
    await section_b_version()
    await section_c_upload_e2e()
    await section_d_cascade()
    section_e_i18n()
    section_f_html()
    await section_g_stress()

    print(f"\n{'=' * 60}")
    print(f"  E2E VERIFICATION RESULT: {PASS} passed / {FAIL} failed")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


sys.exit(asyncio.run(main()))
