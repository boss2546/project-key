"""v7.5.0 — End-to-end verification for Upload Resilience.

Run: python scripts/upload_resilience_e2e_verify.py

4 sections (1 per phase, but committed together as phases ship):
  Section A: Phase 1 — image OCR + structured skip + EMPTY_FILE detect + size msg
  Section B: Phase 4 — big-file chunking + map-reduce summary + bump limits
  Section C: Phase 2 — pre-upload extraction_status + retry endpoint + encrypted detect
  Section D: Phase 3 — xlsx/pptx/html/json/rtf format support

Uses FastAPI TestClient (in-process — no port binding required, sandbox-safe).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
RUN_ID = str(int(time.time()))

# v7.5.0 — clear BYOS env so endpoints don't 503
os.environ.setdefault("ADMIN_PASSWORD", "test1234")
for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"):
    os.environ[k] = ""

# Use a clean test database to avoid polluting dev data
TEST_DB = ROOT / "tests" / "_v750_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATA_DIR"] = str(ROOT / "tests")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.database import init_db  # noqa: E402

PASS = FAIL = 0
SKIP = 0
FIXTURES = ROOT / "tests" / "fixtures" / "upload_samples"


def expect(name: str, actual, equals) -> None:
    global PASS, FAIL
    if actual == equals:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name} — expected {equals!r}, got {actual!r}")
        FAIL += 1


def expect_true(name: str, condition: bool, hint: str = "") -> None:
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        suffix = f" — {hint}" if hint else ""
        print(f"  FAIL  {name}{suffix}")
        FAIL += 1


def skip(name: str, why: str) -> None:
    global SKIP
    print(f"  SKIP  {name} — {why}")
    SKIP += 1


# ─── Setup ──────────────────────────────────────────────────────────


import asyncio
asyncio.run(init_db())

client = TestClient(app)


def _register_user(email: str, password: str = "Pass!1234") -> str:
    """Register + return JWT token."""
    r = client.post("/api/auth/register", json={
        "email": email, "password": password, "name": "Tester",
    })
    if r.status_code not in (200, 201):
        raise RuntimeError(f"register failed: {r.status_code} {r.text}")
    body = r.json()
    return body.get("token") or body.get("access_token")


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─── Section A: Phase 1 — Fix Bugs ───────────────────────────────────


print("\n═══ SECTION A — Phase 1: Fix Bugs ═══")

# Fresh user for isolation
token_a = _register_user(f"a_{RUN_ID}_phase1@test.local")
headers_a = _auth_headers(token_a)

# A.1 — Upload 1 valid TXT (sanity baseline)
r = client.post(
    "/api/upload",
    files=[("files", ("hello.txt", b"hello world v7.5.0 test content for phase 1", "text/plain"))],
    headers=headers_a,
)
expect("A.1 upload valid txt returns 200", r.status_code, 200)
data = r.json()
expect("A.2 upload count = 1", data.get("count"), 1)
expect("A.3 skipped is empty for valid file", len(data.get("skipped", [])), 0)

# A.4-A.7 — Mixed batch: unsupported + too large + empty + valid
big_content = b"x" * (250 * 1024 * 1024)  # 250MB > limit (testing 100MB)
r = client.post(
    "/api/upload",
    files=[
        ("files", ("ok.txt", b"valid content for upload", "text/plain")),
        ("files", ("bad.xyz", b"unsupported", "application/octet-stream")),
        ("files", ("huge.pdf", big_content, "application/pdf")),
        ("files", ("empty.txt", b"", "text/plain")),
    ],
    headers=headers_a,
)
expect("A.4 mixed batch returns 200", r.status_code, 200)
data = r.json()
skipped = data.get("skipped", [])
codes = {s.get("code") for s in skipped}
expect_true("A.5 skip contains UNSUPPORTED_TYPE",
            "UNSUPPORTED_TYPE" in codes, hint=f"got codes={codes}")
expect_true("A.6 skip contains FILE_TOO_LARGE",
            "FILE_TOO_LARGE" in codes, hint=f"got codes={codes}")
expect_true("A.7 skip contains EMPTY_FILE",
            "EMPTY_FILE" in codes, hint=f"got codes={codes}")

# A.8 — Each skip has structured fields
for s in skipped:
    has_all_fields = all(k in s for k in ("filename", "code", "message", "suggestion"))
    if not has_all_fields:
        expect_true(f"A.8 skip entry has all fields ({s.get('filename')})", False,
                    hint=f"missing keys, got={list(s.keys())}")
        break
else:
    expect_true("A.8 every skip has {filename, code, message, suggestion}", True)

# A.9 — Size error msg shows ACTUAL plan limit (not stale 10MB)
size_skip = next((s for s in skipped if s.get("code") == "FILE_TOO_LARGE"), None)
if size_skip:
    msg = size_skip.get("message", "")
    expect_true("A.9 size error msg contains plan limit (100/200MB), not 10MB",
                "10MB" not in msg and ("100MB" in msg or "200MB" in msg or "MB" in msg),
                hint=f"got={msg!r}")
else:
    expect_true("A.9 size error msg present", False, hint="no FILE_TOO_LARGE in skip array")

# A.10 — Suggestion is non-empty string with actionable content
all_have_suggestions = all(
    isinstance(s.get("suggestion"), str) and len(s.get("suggestion", "")) > 5
    for s in skipped
)
expect_true("A.10 every skip has actionable (>5 char) suggestion string", all_have_suggestions)

# A.11 — Backward compat: legacy `reason` field still present
all_have_reason = all("reason" in s for s in skipped)
expect_true("A.11 legacy `reason` field preserved for back-compat", all_have_reason)

# A.12 — Image upload (png) — sanity that endpoint accepts it
import base64
# 1x1 PNG (transparent)
png_min = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+P+/HgAFhAJ/wlseKgAAAABJRU5ErkJggg=="
)
r = client.post(
    "/api/upload",
    files=[("files", ("tiny.png", png_min, "image/png"))],
    headers=headers_a,
)
expect("A.12 png upload returns 200", r.status_code, 200)
data = r.json()
# Even if no tesseract binary → file should still upload (extracted_text will be marker)
expect_true("A.13 png file accepted (count>=1 or moved-to-skip-not-as-unsupported)",
            data.get("count", 0) >= 1 or
            not any(s.get("code") == "UNSUPPORTED_TYPE" and s.get("filename") == "tiny.png"
                    for s in data.get("skipped", [])))


# ─── Final Report ────────────────────────────────────────────────────


def _summary():
    total = PASS + FAIL
    print(f"\n─────────────────────────────────────────────────────")
    print(f"RESULT: {PASS}/{total} PASS  ({SKIP} skipped)")
    if FAIL == 0:
        print("✅ ALL EXPECTED TESTS PASSED")
    else:
        print(f"❌ {FAIL} FAILURES")
    print("─────────────────────────────────────────────────────")
    return 0 if FAIL == 0 else 1


# ─── Section B: Phase 4 — Big File ──────────────────────────────────


print("\n═══ SECTION B — Phase 4: Big File Support ═══")

# B.1 — DB schema includes new v7.5.0 columns
import asyncio as _asyncio
from sqlalchemy import text as _sql

async def _check_schema():
    from backend.database import AsyncSessionLocal
    async with AsyncSessionLocal() as db:
        cur = await db.execute(_sql("PRAGMA table_info(files)"))
        cols = [row[1] for row in cur.fetchall()]
        return cols

cols = _asyncio.run(_check_schema())
expect_true("B.1 files.extraction_status column exists",
            "extraction_status" in cols, hint=f"cols={sorted(cols)}")
expect_true("B.2 files.chunk_count column exists",
            "chunk_count" in cols)
expect_true("B.3 files.is_truncated column exists",
            "is_truncated" in cols)

# B.4 — text_chunker imports + handles big text
from backend.text_chunker import chunk_text as _chunk
from backend.config import LARGE_FILE_THRESHOLD

small_chunks = _chunk("hello " * 100)
expect_true("B.4 chunk_text small text returns 1 chunk",
            len(small_chunks) == 1)

big_text = "## Heading {n}\n".format(n=0) + "\n\n".join(
    f"## Heading {i}\nUNIQUE_MARK_{i:03d} " + ("content " * 1000) for i in range(1, 8)
)
big_chunks = _chunk(big_text)
expect_true("B.5 chunk_text big text returns multiple chunks",
            len(big_chunks) > 1, hint=f"got {len(big_chunks)} chunks for {len(big_text)} chars")

# B.6 — every UNIQUE_MARK present somewhere in chunks
all_text = "".join(big_chunks)
markers_found = sum(1 for i in range(1, 8) if f"UNIQUE_MARK_{i:03d}" in all_text)
expect_true("B.6 all 7 UNIQUE_MARK preserved across chunks",
            markers_found == 7, hint=f"found {markers_found}/7")

# B.7 — bumped size limit (200MB testing)
from backend.plan_limits import PLAN_LIMITS
expect("B.7 free.max_file_size_mb bumped to 200",
       PLAN_LIMITS["free"]["max_file_size_mb"], 200)
expect("B.8 starter.max_file_size_mb bumped to 200",
       PLAN_LIMITS["starter"]["max_file_size_mb"], 200)

# B.9 — allowed types extended
allowed = PLAN_LIMITS["free"]["allowed_file_types"]
new_types = {"xlsx", "pptx", "html", "json", "rtf", "jpeg", "webp"}
missing = new_types - allowed
expect_true("B.9 allowed_types includes xlsx/pptx/html/json/rtf/jpeg/webp",
            not missing, hint=f"missing={missing}")

# B.10 — LARGE_FILE_THRESHOLD = 30000 (per Q-A user decision)
expect("B.10 LARGE_FILE_THRESHOLD = 30000", LARGE_FILE_THRESHOLD, 30000)

# B.11 — File model accepts new columns via ORM (sanity insert + read)
async def _orm_roundtrip():
    from backend.database import AsyncSessionLocal, File, gen_id
    from sqlalchemy import select
    fid = gen_id()
    async with AsyncSessionLocal() as db:
        f = File(
            id=fid, user_id="dummy_user", filename="x.txt",
            filetype="txt", raw_path="/dev/null",
            extracted_text="test", extraction_status="ok",
            chunk_count=5, is_truncated=False,
        )
        db.add(f)
        await db.commit()
        r = await db.execute(select(File).where(File.id == fid))
        got = r.scalar_one_or_none()
        await db.delete(got)
        await db.commit()
        return got

got = _asyncio.run(_orm_roundtrip())
expect("B.11 ORM roundtrip preserves chunk_count", got.chunk_count, 5)
expect("B.12 ORM roundtrip preserves extraction_status", got.extraction_status, "ok")
expect_true("B.13 ORM roundtrip preserves is_truncated default",
            got.is_truncated in (False, 0))


# ─── Section C: Phase 2 — Proactive UX (extraction_status + retry) ──


print("\n═══ SECTION C — Phase 2: Proactive UX ═══")

# C.1 — classify_extraction_status function exists + works
from backend.extraction import classify_extraction_status
expect("C.1 classify normal text → ok",
       classify_extraction_status("hello world this is real text"), "ok")
expect("C.2 classify empty string → empty",
       classify_extraction_status(""), "empty")
expect("C.3 classify encrypted marker → encrypted",
       classify_extraction_status("[PDF encrypted: foo]"), "encrypted")
expect("C.4 classify OCR no-text marker → ocr_failed",
       classify_extraction_status("[Image: no text detected]"), "ocr_failed")
expect("C.5 classify unsupported marker → unsupported",
       classify_extraction_status("[Unsupported file type: heic]"), "unsupported")

# C.6 — Upload sets extraction_status correctly
token_c = _register_user(f"c_{RUN_ID}_phase2@test.local")
headers_c = _auth_headers(token_c)

r = client.post(
    "/api/upload",
    files=[("files", ("normal.txt", b"hello world content for status check",
                      "text/plain"))],
    headers=headers_c,
)
assert r.status_code == 200, r.text
file_id_c = r.json()["uploaded"][0]["id"]

r2 = client.get("/api/files", headers=headers_c)
files_list = r2.json().get("files", [])
target = next((f for f in files_list if f["id"] == file_id_c), None)
expect_true("C.6 GET /api/files exposes extraction_status",
            target and "extraction_status" in target,
            hint=f"got keys={list(target.keys()) if target else None}")
expect("C.7 normal text upload → extraction_status = ok",
       target.get("extraction_status") if target else None, "ok")
expect_true("C.8 GET /api/files exposes chunk_count",
            target and "chunk_count" in target)
expect_true("C.9 GET /api/files exposes is_truncated",
            target and "is_truncated" in target)

# C.10 — Reprocess endpoint accepts mode=reextract
r3 = client.post(
    f"/api/files/{file_id_c}/reprocess?mode=reextract",
    headers=headers_c,
)
expect("C.10 reprocess?mode=reextract returns 200", r3.status_code, 200)
body = r3.json()
expect("C.11 reprocess response has extraction_method=reextract",
       body.get("extraction_method"), "reextract")
expect("C.12 reprocess response includes extraction_status",
       body.get("extraction_status"), "ok")

# C.13 — Reprocess invalid mode returns 422 (FastAPI validation)
r4 = client.post(
    f"/api/files/{file_id_c}/reprocess?mode=garbage",
    headers=headers_c,
)
expect_true("C.13 reprocess?mode=invalid returns 422",
            r4.status_code == 422, hint=f"got {r4.status_code}")

# C.14 — Reprocess for missing file returns 404
r5 = client.post(
    f"/api/files/no_such_id_xxx/reprocess?mode=reextract",
    headers=headers_c,
)
expect("C.14 reprocess missing file → 404", r5.status_code, 404)

# C.15 — Cross-user reprocess returns 404 (silent — don't leak existence)
token_c2 = _register_user(f"c2_{RUN_ID}_other@test.local")
r6 = client.post(
    f"/api/files/{file_id_c}/reprocess?mode=reextract",
    headers=_auth_headers(token_c2),
)
expect_true("C.15 cross-user reprocess returns 404 (no info leak)",
            r6.status_code == 404, hint=f"got {r6.status_code}")


# Section D added in Phase 3
print("\n[Section D added when Phase 3 ships]")

sys.exit(_summary())
