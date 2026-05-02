"""v7.1 — End-to-end verification (ad-hoc deep test สำหรับเขียวก่อนส่งฟ้า).

Run: python scripts/dedupe_e2e_verify.py

**v7.1 user override (2026-05-01):** trigger ของ duplicate detection ย้ายจาก
`/api/upload` → `/api/organize-new` (หลัง vector_search index ไฟล์ใหม่ครบ).
Section C + G อัพเดทให้ trigger detection ผ่าน organize-new endpoint แทน upload.

Coverage ที่ smoke test ของจริง (duplicate_detection_smoke.py) ยังไม่ครอบคลุม:
  Section A: Schema verification — content_hash + indexes มีจริงใน DB
  Section B: APP_VERSION runtime visibility (Swagger/MCP info)
  Section C: End-to-end upload → organize → duplicates_found via TestClient
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

    # v7.5.0 update — accept any 7.x.y version (current = 7.5.0 upload-resilience)
    # Why so loose: dedupe feature itself is v7.1, but later versions (v7.2-v7.5)
    # piggyback the same APP_VERSION constant. Test should pass on any 7.x.
    from backend.config import APP_VERSION
    expect_true(
        f"B.1 config.APP_VERSION starts with '7.' (got '{APP_VERSION}')",
        APP_VERSION.startswith("7."),
    )

    # B.2: FastAPI app instance reads from APP_VERSION
    from backend.main import app
    expect_true(
        f"B.2 FastAPI app.version starts with '7.' (got '{app.version}')",
        app.version.startswith("7."),
    )

    # B.3: app.html (split from index.html in v7.2.0) shows current v7.1.x version
    # v7.2.0 commit cc1ad84 split monolith → landing.html + app.html
    import os
    html_path = "legacy-frontend/app.html"
    if not os.path.exists(html_path):
        # Fallback for pre-v7.2.0 layout
        html_path = "legacy-frontend/index.html"
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    expect_true(f"B.3a {html_path} contains 'v{APP_VERSION}'", f"v{APP_VERSION}" in html)
    expect_true(f"B.3b {html_path} no leftover 'v7.0.1'", "v7.0.1" not in html)


# ═══════════════════════════════════════════════════════════════
# Section C: End-to-end upload → organize → duplicates_found
# ═══════════════════════════════════════════════════════════════
async def section_c_organize_e2e():
    print("\n=== Section C: End-to-end /api/upload + /api/organize-new + skip ===")

    from fastapi.testclient import TestClient
    from backend.main import app
    from backend.auth import create_access_token
    from backend import organizer as _organizer
    from backend import main as _main_mod

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

    # ── C.1: Upload — response ห้ามมี duplicates_found field (contract change) ──
    user_id, token = await _make_user()
    headers = {"Authorization": f"Bearer {token}"}
    file_content = b"This is unique content for E2E test alpha. " * 5
    res = client.post(
        "/api/upload",
        files=[("files", ("alpha.txt", io.BytesIO(file_content), "text/plain"))],
        headers=headers,
    )
    expect("C.1a status 200", res.status_code, 200)
    data = res.json()
    expect_true("C.1b upload response NO 'duplicates_found' field (contract: detection moved to organize-new)",
                "duplicates_found" not in data)
    expect("C.1c 1 file uploaded", data.get("count"), 1)
    first_file_id = data["uploaded"][0]["id"]

    # content_hash ยังต้องถูก compute + เก็บ (สำหรับใช้ตอน organize)
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        f = (await db.execute(select(File).where(File.id == first_file_id))).scalar_one()
    expect_true("C.1d content_hash populated in DB (still computed at upload)",
                f.content_hash is not None)
    expect("C.1e content_hash is 64-char hex", len(f.content_hash or ""), 64)

    # ── C.2: organize-new — empty case (no new files) ──
    # ตอนนี้ user ยังไม่มี FileSummary → organize_new_files จะหาไฟล์เจอ + พยายาม organize
    # แต่ organize เรียก LLM จริง → ใน sandbox ไม่ได้ผล → mock organize_new_files ทั้ง func
    # เพื่อให้มันเป็น no-op ที่ return file_ids ที่ "เพิ่ง organize" (เลียนแบบ post-organize state)

    # Setup: index ไฟล์ที่ upload ไปก่อนหน้านี้เข้า vector_search (เลียนแบบ organize เสร็จ)
    vector_search.index_file(
        file_id=first_file_id, filename="alpha.txt",
        text=file_content.decode(), user_id=user_id,
    )

    # Mock 4 functions ที่ organize_new endpoint เรียก เพื่อ skip LLM call
    original_organize = _organizer.organize_new_files
    original_enrich = _main_mod.enrich_all_files
    original_graph = _main_mod.build_full_graph
    original_suggest = _main_mod.generate_suggestions

    async def mock_organize_returns_file_ids(db, user_id):
        """Stub — บอกว่า organize เสร็จแล้ว (ไฟล์ index แล้วในข้างบน) + return file_ids"""
        return {"skipped": False, "count": 1, "file_ids": [first_file_id]}

    async def mock_noop(*args, **kwargs):
        return {"nodes": 0, "edges": 0}  # graph stub

    async def mock_noop_void(*args, **kwargs):
        return None

    _organizer.organize_new_files = mock_organize_returns_file_ids
    _main_mod.enrich_all_files = mock_noop_void
    _main_mod.build_full_graph = mock_noop
    _main_mod.generate_suggestions = mock_noop_void

    try:
        # Upload ไฟล์ที่ 2 (identical content) → ตอน upload ยังไม่ตรวจ
        res2 = client.post(
            "/api/upload",
            files=[("files", ("alpha_copy.txt", io.BytesIO(file_content), "text/plain"))],
            headers=headers,
        )
        expect("C.2a upload status 200", res2.status_code, 200)
        second_file_id = res2.json()["uploaded"][0]["id"]
        # Index ไฟล์ที่ 2 ด้วย (เลียนแบบ organize)
        vector_search.index_file(
            file_id=second_file_id, filename="alpha_copy.txt",
            text=file_content.decode(), user_id=user_id,
        )

        # Mock organize_new_files ให้ return ทั้ง 2 file_ids (เลียนแบบ organize batch)
        async def mock_organize_two(db, user_id_arg):
            return {"skipped": False, "count": 2, "file_ids": [first_file_id, second_file_id]}
        _organizer.organize_new_files = mock_organize_two

        # ── C.3: organize-new → response ต้องมี duplicates_found ──
        res3 = client.post("/api/organize-new", headers=headers)
        expect("C.3a organize-new status 200", res3.status_code, 200)
        data3 = res3.json()
        expect_true("C.3b 'duplicates_found' field exists ใน organize response",
                    "duplicates_found" in data3)
        dups = data3.get("duplicates_found", [])
        expect_true(f"C.3c found ≥ 1 duplicate (got {len(dups)})", len(dups) >= 1)
        if dups:
            expect("C.3d match_kind = 'exact'", dups[0].get("match_kind"), "exact")
            expect("C.3e similarity = 1.0", dups[0].get("similarity"), 1.0)

        # ── C.4: organize-new skipped path (no new files) → empty duplicates_found ──
        async def mock_organize_skipped(db, user_id_arg):
            return {"skipped": True, "count": 0}
        _organizer.organize_new_files = mock_organize_skipped

        res4 = client.post("/api/organize-new", headers=headers)
        expect("C.4a organize-new (skipped) status 200", res4.status_code, 200)
        data4 = res4.json()
        expect("C.4b new_files = 0", data4.get("new_files"), 0)
        expect_true("C.4c 'duplicates_found' field still present (= [])",
                    "duplicates_found" in data4)
        expect("C.4d duplicates_found is empty list",
               data4.get("duplicates_found"), [])

        # ── C.5: skip-duplicates ลบไฟล์ duplicate ──
        res5 = client.post(
            "/api/files/skip-duplicates",
            json={"file_ids": [second_file_id]},
            headers=headers,
        )
        expect("C.5a skip-duplicates status 200", res5.status_code, 200)
        expect("C.5b file in deleted[]",
               second_file_id in res5.json().get("deleted", []), True)

        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            check = (await db.execute(select(File).where(File.id == second_file_id))).scalar_one_or_none()
        expect_true("C.5c file gone from DB", check is None)

    finally:
        # Restore originals — ห้ามให้ Section อื่นโดน mock ค้าง
        _organizer.organize_new_files = original_organize
        _main_mod.enrich_all_files = original_enrich
        _main_mod.build_full_graph = original_graph
        _main_mod.generate_suggestions = original_suggest


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
    print("\n=== Section F: HTML modal structure (v7.1.5 — per-file UX) ===")

    # v7.2.0 cc1ad84 split monolith → landing.html + app.html
    import os
    html_path = "legacy-frontend/app.html"
    if not os.path.exists(html_path):
        html_path = "legacy-frontend/index.html"
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    # Core modal structure (unchanged in v7.1.5)
    expect_true("F.1 modal overlay element exists", 'id="dup-modal-overlay"' in html)
    expect_true("F.2 modal body container exists", 'id="dup-list"' in html)
    expect_true("F.5 modal title with i18n", 'data-i18n="dup.title"' in html)
    expect_true("F.6 modal hidden by default", 'class="dup-modal-overlay hidden"' in html)

    # v7.1.5 — new per-file selector UX (replaces old skip/keep buttons)
    expect_true("F.7 v7.1.5 quick-keep-all button exists", 'id="dup-quick-keep-all"' in html)
    expect_true("F.8 v7.1.5 quick-skip-all button exists", 'id="dup-quick-skip-all"' in html)
    expect_true("F.9 v7.1.5 cancel (Later) button exists", 'id="dup-cancel-btn"' in html)
    expect_true("F.10 v7.1.5 confirm button exists", 'id="dup-confirm-btn"' in html)
    expect_true("F.11 v7.1.5 cancel uses dup.cancel i18n key", 'data-i18n="dup.cancel"' in html)
    expect_true("F.12 v7.1.5 quick-keep uses dup.quickKeep i18n", 'data-i18n="dup.quickKeep"' in html)
    expect_true("F.13 v7.1.5 quick-skip uses dup.quickSkip i18n", 'data-i18n="dup.quickSkip"' in html)
    expect_true("F.14 v7.1.5 old skip-btn removed", 'id="dup-skip-btn"' not in html)
    expect_true("F.15 v7.1.5 old keep-btn removed", 'id="dup-keep-btn"' not in html)


# ═══════════════════════════════════════════════════════════════
# Section G: Stress — detect_duplicates_for_batch (10-file post-organize)
# ═══════════════════════════════════════════════════════════════
async def section_g_stress():
    print("\n=== Section G: Stress (10-file post-organize batch + performance) ===")

    from backend.duplicate_detector import (
        detect_duplicates_for_batch, compute_content_hash,
    )

    # Setup user + 5 seed files (จำลอง library เดิม)
    user_id = gen_id()
    async with AsyncSessionLocal() as db:
        u = User(id=user_id, email=f"stress_{user_id[:6]}@t.local",
                name="Stress", is_active=True, plan="free",
                subscription_status="free", storage_mode="managed")
        db.add(u)
        await db.commit()

    seed_texts = [f"Seed file content number {i} " + "x" * 100 for i in range(5)]
    seed_ids: list[str] = []
    async with AsyncSessionLocal() as db:
        for i, text in enumerate(seed_texts):
            sid = gen_id()
            f = File(
                id=sid, user_id=user_id, filename=f"seed_{i}.txt",
                filetype="txt", raw_path=f"/tmp/seed_{i}",
                extracted_text=text, processing_status="ready",
                content_hash=compute_content_hash(text),
            )
            db.add(f)
            seed_ids.append(sid)
        await db.commit()

    # Index seeds เข้า vector_search (เลียนแบบ organize เสร็จ)
    for sid, text in zip(seed_ids, seed_texts):
        vector_search.index_file(file_id=sid, filename=f"seed_{sid[:6]}.txt",
                                  text=text, user_id=user_id)

    # Insert 10 ไฟล์ "ใหม่" (3 ซ้ำ seed + 7 unique) — เลียนแบบ post-organize state
    new_ids: list[str] = []
    async with AsyncSessionLocal() as db:
        # 3 duplicates of seed
        for i in range(3):
            nid = gen_id()
            f = File(
                id=nid, user_id=user_id, filename=f"dup_seed_{i}.txt",
                filetype="txt", raw_path=f"/tmp/dup_{i}",
                extracted_text=seed_texts[i], processing_status="ready",
                content_hash=compute_content_hash(seed_texts[i]),
            )
            db.add(f)
            new_ids.append(nid)
        # 7 unique
        for i in range(7):
            nid = gen_id()
            unique_text = f"Stress unique content {i} " + "y" * 100
            f = File(
                id=nid, user_id=user_id, filename=f"unique_{i}.txt",
                filetype="txt", raw_path=f"/tmp/u_{i}",
                extracted_text=unique_text, processing_status="ready",
                content_hash=compute_content_hash(unique_text),
            )
            db.add(f)
            new_ids.append(nid)
        await db.commit()

    # Index ทั้ง 10 ไฟล์ใหม่ (เลียนแบบ organize เสร็จ — ทุกไฟล์อยู่ใน vector_search แล้ว)
    for nid in new_ids:
        async with AsyncSessionLocal() as db:
            from sqlalchemy import select
            f = (await db.execute(select(File).where(File.id == nid))).scalar_one()
        vector_search.index_file(file_id=nid, filename=f.filename,
                                  text=f.extracted_text or "", user_id=user_id)

    # รัน detection — เลียนแบบที่ /api/organize-new เรียก
    start = time.time()
    async with AsyncSessionLocal() as db:
        matches = await detect_duplicates_for_batch(db, user_id, new_ids)
    elapsed = time.time() - start

    expect_true(f"G.1 found ≥ 3 duplicates (got {len(matches)})", len(matches) >= 3)
    if matches:
        # ทั้งหมดควรเป็น exact (เพราะ hash ตรงกับ seed)
        exact_count = sum(1 for m in matches if m["match_kind"] == "exact")
        expect_true(f"G.2 ≥ 3 exact matches (got {exact_count})", exact_count >= 3)
    expect_true(f"G.3 detection completed in < 5s (took {elapsed:.2f}s)",
                elapsed < 5.0)


# ═══════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════
async def main():
    await init_db()

    await section_a_schema()
    await section_b_version()
    await section_c_organize_e2e()
    await section_d_cascade()
    section_e_i18n()
    section_f_html()
    await section_g_stress()

    print(f"\n{'=' * 60}")
    print(f"  E2E VERIFICATION RESULT: {PASS} passed / {FAIL} failed")
    print(f"{'=' * 60}")
    return 0 if FAIL == 0 else 1


sys.exit(asyncio.run(main()))
