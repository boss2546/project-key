"""Tests for signed download URLs (v7.6.0 Section C).

Coverage:
- C1: sign + verify round-trip (8 cases)
- C2: token tampering (3 cases)
- C3: GET /d/{token} endpoint (10 cases)
- C4: get_file_link MCP tool (5 cases)

Total: 26 cases
"""
import asyncio
import pytest
from datetime import datetime, timedelta, timezone

from jose import jwt as jose_jwt

from backend.signed_urls import (
    sign_download_token,
    verify_download_token,
    DownloadTokenError,
    SCOPE_DOWNLOAD,
)
from backend.config import JWT_SECRET_KEY, JWT_ALGORITHM


# ═══════════════════════════════════════════
# C1 — Sign + Verify Round-trip
# ═══════════════════════════════════════════

def test_c1_1_sign_verify_default_ttl():
    """C1.1: sign with default TTL → verify returns payload"""
    token = sign_download_token("file_abc", "user_xyz")
    payload = verify_download_token(token)
    assert payload["file_id"] == "file_abc"
    assert payload["user_id"] == "user_xyz"
    assert payload["scope"] == SCOPE_DOWNLOAD
    assert "exp" in payload
    assert "iat" in payload


def test_c1_2_custom_ttl_5min():
    """C1.2: TTL 300s (5 min) → verify success"""
    token = sign_download_token("f1", "u1", ttl_seconds=300)
    payload = verify_download_token(token)
    assert payload["file_id"] == "f1"


def test_c1_3_custom_ttl_1hour():
    """C1.3: TTL 3600s (1 hour) → verify success"""
    token = sign_download_token("f1", "u1", ttl_seconds=3600)
    payload = verify_download_token(token)
    assert payload["file_id"] == "f1"


def test_c1_4_ttl_too_small_raises():
    """C1.4: TTL < 60s → ValueError"""
    with pytest.raises(ValueError, match="ttl_seconds must be"):
        sign_download_token("f1", "u1", ttl_seconds=59)


def test_c1_5_ttl_too_large_raises():
    """C1.5: TTL > 3600s → ValueError"""
    with pytest.raises(ValueError, match="ttl_seconds must be"):
        sign_download_token("f1", "u1", ttl_seconds=3601)


def test_c1_6_expired_token_link_expired():
    """C1.6: token with past exp → DownloadTokenError("LINK_EXPIRED")"""
    # Manually craft token with already-expired exp
    past = datetime.now(timezone.utc) - timedelta(seconds=10)
    payload = {
        "file_id": "f1",
        "user_id": "u1",
        "iat": past - timedelta(seconds=60),
        "exp": past,
        "scope": SCOPE_DOWNLOAD,
    }
    expired_token = jose_jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    with pytest.raises(DownloadTokenError) as exc:
        verify_download_token(expired_token)
    assert exc.value.code == "LINK_EXPIRED"


def test_c1_7_garbage_token_invalid():
    """C1.7: random string → DownloadTokenError("INVALID_TOKEN")"""
    with pytest.raises(DownloadTokenError) as exc:
        verify_download_token("not-a-jwt-at-all")
    assert exc.value.code == "INVALID_TOKEN"


def test_c1_8_wrong_scope_invalid():
    """C1.8: token with scope='login' → DownloadTokenError("INVALID_TOKEN")"""
    payload = {
        "file_id": "f1",
        "user_id": "u1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=60),
        "scope": "login",  # wrong scope
    }
    bad_token = jose_jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    with pytest.raises(DownloadTokenError) as exc:
        verify_download_token(bad_token)
    assert exc.value.code == "INVALID_TOKEN"


# ═══════════════════════════════════════════
# C2 — Token Tampering
# ═══════════════════════════════════════════

def test_c2_1_different_secret_invalid():
    """C2.1: token signed with different secret → INVALID_TOKEN"""
    payload = {
        "file_id": "f1",
        "user_id": "u1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=60),
        "scope": SCOPE_DOWNLOAD,
    }
    foreign_token = jose_jwt.encode(payload, "different-secret-key", algorithm=JWT_ALGORITHM)
    with pytest.raises(DownloadTokenError) as exc:
        verify_download_token(foreign_token)
    assert exc.value.code == "INVALID_TOKEN"


def test_c2_2_alg_none_rejected():
    """C2.2: alg=none attack → INVALID_TOKEN"""
    # Manually craft an unsigned token (alg=none)
    import base64, json
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps({
        "file_id": "f1",
        "user_id": "u1",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(seconds=60)).timestamp()),
        "scope": SCOPE_DOWNLOAD,
    }).encode()).rstrip(b"=").decode()
    none_token = f"{header}.{body}."
    with pytest.raises(DownloadTokenError) as exc:
        verify_download_token(none_token)
    assert exc.value.code == "INVALID_TOKEN"


def test_c2_3_missing_required_field_invalid():
    """C2.3: token missing file_id → INVALID_TOKEN"""
    payload = {
        # file_id missing
        "user_id": "u1",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(seconds=60),
        "scope": SCOPE_DOWNLOAD,
    }
    incomplete_token = jose_jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    with pytest.raises(DownloadTokenError) as exc:
        verify_download_token(incomplete_token)
    assert exc.value.code == "INVALID_TOKEN"


# ═══════════════════════════════════════════
# C3 — GET /d/{token} Endpoint
# ═══════════════════════════════════════════

@pytest.fixture
def test_client():
    """Provide a TestClient against the real FastAPI app."""
    from fastapi.testclient import TestClient
    from backend.main import app

    return TestClient(app)


def _create_test_file_row(user_id="test_user_abc", filename="test.txt", content=b"hello world"):
    """Helper: create a File row in DB + write physical file (sync wrapper for sync tests)."""
    return asyncio.run(_create_test_file_row_async(user_id, filename, content))


def _delete_test_file_row(file_id):
    """Helper: cleanup test file (sync wrapper for sync tests)."""
    asyncio.run(_delete_test_file_row_async(file_id))


async def _create_test_file_row_async(user_id="test_user_abc", filename="test.txt", content=b"hello world"):
    """Async helper for use inside async tests."""
    import os
    from backend.database import AsyncSessionLocal, File, gen_id, User
    from backend.config import UPLOAD_DIR
    from sqlalchemy import select as _select

    async with AsyncSessionLocal() as session:
        existing = await session.execute(_select(User).where(User.id == user_id))
        if not existing.scalar_one_or_none():
            u = User(id=user_id, name="Test User", email=f"{user_id}@test.local")
            session.add(u)

        file_id = gen_id()
        user_dir = os.path.join(UPLOAD_DIR, user_id)
        os.makedirs(user_dir, exist_ok=True)
        raw_path = os.path.join(user_dir, f"{file_id}_{filename}")
        with open(raw_path, "wb") as f:
            f.write(content)

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
        db_file = File(
            id=file_id,
            user_id=user_id,
            filename=filename,
            filetype=ext,
            raw_path=raw_path,
            extracted_text=content.decode("utf-8", errors="ignore"),
            processing_status="ready",
        )
        session.add(db_file)
        await session.commit()
        return file_id, raw_path


async def _delete_test_file_row_async(file_id):
    """Async helper for use inside async tests."""
    import os
    from backend.database import AsyncSessionLocal, File
    from sqlalchemy import select as _select

    async with AsyncSessionLocal() as session:
        result = await session.execute(_select(File).where(File.id == file_id))
        f = result.scalar_one_or_none()
        if f:
            if os.path.exists(f.raw_path):
                os.remove(f.raw_path)
            await session.delete(f)
            await session.commit()


def test_c3_1_happy_managed_user(test_client):
    """C3.1: valid token → 200 + file bytes"""
    file_id, raw_path = _create_test_file_row(filename="hello.txt", content=b"hello bot")
    try:
        token = sign_download_token(file_id, "test_user_abc", ttl_seconds=60)
        response = test_client.get(f"/d/{token}")
        assert response.status_code == 200
        assert response.content == b"hello bot"
        assert response.headers.get("Content-Disposition", "").startswith("attachment;")
        assert "hello.txt" in response.headers.get("Content-Disposition", "")
    finally:
        _delete_test_file_row(file_id)


def test_c3_3_expired_token_410(test_client):
    """C3.3: expired token → 410 LINK_EXPIRED"""
    file_id, _ = _create_test_file_row(filename="x.txt", content=b"x")
    try:
        # Craft expired token directly
        past = datetime.now(timezone.utc) - timedelta(seconds=10)
        payload = {
            "file_id": file_id,
            "user_id": "test_user_abc",
            "iat": past - timedelta(seconds=60),
            "exp": past,
            "scope": SCOPE_DOWNLOAD,
        }
        expired = jose_jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        response = test_client.get(f"/d/{expired}")
        assert response.status_code == 410
        body = response.json()
        assert body["detail"]["error"]["code"] == "LINK_EXPIRED"
    finally:
        _delete_test_file_row(file_id)


def test_c3_4_invalid_token_401(test_client):
    """C3.4: garbage token → 401 INVALID_TOKEN"""
    response = test_client.get("/d/this-is-not-a-jwt")
    assert response.status_code == 401
    body = response.json()
    assert body["detail"]["error"]["code"] == "INVALID_TOKEN"


def test_c3_5_cross_user_403(test_client):
    """C3.5: token user A but file belongs to user B → 403 WRONG_USER"""
    file_id, _ = _create_test_file_row(user_id="owner_user", filename="x.txt", content=b"x")
    try:
        # Sign token with a different user_id than file owner
        token = sign_download_token(file_id, "attacker_user", ttl_seconds=60)
        response = test_client.get(f"/d/{token}")
        assert response.status_code == 403
        body = response.json()
        assert body["detail"]["error"]["code"] == "WRONG_USER"
    finally:
        _delete_test_file_row(file_id)


def test_c3_6_file_not_found_404(test_client):
    """C3.6: valid token but file_id ไม่อยู่ใน DB → 404 FILE_NOT_FOUND"""
    token = sign_download_token("nonexistent_file_id", "test_user_abc", ttl_seconds=60)
    response = test_client.get(f"/d/{token}")
    assert response.status_code == 404
    body = response.json()
    assert body["detail"]["error"]["code"] == "FILE_NOT_FOUND"


def test_c3_8_cache_headers(test_client):
    """C3.8: response มี Cache-Control: private, no-store"""
    file_id, _ = _create_test_file_row(filename="x.txt", content=b"x")
    try:
        token = sign_download_token(file_id, "test_user_abc", ttl_seconds=60)
        response = test_client.get(f"/d/{token}")
        assert response.status_code == 200
        cache_control = response.headers.get("Cache-Control", "")
        assert "private" in cache_control
        assert "no-store" in cache_control
    finally:
        _delete_test_file_row(file_id)


def test_c3_9_content_disposition_filename(test_client):
    """C3.9: Content-Disposition ระบุ filename"""
    file_id, _ = _create_test_file_row(filename="thesis-2026.pdf", content=b"%PDF-fake")
    try:
        token = sign_download_token(file_id, "test_user_abc", ttl_seconds=60)
        response = test_client.get(f"/d/{token}")
        assert response.status_code == 200
        cd = response.headers.get("Content-Disposition", "")
        assert "thesis-2026.pdf" in cd
        assert "attachment" in cd
    finally:
        _delete_test_file_row(file_id)


# ═══════════════════════════════════════════
# C4 — get_file_link MCP Tool
# ═══════════════════════════════════════════

@pytest.mark.asyncio
async def test_c4_1_happy_default_ttl():
    """C4.1: tool call default → URL valid 30 min, expires_at ISO"""
    from backend.mcp_tools import _tool_get_file_link
    from backend.database import AsyncSessionLocal

    file_id, _ = await _create_test_file_row_async(filename="report.pdf", content=b"%PDF-fake")
    try:
        async with AsyncSessionLocal() as db:
            result = await _tool_get_file_link(db, "test_user_abc", file_id)
        assert "url" in result
        assert "/d/" in result["url"]
        assert result["filename"] == "report.pdf"
        assert result["ttl_minutes"] == 30
        assert "expires_at" in result
    finally:
        await _delete_test_file_row_async(file_id)


@pytest.mark.asyncio
async def test_c4_2_custom_ttl_60min():
    """C4.2: ttl_minutes=60 → TTL clamped 60 (within max)"""
    from backend.mcp_tools import _tool_get_file_link
    from backend.database import AsyncSessionLocal

    file_id, _ = await _create_test_file_row_async(filename="x.txt", content=b"x")
    try:
        async with AsyncSessionLocal() as db:
            result = await _tool_get_file_link(db, "test_user_abc", file_id, ttl_minutes=60)
        assert result["ttl_minutes"] == 60
    finally:
        await _delete_test_file_row_async(file_id)


@pytest.mark.asyncio
async def test_c4_3_ttl_clamp_min():
    """C4.3: ttl_minutes=2 (too small) → clamped to 5"""
    from backend.mcp_tools import _tool_get_file_link
    from backend.database import AsyncSessionLocal

    file_id, _ = await _create_test_file_row_async(filename="x.txt", content=b"x")
    try:
        async with AsyncSessionLocal() as db:
            result = await _tool_get_file_link(db, "test_user_abc", file_id, ttl_minutes=2)
        assert result["ttl_minutes"] == 5
    finally:
        await _delete_test_file_row_async(file_id)


@pytest.mark.asyncio
async def test_c4_4_ttl_clamp_max():
    """C4.4: ttl_minutes=120 (too large) → clamped to 60"""
    from backend.mcp_tools import _tool_get_file_link
    from backend.database import AsyncSessionLocal

    file_id, _ = await _create_test_file_row_async(filename="x.txt", content=b"x")
    try:
        async with AsyncSessionLocal() as db:
            result = await _tool_get_file_link(db, "test_user_abc", file_id, ttl_minutes=120)
        assert result["ttl_minutes"] == 60
    finally:
        await _delete_test_file_row_async(file_id)


@pytest.mark.asyncio
async def test_c4_5_wrong_user_returns_error():
    """C4.5: file_id ของ user อื่น → return error"""
    from backend.mcp_tools import _tool_get_file_link
    from backend.database import AsyncSessionLocal

    file_id, _ = await _create_test_file_row_async(user_id="other_user", filename="x.txt", content=b"x")
    try:
        async with AsyncSessionLocal() as db:
            result = await _tool_get_file_link(db, "wrong_caller", file_id)
        assert "error" in result
    finally:
        await _delete_test_file_row_async(file_id)
