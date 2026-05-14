# Personal Data Bank — Technical & Business Report v9.4.8

**Company**: Axis Solutions Team
**Product**: Personal Data Bank (PDB)
**Production URL**: https://personaldatabank.fly.dev
**Report date**: 2026-05-12
**Prepared for**: External technical expert review

---

## 1. Executive Summary

PDB เป็น **AI-powered personal knowledge workspace** ที่ user อัพโหลดเอกสารทุกประเภท (PDF/DOCX/รูป/เสียง/วิดีโอ) → ระบบ extract เนื้อหา → AI วิเคราะห์ + จัดกลุ่ม + สร้าง Knowledge Graph → user ถามตอบกับข้อมูลของตัวเองผ่าน MCP กับ Claude/ChatGPT/Antigravity ได้

**สถานะปัจจุบัน v9.4.8** (deployed 2026-05-12):
- ✅ Production stable บน Fly.io Singapore — success rate 24h = 100%
- ✅ Pipeline ครบทุก format — 12/13 ไฟล์ทดสอบจริง pass (1 ไฟล์ DOCX ว่างเปล่าจริง)
- ✅ 111 API endpoints across 13 categories
- ✅ 22 MCP tools สำหรับ Claude/ChatGPT/Antigravity integration
- ⚠️ **คอขวด 4 จุด** ระบุชัดเจน — ต้องการความเห็นในส่วน scaling + Tesseract→Gemini PDF migration
- ⚠️ **Reliability gaps 5 จุด** — มี roadmap แต่ยังไม่ลงมือ

**Engineering velocity** (7-day session, 2026-05-05 → 2026-05-12):
- **9 versions** v9.4.0 → v9.4.8 (queue + worker foundation → AI ingest fix → progress callback → filename truncation → quality patches)
- **End-to-end production tests** ดำเนินการบน prod URL จริงด้วย 13 ไฟล์ของ user (รวม PDF 20 หน้า OCR ที่กิน 20 นาที)
- **Playwright UI E2E** verified all user-facing changes

---

## 2. About the Product

### Product Definition (จาก founder strategy doc)
> "Private knowledge space ที่รับไฟล์สำคัญเข้ามา จัดให้เป็นระบบ สร้างไฟล์สรุป `.md` และเปิดให้ผู้ใช้นำข้อมูลนั้นไปใช้กับ AI ได้อย่างควบคุมได้"

**ไม่ใช่แค่ chat with files** — เป็น **พื้นที่ข้อมูลส่วนตัวที่จัดระบบแล้วพร้อมใช้กับ AI**

### Vision (3 layers)
1. **ความเชื่อพื้นฐาน** — preserve value of data through time
2. **ภาพโลกที่อยากเห็น** — important things don't get lost over time
3. **เป้าหมายลงมือ** — make data usable everywhere, seamlessly

### 3-Attribute Promise (core spec)
- **เก็บอย่างดี** (kept well)
- **เป็นส่วนตัว** (private)
- **เป็นระบบ** (organized / systematic)

### Differentiation จาก Cloud Storage
| Cloud Storage (Drive/Notion/Dropbox) | PDB |
|---|---|
| File containers | **Usability + Human Significance** |
| Store and forget | Active organization + AI-ready |
| Generic | Knows you (Context + Knowledge Graph) |

### 4 Product Principles (locked)
1. **Private by default** — ทุกข้อมูลของ user คนนั้น มองเห็นเฉพาะตัวเอง
2. **Original file is preserved** — เก็บไฟล์ต้นฉบับ ไม่ทำลาย
3. **Organized by system** — ระบบช่วยจัด ไม่ใช่ user จัดเอง
4. **AI use must be explainable** — บอกได้ว่า AI ใช้ไฟล์/สรุปอะไรตอบ

### Sales narrative (Tree Model)
> "ลูกค้าไม่ได้ซื้อเทคโนโลยี — ลูกค้าซื้อ **การเอาความวุ่นวายออกไปจากชีวิต**"

Transform: scattered chats/emails/papers → digital system AI-ready

---

## 3. Founder & Team

**Founder**: 23-year-old senior business student building PDB solo
- **Personality**: Enneagram Type 1 (perfectionist)
- **Working style**: Nights + days
- **Communication preference**: Simple language + many concrete examples (avoid abstract)
- **Tech stack choice**: Vanilla JS frontend (no framework) — solo dev = monolithic is faster than learning new framework

**Team structure** (3-in-1 Pipeline Sequential mode):
- **แดง (Red)** — นักวางแผน / Architect
- **เขียว (Green)** — นักพัฒนา / Developer
- **ฟ้า (Blue)** — นักตรวจสอบ / Reviewer (with Playwright E2E)

(แต่ละ role โผล่ใน different sessions; current session ทำเป็น 3-in-1 mode คือ agent เดียวเป็นทั้ง 3 บทบาท)

---

## 4. Target Market & Pricing Tiers

### Personal AI Context (Self-service)
| Tier | Price | Target | Key limits |
|---|---|---|---|
| **Free** | ฿0/เดือน | นักศึกษา, ทดลอง | 50 files / 500 MB / 50 AI summary/เดือน / 100 export prompts |
| **Starter** | ฿99/เดือน | ครู, นักการตลาด, ครีเอเตอร์ | 500 files / 10 GB / 1,000 AI summary/เดือน / 70-day version history |

### Executive Digital Twin (Private demo only)
| Tier | Price | Target | Features |
|---|---|---|---|
| **Core** | ฿12,000/เดือน | Founders / executives | Private Identity Vault, Basic Decision Matrix, Text-based Twin, 50K API calls/mo |
| **Pro** | ฿25,000/เดือน | Leaders (recommended) | + Advanced Decision Matrix, Voice Clone, Priority Support, 3 Delegated Users, 200K API calls/mo |
| **Elite** | ฿45,000/เดือน | High-profile | + Avatar UI, Dedicated CSM, Deep Decision Calibration, 500K API calls/mo |
| **Legacy** | ฿8,000/เดือน | Knowledge preservation | Read-only Twin, Consultation Mode, archive |

### Real validated customer profile (from founder's actual data clusters)
The founder's own files clustered into 6 auto-detected collections — **proof of working AI organization**:
1. โครงการ Personal Data Bank: วิสัยทัศน์และแนวคิดธุรกิจ (6 files)
2. การบริหารจัดการทีมและการจดทะเบียนบริษัท (2 files — voice memos from cafe meetings)
3. ข้อกำหนดผลิตภัณฑ์และระบบการชำระเงิน (3 PRDs)
4. การพัฒนาระบบ COP และงานกองทัพ (5 files — military COPv2 client work)
5. การติดตั้งระบบ Agent และโครงสร้างพื้นฐาน (3 files — VPS/Maya/OpenClaw setup)
6. ข้อมูลบุคคลและประวัติการทำงาน (1 file — personal/CV)

**Killer use case**: Cafe voice memo (Thai .txt) → AI clusters with related business proposal PDF → graph connects them → user asks "เมื่อไหร่ที่ทีมตกลงเรื่องสัดส่วนหุ้น" → PDB recalls from voice memo + cross-references company registration draft. **Real, not hypothetical.**

---

## 5. Feature Inventory (Live in v9.4.8)

### Core Workspace
1. **My Data** (`ข้อมูลของฉัน`) — Upload + browse + filter (all / processed / vault)
2. **Knowledge View** (`มุมมองความรู้`) — Auto-clustered collections + summaries
3. **Knowledge Graph** (`กราฟ`) — D3.js interactive node-edge visualization
4. **AI Chat** (`AI แชท`) — 7-layer context retrieval (Profile + Files + Clusters + Graph + Memory)
5. **Context Memory** — Persistent context across chat sessions

### AI Capabilities
6. **AI Organizer** — Auto-cluster + importance score + Thai summary generation
7. **Personality Profile** — MBTI / Enneagram / CliftonStrengths / VIA + history
8. **AI Vision** (v9.4.2+) — Gemini 2.5 Flash describes images natively
9. **AI Multimodal Ingest** — Audio transcription + Video analysis via Gemini Files API
10. **Context Packs** — Bundle files into shareable AI prompt context

### Integration & Connector
11. **MCP Server** — 22 tools for Claude Desktop / ChatGPT / Antigravity (Streamable HTTP)
12. **Google Drive BYOS** (v7.0+) — User chooses: managed (Fly volume) OR own Drive
13. **LINE Bot** (v9.4.3) — Friend link, message ingestion
14. **Stripe Billing** — Subscription, Customer Portal, plan upgrade/downgrade

### Auth & Identity
15. **Email + Password** — JWT (HS256) + bcrypt
16. **Google Sign-In** — OAuth 2.0 init/callback
17. **MCP Token** — Per-user secret for AI tool access

### Operations & Reliability (recent additions v9.4.0+)
18. **Upload Queue** — DB-as-queue + async worker (no 30s+ inline blocking)
19. **Real-time Progress** — "OCR หน้า 5/20" updates every ~1.5s
20. **Cancel Button** — User cancels queued/extracting jobs
21. **System Health Banner** — degraded/stopped detection
22. **Retry + Dismiss** — Failed upload self-service recovery

### 111 API Endpoints (by category)
```
  Other                27   (utility, debug, admin sub-routes)
  Admin                11
  AI Organize          10
  Context Pack         10
  Auth                  8
  Files                 8
  MCP                   8
  Upload Queue          5
  LINE                  5
  AI Chat               5
  Billing               5
  Drive/BYOS            5
  Profile               3
  Health                1
```

---

## 6. Production State (Live as of 2026-05-12)

```json
{
  "version": "9.4.8",
  "deployed_at": "2026-05-12T01:55:42Z",
  "region": "Singapore (sin)",
  "machines": 2,
  "active_machines": 1,
  "worker": {
    "status": "running",
    "uptime_sec": 857,
    "concurrency": 1,
    "avg_extract_sec_by_class": {
      "1": 1.0,    // fast (txt/code) — sub-second
      "2": 13.27,  // doc (PDF text/DOCX/XLSX) — capped at 60s
      "3": 74.29   // multimodal (audio/video/image) — capped at 300s
    }
  },
  "queue": {"queued": 0, "extracting": 1, "error_24h": 0},
  "metrics": {"extract_success_rate_24h": 1.0}
}
```

**Health indicators**:
- Worker heartbeat fresh (separate task writes every 5s, decoupled from job duration)
- 0 errors in last 24h after v9.4.7 deployment
- Rolling averages stable within cap thresholds

---

## 7. Architecture & Tech Stack

### Backend
- **Runtime**: Python 3.11 + FastAPI + Uvicorn (single-process async)
- **Database**: SQLite via aiosqlite, WAL journal mode (concurrent-safe writes)
- **Schema**: 19 tables; main `files` table has 30+ columns (recently extended with 7 v9.4.0 queue fields + WAL migration)
- **AI / LLM**:
  - **Google Gemini 2.5 Flash** via `google-genai` SDK — multimodal (image/audio/video), File API
  - **Gemini 3 Flash** via OpenRouter — chat / summary / lightweight LLM tasks
- **Auth**: JWT (HS256, 24h expiry) + bcrypt + Google OAuth 2.0
- **MCP**: Streamable HTTP transport, 22 tools per Anthropic spec
- **Billing**: Stripe Checkout + Webhook + Customer Portal
- **Vector**: TF-IDF in-memory + `chroma_db/` foundation (future migration)

### Frontend
- **Stack**: Vanilla HTML/CSS/JS + D3.js v7 (zero framework, zero build)
- **Why**: Solo founder. Adding new pages = edit 3 files (HTML/CSS/JS). Trade-off explicitly chosen for velocity over scale.
- **Files**:
  - `app.html` ~1700 lines (sections + modals)
  - `app.js` ~5100 lines (page system + UploadTray + i18n + all logic)
  - `styles.css` ~5300 lines (CSS variables + UI Foundation Contract v9.3+)
- **i18n**: Bilingual TH/EN via `I18N` dict + `t(key, vars)` function (v9.4.0 added var substitution)

### Infrastructure (Fly.io)
- **Region**: Singapore (sin) — primary
- **Machines**: 2× `shared-cpu-2x` 2GB RAM with `auto_stop_machines = "stop"`
- **Volume**: Persistent `/app/data` (SQLite + uploads + heartbeat file)
- **Build**: Dockerfile via Depot — Python 3.11-slim + tesseract-ocr-tha/eng + poppler-utils
- **Domain**: personaldatabank.fly.dev (Cloudflare-fronted, force HTTPS)

### Upload Pipeline (the critical path)

```
┌─────────┐    ┌──────────┐    ┌─────────┐    ┌──────────┐    ┌──────────┐
│ Browser │───▶│ /api/    │───▶│ SQLite  │───▶│ Async    │───▶│ DB row   │
│ Upload  │    │ upload   │    │ row     │    │ Worker   │    │ updated  │
└─────────┘    │ (<200ms) │    │ status= │    │ extract  │    │ status=  │
               └──────────┘    │ queued  │    └──────────┘    │ uploaded │
                               └─────────┘         │           └──────────┘
                                                   │
                                          ┌────────┴─────────┐
                                          │  Route by ext:   │
                                          │  • doc → Docling │
                                          │    / PyPDF2 /    │
                                          │    Tesseract OCR │
                                          │  • audio/video   │
                                          │    → Gemini API  │
                                          │  • image → Gemini│
                                          │    Vision        │
                                          └──────────────────┘
```

### BYOS Architecture (v7.0+, optional per-user)

```
┌─────────────────────────────────────────────────────────────┐
│ User's Google Drive (Source of truth — storage_mode=byos)    │
│ /Personal Data Bank/                                          │
│   ├── raw/         original files                            │
│   ├── extracted/   plain text                                │
│   ├── summaries/   AI markdown                               │
│   ├── personal/    profile.json + contexts.json              │
│   ├── data/        clusters/graph/relations/chat_history.json│
│   ├── _meta/       schema version + manifest                 │
│   └── _backups/    weekly snapshots                          │
└─────────────────────────────────────────────────────────────┘
                            ↕ sync (poll every 5 min + on-write)
┌─────────────────────────────────────────────────────────────┐
│ PDB Server (Cache + Index)                                   │
│ SQLite — minimal cache:                                       │
│   • user account + OAuth refresh_token (Fernet encrypted)    │
│   • storage_mode = "managed" | "byos"                        │
│   • drive_connection (email, last_sync_at)                   │
│   • files index (file_id ↔ drive_file_id, hash, modified)    │
│   • vector embeddings (rebuildable from Drive)               │
└─────────────────────────────────────────────────────────────┘
```

### Extraction strategy per format
| Format | Tool | Avg time | Notes |
|---|---|---|---|
| TXT / CSV / code | UTF-8 read | < 1s | Encoding fallback chain |
| PDF (text-based) | Docling → PyPDF2 fallback | 3-15s | Preserves markdown structure |
| PDF (image-based) | Tesseract OCR Thai+English | **60s/page** capped 20 pages | ⚠️ **Main bottleneck** |
| DOCX | Docling → python-docx fallback | 2-5s | |
| XLSX / PPTX | openpyxl / python-pptx | 1-3s | |
| Audio (MP3/WAV/M4A) | Gemini 2.5 Flash multimodal | 6-15s | Files API + wait_for_active |
| Video (MP4/MOV) | Gemini 2.5 Flash multimodal | 15-90s | Visual + audio combined |
| Image (JPG/PNG/HEIC) | Gemini 2.5 Flash Vision | 10-20s | 4-section prompt |

---

## 8. Engineering History (Full timeline)

### Major milestones
| Version | Date | Highlight |
|---|---|---|
| v1 (Project KEY) | early 2026 | Initial MVP — chat-with-files |
| v5.0-5.6 | mid-2026 | JWT auth + Context Memory + Guide System |
| v5.8-5.9.3 | late-mid 2026 | Stripe billing + Plan limits + Locked-data guards |
| v6.0 | 2026-04 | Personality Profile (MBTI/Enneagram/Strengths) |
| v6.1 | 2026-04 | Rebrand: Project KEY → Personal Data Bank |
| v7.0 | 2026-05 | **BYOS** — Google Drive as user storage |
| v8.0 | 2026-05 | Admin plan tier (founder-internal) |
| v9.0 | 2026-05 | Phase B v2 — AI multimodal ingestion foundation |
| v9.1 | 2026-05 | Raw File Vault (unsupported formats searchable by name) |
| v9.2 | 2026-05 | Per-plan file_limit + max_file_size guards |
| v9.3 | 2026-05 | UI Foundation Contract (binding CSS rules) |
| **v9.4.0** | **2026-05-05** | **Upload Queue + Worker** — replaced inline blocking |
| **v9.4.5** | **2026-05-10** | **Heartbeat + Recovery + Cancel** |
| **v9.4.6** | **2026-05-10** | **Progress callback (main loop fix)** |
| **v9.4.7** | **2026-05-11** | **Filename truncation 255-byte ext4 limit** |
| **v9.4.8** | **2026-05-12** | **DELETE guard + ai_pack filter + rolling avg cap** |

---

## 9. Recent Engineering Focus — v9.4.0 → v9.4.8 (7-day intensive)

ระบบ upload queue + worker เพิ่งสร้างใหม่ในเซสชั่นนี้. ก่อนหน้า upload ใช้แบบ inline (block request 30-120s, บางครั้ง 500). ครอบ 9 versions:

### v9.4.0 — Upload Queue Foundation
- เพิ่ม 7 columns ใน `files`: progress_step, progress_pct, queued_at, extract_started_at, extract_completed_at, extract_error, attempt_count
- เปิด **SQLite WAL mode** (concurrent-safe write)
- Async background worker (asyncio.create_task) ใน FastAPI startup
- **Round-robin per-user fairness** sort (atomic claim via UPDATE...WHERE+rowcount check)
- 4 new endpoints: /api/upload-status, /api/upload/{id}/retry, /api/upload/{id}/dismiss-error, /api/healthz/queue
- Frontend: UploadTray UI 360 lines + polling 2s with backoff to 5s
- **Truthfulness Contract (TC-1..TC-6)**:
  - TC-1: ห้ามแสดง % ปลอม (ใช้ indeterminate meter ถ้าไม่รู้)
  - TC-2: stage timestamps จริง (queued/started/completed)
  - TC-3: why_slow text บอก user ตรงๆ
  - TC-4: estimated_wait_sec ใช้ rolling avg จริง
  - TC-5: error message ระบุสาเหตุจริง
  - TC-6: system_status banner

### v9.4.1 — Drive Cleanup Async
- DELETE /api/files/{id} เคยใช้ 180s (3 sub-folder × 60s timeout) → 504 Cloudflare error
- v9.4.1: response ~200ms + Drive cleanup เป็น background_tasks
- F5 guard: `_should_trash_drive_file()` ป้องกัน trash file ที่ user import จาก Picker

### v9.4.2 — AI Ingest Fix (critical — Gemini deprecation)
**สถานการณ์**: Google deprecate `gemini-2.0-flash` 2026-05-10 → 404 NOT_FOUND ทุก audio/video
- เปลี่ยน → `gemini-2.5-flash` + env override `GEMINI_FILE_MODEL`
- **เพิ่ม `_wait_for_file_active()`** — Files API ต้องรอ state=ACTIVE (เดิม immediate call = 400 ทุก video)
- **Implement AI Vision** — เดิม `AI_VISION_FORMATS = set()` (ว่าง) → JPG/PNG ไม่เคยเข้า AI
- **Fix `classify_extraction_status`** — 7 markers ถูกจัดเป็น 'ok' ทั้งที่เป็น error
- Add Gemini error patterns: 404/FAILED_PRECONDITION/PERMISSION_DENIED/INVALID_ARGUMENT

### v9.4.3 — LINE Bot (out of scope)

### v9.4.4 — i18n Boundary
- **`format_user_error()` คืน machine code** (ENCRYPTED/TIMEOUT/MODEL_DEPRECATED/...) แทน Thai string
- Frontend แปลตาม locale: 15 error codes × 2 lang
- `localizeBackendStep()` — 14 regex แปล progress_step TH→EN

### v9.4.5 — Worker Lifecycle Hardening
**User report**: "ระบบประมวลผลหยุด" banner ระหว่าง OCR ขนาดใหญ่ทั้งที่ทำงานปกติ
- **Heartbeat task แยก** — เดิม heartbeat write ใน worker loop เท่านั้น → job class-3 (video ~90s) ทำให้ heartbeat ค้างเกิน 30s = false-positive "stopped"
- **Recovery sweep reset ALL extracting** ที่ startup (เดิม cutoff 30 min)
- **`/api/upload/{id}/cancel`** + Cancel button + confirm dialog + i18n

### v9.4.6 — Progress Callback Fix (critical UX)
**User report**: PDF OCR 5+ นาที แต่ tray ค้าง "เตรียมประมวลผล"
- **Root cause**: `_sync_report` เรียก `asyncio.get_event_loop()` จาก thread pool → ได้ loop คนละตัวกับ main → write ไม่ commit
- **Fix**: capture `_main_loop = asyncio.get_running_loop()` ตอน start_worker
- **ผลลัพธ์**: user เห็น "OCR หน้า 1/20" → "2/20" → ... real-time

### v9.4.7 — Filename Truncation (production user hit 500)
- ชื่อไฟล์ไทย 108 ตัวอักษร = **262 bytes UTF-8** (Thai = 3 bytes/char)
- Linux ext4 max filename = **255 bytes** → `OSError [Errno 36]`
- Fix: trim stem ก่อน save, รักษา extension intact
- **+ `flyctl secrets set GOOGLE_API_KEY=...`** (เดิมไม่ได้ตั้ง → audio/video/image fail ทุกตัว)

### v9.4.8 — Quality Patches (latest)
- **DELETE-while-extracting guard** — บังคับ Cancel ก่อน DELETE ถ้า queued/extracting
- **ai_pack_builder filter `extraction_status='ok'`** (4 จุด) — กัน AI pack รวมไฟล์ error
- **Rolling avg cap** per priority class — outlier (1200s OCR PDF) ไม่ pollute typical estimate (3s text PDF)

---

## 10. Test Methodology & Results

### End-to-end production test (multi-round)
ทดสอบ **13 ไฟล์จริงจาก founder's actual data** upload เข้า prod ผ่าน HTTP API multipart, poll status จนเสร็จ, verify chars + extraction_status

| # | ไฟล์ | ขนาด | ผล | Chars | Notes |
|---|---|---|---|---|---|
| 1 | 02a39b.pdf | 3.6 MB | ✅ | 41,584 | PDF text-based, ~5s |
| 2 | 02a395.pdf | 7.4 MB | ✅ | 44,009 | PDF text-based, ~10s |
| 3 | 1.สัญญาจ้าง Dev (ชาญวิทย์).pdf | 572 KB | ✅ | 12,564 | Thai filename + content |
| 4 | 3.TOR บ2 ปี69 (ลายเซ็น)_compressed.pdf | 5.0 MB | ✅ | 45,258 | **Image-based** — Tesseract 20 หน้า ~20 นาที |
| 5 | รายงานตรวจสอบ...pdf | 71 KB | ✅ | 13,642 | Thai PDF |
| 6 | รายงานการประชุม_20260424.docx | 3.6 MB | ✅ | 7,703 | DOCX |
| 7 | การเตรียมตัว Sales Manager.docx | 3 MB | ✅ | 42,995 | DOCX |
| 8 | ChatGPT thought.docx | 45 KB | ✅ | 51,233 | DOCX |
| 9 | Happywork History Chat.docx | 6 KB | ⚠️ | 31 | **ไฟล์ว่างจริง** (verified DOCX XML: 0 `<w:t>`) |
| 10 | AI_Employee_Personas.xlsx | 23 KB | ✅ | 29,578 | XLSX |
| 11 | ถอดไฟล์เสียง...txt | 176 KB | ✅ | 67,864 | Thai TXT |
| 12 | Image 2-5-2569.png | 1.3 MB | ✅ | 1,407 | **Gemini Vision** — military training scene |
| 13 | รายงานทางการ ฉบับเต็ม...docx | 28 KB | ✅ | 13,326 | **Long Thai filename 262 bytes** — truncation verified |

**Result**: 12/13 PASS (1 = expected behavior for empty file)

### UI E2E test via Playwright (latest, post-v9.4.8)
- ✅ Landing → Register modal → Auto-login → /app v9.4.8
- ✅ Upload audio MP3 → tray opens → file extracts to 86 chars (Gemini Files API)
- ✅ Upload PDF 3.TOR → tray shows step="**OCR หน้า 1/20**" real-time + **"ยกเลิก" button visible**
- ✅ i18n correct (Thai locale shows "กำลังทำ" pill)

### Smoke test files
- `scripts/v9_4_2_smoke.py` — 8 cases (codes, frontend mirror, helpers)
- `scripts/v9_4_3_smoke.py` — same suite v9.4.3 era
- `scripts/edge/edge_cases.py` — 10 cases (audio, corrupt MP4, Thai filename, empty, large text)
- `scripts/prod_upload_smoke.py` — full 13-file prod test
- `scripts/prod_round2_smoke.py` — re-test failed files after fixes
- `scripts/round2_wait_verify.py` — long-poll wait verifier

---

## 11. Bottlenecks (Focus area for expert review)

### 🔴 #1: PDF OCR Speed (HIGHEST IMPACT)
- **Current**: Tesseract OCR sequential per page, ~60s/page on Fly shared-cpu-2x
- **Impact**:
  - 20-page PDF = **20 นาที**
  - 50-page PDF = 50 นาที
  - 100-page PDF = 100 นาที (ถ้าไม่มี cap)
- **Hidden silent data loss**: `extraction.py:346` cap ที่ `last_page=20` → PDF เกิน 20 หน้า extract แค่ 20 หน้าแรก (silent truncation, no warning)
- **Mitigated by**:
  - Progress callback per page (v9.4.6)
  - Cancel button (v9.4.5)
- **Proposed**: ใช้ **Gemini Files API native PDF support** แทน Tesseract สำหรับ image PDF
  - Cost: ~$0.0001/page (Gemini 2.5 Flash multimodal)
  - Speed: ~10x faster (batch processing)
  - Accuracy: better (Thai handwriting, complex layouts)
  - Free tier: 1500 req/day, 15 RPM
- **Comparison**:
  | Method | 20-page PDF | 100-page PDF | Cost/100 pages |
  |---|---|---|---|
  | Tesseract (now) | 20 min | 100 min OR capped 20 pages | $0 |
  | Gemini native PDF | ~2 min | ~10 min | ~$0.01 |

### 🟠 #2: Worker Concurrency = 1
- 1 file extract พร้อมกัน ทั้งระบบ
- User A อัพ 20-min PDF → user B-Z ทุกคนรอ 20 min
- Fly machine = 2 CPU + 2GB RAM (can support 2 concurrent extracts safely)
- Atomic claim ใช้ `UPDATE ... WHERE status='queued'` + rowcount check → race-safe for multi-worker
- **Proposed**: bump → 2 concurrent (asyncio.create_task × 2)

### 🟡 #3: Drive Sync 64 stuck rows (in DB right now)
- **Root cause**: `drive_sync._import_drive_file()` sets `processing_status='uploaded'` but worker pickups เฉพาะ `'queued'`
- **Impact**: User ที่ enable Drive sync → file shown "0 chars"
- **Proposed**: 3 strategies for review:
  - **A — eager download**: sync downloads raw file → set status='queued'
  - **B — lazy download**: worker handles raw_path="" → fetch from Drive then extract
  - **C — vault-only**: treat Drive imports as searchable-by-filename only

### 🟢 #4: Fly auto-stop = cold-start delay
- `auto_stop_machines = "stop"` → machine ปิดเมื่อ idle
- First request after idle = wake delay 5-10s
- Not critical but bad first-time UX

---

## 12. Reliability Gaps

| Gap | Risk Scenario | Severity | Proposed Fix |
|---|---|---|---|
| **No periodic stale sweep** | Worker hang during Gemini call > 30 min → no recovery until restart | MED | Background task every 5 min |
| **Vector index inconsistency** | Worker dies during index update → search returns ghost files | LOW | Cleanup sweep + re-index endpoint |
| **JWT 24h no refresh** | User logout daily | LOW | Refresh token endpoint |
| **No SQLite backup automation** | Fly volume corrupt = total data loss | **HIGH** | Daily `sqlite3 .backup` → R2/S3 cron |
| **No automated CI** | All test runs manual | MED | GitHub Actions on push |

---

## 13. Scaling Concerns

| Issue | Threshold | Estimated impact | Action |
|---|---|---|---|
| Gemini quota 429 | 15 RPM Free tier | Audio/video/image fail | Upgrade Gemini billing (paid = 360 RPM) |
| SQLite write lock | 100+ concurrent uploads | DB lock contention | Migrate to Fly Postgres |
| Single-machine bottleneck | 1000+ DAU | Queue ยาว | Multi-machine (atomic claim ready, need shared DB) |
| Gemini spend uncontrolled | Variable | $X/month possible | Per-user spend cap + monthly alert |
| No upload dedup | Same file 2× upload | Wasted Gemini calls | `duplicate_detector.py` exists — verify integration |

---

## 14. Roadmap Recommendations

### v9.4.9 (1-2 hours, immediate ROI)
1. **Worker concurrency 1 → 2** — throughput ×2, no migration risk
2. **Periodic stale sweep** — background task every 5 min

### v9.5.0 (4-6 hours, game-changer)
3. **Gemini native PDF** แทน Tesseract — 10x faster, no 20-page cap, better Thai accuracy
4. **Drive sync redesign** — choose strategy A/B/C

### v9.5.1 (operational hardening)
5. **SQLite daily backup → R2** — `flyctl ssh "sqlite3 .backup"` cron job
6. **Refresh token + silent re-auth**
7. **Per-user Gemini spend cap**

### v10.0 (scale beyond solo founder)
8. **Multi-machine deployment** — atomic claim ready, need Fly Postgres
9. **Vector embeddings** — TF-IDF → real embeddings (chroma_db foundation laid)
10. **CI/CD pipeline** — GitHub Actions on push, smoke tests required

---

## 15. Risk Register

| Risk | Detection Signal | Mitigation Ready |
|---|---|---|
| Gemini model deprecate (เพิ่งเกิด 2026-05-10) | `error="MODEL_DEPRECATED"` | ✅ env override `GEMINI_FILE_MODEL` |
| Gemini quota exhausted | `error="QUOTA_EXCEEDED"` | ✅ User toast + retry button |
| Fly OOM (PDF ใหญ่) | OOMKilled in Fly logs | ✅ `ABSOLUTE_MAX_FILE_SIZE_MB=200` |
| Fly disk full | `OSError [Errno 28]` | ⚠️ Need volume monitor cron |
| Worker hang | queue stale > 30 min | ⚠️ Need periodic sweep (v9.4.9) |
| Drive auth expired | `invalid_grant` | ✅ UI "เชื่อมต่อใหม่" button |
| Spike load 50+ files | `QUEUE_FULL` 409 | ✅ Per-plan queue cap |
| Fly auto_stop mid-job | Restart from scratch | ✅ Recovery sweep at startup |
| Long Thai filename | OSError 36 | ✅ v9.4.7 truncation |
| DELETE during extract | Worker race | ✅ v9.4.8 409 guard |

---

## 16. Code Quality Assessment

### Strengths
- ✅ **Atomic claim race-safe** สำหรับ multi-worker
- ✅ **Truthfulness Contract enforced** — no fake progress
- ✅ **Idempotent migrations** — ADD COLUMN guarded by PRAGMA table_info
- ✅ **Graceful degradation** — marker-based error returns + retry buttons
- ✅ **i18n boundary clean** — backend codes, frontend translates
- ✅ **Real end-to-end tests** against prod with real files (not just mocks)
- ✅ **Documented engineering decisions** in `.agent-memory/`

### Areas Needing Attention
- ⚠️ **`main.py` = 3500+ lines, 111 endpoints** — should split (auth.py, files.py, queue.py, ...)
- ⚠️ **`app.js` = 5100+ lines monolith** — same issue
- ⚠️ **Single-file SQLite migration in code** — should use Alembic for versioning
- ⚠️ **No automated test suite on push** — currently manual smoke scripts
- ⚠️ **Frontend has no TypeScript / linting**
- ⚠️ **No log aggregation** — only Fly logs (ephemeral)

---

## 17. Operational Notes for Reviewer

### Code & Logs Access
- **Repo**: GitHub `boss2546/project-key` (master branch)
- **Recent commits** (last 10):
  ```
  7a2f84a fix(quality): DELETE guard + ai_pack filter + rolling avg cap [v9.4.8]
  e658c74 fix(upload): truncate filename to 255-byte ext4 limit [v9.4.7]
  9f94765 fix(progress+cancel): main loop reference + always-on Cancel button [v9.4.6]
  015628c fix(worker): heartbeat task + startup recovery + cancel endpoint [v9.4.5]
  f2e707e fix(i18n+reprocess): error CODE boundary + reprocess hardening [v9.4.4]
  c738ff0 feat(v9.4.3): LINE UX 5 fixes + nonce hardening + countdown timer
  f45ab96 fix(ai_ingest): Gemini 2.5 Flash + Vision images + truthful classification [v9.4.2]
  a314a42 feat(delete): comprehensive Drive cleanup async + UI feedback [v9.4.1]
  d81369c fix(ui): tray bottom-right + opaque BG + suppress queue toast [v9.4.0.2]
  ```
- **Test scripts**: `scripts/v9_4_*_smoke.py`, `scripts/edge/edge_cases.py`, `scripts/prod_*_smoke.py`
- **OpenAPI docs (auto)**: https://personaldatabank.fly.dev/docs
- **Logs**: `flyctl logs --app personaldatabank` (live tail)
- **Memory & decisions**: `d:\PDB\.agent-memory\` (project context, plans, conventions)
- **PRDs**: `d:\PDB\docs\prd\` (PRD_v1.md, PRD_v5.5_Context_Memory.md, etc.)

### Test Account Setup
- Self-register at https://personaldatabank.fly.dev/ — Free tier (10 file queue cap, 100MB max)
- Sandbox account currently exists for testing (created during smoke runs)

---

## 18. Open Questions for Expert Review

1. **PDF OCR strategy**: เปลี่ยน Tesseract → Gemini native PDF คุ้มไหม สำหรับ Free tier user (cost vs UX trade-off)? มี alternative ที่ดีกว่าทั้งคู่ไหม (เช่น `marker` open-source)?

2. **Worker concurrency**: bump 1 → 2 บน 2-CPU machine ปลอดภัยไหม? ควรเพิ่ม **semaphore limit** ที่ Gemini API call ด้วยไหม (15 RPM Free tier)?

3. **Drive sync**: 64 ไฟล์ค้างใน DB — ควรเลือก strategy ไหน:
   - A) eager download (สิ้นเปลือง bandwidth + Fly volume)
   - B) lazy download in worker (complex worker logic)
   - C) treat as vault-only (no extraction, search by filename)

4. **Scaling threshold**: เมื่อไหร่ควร migrate SQLite → Postgres? Indicator ที่ดี (DAU/QPS/latency)?

5. **Solo developer constraints**: founder ทำคนเดียว — มี tools/patterns อะไรลด maintenance burden? Should I push for framework migration now or keep vanilla JS?

6. **MCP tool priority**: 22 tools ปัจจุบัน — ควรเพิ่ม priority ไหนสำหรับ Personal AI Context tier vs Executive Twin tier?

7. **Pricing**: ฿99/Starter cover cost ของ user ทั่วไป (10-50 files/month, ~100 AI calls) ไหม? ควรปรับ Free tier limits ไหม (50 files → 20)?

8. **Backup strategy**: SQLite WAL on Fly volume — แนะนำ backup frequency + destination?

---

**Report compiled by**: Engineering session (Claude Opus 4.7, 1M context)
**Verified against prod**: https://personaldatabank.fly.dev as of 2026-05-12 02:10 UTC
**File location**: `d:\PDB\REPORT-v9.4.8.md`
**Format**: Markdown — render via GitHub / VS Code preview / Notion import
**For sharing**:
- Markdown direct (Notion/email/Slack)
- `gh gist create d:/PDB/REPORT-v9.4.8.md --secret`
- Print → PDF via VS Code Markdown Preview
