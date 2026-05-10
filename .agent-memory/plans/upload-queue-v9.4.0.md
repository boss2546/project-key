# Plan: Upload Queue + Honest Visibility (v9.4.0)

**Author:** แดง (Daeng)
**Date:** 2026-05-10
**Status:** draft v2 (รอ user approve · revised after เขียว field-audit)
**Foundation:** master HEAD `763a45a` (v9.3.5 review_passed FINAL)
**Target APP_VERSION:** 9.4.0
**Replaces:** [upload-queue-progress-v9.4.0.md](upload-queue-progress-v9.4.0.md) (draft v1)
**Revisions in v2** (per เขียว audit 2026-05-10):
- M-1 [BLOCKER]: Fixed i18n pattern — actual codebase uses single `const I18N = { th, en }` not separate vars
- M-3 [BLOCKER]: Added WAL mode setup in Step 1 (was mentioned but no code)
- M-4 [BLOCKER]: Added reprocess + promote refactor to scope (consistent with "ไม่ค้าง" goal)
- M-2 [MEDIUM]: Specified `func` import location
- M-9 [MEDIUM]: Extended `t()` function to support variable substitution
- M-10 [MEDIUM]: Replaced raw SQL f-string with safer hardcoded CASE

---

## 🌟 หลักคิดหลัก 4 ข้อ (สรุปจากโจทย์ของ user)

1. **ตรงตามความจริง 100%** — ห้ามโชว์ progress ปลอม, ห้ามอ้างเร็วกว่าจริง, error message ต้องระบุสาเหตุจริง
2. **ไม่ค้าง** — `/api/upload` ต้อง return < 200ms เสมอ ไม่ว่าไฟล์จะใหญ่/เล็ก
3. **user เห็นทุกอย่าง** — สถานะ, ขั้นตอน, เหตุผลที่ช้า, อันดับคิว, เวลาเริ่ม-เวลาเสร็จ
4. **ง่ายไม่ซับซ้อน** — DB เป็น queue, worker 1 ตัว in-process, polling 2s, ไม่มี Redis/Celery/SSE/WebSocket

> โจทย์ของคุณคือ "ระบบคิด + แสดงสถานะจริง + ไม่ค้าง + ช้าได้ขอแค่บอกเหตุผล" — plan นี้ตอบครบทั้ง 4 พร้อม future hooks สำหรับ organize queue (รอบหน้า)

---

## 🎯 1. Goal + User Stories

### Goal (1 บรรทัด)
แยก **"รับไฟล์"** (เร็ว ≤ 200ms) ออกจาก **"อ่านไฟล์"** (ช้า — OCR/Gemini) เป็น DB-backed queue + in-process worker + UI tray ที่บอกความจริงทุกขั้น โดยเก็บ extraction stack v9.3.4 เดิมทั้งหมด ไม่แตะ

### User Stories (เห็นภาพชัด)

**US-1 — อัปโหลดไฟล์เดียวเล็กๆ (txt 5KB)**
> เป็น Free user, อัปไฟล์ TXT 1 ไฟล์ → กดปุ่ม → < 1 วินาที tray โผล่ขึ้นมาด้านล่าง-ขวา → tray แสดง "รออันดับ 1" → 2 วินาทีต่อมา "กำลังอ่านข้อความ" → ทันทีหลังจากนั้น "เสร็จแล้ว ✓" → tray หายไป + main file list อัปเดต

**US-2 — อัปโหลด PDF สแกน 50 หน้า (~30 MB)**
> อัป PDF ที่เป็นรูปสแกนล้วน → ภายใน 200ms tray โผล่ → "รออันดับ 1" → "กำลังอ่าน PDF" → "ไม่เจอ text — เริ่ม OCR" → "OCR หน้า 1 จาก 50" → ... → "OCR หน้า 50 จาก 50" → "บันทึกผลลัพธ์" → "เสร็จแล้ว ✓" — รวม ~3 นาที แต่ user เห็นความคืบหน้าทุก 2 วินาที **ไม่เคยรู้สึกค้าง**

**US-3 — อัปโหลด audio Thai 5 นาที (.m4a)**
> อัปเสียง 5 นาที → tray โผล่ → "อัปโหลดไป Gemini" → "Gemini ถอดเสียง (อาจใช้เวลา 1-3 นาที)" — ระบบยอมรับว่าไม่รู้ % ตรงนี้ จึงโชว์ indeterminate (ไม่โชว์ % ปลอม) → "บันทึกผลลัพธ์" → "เสร็จแล้ว ✓"

**US-4 — อัป 20 ไฟล์ผสมขนาด ครั้งเดียว**
> User ลาก 20 ไฟล์ลง drop zone → ภายใน 2 วินาที tray แสดงทั้ง 20 ไฟล์เรียงตามอันดับ → ไฟล์เล็ก/รูป/txt ขึ้นหน้าก่อน (priority 1) → docx/pdf รองลงมา (priority 2) → audio/video หลังสุด (priority 3) → user เห็นว่าไฟล์ไหน "กำลังทำ" ไฟล์ไหน "อันดับ 5" → ปิด browser ไปกินข้าว → กลับมาเปิด → tray โผล่อัตโนมัติ + ส่วนใหญ่เสร็จแล้ว / ที่เหลือยังเดินต่อ (recoverable)

**US-5 — ไฟล์ extract fail (PDF ที่เข้ารหัส)**
> Worker ลองอ่าน PDF → เจอว่าเข้ารหัส → mark error + บอก user ตรงๆ "ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปใหม่" + ปุ่ม "ลองใหม่" / "ลบออก" → user รู้ทันทีว่าทำไม ไม่ใช่ "เกิดข้อผิดพลาด"

---

## 🔒 2. Truthfulness Contract (กฎเหล็ก — ห้ามฝ่าฝืน)

> นี่คือสัญญากับ user. ฟ้าจะ reject PR ที่ละเมิดข้อใดข้อหนึ่ง

### TC-1 — ห้ามโชว์ progress ปลอม

| สิ่งที่ห้าม | ทำแทนยังไง |
|---|---|
| ❌ โชว์ "30%" เมื่อเราไม่รู้จริง | ✅ ใช้ indeterminate spinner ของ `.meter` (เพิ่ม `.is-indeterminate` modifier) |
| ❌ โชว์ "Processing 45%..." เพื่อให้ดูเร็ว | ✅ โชว์ขั้นตอนจริง: "OCR หน้า 5/12" |
| ❌ "กำลังประมวลผล..." (ไม่บอกอะไร) | ✅ "กำลังถอดเสียงด้วย Gemini (อาจใช้เวลา 1-3 นาที)" |

### TC-2 — Stage Timestamps ต้องเป็นของจริง

ทุกไฟล์ต้องมี timeline จริงเก็บใน DB + แสดงให้ user คลิกดูได้:

```
queued_at            ← เวลาเข้าคิว (ของจริง)
extract_started_at   ← เวลา worker หยิบขึ้นมาทำ (ของจริง)
extract_completed_at ← เวลาเสร็จ/error (ของจริง)
```

UI แสดง `2026-05-10 14:23:01 → 14:23:08 → 14:25:42` (Bangkok TZ) ใต้ progress text. user click "รายละเอียด" เห็นช่วงเวลาแต่ละขั้น

### TC-3 — Why-slow Explanation

ถ้า user รออาจ > 30 วินาที, tray ต้องบอกเหตุผลจริง:

| สถานการณ์ | ข้อความที่ user เห็น |
|---|---|
| รออันดับ 5/7 | "อันดับ 5 จาก 7 — ประมาณ 2 นาที" |
| กำลัง OCR PDF 50 หน้า | "OCR หน้า 12/50 — ไฟล์ใหญ่ใช้เวลานาน" |
| กำลังคุย Gemini audio 10 นาที | "Gemini ถอดเสียง 10 นาที — รอประมาณ 2-4 นาที" |
| Gemini ตอบช้า | "Gemini ตอบช้ากว่าปกติ — รออีกสักครู่" |

### TC-4 — Estimated Wait ต้องคำนวณจาก rolling average จริง

ห้าม hardcode "× 8 วินาที" — ต้องเก็บ historical average:

```python
# ใน upload_worker — เก็บ moving average ต่อ file_kind
_avg_extract_sec = {
    "txt": 0.5,    # rolling avg ของ ext-class นี้ (อัปเดตทุก successful extract)
    "pdf": 12.0,
    "m4a": 90.0,
    ...
}
```

API คืน `estimated_wait_sec` คำนวณจาก:
```
sum(_avg_extract_sec[ext-class] for f in files_ahead_in_queue)
```

ไม่รู้ก็บอกว่า "ไม่ทราบ" (return `null`) — ห้ามมั่ว

### TC-5 — Truthful Error Messages

Error catalog (Appendix A) มีรายการ → mapping จาก exception → TH message ที่ระบุสาเหตุจริง

❌ ห้าม "เกิดข้อผิดพลาด — กรุณาลองใหม่"
✅ "Gemini quota เต็ม (1,000 ครั้ง/เดือน) — รอเดือนหน้าหรือเปลี่ยนแพลน"
✅ "PDF เข้ารหัส — ปลดล็อกก่อนอัปใหม่"

### TC-6 — System Status Banner (กรณีคิวตันรวม)

ถ้า worker crash > 3 ครั้งติดต่อกัน หรือคิวตันเกิน 5 นาทีไม่เดิน → แสดง banner รวม:

> "⚠️ ระบบประมวลผลล่าช้ากว่าปกติ — เรากำลังตรวจสอบ"

(ไม่ใช่ "Working hard for you!" หรือ stock copy)

---

## 📚 3. Context

### 3.1 Pain points ปัจจุบัน (v9.3.4)

[backend/main.py:480-629](../../backend/main.py#L480-L629) ทำทุกอย่างใน request เดียว:

```
POST /api/upload (sync)
  → save file
  → extract_text() ← OCR/Tesseract หนัก (PDF 50 หน้า = 90s)
  → ai_ingest.ingest_via_ai() ← Gemini multimodal (audio 10 min = 180s)
  → compute_content_hash + classify + strip_surrogates
  → DB commit
  → BackgroundTask push to Drive (BYOS only)
  ← return (รอจนทุก step เสร็จ)
```

**4 ปัญหา root cause:**

1. **Timeout** — Cloudflare/Fly proxy 60-120s. PDF OCR หรือ audio ยาว → request พัง 504
2. **Block ไฟล์อื่นในชุด** — frontend pool 3 (1 file/req) แต่ slot ค้างถ้าไฟล์ที่ 3 ใช้ Gemini 5 นาที
3. **Memory peak** — `contents = await upload_file.read()` โหลดเข้า RAM พร้อมกัน + pdf2image แปลงทุกหน้าเป็น PIL image ใน RAM → 4GB RAM ก็ peak
4. **Recovery ไม่ได้** — server restart ระหว่าง extract → row ค้าง `processing_status="processing"` ตลอด (orphan)

User experience ([app.js:1488-1507](../../legacy-frontend/app.js#L1488-L1507)):
- เห็นแค่ "เซิร์ฟเวอร์ประมวลผล X/Y ไฟล์..." + indeterminate spinner — **ไม่บอกอะไร**
- ปิด browser = "กลัวว่าหาย"
- Fail = ไม่รู้สาเหตุ ต้องอัปใหม่

### 3.2 ทำไม v9.4.0 ≠ v10.x

v10.x รื้อ extraction stack ทั้งหมด → พังหลาย module พร้อมกัน → rollback เป็น v9.3.4

v9.4.0 ทำตรงข้าม:
- ✅ **เก็บ extraction stack v9.3.4 เดิมทั้งหมด** (PyPDF2 + Tesseract + python-docx + ai_ingest) — ไม่แตะ
- ✅ **เพิ่มเลเยอร์ queue ทับด้านบน** — schema = ADD-only
- ✅ **DB เป็น queue** ไม่ใช้ Redis/Celery
- ✅ **In-process async worker 1 ตัว** ไม่ใช่ worker pool
- ✅ **Scope = ทุก extract path ที่ user เห็น** — upload + reprocess + promote (organize queue ไว้รอบหน้า v9.5.0)

### 3.3 Extract paths ที่ต้อง enqueue (M-4 fix · เพิ่มใน v2)

> เขียว field-audit พบว่า extract_text+ai_ingest ถูกเรียก inline 3 ที่ใน web UI ไม่ใช่แค่ /api/upload
> ถ้าแก้แค่ upload → user reprocess/promote ก็ยังเจอค้าง → ขัด goal "ไม่ค้าง"

| Endpoint | สถานะปัจจุบัน | v9.4.0 ทำยังไง |
|---|---|---|
| `POST /api/upload` | inline (block 30-120s) | save+queue (return ≤200ms) |
| `POST /api/files/{id}/reprocess` ([main.py:1586](../../backend/main.py#L1586)) | inline + LLM cleanup (block) | reset status='queued' → return 200 (worker handle) |
| `POST /api/files/{id}/promote` ([main.py:1714](../../backend/main.py#L1714)) | inline+ai_ingest (block) | set status='queued' → return 200 (worker handle vault→processed) |
| `POST /api/upload/{id}/retry` (NEW) | (ไม่มีปัจจุบัน) | reset status → 'queued' → worker pickup |
| LINE bot · MCP · bot_handlers (sync inline) | คงเดิม — out of scope (ไม่มี user รออยู่หน้า UI) | ไม่กระทบ |

**3 web UI endpoints = enqueue ทั้งหมด** เพื่อ "ไม่ค้าง" 100% ทุก surface

---

## 🚫 4. Out of Scope (สิ่งที่จะ "ไม่" ทำในรอบนี้)

| รายการ | ทำไมเลื่อน | จะทำเมื่อ |
|---|---|---|
| คิว "วิเคราะห์ด้วย AI" (organize) | คุณบอกชัด "คิวทำงานต่อก็อีกเรื่อง" | v9.5.0 |
| Server-Sent Events (SSE) แทน polling | polling 2s เพียงพอ scale ปัจจุบัน + simpler | v9.5.x ถ้าจำเป็น |
| Multi-uvicorn worker (Fly.io scale-out) | atomic claim รองรับแล้ว แต่ยังไม่ทดสอบ | v10.x |
| Redis / Celery / RQ | infra เกินจำเป็น + เพิ่ม cost + เพิ่ม failure surface | ไม่ทำ |
| Streaming upload (ไม่ load RAM ทั้งไฟล์) | ปัญหารอง — request reduced จาก 120s → 200ms ก็พอแล้ว | v9.4.1 |
| WebSocket real-time push | overkill สำหรับ queue feedback 2s | ไม่ทำ |
| Per-stage progress bar (ขั้นตอนเล็กลง) | progress_step text เพียงพอ + tabular nums อ่านง่าย | v9.4.1 ถ้า user ขอ |
| Cost tracking (Gemini minutes) | future hook เก็บไว้ schema-ready | v9.5.0 |
| Web Push notification (ปิด browser แจ้ง) | platform-dependent + ต้องขอ permission | v9.6.0 |

---

## 🪝 5. Future Hooks (เผื่ออนาคต — design now, build later)

> Schema และ state machine ออกแบบให้ extend ได้โดยไม่ต้อง refactor

### FH-1 — Organize Queue (v9.5.0)
- v9.4.0 มี state `uploaded` (extract เสร็จ รอ AI organize)
- v9.5.0 จะเพิ่ม state `organize_queued` → `organizing` → `ready`
- Schema ใช้ `processing_status` column เดิม ไม่ต้องเพิ่ม table
- Worker เดียวกันสามารถ process organize jobs ได้ — แค่เพิ่ม dispatcher

### FH-2 — SSE Upgrade Path (v9.5.x ถ้าจำเป็น)
- API response shape ของ `/api/upload-status` ออกแบบให้เป็น **event-stream-compatible** (one row per item, flat fields, no nested objects)
- Frontend `UploadTray` namespace มี method `_render(snapshot)` แยกชัดจาก `_fetchPolling()` → swap เป็น SSE handler ได้โดยไม่แตะ render

### FH-3 — Multi-worker Safety (v10.x)
- `_claim_next_job()` ใช้ atomic UPDATE ที่ multi-worker safe ตั้งแต่วันแรก
- Recovery ใช้ `extract_started_at < now-30min` เป็น lease expiry — heartbeat-free แต่ปลอดภัย

### FH-4 — Cost Guard (v9.5.0)
- Schema เพิ่ม column `gemini_seconds` (NULL ตอนนี้, populate ใน v9.5.0)
- `ingest_via_ai` คืน duration metadata → save ลง column นี้
- v9.5.0 enforce limit per plan (Free 0 / Starter 1000 / Admin ∞)

### FH-5 — DB Queue Cleanup (v9.5.0)
- Cron job อ่านจาก `extract_completed_at` — archive rows ที่ status ∈ {ready, error} เก่ากว่า 90 วันไป `files_archived` table
- ตอนนี้ table ยังไม่โต — schema-ready, รอใช้

### FH-6 — Web Push Notification (v9.6.0)
- เก็บ `browser_push_subscription` (จาก Service Worker) ใน users table — ตอนนี้ schema-ready ผ่าน v9.4.0
- v9.6.0 push เมื่อทุกไฟล์ใน batch เสร็จ

### FH-7 — Per-file Activity Log (v9.5.0 ถ้าใช้)
- ตอนนี้เรามี progress_step (TEXT) ที่ overwrite ทุกครั้ง
- v9.5.0 เพิ่ม table `file_events` (file_id, event_type, message, ts) สำหรับ user click "ดูประวัติ"
- ตอนนี้ไม่ทำ — overhead ไม่คุ้มสำหรับ MVP

---

## 🧠 6. Architecture Decision Records (ADRs)

### ADR-001: ใช้ DB เป็น queue (ไม่ใช่ Redis)

**Decision:** SQLite เป็น queue, poll ทุก 2s

**Alternatives พิจารณา:**
- Redis + RQ — เพิ่ม infra dependency, Fly.io ต้อง provision Redis instance ($), ผิด "ง่ายไม่ซับซ้อน"
- Celery — overkill สำหรับ scale ปัจจุบัน, learning curve สูง
- arq — Python async + Redis — ผูกกับ Redis ลึก
- In-memory `asyncio.Queue` — server restart = หมด ไม่ recoverable

**Why SQLite:**
- ไม่เพิ่ม infra (PDB ใช้ SQLite อยู่แล้ว)
- Persistent — recoverable หลัง restart
- Atomic UPDATE...WHERE...RETURNING รองรับ race condition (Python 3.11+ stdlib sqlite3)
- 2s poll latency ไม่กระทบ UX (user ไม่กดอะไรอยู่)

**Trade-off:**
- DB write rate ระหว่าง progress update ต้อง throttle (1.5s) เพื่อไม่ lock ไฟล์ DB
- ถ้า scale > 1000 concurrent users — ต้อง revisit (move to Postgres หรือ Redis)

### ADR-002: In-process worker 1 ตัว (ไม่ใช่ separate service)

**Decision:** `asyncio.create_task` ตอน FastAPI startup, ทำงานใน process เดียวกับ uvicorn

**Alternatives:**
- Separate worker process (gunicorn supervisor) — Fly.io machine ต้อง config 2 processes
- ดู systemd/supervisor — Fly.io ใช้ Docker, complex
- AWS Lambda / Fly Machines async — overkill

**Why in-process:**
- Simpler deployment (1 fly.toml entry)
- Memory shared (ไม่ต้อง IPC)
- Restart = ทั้ง worker + API restart พร้อมกัน — recovery clean

**Trade-off:**
- Worker crash = uvicorn ก็ down (แต่ Fly.io auto-restart machine แล้ว)
- ต้องระวัง CPU-bound task block event loop → ใช้ `asyncio.to_thread` wrap

### ADR-003: Polling 2s (ไม่ใช่ SSE/WebSocket)

**Decision:** Frontend `setTimeout(2000)` polling

**Alternatives:**
- Server-Sent Events (SSE) — real-time, ใช้ EventSource API
- WebSocket — bidirectional, ต้อง maintain connection
- Long polling — กึ่งกลาง

**Why polling 2s:**
- Simpler — ไม่ต้อง maintain connection
- Cloudflare-friendly (ไม่มี long-lived connection)
- 2s feedback acceptable สำหรับงานที่ใช้เวลา 30s-5min
- Backoff หลัง 30 ticks → 5s (efficient)
- หยุดเมื่อ tray ปิด / queue ว่าง — ไม่กิน resource

**Trade-off:**
- Real-time น้อยกว่า SSE 2s
- เปลี่ยนเป็น SSE ได้ง่าย (FH-2 future hook)

### ADR-004: Worker concurrency = 1 (ไม่ parallel)

**Decision:** worker ทำทีละไฟล์, ลำดับตาม priority + queued_at

**Alternatives:**
- 2 (parallel) — เร็วขึ้น 2x
- Dynamic (ปรับตาม queue depth)

**Why 1:**
- Sequential = predictable + debug ง่าย
- ไม่ต้อง coordinate resource (Tesseract, Gemini quota)
- Memory-safe — ไม่ peak หลายไฟล์พร้อมกัน
- ปรับเป็น 2 ได้ทีหลัง — แค่เปลี่ยน `range(1)` → `range(2)` ใน worker init

**Trade-off:**
- Throughput = sum of per-file extract time
- ถ้าจำเป็นต้องเร็ว — adjust env var `UPLOAD_WORKER_CONCURRENCY`

### ADR-005: Auto-retry = 0 (manual retry เท่านั้น)

**Decision:** Fail = stop. user เห็น error + กดปุ่ม "ลองใหม่"

**Alternatives:**
- 1 retry (handle transient)
- 3 retries with exponential backoff

**Why 0:**
- ตรงตาม Truthfulness Contract — user เห็น error ทันที ไม่หลอกว่าระบบทำต่อให้
- ลด cost (Gemini quota — retry = ใช้ quota ซ้ำ)
- หลายๆ error ไม่ใช่ transient (PDF เข้ารหัส, format ไม่รองรับ) — retry ก็ไม่ช่วย
- Manual retry = user ตัดสินใจเอง

**Trade-off:**
- Transient error (Gemini 503) ต้องกด retry เอง
- Mitigation: error message บอกชัด "Gemini ตอบช้ากว่าปกติ — กดลองใหม่"

### ADR-006: Multi-tenant fairness = round-robin per-user (ไม่ใช่ pure FIFO)

**Decision:** Worker หยิบงานโดยจัดลำดับ `(user_id_round_robin_position, priority, queued_at)`

**Alternatives:**
- Pure FIFO (queued_at) — user 1 คนสแปม block คนอื่น
- Per-plan tier weight (Admin > Starter > Free) — ซับซ้อน

**Why round-robin per-user:**
- Fair — ไม่ให้ user 1 คน block ระบบ
- Simple — แค่ ORDER BY user_id ก่อน + tracking last user processed

**Implementation:**
```python
# คำนวณ "user-batch position" — user A's 1st file, user B's 1st, user A's 2nd, ...
# query: order by ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY queued_at), priority, queued_at
```
ผ่าน SQL window function (SQLite 3.25+ รองรับ)

**Trade-off:**
- Query ซับซ้อนกว่า ORDER BY queued_at — แต่ index บน (status, queued_at) ช่วยได้
- Free user ที่อัปไฟล์น้อย ได้ priority สูงโดยไม่รู้ตัว — ดี

### ADR-007: Per-Plan Tier Queue Caps

**Decision:** queue cap แตกต่างตาม plan tier

| Plan | Queue Cap | Total File Limit (existing) |
|---|---|---|
| Free | 10 | 50 |
| Starter | 50 | 500 |
| Admin | 200 | 999999 |

**Why:**
- กัน DoS ตัวเอง (Free user spam อัป 100 ไฟล์ → block worker ทั้งระบบ ทั้งวัน)
- Starter ให้สูงพอใช้งาน normal batch
- Admin ปลอดภัย (internal use)

**Code:** อ่านจาก `plan_limits.py` เพิ่ม field `upload_queue_cap`:

```python
PLAN_LIMITS = {
    "free":    {..., "upload_queue_cap": 10},
    "starter": {..., "upload_queue_cap": 50},
    "admin":   {..., "upload_queue_cap": 200},
}
```

---

## 🔄 7. State Machine + Transition Table

### 7.1 State Diagram (ASCII)

```
                          ┌─────────────────────┐
                          │  (file uploaded —   │
                          │   placeholder row)  │
                          └──────────┬──────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  │                                     │
            (vault ext)                          (processed ext)
                  │                                     │
                  ▼                                     ▼
          ┌──────────────┐                       ┌────────┐
          │  vault_only  │                       │ queued │ ◄────┐
          │  (terminal)  │                       └────┬───┘      │
          └──────────────┘                            │          │
                                                      │ worker   │
                                                      │ claims   │ retry
                                                      ▼          │
                                              ┌────────────┐     │
                                              │ extracting │     │
                                              └─────┬──────┘     │
                                                    │            │
                                            ┌───────┴────────┐   │
                                            │                │   │
                                       (success)         (error) │
                                            │                │   │
                                            ▼                ▼   │
                                      ┌──────────┐     ┌───────┐ │
                                      │ uploaded │     │ error │─┘ retry
                                      └─────┬────┘     └───────┘
                                            │
                                  (user clicks "วิเคราะห์ด้วย AI")
                                            │
                                            ▼
                                      ┌─────────┐
                                      │organized│  (handled by organize-new)
                                      └────┬────┘
                                           │
                                           ▼
                                      ┌───────┐
                                      │ ready │  (terminal)
                                      └───────┘
```

### 7.2 Transition Table (event × from-state → to-state + side-effect)

| Event | From | To | Side Effects |
|---|---|---|---|
| upload (vault ext) | (none) | `vault_only` | save raw, vault searchable text, queue=skip |
| upload (processed ext) | (none) | `queued` | save raw, insert placeholder, queued_at=now |
| worker claim | `queued` | `extracting` | extract_started_at=now, attempt_count++ |
| extract success | `extracting` | `uploaded` | extracted_text=..., progress_pct=100, extract_completed_at=now, push_drive_if_byos |
| extract fail | `extracting` | `error` | extract_error=TH msg, extract_completed_at=now |
| user retry | `error` | `queued` | reset extract_*, queued_at=now |
| user dismiss | `error` | (deleted) | delete row + raw file + drive copy |
| recovery (stale > 30min) | `extracting` | `queued` | reset extract_started_at, log warning |
| organize-new | `uploaded` | `organized` | (handled by organizer.py — out of scope v9.4.0) |
| organize finish | `organized` | `ready` | (out of scope v9.4.0) |

### 7.3 Invariants (ห้ามฝ่าฝืนทุกกรณี)

| INV | คำอธิบาย | บังคับใช้โดย |
|---|---|---|
| **INV-1** | ไฟล์ status=`extracting` ต้องมี `extract_started_at` != NULL | DB CHECK + worker code |
| **INV-2** | ไฟล์ status=`error` ต้องมี `extract_error` != NULL | worker `_mark_job_failed` |
| **INV-3** | ไฟล์ status=`uploaded` ต้องมี `extracted_text` != "" + `extraction_status` ∈ {ok, partial, ocr_failed, encrypted, empty} | worker success path |
| **INV-4** | `attempt_count <= MAX_RETRY_ATTEMPTS` (default 3) เสมอ | retry endpoint check |
| **INV-5** | Worker รัน extract เฉพาะกับ row ที่ "claim สำเร็จ" (atomic UPDATE rowcount=1) | `_claim_next_job` |
| **INV-6** | ไฟล์ status=`queued` ห้ามมี `extract_started_at` != NULL | worker reset on recovery |
| **INV-7** | progress_pct ∈ [0, 100] หรือ NULL — ห้ามค่าอื่น | worker code + DB CHECK |
| **INV-8** | Per-user queue cap = `plan_limits.upload_queue_cap` — ตรวจที่ /api/upload | endpoint preflight |

---

## ⚖️ 8. Multi-tenant Fairness Design

### 8.1 ปัญหาที่จะกัน
User A อัป 50 ไฟล์ pdf หนัก → user B อัป 1 txt → ถ้า pure FIFO, user B ต้องรอ 50 ไฟล์ของ A เสร็จ → unfair

### 8.2 Solution: Round-robin per-user + priority

Worker `_claim_next_job` query:

```sql
WITH ranked AS (
  SELECT
    f.*,
    ROW_NUMBER() OVER (PARTITION BY f.user_id ORDER BY f.queued_at ASC) AS user_pos,
    CASE
      WHEN f.filetype IN ('txt','md','csv','png','jpg','jpeg','webp','heic','heif',
                          'gif','bmp','tiff','tif','py','js','ts','jsx','tsx','css',
                          'scss','less','sass','xml','yaml','yml','toml','ini','env',
                          'conf','cfg','sh','bash','zsh','bat','ps1','sql','java',
                          'kt','swift','c','cpp','h','hpp','cs','go','rs','rb','php',
                          'log','tsv','vue','svelte','json','html','rtf') THEN 1
      WHEN f.filetype IN ('pdf','docx','xlsx','pptx') THEN 2
      ELSE 3  -- audio/video
    END AS priority_class
  FROM files f
  WHERE f.processing_status = 'queued'
)
SELECT * FROM ranked
ORDER BY user_pos ASC, priority_class ASC, queued_at ASC
LIMIT 1
```

**ผล:**
- User A อัป 50 + user B อัป 1 พร้อมกัน
- Worker หยิบ: A's 1st → B's 1st → A's 2nd → A's 3rd → ... (B หมดแล้ว)
- B ได้ทำเป็นไฟล์ที่ 2 จากทั้งคิว ไม่ต้องรอจนหลัง 50 ของ A

### 8.3 Per-plan Tier Caps

ก่อน insert placeholder ใน `/api/upload`:

```python
queue_count = await db.scalar(
    select(func.count()).select_from(File).where(
        File.user_id == current_user.id,
        File.processing_status.in_(["queued", "extracting"]),
    )
)
queue_cap = _limits.get("upload_queue_cap", 10)
if queue_count >= queue_cap:
    skipped.append(_make_skip("QUEUE_FULL", original_name, limit=queue_cap))
    continue
```

---

## 📊 9. Observability (เพิ่ม trust + ช่วย debug production)

### 9.1 `/api/healthz/queue` (ใหม่ — public, no auth)

```json
GET /api/healthz/queue

Response 200:
{
  "worker": {
    "status": "running",         // running | stopped | crashed
    "uptime_sec": 3600,
    "last_heartbeat": "2026-05-10T07:23:01Z",
    "concurrency": 1
  },
  "queue": {
    "queued": 12,                // total ทุก user
    "extracting": 1,
    "error_24h": 3,
    "oldest_queued_age_sec": 45  // จาก now - min(queued_at)
  },
  "metrics": {
    "avg_extract_sec_by_class": {
      "1": 0.5,  "2": 12.3,  "3": 87.5
    },
    "extract_success_rate_24h": 0.98
  }
}

Response 503 (degraded):
{
  "worker": {"status": "stopped", ...},
  "queue": {...},
  "alerts": [
    {"code": "WORKER_NOT_RUNNING", "since": "2026-05-10T07:00:00Z"},
    {"code": "OLDEST_QUEUED_OVER_5MIN", "value_sec": 312}
  ]
}
```

**ใช้งาน:**
- Fly.io health check probe → ถ้า /healthz/queue 503 → restart machine
- Frontend banner: ถ้า status != running → แสดง "ระบบประมวลผลล่าช้า" (TC-6)

### 9.2 Structured Log Lines

ทุก state transition + worker action ต้อง log ในรูปแบบ structured (JSON-parseable):

```python
logger.info("upload_worker.claim_job", extra={
    "event": "claim_job",
    "file_id": file_id,
    "user_id": user_id,
    "filetype": ext,
    "wait_time_sec": wait_sec,
    "priority_class": priority_class,
})

logger.info("upload_worker.extract_done", extra={
    "event": "extract_done",
    "file_id": file_id,
    "duration_sec": duration,
    "extraction_status": ext_status,
    "text_length": len(text),
})

logger.warning("upload_worker.extract_failed", extra={
    "event": "extract_failed",
    "file_id": file_id,
    "error_class": type(exc).__name__,
    "error_message": str(exc)[:200],
    "attempt_count": attempt_count,
})

logger.info("upload_worker.recovered_stale", extra={
    "event": "recovered_stale",
    "count": rowcount,
})
```

Fly.io logs ค้นได้ด้วย `fly logs | grep '"event":"extract_failed"'`

### 9.3 Worker Heartbeat

Worker เขียน timestamp ไป `data/worker_heartbeat.txt` ทุก 10 วินาที (เริ่มทุก loop):
```
async def _heartbeat():
    HEARTBEAT_FILE.write_text(datetime.utcnow().isoformat())
```

`/healthz/queue` อ่าน file นี้ → ถ้าค่าเก่ากว่า 30s → status='crashed'

---

## 📁 10. Files to Create / Modify

### Backend (6 modify + 1 create) · v2 includes M-3 WAL + M-4 reprocess/promote refactor

| File | Action | สิ่งที่ทำ |
|---|---|---|
| `backend/database.py` | modify | **WAL mode setup** (M-3 v2) + 7 columns ใน `files` + 2 indexes + idempotent migration v9.4.0 + backfill `processing` → `queued` |
| `backend/main.py` | modify | refactor `/api/upload` (save+queue) + **refactor `/api/files/{id}/reprocess` + `/api/files/{id}/promote` ให้ enqueue** (M-4 v2) + 4 endpoints ใหม่ (status/retry/dismiss-error/healthz) + register worker startup/shutdown + SKIP_TEMPLATES extension + explicit `func` import (M-2 v2) |
| `backend/upload_worker.py` | **create** | ~330 บรรทัด: queue poll + atomic claim (round-robin · **safer SQL pattern via SQLAlchemy ORM** M-10 v2) + extract dispatch + progress reporter (throttled) + recovery + heartbeat + Drive push |
| `backend/extraction.py` | modify | เพิ่ม optional `progress_callback` ใน `extract_text` + `_extract_pdf_basic` + `_extract_pdf_ocr` + `_extract_image_ocr` |
| `backend/ai_ingest.py` | modify | เพิ่ม optional `progress_callback` ใน `ingest_via_ai` + `_ingest_audio` + `_ingest_video` |
| `backend/plan_limits.py` | modify | เพิ่ม `upload_queue_cap` 3 tiers (Free 10, Starter 50, Admin 200) |
| `backend/config.py` | modify | bump `APP_VERSION` 9.3.4 → 9.4.0 |

### Frontend (3 modify + 0 create)

| File | Action | สิ่งที่ทำ |
|---|---|---|
| `legacy-frontend/app.js` | modify | **extend `t(key, vars)` to support variable substitution** (M-9 v2) + เปลี่ยน `uploadFiles()` flow + เพิ่ม `UploadTray` namespace (~300 บรรทัด) + **i18n keys (25 keys × TH+EN = 50 entries) ใน `I18N.th` + `I18N.en` blocks** (M-1 v2) + `openIfHasItems` ใน `showApp()` |
| `legacy-frontend/styles.css` | modify | เพิ่ม `.upload-tray` + child elements (~150 บรรทัด) — token-only + atom reuse + `.meter.is-indeterminate` modifier |
| `legacy-frontend/app.html` | modify | bump version label + cache-bust `?v=9.4.0` |

### Tests (3 create — สำหรับฟ้า · v2 expanded for reprocess/promote)

| File | Cases | สิ่งที่ test |
|---|---|---|
| `scripts/upload_queue_smoke.py` | **48 cases** (was 40) | queue lifecycle, fairness, recovery, retry, race, multi-user, per-plan caps + **reprocess/promote enqueue** + WAL mode |
| `tests/e2e-ui/v9.4.0-upload-tray.spec.js` | 15 cases | tray DOM, polling, render, retry button, persistence on reload, mobile, reduced-motion + **EN+TH i18n verify** |
| `tests/test_upload_progress.py` | 20 cases | progress_callback wiring, error mapping, throttle, healthz endpoint |

### Memory updates

| File | Action |
|---|---|
| `.agent-memory/contracts/data-models.md` | document `files` table v9.4.0 columns |
| `.agent-memory/contracts/api-spec.md` | document 4 new/changed endpoints + healthz |
| `.agent-memory/current/pipeline-state.md` | state `plan_pending_approval` |
| `.agent-memory/current/active-tasks.md` | update |
| `.agent-memory/current/last-session.md` | update |

---

## 💾 11. Data Model + Migration

### 11.1 Schema changes (`files` table — ADD only, no drop/rename)

| Column | Type | Default | Purpose |
|---|---|---|---|
| `progress_step` | TEXT | NULL | TH text 3-80 chars: "OCR หน้า 5/12", "Gemini ถอดเสียง" |
| `progress_pct` | INTEGER | NULL | 0-100 ถ้ารู้ NULL ถ้าไม่รู้ (TC-1 — no fake) |
| `queued_at` | DATETIME | NULL | TC-2 stage timestamp #1 |
| `extract_started_at` | DATETIME | NULL | TC-2 stage timestamp #2 |
| `extract_completed_at` | DATETIME | NULL | TC-2 stage timestamp #3 |
| `extract_error` | TEXT | NULL | TH error message (TC-5), 3-200 chars |
| `attempt_count` | INTEGER | 0 | retry counter (INV-4) |

**Indexes:**
- `idx_files_queue_poll` ON `files(processing_status, queued_at)` — worker poll
- `idx_files_user_status` ON `files(user_id, processing_status)` — `/api/upload-status`

### 11.2 `processing_status` enum extended

```
queued        ← NEW: รออันดับใน queue
extracting    ← NEW: worker หยิบทำอยู่
uploaded      (เดิม) extract เสร็จ รอ AI
organized     (เดิม)
ready         (เดิม)
error         (เดิม) — แต่ตอนนี้ต้องมี extract_error
vault_only    (เดิม)
processing    (legacy) — backfill เป็น queued ตอน migrate
reprocessed   (เดิม)
```

### 11.3 Migration code (idempotent — เพิ่มใน `init_db()` หลัง v9.1.0 block)

#### 11.3.0 Enable WAL mode FIRST (M-3 fix · ก่อน migration block ทั้งหมด)

> **WHY:** v9.4.0 worker เขียน progress columns ทุก 1.5s ขณะ /api/upload เขียน placeholder row พร้อมกัน → SQLite default `journal_mode=DELETE` จะ lock ทั้ง file → เกิด `OperationalError: database is locked`
> **WAL mode** = readers ไม่ block writer, writer ไม่ block readers → safer สำหรับ concurrent write
> **Idempotent:** PRAGMA `journal_mode` set ครั้งเดียว persistent ใน DB file — re-run safe

```python
# v9.4.0 — Enable WAL mode (ใส่ที่จุดแรกของ init_db() block หลัง engine connect แต่ก่อน migrations)
try:
    journal_mode_row = await db.execute("PRAGMA journal_mode=WAL")
    journal_mode = (await journal_mode_row.fetchone())[0]
    if journal_mode.lower() == "wal":
        print(f"  → SQLite journal_mode = WAL (concurrent-safe)")
    else:
        print(f"  ⚠️ SQLite journal_mode = {journal_mode} (expected WAL — concurrent risk)")
except Exception as e:
    print(f"  ⚠️ PRAGMA journal_mode set warning: {e}")
```

#### 11.3.1 v9.4.0 column migrations (block หลัง v9.1.0)

```python
# v9.4.0 Migration — Upload Queue + Visible Progress columns
# ⚠️ ADD-only, no drop/rename — Fly volume DB-safe
result_v940 = await db.execute("PRAGMA table_info(files)")
file_cols_v940 = {row[1] for row in await result_v940.fetchall()}

_v940_adds = [
    ("progress_step",        "TEXT"),
    ("progress_pct",         "INTEGER"),
    ("queued_at",            "DATETIME"),
    ("extract_started_at",   "DATETIME"),
    ("extract_completed_at", "DATETIME"),
    ("extract_error",        "TEXT"),
    ("attempt_count",        "INTEGER DEFAULT 0"),
]
for col_name, col_type in _v940_adds:
    if col_name not in file_cols_v940:
        await db.execute(f"ALTER TABLE files ADD COLUMN {col_name} {col_type}")
        migrated = True
        print(f"  → Added: files.{col_name} (v9.4.0 — Upload Queue)")

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

# Backfill: processing (legacy stuck) → queued
backfill_res = await db.execute(
    "UPDATE files SET "
    "  processing_status='queued', "
    "  queued_at=COALESCE(queued_at, uploaded_at) "
    "WHERE processing_status='processing' AND extracted_text=''"
)
if getattr(backfill_res, 'rowcount', 0):
    print(f"  → Backfilled {backfill_res.rowcount} stuck rows: processing → queued")
    migrated = True
```

### 11.4 Migration Verification SQL (รันหลัง migrate เพื่อ confirm)

```sql
-- ตรวจ 7 columns ใหม่
SELECT name FROM pragma_table_info('files')
WHERE name IN ('progress_step','progress_pct','queued_at',
               'extract_started_at','extract_completed_at',
               'extract_error','attempt_count');
-- ต้องคืน 7 rows

-- ตรวจ 2 indexes
SELECT name FROM sqlite_master WHERE type='index'
AND name IN ('idx_files_queue_poll','idx_files_user_status');
-- ต้องคืน 2 rows

-- ตรวจไม่มี row ค้าง processing
SELECT COUNT(*) FROM files WHERE processing_status='processing' AND extracted_text='';
-- ต้องคืน 0

-- ตรวจ INV-1: extracting ทุก row ต้องมี extract_started_at
SELECT COUNT(*) FROM files WHERE processing_status='extracting' AND extract_started_at IS NULL;
-- ต้องคืน 0

-- ตรวจ INV-7: progress_pct range
SELECT COUNT(*) FROM files WHERE progress_pct IS NOT NULL AND (progress_pct < 0 OR progress_pct > 100);
-- ต้องคืน 0
```

---

## 📡 12. API Specification (with curl)

### 12.1 POST /api/upload (BREAKING shape, semantic preserved)

**Auth:** Required (JWT)
**Request:** multipart form-data, field `files` (1 file/request, frontend pool ส่ง 3 ขนาน) — ไม่เปลี่ยน

**Response 200 (changed):**
```json
{
  "uploaded": [{
    "id": "abc123def456",
    "filename": "doc.pdf",
    "filetype": "pdf",
    "uploaded_at": "2026-05-10T07:14:22Z",
    "processing_status": "queued",
    "queue_position": 3,
    "estimated_wait_sec": 45,
    "estimated_wait_source": "rolling_avg",
    "file_kind": "processed"
  }],
  "count": 1,
  "skipped": []
}
```

**Field changes vs v9.3.4:**
- ❌ ลบ `text_length` (extract ยังไม่เสร็จ — TC-1 no-fake)
- ➕ `queue_position` (1-based, อันดับใน queue ของ user คนนี้)
- ➕ `estimated_wait_sec` — calc จาก rolling avg (TC-4) — `null` ถ้าไม่รู้
- ➕ `estimated_wait_source` — `"rolling_avg"` | `"unknown"` (TC-4)
- 🔁 `processing_status` = `"queued"` แทน `"uploaded"`

**Skip codes (เพิ่ม):**
- ➕ `QUEUE_FULL` — user คนนี้มี queued/extracting >= upload_queue_cap

**curl example:**
```bash
curl -X POST https://personaldatabank.fly.dev/api/upload \
  -H "Authorization: Bearer $JWT" \
  -F "files=@document.pdf"
```

### 12.2 GET /api/upload-status (NEW)

**Auth:** Required (JWT)

**Response 200:**
```json
{
  "active": [
    {
      "id": "abc123",
      "filename": "เอกสาร.pdf",
      "filetype": "pdf",
      "processing_status": "extracting",
      "extraction_status": "pending",
      "queue_position": 0,
      "progress_step": "OCR หน้า 5 จาก 12",
      "progress_pct": 42,
      "progress_pct_known": true,
      "stages": {
        "queued_at":            "2026-05-10T07:14:22Z",
        "extract_started_at":   "2026-05-10T07:14:24Z",
        "extract_completed_at": null
      },
      "elapsed_sec": 18,
      "attempt_count": 0,
      "is_retryable": false,
      "why_slow": "ไฟล์ใหญ่ 12 หน้า — OCR ใช้เวลานาน"
    },
    {
      "id": "xyz789",
      "filename": "voice.m4a",
      "filetype": "m4a",
      "processing_status": "queued",
      "queue_position": 1,
      "progress_step": "อันดับที่ 1 — กำลังรอคิว",
      "progress_pct": null,
      "progress_pct_known": false,
      "stages": {
        "queued_at": "2026-05-10T07:14:25Z",
        "extract_started_at": null,
        "extract_completed_at": null
      },
      "elapsed_sec": 16,
      "attempt_count": 0,
      "is_retryable": false,
      "why_slow": null
    }
  ],
  "failed": [
    {
      "id": "fail001",
      "filename": "broken.pdf",
      "filetype": "pdf",
      "processing_status": "error",
      "extraction_status": "encrypted",
      "extract_error": "ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปใหม่",
      "attempt_count": 1,
      "is_retryable": true,
      "stages": {
        "queued_at":            "2026-05-10T07:13:01Z",
        "extract_started_at":   "2026-05-10T07:13:05Z",
        "extract_completed_at": "2026-05-10T07:13:18Z"
      }
    }
  ],
  "summary": {
    "queued_count": 1,
    "extracting_count": 1,
    "failed_count": 1,
    "total_active": 2,
    "system_status": "ok"
  }
}
```

**`system_status` values:**
- `"ok"` — ปกติ
- `"degraded"` — worker crash > 3 ครั้งใน 5 นาที หรือ oldest queued > 5 นาที
- `"stopped"` — worker ไม่ตอบ heartbeat

**curl:**
```bash
curl -H "Authorization: Bearer $JWT" \
  https://personaldatabank.fly.dev/api/upload-status
```

### 12.3 POST /api/upload/{file_id}/retry (NEW)

**Auth:** Required + ownership check

**Response 200:**
```json
{
  "id": "fail001",
  "processing_status": "queued",
  "queue_position": 4,
  "estimated_wait_sec": 60,
  "attempt_count": 2
}
```

**Errors:**
- 401 `UNAUTHORIZED`
- 403 `FORBIDDEN` — file ไม่ใช่ของ user
- 404 `FILE_NOT_FOUND`
- 409 `NOT_RETRYABLE` — status ≠ error หรือ attempt_count ≥ 3
- 410 `FILE_GONE` — raw_path ไม่อยู่บน disk แล้ว

### 12.4 POST /api/upload/{file_id}/dismiss-error (NEW)

**Auth:** Required + ownership

**Response 200:** `{"deleted": true}`

ลบ row + raw file + Drive copy (ถ้ามี)

### 12.5 GET /api/healthz/queue (NEW — public)

ดู §9.1

**curl:**
```bash
curl https://personaldatabank.fly.dev/api/healthz/queue
```

### 12.6 Error Code Catalog (Appendix A reference)

| HTTP | Code | TH Message | Action |
|---|---|---|---|
| 401 | `UNAUTHORIZED` | "เซสชันหมดอายุ — กรุณาเข้าสู่ระบบใหม่" | redirect login |
| 403 | `FORBIDDEN` | "ไม่มีสิทธิ์เข้าถึงไฟล์นี้" | toast |
| 404 | `FILE_NOT_FOUND` | "ไม่พบไฟล์" | refresh list |
| 409 | `NOT_RETRYABLE` | "ไฟล์นี้ลองใหม่ไม่ได้ — กรุณาอัปใหม่" | upload flow |
| 410 | `FILE_GONE` | "ไฟล์ดิบหายไปแล้ว — ต้องอัปใหม่" | upload flow |
| 413 | `FILE_TOO_LARGE` | "ไฟล์ใหญ่เกิน {limit}MB" | (existing) |
| 429 | `QUEUE_FULL` | "คิวเต็ม ({limit} ไฟล์) — รอบางไฟล์เสร็จก่อน" | (new) |

---

## 🔧 13. Implementation Plan (full code, สำหรับเขียว)

> ทำตามลำดับ Step 1 → Step 10. ทุก step มี self-test ก่อนข้าม

### Step 1 — DB Schema + Migration ([database.py](../../backend/database.py))

#### 1.1 เพิ่ม columns ใน `class File` (block หลัง `file_kind`)

```python
# ─── v9.4.0 — Upload Queue + Visible Progress ───
# ทำไมเพิ่ม 7 columns:
# v9.3.4 ทำ extract แบบ inline ใน /api/upload → request ค้าง 30-120s
# v9.4.0 แยกเป็น save+queue + worker async + UI tray ที่ user เห็นทุกขั้น
# (ดู truthfulness contract ใน plan)

# TC-1: ห้ามโชว์ progress ปลอม — pct=NULL ถ้าไม่รู้
progress_step = Column(Text, nullable=True)
progress_pct = Column(Integer, nullable=True)

# TC-2: stage timestamps จริง (3 จุดของ lifecycle)
queued_at = Column(DateTime, nullable=True)
extract_started_at = Column(DateTime, nullable=True)
extract_completed_at = Column(DateTime, nullable=True)

# TC-5: error message ที่ระบุสาเหตุจริงเป็นภาษาไทย
extract_error = Column(Text, nullable=True)

# INV-4: retry counter — ห้ามเกิน MAX_RETRY_ATTEMPTS (3)
attempt_count = Column(Integer, default=0)
```

#### 1.2 Migration block (ใน `init_db()` หลัง v9.1.0)

[ดูโค้ดเต็มใน §11.3]

**Self-test:**
- ลบ test DB → run startup → ตรวจ pragma
- รัน 5 verification queries (§11.4) ทั้งหมดต้อง return ตาม expected

### Step 2 — `backend/upload_worker.py` (สร้างใหม่)

```python
"""Upload worker — async background processor (v9.4.0).

โมดูลนี้ทำหน้าที่:
1. Poll DB queue ทุก 2s หาไฟล์ที่ status='queued'
2. Atomic claim 1 ไฟล์ (round-robin per-user + priority by ext-class)
3. รัน extract_text หรือ ai_ingest พร้อม progress callback
4. Update DB row ตอนเสร็จ + push ไป Drive (BYOS)
5. Recovery — reset stale 'extracting' (> 30 นาที) → 'queued' ตอน startup
6. Heartbeat — เขียน timestamp ไป file ทุก loop iteration

⚠️ ห้ามทำ:
- Multi-process parallel (single in-process task เท่านั้น)
- Block event loop ด้วย sync IO (extract_text ต้อง wrap asyncio.to_thread)
- Update progress ถี่กว่า PROGRESS_DB_THROTTLE_SEC
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Optional

from sqlalchemy import select, update, text as sql_text, func
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal, File
from .extraction import extract_text, classify_extraction_status, strip_surrogates
from .duplicate_detector import compute_content_hash
from .ai_ingest import ingest_via_ai, is_ai_format

logger = logging.getLogger(__name__)

# ─── Tunable constants ────────────────────────────────────
POLL_INTERVAL_SEC = float(os.getenv("UPLOAD_WORKER_POLL_SEC", "2.0"))
STALE_EXTRACT_TIMEOUT_SEC = int(os.getenv("UPLOAD_STALE_TIMEOUT_SEC", "1800"))  # 30 min
MAX_RETRY_ATTEMPTS = int(os.getenv("UPLOAD_MAX_RETRY", "3"))
PROGRESS_DB_THROTTLE_SEC = 1.5  # อย่า update DB ถี่กว่านี้
HEARTBEAT_FILE = Path(os.getenv("UPLOAD_HEARTBEAT_FILE", "data/worker_heartbeat.txt"))
HEARTBEAT_STALE_SEC = 30  # ถ้า heartbeat เก่ากว่านี้ → /healthz returns 503

# ─── Module state ─────────────────────────────────────────
_worker_task: asyncio.Task | None = None
_shutdown_event: asyncio.Event | None = None
_worker_started_at: datetime | None = None

# Rolling average per ext-class (for TC-4 truthful estimated_wait)
# Updated atomically after each successful extract.
_AVG_EXTRACT_SEC: dict[int, float] = {1: 1.0, 2: 15.0, 3: 90.0}
_AVG_SAMPLE_COUNT: dict[int, int] = {1: 0, 2: 0, 3: 0}

# Ext → priority class mapping
PRIORITY_CLASS_FAST = {  # priority 1
    "txt", "md", "csv", "png", "jpg", "jpeg", "webp", "heic", "heif",
    "gif", "bmp", "tiff", "tif", "py", "js", "ts", "jsx", "tsx", "css",
    "scss", "less", "sass", "xml", "yaml", "yml", "toml", "ini", "env",
    "conf", "cfg", "sh", "bash", "zsh", "bat", "ps1", "sql", "java",
    "kt", "swift", "c", "cpp", "h", "hpp", "cs", "go", "rs", "rb", "php",
    "log", "tsv", "vue", "svelte", "json", "html", "rtf",
}
PRIORITY_CLASS_DOC = {"pdf", "docx", "xlsx", "pptx"}  # priority 2
# audio/video → priority 3 (default)


def get_priority_class(ext: str) -> int:
    e = (ext or "").lower()
    if e in PRIORITY_CLASS_FAST:
        return 1
    if e in PRIORITY_CLASS_DOC:
        return 2
    return 3


def get_avg_sec(priority_class: int) -> float:
    """คืน rolling avg extract time สำหรับ priority class นี้ (TC-4)."""
    return _AVG_EXTRACT_SEC.get(priority_class, 30.0)


def update_avg_sec(priority_class: int, duration_sec: float) -> None:
    """Update rolling avg ด้วย exponential smoothing (alpha=0.2)."""
    cur = _AVG_EXTRACT_SEC.get(priority_class, duration_sec)
    new = 0.8 * cur + 0.2 * duration_sec
    _AVG_EXTRACT_SEC[priority_class] = round(new, 2)
    _AVG_SAMPLE_COUNT[priority_class] = _AVG_SAMPLE_COUNT.get(priority_class, 0) + 1


# ─── Public API ───────────────────────────────────────────

async def start_worker() -> None:
    """เรียกตอน FastAPI startup. Idempotent."""
    global _worker_task, _shutdown_event, _worker_started_at
    if _worker_task and not _worker_task.done():
        return
    _shutdown_event = asyncio.Event()
    await _recover_stale_jobs()
    _worker_started_at = datetime.utcnow()
    _worker_task = asyncio.create_task(_worker_loop(), name="upload_worker")
    logger.info("upload_worker.started")


async def stop_worker() -> None:
    """เรียกตอน shutdown. รอ task เสร็จ (max 5s)."""
    if _shutdown_event:
        _shutdown_event.set()
    if _worker_task:
        try:
            await asyncio.wait_for(_worker_task, timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning("upload_worker.stop_timeout")


def get_worker_health() -> dict:
    """ใช้ใน /api/healthz/queue (§9.1)."""
    now = datetime.utcnow()
    uptime = int((now - _worker_started_at).total_seconds()) if _worker_started_at else 0
    last_hb = _read_heartbeat()
    is_alive = bool(last_hb and (now - last_hb).total_seconds() < HEARTBEAT_STALE_SEC)
    status = "running" if is_alive else ("crashed" if _worker_task and _worker_task.done() else "stopped")
    return {
        "status": status,
        "uptime_sec": uptime,
        "last_heartbeat": last_hb.isoformat() + "Z" if last_hb else None,
        "concurrency": 1,
        "avg_extract_sec_by_class": dict(_AVG_EXTRACT_SEC),
    }


# ─── Internal ────────────────────────────────────────────

async def _worker_loop() -> None:
    """Main loop — poll DB, claim 1 job, process, repeat."""
    while not _shutdown_event.is_set():
        try:
            _write_heartbeat()
            claimed = await _claim_next_job()
            if claimed is None:
                # Idle — sleep until shutdown or next poll
                try:
                    await asyncio.wait_for(_shutdown_event.wait(), timeout=POLL_INTERVAL_SEC)
                except asyncio.TimeoutError:
                    pass
                continue
            await _process_job(claimed)
        except asyncio.CancelledError:
            logger.info("upload_worker.cancelled")
            return
        except Exception as e:
            logger.error("upload_worker.loop_error", extra={
                "event": "loop_error",
                "error_class": type(e).__name__,
                "error_message": str(e)[:200],
            }, exc_info=True)
            await asyncio.sleep(POLL_INTERVAL_SEC)


def _write_heartbeat() -> None:
    """Write timestamp to heartbeat file. Creates parent dir if missing."""
    try:
        HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT_FILE.write_text(datetime.utcnow().isoformat())
    except Exception as e:
        logger.warning("upload_worker.heartbeat_write_failed", extra={"error": str(e)[:100]})


def _read_heartbeat() -> datetime | None:
    try:
        if not HEARTBEAT_FILE.exists():
            return None
        return datetime.fromisoformat(HEARTBEAT_FILE.read_text().strip())
    except Exception:
        return None


async def _claim_next_job() -> dict | None:
    """Atomic claim: round-robin per-user + priority + queued_at.

    ใช้ ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY queued_at) เพื่อ fairness
    ระหว่าง user (ADR-006).

    M-10 fix v2: เลิกใช้ raw SQL f-string concat (เปราะ + อ่านยาก)
    → query file id ที่ status='queued' ทั้งหมดก่อน → คำนวณ priority + sort ใน Python
    → แล้วค่อย atomic claim ทีละ id. Performance OK เพราะคิวมักมี <1000 rows
    """
    async with AsyncSessionLocal() as db:
        # 1. หา candidate ทั้งหมดที่ queued (read-only · cheap query · index hit)
        rows = await db.execute(
            select(
                File.id, File.user_id, File.filename, File.filetype,
                File.raw_path, File.queued_at, File.attempt_count
            ).where(File.processing_status == "queued")
              .order_by(File.queued_at.asc())
        )
        candidates = rows.fetchall()
        if not candidates:
            return None

        # 2. Compute (user_pos, priority_class, queued_at) ใน Python — clearer + safer
        # Group by user → assign user_pos by queued_at ASC
        from collections import defaultdict
        per_user_count = defaultdict(int)
        ranked = []
        for c in candidates:
            per_user_count[c.user_id] += 1
            user_pos = per_user_count[c.user_id]
            priority = get_priority_class(c.filetype or "")
            ranked.append((user_pos, priority, c.queued_at, c))

        # 3. Sort: user_pos ASC (round-robin) → priority ASC → queued_at ASC
        ranked.sort(key=lambda r: (r[0], r[1], r[2] or datetime.utcnow()))
        candidate = ranked[0][3]

        # 4. Atomic claim — UPDATE WHERE status='queued' guards race (multi-worker safe)
        now = datetime.utcnow()
        result = await db.execute(
            update(File)
            .where(File.id == candidate.id, File.processing_status == "queued")
            .values(
                processing_status="extracting",
                extract_started_at=now,
                progress_step="เตรียมเริ่มประมวลผล",
                progress_pct=None,
            )
        )
        await db.commit()

        if result.rowcount != 1:
            # Lost race — คนอื่น claim ไปแล้ว (defense; worker=1 ไม่น่าเกิด)
            return None

        wait_sec = (now - candidate.queued_at).total_seconds() if candidate.queued_at else 0
        logger.info("upload_worker.claim_job", extra={
            "event": "claim_job",
            "file_id": candidate.id,
            "user_id": candidate.user_id,
            "filetype": candidate.filetype,
            "wait_time_sec": round(wait_sec, 2),
            "priority_class": candidate.priority_class,
            "attempt_count": candidate.attempt_count or 0,
        })

        return {
            "id": candidate.id,
            "user_id": candidate.user_id,
            "filename": candidate.filename,
            "filetype": candidate.filetype,
            "raw_path": candidate.raw_path,
            "priority_class": candidate.priority_class,
            "attempt_count": candidate.attempt_count or 0,
        }


async def _process_job(job: dict) -> None:
    """รัน extract สำหรับ 1 ไฟล์ + update progress ระหว่างทาง."""
    file_id = job["id"]
    raw_path = job["raw_path"]
    ext = (job["filetype"] or "").lower()
    started = time.monotonic()

    last_progress_write = 0.0

    async def _async_report(step: str, pct: int | None = None) -> None:
        """Async report — เรียกใน async context (ai_ingest)."""
        nonlocal last_progress_write
        now = time.monotonic()
        if now - last_progress_write < PROGRESS_DB_THROTTLE_SEC:
            return
        last_progress_write = now
        await _write_progress(file_id, step, pct)

    def _sync_report(step: str, pct: int | None = None) -> None:
        """Sync report — เรียกใน sync context (extract_text via to_thread).

        Schedule async write via call_soon_threadsafe.
        """
        nonlocal last_progress_write
        now = time.monotonic()
        if now - last_progress_write < PROGRESS_DB_THROTTLE_SEC:
            return
        last_progress_write = now
        loop = asyncio.get_event_loop()
        # โพสต์ async task ไป main event loop จาก worker thread
        asyncio.run_coroutine_threadsafe(
            _write_progress(file_id, step, pct), loop
        )

    try:
        await _async_report("เตรียมประมวลผล", 5)

        if is_ai_format(ext):
            await _async_report("อัปโหลดไป Gemini", 15)
            text = await ingest_via_ai(raw_path, ext, progress_callback=_async_report)
        else:
            await _async_report("กำลังอ่านข้อความในไฟล์", 20)
            text = await asyncio.to_thread(
                extract_text, raw_path, ext, progress_callback=_sync_report
            )

        text = strip_surrogates(text)
        content_hash = compute_content_hash(text)
        ext_status = classify_extraction_status(text)

        await _async_report("บันทึกผลลัพธ์", 95)

        async with AsyncSessionLocal() as db:
            await db.execute(update(File).where(File.id == file_id).values(
                extracted_text=text,
                content_hash=content_hash,
                extraction_status=ext_status,
                processing_status="uploaded",
                progress_step=None,
                progress_pct=100,
                extract_completed_at=datetime.utcnow(),
                extract_error=None,
            ))
            await db.commit()

        duration = time.monotonic() - started
        update_avg_sec(job["priority_class"], duration)
        logger.info("upload_worker.extract_done", extra={
            "event": "extract_done",
            "file_id": file_id,
            "duration_sec": round(duration, 2),
            "extraction_status": ext_status,
            "text_length": len(text),
            "priority_class": job["priority_class"],
        })

        # Drive push สำหรับ BYOS users (post-extract)
        await _push_to_drive_if_byos(file_id)

    except Exception as e:
        duration = time.monotonic() - started
        logger.error("upload_worker.extract_failed", extra={
            "event": "extract_failed",
            "file_id": file_id,
            "duration_sec": round(duration, 2),
            "error_class": type(e).__name__,
            "error_message": str(e)[:200],
            "attempt_count": job["attempt_count"],
        }, exc_info=True)
        await _mark_job_failed(file_id, e)


async def _write_progress(file_id: str, step: str, pct: int | None) -> None:
    """Update progress columns. Throttled by caller."""
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(update(File).where(File.id == file_id).values(
                progress_step=step[:200],  # safety cap
                progress_pct=pct if (pct is None or 0 <= pct <= 100) else None,
            ))
            await db.commit()
    except Exception as e:
        logger.warning("upload_worker.progress_write_failed", extra={
            "file_id": file_id, "error": str(e)[:100],
        })


async def _mark_job_failed(file_id: str, exc: Exception) -> None:
    """Set status='error' + TC-5 truthful TH message."""
    msg = format_user_error(exc)
    try:
        async with AsyncSessionLocal() as db:
            # อ่าน file เพื่อดู extension → คาดเดา extraction_status ที่เหมาะสม
            row = await db.execute(select(File).where(File.id == file_id))
            f = row.scalar_one_or_none()
            ext_status = "ocr_failed"
            if f:
                if "encrypted" in msg.lower() or "เข้ารหัส" in msg:
                    ext_status = "encrypted"
                elif "ไม่รองรับ" in msg:
                    ext_status = "unsupported"

            await db.execute(update(File).where(File.id == file_id).values(
                processing_status="error",
                extraction_status=ext_status,
                extract_completed_at=datetime.utcnow(),
                extract_error=msg,
                progress_step=None,
                progress_pct=None,
            ))
            await db.commit()
    except Exception as e:
        logger.error("upload_worker.mark_failed_error", extra={
            "file_id": file_id, "error": str(e)[:100],
        })


def format_user_error(exc: Exception) -> str:
    """แปลง exception → TH message ที่ user friendly (TC-5).

    Mapping ตาม Appendix A ของ plan. Default = "ประมวลผลล้มเหลว"
    """
    name = type(exc).__name__
    s = str(exc)[:200]
    s_lower = s.lower()

    # PDF encrypted
    if "encrypted" in s_lower or "password" in s_lower:
        return "ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปโหลดใหม่"

    # File not found / disk error
    if "no such file" in s_lower or "filenotfound" in name.lower():
        return "ไฟล์ดิบหายไประหว่างประมวลผล — ต้องอัปโหลดใหม่"

    # Timeout
    if "timeout" in s_lower or "timed out" in s_lower:
        return "ประมวลผลใช้เวลานานเกินกำหนด — ลองแบ่งไฟล์เล็กลงหรือกดลองใหม่"

    # Memory
    if "memory" in s_lower or name == "MemoryError":
        return "ไฟล์ใหญ่เกินที่ระบบรับไหว — ลองแบ่งไฟล์เล็กลง"

    # Encoding
    if name in ("UnicodeDecodeError", "UnicodeEncodeError"):
        return "ไฟล์มี encoding ผิดปกติ — ลอง re-save เป็น UTF-8 แล้วอัปใหม่"

    # Gemini quota / API errors
    if "quota" in s_lower or "rate limit" in s_lower or "429" in s:
        return "Gemini API ใช้เกินโควต้า — รอเดือนหน้าหรือเปลี่ยนแพลน"
    if "google" in s_lower and ("503" in s or "unavailable" in s_lower):
        return "Gemini ตอบช้ากว่าปกติ — กดลองใหม่อีกครั้ง"
    if "google" in s_lower and "auth" in s_lower:
        return "Gemini API key ไม่ถูกต้อง — ติดต่อแอดมิน"

    # Tesseract
    if "tesseract" in s_lower:
        return "OCR engine ขัดข้อง — ลองอัปใหม่หรือใช้ไฟล์ text แทนรูป"

    # Network
    if "connection" in s_lower or "network" in s_lower:
        return "ปัญหาเครือข่าย — กดลองใหม่อีกครั้ง"

    # Default
    return f"ประมวลผลล้มเหลว ({name}) — กดลองใหม่หรือติดต่อแอดมิน"


async def _recover_stale_jobs() -> None:
    """Reset stuck 'extracting' jobs (> STALE_EXTRACT_TIMEOUT_SEC) → 'queued'."""
    cutoff = datetime.utcnow() - timedelta(seconds=STALE_EXTRACT_TIMEOUT_SEC)
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(update(File).where(
                File.processing_status == "extracting",
                File.extract_started_at < cutoff,
            ).values(
                processing_status="queued",
                extract_started_at=None,
                progress_step=None,
                progress_pct=None,
            ))
            await db.commit()
            if result.rowcount:
                logger.warning("upload_worker.recovered_stale", extra={
                    "event": "recovered_stale",
                    "count": result.rowcount,
                    "cutoff": cutoff.isoformat(),
                })
    except Exception as e:
        logger.error("upload_worker.recovery_error", extra={"error": str(e)[:200]})


async def _push_to_drive_if_byos(file_id: str) -> None:
    """Drive push หลัง extract เสร็จ — best-effort (Drive = mirror, DB = truth)."""
    try:
        async with AsyncSessionLocal() as db:
            row = await db.execute(select(File).where(File.id == file_id))
            f = row.scalar_one_or_none()
            if not f or not f.raw_path or not os.path.exists(f.raw_path):
                return

            from .storage_router import (
                push_extracted_text_to_drive_if_byos,
                push_raw_file_to_drive_if_byos,
            )
            from .main import _guess_mime  # ใน production แยก helper module ดีกว่า

            with open(f.raw_path, "rb") as fp:
                contents = fp.read()
            mime = _guess_mime(f.filetype, None)

            drive_id = await push_raw_file_to_drive_if_byos(
                f.user_id, db, f.id, f.filename, contents, mime,
            )
            if drive_id and f.extracted_text:
                await push_extracted_text_to_drive_if_byos(
                    f.user_id, db, f.id, f.extracted_text,
                )
    except Exception as e:
        logger.warning("upload_worker.drive_push_failed", extra={
            "file_id": file_id, "error": str(e)[:200],
        })
```

**Self-test (เขียวรันก่อนข้าม):**
- Insert row status='queued' → start worker → wait 5s → confirm extracted
- Insert 2 users × 5 ไฟล์ → confirm round-robin (A1 → B1 → A2 → A3 → ...)
- Kill worker mid-extract → restart → recovered
- Throw exception → confirm extract_error TH message
- /healthz/queue คืน status='running' + uptime + heartbeat

### Step 3 — `extraction.py` progress_callback patches

แก้ signature:
```python
def extract_text(filepath: str, filetype: str, progress_callback: Callable[[str, int|None], None] | None = None) -> str:
    return strip_surrogates(_extract_text_raw(filepath, filetype, progress_callback))
```

จุดที่ต้อง report:
- `_extract_pdf_basic` PyPDF2 page loop:
  ```python
  for i, page in enumerate(reader.pages):
      if progress_callback:
          progress_callback(f"อ่าน PDF หน้า {i+1}/{total_pages}", int((i+1)/total_pages * 60))
      text += page.extract_text()
  ```
- `_extract_pdf_ocr` OCR page loop:
  ```python
  for i, img in enumerate(images):
      if progress_callback:
          progress_callback(f"OCR หน้า {i+1}/{total}", int(20 + (i+1)/total * 70))
      ocr_text = pytesseract.image_to_string(img, lang="tha+eng")
  ```
- `_extract_image_ocr`:
  ```python
  if progress_callback:
      progress_callback("OCR รูปภาพ", 50)
  ```

**Backward compat:** `progress_callback=None` = no-op

### Step 4 — `ai_ingest.py` progress_callback patches

```python
async def ingest_via_ai(filepath: str, filetype: str,
                        progress_callback=None) -> str:
    if progress_callback:
        await progress_callback("กำลังเตรียมไฟล์สำหรับ Gemini", 10)
    # ...
    if progress_callback:
        await progress_callback("อัปโหลดไป Gemini Files API", 30)
    file_handle = await _upload_to_gemini(filepath)
    if progress_callback:
        # หมายเหตุ: Gemini transcribe ไม่ stream % ได้ → bool no-pct (TC-1)
        await progress_callback(f"Gemini ถอดเสียง/วิเคราะห์ ({filetype})", None)
    # ... call Gemini ...
    if progress_callback:
        await progress_callback("รับผลลัพธ์จาก Gemini", 90)
```

### Step 5 — `main.py` refactor `/api/upload`

โค้ดใหม่ของ `upload_files`:

```python
@app.post("/api/upload")
async def upload_files(
    files: list[UploadFile],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.4.0 — save + queue mode.

    Extract + AI ingest ย้ายไป upload_worker (background async loop).
    Returns ทันที (~100-200ms ต่อไฟล์ vs 30-120s ใน v9.3.4).
    """
    # M-2 fix v2: explicit imports (pattern เดิมใน main.py = local import inside function · ดู line 730)
    from sqlalchemy import func
    from .upload_worker import get_priority_class, get_avg_sec

    uploaded = []
    skipped = []
    _limits = get_limits(current_user)
    allowed_types = _limits["allowed_file_types"]
    max_bytes = _limits["max_file_size_mb"] * 1024 * 1024
    file_limit = _limits["file_limit"]
    queue_cap = _limits.get("upload_queue_cap", 10)

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
            skipped.append(_make_skip("FILE_TOO_LARGE", original_name,
                                     limit=_limits["max_file_size_mb"]))
            continue

        file_id = gen_id()
        user_upload_dir = os.path.join(UPLOAD_DIR, current_user.id)
        os.makedirs(user_upload_dir, exist_ok=True)
        safe_filename = f"{file_id}_{original_name}"
        raw_path = os.path.join(user_upload_dir, safe_filename)

        async with quota_lock:
            live_count = await get_file_count(db, current_user.id)
            if live_count >= file_limit:
                skipped.append(_make_skip("QUOTA_EXCEEDED", original_name, limit=file_limit))
                continue

            # v9.4.0 — per-plan tier queue cap (ADR-007)
            queue_count = await db.scalar(
                select(func.count()).select_from(File).where(
                    File.user_id == current_user.id,
                    File.processing_status.in_(["queued", "extracting"]),
                )
            )
            if (queue_count or 0) >= queue_cap:
                skipped.append(_make_skip("QUEUE_FULL", original_name, limit=queue_cap))
                continue

            now = datetime.utcnow()
            if is_vault:
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
                    processing_status="queued",
                    content_hash=None,
                    extraction_status="pending",
                    file_kind="processed",
                    queued_at=now,
                )
            db.add(placeholder)
            await db.commit()

        # ของหนักทำนอก lock — IO disk
        with open(raw_path, "wb") as f:
            f.write(contents)

        # คำนวณ queue_position + estimated_wait (TC-4 truthful)
        if is_vault:
            queue_position = 0
            estimated_wait_sec = 0
            wait_source = "rolling_avg"
        else:
            qp_res = await db.execute(
                select(File.filetype).where(
                    File.user_id == current_user.id,
                    File.processing_status == "queued",
                    File.queued_at <= now,
                )
            )
            ahead = qp_res.fetchall()
            queue_position = len(ahead)
            estimated_wait_sec = sum(get_avg_sec(get_priority_class(f[0])) for f in ahead)
            wait_source = "rolling_avg"

        uploaded.append({
            "id": file_id,
            "filename": original_name,
            "filetype": ext,
            "uploaded_at": now.isoformat() + "Z",
            "processing_status": placeholder.processing_status,
            "queue_position": queue_position,
            "estimated_wait_sec": int(estimated_wait_sec),
            "estimated_wait_source": wait_source,
            "file_kind": placeholder.file_kind,
        })

    return {"uploaded": uploaded, "count": len(uploaded), "skipped": skipped}
```

#### 5.2 SKIP_TEMPLATES extension

```python
SKIP_TEMPLATES = {
    "UNSUPPORTED_TYPE": {...},  # existing
    "FILE_TOO_LARGE":  {...},
    "QUOTA_EXCEEDED":  {...},
    "EMPTY_FILE":      {...},
    # v9.4.0
    "QUEUE_FULL": {
        "message": "คิว upload เต็ม ({limit} ไฟล์) — รอบางไฟล์เสร็จก่อน",
        "suggestion": "รอประมาณ 1-2 นาทีแล้วลองอีกครั้ง หรืออัปเกรดแพลน",
    },
}
```

#### 5.3 Endpoint /api/upload-status

[ดูตัวอย่างเต็มใน plan v1 §5.2 — โค้ดเดียวกัน + เพิ่มอีก 2 fields]

เพิ่ม fields ใน active payload:
- `progress_pct_known: bool` (true ถ้า progress_pct != null)
- `stages: {queued_at, extract_started_at, extract_completed_at}`
- `elapsed_sec: int` (computed: now - queued_at หรือ now - extract_started_at)
- `why_slow: str | null` (computed from progress_step + filetype)

Helper สำหรับ `why_slow`:
```python
def _why_slow(f: File) -> str | None:
    if f.processing_status == "queued" and f.queue_position > 3:
        return f"อันดับ {f.queue_position} — รอประมาณ {f.estimated_wait_sec} วินาที"
    if f.processing_status == "extracting":
        if f.filetype in ("pdf", "docx") and f.progress_step and "OCR" in f.progress_step:
            return "ไฟล์ใหญ่ — OCR ใช้เวลานาน"
        if f.filetype in ai_ingest.AUDIO_FORMATS:
            return "Gemini ถอดเสียง — รอประมาณ 1-3 นาที"
        if f.filetype in ai_ingest.VIDEO_FORMATS:
            return "Gemini วิเคราะห์วิดีโอ — รอประมาณ 2-5 นาที"
    return None
```

System status (queue summary):
```python
def _system_status(active_files, worker_health) -> str:
    if worker_health["status"] != "running":
        return "stopped"
    if active_files:
        oldest = min(f.queued_at for f in active_files if f.queued_at)
        if (datetime.utcnow() - oldest).total_seconds() > 300:
            return "degraded"
    return "ok"
```

#### 5.4 Endpoint /api/upload/{id}/retry

[ดูตัวอย่างเต็มใน plan v1 §5.3]

#### 5.5 Endpoint /api/upload/{id}/dismiss-error

```python
@app.post("/api/upload/{file_id}/dismiss-error")
async def dismiss_error(file_id: str,
                        current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    f = res.scalar_one_or_none()
    if not f:
        raise HTTPException(404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}})
    if f.processing_status != "error":
        raise HTTPException(409, detail={"error": {"code": "NOT_DISMISSIBLE", "message": "ไฟล์นี้ไม่ใช่สถานะ error"}})

    # ลบ raw file
    if f.raw_path and os.path.exists(f.raw_path):
        try:
            os.remove(f.raw_path)
        except OSError:
            pass

    # ลบ Drive copy (BYOS)
    try:
        from .storage_router import delete_drive_file_if_byos
        await delete_drive_file_if_byos(current_user.id, db, file_id)
    except Exception as e:
        logger.warning(f"Drive delete failed for {file_id}: {e}")

    # ลบ DB row
    await db.delete(f)
    await db.commit()
    return {"deleted": True}
```

#### 5.6 Endpoint /api/healthz/queue

```python
@app.get("/api/healthz/queue")
async def healthz_queue(db: AsyncSession = Depends(get_db)):
    from .upload_worker import get_worker_health

    worker = get_worker_health()
    queued = await db.scalar(select(func.count()).select_from(File)
                             .where(File.processing_status == "queued"))
    extracting = await db.scalar(select(func.count()).select_from(File)
                                 .where(File.processing_status == "extracting"))
    error_24h = await db.scalar(select(func.count()).select_from(File).where(
        File.processing_status == "error",
        File.extract_completed_at >= datetime.utcnow() - timedelta(hours=24),
    ))

    oldest_queued = await db.scalar(select(func.min(File.queued_at))
                                    .where(File.processing_status == "queued"))
    oldest_age = int((datetime.utcnow() - oldest_queued).total_seconds()) if oldest_queued else 0

    success_24h = await db.scalar(select(func.count()).select_from(File).where(
        File.processing_status == "uploaded",
        File.extract_completed_at >= datetime.utcnow() - timedelta(hours=24),
    ))
    total_24h = (success_24h or 0) + (error_24h or 0)
    success_rate = round((success_24h or 0) / total_24h, 3) if total_24h > 0 else 1.0

    body = {
        "worker": worker,
        "queue": {
            "queued": queued or 0,
            "extracting": extracting or 0,
            "error_24h": error_24h or 0,
            "oldest_queued_age_sec": oldest_age,
        },
        "metrics": {
            "avg_extract_sec_by_class": worker.get("avg_extract_sec_by_class", {}),
            "extract_success_rate_24h": success_rate,
        },
    }

    # 503 ถ้า degraded
    alerts = []
    if worker["status"] != "running":
        alerts.append({"code": "WORKER_NOT_RUNNING"})
    if oldest_age > 300:
        alerts.append({"code": "OLDEST_QUEUED_OVER_5MIN", "value_sec": oldest_age})

    if alerts:
        body["alerts"] = alerts
        return JSONResponse(body, status_code=503)
    return body
```

#### 5.7 Worker startup/shutdown

```python
from .upload_worker import start_worker, stop_worker

@app.on_event("startup")
async def startup():
    await init_db()
    # ... existing rebuild logic ...
    await start_worker()

@app.on_event("shutdown")
async def shutdown():
    await stop_worker()
```

#### 5.8 _serialize_file — เพิ่ม fields

```python
"progress_step": f.progress_step,
"progress_pct": f.progress_pct,
"queued_at":            f.queued_at.isoformat() + "Z" if f.queued_at else None,
"extract_started_at":   f.extract_started_at.isoformat() + "Z" if f.extract_started_at else None,
"extract_completed_at": f.extract_completed_at.isoformat() + "Z" if f.extract_completed_at else None,
"extract_error":        f.extract_error,
"attempt_count":        f.attempt_count or 0,
```

#### 5.9 Refactor `/api/files/{id}/reprocess` (M-4 · v2 added)

**Current behavior (v9.3.4):** เรียก `extract_text` + optional `cleanup_extracted_text` inline → block 30-120s

**v9.4.0 behavior:** Reset row → enqueue → worker handle. คล้าย retry แต่ผ่าน /reprocess endpoint

```python
@app.post("/api/files/{file_id}/reprocess")
async def reprocess_file(
    file_id: str,
    mode: str = Query("cleanup", regex="^(cleanup|reextract)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """v9.4.0 — async reprocess via queue (was inline in v9.3.4)."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}})
    if getattr(file, "is_locked", False):
        raise HTTPException(403, detail={"error": {"code": "LOCKED", "message": "ไฟล์นี้ถูกล็อค"}})
    if not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(404, detail={"error": {"code": "RAW_MISSING", "message": "ไฟล์ดิบหายไปแล้ว — ต้องอัปใหม่"}})

    # v9.4.0: enqueue แทน extract inline
    file.processing_status = "queued"
    file.extract_started_at = None
    file.extract_completed_at = None
    file.extract_error = None
    file.progress_step = None
    file.progress_pct = None
    file.queued_at = datetime.utcnow()
    # mode hint (worker จะอ่าน): default 'cleanup' = LLM thai cleanup, 'reextract' = skip LLM
    # ⚠️ Note: v9.4.0 worker ไม่รัน cleanup_extracted_text (LLM cost). ถ้า mode='cleanup'
    #     → log warning + treat as 'reextract'. LLM cleanup ย้ายเป็น future hook (v9.5.0)
    if mode == "cleanup":
        logger.info(f"reprocess_file: mode=cleanup deferred to future (v9.5.0) — using reextract for {file_id}")
    await db.commit()

    qp_res = await db.execute(
        select(func.count()).select_from(File).where(
            File.user_id == current_user.id,
            File.processing_status == "queued",
            File.queued_at <= file.queued_at,
        )
    )
    return {
        "status": "ok",
        "file_id": file.id,
        "processing_status": "queued",
        "queue_position": qp_res.scalar() or 1,
        "mode": "reextract",  # v9.4.0: cleanup mode deferred
    }
```

**Backward compat note:**
- Response shape เปลี่ยน: เดิมคืน `old_text_length`/`new_text_length`/`improved` → ตอนนี้คืน `queue_position`
- Frontend ที่ใช้ field เดิม (เช่น app.js dialog หลัง reprocess) → ฟ้าตรวจ + เขียวอัปเดต UI ให้ตรง

#### 5.10 Refactor `/api/files/{id}/promote` (M-4 · v2 added)

**Current (v9.3.4):** เรียก `extract_text` + `ingest_via_ai` inline (block 60-300s สำหรับ vault audio/video)

**v9.4.0:** Vault → processed transition ผ่าน queue

```python
@app.post("/api/files/{file_id}/promote")
async def promote_vault_file(
    file_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """v9.4.0 — async vault→processed via queue (was inline in v9.3.4)."""
    result = await db.execute(
        select(File).where(File.id == file_id, File.user_id == current_user.id)
    )
    file = result.scalar_one_or_none()
    if not file:
        raise HTTPException(404, detail={"error": {"code": "FILE_NOT_FOUND", "message": "ไม่พบไฟล์"}})
    if getattr(file, "is_locked", False):
        raise HTTPException(403, detail={"error": {"code": "LOCKED", "message": "ไฟล์ถูกล็อค"}})
    if file.file_kind != "vault_only":
        raise HTTPException(400, detail={"error": {"code": "NOT_VAULT", "message": "ไฟล์นี้ไม่ใช่ vault file"}})
    if not file.raw_path or not os.path.exists(file.raw_path):
        raise HTTPException(404, detail={"error": {"code": "RAW_MISSING", "message": "Raw file หายจาก disk"}})

    # Re-check ext กับ allowed_types ปัจจุบัน
    from .plan_limits import get_limits as _gl
    limits = _gl(current_user)
    if file.filetype not in limits["allowed_file_types"]:
        return {
            "status": "ok",
            "file_id": file_id,
            "promoted": False,
            "file_kind": "vault_only",
            "extraction_status": "vault",
            "message": f"ไฟล์ .{file.filetype} ยังไม่รองรับ — เก็บใน vault ต่อไป",
        }

    # v9.4.0: enqueue + flip file_kind
    file.file_kind = "processed"
    file.processing_status = "queued"
    file.extraction_status = "pending"
    file.extracted_text = ""  # clear vault searchable text — worker จะใส่ extracted จริง
    file.extract_started_at = None
    file.extract_completed_at = None
    file.extract_error = None
    file.progress_step = None
    file.progress_pct = None
    file.queued_at = datetime.utcnow()
    await db.commit()

    qp_res = await db.execute(
        select(func.count()).select_from(File).where(
            File.user_id == current_user.id,
            File.processing_status == "queued",
            File.queued_at <= file.queued_at,
        )
    )
    return {
        "status": "ok",
        "file_id": file_id,
        "promoted": True,
        "file_kind": "processed",
        "processing_status": "queued",
        "queue_position": qp_res.scalar() or 1,
    }
```

### Step 6 — Frontend `app.js` modifications

(ดูโค้ดเต็มใน Step 7 — เป็นโค้ดเดียวกัน)

#### 6.1 `uploadFiles()` — ลด overlay phase, เพิ่ม UploadTray.notifyEnqueued

[ดู Step 7]

#### 6.2 i18n keys — **MUST add into `I18N.th` + `I18N.en` blocks** (M-1 fix · v2)

> **Pattern จริงใน [app.js:595](../../legacy-frontend/app.js#L595):**
> ```javascript
> const I18N = {
>   th: {
>     'auth.signInWithGoogle': 'เข้าสู่ระบบด้วย Google',
>     // ... other keys
>   },
>   en: {
>     'auth.signInWithGoogle': 'Sign in with Google',
>     // ... other keys
>   }
> };
> ```
> ❌ ห้ามสร้างตัวแปร `i18n_th` หรือ `i18n_en` แยก — ไม่มีใน codebase
> ✅ เพิ่ม keys ใน `I18N.th[key]` + `I18N.en[key]` blocks ที่มีอยู่แล้ว

#### 6.2.1 Extend `t(key, vars)` to support variable substitution (M-9 fix · v2)

> **Pattern จริงใน [app.js:1120](../../legacy-frontend/app.js#L1120):**
> ```javascript
> function t(key) {
>   const lang = getLang();
>   return I18N[lang]?.[key] || I18N['en']?.[key] || key;
> }
> ```
>
> **ปัญหา:** UploadTray ใช้ `t('upload.tray.position', { n: 5 })` — แต่ปัจจุบัน `t()` ไม่รับ vars
>
> **แก้ (1 line + extend):**
> ```javascript
> function t(key, vars) {
>   const lang = getLang();
>   const tr = I18N[lang]?.[key] || I18N['en']?.[key] || key;
>   if (!vars) return tr;
>   return tr.replace(/\{(\w+)\}/g, (_, k) => vars[k] != null ? vars[k] : `{${k}}`);
> }
> ```
> Backward compat: `t(key)` (no vars) ทำงานเหมือนเดิม

#### 6.2.2 Keys ที่ต้องเพิ่ม (insert ที่ท้าย block ของแต่ละภาษา ก่อน closing `}`)

```javascript
// ใน I18N.th block (หลัง 'auth.signInWithGoogle' หรือ end of block):
'upload.queuedToast':           'เพิ่ม {n} ไฟล์เข้าคิวแล้ว — ดูคิวด้านล่าง',
'upload.tray.title':            'คิว Upload',
'upload.tray.title_n':          'คิว Upload ({n})',
'upload.tray.minimize':         'ย่อ',
'upload.tray.queued':           'รอคิว',
'upload.tray.working':          'กำลังทำ',
'upload.tray.failed':           'ล้มเหลว',
'upload.tray.done':             'เสร็จแล้ว',
'upload.tray.retry':            'ลองใหม่',
'upload.tray.dismiss':          'ลบออก',
'upload.tray.position':         'อันดับ {n}',
'upload.tray.position_of':      'อันดับ {n} จาก {total}',
'upload.tray.elapsed':          'ใช้เวลา {sec} วินาที',
'upload.tray.elapsed_min':      'ใช้เวลา {min} นาที',
'upload.tray.summary_queued':   '{n} รอคิว',
'upload.tray.summary_extracting': '{n} กำลังทำ',
'upload.tray.summary_failed':   '{n} ล้มเหลว',
'upload.tray.system_degraded':  'ระบบประมวลผลล่าช้ากว่าปกติ — เรากำลังตรวจสอบ',
'upload.tray.system_stopped':   'ระบบประมวลผลหยุด — กรุณาติดต่อแอดมิน',
'upload.tray.empty_done':       'ทุกไฟล์เสร็จเรียบร้อย',
'upload.tray.see_details':      'รายละเอียด',
'upload.tray.stage_queued':     'เข้าคิว',
'upload.tray.stage_started':    'เริ่มประมวลผล',
'upload.tray.stage_completed':  'เสร็จ/ผิดพลาด',
'upload.tray.attempt':          'ครั้งที่ลอง',

// ใน I18N.en block (parity):
'upload.queuedToast':           '{n} files queued — see tray below',
'upload.tray.title':            'Upload Queue',
'upload.tray.title_n':          'Upload Queue ({n})',
'upload.tray.minimize':         'Minimize',
'upload.tray.queued':           'Queued',
'upload.tray.working':          'Working',
'upload.tray.failed':           'Failed',
'upload.tray.done':             'Done',
'upload.tray.retry':            'Retry',
'upload.tray.dismiss':          'Dismiss',
'upload.tray.position':         'Position {n}',
'upload.tray.position_of':      'Position {n} of {total}',
'upload.tray.elapsed':          'Elapsed {sec}s',
'upload.tray.elapsed_min':      'Elapsed {min} min',
'upload.tray.summary_queued':   '{n} queued',
'upload.tray.summary_extracting': '{n} working',
'upload.tray.summary_failed':   '{n} failed',
'upload.tray.system_degraded':  'Processing slower than usual — investigating',
'upload.tray.system_stopped':   'Processing system stopped — please contact admin',
'upload.tray.empty_done':       'All files done',
'upload.tray.see_details':      'Details',
'upload.tray.stage_queued':     'Queued',
'upload.tray.stage_started':    'Started',
'upload.tray.stage_completed':  'Completed',
'upload.tray.attempt':          'Attempt',
```

#### 6.3 `showApp()` เรียก `UploadTray.openIfHasItems()`

```javascript
function showApp() {
  // ... existing ...
  if (window.UploadTray) {
    UploadTray.openIfHasItems();
  }
}
```

### Step 7 — Frontend UploadTray module (full)

```javascript
// ════════════════════════════════════════════════════════
// UPLOAD TRAY — v9.4.0
// ════════════════════════════════════════════════════════
// Persistent UI tray ที่บอกความจริงเรื่องคิว upload ทุกขั้น
// ตาม Truthfulness Contract:
//   - ห้ามโชว์ pct ปลอม → progress_pct_known=false ใช้ indeterminate meter
//   - แสดง stage timestamps จริงในรายละเอียด
//   - why_slow text จาก backend (computed truthful)
//   - estimated_wait จาก rolling avg ของจริง
// Polling 2s, backoff to 5s after 30 ticks (1 min)
// Stops polling เมื่อ tray ปิด หรือ queue ว่าง

const UploadTray = (() => {
  let _pollHandle = null;
  let _pollAttempts = 0;
  let _isOpen = false;
  let _lastSnapshot = { active: [], failed: [], summary: { total_active: 0, failed_count: 0 } };
  let _expandedIds = new Set();  // file_id ที่ user click "รายละเอียด"

  const POLL_INTERVAL_MS = 2000;
  const POLL_BACKOFF_AFTER = 30;  // ticks before slow poll
  const POLL_BACKOFF_MS = 5000;

  const $ = (sel, root = document) => root.querySelector(sel);
  const isTH = () => getLang() === 'th';
  // M-1+M-9 fix v2: ใช้ global t() function ของ app.js (ที่ extend แล้ว support vars)
  // ไม่สร้าง local t() — ใช้ของ global เพื่อ keys ที่ insert ใน I18N.th + I18N.en
  // Helper function t() ของ app.js (line 1120) อยู่ใน global scope

  function escape(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function formatElapsed(sec) {
    if (sec < 60) return t('upload.tray.elapsed', { sec });
    return t('upload.tray.elapsed_min', { min: Math.floor(sec / 60) });
  }

  function ensureDom() {
    if ($('.upload-tray')) return;
    const titleText = isTH() ? 'คิว Upload' : 'Upload Queue';
    const html = `
      <aside class="upload-tray" role="region" aria-label="${escape(titleText)}">
        <header class="upload-tray-header">
          <h3 class="upload-tray-title">
            <svg class="upload-tray-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span class="upload-tray-title-text">${escape(titleText)}</span>
          </h3>
          <button class="upload-tray-close" type="button" aria-label="${escape(t('upload.tray.minimize'))}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
              <line x1="6" y1="6" x2="18" y2="18"></line>
              <line x1="6" y1="18" x2="18" y2="6"></line>
            </svg>
          </button>
        </header>
        <div class="upload-tray-banner" hidden></div>
        <ul class="upload-tray-list" role="list"></ul>
        <footer class="upload-tray-footer">
          <span class="upload-tray-summary"></span>
        </footer>
      </aside>
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
      console.warn('UploadTray fetchStatus error:', e);
      return _lastSnapshot;
    }
  }

  async function openIfHasItems() {
    const data = await fetchStatus();
    if ((data.summary?.total_active || 0) > 0 || (data.summary?.failed_count || 0) > 0) {
      open();
    }
  }

  function open() {
    if (_isOpen) return;
    ensureDom();
    $('.upload-tray').classList.add('is-open');
    _isOpen = true;
    startPolling();
  }

  function close() {
    if (!_isOpen) return;
    $('.upload-tray').classList.remove('is-open');
    _isOpen = false;
    stopPolling();
  }

  function notifyEnqueued(uploadedList) {
    if (!uploadedList || uploadedList.length === 0) return;
    open();
    // Optimistic render — ใส่ไฟล์ที่ enqueue ทันที (อย่ารอ poll)
    const optimistic = uploadedList
      .filter(u => u.processing_status === 'queued')
      .map(u => ({
        id: u.id, filename: u.filename, filetype: u.filetype,
        processing_status: 'queued',
        queue_position: u.queue_position || 1,
        progress_step: t('upload.tray.position', { n: u.queue_position || 1 }),
        progress_pct: null,
        progress_pct_known: false,
        stages: { queued_at: u.uploaded_at, extract_started_at: null, extract_completed_at: null },
        elapsed_sec: 0,
        attempt_count: 0,
        is_retryable: false,
        why_slow: null,
      }));
    _lastSnapshot = {
      active: [...optimistic, ...(_lastSnapshot.active || [])],
      failed: _lastSnapshot.failed || [],
      summary: {
        ...(_lastSnapshot.summary || {}),
        total_active: ((_lastSnapshot.summary?.total_active) || 0) + optimistic.length,
        queued_count: ((_lastSnapshot.summary?.queued_count) || 0) + optimistic.length,
        system_status: _lastSnapshot.summary?.system_status || 'ok',
      },
    };
    render(_lastSnapshot);
  }

  function startPolling() {
    if (_pollHandle) return;
    _pollAttempts = 0;
    const tick = async () => {
      const data = await fetchStatus();
      render(data);
      _pollAttempts++;

      const noActive = (data.summary?.total_active || 0) === 0;
      const noFailed = (data.summary?.failed_count || 0) === 0;

      if (noActive && noFailed) {
        // ทุกอย่างเสร็จ — refresh main list + auto-close
        stopPolling();
        if (typeof loadFiles === 'function') loadFiles();
        if (typeof loadStats === 'function') loadStats();
        if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount();
        // Show "all done" briefly, then close
        const banner = $('.upload-tray-banner');
        if (banner) {
          banner.hidden = false;
          banner.textContent = t('upload.tray.empty_done');
          banner.className = 'upload-tray-banner is-success';
        }
        setTimeout(() => close(), 2000);
        return;
      }

      const interval = _pollAttempts > POLL_BACKOFF_AFTER ? POLL_BACKOFF_MS : POLL_INTERVAL_MS;
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
    const banner = $('.upload-tray-banner');
    if (!list) return;

    const activeCount = data.summary?.total_active || 0;
    const failedCount = data.summary?.failed_count || 0;
    const totalShow = activeCount + failedCount;

    if (titleEl) {
      titleEl.textContent = totalShow > 0
        ? t('upload.tray.title_n', { n: totalShow })
        : t('upload.tray.title');
    }

    if (summaryEl) {
      const parts = [];
      if (data.summary?.queued_count) parts.push(t('upload.tray.summary_queued', { n: data.summary.queued_count }));
      if (data.summary?.extracting_count) parts.push(t('upload.tray.summary_extracting', { n: data.summary.extracting_count }));
      if (failedCount) parts.push(t('upload.tray.summary_failed', { n: failedCount }));
      summaryEl.textContent = parts.join(' • ');
    }

    // System status banner (TC-6)
    if (banner) {
      const status = data.summary?.system_status || 'ok';
      if (status === 'degraded') {
        banner.hidden = false;
        banner.textContent = t('upload.tray.system_degraded');
        banner.className = 'upload-tray-banner is-warning';
      } else if (status === 'stopped') {
        banner.hidden = false;
        banner.textContent = t('upload.tray.system_stopped');
        banner.className = 'upload-tray-banner is-error';
      } else {
        banner.hidden = true;
      }
    }

    const items = [...(data.active || []), ...(data.failed || [])];
    list.innerHTML = items.map(renderItem).join('');

    // Wire actions
    list.querySelectorAll('[data-retry-id]').forEach(btn => {
      btn.addEventListener('click', () => onRetry(btn.dataset.retryId));
    });
    list.querySelectorAll('[data-dismiss-id]').forEach(btn => {
      btn.addEventListener('click', () => onDismiss(btn.dataset.dismissId));
    });
    list.querySelectorAll('[data-toggle-id]').forEach(btn => {
      btn.addEventListener('click', () => {
        const id = btn.dataset.toggleId;
        if (_expandedIds.has(id)) _expandedIds.delete(id);
        else _expandedIds.add(id);
        render(_lastSnapshot);
      });
    });
  }

  function renderItem(item) {
    const isFailed = item.processing_status === 'error';
    const isExtracting = item.processing_status === 'extracting';
    const isQueued = item.processing_status === 'queued';
    const isExpanded = _expandedIds.has(item.id);

    const pillClass = isFailed ? 'is-error' : isExtracting ? 'is-active' : 'is-warning';
    const pillText = isFailed ? t('upload.tray.failed')
                   : isExtracting ? t('upload.tray.working')
                   : t('upload.tray.queued');

    const ext = escape((item.filetype || '—').toUpperCase());
    const filename = escape(item.filename);

    let body = '';
    if (isFailed) {
      body = `
        <div class="upload-tray-error" role="alert">
          ${escape(item.extract_error || (isTH() ? 'ไม่ทราบสาเหตุ' : 'Unknown error'))}
        </div>`;
    } else if (isExtracting) {
      // TC-1 — pct ที่รู้ใช้ determinate, ไม่รู้ใช้ indeterminate
      const meterCls = item.progress_pct_known ? 'meter' : 'meter is-indeterminate';
      const pct = item.progress_pct_known ? Math.max(0, Math.min(100, item.progress_pct || 0)) : 0;
      const fillStyle = item.progress_pct_known ? `width:${pct}%` : '';
      body = `
        <div class="upload-tray-step">${escape(item.progress_step || '...')}</div>
        <div class="${meterCls}" role="progressbar" ${item.progress_pct_known ? `aria-valuenow="${pct}"` : ''} aria-valuemin="0" aria-valuemax="100">
          <div class="meter-fill" style="${fillStyle}"></div>
        </div>
        ${item.why_slow ? `<div class="upload-tray-whyslow">${escape(item.why_slow)}</div>` : ''}`;
    } else {
      body = `
        <div class="upload-tray-step">${escape(item.progress_step || t('upload.tray.position', { n: item.queue_position }))}</div>
        ${item.why_slow ? `<div class="upload-tray-whyslow">${escape(item.why_slow)}</div>` : ''}`;
    }

    // Stages (TC-2 truthful timestamps)
    const stages = item.stages || {};
    const stagesHtml = isExpanded ? `
      <dl class="upload-tray-stages">
        <dt>${escape(isTH() ? 'เข้าคิว' : 'Queued')}</dt>
        <dd>${stages.queued_at ? formatTime(stages.queued_at) : '—'}</dd>
        <dt>${escape(isTH() ? 'เริ่มประมวลผล' : 'Started')}</dt>
        <dd>${stages.extract_started_at ? formatTime(stages.extract_started_at) : '—'}</dd>
        <dt>${escape(isTH() ? 'เสร็จ/ผิดพลาด' : 'Completed')}</dt>
        <dd>${stages.extract_completed_at ? formatTime(stages.extract_completed_at) : '—'}</dd>
        <dt>${escape(isTH() ? 'ครั้งที่ลอง' : 'Attempt')}</dt>
        <dd>${(item.attempt_count || 0) + 1}</dd>
      </dl>
    ` : '';

    const elapsedHtml = (item.elapsed_sec != null && item.elapsed_sec > 0)
      ? `<span class="upload-tray-elapsed">${formatElapsed(item.elapsed_sec)}</span>`
      : '';

    const actions = isFailed ? `
      <div class="upload-tray-actions">
        ${item.is_retryable ? `<button class="btn btn-sm btn-outline" type="button" data-retry-id="${escape(item.id)}">${escape(t('upload.tray.retry'))}</button>` : ''}
        <button class="btn btn-sm btn-ghost" type="button" data-dismiss-id="${escape(item.id)}">${escape(t('upload.tray.dismiss'))}</button>
      </div>` : '';

    return `
      <li class="upload-tray-item" data-file-id="${escape(item.id)}">
        <div class="upload-tray-item-head">
          <span class="upload-tray-filename" title="${filename}">${filename}</span>
          <span class="status-pill ${pillClass}">${escape(pillText)}</span>
        </div>
        <div class="upload-tray-meta">
          <span class="upload-tray-ext">${ext}</span>
          ${elapsedHtml}
          <button class="upload-tray-toggle" type="button" data-toggle-id="${escape(item.id)}" aria-expanded="${isExpanded}">${escape(t('upload.tray.see_details'))}</button>
        </div>
        ${body}
        ${stagesHtml}
        ${actions}
      </li>`;
  }

  function formatTime(iso) {
    try {
      const d = new Date(iso);
      return d.toLocaleString(isTH() ? 'th-TH' : 'en-US', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
      });
    } catch (e) { return iso; }
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
      _expandedIds.delete(fileId);
      await fetchStatus().then(render);
    } catch (e) {}
  }

  return { open, close, openIfHasItems, notifyEnqueued };
})();

window.UploadTray = UploadTray;
```

#### 7.2 เปลี่ยน `uploadFiles()` ให้ใช้ tray

```javascript
async function uploadFiles(fileList) {
  if (_uploadInFlight) {
    showToast(getLang() === 'th' ? 'กำลังอัปโหลดอยู่ กรุณารอให้เสร็จก่อน' : 'Upload already in progress, please wait', 'info');
    return;
  }
  // ... existing batch limit checks (BATCH_SAFE_LIMIT/HARD_LIMIT) ไม่เปลี่ยน ...

  const isTH = getLang() === 'th';
  const baseMsg = (pct, done) => isTH
    ? `กำลังส่งไฟล์ขึ้น server... ${done}/${count} • ${pct}%`
    : `Sending files to server... ${done}/${count} • ${pct}%`;

  _uploadInFlight = true;
  showLoadingOverlay(baseMsg(0, 0), 'upload');
  // ... existing parallel pool 3 unchanged ...

  try {
    // ... existing aggregation ...
    const data = { uploaded: aggUploaded, skipped: aggSkipped, count: aggUploaded.length };

    // v9.4.0 — toast + tray (instead of "processing..." indeterminate phase)
    if (data.count > 0) {
      showToast(t('upload.queuedToast').replace('{n}', data.count), 'info');
      UploadTray.notifyEnqueued(data.uploaded);
    }

    // existing: vault + skipped + duplicate handling unchanged
    // ...
    // remove: loadFiles/loadStats/loadUnprocessedCount calls — UploadTray handles when queue empties
  } catch (e) {
    // existing error handling
  } finally {
    _uploadInFlight = false;
    hideLoadingOverlay();
  }
}
```

### Step 8 — `styles.css` upload-tray (full)

```css
/* ════ UPLOAD TRAY — v9.4.0 (token-only, atom reuse) ════ */

.upload-tray {
  position: fixed;
  bottom: var(--space-4);
  right: var(--space-4);
  width: 360px;
  max-width: calc(100vw - var(--space-8));
  max-height: 65vh;
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
  transition: transform var(--duration-base) var(--ease-out),
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
  flex-shrink: 0;
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
  color: var(--accent);
  flex-shrink: 0;
}
.upload-tray-close {
  background: transparent;
  border: 0;
  color: var(--text-muted);
  cursor: pointer;
  padding: var(--space-1);
  border-radius: var(--radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 32px;
  min-height: 32px;
}
.upload-tray-close:hover {
  color: var(--text-primary);
  background: var(--surface-3);
}
.upload-tray-close:focus-visible {
  box-shadow: var(--ring-focus);
  outline: 0;
}

.upload-tray-banner {
  padding: var(--space-2) var(--space-4);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}
.upload-tray-banner.is-warning {
  background: color-mix(in srgb, var(--warning) 12%, transparent);
  color: var(--warning);
  border-bottom: 1px solid color-mix(in srgb, var(--warning) 30%, transparent);
}
.upload-tray-banner.is-error {
  background: color-mix(in srgb, var(--error) 12%, transparent);
  color: var(--error);
  border-bottom: 1px solid color-mix(in srgb, var(--error) 30%, transparent);
}
.upload-tray-banner.is-success {
  background: color-mix(in srgb, var(--success) 12%, transparent);
  color: var(--success);
  border-bottom: 1px solid color-mix(in srgb, var(--success) 30%, transparent);
}

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
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}
.upload-tray-ext {
  background: var(--surface-3);
  padding: 0 var(--space-2);
  border-radius: var(--radius-xs);
  letter-spacing: 0;  /* TC: no uppercase metric labels */
}
.upload-tray-elapsed {
  margin-left: auto;
}
.upload-tray-toggle {
  background: transparent;
  border: 0;
  color: var(--accent);
  cursor: pointer;
  font-size: var(--fs-xs);
  padding: 0;
  text-decoration: underline;
}
.upload-tray-toggle:focus-visible {
  box-shadow: var(--ring-focus);
  outline: 0;
  border-radius: var(--radius-xs);
}

.upload-tray-step {
  font-size: var(--fs-xs);
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.upload-tray-whyslow {
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-style: italic;
}

.upload-tray-error {
  font-size: var(--fs-xs);
  color: var(--error);
  background: color-mix(in srgb, var(--error) 8%, transparent);
  border: 1px solid color-mix(in srgb, var(--error) 25%, transparent);
  padding: var(--space-2);
  border-radius: var(--radius-sm);
}

.upload-tray-stages {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-1) var(--space-3);
  font-size: var(--fs-xs);
  font-variant-numeric: tabular-nums;
  margin: 0;
  padding: var(--space-2);
  background: var(--surface-3);
  border-radius: var(--radius-sm);
}
.upload-tray-stages dt { color: var(--text-muted); }
.upload-tray-stages dd { color: var(--text-secondary); margin: 0; }

.upload-tray-actions {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.upload-tray-footer {
  padding: var(--space-2) var(--space-4);
  border-top: 1px solid var(--border);
  font-size: var(--fs-xs);
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* New atom modifier: indeterminate meter (TC-1 no-fake) */
.meter.is-indeterminate {
  position: relative;
  overflow: hidden;
}
.meter.is-indeterminate .meter-fill {
  width: 40%;
  background: linear-gradient(90deg, transparent, var(--accent), var(--accent-hover), transparent);
  animation: progressIndeterminate 1.4s ease-in-out infinite;
}

/* Mobile */
@media (max-width: 600px) {
  .upload-tray {
    bottom: var(--space-3);
    right: var(--space-3);
    left: var(--space-3);
    width: auto;
    max-height: 50vh;
  }
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
  .upload-tray {
    transition: opacity var(--duration-fast);
    transform: none;
  }
  .upload-tray.is-open { opacity: 1; }
  .meter.is-indeterminate .meter-fill { animation: none; }
}
```

### Step 9 — i18n keys (เพิ่มใน app.js)

[ดูใน Step 6.2 — รวม 18 keys]

### Step 10 — HTML cache-bust + version

[app.html](../../legacy-frontend/app.html):
- `?v=9.3.4` → `?v=9.4.0` (ทั้งหมด)
- version label `v9.3.4` → `v9.4.0`

[config.py](../../backend/config.py):
- `APP_VERSION = "9.3.4"` → `APP_VERSION = "9.4.0"`

---

## ⚙️ 14. Performance Budget

### 14.1 Per-file resource budget

| Resource | Limit | กัน |
|---|---|---|
| RAM ระหว่าง extract (1 file) | < 500 MB | OCR pdf2image → 1 หน้า/รอบ ไม่โหลดพร้อมกัน (ต้องตรวจ `_extract_pdf_ocr`) |
| Disk write (raw file) | < max_file_size_mb (200 MB Starter) | plan_limits enforce |
| DB write (progress) | ≤ 1 ครั้ง/1.5s/file | PROGRESS_DB_THROTTLE_SEC |
| DB write (state transition) | ≤ 4 ครั้ง/file (queued, claim, success, drive) | by design |
| Gemini API call | 1 / file | by design |
| Tesseract subprocess | 1 / page (ใน OCR loop) | sync, sequential |

### 14.2 Per-system budget

| Metric | Target | Hard limit |
|---|---|---|
| `/api/upload` p95 latency | < 200 ms / file | < 1 s |
| `/api/upload-status` p95 | < 100 ms | < 500 ms |
| `/api/healthz/queue` p95 | < 50 ms | < 200 ms |
| Worker poll loop | 2 s ± 200 ms | < 3 s |
| Recovery on startup | < 500 ms | < 5 s |
| RAM peak (single instance) | < 2 GB | < 3 GB (Fly.io 4GB) |
| DB write rate | < 5/s avg | < 50/s peak |
| Concurrent users | 100 active uploaders | 500 |

### 14.3 ถ้าเกิน — ทำยังไง

| Trigger | Mitigation |
|---|---|
| RAM > 3 GB | Fly.io OOM-kill → auto-restart → recovery clean (ระบบ resilient by design) |
| DB write > 50/s | progress throttle increase 1.5s → 3s |
| /upload-status latency > 500ms | คิว index check, partition by user query |
| Worker stuck > 30 min | recovery hook reset extracting → queued |

---

## 🚨 15. FMEA — Failure Mode and Effects Analysis

| # | Step | Failure Mode | Detection | Effect on User | Mitigation |
|---|---|---|---|---|---|
| F-01 | upload save | disk full | os.write IOError | upload reject | error 500 + cleanup placeholder row before commit |
| F-02 | DB insert placeholder | DB locked | sqlalchemy timeout | upload reject | retry 3x with 100ms backoff in /api/upload |
| F-03 | Worker startup | recovery query fail | exception in `_recover_stale_jobs` | worker still starts | log + continue (non-fatal) |
| F-04 | Worker loop | claim_next_job exception | logged + sleep | no progress | log + continue, alert /healthz |
| F-05 | extract_text | PDF encrypted | exception | row → error + TC-5 msg | classify_extraction_status="encrypted" |
| F-06 | extract_text | PDF parsing crash | exception | row → error | format_user_error → TH msg |
| F-07 | extract_text | OCR timeout (50+ pages) | extract_started_at > 30 min | recovered to queued | `_recover_stale_jobs` |
| F-08 | ai_ingest | Gemini 503 | exception | row → error + retry suggested | format_user_error |
| F-09 | ai_ingest | Gemini quota exceeded | exception 429 | row → error | format_user_error: "quota เต็ม" |
| F-10 | ai_ingest | network drop | timeout | row → error | format_user_error: "เครือข่าย" |
| F-11 | progress write | DB locked | warning logged | progress not updated | next throttle window will retry |
| F-12 | DB commit (success) | DB locked | exception | row stays 'extracting' | recovery in 30 min |
| F-13 | Drive push | OAuth expired | warning logged | extract OK, Drive not synced | covered by v9.3.5 BYOS coverage plan |
| F-14 | Drive push | network drop | warning logged | extract OK, Drive not synced | best-effort by design |
| F-15 | Worker crash | uncaught exception | task done | queue stops | Fly.io auto-restart machine + recovery |
| F-16 | Server kill -9 | row stuck 'extracting' | extract_started_at old | user sees "stuck" in tray | recovery on restart resets to 'queued' |
| F-17 | User aborts upload mid-bytes | xhr abort | row never inserted | no orphan | (frontend Promise resolve กับ error handler) |
| F-18 | Polling spam (1000s users) | DB read load | high CPU | latency up | per-user index + tray closes when empty |
| F-19 | Frontend tab hidden | poll continues | bandwidth/battery | minor | Visibility API stop (FH future, defer v9.4.1) |
| F-20 | Multi-tab upload | duplicate enqueue | both tabs see same files | UX confusion | both tabs poll same data — eventually consistent |
| F-21 | Browser refresh mid-upload | xhr aborted | partial files | placeholder row exists but raw file partial | startup recovery + extract will fail → user retries |
| F-22 | DB schema migration fail | error in init_db | server won't start | total outage | idempotent ADD-only, rollback safe (no data destroyed) |
| F-23 | Heartbeat file unwritable | warning logged | /healthz wrong status | minor | non-fatal, log only |
| F-24 | Round-robin SQL fail (window function) | SQLite version too old | claim returns nothing | queue stops | Python 3.11+ has SQLite ≥3.40 — confirmed |
| F-25 | progress_pct invalid (negative) | INV-7 violated | UI render glitch | minor | worker code clamp 0-100 |

---

## 🧪 16. Test Scenarios (83 cases รวม · v2 +8 for reprocess/promote/WAL)

### Smoke Tests — `scripts/upload_queue_smoke.py` (48 cases · v2 +8)

**Group A — Upload + Queue lifecycle (T1-T10)**
- T1: POST 1 PDF → response ≤ 500ms + status='queued' + queue_position=1
- T2: POST 5 ไฟล์ติดกัน → ทั้งหมด status='queued' + position 1-5
- T3: รอ 30s → first file status='uploaded' + extracted_text != "" + progress_pct=100
- T4: ระหว่าง extract → /api/upload-status คืน status='extracting' + progress_step != null
- T5: priority order — txt + pdf + m4a → process txt → pdf → m4a (priority 1, 2, 3)
- T6: vault file (.exe) → status='vault_only' ทันที (skip queue)
- T7: queue cap Free=10 → file 11 ได้ skip code='QUEUE_FULL'
- T8: queue cap Starter=50 → file 51 ได้ skip code='QUEUE_FULL'
- T9: queue cap Admin=200 → file 201 skip
- T10: 2 users upload 5 ไฟล์พร้อมกัน → /upload-status แต่ละ user เห็นแค่ของตัวเอง

**Group B — Multi-tenant Fairness (T11-T15)**
- T11: User A queue 5 ไฟล์, user B queue 1 ไฟล์ พร้อมกัน → worker ทำ A1 → B1 → A2 → A3 → A4 → A5
- T12: User A queue 3 pdf, user B queue 3 txt → ลำดับ: A1 (pdf) → B1 (txt — เพราะ priority 1 < pdf priority 2 ใน same user_pos), จริงๆ user_pos ก่อน priority → B1 ทำหลัง A1
- T13: 3 users × 2 files → round-robin คือ A1 → B1 → C1 → A2 → B2 → C2
- T14: User A 10 ไฟล์, ใหม่ user B เข้ามาอันดับ 1 ตัว → B's 1st file ทำเป็นไฟล์ที่ 2 ของคิว
- T15: user_pos tie-breaker = priority class ASC → ดูว่าทำงานถูก

**Group C — Worker Recovery (T16-T20)**
- T16: insert row status='extracting' extract_started_at=2 hr ago → start worker → recover เป็น 'queued' (log "recovered_stale" count=1)
- T17: insert row status='extracting' extract_started_at=10 min ago → ไม่ recover (cutoff 30 min)
- T18: kill server SIGTERM กลาง extract → restart → file ที่ค้างถูก recover ภายใน startup
- T19: 100 stale rows → recovery ทำได้ใน < 5 s
- T20: heartbeat file ลบ → /healthz/queue คืน status='crashed' พร้อม alert

**Group D — Progress Reporting (T21-T26)**
- T21: PDF 12 หน้า → progress_step "OCR หน้า X/12" อย่างน้อย 3 ครั้ง (throttle 1.5s)
- T22: progress_pct ค่า monotonic increase (0 → 100 ไม่ลดกลาง)
- T23: throttle: ระหว่าง extract 5s → DB write progress ≤ 4 ครั้ง
- T24: m4a → progress_step "อัปโหลดไป Gemini" → "Gemini ถอดเสียง" → "บันทึกผลลัพธ์"
- T25: Gemini step → progress_pct=null + progress_pct_known=false (TC-1)
- T26: rolling avg update — 5 successful pdf → _AVG_EXTRACT_SEC[2] เปลี่ยน

**Group E — Error Handling + Retry (T27-T34)**
- T27: PDF เข้ารหัส → status='error' + extract_error="ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปโหลดใหม่" + extraction_status='encrypted' + is_retryable=true
- T28: Gemini quota error 429 → extract_error contains "quota เต็ม"
- T29: Gemini 503 → extract_error contains "ตอบช้ากว่าปกติ"
- T30: POST retry → status='queued' + attempt_count=1 + queue_position recalculated
- T31: retry 3 ครั้ง → ครั้งที่ 4 ได้ 409 NOT_RETRYABLE
- T32: retry on file ที่ raw_path หาย → 410 FILE_GONE
- T33: POST dismiss-error → row หาย + raw file ลบ + Drive copy ลบ (BYOS)
- T34: retry on status='uploaded' → 409 NOT_RETRYABLE

**Group F — API Contract + Auth (T35-T40)**
- T35: GET /api/upload-status (no auth) → 401
- T36: POST retry user A's file with user B token → 403 FORBIDDEN
- T37: GET /api/upload-status response shape: active[], failed[], summary{total_active, queued_count, extracting_count, failed_count, system_status}
- T38: estimated_wait_sec ใน response มาจาก rolling avg (TC-4) — ตรวจ source field='rolling_avg'
- T39: GET /api/healthz/queue (no auth) → 200 with full body
- T40: GET /api/healthz/queue worker stopped → 503 + alerts[]

**Group G — Reprocess + Promote enqueue (M-4 v2 · T41-T46)**
- T41: POST /api/files/{id}/reprocess → return ≤ 500ms + status='queued' + queue_position
- T42: reprocess existing 'uploaded' file → worker pickup → re-extract → status='uploaded' updated
- T43: reprocess on locked file → 403 LOCKED
- T44: reprocess on file ไม่มี raw_path → 404 RAW_MISSING
- T45: POST /api/files/{id}/promote vault file → return ≤ 500ms + file_kind='processed' + status='queued'
- T46: promote → worker pickup → ai_ingest (audio) → file_kind=processed + extracted_text != ""

**Group H — WAL mode + concurrent write (M-3 v2 · T47-T48)**
- T47: ตอน startup → query `PRAGMA journal_mode` → return 'wal' (verified setup ทำงาน)
- T48: 2 user upload concurrently + worker เขียน progress พร้อมกัน → ไม่มี `database is locked` exception ใน 30s

### Playwright UI — `tests/e2e-ui/v9.4.0-upload-tray.spec.js` (15 cases)

- E1: upload 1 PDF → tray โผล่ ด้านล่าง-ขวา + filename + status pill 'queued'
- E2: upload 3 ไฟล์ → 3 items ใน list + summary count = 3
- E3: ไฟล์เปลี่ยน status='extracting' → meter (progress bar) แสดง + step text update
- E4: progress_pct_known=false → meter is-indeterminate (animation visible)
- E5: progress_pct_known=true → meter determinate width = pct%
- E6: ไฟล์เสร็จ → หายจาก active list (ภายใน 3s ของ poll)
- E7: ทุกไฟล์เสร็จ → tray แสดง "ทุกไฟล์เสร็จเรียบร้อย ✓" 2s → ปิดอัตโนมัติ + main file list refresh
- E8: simulate fail → ไฟล์ย้ายไป failed section + retry/dismiss buttons แสดง
- E9: คลิก retry → status เปลี่ยน 'queued' + button หาย
- E10: คลิก dismiss → item หายจาก tray
- E11: คลิก minimize → tray หาย + polling หยุด
- E12: refresh page ขณะคิวยังมีไฟล์ → tray โผล่อัตโนมัติ
- E13: คลิก "รายละเอียด" → stages dl เปิดออก + เห็น 3 timestamps
- E14: mobile viewport (375x667) → tray full-width + max-height 50vh
- E15: prefers-reduced-motion → tray ไม่มี translateY animation, indeterminate meter ไม่ animate

### Pytest — `tests/test_upload_progress.py` (20 cases)

- P1-P5: progress_callback wiring (extract_text + ingest_via_ai)
- P6-P10: format_user_error mapping (encrypted/timeout/memory/encoding/quota)
- P11-P13: throttle behavior (< 1.5s = no DB write)
- P14-P16: priority sort (txt < pdf < audio)
- P17: SKIP_TEMPLATES["QUEUE_FULL"] format ถูก
- P18: per-plan tier cap reading from plan_limits
- P19: rolling avg update + clamp
- P20: classify_extraction_status mapping with new "encrypted" path

---

## 🚀 17. Deployment Plan

### 17.1 Pre-deploy checklist

- [ ] All 75 tests pass locally
- [ ] Migration tested ใน sandbox DB (`scripts/test_migration_v940.py`)
- [ ] /healthz/queue tested กับ scenarios 4 อัน (ok, degraded, stopped, crashed)
- [ ] Memory: pipeline-state, data-models, api-spec updated
- [ ] APP_VERSION 9.3.4 → 9.4.0
- [ ] HTML ?v= cache-bust
- [ ] No `console.log` left in app.js diff
- [ ] No `print` debug left in upload_worker.py
- [ ] env vars optional ต้องมี default (`POLL_SEC=2.0`, etc.)
- [ ] UI Foundation Contract §6 checklist ผ่าน (ฟ้าตรวจ)

### 17.2 Deploy commands

```bash
# 1. Final commit + push
git push origin master

# 2. Deploy
fly deploy --app personaldatabank

# 3. Wait for health check
# Fly.io จะ run /api/healthz (existing) — ยังไม่ใช่ /healthz/queue
# (อาจ extend health probe ทีหลัง)

# 4. Tail logs
fly logs --app personaldatabank | grep '"event":"upload_worker'
```

### 17.3 Post-deploy smoke (manual, ภายใน 5 นาทีหลัง deploy)

1. เปิด https://personaldatabank.fly.dev/app
2. Login → upload 1 PDF เล็ก
3. ดู tray โผล่ → "queued" → "extracting" → "เสร็จ"
4. Check `fly logs` → เห็น `claim_job` + `extract_done` events
5. GET `/api/healthz/queue` → 200 + worker.status='running'
6. (BYOS user) ดู Drive ว่ามี file ใหม่
7. (Free user spam) อัป 11 ไฟล์ → ไฟล์ที่ 11 ขึ้น "QUEUE_FULL"

### 17.4 Telemetry to watch (24h หลัง deploy)

| Metric | Healthy | Warning | Critical |
|---|---|---|---|
| `extract_failed` rate | < 5% | 5-15% | > 15% |
| `recovered_stale` count | 0-2/day | 3-10/day | > 10/day |
| Worker status='running' | 99%+ | 95-99% | < 95% |
| Oldest queued age | < 60s | 60-300s | > 300s |
| Mean extract time (priority 2) | 5-30s | 30-120s | > 120s |

**Alert ถ้า:** เช็ค fly logs + /healthz/queue ทุก 1 ชั่วโมงในวันแรก

---

## ↩️ 18. Rollback Plan (multi-tier)

### Tier 1 — Forward fix (preferred)

ถ้าเจอ bug: fix + deploy patch v9.4.1 — เพราะ migration ADD-only ไม่ destructive

### Tier 2 — Disable worker only (mid-tier)

ถ้า worker pathology (memory leak, infinite loop):
```bash
fly secrets set UPLOAD_WORKER_DISABLED=true --app personaldatabank
fly deploy
```

แก้โค้ดให้ check env: `if os.getenv("UPLOAD_WORKER_DISABLED"): return`

ผลลัพธ์: queue stops, แต่ /api/upload ยัง insert row ได้ → user เห็น tray ค้าง "queued" → ใช้ tier 3 ได้

### Tier 3 — Code rollback (full revert)

```bash
# Revert master to v9.3.4
git revert HEAD --no-edit  # revert commits ของ v9.4.0
git push origin master
fly deploy

# DB columns ที่เพิ่ม v9.4.0 ยังอยู่ — ไม่ drop เพราะ ADD-only safe
# v9.3.4 SQLAlchemy ignore extra columns → backward compat
```

**สำคัญ:** ห้ามลบ columns + indexes ของ v9.4.0 หลัง rollback — เก็บไว้สำหรับ re-apply

### Tier 4 — DB restore (worst case)

หาก DB เสีย (เช่น migration ผิด):
- ดึง backup จาก `backups/projectkey_<timestamp>.db` (auto-backup pre-migration)
- Restore → re-run migrate → confirm

### Decision tree

```
ปัญหาเล็ก / specific bug → Tier 1 (forward fix v9.4.1)
Worker behavior แปลก / memory leak → Tier 2 (disable env)
Endpoint /api/upload broken → Tier 3 (revert code)
DB schema corrupt → Tier 4 (restore backup)
```

---

## ✅ 19. Done Criteria (measurable)

- [ ] All 75 tests pass (40 smoke + 15 Playwright + 20 pytest)
- [ ] /api/upload p95 latency < 1s (measured via load test)
- [ ] /api/upload-status p95 latency < 500ms
- [ ] Worker recovery: ลอง kill 5 ครั้ง — recover 5/5
- [ ] Round-robin verified: 2 users × 5 files → A1, B1, A2, A3, A4, A5
- [ ] TC-1 verified: ไฟล์ Gemini → progress_pct_known=false ใน 100% ของ samples
- [ ] TC-2 verified: queued_at + extract_started_at + extract_completed_at = real timestamps in DB
- [ ] TC-3 verified: why_slow text แสดงให้ user เห็นในกรณี > 30s wait
- [ ] TC-4 verified: estimated_wait_sec มาจาก rolling avg (`source='rolling_avg'`)
- [ ] TC-5 verified: 10 error scenarios → 10 specific TH messages (ไม่ใช่ generic)
- [ ] TC-6 verified: worker crash → banner "ระบบประมวลผลล่าช้า" แสดงใน tray
- [ ] No regression: byos_router_smoke 16/16, byos_foundation_smoke 26/26, share_pack 36/36
- [ ] UI Foundation Contract §6: 100% pass (ฟ้าตรวจ)
- [ ] APP_VERSION 9.4.0 + cache-bust ครบ
- [ ] Memory updated: data-models.md, api-spec.md, pipeline-state.md, last-session.md

---

## ⚠️ 20. Risks + Mitigations

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R-1 | SQLite write contention (worker progress + main app) | Medium | Medium | throttle 1.5s + WAL mode + short transactions |
| R-2 | Multi-uvicorn worker conflict (อนาคต) | Low | Medium | atomic UPDATE WHERE id+status (ADR-006) — multi-worker safe by design |
| R-3 | Polling เปลือง bandwidth/battery mobile | Medium | Low | backoff 2s→5s after 30 ticks + close on tray hide |
| R-4 | User เห็นคิวเต็ม frustrated | Low | Low | TC-5 truthful message + ปุ่ม "ดูคิว" + อัปเกรด link |
| R-5 | Memory peak ระหว่าง /api/upload save big file | Low | Medium | (out of scope — defer to v9.4.1 streaming upload) |
| R-6 | BYOS Drive push fail หลัง refactor | Medium | Low | T29 smoke + best-effort by design (ไม่ block extract) |
| R-7 | Migration breaks production DB | Low | High | ADD-only + idempotent + auto-backup pre-migration |
| R-8 | Worker crash → uvicorn down | Low | High | Fly.io auto-restart machine + recovery on startup |
| R-9 | i18n key มิสซิ่ง → "{key}" แสดง | Medium | Low | review checklist + EN+TH parity test |
| R-10 | DB query window function อ่านข้าม Python version | Low | Medium | Python 3.11+ has SQLite 3.40+ — confirmed via fly Docker image |

---

## ❓ 21. Open Questions รอ user ตอบ (หรือยอมรับ default)

| # | คำถาม | Default ที่ผมเลือก | ทางเลือก | ผลกระทบถ้าเปลี่ยน |
|---|---|---|---|---|
| Q1 | Worker concurrency | **1** (sequential, ปลอดภัย, debug ง่าย) | 2 หรือ dynamic | 2 = throughput ×2 แต่เพิ่ม resource race |
| Q2 | Tray location | **bottom-right** (guide-fab hidden แล้ว) | top-right / bottom-center | UX ใกล้เคียง ไม่ critical |
| Q3 | Auto-retry attempts ก่อน manual | **0** (manual เท่านั้น — TC-1 transparency) | 1 (handle transient) / 3 | 1 = handle Gemini 503 แต่ผิด TC-1 |
| Q4 | Rollout strategy | **ทันที** (no feature flag) | env var `UPLOAD_QUEUE_ENABLED` | flag = ปลอดภัย แต่ migration backward compat อยู่แล้ว |
| Q5 | Per-plan queue cap (Free/Starter/Admin) | **10/50/200** | 5/25/100 หรือ 20/100/500 | กระทบ user spam protection |
| Q6 | Polling interval | **2s default + 5s after 30 ticks** | 1s / 3s / 5s | เร็วกว่า = bandwidth สูง, ช้ากว่า = UX แย่ |
| Q7 | Stale extract timeout | **30 min** | 15 min / 60 min | เร็วกว่า = recover เร็ว แต่ false positive |

---

## 📌 22. Notes for เขียว (Implementation Gotchas)

### Critical gotchas (อ่าน 2 รอบ)

1. **`extract_text` เป็น sync** — เรียกใน worker ต้อง wrap `asyncio.to_thread(extract_text, ...)` เพื่อไม่ block event loop
2. **`progress_callback` ใน sync extract_text** — เป็น sync function. Worker ต้อง wrap `asyncio.run_coroutine_threadsafe(write, loop)` เพื่อโพสต์ async DB write กลับ main event loop
3. **`progress_callback` ใน async ai_ingest** — เป็น async function — `await progress_callback(...)`
4. **SQLite UPDATE...RETURNING** — Python 3.11+ stdlib sqlite3 รองรับ. Confirm ใน Fly Dockerfile (`python:3.11+`)
5. **SQLite WAL mode** — เปิดใน init_db ด้วย `PRAGMA journal_mode=WAL` (ถ้ายังไม่เปิด)
6. **`_USER_QUOTA_LOCKS`** — ยังต้องอยู่ ใช้ป้องกัน race ตอน insert placeholder
7. **vault_only files ข้ามคิว** — ทำตรงๆ ใน /api/upload (เร็วอยู่แล้ว) — ไม่เข้า worker
8. **Drive push ใน worker** — เฉพาะ BYOS user (`storage_mode=='byos'`). non-BYOS = no-op
9. **`progress_step` length** — TEXT column ไม่จำกัด แต่ practice ≤ 80 chars + worker เซต safety cap 200 ใน `_write_progress`
10. **Worker shutdown** — ใช้ `asyncio.wait_for(_shutdown_event.wait(), timeout=POLL)` ระหว่าง idle เพื่อตอบ shutdown signal เร็ว
11. **Test ที่ใช้ DB จริง** — ใช้ `tmp_path` + override DATABASE_URL หรือ truncate `files` ก่อน
12. **`escapeHtml`** — ใน app.js ผมไม่เห็น helper เดิม → UploadTray มี local `escape()` ใน module
13. **`.meter.is-indeterminate`** — atom modifier ใหม่ — ฟ้าตรวจว่าอยู่ใน UI Foundation Contract approved (ผม approve ผ่าน plan นี้)
14. **`window.i18n`** — frontend ใช้ pattern อื่น? ตรวจ `t()` function เดิม — UploadTray ควรใช้ pattern เดียวกัน
15. **CSS color-mix support** — Safari < 16.4 ไม่รองรับ → fallback `rgba(...)` หรือ pre-mixed token

### Pattern reuse table

| สิ่งที่ทำ | ใช้ pattern ไหน | Reference |
|---|---|---|
| Per-user lock | `_get_user_quota_lock` เดิม | [main.py:471](../../backend/main.py#L471) |
| Atomic claim | คล้าย pack_share atomic claim | [pack_share.py](../../backend/pack_share.py) |
| Idempotent migration | ตามแบบ v7.5.0 + v9.1.0 | [database.py:init_db](../../backend/database.py) |
| Frontend polling | คล้าย `loadUnprocessedCount` | [app.js](../../legacy-frontend/app.js) |
| i18n keys | object `i18n_th` + `i18n_en` | line ~600+ ใน app.js |
| atom reuse | `.meter`, `.status-pill`, `.btn .btn-sm` | [shared.css](../../legacy-frontend/shared.css) |

### Don't do

- ❌ ห้ามเปลี่ยน existing `extract_text` signature โดยทำให้ `progress_callback` required (ต้อง default=None)
- ❌ ห้ามแก้ `/api/organize-new` logic
- ❌ ห้าม drop `processing="processing"` value — backfill เก็บไว้
- ❌ ห้ามใช้ Redis / Celery / multiprocessing
- ❌ ห้ามสร้าง atom CSS variant ใหม่นอกจาก `.meter.is-indeterminate`
- ❌ ห้ามใช้ literal `8px` `#6366f1` ใน styles.css ใหม่ — token เท่านั้น
- ❌ ห้ามโชว์ progress % ปลอม (TC-1)
- ❌ ห้ามใช้ generic error message (TC-5)
- ❌ ห้าม commit `.env` / `.jwt_secret` / DB
- ❌ ห้ามใช้ WebSocket / SSE
- ❌ ห้ามแก้ extraction.py extract logic — เพิ่มแค่ progress_callback parameter

---

## 📱 23. Browser/Mobile Compatibility

| Browser/Platform | Tested? | Notes |
|---|---|---|
| Chrome/Edge 100+ | ✅ Yes (Playwright) | full support |
| Firefox 100+ | ✅ (manual) | full support |
| Safari 16.4+ | ✅ (manual) | color-mix supported |
| Safari 15-16.3 | ⚠️ partial | color-mix fallback to rgba (may need extra rule) |
| iOS Safari (current) | ✅ Playwright (mobile viewport) | bottom-right tray adapted to mobile |
| Android Chrome | ✅ | same |

**Polyfills:** ไม่ต้องเพิ่ม (ใช้ feature ที่ vanilla supported)

**Visibility API future hook (FH-2):** เพิ่ม `document.addEventListener('visibilitychange', ...)` ใน v9.4.1

---

## 📚 24. Appendix A — Error Catalog (TH messages)

| Exception class | Match pattern | TH message |
|---|---|---|
| Generic encrypted | "encrypted" / "password" in str | "ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปโหลดใหม่" |
| FileNotFoundError | "no such file" / class name | "ไฟล์ดิบหายไประหว่างประมวลผล — ต้องอัปโหลดใหม่" |
| TimeoutError | "timeout" / "timed out" | "ประมวลผลใช้เวลานานเกินกำหนด — ลองแบ่งไฟล์เล็กลงหรือกดลองใหม่" |
| MemoryError | "memory" / class name | "ไฟล์ใหญ่เกินที่ระบบรับไหว — ลองแบ่งไฟล์เล็กลง" |
| UnicodeDecodeError/Encode | class name | "ไฟล์มี encoding ผิดปกติ — ลอง re-save เป็น UTF-8 แล้วอัปใหม่" |
| Gemini quota | "quota" / "rate limit" / "429" | "Gemini API ใช้เกินโควต้า — รอเดือนหน้าหรือเปลี่ยนแพลน" |
| Gemini 503 | "google" + "503" / "unavailable" | "Gemini ตอบช้ากว่าปกติ — กดลองใหม่อีกครั้ง" |
| Gemini auth | "google" + "auth" | "Gemini API key ไม่ถูกต้อง — ติดต่อแอดมิน" |
| Tesseract crash | "tesseract" | "OCR engine ขัดข้อง — ลองอัปใหม่หรือใช้ไฟล์ text แทนรูป" |
| Network drop | "connection" / "network" | "ปัญหาเครือข่าย — กดลองใหม่อีกครั้ง" |
| Default | (anything else) | "ประมวลผลล้มเหลว ({class_name}) — กดลองใหม่หรือติดต่อแอดมิน" |

## 📚 25. Appendix B — i18n Keys (complete)

```javascript
// THAI (i18n_th)
'upload.queuedToast':           'เพิ่ม {n} ไฟล์เข้าคิวแล้ว — ดูคิวด้านล่าง',
'upload.tray.title':            'คิว Upload',
'upload.tray.title_n':          'คิว Upload ({n})',
'upload.tray.minimize':         'ย่อ',
'upload.tray.queued':           'รอคิว',
'upload.tray.working':          'กำลังทำ',
'upload.tray.failed':           'ล้มเหลว',
'upload.tray.done':             'เสร็จแล้ว',
'upload.tray.retry':            'ลองใหม่',
'upload.tray.dismiss':          'ลบออก',
'upload.tray.position':         'อันดับ {n}',
'upload.tray.position_of':      'อันดับ {n} จาก {total}',
'upload.tray.elapsed':          'ใช้เวลา {sec} วินาที',
'upload.tray.elapsed_min':      'ใช้เวลา {min} นาที',
'upload.tray.summary_queued':   '{n} รอคิว',
'upload.tray.summary_extracting': '{n} กำลังทำ',
'upload.tray.summary_failed':   '{n} ล้มเหลว',
'upload.tray.system_degraded':  'ระบบประมวลผลล่าช้ากว่าปกติ — เรากำลังตรวจสอบ',
'upload.tray.system_stopped':   'ระบบประมวลผลหยุด — กรุณาติดต่อแอดมิน',
'upload.tray.empty_done':       'ทุกไฟล์เสร็จเรียบร้อย',
'upload.tray.see_details':      'รายละเอียด',
'upload.tray.stage_queued':     'เข้าคิว',
'upload.tray.stage_started':    'เริ่มประมวลผล',
'upload.tray.stage_completed':  'เสร็จ/ผิดพลาด',
'upload.tray.attempt':          'ครั้งที่ลอง',

// ENGLISH (i18n_en) — parity
'upload.queuedToast':           '{n} files queued — see tray below',
'upload.tray.title':            'Upload Queue',
'upload.tray.title_n':          'Upload Queue ({n})',
// ... + EN equivalents
```

## 📚 26. Appendix C — env vars

| Variable | Default | Purpose |
|---|---|---|
| `UPLOAD_WORKER_POLL_SEC` | 2.0 | Worker poll interval |
| `UPLOAD_STALE_TIMEOUT_SEC` | 1800 | Stale extracting recovery threshold |
| `UPLOAD_MAX_RETRY` | 3 | Max retry attempts (ADR-005) |
| `UPLOAD_HEARTBEAT_FILE` | `data/worker_heartbeat.txt` | Heartbeat file path |
| `UPLOAD_WORKER_DISABLED` | (unset) | Tier-2 rollback hatch |
| `GOOGLE_API_KEY` | (existing) | Gemini multimodal |

---

## 🎬 ขอ user ตัดสินใจก่อน approve

ตอบ Q1-Q7 ใน §21 (หรือยอมรับ default ทั้งหมด) → ผม update state เป็น `plan_approved` → ส่งต่อให้เขียว

**Effort summary (v2 — adjusted after เขียว field-audit):**
- เขียว: **~25-27 hrs (~3.5 วัน)** — เพิ่มจาก v1 22-24 hrs เพราะ:
  - +1 hr: WAL mode setup + verification (M-3)
  - +2 hrs: refactor reprocess + promote endpoints (M-4)
  - +0.5 hr: extend `t()` function + i18n verification (M-1, M-9)
  - +0.5 hr: safer SQL pattern in worker (M-10)
- ฟ้า: **~8-9 hrs (~1 วัน)** — เพิ่มจาก v1 7-8 hrs เพราะ:
  - +0.5 hr: Group G tests (reprocess/promote enqueue)
  - +0.5 hr: WAL mode verification + concurrent write test (Group H)

**Total: ~33-36 hrs (~4 วัน)**

**End of plan — Detailed Proactive Edition v2 (post-audit)**
