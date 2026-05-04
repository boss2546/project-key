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
from typing import Optional


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
    Uses HTTP API directly (httpx) แทน line-bot-sdk async wrapper เพื่อ:
    - Async-native (SDK เป็น sync, ต้อง wrap)
    - Less dependency surface — รู้ exact endpoints + payloads
    - Easy to mock ใน tests (mock httpx.AsyncClient)

    All LINE Messaging API endpoints documented at:
    https://developers.line.biz/en/reference/messaging-api/
    """

    BASE_URL = "https://api.line.me"
    DATA_URL = "https://api-data.line.me"

    def __init__(self, channel_access_token: str):
        self._access_token = channel_access_token

    @property
    def platform_name(self) -> str:
        return "line"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _convert_message(self, message: BotMessage) -> list[dict]:
        """Convert BotMessage → list of LINE message objects (max 5 per call)."""
        out = []
        if message.text:
            text_msg: dict = {"type": "text", "text": message.text}
            if message.quick_reply:
                # Already in LINE quickReply format ถ้ามาจาก bot_messages.text_with_quick_replies
                items = []
                for qr in message.quick_reply[:13]:
                    if "type" in qr and qr.get("type") == "action":
                        items.append(qr)
                    elif "data" in qr:
                        items.append({"type": "action", "action": {
                            "type": "postback", "label": qr["label"], "data": qr["data"]
                        }})
                    else:
                        items.append({"type": "action", "action": {
                            "type": "message", "label": qr["label"], "text": qr.get("text", qr["label"])
                        }})
                if items:
                    text_msg["quickReply"] = {"items": items}
            out.append(text_msg)
        if message.flex:
            out.append(message.flex)
        return out[:5]  # LINE limit

    async def send_message(self, recipient_id: str, message: BotMessage) -> None:
        """Push a message via /v2/bot/message/push (uses quota: 200/mo free)."""
        import httpx
        import logging
        log = logging.getLogger(__name__)
        msgs = self._convert_message(message)
        if not msgs:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v2/bot/message/push",
                headers=self._headers(),
                json={"to": recipient_id, "messages": msgs},
            )
            if resp.status_code >= 400:
                log.warning("LINE push failed: %s %s", resp.status_code, resp.text[:200])

    async def reply_message(self, reply_token: str, message: BotMessage) -> None:
        """Reply via /v2/bot/message/reply (free — doesn't count quota).

        Reply token expires 30s — caller ต้อง ack webhook 200 ก่อน + reply เร็ว.
        """
        import httpx
        import logging
        log = logging.getLogger(__name__)
        msgs = self._convert_message(message)
        if not msgs:
            return
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v2/bot/message/reply",
                headers=self._headers(),
                json={"replyToken": reply_token, "messages": msgs},
            )
            if resp.status_code >= 400:
                log.warning("LINE reply failed: %s %s", resp.status_code, resp.text[:200])

    async def download_attachment(self, message_id: str) -> BotAttachment:
        """Fetch user-uploaded file from api-data.line.me/v2/bot/message/{id}/content.

        Returns bytes + inferred filename + content-type. LINE doesn't always
        provide filename for image/video/audio — caller สามารถ override ผ่าน
        event.message.fileName (only for `file` type messages).
        """
        import httpx
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{self.DATA_URL}/v2/bot/message/{message_id}/content",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            resp.raise_for_status()
            content = resp.content
            mime_type = (resp.headers.get("content-type") or "application/octet-stream").split(";")[0].strip()
            # Infer filename from content-disposition or fallback
            cd = resp.headers.get("content-disposition", "")
            import re
            m = re.search(r'filename="?([^";]+)"?', cd)
            filename = m.group(1) if m else f"line_{message_id}.{_mime_to_ext(mime_type)}"
        return BotAttachment(
            content=content,
            filename=filename,
            mime_type=mime_type,
            message_id=message_id,
        )

    async def show_typing(self, recipient_id: str, duration_sec: int = 5) -> None:
        """POST /v2/bot/chat/loading/start — show loading indicator (1:1 only).

        duration_sec must be 5-60 (LINE spec).
        """
        import httpx
        import logging
        log = logging.getLogger(__name__)
        if duration_sec < 5:
            duration_sec = 5
        elif duration_sec > 60:
            duration_sec = 60
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{self.BASE_URL}/v2/bot/chat/loading/start",
                headers=self._headers(),
                json={"chatId": recipient_id, "loadingSeconds": duration_sec},
            )
            if resp.status_code >= 400:
                log.debug("LINE loading indicator failed (non-fatal): %s", resp.status_code)

    async def issue_link_token(self, line_user_id: str) -> Optional[str]:
        """POST /v2/bot/user/{userId}/linkToken — get linkToken for Account Link feature.

        Returns linkToken string ที่ใช้ build URL: /auth/line?linkToken=<token>
        Returns None ถ้า LINE API fail.
        """
        import httpx
        import logging
        log = logging.getLogger(__name__)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.BASE_URL}/v2/bot/user/{line_user_id}/linkToken",
                    headers=self._headers(),
                )
                if resp.status_code != 200:
                    log.warning("issue_link_token failed: %s %s", resp.status_code, resp.text[:200])
                    return None
                return resp.json().get("linkToken")
        except Exception as e:
            log.exception("issue_link_token error: %s", e)
            return None

    async def get_user_profile(self, line_user_id: str) -> Optional[dict]:
        """GET /v2/bot/profile/{userId} — fetch display name + picture."""
        import httpx
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{self.BASE_URL}/v2/bot/profile/{line_user_id}",
                    headers={"Authorization": f"Bearer {self._access_token}"},
                )
                if resp.status_code != 200:
                    return None
                return resp.json()
        except Exception:
            return None


_MIME_EXT_MAP = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "audio/mpeg": "mp3",
    "audio/m4a": "m4a",
    "audio/mp4": "m4a",
    "audio/x-m4a": "m4a",
    "video/mp4": "mp4",
    "application/pdf": "pdf",
    "application/zip": "zip",
}


def _mime_to_ext(mime: str) -> str:
    return _MIME_EXT_MAP.get(mime.lower(), "bin")


def get_line_adapter() -> Optional[LineBotAdapter]:
    """Factory: return LineBotAdapter ถ้า configured, else None.

    Caller ใน webhook handler ตรวจ None → skip ไม่ raise.
    """
    from .config import is_line_configured, LINE_CHANNEL_ACCESS_TOKEN
    if not is_line_configured():
        return None
    return LineBotAdapter(channel_access_token=LINE_CHANNEL_ACCESS_TOKEN)
