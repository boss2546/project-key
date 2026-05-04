"""LINE Bot webhook handler + signature verification (v8.0.0).

Handles inbound LINE webhook events:
- follow / unfollow — user เพิ่ม/ลบ bot
- message (text/image/file/audio/video) — user ส่งข้อความ/ไฟล์
- accountLink — LINE Account Link feature (post-OAuth callback)
- postback — Rich Menu / Quick Reply button taps

Phase D scope (this file in v7.6.0/v8.0.0 foundation):
- verify_signature() — HMAC-SHA256 ตาม LINE spec
- handle_line_event() — dispatcher placeholder (full handlers ใน Phase E-K)

Reference: https://developers.line.biz/en/reference/messaging-api/#webhook-event-objects
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import logging
from typing import Optional

from .config import LINE_CHANNEL_SECRET

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Signature Verification (LINE spec)
# ═══════════════════════════════════════════

def verify_signature(body: bytes, signature: Optional[str]) -> bool:
    """Verify X-Line-Signature header against HMAC-SHA256(channel_secret, raw_body).

    LINE spec: https://developers.line.biz/en/reference/messaging-api/#signature-validation

    Args:
        body: raw request body (bytes — สำคัญ! ห้าม parse JSON ก่อน)
        signature: ค่าจาก X-Line-Signature header (base64-encoded HMAC-SHA256)

    Returns:
        True ถ้า signature valid + channel secret configured
        False ถ้า:
        - LINE_CHANNEL_SECRET not configured (fail closed — กัน accidental open webhook)
        - signature header missing
        - HMAC mismatch

    Note: ใช้ hmac.compare_digest() กัน timing attack
    """
    if not LINE_CHANNEL_SECRET:
        logger.warning("verify_signature: LINE_CHANNEL_SECRET not configured — rejecting")
        return False
    if not signature:
        logger.warning("verify_signature: X-Line-Signature header missing — rejecting")
        return False

    expected = base64.b64encode(
        hmac.new(
            LINE_CHANNEL_SECRET.encode("utf-8"),
            body,
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    # constant-time compare
    return hmac.compare_digest(expected, signature)


# ═══════════════════════════════════════════
# Event Dispatcher
# ═══════════════════════════════════════════

async def handle_line_event(event: dict) -> None:
    """Dispatch a single LINE webhook event to the right handler.

    Phase D scope = skeleton (logs + returns). Full handlers จะ implement
    ใน Phase E-K:
    - Phase E: follow + accountLink
    - Phase F: message (file/image/video/audio)
    - Phase G: message (text — chat/search/stats/get-file intents)
    - Phase H: forward + edge cases
    - Phase I: postback (Rich Menu)

    Args:
        event: LINE webhook event dict (1 of array จาก webhook payload)
    """
    event_type = event.get("type")
    source = event.get("source", {})
    line_user_id = source.get("userId")

    logger.info(
        "LINE event received: type=%s line_user_id=%s",
        event_type,
        line_user_id,
    )

    # Phase D placeholder — log only. Real handlers ใน Phase E onward.
    handlers = {
        "follow": _handle_follow_placeholder,
        "unfollow": _handle_unfollow_placeholder,
        "message": _handle_message_placeholder,
        "accountLink": _handle_account_link_placeholder,
        "postback": _handle_postback_placeholder,
        "memberJoined": _ignore,
        "memberLeft": _ignore,
        "join": _ignore,  # bot ถูก add เข้า group/room
        "leave": _ignore,
    }
    handler = handlers.get(event_type, _handle_unknown)
    try:
        await handler(event)
    except Exception as e:
        # ห้าม raise ออกจาก background task — log + continue
        logger.exception("LINE event handler error: type=%s err=%s", event_type, e)


# ─── Placeholder handlers (Phase D — log only, return None) ───
async def _handle_follow_placeholder(event: dict) -> None:
    user_id = event.get("source", {}).get("userId")
    logger.info("follow event (placeholder): user_id=%s — Phase E will send link prompt", user_id)


async def _handle_unfollow_placeholder(event: dict) -> None:
    user_id = event.get("source", {}).get("userId")
    logger.info("unfollow event (placeholder): user_id=%s", user_id)


async def _handle_message_placeholder(event: dict) -> None:
    msg_type = event.get("message", {}).get("type")
    user_id = event.get("source", {}).get("userId")
    logger.info(
        "message event (placeholder): user_id=%s msg_type=%s — Phase F/G will handle",
        user_id, msg_type,
    )


async def _handle_account_link_placeholder(event: dict) -> None:
    user_id = event.get("source", {}).get("userId")
    nonce = event.get("link", {}).get("nonce")
    logger.info(
        "accountLink event (placeholder): user_id=%s nonce=%s — Phase E will match nonce",
        user_id, nonce[:8] if nonce else None,
    )


async def _handle_postback_placeholder(event: dict) -> None:
    user_id = event.get("source", {}).get("userId")
    data = event.get("postback", {}).get("data")
    logger.info(
        "postback event (placeholder): user_id=%s data=%s — Phase I (Rich Menu) will handle",
        user_id, data,
    )


async def _ignore(event: dict) -> None:
    """Events ที่เรา ignore (group/room — bot รองรับ 1:1 chat เท่านั้น)."""
    logger.debug("Ignored event: type=%s", event.get("type"))


async def _handle_unknown(event: dict) -> None:
    """Unknown event type — log warning + continue (forward-compat)."""
    logger.warning("Unknown LINE event type: %s", event.get("type"))
