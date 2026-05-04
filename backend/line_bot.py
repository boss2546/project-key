"""LINE Bot webhook handler + signature verification (v8.0.0).

Phase D-K event handlers:
- Phase D: signature verify + dispatcher (foundation)
- Phase E: follow + accountLink + welcome flow
- Phase F: message (file/image/text + URL detection)
- Phase G: text intent dispatch (chat/search/stats/get-file) — TODO
- Phase H: forward + edge cases — TODO
- Phase I: postback (Rich Menu) — TODO

Reference: https://developers.line.biz/en/reference/messaging-api/#webhook-event-objects
"""
from __future__ import annotations
import base64
import hashlib
import hmac
import logging
from datetime import datetime as _dt
from typing import Optional

from sqlalchemy import select

from .config import LINE_CHANNEL_SECRET, APP_BASE_URL
from .database import AsyncSessionLocal, LineUser, User

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# Signature Verification (LINE spec)
# ═══════════════════════════════════════════

def verify_signature(body: bytes, signature: Optional[str]) -> bool:
    """Verify X-Line-Signature header against HMAC-SHA256(channel_secret, raw_body).

    LINE spec: https://developers.line.biz/en/reference/messaging-api/#signature-validation

    Returns:
        True ถ้า signature valid + channel secret configured
        False ถ้า: no secret / no header / HMAC mismatch (fail-closed)
    """
    if not LINE_CHANNEL_SECRET:
        logger.warning("verify_signature: LINE_CHANNEL_SECRET not configured — rejecting")
        return False
    if not signature:
        logger.warning("verify_signature: X-Line-Signature header missing — rejecting")
        return False

    expected = base64.b64encode(
        hmac.new(LINE_CHANNEL_SECRET.encode("utf-8"), body, hashlib.sha256).digest()
    ).decode("utf-8")

    return hmac.compare_digest(expected, signature)


# ═══════════════════════════════════════════
# Event Dispatcher
# ═══════════════════════════════════════════

async def handle_line_event(event: dict) -> None:
    """Dispatch a single LINE webhook event to the right handler.

    Errors caught + logged — never propagate (background task contract).
    """
    event_type = event.get("type")
    source = event.get("source", {})
    line_user_id = source.get("userId")

    logger.info("LINE event: type=%s line_user=%s", event_type, line_user_id)

    handlers = {
        "follow": _handle_follow,
        "unfollow": _handle_unfollow,
        "message": _handle_message,
        "accountLink": _handle_account_link,
        "postback": _handle_postback,
        "memberJoined": _ignore,
        "memberLeft": _ignore,
        "join": _handle_group_join,
        "leave": _ignore,
    }
    handler = handlers.get(event_type, _handle_unknown)
    try:
        await handler(event)
    except Exception as e:
        logger.exception("LINE event handler error: type=%s err=%s", event_type, e)


# ═══════════════════════════════════════════
# Phase E — Account Linking + Welcome Flow
# ═══════════════════════════════════════════

async def _handle_follow(event: dict) -> None:
    """User เพิ่ม bot เป็นเพื่อน → ส่ง link prompt card.

    Flow:
    1. Get linkToken จาก LINE API (POST /v2/bot/user/{userId}/linkToken)
    2. Build link URL: {APP_BASE_URL}/auth/line?linkToken=<token>
    3. Reply Flex card with URI button → user คลิก → /auth/line page
    4. /auth/line confirms + เรียก /api/line/confirm-link → save nonce
    5. Web frontend redirect ไป LINE accountLink dialog (Phase E.5 — TODO)
    6. หลัง user confirm → LINE ส่ง accountLink event → _handle_account_link
    """
    from .bot_adapters import get_line_adapter, BotMessage
    from .bot_messages import link_prompt_card

    line_user_id = event.get("source", {}).get("userId")
    reply_token = event.get("replyToken")
    if not line_user_id or not reply_token:
        return

    adapter = get_line_adapter()
    if not adapter:
        logger.warning("_handle_follow: LINE not configured")
        return

    # Step 1: Get linkToken from LINE API
    link_token = await adapter.issue_link_token(line_user_id)
    if not link_token:
        # Fallback: ส่ง text reply (กรณี API fail)
        await adapter.reply_message(reply_token, BotMessage(
            text="👋 ยินดีต้อนรับ! กรุณาลองใหม่อีกครั้ง — ระบบเชื่อมบัญชีไม่พร้อม"
        ))
        return

    # Step 2: Build link URL → auth-line.html
    link_url = f"{APP_BASE_URL.rstrip('/')}/auth/line?linkToken={link_token}"

    # Step 3: Reply with link prompt card
    flex = link_prompt_card(link_url)
    await adapter.reply_message(reply_token, BotMessage(flex=flex))
    logger.info("_handle_follow: link prompt sent to %s", line_user_id)


async def _handle_account_link(event: dict) -> None:
    """LINE Account Link feature webhook — fired หลัง user confirm OAuth dialog.

    Event payload:
    {
      "type": "accountLink",
      "replyToken": "...",
      "source": {"type": "user", "userId": "U..."},
      "link": {"result": "ok"|"failed", "nonce": "..."}
    }
    """
    line_user_id = event.get("source", {}).get("userId")
    reply_token = event.get("replyToken")
    link = event.get("link", {})
    nonce = link.get("nonce")
    result = link.get("result", "failed")

    if not line_user_id or not nonce:
        logger.warning("_handle_account_link: missing userId or nonce")
        return

    if result != "ok":
        logger.info("_handle_account_link: result=%s — skip", result)
        return

    # Match nonce → find LineUser row
    async with AsyncSessionLocal() as db:
        result_q = await db.execute(
            select(LineUser).where(LineUser.link_nonce == nonce)
        )
        row = result_q.scalar_one_or_none()
        if not row:
            logger.warning("_handle_account_link: no LineUser with nonce=%s", nonce[:8])
            return
        if row.link_nonce_expires_at and row.link_nonce_expires_at < _dt.utcnow():
            logger.warning("_handle_account_link: nonce expired for line_user=%s", line_user_id)
            return

        # Bind LINE user ID + clear nonce
        row.line_user_id = line_user_id
        row.link_nonce = None
        row.link_nonce_expires_at = None
        row.linked_at = _dt.utcnow()
        row.last_seen_at = _dt.utcnow()
        if row.unlinked_at:
            row.unlinked_at = None

        # Get LINE display name (best-effort)
        from .bot_adapters import get_line_adapter
        adapter = get_line_adapter()
        if adapter:
            profile = await adapter.get_user_profile(line_user_id)
            if profile:
                row.line_display_name = profile.get("displayName")

        # Load PDB user for welcome flow
        user_q = await db.execute(select(User).where(User.id == row.pdb_user_id))
        pdb_user = user_q.scalar_one_or_none()

        await db.commit()

    # Trigger welcome flow (only first link, not re-link)
    if pdb_user and not row.welcomed:
        await _send_welcome_flow(line_user_id, pdb_user, reply_token)
        async with AsyncSessionLocal() as db2:
            row2 = (await db2.execute(select(LineUser).where(LineUser.line_user_id == line_user_id))).scalar_one_or_none()
            if row2:
                row2.welcomed = True
                await db2.commit()


async def _send_welcome_flow(line_user_id: str, pdb_user: User, reply_token: Optional[str]) -> None:
    """Send 3-message welcome flow ตาม Phase E spec.

    Use reply_token ถ้ายังไม่หมดอายุ (มี <30s หลัง accountLink event).
    Otherwise fall back to push API (uses quota).
    """
    from .bot_adapters import get_line_adapter, BotMessage
    from .bot_messages import vault_status_card, text_with_quick_replies
    from .plan_limits import get_file_count, get_pack_count, get_storage_used_mb, get_limits

    adapter = get_line_adapter()
    if not adapter:
        return

    # Gather vault stats
    async with AsyncSessionLocal() as db:
        from .database import Cluster, File
        file_count = await get_file_count(db, pdb_user.id)
        pack_count = await get_pack_count(db, pdb_user.id)
        storage_mb = await get_storage_used_mb(db, pdb_user.id)
        clusters_q = await db.execute(
            select(Cluster).where(Cluster.user_id == pdb_user.id)
        )
        cluster_count = len(clusters_q.scalars().all())
        # Pending files (uploaded but not organized)
        pending_q = await db.execute(
            select(File).where(File.user_id == pdb_user.id, File.processing_status == "uploaded")
        )
        pending_count = len(pending_q.scalars().all())

    limits = get_limits(pdb_user)
    storage_limit = limits.get("storage_limit_mb", 50)

    # Message 1: Greeting (text)
    greeting = BotMessage(text=(
        f"สวัสดี {pdb_user.name or 'คุณ'} 👋\n"
        "ผม PDB Assistant — ผู้ช่วยจัดการข้อมูลส่วนตัวของคุณครับ\n"
        "เชื่อมต่อสำเร็จแล้ว ✅"
    ))

    # Message 2: Status Flex card
    status = BotMessage(flex=vault_status_card(
        user_name=pdb_user.name or "คุณ",
        file_count=file_count,
        cluster_count=cluster_count,
        pack_count=pack_count,
        storage_mb_used=storage_mb,
        storage_mb_limit=storage_limit,
        storage_mode=getattr(pdb_user, "storage_mode", "managed"),
        pending_organize=pending_count,
    ))

    # Message 3: Capabilities + Quick Reply
    capabilities = (
        "ผมทำอะไรได้บ้าง 👇\n"
        "📤 ส่งไฟล์ให้ผม → จัดให้อัตโนมัติ\n"
        "💬 ถามคำถามจากข้อมูลในตู้\n"
        "🔍 ค้นหาไฟล์ที่เกี่ยวข้อง\n"
        "📥 ขอไฟล์กลับ → ส่ง download link\n\n"
        "ลองพิมพ์มาเลย หรือใช้ปุ่มเมนูด้านล่าง ⬇️"
    )
    quick_reply_items = [
        {"label": "📤 วิธีส่งไฟล์", "data": "action=upload_help"},
        {"label": "🔍 ดูไฟล์ทั้งหมด", "data": "action=list_files"},
        {"label": "🌐 เปิดเว็บ", "text": "เปิดเว็บ"},
    ]
    capabilities_msg = BotMessage(text=capabilities, quick_reply=quick_reply_items)

    # Send 3 messages via push API — Welcome is rare (once per link) so quota
    # cost is acceptable. reply_token would batch 5 messages but adapter
    # doesn't support multi-BotMessage reply yet — defer optimization to Phase H.
    # (reply_token parameter kept for future multi-message reply support)
    await adapter.send_message(line_user_id, greeting)
    await adapter.send_message(line_user_id, status)
    await adapter.send_message(line_user_id, capabilities_msg)


# ═══════════════════════════════════════════
# Phase F — Message Handling (placeholder for now)
# ═══════════════════════════════════════════

async def _handle_message(event: dict) -> None:
    """Route message events: text → chat/intent, file → upload, image → upload."""
    msg = event.get("message", {})
    msg_type = msg.get("type")
    line_user_id = event.get("source", {}).get("userId")
    reply_token = event.get("replyToken")

    if not line_user_id:
        return

    # Update last_seen_at
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(LineUser).where(
                LineUser.line_user_id == line_user_id,
                LineUser.unlinked_at.is_(None),
            )
        )
        row = result.scalar_one_or_none()

    if not row or not row.pdb_user_id:
        # Not linked → prompt link with Flex+button (issues linkToken)
        await _reply_not_linked(reply_token, line_user_id=line_user_id)
        return

    # Update last_seen_at
    async with AsyncSessionLocal() as db:
        row2 = (await db.execute(
            select(LineUser).where(LineUser.line_user_id == line_user_id)
        )).scalar_one_or_none()
        if row2:
            row2.last_seen_at = _dt.utcnow()
            await db.commit()

    if msg_type == "text":
        await _handle_text_message(event, row.pdb_user_id)
    elif msg_type in ("file", "image", "video", "audio"):
        await _handle_file_message(event, row.pdb_user_id, msg_type)
    else:
        logger.info("Unsupported message type: %s", msg_type)


async def _reply_not_linked(reply_token: Optional[str], line_user_id: Optional[str] = None) -> None:
    """User send message ก่อน link → issue linkToken + ส่ง Flex card with login button.

    Flow:
    1. POST /v2/bot/user/{userId}/linkToken → get fresh linkToken
    2. Build link URL: {APP_BASE_URL}/auth/line?linkToken=<token>
    3. Reply Flex card (link_prompt_card) → ปุ่มกดเปิดหน้า login PDB
    4. (Fallback) ถ้า issue token ไม่ผ่าน → text + URL plain

    เรียกได้ทั้งจาก /start คำสั่ง หรือทุกครั้งที่ unlinked user ส่งข้อความเข้ามา.
    """
    from .bot_adapters import get_line_adapter, BotMessage
    from .bot_messages import link_prompt_card

    if not reply_token:
        return
    adapter = get_line_adapter()
    if not adapter:
        return

    link_url: Optional[str] = None
    if line_user_id:
        try:
            link_token = await adapter.issue_link_token(line_user_id)
            if link_token:
                link_url = f"{APP_BASE_URL.rstrip('/')}/auth/line?linkToken={link_token}"
        except Exception as e:
            logger.warning("_reply_not_linked: issue_link_token failed: %s", e)

    if link_url:
        flex = link_prompt_card(link_url)
        await adapter.reply_message(reply_token, BotMessage(flex=flex))
    else:
        # Fallback: plain text + base URL (กรณี LINE API fail)
        await adapter.reply_message(reply_token, BotMessage(
            text=(
                "🔗 กรุณาเชื่อมบัญชี Personal Data Bank ก่อนเริ่มใช้งานครับ\n\n"
                f"เปิดเว็บ: {APP_BASE_URL.rstrip('/')}/app\n"
                "หรือพิมพ์ /start อีกครั้งเพื่อขอลิงก์ใหม่"
            )
        ))


async def _handle_text_message(event: dict, pdb_user_id: str) -> None:
    """Phase G — dispatch text to bot_handlers.handle_text_intent.

    Intents: STATS / SEARCH / GET_FILE / HELP / CHAT (default RAG)
    Returns 0+ BotMessages — first via reply_message (free), rest via push API.

    Special case: "เปิดเว็บ" → quick redirect link (handled inline, no LLM call)
    """
    from .bot_adapters import get_line_adapter, BotMessage
    from .bot_handlers import handle_text_intent

    text = event.get("message", {}).get("text", "").strip()
    reply_token = event.get("replyToken")
    line_user_id = event.get("source", {}).get("userId")
    if not text:
        return

    adapter = get_line_adapter()
    if not adapter:
        return

    # Quick shortcut: "เปิดเว็บ" / "open web" → web URL
    if text.lower().strip() in ("เปิดเว็บ", "open web", "web"):
        if reply_token:
            await adapter.reply_message(reply_token, BotMessage(
                text=f"🌐 เปิดเว็บ Personal Data Bank:\n{APP_BASE_URL.rstrip('/')}/app"
            ))
        return

    # Show loading indicator (best effort) — RAG/search อาจช้า
    try:
        if line_user_id:
            await adapter.show_typing(line_user_id, duration_sec=10)
    except Exception:
        pass

    # Dispatch to bot_handlers (platform-agnostic)
    try:
        messages = await handle_text_intent(pdb_user_id, text)
    except Exception as e:
        logger.exception("handle_text_intent failed: %s", e)
        if reply_token:
            await adapter.reply_message(reply_token, BotMessage(text="ขอโทษ ระบบมีปัญหา ลองใหม่อีกครั้ง"))
        return

    if not messages:
        return

    # First message via reply (free), rest via push (uses quota — only when 2+ msgs)
    if reply_token:
        await adapter.reply_message(reply_token, messages[0])
    else:
        # Reply token expired/missing → all via push
        if line_user_id:
            await adapter.send_message(line_user_id, messages[0])

    if line_user_id and len(messages) > 1:
        for msg in messages[1:]:
            await adapter.send_message(line_user_id, msg)


async def _handle_file_message(event: dict, pdb_user_id: str, msg_type: str) -> None:
    """Phase F — handle file/image/video/audio upload.

    Flow:
    1. Show typing indicator
    2. Download attachment from LINE
    3. Save to disk + extract text + plan limit check
    4. (BYOS) push to Drive
    5. Reply Flex confirmation card with download link
    """
    from .bot_adapters import get_line_adapter, BotMessage
    from .bot_messages import file_upload_confirmation_card, error_card
    from .plan_limits import check_upload_allowed
    from .extraction import extract_text
    from .duplicate_detector import compute_content_hash
    from .storage_router import push_raw_file_to_drive_if_byos
    from .signed_urls import sign_download_token
    from .database import gen_id, File
    from .config import UPLOAD_DIR
    import os

    msg = event.get("message", {})
    message_id = msg.get("id")
    reply_token = event.get("replyToken")
    line_user_id = event.get("source", {}).get("userId")
    if not message_id or not line_user_id:
        return

    adapter = get_line_adapter()
    if not adapter:
        return

    # Show loading indicator (best effort)
    try:
        await adapter.show_typing(line_user_id, duration_sec=20)
    except Exception:
        pass

    # Download from LINE
    try:
        attachment = await adapter.download_attachment(message_id)
    except Exception as e:
        logger.exception("download_attachment failed: %s", e)
        await adapter.reply_message(
            reply_token,
            BotMessage(text="ดาวน์โหลดไฟล์ไม่สำเร็จ ลองส่งใหม่อีกครั้ง"),
            fallback_user_id=line_user_id,
        )
        return

    filename = msg.get("fileName") or attachment.filename
    ext = (filename.rsplit(".", 1)[-1].lower() if "." in filename else "") or "bin"
    contents = attachment.content

    # Plan limit check
    async with AsyncSessionLocal() as db:
        user_q = await db.execute(select(User).where(User.id == pdb_user_id))
        user = user_q.scalar_one_or_none()
        if not user:
            return

        check = await check_upload_allowed(db, user, len(contents), ext)
        if check is not None:
            err = check.get("error", "Upload ไม่สำเร็จ")
            upgrade = check.get("upgrade", False)
            upgrade_url = f"{APP_BASE_URL.rstrip('/')}/app" if upgrade else None
            flex = error_card(
                title="เกินขีดจำกัด" if upgrade else "Upload ไม่สำเร็จ",
                message=err,
                suggestion=("อัปเกรด Starter เพื่อปลดล็อกโควต้าเต็ม" if upgrade else None),
                upgrade_url=upgrade_url,
            )
            await adapter.reply_message(reply_token, BotMessage(flex=flex))
            return

        # Save raw file
        file_id = gen_id()
        user_dir = os.path.join(UPLOAD_DIR, pdb_user_id)
        os.makedirs(user_dir, exist_ok=True)
        raw_path = os.path.join(user_dir, f"{file_id}_{filename}")
        with open(raw_path, "wb") as f:
            f.write(contents)

        # Extract text
        try:
            extracted = extract_text(raw_path, ext)
        except Exception as e:
            logger.exception("extract_text failed: %s", e)
            extracted = ""

        content_hash = compute_content_hash(extracted)

        db_file = File(
            id=file_id,
            user_id=pdb_user_id,
            filename=filename,
            filetype=ext,
            raw_path=raw_path,
            extracted_text=extracted,
            processing_status="uploaded",
            content_hash=content_hash,
        )
        db.add(db_file)
        await db.commit()

        # BYOS push (best effort)
        try:
            await push_raw_file_to_drive_if_byos(
                pdb_user_id, db, file_id, filename, contents, attachment.mime_type
            )
        except Exception as e:
            logger.warning("BYOS push failed for LINE upload %s: %s", file_id, e)

    # Build confirmation card with download URL (signed)
    token = sign_download_token(file_id, pdb_user_id, ttl_seconds=1800)
    download_url = f"{APP_BASE_URL.rstrip('/')}/d/{token}"
    web_url = f"{APP_BASE_URL.rstrip('/')}/app"

    flex = file_upload_confirmation_card(
        file_id=file_id,
        filename=filename,
        filetype=ext,
        text_length=len(extracted),
        cluster_title=None,  # Not yet organized — Phase F.5 will trigger organize
        download_url=download_url,
        web_url=web_url,
    )
    # Phase H: file upload pipeline can take >30s (extract + BYOS push).
    # Reply token may have expired → adapter falls back to push API.
    await adapter.reply_message(
        reply_token, BotMessage(flex=flex), fallback_user_id=line_user_id
    )
    logger.info("LINE file upload OK: file=%s user=%s type=%s", file_id, pdb_user_id, msg_type)

    # v8.0.5 — Auto-organize: fire-and-forget background task.
    # User wants the file processed (cluster + summary + insights + duplicate check)
    # without having to open the web app. Don't await — keep the webhook response fast.
    import asyncio as _asyncio
    _asyncio.create_task(_auto_organize_after_upload(pdb_user_id, line_user_id, filename))


async def _auto_organize_after_upload(pdb_user_id: str, line_user_id: str, filename: str) -> None:
    """Run organize-new pipeline for the user, then push a brief status message.

    Fire-and-forget — caller does not await. Errors are swallowed but logged
    (we never want a stuck organize to block future uploads).
    """
    from .bot_adapters import get_line_adapter, BotMessage
    from .organizer import organize_new_files
    from .metadata import enrich_all_files
    from .graph_builder import build_full_graph
    from .relations import generate_suggestions

    adapter = get_line_adapter()

    try:
        async with AsyncSessionLocal() as db:
            result = await organize_new_files(db, pdb_user_id)
            await db.commit()

            if result.get("skipped"):
                logger.info("auto-organize skipped (no new files) user=%s", pdb_user_id)
                return

            # Best-effort enrichment + graph + suggestions (same as web "Organize new")
            try:
                await enrich_all_files(db, pdb_user_id)
            except Exception as e:
                logger.warning("enrich_all_files failed in auto-organize: %s", e)
            try:
                await build_full_graph(db, pdb_user_id)
            except Exception as e:
                logger.warning("build_full_graph failed in auto-organize: %s", e)
            try:
                await generate_suggestions(db, pdb_user_id)
            except Exception as e:
                logger.warning("generate_suggestions failed in auto-organize: %s", e)

        count = result.get("count", 0)
        logger.info("auto-organize done: %d files processed for user=%s", count, pdb_user_id)

        # Notify user via push (best-effort)
        if adapter and line_user_id:
            try:
                msg_text = (
                    f"จัดการไฟล์ {filename} เรียบร้อยแล้วครับ "
                    f"({count} ไฟล์ใหม่ถูกสรุปและจัดกลุ่มอัตโนมัติ)"
                )
                await adapter.send_message(line_user_id, BotMessage(text=msg_text))
            except Exception as e:
                logger.warning("auto-organize push notify failed: %s", e)
    except Exception as e:
        logger.exception("auto-organize task failed for user=%s: %s", pdb_user_id, e)


# ═══════════════════════════════════════════
# Other handlers (placeholders / ignore)
# ═══════════════════════════════════════════

async def _handle_unfollow(event: dict) -> None:
    """User remove bot — soft-unlink via unlinked_at (preserve history)."""
    line_user_id = event.get("source", {}).get("userId")
    if not line_user_id:
        return
    async with AsyncSessionLocal() as db:
        row = (await db.execute(
            select(LineUser).where(LineUser.line_user_id == line_user_id)
        )).scalar_one_or_none()
        if row and not row.unlinked_at:
            row.unlinked_at = _dt.utcnow()
            await db.commit()
            logger.info("_handle_unfollow: soft-unlinked %s", line_user_id)


async def _handle_postback(event: dict) -> None:
    """Phase F/I — Handle Postback events (Quick Reply or Rich Menu)."""
    from urllib.parse import parse_qsl
    from .bot_adapters import get_line_adapter, BotMessage
    
    data = event.get("postback", {}).get("data", "")
    reply_token = event.get("replyToken")
    line_user_id = event.get("source", {}).get("userId")
    if not data or not line_user_id:
        return

    logger.info("postback: data=%s", data[:50])
    parsed = dict(parse_qsl(data))
    action = parsed.get("action")

    # Find the linked user
    async with AsyncSessionLocal() as db:
        row = (await db.execute(
            select(LineUser).where(LineUser.line_user_id == line_user_id)
        )).scalar_one_or_none()
    
    if not row or not row.pdb_user_id:
        await _reply_not_linked(reply_token, line_user_id=line_user_id)
        return

    if action == "upload_url":
        url = parsed.get("url")
        if not url:
            return

        adapter = get_line_adapter()
        if adapter:
            # show typing indicator
            try:
                await adapter.show_typing(line_user_id, duration_sec=15)
            except Exception:
                pass

        from .bot_handlers import handle_url_upload
        messages = await handle_url_upload(row.pdb_user_id, url)

        if adapter and messages:
            if reply_token:
                await adapter.reply_message(
                    reply_token, messages[0], fallback_user_id=line_user_id
                )
            else:
                await adapter.send_message(line_user_id, messages[0])

    elif action == "upload_help":
        # Phase I — Rich Menu "Upload" button
        adapter = get_line_adapter()
        if adapter and reply_token:
            await adapter.reply_message(reply_token, BotMessage(
                text=(
                    "📤 วิธีส่งไฟล์เข้า Personal Data Bank\n\n"
                    "ส่งไฟล์ตรงนี้ได้เลย — ผมรองรับ:\n"
                    "📕 PDF / 📘 DOCX / 📊 CSV / 📝 TXT, MD\n"
                    "🖼️ ภาพ (PNG, JPG)\n\n"
                    "หรือส่งลิงก์เว็บ → ผมจะถามว่าจะให้เก็บไหม"
                )
            ), fallback_user_id=line_user_id)

    elif action == "settings":
        # Phase I — Rich Menu "Settings" button
        from .config import APP_BASE_URL
        adapter = get_line_adapter()
        if adapter and reply_token:
            await adapter.reply_message(reply_token, BotMessage(
                text=(
                    "⚙️ ตั้งค่าบัญชี\n\n"
                    "ตั้งค่า profile, เปลี่ยน plan, จัดการ storage mode\n"
                    f"กรุณาเข้าเว็บ: {APP_BASE_URL.rstrip('/')}/app"
                )
            ), fallback_user_id=line_user_id)

    elif action == "organize_now":
        # Phase E status card "จัดระเบียบเลย" button
        from .organizer import organize_files
        adapter = get_line_adapter()
        if adapter and reply_token:
            try:
                await adapter.show_typing(line_user_id, duration_sec=20)
            except Exception:
                pass

        try:
            async with AsyncSessionLocal() as db:
                await organize_files(db, row.pdb_user_id)
            if adapter and reply_token:
                await adapter.reply_message(reply_token, BotMessage(
                    text="✅ จัดระเบียบเสร็จแล้วครับ — พิมพ์ 'สถานะ' เพื่อดูผลลัพธ์"
                ), fallback_user_id=line_user_id)
        except Exception as e:
            logger.exception("organize_now failed: %s", e)
            if adapter and reply_token:
                await adapter.reply_message(reply_token, BotMessage(
                    text=f"จัดระเบียบไม่สำเร็จ: {str(e)[:80]}"
                ), fallback_user_id=line_user_id)

    elif action == "open_file":
        # Search carousel "เปิดดู" button → return signed download URL
        file_id = parsed.get("file_id")
        if not file_id:
            return
        from .bot_handlers import _handle_get_file
        from .database import File
        async with AsyncSessionLocal() as db:
            file_row = (await db.execute(
                select(File).where(File.id == file_id, File.user_id == row.pdb_user_id)
            )).scalar_one_or_none()
        adapter = get_line_adapter()
        if not adapter or not file_row:
            return
        # Reuse get_file handler with filename (single-match path returns Flex card)
        messages = await _handle_get_file(row.pdb_user_id, file_row.filename)
        if reply_token and messages:
            await adapter.reply_message(
                reply_token, messages[0], fallback_user_id=line_user_id
            )

    else:
        logger.info("Unknown postback action: %s", action)


async def _handle_group_join(event: dict) -> None:
    """Bot ถูก add เข้า group/room — PDB เป็น 1:1 only.

    Phase H: ตอบ politely + ออกจาก group ทันที (LINE API leave endpoint).
    """
    from .bot_adapters import get_line_adapter, BotMessage
    import httpx

    source = event.get("source", {})
    source_type = source.get("type")  # "group" or "room"
    group_id = source.get("groupId") or source.get("roomId")
    reply_token = event.get("replyToken")

    if not group_id or source_type not in ("group", "room"):
        logger.info("_handle_group_join: not a group/room — ignoring")
        return

    adapter = get_line_adapter()
    if not adapter:
        return

    # Reply with polite message before leaving
    if reply_token:
        try:
            await adapter.reply_message(reply_token, BotMessage(
                text="สวัสดีครับ — ผม PDB Assistant ทำงานเฉพาะแชท 1:1 ครับ\n"
                     "กรุณาเพิ่มผมเป็นเพื่อนใน LINE แทน เพื่อใช้งานเก็บข้อมูลส่วนตัวได้"
            ))
        except Exception as e:
            logger.warning("group reply failed: %s", e)

    # Leave the group/room via LINE API
    endpoint = f"{adapter.BASE_URL}/v2/bot/{source_type}/{group_id}/leave"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, headers=adapter._headers())
            if resp.status_code < 400:
                logger.info("Left %s %s", source_type, group_id)
            else:
                logger.warning("Leave %s failed: %s %s", source_type, resp.status_code, resp.text[:200])
    except Exception as e:
        logger.exception("Leave %s exception: %s", source_type, e)


async def _ignore(event: dict) -> None:
    logger.debug("Ignored event: type=%s", event.get("type"))


async def _handle_unknown(event: dict) -> None:
    logger.warning("Unknown LINE event type: %s", event.get("type"))
