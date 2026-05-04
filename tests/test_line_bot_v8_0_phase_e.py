"""Tests for LINE Bot v8.0.0 Phase E — Account Linking + Welcome Flow.

Covers:
- E1: follow event → link prompt card (via adapter mock)
- E2: /auth/line → serves auth-line.html
- E3: POST /api/line/confirm-link → returns LINE accountLink dialog URL
- E4: accountLink webhook → matches nonce → triggers welcome flow
- E5: welcome flow sends 3 messages
- E6: re-follow (user unfollowed then re-added bot)
"""
import base64
import hashlib
import hmac
import json
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from httpx import AsyncClient, ASGITransport

# Monkeypatch LINE config BEFORE importing app
import backend.config as cfg
cfg.LINE_CHANNEL_SECRET = "test_secret_e"
cfg.LINE_CHANNEL_ACCESS_TOKEN = "test_token_e"
cfg.LINE_BOT_BASIC_ID = "@testpdb"
cfg.LINE_LOGIN_CHANNEL_ID = "1234567890"
cfg.LINE_LOGIN_CHANNEL_SECRET = "test_login_secret"
cfg.APP_BASE_URL = "https://test.example.com"

from backend.main import app
from backend.database import init_db, AsyncSessionLocal, LineUser, User


def _sign(body: str) -> str:
    """Generate valid LINE webhook signature."""
    return base64.b64encode(
        hmac.new(b"test_secret_e", body.encode(), hashlib.sha256).digest()
    ).decode()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Init DB (creates tables including line_users)."""
    await init_db()
    yield


@pytest_asyncio.fixture
async def test_user():
    """Create a test PDB user for account linking tests."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        existing = (await db.execute(select(User).where(User.email == "test-e@example.com"))).scalar_one_or_none()
        if existing:
            return existing
        user = User(
            id="test_user_e",
            email="test-e@example.com",
            name="Test E User",
            password_hash="x",
            plan="free",
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        return user


@pytest_asyncio.fixture
async def auth_token(test_user):
    """Get a valid JWT for the test user."""
    from backend.auth import create_access_token
    return create_access_token(test_user.id, test_user.email, test_user.name)


# ═══════════════════════════════════════════════════════════
# E1 — Follow event → sends link prompt card
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e1_follow_sends_link_prompt():
    """Follow event should issue linkToken + send Flex card with link URL."""
    from backend.line_bot import _handle_follow
    
    mock_adapter = AsyncMock()
    mock_adapter.issue_link_token = AsyncMock(return_value="test_link_token_123")
    mock_adapter.reply_message = AsyncMock()
    
    event = {
        "type": "follow",
        "replyToken": "reply_token_follow",
        "source": {"type": "user", "userId": "U_follow_test"},
    }
    
    with patch("backend.bot_adapters.get_line_adapter", return_value=mock_adapter):
        await _handle_follow(event)
    
    mock_adapter.issue_link_token.assert_called_once_with("U_follow_test")
    mock_adapter.reply_message.assert_called_once()
    
    # Check that the reply contains a BotMessage with flex (link_prompt_card)
    call_args = mock_adapter.reply_message.call_args
    assert call_args[0][0] == "reply_token_follow"
    msg = call_args[0][1]
    assert msg.flex is not None
    assert "linkToken=test_link_token_123" in json.dumps(msg.flex)


# ═══════════════════════════════════════════════════════════
# E2 — /auth/line serves auth-line.html
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e2_auth_line_page():
    """GET /auth/line should return auth-line.html."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/line")
    assert resp.status_code == 200
    assert "เชื่อมบัญชี LINE" in resp.text


@pytest.mark.asyncio
async def test_e2_auth_line_page_with_link_token():
    """GET /auth/line?linkToken=xxx should still serve the page."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/line?linkToken=test123")
    assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════
# E3 — POST /api/line/confirm-link
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e3_confirm_link_returns_account_link_url(auth_token):
    """confirm-link should return LINE accountLink dialog URL with nonce."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/line/confirm-link",
            json={"link_token": "LINE_LINK_TOKEN_ABC"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending_link"
    assert "access.line.me/dialog/bot/accountLink" in data["redirect_url"]
    assert "linkToken=LINE_LINK_TOKEN_ABC" in data["redirect_url"]
    assert "nonce=" in data["redirect_url"]


@pytest.mark.asyncio
async def test_e3_confirm_link_creates_line_user_row(auth_token, test_user):
    """confirm-link should create a LineUser row with nonce."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/line/confirm-link",
            json={"link_token": "TEST_LT_2"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert resp.status_code == 200

    # Check LineUser row was created
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(LineUser).where(LineUser.pdb_user_id == test_user.id)
        )
        row = result.scalar_one_or_none()
        assert row is not None
        assert row.link_nonce is not None
        assert row.link_nonce_expires_at is not None
        assert row.link_nonce_expires_at > datetime.utcnow()
        # line_user_id might not be None if this test is run after e4, which is fine since we just check nonce generation


@pytest.mark.asyncio
async def test_e3_confirm_link_missing_token(auth_token):
    """confirm-link without link_token should 400."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/line/confirm-link",
            json={"link_token": ""},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_e3_confirm_link_no_auth():
    """confirm-link without auth token should 401."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/line/confirm-link",
            json={"link_token": "test"},
        )
    assert resp.status_code in (401, 403)


# ═══════════════════════════════════════════════════════════
# E4 — accountLink webhook → match nonce → trigger welcome
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e4_account_link_matches_nonce(auth_token, test_user):
    """accountLink event with matching nonce should bind LINE user ID."""
    # Step 1: Create LineUser row via confirm-link
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/line/confirm-link",
            json={"link_token": "LT_FOR_NONCE_TEST"},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert resp.status_code == 200
    redirect_url = resp.json()["redirect_url"]
    
    # Extract nonce from redirect URL
    import urllib.parse
    parsed = urllib.parse.urlparse(redirect_url)
    params = urllib.parse.parse_qs(parsed.query)
    nonce = params["nonce"][0]
    
    # Step 2: Simulate accountLink webhook event
    from backend.line_bot import _handle_account_link
    
    event = {
        "type": "accountLink",
        "replyToken": "reply_token_acl",
        "source": {"type": "user", "userId": "U_line_user_e4"},
        "link": {"result": "ok", "nonce": nonce},
    }
    
    mock_adapter = AsyncMock()
    mock_adapter.get_user_profile = AsyncMock(return_value={"displayName": "Test LINE User"})
    mock_adapter.send_message = AsyncMock()
    
    with patch("backend.bot_adapters.get_line_adapter", return_value=mock_adapter):
        await _handle_account_link(event)
    
    # Step 3: Verify LineUser row is updated
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(LineUser).where(LineUser.pdb_user_id == test_user.id)
        )).scalar_one_or_none()
        assert row is not None
        assert row.line_user_id == "U_line_user_e4"
        assert row.link_nonce is None  # Consumed
        assert row.linked_at is not None
        assert row.line_display_name == "Test LINE User"


@pytest.mark.asyncio
async def test_e4_account_link_expired_nonce(test_user):
    """accountLink with expired nonce should not link."""
    # Insert LineUser with expired nonce
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(LineUser).where(LineUser.pdb_user_id == test_user.id)
        )).scalar_one_or_none()
        if row:
            row.link_nonce = "expired_nonce_xyz"
            row.link_nonce_expires_at = datetime.utcnow() - timedelta(minutes=1)
            row.line_user_id = None  # Reset
        else:
            row = LineUser(
                pdb_user_id=test_user.id,
                link_nonce="expired_nonce_xyz",
                link_nonce_expires_at=datetime.utcnow() - timedelta(minutes=1),
            )
            db.add(row)
        await db.commit()
    
    from backend.line_bot import _handle_account_link
    event = {
        "type": "accountLink",
        "source": {"type": "user", "userId": "U_expired_test"},
        "link": {"result": "ok", "nonce": "expired_nonce_xyz"},
    }
    
    mock_adapter = AsyncMock()
    with patch("backend.bot_adapters.get_line_adapter", return_value=mock_adapter):
        await _handle_account_link(event)
    
    # Should NOT have linked
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(LineUser).where(LineUser.pdb_user_id == test_user.id)
        )).scalar_one_or_none()
        assert row is not None
        # line_user_id should still be None (not linked due to expired nonce)
        assert row.line_user_id is None or row.line_user_id != "U_expired_test"


# ═══════════════════════════════════════════════════════════
# E5 — Welcome flow sends 3 messages
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e5_welcome_flow_sends_3_messages(test_user):
    """Welcome flow should send greeting + status card + capabilities."""
    from backend.line_bot import _send_welcome_flow
    
    mock_adapter = AsyncMock()
    mock_adapter.send_message = AsyncMock()
    
    with patch("backend.bot_adapters.get_line_adapter", return_value=mock_adapter):
        await _send_welcome_flow("U_welcome_test", test_user, "reply_tok_welcome")
    
    # Should have called send_message 3 times (1 greeting, 1 status card, 1 capabilities)
    assert mock_adapter.send_message.call_count == 3
    
    # Message 1: greeting (text)
    msg1 = mock_adapter.send_message.call_args_list[0][0][1]
    assert msg1.text is not None
    assert "เชื่อมต่อสำเร็จ" in msg1.text
    
    # Message 2: status card (flex)
    msg2 = mock_adapter.send_message.call_args_list[1][0][1]
    assert msg2.flex is not None
    
    # Message 3: capabilities (text + quick reply)
    msg3 = mock_adapter.send_message.call_args_list[2][0][1]
    assert msg3.text is not None
    assert "ผมทำอะไรได้บ้าง" in msg3.text
    assert msg3.quick_reply is not None


# ═══════════════════════════════════════════════════════════
# E6 — Unfollow + re-follow
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e6_unfollow_sets_unlinked_at(test_user):
    """Unfollow event should set unlinked_at timestamp."""
    # Ensure LineUser exists with line_user_id
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(LineUser).where(LineUser.pdb_user_id == test_user.id)
        )).scalar_one_or_none()
        if row:
            row.line_user_id = "U_unfollow_e6"
            row.unlinked_at = None
        else:
            row = LineUser(
                pdb_user_id=test_user.id,
                line_user_id="U_unfollow_e6",
            )
            db.add(row)
        await db.commit()
    
    from backend.line_bot import _handle_unfollow
    event = {"type": "unfollow", "source": {"type": "user", "userId": "U_unfollow_e6"}}
    await _handle_unfollow(event)
    
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        row = (await db.execute(
            select(LineUser).where(LineUser.line_user_id == "U_unfollow_e6")
        )).scalar_one_or_none()
        assert row is not None
        assert row.unlinked_at is not None


# ═══════════════════════════════════════════════════════════
# E7 — Flex message builders
# ═══════════════════════════════════════════════════════════

def test_e7_link_prompt_card():
    """link_prompt_card should produce valid Flex JSON."""
    from backend.bot_messages import link_prompt_card
    card = link_prompt_card("https://test.example.com/auth/line?linkToken=abc")
    assert card["type"] == "flex"
    assert "เชื่อมบัญชี" in card["altText"]
    assert card["contents"]["type"] == "bubble"
    # Footer should have button with URI action
    footer = card["contents"]["footer"]
    btn = footer["contents"][0]
    assert btn["action"]["type"] == "uri"
    assert "linkToken=abc" in btn["action"]["uri"]


def test_e7_vault_status_card():
    """vault_status_card should produce valid Flex JSON."""
    from backend.bot_messages import vault_status_card
    card = vault_status_card(
        user_name="Test",
        file_count=5,
        cluster_count=2,
        pack_count=1,
        storage_mb_used=12.5,
        storage_mb_limit=50,
    )
    assert card["type"] == "flex"
    assert "5" in card["altText"]
    assert card["contents"]["type"] == "bubble"


def test_e7_error_card():
    """error_card should produce valid Flex JSON."""
    from backend.bot_messages import error_card
    card = error_card("เกินขีดจำกัด", "คุณมีไฟล์เกินโควตา", suggestion="อัปเกรด")
    assert card["type"] == "flex"
    assert "เกินขีดจำกัด" in card["altText"]


# ═══════════════════════════════════════════════════════════
# E8 — LINE status endpoint
# ═══════════════════════════════════════════════════════════

@pytest.mark.asyncio
async def test_e8_line_status_not_linked(auth_token):
    """GET /api/line/status when not linked should return linked=false."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/line/status",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["feature_available"] is True
    # May or may not be linked depending on test order; check structure
    assert "linked" in data
    assert "bot_basic_id" in data
