"""Tests for LINE Bot Foundation (v8.0.0 Phase D).

Coverage:
- D.1 verify_signature() function (5 cases)
- D.2 POST /webhook/line endpoint (5 cases)
- D.3 LineUser model + DB operations (3 cases)
- D.4 BotAdapter abstraction (3 cases)
- D.5 handle_line_event dispatcher (4 cases)

Total: 20 cases (Phase D foundation, not full LINE bot)
"""
import asyncio
import base64
import hashlib
import hmac
import json
import os
import importlib
import pytest


# ═══════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════

def _sign_body(body: bytes, secret: str) -> str:
    """Helper: compute valid X-Line-Signature for testing."""
    return base64.b64encode(
        hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")


@pytest.fixture
def line_secret(monkeypatch):
    """Set LINE_CHANNEL_SECRET + LINE_CHANNEL_ACCESS_TOKEN for test, return secret."""
    secret = "test_channel_secret_abc"
    monkeypatch.setenv("LINE_CHANNEL_SECRET", secret)
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_access_token_xyz")
    # Reload config + line_bot to pick up env
    from backend import config, line_bot
    importlib.reload(config)
    importlib.reload(line_bot)
    return secret


@pytest.fixture
def no_line_config(monkeypatch):
    """Clear LINE config — feature disabled."""
    monkeypatch.delenv("LINE_CHANNEL_SECRET", raising=False)
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    from backend import config, line_bot
    importlib.reload(config)
    importlib.reload(line_bot)


# ═══════════════════════════════════════════
# D.1 — verify_signature() (5 cases)
# ═══════════════════════════════════════════

def test_d1_1_no_config_returns_false(no_line_config):
    """D1.1: no LINE_CHANNEL_SECRET → False (fail closed)"""
    from backend.line_bot import verify_signature
    result = verify_signature(b"{}", "any-signature")
    assert result is False


def test_d1_2_missing_signature_returns_false(line_secret):
    """D1.2: signature header is None → False"""
    from backend.line_bot import verify_signature
    result = verify_signature(b"{}", None)
    assert result is False


def test_d1_3_valid_signature_returns_true(line_secret):
    """D1.3: signature matches HMAC → True"""
    from backend.line_bot import verify_signature
    body = b'{"events":[]}'
    sig = _sign_body(body, line_secret)
    assert verify_signature(body, sig) is True


def test_d1_4_wrong_signature_returns_false(line_secret):
    """D1.4: signature doesn't match → False"""
    from backend.line_bot import verify_signature
    body = b'{"events":[]}'
    bad_sig = _sign_body(body, "DIFFERENT_SECRET")
    assert verify_signature(body, bad_sig) is False


def test_d1_5_tampered_body_returns_false(line_secret):
    """D1.5: body tampered after sign → False"""
    from backend.line_bot import verify_signature
    original_body = b'{"events":[]}'
    sig = _sign_body(original_body, line_secret)
    tampered_body = b'{"events":[{"type":"message"}]}'  # added content
    assert verify_signature(tampered_body, sig) is False


# ═══════════════════════════════════════════
# D.2 — POST /webhook/line endpoint (5 cases)
# ═══════════════════════════════════════════

@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


def test_d2_1_no_config_503(test_client, no_line_config):
    """D2.1: LINE not configured → 503 LINE_NOT_CONFIGURED"""
    resp = test_client.post("/webhook/line", content=b"{}", headers={"X-Line-Signature": "any"})
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "LINE_NOT_CONFIGURED"


def test_d2_2_invalid_signature_401(test_client, line_secret):
    """D2.2: signature invalid → 401 INVALID_SIGNATURE"""
    resp = test_client.post(
        "/webhook/line",
        content=b'{"events":[]}',
        headers={"X-Line-Signature": "definitely-wrong-sig"},
    )
    assert resp.status_code == 401
    body = resp.json()
    assert body["detail"]["error"]["code"] == "INVALID_SIGNATURE"


def test_d2_3_valid_signature_200_ack(test_client, line_secret):
    """D2.3: valid signature + empty events → 200 ack"""
    body = b'{"events":[]}'
    sig = _sign_body(body, line_secret)
    resp = test_client.post(
        "/webhook/line",
        content=body,
        headers={"X-Line-Signature": sig},
    )
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["events_received"] == 0


def test_d2_4_valid_signature_with_events_200(test_client, line_secret):
    """D2.4: valid signature + events → 200 + events_received count"""
    payload = {
        "events": [
            {"type": "follow", "source": {"userId": "U_TEST"}},
            {"type": "message", "source": {"userId": "U_TEST"}, "message": {"type": "text", "text": "hello"}},
        ]
    }
    body = json.dumps(payload).encode("utf-8")
    sig = _sign_body(body, line_secret)
    resp = test_client.post(
        "/webhook/line",
        content=body,
        headers={"X-Line-Signature": sig},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["events_received"] == 2


def test_d2_5_invalid_json_400(test_client, line_secret):
    """D2.5: valid sig but body not JSON → 400 INVALID_PAYLOAD"""
    body = b"not-valid-json"
    sig = _sign_body(body, line_secret)
    resp = test_client.post(
        "/webhook/line",
        content=body,
        headers={"X-Line-Signature": sig},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert data["detail"]["error"]["code"] == "INVALID_PAYLOAD"


# ═══════════════════════════════════════════
# D.3 — LineUser model (3 cases)
# ═══════════════════════════════════════════

def test_d3_1_line_user_table_exists():
    """D3.1: LineUser table exists in DB schema"""
    from backend.database import LineUser, Base
    assert LineUser.__tablename__ == "line_users"
    assert "line_user_id" in LineUser.__table__.columns
    assert "pdb_user_id" in LineUser.__table__.columns
    assert "link_nonce" in LineUser.__table__.columns
    assert "welcomed" in LineUser.__table__.columns


def test_d3_2_line_user_id_unique_constraint():
    """D3.2: line_user_id has unique=True"""
    from backend.database import LineUser
    col = LineUser.__table__.columns["line_user_id"]
    assert col.unique is True
    assert col.index is True


def test_d3_3_line_user_insert_select():
    """D3.3: Can insert + select LineUser row"""
    from backend.database import init_db, AsyncSessionLocal, LineUser, User, gen_id
    from sqlalchemy import select

    async def _do():
        await init_db()
        async with AsyncSessionLocal() as db:
            user_id = "test_user_d3"
            # Create User first (FK)
            existing = await db.execute(select(User).where(User.id == user_id))
            if not existing.scalar_one_or_none():
                u = User(id=user_id, name="D3 Test", email="d3@test.local")
                db.add(u)
                await db.commit()

            # Cleanup any leftover from previous run
            from sqlalchemy import delete
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
            await db.commit()

            # Insert LineUser
            line_user = LineUser(
                line_user_id="U_LINE_D3",
                pdb_user_id=user_id,
                link_nonce="test_nonce_d3",
                welcomed=False,
            )
            db.add(line_user)
            await db.commit()

            # Select back
            result = await db.execute(select(LineUser).where(LineUser.line_user_id == "U_LINE_D3"))
            found = result.scalar_one_or_none()
            assert found is not None
            assert found.pdb_user_id == user_id
            assert found.welcomed is False

            # Cleanup
            await db.delete(found)
            await db.commit()

    asyncio.run(_do())


# ═══════════════════════════════════════════
# D.4 — BotAdapter abstraction (3 cases)
# ═══════════════════════════════════════════

def test_d4_1_bot_message_dataclass():
    """D4.1: BotMessage dataclass works"""
    from backend.bot_adapters import BotMessage
    msg = BotMessage(text="hello", quick_reply=[{"label": "OK"}])
    assert msg.text == "hello"
    assert msg.flex is None
    assert msg.quick_reply == [{"label": "OK"}]


def test_d4_2_noop_adapter_does_nothing():
    """D4.2: NoopBotAdapter all methods return None without error"""
    from backend.bot_adapters import NoopBotAdapter, BotMessage

    async def _do():
        a = NoopBotAdapter()
        assert a.platform_name == "noop"
        assert await a.send_message("u1", BotMessage(text="hi")) is None
        assert await a.reply_message("token", BotMessage(text="hi")) is None
        attach = await a.download_attachment("msg_id")
        assert attach.message_id == "msg_id"
        assert attach.content == b""
        assert await a.show_typing("u1") is None

    asyncio.run(_do())


def test_d4_3_get_line_adapter_returns_none_when_unconfigured(no_line_config):
    """D4.3: get_line_adapter() = None when LINE not configured"""
    from backend import bot_adapters
    importlib.reload(bot_adapters)
    adapter = bot_adapters.get_line_adapter()
    assert adapter is None


# ═══════════════════════════════════════════
# D.5 — handle_line_event dispatcher (4 cases)
# ═══════════════════════════════════════════

def test_d5_1_dispatch_follow_event():
    """D5.1: follow event dispatched to placeholder (no error)"""
    from backend.line_bot import handle_line_event

    async def _do():
        await handle_line_event({"type": "follow", "source": {"userId": "U_TEST"}})

    asyncio.run(_do())  # should not raise


def test_d5_2_dispatch_message_event():
    """D5.2: message event dispatched (no error)"""
    from backend.line_bot import handle_line_event

    async def _do():
        await handle_line_event({
            "type": "message",
            "source": {"userId": "U_TEST"},
            "message": {"type": "text", "text": "hi"},
        })

    asyncio.run(_do())


def test_d5_3_dispatch_unknown_event():
    """D5.3: unknown event type → log warning, no error"""
    from backend.line_bot import handle_line_event

    async def _do():
        await handle_line_event({"type": "unknown_xyz", "source": {"userId": "U_TEST"}})

    asyncio.run(_do())


def test_d5_4_handler_exception_caught():
    """D5.4: if handler raises → handle_line_event catches + logs (doesn't propagate)"""
    from backend import line_bot

    # Monkeypatch the message handler to raise (renamed from _handle_message_placeholder
    # to _handle_message in Phase E full)
    original = line_bot._handle_message

    async def _bad_handler(event):
        raise RuntimeError("simulated handler error")

    line_bot._handle_message = _bad_handler
    try:
        async def _do():
            # Should not raise — exception caught inside handle_line_event
            await line_bot.handle_line_event({
                "type": "message",
                "source": {"userId": "U"},
                "message": {"type": "text"},
            })

        asyncio.run(_do())
    finally:
        line_bot._handle_message = original
