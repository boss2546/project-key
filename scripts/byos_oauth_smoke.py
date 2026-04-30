"""BYOS v7.0 — drive_oauth.py unit tests (no real Google OAuth call).

Run: python scripts/byos_oauth_smoke.py

Strategy:
- Set fake env vars (CLIENT_ID/SECRET/ENCRYPTION_KEY) to satisfy is_byos_configured()
- Call encrypt/decrypt directly (no network)
- Test in-memory CSRF state cache
- Verify init_oauth doesn't call Google (no network — just builds URL string)
- Verify revoke_refresh_token returns False on connection error (graceful)
"""
from __future__ import annotations

import importlib
import os
import sys
import time

sys.path.insert(0, ".")

from cryptography.fernet import Fernet


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


def setup_env():
    """Ensure BYOS env vars set + reload config + drive_oauth modules."""
    os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "fake_client_id.apps.googleusercontent.com"
    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "GOCSPX-fake_secret_for_unit_test"
    os.environ["GOOGLE_OAUTH_REDIRECT_URI"] = "http://localhost:8000/api/drive/oauth/callback"
    os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    from backend import config as _cfg, drive_oauth as _do
    importlib.reload(_cfg)
    importlib.reload(_do)
    return _cfg, _do


def teardown_env():
    for k in ["GOOGLE_OAUTH_CLIENT_ID", "GOOGLE_OAUTH_CLIENT_SECRET",
              "GOOGLE_OAUTH_REDIRECT_URI", "DRIVE_TOKEN_ENCRYPTION_KEY"]:
        os.environ.pop(k, None)
    from backend import config as _cfg, drive_oauth as _do
    importlib.reload(_cfg)
    importlib.reload(_do)


# ═══════════════════════════════════════════════════════════════
print("=== 1. Encryption: Fernet round-trip ===")
# ═══════════════════════════════════════════════════════════════
def t1a():
    setup_env()
    from backend import drive_oauth as do
    plaintext = "1//04abcDEFGHIJK_test_refresh_token_xyz"
    enc = do.encrypt_refresh_token(plaintext)
    dec = do.decrypt_refresh_token(enc)
    teardown_env()
    return dec == plaintext and enc != plaintext
t("encrypt -> decrypt preserves plaintext + cipher differs", t1a)


def t1b():
    setup_env()
    from backend import drive_oauth as do
    enc = do.encrypt_refresh_token("ABC")
    enc2 = do.encrypt_refresh_token("ABC")
    teardown_env()
    # Fernet uses random IV → same plaintext, different cipher each time
    return enc != enc2
t("encrypt: same plaintext -> different cipher (random IV)", t1b)


def t1c():
    setup_env()
    from backend import drive_oauth as do
    payload = "x" * 10000  # 10KB payload — Drive refresh tokens are short, but
                           # Fernet should handle arbitrary size
    enc = do.encrypt_refresh_token(payload)
    dec = do.decrypt_refresh_token(enc)
    teardown_env()
    return dec == payload
t("encrypt/decrypt handles 10KB payload", t1c)


def t1d():
    setup_env()
    from backend import drive_oauth as do
    # Empty plaintext should still encrypt/decrypt
    enc = do.encrypt_refresh_token("")
    dec = do.decrypt_refresh_token(enc)
    teardown_env()
    return dec == ""
t("encrypt/decrypt handles empty string", t1d)


# ═══════════════════════════════════════════════════════════════
print("\n=== 2. Encryption: error paths ===")
# ═══════════════════════════════════════════════════════════════
def t2a():
    """Decrypt with rotated key -> RuntimeError."""
    setup_env()
    from backend import drive_oauth as do
    enc = do.encrypt_refresh_token("token-A")
    # Rotate key
    os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
    importlib.reload(__import__("backend.config", fromlist=[""]))
    importlib.reload(do)
    try:
        do.decrypt_refresh_token(enc)
        teardown_env()
        return False
    except RuntimeError as e:
        teardown_env()
        return "ถอด" in str(e) or "decrypt" in str(e).lower()
t("Decrypt with rotated key -> RuntimeError mentioning re-connect", t2a)


def t2b():
    """encrypt without env var -> RuntimeError."""
    teardown_env()
    from backend import drive_oauth as do
    try:
        do.encrypt_refresh_token("x")
        return False
    except RuntimeError:
        return True
t("encrypt without DRIVE_TOKEN_ENCRYPTION_KEY -> RuntimeError", t2b)


def t2c():
    """encrypt with invalid key format -> RuntimeError."""
    os.environ["DRIVE_TOKEN_ENCRYPTION_KEY"] = "not_a_valid_fernet_key_too_short"
    os.environ["GOOGLE_OAUTH_CLIENT_ID"] = "x"
    os.environ["GOOGLE_OAUTH_CLIENT_SECRET"] = "y"
    from backend import config as _cfg, drive_oauth as _do
    importlib.reload(_cfg)
    importlib.reload(_do)
    try:
        _do.encrypt_refresh_token("x")
        teardown_env()
        return False
    except RuntimeError as e:
        teardown_env()
        return "format" in str(e).lower() or "Fernet" in str(e)
t("encrypt with malformed key -> RuntimeError mentioning format", t2c)


# ═══════════════════════════════════════════════════════════════
print("\n=== 3. CSRF state cache ===")
# ═══════════════════════════════════════════════════════════════
def t3a():
    """init_oauth produces a unique state token + caches it."""
    setup_env()
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    r = do.init_oauth("user_001")
    state_in_url = "state=" in r["auth_url"]
    cache_size = len(do._STATE_CACHE)
    teardown_env()
    return state_in_url and cache_size == 1
t("init_oauth -> auth_url contains state= + cache has 1 entry", t3a)


def t3b():
    """Two init_oauth calls produce different states."""
    setup_env()
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    r1 = do.init_oauth("user_001")
    r2 = do.init_oauth("user_002")
    teardown_env()
    state1 = r1["auth_url"].split("state=")[1].split("&")[0]
    state2 = r2["auth_url"].split("state=")[1].split("&")[0]
    return state1 != state2
t("Two init_oauth calls -> different states", t3b)


def t3c():
    """auth_url includes drive.file scope + offline access."""
    setup_env()
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    r = do.init_oauth("user_001")
    url = r["auth_url"]
    teardown_env()
    return ("drive.file" in url
            and "access_type=offline" in url
            and "prompt=consent" in url
            and "client_id=fake_client_id" in url)
t("auth_url has drive.file scope + offline access + consent prompt + client_id", t3c)


def t3d():
    """Expired state is cleaned up on next access."""
    setup_env()
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    # Manually inject an expired entry
    do._STATE_CACHE["expired_state_token"] = {
        "user_id": "user_001",
        "expires": time.time() - 100,  # 100 seconds ago
    }
    do._cleanup_expired_states()
    teardown_env()
    return "expired_state_token" not in do._STATE_CACHE
t("_cleanup_expired_states removes entries past TTL", t3d)


def t3e():
    """init_oauth without GOOGLE_OAUTH_CLIENT_ID -> RuntimeError."""
    teardown_env()
    from backend import drive_oauth as do
    try:
        do.init_oauth("user_001")
        return False
    except RuntimeError as e:
        return "BYOS" in str(e) or "configure" in str(e).lower()
t("init_oauth without configure -> RuntimeError mentioning BYOS/configure", t3e)


def t3f():
    """auth_url uses redirect_uri from env."""
    setup_env()
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    r = do.init_oauth("user_001")
    teardown_env()
    # URL-encoded redirect_uri (slashes & colons get %-encoded)
    return ("redirect_uri=" in r["auth_url"]
            and ("localhost" in r["auth_url"] or "127.0.0.1" in r["auth_url"]))
t("auth_url contains redirect_uri matching env", t3f)


# ═══════════════════════════════════════════════════════════════
print("\n=== 4. handle_callback validation (no real Google) ===")
# ═══════════════════════════════════════════════════════════════
def t4a():
    """handle_callback with unknown state -> ValueError."""
    setup_env()
    import asyncio
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    try:
        asyncio.run(do.handle_callback("any-code", "never-issued-state"))
        teardown_env()
        return False
    except ValueError as e:
        teardown_env()
        return "INVALID_OAUTH_STATE" in str(e)
t("handle_callback with unknown state -> ValueError(INVALID_OAUTH_STATE)", t4a)


def t4b():
    """handle_callback with expired state -> ValueError."""
    setup_env()
    import asyncio
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    # Inject expired state (TTL passed)
    do._STATE_CACHE["s_expired"] = {
        "user_id": "user_001",
        "expires": time.time() - 1,
    }
    try:
        asyncio.run(do.handle_callback("any-code", "s_expired"))
        teardown_env()
        return False
    except ValueError:
        teardown_env()
        return True
t("handle_callback with expired state -> ValueError", t4b)


def t4c():
    """handle_callback consumes state (one-time use)."""
    setup_env()
    import asyncio
    from backend import drive_oauth as do
    do._reset_state_cache_for_testing()
    # First call should pop the state. If we add then call → cache empty.
    do._STATE_CACHE["s_test"] = {"user_id": "u1", "expires": time.time() + 600}
    # We can't actually fetch_token without real Google, but the function
    # pops state BEFORE network call. So even though it'll later fail,
    # the cache should be empty after.
    try:
        asyncio.run(do.handle_callback("any-code", "s_test"))
    except Exception:
        pass  # expected — fetch_token will fail without real Google
    cache_empty = "s_test" not in do._STATE_CACHE
    teardown_env()
    return cache_empty
t("handle_callback consumes state (one-time use)", t4c)


# ═══════════════════════════════════════════════════════════════
print("\n=== 5. Build credentials helper ===")
# ═══════════════════════════════════════════════════════════════
def t5a():
    setup_env()
    from backend import drive_oauth as do
    creds = do.build_credentials_from_refresh_token("plaintext_refresh_token")
    teardown_env()
    return (creds.refresh_token == "plaintext_refresh_token"
            and creds.client_id == "fake_client_id.apps.googleusercontent.com"
            and creds.token_uri == "https://oauth2.googleapis.com/token")
t("build_credentials_from_refresh_token sets all required fields", t5a)


def t5b():
    setup_env()
    from backend import drive_oauth as do
    creds = do.build_credentials_from_refresh_token("any")
    teardown_env()
    # Scopes should include drive.file
    return any("drive.file" in s for s in (creds.scopes or []))
t("Credentials.scopes includes drive.file", t5b)


# ═══════════════════════════════════════════════════════════════
print("\n=== 6. revoke_refresh_token graceful on network error ===")
# ═══════════════════════════════════════════════════════════════
def t6a():
    """revoke against unreachable Google should return False, not raise."""
    setup_env()
    from backend import drive_oauth as do
    # Monkey-patch httpx to simulate connection error
    import httpx
    original_post = httpx.post

    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("simulated network error")
    httpx.post = fake_post  # type: ignore[assignment]
    try:
        result = do.revoke_refresh_token("any-token")
        return result is False  # graceful False, no exception
    finally:
        httpx.post = original_post
        teardown_env()
t("revoke on network error -> False (graceful, no exception)", t6a)


# ═══════════════════════════════════════════════════════════════
print("\n=== 7. SCOPES configuration ===")
# ═══════════════════════════════════════════════════════════════
def t7():
    setup_env()
    from backend import drive_oauth as do
    teardown_env()
    return ("https://www.googleapis.com/auth/drive.file" in do.SCOPES
            and len(do.SCOPES) >= 1)  # at least drive.file (+ openid + email per design)
t("SCOPES contains drive.file (and minimal additional scopes)", t7)


print(f"\n{'=' * 60}")
print(f"  RESULT: {PASS} passed / {FAIL} failed")
print(f"{'=' * 60}")
sys.exit(0 if FAIL == 0 else 1)
