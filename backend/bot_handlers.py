"""Platform-agnostic bot intent dispatch (v8.0.0 Phase G).

หน้าที่: รับ text → ตรวจ intent → return BotMessage(s)

ออกแบบให้ platform-agnostic — ไม่ import linebot SDK / Telegram SDK ตรง.
Caller (line_bot.py / future telegram_bot.py) เรียก handle_text_intent() แล้ว
adapter convert BotMessage → platform-specific format.

Intents:
- INTENT_STATS — "กี่ไฟล์" / "stats" / "สถานะ"
- INTENT_SEARCH — "หา X" / "ค้นหา" / "search X"
- INTENT_GET_FILE — "ขอไฟล์ X" / "ส่ง X" / "send file X"
- INTENT_HELP — "/help" / "ช่วยเหลือ"
- INTENT_CHAT (default) — anything else → AI chat with retrieval
"""
from __future__ import annotations
import logging
import re
from enum import Enum
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .bot_adapters import BotMessage
from .bot_messages import (
    vault_status_card,
    file_search_carousel,
    file_upload_confirmation_card,
)
from .config import APP_BASE_URL
from .database import (
    AsyncSessionLocal,
    Cluster,
    ContextPack,
    File,
    User,
)
from .plan_limits import (
    get_file_count,
    get_pack_count,
    get_storage_used_mb,
    get_limits,
)

logger = logging.getLogger(__name__)


class Intent(str, Enum):
    STATS = "stats"
    SEARCH = "search"
    GET_FILE = "get_file"
    HELP = "help"
    CHAT = "chat"
    URL_UPLOAD = "url_upload"


# Keyword patterns (Thai + English)
_STATS_KEYWORDS = [
    "กี่ไฟล์", "ทั้งหมด", "stats", "สถานะ", "status",
    "ฉันมี", "i have", "ดูตู้",
]
_SEARCH_KEYWORDS_PREFIX = ["หาไฟล์", "ค้นหา", "search", "find", "หา ", "ค้น ", "หาไฟล์เรื่อง"]
_GETFILE_KEYWORDS = ["ขอไฟล์", "ส่งไฟล์", "ขอ file", "send file", "download", "ดาวน์โหลด"]
_HELP_KEYWORDS = ["/help", "ช่วยเหลือ", "วิธีใช้", "help", "/start"]


def detect_intent(text: str) -> tuple[Intent, str]:
    """Classify text into Intent + return cleaned query string for downstream handler.

    Order matters: more specific patterns first.
    Returns (intent, query) where query has prefix stripped (e.g., "หาไฟล์ AI" → "AI").
    """
    if not text:
        return Intent.CHAT, ""

    lowered = text.lower().strip()

    # URL detection (highest priority after Help)
    url_match = re.search(r'(https?://[^\s]+)', text)
    if url_match:
        return Intent.URL_UPLOAD, url_match.group(1)

    # Help (highest priority — exact-ish match)
    for kw in _HELP_KEYWORDS:
        if lowered == kw or lowered.startswith(kw + " "):
            return Intent.HELP, ""

    # Get file (more specific than search)
    for kw in _GETFILE_KEYWORDS:
        if kw in lowered:
            # Strip the keyword to get filename hint
            query = re.sub(re.escape(kw), "", text, count=1, flags=re.IGNORECASE).strip()
            return Intent.GET_FILE, query

    # Search
    for kw in _SEARCH_KEYWORDS_PREFIX:
        if lowered.startswith(kw):
            query = text[len(kw):].strip()
            return Intent.SEARCH, query
        # also fuzzy: "ค้น" + word
        if " " + kw + " " in " " + lowered + " ":
            query = re.sub(re.escape(kw), "", text, count=1, flags=re.IGNORECASE).strip()
            return Intent.SEARCH, query

    # Stats (least specific keywords — check after SEARCH+GET_FILE)
    for kw in _STATS_KEYWORDS:
        if kw in lowered:
            return Intent.STATS, ""

    # Default → chat (RAG over user data)
    return Intent.CHAT, text


# ═══════════════════════════════════════════
# Intent Handlers — return list[BotMessage]
# ═══════════════════════════════════════════

async def handle_text_intent(pdb_user_id: str, text: str) -> list[BotMessage]:
    """Top-level dispatch — returns 0+ BotMessages to send back to user.

    Caller (LINE adapter etc.) iterates and calls reply/send for each.
    """
    intent, query = detect_intent(text)
    logger.info("Intent: user=%s intent=%s query_preview=%s", pdb_user_id, intent.value, query[:60])

    if intent == Intent.STATS:
        return await _handle_stats(pdb_user_id)
    if intent == Intent.HELP:
        return _handle_help()
    if intent == Intent.SEARCH:
        if not query:
            return [BotMessage(text="คำค้นว่างเปล่า — ลอง 'หาไฟล์เรื่อง AI' หรือ 'ค้นหา machine learning'")]
        return await _handle_search(pdb_user_id, query)
    if intent == Intent.GET_FILE:
        if not query:
            return [BotMessage(text="กรุณาระบุชื่อไฟล์ — เช่น 'ขอไฟล์ thesis.pdf'")]
        return await _handle_get_file(pdb_user_id, query)
    if intent == Intent.URL_UPLOAD:
        return await _handle_url_prompt(pdb_user_id, query)
    # Default = CHAT
    return await _handle_chat(pdb_user_id, text)


async def _handle_stats(pdb_user_id: str) -> list[BotMessage]:
    """Return Flex status card with vault overview."""
    async with AsyncSessionLocal() as db:
        user_q = await db.execute(select(User).where(User.id == pdb_user_id))
        user = user_q.scalar_one_or_none()
        if not user:
            return [BotMessage(text="ไม่พบบัญชีของคุณ — กรุณาเชื่อมบัญชีใหม่")]

        file_count = await get_file_count(db, pdb_user_id)
        pack_count = await get_pack_count(db, pdb_user_id)
        storage_mb = await get_storage_used_mb(db, pdb_user_id)
        clusters_q = await db.execute(
            select(Cluster).where(Cluster.user_id == pdb_user_id)
        )
        cluster_count = len(clusters_q.scalars().all())
        pending_q = await db.execute(
            select(File).where(
                File.user_id == pdb_user_id, File.processing_status == "uploaded"
            )
        )
        pending = len(pending_q.scalars().all())

    limits = get_limits(user)
    flex = vault_status_card(
        user_name=user.name or "คุณ",
        file_count=file_count,
        cluster_count=cluster_count,
        pack_count=pack_count,
        storage_mb_used=storage_mb,
        storage_mb_limit=limits.get("storage_limit_mb", 50),
        storage_mode=getattr(user, "storage_mode", "managed"),
        pending_organize=pending,
    )
    return [BotMessage(flex=flex)]


def _handle_help() -> list[BotMessage]:
    """Static help text + Quick Reply."""
    text = (
        "🤖 PDB Assistant — คำสั่งที่ใช้ได้\n\n"
        "📤 ส่งไฟล์ (PDF/DOCX/รูป) → ผมจะเก็บใน data bank\n"
        "🔍 \"หาไฟล์เรื่อง AI\" → ค้นหาไฟล์ที่เกี่ยวข้อง\n"
        "📥 \"ขอไฟล์ thesis.pdf\" → ผมส่ง download link\n"
        "📊 \"กี่ไฟล์\" / \"สถานะ\" → ดูสถานะตู้\n"
        "💬 พิมพ์คำถามทั่วไป → AI ตอบจากข้อมูลในตู้คุณ\n\n"
        "🌐 เปิดเว็บ: " + APP_BASE_URL.rstrip("/") + "/app"
    )
    return [
        BotMessage(
            text=text,
            quick_reply=[
                {"label": "📊 ดูสถานะ", "text": "ฉันมีกี่ไฟล์"},
                {"label": "🔍 ค้นหา", "text": "หาไฟล์"},
                {"label": "🌐 เปิดเว็บ", "text": "เปิดเว็บ"},
            ],
        )
    ]


async def _handle_search(pdb_user_id: str, query: str) -> list[BotMessage]:
    """Vector search → Flex carousel of top results."""
    from . import vector_search

    try:
        raw_results = vector_search.hybrid_search(
            query=query, n_results=10, user_id=pdb_user_id, alpha=0.6
        )
    except Exception as e:
        logger.exception("vector_search failed for user=%s: %s", pdb_user_id, e)
        return [BotMessage(text=f"ค้นหาไม่สำเร็จ ลองใหม่: {str(e)[:80]}")]

    if not raw_results:
        return [BotMessage(text=f"🔍 ไม่พบไฟล์ที่เกี่ยวข้องกับ '{query[:50]}' — ลองคำค้นอื่น หรือ upload ไฟล์ใหม่")]

    # Group chunks by file_id (อย่าซ้ำใน carousel)
    seen_files = {}
    for r in raw_results:
        fid = r.get("file_id")
        if not fid or fid in seen_files:
            continue
        seen_files[fid] = r

    # Hydrate filename + filetype from DB
    results: list[dict] = []
    async with AsyncSessionLocal() as db:
        for fid, r in seen_files.items():
            file_q = await db.execute(select(File).where(File.id == fid, File.user_id == pdb_user_id))
            file = file_q.scalar_one_or_none()
            if not file:
                continue
            score = r.get("semantic_score") or r.get("keyword_score") or r.get("relevance", 0)
            snippet = (r.get("text") or "")[:200]
            results.append({
                "file_id": file.id,
                "filename": file.filename,
                "filetype": file.filetype,
                "snippet": snippet,
                "score": float(score) if score else 0,
            })

    if not results:
        return [BotMessage(text=f"🔍 ไม่พบไฟล์ที่เกี่ยวข้องกับ '{query[:50]}'")]

    flex = file_search_carousel(results)
    return [BotMessage(flex=flex)]


async def _handle_url_prompt(pdb_user_id: str, url: str) -> list[BotMessage]:
    """Prompt user if they want to save the URL."""
    # Truncate URL for postback data limit (LINE limit 300 chars for data)
    # action=upload_url&url=...
    # 300 - 18 = 282
    if len(url) > 280:
        return [BotMessage(text=f"พบลิงก์ยาวเกินไป ไม่รองรับการนำเข้าอัตโนมัติ: {url[:100]}...")]

    quick_reply = [
        {"label": "✅ ใช่ เก็บเลย", "data": f"action=upload_url&url={url}", "type": "postback"},
        {"label": "❌ ไม่ใช่ ถามคำถาม", "text": "ถามคำถามจากเนื้อหาในตู้"},
    ]
    return [
        BotMessage(
            text=f"พบลิงก์ — ต้องการให้เก็บเนื้อหาใน PDB ไหม?\n{url}",
            quick_reply=quick_reply
        )
    ]


async def handle_url_upload(pdb_user_id: str, url: str) -> list[BotMessage]:
    """Actually fetch the URL, extract text, and save as file."""
    import httpx
    import hashlib
    from .database import gen_id
    from .extraction import extract_text_from_html
    from .duplicate_detector import compute_content_hash
    from .plan_limits import check_upload_allowed
    from .storage_router import push_raw_file_to_drive_if_byos
    import os
    from .config import UPLOAD_DIR
    
    # Check limits first (approximate size 0)
    async with AsyncSessionLocal() as db:
        user_q = await db.execute(select(User).where(User.id == pdb_user_id))
        user = user_q.scalar_one_or_none()
        if not user:
            return [BotMessage(text="ไม่พบบัญชีของคุณ")]
            
        check = await check_upload_allowed(db, user, 1024, "html")
        if check is not None:
            return [BotMessage(text=check.get("error", "ไม่สามารถนำเข้าได้เนื่องจากเกินขีดจำกัดของ Plan"))]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
            html_content = resp.text
            mime_type = resp.headers.get("Content-Type", "text/html")
    except Exception as e:
        logger.exception("Failed to fetch URL %s: %s", url, e)
        return [BotMessage(text=f"ไม่สามารถดาวน์โหลดข้อมูลจากลิงก์ได้: {str(e)[:80]}")]

    file_id = gen_id()
    user_dir = os.path.join(UPLOAD_DIR, pdb_user_id)
    os.makedirs(user_dir, exist_ok=True)
    filename = f"web_{hashlib.md5(url.encode()).hexdigest()[:8]}.html"
    raw_path = os.path.join(user_dir, f"{file_id}_{filename}")
    
    with open(raw_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    from .extraction import extract_text
    try:
        extracted = extract_text(raw_path, "html")
        if not extracted.strip() or extracted.startswith("["):
            return [BotMessage(text="ไม่พบเนื้อหาข้อความในลิงก์นี้")]
    except Exception as e:
        return [BotMessage(text="เกิดข้อผิดพลาดในการดึงข้อความจากลิงก์")]

    # Prepend URL to the extracted text
    extracted = f"Source URL: {url}\n\n{extracted}"
    content_hash = compute_content_hash(extracted)

    async with AsyncSessionLocal() as db:
        db_file = File(
            id=file_id,
            user_id=pdb_user_id,
            filename=filename,
            filetype="html",
            raw_path=raw_path,
            extracted_text=extracted,
            processing_status="uploaded",
            content_hash=content_hash,
        )
        db.add(db_file)
        await db.commit()

        # BYOS
        try:
            raw_bytes = html_content.encode("utf-8")
            await push_raw_file_to_drive_if_byos(
                pdb_user_id, db, file_id, filename, raw_bytes, "text/html"
            )
        except Exception:
            pass
            
    # Need signed URL
    from .signed_urls import sign_download_token
    token = sign_download_token(file_id, pdb_user_id, ttl_seconds=1800)
    download_url = f"{APP_BASE_URL.rstrip('/')}/d/{token}"
    web_url = f"{APP_BASE_URL.rstrip('/')}/app"

    flex = file_upload_confirmation_card(
        file_id=file_id,
        filename=url,
        filetype="url",
        text_length=len(extracted),
        cluster_title=None,
        download_url=download_url,
        web_url=web_url,
    )
    return [BotMessage(flex=flex)]


async def _handle_get_file(pdb_user_id: str, filename_hint: str) -> list[BotMessage]:
    """Find file by filename (LIKE) → reply Flex card with signed download URL."""
    from .signed_urls import sign_download_token

    if not filename_hint:
        return [BotMessage(text="กรุณาระบุชื่อไฟล์")]

    async with AsyncSessionLocal() as db:
        # LIKE match — case-insensitive
        result = await db.execute(
            select(File).where(
                File.user_id == pdb_user_id,
                File.filename.ilike(f"%{filename_hint}%"),
            ).limit(5)
        )
        files = result.scalars().all()

    if not files:
        return [BotMessage(text=f"📁 ไม่พบไฟล์ที่ชื่อมี '{filename_hint}' — ลอง 'ค้นหา {filename_hint}' เพื่อดูเนื้อหาแทน")]

    if len(files) > 1:
        # Multi-match → carousel of candidates
        results = [
            {
                "file_id": f.id,
                "filename": f.filename,
                "filetype": f.filetype,
                "snippet": f"คลิกเพื่อขอ download link",
            }
            for f in files
        ]
        return [
            BotMessage(text=f"พบ {len(files)} ไฟล์ที่ตรงกัน — เลือกไฟล์ที่ต้องการ:"),
            BotMessage(flex=file_search_carousel(results)),
        ]

    # Single match — return Flex card + signed URL
    file = files[0]
    token = sign_download_token(file.id, pdb_user_id, ttl_seconds=1800)
    download_url = f"{APP_BASE_URL.rstrip('/')}/d/{token}"
    web_url = f"{APP_BASE_URL.rstrip('/')}/app"

    flex = file_upload_confirmation_card(
        file_id=file.id,
        filename=file.filename,
        filetype=file.filetype,
        text_length=len(file.extracted_text or ""),
        cluster_title=None,
        download_url=download_url,
        web_url=web_url,
    )
    return [BotMessage(flex=flex)]


_MARKDOWN_BOLD = re.compile(r"\*\*([^*]+?)\*\*")
_MARKDOWN_ITALIC_STAR = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")
_MARKDOWN_ITALIC_UND = re.compile(r"(?<!_)_([^_\n]+?)_(?!_)")
_MARKDOWN_CODE_BLOCK = re.compile(r"```[a-zA-Z]*\n?([\s\S]*?)```")
_MARKDOWN_INLINE_CODE = re.compile(r"`([^`\n]+?)`")
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+", flags=re.MULTILINE)
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_MARKDOWN_BULLET = re.compile(r"^\s*[-*]\s+", flags=re.MULTILINE)


def strip_markdown(text: str) -> str:
    """Remove common markdown so LINE shows plain readable text.

    LINE Messaging API ไม่ render markdown — ปล่อยตรงๆ จะเห็น **bold** / *em* ดิบๆ
    """
    if not text:
        return text
    text = _MARKDOWN_CODE_BLOCK.sub(r"\1", text)
    text = _MARKDOWN_INLINE_CODE.sub(r"\1", text)
    text = _MARKDOWN_BOLD.sub(r"\1", text)
    text = _MARKDOWN_ITALIC_STAR.sub(r"\1", text)
    text = _MARKDOWN_ITALIC_UND.sub(r"\1", text)
    text = _MARKDOWN_LINK.sub(r"\1 (\2)", text)
    text = _MARKDOWN_HEADING.sub("", text)
    text = _MARKDOWN_BULLET.sub("• ", text)
    return text.strip()


_FILETYPE_ICON = {
    "pdf": "📄", "docx": "📄", "doc": "📄", "txt": "📝", "md": "📝",
    "csv": "📊", "xlsx": "📊", "xls": "📊",
    "pptx": "📑", "ppt": "📑",
    "png": "🖼", "jpg": "🖼", "jpeg": "🖼", "webp": "🖼",
    "html": "🌐", "json": "🧾", "rtf": "📝",
}


def _file_icon(filetype: str) -> str:
    return _FILETYPE_ICON.get((filetype or "").lower(), "📁")


async def _handle_chat(pdb_user_id: str, question: str) -> list[BotMessage]:
    """RAG chat — call retriever.chat_with_retrieval (same engine as web app).

    Output format (plain text, no markdown):
      <answer>

      📁 อ้างอิงจาก N ไฟล์:
      • <icon> <filename>
        <one-liner หรือ snippet>
      • ...
    """
    from .retriever import chat_with_retrieval

    async with AsyncSessionLocal() as db:
        try:
            result = await chat_with_retrieval(db, pdb_user_id, question)
        except Exception as e:
            logger.exception("chat_with_retrieval failed: %s", e)
            return [BotMessage(text="ตอบไม่สำเร็จ — ลองใหม่อีกครั้ง")]

    answer = strip_markdown((result.get("answer") or "").strip())
    if not answer:
        return [BotMessage(text="ผมยังไม่มีข้อมูลพอที่จะตอบ ลองอัปโหลดไฟล์ที่เกี่ยวข้องก่อน")]

    files_used = result.get("files_used") or []

    # Hydrate filename + insight.one_liner / summary for each cited file
    file_blocks: list[str] = []
    by_id: dict = {}
    if files_used:
        file_ids = [f.get("id") for f in files_used if f.get("id")]
        async with AsyncSessionLocal() as db:
            from sqlalchemy.orm import selectinload
            rows = (await db.execute(
                select(File)
                .where(File.id.in_(file_ids), File.user_id == pdb_user_id)
                .options(selectinload(File.insight), selectinload(File.summary))
            )).scalars().all()
            by_id = {row.id: row for row in rows}

        for f in files_used:
            row = by_id.get(f.get("id"))
            if not row:
                continue
            icon = _file_icon(row.filetype)
            # Detail: prefer insight.why_important > summary.summary_text > excerpt
            detail = ""
            if row.insight and (row.insight.why_important or "").strip():
                detail = row.insight.why_important
            elif row.summary and (row.summary.summary_text or "").strip():
                detail = row.summary.summary_text
            elif row.extracted_text:
                detail = row.extracted_text
            detail = strip_markdown(detail or "").replace("\n", " ").strip()
            if len(detail) > 140:
                detail = detail[:137] + "..."

            block = f"• {icon} {row.filename}"
            if detail:
                block += f"\n  {detail}"
            file_blocks.append(block)

    # Compose final text
    parts = [answer]
    if file_blocks:
        parts.append("")
        parts.append(f"📁 อ้างอิงจาก {len(file_blocks)} ไฟล์:")
        parts.extend(file_blocks)

    final_text = "\n".join(parts)

    # Truncate to LINE max (5000 chars; leave headroom)
    if len(final_text) > 4500:
        final_text = final_text[:4500] + "...\n[ข้อความถูกตัด — เปิดเว็บเพื่อดูเต็ม]"

    quick_reply = []
    # Add up to 2 file shortcuts as Quick Reply chips
    for f in files_used[:2]:
        row = by_id.get(f.get("id"))
        if row:
            short = (row.filename or "")[:18]
            if short:
                quick_reply.append({"label": f"📄 {short}", "text": f"ขอไฟล์ {row.filename}"})
    quick_reply.append({"label": "🌐 เปิดเว็บ", "text": "เปิดเว็บ"})

    return [BotMessage(text=final_text, quick_reply=quick_reply)]
