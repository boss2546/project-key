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


async def _handle_chat(pdb_user_id: str, question: str) -> list[BotMessage]:
    """RAG chat — call retriever.chat_with_retrieval."""
    from .retriever import chat_with_retrieval

    async with AsyncSessionLocal() as db:
        try:
            result = await chat_with_retrieval(db, pdb_user_id, question)
        except Exception as e:
            logger.exception("chat_with_retrieval failed: %s", e)
            return [BotMessage(text=f"ตอบไม่สำเร็จ — ลองใหม่อีกครั้ง")]

    answer = result.get("answer", "").strip()
    if not answer:
        return [BotMessage(text="ผมยังไม่มีข้อมูลพอที่จะตอบ ลองอัปโหลดไฟล์ที่เกี่ยวข้องก่อน")]

    # Truncate to LINE max (5000 chars)
    if len(answer) > 4500:
        answer = answer[:4500] + "...\n[ตัด — เปิดเว็บเพื่อดูเต็ม]"

    sources = result.get("sources", []) or []
    quick_reply = []
    if sources:
        # Show 1-2 source filenames as quick reply chips
        for s in sources[:2]:
            fname = (s.get("filename") or "")[:20]
            if fname:
                quick_reply.append({"label": f"📄 {fname}", "text": f"ขอไฟล์ {fname}"})
    quick_reply.append({"label": "🌐 เปิดเว็บ", "text": "เปิดเว็บ"})

    return [BotMessage(text=answer, quick_reply=quick_reply)]
