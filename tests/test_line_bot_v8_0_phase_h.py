"""Tests for LINE Bot Phase H — push fallback + quota + group leave + admin endpoint.

Coverage:
- QT: line_quota module (5 cases)
- FB: reply_message fallback to push (4 cases)
- GR: group/room join → leave (3 cases)
- AD: admin quota endpoint (3 cases)

Total: 15 cases
"""
import asyncio
import importlib
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def line_full_config(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test_secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("LINE_BOT_BASIC_ID", "@PDBBot")
    from backend import config, line_bot, bot_adapters
    importlib.reload(config)
    importlib.reload(line_bot)
    importlib.reload(bot_adapters)


@pytest.fixture
def quota_reset():
    """Reset quota counter before/after each test."""
    from backend import line_quota
    line_quota.reset()
    yield
    line_quota.reset()


@pytest.fixture
def test_client():
    from fastapi.testclient import TestClient
    from backend.main import app
    return TestClient(app)


def _register_user(client, email="h@test.local"):
    resp = client.post("/api/auth/register", json={
        "email": email, "password": "testpass123", "name": "H Test"
    })
    if resp.status_code == 200:
        return resp.json()["token"]
    resp = client.post("/api/auth/login", json={"email": email, "password": "testpass123"})
    return resp.json()["token"]


# ═══════════════════════════════════════════
# QT — line_quota module (5 cases)
# ═══════════════════════════════════════════

def test_qt1_initial_zero(quota_reset):
    from backend import line_quota
    usage = line_quota.get_current_usage()
    assert usage["pushes_used"] == 0
    assert usage["limit"] == 200
    assert usage["percent"] == 0.0
    assert usage["remaining"] == 200
    assert usage["exceeded"] is False


def test_qt2_record_push_increments(quota_reset):
    from backend import line_quota
    line_quota.record_push()
    line_quota.record_push()
    line_quota.record_push()
    usage = line_quota.get_current_usage()
    assert usage["pushes_used"] == 3
    assert usage["remaining"] == 197


def test_qt3_warning_at_80_percent(quota_reset, caplog):
    """Logs warning at 80% (160 pushes)"""
    import logging
    from backend import line_quota
    caplog.set_level(logging.WARNING, logger="backend.line_quota")
    for _ in range(160):
        line_quota.record_push()
    # Warning logged once at 80%
    assert any("80" in r.message for r in caplog.records)


def test_qt4_error_at_100_percent(quota_reset, caplog):
    """Logs error at 100% (200 pushes)"""
    import logging
    from backend import line_quota
    caplog.set_level(logging.WARNING, logger="backend.line_quota")
    for _ in range(200):
        line_quota.record_push()
    usage = line_quota.get_current_usage()
    assert usage["exceeded"] is True
    # Error logged at 100%
    assert any("EXCEEDED" in r.message for r in caplog.records)


def test_qt5_exceeded_flag(quota_reset):
    from backend import line_quota
    for _ in range(199):
        line_quota.record_push()
    assert line_quota.get_current_usage()["exceeded"] is False
    line_quota.record_push()
    assert line_quota.get_current_usage()["exceeded"] is True


# ═══════════════════════════════════════════
# FB — reply_message fallback to push (4 cases)
# ═══════════════════════════════════════════

def test_fb1_reply_success_no_fallback():
    """reply succeeds → no push fallback called"""
    from backend.bot_adapters import LineBotAdapter, BotMessage

    a = LineBotAdapter("token")
    captured = {"reply": 0, "push": 0}

    class _OkResp:
        status_code = 200
        text = ""

    class _ReplyClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers=None, json=None):
            if "reply" in url:
                captured["reply"] += 1
                return _OkResp()
            captured["push"] += 1
            return _OkResp()

    with patch("httpx.AsyncClient", _ReplyClient):
        ok = asyncio.run(a.reply_message("TKN", BotMessage(text="hi"), fallback_user_id="U1"))
    assert ok is True
    assert captured["reply"] == 1
    assert captured["push"] == 0


def test_fb2_reply_fail_falls_back_to_push():
    """reply fails (400) → push fallback called automatically"""
    from backend.bot_adapters import LineBotAdapter, BotMessage

    a = LineBotAdapter("token")
    captured = {"reply": 0, "push": 0}

    class _FailReply:
        status_code = 400
        text = "Invalid reply token"

    class _OkPush:
        status_code = 200
        text = ""

    class _Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers=None, json=None):
            if "reply" in url:
                captured["reply"] += 1
                return _FailReply()
            captured["push"] += 1
            return _OkPush()

    with patch("httpx.AsyncClient", _Client):
        ok = asyncio.run(a.reply_message("EXPIRED", BotMessage(text="hi"), fallback_user_id="U1"))
    assert ok is True
    assert captured["reply"] == 1
    assert captured["push"] == 1


def test_fb3_reply_fail_no_fallback_returns_false():
    """reply fails + no fallback_user_id → returns False"""
    from backend.bot_adapters import LineBotAdapter, BotMessage

    a = LineBotAdapter("token")

    class _FailReply:
        status_code = 400
        text = "expired"

    class _Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers=None, json=None):
            return _FailReply()

    with patch("httpx.AsyncClient", _Client):
        ok = asyncio.run(a.reply_message("EXPIRED", BotMessage(text="hi")))
    assert ok is False


def test_fb4_send_message_records_quota(quota_reset):
    """send_message → record_push called on success"""
    from backend.bot_adapters import LineBotAdapter, BotMessage
    from backend import line_quota

    a = LineBotAdapter("token")

    class _OkResp:
        status_code = 200
        text = ""

    class _Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            return _OkResp()

    with patch("httpx.AsyncClient", _Client):
        asyncio.run(a.send_message("U1", BotMessage(text="hi")))
    assert line_quota.get_current_usage()["pushes_used"] == 1


# ═══════════════════════════════════════════
# GR — group/room join → leave (3 cases)
# ═══════════════════════════════════════════

def test_gr1_group_join_calls_leave(line_full_config):
    """group join event → reply polite + call leave API"""
    from backend import line_bot, bot_adapters

    captured = {"reply": False, "leave_url": None}

    async def fake_reply(self, token, msg, **kwargs):
        captured["reply"] = True

    class _OkResp:
        status_code = 200
        text = ""

    class _Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            captured["leave_url"] = url
            return _OkResp()

    with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
        with patch("httpx.AsyncClient", _Client):
            asyncio.run(line_bot._handle_group_join({
                "type": "join",
                "source": {"type": "group", "groupId": "C_GROUP_TEST"},
                "replyToken": "TKN",
            }))
    assert captured["reply"] is True
    assert "/v2/bot/group/C_GROUP_TEST/leave" in captured["leave_url"]


def test_gr2_room_join_leaves_room(line_full_config):
    """room join (not group) → /v2/bot/room/.../leave"""
    from backend import line_bot, bot_adapters

    captured = {"leave_url": None}

    async def fake_reply(self, token, msg, **kwargs): return True

    class _OkResp:
        status_code = 200
        text = ""

    class _Client:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, **kwargs):
            captured["leave_url"] = url
            return _OkResp()

    with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
        with patch("httpx.AsyncClient", _Client):
            asyncio.run(line_bot._handle_group_join({
                "type": "join",
                "source": {"type": "room", "roomId": "R_TEST"},
                "replyToken": "TKN",
            }))
    assert "/v2/bot/room/R_TEST/leave" in captured["leave_url"]


def test_gr3_no_group_id_skips(line_full_config):
    """malformed source (no groupId/roomId) → skip without error"""
    from backend import line_bot
    asyncio.run(line_bot._handle_group_join({
        "type": "join",
        "source": {"type": "group"},  # missing groupId
    }))


# ═══════════════════════════════════════════
# AD — admin quota endpoint (3 cases)
# ═══════════════════════════════════════════

def test_ad1_admin_quota_unauthorized(test_client):
    """no auth → 401"""
    resp = test_client.get("/api/line/admin/quota")
    assert resp.status_code == 401


def test_ad2_admin_quota_returns_usage(test_client, quota_reset):
    """authenticated → returns quota stats"""
    token = _register_user(test_client, email="h_ad2@test.local")
    resp = test_client.get(
        "/api/line/admin/quota", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pushes_used"] == 0
    assert data["limit"] == 200
    assert "percent" in data


def test_ad3_admin_quota_reflects_pushes(test_client, quota_reset):
    """record pushes → endpoint shows them"""
    from backend import line_quota
    token = _register_user(test_client, email="h_ad3@test.local")
    for _ in range(5):
        line_quota.record_push()
    resp = test_client.get(
        "/api/line/admin/quota", headers={"Authorization": f"Bearer {token}"}
    )
    data = resp.json()
    assert data["pushes_used"] == 5
    assert data["remaining"] == 195
