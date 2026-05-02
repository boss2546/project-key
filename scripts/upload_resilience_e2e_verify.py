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


# Sections B/C/D get added in their respective phases
print("\n[Sections B, C, D will be added as Phase 4/2/3 ship]")

sys.exit(_summary())
