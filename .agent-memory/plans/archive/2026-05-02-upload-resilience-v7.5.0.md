# Plan: Upload Resilience v7.5.0

**Author:** แดง (Daeng)
**Date:** 2026-05-02
**Status:** approved (per user "ดำเนินการตามที่แดงแนะนำ" 2026-05-02)
**Foundation:** v7.4.0 master HEAD `b8e8014` + v7.1.0 dedupe pivot (DUP-003)
**Estimated time:** ~12-13 ชม. รวม 4 phase (ทำเป็นช่วงได้)

---

## 🎯 Goal

ทำให้ระบบ upload + extract + organize **rock-solid** สำหรับไฟล์ที่ผู้ใช้จริงเอามา (รวมไฟล์ใหญ่ / ไฟล์เพี้ยน / format นอก list) แทนที่จะ silently fail หรือเตะออกเฉยๆ

**Key outcomes:**
1. ไม่มี orphan file ใน DB (extract พังต้องบอก user รู้ + retry ได้)
2. ไฟล์ใหญ่ใช้งานได้จริง — เก็บต้นฉบับเต็ม + วิเคราะห์ครบทุกส่วน (map-reduce)
3. Skip reason actionable — บอก user ว่าทำต่ออะไร ไม่ใช่แค่ "ไม่รองรับ"
4. รองรับ format ที่ business user คาดหวัง (xlsx ขึ้นไป)

---

## 📚 Context

### ทำไมต้องทำ
แดงสำรวจ pipeline upload→extract→organize ตามที่ user ถาม "ระบบจัดการไฟล์ที่ upload ได้มีประสิทธิภาพมั้ย" เจอ 6 ปัญหาที่ระบบทำงานพังเงียบๆ:

1. **png/jpg ใน `allowed_types` แต่ extraction reject** — [extraction.py:52-59](../../backend/extraction.py#L52-L59) → orphan
2. **Error msg size ผิด** — [main.py:301](../../backend/main.py#L301) ใช้ `MAX_FILE_SIZE_MB=10` แสดง แต่ check จริง `_limits=100`
3. **Skip reason flat string** — [main.py:282](../../backend/main.py#L282) ไม่มี code/suggestion ให้ frontend ใช้
4. **Frontend join skip เป็น toast เดียว** — [app.js:1287-1294](../../legacy-frontend/app.js#L1287) อ่านไม่รู้เรื่อง
5. **ไม่มี extraction_status column** — [database.py:56](../../backend/database.py#L56) `processing_status` mix หลายความหมาย
6. **LLM ตัดเหลือ 6K chars** — [organizer.py:252](../../backend/organizer.py#L252) ไฟล์ใหญ่ถูกตัด 96%

### Decisions ก่อนหน้าที่เกี่ยวข้อง
- **DUP-003 (v7.1):** dedupe trigger ย้าย upload → organize-new — ไฟล์เข้า DB ก่อน detect
- **v7.0 BYOS:** raw + extracted text push Drive ผ่าน background_task — ไม่ block upload
- **v7.2.0:** XHR onprogress + beforeunload guard มีแล้ว — ใช้ pattern เดียวกันสำหรับ chunk progress
- **BACKLOG-008:** plan_limits.py ตอนนี้ testing mode (999999) — ค่าที่บอกใน plan นี้คือ "หลัง restore production"

### User decisions (จากการสนทนา)
| Q | คำตอบ |
|---|------|
| Q-A: Threshold "ไฟล์ใหญ่" | **30,000 chars** |
| Q-B: Bump size limit | **25/100MB** (free/starter), testing **200MB** |
| Q-C: Chunk overlap | **500 chars** |
| Q-D: ขยาย storage_limit_mb | คู่กับ BACKLOG-008 (ไม่ทำใน plan นี้) |
| Q-E: Map-reduce sync vs background | **background + polling** |
| Q-F: Big file นับ AI quota | **ครั้งเดียวต่อไฟล์** |
| Image OCR engine | **tesseract local** (ฟรี + มี dep แล้ว) |
| Pre-upload modal trigger | **เสมอเมื่อมี skip** |
| xlsx multi-sheet | **flatten** ทุก sheet เป็นไฟล์เดียว |
| Retry extraction | **re-run จาก raw_path เดิม** |

---

## 📁 Files to Create / Modify

### Backend
- [ ] `backend/extraction.py` (modify) — เพิ่ม image OCR + xlsx/pptx/html/json/rtf handlers + return `(text, status)` tuple
- [ ] `backend/text_chunker.py` (**create**) — smart chunk (heading → para → sentence → char)
- [ ] `backend/organizer.py` (modify) — `_generate_summary` รองรับ map-reduce mode
- [ ] `backend/main.py` (modify) — upload structured skip schema + retry endpoint extension + reprocess for big file
- [ ] `backend/config.py` (modify) — bump APP_VERSION → "7.5.0" + add `LARGE_FILE_THRESHOLD = 30000`
- [ ] `backend/database.py` (modify) — add columns: `extraction_status`, `chunk_count`, `is_truncated` + migration
- [ ] `backend/plan_limits.py` (modify — TESTING values only) — bump `max_file_size_mb` → 200, add `xlsx, pptx, html, json, rtf` ใน `allowed_file_types`
- [ ] `backend/duplicate_detector.py` (NO CHANGE — TF-IDF 2000-char query ยังทำงานได้กับไฟล์ใหญ่)

### Frontend
- [ ] `legacy-frontend/app.html` (modify) — modal `upload-result-modal` (per-file skip + success summary) + pre-upload preview modal + extraction badge + retry button
- [ ] `legacy-frontend/app.js` (modify) — `uploadFiles()` add pre-validation + `showUploadResultModal()` + `retryExtraction()` handler + extraction_status badge render
- [ ] `legacy-frontend/styles.css` (modify) — append .upload-result-modal + .extraction-badge styles
- [ ] เพิ่ม i18n keys (~30 keys × 2 langs) ใน app.js

### Tests
- [ ] `scripts/upload_resilience_e2e_verify.py` (**create**) — E2E test ครอบ 4 phase (image OCR / structured skip / big file chunking / new formats)
- [ ] Update `tests/test_production.py` — add new file size limit + extraction_status column
- [ ] Update `tests/e2e/*.spec.js` — Playwright spec สำหรับ pre-upload modal + retry button

### Dependencies (requirements.txt)
- [ ] `openpyxl` (~3MB) — xlsx
- [ ] `python-pptx` (~5MB) — pptx
- [ ] `beautifulsoup4` (อาจมีอยู่แล้วผ่าน Docling) — html
- [ ] `striprtf` (~50KB) — rtf
- [ ] tesseract binary — มีใน Fly.io image แล้วผ่าน Dockerfile (verify ก่อน)

---

## 📡 API Changes

### POST /api/upload (modify response)

**Request:** ไม่เปลี่ยน (multipart/form-data, `files: list[UploadFile]`)

**Response 200 (ใหม่):**
```json
{
  "uploaded": [...],   // unchanged
  "count": 5,
  "skipped": [
    {
      "filename": "report.xlsx",
      "code": "UNSUPPORTED_TYPE",
      "message": "ไฟล์ .xlsx ยังไม่รองรับ",
      "suggestion": "บันทึกเป็น CSV จาก Excel แล้วลองใหม่"
    },
    {
      "filename": "huge.pdf",
      "code": "FILE_TOO_LARGE",
      "message": "ไฟล์ใหญ่เกิน 200MB",
      "suggestion": "บีบอัดด้วย Smallpdf หรือแยกเป็นไฟล์ย่อย"
    }
  ]
}
```

**Skip codes:**
- `UNSUPPORTED_TYPE` — ext ไม่ใน allowed_types
- `FILE_TOO_LARGE` — exceeds plan limit
- `QUOTA_EXCEEDED` — file count limit
- `EMPTY_FILE` — 0 bytes (new check)

### POST /api/files/{file_id}/reprocess (extend)

**Current:** [main.py:859](../../backend/main.py#L859) re-run LLM cleanup only

**New:** เพิ่ม `mode` query param
- `mode=cleanup` (default, current behavior) — LLM text cleanup
- `mode=reextract` (new) — re-run extraction จาก raw_path (สำหรับ encrypted PDF ที่ปลดล็อกแล้ว user upload ทับใหม่ — actually need new endpoint, see below)
- `mode=resummarize` (new) — re-run map-reduce summary (สำหรับไฟล์เก่าที่ extract แล้วแต่ summary ตัดเนื้อหา)

**Errors:**
- 404 `FILE_NOT_FOUND`
- 400 `INVALID_MODE`
- 400 `RAW_PATH_MISSING` — ไฟล์เก่าที่ raw หาย (legacy)
- 503 `EXTRACTION_PENDING` — กำลัง process อยู่ (ป้องกัน double-trigger)

### GET /api/files/{file_id}/status (NEW — for big file polling)

**Response 200:**
```json
{
  "file_id": "...",
  "processing_status": "processing",
  "extraction_status": "ok",
  "chunk_count": 5,
  "chunks_processed": 3,    // for progress UI
  "is_truncated": false,
  "estimated_seconds_remaining": 15
}
```

ใช้ frontend polling ตอน big file map-reduce กำลังทำงาน (Q-E: background mode)

---

## 💾 Data Model Changes

### File table — เพิ่ม 3 columns

```python
# database.py — class File
extraction_status = Column(String, default="ok")
# values: ok | empty | encrypted | ocr_failed | unsupported | partial

chunk_count = Column(Integer, default=0)
# 0 = ไม่หั่น (ปกติ), >0 = ไฟล์ใหญ่ที่ map-reduce แล้ว

is_truncated = Column(Boolean, default=False)
# True = ไฟล์ใหญ่มาก เกินแม้ chunk แล้ว ตัดทิ้งบางส่วน
```

### Migration
- เพิ่มใน `database.py` migration block (ตามแบบเดียวกับ `content_hash` migration ที่ [database.py:627](../../backend/database.py#L627))
- Backfill existing files:
  - `extraction_status = "ok"` (assume เก่าทำงานได้)
  - `chunk_count = 0`, `is_truncated = False`
- Idempotent — ใช้ `IF NOT EXISTS` pattern เดิม

### plan_limits.py — TESTING values
```python
"free": {
    "max_file_size_mb": 200,  # was 100
    "allowed_file_types": {"pdf", "docx", "txt", "md", "csv", "png", "jpg",
                           "xlsx", "pptx", "html", "json", "rtf"},  # +5
    # อื่นๆ ไม่เปลี่ยน
},
"starter": { ... เหมือน free ตอน testing ... }
```

**Note สำหรับ BACKLOG-008:** production values ที่จะ restore ต้องมี:
- `free.max_file_size_mb`: เพิ่มจาก 10 → **25** (ตาม Q-B)
- `starter.max_file_size_mb`: เพิ่มจาก 20 → **100** (ตาม Q-B)
- `allowed_file_types`: ตาม testing mode ใหม่ (รวม xlsx etc.)

---

## 🔧 Step-by-Step Implementation

ทำตามลำดับ Phase 1 → Phase 4 → Phase 2 → Phase 3 (per user แดงแนะนำ)
แต่ละ phase = 1 commit + 1 test pass ก่อนไปต่อ

---

### **PHASE 1 — Fix Bugs (~2 ชม.)**

#### Step 1.1 — Image OCR
แก้ [backend/extraction.py](../../backend/extraction.py):

```python
def _extract_image_ocr(filepath: str) -> str:
    """OCR สำหรับ png/jpg/jpeg/webp ผ่าน pytesseract."""
    if not _HAS_OCR:
        return "[Image: OCR not available]"
    try:
        from PIL import Image
        img = Image.open(filepath)
        text = pytesseract.image_to_string(img, lang='tha+eng')
        if text and text.strip():
            return text.strip()
        return "[Image: no text detected]"
    except Exception as e:
        logger.error(f"Image OCR failed for {filepath}: {e}")
        return f"[OCR error: {str(e)}]"
```

แก้ `extract_text` เพิ่ม branch:
```python
elif filetype in ("png", "jpg", "jpeg", "webp"):
    return _extract_image_ocr(filepath)
```

#### Step 1.2 — Fix size error msg
แก้ [main.py:301](../../backend/main.py#L301):
```python
# เก่า:
skipped.append({"filename": original_name, "reason": f"ไฟล์ใหญ่เกิน {MAX_FILE_SIZE_MB}MB"})
# ใหม่:
skipped.append(_make_skip("FILE_TOO_LARGE", original_name, limit=_limits["max_file_size_mb"]))
```

#### Step 1.3 — Structured skip schema
เพิ่ม helper ใน main.py (ก่อน upload endpoint):
```python
SKIP_TEMPLATES = {
    "UNSUPPORTED_TYPE": {
        "message": "ไฟล์ .{ext} ยังไม่รองรับ",
        "suggestion": "ลองบันทึกเป็น PDF, Word, หรือ TXT แล้วอัปอีกครั้ง",
    },
    "FILE_TOO_LARGE": {
        "message": "ไฟล์ใหญ่เกิน {limit}MB",
        "suggestion": "บีบอัดด้วย Smallpdf หรือแยกเป็นไฟล์ย่อย",
    },
    "QUOTA_EXCEEDED": {
        "message": "ครบจำนวนไฟล์ที่เก็บได้แล้ว ({limit} ไฟล์)",
        "suggestion": "ลบไฟล์เก่าที่ไม่ใช้ หรืออัปเกรดแพลน",
    },
    "EMPTY_FILE": {
        "message": "ไฟล์ว่างเปล่า",
        "suggestion": "ตรวจว่าไฟล์ไม่เสียหายก่อนอัปใหม่",
    },
}

def _make_skip(code: str, filename: str, **fmt_args) -> dict:
    tpl = SKIP_TEMPLATES[code]
    return {
        "filename": filename,
        "code": code,
        "message": tpl["message"].format(**fmt_args),
        "suggestion": tpl["suggestion"],
    }
```

แก้ทุก `skipped.append({...})` ให้ใช้ helper

เพิ่ม **EMPTY_FILE check** ใน upload loop (หลัง read contents):
```python
if len(contents) == 0:
    skipped.append(_make_skip("EMPTY_FILE", original_name))
    continue
```

#### Step 1.4 — Frontend per-file skip UI
แก้ [app.html](../../legacy-frontend/app.html) เพิ่ม modal:
```html
<div id="upload-result-modal" class="modal-overlay" style="display:none">
  <div class="modal upload-result-modal">
    <div class="modal-header">
      <h3 id="upload-result-title">ผลการอัปโหลด</h3>
    </div>
    <div class="modal-body">
      <div id="upload-result-success" class="upload-result-section"></div>
      <div id="upload-result-skipped" class="upload-result-section"></div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-primary" id="upload-result-close" data-i18n="upload.understand">เข้าใจแล้ว</button>
    </div>
  </div>
</div>
```

แก้ [app.js:uploadFiles](../../legacy-frontend/app.js#L1247):
- ลบ `comma.join()` toast pattern
- เรียก `showUploadResultModal(uploaded, skipped)` แทน
- Function render: success count + per-skip card (icon + filename + message + suggestion)

#### Phase 1 Tests
1. Upload `test.png` ที่มี text → extracted_text มี content (OCR ทำงาน)
2. Upload `test.png` ภาพล้วนไม่มี text → extracted_text = `[Image: no text detected]`
3. Upload mixed batch (1 valid + 1 .xyz + 1 200MB + 1 0-byte) → response มี 4 skip codes
4. Upload `test.xlsx` → skip code `UNSUPPORTED_TYPE` (ก่อน Phase 3 ถึงจะรองรับ)
5. Frontend: upload mix → modal ขึ้น แสดง success + per-file skip
6. Verify error msg แสดง "200MB" (ไม่ใช่ "10MB")

---

### **PHASE 4 — Big File Support (~4-5 ชม.)**

#### Step 4.1 — Smart text chunker
สร้าง [backend/text_chunker.py](../../backend/text_chunker.py) (ไฟล์ใหม่):

```python
"""Smart text chunker for big-file map-reduce processing.

Strategy (in order):
1. Markdown headings (`#`, `##`, `###`) — Docling output มี structure
2. Double newline (paragraph boundary)
3. Sentence boundary (. ! ? ฯลฯ)
4. Hard char split (last resort)

Target chunk size: ~10K chars + overlap 500 chars
"""
import re
from typing import List

CHUNK_SIZE = 10_000      # target chars per chunk
CHUNK_OVERLAP = 500      # gun context loss ที่ขอบ
MIN_CHUNK_SIZE = 2_000   # chunk เล็กกว่านี้รวมกับ chunk ถัดไป

def chunk_text(text: str) -> List[str]:
    """หั่น text เป็น chunks ขนาด ~10K chars + overlap 500"""
    if len(text) <= CHUNK_SIZE:
        return [text]
    # Try heading split first
    chunks = _split_by_heading(text)
    if all(len(c) <= CHUNK_SIZE * 1.5 for c in chunks):
        return _add_overlap(chunks)
    # Fall back to paragraph split
    chunks = _split_by_paragraph(text)
    if all(len(c) <= CHUNK_SIZE * 1.5 for c in chunks):
        return _add_overlap(chunks)
    # Hard char split
    return _hard_split(text, CHUNK_SIZE, CHUNK_OVERLAP)

# implementation details ใน build phase
```

#### Step 4.2 — Map-reduce summary
แก้ [backend/organizer.py:_generate_summary](../../backend/organizer.py#L249):

```python
async def _generate_summary(file: File, cluster_title: str, importance: dict) -> dict:
    text = file.extracted_text or ""
    if len(text) <= LARGE_FILE_THRESHOLD:  # 30K
        return await _generate_summary_simple(file, cluster_title, importance)
    return await _generate_summary_mapreduce(file, cluster_title, importance)


async def _generate_summary_mapreduce(file, cluster_title, importance) -> dict:
    """หั่น → summarize ทุก chunk → merge เป็น final summary"""
    from .text_chunker import chunk_text
    chunks = chunk_text(file.extracted_text)
    file.chunk_count = len(chunks)

    # Map: per-chunk mini-summary
    mini_summaries = []
    for i, chunk in enumerate(chunks):
        logger.info(f"Map-reduce {file.filename}: chunk {i+1}/{len(chunks)}")
        mini = await _summarize_chunk(chunk, file.filename, i+1, len(chunks))
        mini_summaries.append(mini)

    # Reduce: merge into final
    return await _merge_summaries(mini_summaries, file.filename, cluster_title, importance)
```

#### Step 4.3 — DB migration (extraction_status / chunk_count / is_truncated)
แก้ [database.py:File](../../backend/database.py) + add migration ในรูปแบบเดียวกับ content_hash

#### Step 4.4 — Bump size limits
แก้ [plan_limits.py:17-42](../../backend/plan_limits.py#L17-L42):
- `max_file_size_mb`: 100 → 200 (testing mode)
- เพิ่ม xlsx/pptx/html/json/rtf ใน `allowed_file_types` (สำหรับ Phase 3)

แก้ [config.py:21](../../backend/config.py#L21):
- เก็บ `MAX_FILE_SIZE_MB` ไว้เป็น emergency hard cap (= 200) — ใช้ตอน plan_limits ยังโหลดไม่เสร็จ

#### Step 4.5 — Background task + status polling
แก้ organize-new endpoint:
- ถ้าไฟล์ใดๆ extracted_text > LARGE_FILE_THRESHOLD → run organize ใน `background_tasks.add_task()` แทน inline
- Frontend polling ผ่าน `GET /api/files/{file_id}/status` ทุก 3 วินาที จนกว่า `processing_status == "ready"`
- Modal "กำลังวิเคราะห์ไฟล์ใหญ่... (3/10 ส่วน)" + progress bar

#### Step 4.6 — File card badge (Frontend)
ใน file list render — ถ้า `chunk_count > 0`:
```html
<span class="file-badge file-badge-chunks">📚 {chunk_count} ส่วน</span>
```
ถ้า `is_truncated`:
```html
<span class="file-badge file-badge-warn">⚠️ บางส่วนถูกตัด</span>
```

#### Phase 4 Tests
1. Upload PDF 200 หน้า (~150K chars) → success + chunk_count = 10 (~15K chars/chunk)
2. Summary ของไฟล์ใหญ่ → มีเนื้อหาจาก หน้า 1 + หน้า 100 + หน้า 200 (ไม่ใช่แค่หน้าแรก)
3. Chat ถาม "เนื้อหาในส่วนกลางบอกอะไร" → answer มาจาก chunk 5 ไม่ใช่ chunk 1
4. Cost test: upload 5 ไฟล์ใหญ่ → AI summary count = 5 (ไม่ใช่ 50)
5. UI: badge `📚 10 ส่วน` ขึ้นที่ file card
6. Polling: upload ไฟล์ใหญ่ → modal "(3/10 ส่วน)" update real-time
7. Error: chunk 5 LLM error → final status = "ready" + is_truncated badge + summary บอก "ส่วนที่ 5 อ่านไม่ได้"

---

### **PHASE 2 — Proactive UX (~3 ชม.)**

#### Step 2.1 — Pre-upload validation modal (client-side)
แก้ [app.js:uploadFiles](../../legacy-frontend/app.js#L1247) — ก่อน FormData append:
- Loop ตรวจ ext + size client-side
- ถ้ามี skip-able → ขึ้น `pre-upload-preview-modal` แสดง list "✅ จะอัป N ไฟล์ / ⚠️ ข้าม M ไฟล์"
- ปุ่ม "อัปโหลด {N} ไฟล์" / "ยกเลิก"
- ถ้าทุกไฟล์ผ่าน → silently proceed (ไม่ขึ้น modal)
- Use API `GET /api/usage` ที่มีอยู่ ([main.py:get_usage_summary]) เพื่อดึง allowed_types + max_file_size_mb (single source of truth)

#### Step 2.2 — Encrypted/empty/corrupted detection
แก้ [extraction.py](../../backend/extraction.py) — เปลี่ยน return type จาก `str` เป็น `tuple[str, str]`:
```python
def extract_text(filepath, filetype) -> tuple[str, str]:
    """Returns (text, status). status ∈ {ok, empty, encrypted, ocr_failed, unsupported}"""
```

PDF check encrypted ก่อน:
```python
from PyPDF2 import PdfReader
reader = PdfReader(filepath)
if reader.is_encrypted:
    return ("", "encrypted")
```

ทุก caller ของ `extract_text` ต้อง unpack tuple — แก้ใน:
- [main.py:308](../../backend/main.py#L308) — upload endpoint
- [main.py:866](../../backend/main.py#L866) — reprocess endpoint

#### Step 2.3 — Retry extraction button
- File card: ถ้า `extraction_status != "ok"` → badge + ปุ่ม "ลองอ่านใหม่"
- Click → `POST /api/files/{id}/reprocess?mode=reextract`
- Backend: re-run `extract_text(raw_path, filetype)` → update extracted_text + extraction_status + content_hash

#### Step 2.4 — extraction_status badge UI
i18n strings:
```js
'extract.status.empty': 'ไม่มีข้อความในไฟล์',
'extract.status.encrypted': 'ไฟล์ติดรหัสผ่าน — ปลดล็อกก่อนอัปใหม่',
'extract.status.ocr_failed': 'อ่านข้อความจากรูปไม่ออก',
'extract.status.unsupported': 'ไฟล์นี้ระบบยังอ่านไม่ได้',
'extract.retry': 'ลองอ่านใหม่',
```

#### Phase 2 Tests
1. Drop 5 ไฟล์ (3 valid + 2 .exe) → pre-upload modal ขึ้น "อัป 3 / ข้าม 2"
2. Upload encrypted PDF → extraction_status = "encrypted" + badge แสดง
3. Click "ลองอ่านใหม่" → re-trigger extraction
4. Upload empty .txt → extraction_status = "empty"

---

### **PHASE 3 — More Formats (~3 ชม.)**

#### Step 3.1 — xlsx via openpyxl
```python
def _extract_xlsx(filepath: str) -> str:
    from openpyxl import load_workbook
    wb = load_workbook(filepath, data_only=True, read_only=True)
    sections = []
    for sheet in wb.worksheets:
        sections.append(f"# Sheet: {sheet.title}")
        rows = []
        for row in sheet.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(cells):
                rows.append("| " + " | ".join(cells) + " |")
        if rows:
            sections.append("\n".join(rows))
    return "\n\n".join(sections) if sections else "[Empty workbook]"
```

#### Step 3.2 — pptx via python-pptx
ดึง text + speaker notes ทุก slide

#### Step 3.3 — html via BeautifulSoup
```python
from bs4 import BeautifulSoup
soup = BeautifulSoup(content, 'html.parser')
for tag in soup(['script', 'style']):  # security
    tag.decompose()
return soup.get_text(separator='\n', strip=True)
```

#### Step 3.4 — json/rtf
- json: `json.dumps(json.load(f), indent=2, ensure_ascii=False)`
- rtf: `striprtf.striprtf(content)`

#### Phase 3 Tests
1. Upload .xlsx 3 sheets → cluster + summary มีข้อมูลทุก sheet
2. Upload .pptx 20 slides → summary มี speaker notes
3. Upload .html (export from Notion) → text สะอาด ไม่มี script/style
4. Upload .json (config file) → preserve structure

---

## 🧪 Test Scenarios (สำหรับฟ้า / E2E)

### Happy Path
1. Upload mixed batch (pdf, docx, png, txt, xlsx) → all success
2. Upload big PDF 150K chars → chunk_count > 0, summary ครบทุกส่วน
3. Upload duplicate (exact + semantic) → dedupe modal ทำงาน (regression v7.1.5)

### Validation Errors
- Empty file (0 bytes) → `EMPTY_FILE` skip code
- File > 200MB → `FILE_TOO_LARGE`
- .exe / .zip → `UNSUPPORTED_TYPE`
- Quota exceeded → `QUOTA_EXCEEDED`

### Edge Cases
- Encrypted PDF → extraction_status = "encrypted"
- Corrupted PDF → extraction_status = "ocr_failed" or partial
- Image-only PDF without OCR available → ocr_failed
- xlsx with formula → ดึง value (data_only=True)
- HTML with `<script>` → strip ออก ไม่ leak ไป LLM
- Big file ที่ chunk 5/10 LLM error → is_truncated=True, ไฟล์อื่นๆ ยัง ready

### Regression
- v7.1.5 dedupe modal ทำงาน
- v7.2.0 upload progress bar ทำงาน
- v7.3.0 mobile responsive ไม่พัง
- v7.4.0 file card view (mobile) ไม่พัง
- BYOS push raw + extracted ทำงาน (Drive sync ปกติ)

### Cost / Performance
- Upload 5 ไฟล์ใหญ่ → AI summary log = 5 entries (per-file count)
- Big file extraction time ≤ 60 วิ (Fly.io HTTP timeout)
- Memory: ไม่ OOM ที่ Fly.io 1024MB กับไฟล์ 100MB PDF

---

## ✅ Done Criteria

### Phase 1
- [ ] Upload .png/.jpg → extracted_text มี content จริง (OCR)
- [ ] Skip modal แสดงต่อไฟล์ พร้อม suggestion
- [ ] Error msg size แสดง limit ถูกต้อง (200MB ตอน testing)
- [ ] Empty file detect + EMPTY_FILE code
- [ ] E2E mixed batch test pass

### Phase 4
- [ ] Upload 100MB PDF → success, raw เก็บครบ
- [ ] PDF 300 หน้า → chunk_count > 0 + summary มีเนื้อหาจาก chapter ทุกส่วน
- [ ] Files page badge `📚 N ส่วน` แสดง
- [ ] Chat retrieval ตอบจาก chunk กลาง/ท้ายไฟล์ได้
- [ ] Reprocess `mode=resummarize` re-run map-reduce
- [ ] Cost: 5 big files = AI summary count 5

### Phase 2
- [ ] Pre-upload preview ขึ้นเมื่อมีไฟล์ skip-able
- [ ] extraction_status column + migration idempotent
- [ ] Encrypted PDF detect + actionable badge
- [ ] Retry extraction button ทำงานบนไฟล์ extract พัง

### Phase 3
- [ ] xlsx/pptx/html/json/rtf upload + organize ผ่าน
- [ ] allowed_types frontend + backend sync ตรงกัน

### ระดับ Plan
- [ ] APP_VERSION bump → "7.5.0"
- [ ] All regression suites pass (byos × 5 + rebrand_smoke + dedupe_e2e_verify + new upload_resilience_e2e_verify)
- [ ] No new security issues (HTML script strip + path traversal still defended)
- [ ] requirements.txt updated + Fly.io deploy ready

---

## ⚠️ Risks / Open Questions

### Risks (mitigation วางไว้แล้ว)
1. **Memory blow-up ที่ Fly.io 1024MB ตอน extract 200MB PDF** — Docling โหลด RAM
   - Mitigation: stream-based ไม่ได้ในทันที — เพิ่ม `if file_size > 100MB: warn user "อาจช้า"` modal + monitor Fly.io memory metric หลัง deploy
   - Fallback: ลด hard cap เป็น 100MB ถ้าเจอ OOM
2. **Map-reduce timeout** — 10 chunks × 5s = 50s + LLM overhead → อาจ > 60s HTTP timeout
   - Mitigation: Q-E ตัดสินแล้ว = background task + polling endpoint
3. **Cost predictability** — user upload 100 ไฟล์ใหญ่ = ~$1
   - Mitigation: Q-F ตัดสินแล้ว = นับ 1 quota/ไฟล์ (ไม่ใช่ตาม chunk)
4. **HTML script injection ไป LLM** — XSS-style data exfiltration
   - Mitigation: BeautifulSoup `for tag in soup(['script','style']): tag.decompose()` ก่อน get_text
5. **Tesseract binary หาย ใน Fly.io image** — image OCR fail
   - Mitigation: Phase 1.1 verify Dockerfile installs tesseract + tessdata-tha — ถ้าไม่มี ต้อง add `RUN apt-get install -y tesseract-ocr tesseract-ocr-tha`
6. **Backward compat** — ไฟล์เก่าที่ extract truncated 6K chars
   - Mitigation: ไม่ auto-resummarize — user ใช้ "Reprocess (resummarize)" button เลือกเอง
7. **Chunk overlap = duplicate text in vector index** — อาจเพิ่ม noise
   - Mitigation: 500 chars overlap = 5% ของ chunk 10K = noise เล็กน้อย acceptable

### Open Questions ที่ตัดสินแล้ว ✅
ทุก Q-A ถึง Q-F + 4 sub-q user approve "ตามที่แดงแนะนำ" 2026-05-02

### ยังเปิดสำหรับ build phase
- **Q-G:** Phase 4 ทำเสร็จแล้ว ส่ง progress polling แบบไหน?
   - ง่าย: 3-วิ polling (ทำ Q-E สั่ง)
   - ดี: Server-Sent Events
   - ผมเลือกง่ายก่อน — **3-วิ polling** ตามแบบของ existing organize spinner
- **Q-H:** Reprocess endpoint — ใช้ JWT user auth เดิม หรือต้อง check ownership ซ้ำ?
   - ใช้ pattern เดียวกับ skip-duplicates ([main.py:980](../../backend/main.py#L980)) → query File where user_id = current_user.id

---

## 📌 Notes for นักพัฒนา (เขียว)

### Convention ที่ต้องรักษา
1. **Path traversal defense** — ใช้ `os.path.basename()` กับทุก attacker-supplied filename เหมือน [main.py:278](../../backend/main.py#L278)
2. **MIME validation** — ใช้ `_guess_mime()` ที่มีอยู่ ([main.py:378](../../backend/main.py#L378)) — อย่า trust Content-Type header
3. **BYOS background push** — ทุก endpoint ที่สร้าง/แก้ raw file ต้อง schedule push to Drive ผ่าน `pending_drive_pushes` pattern
4. **Per-user isolation** — ทุก vector_search call ต้อง pass `user_id` (DUP-002 lesson)
5. **Best-effort errors** — Drive push / vector index ห้าม raise — log + swallow (DB = source of truth)

### Gotchas
1. **`extraction_status` migration** — backfill `"ok"` กับ existing files ที่จริงๆ extract พัง → user จะไม่เห็น badge จนกว่าจะ reprocess. ตั้งใจให้เป็นแบบนี้ (ไม่อยาก trigger mass-reprocess)
2. **`extract_text` return signature เปลี่ยน** ใน Phase 2 — ต้องแก้ทุก caller (มี 2 จุด: upload + reprocess) อย่าลืม
3. **chunk_text overlap** — ใช้ตัด `chunks[i+1] = chunks[i].endswith(N_chars) + chunks[i+1]` — อย่าทำ overlap แบบ strict slicing เพราะอาจตัดกลางคำ
4. **Map-reduce LLM call** — ใช้ `LLM_MODEL` (Flash) สำหรับ chunk summary, `LLM_MODEL_PRO` (ตอนนี้ก็ Flash จาก [config.py:18](../../backend/config.py#L18)) สำหรับ merge — แต่ Flash ทำได้หมด
5. **Big file detection trigger** — เช็คที่ `len(extracted_text) > LARGE_FILE_THRESHOLD` ไม่ใช่ raw file size — สำคัญ! 5MB PDF อาจมี 100K chars
6. **Upload flow order** — extract → check empty → check too large (ขนาด extracted_text? ขนาด raw?) → save DB → schedule Drive
   - **Decision:** ขนาด raw bytes ถูก check ก่อน save (existing) — Phase 4 ไม่เปลี่ยน flow ตรงนี้
7. **Reprocess pre-existing files** — ก่อน Phase 4: summary ตัด 6K chars. หลัง Phase 4: button "Reprocess (resummarize)" จะ run map-reduce — แต่ user ต้อง trigger เอง (ไม่ auto)

### Test ก่อน commit
แต่ละ Phase commit ต้องผ่าน:
```bash
python scripts/upload_resilience_e2e_verify.py     # ใหม่ใน plan นี้
python scripts/dedupe_e2e_verify.py                # regression v7.1.5
python -m pytest tests/test_production.py          # backend regression
python tests/e2e/playwright/...                    # frontend regression (ถ้ามี time)
```

### Pipeline state ที่จะ update
ก่อนเริ่ม build:
- pipeline-state.md → state = `building`
- เพิ่ม v7.5.0 ใน "Current Pipeline State" section

หลัง build เสร็จ:
- ถ้า single-agent 3-in-1 mode (เหมือน v7.1.5) → state = `done` หลัง self-review pass
- ถ้า handoff to ฟ้า → state = `built_pending_review`

---

## 📌 Defer (Out of Scope สำหรับ v7.5.0)

ทำใน v7.5.x หรือ v7.6+:
- ❌ doc (legacy Word) — antiword + libreoffice ผ่อนแรง, niche
- ❌ heic (iPhone photo) — user แปลงเอง, niche
- ❌ zip extract — security + UX ซับซ้อน
- ❌ audio/video transcription (Whisper API) — cost concern
- ❌ Server-Sent Events progress (Q-G) — ใช้ 3-วิ polling พอใน MVP
- ❌ Background re-extraction queue (auto-retry failed files) — ต้อง Celery/RQ
- ❌ Production plan_limits restore (BACKLOG-008) — แยก ticket
- ❌ Storage quota expansion (Q-D) — แยก ticket คู่กับ BACKLOG-008
- ❌ Dedupe TF-IDF query window > 2000 chars สำหรับ big files — Phase 5

---

## 🧪 Test Plan per Milestone (4-Layer Coverage)

### หลักการ
ทุก phase ต้องผ่าน **4 layers** ก่อน mark done — backend อย่างเดียวไม่พอ ต้องเทสหน้าเว็บจริงบน browser ด้วย

```
Layer 1: Backend pytest (unit + integration)
   ↓ pass
Layer 2: Backend E2E TestClient (FastAPI in-process, full HTTP flow)
   ↓ pass
Layer 3: Frontend Playwright (real Chromium, real DOM, real fetch)
   ↓ pass
Layer 4: Manual visual smoke (human ตรวจตา on real browser)
   ↓ pass
=== Phase ship ===
```

### Test Infrastructure (มีอยู่แล้ว — reuse pattern)

| Layer | Tool | Location | Pattern อ้างอิง |
|------|------|---------|---------|
| 1 — pytest | `pytest` | `tests/test_*.py` | [test_production.py](../../tests/test_production.py) |
| 2 — Backend E2E | FastAPI TestClient | `scripts/*_e2e_verify.py` | [dedupe_e2e_verify.py](../../scripts/dedupe_e2e_verify.py) |
| 3 — Playwright | `@playwright/test` Chromium | `tests/e2e-ui/v*.spec.js` | [v7.4.0-saas-responsive.spec.js](../../tests/e2e-ui/v7.4.0-saas-responsive.spec.js) + [fixtures/auth.js](../../tests/e2e-ui/fixtures/auth.js) `registerAndEnterApp(page)` |
| 4 — Manual | Real Chrome/Safari/iPhone | checklist | 8 visual screenshots from v7.3.0 pattern |

### Test Files to Create

**Backend:**
- `tests/test_extraction_v750.py` (**ใหม่**) — unit: image OCR + format handlers + tuple return
- `tests/test_text_chunker.py` (**ใหม่**) — unit: smart chunking strategies
- `tests/test_upload_resilience_v750.py` (**ใหม่**) — integration: skip schema + reprocess endpoint + migration
- `scripts/upload_resilience_e2e_verify.py` (**ใหม่**) — Backend E2E (4 sections, ~50 cases)

**Frontend:**
- `tests/e2e-ui/v7.5.0-upload-resilience.spec.js` (**ใหม่**) — Playwright per-phase tests (~25 tests)
- `tests/e2e-ui/v7.5.0-visual.spec.js` (**ใหม่**) — visual screenshots (modal states, badges)

**Test fixtures (pre-generate, commit to repo):**
- `tests/fixtures/upload_samples/` (**dir ใหม่**)
  - `sample.png` — PNG with Thai+EN text
  - `sample_blank.png` — blank image (no text)
  - `sample_xss.png` — image with text "alert(1)" (XSS-style content test)
  - `encrypted.pdf` — password-protected
  - `empty.pdf` — 0-byte (or PDF with no text content)
  - `big_text.pdf` — ~200K chars lorem ipsum (test chunker)
  - `big_thai.pdf` — Thai content ~100K chars
  - `sample.xlsx` — 3 sheets + formulas + mixed data
  - `sample.pptx` — 5 slides + speaker notes
  - `sample_safe.html` — clean HTML export
  - `sample_xss.html` — with `<script>alert(1)</script>` (security test)
  - `sample.json` — nested config
  - `sample.rtf` — basic rich text

---

### Phase 1 Tests — Fix Bugs (~40 cases)

#### Layer 1: pytest (`tests/test_extraction_v750.py` + `test_upload_resilience_v750.py`)
```python
# Image OCR
def test_extract_image_with_text(): assert extract_text("sample.png", "png").strip()
def test_extract_image_blank(): assert extract_text("blank.png", "png") == "[Image: no text detected]"
def test_extract_image_ocr_unavailable_fallback(monkeypatch): ...
def test_extract_image_corrupt_returns_error_marker(): ...

# Skip schema
def test_skip_template_unsupported(): assert _make_skip("UNSUPPORTED_TYPE", "x.xyz", ext="xyz") == {...}
def test_skip_template_too_large(): ...
def test_skip_template_empty(): ...
def test_skip_template_quota(): ...
def test_skip_unknown_code_raises_keyerror(): ...

# Empty file detection
def test_upload_empty_file_returns_empty_skip(): ...
```

#### Layer 2: Backend E2E (`scripts/upload_resilience_e2e_verify.py` Section A)
```python
# Section A — Phase 1 fixes
expect_true("A.1 png upload + OCR extracts text", _upload_png_returns_extracted())
expect_true("A.2 jpg upload + OCR extracts text", ...)
expect_true("A.3 mixed batch — 1 valid + 1 .xyz + 1 200MB + 1 empty", ...)
expect_true("A.4 skip array contains UNSUPPORTED_TYPE for .xyz")
expect_true("A.5 skip array contains FILE_TOO_LARGE with limit=200")
expect_true("A.6 skip array contains EMPTY_FILE for 0-byte")
expect_true("A.7 size error msg shows 200MB (not 10MB)")
expect_true("A.8 each skip has {filename, code, message, suggestion}")
```

#### Layer 3: Playwright (`tests/e2e-ui/v7.5.0-upload-resilience.spec.js`)
```javascript
test.describe("v7.5.0 / Phase1 / Upload Result Modal", () => {
  test("png upload appears in file list with extracted text", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.setInputFiles('input[type=file]', 'tests/fixtures/upload_samples/sample.png');
    await page.waitForSelector('.file-item', { timeout: 15000 });
    // verify file appears + has filetype badge
  });

  test("unsupported file → upload-result-modal opens with skip card", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.setInputFiles('input[type=file]', 'tests/fixtures/upload_samples/sample.xyz');
    await expect(page.locator('#upload-result-modal')).toBeVisible();
    await expect(page.locator('.skip-card')).toContainText('ยังไม่รองรับ');
    await expect(page.locator('.skip-card')).toContainText('ลองบันทึกเป็น'); // suggestion
  });

  test("mixed batch → modal shows success + per-file skip", async ({ page }) => { ... });
  test("EMPTY_FILE 0-byte → specific code badge", async ({ page }) => { ... });
  test("size error shows 200MB not 10MB", async ({ page }) => { ... });
  test("modal close button dismisses", async ({ page }) => { ... });
});
```

#### Layer 4: Manual smoke checklist
- [ ] Drag .heic จาก iPhone photo → modal บอก "ยังไม่รองรับ" + suggestion
- [ ] Drag photo รายการอาหารภาษาไทย → OCR ดึงข้อความได้ถูกต้อง (เช็คตา)
- [ ] Drag empty .txt → "ไฟล์ว่างเปล่า" badge
- [ ] DevTools console: ไม่มี error สีแดงตลอด upload flow

---

### Phase 4 Tests — Big File (~50 cases)

#### Layer 1: pytest (`tests/test_text_chunker.py`)
```python
# Chunker correctness
def test_chunk_small_text_no_split(): assert chunk_text("a"*10000) == ["a"*10000]
def test_chunk_heading_based(): chunks = chunk_text(MARKDOWN_WITH_3_HEADINGS); assert len(chunks) == 3
def test_chunk_paragraph_fallback_when_no_heading(): ...
def test_chunk_hard_split_oversized_paragraph(): ...
def test_chunk_overlap_500_chars(): assert chunks[1].startswith(chunks[0][-500:])
def test_chunk_min_size_merge_with_next(): ...
def test_chunk_target_size_within_50_percent_tolerance(): ...

# Map-reduce
@pytest.mark.asyncio
async def test_map_reduce_calls_llm_n_plus_one(monkeypatch): ...
async def test_map_reduce_aggregates_key_topics_dedupe(): ...
async def test_map_reduce_partial_failure_sets_is_truncated(): ...
async def test_map_reduce_quota_counted_once_not_per_chunk(): ...

# DB migration
async def test_migration_adds_extraction_status_column(): ...
async def test_migration_backfills_existing_files_to_ok(): ...
async def test_migration_idempotent_on_rerun(): ...
```

#### Layer 2: Backend E2E (`scripts/upload_resilience_e2e_verify.py` Section B)
```python
# Section B — Big File
expect_true("B.1 upload 200K-char PDF → chunk_count > 0")
expect_true("B.2 chunk_count matches len(chunks)")
expect_true("B.3 summary contains content from chunk[0], chunk[mid], chunk[-1]")
expect_true("B.4 vector_search.hybrid_search('content from chunk[5]') returns chunk 5 file")
expect_true("B.5 raw_path file size matches uploaded bytes (no truncation of raw)")
expect_true("B.6 cost check — 5 big uploads = 5 AI summary log entries")
expect_true("B.7 GET /api/files/{id}/status returns chunks_processed during organize")
expect_true("B.8 reprocess mode=resummarize re-runs map-reduce")
expect_true("B.9 reprocess preserves chunk_count")
expect_true("B.10 partial failure → is_truncated=True + processing_status=ready")
```

#### Layer 3: Playwright (Phase 4 spec section)
```javascript
test.describe("v7.5.0 / Phase4 / Big File", () => {
  test("upload big PDF → progress modal shows chunk count", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.setInputFiles('input[type=file]', 'tests/fixtures/upload_samples/big_text.pdf');
    await page.click('#btn-organize-new');
    // Poll for progress modal
    await expect(page.locator('.big-file-progress')).toBeVisible({ timeout: 5000 });
    await expect(page.locator('.big-file-progress')).toContainText(/\d+\/\d+ ส่วน/);
    // Wait for completion
    await page.waitForSelector('.file-item .file-badge-chunks', { timeout: 90000 });
  });

  test("file card shows chunk badge after big-file organize", async ({ page }) => {
    // ... upload + organize
    await expect(page.locator('.file-badge-chunks')).toContainText('ส่วน');
  });

  test("chat retrieval finds content from middle chunk", async ({ page }) => {
    // upload big file with known content at position 50% → chat → verify answer cites that chunk
  });

  test("mobile big-file UI doesn't break card view", async ({ page }) => {
    page.setViewportSize({ width: 375, height: 667 });
    // ... regression: badge still readable on mobile
  });

  test("polling stops after status=ready", async ({ page }) => {
    let pollCount = 0;
    await page.route("**/api/files/*/status", async (route) => {
      pollCount++;
      await route.fulfill({ status: 200, body: JSON.stringify({ processing_status: "ready" }) });
    });
    // ... trigger organize, wait, verify poll stopped
  });
});
```

#### Layer 4: Manual smoke
- [ ] Upload War & Peace .txt (~3MB text) → wait organize → ตรวจ summary มีเนื้อหาจาก ch1 + ch10 + ch-last
- [ ] เปิด Fly.io metrics → upload 100MB PDF → memory peak ≤ 700MB (กัน OOM)
- [ ] Network tab: status polling ทุก 3 วิ จริง
- [ ] หลัง organize เสร็จ: เปิด file detail → เห็น "เนื้อหา 10 ส่วน" section

---

### Phase 2 Tests — Proactive UX (~30 cases)

#### Layer 1: pytest
```python
# extract_text returns tuple
def test_extract_text_returns_tuple_for_all_branches(): ...
def test_extract_pdf_encrypted_returns_encrypted_status(): ...
def test_extract_pdf_empty_returns_empty_status(): ...
def test_extract_image_no_text_returns_ocr_failed_status(): ...

# Migration
async def test_migration_extraction_status_column_idempotent(): ...
async def test_migration_does_not_change_existing_data(): ...

# Reprocess endpoint
async def test_reprocess_mode_reextract_updates_status(): ...
async def test_reprocess_returns_404_for_missing_file(): ...
async def test_reprocess_returns_403_for_other_users_file(): ...
async def test_reprocess_invalid_mode_returns_400(): ...
```

#### Layer 2: Backend E2E (Section C)
```python
expect_true("C.1 upload encrypted.pdf → File.extraction_status = encrypted")
expect_true("C.2 upload empty PDF → status = empty")
expect_true("C.3 reprocess mode=reextract updates extracted_text + status")
expect_true("C.4 reprocess preserves file_id (no new row)")
expect_true("C.5 cross-user reprocess returns 403")
expect_true("C.6 migration backfills existing files to status=ok")
```

#### Layer 3: Playwright
```javascript
test.describe("v7.5.0 / Phase2 / Proactive UX", () => {
  test("pre-upload preview modal shows skip-able files", async ({ page }) => {
    await registerAndEnterApp(page);
    // Set 5 files (3 valid + 2 .xyz)
    await page.setInputFiles('input[type=file]', [
      'sample.png', 'sample.pdf', 'sample.txt', 'sample.xyz', 'sample.exe'
    ]);
    await expect(page.locator('#pre-upload-preview-modal')).toBeVisible();
    await expect(page.locator('#pre-upload-valid-count')).toContainText('3');
    await expect(page.locator('#pre-upload-skip-count')).toContainText('2');
  });

  test("pre-upload all valid → no modal, silent proceed", async ({ page }) => { ... });

  test("encrypted PDF → file card shows lock badge + suggestion", async ({ page }) => {
    // upload encrypted.pdf → wait organize → verify badge "🔒 ปลดล็อกก่อนอัปใหม่"
  });

  test("retry button triggers reextract endpoint", async ({ page }) => {
    let reextractCalled = false;
    await page.route("**/api/files/*/reprocess?mode=reextract", async (route) => {
      reextractCalled = true;
      await route.fulfill({ status: 200, body: JSON.stringify({ extraction_status: "ok" }) });
    });
    // upload encrypted → click "ลองอ่านใหม่" button
    expect(reextractCalled).toBe(true);
  });

  test("badge i18n EN switch shows English text", async ({ page }) => { ... });
});
```

#### Layer 4: Manual smoke
- [ ] เอา PDF ใส่รหัสด้วย Smallpdf → upload → เห็น 🔒 badge
- [ ] ปลด password → upload ใหม่ทับ → เห็น badge หาย
- [ ] empty .txt (touch zero-byte) → "ไม่มีข้อความในไฟล์"

---

### Phase 3 Tests — More Formats (~40 cases)

#### Layer 1: pytest (security-critical)
```python
def test_extract_xlsx_3_sheets_flatten(): assert "Sheet: Q1" in result and "Sheet: Q2" in result
def test_extract_xlsx_formula_data_only_returns_value(): ...
def test_extract_xlsx_empty_workbook_returns_marker(): ...
def test_extract_pptx_includes_speaker_notes(): assert "[NOTES]" in result
def test_extract_pptx_preserves_slide_order(): ...

# Security: HTML must strip script/style
def test_extract_html_removes_script_tag(): assert "<script>" not in result and "alert" not in result
def test_extract_html_removes_style_tag(): ...
def test_extract_html_xss_payload_neutralized(): ...
def test_extract_html_preserves_heading_hierarchy(): ...

def test_extract_json_valid_pretty_printed(): ...
def test_extract_json_malformed_returns_error_marker(): ...

def test_extract_rtf_strips_control_codes(): assert "\\f0" not in result
```

#### Layer 2: Backend E2E (Section D)
```python
expect_true("D.1 upload sample.xlsx → success + extracted has all 3 sheets")
expect_true("D.2 upload sample.pptx → extracted has all slides + notes")
expect_true("D.3 upload sample_xss.html → extracted has NO <script> or 'alert' string")
expect_true("D.4 upload sample.json → extracted is pretty-printed JSON")
expect_true("D.5 upload sample.rtf → extracted is plain text")
expect_true("D.6 frontend allowed_types via /api/usage includes xlsx, pptx, html, json, rtf")
expect_true("D.7 .doc still rejected as UNSUPPORTED_TYPE (not in allowed_types)")
```

#### Layer 3: Playwright
```javascript
test.describe("v7.5.0 / Phase3 / Formats", () => {
  test("xlsx upload → organize creates summary", async ({ page }) => { ... });
  test("pptx upload → file appears with .pptx filetype badge", async ({ page }) => { ... });
  test("xss html → no script in extracted_text", async ({ page }) => {
    // upload sample_xss.html → fetch /api/files/{id} → verify extracted_text does NOT contain "alert(1)"
  });
  test("pre-upload preview accepts xlsx (not in skip list)", async ({ page }) => { ... });
});
```

#### Layer 4: Manual smoke
- [ ] เอา Excel ของจริงจากที่ทำงาน upload → ดู summary capture ข้อมูลครบ sheet
- [ ] PowerPoint slide deck พร้อม notes → ตรวจ notes ขึ้น summary
- [ ] HTML export from Notion → ตรวจ no <style> leak ไป summary

---

### Regression Suites (must pass after EACH phase)

```bash
# Backend regression (existing — must stay passing)
python scripts/dedupe_e2e_verify.py            # 55/55
python scripts/byos_foundation_verify.py        # 26/26
python scripts/byos_storage_verify.py           # 20/20
python scripts/byos_sync_verify.py              # 24/24
python scripts/byos_oauth_verify.py             # 20/20
python scripts/byos_router_verify.py            # 16/16
python scripts/rebrand_smoke.py                 # 77/77
python -m pytest tests/test_production.py       # ~52 cases

# Frontend regression (Playwright — must stay passing)
npx playwright test tests/e2e-ui/v7.2.0-uxhotfix.spec.js
npx playwright test tests/e2e-ui/v7.3.0-edgecases.spec.js
npx playwright test tests/e2e-ui/v7.4.0-saas-responsive.spec.js
npx playwright test tests/e2e-ui/thorough-pages.spec.js
npx playwright test tests/e2e-ui/thorough-flows.spec.js

# Total regression: 238 backend + ~120 frontend = ~358 tests must stay green
```

---

### Pre-Deploy Gate (per phase) — checklist

**ก่อน commit phase ใดๆ ต้อง verify ครบ 4 layer:**

#### Phase 1 Gate (~2 ชม. work + 1 ชม. test)
- [ ] Layer 1: ≥10 pytest cases pass
- [ ] Layer 2: upload_resilience_e2e_verify Section A ทุก case pass (~10 cases)
- [ ] Layer 3: Playwright Phase1 spec pass (~6 tests)
- [ ] Layer 4: Manual checklist 4 items confirmed
- [ ] Regression: 238 backend + 120 frontend ทั้งหมด pass
- [ ] Console: no red errors during upload flow

#### Phase 4 Gate (~4-5 ชม. work + 2 ชม. test)
- [ ] Layer 1: ≥15 pytest cases pass (chunker + map-reduce + migration)
- [ ] Layer 2: Section B 10+ cases pass
- [ ] Layer 3: Playwright Phase4 spec pass (~5 tests)
- [ ] Layer 4: 4 items + memory check + cost check
- [ ] **Memory:** Fly.io 100MB upload → peak ≤ 700MB
- [ ] **Cost:** 5 big files = 5 AI summary log entries (not 50)
- [ ] Regression all pass

#### Phase 2 Gate (~3 ชม. work + 1.5 ชม. test)
- [ ] Layer 1: ≥10 pytest cases pass
- [ ] Layer 2: Section C 6+ cases pass
- [ ] Layer 3: Playwright Phase2 spec pass (~5 tests)
- [ ] Layer 4: 3 items confirmed
- [ ] **Migration:** existing DB → all files get extraction_status="ok" (verify with prod-like data)
- [ ] Regression all pass

#### Phase 3 Gate (~3 ชม. work + 2 ชม. test)
- [ ] Layer 1: ≥12 pytest cases pass
- [ ] Layer 2: Section D 7+ cases pass
- [ ] Layer 3: Playwright Phase3 spec pass (~4 tests)
- [ ] Layer 4: 3 items confirmed (real Excel/PPT/HTML)
- [ ] **Security:** HTML XSS test — sample_xss.html → no `alert(1)` string in extracted_text
- [ ] Regression all pass

---

### Final Pre-Production Gate (ทุก 4 phase done — ก่อน deploy Fly.io)

- [ ] Total **new** tests pass: ~80 (Phase 1: 16, Phase 4: 25, Phase 2: 16, Phase 3: 20+)
- [ ] Total **regression** tests still pass: 358+
- [ ] All 4-layer manual smoke (12 items) confirmed
- [ ] **Real-device check:** iPhone Safari + Android Chrome → upload flow works end-to-end
- [ ] **Staging deploy:** push to `personaldatabank-staging.fly.dev` → soak 30 min → 0 errors in `flyctl logs`
- [ ] **Memory profile:** monitor Fly.io for 1 hr with mixed traffic → no OOM kill
- [ ] **Cost dashboard:** 1 day of normal usage → LLM cost within expected range (~$0.01-0.05/user/day)
- [ ] All 4 backend E2E sections (A, B, C, D) pass: ~33 cases
- [ ] All 20+ Playwright v7.5.0 tests pass

---

### Test Output Expected

```
$ python scripts/upload_resilience_e2e_verify.py
─────────────────────────────────────────────────────
v7.5.0 Upload Resilience — E2E Verification
─────────────────────────────────────────────────────
SECTION A — Phase 1 Bug Fixes (10 cases)
  PASS  A.1 png upload + OCR extracts text
  PASS  A.2 jpg upload + OCR extracts text
  ...
  PASS  A.10 size error msg shows 200MB

SECTION B — Phase 4 Big File (10 cases)
  PASS  B.1 upload 200K-char PDF → chunk_count > 0
  ...

SECTION C — Phase 2 Proactive UX (6 cases)
  ...

SECTION D — Phase 3 Formats (7 cases)
  ...

─────────────────────────────────────────────────────
RESULT: 33/33 PASS
```

```
$ npx playwright test tests/e2e-ui/v7.5.0-upload-resilience.spec.js
Running 25 tests using 1 worker

  ✓ v7.5.0 / Phase1 / png upload appears in file list (3.2s)
  ✓ v7.5.0 / Phase1 / unsupported file → upload-result-modal opens (2.1s)
  ...
  ✓ v7.5.0 / Phase4 / mobile big-file UI (4.8s)

  25 passed (52s)
```

---

## 📅 Timeline (estimate — รวม test time แล้ว)

| Phase | Build | Test | Total | Sub-tasks |
|-------|------|------|------|-----------|
| Phase 1 — Fix Bugs | 2 ชม. | 1 ชม. | 3 ชม. | image OCR + size msg + structured skip + frontend modal |
| Phase 4 — Big File | 4-5 ชม. | 2 ชม. | 6-7 ชม. | chunker + map-reduce + DB migration + bump limits + polling |
| Phase 2 — Proactive UX | 3 ชม. | 1.5 ชม. | 4.5 ชม. | pre-upload preview + extraction_status + retry + encrypted detect |
| Phase 3 — More Formats | 3 ชม. | 2 ชม. | 5 ชม. | xlsx + pptx + html + json + rtf + security tests |
| Test fixtures setup | — | 1 ชม. | 1 ชม. | สร้าง 12 sample files ใน tests/fixtures/upload_samples/ |
| **Total** | **12-13 ชม.** | **7.5 ชม.** | **~20 ชม.** | (ทำเป็นช่วงได้ ไม่ต้องรวด) |

แนะนำ commit แยกต่อ phase — แต่ละ commit = 1 phase done + ครบ 4 layer test pass
