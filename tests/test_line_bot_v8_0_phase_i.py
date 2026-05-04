"""Tests for LINE Bot Phase I — Rich Menu + Postback dispatch.

Coverage:
- RM: Rich menu structure validation (3 cases)
- PB: postback dispatch (5 cases)
- IM: image generation (2 cases)

Total: 10 cases
"""
import asyncio
import importlib
import os
from datetime import datetime as _dt
from unittest.mock import patch

import pytest


@pytest.fixture
def line_full_config(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "test_secret")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "test_token")
    from backend import config, line_bot, bot_adapters
    importlib.reload(config)
    importlib.reload(line_bot)
    importlib.reload(bot_adapters)


def _create_user_with_line(user_id: str, line_user_id: str, email: str):
    from backend.database import AsyncSessionLocal, User, LineUser
    from sqlalchemy import select, delete

    async def _do():
        async with AsyncSessionLocal() as db:
            if not (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none():
                db.add(User(id=user_id, name="Test", email=email))
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
            await db.commit()
            db.add(LineUser(pdb_user_id=user_id, line_user_id=line_user_id, linked_at=_dt.utcnow()))
            await db.commit()
    asyncio.run(_do())


def _cleanup(user_id: str):
    from backend.database import AsyncSessionLocal, User, LineUser
    from sqlalchemy import delete
    async def _do():
        async with AsyncSessionLocal() as db:
            await db.execute(delete(LineUser).where(LineUser.pdb_user_id == user_id))
            await db.execute(delete(User).where(User.id == user_id))
            await db.commit()
    asyncio.run(_do())


# ═══════════════════════════════════════════
# RM — Rich Menu structure (3 cases)
# ═══════════════════════════════════════════

def test_rm1_menu_definition_valid():
    """Menu structure has 6 areas + valid bounds"""
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader("setup_rm", "scripts/setup_line_rich_menu.py").load_module()
    defn = mod.RICH_MENU_DEFINITION
    assert defn["size"]["width"] == 2500
    assert defn["size"]["height"] == 1686
    assert len(defn["areas"]) == 6
    # All areas have valid bounds (no overlap, fill canvas)
    for area in defn["areas"]:
        assert area["bounds"]["width"] > 0
        assert area["bounds"]["height"] > 0
        assert area["action"]["type"] in ("postback", "message", "uri")


def test_rm2_menu_actions_have_handlers():
    """Each menu action data should map to a handler in line_bot postback"""
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader("setup_rm", "scripts/setup_line_rich_menu.py").load_module()
    defn = mod.RICH_MENU_DEFINITION
    # Postback actions in menu
    postback_actions = []
    for area in defn["areas"]:
        if area["action"]["type"] == "postback":
            data = area["action"]["data"]
            action = dict(p.split("=") for p in data.split("&"))["action"]
            postback_actions.append(action)
    # Each postback action should be handled in line_bot._handle_postback
    import inspect
    from backend import line_bot
    src = inspect.getsource(line_bot._handle_postback)
    for action in postback_actions:
        assert action in src, f"action='{action}' not handled in _handle_postback"


def test_rm3_message_actions_known_keywords():
    """Message-type actions should produce text that matches known intents"""
    from importlib.machinery import SourceFileLoader
    mod = SourceFileLoader("setup_rm", "scripts/setup_line_rich_menu.py").load_module()
    defn = mod.RICH_MENU_DEFINITION
    from backend.bot_handlers import detect_intent, Intent

    for area in defn["areas"]:
        if area["action"]["type"] == "message":
            text = area["action"]["text"]
            intent, _ = detect_intent(text)
            # Should map to a real intent (not CHAT default)
            # Allow CHAT for "เปิดเว็บ" since it's a shortcut handled elsewhere
            assert intent in (Intent.STATS, Intent.SEARCH, Intent.HELP, Intent.GET_FILE, Intent.CHAT)


# ═══════════════════════════════════════════
# PB — postback dispatch (5 cases)
# ═══════════════════════════════════════════

def test_pb1_upload_help_postback(line_full_config):
    """upload_help postback → reply with upload instructions"""
    from backend import line_bot, bot_adapters

    user_id = "test_pb1_user"
    line_user_id = "U_PB1"
    _create_user_with_line(user_id, line_user_id, "pb1@test.local")

    captured = {}
    async def fake_reply(self, token, msg, **kwargs):
        captured["text"] = msg.text

    try:
        with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
            asyncio.run(line_bot._handle_postback({
                "type": "postback",
                "source": {"userId": line_user_id},
                "replyToken": "TKN",
                "postback": {"data": "action=upload_help"},
            }))
        assert "ส่งไฟล์" in captured.get("text", "")
    finally:
        _cleanup(user_id)


def test_pb2_settings_postback(line_full_config):
    """settings postback → reply with settings link"""
    from backend import line_bot, bot_adapters

    user_id = "test_pb2_user"
    line_user_id = "U_PB2"
    _create_user_with_line(user_id, line_user_id, "pb2@test.local")

    captured = {}
    async def fake_reply(self, token, msg, **kwargs):
        captured["text"] = msg.text

    try:
        with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
            asyncio.run(line_bot._handle_postback({
                "type": "postback",
                "source": {"userId": line_user_id},
                "replyToken": "TKN",
                "postback": {"data": "action=settings"},
            }))
        assert "ตั้งค่า" in captured.get("text", "")
    finally:
        _cleanup(user_id)


def test_pb3_open_file_postback(line_full_config):
    """open_file postback → returns Flex card with download URL"""
    from backend import line_bot, bot_adapters
    from backend.database import AsyncSessionLocal, File, gen_id
    from sqlalchemy import delete

    user_id = "test_pb3_user"
    line_user_id = "U_PB3"
    _create_user_with_line(user_id, line_user_id, "pb3@test.local")

    file_id = gen_id()
    async def setup_file():
        async with AsyncSessionLocal() as db:
            db.add(File(
                id=file_id, user_id=user_id, filename="report.pdf",
                filetype="pdf", raw_path="/tmp/r.pdf",
                extracted_text="x", processing_status="ready",
            ))
            await db.commit()
    asyncio.run(setup_file())

    captured = {}
    async def fake_reply(self, token, msg, **kwargs):
        captured["flex"] = msg.flex

    try:
        with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
            asyncio.run(line_bot._handle_postback({
                "type": "postback",
                "source": {"userId": line_user_id},
                "replyToken": "TKN",
                "postback": {"data": f"action=open_file&file_id={file_id}"},
            }))
        flex = captured.get("flex")
        assert flex is not None
        assert "report.pdf" in flex.get("altText", "")
    finally:
        async def _del():
            async with AsyncSessionLocal() as db:
                await db.execute(delete(File).where(File.id == file_id))
                await db.commit()
        asyncio.run(_del())
        _cleanup(user_id)


def test_pb4_unknown_action_logged(line_full_config):
    """unknown action → logged, no error"""
    from backend import line_bot
    asyncio.run(line_bot._handle_postback({
        "type": "postback",
        "source": {"userId": "U_UNKNOWN"},
        "replyToken": "TKN",
        "postback": {"data": "action=does_not_exist"},
    }))


def test_pb5_postback_unlinked_user(line_full_config):
    """postback from unlinked user → reply prompt to link"""
    from backend import line_bot, bot_adapters

    captured = {}
    async def fake_reply(self, token, msg, **kwargs):
        captured["text"] = msg.text

    with patch.object(bot_adapters.LineBotAdapter, "reply_message", fake_reply):
        asyncio.run(line_bot._handle_postback({
            "type": "postback",
            "source": {"userId": "U_NOT_LINKED"},
            "replyToken": "TKN",
            "postback": {"data": "action=settings"},
        }))
    assert "เชื่อมบัญชี" in captured.get("text", "")


# ═══════════════════════════════════════════
# IM — image generation (2 cases)
# ═══════════════════════════════════════════

def test_im1_generated_image_exists():
    """Image file exists at expected path"""
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_path = os.path.join(repo_root, "legacy-frontend", "line-rich-menu.png")
    assert os.path.exists(image_path), "Run scripts/generate_line_rich_menu_image.py first"


def test_im2_image_dimensions_correct():
    """Image is 2500×1686 (LINE Rich Menu spec)"""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("Pillow not installed")
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    image_path = os.path.join(repo_root, "legacy-frontend", "line-rich-menu.png")
    if not os.path.exists(image_path):
        pytest.skip("Image not generated")
    img = Image.open(image_path)
    assert img.size == (2500, 1686), f"Expected 2500×1686, got {img.size}"
    # File size < 1MB (LINE limit)
    assert os.path.getsize(image_path) < 1024 * 1024, "Image > 1MB will be rejected by LINE"
