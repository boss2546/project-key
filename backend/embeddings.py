"""Embedding service for v11.0.0 Hybrid Clustering pipeline.

หน้าที่:
- คำนวณ vector embedding ของไฟล์ (text) ด้วย Gemini text-embedding API
- Cache embedding ใน File.embedding_vector (BLOB ใน SQLite)
- Cache invalidation ด้วย File.content_hash (เปลี่ยน text → re-embed)
- Batch API calls สำหรับ efficiency + rate-limit safety

ใช้โดย:
- backend/clustering.py — hybrid clustering ขั้น Cluster
- scripts/migrate_to_v11.py — one-time bulk embed migration
- (อนาคต) chat search semantic — ตอนนี้ยังใช้ TF-IDF vector_search.py

Plan reference: .agent-memory/plans/organize-refactor-v11.md (Step 0.2)

ทำไมแยก service จาก vector_search.py:
- vector_search.py = TF-IDF (keyword-based, lightweight) สำหรับ chat search
- embeddings.py = neural embeddings (semantic, heavier) สำหรับ clustering + entity dedup
- TWO INDEX ดีกว่า one heavy index — separation of concerns
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import numpy as np

# v11.0.0-fix (ฟ้า review LOW finding): consolidate constants — import จาก config
# เลิก duplicate EMBEDDING_MODEL/BATCH_SIZE ใน 2 ไฟล์
from .config import EMBEDDING_MODEL, EMBEDDING_BATCH_SIZE

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════
# Config local (เฉพาะของ embeddings — ไม่ใช้นอกโมดูล)
# ═══════════════════════════════════════════════════════════════

# Sleep ระหว่าง batch — local-only เพราะใช้แค่ใน embed_texts_batch loop.
# free tier Gemini: 1500 RPM = 25 req/sec. batch=50 + sleep 250ms → 4 req/sec, safe.
EMBEDDING_BATCH_SLEEP_SEC: float = float(os.getenv("EMBEDDING_BATCH_SLEEP_SEC", "0.25"))

# Max text length per embedding (Gemini limit ~30K tokens; 1 token ~ 4 chars → 120K chars max)
# ใช้ค่า conservative 80K chars เพื่อ headroom + reduce cost
# Local-only — ไม่ expose ใน config (พฤติกรรมเฉพาะของ embeddings module)
EMBEDDING_MAX_TEXT_CHARS: int = int(os.getenv("EMBEDDING_MAX_TEXT_CHARS", "80000"))


# ═══════════════════════════════════════════════════════════════
# Gemini SDK lazy init (graceful degrade ถ้าไม่มี API key หรือ SDK)
# ═══════════════════════════════════════════════════════════════
_HAS_GEMINI: bool = False
_genai_client = None
_init_attempted: bool = False


def _init_genai() -> None:
    """Lazy-init Gemini client. Idempotent (run-once per process).

    ทำไม lazy: ai_ingest.py โหลด google-genai ตอน import → ถ้า embeddings.py
    โหลดอีกครั้งจะซ้ำซ้อน. Better: รอจนคน call จริง.
    """
    global _HAS_GEMINI, _genai_client, _init_attempted
    if _init_attempted:
        return
    _init_attempted = True

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        logger.warning(
            "embeddings.py: GOOGLE_API_KEY not set — embedding service disabled. "
            "Hybrid clustering will fall back to legacy LLM-cluster."
        )
        return

    try:
        from google import genai
        _genai_client = genai.Client(api_key=api_key)
        _HAS_GEMINI = True
        logger.info(f"embeddings.py: Gemini API enabled (model={EMBEDDING_MODEL})")
    except ImportError:
        logger.warning(
            "embeddings.py: google-genai SDK not installed. "
            "Run: pip install google-genai>=0.3.0"
        )


def is_available() -> bool:
    """True ถ้า GOOGLE_API_KEY set + google-genai SDK installed."""
    _init_genai()
    return _HAS_GEMINI


# ═══════════════════════════════════════════════════════════════
# Vector serialization (numpy float32 ↔ bytes)
# ═══════════════════════════════════════════════════════════════
def encode_vector(arr: np.ndarray) -> bytes:
    """Serialize numpy float32 array → bytes สำหรับเก็บใน DB BLOB.

    เหตุผลที่ float32 (ไม่ float64): vector mostly L2-normalized [-1, 1].
    Float32 precision พอแน่นอน + ขนาดครึ่งหนึ่ง (768 × 4 = 3KB/file vs 6KB).
    """
    if arr.dtype != np.float32:
        arr = arr.astype(np.float32)
    return arr.tobytes()


def decode_vector(b: bytes) -> np.ndarray:
    """Deserialize bytes → numpy float32 array (read จาก DB BLOB)."""
    return np.frombuffer(b, dtype=np.float32)


# ═══════════════════════════════════════════════════════════════
# Single text embedding (low-level)
# ═══════════════════════════════════════════════════════════════
async def embed_text(text: str) -> Optional[np.ndarray]:
    """Embed single text. Returns None ถ้า service ไม่พร้อม.

    Raises: Exception จาก Gemini API (network, quota, etc.)
    Caller รับผิดชอบ retry + fallback.
    """
    _init_genai()
    if not _HAS_GEMINI or _genai_client is None:
        return None

    # Truncate ถ้ายาวเกิน — log warning เพื่อให้ดูได้
    if len(text) > EMBEDDING_MAX_TEXT_CHARS:
        logger.warning(
            f"embed_text: text {len(text)} chars > limit {EMBEDDING_MAX_TEXT_CHARS}, "
            f"truncating (may lose tail content)"
        )
        text = text[:EMBEDDING_MAX_TEXT_CHARS]

    if not text.strip():
        # Empty text → return zero vector (rare edge case, downstream handles)
        logger.debug("embed_text: empty text, returning None")
        return None

    # Gemini SDK เป็น sync → wrap with asyncio.to_thread()
    def _call():
        result = _genai_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text,
        )
        # SDK returns object with .embeddings = [Embedding(values=[...])]
        return result.embeddings[0].values

    values = await asyncio.to_thread(_call)
    return np.array(values, dtype=np.float32)


# ═══════════════════════════════════════════════════════════════
# Batch embedding (high-level — primary entry for clustering)
# ═══════════════════════════════════════════════════════════════
async def embed_texts_batch(texts: list[str]) -> list[Optional[np.ndarray]]:
    """Batch embed many texts ในครั้งเดียว.

    Returns: list[np.ndarray | None] ตามลำดับ input (None ถ้า text ว่าง/error)

    Rate-limit safety: sleep `EMBEDDING_BATCH_SLEEP_SEC` ระหว่าง sub-batch.

    Raises: Exception ถ้า API ล่ม (caller รับผิดชอบ retry).
    """
    _init_genai()
    if not _HAS_GEMINI or _genai_client is None:
        return [None] * len(texts)

    if not texts:
        return []

    # Group เป็น sub-batches
    results: list[Optional[np.ndarray]] = []
    n_batches = (len(texts) + EMBEDDING_BATCH_SIZE - 1) // EMBEDDING_BATCH_SIZE

    for batch_idx in range(n_batches):
        start = batch_idx * EMBEDDING_BATCH_SIZE
        end = min(start + EMBEDDING_BATCH_SIZE, len(texts))
        batch = texts[start:end]

        # Truncate each text + handle empty
        # v11.0.0-fix (ฟ้า review LOW finding): ลบ empty_indices ที่ไม่ได้ใช้ออก
        prepared = []
        for t in batch:
            if not t.strip():
                prepared.append("")  # placeholder, จะถูก replace ด้วย None ตอน map back
                continue
            if len(t) > EMBEDDING_MAX_TEXT_CHARS:
                t = t[:EMBEDDING_MAX_TEXT_CHARS]
            prepared.append(t)

        # Call Gemini batch
        # Note: SDK accepts list[str] for contents (batch mode)
        if any(t.strip() for t in prepared):
            def _call():
                result = _genai_client.models.embed_content(
                    model=EMBEDDING_MODEL,
                    contents=[p for p in prepared if p.strip()],
                )
                return [emb.values for emb in result.embeddings]

            try:
                api_values_list = await asyncio.to_thread(_call)
            except Exception as e:
                logger.error(f"embed_texts_batch: batch {batch_idx+1}/{n_batches} failed: {e}")
                raise  # caller decides retry strategy

            # Map กลับเข้า positions ของ batch (skip empty positions)
            api_idx = 0
            for i, p in enumerate(prepared):
                if not p.strip():
                    results.append(None)
                else:
                    results.append(np.array(api_values_list[api_idx], dtype=np.float32))
                    api_idx += 1
        else:
            # ทั้ง batch ว่าง — skip API call
            results.extend([None] * len(batch))

        logger.info(
            f"embed_texts_batch: {batch_idx+1}/{n_batches} done "
            f"(items={len(batch)}, non-empty={len([p for p in prepared if p.strip()])})"
        )

        # Rate-limit safety ระหว่าง sub-batch
        if batch_idx < n_batches - 1:
            await asyncio.sleep(EMBEDDING_BATCH_SLEEP_SEC)

    return results


# ═══════════════════════════════════════════════════════════════
# File-level embedding with cache (primary entry for clustering)
# ═══════════════════════════════════════════════════════════════
async def embed_files(files: list) -> dict[str, np.ndarray]:
    """Embed multiple File objects with content_hash-based cache.

    Cache strategy:
    - HIT: file.embedding_vector มี + file.embedding_hash == file.content_hash
           + file.embedding_model == EMBEDDING_MODEL → decode from BLOB
    - MISS: เรียก API + update file fields in-memory (caller commit เอง)

    Args:
        files: list of File objects (จาก SQLAlchemy session, attached)

    Returns:
        {file_id: np.ndarray} — เฉพาะ files ที่ embed สำเร็จ.
        Files ที่ extracted_text ว่าง / error → ไม่อยู่ใน result dict.

    Side effects (in-memory only — caller responsible to commit):
        file.embedding_vector = bytes
        file.embedding_model = EMBEDDING_MODEL
        file.embedding_hash = file.content_hash (or sha256 ถ้า content_hash ว่าง)
    """
    _init_genai()
    if not files:
        return {}

    result: dict[str, np.ndarray] = {}
    to_embed: list = []  # files ที่ cache miss
    to_embed_texts: list[str] = []

    # ─── Cache check ────────────────────────────────────────────
    cache_hits = 0
    for f in files:
        text = (f.extracted_text or "").strip()
        if not text:
            logger.debug(f"embed_files: skip {f.id} (empty extracted_text)")
            continue

        # Content hash สำหรับ cache key — ใช้ content_hash ที่ duplicate_detector ตั้งไว้.
        # ถ้า content_hash ว่าง (legacy file) → compute sha256 ของ text ที่นี่
        cache_key = getattr(f, "content_hash", None) or _sha256_text(text)

        # Cache hit?
        embedding_vector = getattr(f, "embedding_vector", None)
        embedding_hash = getattr(f, "embedding_hash", "") or ""
        embedding_model = getattr(f, "embedding_model", "") or ""

        if (
            embedding_vector
            and embedding_hash == cache_key
            and embedding_model == EMBEDDING_MODEL
        ):
            result[f.id] = decode_vector(embedding_vector)
            cache_hits += 1
            continue

        # Cache miss
        to_embed.append((f, cache_key))
        to_embed_texts.append(text)

    if not to_embed:
        logger.info(f"embed_files: cache HIT {cache_hits}/{len(files)} (all cached)")
        return result

    # ─── Fetch fresh embeddings ─────────────────────────────────
    if not _HAS_GEMINI:
        logger.warning(
            f"embed_files: {len(to_embed)} files need embedding but Gemini unavailable. "
            "Returning cached results only."
        )
        return result

    logger.info(
        f"embed_files: cache HIT {cache_hits}/{len(files)}, "
        f"fetching {len(to_embed)} fresh"
    )

    vectors = await embed_texts_batch(to_embed_texts)

    # ─── Write back (in-memory only — caller commits) ───────────
    for (f, cache_key), vec in zip(to_embed, vectors):
        if vec is None:
            logger.warning(f"embed_files: {f.id} embed returned None (skipped)")
            continue
        f.embedding_vector = encode_vector(vec)
        f.embedding_model = EMBEDDING_MODEL
        f.embedding_hash = cache_key
        result[f.id] = vec

    logger.info(f"embed_files: complete ({len(result)}/{len(files)} have embeddings)")
    return result


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════
def _sha256_text(text: str) -> str:
    """SHA-256 hex ของ text. Used เป็น cache key fallback ถ้าไม่มี content_hash."""
    import hashlib
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


# ═══════════════════════════════════════════════════════════════
# Test/diagnostic helpers (สำหรับ scripts/ และ manual verify)
# ═══════════════════════════════════════════════════════════════
async def smoke_test() -> dict:
    """Run smoke test ของ embedding service.

    Returns dict กับ:
        - available: bool
        - model: str
        - sample_dim: int (จริง ๆ ของ embedding output)
        - sample_norm: float (L2 norm — Gemini default returns normalized vectors)
    """
    info = {"available": is_available(), "model": EMBEDDING_MODEL}
    if not info["available"]:
        info["error"] = "Gemini not available (GOOGLE_API_KEY or SDK missing)"
        return info

    try:
        vec = await embed_text("Hello, this is a test sentence for embedding.")
        if vec is None:
            info["error"] = "embed_text returned None"
            return info
        info["sample_dim"] = int(vec.shape[0])
        info["sample_norm"] = float(np.linalg.norm(vec))
        info["sample_dtype"] = str(vec.dtype)
    except Exception as e:
        info["error"] = f"{type(e).__name__}: {e}"

    return info
