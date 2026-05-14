# Personal Data Bank (PDB) — Software Design Document (Blueprint)

> **Version:** v9.4.8 snapshot (2026-05-13)
> **Purpose:** พิมพ์เขียวฉบับสมบูรณ์ — ถ้าจะสร้าง PDB ใหม่จาก 0 → production อ่านเอกสารนี้แล้วทำตามได้
> **Audience:** Senior engineer ที่จะ rebuild หรือ fork
> **Source:** Synthesis จาก [REPORT-v9.4.8.md](../../REPORT-v9.4.8.md), [.agent-memory/](../../.agent-memory/), และ source code audit

---

## สารบัญ

- [§0 วิธีใช้เอกสารนี้](#0-วิธีใช้เอกสารนี้)
- [§1 Product Vision & Scope](#1-product-vision--scope)
- [§2 Architecture Overview](#2-architecture-overview)
- [§3 Data Model (Schema)](#3-data-model-schema)
- [§4 Backend Module Map](#4-backend-module-map)
- [§5 Upload Pipeline State Machine](#5-upload-pipeline-state-machine)
- [§6 AI & Knowledge Layer](#6-ai--knowledge-layer)
- [§7 REST API Surface](#7-rest-api-surface)
- [§8 MCP Integration](#8-mcp-integration)
- [§9 BYOS — Google Drive Sync](#9-byos--google-drive-sync)
- [§10 Auth, Identity & Plan Limits](#10-auth-identity--plan-limits)
- [§11 Frontend Architecture](#11-frontend-architecture)
- [§12 Design System & UI Foundation](#12-design-system--ui-foundation)
- [§13 Infrastructure & Deployment](#13-infrastructure--deployment)
- [§14 Operations & Reliability](#14-operations--reliability)
- [§15 Security Model](#15-security-model)
- [§16 Rebuild Roadmap (15 Phases)](#16-rebuild-roadmap-15-phases)
- [§17 Appendix](#17-appendix)

---

## §0 วิธีใช้เอกสารนี้

เอกสารนี้เป็น **blueprint** ไม่ใช่คู่มือผู้ใช้ ไม่ใช่ marketing material อ่านลำดับนี้ถ้าจะ rebuild:

1. §1 → เข้าใจ "ทำไมมี product นี้" ก่อน ห้ามข้าม
2. §2 → architecture overview, ADRs, tech choices
3. §3-§6 → backend core (DB, modules, pipeline, AI)
4. §7-§8 → API surface สำหรับ frontend/MCP
5. §9-§10 → integrations + auth
6. §11-§12 → frontend
7. §13-§15 → ops + security
8. §16 → step-by-step rebuild

**Convention:** อ้างอิงโค้ดจริงใช้ `[file](path#L123)` รูปแบบ markdown link

---

## §1 Product Vision & Scope

### §1.1 หลักการสูงสุด (Foundational Beliefs)

3-layer vision ที่ตัด/แก้ไม่ได้:

1. **ความเชื่อพื้นฐาน** — *preserve the value of data through time* — ของสำคัญในชีวิตที่ไม่หาย
2. **ภาพโลกที่อยากเห็น** — important things don't get lost over time
3. **เป้าหมายการลงมือทำ** — make data usable everywhere, seamlessly

### §1.2 3-Attribute Promise (Core Spec ที่ห้ามแหก)

PDB เก็บข้อมูล user ให้:
- **เก็บอย่างดี** (kept well) — preserve original, no loss
- **เป็นส่วนตัว** (private) — user เท่านั้นที่เห็น
- **เป็นระบบ** (organized) — AI ช่วยจัด ไม่ใช่ user จัดเอง

### §1.3 4 Product Principles (Locked)

| # | Principle | ผลต่อ design |
|---|---|---|
| 1 | Private by default | ทุก endpoint filter `user_id`; ไม่มี global feed/social |
| 2 | Original file preserved | เก็บ `raw_path`; extraction ไม่ destroy ต้นฉบับ |
| 3 | Organized by system | AI organizer + clustering, ไม่ใช่ user folder |
| 4 | AI use must be explainable | ต้อง return `sources`/`context_used` ทุก chat |

### §1.4 Definition of "Data" — Hybrid

ไม่ใช่แค่ cloud storage:
- **Digital files** — PDF/DOCX/รูป/เสียง/วิดีโอ (technical layer)
- **ความทรงจำสำคัญ** (emotional value) — voice memos, photos, personal notes (humanity layer)

→ จุดต่างจาก Drive/Notion/Dropbox: **Usability + Human Significance**

### §1.5 Target Market & Tiers

| Tier | Price | Target | Key Limits |
|---|---|---|---|
| Free | ฿0/mo | นักศึกษา + ทดลอง | 50 files / 500 MB / 50 AI summary/mo |
| Starter | ฿99/mo | ครู / นักการตลาด / ครีเอเตอร์ | 500 files / 10 GB / 1,000 AI summary/mo |
| ED-Core | ฿12K/mo | Founders/Executives (demo only) | Private Identity Vault + Decision Matrix |
| ED-Pro | ฿25K/mo | Recommended tier | + Voice clone + 200K API calls/mo |
| ED-Elite | ฿45K/mo | High-profile | + Avatar UI + Dedicated CSM |
| ED-Legacy | ฿8K/mo | Knowledge preservation | Read-only Twin + archive |

### §1.6 Sales Narrative (ตึงไว้ในใจตอนเขียน copy)

> "ลูกค้าไม่ได้ซื้อเทคโนโลยี — ลูกค้าซื้อการเอาความวุ่นวายออกไปจากชีวิต"

Transform: **scattered chats/emails/papers → digital system AI-ready**

---

## §2 Architecture Overview

### §2.1 4-Layer Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│ LAYER 1: CLIENTS                                                     │
│  • Browser (vanilla JS frontend)                                     │
│  • Claude Desktop / ChatGPT / Antigravity (MCP)                      │
│  • LINE Bot (webhook)                                                │
│  • Stripe (webhook)                                                  │
└────────────────────────┬─────────────────────────────────────────────┘
                         │ HTTPS
                         ▼
┌──────────────────────────────────────────────────────────────────────┐
│ LAYER 2: APPLICATION (FastAPI on Fly.io, Singapore)                  │
│  • REST API: 124 endpoints, JWT auth                                 │
│  • MCP Streamable HTTP: /mcp/{user_secret} JSON-RPC 2.0              │
│  • Webhook handlers (LINE HMAC, Stripe signature)                    │
│  • Async upload worker (1 task, in-process)                          │
│  • Background sync (Drive BYOS poll)                                 │
└────────────────────────┬─────────────────────────────────────────────┘
                         │
            ┌────────────┴───────────┐
            ▼                        ▼
┌──────────────────────────┐  ┌─────────────────────────────┐
│ LAYER 3: STORAGE          │  │ LAYER 4: EXTERNAL AI         │
│  • SQLite (aiosqlite+WAL) │  │  • Gemini 2.5 Flash (vision/ │
│  • Fly volume /app/data   │  │    audio/video via Files API)│
│  • ChromaDB (foundation,  │  │  • Gemini 3 Flash via        │
│    not yet active)        │  │    OpenRouter (chat/organize)│
│  • Optional BYOS:         │  │  • Tesseract OCR (system)    │
│    User's Google Drive    │  │  • Docling/PyPDF2 (local)    │
└──────────────────────────┘  └─────────────────────────────┘
```

### §2.2 Architectural Decision Records (ADRs)

ดูฉบับเต็มใน [.agent-memory/project/decisions.md](../../.agent-memory/project/decisions.md) — สรุป 25 ADR หลัก:

#### Database & Schema
| # | Decision | Why |
|---|---|---|
| DB-001 | SQLite + aiosqlite + WAL, **ไม่ใช้ Postgres** | Simplicity + Fly volume mount; ห้าม migrate ถ้าไม่มี requirement ใหม่ |
| DB-002 | ChromaDB embedded (in `/chroma_db/`, **ห้าม commit** ลง git) | ไม่ต้องรัน vector DB แยก |
| DB-003 | Migration safety: ADD only, idempotent, auto-backup | Prod DB ใน Fly volume — broken migration = lost data |

#### Frontend & Auth
| # | Decision | Why |
|---|---|---|
| FE-001 | Frontend คง vanilla HTML/JS — **ไม่ migrate ไป React/Vue** | Solo founder velocity, no budget for migration |
| AUTH-001 | JWT stateless | MCP-friendly; ไม่มี sessions |

#### MCP (Core Value Prop)
| # | Decision | Why |
|---|---|---|
| MCP-001 | MCP เป็น first-class — ทุก API ใหม่ควรพิจารณา MCP equivalent | จุดขายหลัก: ให้ Claude/AI access ข้อมูล |
| MCP-002 | URL-secret-in-path (`/mcp/{secret}`) | Claude Desktop/Antigravity/mcp-remote ไม่ใส่ Bearer ใน initialize call |

#### Billing & Plans
| # | Decision | Why |
|---|---|---|
| BILL-001 | Stripe เดียว — ห้ามเสนอเพิ่ม PayPal | v5.9.3 ลงทุนกับ Stripe เยอะแล้ว |
| BILL-002 | Plan ×10 baseline (Free 50 files / Starter 500) ตั้งแต่ v8.0.2 — **ห้าม revert** | Production decision 2026-05-05; pricing strategy ผูกแน่น |

#### Security
| # | Decision | Why |
|---|---|---|
| SEC-001 | Locked-data guards (v5.9.3) | ป้องกันแก้ไข share/reprocess/regenerate ตอนข้อมูล lock |
| SEC-002 | Refresh tokens encrypted (Fernet AES-128+HMAC) | DB leak alone ห้าม expose user's Drive data — **ห้าม commit key ใน docs** (lesson: commit `d75d5ea` leak, fixed `58e8b9d`) |

#### Storage / BYOS
| # | Decision | Why |
|---|---|---|
| STORAGE-001 | Hybrid: Drive = source of truth, Server = cache + index | Pure cloud = slow search; pure server = no user sovereignty |
| STORAGE-002 | `drive.file` scope (Phase 1) — defer full `drive` to Phase 2 | Full `drive` ต้อง CASA verification ($25K-85K/yr + 6mo); `drive.file` ฟรี + 2-4 สัปดาห์ |
| STORAGE-003 | Coexist managed + BYOS (no forced migration) | New users default managed; opt-in BYOS |
| STORAGE-004 | Transparent JSON in Drive (no content encryption) | "Open your Drive — we hide nothing" (refresh tokens still encrypted per SEC-002) |
| STORAGE-005 | Testing mode for MVP launch (`GOOGLE_OAUTH_MODE=testing`) | Verification 2-4 weeks; refresh token 7-day expiry acceptable for early adopters |
| STORAGE-006 | Invalid_grant graceful coverage (all 9 push helpers) — v9.3.5 | Live test 2026-05-10: 8 files stuck local + sync 500. Pattern = canonical reference for all future push helpers |
| STORAGE-007 | Submit Google OAuth verification (founder action) | 7-day refresh expiry = poor UX long-term. Status: OPEN |
| STORAGE-008 | Comprehensive Delete + Sync cleanup contract (v9.4.1) | 10 edge cases discovered: 3 sub-folder cleanup, storage_source guard, DELETE async, F24 push guard, orphan retry budget, deleted_in_drive filter |

#### Duplicate Detection
| # | Decision | Status |
|---|---|---|
| DUP-001 | SHA-256 + TF-IDF (no LLM) for dedup | Free + fast; ≥ 80% similar caught; paraphrase 50-80% deferred to Phase 2 |
| DUP-002 | Skip action = soft delete + Drive trash (recoverable 30d) | Storage_router cleanup helpers; best-effort fail-open |
| DUP-003 | Trigger = organize-time (not upload-time) — user override 2026-05-01 | Vector index พร้อมเต็ม → semantic detection ครอบคลุมกว่า |
| DUP-004 | **DISABLED** since v9.3.2 (`_DEDUP_DISABLED=True`) | UnicodeEncodeError on PDF surrogates → HTTP 500. Re-enable: flip flag + smoke (5 steps) |

#### Rebrand
| # | Decision | Why |
|---|---|---|
| REBRAND-001 | Keep `projectkey.db` filename; Fly app renamed `project-key` → `personaldatabank` (migration 2026-05-01) | Original plan: keep both. localStorage keys MIGRATED to `pdb_*` ใน app.js:40-44. Fly app rename executed during migration despite earlier deferral. |
| REBRAND-002 | `backend/config.py:APP_VERSION = "9.4.8"` = canonical source-of-truth | Multiple display points; minor drift in `index.html` flagged |

#### Operations & Tests
| # | Decision | Why |
|---|---|---|
| DEPLOY-001 | Fly.io = production target | Dockerfile + fly.toml + volume ready |
| DEPLOY-002 | Fly.io app renamed `project-key` → `personaldatabank` (migration 2026-05-01) | Original "keep" decision reversed; volume migrated + DNS swap completed |
| TEST-001 | Real DB tests, **ไม่ใช่ mocks** | Mock/prod divergence = pain |
| TEST-002 | In-process FastAPI TestClient + real SQLite | Sandbox ห้าม uvicorn port bind; BYOS tests inject DriveClient |

#### LINE Bot
| # | Decision | Why |
|---|---|---|
| LINE-001 | LINE Connect button opens bot URL directly (`https://line.me/R/ti/p/%40<id>`) — `/api/line/connect` กลายเป็น dead code | LINE Messaging API spec: `linkToken` ออกได้เฉพาะหลัง user follow bot; server-initiated link ทำไม่ได้ |

#### Worker
| # | Decision | Why |
|---|---|---|
| WORK-001 | Atomic claim worker, single concurrency = 1 | SQLite WAL ปลอดภัย; plan bump → 2 ใน v9.4.9 |
| WORK-002 | Truthfulness Contract TC-1..6 | ห้ามแสดง progress ปลอม |
| WORK-003 | Auto-stop machines (Fly) | Cost saving; cold start 5-10s trade-off accepted |

#### UI
| # | Decision | Why |
|---|---|---|
| UI-001 | UI Foundation Contract v9.3.0+ — 11-item checklist | Token+atom system; ห้ามสร้าง variant ใหม่ |
| UI-002 | Signed JWT download URLs (stateless) | Scale across instances, TTL-based |

### §2.3 Tech Stack (Full Inventory)

#### §2.3.1 Languages & Runtime

| Component | Choice | Version | Why |
|---|---|---|---|
| Backend language | Python | **3.11** (slim image) | Async/await mature, type hints, FastAPI sweet spot |
| Frontend language | Vanilla JS (ES6+) | — | No build chain, no transpiler |
| Markup | HTML5 | — | Semantic tags, no JSX |
| Styles | CSS3 + CSS Variables | — | Token system (ห้าม `!important`) |

#### §2.3.2 Backend Framework

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | **0.115.6** | Async web framework |
| `uvicorn[standard]` | **0.34.0** | ASGI server (uvloop + httptools) |
| `python-multipart` | **0.0.20** | Multipart form parsing (file upload) |
| `pydantic` | **2.10.4** | Request/response validation |
| `httpx` | **0.28.1** | Async HTTP client (OpenRouter, Google APIs) |
| `pyyaml` | `>=6.0` | YAML config parsing |
| `python-dotenv` | `>=1.0.0` | Load `.env` in dev |

#### §2.3.3 Database & ORM

| Package | Version | Purpose |
|---|---|---|
| `sqlalchemy` | **2.0.36** | ORM (async support) |
| `aiosqlite` | **0.20.0** | Async SQLite driver |
| `chromadb` | `>=1.5.0` | Vector DB (**dev only**, foundation for v10) |

**SQLite config:**
- `PRAGMA journal_mode=WAL` (v9.4.0+)
- `PRAGMA foreign_keys=ON`
- Connection string: `sqlite+aiosqlite:///{DATA_DIR}/projectkey.db`

#### §2.3.4 Auth & Security

| Package | Version | Purpose |
|---|---|---|
| `python-jose[cryptography]` | `>=3.3.0` | JWT (HS256, 24h expiry) |
| `passlib[bcrypt]` | `>=1.7.4` | Password hashing wrapper |
| `bcrypt` | `>=4.0.0` | Password hash backend (prod requires explicit pin) |
| `cryptography` | `>=42.0.0` | Fernet (AES-128 + HMAC) for Drive refresh_token |

#### §2.3.5 AI / LLM Providers

| Service | SDK | Model | Use |
|---|---|---|---|
| **OpenRouter** | `httpx` (no SDK) | `google/gemini-3-flash-preview` | Chat, organize, summary (`LLM_MODEL`) |
| **OpenRouter** | `httpx` | `google/gemini-3-flash-preview` | Pro tier (`LLM_MODEL_PRO`, same as Flash currently) |
| **Google Gemini Direct** | `google-genai>=0.3.0` | `gemini-2.5-flash` (`GEMINI_FILE_MODEL`) | Multimodal Files API (audio/video/image) |

**Why split:** OpenRouter ไม่ support Files API ดีพอ + Gemini Direct มี wait_for_active() + Files API ที่ Gemini ออกแบบเอง

**Provider routing (OpenRouter):**
```json
{"provider": {"order": ["Google"], "allow_fallbacks": true}}
```

#### §2.3.6 Document Processing

| Package | Version | Format | Notes |
|---|---|---|---|
| `docling` | `>=2.80.0` | PDF/DOCX (high-quality) | **Dev only** — heavy deps (~2GB), prod ใช้ PyPDF2 |
| `PyPDF2` | **3.0.1** | PDF (text-based) | Fallback when Docling absent |
| `python-docx` | **1.1.2** | DOCX | |
| `python-pptx` | `>=0.6.23` | PPTX | |
| `openpyxl` | `>=3.1.0` | XLSX | |
| `beautifulsoup4` | `>=4.12.0` | HTML | |
| `striprtf` | `>=0.0.26` | RTF | |

#### §2.3.7 OCR & Images

| Package | Version | Purpose |
|---|---|---|
| `pytesseract` | `>=0.3.10` | Python binding for system Tesseract |
| `pdf2image` | `>=1.16.0` | PDF → PIL Image (needs poppler-utils system pkg) |
| `Pillow` | `>=10.0.0` | Image processing |
| `pillow-heif` | `>=0.18.0` | HEIC/HEIF (iPhone default format) |

**System OCR dependency:** `tesseract-ocr` + `tesseract-ocr-tha` + `tesseract-ocr-eng` (apt-get) — **ห้ามลืม Thai pack** ([Dockerfile:8-11](../../Dockerfile))

#### §2.3.8 Payments & Communication

| Package | Version | Purpose |
|---|---|---|
| `stripe` | `>=8.0.0` | Checkout + Webhook + Portal (signature verify built-in) |
| `resend` | `>=2.0.0` | Transactional email (password reset) |
| `line-bot-sdk` | `>=3.11.0` | LINE Messaging API + webhook signing |

#### §2.3.9 Google APIs (BYOS Drive + OAuth Login)

| Package | Version | Purpose |
|---|---|---|
| `google-auth` | `>=2.30.0` | OAuth2 token handling |
| `google-auth-oauthlib` | `>=1.2.0` | OAuth2 flow helpers |
| `google-auth-httplib2` | `>=0.2.0` | HTTP transport |
| `google-api-python-client` | `>=2.140.0` | Drive API client |

**OAuth scopes:**
- Login: `openid` + `email` + `profile`
- Drive BYOS: `drive.file` (Phase 1, FREE verification) — NOT full `drive` (STORAGE-002: CASA $25K+/yr)

#### §2.3.10 Frontend Stack

| Component | Choice | Version | Notes |
|---|---|---|---|
| Markup | HTML5 | — | Semantic tags |
| Styles | CSS3 + variables | — | shared.css = 718 lines, styles.css = 5321, landing.css = 739 |
| Logic | Vanilla JS (ES6+) | — | app.js = 5957 lines, landing.js = 621 |
| Graph viz | **D3.js** | **v7** | Force-directed simulation |
| Build | **None** | — | No webpack/vite/rollup |
| Bundler | **None** | — | Cache-bust via `?v=9.4.8` query string |
| Framework | **None** (intentional, FE-001 + ADR-002) | — | Solo founder velocity > scale |

**Load order in [app.html](../../legacy-frontend/app.html):**
```html
<script src="/legacy/app.js?v=9.4.8" defer></script>
<script src="/legacy/storage_mode.js?v=9.4.8" defer></script>
<script src="/legacy/line_ui.js?v=9.4.8" defer></script>
<script src="/legacy/landing.js?v=9.4.8" defer></script>
```

#### §2.3.11 Infrastructure

| Layer | Choice | Spec |
|---|---|---|
| **Cloud** | Fly.io | Region `sin` (Singapore primary) |
| **Container** | Docker (Python 3.11-slim base) | Built via Fly Depot |
| **Machine** | shared-cpu-2x | 2 CPU + **2048 MB RAM** |
| **Volume** | Persistent disk | `project_key_data` → mounted at `/app/data` |
| **Auto-scale** | `auto_stop_machines = "stop"` + `min_machines_running = 1` | Cost saving; cold start 5-10s |
| **TLS** | Auto-managed by Fly | `force_https = true` |
| **CDN** | Cloudflare-fronted | Custom domain `personaldatabank.fly.dev` |
| **Internal port** | 8000 | Uvicorn |

#### §2.3.12 System Packages (Debian apt-get)

จาก [Dockerfile](../../Dockerfile):
```bash
tesseract-ocr           # OCR engine
tesseract-ocr-tha       # Thai language pack ⚠️ CRITICAL
tesseract-ocr-eng       # English
poppler-utils           # PDF rendering (pdf2image dependency)
```

#### §2.3.13 DevTools & Testing

| Tool | Version | Purpose |
|---|---|---|
| `@playwright/test` | `^1.59.1` | E2E browser tests (TH + EN locales) |
| `pytest` | (latest) | Python unit + integration tests |
| `flyctl` | (latest) | Fly.io deploy + secrets + logs |

**Test commands** ([package.json](../../package.json)):
```json
"test": "npx playwright test",
"test:api": "python -m pytest tests/test_production.py -v",
"test:ui": "npx playwright test --reporter=list",
"test:all": "python -m pytest tests/test_production.py -v && npx playwright test --reporter=list"
```

#### §2.3.14 External Services (Account Setup สำหรับ Rebuild)

| Service | Plan | Cost | Required? |
|---|---|---|---|
| **Fly.io** | Hobby (auto-billing) | ~$2-5/mo for shared-cpu-2x | ✅ Production deploy |
| **OpenRouter** | Pay-per-token | Variable (Gemini 3 Flash cheap) | ✅ Chat/organize |
| **Google AI Studio** | Free tier 1500 req/day | Free → $0.0001/req paid | 🟡 Multimodal audio/video/image |
| **Google Cloud Console** | OAuth credentials (Web app) | Free | 🟡 Drive BYOS + Login |
| **Stripe** | Pay-per-tx 2.9% + 30¢ | Free until first sale | 🟡 Billing |
| **Resend** | Free tier 100/day, 3K/mo | Free → $20/mo (50K) | 🟡 Password reset email |
| **LINE Developers** | Free Messaging API | Free (limited push msgs) | 🟡 LINE bot |
| **Cloudflare** (optional) | DNS + edge | Free | 🟢 If custom domain |

#### §2.3.15 Browser/Client Compatibility

| Client | Min Version | Notes |
|---|---|---|
| Chrome | 90+ | ES6+, fetch, async/await native |
| Safari | 14+ | iOS Safari 14+ for HEIC paste |
| Firefox | 88+ | |
| Edge | Chromium | Same as Chrome |
| **Claude Desktop** | Latest | MCP Streamable HTTP support |
| **ChatGPT** | Latest | MCP Custom Connector |
| **Antigravity** | Latest | MCP via per-user secret URL |
| **LINE Mobile** | iOS/Android | Webhook + flex messages |

#### §2.3.16 Dev vs Prod Dependency Diff

| Package | dev `requirements.txt` | prod `requirements-fly.txt` | Why |
|---|---|---|---|
| `docling` | ✅ `>=2.80.0` | ❌ | Heavy (~2GB), prod fallback to PyPDF2 |
| `chromadb` | ✅ `>=1.5.0` | ❌ | Vector DB foundation, ยังไม่ใช้ใน prod |
| `bcrypt` | ❌ (transitive via passlib) | ✅ `>=4.0.0` | Prod ต้องการ explicit pin |

ที่เหลือเหมือนกัน 100%

#### §2.3.17 LLM Cost Profile (Approximate)

| Operation | Model | Cost per call |
|---|---|---|
| Chat (1 question) | Gemini 3 Flash | ~$0.0001 |
| Summarize 1 file | Gemini 3 Flash | ~$0.0003 |
| Organize 10 files | Gemini 3 Flash | ~$0.002 |
| Audio transcribe (5 min) | Gemini 2.5 Flash multimodal | ~$0.005 |
| Video analyze (30 min) | Gemini 2.5 Flash multimodal | ~$0.01-0.03 |
| Image OCR + describe | Gemini 2.5 Flash Vision | ~$0.001 |
| PDF native (proposed v9.5) | Gemini 2.5 Flash | ~$0.0001/page |

**Free tier limits (Google AI Studio):**
- 15 RPM
- 1500 RPD
- 1M TPM (tokens per minute)

**Paid tier (after upgrade):**
- 360 RPM (24x)
- ∞ RPD
- 4M TPM

---

---

## §3 Data Model (Schema)

### §3.1 Schema Overview — 26 Tables

SQLite database file: `data/projectkey.db` (legacy name; **DB-001 + REBRAND-001 = keep filename** เพราะ rename = downtime + Fly volume migration high risk)

**ตารางทั้ง 26 ตัว** (verified จาก [database.py](../../backend/database.py) class declarations):

| # | Class | Table | Purpose |
|---|---|---|---|
| 1 | `User` | users | Account + auth + plan + mcp_secret + storage_mode |
| 2 | `File` | files | Uploaded files + extraction state + queue fields |
| 3 | `Cluster` | clusters | AI-generated groupings |
| 4 | `FileClusterMap` | file_cluster_map | N:N bridge with relevance_score |
| 5 | `FileInsight` | file_insights | importance_score + label |
| 6 | `FileSummary` | file_summaries | AI summary + key_topics + key_facts |
| 7 | `ChatQuery` | chat_queries | Chat history |
| 8 | `UserProfile` | user_profiles | Identity + goals + personality (v6.0) |
| 9 | `ContextPack` | context_packs | Reusable AI prompt bundles |
| 10 | `ContextInjectionLog` | context_injection_logs | Per-chat retrieval audit |
| 11 | `NoteObject` | note_objects | Notes/entities/concepts/persons/projects/tags |
| 12 | `GraphNode` | graph_nodes | Knowledge graph nodes |
| 13 | `GraphEdge` | graph_edges | Graph edges (typed, weighted, directed) |
| 14 | `SuggestedRelation` | suggested_relations | LLM-proposed relations awaiting approval |
| 15 | `GraphLens` | graph_lenses | Saved graph views/filters |
| 16 | `CanvasObject` | canvas_objects | Future canvas workspace (v3.1+) |
| 17 | `PersonalityHistory` | personality_history | Append-only personality audit (v6.0) |
| 18 | `ContextMemory` | context_memories | Cross-platform context (v5.5) |
| 19 | `MCPToken` | mcp_tokens | `pk_*` Bearer tokens (SHA-256 hash) |
| 20 | `MCPUsageLog` | mcp_usage_logs | Per-tool call audit |
| 21 | `WebhookLog` | webhook_logs | Stripe webhook idempotency (v5.9.2) |
| 22 | `UsageLog` | usage_logs | Monthly quota tracking (v5.9.3) |
| 23 | `AuditLog` | audit_logs | Plan changes + usage limits + file locks |
| 24 | `DriveConnection` | drive_connections | BYOS OAuth state (Fernet-encrypted refresh_token) |
| 25 | `PackShare` | pack_shares | Public pack shares (v9.3.0) |
| 26 | `LineUser` | line_users | LINE account linking (v8.0.0+) |

**Setup at startup:**
```python
await db.execute("PRAGMA journal_mode=WAL")  # v9.4.0+
await db.execute("PRAGMA foreign_keys=ON")
```

### §3.2 Core Tables

#### `users`
| Column | Type | Note |
|---|---|---|
| id | TEXT PK | 12-char `gen_id()` |
| email | TEXT UNIQUE NULLABLE | NULL = Google-only user |
| password_hash | TEXT NULLABLE | bcrypt cost=12, NULL = no password |
| name | TEXT | |
| google_sub | TEXT UNIQUE NULLABLE | OAuth subject (immutable, v8.1.0) |
| is_admin | BOOL | DB-level admin (v8.2.0) |
| manual_plan_override | TEXT NULLABLE | admin override (v8.2.0) |
| mcp_secret | TEXT UNIQUE | UUID for `/mcp/{secret}` route (v5.1) |
| plan | TEXT | "free"/"starter"/"admin" |
| subscription_status | TEXT | "starter_active"/"starter_past_due"/"free" |
| stripe_customer_id | TEXT NULLABLE | |
| storage_mode | TEXT | "managed"/"byos" (v7.0) |
| is_active | BOOL | Disable flag |
| created_at | TIMESTAMP | |

**Indexes:** `idx_users_google_sub`, `idx_users_email`

#### `files` (the workhorse — 30+ columns)
| Column | Type | Note |
|---|---|---|
| id | TEXT PK | |
| user_id | TEXT FK | |
| filename | TEXT | After ext4 truncation (v9.4.7: 255-byte limit) |
| filetype | TEXT | Lowercase extension |
| raw_path | TEXT | Disk path |
| extracted_text | TEXT | Plain text from extraction |
| processing_status | TEXT | `uploaded`/`queued`/`extracting`/`organized`/`ready`/`error` |
| extraction_status | TEXT | `ok`/`empty`/`encrypted`/`ocr_failed`/`unsupported`/`partial` (v7.5) |
| tags | TEXT JSON | Array |
| aliases | TEXT JSON | Array |
| sensitivity | TEXT | normal/sensitive/confidential |
| freshness | TEXT | current/stale/historical |
| source_of_truth | BOOL | User-promoted |
| version | INT | |
| is_locked | BOOL | Plan downgrade lock |
| locked_reason | TEXT | |
| drive_file_id | TEXT NULLABLE | BYOS link (v7.0) |
| storage_source | TEXT | local/drive_uploaded/drive_picked |
| content_hash | TEXT NULLABLE | SHA-256 (v7.1) |
| chunk_count | INT | (v7.5) |
| is_truncated | BOOL | (v7.5) |
| file_kind | TEXT | `processed`/`vault_only` (v9.1) |
| **Queue fields (v9.4.0):** | | |
| queued_at | TIMESTAMP | |
| extract_started_at | TIMESTAMP | |
| extract_completed_at | TIMESTAMP | |
| progress_step | TEXT NULLABLE | Worker writes (เช่น "OCR หน้า 5/20") |
| progress_pct | INT NULLABLE | 0-100, NULL = indeterminate |
| extract_error | TEXT NULLABLE | CODE (e.g. `ENCRYPTED`, `TIMEOUT`) |
| attempt_count | INT | Capped at MAX_RETRY=3 |
| uploaded_at | TIMESTAMP | |

**Indexes:**
- `idx_files_drive_file_id`
- `idx_files_content_hash`
- `idx_files_file_kind`
- `idx_files_queue_poll (processing_status, queued_at)` — critical for worker
- `idx_files_user_status (user_id, processing_status)`

#### `file_summaries`
| Column | Type | Note |
|---|---|---|
| id | INT PK AUTOINCREMENT | |
| file_id | TEXT FK UNIQUE | |
| md_path | TEXT | Path to `.md` file on disk |
| summary_text | TEXT | |
| key_topics | TEXT JSON | Array |
| key_facts | TEXT JSON | Array |
| why_important | TEXT | |
| suggested_usage | TEXT | |

#### `file_insights`
| Column | Type | Note |
|---|---|---|
| id | INT PK AUTOINCREMENT | |
| file_id | TEXT FK UNIQUE | |
| importance_score | INT | 0-100 |
| importance_label | TEXT | high/medium/low |
| is_primary_candidate | BOOL | |
| why_important | TEXT | |

#### `clusters` + `file_cluster_map`
- `clusters`: id, user_id, title, summary
- `file_cluster_map`: file_id, cluster_id, relevance_score (float) — N:N bridge

#### `context_packs`
| Column | Type | Note |
|---|---|---|
| id | TEXT PK | |
| user_id | TEXT FK | |
| type | TEXT | profile/study/work/project |
| title | TEXT | |
| summary_text | TEXT | |
| md_path | TEXT | |
| source_file_ids | TEXT JSON | |
| source_cluster_ids | TEXT JSON | |
| is_locked | BOOL | |
| intent | TEXT | (v9.2) |
| scope | TEXT | (v9.2) |
| created_via | TEXT | manual/ai_builder (v9.2) |

#### `pack_shares` (v9.3.0)
| Column | Type | Note |
|---|---|---|
| id | TEXT PK | |
| pack_id | TEXT FK | |
| owner_user_id | TEXT FK | |
| include_files | BOOL | |
| revoked_at | TIMESTAMP NULLABLE | |
| view_count | INT | |
| clone_count | INT | |

#### `context_memories` (v5.5)
ข้อมูล context cross-platform จาก chat sessions:
| Column | Type | Note |
|---|---|---|
| id | TEXT PK | |
| user_id | TEXT FK | |
| title | TEXT | Smart-merge key (2hr window) |
| content | TEXT | |
| summary | TEXT | Auto-generated |
| context_type | TEXT | |
| platform | TEXT | claude/chatgpt/antigravity |
| tags | TEXT JSON | |
| is_active | BOOL | Max 20/user |
| is_pinned | BOOL | Max 3/user |
| related_file_ids | TEXT JSON | |
| parent_id | TEXT FK NULLABLE | Self-reference |
| last_used_at | TIMESTAMP | |

#### `user_profiles`
| Column | Type | Note |
|---|---|---|
| id | INT PK AUTOINCREMENT | |
| user_id | TEXT FK UNIQUE | |
| identity_summary | TEXT | |
| goals | TEXT | |
| working_style | TEXT | |
| preferred_output_style | TEXT | |
| background_context | TEXT | |
| **Personality (v6.0):** | | |
| mbti_type | TEXT | INTJ/-A/-T |
| mbti_source | TEXT | official/neris/self_report |
| enneagram_data | TEXT JSON | `{core: 5, wing: 4}` |
| clifton_top5 | TEXT JSON | 34-theme array |
| via_top5 | TEXT JSON | 24-strength array |
| updated_at | TIMESTAMP | |

#### `personality_history` (append-only audit, v6.0)
- id, user_id, system (mbti/enneagram/clifton/via), data_json (snapshot), source (user_update/mcp_update), recorded_at
- Index: `idx_personality_history_user_system (user_id, system, recorded_at DESC)`

### §3.3 Knowledge Graph Tables (v3)

#### `note_objects`, `graph_nodes`, `graph_edges`, `suggested_relations`, `graph_lenses`

**`graph_nodes`:**
- id, user_id, object_type (source_file/note/entity/tag/context_pack/project/person/cluster), object_id (FK), label
- node_family, importance_score (0-1), freshness_score (0-1), pinned (bool), metadata_json

**`graph_edges`:**
- id, user_id, source_node_id, target_node_id, edge_type
- edge_type: `explicit_link`/`has_tag`/`mentions`/`derived_from`/`semantically_related`/`same_entity`/`used_together`/`contains`
- weight (0-1), confidence (0-1), provenance (system/user/llm), evidence_text

**`suggested_relations`** — LLM proposals awaiting user approval (status: pending/accepted/dismissed)

### §3.4 Integration Tables

#### `mcp_tokens`
- id, user_id, token_hash (SHA-256 unique), label, scope, is_active, created_at, last_used_at, revoked_at

#### `mcp_usage_logs`
- id, user_id, token_id, tool_name, request_summary, status, latency_ms, error_message, created_at

#### `drive_connections`
- id, user_id (UNIQUE), drive_email, refresh_token_encrypted (Fernet), drive_root_folder_id, last_sync_at, last_sync_status, last_sync_error, connected_at, revoked_at

#### `line_users`
- id, line_user_id (UNIQUE NULLABLE), pdb_user_id (UNIQUE FK), line_display_name, link_nonce (32-hex), link_nonce_expires_at, welcomed, rich_menu_id, linked_at, unlinked_at

#### `webhook_logs` (Stripe idempotency, v5.9.2)
- id, event_id (UNIQUE), event_type, stripe_object_id, status, error_message, processed_at

#### `usage_logs` + `audit_logs` (v5.9.3)
- usage_logs: user_id, action (ai_summary/export/refresh/pack_share), created_at — monthly quota reset
- audit_logs: user_id, event_type (plan_changed/usage_limit_reached/file_locked), old_value, new_value, triggered_by, created_at

#### `chat_queries` + `context_injection_logs`
- chat_queries: question, answer, selected_cluster_ids, selected_file_ids, retrieval_modes, reasoning
- context_injection_logs: chat_query_id (FK), profile_used, context_pack_ids, file_ids, cluster_ids, node_ids_used (v3 graph), edge_ids_used, injection_summary, retrieval_reason

### §3.5 Migration Pattern (CRITICAL — เพราะ prod DB อยู่ใน Fly volume)

**Idempotent migrations** — ทุก ALTER ต้อง guard ด้วย `PRAGMA table_info`:

```python
async def migrate_v9_4_0(db):
    cols = await db.execute("PRAGMA table_info(files)")
    existing = {c[1] for c in cols.fetchall()}
    
    if 'progress_step' not in existing:
        await db.execute("ALTER TABLE files ADD COLUMN progress_step TEXT")
    # ... repeat for each new column
    
    # Idempotent index
    await db.execute("CREATE INDEX IF NOT EXISTS idx_files_queue_poll ON files(processing_status, queued_at)")
```

**Safety rules** (locked):
- ❌ ห้าม DROP column (SQLite ไม่รองรับ atomic; ใช้ "deprecated" tag)
- ❌ ห้าม rename
- ✅ Add only
- ✅ Auto-backup ก่อน migration: `data/backups/projectkey_YYYYMMDD_HHMMSS.db` (keep 5 ล่าสุด)

---

## §4 Backend Module Map

โครงสร้าง `backend/` — **44 modules** (รวม `__init__.py`):

### §4.1 Foundation (อ่านลำดับนี้)

| Module | บทบาท | Key Public API |
|---|---|---|
| [config.py](../../backend/config.py) | Single source of truth สำหรับ env vars + constants | `JWT_SECRET_KEY`, `OPENROUTER_API_KEY`, `GEMINI_FILE_MODEL`, paths |
| [database.py](../../backend/database.py) | Async SQLite + schema + migrations | `init_db()`, `get_db()`, `gen_id()` |
| [auth.py](../../backend/auth.py) | JWT + bcrypt + password reset | `create_access_token()`, `get_current_user()`, `verify_password()` |
| [main.py](../../backend/main.py) | FastAPI app + 124 endpoint handlers (~4240 lines) | `app`, all route decorators |

### §4.2 Storage Layer

| Module | บทบาท |
|---|---|
| [storage_router.py](../../backend/storage_router.py) | Abstraction: managed (local) vs BYOS (Drive) — `fetch_file_bytes(file_id)` |
| [vault.py](../../backend/vault.py) | Raw File Vault (v9.1) — files searchable by name only |
| [markdown_store.py](../../backend/markdown_store.py) | Summary `.md` files on disk + Drive push |
| [signed_urls.py](../../backend/signed_urls.py) | JWT download tokens (v7.6, TTL 5-60min) |
| [shared_links.py](../../backend/shared_links.py) | Public file shares |
| [pack_share.py](../../backend/pack_share.py) | Public context pack shares (v9.3) |

### §4.3 File Processing Pipeline

| Module | บทบาท |
|---|---|
| [upload_worker.py](../../backend/upload_worker.py) | Async worker (v9.4.0) — atomic claim, heartbeat, recovery, progress callback |
| [extraction.py](../../backend/extraction.py) | Docling → PyPDF2 → Tesseract OCR + Thai cleanup |
| [ai_ingest.py](../../backend/ai_ingest.py) | Gemini Files API multimodal (audio/video/image) |
| [text_chunker.py](../../backend/text_chunker.py) | Chunk extracted text สำหรับ vector index |
| [duplicate_detector.py](../../backend/duplicate_detector.py) | Content hash dedup (currently `_DEDUP_DISABLED=True` since v9.3.2) |

### §4.4 AI / Knowledge Layer

| Module | บทบาท |
|---|---|
| [llm.py](../../backend/llm.py) | OpenRouter wrapper — `call_llm()` Flash, `call_llm_pro()` Pro, `call_llm_json()` JSON-mode |
| [retriever.py](../../backend/retriever.py) | 7-layer context retrieval สำหรับ chat |
| [organizer.py](../../backend/organizer.py) | Cluster + importance + summary generation |
| [ai_pack_builder.py](../../backend/ai_pack_builder.py) | AI Context Pack builder (v9.2) — `/clarify` → `/propose` → `/confirm` 2-step flow with in-memory `_SESSION_CACHE` + `_DRAFT_CACHE` |
| [graph_builder.py](../../backend/graph_builder.py) | Build knowledge graph from summaries |
| [relations.py](../../backend/relations.py) | Graph node/edge CRUD |
| [vector_search.py](../../backend/vector_search.py) | TF-IDF in-memory + ChromaDB foundation |
| [metadata.py](../../backend/metadata.py) | AI tag + sensitivity enrichment |
| [context_packs.py](../../backend/context_packs.py) | Pack CRUD (manual + accepts override_summary from ai_pack_builder) |
| [context_memory.py](../../backend/context_memory.py) | Cross-platform context (v5.5) + smart merge |
| [personality.py](../../backend/personality.py) | MBTI/Enneagram/Clifton/VIA + history audit |
| [profile.py](../../backend/profile.py) | User profile CRUD |

### §4.5 Integration Layer

| Module | บทบาท |
|---|---|
| [mcp_tools.py](../../backend/mcp_tools.py) | 22 MCP tool dispatcher + TOOL_REGISTRY |
| [mcp_tokens.py](../../backend/mcp_tokens.py) | `pk_` prefix tokens + SHA-256 hash storage |
| [billing.py](../../backend/billing.py) | Stripe Checkout + Webhook + Portal |
| [drive_oauth.py](../../backend/drive_oauth.py) | Drive OAuth flow + Fernet token encryption |
| [drive_storage.py](../../backend/drive_storage.py) | Drive client (read/write) |
| [drive_layout.py](../../backend/drive_layout.py) | Drive folder structure (raw/extracted/summaries/_meta/_backups) |
| [drive_sync.py](../../backend/drive_sync.py) | Bidirectional sync (push → pull) |
| [google_login.py](../../backend/google_login.py) | OAuth login (no refresh_token) — separate from drive_oauth |
| [line_bot.py](../../backend/line_bot.py) | LINE SDK wrapper |
| [bot_handlers.py](../../backend/bot_handlers.py) | Webhook event handlers |
| [bot_messages.py](../../backend/bot_messages.py) | TH/EN reply templates |
| [bot_adapters.py](../../backend/bot_adapters.py) | LINE → PDB user mapping |
| [line_quota.py](../../backend/line_quota.py) | LINE push API quota tracking |
| [email_service.py](../../backend/email_service.py) | Resend SDK wrapper (password reset, etc.) |

### §4.6 Plan & Admin Layer

| Module | บทบาท |
|---|---|
| [plan_limits.py](../../backend/plan_limits.py) | Tier definition + gate functions + lock_excess_data |
| [admin.py](../../backend/admin.py) | Admin endpoints (require_admin dependency) |

---

## §5 Upload Pipeline State Machine

### §5.1 State Diagram

```
┌──────────────────────────────────────────────────────────┐
│ POST /api/upload (multipart)                             │
│   1. Truncate filename → 255-byte ext4 limit (v9.4.7)    │
│   2. Save raw file → data/uploads/{user_id}/{file_id}    │
│   3. INSERT files row · status=queued · queued_at=now    │
│   4. Return {file_id, status, estimated_wait_sec} <200ms │
└──────────────────────────────────────────────────────────┘
                         │
                         ▼
                   status=queued
                         │
                         │  worker polls every 2s
                         │  atomic UPDATE WHERE status='queued'
                         ▼
                   status=extracting
                   extract_started_at=now
                         │
            ┌────────────┴────────────┐
            │ Routing by file ext     │
            ├── ai_ingest (audio/video/image) → Gemini Files API
            ├── extract_text          (pdf/docx/xlsx/txt) → Docling/PyPDF2/Tesseract
            └── vault                 (unknown) → file_kind='vault_only'
                         │
            Progress callback writes every ≤1.5s:
            progress_step + progress_pct (None if unknowable)
                         │
              ┌──────────┴──────────┐
              ▼                      ▼
       status=uploaded         status=error
       extracted_text=...      extract_error=CODE
       content_hash=sha256     attempt_count++
       progress_pct=100        (if <MAX_RETRY=3, user can retry)
       extract_completed_at
              │
              │ User triggers POST /api/organize
              ▼
       status=processing
              │
              ├── cluster (LLM)
              ├── summarize (LLM)
              ├── index vector
              └── build graph
              │
              ▼
       status=ready
```

### §5.2 Worker Design Pattern

**Single async task** ใน FastAPI startup (`asyncio.create_task`)

#### §5.2.1 Atomic Claim SQL

```python
# 1. Fetch candidates
rows = await db.execute(
    "SELECT * FROM files WHERE processing_status='queued' ORDER BY queued_at"
)

# 2. Rank in Python with round-robin fairness
ranked = sorted(candidates, key=lambda c: (
    per_user_position[c.user_id],   # round-robin
    priority_class(c.filetype),     # 1=fast, 2=doc, 3=multimodal
    c.queued_at                     # FIFO within tier
))

# 3. Atomic claim
result = await db.execute(
    """UPDATE files 
       SET processing_status='extracting', extract_started_at=:now
       WHERE id=:id AND processing_status='queued'""",
    {'id': ranked[0].id, 'now': datetime.utcnow()}
)
await db.commit()

if result.rowcount != 1:
    return None  # Lost race (defensive — single worker shouldn't race)
```

#### §5.2.2 Priority Classes ([upload_worker.py](../../backend/upload_worker.py))

| Class | Files | Rolling Avg Cap |
|---|---|---|
| 1 (fast) | txt, csv, code, small images | 5s |
| 2 (doc) | pdf, docx, xlsx, pptx | 60s |
| 3 (multimodal) | mp3, mp4, mov, large images via Gemini | 300s |

**Rolling average:** Exponential smoothing α=0.2, **cap per class** ป้องกัน outlier (เช่น 20-page OCR PDF = 1200s) pollute typical estimate

#### §5.2.3 Progress Callback Fix (v9.4.6 — Critical)

**Problem:** `extract_text()` รันใน `asyncio.to_thread()` thread pool ดังนั้น `asyncio.get_event_loop()` ใน thread = loop คนละตัวกับ main → progress DB write ไม่ commit

**Fix:**
```python
# Capture at worker startup
_main_loop = asyncio.get_running_loop()

# Sync callback (called from thread pool)
def _sync_report(step, pct=None):
    asyncio.run_coroutine_threadsafe(
        _write_progress(file_id, step, pct),
        _main_loop  # ← explicit reference
    )

# Throttle to 1.5s (avoid SQLite lock contention)
PROGRESS_DB_THROTTLE_SEC = 1.5
```

#### §5.2.4 Heartbeat Task (v9.4.5)

**Problem:** Class-3 job (video ~90s) ทำให้ main loop ค้างนาน → heartbeat file stale > 30s → `/healthz/queue` returns degraded → frontend แสดง "ระบบประมวลผลหยุด" ผิด

**Fix:** Heartbeat แยกเป็น `asyncio.create_task` ไม่อยู่ใน main loop, เขียน file ทุก 5s
```python
async def _heartbeat_loop():
    while not _shutdown_event.is_set():
        (DATA_DIR / "worker_heartbeat").write_text(str(time.time()))
        await asyncio.sleep(5)
```

#### §5.2.5 Recovery Sweep (Startup)

```python
async def _recover_stale_jobs():
    # Reset ALL extracting → queued (not just stale by timeout)
    # Reason: process crash = orphan, no way to know if job complete
    await db.execute(
        "UPDATE files SET processing_status='queued', extract_started_at=NULL "
        "WHERE processing_status='extracting'"
    )
```

### §5.3 Error Classification

| CODE | Trigger | User-facing (TH/EN) |
|---|---|---|
| `ENCRYPTED` | "password" in exception | "ไฟล์ติดรหัส" / "Encrypted file" |
| `FILE_MISSING` | FileNotFoundError | "ไฟล์หาย" / "File missing" |
| `TIMEOUT` | "timeout" keyword | "หมดเวลา" / "Timed out" |
| `OUT_OF_MEMORY` | MemoryError | "หน่วยความจำเต็ม" / "Out of memory" |
| `ENCODING` | UnicodeError | "อักขระเสีย" / "Encoding error" |
| `QUOTA_EXCEEDED` | "quota"/"429" | "เกินโควต้า" / "Quota exceeded" |
| `GEMINI_UNAVAILABLE` | "google" + "503" | "Gemini ขัดข้อง" |
| `MODEL_DEPRECATED` | "404" + "not_found" | "โมเดลถูกยกเลิก" |
| `FILE_NOT_ACTIVE` | "failed_precondition" | "ไฟล์ยังประมวลผลไม่เสร็จ" |
| `PERMISSION_DENIED` | "permission_denied" | "ไม่มีสิทธิ์" |
| `OCR_FAIL` | "tesseract" | "OCR ผิดพลาด" |
| `NETWORK` | "connection"/"network" | "เน็ตขัดข้อง" |
| `UNKNOWN` | default | "ขัดข้อง — ลองใหม่" |

**i18n boundary (v9.4.4):** Backend returns CODE strings ไม่ใช่ Thai text. Frontend แปลตาม `localStorage.pdb_lang`

### §5.4 AI Ingest Routing

| Extension | Handler | Model | Output |
|---|---|---|---|
| mp3, wav, m4a, flac, aac, ogg, opus, wma | `ingest_audio()` | Gemini 2.5 Flash (Files API) | Transcribe + speaker labels + [HH:MM:SS] |
| mp4, mov, mkv, webm, avi, wmv, flv, m4v, 3gp | `ingest_video()` | Gemini 2.5 Flash | Scenes (30s) + speech + on-screen text |
| jpg, jpeg, png, webp, heic, heif, gif, bmp, tiff | `ingest_image_smart()` | Gemini 2.5 Flash Vision | Describe + extract text (Thai/EN native) |
| pdf | `extract_text()` (Docling → PyPDF2 → Tesseract) | local | Plain text |
| docx, xlsx, pptx | `extract_text()` (python-docx/openpyxl/python-pptx) | local | Plain text |
| txt, csv, md, code | UTF-8 read with encoding fallback | local | Plain text |

**Critical: `_wait_for_file_active()`** — Gemini Files API ต้องรอ `state == ACTIVE` ก่อนเรียก generate_content (max 300s polling) มิฉะนั้น video → 400 FAILED_PRECONDITION

**Strip surrogates** (v9.3.3): หลัง extract ต้อง `strip_surrogates(text)` ก่อนเขียน DB เพื่อกัน UnicodeEncodeError จาก lone UTF-16 surrogates ใน PDF font edge cases

---

## §6 AI & Knowledge Layer

### §6.1 LLM Provider Strategy

**Two-model setup:**
- **LLM_MODEL** = `google/gemini-3-flash-preview` (lightweight: chat, retrieval, JSON parse)
- **LLM_MODEL_PRO** = `google/gemini-3-flash-preview` (heavy: organize, summarize — currently same as Flash for cost/quality tuning)
- **GEMINI_FILE_MODEL** = `gemini-2.5-flash` (direct google-genai SDK สำหรับ multimodal Files API — OpenRouter ไม่ support Files API ดีพอ)

**OpenRouter routing:** `provider: {"order": ["Google"], "allow_fallbacks": true}` → ดึง Gemini จาก Google + partner edges

**JSON parsing (`call_llm_json`):** Try direct parse → fallback strip ```` ```json ```` fence → fallback regex extract `{}`/`[]`

### §6.2 7-Layer Context Retrieval (Chat)

```
POST /api/chat {question}
            │
            ▼
   [Retriever v3 graph-aware]
            │
   1. User Profile          (is_profile_complete check)
            │
   2. Context Packs          (LLM selects from inventory)
            │
   3. Files (Summary)        ↘
   4. Files (Excerpt)         } per-file LLM decides mode
   5. Files (Raw)            ↗ (raw = first 6000 chars)
            │
   6. Graph Nodes & Edges    (traverse from files used, max 5 edges/file)
            │
   7. Hybrid Vector Search   (TF-IDF + semantic, top 5)
            │
            ▼
   MAX_CONTEXT_CHARS = 12000 (hard budget)
            │
            ▼
   LLM generate answer + return sources
```

**Per-file mode logic** ([retriever.py](../../backend/retriever.py)): LLM ดู file inventory + vector hit แล้ว return `{file_id, mode}` ใน JSON → injection logic ใช้ summary/excerpt/raw ตาม mode

**Graph injection** (v3): หลังเลือก files แล้ว ดึง outgoing/incoming edges (max 5/file) → build `edges_used`, `nodes_used`, `evidence_text` → ส่งให้ LLM พร้อม context

### §6.3 Organize Pipeline ([organizer.py](../../backend/organizer.py))

```
1. _cluster_files()
   - LLM call: inventory of files + tags → JSON clusters with file assignments + relevance scores
   - Vault files (file_kind=vault_only) excluded
   - Files with extraction_status != 'ok' excluded (v9.4.2)

2. _find_importance()
   - LLM call: file → importance_score (0-100) + label + is_primary_candidate

3. _generate_summary()
   - LLM call: file text + cluster title → summary + key_topics + key_facts + why_important + suggested_usage

4. Write outputs:
   - FileInsight, FileSummary, FileClusterMap
   - vector_search.index_file()
   - markdown_store.write_summary_md() (path stored in FileSummary.md_path)
   - BYOS push (if user.storage_mode='byos')

5. Build graph (graph_builder.py):
   - Extract entities + relationships from summaries
   - Create graph_nodes + graph_edges
   - Compute importance_score + freshness_score
```

### §6.4 Knowledge Graph Design

**Node families** (color coding ใน UI):
| Family | Color | Examples |
|---|---|---|
| source_file | gold `#ffd54f` | Uploaded files |
| entity | orange `#ff8a65` | People/orgs/concepts |
| tag | cyan `#4fc3f7` | User tags |
| project | green `#81c784` | Project groupings |
| pack | teal `#4dd0e1` | Context packs |
| person | purple `#b39ddb` | Named individuals |
| note | light green `#aed581` | User notes |

**Edge types:**
- `explicit_link` (user-created), `has_tag`, `mentions`, `derived_from`, `semantically_related`, `same_entity`, `used_together`, `contains`

**Frontend rendering:** D3.js v7 force-directed simulation, `state.simulation` instance, filter by `state.filters[family]`

---

## §7 REST API Surface

### §7.1 Overview

- **124 endpoint declarations** ใน [backend/main.py](../../backend/main.py)
- **Auth pattern:** ส่วนใหญ่ใช้ `Depends(get_current_user)` (JWT Bearer)
- **Public exceptions:** register, login, password reset, personality reference, shared links, Stripe webhook, LINE webhook, MCP secret route
- **Frontend wrapper:** [authFetch()](../../legacy-frontend/app.js) — adds Bearer header, 401 → doLogout

### §7.2 Auth & Identity (7 endpoints)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/api/auth/register` | none | `{email, password}` → `{access_token, user}` |
| POST | `/api/auth/login` | none | `{email, password}` → `{access_token}` |
| GET | `/api/auth/me` | JWT | Current user |
| POST | `/api/auth/request-reset` | none | `{email}` — uniform response (anti-enumeration) |
| POST | `/api/auth/reset-password` | none | `{token, password}` |
| GET | `/api/auth/google/init` | none | → `{auth_url, state, code_verifier}` |
| GET | `/api/auth/google/callback` | CSRF state | → 302 to `/app?google_linked=true` |

### §7.3 Files (15 endpoints)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/upload` | Multipart upload → queue |
| GET | `/api/upload-status` | Poll: `?file_ids=...` → progress per file |
| POST | `/api/upload/{id}/retry` | Re-queue failed |
| POST | `/api/upload/{id}/dismiss-error` | Clear error |
| POST | `/api/upload/{id}/cancel` | Cancel queued/extracting (v9.4.5) |
| GET | `/api/healthz/queue` | `{queued_count, processing, worker_alive}` |
| GET | `/api/unprocessed-count` | |
| POST | `/api/files/{id}/reprocess` | `?mode=cleanup\|reextract` |
| DELETE | `/api/files/{id}` | Cascade: disk + DB + vector + Drive + summaries (v9.4.8 blocks if extracting) |
| POST | `/api/files/{id}/promote` | source_of_truth=true |
| POST | `/api/files/skip-duplicates` | Bulk dismiss |
| GET | `/api/files` | List with pagination |
| GET | `/api/files/{id}/content` | `?offset, limit` paginated text |
| GET | `/api/files/{id}/download` | Streams raw_path |
| POST | `/api/files/{id}/share` | → `{token, share_url}` |

### §7.4 Summaries & Metadata (5 endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/summary/{id}` | summary_text + key_topics + key_facts |
| PUT | `/api/summary/{id}` | Update fields |
| GET | `/api/metadata/{id}` | tags + sensitivity + freshness |
| PUT | `/api/metadata/{id}` | Update |
| POST | `/api/metadata/enrich` | LLM batch enrichment |

### §7.5 AI Organization (5 endpoints)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/organize` | Background: cluster + summarize + graph |
| POST | `/api/organize-new` | v7.1+ with dup detection |
| GET | `/api/clusters` | Paginated |
| PUT | `/api/clusters/{id}` | Rename |
| POST | `/api/graph/build` | Rebuild graph |

### §7.6 Knowledge Graph (8 endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/graph/global` | D3 data: `{nodes, edges, families}` |
| GET | `/api/graph/nodes` | `?family=X` filtered |
| GET | `/api/graph/nodes/{id}` | Node detail |
| GET | `/api/graph/neighborhood/{id}` | `?depth=1-3` |
| GET | `/api/graph/edges` | `?edge_type=X` |
| GET | `/api/relations/backlinks/{node_id}` | Incoming |
| GET | `/api/relations/outgoing/{node_id}` | Outgoing |
| GET | `/api/suggestions` | LLM-proposed pending |

### §7.7 Context Packs (11 endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/context-packs` | List |
| POST | `/api/context-packs` | Create (require file_ids OR cluster_ids, v9.0.1) |
| GET | `/api/context-packs/{id}` | Detail |
| DELETE | `/api/context-packs/{id}` | |
| POST | `/api/context-packs/{id}/regenerate` | Rebuild summary |
| POST | `/api/context-packs/{id}/share` | `{expires_in}` |
| PATCH | `/api/context-packs/shares/{share_id}` | Update share |
| DELETE | `/api/context-packs/shares/{share_id}` | Revoke |
| GET | `/api/context-packs/{id}/shares` | List shares |
| POST | `/api/context-packs/ai-build/clarify` | AI builder Q1 |
| POST | `/api/context-packs/ai-build/propose` | AI builder Q2 |

### §7.8 Context Memory (5 endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/contexts` | `?limit=10` |
| POST | `/api/contexts` | Smart-merge if title exists < 2h |
| PUT | `/api/contexts/{id}` | Max 3 pinned |
| DELETE | `/api/contexts/{id}` | |
| GET | `/api/contexts/{id}` | |

### §7.9 Public/Unauthenticated (7 endpoints)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/api/shared/{token}` | Share token in URL | View shared file |
| GET | `/d/{token}` | Signed JWT | Download file (stateless verify) |
| GET | `/api/shared/pack/{token}` | Pack share token | View pack |
| POST | `/api/shared/pack/{token}/claim` | Pack share token | Clone to own KB |
| GET | `/p/{token}` | Pack share token | 302 to `/app?pack_share_token=X` |
| GET | `/api/personality/reference` | none | MBTI/Enneagram public reference data |
| POST | `/api/stripe/webhook` | Stripe signature | Webhook (idempotent by event_id) |

### §7.10 Profile & Personality (4 endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/profile` | identity_summary + goals + personality |
| PUT | `/api/profile` | Update fields |
| GET | `/api/profile/personality/history` | Audit log |
| GET | `/api/personality/reference` | Public 4-system reference |

### §7.11 LINE Bot (9 endpoints)

| Method | Path | Auth | Purpose |
|---|---|---|---|
| POST | `/webhook/line` | HMAC SHA256 | Incoming events |
| GET | `/api/line/status` | JWT | Connection state |
| POST | `/api/line/connect` | JWT | Init account link |
| POST | `/api/line/disconnect` | JWT | Unlink |
| GET | `/auth/line` | link nonce + linkToken | Account link confirm page |
| POST | `/api/line/confirm-link` | link nonce | Finalize |
| GET | `/api/line/admin/quota` | Admin | LINE push quota |
| POST | `/api/chat` | JWT | Chat (used by bot too) |

**LINE Flow:**
1. User taps "Link Account" in rich menu
2. Bot replies flex card → `https://access.line.me/dialog/bot/accountLink?linkToken=X&nonce=Y`
3. User grants → LINE POST `/webhook/line` with `accountLink` event
4. Handler verifies `LineUser.link_nonce` (32-hex, expires 10min)
5. Redirect to `/auth/line?linkToken=X` → user clicks confirm → POST `/api/line/confirm-link`

**LINE constraint:** Nonce ต้องเป็น alphanumeric เท่านั้น 10-255 chars → ใช้ `secrets.token_hex(32)` (64 hex chars [0-9a-f]) **ไม่ใช่ base64url** (LINE reject `-`/`_`)

### §7.12 Stripe Billing (5 endpoints)

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/billing/create-checkout-session` | `{plan: "starter"}` → checkout_url |
| POST | `/api/billing/create-portal-session` | → portal_url |
| POST | `/api/stripe/webhook` | Signature verify + idempotency |
| GET | `/api/billing/info` | subscription_status + renewal_date |
| GET | `/billing/success` | 302 to `/app?billing=success` |

**Webhook events:**
- `checkout.session.completed` → flip subscription_status="starter_active"
- `customer.subscription.updated` → update status + renewal
- `customer.subscription.deleted` → downgrade to "free" + lock excess data
- `invoice.payment_succeeded` → audit log

### §7.13 Drive BYOS (5 endpoints)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/drive/status` | `{connected, drive_email, storage_mode, last_sync_status}` |
| GET | `/api/drive/oauth/init` | → auth_url |
| GET | `/api/drive/oauth/callback` | CSRF state verify → 302 to `/app?drive_connected=true\|false` |
| POST | `/api/drive/disconnect` | `{keep_files?: bool}` |
| POST | `/api/drive/sync` | Manual trigger → `{stats: {pushed, pulled, conflicts, errors, duration_ms}}` |

### §7.14 Admin (13 endpoints)

ทุก endpoint ใช้ `Depends(require_admin)`:
- `/api/admin/me`, `/api/admin/stats`, `/api/admin/users`, `/api/admin/users/{id}`
- `PUT /api/admin/users/{id}/plan`, `POST /api/admin/users/{id}/reset-password`
- `PUT /api/admin/users/{id}/active`, `PUT /api/admin/users/{id}/admin`
- `/api/admin/audit-logs`
- `/api/stats` (user's own), `/api/usage`, `/api/plan-limits`
- `DELETE /api/reset` (nuke all user data)

---

## §8 MCP Integration

### §8.1 Two Transports

#### A. Streamable HTTP — `/mcp/{secret}` (Primary)

**Pattern:** Per-user secret in URL (UUID stored in `users.mcp_secret`)

**Why this pattern:** Claude Custom Connector ไม่ parse Authorization header ใน URL request ได้ — ต้องใส่ secret เป็นส่วนของ path

**Protocol:** JSON-RPC 2.0
```json
POST /mcp/{secret}
Content-Type: application/json

{"jsonrpc":"2.0","id":1,"method":"tools/list"}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"get_overview","arguments":{}}}
```

**Methods:**
- `initialize` → `{protocolVersion, capabilities, serverInfo: {name, version}}`
- `tools/list` → array of tool schemas
- `tools/call` → returns MCP content array
- `ping` → heartbeat

#### B. REST API — `/api/mcp/*` (Secondary, for tokens)

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/mcp/info` | Per-user MCP URLs |
| POST | `/api/mcp/tokens` | Generate `pk_*` token (returns once, never shown again) |
| GET | `/api/mcp/tokens` | List (without raw tokens) |
| DELETE | `/api/mcp/tokens/{id}` | Revoke |
| POST | `/api/mcp/test` | Test Bearer auth |
| POST | `/api/mcp/tools/call` | Direct REST tool call |
| GET | `/api/mcp/logs` | Usage logs |
| GET/PUT | `/api/mcp/permissions` | Per-tool toggle |

**Token format:**
- Prefix: `pk_` + 48 hex chars (e.g. `pk_abc123def456...`)
- Storage: SHA-256 hash in `mcp_tokens.token_hash`
- Header: `Authorization: Bearer pk_...`

### §8.2 MCP Tools (22 in TOOL_REGISTRY + 5 context_memory in dispatcher = 27 total)

**Caveat:** [mcp_tools.py](../../backend/mcp_tools.py) docstring เคยเขียน "30 tools" แต่ของจริง = 22 ใน `TOOL_REGISTRY` (เห็นใน `tools/list`) + 5 context_memory tools dispatched แต่ไม่ register (`save_context`, `load_context`, `list_contexts`, `update_context`, `auto_context`) = 27 callable tools



#### Read Tools (12)
| Tool | Purpose |
|---|---|
| `get_profile` | Includes `active_contexts` (latest + pinned) — zero-effort UX |
| `list_files` | Paginated file list |
| `get_file_content` | Paginated text (max 10KB chunk) |
| `get_file_link` | Signed JWT URL, TTL 5-60min |
| `get_file_summary` | summary + topics + facts |
| `list_collections` | AI clusters |
| `list_context_packs` | |
| `get_context_pack` | |
| `search_knowledge` | Hybrid (vector + TF-IDF + graph) |
| `explore_graph` | Overview or neighborhood (depth=1) |
| `get_overview` | System stats |
| `export_file_to_chat` | Returns `__mcp_content` array (EmbeddedResource base64) — fallback to signed URL if >10MB |

#### Edit Tools (5)
| Tool | Purpose |
|---|---|
| `create_context_pack` | Require ≥1 of file_ids/cluster_ids (v9.0.1) |
| `add_note` | Auto-creates FileSummary |
| `update_file_tags` | Replaces tags |
| `upload_text` | Creates `.md`/`.txt` |
| `update_profile` | All fields optional, source="mcp_update" |

#### Delete Tools (2)
| Tool | Purpose |
|---|---|
| `delete_file` | Cascade sync (not background); storage_source guard |
| `delete_context_pack` | |

#### Pipeline Tools (5)
| Tool | Purpose |
|---|---|
| `run_organize` | Full pipeline |
| `build_graph` | Rebuild |
| `enrich_metadata` | LLM batch tag + sensitivity |
| `reprocess_file` | OCR fallback + Thai cleanup |
| `admin_login` | `{admin_key}` → unlock disabled tools |

#### Context Memory Tools (5) — dispatcher only, not in TOOL_REGISTRY
- `save_context`, `load_context`, `list_contexts`, `update_context`, `auto_context`

### §8.3 Special Response: `__mcp_content`

Tool functions ปกติ return JSON ที่ทำ stringify ลง `content[0].text` แต่บางตัว (เช่น `export_file_to_chat`) ต้อง return EmbeddedResource (base64 blob)

**Pattern:**
```python
def export_file_to_chat(file_id):
    if file_size > 10MB:
        url = sign_download_token(file_id, user_id)
        return {"signed_url": url, "size": file_size}  # normal path
    return {
        "__mcp_content": [
            {"type": "resource", "resource": {
                "uri": f"file://{filename}",
                "mimeType": mime,
                "blob": base64.b64encode(bytes).decode()
            }},
            {"type": "text", "text": json.dumps({"filename": filename})}
        ]
    }
```

[main.py](../../backend/main.py) MCP handler ตรวจ key `__mcp_content` แล้ว pass through ตรงๆ ไม่ stringify

### §8.4 Permissions System

`MCP_PERMISSIONS[user_id][tool_name] = bool` (in-memory dict, persisted to DB)
- User toggle ผ่าน `PUT /api/mcp/permissions`
- Disabled tool + no `admin_key` → return error inside MCP result (ไม่ใช่ HTTP error)
- Admin gates บน destructive tools (delete_file, unlink_nodes) ต้องการ ADMIN_PASSWORD env validation

### §8.5 Usage Logging

ทุก tool call → INSERT `mcp_usage_logs`:
- tool_name, request_summary (truncated), latency_ms, status, error_message

---

## §9 BYOS — Google Drive Sync

### §9.1 Architecture

**Drive = source of truth** (storage_mode='byos'). Server SQLite = cache + index (rebuildable)

```
┌────────────────────────────────────────────┐
│ User's Google Drive                         │
│ /Personal Data Bank/                        │
│   ├── raw/         original files          │
│   ├── extracted/   plain text              │
│   ├── summaries/   AI markdown             │
│   ├── personal/    profile.json + contexts │
│   ├── data/        clusters/graph/history  │
│   ├── _meta/       schema version + manifest│
│   └── _backups/    weekly snapshots        │
└────────────────────────────────────────────┘
            ↕ sync (poll 5min + on-write)
┌────────────────────────────────────────────┐
│ PDB Server (Cache)                          │
│ SQLite minimal cache:                       │
│  • user + OAuth refresh_token (Fernet enc) │
│  • storage_mode = "managed" \| "byos"      │
│  • drive_connection (email, last_sync_at)  │
│  • files index (file_id ↔ drive_file_id)   │
│  • vector embeddings (rebuildable)         │
└────────────────────────────────────────────┘
```

### §9.2 OAuth Flow

**Differences from `google_login.py`:**

| Aspect | google_login | drive_oauth |
|---|---|---|
| Scopes | openid + email + profile | drive.file + offline_access |
| refresh_token | NOT stored | Stored encrypted |
| State | CSRF only | Bound to user_id |
| Encryption | N/A | Fernet AES-128 + HMAC |

**Token storage:**
- Key: `DRIVE_TOKEN_ENCRYPTION_KEY` env (Fernet.generate_key())
- Stored: `drive_connections.refresh_token_encrypted`
- Decrypt on demand → exchange for access_token

**OAuth mode:** `GOOGLE_OAUTH_MODE = "testing"` → 7-day refresh token expiry → users hit `invalid_grant` weekly. Solution: submit Google verification for "production" mode (permanent tokens).

### §9.3 Sync Algorithm

**`run_full_sync()` → SyncStats:**

```python
1. PUSH: local → Drive
   - Fetch all files where storage_source='local' + drive_file_id IS NULL
   - F24 duplicate prevention (v9.3.5.5): pre-fetch Drive listing
     → if file with same name+hash exists → relink (update drive_file_id) instead of duplicate
   - Upload to Drive, save drive_file_id

2. PULL: Drive → local
   - List Drive files in PDB folder
   - For each:
     - If file_id NOT in local DB → import (file_kind='vault_only' until processed)
     - If file_id IN local AND drive_modified > cache_modified → re-download
     - If file_id IN local but Drive entry deleted → soft-delete cache

3. CONFLICT RESOLUTION:
   - Drive modifiedTime wins (last-write-wins)
   - Orphan cleanup: max 3 retries per file per session (_orphan_retry_count dict)

4. Returns stats: {pulled_new, pulled_updated, pulled_deleted, pushed_new, 
                  pushed_updated, relinked, orphans_cleaned, orphans_skipped_budget,
                  duplicate_push_prevented, conflicts_resolved, errors, duration_ms}
```

### §9.4 Error Handling

**`invalid_grant` (token revoked/expired):**
- `_mark_drive_connection_errored()` flips `last_sync_status='error'` + `last_sync_error='INVALID_GRANT'`
- Frontend banner: "เชื่อมต่อ Google Drive หาย — กดเพื่อ reconnect"
- Wraps `ensure_pdb_folder_structure()` ใน try-except เพื่อ catch ตั้งแต่ load (v9.3.5)

**Known issue:** 64 stuck rows ใน prod DB จาก `drive_sync._import_drive_file()` ตั้ง `processing_status='uploaded'` แต่ worker pickup เฉพาะ `'queued'` → ต้องเลือก strategy A/B/C ([§14.3](#143-known-issues))

---

## §10 Auth, Identity & Plan Limits

### §10.1 JWT Auth

**Token shape:**
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "name": "Display Name",
  "exp": 1234567890,
  "iat": 1234567890
}
```

- Algorithm: HS256
- Secret: `JWT_SECRET_KEY` env (or `.jwt_secret` file fallback)
- Expiry: `JWT_EXPIRE_MINUTES = 1440` (24h)
- Bcrypt cost: default (12, ~100ms hash/verify)

**Frontend usage:**
- Stored: `localStorage.pdb_token`
- Header: `Authorization: Bearer <jwt>`
- On 401 + `_isInitVerified=true` → doLogout()

**Google-only users:**
- `password_hash = NULL`
- Login attempt → return 401 with code `USE_GOOGLE_LOGIN`
- Frontend redirects to Google button

**Password reset:**
- 15-minute token + Resend email
- Uniform response (anti-enumeration: ไม่บอกว่า email มีในระบบไหม)

### §10.2 Google OAuth (Login)

**Flow:**
1. `GET /api/auth/google/init` → return `{auth_url, state, code_verifier}`
2. Frontend redirect to Google with `state` + `code_challenge` (PKCE S256)
3. Google → callback with `code + state`
4. Backend verify state (check `_GLOGIN_STATE_CACHE` + TTL, separate from Drive state cache)
5. Exchange code → ID token (PKCE verified locally with clock_skew=60s for Windows drift)
6. Extract `{google_sub, email, email_verified, name}`
7. Lookup user: google_sub > email > create new

### §10.3 Plan Limits

#### Tier definitions ([plan_limits.py](../../backend/plan_limits.py))

```python
TIERS = {
    "free": {
        "context_pack_limit": 10,
        "file_limit": 50,
        "storage_limit_mb": 500,
        "max_file_size_mb": 100,
        "ai_summary_limit_monthly": 50,
        "export_limit_monthly": 100,
        "refresh_limit_monthly": 0,  # blocked entirely
        "pack_share_limit_monthly": 5,
        "upload_queue_cap": 10,
        "semantic_search_enabled": False,
    },
    "starter": {  # ×10 baseline (locked by ADR-008)
        "context_pack_limit": 50,
        "file_limit": 500,
        "storage_limit_mb": 10_240,  # 10 GB
        "max_file_size_mb": 200,
        "ai_summary_limit_monthly": 1000,
        # ... ×10 all
        "upload_queue_cap": 50,
        "semantic_search_enabled": True,
    },
    "admin": {
        # 999999 except upload_queue_cap=200 (DoS guard)
    },
}
```

#### Effective Plan Logic

```python
def _effective_plan(user):
    if user.is_admin: return "admin"          # DB-level (v8.2.0)
    if user.email in ADMIN_EMAILS: return "admin"  # env break-glass
    if user.subscription_status in ("starter_active", "starter_past_due", "starter_canceled"):
        return "starter"  # grace period included
    return "free"
```

#### Gate Functions (pre-check before action)

| Function | Returns |
|---|---|
| `check_upload_allowed()` | file type + size + count + storage |
| `check_pack_create_allowed()` | count limit |
| `check_summary_allowed()` | monthly (resets on billing period) |
| `check_export_allowed()` | monthly |
| `check_pack_share_create_allowed()` | monthly (revoked count) |
| `check_refresh_allowed()` | 0 for Free → blocked entirely |
| `check_semantic_search_allowed()` | feature flag |

**Return:** `None` (allowed) | `{"error": "MSG", "upgrade": bool}`

**Failure response:** HTTPException 402 (Payment Required) + prompt upgrade

#### Locked Data (Plan Downgrade)

- Downgrade → `lock_excess_data()` marks oldest items `is_locked=True`
- Data NEVER deleted
- Locked items: skipped in read queries (`WHERE is_locked=False`) + write blocked
- Upgrade → `unlock_data_for_plan()` reverses based on new limit

---

## §11 Frontend Architecture

### §11.1 File Structure

```
legacy-frontend/
├── landing.html       523 lines    Public marketing + auth modal
├── landing.css        739 lines    Landing-only styles
├── landing.js         621 lines    Auth flow + showLanding/showApp
├── app.html         1,528 lines    Auth shell + 8 page sections
├── app.js           5,957 lines    Page system + UploadTray + i18n + all logic
├── styles.css       5,321 lines    App-only styles + Phase B cascade
├── shared.css         718 lines    ⭐ Foundation — tokens + canonical atoms
├── shared_pack.html   pack share view (public)
├── shared_pack.css    pack share styles
├── shared_pack.js     pack share script
├── pricing.html       static pricing page
├── admin.html/admin.js admin panel
├── auth-line.html/auth-line.js  LINE account link confirm page
├── line_ui.js         LINE status UI module (loaded in app.html)
└── storage_mode.js    BYOS toggle UI module
```

### §11.2 Page System (No-Hash Routing)

```javascript
function switchPage(page) {
    state.currentPage = page;
    document.querySelectorAll('.nav-item[data-page]').forEach(el => el.classList.remove('active'));
    document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
    document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
    document.getElementById(`page-${page}`)?.classList.add('active');
    
    // Lazy load per page
    if (page === 'knowledge') loadKnowledge();
    if (page === 'graph') loadGraph();
    if (page === 'chat') loadChat();
    // ...
}
```

**8 page IDs:** my-data, knowledge, graph, chat, context-memory, mcp-setup, tokens, mcp-logs

**CSS:** `.page { display: none } .page.active { display: block; animation: fadeIn 0.2s ease }`

**Profile = slide-in panel ไม่ใช่ .page** (`.slide-panel.slide-panel-sm`)

### §11.3 Global State

```javascript
// app.js declares with `var` so landing.js can read
var state = {
    currentPage: 'my-data',
    graphMode: 'global',           // global | local
    localNodeId: null,
    graphData: { nodes: [], edges: [] },
    simulation: null,               // d3-force instance
    selectedNodeId: null,
    filters: {                      // node visibility
        source_file: true, entity: true, tag: true,
        project: true, context_pack: true, person: true,
    },
    knowledgeTab: 'collections',
    mcpInfo: null,
    authToken: localStorage.getItem('pdb_token') || null,
    currentUser: JSON.parse(localStorage.getItem('pdb_user') || 'null'),
};

// Auth state machine flags
var _logoutDebounce = false;
var _isInitVerified = false;
```

**localStorage keys (pdb_ prefix, migrated from projectkey_ at v7.1):**
- `pdb_token` — JWT
- `pdb_user` — JSON object
- `pdb_lang` — 'th' | 'en'
- `pdb_rebrand_notice_seen` — one-time toast
- `pdb_admin_probe_ts` — sessionStorage TTL

### §11.4 authFetch Pattern

```javascript
async function authFetch(url, options = {}) {
    if (!options.headers) options.headers = {};
    if (state.authToken) {
        options.headers['Authorization'] = `Bearer ${state.authToken}`;
    }
    const isBackground = options._background === true;  // non-logout on 401
    delete options._background;
    
    let res;
    try {
        res = await fetch(url, options);
    } catch (err) {
        if (!isBackground) showToast('Cannot connect to server', 'error');
        throw err;
    }
    
    if (res.status === 401 && _isInitVerified) {
        if (!_logoutDebounce && state.authToken && !isBackground) {
            _logoutDebounce = true;
            doLogout();
            showToast('Session expired', 'error');
            setTimeout(() => { _logoutDebounce = false; }, 5000);
        }
        if (!isBackground) throw new Error('Session expired');
    }
    return res;
}
```

**Critical flags:**
- `_isInitVerified` — true after first `/api/auth/me` succeeds (set in landing.js)
- `_background: true` — prevents logout (สำหรับ startup grace period)
- `_logoutDebounce` — 5s window prevents duplicate logout toasts

### §11.5 i18n (Bilingual TH/EN)

```javascript
const I18N = {
    th: {
        'nav.myData': 'ข้อมูลของฉัน',
        'upload.tray.position': 'อันดับ {n}',
        // ... 500+ keys
    },
    en: { /* parallel */ }
};

function t(key, vars) {
    const lang = getLang();  // localStorage.pdb_lang || 'th'
    const tr = I18N[lang]?.[key] || I18N['en']?.[key] || key;
    if (!vars) return tr;
    return tr.replace(/\{(\w+)\}/g, (_, k) => vars[k] != null ? vars[k] : `{${k}}`);
}

function applyLanguage(lang) {
    document.querySelectorAll('[data-i18n]').forEach(el => {
        el.textContent = t(el.dataset.i18n);
    });
    // Update placeholders, re-render dynamic content
    localStorage.pdb_lang = lang;
    document.documentElement.lang = lang;
}
```

**Usage in HTML:**
```html
<h1 data-i18n="myData.title">My Data</h1>
```

**localizeBackendStep (v9.4.4):** Backend ส่ง CODE หรือ Thai step ([upload_worker.format_user_error](../../backend/upload_worker.py)) → frontend แปลด้วย regex pattern (14 patterns):
```javascript
/^OCR หน้า (\d+)\/(\d+)$/ → `OCR page {n}/{total}`
/^Gemini เตรียมไฟล์ \(([A-Z_]+), (\d+)s\)$/ → `Gemini preparing ({code}, {sec}s)`
```

### §11.6 UploadTray Module (Critical UX)

**Pattern: IIFE module exposed as `window.UploadTray`**

```javascript
const UploadTray = (() => {
    let _pollHandle = null;
    let _pollAttempts = 0;
    let _isOpen = false;
    let _lastSnapshot = { active: [], failed: [], summary: {} };
    const _expandedIds = new Set();
    
    const POLL_INTERVAL_MS = 2000;       // initial 2s
    const POLL_BACKOFF_MS = 5000;        // after 30 ticks (1min)
    const POLL_BACKOFF_AFTER = 30;
    
    function open() { /* ... */ }
    function close() { /* ... */ }
    function openIfHasItems() { /* poll /api/upload-status */ }
    function notifyEnqueued(uploaded) { /* optimistic */ }
    
    return { open, close, openIfHasItems, notifyEnqueued };
})();
window.UploadTray = UploadTray;
```

**States per item:**
- `queued` (warning pill)
- `extracting` (active pill + progress bar)
- `error` (error pill + retry/dismiss buttons)
- `done` (auto-removed after 2s)

**Truthfulness Contract (TC-1..6) in UI:**
- TC-1: No fake %  → indeterminate meter if `progress_pct_known === false`
- TC-2: Real timestamps (queued_at, extract_started_at, extract_completed_at)
- TC-3: why_slow text from backend (รูปแบบ "OCR หน้า 5/20 ใช้เวลาเฉลี่ย ~60s/page")
- TC-4: estimated_wait_sec จาก rolling avg
- TC-5: Error CODE → user-friendly TH/EN
- TC-6: System status banner (degraded/stopped)

### §11.7 Auth State Machine

```
Page load
   │
   ▼
landing.js initAuth()
   │
   ├── If state.authToken → call /api/auth/me (_background: true)
   │     ├── 200 → showApp() → _isInitVerified = true → initAppData()
   │     └── 401 → showLanding()
   │
   └── No token → showLanding()

User submits register/login
   │
   ▼
state.authToken = response.token
localStorage.pdb_token = token
showApp()
   │
   ▼
initAppData() → load profile + files + clusters

User clicks Logout (or 401 detected)
   │
   ▼
doLogout()
   ├── localStorage.removeItem('pdb_token')
   ├── localStorage.removeItem('pdb_user')
   ├── state.authToken = null
   ├── state.currentUser = null
   └── window.location.href = '/'  // null-safe redirect (app.html missing #landing-page)
```

### §11.8 Cross-Script Globals (app.js exposes to landing.js)

**Variables** (declared with `var`):
- `state`, `_logoutDebounce`, `_isInitVerified`

**Functions** (hoisted):
- `authFetch()`, `showToast()`, `showConfirm()`, `escapeHtml()`
- `hideLoadingOverlay()`, `showLoadingOverlay()`
- `getLang()`, `applyLanguage()`, `t()`
- `initAppData()`
- `window.UploadTray`

**Script load order in app.html:**
```html
<script src="/legacy/app.js?v=9.4.8" defer></script>
<script src="/legacy/storage_mode.js?v=9.4.8" defer></script>
<script src="/legacy/line_ui.js?v=9.4.8" defer></script>
<script src="/legacy/landing.js?v=9.4.8" defer></script>
```

### §11.9 DOM Build Pattern

**Template strings + innerHTML + escapeHtml():**

```javascript
function escapeHtml(s) {
    if (!s) return '';
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

const html = files.map(f => `
    <div class="file-item" data-id="${f.id}">
        <span>${escapeHtml(f.filename)}</span>
        <span class="status-pill ${pillClass(f.status)}">${escapeHtml(f.status)}</span>
    </div>
`).join('');
container.innerHTML = html;
```

**ห้าม:** plain `innerHTML = userInput` หรือ template literal กับ user data โดยไม่ escape

---

## §12 Design System & UI Foundation

### §12.1 UI Foundation Contract (Binding ตั้งแต่ v9.3.0+)

ดู [.agent-memory/contracts/ui-foundation.md](../../.agent-memory/contracts/ui-foundation.md) — **ทุก PR ที่แตะ frontend ต้องผ่าน 11-item checklist**

### §12.2 CSS Tokens (จาก [shared.css](../../legacy-frontend/shared.css) `:root`)

#### Spacing
```css
--space-1: 4px;   --space-2: 8px;   --space-3: 12px;   --space-4: 16px;
--space-5: 20px;  --space-6: 24px;  --space-8: 32px;   --space-12: 48px;
```

#### Radius
```css
--radius-xs: 4px;   --radius-sm: 6px;   --radius-md: 8px;
--radius-lg: 10px;  --radius-xl: 14px;  --radius-pill: 999px;
```

#### Elevation
```css
--elev-0: none;
--elev-1: 0 1px 2px rgba(0,0,0,0.20);
--elev-2: 0 4px 12px rgba(0,0,0,0.25);
--elev-3: 0 8px 24px -8px rgba(0,0,0,0.40);
--elev-4: 0 16px 48px -12px rgba(0,0,0,0.50);
--elev-popover: 0 8px 32px rgba(0,0,0,0.45);
```

#### Motion
```css
--ease-out: cubic-bezier(0.16, 1, 0.3, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
--duration-fast: 0.15s;
--duration-base: 0.2s;
--duration-slow: 0.3s;
```

#### Typography
```css
--fs-xs: 11px;   --fs-sm: 12px;   --fs-base: 13px;   --fs-md: 14px;
--fs-lg: 16px;   --fs-xl: 18px;   --fs-2xl: 22px;
--tracking-tight: -0.02em;
```

#### Z-index Registry
```css
--z-sticky: 50;
--z-page-header-sticky: 80;
--z-sidebar-mobile: 9800;
--z-modal: 10500;
--z-loading: 10800;
--z-toast: 11050;
```

#### Colors

**Background stack (dark only):**
```css
--bg-primary: #0a0e1a;       /* navy base */
--bg-secondary: #111827;
--bg-card: rgba(17, 24, 39, 0.8);
--surface-1: rgba(255, 255, 255, 0.03);
--surface-2: rgba(255, 255, 255, 0.06);
--surface-3: rgba(255, 255, 255, 0.09);
```

**Text (opacity-based hierarchy):**
```css
--text-primary: rgba(255, 255, 255, 0.92);  /* 92% */
--text-secondary: rgba(255, 255, 255, 0.55); /* 55% */
--text-muted: rgba(255, 255, 255, 0.35);     /* 35% */
```

**Accent (PDB Indigo):**
```css
--accent: #4F46E5;
--accent-hover: #6366f1;
--accent-glow: rgba(79, 70, 229, 0.12);
--accent-soft: rgba(79, 70, 229, 0.06);
```

**Status:**
```css
--success: #22c55e;
--warning: #f59e0b;
--error: #ef4444;
```

**Borders:**
```css
--border: rgba(255, 255, 255, 0.08);
--border-hover: rgba(255, 255, 255, 0.15);
```

**Focus rings:**
```css
--ring-focus: 0 0 0 3px rgba(79, 70, 229, 0.35);
--ring-error: 0 0 0 3px rgba(239, 68, 68, 0.30);
```

**Node families (graph):**
```css
--color-file: #ffd54f;     /* gold */
--color-entity: #ff8a65;   /* orange */
--color-tag: #4fc3f7;      /* cyan */
--color-project: #81c784;  /* green */
--color-pack: #4dd0e1;     /* teal */
--color-person: #b39ddb;   /* purple */
--color-note: #aed581;     /* light green */
--color-mcp: #a78bfa;      /* violet (MCP only) */
```

### §12.3 Canonical Atoms (ห้ามสร้าง variant ใหม่)

| Atom | Variants | Use |
|---|---|---|
| `.btn` | `.btn-primary` `.btn-outline` `.btn-danger` `.btn-ghost` `.btn-sm` `.btn-block` `.btn-lg` | All buttons (5 core + sizing) |
| `.form-input` | `.is-invalid` | Inputs (text/email/password/textarea) |
| `.card` | `.card-tight` `.card-flat` | Container (replaces 7+ legacy variants) |
| `.status-pill` | `.is-active` `.is-warning` `.is-error` `.is-accent` | Status badge (replaces 10+ badges) |
| `.chip` | `.is-active` `.chip-square` | Tag/filter |
| `.meter` (+ `.meter-fill`) | `.is-warning` `.is-error` | Progress/quota |
| `.skeleton` | `-line` `-card` `-circle` | Loading placeholder (replaces "loading...") |
| `.slide-panel` | `.slide-panel-sm` `.slide-panel-md` `.is-open` | Right-side drawer |

### §12.4 Required Patterns

**Page header:**
```html
<div class="page-header">
    <div>
        <h1 class="page-title">Title</h1>
        <p class="page-subtitle">Subtitle</p>
    </div>
    <div class="header-actions"><!-- CTA --></div>
</div>
```

**Empty state (4 children required):**
```html
<div class="empty-state">
    <div class="empty-state-icon">📦</div>
    <h3 class="empty-state-title">ไม่มีไฟล์</h3>
    <p class="empty-state-hint">ลองอัปโหลดไฟล์แรก</p>
    <button class="btn btn-primary empty-state-cta">อัปโหลด</button>
</div>
```

**Modal:**
```html
<div class="modal-overlay">
    <div class="modal">
        <div class="modal-header">
            <h2>Title</h2>
            <button class="btn-close"></button>
        </div>
        <div class="modal-body">Content</div>
        <div class="modal-footer">
            <button class="btn btn-primary">OK</button>
        </div>
    </div>
</div>
```

### §12.5 Trust Signals (Required per Feature)

- [x] **Tabular numbers** — `font-variant-numeric: tabular-nums;` บนทุก count/size/date/percent
- [x] **Focus ring** — `:focus-visible { box-shadow: var(--ring-focus); }` auto-applied to `.btn`/`.form-input`/`.chip`
- [x] **Empty state** — icon + title + hint + optional CTA
- [x] **Skeleton** — แทน "loading..." text
- [x] **Status pill** — entities with state (file, pack, token, plan)
- [x] **Subtle motion** — ≤ 300ms, no bounce/elastic, respect `prefers-reduced-motion`

### §12.6 Anti-AI-Slop Guards (BANNED)

- ❌ Teal accent `#14b8a6`, `#06b6d4` — use indigo `#4F46E5`
- ❌ Purple-pink gradient ใน loading/CTA — only MCP layer (`--color-mcp: #a78bfa`)
- ❌ Serif heading — Inter sans-serif only
- ❌ **Uppercase metric labels** (`text-transform: uppercase` + `letter-spacing > 0.03em`) — sentence case only
- ❌ Glassmorphism over-the-top — limit blur ≤ 14px, opacity ≥ 0.7
- ❌ Emoji in UI text (icon SVG OK)
- ❌ Generic AI copy ("Welcome!", "Get started!", "Boost your productivity")

### §12.7 Breakpoints

```css
@media (max-width: 900px) { /* tablets */ }
@media (max-width: 768px) { /* mobile primary */ }
@media (max-width: 700px) { /* narrow phones */ }
@media (max-width: 600px) { /* very narrow */ }
@media (max-width: 480px) { /* iPhone SE */ }

/* Mobile touch targets (WCAG 2.5.5) */
@media (max-width: 768px) {
    .btn, .form-input { min-height: 44px; }
    .kebab-btn { min-width: 44px; min-height: 44px; }
}
```

### §12.8 Pre-merge Checklist (11 items, ฟ้า verify)

```
[ ] Token usage 100% — no literal padding/radius/color/duration in CSS
[ ] No new card/chip/pill/button/atom variants (or PR has plan)
[ ] Page header + empty state + focus ring ครบ (ถ้ามีหน้าใหม่)
[ ] Skeleton แทน loading text (ถ้ามี async fetch)
[ ] Tabular-nums บนตัวเลข
[ ] No uppercase metric labels
[ ] No purple gradient (loading / CTA)
[ ] No emoji in UI text
[ ] Mobile touch ≥ 44px
[ ] @media (prefers-reduced-motion: reduce) respected
[ ] z-index ใช้ token จาก registry (--z-*)
```

---

## §13 Infrastructure & Deployment

### §13.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies — CRITICAL
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-tha \      # Thai language pack (essential!)
    tesseract-ocr-eng \      # English
    poppler-utils \           # pdf2image dependency
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements-fly.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Code
COPY backend/ ./backend/
COPY legacy-frontend/ ./legacy-frontend/

# Data dirs (Fly volume mount target)
ENV DATA_DIR=/app/data
RUN mkdir -p /app/data/uploads /app/data/summaries /app/data/context_packs /app/data/backups

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Critical:** ห้ามลืม `tesseract-ocr-tha` ไม่งั้น OCR Thai PDF fail silent

### §13.2 fly.toml

```toml
app = "personaldatabank"
primary_region = "sin"   # Singapore

[build]
  # Uses Dockerfile

[env]
  PORT = "8000"

[http_service]
  internal_port = 8000
  force_https = true
  auto_stop_machines = "stop"     # cost saving
  auto_start_machines = true
  min_machines_running = 1

[[vm]]
  memory = "2048mb"
  cpu_kind = "shared"
  cpus = 2

[mounts]
  source = "project_key_data"     # volume name (legacy)
  destination = "/app/data"
```

### §13.3 Python Dependencies (requirements-fly.txt)

**Core:**
- fastapi==0.115.6, uvicorn[standard]==0.34.0
- sqlalchemy==2.0.36, aiosqlite==0.20.0
- pydantic==2.10.4

**Auth:**
- bcrypt>=4.0.0, passlib[bcrypt]>=1.7.4
- python-jose[cryptography]>=3.3.0

**Document parsing:**
- PyPDF2==3.0.1
- python-docx==1.1.2
- beautifulsoup4>=4.12.0
- striprtf>=0.0.26
- python-pptx>=0.6.23
- openpyxl>=3.1.0

**OCR & Images:**
- pytesseract>=0.3.10
- pdf2image>=1.16.0
- Pillow>=10.0.0, pillow-heif>=0.18.0 (HEIC for iPhone)

**AI:**
- google-genai>=0.3.0 (multimodal Files API)

**Billing & Integrations:**
- stripe>=8.0.0
- google-auth>=2.30.0, google-auth-oauthlib>=1.2.0
- google-api-python-client>=2.140.0
- cryptography>=42.0.0 (Fernet)
- resend>=2.0.0
- line-bot-sdk>=3.11.0

**NOT installed on Fly:** Docling (heavy deps, fallback to PyPDF2)

### §13.4 Node Dependencies (package.json)

```json
{
  "devDependencies": {
    "@playwright/test": "^1.59.1"
  }
}
```

**Why only Playwright?** ไม่มี build chain — เป็น vanilla HTML/CSS/JS. Playwright สำหรับ E2E tests เท่านั้น (ไม่ ship ใน prod)

### §13.5 Static Serving

```python
# main.py routes
@app.get("/")               # → landing.html
@app.get("/app")            # → app.html
@app.get("/legacy")         # backward-compat alias for landing
@app.get("/legacy/{filename}") # → legacy-frontend/{filename}
@app.get("/{filename}")     # catch-all static

@app.get("/billing/success") # → 302 /app?billing=success
@app.get("/billing/cancelled") # → 302 /app?billing=cancelled
@app.get("/api/drive/oauth/callback") # → 302 /app?drive_connected=true|false
```

**Cache-Control headers** for `.js`/`.css`/`.html`:
```
Cache-Control: no-cache, no-store, must-revalidate
```
Plus query-string cache-bust: `<link href="/legacy/shared.css?v=9.4.8">`

### §13.6 CORS

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
```

Wide-open (no other domains in normal use — MCP, LINE webhook, Stripe webhook all cross-domain anyway)

### §13.7 Volume Layout

```
/app/data/                              ← Fly volume mount
├── projectkey.db                       ← SQLite (legacy name)
├── projectkey.db-wal                   ← WAL file (concurrent reads)
├── projectkey.db-shm                   ← Shared memory
├── uploads/{user_id}/{file_id}         ← Raw uploaded files
├── summaries/{user_id}/{file_id}.md    ← AI-generated summaries
├── context_packs/{user_id}/{pack_id}.md
├── chroma_db/                          ← Vector embeddings (foundation, unused)
├── backups/projectkey_YYYYMMDD_HHMMSS.db  ← Auto-backup (keep 5)
├── worker_heartbeat                    ← Heartbeat file (touched every 5s)
├── .jwt_secret                         ← JWT key fallback
└── .mcp_secret                         ← MCP server secret fallback
```

---

## §14 Operations & Reliability

### §14.1 Health Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/healthz/queue` | `{queued, processing, success_24h, error_24h, worker_uptime_sec, worker_alive, avg_extract_sec_by_class}` |
| Default `GET /` | landing.html (200 if alive) |

### §14.2 Operational Patterns

**Worker recovery (startup):**
- Reset ALL `processing_status='extracting'` → `'queued'`
- Re-claim within 2s

**Heartbeat detection:**
- Write `/app/data/worker_heartbeat` every 5s
- `/healthz/queue` checks file mtime; ≥ 30s = degraded

**Rolling avg cap** (v9.4.8): outlier protection per priority class

**DELETE guard** (v9.4.8): block DELETE if file is `queued`/`extracting` — return 409 + "Cancel first"

**ai_pack filter** (v9.4.8): organize/pack builder filter `WHERE extraction_status='ok'` (4 places) — กัน AI pack รวม error files

### §14.3 Currently Disabled Features (ห้ามลบ code/DB column)

| Feature | Disabled in | Reason | Re-enable |
|---|---|---|---|
| **Duplicate Detection** (`compute_content_hash` + `find_duplicate_for_file` + `detect_duplicates_for_batch`) | v9.3.2 (2026-05-08) | `UnicodeEncodeError: surrogates not allowed` on PDF text edge case → HTTP 500 on `/api/files/{id}/reprocess` | [DUP-004](../../.agent-memory/project/decisions.md): Flip `_DEDUP_DISABLED = False` ใน [duplicate_detector.py](../../backend/duplicate_detector.py) (1-line) + verify `errors="replace"` in `compute_content_hash.encode()` + run `pytest scripts/duplicate_detection_smoke.py` (33 cases) |

**กฎสำหรับ agent ที่แตะ disabled feature:**
- ❌ ห้ามลบ source code ของ feature ที่ disable
- ❌ ห้าม DROP DB column ของ feature ที่ disable (per DB-003)
- ✅ เปิดกลับโดย flip flag — ห้าม rewrite จาก 0
- ✅ อ่าน TODO marker block ใน source file ก่อน flip

### §14.4 Known Issues

| # | ปัญหา | Severity | Status |
|---|---|---|---|
| P9 | Duplicate detection disabled (`_DEDUP_DISABLED = True` since v9.3.2) | 🟡 MED | Backlog: pending re-enable + pytest |
| P4 | v9.4.2-9.4.8 ไม่มี plan files (shipped 3-in-1 mode) | 🟢 LOW | Acceptable |
| P1 | TC-1..6 ไม่เคย E2E audit | 🟢 LOW | Acceptable, prod stable |
| BN1 | PDF OCR speed 60s/page + silent 20-page cap | 🔴 HIGH | Plan: Gemini native PDF (v9.5) |
| BN2 | Worker concurrency = 1 | 🟠 MED | Plan: bump to 2 (v9.4.9) |
| BN3 | 64 Drive sync stuck rows (`uploaded` not `queued`) | 🟡 MED | Choose strategy A/B/C |
| BN4 | Fly auto-stop cold start 5-10s | 🟢 LOW | Trade-off accepted |

### §14.5 Reliability Gaps (กับ fix proposal)

| Gap | Risk | Proposed Fix |
|---|---|---|
| No periodic stale sweep | Worker hang > 30 min → no recovery until restart | Background task every 5min |
| No SQLite backup automation | Fly volume corrupt = total data loss | Daily `sqlite3 .backup` → R2/S3 |
| JWT 24h no refresh | User logout daily | Refresh token endpoint |
| Vector index inconsistency | Worker dies during index → ghost files | Cleanup sweep + re-index endpoint |
| No CI/CD | All tests manual | GitHub Actions on push |

### §14.6 Scaling Concerns

| Issue | Threshold | Action |
|---|---|---|
| Gemini quota 429 (15 RPM Free) | 100+ AI calls/min | Upgrade Gemini billing (paid = 360 RPM) |
| SQLite write lock | 100+ concurrent uploads | Migrate to Fly Postgres |
| Single-machine bottleneck | 1000+ DAU | Multi-machine (atomic claim ready) |
| Gemini spend uncontrolled | Variable | Per-user spend cap + alert |
| No upload dedup | Same file 2× | Re-enable duplicate_detector |

---

## §15 Security Model

### §15.1 Secrets Management

**Env vars (required for prod):**
- `JWT_SECRET_KEY` — JWT signing (recommend 64-byte random)
- `ADMIN_PASSWORD` — gates dangerous MCP ops, fail-closed if missing
- `OPENROUTER_API_KEY` — LLM
- `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET`
- `RESEND_API_KEY` — email
- `LINE_CHANNEL_SECRET` + `LINE_CHANNEL_ACCESS_TOKEN`
- `GOOGLE_API_KEY` — Gemini multimodal
- `GOOGLE_OAUTH_CLIENT_ID` + `GOOGLE_OAUTH_CLIENT_SECRET` — Drive + Login
- `DRIVE_TOKEN_ENCRYPTION_KEY` — Fernet for refresh_token

**File fallbacks (dev only, ⚠️ multi-machine unsafe):**
- `.jwt_secret`, `.mcp_secret` in `DATA_DIR`

**Set on Fly:**
```bash
flyctl secrets set OPENROUTER_API_KEY=...
flyctl secrets set GOOGLE_API_KEY=...
# etc.
```

### §15.2 Cryptographic Operations

| Operation | Algorithm | Key Source |
|---|---|---|
| Password hash | bcrypt cost=12 | password itself (salt embedded) |
| JWT sign | HS256 | JWT_SECRET_KEY |
| Drive refresh_token encrypt | Fernet (AES-128 + HMAC) | DRIVE_TOKEN_ENCRYPTION_KEY |
| MCP token storage | SHA-256 (one-way) | token plaintext (not stored) |
| File content hash | SHA-256 | file bytes |
| LINE webhook verify | HMAC-SHA256 | LINE_CHANNEL_SECRET |
| Stripe webhook verify | HMAC-SHA256 (stripe SDK) | STRIPE_WEBHOOK_SECRET |
| OAuth PKCE | S256 | random code_verifier |

### §15.3 Input Validation

**Backend:**
- Pydantic models บน request body
- SQL injection: SQLAlchemy parameterized queries (no raw concatenation)
- Path traversal: `filename` sanitized + `secure_filename()` pattern
- File size: enforced at multipart parser + plan_limits

**Frontend:**
- `escapeHtml()` ทุก user-controlled string ก่อน innerHTML
- ไม่มี dangerouslySetInnerHTML pattern (vanilla เลยไม่มี)

### §15.4 Auth Patterns

- JWT in `Authorization: Bearer ...`
- 401 → frontend doLogout
- CSRF: state token in OAuth init (verified in callback)
- Anti-enumeration: uniform response on password reset (whether email exists or not)
- Rate limiting: ⚠️ NOT IMPLEMENTED yet (gap)

### §15.5 Data Privacy

- Per-user filter on every query (`WHERE user_id = :uid`)
- ไม่มี global feed/social — `private_by_default`
- BYOS = user's data ใน user's Drive (server เป็น cache เท่านั้น)
- Original file preserved (no destructive transform)

### §15.6 Drive OAuth Mode Warning

**`GOOGLE_OAUTH_MODE = "testing"`** = refresh tokens หมดอายุ 7 วัน → user hit invalid_grant ทุกสัปดาห์

**Solution:** ส่ง Google verification เพื่อเข้า "production" mode → permanent tokens

**Mitigation (now):** Error banner + 1-click reconnect

---

## §16 Rebuild Roadmap (15 Phases)

ลำดับ phase ที่แนะนำสำหรับ rebuild จาก 0 → feature parity v9.4.8:

### Phase 0 — Foundation (1 day)

- [ ] Setup Python 3.11 + venv
- [ ] Install dependencies (`requirements-fly.txt`)
- [ ] Setup SQLite + create schema (§3.2)
- [ ] Create `config.py` + read env vars
- [ ] Generate secrets: JWT_SECRET_KEY, ADMIN_PASSWORD, DRIVE_TOKEN_ENCRYPTION_KEY
- [ ] Setup FastAPI skeleton + CORS middleware
- [ ] Verify: `GET /` returns 200

### Phase 1 — Auth (1 day)

- [ ] Implement `auth.py`: bcrypt + JWT create/verify
- [ ] Endpoints: register, login, me, request-reset, reset-password
- [ ] Email service via Resend
- [ ] Frontend: `landing.html` + login modal + `landing.js`

### Phase 2 — File Upload Foundation (2 days)

- [ ] Schema: files + indexes
- [ ] POST `/api/upload` (multipart, save raw)
- [ ] Filename truncation (255-byte ext4 limit)
- [ ] GET `/api/files` listing
- [ ] DELETE `/api/files/{id}` (cascade)
- [ ] Frontend: upload zone + file list (no extraction yet)

### Phase 3 — Extraction Pipeline (2 days)

- [ ] `extraction.py`: Docling/PyPDF2/Tesseract (system tesseract-ocr-tha required)
- [ ] `strip_surrogates()` post-processing
- [ ] Synchronous extract in-request (will replace in Phase 5)
- [ ] Frontend: file detail panel with extracted_text preview

### Phase 4 — Plan Limits (1 day)

- [ ] `plan_limits.py`: tier definitions + gate functions
- [ ] Apply gates in upload/pack/summary endpoints
- [ ] Frontend: usage display + 402 error handling

### Phase 5 — Upload Queue + Worker (3 days) — **Critical foundation**

- [ ] Migrate files table: add 7 queue columns (v9.4.0)
- [ ] Enable SQLite WAL mode
- [ ] `upload_worker.py`: atomic claim + heartbeat + recovery
- [ ] Progress callback (asyncio.run_coroutine_threadsafe pattern)
- [ ] Endpoints: /api/upload-status, /api/upload/{id}/retry, /api/upload/{id}/cancel, /api/healthz/queue
- [ ] Frontend: UploadTray IIFE module (360 lines)
- [ ] Truthfulness Contract TC-1..6 enforcement
- [ ] Rolling avg cap per priority class

### Phase 6 — AI Layer (3 days)

- [ ] `llm.py`: OpenRouter wrapper + 3 functions (call_llm, call_llm_pro, call_llm_json)
- [ ] `ai_ingest.py`: Gemini Files API + wait_for_active() polling
- [ ] AI vision for images, audio transcription, video analysis
- [ ] Error classification (15 CODEs)
- [ ] Wire AI ingest into worker for audio/video/image extensions

### Phase 7 — Organize Pipeline (2 days)

- [ ] `organizer.py`: cluster + summary + importance
- [ ] `vector_search.py`: TF-IDF in-memory
- [ ] `graph_builder.py`: extract entities + edges
- [ ] Schema: clusters, file_cluster_map, file_summaries, file_insights, graph_nodes, graph_edges
- [ ] POST /api/organize + /api/organize-new
- [ ] Frontend: Knowledge page + collections view

### Phase 8 — Chat (RAG 7-layer) (2 days)

- [ ] `retriever.py`: 7-layer logic with 12K char budget
- [ ] POST /api/chat → answer + sources
- [ ] Schema: chat_queries + context_injection_logs
- [ ] Frontend: chat page with message stream + sources sidebar

### Phase 9 — Knowledge Graph UI (2 days)

- [ ] 8 graph endpoints (global, nodes, edges, neighborhood, backlinks, outgoing, suggestions)
- [ ] D3.js v7 force-directed simulation
- [ ] Filter chips per family
- [ ] Click node → local subgraph mode

### Phase 10 — Profile + Personality (2 days)

- [ ] Schema: user_profiles + personality_history
- [ ] 4 personality systems (MBTI/Enneagram/Clifton/VIA) + validators
- [ ] GET /api/personality/reference (public)
- [ ] Frontend: profile slide-in panel

### Phase 11 — Context Packs + Memory (2 days)

- [ ] Schema: context_packs + context_memories + pack_shares
- [ ] CRUD + share endpoints
- [ ] AI builder (clarify/propose) — 2-step LLM
- [ ] Smart-merge for context memory (2-hour window)
- [ ] Frontend: pack list + AI builder modal

### Phase 12 — MCP Server (3 days) — **Critical for value prop**

- [ ] Per-user mcp_secret column on users
- [ ] POST `/mcp/{secret}` JSON-RPC 2.0 handler
- [ ] mcp_tools.py: TOOL_REGISTRY + dispatcher
- [ ] Implement 22 tools (start with Read + System, then Edit, then Delete)
- [ ] mcp_tokens.py: `pk_` prefix + SHA-256 storage
- [ ] /api/mcp/info + tokens + permissions endpoints
- [ ] Signed URL pattern for file links (sign_download_token + /d/{token})
- [ ] Frontend: MCP setup page with copy-paste config

### Phase 13 — BYOS Drive (3 days)

- [ ] `drive_oauth.py`: separate from google_login.py
- [ ] Fernet encryption for refresh_token
- [ ] `drive_storage.py` + `drive_layout.py` (folder structure)
- [ ] `drive_sync.py`: push then pull, duplicate prevention, orphan budget
- [ ] PUT /api/storage-mode toggle
- [ ] Frontend: storage_mode.js module + Drive panel in profile

### Phase 14 — Stripe Billing (2 days)

- [ ] `billing.py`: Checkout + Webhook + Portal
- [ ] Webhook signature verify + idempotency (event_id)
- [ ] Schema: webhook_logs + usage_logs + audit_logs
- [ ] subscription_status state machine
- [ ] Frontend: pricing.html + upgrade modal + billing info in profile

### Phase 15 — LINE Bot + Polish (3 days)

- [ ] LINE webhook signature verify (HMAC SHA-256)
- [ ] Account link flow (alphanumeric nonce, 10-min expiry)
- [ ] Rich menu + flex messages
- [ ] Frontend: line_ui.js module + LINE panel in profile
- [ ] Admin panel (`admin.html` + admin endpoints)
- [ ] Polish: i18n TH/EN, Playwright E2E, deployment

### Phase Total: ~32 days for solo developer at high productivity (or ~6-8 weeks realistic)

---

## §17 Appendix

### §17.1 Environment Variables Reference

| Var | Required | Default | Purpose |
|---|---|---|---|
| `JWT_SECRET_KEY` | ⚠️ prod | `.jwt_secret` file | JWT signing |
| `JWT_EXPIRE_MINUTES` | no | 1440 | Token TTL |
| `ADMIN_PASSWORD` | ✅ | (fail-closed) | MCP admin gates |
| `ADMIN_EMAILS` | no | bossok2546@... | Comma-separated bootstrap admins |
| `OPENROUTER_API_KEY` | ✅ | (none) | LLM (chat, organize) |
| `GOOGLE_API_KEY` | no | (none) | Gemini multimodal (audio/video/image) |
| `GEMINI_FILE_MODEL` | no | gemini-2.5-flash | Multimodal model override |
| `GOOGLE_OAUTH_CLIENT_ID` | no | (none) | Drive + Login |
| `GOOGLE_OAUTH_CLIENT_SECRET` | no | (none) | Pair with CLIENT_ID |
| `GOOGLE_OAUTH_REDIRECT_URI` | no | auto | OAuth callback URL |
| `GOOGLE_OAUTH_MODE` | no | testing | testing (7-day tokens) or production |
| `DRIVE_TOKEN_ENCRYPTION_KEY` | ⚠️ if BYOS | (none) | Fernet key (run `Fernet.generate_key()`) |
| `STRIPE_SECRET_KEY` | no | (none) | Billing |
| `STRIPE_WEBHOOK_SECRET` | no | (none) | Webhook signature verify |
| `RESEND_API_KEY` | no | (none) | Password reset emails |
| `LINE_CHANNEL_SECRET` | no | (none) | LINE bot |
| `LINE_CHANNEL_ACCESS_TOKEN` | no | (none) | LINE push API |
| `UPLOAD_WORKER_DISABLED` | no | false | Fallback to inline extraction |
| `UPLOAD_WORKER_POLL_SEC` | no | 2.0 | Worker polling interval |
| `UPLOAD_STALE_TIMEOUT_SEC` | no | 1800 | (unused since v9.4.5) |
| `UPLOAD_MAX_RETRY` | no | 3 | Per-file retry cap |
| `DATA_DIR` | no | BASE_DIR | File storage root |
| `DATABASE_URL` | no | `sqlite+aiosqlite:///{DATA_DIR}/projectkey.db` | DB connection |
| `APP_VERSION` | no | 9.4.8 | Returned in /api/mcp/info |
| `MCP_SECRET` | no | `.mcp_secret` file | Server-wide secret |
| `APP_BASE_URL` | no | http://localhost:8000 | OAuth redirects + emails |

### §17.2 Error Codes Reference

**Backend → Frontend i18n boundary** (v9.4.4)

| CODE | Cause | TH | EN |
|---|---|---|---|
| ENCRYPTED | PDF password-protected | ไฟล์ติดรหัส | Encrypted file |
| FILE_MISSING | Disk file deleted | ไฟล์หาย | File missing |
| TIMEOUT | Extraction > limit | หมดเวลา | Timed out |
| OUT_OF_MEMORY | MemoryError | หน่วยความจำเต็ม | Out of memory |
| ENCODING | UnicodeError | อักขระเสีย | Encoding error |
| QUOTA_EXCEEDED | Gemini 429 | เกินโควต้า | Quota exceeded |
| GEMINI_UNAVAILABLE | Gemini 503 | Gemini ขัดข้อง | Gemini unavailable |
| MODEL_DEPRECATED | Gemini 404 | โมเดลถูกยกเลิก | Model deprecated |
| FILE_NOT_ACTIVE | Files API state != ACTIVE | ไฟล์ยังประมวลผลไม่เสร็จ | File not active |
| PERMISSION_DENIED | Auth issue | ไม่มีสิทธิ์ | Permission denied |
| OCR_FAIL | Tesseract error | OCR ผิดพลาด | OCR failed |
| NETWORK | Connection issue | เน็ตขัดข้อง | Network error |
| UNKNOWN | Default | ขัดข้อง — ลองใหม่ | Unknown error — retry |

### §17.3 Critical "Gotchas" สำหรับคน Rebuild

1. **`var state` not `const`** — landing.js ต้องอ่านได้ → ใช้ `var` ห้าม `const`/`let`
2. **`_isInitVerified` guard** — ป้องกัน logout ระหว่าง startup grace period
3. **`_background: true` option** — สำหรับ pre-auth fetch ที่ 401 ไม่ควรทำให้ logout
4. **localStorage `pdb_*` prefix migration** — `app.js:43-51` migrate `projectkey_*` keys ก่อนใช้
5. **Tesseract Thai pack** — `tesseract-ocr-tha` ต้องอยู่ใน Dockerfile, ไม่งั้น OCR Thai PDF fail silent
6. **LINE nonce ALPHANUMERIC ONLY** — ใช้ `secrets.token_hex(32)` (64 hex chars) ห้าม base64url (LINE reject `-`/`_`)
7. **OAuth state cache แยก** — `_GLOGIN_STATE_CACHE` (login) vs `_STATE_CACHE` (Drive) → ห้ามใช้ร่วม
8. **Per-user MCP secret in URL** — `/mcp/{secret}` ไม่ใช่ Authorization header (Claude Connector ไม่อ่าน)
9. **Recovery sweep reset ALL** — ไม่ใช่ stale-by-timeout เท่านั้น (v9.4.5 fix)
10. **Heartbeat task separate** — ไม่อยู่ใน main loop (v9.4.5 — fix false-positive "stopped")
11. **Progress callback `asyncio.run_coroutine_threadsafe(_main_loop)`** — ห้ามใช้ `get_event_loop()` ใน thread (v9.4.6)
12. **DELETE block during extracting** — return 409 + "Cancel first" (v9.4.8)
13. **ai_pack_builder filter `extraction_status='ok'`** — 4 จุด (v9.4.8)
14. **Rolling avg cap per class** — 5/60/300s — ห้าม pollute typical estimate (v9.4.8)
15. **`strip_surrogates()` before DB write** — กัน UnicodeEncodeError จาก PDF font edge cases (v9.3.3)
16. **20-page OCR cap** — silent truncation in `extraction.py` — user ไม่รู้ → ต้องแจ้งใน UI
17. **Filename UTF-8 byte count** — Thai = 3 bytes/char → 108 ตัว = 262 bytes > 255 ext4 limit → ต้อง truncate stem (v9.4.7)
18. **Stripe webhook idempotency** — INSERT to `webhook_logs` WHERE event_id NOT EXISTS ก่อน process
19. **Plan limits ก่อน action** — ห้าม check หลัง (ค่าใช้จ่าย Gemini ไปแล้ว → bill user)
20. **CORS wide-open OK** — ทุก endpoint check Authorization header แล้ว

### §17.4 Code Conventions (จาก [.agent-memory/contracts/conventions.md](../../.agent-memory/contracts/conventions.md))

#### Python (Backend)

**Style:**
- ใช้ **type hints** ทุก function
- ใช้ **f-strings** ห้าม `.format()` หรือ `%`
- Import order: stdlib → third-party → local
- Function/variable: `snake_case`
- Class: `PascalCase`
- Constants: `UPPER_SNAKE_CASE`

**Comments:**
- Comment + docstring = **ภาษาไทย** (สำหรับ business logic)
- ตัวแปร/ชื่อฟังก์ชัน = English เสมอ
- Comment เฉพาะ "WHY" ห้าม "WHAT"

**Error handling:**
- Validate input ที่ boundary (API endpoints) เสมอ
- Internal functions ไม่ defensive ถ้า caller validate แล้ว
- Error response: `{"error": {"code": "ERROR_CODE", "message": "..."}}`
- Error codes: `UPPER_SNAKE_CASE` (e.g. `INVALID_TOKEN`, `FILE_NOT_FOUND`)

**API routes (FastAPI):**
- Path: `/api/<resource>` หรือ `/api/<resource>/<action>`
- Method: REST conventions (GET / POST / PUT / DELETE)
- Auth: dependency injection จาก [auth.py](../../backend/auth.py)
- Response models: Pydantic

#### Frontend (Legacy HTML/JS)

**JavaScript:**
- ES6+ (const/let, arrow functions, async/await)
- ห้าม `var` (ยกเว้น `state`, `_logoutDebounce`, `_isInitVerified` ที่ landing.js ต้องอ่าน)
- `fetch()` สำหรับ API calls
- Function: `camelCase`
- DOM IDs: `kebab-case`

**CSS:**
- Class-based selectors
- ห้าม `!important` ถ้าไม่จำเป็น
- ใช้ CSS variables — token-only ตาม [UI Foundation Contract](.agent-memory/contracts/ui-foundation.md) §12.8

**HTML:**
- Semantic HTML5 (`<header>`, `<nav>`, `<main>`)
- Forms ต้องมี `<label>` เชื่อมกับ input
- aria-labels บนปุ่ม icon-only

#### Git Commits

**Format:**
```
<type>(<scope>): <description>

[optional body]

Author-Agent: <agent-name>
```

**Types:** `feat` / `fix` / `refactor` / `test` / `docs` / `chore`

**Scopes:** `auth`, `billing`, `mcp`, `frontend`, `backend`, `db`, `tests`, `memory`, `upload`, `quality`

**Example:**
```
feat(auth): add password reset endpoint

เพิ่ม POST /api/auth/reset-password
ส่ง email link ผ่าน Resend API
Token หมดอายุใน 1 ชั่วโมง

Author-Agent: แดง (Daeng)
```

#### File / Folder Naming
- Python: `snake_case.py`
- HTML/CSS/JS: `kebab-case.html`
- Markdown root docs: `UPPER_SNAKE_CASE.md`
- Tests: `_test_<module>.py` or `test_<module>.py`

#### ภาษา (Language Usage Matrix)

| Context | Language |
|---|---|
| Code (vars, functions, classes) | English |
| Comments / docstrings (business) | Thai |
| Comments (algo) | English OK |
| Error messages → user | Thai |
| Error codes (constants) | English UPPER_SNAKE_CASE |
| Git commit messages | Thai OR English (consistent per commit) |
| Memory files | Thai primary |
| Agent communication | Thai |

#### Security Conventions
- **ห้าม commit:** `.env`, `.jwt_secret`, `.mcp_secret`, `*.db`, API keys
- **ห้าม log:** passwords, tokens, full credit card numbers
- **Validate:** ทุก user input ที่เข้า DB หรือ shell
- **SQL:** parameterized queries เท่านั้น (database.py ทำให้แล้ว)

### §17.5 Test Strategy

**Unit:**
- pytest สำหรับ extraction, organizer, retriever, plan_limits
- Mock Gemini/OpenRouter responses

**Integration:**
- Smoke scripts ใน [scripts/](../../scripts/) — pattern `v9_X_Y_smoke.py`
- Run real file ผ่าน full pipeline (1 file per format group)

**E2E:**
- Playwright suite ใน [tests/e2e-ui/](../../tests/e2e-ui/)
- phase0-baseline.spec.js — 17 critical flows
- v9.3.0-foundation.spec.js — UI tokens compliance
- Run with `PDB_TEST_URL=http://127.0.0.1:8765 npx playwright test ...`

**Real End-to-End (lesson from v9.4.x):**
- ทุก format group ต้องผ่านไฟล์จริง 1 ไฟล์ก่อนบอก "done"
- Per-format smoke checklist:
  - [ ] Text doc (pdf, docx)
  - [ ] Image (jpg, png)
  - [ ] Audio (mp3, wav)
  - [ ] Video (mp4, mov)

### §17.6 Reference Documents

- [REPORT-v9.4.8.md](../../REPORT-v9.4.8.md) — Technical & Business Report (600 lines)
- [.agent-memory/](../../.agent-memory/) — Working memory + plans + decisions
- [.agent-memory/contracts/ui-foundation.md](../../.agent-memory/contracts/ui-foundation.md) — UI Foundation Contract
- [.agent-memory/contracts/conventions.md](../../.agent-memory/contracts/conventions.md) — Coding conventions
- [.agent-memory/project/architecture.md](../../.agent-memory/project/architecture.md) — Architecture decisions
- [.agent-memory/project/decisions.md](../../.agent-memory/project/decisions.md) — ADRs
- [.agent-memory/current/pipeline-state.md](../../.agent-memory/current/pipeline-state.md) — Current sprint state
- [docs/prd/](../prd/) — PRDs (v1, v5.5 Context Memory, v5.6 Guide, v5.9.x billing)

---

## END OF BLUEPRINT

**สรุปคำคุณภาพ:**
- เอกสารนี้คือ snapshot ที่ v9.4.8 — โครงสร้างนี้ยังใช้ได้แม้ feature เปลี่ยน เพราะ architecture decisions (ADRs) เป็นของ persistent
- ถ้า rebuild ตาม §16 จะได้ feature parity v9.4.8 ใน 6-8 สัปดาห์ (solo, full-time)
- **ห้ามแหก:** §1.3 4 Principles + §15 Security Model + §12.1 UI Foundation Contract
- **ห้ามลืม:** Tesseract Thai pack, var state, per-user MCP secret, Fernet for Drive tokens, atomic claim SQL, 1.5s progress throttle, heartbeat task separate
- ถ้ามีคำถาม: ดู `.agent-memory/` ก่อน → ดู source code line เลข → ถาม founder
