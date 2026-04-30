"""BYOS v7.0 foundation smoke test (in-process TestClient).

Run: python scripts/byos_foundation_smoke.py

Covers:
  1. /api/drive/status (no env vars) -> feature_available=False
  2. 503 fallback on 4 endpoints when not configured
  3. DB schema: storage_mode + drive_connections + files.drive_*
  4. drive_connections column structure
  5. Fernet encrypt/decrypt round-trip + key rotation
  6. drive_layout helpers (path builders, mime checks, enums)
  7. is_byos_configured() truth table
  8. Storage mode validation (invalid mode + byos without connection)
  9. Disconnect without connection -> 404
"""
import os
import sys
import secrets as _s
import importlib
import asyncio
import aiosqlite

sys.path.insert(0, ".")

# Force-clear env vars BEFORE importing backend.main (which triggers
# config.py's load_dotenv()).
# Set to "" instead of pop because load_dotenv defaults to override=False:
# - pop -> var missing -> dotenv reads .env and repopulates (defeats clear)
# - set "" -> var present (empty) -> dotenv skips (preserves clear)
for k in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"]:
    os.environ[k] = ""

from fastapi.testclient import TestClient
from backend.main import app
from backend.config import DATABASE_URL

c = TestClient(app)
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


def reload_cfg():
    from backend import config as _cfg
    importlib.reload(_cfg)
    return _cfg


def set_byos_env():
    from cryptography.fernet import Fernet
    os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "test_client_id"
    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "test_client_secret"
    os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    return reload_cfg()


def clear_byos_env():
    # Set to "" (not pop) so dotenv reload doesn't repopulate from .env
    for k in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET", "DRIVE_TOKEN_ENCRYPTION_KEY"]:
        os.environ[k] = ""
    return reload_cfg()


# Setup user
email = f"byos_{_s.token_hex(4)}@test.local"
r = c.post("/api/auth/register", json={"email": email, "password": "Smoke1234!", "display_name": "B"})
assert r.status_code == 200, f"register failed: {r.status_code} {r.text}"
tok = r.json()["token"]
H = {"Authorization": f"Bearer {tok}"}


print("=== 1. /api/drive/status (no env vars set) ===")
def t1():
    r = c.get("/api/drive/status", headers=H)
    if r.status_code != 200:
        return False
    j = r.json()
    return (
        j["feature_available"] is False
        and j["storage_mode"] == "managed"
        and j["drive_connected"] is False
        and j["drive_root_folder_name"] == "Personal Data Bank"
        and j["drive_schema_version"] == "1.0"
    )
t("status: feature_available=False, mode=managed, folder='Personal Data Bank'", t1)
t("status without auth -> 401/403",
  lambda: c.get("/api/drive/status").status_code in (401, 403))


print("\n=== 2. 503 fallback when BYOS not configured ===")
def is_503_with_code(r):
    if r.status_code != 503:
        return False
    body = r.json()
    return body.get("detail", {}).get("error", {}).get("code") == "GOOGLE_OAUTH_NOT_CONFIGURED"

t("/api/drive/oauth/init -> 503 GOOGLE_OAUTH_NOT_CONFIGURED",
  lambda: is_503_with_code(c.get("/api/drive/oauth/init", headers=H)))
t("/api/drive/oauth/callback -> 503",
  lambda: c.get("/api/drive/oauth/callback?code=x&state=y").status_code == 503)
t("POST /api/drive/disconnect -> 503",
  lambda: c.post("/api/drive/disconnect", headers=H).status_code == 503)
t("PUT /api/storage-mode -> 503",
  lambda: c.put("/api/storage-mode", headers=H, json={"mode": "byos"}).status_code == 503)


print("\n=== 3. DB schema migration applied ===")
def t3a():
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    async def check():
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute("PRAGMA table_info(users)")
            user_cols = {row[1] for row in await cur.fetchall()}
            if "storage_mode" not in user_cols:
                return False
            cur = await db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='drive_connections'"
            )
            if not await cur.fetchone():
                return False
            cur = await db.execute("PRAGMA table_info(files)")
            file_cols = {row[1] for row in await cur.fetchall()}
            return all(c in file_cols for c in ["drive_file_id", "drive_modified_time", "storage_source"])
    return asyncio.run(check())
t("Schema: users.storage_mode + drive_connections table + files.drive_*", t3a)
t("New user defaults to storage_mode=managed",
  lambda: c.get("/api/drive/status", headers=H).json()["storage_mode"] == "managed")


print("\n=== 4. drive_connections column structure ===")
def t4():
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    async def check():
        async with aiosqlite.connect(db_path) as db:
            cur = await db.execute("PRAGMA table_info(drive_connections)")
            cols = {row[1] for row in await cur.fetchall()}
            expected = {
                "id", "user_id", "drive_email", "refresh_token_encrypted",
                "drive_root_folder_id", "last_sync_at", "last_sync_status",
                "last_sync_error", "connected_at", "revoked_at",
            }
            return expected.issubset(cols)
    return asyncio.run(check())
t("drive_connections has all expected columns", t4)


print("\n=== 5. Fernet encrypt/decrypt round-trip ===")
def t5a():
    set_byos_env()
    from backend import drive_oauth as _do
    importlib.reload(_do)
    plaintext = "1//04abcDEF_test_refresh_token_xyz"
    enc = _do.encrypt_refresh_token(plaintext)
    dec = _do.decrypt_refresh_token(enc)
    return dec == plaintext and enc != plaintext and len(enc) > len(plaintext)
t("encrypt -> decrypt round-trip preserves plaintext + cipher differs", t5a)

def t5b():
    """Decrypt with rotated key must raise RuntimeError."""
    set_byos_env()
    from backend import drive_oauth as _do
    importlib.reload(_do)
    enc = _do.encrypt_refresh_token("secret-token")
    # Rotate to new key
    set_byos_env()
    importlib.reload(_do)
    try:
        _do.decrypt_refresh_token(enc)
        return False
    except RuntimeError:
        return True
    finally:
        clear_byos_env()
t("Decrypt with rotated key -> RuntimeError (force re-connect)", t5b)


print("\n=== 6. drive_layout helpers ===")
clear_byos_env()
from backend.drive_layout import (
    raw_path_for, extracted_path_for, summary_path_for, is_google_native,
    VALID_STORAGE_MODES, VALID_STORAGE_SOURCES, DRIVE_ROOT_FOLDER_NAME,
    DRIVE_SCHEMA_VERSION, SUB_FOLDERS,
)
t("path helpers produce expected paths",
  lambda: (raw_path_for("abc123", "report.pdf") == "raw/abc123_report.pdf"
           and extracted_path_for("abc123") == "extracted/abc123.txt"
           and summary_path_for("abc123") == "summaries/abc123.md"))
t("is_google_native: docs=True, pdf=False",
  lambda: is_google_native("application/vnd.google-apps.document") and not is_google_native("application/pdf"))
t("VALID_STORAGE_MODES = {managed, byos}",
  lambda: VALID_STORAGE_MODES == {"managed", "byos"})
t("VALID_STORAGE_SOURCES has 3 expected values",
  lambda: VALID_STORAGE_SOURCES == {"local", "drive_uploaded", "drive_picked"})
t("Folder name = 'Personal Data Bank' (rebrand-aligned)",
  lambda: DRIVE_ROOT_FOLDER_NAME == "Personal Data Bank")
t("Schema version = '1.0'",
  lambda: DRIVE_SCHEMA_VERSION == "1.0")
t("7 sub-folders defined",
  lambda: set(SUB_FOLDERS) == {"raw", "extracted", "summaries", "personal", "data", "_meta", "_backups"})


print("\n=== 7. is_byos_configured() truth table ===")
def t7():
    clear_byos_env()
    cfg = reload_cfg()
    if cfg.is_byos_configured():
        return False
    # Set 2/3 -> still False
    os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "x"
    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "y"
    cfg = reload_cfg()
    if cfg.is_byos_configured():
        return False
    # Set all 3 -> True
    from cryptography.fernet import Fernet
    os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    cfg = reload_cfg()
    if not cfg.is_byos_configured():
        return False
    clear_byos_env()
    return not reload_cfg().is_byos_configured()
t("is_byos_configured(): all 3 env vars required", t7)


print("\n=== 8. Storage mode validation (when configured) ===")
def t8a():
    set_byos_env()
    from fastapi.testclient import TestClient as TC
    from backend.main import app as _app
    c2 = TC(_app)
    r = c2.put("/api/storage-mode", headers=H, json={"mode": "invalid_xyz"})
    clear_byos_env()
    return r.status_code == 400 and "INVALID_STORAGE_MODE" in r.text
t("PUT /api/storage-mode with invalid mode -> 400 INVALID_STORAGE_MODE", t8a)

def t8b():
    set_byos_env()
    from fastapi.testclient import TestClient as TC
    from backend.main import app as _app
    c2 = TC(_app)
    r = c2.put("/api/storage-mode", headers=H, json={"mode": "byos"})
    clear_byos_env()
    return r.status_code == 400 and "BYOS_REQUIRES_DRIVE_CONNECTION" in r.text
t("PUT /api/storage-mode mode=byos w/o drive_connection -> 400 BYOS_REQUIRES_DRIVE_CONNECTION", t8b)

def t8c():
    set_byos_env()
    from fastapi.testclient import TestClient as TC
    from backend.main import app as _app
    c2 = TC(_app)
    r = c2.put("/api/storage-mode", headers=H, json={"mode": "managed"})
    clear_byos_env()
    return r.status_code == 200 and r.json()["storage_mode"] == "managed"
t("PUT /api/storage-mode mode=managed -> 200 (managed always allowed)", t8c)


print("\n=== 9. Disconnect without connection ===")
def t9():
    set_byos_env()
    from fastapi.testclient import TestClient as TC
    from backend.main import app as _app
    c2 = TC(_app)
    r = c2.post("/api/drive/disconnect", headers=H)
    clear_byos_env()
    return r.status_code == 404 and "NO_DRIVE_CONNECTION" in r.text
t("POST /api/drive/disconnect w/o connection -> 404 NO_DRIVE_CONNECTION", t9)


print("\n=== 10. OAuth callback edge cases (when configured) ===")
def t10a():
    set_byos_env()
    from fastapi.testclient import TestClient as TC
    from backend.main import app as _app
    c2 = TC(_app, follow_redirects=False)
    # User denied consent
    r = c2.get("/api/drive/oauth/callback?error=access_denied")
    clear_byos_env()
    return r.status_code in (302, 307) and "drive_connected=false" in r.headers.get("location", "")
t("OAuth callback with error=access_denied -> redirect with drive_connected=false", t10a)

def t10b():
    set_byos_env()
    from fastapi.testclient import TestClient as TC
    from backend.main import app as _app
    c2 = TC(_app)
    # Missing code/state
    r = c2.get("/api/drive/oauth/callback")
    clear_byos_env()
    return r.status_code == 400 and "MISSING_OAUTH_PARAMS" in r.text
t("OAuth callback w/o code+state -> 400 MISSING_OAUTH_PARAMS", t10b)

def t10c():
    set_byos_env()
    from fastapi.testclient import TestClient as TC
    from backend.main import app as _app
    c2 = TC(_app)
    # Invalid state (not in CSRF cache)
    r = c2.get("/api/drive/oauth/callback?code=fakecode&state=neverissued")
    clear_byos_env()
    return r.status_code == 400 and "INVALID_OAUTH_STATE" in r.text
t("OAuth callback with unknown state -> 400 INVALID_OAUTH_STATE", t10c)


print(f"\n{'=' * 60}")
print(f"  RESULT: {PASS} passed / {FAIL} failed")
print(f"{'=' * 60}")
sys.exit(0 if FAIL == 0 else 1)
