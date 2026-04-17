# 📋 Project KEY — รายงานสรุป MVP v2.0

> **วันที่จัดทำ:** 17 เมษายน 2569  
> **เวอร์ชัน:** MVP v2.0 (Second Brain Chat Layer)  
> **เวอร์ชันก่อนหน้า:** MVP v0.1 (Stable Foundation)  
> **สถานะ:** ✅ Production-ready (single-user, local deployment)  
> **จัดทำโดย:** Antigravity AI + ทีมพัฒนา

---

## 1. Vision & เป้าหมายโปรเจกต์

> **v0.1: "พื้นที่ข้อมูลส่วนตัว — ปลอดภัย เป็นระบบ เรียกค้นได้ทันที"**  
> **v2.0: "Second Brain — AI ที่เข้าใจตัวคุณ เข้าใจบริบท และตอบได้อย่างต่อเนื่อง"**

### สิ่งที่เปลี่ยนจาก v0.1 → v2.0

| ด้าน | v0.1 | v2.0 |
|------|------|------|
| **AI Context** | ใช้เฉพาะไฟล์ที่อัปโหลด | Profile + Context Packs + Files (หลายชั้น) |
| **ความเข้าใจผู้ใช้** | ไม่มี — ต้องอธิบายตัวเองทุกครั้ง | User Profile — AI รู้จักคุณตั้งแต่แรก |
| **การค้นหา** | TF-IDF อย่างเดียว | Hybrid Search (semantic + keyword) |
| **ความโปร่งใส** | แสดง files ที่ใช้ | แสดง 4 layers + reasoning + injection summary |
| **ข้อมูลระดับสูง** | ไม่มี | Context Packs — กลั่นความรู้จากหลายไฟล์ |
| **ความปลอดภัย** | API key hardcode | `.env` + file size limit |

### การทำงานของ v2.0

```
v1: Store → Organize → Summarize → AI Chat (file-level)
v2: Store → Organize → Summarize → Profile + Context Packs → Auto Inject → AI Chat (multi-layer)
```

---

## 2. สรุประบบ Functional Requirements

### Requirements เดิม (v0.1) — ยังคงทำงานครบ

| รหัส | Requirement | สถานะ |
|------|-------------|--------|
| FR-1 | อัปโหลดไฟล์ (PDF, TXT, MD, DOCX) | ✅ ครบ + file size validation |
| FR-2 | เก็บ metadata และ extracted text | ✅ ครบ |
| FR-3 | ดึงข้อความจากไฟล์ (extraction) | ✅ ครบ |
| FR-4 | แสดงรายการไฟล์พร้อม metadata | ✅ ครบ |
| FR-5 | จัดกลุ่มไฟล์ด้วย AI (clustering) | ✅ ครบ |
| FR-6 | ให้คะแนนความสำคัญ (importance scoring) | ✅ ครบ |
| FR-7 | ระบุ Primary Candidate | ✅ ครบ |
| FR-8 | สร้าง Markdown summary ต่อไฟล์ | ✅ ครบ |
| FR-9 | AI Chat พร้อม Retrieval | ✅ ครบ — **ยกเครื่องใหม่ด้วย Auto Injection** |
| FR-10 | แสดง Source Transparency | ✅ ครบ — **4-layer transparency panel** |
| FR-11 | Privacy (single-user isolation) | ⚠️ `DEFAULT_USER_ID` (no auth) |

### Requirements ใหม่ (v2.0)

| รหัส | Requirement | สถานะ |
|------|-------------|--------|
| FR-12 | 👤 User Profile — ระบบรู้จักผู้ใช้ | ✅ ครบ — CRUD API + Profile Panel UI |
| FR-13 | 📦 Context Packs — กลั่นบริบทจากหลายไฟล์ | ✅ ครบ — LLM distillation + vector indexing |
| FR-14 | 🔍 Hybrid Search — semantic + keyword | ✅ ครบ — alpha=0.6 configurable |
| FR-15 | 🧠 Auto Context Injection — inject อัตโนมัติ 5 ชั้น | ✅ ครบ — Profile → Packs → Clusters → Files |
| FR-16 | 📊 Context Injection Log — บันทึกการ inject | ✅ ครบ — DB logging + injection_summary |
| FR-17 | 🔒 API Key Security — ย้ายไป .env | ✅ ครบ — python-dotenv |
| FR-18 | 📏 File Size Validation | ✅ ครบ — max 20 MB |

---

## 3. Architecture & Tech Stack (v2.0)

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (v2.0)                           │
│   index.html + app.js + styles.css                               │
│   Vanilla HTML / CSS / JavaScript                                 │
│                                                                   │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────────────────┐│
│   │ My Data      │ │ Collections  │ │ AI Chat                  ││
│   │ + Status     │ │ + Derived    │ │ + 4-Layer Sources Panel  ││
│   │   Cards      │ │   Packs      │ │ + Profile Indicator      ││
│   │ + Pack Cards │ │              │ │ + Injection Badge        ││
│   └──────────────┘ └──────────────┘ └──────────────────────────┘│
│   ┌──────────────────────────────────────────────────────────┐  │
│   │ Modals: Profile Panel + Create Pack + Confirm + Summary  │  │
│   └──────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────────┘
                       │  HTTP REST API (fetch)
┌──────────────────────▼──────────────────────────────────────────┐
│                        BACKEND (v2.0)                             │
│   FastAPI v0.115.6 + Uvicorn v0.34.0                             │
│   Python 3.10                                                     │
│                                                                   │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ main.py    │  │organizer │  │ retriever.py │  │ llm.py    │ │
│  │ 16 API     │  │ (AI pipe)│  │ (5-LAYER     │  │ OpenRouter│ │
│  │ endpoints  │  │          │  │  INJECTION)  │  │ wrapper   │ │
│  └────────────┘  └──────────┘  └──────────────┘  └───────────┘ │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐ │
│  │ profile.py │  │context_  │  │vector_search │  │extraction │ │
│  │ NEW — User │  │packs.py  │  │ ENHANCED —   │  │ (text)    │ │
│  │ Profile    │  │ NEW —    │  │ Hybrid Mode  │  │           │ │
│  │ Service    │  │ Context  │  │              │  │           │ │
│  └────────────┘  └──────────┘  └──────────────┘  └───────────┘ │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                        DATA LAYER (v2.0)                         │
│  SQLite (projectkey.db) — async via aiosqlite                    │
│  SQLAlchemy 2.0 ORM (Async) — 10 tables (+3 ใหม่)               │
│  Filesystem: uploads/ + summaries/ + context_packs/              │
│  .env — API key storage (python-dotenv)                          │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                     EXTERNAL API                                  │
│  OpenRouter API → google/gemini-2.5-flash                        │
│  (Clustering, Scoring, Summary, Pack Generation, Chat)           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. โครงสร้างไฟล์โปรเจกต์ (v2.0)

```
PDB/
├── .env                        # 🔒 API key (NEW — ไม่ commit)
├── .gitignore                  # ป้องกัน .env, DB, uploads
├── index.html                  # UI หลัก (3 หน้า + 4 modals)
├── app.js                      # Frontend logic (v2 — ~600 lines)
├── styles.css                  # Design system (v2 — ~950 lines)
├── PRD.md                      # PRD เวอร์ชัน v0.1
├── Project_KEY_PRD_MVP_v2.md   # PRD เวอร์ชัน v2.0
├── PROJECT_REPORT.md           # ← ไฟล์นี้
├── requirements.txt            # Python dependencies (11 packages)
├── projectkey.db               # SQLite database (10 tables)
│
├── backend/
│   ├── main.py                 # FastAPI app — 16 API endpoints
│   ├── database.py             # SQLAlchemy models — 10 tables (+3 ใหม่)
│   ├── config.py               # Configuration — dotenv + paths
│   ├── profile.py              # 🆕 User Profile service
│   ├── context_packs.py        # 🆕 Context Pack service
│   ├── retriever.py            # 🔀 Refactored — 5-layer auto injection
│   ├── vector_search.py        # 🔀 Enhanced — Hybrid search
│   ├── organizer.py            # AI clustering + scoring + summarization
│   ├── extraction.py           # Text extraction (PDF/TXT/MD/DOCX)
│   ├── markdown_store.py       # บันทึก/อ่าน .md summary files
│   └── llm.py                  # OpenRouter API wrapper
│
├── uploads/                    # ไฟล์ดิบที่อัปโหลด
├── summaries/                  # Markdown summaries ต่อไฟล์
├── context_packs/              # 🆕 Context pack .md files
└── testsprite_tests/           # TestSprite E2E test scripts
```

---

## 5. Database Schema (v2.0)

### ตารางเดิม (v0.1)
```
users          → id, name, created_at
files          → id, user_id, filename, filetype, raw_path,
                 uploaded_at, extracted_text, processing_status
clusters       → id, user_id, title, summary, created_at
file_cluster_map → file_id, cluster_id, relevance_score
file_insights  → file_id, importance_score (0-100),
                 importance_label (high/medium/low),
                 is_primary_candidate, why_important
file_summaries → file_id, md_path, summary_text,
                 key_topics (JSON), key_facts (JSON),
                 why_important, suggested_usage
chat_queries   → id, user_id, question, answer,
                 selected_cluster_ids, selected_file_ids,
                 retrieval_modes, reasoning, created_at
```

### ตารางใหม่ (v2.0) 🆕
```
user_profiles          → user_id (FK), identity_summary, goals,
                         working_style, preferred_output_style,
                         background_context, updated_at

context_packs          → id, user_id, type (profile/study/work/project),
                         title, summary_text, md_path,
                         source_file_ids (JSON), source_cluster_ids (JSON),
                         created_at, updated_at

context_injection_logs → id, chat_query_id (FK), profile_used (bool),
                         context_pack_ids (JSON), file_ids (JSON),
                         cluster_ids (JSON), injection_summary, 
                         retrieval_reason, created_at
```

### ความสัมพันธ์

```
User ← 1:1 → UserProfile
ChatQuery ← 1:1 → ContextInjectionLog
User ← 1:N → ContextPack
ContextPack → N:M → Files (via source_file_ids JSON)
ContextPack → N:M → Clusters (via source_cluster_ids JSON)
```

---

## 6. API Endpoints (v2.0)

### Endpoints เดิม (v0.1 — ปรับปรุง)

| Method | Path | คำอธิบาย | v2 Changes |
|--------|------|----------|------------|
| `POST` | `/api/upload` | อัปโหลดไฟล์ + extract text | +file size validation |
| `POST` | `/api/organize` | AI pipeline (cluster+score+summarize) | — |
| `GET` | `/api/files` | รายการไฟล์พร้อม metadata | — |
| `DELETE` | `/api/files/{id}` | ลบไฟล์ | — |
| `GET` | `/api/clusters` | รายการ clusters + ไฟล์ | +derived_packs field |
| `GET` | `/api/summary/{id}` | ดึง summary ต่อไฟล์ | — |
| `POST` | `/api/chat` | AI Chat | **ยกเครื่อง — Auto Injection** |
| `GET` | `/api/stats` | สถิติภาพรวม | +packs count, profile status |

### Endpoints ใหม่ (v2.0) 🆕

| Method | Path | คำอธิบาย |
|--------|------|----------|
| `GET` | `/api/profile` | ดึง User Profile |
| `PUT` | `/api/profile` | สร้าง/อัปเดต Profile |
| `GET` | `/api/context-packs` | รายการ Context Packs ทั้งหมด |
| `POST` | `/api/context-packs` | สร้าง Context Pack (LLM generation) |
| `GET` | `/api/context-packs/{id}` | ดึง Pack เดียว |
| `DELETE` | `/api/context-packs/{id}` | ลบ Context Pack |
| `POST` | `/api/context-packs/{id}/regenerate` | Regenerate จาก sources เดิม |
| `DELETE` | `/api/reset` | Reset data ทั้งหมด (testing) |

### Chat Response Format (v2.0)

```json
{
  "answer": "...",
  "cluster": { "id": "...", "title": "...", "summary": "..." },
  "files_used": [
    { "id": "...", "filename": "...", "importance_label": "high", "is_primary": true }
  ],
  "context_packs_used": [
    { "id": "...", "type": "study", "title": "NOVA Research Context" }
  ],
  "profile_used": true,
  "retrieval_modes": { "file_id": "summary" },
  "reasoning": "อธิบายเหตุผลการเลือกข้อมูลเป็นภาษาไทย",
  "injection_summary": "โปรไฟล์ผู้ใช้ + 1 Context Pack + 2 ไฟล์"
}
```

---

## 7. AI Pipeline อธิบายละเอียด (v2.0)

### 7.1 Organization Pipeline (`organizer.py`) — ไม่เปลี่ยน

```
1. โหลดไฟล์ทั้งหมด → 2. LLM จัดกลุ่ม → 3. LLM ให้คะแนน → 4. LLM สร้างสรุป → 5. TF-IDF index
```

### 7.2 Context Pack Generation (`context_packs.py`) 🆕

```
1. ผู้ใช้เลือก source files + source clusters
2. รวบรวม content จาก summaries / extracted text
3. ส่งไป LLM → distill เป็นบริบทระดับสูง (ภาษาไทย)
4. บันทึกเป็น .md file ใน context_packs/
5. บันทึก ContextPack record ใน DB
6. Index ใน vector search เพื่อให้ hybrid search หาเจอ
```

### 7.3 Hybrid Search (`vector_search.py`) 🆕

```
hybrid_search(query, alpha=0.6):
  1. semantic_results = TF-IDF cosine similarity (full query)
  2. keyword_results  = exact/partial token matching
  3. merged = merge by (file_id, chunk_index)
  4. score  = alpha × semantic + (1-alpha) × keyword
  5. return sorted by score, top N
```

### 7.4 Auto Context Injection Pipeline (`retriever.py`) — ยกเครื่องใหม่ 🆕

```
User Question
     │
     ├─── Layer 1: Load User Profile → inject as system context
     │
     ├─── Layer 2: Load Context Packs → hybrid search for relevant packs
     │
     ├─── Layer 3: Hybrid Search → find relevant chunks across ALL data
     │
     ├─── Layer 4: Build Inventory → list all available sources for LLM
     │
     ├─── Layer 5: LLM Context Selection → choose best sources + mode
     │         ├── mode: "summary" (default, overview)
     │         ├── mode: "excerpt" (specific details)  
     │         └── mode: "raw" (exact quotes)
     │
     ├─── Assemble Context Block (priority: Profile → Packs → Clusters → Files)
     │    └── Token budget: max 12,000 chars
     │
     ├─── Generate Answer (LLM + user's preferred output style)
     │
     ├─── Log Injection (ContextInjectionLog → DB)
     │
     └─── Return: answer + files_used + packs_used + profile_used + reasoning
```

---

## 8. UI/UX สรุป (v2.0)

### 3 หน้าหลัก

| หน้า | ฟีเจอร์ v0.1 | ฟีเจอร์ใหม่ v2.0 |
|------|-------------|------------------|
| **My Data** | Upload zone, file list, status badges, organize button | + 3 Status Cards (Profile/Packs/AI Ready), Context Packs grid, create pack modal |
| **Collections** | Cluster cards, importance badges, primary badge, summary modal | + Derived Context Packs row ในแต่ละ cluster |
| **AI Chat** | Chat UI, suggestion chips, Sources Panel | + Profile indicator, 4-layer welcome chips, injection badge, enhanced 6-section Sources Panel |

### UI Components ใหม่ (v2.0) 🆕

| Component | ตำแหน่ง | หน้าที่ |
|-----------|---------|---------|
| **Status Cards** | My Data (top) | แสดง Profile / Packs / AI Ready status |
| **Context Pack Cards** | My Data (bottom) | แสดง packs ที่สร้างแล้ว + regenerate/delete |
| **Profile Panel** | Modal (click sidebar avatar) | 5 fields: identity, goals, style, output, background |
| **Create Pack Modal** | Modal (click "+ สร้าง Context Pack") | Type selector + title + source checkboxes |
| **Profile Indicator** | Chat header (top right) | แสดง "Profile: Active" / "Profile: Not set" |
| **Context Layer Chips** | Chat welcome | แสดง 4 layers + counts (Profile ✓ / Packs 1 / Collections 3 / Files 5) |
| **Injection Badge** | Chat response | 🧠 badge แสดง injection summary |
| **Derived Packs Row** | Collections clusters | แสดง Context Packs ที่สร้างจาก cluster นี้ |

### Design System (v2.0)

| ด้าน | รายละเอียด |
|------|-----------|
| **Color Scheme** | Dark mode `#0a0e1a` base |
| **Layer Colors** | 👤 Profile = Purple `#b39ddb` / 📦 Packs = Blue `#4fc3f7` / 📁 Collections = Green `#81c784` / 📄 Files = Yellow `#ffd54f` |
| **Typography** | Google Inter (300-700) |
| **Effects** | Glassmorphism, backdrop-blur, gradient buttons |
| **Animations** | fadeIn, slideUp, slideIn, pulse, spin |

---

## 9. การทดสอบ E2E — MVP v2.0

### ผลการทดสอบแบบเต็ม Flow

| # | Test | ขั้นตอน | ผล | Evidence |
|---|------|---------|-----|----------|
| 1 | 👤 Profile Setup | เปิด Profile Panel → กรอก 5 fields → Save | ✅ **PASS** | Status dot เปลี่ยนเป็นเขียว, sidebar แสดง "Active" |
| 2 | 📦 Create Context Pack | เลือก type "การเรียน" → ตั้งชื่อ → เลือก 2 sources → Generate | ✅ **PASS** | Pack card ปรากฏ, sidebar แสดง "1 context packs" |
| 3 | 🧠 AI Chat + Injection | ถาม "NOVA คืออะไร" → รอ AI ตอบ | ✅ **PASS** | AI ตอบเป็นภาษาไทย, อ้างอิง files + pack |
| 4 | 📊 Injection Verification | ตรวจ API response | ✅ **PASS** | `profile_used: true`, `context_packs_used: ["NOVA Research Context"]`, `files_used: 2`, `injection_summary: "โปรไฟล์ผู้ใช้ + 1 Context Pack + 2 ไฟล์"` |
| 5 | 🔍 Hybrid Search | AI เลือก sources ถูกต้อง | ✅ **PASS** | เลือก NOVA PDFs + Context Pack ที่เกี่ยวข้อง |
| 6 | 💬 Reasoning | ระบบอธิบายเหตุผล | ✅ **PASS** | reasoning เป็นภาษาไทย อธิบายว่าเลือก sources อะไรและเพราะอะไร |
| 7 | 📄 v1 Compatibility | ข้อมูลเดิม 5 ไฟล์ + 3 clusters ยังทำงาน | ✅ **PASS** | ไม่มี migration issues |

### API Verification (ตัวอย่าง response จริง)

```
injection_summary: "โปรไฟล์ผู้ใช้ + 1 Context Pack + 2 ไฟล์"

Layer 1 — Profile:     ✅ ใช้ (profile_used: true)
Layer 2 — Packs:       ✅ "NOVA Research Context" (type: study)
Layer 3 — Collections: — (cross-collection query)
Layer 4 — Files:       ✅ วิจัยโปร NOVA V1.pdf (summary, high)
                       ✅ problem_analysis_ai_context_continuity.md (summary, high, primary)
```

---

## 10. สิ่งที่เปลี่ยนแปลงจาก v0.1 → v2.0 (Changelog)

### A. ไฟล์ใหม่ (3 ไฟล์)

| ไฟล์ | หน้าที่ |
|------|---------|
| `.env` | เก็บ API key แบบปลอดภัย (ไม่ commit) |
| `backend/profile.py` | User Profile CRUD + context text generation |
| `backend/context_packs.py` | Context Pack CRUD + LLM distillation + vector indexing |

### B. ไฟล์ที่แก้ไข (10 ไฟล์)

| ไฟล์ | การเปลี่ยนแปลงหลัก |
|------|-------------------|
| `backend/config.py` | dotenv loading + `CONTEXT_PACKS_DIR` + `MAX_FILE_SIZE_MB` |
| `backend/database.py` | +3 ORM models: UserProfile, ContextPack, ContextInjectionLog |
| `backend/vector_search.py` | +`keyword_search()` + `hybrid_search(alpha=0.6)` |
| `backend/retriever.py` | **Full rewrite** — 5-layer auto injection pipeline |
| `backend/main.py` | +8 new endpoints (profile, packs, reset, enhanced stats) |
| `requirements.txt` | +`python-dotenv` |
| `index.html` | +Profile panel, +Pack modal, +Status cards, +Enhanced chat UI |
| `styles.css` | **Full rewrite** — v2 design system with layer colors |
| `app.js` | **Full rewrite** — Profile/Pack CRUD, injection viz, source panel |
| `.gitignore` | ยืนยัน `.env` ถูก ignore |

### C. ข้อจำกัดจาก v0.1 ที่แก้ไขแล้ว

| # | ข้อจำกัด v0.1 | สถานะ v2.0 |
|---|--------------|------------|
| 1 | API Key hardcode ใน config.py | ✅ **แก้แล้ว** — ย้ายไป `.env` |
| 2 | ไม่มี file size limit | ✅ **แก้แล้ว** — max 20 MB |
| 3 | Vector index ใน RAM — restart หาย | ⚠️ ยังเป็น in-memory (rebuild on reload) |
| 4 | ไม่มีระบบ Auth | ⚠️ ยังเป็น `DEFAULT_USER_ID` |

---

## 11. ข้อจำกัดที่ยังมีอยู่ (Known Limitations v2.0)

| # | ข้อจำกัด | ความเสี่ยง | แนวทาง Next Version |
|---|---------|-----------|-------------------| 
| 1 | **ไม่มีระบบ Auth** — DEFAULT_USER_ID | High (ถ้า deploy shared) | JWT / OAuth2 |
| 2 | **Vector index ใน RAM** — restart rebuild | Medium | Persist ลง disk / ChromaDB |
| 3 | **ไม่มี encryption** — ไฟล์เก็บ plaintext | Low (local deploy) | Encrypt at rest |
| 4 | **Context Pack ไม่ auto-update** เมื่อ source เปลี่ยน | Low | Auto-regenerate trigger |
| 5 | **Profile ไม่มี AI suggestion** | Low | LLM suggest profile fields |
| 6 | **Single-threaded organize** — ทีละไฟล์ | Low (MVP scale) | Background task / queue |

---

## 12. วิธีรัน

### Prerequisites

```bash
# Python 3.10+
pip install -r requirements.txt
```

### Setup .env

```bash
# สร้างไฟล์ .env ที่ root directory
echo OPENROUTER_API_KEY=sk-or-v1-xxxxxxxxxxxx > .env
```

### Start Server

```bash
cd c:\Users\meuok\Desktop\PDB
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### เปิดเว็บ

```
http://localhost:8000
```

### Quick Start Guide

1. **ตั้งค่า Profile** — คลิก "My Profile" ที่ sidebar ล่าง → กรอกข้อมูล → Save
2. **อัปโหลดไฟล์** — ลากวางที่ Upload Zone หรือคลิก "Upload Files"
3. **จัดระเบียบ** — คลิก "จัดระเบียบด้วย AI" (รอ 30-60 วินาที)
4. **สร้าง Context Pack** — คลิก "+ สร้าง Context Pack" → เลือก sources → Generate
5. **ถาม AI** — ไปหน้า AI Chat → ถามคำถาม → ดู Sources Panel ด้านขวา

---

## 13. Roadmap — Next Steps

### P0 — Trust & Auth

- [ ] เพิ่ม Authentication (JWT / session-based)
- [ ] Persist TF-IDF index ลง disk
- [ ] Rate limiting ที่ `/api/organize` และ `/api/context-packs`

### P1 — Intelligence

- [ ] Auto Context Pack — สร้างอัตโนมัติเมื่อ organize เสร็จ
- [ ] AI-suggested Profile — LLM แนะนำ fields จากไฟล์ที่อัปโหลด
- [ ] Conversation Memory — จำบทสนทนาข้ามรอบ

### P2 — UX Enhancement

- [ ] Search bar ในหน้า My Data
- [ ] Pack detail view (expand full content)
- [ ] Export summary + packs เป็น PDF
- [ ] Profile progress bar / completeness indicator

### P3 — DevOps

- [ ] Docker Compose (backend + frontend)
- [ ] GitHub Actions CI pipeline
- [ ] Production deployment guide (HTTPS)

---

## 14. สถิติโปรเจกต์

| รายการ | v0.1 | v2.0 |
|--------|------|------|
| **Backend modules** | 8 files | 10 files (+2) |
| **Frontend files** | 3 files | 3 files (rewritten) |
| **Database tables** | 7 tables | 10 tables (+3) |
| **API endpoints** | 8 endpoints | 16 endpoints (+8) |
| **Python dependencies** | 10 packages | 11 packages (+1) |
| **Backend code** | ~1,200 lines | ~2,100 lines |
| **Frontend code** | ~1,350 lines | ~2,000 lines |
| **Total code** | ~2,550 lines | ~4,100 lines |
| **LLM calls per chat** | 2 (select + answer) | 2 (select + answer) + profile injection |
| **LLM calls per pack create** | — | 1 (distillation) |
| **E2E tests passed** | 9/15 (60%) | 7/7 (100%) |

---

*รายงานจัดทำโดย Antigravity AI · Project KEY MVP v2.0 · 17 เมษายน 2569*
