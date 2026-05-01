"""Duplicate detection — หา similar/identical files ใน library ของ user (v7.1).

**Trigger location (v7.1 user override 2026-05-01):** เรียกจาก `/api/organize-new`
หลัง organize เสร็จ (ไม่ใช่ตอน upload เหมือน round แรก) — เพราะตรงนี้ไฟล์ใหม่
ทุกตัวถูก index เข้า vector_search แล้ว → semantic detection ทำงานเต็ม +
intra-batch SEMANTIC detection ก็ทำได้ (Risk #9 ของ round แรกหายไปแล้ว). ดู
DUP-003 ใน decisions.md สำหรับ rationale.

อัลกอริทึม (MVP — ไม่ใช้ LLM):
1. **Exact match (SHA-256):** hash normalized extracted_text → similarity = 1.0 ผ่าน
   SQL query บน `files.content_hash` column (per-user filter ผ่าน `user_id`).
   Hash ถูกคำนวณ + เก็บตอน upload เพื่อให้ exact match ทำงานได้แม้ user ยังไม่ organize
2. **Semantic match (TF-IDF cosine):** เรียก `vector_search.hybrid_search()` ที่มี
   per-user isolation อยู่แล้ว → similarity ≥ 0.80 ถือว่า duplicate. ตอน organize-time
   ไฟล์ใหม่ทุกตัวอยู่ใน vector_search index แล้ว → intra-batch + cross-existing
   ครอบคลุมทั้งคู่
3. ไม่เรียก LLM — cost = ฿0

Why hash + TF-IDF (ไม่ใช่ LLM):
  - Free + fast (≤ 100ms ต่อไฟล์ ใน batch ~5 ไฟล์)
  - Reuses existing per-user vector index ที่ build ตอน organize อยู่แล้ว
  - ดีพอสำหรับ ≥ 80% similar — paraphrase หนัก (50-80%) จะ miss (Phase 2 = LLM diff)

Reused infrastructure:
  - backend/vector_search.py — hybrid_search() with per-user isolation
  - backend/database.py — File model with content_hash column (v7.1 migration)
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Optional, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import File
from . import vector_search

logger = logging.getLogger(__name__)

# Threshold: similarity ≥ ค่านี้ถือว่า duplicate (ใช้กับ semantic match เท่านั้น —
# exact match ใช้ 1.0 ตามนิยามของ SHA-256 collision)
SIMILARITY_THRESHOLD: float = 0.80

# Minimum text length เพื่อ trust similarity score
# Why 50: TF-IDF อ่อนกับ text สั้น (chunk เดียว, IDF ไม่มีน้ำหนัก) + hash ของ text สั้นๆ
# มัก collide กับ greeting / template snippets ทำให้ false positive
MIN_TEXT_LENGTH_FOR_DETECTION: int = 50

# Maximum chars จาก extracted_text ที่ส่งเข้า vector_search.hybrid_search() เป็น query
# Why 2000: เพียงพอสำหรับ TF-IDF scoring (พอจับ topic distribution) + ไม่ทำ search ช้าเกิน
# Trade-off: ไฟล์ที่เนื้อหาต่างกันใน 2000 chars แรก แต่เหมือนกันท้ายๆ → miss (Risk #3)
MAX_QUERY_CHARS: int = 2000


class DuplicateMatch(TypedDict):
    """Schema ของ duplicate match ใน upload response.

    new_file_id / new_filename: ไฟล์ใหม่ที่เพิ่ง upload
    match_file_id / match_filename: ไฟล์เก่า (หรือไฟล์อื่นใน batch เดียวกัน) ที่คล้ายกัน
    similarity: 0.0-1.0
    match_kind: "exact" (SHA-256 ตรง) | "semantic" (TF-IDF cosine ≥ threshold)
    matched_topics: key topics จาก match_file's summary (ถ้า organized แล้ว) — empty ถ้ายัง
    """
    new_file_id: str
    new_filename: str
    match_file_id: str
    match_filename: str
    similarity: float
    match_kind: str
    matched_topics: list[str]


def normalize_text(text: str) -> str:
    """Lowercase + collapse whitespace + strip → input ที่ stable สำหรับ SHA-256.

    Why normalize: ไฟล์ 2 ไฟล์ที่มี "extra whitespace" / "case ต่างกัน" แต่ content เหมือน
    ควรนับเป็น duplicate exact (ไม่ใช่แค่ semantic) → user expectation
    """
    if not text:
        return ""
    text = text.lower()
    # Collapse whitespace (รวม \n, \t, multiple spaces) เป็น single space
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_content_hash(text: str) -> Optional[str]:
    """SHA-256 hex (lowercase) ของ normalized text.

    คืน None ในกรณีที่ไม่ควร hash:
      - text ว่าง / สั้นเกิน MIN_TEXT_LENGTH_FOR_DETECTION (กัน hash collision ของ snippet)
      - extraction error marker (text ขึ้นต้นด้วย "[" — เช่น "[OCR error: ...]")

    Why None ไม่ใช่ empty string: เก็บ NULL ใน DB → exact-match SQL query จะไม่ match
    (NULL ≠ NULL ใน SQL) → ไฟล์ที่ extraction ล้มเหลว 2 ไฟล์จะไม่ false-match กันเอง
    """
    if not text or len(text) < MIN_TEXT_LENGTH_FOR_DETECTION:
        return None
    # Skip extraction error markers — ไม่ควร hash เพราะไม่ใช่ user content จริง
    if text.startswith("["):
        return None
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_topics(file: File) -> list[str]:
    """ดึง key_topics จาก file.summary — top 5 strings.

    คืน [] ถ้า:
      - File ยังไม่ organize (file.summary = None)
      - Summary ไม่มี key_topics (raw upload)
      - JSON parse fail (corrupted data)

    Why max 5: UI modal มีพื้นที่จำกัด + topics 5 อันแรกพอบอก theme ของไฟล์
    """
    if not file.summary or not file.summary.key_topics:
        return []
    try:
        topics = json.loads(file.summary.key_topics)
        if isinstance(topics, list):
            return [str(t) for t in topics[:5]]
    except (json.JSONDecodeError, TypeError):
        pass
    return []


async def find_duplicate_for_file(
    db: AsyncSession,
    user_id: str,
    new_file_id: str,
    new_text: str,
    new_filename: str,
    threshold: float = SIMILARITY_THRESHOLD,
) -> Optional[DuplicateMatch]:
    """หา best match (exact หรือ semantic) สำหรับ 1 ไฟล์ใหม่.

    Strategy:
      1. ลอง exact match ก่อน (SHA-256 query บน content_hash) — ถ้าเจอ return ทันที
      2. ถ้าไม่เจอ → ลอง semantic ผ่าน vector_search.hybrid_search()
      3. ถ้าทั้งคู่ไม่เจอ → return None

    Args:
        db: async DB session
        user_id: เจ้าของไฟล์ — ใช้ filter exact + semantic (per-user isolation)
        new_file_id: id ของไฟล์ใหม่ใน DB (เพื่อ exclude จาก match — ห้าม self-match)
        new_text: extracted_text ของไฟล์ใหม่
        new_filename: filename สำหรับ display ใน popup
        threshold: similarity ≥ ค่านี้ถือว่า duplicate (default 0.80)

    Returns:
        DuplicateMatch ถ้าเจอ, None ถ้าไม่เจอ / text สั้นเกิน / extraction error
    """
    # Skip ไฟล์ที่ text สั้นเกิน — TF-IDF อ่อน + hash ไม่น่าเชื่อถือ
    if not new_text or len(new_text) < MIN_TEXT_LENGTH_FOR_DETECTION:
        return None
    if new_text.startswith("["):
        return None

    # ── 1. Exact match via SHA-256 ────────────────────────────────────
    # Why hash query ก่อน semantic: O(1) index lookup vs O(n) cosine across chunks
    # → ถ้าเจอ exact ไม่ต้องเสีย CPU compute TF-IDF
    new_hash = compute_content_hash(new_text)
    if new_hash:
        result = await db.execute(
            select(File)
            .where(
                File.user_id == user_id,
                File.content_hash == new_hash,
                File.id != new_file_id,
            )
            .options(selectinload(File.summary))
        )
        exact_match = result.scalars().first()
        if exact_match:
            logger.info(
                "DUP: exact match found for new_file=%s → existing=%s (user=%s..)",
                new_file_id, exact_match.id, user_id[:8],
            )
            return {
                "new_file_id": new_file_id,
                "new_filename": new_filename,
                "match_file_id": exact_match.id,
                "match_filename": exact_match.filename,
                "similarity": 1.0,
                "match_kind": "exact",
                "matched_topics": _extract_topics(exact_match),
            }

    # ── 2. Semantic match via TF-IDF (vector_search) ─────────────────
    # vector_search.is_available() = True เสมอ (pure Python) แต่เผื่ออนาคตเปลี่ยน
    if not vector_search.is_available():
        return None

    # ใช้ first MAX_QUERY_CHARS เป็น query — เพียงพอสำหรับ TF-IDF scoring
    # n_results=5 → ดู top-5 hits ที่อาจเป็น duplicate (file ละ 1 chunk หรือ multi-chunks ก็ได้)
    hits = vector_search.hybrid_search(
        query=new_text[:MAX_QUERY_CHARS],
        n_results=5,
        user_id=user_id,
    )

    # หา top non-self hit ที่ similarity ≥ threshold
    # Note: hybrid_search return chunks ไม่ใช่ files — ไฟล์เดียวอาจมีหลาย chunks
    # → loop หา file_id ที่ relevance สูงสุดที่ไม่ใช่ตัวเอง
    seen_file_ids: set[str] = set()
    for hit in hits:
        hit_file_id = hit["file_id"]
        if hit_file_id == new_file_id:
            continue
        # Dedup chunks ของ file เดียวกัน — เก็บ chunk ที่ relevance สูงสุดเท่านั้น
        # (hits ถูก sort by relevance desc แล้วใน hybrid_search → chunk แรกของแต่ละ file
        # = relevance สูงสุดของไฟล์นั้น)
        if hit_file_id in seen_file_ids:
            continue
        seen_file_ids.add(hit_file_id)

        if hit["relevance"] < threshold:
            continue

        # Lookup File row พร้อม summary (สำหรับ matched_topics)
        result = await db.execute(
            select(File).where(File.id == hit_file_id)
            .options(selectinload(File.summary))
        )
        match = result.scalars().first()
        if not match:
            # vector_search index มีแต่ DB ลบไปแล้ว — orphan index → skip
            continue

        # Cross-user safety: vector_search ถูก isolate per-user แล้ว แต่ double-check
        if match.user_id != user_id:
            logger.warning(
                "DUP: cross-user hit detected (vector_search leak?) — "
                "skipping match=%s user=%s vs requester=%s",
                match.id, match.user_id[:8], user_id[:8],
            )
            continue

        logger.info(
            "DUP: semantic match for new_file=%s → existing=%s (%.2f, user=%s..)",
            new_file_id, match.id, hit["relevance"], user_id[:8],
        )
        return {
            "new_file_id": new_file_id,
            "new_filename": new_filename,
            "match_file_id": match.id,
            "match_filename": match.filename,
            "similarity": round(hit["relevance"], 2),
            "match_kind": "semantic",
            "matched_topics": _extract_topics(match),
        }

    return None


async def detect_duplicates_for_batch(
    db: AsyncSession,
    user_id: str,
    new_file_ids: list[str],
) -> list[DuplicateMatch]:
    """หา duplicates สำหรับ batch ของไฟล์ที่เพิ่ง organize.

    Caller (`/api/organize-new` endpoint) ต้อง:
      1. รัน organize_new_files() จนเสร็จ (commit summaries + index เข้า vector_search)
         → ตรงนี้ทุกไฟล์ใหม่ทั้ง content_hash + vector index พร้อมใช้
      2. ส่ง list of file_ids ที่เพิ่ง organize เข้ามา → function จะหา match ของแต่ละ
         ไฟล์เทียบกับ library ทั้งหมดของ user (รวมไฟล์เก่า + intra-batch กันเอง)

    เพราะเรียกหลัง organize → semantic detection ทำงานเต็ม + intra-batch SEMANTIC
    เจอด้วย (ต่างจาก v7.1 round แรกที่ trigger ตอน upload แล้วต้อง accept Risk #9)

    Args:
        db: async DB session (must have organize complete + committed)
        user_id: เจ้าของ batch
        new_file_ids: list ของ file_id ที่เพิ่ง organize (ลำดับเดิมเสมอ)

    Returns:
        List ของ DuplicateMatch — อาจว่างถ้าไม่มีไฟล์ไหนซ้ำ
    """
    matches: list[DuplicateMatch] = []
    for file_id in new_file_ids:
        result = await db.execute(select(File).where(File.id == file_id))
        new_file = result.scalars().first()
        if not new_file:
            # ไฟล์หายระหว่าง commit + check (race condition / external delete) — skip
            continue
        # Cross-user safety
        if new_file.user_id != user_id:
            logger.warning(
                "DUP: skipping file %s — user mismatch (file=%s vs requester=%s)",
                file_id, new_file.user_id[:8], user_id[:8],
            )
            continue
        match = await find_duplicate_for_file(
            db,
            user_id,
            new_file.id,
            new_file.extracted_text or "",
            new_file.filename,
        )
        if match:
            matches.append(match)
    return matches
