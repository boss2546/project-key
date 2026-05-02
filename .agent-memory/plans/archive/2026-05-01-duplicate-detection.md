# Plan: Duplicate Detection on Upload (MVP)

**Author:** แดง (Daeng)
**Date:** 2026-05-01
**Status:** draft (รอ user approve)
**Estimated effort:** เขียว ~3-4 ชม. + ฟ้า ~1-2 ชม.
**Target version:** v7.1.0

---

## 🎯 Goal

ตอน user upload ไฟล์ ถ้าเนื้อหาเหมือน/คล้ายกับไฟล์ที่มีอยู่แล้วในบัญชีของ user (≥ 80% similar)
→ แสดง popup เตือน + ให้ user เลือกได้ว่าจะ "ข้ามที่ซ้ำ" หรือ "เก็บทั้งหมด"

**ผู้ใช้:**
- คนที่อัปไฟล์เวอร์ชันใหม่ของ doc เดิม โดยไม่รู้ว่าตัวเองมีของเก่าอยู่
- คนที่เผลอ drag-drop ไฟล์ซ้ำในการอัปครั้งเดียวกัน
- คนที่ไม่อยากให้ library รก/ซ้ำ

**ทำเสร็จแล้วได้อะไร:**
1. Library ของ user สะอาดขึ้น — ลด noise ใน search/chat/graph
2. ลด token cost ตอน organize/chat (ไฟล์น้อยลง = context สั้นลง)
3. UX ที่โปร่งใส — user เห็นว่าระบบมี "อะไรอยู่แล้วบ้าง" ก่อนตัดสินใจ

---

## 📚 Context

### Foundation ที่มีอยู่ (reuse)
- [`backend/vector_search.py:251-300`](../../backend/vector_search.py#L251-L300) — `hybrid_search()` TF-IDF + keyword (per-user isolated)
- [`backend/database.py:47-81`](../../backend/database.py#L47-L81) — `File` model (มี `extracted_text`, `processing_status`, related summary/insight)
- [`backend/main.py:239-335`](../../backend/main.py#L239-L335) — `POST /api/upload` (จุดที่ต้อง modify)
- [`backend/storage_router.py`](../../backend/storage_router.py) — best-effort BYOS push (ใช้ pattern เดียวกัน)

### Decisions ที่ user lock
- **Threshold:** ≥ 80% similarity → popup
- **Algorithm:** SHA-256 (exact) + TF-IDF cosine (semantic) — **ไม่เรียก LLM**
- **Cross-format:** เปรียบที่ extracted_text (PDF↔DOCX content เดียวกัน detect ได้)
- **Scope:** Upload-time only (ไม่ scan library เก่า — defer)
- **Actions:** 2 ปุ่ม: "ข้ามที่ซ้ำ" + "เก็บทั้งหมด" (ไม่มี Replace)
- **Diff display:** % + matched topics (ไม่มี side-by-side text diff)

### MVP Scope (Phase 1)
- ✅ Detect ตอน upload (sync, in same request)
- ✅ Cross-format (เทียบ extracted_text)
- ✅ Both managed + BYOS modes (โครงสร้างเดียวกัน — เทียบ DB ไม่ใช่ Drive)
- ✅ **Intra-batch EXACT detection** (SHA-256 ตรงกัน — ผ่าน SQL query บน content_hash column)
- ⚠️ **Intra-batch SEMANTIC detection — NOT supported ใน MVP** (vector_search index ใหม่ยังไม่อยู่จนกว่าจะ organize → ไฟล์ paraphrase ใน batch เดียวกันจะ miss; user จะเจอใน upload ครั้งถัดไปหลัง organize) — เป็น trade-off เพื่อไม่กระทบ chat context (ดู [Risk #9](#9-intra-batch-semantic-miss--accepted-trade-off))
- ❌ LLM-based deep diff (defer)
- ❌ Side-by-side text diff (defer)
- ❌ Knowledge graph `duplicate_of` edge (defer)
- ❌ MCP `find_duplicates` tool (defer)
- ❌ Library scan endpoint (`POST /api/files/scan-duplicates`) (defer)
- ❌ Pending-review session table (ไม่มี state นี้ — return ทันทีใน upload response)
- ❌ Replace action (ลบของเก่า + ใช้ของใหม่) (defer — ซับซ้อน เพราะต้อง preserve cluster_maps + tags + insights)

---

## 📁 Files to Create / Modify

### Backend
- [ ] [`backend/database.py`](../../backend/database.py) (modify) — เพิ่ม column `content_hash` ใน `File` model + migration ใน `init_db()`
- [ ] [`backend/duplicate_detector.py`](../../backend/duplicate_detector.py) (**create**) — module ใหม่ — hash + similarity + main detection function
- [ ] [`backend/storage_router.py`](../../backend/storage_router.py) (modify) — เพิ่ม `delete_drive_file_if_byos()` public helper (ตาม pattern `push_*_to_drive_if_byos`)
- [ ] [`backend/vector_search.py`](../../backend/vector_search.py) (modify) — เพิ่ม `remove_file()` helper (สำหรับ skip endpoint clean index ถ้า file เคย organize)
- [ ] [`backend/main.py`](../../backend/main.py) (modify):
  - แก้ `POST /api/upload` — เพิ่ม `content_hash` + duplicate check (sync, after commit) + return `duplicates_found`
  - เพิ่ม `POST /api/files/skip-duplicates` endpoint

### Frontend
- [ ] [`legacy-frontend/index.html`](../../legacy-frontend/index.html) (modify) — เพิ่ม modal HTML (hidden by default)
- [ ] [`legacy-frontend/app.js`](../../legacy-frontend/app.js) (modify):
  - แก้ upload handler — รับ `duplicates_found` + เปิด modal
  - เพิ่ม functions: `showDuplicateModal()`, `resolveDuplicates()`
  - เพิ่ม i18n keys (TH+EN)
- [ ] [`legacy-frontend/styles.css`](../../legacy-frontend/styles.css) (modify) — style modal + similarity bar

### Tests (สำหรับฟ้า)
- [ ] [`scripts/duplicate_detection_smoke.py`](../../scripts/duplicate_detection_smoke.py) (**create**) — in-process smoke tests (เหมือน byos_*_smoke.py pattern)
- [ ] (optional) Playwright UI test สำหรับ modal interaction

### Memory updates
- [ ] [`.agent-memory/contracts/api-spec.md`](../contracts/api-spec.md) — document `POST /api/files/skip-duplicates` + modify `/api/upload` response
- [ ] [`.agent-memory/contracts/data-models.md`](../contracts/data-models.md) — เพิ่ม `files.content_hash`
- [ ] [`.agent-memory/project/decisions.md`](../project/decisions.md) — เพิ่ม `DUP-001` (algorithm choice rationale)

---

## 📡 API Changes

### A) Modify `POST /api/upload`

**Request:** เหมือนเดิม (multipart files) — เพิ่ม **optional** query param:
- `detect_duplicates` (bool, default `true`) — ถ้า `false` จะ skip duplicate check (สำหรับ programmatic upload)

**Response 200:** เพิ่ม field `duplicates_found`

```json
{
  "uploaded": [
    {"id": "abc123", "filename": "thesis_v3.pdf", "filetype": "pdf", "uploaded_at": "...", "processing_status": "uploaded", "text_length": 12345}
  ],
  "count": 1,
  "skipped": [],
  "duplicates_found": [
    {
      "new_file_id": "abc123",
      "new_filename": "thesis_v3.pdf",
      "match_file_id": "old456",
      "match_filename": "thesis_v2.pdf",
      "similarity": 0.87,
      "match_kind": "semantic",
      "matched_topics": ["AI", "deep learning", "results"]
    }
  ]
}
```

**Behavior:**
- ทุกไฟล์ใหม่จะถูก save ลง DB ทันที (status = `"uploaded"`)
- ทุกไฟล์ใหม่จะถูก index เข้า `vector_search` ทันที (เพื่อให้ batch ถัดไปใน loop เดียวกัน detect intra-batch ได้)
- หลัง commit → loop เช็ค duplicate ของแต่ละไฟล์
- Return ทุกไฟล์ที่ uploaded + array `duplicates_found` (อาจว่างถ้าไม่เจออะไร)
- **ไม่ block upload** — ไฟล์อยู่ใน DB แล้ว user เลือกเอง

**Errors:** เหมือนเดิม (no new error codes for upload)

---

### B) NEW: `POST /api/files/skip-duplicates`

**Auth:** Required (JWT)

**Request:**
```json
{
  "file_ids": ["abc123", "def789"]
}
```

**Response 200:**
```json
{
  "status": "ok",
  "deleted": ["abc123", "def789"],
  "count": 2,
  "skipped": []
}
```

**Behavior:**
- Validate ว่าทุก `file_id` เป็นของ user นี้จริง (กัน leak ข้าม users)
- ถ้า file มี `raw_path` ที่ exists → `os.remove()` (free disk)
- BYOS-aware: ถ้า file มี `drive_file_id` → call `drive_storage.DriveClient.delete_file()` ผ่าน storage_router (best-effort, log ถ้า fail แต่ลบ DB ต่อ)
- ลบ row จาก `files` table → cascade ลบ `file_insights`, `file_summaries`, `file_cluster_map` (existing FK behavior)
- ลบจาก `vector_search` index (เรียก helper ใหม่ `vector_search.remove_file()`)

**Errors:**
- 400 `EMPTY_FILE_IDS` — array ว่าง
- 401 `UNAUTHORIZED` — no token
- (file ที่ไม่มี / ไม่ใช่ของ user → silently skip — ใส่ใน `skipped` array)

---

## 💾 Data Model Changes

### Add column to `files` table

```python
class File(Base):
    # ... existing fields ...
    content_hash = Column(String(64), nullable=True, index=True)
    # SHA-256 hex of normalized extracted_text (lowercase + collapsed whitespace)
    # NULL ถ้า extraction ล้มเหลว / text สั้นเกินไป (< 50 chars)
```

### Migration in `init_db()` ([`backend/database.py:467+`](../../backend/database.py#L467))

วางหลัง v7.0 BYOS migration:

```python
# v7.1 Migration — Duplicate detection content hash
cursor = await db.execute("PRAGMA table_info(files)")
file_cols_v71 = [row[1] for row in await cursor.fetchall()]
if "content_hash" not in file_cols_v71:
    await db.execute("ALTER TABLE files ADD COLUMN content_hash TEXT")
    migrated = True
    print("  → Added: files.content_hash (duplicate detection)")

try:
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_content_hash "
        "ON files(content_hash)"
    )
except Exception as e:
    print(f"  ⚠️ files.content_hash index creation warning: {e}")
```

**Backfill consideration:**
- ไฟล์เก่าที่ไม่มี `content_hash` → first duplicate check จะ skip (no exact match possible)
- Optional one-shot backfill script: `scripts/backfill_content_hash.py` (run manually after deploy)
- **MVP: ไม่ต้องทำ backfill** — ไฟล์เก่ายังเทียบ semantic ได้ผ่าน TF-IDF

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

### Step 1: Schema migration (~10 นาที)

1. แก้ [`backend/database.py`](../../backend/database.py):
   - เพิ่ม column `content_hash = Column(String(64), nullable=True, index=True)` ใน class `File` (วางใต้ `storage_source`)
   - ใน `init_db()` เพิ่ม migration block หลัง v7.0 BYOS section (ตามตัวอย่างข้างบน)
2. รัน server local → ดู log ว่า migration ผ่าน + index created
3. `sqlite3 projectkey.db ".schema files"` → ตรวจว่ามี `content_hash` column

### Step 2: Backend module — `backend/duplicate_detector.py` (~45 นาที)

สร้าง module ใหม่:

```python
"""Duplicate detection — find similar files in user's library at upload time.

Algorithm (MVP — no LLM):
1. SHA-256 of normalized extracted_text → exact match (similarity = 1.0)
2. TF-IDF cosine via vector_search.hybrid_search() → semantic similarity
3. Threshold: 0.80 (configurable per call)

Reused: backend/vector_search.py — hybrid_search() with per-user isolation
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

# Threshold: similarity ≥ นี้ถือว่า duplicate (semantic)
SIMILARITY_THRESHOLD = 0.80

# Min text length เพื่อ trust similarity score (TF-IDF อ่อนกับ text สั้น)
MIN_TEXT_LENGTH_FOR_DETECTION = 50


class DuplicateMatch(TypedDict):
    new_file_id: str
    new_filename: str
    match_file_id: str
    match_filename: str
    similarity: float
    match_kind: str  # "exact" | "semantic"
    matched_topics: list[str]


def normalize_text(text: str) -> str:
    """Lowercase + collapse whitespace + strip → stable hash input.

    Strategy: ใช้ stable normalization ที่เปลี่ยน formatting ไม่กระทบ hash
    (กัน "extra space แต่ content เหมือน" หลุด exact match)
    """
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_content_hash(text: str) -> Optional[str]:
    """SHA-256 ของ normalized text. None ถ้า text สั้นเกิน / extraction error."""
    if not text or len(text) < MIN_TEXT_LENGTH_FOR_DETECTION:
        return None
    # Skip extraction error markers (e.g., "[OCR error: ...]")
    if text.startswith("["):
        return None
    normalized = normalize_text(text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _extract_topics(file: File) -> list[str]:
    """Get key_topics จาก file's summary. Empty list ถ้ายังไม่ organized."""
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
    """Find best match (exact or semantic) for a new file.

    Returns:
        DuplicateMatch dict ถ้าเจอ similarity ≥ threshold
        None ถ้าไม่เจอ / text สั้นเกิน / extraction error
    """
    # Skip ถ้า text สั้นเกิน — TF-IDF อ่อน + hash ไม่มีความหมาย
    if not new_text or len(new_text) < MIN_TEXT_LENGTH_FOR_DETECTION:
        return None
    if new_text.startswith("["):
        return None

    # 1. Exact match via SHA-256 (รวดเร็วที่สุด)
    new_hash = compute_content_hash(new_text)
    if new_hash:
        result = await db.execute(
            select(File).where(
                File.user_id == user_id,
                File.content_hash == new_hash,
                File.id != new_file_id,
            ).options(selectinload(File.summary))
        )
        exact_match = result.scalar_one_or_none()
        if exact_match:
            logger.info(
                "DUP: exact match found for new_file=%s → existing=%s",
                new_file_id, exact_match.id,
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

    # 2. Semantic match via TF-IDF (reuse existing index)
    if not vector_search.is_available():
        return None

    # ใช้ first 2000 chars เป็น query — เพียงพอสำหรับ similarity scoring
    # + ไม่ทำให้ vector_search ช้าเพราะ query ยาวเกิน
    hits = vector_search.hybrid_search(
        query=new_text[:2000],
        n_results=5,
        user_id=user_id,
    )

    # Find top non-self hit ที่ similarity ≥ threshold
    for hit in hits:
        if hit["file_id"] == new_file_id:
            continue
        if hit["relevance"] < threshold:
            continue

        # Look up File row
        result = await db.execute(
            select(File).where(File.id == hit["file_id"])
            .options(selectinload(File.summary))
        )
        match = result.scalar_one_or_none()
        if not match:
            continue

        logger.info(
            "DUP: semantic match for new_file=%s → existing=%s (%.2f)",
            new_file_id, match.id, hit["relevance"],
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
    """Detect duplicates for a batch of newly-uploaded files.

    Caller ต้อง:
    1. Save File rows ลง DB ก่อน (เพื่อ exact-match query เห็น)
    2. Index เข้า vector_search ก่อน (เพื่อ intra-batch detection)
    3. Commit DB ก่อนเรียก function นี้

    Returns:
        List of duplicate matches (อาจว่าง ถ้าไม่มี dup)
    """
    matches: list[DuplicateMatch] = []
    for file_id in new_file_ids:
        result = await db.execute(select(File).where(File.id == file_id))
        new_file = result.scalar_one_or_none()
        if not new_file:
            continue
        match = await find_duplicate_for_file(
            db, user_id, new_file.id,
            new_file.extracted_text or "",
            new_file.filename,
        )
        if match:
            matches.append(match)
    return matches
```

### Step 2.5: เพิ่ม `storage_router.delete_drive_file_if_byos()` (~10 นาที)

แก้ [`backend/storage_router.py`](../../backend/storage_router.py) — เพิ่มท้ายไฟล์ (ตาม pattern public `*_to_drive_if_byos`):

```python
async def delete_drive_file_if_byos(
    user_id: str,
    db: AsyncSession,
    drive_file_id: str,
) -> bool:
    """Best-effort: trash a file in user's Drive ถ้า user เป็น byos + connected.

    ใช้ใน skip-duplicates endpoint — เมื่อ user ลบไฟล์ที่อัปขึ้น Drive ไปแล้ว.
    Drive trash = recoverable 30 days (per drive_storage.delete_file behavior).

    Returns:
        True  = trashed สำเร็จ
        False = no-op (managed/not configured/not connected) หรือ Drive failure
    """
    pair = await _get_byos_user_with_connection(user_id, db)
    if not pair:
        return False
    _user, conn = pair
    try:
        client = await _build_drive_client(conn)
        client.delete_file(drive_file_id)
        logger.info("BYOS: trashed Drive file %s for user %s", drive_file_id, user_id)
        return True
    except Exception as e:
        logger.warning(
            "BYOS: delete_drive_file failed for user %s file %s (%s)",
            user_id, drive_file_id, e,
        )
        return False
```

### Step 3: เพิ่ม `vector_search.remove_file()` (~5 นาที)

แก้ [`backend/vector_search.py`](../../backend/vector_search.py) — เพิ่ม helper:

```python
def remove_file(file_id: str, user_id: str = "") -> None:
    """Remove a file from the per-user TF-IDF index. No-op ถ้าไม่อยู่.

    Called when user skips a duplicate file → ลบ index entry ป้องกัน orphan
    """
    if not user_id:
        user_id = "__global__"
    if user_id not in _user_indexes:
        return
    if file_id in _user_indexes[user_id]:
        del _user_indexes[user_id][file_id]
        _user_doc_counts[user_id] = sum(
            len(c) for c in _user_indexes[user_id].values()
        )
        _rebuild_idf(user_id)
        logger.info(f"Removed file {file_id} from search index (user={user_id[:8]}..)")
```

### Step 4: Modify upload endpoint (~30 นาที)

แก้ [`backend/main.py:239-335`](../../backend/main.py#L239-L335) — เพิ่ม import + แก้ function body:

```python
# At top of file, add import
from .duplicate_detector import (
    compute_content_hash,
    detect_duplicates_for_batch,
)
```

แก้ `POST /api/upload`:

```python
@app.post("/api/upload")
async def upload_files(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    detect_duplicates: bool = Query(True),  # NEW — default true
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload one or more files, extract text, save to database.

    v7.1: เพิ่ม duplicate detection — return field `duplicates_found` ใน response.
    User เลือก keep all (no action) หรือ skip duplicates (call /api/files/skip-duplicates)
    """
    uploaded = []
    skipped = []
    pending_drive_pushes: list[tuple[str, str, bytes, str, str]] = []
    new_file_ids: list[str] = []  # NEW — track สำหรับ duplicate check

    # ... existing limit checks (allowed_types, max_bytes, file_limit) ...

    for upload_file in files:
        # ... existing extraction logic ...

        extracted = extract_text(raw_path, ext)

        # NEW: compute content hash
        content_hash = compute_content_hash(extracted)

        db_file = File(
            id=file_id,
            user_id=current_user.id,
            filename=original_name,
            filetype=ext,
            raw_path=raw_path,
            extracted_text=extracted,
            processing_status="uploaded",
            content_hash=content_hash,  # NEW
        )
        db.add(db_file)
        new_file_ids.append(file_id)  # NEW

        # ... existing pending_drive_pushes ...

        uploaded.append({...})

    await db.commit()

    # NEW: Run duplicate detection (sync, in-request)
    # หมายเหตุ: ไม่ index uploaded files เข้า vector_search ทันที (รักษา invariant ของ
    # retriever.py:91 + mcp_tools.py:743 ที่คาดว่า indexed files = "ready" only)
    # → Intra-batch SEMANTIC dup จะ miss (ดู Risk #9) — ใช้ exact match (SHA-256) ครอบคลุม
    #   intra-batch identical files ผ่าน SQL query บน content_hash column
    duplicates_found: list = []
    if detect_duplicates and new_file_ids:
        try:
            duplicates_found = await detect_duplicates_for_batch(
                db, current_user.id, new_file_ids,
            )
        except Exception as e:
            # Non-fatal: log + return ว่าง array. Upload สำเร็จไปแล้ว
            logger.warning(f"Duplicate detection failed: {e}")

    # Existing: BYOS background push
    if pending_drive_pushes:
        background_tasks.add_task(
            _push_uploads_to_drive,
            current_user.id,
            pending_drive_pushes,
        )

    return {
        "uploaded": uploaded,
        "count": len(uploaded),
        "skipped": skipped,
        "duplicates_found": duplicates_found,  # NEW
    }
```

### Step 5: New endpoint `POST /api/files/skip-duplicates` (~20 นาที)

วางใน [`backend/main.py`](../../backend/main.py) ใต้ `delete_file` endpoint:

```python
class SkipDuplicatesRequest(BaseModel):
    file_ids: list[str]


@app.post("/api/files/skip-duplicates")
async def skip_duplicates(
    req: SkipDuplicatesRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """ลบไฟล์ใหม่ที่ user เลือก "ข้ามที่ซ้ำ" หลังเห็น duplicate popup.

    Validate: ทุก file_id ต้องเป็นของ user นี้จริง (กัน cross-user delete)
    BYOS-aware: ถ้า file อยู่บน Drive ด้วย → trigger best-effort delete on Drive
    """
    if not req.file_ids:
        raise HTTPException(status_code=400, detail={
            "error": {"code": "EMPTY_FILE_IDS", "message": "ต้องระบุ file_ids อย่างน้อย 1 ไฟล์"}
        })

    deleted: list[str] = []
    skipped_ids: list[str] = []

    for file_id in req.file_ids:
        result = await db.execute(
            select(File).where(File.id == file_id, File.user_id == current_user.id)
        )
        f = result.scalar_one_or_none()
        if not f:
            skipped_ids.append(file_id)
            continue

        # Best-effort: ลบ raw file จาก disk
        if f.raw_path and os.path.exists(f.raw_path):
            try:
                os.remove(f.raw_path)
            except OSError as e:
                logger.warning(f"Failed to remove raw_path {f.raw_path}: {e}")

        # Best-effort: BYOS — ลบจาก Drive ถ้ามี drive_file_id
        if f.drive_file_id:
            try:
                from .storage_router import delete_drive_file_if_byos
                await delete_drive_file_if_byos(
                    current_user.id, db, f.drive_file_id
                )
            except Exception as e:
                logger.warning(f"BYOS Drive delete failed for {file_id}: {e}")

        # ลบจาก vector_search index
        try:
            from . import vector_search as _vs
            _vs.remove_file(f.id, user_id=current_user.id)
        except Exception as e:
            logger.warning(f"vector_search remove failed for {file_id}: {e}")

        # ลบ DB row (cascade ลบ insight/summary/cluster_map ผ่าน FK)
        await db.delete(f)
        deleted.append(file_id)

    await db.commit()

    logger.info(
        f"User {current_user.id} skipped {len(deleted)} duplicate files"
    )

    return {
        "status": "ok",
        "deleted": deleted,
        "count": len(deleted),
        "skipped": skipped_ids,
    }
```

### Step 6: Frontend HTML — เพิ่ม modal (~15 นาที)

แก้ [`legacy-frontend/index.html`](../../legacy-frontend/index.html) — วาง modal element ใต้ `<div id="app">` (ใกล้ๆ modal อื่น เช่น `pack-modal-overlay`):

```html
<!-- ─── DUPLICATE DETECTION MODAL (v7.1) ─── -->
<div class="dup-modal-overlay hidden" id="dup-modal-overlay">
  <div class="dup-modal">
    <div class="dup-modal-header">
      <h2 id="dup-modal-title" data-i18n="dup.title">⚠ พบไฟล์คล้ายกัน</h2>
    </div>
    <div class="dup-modal-body">
      <p class="dup-modal-subtitle" data-i18n="dup.subtitle">
        ไฟล์ที่อัปโหลดใหม่บางไฟล์มีเนื้อหาคล้ายกับไฟล์ที่มีอยู่แล้ว
      </p>
      <div class="dup-list" id="dup-list">
        <!-- Generated by JS -->
      </div>
    </div>
    <div class="dup-modal-footer">
      <button class="btn btn-outline" id="dup-skip-btn" data-i18n="dup.skip">
        ✗ ข้ามที่ซ้ำ — ใช้ของเก่า
      </button>
      <button class="btn btn-primary" id="dup-keep-btn" data-i18n="dup.keep">
        ✓ เก็บทั้งหมด
      </button>
    </div>
  </div>
</div>
```

### Step 7: Frontend JS — handler logic (~40 นาที)

แก้ [`legacy-frontend/app.js`](../../legacy-frontend/app.js):

**(a) State สำหรับ modal:**
```javascript
let _pendingDuplicates = []; // duplicates_found จาก response ล่าสุด
```

**(b) แก้ upload handler** — หาฟังก์ชันที่จัดการ upload response (search หา `'/api/upload'` หรือ `uploaded.length`):
```javascript
// หลัง response มา
if (data.duplicates_found && data.duplicates_found.length > 0) {
  _pendingDuplicates = data.duplicates_found;
  showDuplicateModal();
}
loadFiles(); // refresh list ตามปกติ
```

**(c) ฟังก์ชันใหม่:**
```javascript
function showDuplicateModal() {
  const modal = document.getElementById('dup-modal-overlay');
  if (!modal) return;
  const list = document.getElementById('dup-list');
  if (!list) return;

  const isTH = getLang() === 'th';
  list.innerHTML = _pendingDuplicates.map(d => {
    const pct = Math.round(d.similarity * 100);
    const kindLabel = d.match_kind === 'exact'
      ? (isTH ? '(ตรงเป๊ะ)' : '(exact)')
      : '';
    const topicsLabel = isTH ? 'ตรงกัน' : 'matched';
    const topics = (d.matched_topics && d.matched_topics.length > 0)
      ? `<div class="dup-topics">${topicsLabel}: ${d.matched_topics.join(', ')}</div>`
      : '';
    const similarLabel = isTH ? 'คล้าย' : 'similar to';
    return `
      <div class="dup-row">
        <div class="dup-new">📄 <strong>${escapeHtml(d.new_filename)}</strong> ${isTH ? '(ใหม่)' : '(new)'}</div>
        <div class="dup-old">
          <div class="dup-arrow">↪ ${similarLabel} <strong>${escapeHtml(d.match_filename)}</strong></div>
          <div class="dup-bar">
            <div class="dup-bar-fill" style="width:${pct}%"></div>
            <div class="dup-bar-label">${pct}% ${kindLabel}</div>
          </div>
          ${topics}
        </div>
      </div>
    `;
  }).join('');

  modal.classList.remove('hidden');
}

function hideDuplicateModal() {
  const modal = document.getElementById('dup-modal-overlay');
  if (modal) modal.classList.add('hidden');
  _pendingDuplicates = [];
}

async function resolveDuplicates(action) {
  if (action === 'skip') {
    const fileIds = _pendingDuplicates.map(d => d.new_file_id);
    if (fileIds.length === 0) {
      hideDuplicateModal();
      return;
    }
    try {
      const res = await authFetch('/api/files/skip-duplicates', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({file_ids: fileIds}),
      });
      if (res.ok) {
        const data = await res.json();
        const isTH = getLang() === 'th';
        showToast(
          isTH ? `ข้าม ${data.count} ไฟล์ที่ซ้ำแล้ว` : `Skipped ${data.count} duplicate files`,
          'success'
        );
        loadFiles();
        loadStats();
      } else {
        showToast(getLang() === 'th' ? 'ไม่สามารถลบไฟล์ได้' : 'Failed to skip duplicates', 'error');
      }
    } catch {
      showToast(getLang() === 'th' ? 'เกิดข้อผิดพลาด' : 'Error', 'error');
    }
  } else {
    // keep — ไม่ต้องทำอะไร ไฟล์อยู่แล้ว
    showToast(
      getLang() === 'th' ? 'เก็บไฟล์ทั้งหมดเรียบร้อย' : 'All files kept',
      'success'
    );
  }
  hideDuplicateModal();
}

function escapeHtml(s) {
  const div = document.createElement('div');
  div.textContent = s ?? '';
  return div.innerHTML;
}
```

**(d) Wire ปุ่ม** ใน `initApp()` (หรือ DOMContentLoaded handler):
```javascript
document.getElementById('dup-skip-btn')?.addEventListener('click', () => resolveDuplicates('skip'));
document.getElementById('dup-keep-btn')?.addEventListener('click', () => resolveDuplicates('keep'));
```

**(e) i18n keys** — เพิ่มใน I18N dict ทั้ง `th` และ `en`:
```javascript
// th
'dup.title': '⚠ พบไฟล์คล้ายกัน',
'dup.subtitle': 'ไฟล์ที่อัปโหลดใหม่บางไฟล์มีเนื้อหาคล้ายกับไฟล์ที่มีอยู่แล้ว',
'dup.skip': '✗ ข้ามที่ซ้ำ — ใช้ของเก่า',
'dup.keep': '✓ เก็บทั้งหมด',
'dup.matchedSemantic': 'คล้าย',
'dup.matchedExact': 'ตรงเป๊ะ',
'dup.matchedTopics': 'ตรงกัน',

// en
'dup.title': '⚠ Similar files detected',
'dup.subtitle': 'Some uploaded files have content similar to existing files',
'dup.skip': '✗ Skip duplicates',
'dup.keep': '✓ Keep all',
'dup.matchedSemantic': 'similar to',
'dup.matchedExact': 'exact',
'dup.matchedTopics': 'matched',
```

### Step 8: CSS — modal styling (~20 นาที)

แก้ [`legacy-frontend/styles.css`](../../legacy-frontend/styles.css) — เพิ่มท้ายไฟล์:

```css
/* ─── Duplicate Detection Modal (v7.1) ─── */
.dup-modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.6);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}
.dup-modal-overlay.hidden { display: none; }

.dup-modal {
  background: #191a1b;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  width: 90%; max-width: 600px;
  max-height: 80vh;
  display: flex; flex-direction: column;
  box-shadow: 0 20px 60px rgba(0,0,0,0.5);
}
.dup-modal-header {
  padding: 20px 24px;
  border-bottom: 1px solid rgba(255,255,255,0.05);
}
.dup-modal-header h2 {
  margin: 0; color: #f7f8f8;
  font-size: 18px; font-weight: 600;
}
.dup-modal-body {
  padding: 16px 24px;
  overflow-y: auto; flex: 1;
}
.dup-modal-subtitle {
  color: #8a8f98; font-size: 13px; margin-bottom: 16px;
}
.dup-list { display: flex; flex-direction: column; gap: 12px; }

.dup-row {
  background: rgba(255,255,255,0.025);
  border: 1px solid rgba(255,255,255,0.05);
  border-radius: 8px;
  padding: 14px;
}
.dup-new {
  color: #f7f8f8; font-size: 14px; margin-bottom: 8px;
}
.dup-arrow {
  color: #d0d6e0; font-size: 13px; margin-bottom: 6px;
}
.dup-bar {
  position: relative;
  background: rgba(255,255,255,0.05);
  border-radius: 4px;
  height: 18px;
  overflow: hidden;
  margin-bottom: 6px;
}
.dup-bar-fill {
  background: linear-gradient(90deg, #f59e0b, #ef4444);
  height: 100%;
  transition: width 0.3s;
}
.dup-bar-label {
  position: absolute;
  top: 0; left: 50%;
  transform: translateX(-50%);
  font-size: 11px; font-weight: 600;
  color: #f7f8f8;
  line-height: 18px;
  text-shadow: 0 0 3px rgba(0,0,0,0.5);
}
.dup-topics {
  color: #8a8f98; font-size: 12px; margin-top: 4px;
  font-style: italic;
}
.dup-modal-footer {
  padding: 16px 24px;
  border-top: 1px solid rgba(255,255,255,0.05);
  display: flex; gap: 12px; justify-content: flex-end;
}
@media (max-width: 600px) {
  .dup-modal { width: 95%; max-height: 90vh; }
  .dup-modal-footer { flex-direction: column-reverse; }
  .dup-modal-footer .btn { width: 100%; }
}
```

### Step 9: Self-test (~30 นาที)

1. รัน server local
2. Login บัญชีทดสอบ
3. **Test 1 (exact match):**
   - Upload `test.md` ที่มีเนื้อ "Lorem ipsum dolor sit amet..." ≥ 50 chars
   - Upload ไฟล์เดียวกันชื่อ `test-copy.md`
   - คาดหวัง: popup แสดง 100% (exact)
4. **Test 2 (semantic):**
   - Upload `notes_v1.md` (เนื้อหาสั้นๆ เกี่ยวกับ AI 1 หน้า)
   - Edit เนื้อหา ~10% (เปลี่ยน wording บางส่วน)
   - Upload เป็น `notes_v2.md`
   - คาดหวัง: popup แสดง similarity ~85-95% (semantic)
5. **Test 3 (intra-batch):**
   - Drag-drop 3 ไฟล์ที่เนื้อหาเดียวกันใน batch เดียว
   - คาดหวัง: popup แสดง matches ระหว่างกันเอง
6. **Test 4 (no match):**
   - Upload ไฟล์เนื้อหาแตกต่างจากที่มี
   - คาดหวัง: ไม่ popup
7. **Test 5 (skip action):**
   - กด "ข้ามที่ซ้ำ"
   - ตรวจ: ไฟล์ใหม่หายจาก list, raw_path ถูกลบ, vector_search index ถูก clear
8. **Test 6 (keep action):**
   - กด "เก็บทั้งหมด"
   - ตรวจ: ไฟล์ใหม่ยังอยู่, ไม่มีอะไรเปลี่ยน
9. **Test 7 (BYOS):**
   - Switch user เป็น byos mode + connected Drive
   - Upload ไฟล์ซ้ำ + กด skip
   - ตรวจ: drive_file_id หาย + ไฟล์บน Drive ถูก trash

### Step 10: Update memory (~10 นาที)

1. [`contracts/api-spec.md`](../contracts/api-spec.md) — document `POST /api/files/skip-duplicates` + แก้ `/api/upload` response
2. [`contracts/data-models.md`](../contracts/data-models.md) — เพิ่ม `files.content_hash` ใน column list + migration history v7.1
3. [`project/decisions.md`](../project/decisions.md) — เพิ่ม:
   ```
   ## DUP-001: Hash + TF-IDF (no LLM) for duplicate detection
   **Why:** Free + fast (≤100ms), reuses existing vector_search index, ดีพอสำหรับ ≥80% similar
   **Implication:** ไม่เจอ paraphrase หนัก (similarity 60-80%) — เป็น MVP trade-off, deep diff via LLM = Phase 2
   ```
4. [`current/pipeline-state.md`](../current/pipeline-state.md) — เพิ่ม v7.1 feature ใน Up Next queue (state = `plan_pending_approval`)

### Step 11: Commit + handoff to ฟ้า (~10 นาที)

Commit message format (ดู [`contracts/conventions.md`](../contracts/conventions.md)):
```
feat(dedupe): duplicate detection on upload — v7.1.0

เพิ่ม duplicate detection ตอน upload:
- SHA-256 exact match (covers intra-batch + cross-existing)
- TF-IDF semantic similarity via existing vector_search index (cross-existing only)
- Threshold 0.80, modal popup + 2 actions (skip / keep all)
- Both managed + BYOS modes (storage_router.delete_drive_file_if_byos)
- ไม่เรียก LLM (cost = 0)
- Intra-batch SEMANTIC miss = accepted MVP trade-off (see plan Risk #9)

Files:
- backend/duplicate_detector.py (new, ~150 lines)
- backend/database.py: + content_hash column + migration
- backend/storage_router.py: + delete_drive_file_if_byos()
- backend/vector_search.py: + remove_file()
- backend/main.py: modify /api/upload + add /api/files/skip-duplicates
- legacy-frontend/{index.html,app.js,styles.css}: + dup modal

Tests: scripts/duplicate_detection_smoke.py (TBD by ฟ้า)

Refs: plans/duplicate-detection.md
Author-Agent: เขียว (Khiao)
```

Update [`inbox/for-ฟ้า.md`](../communication/inbox/for-ฟ้า.md) section 🔴 New:
```markdown
### MSG-NNN 🟡 MEDIUM — Review v7.1 duplicate detection
**From:** เขียว
**Date:** YYYY-MM-DD HH:MM
**Status:** 🔴 New

Code commit: <hash>
Plan: plans/duplicate-detection.md
Self-test: 7/7 scenarios pass

ฝาก review:
- Algorithm correctness (TF-IDF + hash combined)
- Edge cases ใน detect_duplicates_for_batch
- BYOS Drive delete flow ใน skip-duplicates endpoint
- Modal UX
```

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Happy Path
1. **Exact match (single file):** Upload `a.md` → upload identical content as `b.md` → popup shows `b → a, 100% (exact)` → click "Keep" → both files remain
2. **Semantic match (single file):** Upload `note_v1.md` (paragraph about AI) → upload `note_v2.md` (~85% same words, slightly rephrased) → popup shows ~85-90% (semantic) → click "Skip" → `note_v2.md` deleted
3. **No duplicate:** Upload completely different content → no popup
4. **Intra-batch:** drag-drop 3 identical files in one upload → popup shows 2 matches (file2→file1, file3→file1)
5. **Mixed batch:** 5 files — 2 duplicates of existing + 1 intra-batch dup + 2 fresh → popup shows 3 matches, 2 fresh upload silently

### Validation Errors
- `POST /api/files/skip-duplicates` with empty `file_ids` → 400 EMPTY_FILE_IDS
- `POST /api/files/skip-duplicates` with `file_ids` from other user → silently skipped (in `skipped` array)

### Auth Errors
- Upload without JWT → 401
- Skip-duplicates without JWT → 401
- Expired token → 401

### Edge Cases
- **Empty extracted_text** (extraction failed) → no duplicate check, upload normally
- **Very short text** (< 50 chars, e.g., "hi") → no duplicate check, upload normally
- **OCR error marker** (text starts with `[OCR error: ...]`) → no duplicate check
- **Two NULL hash files compared** (both have NULL content_hash) → no exact match (NULL ≠ NULL in SQL), semantic via TF-IDF only
- **Content_hash collision unlikely** but if happens → still semantic check confirms
- **File with summary but no key_topics** → matched_topics = []
- **File without summary at all** (not yet organized) → matched_topics = []
- **`detect_duplicates=false` query param** → upload returns `duplicates_found=[]` regardless
- **Skip on locked file** (existing match is `is_locked=true`) → can still skip new file (action affects new only)

### BYOS Scenarios
- Upload duplicate in BYOS mode → popup works (compares DB extracted_text, not Drive)
- Skip duplicate in BYOS mode → backend deletes from DB + best-effort Drive trash via `drive_storage.delete_file`
- Skip when Drive disconnected mid-flow → DB delete succeeds, Drive delete logged warning, no error to user

### Performance / Stress
- Upload 1 file vs 100 existing → detection ≤ 500ms
- Upload 10-file batch vs 100 existing → detection ≤ 5s (acceptable inline)
- Upload 50-file batch → may take 30-60s (acceptable for MVP, document as known limit)

### Regression
- Files endpoints (`GET /api/files`, `GET /api/files/{id}/content`, etc.) — no changes
- Organize flow — re-indexing in `organizer.py` should be idempotent (overwrite existing index entries)
- Existing files without `content_hash` (pre-v7.1) → semantic similarity still works

---

## ✅ Done Criteria

- [ ] Schema migration ผ่าน (column + index created, idempotent re-run safe)
- [ ] `backend/duplicate_detector.py` — exact + semantic detection ทำงาน
- [ ] `POST /api/upload` return `duplicates_found` field (อาจว่างถ้าไม่เจอ)
- [ ] `POST /api/files/skip-duplicates` ลบไฟล์ + raw + index + Drive (BYOS)
- [ ] Frontend modal แสดง similarity bar + topics
- [ ] 2 ปุ่มทำงาน: Skip → call API + refresh, Keep → close + toast
- [ ] i18n TH+EN ครบทุก label
- [ ] CSS responsive (mobile โหลดได้)
- [ ] Self-test 7/7 scenarios pass
- [ ] No regression — `pytest scripts/byos_*_smoke.py` + `rebrand_smoke_v6.1.0.py` ผ่านทั้งหมด
- [ ] Memory updates: api-spec.md + data-models.md + decisions.md + pipeline-state.md
- [ ] Commit message format ครบ (Author-Agent: เขียว (Khiao))
- [ ] Bump APP_VERSION → "7.1.0" ใน `backend/config.py`

---

## ⚠️ Risks / Open Questions

### Known limitations (ของ MVP — accept ได้)
1. **TF-IDF อ่อนกับ paraphrase หนัก** — ถ้า user rewrite ทั้งเอกสารด้วย wording ต่างกันมาก (similarity จริง ~70%) จะ miss → ปกติของ free algorithm. Phase 2 LLM diff จะแก้ได้
2. **Vector_search ทำงานบน chunks 500 chars** — ไฟล์สั้น (< 500 chars) จะ index เป็น 1 chunk เท่านั้น → similarity score อาจ noisy
3. **Detection ใช้ first 2000 chars** — ไฟล์ยาวที่เนื้อหาต่างกันใน 2000 chars แรก แต่เหมือนกันท้ายๆ จะ miss
4. **Cross-format edge case:** PDF ที่ extraction มี "--- Page 1 ---" markers จะ hash ต่างจาก DOCX content เดียวกัน → exact match miss แต่ semantic ยังเจอ
5. **ไฟล์ที่ extraction ล้มเหลว** (text = `"[Extraction error: ...]"`) — ไม่เช็ค → safe default

### Performance risks
6. **Batch ใหญ่ (>50 files)** — sync detection อาจ timeout (Fly.io HTTP timeout = 60s default) → user เห็น 502
   - **Mitigation:** ใส่ guard ใน upload loop — ถ้า batch > 30 files → skip duplicate detection + return field `dedup_skipped: true` → frontend แสดง toast "Batch ใหญ่เกิน — ข้าม duplicate check ครั้งนี้"
   - Phase 2: async background job

### 9. Intra-batch SEMANTIC miss — accepted trade-off
**Issue:** ถ้า user drop 2 ไฟล์ใน batch เดียวกันที่ paraphrase กัน (different SHA-256, ~85% similar text) → MVP detect ไม่เจอ
**Why:** ไฟล์ใหม่ยังไม่ถูก index เข้า `vector_search` (เพื่อรักษา invariant ที่ retriever.py:91 + mcp_tools.py:743 คาดว่า indexed = "ready" only)
**Coverage ที่เหลือ:**
- ✅ Intra-batch EXACT (SHA-256 ตรง) — ใช้ SQL query บน `content_hash` column (ไม่พึ่ง vector_search)
- ✅ Cross-existing EXACT — เหมือนข้างบน
- ✅ Cross-existing SEMANTIC — vector_search hits "ready" files
**Mitigation:** ถ้า user organize หลัง upload → ไฟล์ paraphrase ทั้งคู่จะถูก index → upload ครั้งถัดไปจะ detect เจอ
**Phase 2 fix:** inline cosine comparison ระหว่าง batch members (ไม่ต้องผ่าน vector_search index) — เพิ่มความซับซ้อน ~50 บรรทัด
**Why accept:** scenario นี้ rare — user น้อยคนที่จะ drop 2 paraphrased copies ใน batch เดียวกัน. Common case (identical files double-selected) ยังครอบคลุม

### Security risks
7. **User A เห็น filename ของ User B หรือเปล่า?** — ไม่. ทุก query filter `user_id == current_user.id`. vector_search ใช้ per-user index
8. **Race condition:** 2 uploads concurrent — file A และ B identical → ทั้งคู่อาจไม่เห็นกัน (ถ้า index ยังไม่ rebuild) → MVP accept (rare case, manual cleanup ผ่าน scan endpoint Phase 2)

### Open Questions (รอ user/แดง decide ตอน Phase 2)
- **Q-A:** Phase 2 — เพิ่ม "Replace existing" button (ลบของเก่า + ใช้ของใหม่ พร้อม preserve cluster/tags)?
- **Q-B:** Phase 2 — LLM-based deep diff (side-by-side text diff) ตอน user คลิก "ดูตรงไหนเหมือน/ต่าง"?
- **Q-C:** Phase 2 — Library scan endpoint สำหรับหา duplicate ในไฟล์เก่า (รายงานก่อน บอก user list)?
- **Q-D:** เปลี่ยน threshold (80%) เป็น user-configurable ใน profile settings?
- **Q-E:** เพิ่ม MCP tool `find_duplicates(file_id)` สำหรับ AI ช่วย user หา?
- **Q-F:** Knowledge graph — เพิ่ม edge type `duplicate_of` (weight = similarity) → user เห็น cluster ของไฟล์ซ้ำใน graph view?

---

## 📌 Notes for เขียว

### กฎที่ห้ามลืม
1. **เก็บ `content_hash` เป็น lowercase hex** — `hashlib.sha256(...).hexdigest()` คืน lowercase ปกติ (อย่า `.upper()`)
2. **`compute_content_hash` คืน None ได้** — ถ้า text สั้น/empty/error marker → ใส่ NULL ใน DB → SQL exact-match query จะไม่ match (NULL ≠ NULL)
3. **Index file ก่อน duplicate check** — ใน upload loop ต้อง index ทุกไฟล์ใหม่เข้า vector_search ก่อน loop ที่เรียก `find_duplicate_for_file` มิฉะนั้น intra-batch จะ miss
4. **Vector_search.index_file rebuild IDF ทุกครั้ง** — สำหรับ batch ใหญ่อาจช้า → MVP accept, Phase 2 อาจ batch-update IDF
5. **ห้าม raise ใน duplicate detection** — wrap ทุกอย่างใน try/except → upload ต้อง succeed แม้ detection fail
6. **`Author-Agent: เขียว (Khiao)`** ใน commit
7. **ห้าม commit** `.env`, `projectkey.db`

### Gotchas
- **`File.content_hash` nullable** — ห้าม assume non-null ใน query. Index ทำงานกับ NULL OK แต่ exact-match จะไม่ดึง NULL row
- **`vector_search.hybrid_search` filter ด้วย `user_id`** — ห้าม leak cross-user. Default `user_id="__global__"` ถ้า user_id ไม่ส่ง — ตรวจให้แน่ใจส่ง user_id เสมอ
- **`vector_search._user_indexes` is in-memory** — restart server = หายหมด → ต้องรอ startup index rebuild ก่อน detection จะ work หลัง restart. Edge case: user upload ทันทีหลัง deploy → index ยังไม่ rebuild → semantic check return None → ใช้ exact match อย่างเดียว (acceptable degradation)
- **vector_search.hybrid_search ไม่ filter trashed/deleted** — แต่ `remove_file()` clear แล้ว + DB delete cascade → consistent
- **`escapeHtml` ใน frontend** — sanitize filename + topic names กัน XSS
- **i18n key naming** — ใช้ pattern `dup.<key>` ตาม convention เดิม

### Performance tips
- TF-IDF ใช้ first 2000 chars สำหรับ query — เพียงพอ
- Index file ตอน upload จะถูก re-index อีกครั้งใน organizer (idempotent — overwrite)
- ถ้า batch ใหญ่ (>30 files) ใส่ guard skip detection (Phase 2 ทำ async)

### Testing tips
- ใช้ in-process TestClient (เหมือน byos_*_smoke.py) — sandbox block port binding
- Mock vector_search ผ่านการ inject _user_indexes โดยตรง (มี state-based isolation)
- Test BYOS flow ผ่าน `_from_service` injection (เหมือนใน drive_storage tests)

### ขนาด PR ที่คาดไว้
- backend: ~250 lines (duplicate_detector 150 + main.py mods 70 + vector_search 20 + database.py 10)
- frontend: ~200 lines (modal HTML 30 + app.js 100 + styles.css 70)
- tests: ~150 lines (ฟ้าจะเขียน)
- รวม: PR ขนาด **medium** — 1 commit เพียงพอ (feature เดียว)

### Pre-launch checklist (เขียวต้องตรวจก่อนส่งฟ้า)
- [ ] Schema migration ทำงาน (เปิด server fresh + พบ "Added: files.content_hash")
- [ ] Modal เปิด/ปิดได้ ไม่ค้าง
- [ ] Skip ลบไฟล์ครบ (DB + raw + index + Drive ถ้า byos)
- [ ] Keep ไม่ทำอะไร (popup ปิด, files คงเดิม)
- [ ] `pytest scripts/byos_*_smoke.py scripts/rebrand_smoke_v6.1.0.py` — no regression
- [ ] APP_VERSION = "7.1.0" + memory updated
