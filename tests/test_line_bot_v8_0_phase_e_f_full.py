"""Tests for LINE Bot Phase E full + Phase F (post-Phase 0).

Coverage:
- BM: bot_messages.py Flex builders (8 cases)
- ADP: LineBotAdapter HTTP methods with mocked httpx (6 cases)
- E: follow event + accountLink event handlers (6 cases)
- F: file/text message handlers (6 cases)

Total: 26 cases
"""
import asyncio
import importlib
from datetime import datetime as _dt, timedelta as _td
from unittest.mock import patch, AsyncMock, MagicMock

import pytest


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def line_full_config(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test_secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("LINE_LOGIN_CHANNEL_ID", "test_login_id")
    monkeypatch.setenv("LINE_LOGIN_CHANNEL_SECRET", "test_login_secret")
    monkeypatch.setenv("LINE_BOT_BASIC_ID", "@PDBBot")
    monkeypatch.setenv("LINE_BOT_BASE_URL", "https://test.example.com")
    from backend import config, line_bot, bot_adapters
    importlib.reload(config)
    importlib.reload(line_bot)
    importlib.reload(bot_adapters)


# ═══════════════════════════════════════════
# BM — bot_messages.py builders (8 cases)
# ═══════════════════════════════════════════

def test_bm1_link_prompt_card_structure():
    from backend.bot_messages import link_prompt_card
    m = link_prompt_card("https://example/auth/line?linkToken=abc")
    assert m["type"] == "flex"
    assert "altText" in m
    bubble = m["contents"]
    assert bubble["type"] == "bubble"
    # Find the URI button
    btn = bubble["footer"]["contents"][0]
    assert btn["action"]["type"] == "uri"
    assert "linkToken=abc" in btn["action"]["uri"]


def test_bm2_vault_status_card_pending():
    from backend.bot_messages import vault_status_card
    m = vault_status_card("Alice", 47, 8, 3, 234, 1024, "byos", pending_organize=5)
    assert m["type"] == "flex"
    bubble = m["contents"]
    # Pending organize triggers footer button
    assert "footer" in bubble
    btn = bubble["footer"]["contents"][0]
    assert btn["action"]["type"] == "postback"
    assert "organize_now" in btn["action"]["data"]


def test_bm3_vault_status_card_no_pending():
    from backend.bot_messages import vault_status_card
    m = vault_status_card("Bob", 5, 1, 0, 10, 50, "managed", pending_organize=0)
    bubble = m["contents"]
    # No pending → no footer
    assert "footer" not in bubble


def test_bm4_file_upload_confirmation_with_cluster():
    from backend.bot_messages import file_upload_confirmation_card
    m = file_upload_confirmation_card(
        "f1", "thesis.pdf", "pdf", 12345,
        cluster_title="AI Research",
        download_url="https://x/d/tok",
    )
    assert m["type"] == "flex"
    bubble = m["contents"]
    # Has download button
    btns = bubble["footer"]["contents"]
    assert any("ดาวน์โหลด" in b["action"]["label"] for b in btns)


def test_bm5_file_upload_confirmation_no_extras():
    from backend.bot_messages import file_upload_confirmation_card
    m = file_upload_confirmation_card("f2", "x.txt", "txt", 100)
    bubble = m["contents"]
    # No buttons → no footer
    assert "footer" not in bubble


def test_bm6_error_card_with_upgrade():
    from backend.bot_messages import error_card
    m = error_card("Limit", "msg", "suggest", upgrade_url="https://upgrade")
    bubble = m["contents"]
    btn = bubble["footer"]["contents"][0]
    assert btn["action"]["uri"] == "https://upgrade"


def test_bm7_search_carousel_results():
    from backend.bot_messages import file_search_carousel
    m = file_search_carousel([
        {"file_id": "f1", "filename": "a.pdf", "filetype": "pdf", "score": 0.95},
        {"file_id": "f2", "filename": "b.docx", "filetype": "docx", "score": 0.8},
    ])
    assert m["contents"]["type"] == "carousel"
    assert len(m["contents"]["contents"]) == 2


def test_bm8_search_carousel_empty():
    from backend.bot_messages import file_search_carousel
    m = file_search_carousel([])
    assert m["contents"]["type"] == "bubble"
    assert "ไม่พบ" in m["altText"]


# ═══════════════════════════════════════════
# ADP — LineBotAdapter HTTP methods (6 cases)
# ═══════════════════════════════════════════

def test_adp1_convert_text_message():
    from backend.bot_adapters import LineBotAdapter, BotMessage
    a = LineBotAdapter("token")
    msgs = a._convert_message(BotMessage(text="hello"))
    assert msgs == [{"type": "text", "text": "hello"}]


def test_adp2_convert_text_with_quick_reply():
    from backend.bot_adapters import LineBotAdapter, BotMessage
    a = LineBotAdapter("token")
    msgs = a._convert_message(BotMessage(text="pick", quick_reply=[
        {"label": "A", "data": "x=1"},
        {"label": "B", "text": "B-text"},
    ]))
    assert msgs[0]["quickReply"]["items"][0]["action"]["type"] == "postback"
    assert msgs[0]["quickReply"]["items"][1]["action"]["type"] == "message"


def test_adp3_convert_text_plus_flex():
    from backend.bot_adapters import LineBotAdapter, BotMessage
    a = LineBotAdapter("token")
    flex = {"type": "flex", "altText": "x", "contents": {}}
    msgs = a._convert_message(BotMessage(text="hi", flex=flex))
    assert len(msgs) == 2
    assert msgs[1]["type"] == "flex"


def test_adp4_send_message_calls_push_api():
    from backend.bot_adapters import LineBotAdapter, BotMessage
    a = LineBotAdapter("token")

    captured = {}

    class _MockResp:
        status_code = 200
        text = ""

    class _MockClient:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _MockResp()

    with patch("httpx.AsyncClient", _MockClient):
        asyncio.run(a.send_message("U_TEST", BotMessage(text="hi")))

    assert "/v2/bot/message/push" in captured["url"]
    assert captured["json"]["to"] == "U_TEST"
    assert captured["json"]["messages"] == [{"type": "text", "text": "hi"}]
    assert captured["headers"]["Authorization"] == "Bearer token"


def test_adp5_reply_message_uses_reply_endpoint():
    from backend.bot_adapters import LineBotAdapter, BotMessage
    a = LineBotAdapter("tok")
    captured = {}

    class _MR:
        status_code = 200
        text = ""

    class _MC:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["body"] = json
            return _MR()

    with patch("httpx.AsyncClient", _MC):
        asyncio.run(a.reply_message("REPLY_TKN", BotMessage(text="ack")))
    assert "/v2/bot/message/reply" in captured["url"]
    assert captured["body"]["replyToken"] == "REPLY_TKN"


def test_adp6_issue_link_token_returns_token():
    from backend.bot_adapters import LineBotAdapter
    a = LineBotAdapter("tok")

    class _MR:
        status_code = 200
        text = ""
        def json(self): return {"linkToken": "LINK123"}

    class _MC:
        def __init__(self, *args, **kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, url, headers=None, json=None):
            return _MR()

    with patch("httpx.AsyncClient", _MC):
        result = asyncio.run(a.issue_link_token("U_TEST"))
    assert result == "LINK123"


# ═══════════════════════════════════════════
# E — follow + accountLink handlers (6 cases)
# ═══════════════════════════════════════════

def test_e_full1_follow_no_config_skips(monkeypatch):
    """follow without config → adapter=None → no exception"""
    monkeypatch.delenv("LINE_CHANNEL_SECRET", raising=False)
    monkeypatch.delenv("LINE_CHANNEL_ACCESS_TOKEN", raising=False)
    from backend import config, line_bot, bot_adapters
    importlib.reload(config)
    importlib.reload(line_bot)
    importlib.reload(bot_adapters)

    async def _do():
        await line_bot._handle_follow({
            "type": "follow",
            "source": {"userId": "U1"},
            "replyToken": "TKN",
        })
    asyncio.run(_do())  # should not raise


def test_e_full2_follow_calls_adapter(line_full_config):
    """follow → issue_link_token → reply_message with link_prompt_card"""
    from backend import line_bot, bot_adapters

    calls = []

    async def fake_issue(self, line_user_id):
        calls.append(("issue", line_user_id))
        return "FAKE_LINK_TOKEN"

    async def fake_reply(self, reply_token, message):
        calls.append(("reply", reply_token, message.flex is not None))

    with patch.object(bot_adapters.LineBotAdapter, "issue_link_token", fake_issue):
        with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
            asyncio.run(line_bot._handle_follow({
                "type": "follow",
                "source": {"userId": "U_FOLLOW"},
                "replyToken": "TKN",
            }))
    assert ("issue", "U_FOLLOW") in calls
    # Check that reply_message was called with flex card
    assert any(c[0] == "reply" and c[2] is True for c in calls)


def test_e_full3_account_link_matches_nonce(line_full_config):
    """accountLink event → match nonce → bind line_user_id + clear nonce"""
    from backend import line_bot, bot_adapters
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete

    async def setup():
        async with AsyncSessionLocal() as db:
            # Create user
            u_id = "test_e3_user"
            existing = (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none()
            if not existing:
                db.add(User(id=u_id, name="E3", email="e3@test.local"))
            # Cleanup leftover
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u_id))
            await db.commit()
            row = LineUser(
                pdb_user_id=u_id,
                link_nonce="TEST_NONCE_E3",
                link_nonce_expires_at=_dt.utcnow() + _td(minutes=5),
            )
            db.add(row)
            await db.commit()
            return u_id

    user_id = asyncio.run(setup())

    # Mock adapter calls (welcome flow + profile)
    async def fake_send(*args, **kwargs): return None
    async def fake_profile(self, line_user_id): return {"displayName": "Test User"}

    try:
        with patch.object(bot_adapters.LineBotAdapter, "send_message", fake_send):
            with patch.object(bot_adapters.LineBotAdapter, "get_user_profile", fake_profile):
                asyncio.run(line_bot._handle_account_link({
                    "type": "accountLink",
                    "source": {"userId": "U_LINKED_E3"},
                    "replyToken": None,
                    "link": {"result": "ok", "nonce": "TEST_NONCE_E3"},
                }))

        async def verify():
            async with AsyncSessionLocal() as db:
                row = (await db.execute(
                    select(LineUser).where(LineUser.pdb_user_id == user_id)
                )).scalar_one()
                return row.line_user_id, row.link_nonce, row.line_display_name, row.welcomed

        line_id, nonce, name, welcomed = asyncio.run(verify())
        assert line_id == "U_LINKED_E3"
        assert nonce is None  # cleared
        assert name == "Test User"
        assert welcomed is True
    finally:
        async def cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
        asyncio.run(cleanup())


def test_e_full4_account_link_bad_nonce(line_full_config):
    """accountLink with unknown nonce → no-op (no error)"""
    from backend import line_bot
    asyncio.run(line_bot._handle_account_link({
        "type": "accountLink",
        "source": {"userId": "U_X"},
        "replyToken": None,
        "link": {"result": "ok", "nonce": "DOES_NOT_EXIST"},
    }))


def test_e_full5_account_link_expired_nonce(line_full_config):
    """accountLink with expired nonce → skip (no error)"""
    from backend import line_bot
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete

    async def setup():
        async with AsyncSessionLocal() as db:
            u_id = "test_e5_user"
            if not (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none():
                db.add(User(id=u_id, name="E5", email="e5@test.local"))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u_id))
            await db.commit()
            db.add(LineUser(
                pdb_user_id=u_id,
                link_nonce="EXPIRED_NONCE",
                link_nonce_expires_at=_dt.utcnow() - _td(minutes=1),  # expired
            ))
            await db.commit()
            return u_id

    user_id = asyncio.run(setup())

    try:
        asyncio.run(line_bot._handle_account_link({
            "type": "accountLink",
            "source": {"userId": "U_TRY"},
            "replyToken": None,
            "link": {"result": "ok", "nonce": "EXPIRED_NONCE"},
        }))

        # Verify line_user_id NOT set (link rejected)
        async def verify():
            async with AsyncSessionLocal() as db:
                row = (await db.execute(
                    select(LineUser).where(LineUser.pdb_user_id == user_id)
                )).scalar_one()
                return row.line_user_id

        line_id = asyncio.run(verify())
        assert line_id is None
    finally:
        async def cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
        asyncio.run(cleanup())


def test_e_full6_account_link_failed_result(line_full_config):
    """accountLink with result=failed → skip (no DB writes)"""
    from backend import line_bot
    asyncio.run(line_bot._handle_account_link({
        "type": "accountLink",
        "source": {"userId": "U"},
        "link": {"result": "failed", "nonce": "any"},
    }))


# ═══════════════════════════════════════════
# F — message handlers (6 cases)
# ═══════════════════════════════════════════

def test_f1_text_message_not_linked_prompts_link(line_full_config):
    """user not linked → reply prompts to link"""
    from backend import line_bot, bot_adapters

    captured = {}
    async def fake_reply(self, token, message):
        captured["text"] = message.text

    with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
        asyncio.run(line_bot._handle_message({
            "type": "message",
            "source": {"userId": "U_NEW"},
            "replyToken": "TKN",
            "message": {"type": "text", "text": "hello"},
        }))
    assert "เชื่อมบัญชี" in captured.get("text", "")


def test_f2_text_message_stats_keyword(line_full_config):
    """user linked + พิมพ์ 'กี่ไฟล์' → stats reply"""
    from backend import line_bot, bot_adapters
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete

    async def setup():
        async with AsyncSessionLocal() as db:
            u_id = "test_f2_user"
            if not (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none():
                db.add(User(id=u_id, name="F2", email="f2@test.local"))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u_id))
            await db.commit()
            db.add(LineUser(
                pdb_user_id=u_id,
                line_user_id="U_F2_LINKED",
                linked_at=_dt.utcnow(),
            ))
            await db.commit()
            return u_id

    user_id = asyncio.run(setup())

    captured = {}
    async def fake_reply(self, token, message):
        captured["text"] = message.text
        captured["flex"] = message.flex
    async def fake_typing(self, *args, **kwargs):
        return None

    try:
        with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
            with patch.object(bot_adapters.LineBotAdapter, "show_typing", fake_typing):
                asyncio.run(line_bot._handle_message({
                    "type": "message",
                    "source": {"userId": "U_F2_LINKED"},
                    "replyToken": "TKN",
                    "message": {"type": "text", "text": "ฉันมีกี่ไฟล์"},
                }))
        # Phase G stats handler returns Flex card (not text)
        flex = captured.get("flex")
        assert flex is not None
        # altText contains stats summary
        alt = flex.get("altText", "")
        assert "ไฟล์" in alt or "สถานะตู้" in alt
    finally:
        async def cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
        asyncio.run(cleanup())


def test_f3_text_message_general_chat(line_full_config):
    """linked + general text → Phase G dispatches to bot_handlers.handle_text_intent.

    Phase G changed _handle_text_message: was placeholder echo "ได้ยิน...",
    now routes to bot_handlers (CHAT intent → call retriever.chat_with_retrieval).
    Mock chat_with_retrieval to verify wiring works.
    """
    from backend import line_bot, bot_adapters
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete

    async def setup():
        async with AsyncSessionLocal() as db:
            u_id = "test_f3_user"
            if not (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none():
                db.add(User(id=u_id, name="F3", email="f3@test.local"))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=u_id, line_user_id="U_F3_LINKED",
                            linked_at=_dt.utcnow()))
            await db.commit()
            return u_id

    user_id = asyncio.run(setup())

    captured = {}
    async def fake_reply(self, token, message):
        captured["text"] = message.text
    async def fake_typing(self, *args, **kwargs):
        return None

    # Mock retriever to avoid LLM call
    async def fake_chat(db, user_id_arg, question):
        return {
            "answer": "ผมรับคำถาม 'สวัสดี' ของคุณแล้วครับ",
            "sources": [],
        }

    try:
        with patch("backend.retriever.chat_with_retrieval", side_effect=fake_chat):
            with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
                with patch.object(bot_adapters.LineBotAdapter, "show_typing", fake_typing):
                    asyncio.run(line_bot._handle_message({
                        "type": "message",
                        "source": {"userId": "U_F3_LINKED"},
                        "replyToken": "TKN",
                        "message": {"type": "text", "text": "สวัสดี"},
                    }))
        assert "สวัสดี" in captured.get("text", "")
    finally:
        async def cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
        asyncio.run(cleanup())


def test_f4_unfollow_soft_unlinks(line_full_config):
    """unfollow → unlinked_at set"""
    from backend import line_bot
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete

    async def setup():
        async with AsyncSessionLocal() as db:
            u_id = "test_f4_user"
            if not (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none():
                db.add(User(id=u_id, name="F4", email="f4@test.local"))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=u_id, line_user_id="U_F4",
                            linked_at=_dt.utcnow()))
            await db.commit()
            return u_id

    user_id = asyncio.run(setup())

    try:
        asyncio.run(line_bot._handle_unfollow({
            "type": "unfollow",
            "source": {"userId": "U_F4"},
        }))

        async def verify():
            async with AsyncSessionLocal() as db:
                row = (await db.execute(select(LineUser).where(LineUser.pdb_user_id == user_id))).scalar_one()
                return row.unlinked_at
        unlinked = asyncio.run(verify())
        assert unlinked is not None
    finally:
        async def cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
        asyncio.run(cleanup())


def test_f5_file_message_uploads(line_full_config, tmp_path, monkeypatch):
    """linked + file message → download + save + reply confirmation"""
    from backend import line_bot, bot_adapters
    from backend.bot_adapters import BotAttachment
    from backend.database import AsyncSessionLocal, LineUser, User, File
    from sqlalchemy import select, delete

    # Use temp upload dir
    monkeypatch.setattr("backend.line_bot.UPLOAD_DIR", str(tmp_path), raising=False)

    async def setup():
        async with AsyncSessionLocal() as db:
            u_id = "test_f5_user"
            if not (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none():
                db.add(User(id=u_id, name="F5", email="f5@test.local"))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=u_id, line_user_id="U_F5_LINKED",
                            linked_at=_dt.utcnow()))
            await db.commit()
            return u_id

    user_id = asyncio.run(setup())

    fake_attachment = BotAttachment(
        content=b"test file content",
        filename="test.txt",
        mime_type="text/plain",
        message_id="M_F5",
    )

    async def fake_download(self, mid): return fake_attachment
    async def fake_typing(self, *args, **kwargs): return None
    captured = {}
    async def fake_reply(self, token, message, **kwargs):
        captured["flex"] = message.flex

    try:
        with patch.object(bot_adapters.LineBotAdapter, "download_attachment", fake_download):
            with patch.object(bot_adapters.LineBotAdapter, "show_typing", fake_typing):
                with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
                    asyncio.run(line_bot._handle_message({
                        "type": "message",
                        "source": {"userId": "U_F5_LINKED"},
                        "replyToken": "TKN",
                        "message": {"type": "file", "id": "M_F5", "fileName": "test.txt", "fileSize": 17},
                    }))

        # Verify flex confirmation card
        flex = captured.get("flex")
        assert flex is not None
        assert "test.txt" in flex["altText"]

        # Verify File row created
        async def verify():
            async with AsyncSessionLocal() as db:
                rows = (await db.execute(select(File).where(File.user_id == user_id))).scalars().all()
                return rows
        files = asyncio.run(verify())
        assert len(files) == 1
        assert files[0].filename == "test.txt"
    finally:
        async def cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(File).where(File.user_id == user_id))
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
        asyncio.run(cleanup())


def test_f6_file_message_plan_limit_rejects(line_full_config, tmp_path, monkeypatch):
    """linked free user at file limit → next file rejected with error card.

    Free file_limit = 50 (v8.0.2 ×10 from baseline). Pre-seed 50 files to trigger.
    """
    from backend import line_bot, bot_adapters
    from backend.bot_adapters import BotAttachment
    from backend.database import AsyncSessionLocal, LineUser, User, File, gen_id
    from backend.plan_limits import PLAN_LIMITS
    from sqlalchemy import select, delete

    monkeypatch.setattr("backend.line_bot.UPLOAD_DIR", str(tmp_path), raising=False)

    free_limit = PLAN_LIMITS["free"]["file_limit"]

    async def setup():
        async with AsyncSessionLocal() as db:
            u_id = "test_f6_user"
            if not (await db.execute(select(User).where(User.id == u_id))).scalar_one_or_none():
                db.add(User(id=u_id, name="F6", email="f6@test.local"))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == u_id))
            await db.execute(delete(File).where(File.user_id == u_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=u_id, line_user_id="U_F6_LINKED", linked_at=_dt.utcnow()))
            # Pre-seed up to free limit
            for i in range(free_limit):
                db.add(File(
                    id=gen_id(),
                    user_id=u_id,
                    filename=f"f{i}.txt",
                    filetype="txt",
                    raw_path=str(tmp_path / f"f{i}.txt"),
                    extracted_text="x",
                    processing_status="ready",
                ))
            await db.commit()
            return u_id

    user_id = asyncio.run(setup())

    fake_attachment = BotAttachment(content=b"next", filename="next.txt", mime_type="text/plain", message_id="MNEXT")

    async def fake_download(self, mid): return fake_attachment
    async def fake_typing(self, *args, **kwargs): return None
    captured = {}
    async def fake_reply(self, token, message, **kwargs):
        captured["flex"] = message.flex

    try:
        with patch.object(bot_adapters.LineBotAdapter, "download_attachment", fake_download):
            with patch.object(bot_adapters.LineBotAdapter, "show_typing", fake_typing):
                with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
                    asyncio.run(line_bot._handle_message({
                        "type": "message",
                        "source": {"userId": "U_F6_LINKED"},
                        "replyToken": "TKN",
                        "message": {"type": "file", "id": "MNEXT", "fileName": "next.txt", "fileSize": 4},
                    }))

        flex = captured.get("flex")
        assert flex is not None
        # Error card has "เกิน" or limit message
        assert "เกิน" in flex["altText"] or "Limit" in flex["altText"] or "ไฟล์" in flex["altText"]
    finally:
        async def cleanup():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(File).where(File.user_id == user_id))
                await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
                await db.execute(delete(User).where(User.id == user_id))
                await db.commit()
        asyncio.run(cleanup())
