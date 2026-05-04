"""Tests for LINE Bot Phase E + J (account link + profile UI endpoints).

Phase E (account linking — partial in Phase D scaffold):
- /api/line/confirm-link
- /auth/line landing page

Phase J (profile UI):
- /api/line/status
- /api/line/connect
- /api/line/disconnect

These tests focus on backend endpoint behavior — frontend rendering
ทดสอบใน Playwright E2E ภายหลัง.
"""
import asyncio
import importlib
import pytest


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def line_full_config(monkeypatch):
    """Set both Messaging API + LINE Login env vars."""
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test_secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("LINE_LOGIN_CHANNEL_ID", "test_login_id")
    monkeypatch.setenv("LINE_LOGIN_CHANNEL_SECRET", "test_login_secret")
    monkeypatch.setenv("LINE_BOT_BASIC_ID", "@PDBBot")
    from backend import config, line_bot
    importlib.reload(config)
    importlib.reload(line_bot)


@pytest.fixture
def line_messaging_only(monkeypatch):
    """Messaging API set, LINE Login not."""
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test_secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
    monkeypatch.delenv("LINE_LOGIN_CHANNEL_ID", raising=False)
    monkeypatch.delenv("LINE_LOGIN_CHANNEL_SECRET", raising=False)
    from backend import config, line_bot
    importlib.reload(config)
    importlib.reload(line_bot)


@pytest.fixture
def line_unconfigured(monkeypatch):
    """All LINE env vars cleared."""
    for var in ("LINE_CHANNEL_SECRET", "LINE_CHANNEL_ACCESS_TOKEN",
                "LINE_LOGIN_CHANNEL_ID", "LINE_LOGIN_CHANNEL_SECRET",
                "LINE_BOT_BASIC_ID"):
        monkeypatch.delenv(var, raising=False)
    from backend import config, line_bot
    importlib.reload(config)
    importlib.reload(line_bot)


@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


def _register_user(client, email="ej@test.local", password="testpass123"):
    """Register a fresh user + return auth token."""
    resp = client.post("/api/auth/register", json={
        "email": email, "password": password, "name": "EJ Test"
    })
    if resp.status_code == 200:
        return resp.json()["token"]
    # If exists, login instead
    resp = client.post("/api/auth/login", json={"email": email, "password": password})
    return resp.json()["token"]


# ═══════════════════════════════════════════
# Phase J — /api/line/status (5 cases)
# ═══════════════════════════════════════════

def test_j1_status_unauthorized_401(test_client):
    """J1: no auth header → 401"""
    resp = test_client.get("/api/line/status")
    assert resp.status_code == 401


def test_j2_status_feature_disabled(test_client, line_unconfigured):
    """J2: LINE not configured → feature_available=False"""
    token = _register_user(test_client, email="j2@test.local")
    resp = test_client.get("/api/line/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature_available"] is False
    assert data["linked"] is False


def test_j3_status_not_linked(test_client, line_full_config):
    """J3: configured + user not linked → linked=False + bot_url"""
    token = _register_user(test_client, email="j3@test.local")
    resp = test_client.get("/api/line/status", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature_available"] is True
    assert data["linked"] is False
    assert data.get("bot_basic_id") == "@PDBBot"
    assert "line.me/R/ti/p/" in data.get("bot_url", "")


def test_j4_status_linked(test_client, line_full_config):
    """J4: linked LineUser exists → linked=True + display info"""
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete
    from datetime import datetime as _dt

    token = _register_user(test_client, email="j4@test.local")

    # Manually insert linked LineUser row
    async def _setup():
        async with AsyncSessionLocal() as db:
            user = await db.execute(select(User).where(User.email == "j4@test.local"))
            u = user.scalar_one()
            # Cleanup any leftover
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u.id))
            await db.commit()
            row = LineUser(
                pdb_user_id=u.id,
                line_user_id="U_J4_TEST",
                line_display_name="J4 Tester",
                linked_at=_dt.utcnow(),
                last_seen_at=_dt.utcnow(),
            )
            db.add(row)
            await db.commit()
            return u.id

    pdb_user_id = asyncio.run(_setup())

    try:
        resp = test_client.get("/api/line/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["feature_available"] is True
        assert data["linked"] is True
        assert data["line_user_id"] == "U_J4_TEST"
        assert data["line_display_name"] == "J4 Tester"
        assert data["linked_at"] is not None
    finally:
        # Cleanup
        async def _cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == pdb_user_id))
                await db.commit()
        asyncio.run(_cleanup())


def test_j5_status_unlinked_excluded(test_client, line_full_config):
    """J5: row with unlinked_at != None → linked=False (soft-unlink respected)"""
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete
    from datetime import datetime as _dt

    token = _register_user(test_client, email="j5@test.local")

    async def _setup():
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.email == "j5@test.local"))).scalar_one()
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u.id))
            await db.commit()
            row = LineUser(
                pdb_user_id=u.id,
                line_user_id="U_J5_TEST",
                unlinked_at=_dt.utcnow(),  # soft-unlinked
            )
            db.add(row)
            await db.commit()
            return u.id

    pdb_user_id = asyncio.run(_setup())

    try:
        resp = test_client.get("/api/line/status", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["linked"] is False  # soft-unlinked → not linked
    finally:
        async def _c():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == pdb_user_id))
                await db.commit()
        asyncio.run(_c())


# ═══════════════════════════════════════════
# Phase J — /api/line/connect (3 cases)
# ═══════════════════════════════════════════

def test_j6_connect_no_login_config(test_client, line_messaging_only):
    """J6: LINE_LOGIN not configured → 503 LINE_LOGIN_NOT_CONFIGURED"""
    token = _register_user(test_client, email="j6@test.local")
    resp = test_client.post("/api/line/connect", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "LINE_LOGIN_NOT_CONFIGURED"


def test_j7_connect_returns_redirect(test_client, line_full_config):
    """J7: configured → 200 + redirect_url"""
    token = _register_user(test_client, email="j7@test.local")
    resp = test_client.post("/api/line/connect", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "redirect_url" in data
    assert "/auth/line" in data["redirect_url"]


def test_j8_connect_unauthorized(test_client):
    """J8: no auth → 401"""
    resp = test_client.post("/api/line/connect")
    assert resp.status_code == 401


# ═══════════════════════════════════════════
# Phase J — /api/line/disconnect (3 cases)
# ═══════════════════════════════════════════

def test_j9_disconnect_not_linked_404(test_client, line_full_config):
    """J9: no LineUser row → 404 NOT_LINKED"""
    token = _register_user(test_client, email="j9@test.local")
    resp = test_client.post("/api/line/disconnect", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 404
    body = resp.json()
    # JSONResponse returns body directly (not wrapped in 'detail' like HTTPException)
    assert body["error"]["code"] == "NOT_LINKED"


def test_j10_disconnect_sets_unlinked_at(test_client, line_full_config):
    """J10: linked → POST → unlinked_at set"""
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete
    from datetime import datetime as _dt

    token = _register_user(test_client, email="j10@test.local")

    async def _setup():
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.email == "j10@test.local"))).scalar_one()
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u.id))
            await db.commit()
            db.add(LineUser(pdb_user_id=u.id, line_user_id="U_J10", linked_at=_dt.utcnow()))
            await db.commit()
            return u.id

    pdb_user_id = asyncio.run(_setup())

    try:
        resp = test_client.post("/api/line/disconnect", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["status"] == "disconnected"

        # Verify unlinked_at was set
        async def _verify():
            async with AsyncSessionLocal() as db:
                r = (await db.execute(select(LineUser).where(LineUser.pdb_user_id == pdb_user_id))).scalar_one()
                return r.unlinked_at
        unlinked = asyncio.run(_verify())
        assert unlinked is not None
    finally:
        async def _c():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == pdb_user_id))
                await db.commit()
        asyncio.run(_c())


def test_j11_disconnect_unauthorized(test_client):
    """J11: no auth → 401"""
    resp = test_client.post("/api/line/disconnect")
    assert resp.status_code == 401


# ═══════════════════════════════════════════
# Phase E — /api/line/confirm-link (5 cases)
# ═══════════════════════════════════════════

def test_e1_confirm_no_config(test_client, line_unconfigured):
    """E1: LINE not configured → 503"""
    token = _register_user(test_client, email="e1@test.local")
    resp = test_client.post(
        "/api/line/confirm-link",
        json={"link_token": "some-token"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "LINE_NOT_CONFIGURED"


def test_e2_confirm_missing_link_token(test_client, line_full_config):
    """E2: empty link_token → 400 MISSING_LINK_TOKEN"""
    token = _register_user(test_client, email="e2@test.local")
    resp = test_client.post(
        "/api/line/confirm-link",
        json={"link_token": ""},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 400
    body = resp.json()
    assert body["detail"]["error"]["code"] == "MISSING_LINK_TOKEN"


def test_e3_confirm_creates_line_user_row(test_client, line_full_config):
    """E3: valid request → LineUser row created with nonce"""
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete

    token = _register_user(test_client, email="e3@test.local")

    # Cleanup any leftover
    async def _pre():
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.email == "e3@test.local"))).scalar_one()
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u.id))
            await db.commit()
            return u.id

    pdb_user_id = asyncio.run(_pre())

    try:
        resp = test_client.post(
            "/api/line/confirm-link",
            json={"link_token": "fake_link_token_for_test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # Phase E full impl: status="pending_link" (waiting for accountLink webhook)
        # redirect_url = LINE accountLink dialog URL with nonce
        assert data["status"] == "pending_link"
        assert "redirect_url" in data
        assert "access.line.me/dialog/bot/accountLink" in data["redirect_url"]
        assert "nonce=" in data["redirect_url"]

        # Verify row created
        async def _check():
            async with AsyncSessionLocal() as db:
                r = (await db.execute(select(LineUser).where(LineUser.pdb_user_id == pdb_user_id))).scalar_one()
                return r
        row = asyncio.run(_check())
        assert row.link_nonce is not None
        assert len(row.link_nonce) >= 16  # urlsafe(32) is plenty long
        assert row.link_nonce_expires_at is not None
        assert row.line_user_id is None  # not yet linked (needs accountLink event)
    finally:
        async def _c():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == pdb_user_id))
                await db.commit()
        asyncio.run(_c())


def test_e4_confirm_reuses_existing_row(test_client, line_full_config):
    """E4: existing LineUser row → updates nonce instead of creating duplicate"""
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete, func

    token = _register_user(test_client, email="e4@test.local")

    async def _pre():
        async with AsyncSessionLocal() as db:
            u = (await db.execute(select(User).where(User.email == "e4@test.local"))).scalar_one()
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u.id))
            await db.commit()
            db.add(LineUser(pdb_user_id=u.id, link_nonce="OLD_NONCE"))
            await db.commit()
            return u.id

    pdb_user_id = asyncio.run(_pre())

    try:
        resp = test_client.post(
            "/api/line/confirm-link",
            json={"link_token": "fake"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        async def _check():
            async with AsyncSessionLocal() as db:
                count = (await db.execute(
                    select(func.count(LineUser.id)).where(LineUser.pdb_user_id == pdb_user_id)
                )).scalar()
                row = (await db.execute(select(LineUser).where(LineUser.pdb_user_id == pdb_user_id))).scalar_one()
                return count, row.link_nonce
        count, nonce = asyncio.run(_check())
        assert count == 1  # not duplicated
        assert nonce != "OLD_NONCE"  # nonce rotated
    finally:
        async def _c():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == pdb_user_id))
                await db.commit()
        asyncio.run(_c())


def test_e5_confirm_unauthorized(test_client, line_full_config):
    """E5: no auth → 401"""
    resp = test_client.post(
        "/api/line/confirm-link",
        json={"link_token": "fake"},
    )
    assert resp.status_code == 401


# ═══════════════════════════════════════════
# Phase E — /auth/line landing page (1 case)
# ═══════════════════════════════════════════

def test_e6_auth_line_serves_html(test_client):
    """E6: GET /auth/line → 200 + HTML content"""
    resp = test_client.get("/auth/line")
    assert resp.status_code == 200
    assert "text/html" in resp.headers.get("Content-Type", "")
    body = resp.text
    assert "เชื่อมบัญชี LINE" in body or "auth-line" in body
    assert "auth-line.js" in body  # script tag present
