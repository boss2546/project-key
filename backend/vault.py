"""Raw File Vault helpers (v9.1.0).

Files ที่ ext ไม่อยู่ใน ALL_FILE_TYPES → save raw + classify เป็น "vault_only"
ไม่ extract เนื้อหา แต่สร้าง searchable_text จาก filename + ext เพื่อให้:
- AI chat ค้นเจอว่ามีไฟล์ชื่ออะไรบ้างใน vault (Q5 user decision)
- AI เดาได้ว่าน่าจะเป็นอะไรจาก filename tokens
- vector_search index จัดการได้ผ่าน pipeline เดิม (TF-IDF)

Why no LLM call:
- ค่าใช้จ่าย $0 (filename tokens เพียงพอสำหรับ semantic match)
- Upload เร็ว (no async API call)
- Deterministic — same filename = same searchable_text
- User ตัดสินใจ: "AI รู้แค่ว่ามีไฟล์ชื่ออะไรบ้าง + เดาจากชื่อ+นามสกุล"

Format ของ searchable_text:
    "[Vault file] meeting-notes-q4 (extension: zip) — meeting notes q4 zip"
                  ↑ basename     ↑ ext         ↑ tokenized keywords

ใช้ใน:
- backend/main.py upload endpoint (เก็บลง files.extracted_text สำหรับ vault row)
- backend/promote (ตอน promote → ลบ vault summary, แทนด้วย real extract)
"""
from __future__ import annotations

import os
import re
from typing import Optional

# Separators ทั่วไปใน filename (- _ . space)
_SEP_RE = re.compile(r"[-_.\s]+")
# CamelCase split: insert space ระหว่าง lowercase→uppercase boundary
_CAMEL_RE = re.compile(r"(?<=[a-z])(?=[A-Z])")

# Tokens ที่ skip (ไม่มีความหมาย — กัน noise ใน vector search)
# ⚠️ อย่ารวม extension names (doc/pdf/etc.) — extension เก็บ semantic value!
_STOPWORDS = {
    "a", "an", "the", "of", "and", "or", "for", "to", "in", "on",
    "at", "by", "with", "from", "is", "it",
    # Common file naming noise (version/state markers, ไม่ใช่ extension)
    "copy", "final", "v1", "v2", "v3", "v4", "v5",
    "draft", "new", "old", "temp", "tmp", "untitled",
}


def tokenize_filename(filename: str) -> list[str]:
    """แตก filename เป็น tokens ที่มีความหมาย (skip stopwords + duplicates).

    Examples:
        "meeting-notes-2024-Q4.zip" → ["meeting", "notes", "2024", "q4", "zip"]
        "MyDesignPortfolio.psd"     → ["my", "design", "portfolio", "psd"]
        "IMG_20260507_142233.heic"  → ["img", "20260507", "142233", "heic"]
    """
    if not filename:
        return []
    # Step 1: Split CamelCase ก่อน (ต้องทำตอน case ยัง intact)
    #   "MyDesignPortfolio" → "My Design Portfolio"
    spaced = _CAMEL_RE.sub(" ", filename)
    # Step 2: Lowercase + split on separators (- _ . space)
    parts = _SEP_RE.split(spaced.lower())
    seen: set[str] = set()
    tokens = []
    for p in parts:
        p = p.strip()
        if not p or p in _STOPWORDS or p in seen:
            continue
        # Skip pure-numeric tokens shorter than 4 chars (เลขเศษ ไม่มีความหมาย)
        if p.isdigit() and len(p) < 4:
            continue
        seen.add(p)
        tokens.append(p)
    return tokens


def build_vault_searchable_text(filename: str, ext: str) -> str:
    """สร้าง searchable_text สำหรับ vault file.

    Used as files.extracted_text — index ผ่าน vector_search (TF-IDF)
    จะถูก match เมื่อ AI chat ค้นด้วย topic ที่ตรงกับชื่อไฟล์

    Args:
        filename: original filename (with extension), เช่น "meeting-notes.zip"
        ext: lowercase extension without dot, เช่น "zip"

    Returns:
        Multi-line text ที่ optimized สำหรับ TF-IDF match — รวมถึง:
        - Header marker บอกชัดว่าเป็น vault
        - Original filename (intact, ตาม user pattern เดิม)
        - Tokenized keywords (สำหรับ TF-IDF semantic match)
        - Extension hint (สำหรับ ext-based query)

    Example:
        >>> build_vault_searchable_text("meeting-notes-Q4.zip", "zip")
        '[Vault file] meeting-notes-Q4.zip (extension: zip)
         Filename keywords: meeting notes q4 zip'
    """
    safe_filename = os.path.basename(filename or "untitled")
    safe_ext = (ext or "unknown").lstrip(".").lower()
    tokens = tokenize_filename(safe_filename)
    keywords = " ".join(tokens) if tokens else safe_filename

    # Multi-line format:
    # - Line 1: Marker + original filename (user grep-able)
    # - Line 2: Tokenized keywords (TF-IDF rich match)
    # - กระชับ — vault file ไม่ควรครอบคลุม chat context มาก
    return (
        f"[Vault file] {safe_filename} (extension: {safe_ext})\n"
        f"Filename keywords: {keywords}"
    )


def is_vault_extracted_text(text: Optional[str]) -> bool:
    """ตรวจว่า text เป็น vault searchable_text หรือไม่.

    Used by:
    - frontend serialize (อย่าให้ snippet preview แสดง "[Vault file]" marker)
    - chat retriever (อาจ format prompt บอก AI ว่าเป็น vault file)
    """
    if not text:
        return False
    return text.startswith("[Vault file]")
