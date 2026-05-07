# Plan: Multimodal File Support v9.0.0

**Author:** แดง (Daeng)
**Date:** 2026-05-04
**Status:** draft
**Foundation:** master HEAD `87a3734` (v8.2.0 production)

---

## 🎯 Goal

ทำให้ PDB **รองรับไฟล์ได้เยอะกว่าตอนนี้** เพื่อตอบโจทย์ user ที่บอก "อยากใส่ทุกไฟล์ในคอม":

- **ปัจจุบัน:** 5 formats (PDF, DOCX, TXT, MD, CSV)
- **เป้าหมายสุดท้าย:** 30+ formats รวมรูป/เพลง/วิดีโอ/iPhone HEIC/Office เก่า

แบ่งเป็น 2 phase ทำตามลำดับ:

---

## 📊 Strategy: 2 Phase

| Phase | ขอบเขต | จำนวน format ใหม่ | เวลา | Cost |
|-------|--------|------------------|------|------|
| **A. Quick Win** (เปิดของเก่า) | image (Tesseract OCR), xlsx, pptx, html, json, rtf | +9 formats | 10 นาที | ฟรี |
| **B. AI-First** (Gemini multimodal) | iPhone HEIC, audio (mp3/wav), video (mp4/mov), Word เก่า (.doc), code, ebook | +20 formats | 6-8 ชม. | ~$0.001-0.02/file |

**ทำ A ก่อน** → ได้ value เร็ว + ทดสอบว่า user ใช้ feature นี้จริงมั้ย → ค่อย build B

---

## 📚 Context

### ที่มาของ regression
- v7.5.0 (ที่แดง ship) — รองรับ 14 formats รวม image OCR + xlsx/pptx/html/json/rtf
- v8.x (agent อื่น ship ใน parallel session) — restore production plan_limits → กลับเหลือ 5 formats
- v8.x ไม่ได้ลบ extractor functions — แค่ปิด gate ใน `plan_limits.py`

### Backend infrastructure ที่ "พร้อมแล้ว" (ตรวจ master HEAD แล้ว)
- ✅ `backend/extraction.py` มี `_extract_image_ocr` / `_extract_xlsx` / `_extract_pptx` / `_extract_html` / `_extract_json` / `_extract_rtf` ครบ
- ✅ `extract_text()` dispatch ครบทุก ext (line 65-76)
- ✅ Dockerfile install `tesseract-ocr` + `tesseract-ocr-tha` แล้ว
- ✅ `requirements-fly.txt` มี pytesseract / openpyxl / python-pptx / beautifulsoup4 / striprtf / Pillow

### Frontend ที่พร้อม
- ✅ `<input accept>` รองรับ 14 ext แล้ว
- ✅ Upload hint เขียน "max 200 MB · ครั้งละ 20 ไฟล์"
- ✅ Skip modal v7.5.0 + retry button v7.5.0 + extraction badges v7.5.0

= **ขาดแค่เปิด gate ใน `plan_limits.py`**

---

## 📁 Files to Create / Modify — Phase A

### Backend
- [ ] `backend/plan_limits.py` (modify, ~2 บรรทัด) — เพิ่ม 9 ext ใน `allowed_file_types` ของ `free` + `starter`

### Frontend
- ไม่ต้องแก้ — รับ ext ครบแล้วตั้งแต่ v7.5.0

### Tests
- [ ] (optional) `tests/test_plan_limits_v9.py` — verify 14 formats ใน list ของ free + starter

---

## 🔧 Phase A — Step-by-Step (10 นาที)

### Step 1: Edit `backend/plan_limits.py`

**Free plan (line ~28):**
```python
# ก่อน
"allowed_file_types": {"pdf", "docx", "txt", "md", "csv"},

# หลัง
"allowed_file_types": {
    "pdf", "docx", "txt", "md", "csv",
    # v9.0.0 — re-enable v7.5.0 formats (extractors มีอยู่แล้ว)
    "png", "jpg", "jpeg", "webp",            # Tesseract OCR (Thai+EN)
    "xlsx", "pptx", "html", "json", "rtf",   # office + web + structured
},
```

**Starter plan (line ~40):** เพิ่มแบบเดียวกัน

### Step 2: Commit
```bash
git add backend/plan_limits.py
git commit -m "feat(plans): re-enable v7.5.0 formats — image OCR + xlsx/pptx/html/json/rtf

extraction.py + Dockerfile + Frontend ทุกอย่างพร้อมตั้งแต่ v7.5.0 แล้ว
แต่ v8.x restore production plan_limits ทำให้ allowed_file_types เหลือ 5
เปิด gate กลับ → รองรับ 14 formats ทันที (ไม่กระทบ existing data)"
```

### Step 3: Push
```bash
git push origin master
```

### Step 4: Deploy (user รัน — ผม blocked)
```bash
flyctl deploy -a personaldatabank --remote-only
```

### Step 5: Verify (ผม curl ทดสอบ)
```bash
# Register fresh user
TOKEN=$(curl -X POST .../api/auth/register ...)

# Upload PNG → ควร success
curl -F "files=@sample.png" .../api/upload

# Upload XLSX → ควร success
curl -F "files=@sample.xlsx" .../api/upload

# /api/usage → allowed_file_types ควรมี 14 ตัว
```

### Phase A Done Criteria
- [ ] `plan_limits.py` updated + committed + pushed
- [ ] Production deployed
- [ ] PNG upload returns count=1, extraction_status=ok, text_length>0
- [ ] XLSX upload returns count=1
- [ ] /api/usage returns 14 file types

---

## 🤖 Phase B — AI-First Multimodal (6-8 ชม.)

### 🎯 Goal Phase B
รองรับไฟล์ที่ Tesseract/openpyxl ทำไม่ได้ — ใช้ **Gemini multimodal API** แทน

### Format ที่จะเพิ่มใน Phase B (~20 formats)

| Group | Format | ใช้ Gemini API ไหน |
|-------|--------|------------------|
| Image extra | `.heic` `.heif` `.gif` `.bmp` `.tiff` | Vision (รวม HEIC ของ iPhone) |
| Word เก่า | `.doc` | Convert via libreoffice → docx → extract |
| Audio | `.mp3` `.wav` `.m4a` `.flac` `.aac` `.ogg` | Audio API (transcribe) |
| Video | `.mp4` `.mov` `.avi` `.mkv` `.webm` | Video API (frames + audio) |
| Apple iWork | `.pages` `.numbers` `.keynote` | Convert (no direct support) — defer |
| Code | `.py` `.js` `.ts` `.html` `.css` `.json` `.xml` `.yaml` `.sh` `.sql` | Treat as text (encoding fallback) |
| Ebook | `.epub` `.mobi` | python-ebook libraries → text |
| Archive | `.zip` | Extract + recurse (security: limit depth) |

### Architecture Phase B

#### A. New module: `backend/ai_ingest.py`
```python
"""AI multimodal ingestion dispatcher (v9.0.0).

For formats ที่ Tesseract/openpyxl/etc. ทำไม่ได้:
- Image (HEIC/GIF/BMP/TIFF) → Gemini Vision describe + extract text
- Audio (MP3/WAV/M4A/FLAC) → Gemini Audio transcribe
- Video (MP4/MOV/MKV) → Gemini Video summarize + extract speech

Routing logic:
1. ถ้า ext ∈ TEXT_FORMATS → ใช้ extract_text() เดิม (ฟรี)
2. ถ้า ext ∈ AI_VISION → Gemini Vision API (~$0.002/image)
3. ถ้า ext ∈ AI_AUDIO  → Gemini Audio API (~$0.005/min)
4. ถ้า ext ∈ AI_VIDEO  → Gemini Video API (~$0.02/file)

Quota:
- ai_summary_limit_monthly จะนับการ ingest ผ่าน AI ด้วย
- ป้องกัน cost runaway
"""

async def ai_ingest_file(filepath, ext, user) -> dict:
    """Returns {extracted_text, ai_method, cost_estimate}"""
    if ext in AI_VISION:
        return await _gemini_vision_extract(filepath)
    elif ext in AI_AUDIO:
        return await _gemini_audio_transcribe(filepath)
    elif ext in AI_VIDEO:
        return await _gemini_video_analyze(filepath)
```

#### B. Modify `backend/main.py` upload endpoint
```python
# Existing extract_text logic
extracted = extract_text(raw_path, ext)

# v9.0.0 — fallback to AI if extract_text returns "[Unsupported file type]"
if extracted.startswith("[Unsupported"):
    if ext in AI_FORMATS:
        result = await ai_ingest_file(raw_path, ext, current_user)
        extracted = result["extracted_text"]
        # Track AI cost
        await log_usage(db, current_user.id, "ai_ingest")
```

#### C. Modify `backend/plan_limits.py`
```python
# Add Phase B formats
"allowed_file_types": {
    # Phase A (Tesseract + extractors)
    "pdf", "docx", "txt", "md", "csv",
    "png", "jpg", "jpeg", "webp",
    "xlsx", "pptx", "html", "json", "rtf",
    # Phase B (Gemini multimodal — paid AI calls)
    "heic", "heif", "gif", "bmp", "tiff",   # extra image
    "doc",                                   # legacy Word
    "mp3", "wav", "m4a", "flac",            # audio
    "mp4", "mov", "mkv", "webm",            # video
    "py", "js", "ts", "css", "yaml", "sql", # code (text-based)
    "epub",                                  # ebook
    "zip",                                   # archive
},

# New limit for cost control
"ai_ingest_limit_monthly": 100,    # Free
"ai_ingest_limit_monthly": 1000,   # Starter
```

#### D. New table: `usage_log` extension
```sql
-- Track AI ingest cost per user
ALTER TABLE usage_log ADD COLUMN ai_method TEXT;       -- "vision"/"audio"/"video"
ALTER TABLE usage_log ADD COLUMN ai_cost_estimate REAL;  -- USD
```

### Phase B Open Questions
- **Q1:** ใช้ Gemini Files API (upload file 48hr) หรือ inline base64?
- **Q2:** Audio chunk size — 5min/10min/all-at-once?
- **Q3:** Video — ส่ง frames sample หรือ full file?
- **Q4:** Cost gate — Free 100 calls/เดือน, Starter 1000?
- **Q5:** Privacy disclosure — ต้องแจ้ง user มั้ยว่าไฟล์ขึ้น Gemini?
- **Q6:** Fallback ถ้า Gemini API down — store raw + retry later?

---

## 🧪 Test Scenarios

### Phase A
- ✅ Upload PNG with Thai text → OCR extract Thai text
- ✅ Upload XLSX 3 sheets → flatten markdown + all data
- ✅ Upload PPTX → slides + speaker notes
- ✅ Upload HTML with `<script>` → strip, no XSS leak
- ✅ JSON/RTF → text extracted
- ✅ Existing TXT/PDF/DOCX upload still works (regression)

### Phase B (เพิ่มจาก A)
- ✅ Upload HEIC iPhone photo → Gemini Vision describe + OCR text
- ✅ Upload MP3 voice memo → Gemini transcribe
- ✅ Upload MP4 lecture → Gemini summarize + extract speech
- ✅ Upload .py code → text extract (no Gemini needed)
- ✅ Cost tracking: 5 audio uploads = 5 ai_ingest log entries

---

## ✅ Done Criteria

### Phase A
- [ ] `plan_limits.py` มี 14 ext ใน Free + Starter
- [ ] PNG/JPG/XLSX/PPTX/HTML/JSON/RTF upload ไม่โดน UNSUPPORTED_TYPE
- [ ] Existing files ของ user ไม่กระทบ (DB schema ไม่เปลี่ยน)
- [ ] Production deploy + verify ผ่าน

### Phase B
- [ ] `ai_ingest.py` module ทำงานครบ Vision/Audio/Video
- [ ] HEIC/MP3/MP4/MOV upload → extract ผ่าน AI
- [ ] Cost tracking ใน `usage_log`
- [ ] `ai_ingest_limit_monthly` enforce
- [ ] Privacy notice ใน UI (ก่อน Phase B ไฟล์อยู่แค่ server เรา → ตอนนี้ขึ้น Gemini)
- [ ] Tests + regression PASS

---

## ⚠️ Risks

### Phase A
- 🟢 **Low risk** — code มีอยู่ + tested ใน v7.5.0 + deployed Tesseract แล้ว
- ⚠️ Memory: image OCR ใช้ RAM ~50-200MB peak → ถ้า upload หลายรูปพร้อมกันอาจ OOM (Fly 1024MB)
  - Mitigation: batch limit 20 ไฟล์ที่มีอยู่แล้วช่วยกัน

### Phase B
- 🟡 **Medium risk** — Gemini API integration ใหม่ + cost model ใหม่
- ⚠️ **Privacy** — ไฟล์ user ถูก upload ไป Google Gemini (auto-delete 48hr)
- ⚠️ **Cost runaway** — user upload audio 100 ไฟล์ = $5+ ทันที
- ⚠️ **HTTP timeout** — video analyze อาจ >60s → ต้องทำ async + status polling
- ⚠️ **Vendor lock-in** — เลือก Gemini = ผูกกับ Google

---

## 📌 Notes for นักพัฒนา

### Phase A
1. แค่แก้ `plan_limits.py` 2 ที่ (free + starter) — **ห้ามแก้ extraction.py / main.py**
2. ทดสอบ regression: existing PDF/DOCX/TXT ต้องยัง work
3. Verify Tesseract บน Fly machine: `flyctl ssh console -C "tesseract --version"`

### Phase B
1. Gemini Files API: upload file → ได้ file_id → reference ใน prompt → auto-delete 48hr
2. ต้อง add `gemini_file_id` column ใน `files` table (cache ระหว่าง 48hr)
3. Sequential ingest ก่อน — parallel เป็น Phase 5+ scaling
4. Privacy: เพิ่ม checkbox ใน upload modal "อนุญาตให้ AI ประมวลผลไฟล์ multimedia"

---

## 📅 Timeline

| Phase | Build | Test | Total |
|-------|-------|------|-------|
| A. Re-enable v7.5.0 | 5 นาที | 5 นาที | **10 นาที** |
| B. AI multimodal | 6 ชม. | 2 ชม. | **8 ชม.** |
| **Total** | | | **~8 ชม.** (แต่ shipping incremental) |

---

## 🚦 Recommended Order

1. **NOW:** ทำ Phase A → ship → user verify ว่า image/xlsx/etc. ใช้งานได้จริง
2. **+1 day:** ดู usage data — user upload format ไหนบ่อยสุด → priority Phase B
3. **+1 week:** ถ้า user request mp3/mp4/heic บ่อย → ค่อย start Phase B
4. **NOT NOW:** อย่า over-build — ทำ Phase B เมื่อ user ต้องการจริง
