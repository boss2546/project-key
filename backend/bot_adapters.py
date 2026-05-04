"""Bot Adapter abstraction (v8.0.0).

Platform-agnostic interface สำหรับ chat bot — ออกแบบให้ Telegram + Discord
plug in ทีหลังได้โดยไม่กระทบ business logic ใน bot_handlers.py

Design pattern:
- BotAdapter (abstract) — defines interface
- LineBotAdapter — implementation สำหรับ LINE Messaging API
- Future: TelegramBotAdapter, DiscordBotAdapter

Why abstract:
- bot_handlers.py (intent detect + search + stats + file ops) เขียนครั้งเดียว
- แต่ละ platform มี send/receive format ต่างกัน → adapter convert
- Test ง่าย — mock adapter ใน unit tests, ไม่ต้องเรียก LINE API จริง
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class BotMessage:
    """Platform-agnostic outbound message format.

    แต่ละ adapter convert เป็น format ของ platform ตัวเอง:
    - LINE: text → TextMessage, flex → FlexMessage, file_url → URI Action button
    - Telegram (future): text → sendMessage, file_url → sendDocument
    - Discord (future): text → channel.send, flex → embeds + components
    """
    text: Optional[str] = None  # Plain text body
    flex: Optional[dict] = None  # Flex Message JSON (LINE), embeds (Discord)
    quick_reply: Optional[list[dict]] = None  # Quick reply chips
    file_url: Optional[str] = None  # For platforms that send files (Telegram/Discord)
    metadata: dict = field(default_factory=dict)


@dataclass
class BotAttachment:
    """Inbound attachment from user (file/image/audio/video)."""
    content: bytes
    filename: str
    mime_type: str
    message_id: str  # Platform-specific message ID (LINE messageId, Telegram file_id)


class BotAdapter(ABC):
    """Abstract bot adapter — each platform implements own send/receive logic.

    Each adapter encapsulates:
    - Platform-specific API client (LINE SDK, Telegram SDK, Discord SDK)
    - Authentication (channel secrets, bot tokens)
    - Format conversion (BotMessage ↔ native message format)
    - Error handling (rate limits, transient failures)
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Short identifier — 'line', 'telegram', 'discord'."""
        ...

    @abstractmethod
    async def send_message(self, recipient_id: str, message: BotMessage) -> None:
        """Send a message to a user.

        Args:
            recipient_id: platform-specific user ID
            message: BotMessage with text/flex/quick_reply
        """
        ...

    @abstractmethod
    async def reply_message(self, reply_token: str, message: BotMessage) -> None:
        """Reply to an inbound event using a reply token (LINE-specific concept,
        Telegram = sendMessage with reply_to_message_id, Discord = message.reply()).

        Reply tokens often have short expiry (LINE = 30s) — caller ต้อง ack
        webhook 200 ก่อนใช้.
        """
        ...

    @abstractmethod
    async def download_attachment(self, message_id: str) -> BotAttachment:
        """Download an inbound file/image/video/audio attachment.

        Args:
            message_id: platform-specific ID (LINE messageId)
        Returns:
            BotAttachment with bytes + filename + mime
        """
        ...

    @abstractmethod
    async def show_typing(self, recipient_id: str, duration_sec: int = 5) -> None:
        """Show typing/loading indicator (UX feedback during slow ops).

        LINE: POST /v2/bot/chat/loading/start (5-60 sec, 1:1 chat only)
        Telegram: sendChatAction (~5 sec auto-refresh)
        Discord: async with channel.typing()
        """
        ...


class NoopBotAdapter(BotAdapter):
    """Test/fallback adapter — does nothing, for unit tests + when not configured."""

    @property
    def platform_name(self) -> str:
        return "noop"

    async def send_message(self, recipient_id: str, message: BotMessage) -> None:
        return None

    async def reply_message(self, reply_token: str, message: BotMessage) -> None:
        return None

    async def download_attachment(self, message_id: str) -> BotAttachment:
        return BotAttachment(content=b"", filename="empty", mime_type="application/octet-stream", message_id=message_id)

    async def show_typing(self, recipient_id: str, duration_sec: int = 5) -> None:
        return None


# ═══════════════════════════════════════════
# LINE Bot Adapter (v8.0.0)
# ═══════════════════════════════════════════
# Note: เต็มๆ implementation อยู่ใน line_bot.py เพื่อแยก SDK imports + setup logic
# Class นี้เป็น skeleton เท่านั้น — methods จะ delegate ไป line_bot helpers
class LineBotAdapter(BotAdapter):
    """LINE Messaging API adapter (v8.0.0).

    Initialized lazily ตอน is_line_configured() == True.
    Uses line-bot-sdk v3 (linebot.v3.messaging + linebot.v3.webhooks).
    """

    def __init__(self, channel_access_token: str):
        self._access_token = channel_access_token
        # Lazy SDK client init — ลด overhead ถ้า bot not used
        self._messaging_api: Any = None

    @property
    def platform_name(self) -> str:
        return "line"

    def _ensure_client(self):
        """Lazy init MessagingApi client (avoid SDK import cost when bot not used)."""
        if self._messaging_api is None:
            from linebot.v3.messaging import (
                Configuration,
                ApiClient,
                MessagingApi,
            )
            config = Configuration(access_token=self._access_token)
            api_client = ApiClient(config)
            self._messaging_api = MessagingApi(api_client)
        return self._messaging_api

    async def send_message(self, recipient_id: str, message: BotMessage) -> None:
        """Push a message to a LINE user (uses Push API quota — 200/mo free)."""
        # Phase D = skeleton. Full impl ใน Phase E (welcome flow ใช้ push หลัง accountLink event)
        raise NotImplementedError("send_message: implement in Phase E")

    async def reply_message(self, reply_token: str, message: BotMessage) -> None:
        """Reply to a LINE event (free — doesn't count against push quota)."""
        # Phase D = skeleton. Full impl ใน Phase E
        raise NotImplementedError("reply_message: implement in Phase E")

    async def download_attachment(self, message_id: str) -> BotAttachment:
        """Fetch user-uploaded file from LINE content server (api-data.line.me)."""
        # Phase D = skeleton. Full impl ใน Phase F (file upload flow)
        raise NotImplementedError("download_attachment: implement in Phase F")

    async def show_typing(self, recipient_id: str, duration_sec: int = 5) -> None:
        """POST /v2/bot/chat/loading/start — typing indicator (1:1 only)."""
        # Phase D = skeleton. Full impl ใน Phase F (long ops UX)
        raise NotImplementedError("show_typing: implement in Phase F")


def get_line_adapter() -> Optional[LineBotAdapter]:
    """Factory: return LineBotAdapter ถ้า configured, else None.

    Caller ใน webhook handler ตรวจ None → skip ไม่ raise.
    """
    from .config import is_line_configured, LINE_CHANNEL_ACCESS_TOKEN
    if not is_line_configured():
        return None
    return LineBotAdapter(channel_access_token=LINE_CHANNEL_ACCESS_TOKEN)
