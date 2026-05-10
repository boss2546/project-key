# Plan: Upload Queue + Visible Progress (v9.4.0)

**Author:** แดง (Daeng)
**Date:** 2026-05-10
**Status:** draft (รอ user approve)
**Foundation:** master HEAD `c0ffdc0` (v9.3.4 review_passed)
**Target APP_VERSION:** 9.4.0 (minor — feature เพิ่มใหม่ ไม่ใช่ bug fix)

---

## 🎯 Goal

แยก **"รับไฟล์"** (เร็ว < 200ms) ออกจาก **"อ่านไฟล์"** (ช้า — extract/OCR/AI multimodal) ให้ user เห็นว่า**ตอนนี้ทำอะไรอยู่** ทุกขั้นตอน + ระบบไม่ค้างเมื่ออัปไฟล์เยอะ + ระบบกู้คืนได้เมื่อ server restart

### ผลลัพธ์ที่ user สัมผัสได้
1. **กด upload → response ทันที** (ไม่รอ 30-120s แบบเดิม)
2. **Upload Tray เปิดมาด้านล่าง-ขวา** แสดงไฟล์ทุกอันในคิว + สถานะสด
3. **เห็นข้อความสด** เช่น "อันดับ 3/7 ในคิว" / "กำลัง OCR หน้า 5/12" / "Gemini ถอดเสียง 02:14/05:30"
4. **ช้าได้** แต่ user ไม่งง — รู้ว่าช้าเพราะอะไร, ไฟล์ไหน, ทำได้ที่ไหนแล้ว
5. **Retry ได้** ถ้า fail (ไม่ต้องอัปใหม่)
6. **ทำงานได้แม้ปิด browser** — เปิดมาใหม่ tray โผล่อัตโนมัติถ้ายังมีไฟล์ในคิว
7. **Server restart ก็ไม่หาย** — recovery automatic

---

## 📚 Context

### Pain points ปัจจุบัน (v9.3.4)

อัปโหลดทำทุกอย่างใน request เดียว ([backend/main.py:480-629](../../backend/main.py#L480-L629)):

```
POST /api/upload (sync)
  → save file
  → extract_text() ← OCR/Tesseract หนัก
  → ai_ingest.ingest_via_ai() ← Gemini multimodal สำหรับ audio/video (60-300s)
  → compute_content_hash + classify + strip_surrogates
  → DB commit
  → BackgroundTask push to Drive (BYOS only)
  ← return ผลลัพธ์ (รอจน step ทุกอันเสร็จ)
```

**4 ปัญหาที่ root cause:**
1. **Timeout** — Cloudflare/Fly.io HTTP timeout ~60-120s. PDF OCR หนักหรือ audio ยาว → request พัง
2. **Block ไฟล์อื่นในชุด** — แม้ frontend ทำ parallel pool 3 (1 file/request) แต่ถ้าไฟล์ที่ 3 ใช้ Gemini 5 นาที → 2 ไฟล์ที่เหลือก็รอ slot นั้น
3. **Memory บวม** — ทุกไฟล์อ่านเข้า `contents = await upload_file.read()` พร้อมกัน + OCR pdf2image แปลงทุกหน้าเป็น image ใน RAM → 4GB ก็ peak ได้
4. **Recovery ไม่ได้** — server restart ระหว่าง extract → row ค้าง `processing_status="processing"` ตลอด (orphan)

ที่ user รู้สึกในตอนนี้ ([app.js:1488-1507](../../legacy-frontend/app.js#L1488-L1507)):
- เห็นแค่ "เซิร์ฟเวอร์ประมวลผล X/Y ไฟล์..." + indeterminate spinner
- ไม่รู้ว่ากำลังทำไฟล์ไหน, ทำขั้นไหน, อีกนานแค่ไหน
- ปิด browser = "กลัวว่าจะหาย" (แม้ฝั่ง backend ทำเสร็จ DB คืน)
- ถ้า fail = ต้องอัปใหม่ทั้งไฟล์

### ที่ v10.x พยายามทำแล้วพังแบบไหน
v10.x ใส่ `job_queue.py` + `worker_pool.py` + `circuit_breaker.py` + `watchdog.py` + Pydantic schema + Gemini multimodal pipeline ในขั้นเดียวกัน — รื้อ extraction stack ทั้งหมด ทำให้พังหลาย module พร้อมกัน

**v9.4.0 ต่างจาก v10.x ตรงไหน:**
- ✅ **เก็บ extraction stack เดิมทั้งหมด** (PyPDF2 + Tesseract + python-docx + python-pptx + ai_ingest) — ไม่แตะ
- ✅ **ใช้ DB เป็น queue** (ไม่ใช้ Redis/Celery) — ไม่เพิ่ม infra
- ✅ **In-process worker** (1 ตัว, asyncio.create_task ที่ startup) — ไม่ใช่ Worker pool ซับซ้อน
- ✅ **เพิ่ม column ใน files table** ไม่สร้าง table ใหม่ — backward compat สูง
- ✅ **/api/organize-new + organizer.py + 5-stage pipeline เดิม ไม่แตะ** — แค่เปลี่ยน upload phase
- ✅ **Scope แค่ upload** — คิว AI organize เก็บไว้รอบหน้า

### Design principle: "ง่ายๆ ไม่ซับซ้อน"
- ไม่เพิ่ม table ใหม่ — เพิ่ม column ใน `files`
- ไม่เพิ่ม dependency ใหม่
- ไม่ใช้ WebSocket / SSE — ใช้ HTTP polling 2s (เปิดเฉพาะตอน tray เปิด)
- Worker concurrency = 1 ก่อน (sequential ปลอดภัยที่สุด, ปรับได้ทีหลัง)
- ทุก state change = atomic SQLite UPDATE (no race)

---

## 📁 Files to Create / Modify

### Backend (5 modify + 1 create)

- [ ] **`backend/database.py`** (modify) — เพิ่ม 6 columns ใน `File` model + idempotent migration ใน `init_db()` + startup recovery hook
- [ ] **`backend/main.py`** (modify) — แยก `/api/upload` เป็น "save + queue" + เพิ่ม `/api/upload-status` + `/api/upload/{file_id}/retry` + register worker startup task
- [ ] **`backend/upload_worker.py`** (create) — โมดูลใหม่ ~250 บรรทัด: queue poll loop + extract dispatch + progress reporter + recovery
- [ ] **`backend/extraction.py`** (modify-light) — เพิ่ม optional `progress_callback` parameter ที่ extract paths หนัก (PDF OCR loop หน้าต่อหน้า) เพื่อให้ worker update progress_step ได้
- [ ] **`backend/ai_ingest.py`** (modify-light) — เพิ่ม optional `progress_callback` ที่ Gemini Files API upload + transcribe paths
- [ ] **`backend/config.py`** (modify) — bump `APP_VERSION` 9.3.4 → 9.4.0

### Frontend (3 modify + 0 create)

- [ ] **`legacy-frontend/app.js`** (modify) — เปลี่ยน `uploadFiles()` flow + เพิ่ม `UploadTray` namespace (~250 บรรทัด): polling + render + retry handler + tray persistence on app load
- [ ] **`legacy-frontend/styles.css`** (modify) — เพิ่ม `.upload-tray` + child elements (~120 บรรทัด) ตาม UI Foundation Contract (token-only + atom reuse: `.meter`, `.skeleton`, `.status-pill`)
- [ ] **`legacy-frontend/app.html`** (modify) — เปลี่ยน version label + cache-bust `?v=9.4.0`

### Tests (สำหรับฟ้า — 3 create)

- [ ] **`scripts/upload_queue_smoke.py`** (create) — ~30 cases: queue lifecycle + worker recovery + race conditions + multi-file batching + retry flow
- [ ] **`tests/e2e-ui/v9.4.0-upload-tray.spec.js`** (create) — Playwright UI tests: tray DOM contract + polling cycle + retry button + persistence on reload
- [ ] **`tests/test_upload_progress.py`** (create) — pytest 15 cases: progress_callback wiring + step text formatting + DB write throttling

### Memory (มี/แก้)

- [ ] **`.agent-memory/contracts/data-models.md`** (update) — document `files` table v9.4.0 columns
- [ ] **`.agent-memory/contracts/api-spec.md`** (update — ถ้ามี / create section ถ้าไม่มี) — POST /api/upload (changed) + GET /api/upload-status (new) + POST /api/upload/{id}/retry (new)
- [ ] **`.agent-memory/current/pipeline-state.md`** (update) — state, version, plan
- [ ] **`.agent-memory/current/active-tasks.md`** (update)
- [ ] **`.agent-memory/current/last-session.md`** (update)

---

## 📡 API Changes

### POST /api/upload (BREAKING in shape, but backward-compat semantics)

**Auth:** Required (JWT) — เหมือนเดิม

**Request:** multipart form-data, field `files` (1 file/request เหมือนเดิม) — ไม่เปลี่ยน

**Response 200 (changed — ตอนนี้ extract ยังไม่เสร็จ):**
```json
{
  "uploaded": [
    {
      "id": "abc123def456",
      "filename": "document.pdf",
      "filetype": "pdf",
      "uploaded_at": "2026-05-10T03:14:22.000Z",
      "processing_status": "queued",
      "queue_position": 3,
      "estimated_wait_sec": 45,
      "file_kind": "processed"
    }
  ],
  "count": 1,
  "skipped": []
}
```

**Field changes:**
- ❌ ลบ `text_length` (extract ยังไม่เสร็จตอน return)
- ➕ เพิ่ม `queue_position` (1-based, อันดับในคิวของ user คนนี้)
- ➕ เพิ่ม `estimated_wait_sec` (heuristic: queue_position × 8s default)
- 🔁 `processing_status` = `"queued"` แทน `"uploaded"`

**Skipped reasons (เพิ่ม):**
- ➕ `QUEUE_FULL` — global cap คิว user คนเดียว ≥ 50 ไฟล์ที่ status ∈ {queued, extracting}

**Errors (เพิ่ม):** ไม่เพิ่ม HTTP error code ใหม่ (validation 400/401/413 เหมือนเดิม)

---

### GET /api/upload-status (NEW)

**Auth:** Required (JWT)

**Query:** ไม่มี

**Response 200:**
```json
{
  "active": [
    {
      "id": "abc123",
      "filename": "เอกสารยาว.pdf",
      "filetype": "pdf",
      "processing_status": "extracting",
      "extraction_status": "pending",
      "queue_position": 0,
      "progress_step": "OCR หน้า 5 จาก 12",
      "progress_pct": 42,
      "queued_at": "2026-05-10T03:14:22.000Z",
      "extract_started_at": "2026-05-10T03:14:24.000Z",
      "attempt_count": 0,
      "is_retryable": false
    },
    {
      "id": "xyz789",
      "filename": "voice.m4a",
      "filetype": "m4a",
      "processing_status": "queued",
      "queue_position": 1,
      "progress_step": "รออันดับ 1",
      "progress_pct": 0,
      "queued_at": "2026-05-10T03:14:25.000Z"
    }
  ],
  "failed": [
    {
      "id": "fail001",
      "filename": "broken.pdf",
      "filetype": "pdf",
      "processing_status": "error",
      "extraction_status": "ocr_failed",
      "extract_error": "PDF เข้ารหัส — ปลดล็อกก่อนอัปโหลดใหม่",
      "attempt_count": 1,
      "is_retryable": true,
      "queued_at": "2026-05-10T03:13:01.000Z",
      "extract_completed_at": "2026-05-10T03:13:18.000Z"
    }
  ],
  "summary": {
    "queued_count": 1,
    "extracting_count": 1,
    "failed_count": 1,
    "total_active": 3
  }
}
```

**Behavior:**
- คืนเฉพาะของ user คนนี้
- `active` = `processing_status ∈ {queued, extracting}` ที่ยังไม่จบ
- `failed` = `processing_status='error'` ที่ยังไม่ถูก dismiss (in 24h window)
- เรียง active = queue_position ASC, failed = uploaded_at DESC
- เมื่อ `summary.total_active==0 AND failed_count==0` → frontend หยุด poll

**Errors:**
- 401 `UNAUTHORIZED` — no token

---

### POST /api/upload/{file_id}/retry (NEW)

**Auth:** Required (JWT) + ต้อง own file_id

**Request:** ไม่มี body

**Response 200:**
```json
{
  "id": "fail001",
  "processing_status": "queued",
  "queue_position": 4,
  "attempt_count": 2
}
```

**Behavior:**
- เฉพาะ file ที่ `processing_status='error'` AND `attempt_count < 3`
- Reset: `processing_status='queued'`, `extract_started_at=NULL`, `extract_completed_at=NULL`, `extract_error=NULL`
- เพิ่ม `attempt_count += 1`
- ไฟล์ดิบยังอยู่ใน disk (ไม่ลบตอน fail) → worker หยิบ extract ใหม่ได้

**Errors:**
- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN` — file_id ไม่ใช่ของ user
- 404 `FILE_NOT_FOUND`
- 409 `NOT_RETRYABLE` — status ≠ 'error' หรือ attempt_count ≥ 3
- 410 `FILE_GONE` — raw_path ไม่อยู่บนดิสก์แล้ว (ต้องอัปใหม่)

---

### POST /api/upload/{file_id}/dismiss-error (NEW)

**Auth:** Required (JWT) + ต้อง own file_id

**Behavior:** ลบ row ของ failed file ออกจาก DB + ลบไฟล์ดิบจาก disk + ลบ Drive copy (ถ้ามี) — สำหรับให้ user "เอาออกจาก tray" โดยไม่ต้องผ่าน /api/files/{id} DELETE flow

**Response 200:** `{"deleted": true}`

**Errors:**
- 401, 403, 404 standard

---

### GET /api/files (no schema change, but added fields surfaced)

`_serialize_file()` เพิ่ม 4 fields:
- `progress_step` (string | null)
- `progress_pct` (int 0-100 | null)
- `queued_at` (ISO datetime | null)
- `attempt_count` (int)

ของเดิมทุก field ยังเหมือน — backward compat สำหรับ /api/files consumers

---

## 💾 Data Model Changes

### `files` table — เพิ่ม 6 columns (idempotent migration)

| Column | Type | Default | Purpose |
|---|---|---|---|
| `progress_step` | TEXT | NULL | ข้อความสด TH 3-50 ตัวอักษร เช่น `"OCR หน้า 5/12"` `"Gemini ถอดเสียง"` |
| `progress_pct` | INTEGER | NULL | 0-100, NULL ถ้าไม่ทราบ (audio Gemini ไม่ stream % ได้) |
| `queued_at` | DATETIME | NULL | เวลาเข้าคิว (set ตอน /api/upload เสร็จ) |
| `extract_started_at` | DATETIME | NULL | เวลา worker หยิบไฟล์ออกจากคิว |
| `extract_completed_at` | DATETIME | NULL | เวลา extract เสร็จ (success หรือ error) |
| `extract_error` | TEXT | NULL | error message TH ที่ user friendly (3-200 chars) |
| `attempt_count` | INTEGER | 0 | retry counter |

**Indexes ใหม่:**
- `idx_files_queue_poll` ON `files(processing_status, queued_at)` — สำหรับ worker poll
- `idx_files_user_status` ON `files(user_id, processing_status)` — สำหรับ /api/upload-status

### `processing_status` enum (extended)

| State (เดิม) | State (ใหม่) | Transition |
|---|---|---|
| `processing` (placeholder ระหว่าง upload) | **เปลี่ยนเป็น** `queued` | upload → queued |
| `uploaded` (extract เสร็จ รอ AI) | คงเดิม | extracting → uploaded |
| - | **เพิ่ม** `extracting` | queued → extracting |
| `error` | คงเดิม | extracting → error (มี extract_error) |
| `organized` | คงเดิม | uploaded → organized (ผ่าน organize-new) |
| `ready` | คงเดิม | organized → ready (ผ่าน organize ครบ) |
| `vault_only` | คงเดิม | upload → vault_only (skip queue, ไม่ extract) |
| `reprocessed` | คงเดิม | (ผ่าน /api/files/{id}/reprocess) |

### Migration plan ([backend/database.py:init_db()](../../backend/database.py))

Idempotent SQLite migration block (เพิ่มใน v9.4.0 section หลัง v9.1.0):

```python
# v9.4.0 Migration — Upload Queue + Progress columns
result_v940 = await db.execute("PRAGMA table_info(files)")
file_cols_v940 = {row[1] for row in result_v940.fetchall()}

if "progress_step" not in file_cols_v940:
    await db.execute("ALTER TABLE files ADD COLUMN progress_step TEXT")
    migrated = True
if "progress_pct" not in file_cols_v940:
    await db.execute("ALTER TABLE files ADD COLUMN progress_pct INTEGER")
    migrated = True
if "queued_at" not in file_cols_v940:
    await db.execute("ALTER TABLE files ADD COLUMN queued_at DATETIME")
    migrated = True
if "extract_started_at" not in file_cols_v940:
    await db.execute("ALTER TABLE files ADD COLUMN extract_started_at DATETIME")
    migrated = True
if "extract_completed_at" not in file_cols_v940:
    await db.execute("ALTER TABLE files ADD COLUMN extract_completed_at DATETIME")
    migrated = True
if "extract_error" not in file_cols_v940:
    await db.execute("ALTER TABLE files ADD COLUMN extract_error TEXT")
    migrated = True
if "attempt_count" not in file_cols_v940:
    await db.execute("ALTER TABLE files ADD COLUMN attempt_count INTEGER DEFAULT 0")
    migrated = True

# Indexes
try:
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_queue_poll "
        "ON files(processing_status, queued_at)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_files_user_status "
        "ON files(user_id, processing_status)"
    )
except Exception as e:
    print(f"  ⚠️ v9.4.0 index warning: {e}")

# Backfill ไฟล์เก่า: ที่ status='processing' (ค้าง) → status='queued' (ให้ worker หยิบ)
# (กรณี upgrade ขณะมีไฟล์ค้าง pre-v9.4.0)
await db.execute(
    "UPDATE files SET processing_status='queued', queued_at=COALESCE(queued_at, uploaded_at) "
    "WHERE processing_status='processing' AND extracted_text=''"
)
```

**Production safety:** ADD only, idempotent, no drop/rename — compatible กับ Fly.io volume DB

---

## 🔧 Step-by-Step Implementation (สำหรับเขียว)

> ทำตามลำดับ Step 1 → Step 8. ทุก step มี self-test verification ก่อนข้าม

### Step 1: DB Schema + Migration

1. แก้ [backend/database.py](../../backend/database.py) — `class File`:
   - เพิ่ม 6 columns ตามตารางข้างบน (block หลัง `file_kind`)
   - Comment WHY ตาม convention (ไทย, อธิบายเหตุผล)
2. ใน `init_db()` — เพิ่ม migration block v9.4.0 (ตามตัวอย่างข้างบน)
3. **Self-test:** ลบ test DB → run startup → confirm 6 columns + 2 indexes สร้างได้

### Step 2: `backend/upload_worker.py` (NEW module)

โครงสร้าง:

```python
"""Upload worker — async background processor (v9.4.0).

Polls DB queue, runs extract_text + ai_ingest with progress reporting,
updates DB row when done. Single in-process task (asyncio.create_task at startup).

Recovery: on startup, reset rows with status='extracting' AND
extract_started_at < now-30min back to 'queued'.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from sqlalchemy import select, update
from .database import get_db, File
from .extraction import extract_text, classify_extraction_status, strip_surrogates
from .duplicate_detector import compute_content_hash
from .ai_ingest import ingest_via_ai, is_ai_format

logger = logging.getLogger(__name__)

# Tunable constants — ทำให้ test ง่าย
POLL_INTERVAL_SEC = 2.0
STALE_EXTRACT_TIMEOUT_SEC = 1800  # 30 min — ถ้านานกว่านี้ถือว่า worker crashed
MAX_RETRY_ATTEMPTS = 3
PROGRESS_DB_THROTTLE_SEC = 1.5  # อย่า update DB ถี่กว่านี้

_worker_task: asyncio.Task | None = None
_shutdown_event: asyncio.Event | None = None


async def start_worker() -> None:
    """เรียกตอน FastAPI startup. Idempotent (ถ้า task รันอยู่แล้ว = no-op)."""
    global _worker_task, _shutdown_event
    if _worker_task and not _worker_task.done():
        return
    _shutdown_event = asyncio.Event()
    await _recover_stale_jobs()
    _worker_task = asyncio.create_task(_worker_loop(), name="upload_worker")
    logger.info("Upload worker started")


async def stop_worker() -> None:
    """เรียกตอน shutdown. รอ task เสร็จ (max 5s)."""
    if _shutdown_event:
        _shutdown_event.set()
    if _worker_task:
        try:
            await asyncio.wait_for(_worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("Worker did not stop within 5s")


async def _worker_loop() -> None:
    """Main loop — poll DB, claim 1 job, process, repeat."""
    while not _shutdown_event.is_set():
        try:
            claimed = await _claim_next_job()
            if claimed is None:
                # No jobs — sleep + check shutdown
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=POLL_INTERVAL_SEC)
                except asyncio.TimeoutError:
                    pass
                continue
            await _process_job(claimed)
        except Exception as e:
            logger.error(f"Worker loop error: {e}", exc_info=True)
            await asyncio.sleep(POLL_INTERVAL_SEC)


async def _claim_next_job() -> dict | None:
    """Atomic SQLite UPDATE...WHERE...RETURNING (3.35+).

    Picks highest-priority queued file:
    sort key = (priority by ext-class, queued_at ASC)
    where priority: txt/img/code=1, docx/xlsx/pptx/pdf=2, audio/video=3
    """
    # ใช้ SQLAlchemy execute raw SQL เพื่อใช้ RETURNING
    # หรือใช้ SELECT ... FOR UPDATE ผ่าน 2-step (ใน SQLite ทำได้ผ่าน BEGIN IMMEDIATE)
    # Implementation: prefer atomic UPDATE...RETURNING ที่ SQLite 3.35+ รองรับ
    ...


async def _process_job(job: dict) -> None:
    """Run extract for 1 file. Updates progress periodically."""
    file_id = job["id"]
    raw_path = job["raw_path"]
    ext = job["filetype"]

    last_progress_write = 0.0

    async def report_progress(step: str, pct: int | None = None):
        nonlocal last_progress_write
        now = asyncio.get_event_loop().time()
        if now - last_progress_write < PROGRESS_DB_THROTTLE_SEC:
            return  # Throttle — กัน DB write spam
        last_progress_write = now
        async for db in get_db():
            await db.execute(
                update(File)
                .where(File.id == file_id)
                .values(progress_step=step, progress_pct=pct)
            )
            await db.commit()
            break

    try:
        await report_progress("กำลังเตรียมไฟล์", 5)

        # extract_text now accepts optional progress_callback
        if is_ai_format(ext):
            await report_progress("ส่งไฟล์ไป AI multimodal", 10)
            text = await ingest_via_ai(raw_path, ext, progress_callback=report_progress)
        else:
            await report_progress("กำลังอ่านข้อความในไฟล์", 20)
            # extract_text is sync — wrap in thread pool to not block event loop
            text = await asyncio.to_thread(
                extract_text, raw_path, ext, progress_callback=report_progress
            )

        text = strip_surrogates(text)
        content_hash = compute_content_hash(text)
        ext_status = classify_extraction_status(text)

        await report_progress("บันทึกผลลัพธ์", 95)

        async for db in get_db():
            await db.execute(
                update(File).where(File.id == file_id).values(
                    extracted_text=text,
                    content_hash=content_hash,
                    extraction_status=ext_status,
                    processing_status="uploaded",
                    progress_step=None,
                    progress_pct=100,
                    extract_completed_at=datetime.utcnow(),
                    extract_error=None,
                )
            )
            await db.commit()
            break

        # BYOS Drive push (เดิมเคยทำใน BackgroundTask — ย้ายมาที่นี่)
        await _push_to_drive_if_byos(file_id)

    except Exception as e:
        logger.error(f"Extract failed for {file_id}: {e}", exc_info=True)
        await _mark_job_failed(file_id, e)


async def _mark_job_failed(file_id: str, exc: Exception) -> None:
    """Set status=error + user-friendly TH message."""
    msg = _format_user_error(exc)
    async for db in get_db():
        await db.execute(
            update(File).where(File.id == file_id).values(
                processing_status="error",
                extraction_status="ocr_failed",  # generic label
                extract_completed_at=datetime.utcnow(),
                extract_error=msg,
                progress_step=None,
                progress_pct=None,
            )
        )
        await db.commit()
        break


def _format_user_error(exc: Exception) -> str:
    """Translate exception → user-friendly Thai message (3-200 chars)."""
    name = type(exc).__name__
    s = str(exc)[:150]
    if "encrypted" in s.lower() or "password" in s.lower():
        return "ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปโหลดใหม่"
    if "timeout" in s.lower():
        return "ไฟล์ใหญ่เกินไป — ใช้เวลาประมวลผลนานเกินกำหนด"
    if "memory" in s.lower():
        return "ไฟล์ใหญ่เกินที่ระบบรับไหว — ลองแบ่งไฟล์เล็กลง"
    if name in ("UnicodeDecodeError", "UnicodeEncodeError"):
        return "encoding ของไฟล์ผิดปกติ — ลอง re-save เป็น UTF-8"
    return f"ประมวลผลล้มเหลว ({name}) — ลองอัปใหม่หรือกดลองอีกครั้ง"


async def _recover_stale_jobs() -> None:
    """Reset jobs ที่ status='extracting' นานเกิน 30 นาที → 'queued' ที่ระบุ retry."""
    cutoff = datetime.utcnow() - timedelta(seconds=STALE_EXTRACT_TIMEOUT_SEC)
    async for db in get_db():
        result = await db.execute(
            update(File).where(
                File.processing_status == "extracting",
                File.extract_started_at < cutoff,
            ).values(
                processing_status="queued",
                extract_started_at=None,
                progress_step=None,
                progress_pct=None,
            )
        )
        await db.commit()
        if result.rowcount:
            logger.warning(f"Recovered {result.rowcount} stale jobs from extracting → queued")
        break


async def _push_to_drive_if_byos(file_id: str) -> None:
    """ย้าย Drive push logic เดิมมาที่นี่ (post-extract) — กัน duplicate code."""
    # Implementation: เรียก _push_uploads_to_drive เดิมจาก main.py
    # หรือ refactor ให้เป็น standalone function ใน drive_sync.py
    pass
```

**สิ่งที่เขียวต้อง implement:**
- [ ] `_claim_next_job()` ใช้ `BEGIN IMMEDIATE` + UPDATE...RETURNING (SQLite 3.35+, มาแน่ใน Python 3.11+ stdlib sqlite3)
- [ ] Priority sort logic (txt/img priority 1, docx/pdf=2, audio/video=3)
- [ ] `_push_to_drive_if_byos` — refactor logic เดิมจาก `main.py:_push_uploads_to_drive`

**Self-test (run manually):**
- [ ] Insert row status='queued' → start worker → wait 5s → confirm extracted
- [ ] Insert 5 rows → confirm processed in priority order
- [ ] Kill worker mid-extract → restart → confirm recovery (extract_started_at เก่า → queued)
- [ ] Force exception → confirm extract_error TH message ถูก format

### Step 3: `backend/extraction.py` — เพิ่ม progress_callback

แก้ `extract_text(filepath, filetype)` → `extract_text(filepath, filetype, progress_callback=None)`

จุดที่ต้อง report:
- `_extract_pdf_with_fallbacks` — PyPDF2 page loop: `progress_callback(f"อ่าน PDF หน้า {i}/{total}", int(i/total*60))`
- `_extract_pdf_ocr` — OCR loop หน้าต่อหน้า: `progress_callback(f"OCR หน้า {i}/{total}", int(20 + i/total*70))`
- `_extract_image_ocr` — `progress_callback("OCR รูปภาพ", 50)` (image OCR เดียว ไม่มี loop)
- ที่ไม่ใช่ async — callback เป็น sync function (worker wrap to async)

**Backward compat:** `progress_callback=None` = no-op (ไม่กระทบ caller เดิม)

### Step 4: `backend/ai_ingest.py` — เพิ่ม progress_callback

แก้ `ingest_via_ai(filepath, filetype)` → `ingest_via_ai(filepath, filetype, progress_callback=None)`

จุดที่ report:
- `_upload_to_gemini` start: `await progress_callback("อัปโหลดไป Gemini", 15)`
- After upload: `await progress_callback("Gemini ถอดเสียง/วิเคราะห์", 50)`
- After response: `await progress_callback("รับผลลัพธ์", 95)`

**Note:** Gemini ไม่ stream byte/duration progress ได้ — ใช้ขั้นตอน 3 ขั้นข้างต้น

### Step 5: `backend/main.py` — รื้อ `/api/upload` + เพิ่ม endpoints ใหม่

#### 5.1 เปลี่ยน `/api/upload` (เลิกทำ extract inline)

```python
@app.post("/api/upload")
async def upload_files(files, background_tasks, current_user, db):
    """v9.4.0 — save + queue mode. Extract runs in upload_worker background.

    Returns immediately (~100-200ms per file vs 30-120s before).
    """
    uploaded = []
    skipped = []
    _limits = _gl(current_user)
    allowed_types = _limits["allowed_file_types"]
    max_bytes = _limits["max_file_size_mb"] * 1024 * 1024
    file_limit = _limits["file_limit"]
    QUEUE_USER_CAP = 50  # max queued/extracting per user

    quota_lock = await _get_user_quota_lock(current_user.id)

    for upload_file in files:
        original_name = os.path.basename(upload_file.filename or "") or "unnamed"
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        is_vault = ext not in allowed_types
        contents = await upload_file.read()

        if len(contents) == 0:
            skipped.append(_make_skip("EMPTY_FILE", original_name))
            continue
        if len(contents) > max_bytes:
            skipped.append(_make_skip("FILE_TOO_LARGE", original_name, limit=_limits["max_file_size_mb"]))
            continue

        file_id = gen_id()
        user_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
        os.makedirs(user_upload_dir, exist_ok=True)
        safe_filename = f"{file_id}_{original_name}"
        raw_path = os.path.join(user_upload_dir, safe_filename)

        async with quota_lock:
            live_count = await _fc(db, current_user.id)
            if live_count >= file_limit:
                skipped.append(_make_skip("QUOTA_EXCEEDED", original_name, limit=file_limit))
                continue

            # v9.4.0 — global queue cap
            queue_count = await db.scalar(
                select(func.count()).select_from(File).where(
                    File.user_id == current_user.id,
                    File.processing_status.in_(["queued", "extracting"]),
                )
            )
            if queue_count and queue_count >= QUEUE_USER_CAP:
                skipped.append(_make_skip("QUEUE_FULL", original_name, limit=QUEUE_USER_CAP))
                continue

            now = datetime.utcnow()
            if is_vault:
                # vault skips queue — extract = name only, instant
                from .vault import build_vault_searchable_text
                vault_text = build_vault_searchable_text(original_name, ext)
                placeholder = File(
                    id=file_id, user_id=current_user.id, filename=original_name,
                    filetype=ext, raw_path=raw_path,
                    extracted_text=vault_text,
                    processing_status="vault_only",
                    extraction_status="vault",
                    file_kind="vault_only",
                    queued_at=now,
                    extract_completed_at=now,
                    progress_pct=100,
                )
            else:
                placeholder = File(
                    id=file_id, user_id=current_user.id, filename=original_name,
                    filetype=ext, raw_path=raw_path,
                    extracted_text="",
                    processing_status="queued",     # ← v9.4.0: queued instead of "processing"
                    content_hash=None,
                    extraction_status="pending",
                    file_kind="processed",
                    queued_at=now,
                )
            db.add(placeholder)
            await db.commit()

        # Save raw bytes — ทำนอก lock (lock ไม่ block IO)
        with open(raw_path, "wb") as f:
            f.write(contents)

        # คำนวณ queue_position (สำหรับ UI hint ทันที)
        if is_vault:
            queue_position = 0
            estimated_wait = 0
        else:
            qp_res = await db.execute(
                select(func.count()).select_from(File).where(
                    File.user_id == current_user.id,
                    File.processing_status == "queued",
                    File.queued_at <= now,
                )
            )
            queue_position = qp_res.scalar() or 1
            estimated_wait = queue_position * 8  # rough estimate

        uploaded.append({
            "id": file_id,
            "filename": original_name,
            "filetype": ext,
            "uploaded_at": now.isoformat(),
            "processing_status": placeholder.processing_status,
            "queue_position": queue_position,
            "estimated_wait_sec": estimated_wait,
            "file_kind": placeholder.file_kind,
        })

    return {"uploaded": uploaded, "count": len(uploaded), "skipped": skipped}
```

**สำคัญ:**
- ❌ ไม่เรียก `extract_text` หรือ `ai_ingest` ที่นี่อีกต่อไป
- ❌ ไม่ใช้ `pending_drive_pushes` + `BackgroundTask` (ย้ายไป worker)
- ✅ vault file ยังทำตรงๆ ไม่เข้าคิว (เร็วอยู่แล้ว — name-based text)

#### 5.2 เพิ่ม `/api/upload-status`

```python
@app.get("/api/upload-status")
async def upload_status(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # active = queued + extracting
    active_res = await db.execute(
        select(File).where(
            File.user_id == current_user.id,
            File.processing_status.in_(["queued", "extracting"]),
        ).order_by(File.queued_at.asc())
    )
    active_files = active_res.scalars().all()

    failed_cutoff = datetime.utcnow() - timedelta(hours=24)
    failed_res = await db.execute(
        select(File).where(
            File.user_id == current_user.id,
            File.processing_status == "error",
            File.extract_completed_at >= failed_cutoff,
        ).order_by(File.uploaded_at.desc())
    )
    failed_files = failed_res.scalars().all()

    # Compute queue_position สำหรับ active list
    active_payload = []
    queued_idx = 0
    for f in active_files:
        if f.processing_status == "queued":
            queued_idx += 1
            qp = queued_idx
            step = f.progress_step or f"รออันดับ {qp}"
        else:
            qp = 0
            step = f.progress_step or "กำลังประมวลผล"
        active_payload.append({
            "id": f.id,
            "filename": f.filename,
            "filetype": f.filetype,
            "processing_status": f.processing_status,
            "extraction_status": f.extraction_status,
            "queue_position": qp,
            "progress_step": step,
            "progress_pct": f.progress_pct or 0,
            "queued_at": f.queued_at.isoformat() if f.queued_at else None,
            "extract_started_at": f.extract_started_at.isoformat() if f.extract_started_at else None,
            "attempt_count": f.attempt_count or 0,
            "is_retryable": False,
        })

    failed_payload = [{
        "id": f.id, "filename": f.filename, "filetype": f.filetype,
        "processing_status": "error",
        "extraction_status": f.extraction_status,
        "extract_error": f.extract_error,
        "attempt_count": f.attempt_count or 0,
        "is_retryable": (f.attempt_count or 0) < MAX_RETRY_ATTEMPTS and os.path.exists(f.raw_path),
        "queued_at": f.queued_at.isoformat() if f.queued_at else None,
        "extract_completed_at": f.extract_completed_at.isoformat() if f.extract_completed_at else None,
    } for f in failed_files]

    return {
        "active": active_payload,
        "failed": failed_payload,
        "summary": {
            "queued_count": sum(1 for f in active_files if f.processing_status == "queued"),
            "extracting_count": sum(1 for f in active_files if f.processing_status == "extracting"),
            "failed_count": len(failed_payload),
            "total_active": len(active_payload),
        }
    }
```

#### 5.3 เพิ่ม `/api/upload/{file_id}/retry`

```python
@app.post("/api/upload/{file_id}/retry")
async def retry_upload(file_id: str, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}})
    if f.processing_status != "error":
        raise HTTPException(409, detail={"error": {"code": "NOT_RETRYABLE", "message": "ไฟล์นี้ไม่อยู่ในสถานะที่ retry ได้"}})
    if (f.attempt_count or 0) >= MAX_RETRY_ATTEMPTS:
        raise HTTPException(409, detail={"error": {"code": "NOT_RETRYABLE", "message": "เกิน retry limit"}})
    if not os.path.exists(f.raw_path):
        raise HTTPException(410, detail={"error": {"code": "FILE_GONE", "message": "ไฟล์ดิบหายไปแล้ว — ต้องอัปใหม่"}})

    f.processing_status = "queued"
    f.extract_started_at = None
    f.extract_completed_at = None
    f.extract_error = None
    f.progress_step = None
    f.progress_pct = None
    f.attempt_count = (f.attempt_count or 0) + 1
    f.queued_at = datetime.utcnow()
    await db.commit()

    qp_res = await db.execute(
        select(func.count()).select_from(File).where(
            File.user_id == current_user.id,
            File.processing_status == "queued",
            File.queued_at <= f.queued_at,
        )
    )
    return {
        "id": f.id,
        "processing_status": "queued",
        "queue_position": qp_res.scalar() or 1,
        "attempt_count": f.attempt_count,
    }
```

#### 5.4 เพิ่ม `/api/upload/{file_id}/dismiss-error`

(โค้ดสั้น — ลบ row + raw file + Drive copy ถ้ามี — ทำตาม pattern DELETE /api/files/{id})

#### 5.5 Update `_serialize_file` — เพิ่ม 4 fields

```python
"progress_step": f.progress_step,
"progress_pct": f.progress_pct,
"queued_at": f.queued_at.isoformat() if f.queued_at else None,
"attempt_count": f.attempt_count or 0,
```

#### 5.6 Register worker startup/shutdown hooks

```python
from .upload_worker import start_worker, stop_worker

@app.on_event("startup")
async def startup():
    await init_db()
    # ... existing rebuild logic ...
    await start_worker()  # ← NEW

@app.on_event("shutdown")
async def shutdown():
    await stop_worker()  # ← NEW
```

#### 5.7 ป้องกัน organize-new กดทับคิว

ใน `/api/organize-new` หรือ frontend — เพิ่ม preflight:

```python
# ใน /api/organize-new (backend) — สั้นๆ
queue_check = await db.scalar(
    select(func.count()).select_from(File).where(
        File.user_id == current_user.id,
        File.processing_status.in_(["queued", "extracting"]),
    )
)
if queue_check:
    # ไม่ block — แค่ถาม ผ่าน return field "pending_queue_count"
    # frontend แสดง toast เตือน + กดยืนยันต่อก็ได้ (organize เฉพาะที่ status='uploaded')
```

จริงๆ existing `/api/organize-new` query แค่ status='uploaded' อยู่แล้ว → ไม่ต้องแก้ logic เลย แค่เพิ่ม return field สำหรับ frontend tooltip

### Step 6: Frontend — `legacy-frontend/app.js`

#### 6.1 เปลี่ยน `uploadFiles()` flow (line 1439)

ของเดิม: รอ response นาน → loadFiles() ตอนเสร็จ
ของใหม่: response เร็ว → เปิด UploadTray → tray polls + auto-loadFiles เมื่อมีไฟล์เสร็จ

**Diff สำคัญ:**
- `xhr.upload.onload` ยังอยู่ — ใช้ track byte upload (ขั้น 1 = ส่งไฟล์)
- `xhr.onload` (response received) — ตอนนี้ response เร็ว → ปิด overlay + เปิด UploadTray
- ลบ `processingMsg` indeterminate phase (เพราะ extract ย้ายไป background)
- เพิ่ม `UploadTray.notifyEnqueued(uploaded)` หลัง response

#### 6.2 เพิ่ม `UploadTray` namespace (~250 lines)

```javascript
const UploadTray = (() => {
  let _pollHandle = null;
  let _pollAttempts = 0;
  let _isOpen = false;
  let _lastSnapshot = { active: [], failed: [], summary: {} };

  const POLL_INTERVAL_MS = 2000;
  const POLL_BACKOFF_AFTER_ATTEMPTS = 30; // 1 min — slow down if no change

  const $ = (sel) => document.querySelector(sel);
  const isTH = () => getLang() === 'th';

  function openIfHasItems() {
    // เรียกตอน load app — ตรวจถ้ามีงานในคิว → เปิด tray
    fetchStatus().then(s => {
      if (s.summary.total_active > 0 || s.summary.failed_count > 0) open();
    });
  }

  function open() {
    if (_isOpen) return;
    _ensureDom();
    document.querySelector('.upload-tray').classList.add('is-open');
    _isOpen = true;
    startPolling();
  }

  function close() {
    if (!_isOpen) return;
    document.querySelector('.upload-tray').classList.remove('is-open');
    _isOpen = false;
    stopPolling();
  }

  function _ensureDom() {
    if (document.querySelector('.upload-tray')) return;
    const html = `
      <div class="upload-tray" role="region" aria-label="${isTH() ? 'คิวอัปโหลด' : 'Upload queue'}">
        <header class="upload-tray-header">
          <h3 class="upload-tray-title">
            <svg class="upload-tray-icon" ...></svg>
            <span class="upload-tray-title-text"></span>
          </h3>
          <button class="upload-tray-close" aria-label="${isTH() ? 'ย่อ' : 'Minimize'}">
            <svg ...></svg>
          </button>
        </header>
        <ul class="upload-tray-list" role="list"></ul>
        <footer class="upload-tray-footer">
          <span class="upload-tray-summary"></span>
        </footer>
      </div>
    `;
    document.body.insertAdjacentHTML('beforeend', html);
    $('.upload-tray-close').addEventListener('click', close);
  }

  async function fetchStatus() {
    try {
      const res = await authFetch('/api/upload-status');
      if (!res.ok) return _lastSnapshot;
      const data = await res.json();
      _lastSnapshot = data;
      return data;
    } catch (e) {
      return _lastSnapshot;
    }
  }

  function startPolling() {
    if (_pollHandle) return;
    _pollAttempts = 0;
    const tick = async () => {
      const data = await fetchStatus();
      render(data);
      _pollAttempts++;

      // หยุด poll ถ้าไม่มีอะไรเหลือ
      if (data.summary.total_active === 0 && data.summary.failed_count === 0) {
        stopPolling();
        // Auto-close เฉพาะกรณีไม่มี failed (ให้ user กดเอง)
        setTimeout(() => close(), 1500);
        // refresh main file list
        if (typeof loadFiles === 'function') loadFiles();
        if (typeof loadStats === 'function') loadStats();
        if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount();
        return;
      }

      // Backoff: หลัง 30 ticks (1 min) ถ้ายังเหมือนเดิม → poll ทุก 5s แทน 2s
      const interval = _pollAttempts > POLL_BACKOFF_AFTER_ATTEMPTS ? 5000 : POLL_INTERVAL_MS;
      _pollHandle = setTimeout(tick, interval);
    };
    tick();
  }

  function stopPolling() {
    if (_pollHandle) {
      clearTimeout(_pollHandle);
      _pollHandle = null;
    }
  }

  function render(data) {
    const list = $('.upload-tray-list');
    const titleEl = $('.upload-tray-title-text');
    const summaryEl = $('.upload-tray-summary');
    if (!list) return;

    const items = [...data.active, ...data.failed];
    if (titleEl) {
      titleEl.textContent = isTH()
        ? `คิวอัปโหลด (${data.summary.total_active + data.summary.failed_count})`
        : `Upload queue (${data.summary.total_active + data.summary.failed_count})`;
    }
    if (summaryEl) {
      const parts = [];
      if (data.summary.queued_count) parts.push(isTH() ? `${data.summary.queued_count} รอ` : `${data.summary.queued_count} queued`);
      if (data.summary.extracting_count) parts.push(isTH() ? `${data.summary.extracting_count} กำลังทำ` : `${data.summary.extracting_count} processing`);
      if (data.summary.failed_count) parts.push(isTH() ? `${data.summary.failed_count} ล้มเหลว` : `${data.summary.failed_count} failed`);
      summaryEl.textContent = parts.join(' • ');
    }

    list.innerHTML = items.map(_renderItem).join('');
    list.querySelectorAll('[data-retry-id]').forEach(btn => {
      btn.addEventListener('click', () => onRetry(btn.dataset.retryId));
    });
    list.querySelectorAll('[data-dismiss-id]').forEach(btn => {
      btn.addEventListener('click', () => onDismiss(btn.dataset.dismissId));
    });
  }

  function _renderItem(item) {
    const isFailed = item.processing_status === 'error';
    const isExtracting = item.processing_status === 'extracting';
    const isQueued = item.processing_status === 'queued';
    const pillClass = isFailed ? 'is-error' : isExtracting ? 'is-active' : 'is-warning';
    const pillText = isFailed ? (isTH() ? 'ล้มเหลว' : 'Failed')
                   : isExtracting ? (isTH() ? 'กำลังทำ' : 'Working')
                   : (isTH() ? 'รอคิว' : 'Queued');
    const ext = item.filetype || '—';
    const filenameEsc = escapeHtml(item.filename);

    let body;
    if (isFailed) {
      body = `<div class="upload-tray-error">${escapeHtml(item.extract_error || (isTH() ? 'ไม่ทราบสาเหตุ' : 'Unknown error'))}</div>`;
    } else if (isExtracting) {
      const pct = Math.max(0, Math.min(100, item.progress_pct || 0));
      body = `
        <div class="upload-tray-step">${escapeHtml(item.progress_step || '...')}</div>
        <div class="meter" aria-label="${pct}%">
          <div class="meter-fill" style="width:${pct}%"></div>
        </div>`;
    } else { // queued
      body = `<div class="upload-tray-step">${escapeHtml(item.progress_step || (isTH() ? `อันดับ ${item.queue_position}` : `Position ${item.queue_position}`))}</div>`;
    }

    const actions = isFailed ? `
      <div class="upload-tray-actions">
        ${item.is_retryable ? `<button class="btn btn-sm btn-outline" data-retry-id="${item.id}">${isTH() ? 'ลองใหม่' : 'Retry'}</button>` : ''}
        <button class="btn btn-sm btn-ghost" data-dismiss-id="${item.id}">${isTH() ? 'ลบ' : 'Dismiss'}</button>
      </div>
    ` : '';

    return `
      <li class="upload-tray-item" data-file-id="${item.id}">
        <div class="upload-tray-item-head">
          <span class="upload-tray-filename" title="${filenameEsc}">${filenameEsc}</span>
          <span class="status-pill ${pillClass}">${pillText}</span>
        </div>
        <div class="upload-tray-meta">
          <span class="upload-tray-ext">.${escapeHtml(ext)}</span>
        </div>
        ${body}
        ${actions}
      </li>
    `;
  }

  async function onRetry(fileId) {
    try {
      const res = await authFetch(`/api/upload/${fileId}/retry`, { method: 'POST' });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        showToast(err.error?.message || (isTH() ? 'ลองใหม่ไม่ได้' : 'Retry failed'), 'error');
        return;
      }
      await fetchStatus().then(render);
    } catch (e) {
      showToast(isTH() ? 'เครือข่ายขัดข้อง' : 'Network error', 'error');
    }
  }

  async function onDismiss(fileId) {
    try {
      await authFetch(`/api/upload/${fileId}/dismiss-error`, { method: 'POST' });
      await fetchStatus().then(render);
    } catch (e) {}
  }

  function notifyEnqueued(uploaded) {
    if (!uploaded || uploaded.length === 0) return;
    open();
    // Optimistic — render พร้อมไฟล์ที่เพิ่ง enqueue (ไม่ต้องรอ poll tick แรก)
    const optimistic = uploaded.map(u => ({
      id: u.id, filename: u.filename, filetype: u.filetype,
      processing_status: u.processing_status,
      queue_position: u.queue_position || 1,
      progress_step: isTH() ? `อันดับ ${u.queue_position || 1}` : `Position ${u.queue_position || 1}`,
      progress_pct: 0, attempt_count: 0,
    }));
    _lastSnapshot = {
      active: [...optimistic, ..._lastSnapshot.active],
      failed: _lastSnapshot.failed,
      summary: { ..._lastSnapshot.summary, total_active: (_lastSnapshot.summary.total_active || 0) + optimistic.length },
    };
    render(_lastSnapshot);
  }

  return { open, close, openIfHasItems, notifyEnqueued };
})();

// เรียกตอน showApp() / boot
window.UploadTray = UploadTray;
```

#### 6.3 เปลี่ยน `uploadFiles()` ให้ใช้ Tray

```javascript
async function uploadFiles(fileList) {
  if (_uploadInFlight) { /* ... existing ... */ return; }
  // ... existing batch limit checks ...

  _uploadInFlight = true;
  // ลด overlay ลงเหลือแค่ "ส่งไฟล์ขึ้น server" — extract ย้ายไป tray
  showLoadingOverlay(baseMsg(0, 0), 'upload');

  try {
    // ... existing parallel pool 3 (ไม่เปลี่ยน) ...
    const data = { uploaded: aggUploaded, skipped: aggSkipped, count: aggUploaded.length };

    // v9.4.0 — toast + tray instead of "processing..." overlay phase
    if (data.count > 0) {
      showToast(`${t('upload.queuedCount').replace('{n}', data.count)}`, 'info');
      UploadTray.notifyEnqueued(data.uploaded);
    }

    // ... existing skipped/quota/vault/duplicate handling — same ...
    // No changes to loadFiles / loadStats — tray will trigger them when queue empties
  } catch (e) {
    // ... existing error handling ...
  } finally {
    _uploadInFlight = false;
    hideLoadingOverlay();
  }
}
```

#### 6.4 เพิ่ม i18n keys (TH+EN)

```javascript
'upload.queuedCount': 'เพิ่ม {n} ไฟล์เข้าคิวแล้ว — กำลังประมวลผลด้านล่าง',  // TH
'upload.queuedCount': '{n} files queued — processing in tray below',          // EN
'upload.tray.title': 'คิวอัปโหลด',
'upload.tray.minimize': 'ย่อ',
'upload.tray.queued': 'รอคิว',
'upload.tray.working': 'กำลังทำ',
'upload.tray.failed': 'ล้มเหลว',
'upload.tray.retry': 'ลองใหม่',
'upload.tray.dismiss': 'ลบ',
'upload.tray.position': 'อันดับ {n}',
// ... + EN equivalents
```

#### 6.5 เรียก `UploadTray.openIfHasItems()` ตอน showApp()

ใน `showApp()` หรือ `init()` หลัง JWT verify → call `UploadTray.openIfHasItems()` เพื่อเปิด tray ถ้ายังมีไฟล์ค้างจาก session ก่อน

### Step 7: Frontend — `legacy-frontend/styles.css`

ใช้ token เดิมเท่านั้น (ดู [ui-foundation.md §1](../contracts/ui-foundation.md)). ห้าม literal padding/color/duration

```css
/* ═══ UPLOAD TRAY — v9.4.0 ═══ */

.upload-tray {
  position: fixed;
  bottom: var(--space-4);
  right: var(--space-4);
  width: 360px;
  max-width: calc(100vw - var(--space-8));
  max-height: 60vh;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--elev-3);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  transform: translateY(calc(100% + var(--space-4)));
  opacity: 0;
  pointer-events: none;
  transition:
    transform var(--duration-base) var(--ease-out),
    opacity var(--duration-base) var(--ease-out);
}
.upload-tray.is-open {
  transform: translateY(0);
  opacity: 1;
  pointer-events: auto;
}

.upload-tray-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--border);
}

.upload-tray-title {
  font-size: var(--fs-base);
  font-weight: 600;
  color: var(--text-primary);
  margin: 0;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-variant-numeric: tabular-nums;
}

.upload-tray-icon {
  width: 16px;
  height: 16px;
  color: var(--accent);
}

.upload-tray-close {
  background: transparent;
  border: 0;
  color: var(--text-muted);
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
}
.upload-tray-close:hover { color: var(--text-primary); background: var(--surface-3); }
.upload-tray-close:focus-visible { box-shadow: var(--ring-focus); outline: 0; }

.upload-tray-list {
  list-style: none;
  margin: 0;
  padding: var(--space-2);
  overflow-y: auto;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.upload-tray-item {
  padding: var(--space-3);
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.upload-tray-item-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-2);
}

.upload-tray-filename {
  font-size: var(--fs-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.upload-tray-meta {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.upload-tray-step {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.upload-tray-error {
  font-size: var(--fs-xs);
  color: var(--error);
  background: color-mix(in srgb, var(--error) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--error) 25%, transparent);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
}

.upload-tray-actions {
  display: flex;
  gap: var(--space-2);
}

.upload-tray-footer {
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

@media (max-width: 600px) {
  .upload-tray {
    bottom: var(--space-3);
    right: var(--space-3);
    left: var(--space-3);
    width: auto;
    max-height: 50vh;
  }
}

@media (prefers-reduced-motion: reduce) {
  .upload-tray { transition: opacity var(--duration-fast); transform: none; }
  .upload-tray.is-open { opacity: 1; }
}
```

**UI Foundation Contract checklist:**
- [x] Token-only — no literals
- [x] Reuses `.meter` `.meter-fill` `.status-pill` `.btn .btn-sm .btn-outline .btn-ghost` (atom reuse)
- [x] No new card/chip variants
- [x] Tabular nums บนตัวเลข (count, position, %)
- [x] Focus ring บน close button
- [x] No emoji ใน UI text
- [x] No uppercase metric labels
- [x] @media reduced-motion respected
- [x] Mobile responsive (≥ 44px touch via existing `.btn-sm`)
- [x] z-index ใช้ token

### Step 8: HTML cache-bust + version label

[legacy-frontend/app.html](../../legacy-frontend/app.html):
- เปลี่ยน `?v=9.3.4` → `?v=9.4.0` ทุกที่
- version label `v9.3.4` → `v9.4.0`

[backend/config.py](../../backend/config.py):
- `APP_VERSION = "9.3.4"` → `APP_VERSION = "9.4.0"`

---

## 🧪 Test Scenarios (สำหรับฟ้า)

### Smoke (`scripts/upload_queue_smoke.py` — 30 cases)

**Queue lifecycle (T1-T8):**
- T1: POST /api/upload (PDF) → response < 500ms + status='queued' + queue_position=1
- T2: POST 5 ไฟล์ติด → ทั้งหมด status='queued' + position 1-5
- T3: รอ 30s → first file status='uploaded' + extracted_text != "" + progress_pct=100
- T4: ระหว่าง extract → GET /api/upload-status → file 1 status='extracting' + progress_step != null
- T5: txt+pdf+m4a queued พร้อมกัน → priority order: txt → pdf → m4a (ตาม ext-class)
- T6: vault file (.exe) → status='vault_only' ทันที (ไม่เข้าคิว)
- T7: queue 50 ไฟล์ → file 51 ได้ skip code='QUEUE_FULL'
- T8: 2 users upload 5 ไฟล์พร้อมกัน → ไฟล์ของกัน user แยกออกใน /api/upload-status

**Worker recovery (T9-T12):**
- T9: insert row status='extracting' extract_started_at=2 hr ago → start worker → recover เป็น 'queued'
- T10: insert row status='extracting' extract_started_at=10 min ago → ยังไม่ recover (< 30 min)
- T11: kill server กลาง extract → restart → file ที่ค้างถูก recover
- T12: 100 stale rows → recovery ทำได้ใน < 5s

**Progress reporting (T13-T16):**
- T13: PDF 12 หน้า → progress_step มี "OCR หน้า X/12" อย่างน้อย 3 ครั้ง
- T14: progress_pct ค่าเพิ่มขึ้น monotonically (0 → 100)
- T15: throttle: ระหว่าง extract 5s → DB write progress ≤ 4 ครั้ง (ทุก 1.5s)
- T16: m4a audio → progress_step ผ่าน "อัปโหลดไป Gemini" → "Gemini ถอดเสียง" → "บันทึกผลลัพธ์"

**Error + Retry (T17-T22):**
- T17: PDF เข้ารหัส → status='error' + extract_error=TH message + is_retryable=true
- T18: simulate Gemini quota error → user-friendly TH message
- T19: POST /api/upload/{id}/retry → status='queued' + attempt_count=1
- T20: retry 3 ครั้ง → ครั้งที่ 4 ได้ 409 NOT_RETRYABLE
- T21: ลบ raw file → POST retry → ได้ 410 FILE_GONE
- T22: POST /api/upload/{id}/dismiss-error → row หาย + raw file หาย

**API contract (T23-T26):**
- T23: GET /api/upload-status (no auth) → 401
- T24: POST retry user A's file with user B token → 403 FORBIDDEN
- T25: POST retry on file status='uploaded' → 409 NOT_RETRYABLE
- T26: GET /api/files response มี 4 fields ใหม่ (progress_step, progress_pct, queued_at, attempt_count)

**Backward compat (T27-T30):**
- T27: existing file (status='uploaded') ไม่ถูก worker ไปหยิบทำใหม่
- T28: organize-new ใช้ได้ปกติ + ข้าม file ที่ status ∈ {queued, extracting}
- T29: BYOS user file ที่ extract เสร็จ → push ไป Drive ได้ปกติ
- T30: existing extract_status='vault' ของ vault file ไม่เปลี่ยน

### Playwright UI (`tests/e2e-ui/v9.4.0-upload-tray.spec.js` — 12 cases)

- E1: upload 1 PDF → tray โผล่ ด้านล่าง-ขวา + filename + status pill 'queued'
- E2: upload 3 ไฟล์ → 3 items ใน list + summary count = 3
- E3: ไฟล์เปลี่ยน status='extracting' → meter (progress bar) แสดง + step text update
- E4: ไฟล์เสร็จ → หายจาก active list (ภายใน 3s ของ poll)
- E5: ทุกไฟล์เสร็จ → tray ปิดอัตโนมัติ + main file list refresh
- E6: simulate fail → ไฟล์ย้ายไป failed section + retry/dismiss buttons แสดง
- E7: คลิก retry → status เปลี่ยน 'queued' + button หาย
- E8: คลิก dismiss → item หายจาก tray
- E9: คลิก minimize → tray หาย + polling หยุด
- E10: refresh page ขณะคิวยังมีไฟล์ → tray โผล่อัตโนมัติ
- E11: mobile viewport (375x667) → tray full-width + max-height 50vh
- E12: prefers-reduced-motion → tray ไม่มี translateY animation

### Pytest (`tests/test_upload_progress.py` — 15 cases)

- P1-P5: progress_callback wiring บน extract_text + ai_ingest paths
- P6-P9: _format_user_error mapping (encrypted/timeout/memory/encoding)
- P10-P12: throttle behavior (< 1.5s = no DB write)
- P13-P15: priority sort logic (txt < pdf < audio)

---

## ✅ Done Criteria

- [ ] 6 columns + 2 indexes added via idempotent migration (verified ใน sandbox DB)
- [ ] `/api/upload` คืน response < 500ms (vs 30-120s เดิม) สำหรับไฟล์ปกติ
- [ ] `/api/upload-status` ทำงาน + คืนเฉพาะ user ตัวเอง
- [ ] `/api/upload/{id}/retry` ทำงาน + enforce attempt_count ≤ 3
- [ ] `/api/upload/{id}/dismiss-error` ทำงาน + ลบ raw file
- [ ] Worker auto-start ตอน FastAPI startup
- [ ] Worker recovery: stale 'extracting' → 'queued'
- [ ] Upload Tray UI โผล่ + polling 2s + auto-close
- [ ] Tray persists ข้าม browser reload (ถ้า queue ยังไม่ว่าง)
- [ ] Retry + Dismiss buttons ทำงานครบ
- [ ] Progress step + meter render ถูก
- [ ] No breaking change กับ /api/files / /api/organize-new / Drive push
- [ ] All v9.4.0 + v9.3.4 + v9.3.0 regression tests pass
- [ ] APP_VERSION bumped 9.3.4 → 9.4.0
- [ ] data-models.md + api-spec.md updated
- [ ] UI Foundation Contract §6 checklist passed (no token violations)

---

## ⚠️ Risks / Open Questions

### Risk 1 — SQLite write contention (worker progress + main app writes)

**Risk:** Worker เขียน progress ทุก 1.5s + main app เขียน upload row อาจชน → SQLite ล็อกทั้งไฟล์

**Mitigation:**
- Throttle progress write ไม่เกิน 1 ครั้ง / 1.5s
- ใช้ short transaction (`async with db.begin()` คอยปิดเร็ว)
- WAL mode ตั้งใน init_db (ถ้ายังไม่ได้ตั้ง — เช็คใน database.py ก่อน)
- Index บน (status, queued_at) ลด lock duration

### Risk 2 — Multi-uvicorn worker conflict (อนาคต)

**Risk:** ถ้า scale uvicorn เป็น multi-worker (Fly.io) → worker หลายตัว poll DB ตัวเดียวกัน อาจหยิบ row ซ้ำ

**Mitigation:**
- Atomic claim ผ่าน `UPDATE files SET status='extracting', extract_started_at=? WHERE id=? AND status='queued'` + ตรวจ rowcount
- ถ้า rowcount=0 → คนอื่น claim ไปแล้ว → loop ใหม่
- Document ใน worker module: "uvicorn workers > 1 ต้องตรวจ multi-worker safety ด้วย"

### Risk 3 — Frontend polling ใช้ bandwidth + battery มือถือ

**Risk:** mobile user เปิดทิ้ง = poll ทุก 2s ตลอด

**Mitigation:**
- Backoff หลัง 30 ticks (1 min) → ทุก 5s
- หยุด poll เมื่อ tray ปิด
- หยุด poll เมื่อ summary ว่าง
- Document Visibility API: หยุด poll เมื่อ tab ถูก hide → resume เมื่อกลับมา (defer to v9.4.1 ถ้ายังไม่ทำ)

### Risk 4 — User เห็น queue เต็มแล้ว frustrated

**Risk:** QUEUE_USER_CAP=50 — ถ้า user อัป 100 ไฟล์ → 50 ไฟล์แรกขึ้นคิว 50 ไฟล์หลัง skip

**Mitigation:**
- Toast แสดงชัดเจน: "{n} ไฟล์อยู่ในคิวแล้ว — รอคิวว่างก่อนอัปเพิ่ม"
- ปุ่ม "ดูคิว" ใน toast → เปิด tray
- Free plan limit อยู่แล้ว 50 ไฟล์รวม → ไม่กระทบ free
- Starter limit 200 ไฟล์ → 50 queue cap = soft limit ป้องกัน DoS ตัวเอง

### Risk 5 — Backend memory ระหว่าง /api/upload save ไฟล์ใหญ่

**Risk:** `contents = await upload_file.read()` ยังโหลดทั้งไฟล์เข้า RAM (ไม่เปลี่ยนจาก v9.3.4)

**Mitigation (out of scope v9.4.0):** stream ไฟล์ลง disk แทน load RAM — ทำใน v9.4.1+
**Note:** v9.4.0 อย่างน้อยลดเวลา request ลง 100x (extract ย้ายไป background) — RAM peak สั้นลงแล้ว

### Risk 6 — BYOS Drive push ไม่ทำงาน (ย้าย logic)

**Risk:** ของเดิม `_push_uploads_to_drive` เป็น BackgroundTask หลัง /api/upload commit. v9.4.0 ย้ายไป worker — ถ้า refactor พลาด Drive push หาย

**Mitigation:**
- Refactor: extract `_push_to_drive` เป็น standalone function (callable จาก worker)
- Test: T29 ตรวจ BYOS user → file ที่ extract เสร็จ → Drive copy มี
- Fallback path: ถ้า worker push fail → log error, ไม่ retry (เหมือนเดิมที่ "best-effort")

### Open Question 1 — Worker concurrency เริ่มที่ 1 หรือ 2?

- **1 (เลือก default):** ปลอดภัย, sequential, ง่ายต่อ debug
- **2:** เร็วขึ้น 2x (ถ้า CPU ไม่ติด lock) แต่เพิ่มความซับซ้อน

**Recommendation:** เริ่ม 1 → measurement → ปรับเป็น 2 ในเวอรชั่นหน้าถ้าจำเป็น

### Open Question 2 — Tray location bottom-right ตีกับ guide-fab ที่ hidden แล้วไหม?

- v9.3.x guide-fab `display: none` แล้ว ([per memory](../current/pipeline-state.md))
- bottom-right ว่าง — ใช้ตำแหน่งนี้ปลอดภัย

**Confirmed:** ใช้ bottom-right ได้

### Open Question 3 — Auto-retry กี่ครั้งก่อนต้องให้ user กด?

- **0 (เลือก default):** error ก็ stop ทันที, user เห็น message + กด retry
- **1:** retry อัตโนมัติ 1 ครั้ง (handle transient error เช่น Gemini 503)
- **3:** retry 3 ครั้ง exponential backoff

**Recommendation:** เริ่ม 0 (manual retry) → ดูผลจริงก่อน
**Reasoning:** ผู้ใช้บอกว่า "ช้าได้แค่ต้องรู้ว่าทำอะไรอยู่" → ลำเอียงไปทาง transparency มากกว่า auto-magic

### Open Question 4 — Rollout strategy: ทันทีหรือ feature flag?

- **ทันที:** simpler, ทุก user ได้พร้อมกัน
- **Feature flag:** ENV var `UPLOAD_QUEUE_ENABLED=true` → ถ้า false fallback inline (ปลอดภัย)

**Recommendation:** **ทันที** เพราะ migration backward compat (existing files ไม่กระทบ) + worker recovery รับ stale rows ได้

---

## 📌 Notes for นักพัฒนา (เขียว)

### Gotchas

1. **`extract_text` เป็น sync** — เรียกใน worker ต้อง wrap `asyncio.to_thread(extract_text, ...)` เพื่อไม่ block event loop
2. **`progress_callback` ส่งเข้า extract_text** — ต้องเป็น sync function. Worker ต้อง wrap `_progress_proxy` ที่ schedule async DB write ผ่าน event loop
3. **SQLite UPDATE...RETURNING** — Python 3.11+ stdlib sqlite3 รองรับ. Confirm Python version ก่อน implement (ดู `python --version` บน Fly.io image)
4. **`_USER_QUOTA_LOCKS` ยังต้องอยู่** — ป้องกัน race ในการ insert placeholder
5. **`vault_only` files ข้ามคิว** — ทำใน /api/upload ตรงๆ เหมือนเดิม (เร็วอยู่แล้ว)
6. **Drive push ใน worker** — ใน BYOS user เท่านั้น (`storage_mode=='byos'`). non-BYOS = no-op
7. **`progress_step` Thai length** — TEXT column ไม่จำกัด แต่ keep ≤ 80 chars ใน practice
8. **Worker shutdown** — ใช้ `asyncio.wait_for(_shutdown_event.wait(), timeout=POLL_INTERVAL_SEC)` ระหว่าง idle เพื่อตอบ shutdown signal เร็ว
9. **`ai_ingest.ingest_via_ai` async** — ไม่ต้อง to_thread (มันใช้ httpx async อยู่แล้ว)
10. **Test ที่ใช้ DB จริง** — ใช้ `tmp_path` + override DATABASE_URL หรือสร้าง test fixture ที่ truncate `files` ก่อน

### Pattern reuse

- Per-user lock: ใช้ `_get_user_quota_lock` เดิม (ไม่สร้างใหม่)
- Atomic claim pattern: คล้ายกับ `pack_share.py` cascade-safe atomic claim ([reference](../plans/archive/2026-05-08-share-pack-v9.3.0.md))
- DB migration idempotent: ตามแบบ v7.5.0 + v9.1.0 ใน [database.py:init_db()](../../backend/database.py)
- Frontend polling pattern: คล้าย `loadUnprocessedCount` ที่เรียกหลัง upload — แต่ tray มี explicit poll loop
- i18n keys: ใส่ใน object `i18n_th` + `i18n_en` ตามแบบเดิม (line ~600+)
- Atom reuse: `.meter`, `.status-pill`, `.btn .btn-sm .btn-outline .btn-ghost` — ดู [shared.css canonical atoms section](../../legacy-frontend/shared.css)

### Don't do

- ❌ ห้ามเปลี่ยน existing `extract_text` signature โดยทำให้ `progress_callback` required (default=None)
- ❌ ห้ามแก้ `/api/organize-new` logic — เพิ่มแค่ tooltip return field
- ❌ ห้าม drop `processing="processing"` value — backfill ที่ migrate เก็บไว้ + ให้ worker หยิบไป
- ❌ ห้ามใช้ Redis / Celery / multiprocessing
- ❌ ห้ามสร้าง atom CSS variant ใหม่ (`.upload-tray-pill` ฯลฯ — ใช้ `.status-pill.is-error` แทน)
- ❌ ห้ามใช้ literal `8px` `#6366f1` ใน styles.css ใหม่ — ใช้ token เท่านั้น
- ❌ ห้าม commit `.env` / `.jwt_secret` / DB
- ❌ ห้าม WebSocket — polling เพียงพอสำหรับ scale ปัจจุบัน

### Effort estimate

| Phase | สิ่งที่ทำ | เวลา (เขียว) |
|---|---|---|
| 1 | DB schema + migration | 1 hr |
| 2 | upload_worker.py + recovery | 4 hrs |
| 3-4 | extract_text + ai_ingest progress_callback | 1 hr |
| 5 | main.py refactor + 4 endpoints | 3 hrs |
| 6 | Frontend tray module + uploadFiles changes + i18n | 4 hrs |
| 7 | styles.css upload-tray | 1.5 hrs |
| 8 | HTML cache-bust + version | 0.5 hr |
| **Self-test** | manual + 30 smoke + 12 Playwright + 15 pytest | 3 hrs |
| **Memory updates** | data-models, api-spec, pipeline-state | 0.5 hr |
| **Total** | | **~18.5 hrs (~2.5 วัน)** |

ฟ้า: ~6 hrs (review + 57 cases run + UI Foundation Contract verify + edge case probing)

---

## 🎬 Pre-flight checks ก่อน user approve

- [ ] User ตอบ Open Question 1-4 (หรือยอมรับ default ทั้งหมด)
- [ ] User confirm scope = "upload only, organize queue เก็บไว้รอบหน้า"
- [ ] User confirm acceptable: สถานะ "processing" เก่าใน DB จะถูก backfill เป็น "queued"
- [ ] User confirm: Drive push retain semantic (best-effort, ย้ายมาที่ worker)
- [ ] User confirm: ไม่ต้องการ feature flag (rollout ทันที)

---

**End of plan — รอ user approve เพื่อไป state `plan_approved` แล้วส่งต่อให้เขียว**
