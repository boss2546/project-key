"""Tests for LINE Bot Phase G — text intent dispatch.

Coverage:
- IT: detect_intent classification (10 cases)
- ST: stats handler (2 cases)
- HP: help handler (1 case)
- SR: search handler (3 cases)
- GF: get_file handler (4 cases)
- CH: chat handler (3 cases)
- WIRE: line_bot._handle_text_message uses bot_handlers (3 cases)

Total: 26 cases
"""
import asyncio
import importlib
from datetime import datetime as _dt
from unittest.mock import patch, AsyncMock

import pytest


# ═══════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════

@pytest.fixture
def line_full_config(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test_secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
    monkeypatch.setenv("LINE_BOT_BASIC_ID", "@PDBBot")
    monkeypatch.setenv("LINE_BOT_BASE_URL", "https://test.example.com")
    from backend import config, line_bot, bot_adapters, bot_handlers
    importlib.reload(config)
    importlib.reload(line_bot)
    importlib.reload(bot_adapters)
    importlib.reload(bot_handlers)


def _create_test_user(user_id: str, email: str):
    """Create User if not exists."""
    from backend.database import AsyncSessionLocal, User
    from sqlalchemy import select

    async def _do():
        async with AsyncSessionLocal() as db:
            existing = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
            if not existing:
                db.add(User(id=user_id, name="G Test", email=email))
                await db.commit()
    asyncio.run(_do())


def _cleanup_user(user_id: str):
    from backend.database import AsyncSessionLocal, User, File, Cluster, ContextPack, LineUser
    from sqlalchemy import delete

    async def _do():
        async with AsyncSessionLocal() as db:
            await db.execute(delete(File).where(File.user_id == user_id))
            await db.execute(delete(Cluster).where(Cluster.user_id == user_id))
            await db.execute(delete(ContextPack).where(ContextPack.user_id == user_id))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
    asyncio.run(_do())


# ═══════════════════════════════════════════
# IT — detect_intent (10 cases)
# ═══════════════════════════════════════════

def test_it1_help_exact():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("/help")
    assert intent == Intent.HELP


def test_it2_help_thai():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("ช่วยเหลือ")
    assert intent == Intent.HELP


def test_it3_get_file():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("ขอไฟล์ thesis.pdf")
    assert intent == Intent.GET_FILE
    assert "thesis.pdf" in q


def test_it4_get_file_english():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("download my report")
    assert intent == Intent.GET_FILE
    assert "my report" in q.lower()


def test_it5_search_thai():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("หาไฟล์ AI machine learning")
    assert intent == Intent.SEARCH
    assert "AI" in q


def test_it6_search_english():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("search transformer architecture")
    assert intent == Intent.SEARCH
    assert "transformer" in q.lower()


def test_it7_stats_thai():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("ฉันมีกี่ไฟล์")
    assert intent == Intent.STATS


def test_it8_stats_english():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("show stats please")
    assert intent == Intent.STATS


def test_it9_chat_default():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("อธิบาย transformer ให้ฟังหน่อย")
    assert intent == Intent.CHAT
    assert "transformer" in q


def test_it10_empty_text():
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("")
    assert intent == Intent.CHAT
    assert q == ""


def test_it11_url_detected():
    """URL in text → URL_UPLOAD intent (added by parallel agent)"""
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("เก็บไฟล์นี้ https://arxiv.org/pdf/2401.00001.pdf")
    assert intent == Intent.URL_UPLOAD
    assert q == "https://arxiv.org/pdf/2401.00001.pdf"


def test_it12_url_priority_over_search():
    """URL takes priority even if 'หา' keyword present"""
    from backend.bot_handlers import detect_intent, Intent
    intent, q = detect_intent("หาไฟล์จาก https://example.com/doc.pdf")
    assert intent == Intent.URL_UPLOAD
    assert "example.com" in q


def test_url1_prompt_returns_confirmation():
    """_handle_url_prompt returns Quick Reply with confirm/decline"""
    import asyncio
    from backend.bot_handlers import _handle_url_prompt
    msgs = asyncio.run(_handle_url_prompt("any_user", "https://example.com/file.pdf"))
    assert len(msgs) == 1
    assert "ลิงก์" in msgs[0].text or "https://example.com" in msgs[0].text
    assert msgs[0].quick_reply is not None
    # Has yes/no chips
    labels = [qr["label"] for qr in msgs[0].quick_reply]
    assert any("ใช่" in l or "เก็บ" in l for l in labels)


def test_url2_prompt_truncates_long_url():
    """URL > 280 chars → declined (postback data limit)"""
    import asyncio
    from backend.bot_handlers import _handle_url_prompt
    long_url = "https://example.com/" + "x" * 300
    msgs = asyncio.run(_handle_url_prompt("any_user", long_url))
    assert "ยาวเกิน" in msgs[0].text or "ไม่รองรับ" in msgs[0].text


# ═══════════════════════════════════════════
# ST — stats handler (2 cases)
# ═══════════════════════════════════════════

def test_st1_stats_returns_flex_card():
    from backend.bot_handlers import handle_text_intent

    user_id = "test_g_st1"
    _create_test_user(user_id, "g_st1@test.local")
    try:
        msgs = asyncio.run(handle_text_intent(user_id, "ฉันมีกี่ไฟล์"))
        assert len(msgs) == 1
        assert msgs[0].flex is not None
        assert "สถานะตู้" in msgs[0].flex["altText"] or "ไฟล์" in msgs[0].flex["altText"]
    finally:
        _cleanup_user(user_id)


def test_st2_stats_unknown_user():
    """Unknown user_id → fallback message"""
    from backend.bot_handlers import handle_text_intent
    msgs = asyncio.run(handle_text_intent("nonexistent_user_xyz", "stats"))
    assert len(msgs) == 1
    assert "ไม่พบบัญชี" in msgs[0].text


# ═══════════════════════════════════════════
# HP — help handler (1 case)
# ═══════════════════════════════════════════

def test_hp1_help_returns_text_with_quick_reply():
    from backend.bot_handlers import handle_text_intent
    msgs = asyncio.run(handle_text_intent("any_user", "/help"))
    assert len(msgs) == 1
    assert "PDB Assistant" in msgs[0].text
    assert msgs[0].quick_reply is not None
    assert len(msgs[0].quick_reply) >= 2


# ═══════════════════════════════════════════
# SR — search handler (3 cases)
# ═══════════════════════════════════════════

def test_sr1_search_empty_query():
    from backend.bot_handlers import handle_text_intent
    msgs = asyncio.run(handle_text_intent("any_user", "หาไฟล์"))
    assert len(msgs) == 1
    assert "ว่างเปล่า" in msgs[0].text or "ลอง" in msgs[0].text


def test_sr2_search_no_results():
    from backend.bot_handlers import handle_text_intent

    user_id = "test_g_sr2"
    _create_test_user(user_id, "g_sr2@test.local")
    try:
        # User has no files → empty results
        msgs = asyncio.run(handle_text_intent(user_id, "หาไฟล์ unicorn"))
        assert len(msgs) == 1
        # Either text "ไม่พบ" or empty Flex card
        text = msgs[0].text or ""
        flex_alt = (msgs[0].flex or {}).get("altText", "")
        assert "ไม่พบ" in text or "ไม่พบ" in flex_alt
    finally:
        _cleanup_user(user_id)


def test_sr3_search_with_results():
    from backend.bot_handlers import handle_text_intent
    from backend.database import AsyncSessionLocal, File, gen_id
    from sqlalchemy import delete

    user_id = "test_g_sr3"
    _create_test_user(user_id, "g_sr3@test.local")

    async def setup_files():
        async with AsyncSessionLocal() as db:
            db.add(File(
                id=gen_id(),
                user_id=user_id,
                filename="ai_paper.pdf",
                filetype="pdf",
                raw_path="/tmp/ai_paper.pdf",
                extracted_text="machine learning artificial intelligence neural networks transformer",
                processing_status="ready",
            ))
            await db.commit()
    asyncio.run(setup_files())

    # Mock vector_search.hybrid_search to return our test file
    fake_results = [
        {"file_id": "fake", "chunk_index": 0, "text": "AI snippet", "relevance": 0.9, "semantic_score": 0.9}
    ]

    try:
        # Inject fake result that matches our file
        async def setup_real_id():
            async with AsyncSessionLocal() as db:
                from sqlalchemy import select
                row = (await db.execute(
                    select(File).where(File.user_id == user_id)
                )).scalar_one()
                return row.id
        real_file_id = asyncio.run(setup_real_id())
        fake_results[0]["file_id"] = real_file_id

        with patch("backend.vector_search.hybrid_search", return_value=fake_results):
            msgs = asyncio.run(handle_text_intent(user_id, "หาไฟล์ AI"))

        assert len(msgs) == 1
        assert msgs[0].flex is not None
        assert msgs[0].flex["contents"]["type"] == "carousel"
    finally:
        _cleanup_user(user_id)


# ═══════════════════════════════════════════
# GF — get_file handler (4 cases)
# ═══════════════════════════════════════════

def test_gf1_get_file_empty_hint():
    from backend.bot_handlers import handle_text_intent
    # GET_FILE with empty hint after stripping keyword
    msgs = asyncio.run(handle_text_intent("any_user", "ขอไฟล์"))
    assert len(msgs) == 1
    assert "ระบุชื่อ" in msgs[0].text or "ชื่อไฟล์" in msgs[0].text


def test_gf2_get_file_not_found():
    from backend.bot_handlers import handle_text_intent

    user_id = "test_g_gf2"
    _create_test_user(user_id, "g_gf2@test.local")
    try:
        msgs = asyncio.run(handle_text_intent(user_id, "ขอไฟล์ doesnotexist.pdf"))
        assert len(msgs) == 1
        assert "ไม่พบ" in msgs[0].text
    finally:
        _cleanup_user(user_id)


def test_gf3_get_file_single_match():
    from backend.bot_handlers import handle_text_intent
    from backend.database import AsyncSessionLocal, File, gen_id

    user_id = "test_g_gf3"
    _create_test_user(user_id, "g_gf3@test.local")

    async def setup():
        async with AsyncSessionLocal() as db:
            db.add(File(
                id=gen_id(),
                user_id=user_id,
                filename="thesis-2026.pdf",
                filetype="pdf",
                raw_path="/tmp/thesis-2026.pdf",
                extracted_text="thesis content",
                processing_status="ready",
            ))
            await db.commit()
    asyncio.run(setup())

    try:
        msgs = asyncio.run(handle_text_intent(user_id, "ขอไฟล์ thesis"))
        assert len(msgs) == 1
        assert msgs[0].flex is not None
        # File card should mention filename
        assert "thesis-2026.pdf" in msgs[0].flex["altText"]
    finally:
        _cleanup_user(user_id)


def test_gf4_get_file_multi_match():
    from backend.bot_handlers import handle_text_intent
    from backend.database import AsyncSessionLocal, File, gen_id

    user_id = "test_g_gf4"
    _create_test_user(user_id, "g_gf4@test.local")

    async def setup():
        async with AsyncSessionLocal() as db:
            for i in range(3):
                db.add(File(
                    id=gen_id(),
                    user_id=user_id,
                    filename=f"report_v{i}.pdf",
                    filetype="pdf",
                    raw_path=f"/tmp/r{i}.pdf",
                    extracted_text="x",
                    processing_status="ready",
                ))
            await db.commit()
    asyncio.run(setup())

    try:
        msgs = asyncio.run(handle_text_intent(user_id, "ขอไฟล์ report"))
        # Multi-match → 2 messages: text + carousel
        assert len(msgs) == 2
        assert "พบ 3" in msgs[0].text or "ตรงกัน" in msgs[0].text
        assert msgs[1].flex is not None
    finally:
        _cleanup_user(user_id)


# ═══════════════════════════════════════════
# CH — chat handler (3 cases)
# ═══════════════════════════════════════════

def test_ch1_chat_calls_retriever():
    from backend.bot_handlers import handle_text_intent

    fake_result = {
        "answer": "Transformer คือ neural network architecture ที่ใช้ self-attention",
        "sources": [{"filename": "ai.pdf"}],
    }

    async def fake_chat(db, user_id, question):
        return fake_result

    with patch("backend.retriever.chat_with_retrieval", side_effect=fake_chat):
        msgs = asyncio.run(handle_text_intent("any_user", "transformer คืออะไร"))
    assert len(msgs) == 1
    assert "Transformer" in msgs[0].text
    assert msgs[0].quick_reply is not None


def test_ch2_chat_empty_answer():
    from backend.bot_handlers import handle_text_intent

    async def fake_empty(db, user_id, question):
        return {"answer": "", "sources": []}

    with patch("backend.retriever.chat_with_retrieval", side_effect=fake_empty):
        msgs = asyncio.run(handle_text_intent("any_user", "ถามอะไรสักอย่าง"))
    assert "อัปโหลด" in msgs[0].text or "ข้อมูล" in msgs[0].text


def test_ch3_chat_truncates_long_answer():
    from backend.bot_handlers import handle_text_intent

    long_text = "x" * 5000

    async def fake_long(db, user_id, question):
        return {"answer": long_text, "sources": []}

    with patch("backend.retriever.chat_with_retrieval", side_effect=fake_long):
        msgs = asyncio.run(handle_text_intent("any_user", "อะไรก็ได้"))
    assert len(msgs[0].text) <= 4600  # truncated to 4500 + "..."
    assert "ตัด" in msgs[0].text


# ═══════════════════════════════════════════
# WIRE — _handle_text_message uses bot_handlers (3 cases)
# ═══════════════════════════════════════════

def test_wire1_text_message_dispatches_to_handler(line_full_config):
    """text msg from linked user → calls handle_text_intent"""
    from backend import line_bot, bot_adapters
    from backend.bot_adapters import BotMessage
    from backend.database import AsyncSessionLocal, LineUser, User
    from sqlalchemy import select, delete

    user_id = "test_g_wire1"
    _create_test_user(user_id, "g_wire1@test.local")

    async def setup_link():
        async with AsyncSessionLocal() as db:
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=user_id, line_user_id="U_WIRE1", linked_at=_dt.utcnow()))
            await db.commit()
    asyncio.run(setup_link())

    captured = {}
    async def fake_intent(uid, text):
        captured["user_id"] = uid
        captured["text"] = text
        return [BotMessage(text="OK from handler")]

    async def fake_reply(self, token, msg):
        captured["replied"] = msg.text
    async def fake_typing(self, *a, **kw): return None

    try:
        with patch("backend.bot_handlers.handle_text_intent", side_effect=fake_intent):
            with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
                with patch.object(bot_adapters.LineBotAdapter, "show_typing", fake_typing):
                    asyncio.run(line_bot._handle_message({
                        "type": "message",
                        "source": {"userId": "U_WIRE1"},
                        "replyToken": "TKN",
                        "message": {"type": "text", "text": "hello world"},
                    }))
        assert captured.get("text") == "hello world"
        assert captured.get("replied") == "OK from handler"
    finally:
        _cleanup_user(user_id)


def test_wire2_open_web_shortcut(line_full_config):
    """text 'เปิดเว็บ' → quick redirect, no LLM call"""
    from backend import line_bot, bot_adapters
    from backend.database import AsyncSessionLocal, LineUser
    from sqlalchemy import delete

    user_id = "test_g_wire2"
    _create_test_user(user_id, "g_wire2@test.local")

    async def setup():
        async with AsyncSessionLocal() as db:
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=user_id, line_user_id="U_WIRE2", linked_at=_dt.utcnow()))
            await db.commit()
    asyncio.run(setup())

    captured = {}
    async def fake_reply(self, token, msg):
        captured["text"] = msg.text
    intent_called = {"called": False}
    async def fake_intent(*a, **kw):
        intent_called["called"] = True
        return []

    try:
        with patch("backend.bot_handlers.handle_text_intent", side_effect=fake_intent):
            with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
                asyncio.run(line_bot._handle_message({
                    "type": "message",
                    "source": {"userId": "U_WIRE2"},
                    "replyToken": "TKN",
                    "message": {"type": "text", "text": "เปิดเว็บ"},
                }))
        assert "/app" in captured.get("text", "")
        assert intent_called["called"] is False  # shortcut bypasses bot_handlers
    finally:
        _cleanup_user(user_id)


def test_wire3_handler_exception_replies_error(line_full_config):
    """If bot_handlers raises → reply with error message (no propagation)"""
    from backend import line_bot, bot_adapters
    from backend.database import AsyncSessionLocal, LineUser
    from sqlalchemy import delete

    user_id = "test_g_wire3"
    _create_test_user(user_id, "g_wire3@test.local")

    async def setup():
        async with AsyncSessionLocal() as db:
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=user_id, line_user_id="U_WIRE3", linked_at=_dt.utcnow()))
            await db.commit()
    asyncio.run(setup())

    captured = {}
    async def fake_intent(*a, **kw):
        raise RuntimeError("boom")
    async def fake_reply(self, token, msg):
        captured["text"] = msg.text
    async def fake_typing(self, *a, **kw): return None

    try:
        with patch("backend.bot_handlers.handle_text_intent", side_effect=fake_intent):
            with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
                with patch.object(bot_adapters.LineBotAdapter, "show_typing", fake_typing):
                    asyncio.run(line_bot._handle_message({
                        "type": "message",
                        "source": {"userId": "U_WIRE3"},
                        "replyToken": "TKN",
                        "message": {"type": "text", "text": "anything"},
                    }))
        assert "ปัญหา" in captured.get("text", "") or "ลองใหม่" in captured.get("text", "")
    finally:
        _cleanup_user(user_id)
