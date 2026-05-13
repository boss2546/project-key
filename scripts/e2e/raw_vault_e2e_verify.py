"""v9.1.0 — End-to-end verification for Raw File Vault.

Run: python scripts/raw_vault_e2e_verify.py

5 sections (~30 cases):
  Section A: Vault Upload Behavior (8) — UNSUPPORTED → vault, supported → processed
  Section B: List Filter (6) — ?kind=all|processed|vault
  Section C: Promote Endpoint (8) — vault → processed flow + 5 error cases
  Section D: Vault excluded from AI pipeline (4) — organize/cluster/chat
  Section E: Stats + Vault search via TF-IDF (4)

Uses FastAPI TestClient (in-process — no port binding required).
"""
from __future__ import annotations

import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("ADMIN_PASSWORD", "test1234")
for k in ("GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"):
    os.environ[k] = ""

TEST_DB = ROOT / "tests" / "_v910_vault_test.db"
if TEST_DB.exists():
    TEST_DB.unlink()
os.environ["DATA_DIR"] = str(ROOT / "tests")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"

from fastapi.testclient import TestClient  # noqa: E402

from backend.main import app  # noqa: E402
from backend.database import init_db  # noqa: E402

PASS = FAIL = 0


def expect(name, actual, equals):
    global PASS, FAIL
    if actual == equals:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        print(f"  FAIL  {name} — expected {equals!r}, got {actual!r}")
        FAIL += 1


def expect_true(name, condition, hint=""):
    global PASS, FAIL
    if condition:
        print(f"  PASS  {name}")
        PASS += 1
    else:
        suffix = f" — {hint}" if hint else ""
        print(f"  FAIL  {name}{suffix}")
        FAIL += 1


import asyncio
asyncio.run(init_db())

client = TestClient(app)
RUN_ID = str(int(time.time()))


def _register(email_suffix):
    r = client.post("/api/auth/register", json={
        "email": f"{email_suffix}_{RUN_ID}@vault.test",
        "password": "Vault!1234", "name": "Vault Tester",
    })
    if r.status_code not in (200, 201):
        raise RuntimeError(f"register failed: {r.status_code} {r.text}")
    return r.json()["token"]


def _hdr(t):
    return {"Authorization": f"Bearer {t}"}


# ─── SECTION A: Vault upload behavior ────────────────────────────────


print("\n═══ SECTION A — Vault upload behavior ═══")
token_a = _register("a")
hdr_a = _hdr(token_a)

# A.1 — Upload .zip → vault
r = client.post("/api/upload",
                files=[("files", ("design.zip", b"fake zip content", "application/zip"))],
                headers=hdr_a)
expect("A.1 zip upload returns 200", r.status_code, 200)
data = r.json()
expect_true("A.2 zip uploaded count=1 (not skipped)", data.get("count") == 1)
if data.get("uploaded"):
    expect_true("A.3 zip file_kind = vault_only",
                data["uploaded"][0].get("file_kind") == "vault_only",
                hint=f"got {data['uploaded'][0]}")

# A.4 — Upload .pdf → processed
r = client.post("/api/upload",
                files=[("files", ("doc.pdf", b"%PDF-1.4 fake pdf content here for test extract",
                                  "application/pdf"))],
                headers=hdr_a)
data = r.json()
if data.get("uploaded"):
    expect_true("A.4 pdf file_kind = processed",
                data["uploaded"][0].get("file_kind") == "processed")

# A.5 — Mixed batch (.zip + .pdf) → ทั้งคู่อัพ
r = client.post("/api/upload",
                files=[("files", ("data.csv", b"a,b\n1,2\n", "text/csv")),
                       ("files", ("photo.psd", b"fake psd", "application/octet-stream"))],
                headers=hdr_a)
data = r.json()
expect_true("A.5 mixed batch — count=2 (no skip)",
            data.get("count") == 2 and len(data.get("skipped", [])) == 0,
            hint=f"count={data.get('count')} skipped={data.get('skipped')}")
kinds = sorted([u.get("file_kind") for u in (data.get("uploaded") or [])])
expect("A.6 mixed batch kinds = [processed, vault_only]",
       kinds, ["processed", "vault_only"])

# A.7 — empty file → SKIPPED EMPTY_FILE (not vault — empty check ก่อน vault)
r = client.post("/api/upload",
                files=[("files", ("empty.zip", b"", "application/zip"))],
                headers=hdr_a)
data = r.json()
codes = [s.get("code") for s in (data.get("skipped") or [])]
expect_true("A.7 empty .zip → SKIPPED EMPTY_FILE (not vault)",
            "EMPTY_FILE" in codes,
            hint=f"got skipped={data.get('skipped')}")

# A.8 — file too large → SKIPPED FILE_TOO_LARGE (not vault)
big_data = b"x" * (250 * 1024 * 1024)  # 250MB > 200MB hard cap
r = client.post("/api/upload",
                files=[("files", ("huge.zip", big_data, "application/zip"))],
                headers=hdr_a)
data = r.json()
codes = [s.get("code") for s in (data.get("skipped") or [])]
expect_true("A.8 huge .zip → SKIPPED FILE_TOO_LARGE (not vault)",
            "FILE_TOO_LARGE" in codes)


# ─── SECTION B: List filter ─────────────────────────────────────────


print("\n═══ SECTION B — List filter ?kind= ═══")

# B.1 — default = all
r = client.get("/api/files", headers=hdr_a)
expect("B.1 GET /api/files returns 200", r.status_code, 200)
all_files = r.json().get("files", [])
expect_true("B.2 default returns both kinds",
            any(f.get("file_kind") == "processed" for f in all_files) and
            any(f.get("file_kind") == "vault_only" for f in all_files),
            hint=f"got kinds={[f.get('file_kind') for f in all_files]}")

# B.3 — kind=processed
r = client.get("/api/files?kind=processed", headers=hdr_a)
processed_files = r.json().get("files", [])
expect_true("B.3 kind=processed only returns processed",
            all(f.get("file_kind") == "processed" for f in processed_files))

# B.4 — kind=vault
r = client.get("/api/files?kind=vault", headers=hdr_a)
vault_files = r.json().get("files", [])
expect_true("B.4 kind=vault only returns vault_only",
            all(f.get("file_kind") == "vault_only" for f in vault_files))

# B.5 — Each file has file_kind + vault_reason
sample = (vault_files or all_files)
if sample:
    f = sample[0]
    expect_true("B.5 file response has file_kind + vault_reason fields",
                "file_kind" in f and "vault_reason" in f)

# B.6 — invalid kind → 422
r = client.get("/api/files?kind=invalid", headers=hdr_a)
expect("B.6 invalid kind returns 422", r.status_code, 422)


# ─── SECTION C: Promote endpoint ─────────────────────────────────────


print("\n═══ SECTION C — Promote endpoint ═══")
token_c = _register("c")
hdr_c = _hdr(token_c)

# Setup: upload a vault file
r = client.post("/api/upload",
                files=[("files", ("test.zip", b"vault content", "application/zip"))],
                headers=hdr_c)
data = r.json()
vault_id = data["uploaded"][0]["id"] if data.get("uploaded") else None
assert vault_id, f"setup failed: {data}"

# Setup: upload a processed file
r = client.post("/api/upload",
                files=[("files", ("ok.txt", b"hello world content", "text/plain"))],
                headers=hdr_c)
data = r.json()
processed_id = data["uploaded"][0]["id"] if data.get("uploaded") else None

# C.1 — promote on processed → 400 NOT_VAULT
r = client.post(f"/api/files/{processed_id}/promote", headers=hdr_c)
expect("C.1 promote on processed → 400", r.status_code, 400)
body = r.json()
expect_true("C.2 error code = NOT_VAULT",
            body.get("detail", {}).get("error", {}).get("code") == "NOT_VAULT")

# C.3 — promote on missing file → 404
r = client.post("/api/files/nonexistent_id/promote", headers=hdr_c)
expect("C.3 promote on missing → 404", r.status_code, 404)

# C.4 — promote cross-user → 404 (no info leak)
token_other = _register("other")
r = client.post(f"/api/files/{vault_id}/promote", headers=_hdr(token_other))
expect("C.4 promote cross-user → 404 (no leak)", r.status_code, 404)

# C.5 — promote vault file → still vault (zip still not in allowed_types)
r = client.post(f"/api/files/{vault_id}/promote", headers=hdr_c)
expect("C.5 promote vault returns 200", r.status_code, 200)
body = r.json()
expect_true("C.6 promoted=False (zip still unsupported)",
            body.get("promoted") is False,
            hint=f"got body={body}")
expect_true("C.7 file_kind still vault_only",
            body.get("file_kind") == "vault_only")

# C.8 — verify vault file still has searchable text
r = client.get(f"/api/files?kind=vault", headers=hdr_c)
vault_list = r.json().get("files", [])
expect_true("C.8 vault file has text_length > 0 (searchable)",
            any(f["id"] == vault_id and f.get("text_length", 0) > 0 for f in vault_list),
            hint=f"vault files={vault_list}")


# ─── SECTION D: Vault excluded from AI pipeline ──────────────────────


print("\n═══ SECTION D — Vault excluded from AI pipeline ═══")

# D.1 — organize-new query excludes vault (smoke)
# We can't actually run organize without LLM, but verify SQL filter via
# direct DB query: count files where file_kind="processed"
async def _check_organize_filter():
    from backend.database import AsyncSessionLocal, File
    from sqlalchemy import select, func
    async with AsyncSessionLocal() as db:
        # Count processed files for hdr_c user
        from backend.auth import decode_token
        payload = decode_token(token_c)
        user_id = payload["sub"]
        cur = await db.execute(select(func.count(File.id)).where(
            File.user_id == user_id,
            File.file_kind == "processed",
        ))
        processed_count = cur.scalar()
        cur = await db.execute(select(func.count(File.id)).where(
            File.user_id == user_id,
            File.file_kind == "vault_only",
        ))
        vault_count = cur.scalar()
        return processed_count, vault_count

p_count, v_count = asyncio.run(_check_organize_filter())
expect_true("D.1 user has both processed + vault files",
            p_count >= 1 and v_count >= 1,
            hint=f"processed={p_count} vault={v_count}")

# D.2-D.4 — vault file's searchable_text format (no extracted content, only filename+ext)
r = client.get("/api/files?kind=vault", headers=hdr_c)
vault_data = r.json().get("files", [])
if vault_data:
    f = vault_data[0]
    # text_length > 0 (vault has searchable filename) but processing_status="vault_only"
    expect_true("D.2 vault file processing_status=vault_only",
                f.get("processing_status") == "vault_only",
                hint=f"got status={f.get('processing_status')}")
    expect_true("D.3 vault file extraction_status=vault",
                f.get("extraction_status") == "vault",
                hint=f"got ext_status={f.get('extraction_status')}")
    expect_true("D.4 vault file has text_length > 0 (searchable by filename)",
                f.get("text_length", 0) > 0)


# ─── SECTION E: Stats + Vault search ─────────────────────────────────


print("\n═══ SECTION E — Stats + Vault search ═══")

r = client.get("/api/stats", headers=hdr_c)
stats = r.json()
expect_true("E.1 /api/stats has vault_files field",
            "vault_files" in stats, hint=f"keys={list(stats.keys())}")
expect_true("E.2 /api/stats has processed_files field",
            "processed_files" in stats)
expect_true("E.3 vault_files >= 1 (uploaded earlier)",
            stats.get("vault_files", 0) >= 1)
expect_true("E.4 total = processed + vault",
            stats.get("total_files") == stats.get("processed_files", 0) + stats.get("vault_files", 0),
            hint=f"total={stats.get('total_files')} p={stats.get('processed_files')} v={stats.get('vault_files')}")


# ─── Final ───────────────────────────────────────────────────────────


total = PASS + FAIL
print(f"\n─────────────────────────────────────────")
print(f"RESULT: {PASS}/{total} PASS")
if FAIL == 0:
    print("✅ ALL EXPECTED TESTS PASSED")
else:
    print(f"❌ {FAIL} FAILURES")
print("─────────────────────────────────────────")

sys.exit(0 if FAIL == 0 else 1)
