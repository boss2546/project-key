# 📋 Project KEY — รายงานสรุปโปรเจกต์ (v0.1 → v5.4)

> **วันที่จัดทำ:** 19 เมษายน 2569  
> **อัพเดทล่าสุด:** 25 เมษายน 2569  
> **เวอร์ชันปัจจุบัน:** v5.4 — File Attachment + MCP Annotations + 24 Tools  
> **Git Tags:** `MVPV1` → `v3.0` → `v4.2`  
> **สถานะ:** ✅ Production (https://project-key.fly.dev/)  
> **จัดทำโดย:** Antigravity AI + ทีมพัฒนา  
> **Repository:** https://github.com/boss2546/project-key

---

## 1. Vision & วิวัฒนาการ

```
v0.1  → Personal Data Bank — อัปโหลด จัดเก็บ สรุป AI Chat
v2.0  → Second Brain — Profile + Context Packs + Hybrid Search
v3.0  → Knowledge Workspace — Graph Visualization + i18n
v4.0  → Production Deploy — Fly.io + MCP Connector (5 tools)
v4.1  → Full MCP — 21 tools + Data Management UX
v4.2  → Permission System — 4 categories + Admin bypass + Thai bilingual complete
v4.3  → Bugfix — Search index auto-rebuild + DB fallback + add_note fix
v5.0  → Multi-User Auth — สมัคร/ล็อกอิน/JWT + ข้อมูลแยกรายบุคคล
v5.1  → Token Security — รีเซ็ตรหัสผ่าน + Token ส่วนตัว + URL แยกผู้ใช้
v5.2  → Dual AI — Gemini 3.1 Pro/Flash + LLM Text Cleanup + File Sharing
v5.3  → Multi-Platform MCP — Antigravity bridge + import os fix + 23 tools
v5.4  → File Attachment — export_file_to_chat + MCP Annotations + 24 tools
```

---

## 2. Changelog ทุก Version

### 📦 v0.1 — Stable Foundation
> **Commit:** `41be76e` | **Tag:** `MVPV1` | **วันที่:** 15 เม.ย. 2569

| ฟีเจอร์ | รายละเอียด |
|---------|-----------|
| อัปโหลดไฟล์ | PDF, TXT, MD, DOCX (20 MB limit) |
| Text Extraction | ดึงข้อความจากทุกรูปแบบ |
| AI Organization | Clustering + Scoring + Summarization |
| AI Chat | RAG-based Q&A พร้อม Source Transparency |
| Thai Localized | UI ภาษาไทยทั้งหมด |

**สถิติ:** 8 backend modules, 7 DB tables, 8 API endpoints, ~2,550 lines

---

### 📦 v2.0 — Second Brain Chat Layer
> **Commit:** `e92ae1b` | **วันที่:** 17 เม.ย. 2569

| ฟีเจอร์ใหม่ | รายละเอียด |
|-------------|-----------|
| 👤 User Profile | ตัวตน, เป้าหมาย, สไตล์, ความชอบ |
| 📦 Context Packs | กลุ่มความรู้สกัดแล้ว (profile/study/work/project) |
| 🔍 Hybrid Search | TF-IDF + Keyword search |
| 🧠 Auto Context Injection | 5-layer injection (Profile → Packs → Files) |
| 📊 Context Injection Log | บันทึกว่า AI ใช้ข้อมูลอะไร |

**สถิติ:** 10 modules, 10 tables, 16 endpoints, ~4,100 lines

---

### 📦 v3.0 — Knowledge Workspace
> **Commit:** `8122383` | **Tag:** `v3.0` | **วันที่:** 18 เม.ย. 2569

| ฟีเจอร์ใหม่ | รายละเอียด |
|-------------|-----------|
| 🔗 Knowledge Graph | Auto-build จากไฟล์ (6 node types, 5 edge types) |
| 🌍 Graph Visualization | D3.js force-directed (zoom, pan, search, filter) |
| 🎯 Local Graph | Neighborhood view 1-3 hops |
| 🏷️ Metadata Enrichment | LLM tags, sensitivity, freshness |
| 🧠 Graph-aware AI | 7-layer injection + nodes/edges ใน response |
| 📊 Evidence Graph | Mini D3.js ใน Sources Panel |
| 🔗 Backlinks & Relations | Outgoing/incoming links + suggested relations |
| 🌐 Bilingual i18n | 120+ keys TH/EN + toggle real-time |
| 📁 Project Restructure | docs/, tests/, README.md |

**สถิติ:** 15 modules, 16 tables (+6), ~30 endpoints (+14), ~6,773 lines

---

### 📦 v4.0 — Production Deploy + MCP Connector
> **Commit:** `7ac12ce` → `ccfd514` | **วันที่:** 18 เม.ย. 2569

| ฟีเจอร์ใหม่ | รายละเอียด |
|-------------|-----------|
| 🚀 Fly.io Deployment | Production at `project-key.fly.dev` |
| 🐳 Docker | Multi-stage build, persistent volume |
| 🔌 MCP Connector | Claude Custom Connector (MCP Streamable HTTP) |
| 🔑 Bearer Token Auth | Token generation + revocation |
| 📋 MCP Logs | Tool usage tracking + debug |
| 🛠️ 5 MCP Tools | get_profile, list_files, get_file_summary, list_context_packs, search_knowledge |

**ไฟล์ใหม่:**
- `Dockerfile` — Production containerization
- `fly.toml` — Fly.io config
- `backend/mcp_tools.py` — MCP tool registry + dispatcher
- `backend/mcp_tokens.py` — Token management

---

### 📦 v4.1 — Full MCP + Data Management UX
> **Commit:** `925c0a7` → `eac9266` → `fedc9f1` | **วันที่:** 18-19 เม.ย. 2569

#### A. Data Management UX (`925c0a7`)

| ฟีเจอร์ | รายละเอียด |
|---------|-----------|
| 📄 File Detail Panel | Slide-in panel แสดงเนื้อหา + metadata ครบ |
| ✏️ Summary Editing | แก้ไข AI summary ของแต่ละไฟล์ |
| 📦 Context Pack CRUD | สร้าง/ดู/ลบ context packs จาก UI |
| 🏷️ Collection Editing | เปลี่ยนชื่อ collection, ปรับ summary |

#### B. MCP Expansion: 5 → 21 Tools

| หมวด | เครื่องมือ |
|------|-----------|
| **Read** (7) | get_profile, list_files, get_file_content, get_file_summary, list_collections, list_context_packs, get_context_pack |
| **Search** (2) | search_knowledge, explore_graph |
| **Write** (3) | create_context_pack, add_note, update_file_tags |
| **System** (1) | get_overview |
| **Admin** (8) | admin_login, delete_file, delete_pack, run_organize, build_graph, enrich_metadata, update_profile, upload_text |

#### C. Admin Mode

| ฟีเจอร์ | รายละเอียด |
|---------|-----------|
| 🔐 Admin Login | รหัสผ่าน `1234` ปลดล็อค admin tools |
| 🔓 Permission Toggles | เปิด/ปิดแต่ละ tool ผ่านหน้าเว็บ |

---

### 📦 v4.2 — Full Permission System + Bilingual Complete
> **Commit:** `75e4c6d` | **Tag:** `v4.2` | **วันที่:** 19 เม.ย. 2569

#### A. จัดหมวดใหม่ 4 กลุ่ม (ไม่มี "Admin" แยก)

| หมวด | จำนวน | เครื่องมือ |
|------|-------|-----------|
| 📖 **อ่านและค้นหา** (Read & Search) | 10 | get_profile, list_files, get_file_content, get_file_summary, list_collections, list_context_packs, get_context_pack, search_knowledge, explore_graph, get_overview |
| ✏️ **สร้างและแก้ไข** (Create & Edit) | 5 | create_context_pack, add_note, update_file_tags, upload_text, update_profile |
| 🗑️ **ลบข้อมูล** (Delete) | 2 | delete_file, delete_pack |
| ⚙️ **ประมวลผล AI** (AI Pipeline) | 4 | run_organize, build_graph, enrich_metadata, admin_login |

#### B. ระบบสิทธิ์แบบยืดหยุ่น

```
ทุก 21 tools → เปิดใช้ได้หมด (default: ON)
      ↓
ผู้ใช้ปิด toggle → Claude ใช้ tool นั้นไม่ได้
      ↓
ใส่ admin_key: "1234" → Bypass เข้าถึง tool ที่ปิดได้
```

| สถานการณ์ | ผลลัพธ์ |
|-----------|---------|
| Toggle เปิด | ✅ ใช้ได้เลย ไม่ต้องรหัส |
| Toggle ปิด | ❌ ใช้ไม่ได้ |
| Toggle ปิด + admin_key | ✅ Bypass ได้ |

**Backend:** `GET/PUT /api/mcp/permissions` + in-memory `MCP_PERMISSIONS`

#### C. ระบบ 2 ภาษาครบ 100%

| ส่วน | EN | TH |
|------|-----|------|
| หมวดหมู่ 1 | Read & Search | อ่านและค้นหา |
| หมวดหมู่ 2 | Create & Edit | สร้างและแก้ไข |
| หมวดหมู่ 3 | Delete | ลบข้อมูล |
| หมวดหมู่ 4 | AI Pipeline | ประมวลผล AI |
| Tool descriptions | ✅ 21 ตัวครบ | ✅ 21 ตัวครบ |
| Toggle toast | Enabled/Disabled | เปิดใช้งาน/ปิดใช้งาน |
| Category headers | ✅ สลับทันที | ✅ สลับทันที |

**ตัวอย่าง Thai descriptions:**
- `get_profile` → "ดูโปรไฟล์ผู้ใช้ รวมถึงตัวตน เป้าหมาย สไตล์การทำงาน และความชอบ"
- `search_knowledge` → "ค้นหาฐานความรู้แบบ Semantic + Keyword ผสม ได้ไฟล์ แพ็ก และโหนดกราฟ"
- `run_organize` → "รันไปป์ไลน์ AI แบบเต็ม: สรุป จัดกลุ่ม สร้างกราฟ"

---

## 3. Architecture (v4.2)

```
┌──────────────────────────────────────────────────────────────────────┐
│                     FRONTEND (v4.2)                                    │
│  index.html (691 lines) + app.js (1,980 lines) + styles.css (2,116)  │
│  Vanilla HTML/CSS/JS + D3.js v7 (CDN)                                │
│                                                                        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │ My Data      │ │Knowledge View│ │    Graph     │ │  AI Chat   │  │
│  │ + File Detail│ │ + 3 Tabs     │ │ + Global     │ │ + 7-Layer  │  │
│  │ + Edit       │ │ (Collections │ │ + Local      │ │   Evidence │  │
│  │ + Upload     │ │  Notes       │ │ + Detail     │ │ + Evidence │  │
│  │   Zone       │ │  Packs CRUD) │ │   Panel      │ │   Graph    │  │
│  └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│  │ MCP Setup    │ │   Tokens     │ │  MCP Logs    │  ← v4 pages     │
│  │ + Tool Toggle│ │ + Generate   │ │ + Filter     │                  │
│  │ + 4 Category │ │ + Revoke     │ │ + Debug      │                  │
│  │ + Bilingual  │ │              │ │              │                  │
│  └──────────────┘ └──────────────┘ └──────────────┘                  │
│  ┌────────────────────────────────────────────────────────────────┐   │
│  │ i18n: 170+ keys (TH/EN) | Modals | Toast | Language Toggle   │   │
│  └────────────────────────────────────────────────────────────────┘   │
└───────────────────────┬──────────────────────────────────────────────┘
                        │  HTTP REST API + MCP Streamable HTTP
┌───────────────────────▼──────────────────────────────────────────────┐
│                     BACKEND (v4.2)                                      │
│  FastAPI + Uvicorn — Python 3.10 — 17 modules                         │
│                                                                        │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐      │
│  │ main.py    │  │organizer │  │ retriever.py │  │ llm.py    │      │
│  │ 886 lines  │  │ AI pipe  │  │ 7-LAYER RAG  │  │ OpenRouter│      │
│  │ ~30+ API   │  │          │  │              │  │ wrapper   │      │
│  └────────────┘  └──────────┘  └──────────────┘  └───────────┘      │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐      │
│  │ mcp_tools  │  │mcp_tokens│  │graph_builder │  │ relations │      │
│  │ 817 lines  │  │Token CRUD│  │ Auto graph   │  │ Backlinks │      │
│  │ 21 tools   │  │          │  │ + entities   │  │ Suggest   │      │
│  │ 4 category │  │          │  │              │  │           │      │
│  └────────────┘  └──────────┘  └──────────────┘  └───────────┘      │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐                      │
│  │ profile.py │  │context_  │  │ metadata.py  │                      │
│  │ Profile    │  │packs.py  │  │ LLM enrich   │                      │
│  └────────────┘  └──────────┘  └──────────────┘                      │
│  ┌────────────────────────────────────────────────────────┐          │
│  │ Permission System: MCP_PERMISSIONS + admin_key bypass  │          │
│  └────────────────────────────────────────────────────────┘          │
└───────────────────────┬──────────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────────┐
│                     DATA LAYER                                          │
│  SQLite (persistent volume /data/) — async via aiosqlite                │
│  SQLAlchemy 2.0 ORM (Async) — 18 tables                                │
│  Filesystem: /data/uploads/ + /data/summaries/ + /data/context_packs/  │
└───────────────────────┬──────────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────────┐
│                     INFRASTRUCTURE                                      │
│  Fly.io (shared-cpu-1x, 256MB) — Auto-stop/start                      │
│  Persistent Volume: /data/ (1 GB)                                      │
│  Docker: python:3.10-slim multi-stage build (64 MB image)              │
│  Domain: https://project-key.fly.dev/                                  │
│  HTTPS: Automatic via Fly.io proxy                                     │
└───────────────────────┬──────────────────────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────────────────────┐
│                     EXTERNAL SERVICES                                   │
│  OpenRouter API → google/gemini-2.5-flash (LLM)                       │
│  Claude → MCP Streamable HTTP Connector (21 tools)                     │
│  D3.js v7 (CDN) — Force-directed Graph Visualization                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. MCP Tools — ทั้ง 21 เครื่องมือ (v4.2)

### 📖 Read & Search (10)

| Tool | คำอธิบาย |
|------|---------|
| `get_profile` | ดูโปรไฟล์ผู้ใช้ (ตัวตน เป้าหมาย สไตล์) |
| `list_files` | แสดงรายการไฟล์ทั้งหมดพร้อม metadata |
| `get_file_content` | ดูเนื้อหาข้อความของไฟล์ (max 5000 chars) |
| `get_file_summary` | ดูสรุป AI + หัวข้อ + ข้อเท็จจริง |
| `list_collections` | แสดงคอลเลกชันที่ AI จัดกลุ่ม |
| `list_context_packs` | แสดงรายการ Context Pack |
| `get_context_pack` | ดู Context Pack ตาม ID |
| `search_knowledge` | ค้นหาแบบ Semantic + Keyword ผสม |
| `explore_graph` | สำรวจ Knowledge Graph |
| `get_overview` | ดูภาพรวมระบบ (files, nodes, edges) |

### ✏️ Create & Edit (5)

| Tool | คำอธิบาย |
|------|---------|
| `create_context_pack` | สร้าง Context Pack ใหม่จากไฟล์ที่เลือก |
| `add_note` | อัพเดทสรุปของไฟล์ |
| `update_file_tags` | อัพเดทแท็กของไฟล์ |
| `upload_text` | อัพโหลดข้อความเป็นไฟล์ใหม่ |
| `update_profile` | อัพเดทโปรไฟล์ผู้ใช้ |

### 🗑️ Delete (2)

| Tool | คำอธิบาย |
|------|---------|
| `delete_file` | ลบไฟล์และข้อมูลที่เกี่ยวข้องทั้งหมด |
| `delete_pack` | ลบ Context Pack |

### ⚙️ AI Pipeline (4)

| Tool | คำอธิบาย |
|------|---------|
| `run_organize` | รันไปป์ไลน์ AI: สรุป จัดกลุ่ม สร้างกราฟ |
| `build_graph` | สร้างกราฟความรู้ใหม่ |
| `enrich_metadata` | รัน AI เสริมข้อมูลเมตา |
| `admin_login` | ยืนยันรหัสผ่านแอดมิน (bypass disabled tools) |

---

## 5. API Endpoints (v4.2) — 40+ Endpoints

### Core API (v0.1-v3.0)

| Method | Path | คำอธิบาย |
|--------|------|---------|
| `POST` | `/api/upload` | อัปโหลดไฟล์ |
| `POST` | `/api/organize` | AI pipeline |
| `GET` | `/api/files` | รายการไฟล์ |
| `DELETE` | `/api/files/{id}` | ลบไฟล์ |
| `GET` | `/api/files/{id}/content` | เนื้อหาไฟล์ |
| `GET` | `/api/clusters` | รายการ clusters |
| `PUT` | `/api/clusters/{id}` | แก้ไข cluster |
| `GET` | `/api/summary/{id}` | Summary ต่อไฟล์ |
| `PUT` | `/api/summary/{id}` | แก้ไข summary |
| `POST` | `/api/chat` | AI Chat |
| `GET` | `/api/stats` | สถิติภาพรวม |
| `GET/PUT` | `/api/profile` | Profile CRUD |
| `GET/POST/DELETE` | `/api/context-packs` | Pack CRUD |
| `POST` | `/api/context-packs/{id}/regenerate` | Regenerate Pack |

### Graph API (v3.0)

| Method | Path | คำอธิบาย |
|--------|------|---------|
| `POST` | `/api/graph/build` | สร้าง Knowledge Graph |
| `GET` | `/api/graph/global` | Global graph data |
| `GET` | `/api/graph/nodes` | รายการ nodes |
| `GET` | `/api/graph/nodes/{id}` | Node detail + relations |
| `GET` | `/api/graph/neighborhood/{id}` | N-hop neighborhood |
| `GET` | `/api/graph/edges` | รายการ edges |
| `GET` | `/api/relations/backlinks/{id}` | Backlinks |
| `GET` | `/api/relations/outgoing/{id}` | Outgoing links |
| `GET/POST` | `/api/suggestions` | Suggested relations |
| `GET/PUT` | `/api/metadata/{file_id}` | Metadata CRUD |
| `POST` | `/api/metadata/enrich` | LLM metadata enrichment |

### MCP API (v4.0-v4.2)

| Method | Path | คำอธิบาย |
|--------|------|---------|
| `GET` | `/api/mcp/info` | MCP server info + 21 tools |
| `POST` | `/api/mcp/tokens` | Generate Bearer token |
| `GET` | `/api/mcp/tokens` | List tokens |
| `DELETE` | `/api/mcp/tokens/{id}` | Revoke token |
| `POST` | `/api/mcp/test` | Test connection |
| `GET` | `/api/mcp/logs` | Tool usage logs |
| `GET` | `/api/mcp/permissions` | Get tool permissions |
| `PUT` | `/api/mcp/permissions` | Update tool permissions |
| `POST` | `/mcp/{secret}` | **MCP Streamable HTTP** (JSON-RPC 2.0) |

---

## 6. Database Schema (v4.2) — 18 ตาราง

```
users              → id, name, created_at
files              → id, user_id, filename, filetype, raw_path,
                     uploaded_at, extracted_text, processing_status,
                     tags (JSON), aliases (JSON), sensitivity,
                     freshness, source_of_truth, version
clusters           → id, user_id, title, summary, created_at
file_cluster_map   → file_id, cluster_id, relevance_score
file_insights      → file_id, importance_score, importance_label,
                     is_primary_candidate, why_important
file_summaries     → file_id, md_path, summary_text,
                     key_topics (JSON), key_facts (JSON),
                     why_important, suggested_usage
chat_queries       → id, user_id, question, answer, ...
user_profiles      → user_id, identity_summary, goals, ...
context_packs      → id, user_id, type, title, summary_text, ...
context_injection_logs → id, chat_query_id, ..., node_ids_used, edge_ids_used
graph_nodes        → id, user_id, object_type, object_id, label, ...
graph_edges        → id, user_id, source_node_id, target_node_id, edge_type, ...
note_objects       → id, user_id, title, content, tags, ...
suggested_relations → id, user_id, source_node_id, target_node_id, ...
graph_lenses       → id, user_id, name, type, filter_json, ...
canvas_objects     → id, user_id, canvas_name, ...
mcp_tokens         → id, user_id, label, token_hash, is_active, ...
mcp_logs           → id, user_id, tool_name, caller, arguments, status, ...
```

---

## 7. โครงสร้างไฟล์โปรเจกต์ (v4.2)

```
Project KEY/
├── .env                         # 🔒 API key (ไม่ commit)
├── .gitignore
├── Dockerfile                   # 🆕 v4 — Production container
├── fly.toml                     # 🆕 v4 — Fly.io config
├── README.md
├── index.html                   # 691 lines — 7 pages + modals + i18n
├── app.js                       # 1,980 lines — D3.js + i18n 170+ keys
├── styles.css                   # 2,116 lines — Dark theme + graph + toggle
├── requirements.txt             # Python dependencies (12 packages)
│
├── backend/                     # ⚙️ 17 Python modules
│   ├── __init__.py
│   ├── main.py                  # 886 lines — 40+ API endpoints + MCP handler
│   ├── mcp_tools.py             # 817 lines — 21 tools registry + dispatcher
│   ├── mcp_tokens.py            # 106 lines — Token management
│   ├── graph_builder.py         # 490 lines — Auto graph + entity extraction
│   ├── retriever.py             # 378 lines — 7-layer graph-aware RAG
│   ├── vector_search.py         # 233 lines — Hybrid search
│   ├── database.py              # 251 lines — 18 ORM models
│   ├── organizer.py             # 238 lines — AI clustering + scoring
│   ├── context_packs.py         # 224 lines — Pack CRUD + generation
│   ├── relations.py             # 196 lines — Backlinks + suggestions
│   ├── metadata.py              # 129 lines — LLM metadata enrichment
│   ├── extraction.py            # 110 lines — Text extraction
│   ├── markdown_store.py        # 110 lines — Summary file I/O
│   ├── profile.py               # 86 lines — User profile CRUD
│   ├── llm.py                   # 69 lines — OpenRouter wrapper
│   └── config.py                # 36 lines — Environment config
│
├── docs/                        # 📚 เอกสารโปรเจกต์
│   ├── PROJECT_REPORT.md        # ← ไฟล์นี้
│   ├── prd/                     # PRD ทุก version
│   ├── guides/                  # User Guides
│   └── screenshots/             # UI screenshots
│
├── tests/                       # 🧪 ชุดทดสอบ
│   ├── e2e/                     # End-to-end tests
│   ├── testsprite/              # TestSprite 29 TCs
│   └── fixtures/                # Test data
│
└── Project_KEY_PRD_MVP_v4.md    # PRD v4 — MCP Connector
```

---

## 8. สถิติโปรเจกต์ — เปรียบเทียบทุก Version

| รายการ | v0.1 | v2.0 | v3.0 | v4.0 | v4.2 |
|--------|------|------|------|------|------|
| **Backend modules** | 8 | 10 | 15 | 17 | **17** |
| **Frontend files** | 3 | 3 | 3 | 3 | **3** |
| **Database tables** | 7 | 10 | 16 | 18 | **18** |
| **API endpoints** | 8 | 16 | ~30 | ~35 | **40+** |
| **Backend code** | ~1,200 | ~2,100 | ~3,660 | ~4,200 | **~4,360 lines** |
| **Frontend code** | ~1,350 | ~2,000 | ~3,113 | ~4,200 | **~4,787 lines** |
| **Total code** | ~2,550 | ~4,100 | ~6,773 | ~8,400 | **~9,147 lines** |
| **MCP Tools** | — | — | — | 5 | **21** |
| **i18n keys** | — | — | 120+ | 130+ | **170+** |
| **Languages** | TH | TH | TH+EN | TH+EN | **TH+EN** |
| **Graph nodes** | — | — | 33 | 38 | **38** |
| **Graph edges** | — | — | 56 | 62 | **62** |
| **Git tags** | MVPV1 | — | v3.0 | — | **v4.2** |
| **Deployment** | Local | Local | Local | **Fly.io** | **Fly.io** |

### สถิติไฟล์ (v4.2)

| ไฟล์ | บรรทัด | หน้าที่ |
|------|--------|--------|
| `styles.css` | 2,116 | Dark theme + graph + toggle switches + animations |
| `app.js` | 1,980 | D3.js graph + i18n 170+ keys + MCP UI + chat |
| `main.py` | 886 | 40+ API endpoints + MCP Streamable HTTP |
| `mcp_tools.py` | 817 | 21 tools registry + dispatcher + admin system |
| `index.html` | 691 | 7 pages + modals + data-i18n attributes |
| `graph_builder.py` | 490 | Auto graph construction + LLM entity extraction |
| `retriever.py` | 378 | 7-layer graph-aware RAG retrieval |

---

## 9. Deployment & Infrastructure

### Production URL
```
https://project-key.fly.dev/
```

### Docker Image
```dockerfile
FROM python:3.10-slim
# Multi-stage build → 64 MB image
# Persistent volume: /data/ (DB, uploads, summaries)
```

### Fly.io Config
```toml
app = "project-key"
primary_region = "sin"  # Singapore
[http_service]
  internal_port = 8000
  auto_stop_machines = "stop"
  auto_start_machines = true
  min_machines_running = 0
[[vm]]
  memory = "256mb"
  cpu_kind = "shared"
  cpus = 1
[mounts]
  source = "projectkey_data"
  destination = "/data"
```

### MCP Connector Setup
```json
{
  "mcpServers": {
    "project-key": {
      "type": "streamable-http",
      "url": "https://project-key.fly.dev/mcp/{SECRET_KEY}"
    }
  }
}
```

---

## 10. Version History

| Version | Tag | Commit | วันที่ | สรุป |
|---------|-----|--------|-------|------|
| v0.1 | `MVPV1` | `41be76e` | 15 เม.ย. 69 | Stable Foundation — Upload, Organize, AI Chat |
| v2.0 | — | `e92ae1b` | 17 เม.ย. 69 | Second Brain — Profile, Packs, Hybrid Search |
| v3.0 | `v3.0` | `8122383` | 18 เม.ย. 69 | Knowledge Workspace — Graph, i18n, Restructure |
| v4.0 | — | `7ac12ce` | 18 เม.ย. 69 | Production Deploy — Fly.io + MCP 5 tools |
| v4.1 | — | `fedc9f1` | 19 เม.ย. 69 | Full MCP — 21 tools + Data Management UX |
| v4.2 | `v4.2` | `75e4c6d` | 19 เม.ย. 69 | Permission System — 4 categories + Admin + Thai |

---

## 11. สิ่งที่ทำเพิ่มเหนือจากแผน (Beyond the Plan) 🌟

| หมวด | รายละเอียด |
|------|-----------|
| 🌐 Bilingual i18n | 170+ translation keys ครอบคลุม TH + EN ทุก tool description |
| 📁 Project Restructure | docs/, tests/, README.md ตามมาตรฐาน |
| 🔌 MCP Connector | 21 tools ให้ Claude เข้าถึงข้อมูลทั้งหมด |
| 🔐 Permission System | UI toggles + admin key bypass |
| 🐳 Docker + Fly.io | Production deployment 64 MB image |
| 📄 File Detail Panel | Slide-in panel + edit summaries + tags |
| 📦 Context Pack CRUD | สร้าง/ดู/ลบ packs จาก UI |
| 🏷️ Collection Editing | เปลี่ยนชื่อ + ปรับ summary |
| 🧪 TestSprite 29 TCs | Automated E2E testing |
| 📋 MCP Logs | Tool usage tracking + debug |

---

### 📦 v4.3 — Bugfix: Search + add_note + Metadata
> **Commit:** `5929134` | **วันที่:** 19 เม.ย. 2569

**ปัญหาจากรายงานทดสอบ MCP (Claude Sonnet 4.6 ทดสอบ 21 ฟังก์ชัน):**

| Bug | Root Cause | Fix |
|-----|-----------|-----|
| `search_knowledge` ผลลัพธ์ว่างเปล่า | TF-IDF index อยู่ใน RAM หายตอน Fly.io restart | ✅ Startup auto-rebuild จาก DB + DB fallback search |
| `enrich_metadata` enriched=0 ไม่บอกเหตุผล | Response ไม่มี context | ✅ เพิ่ม total_files + message อธิบายเหตุผล |
| `add_note` ต้อง organize ก่อน | ไม่มี FileSummary record | ✅ Auto-create summary record ถ้ายังไม่มี |

**ผลลัพธ์:** 21/21 ฟังก์ชัน ✅ PASS ครบหมด

---

### 📦 v5.0 — Multi-User Auth
> **วันที่:** 20 เม.ย. 2569

| ฟีเจอร์ใหม่ | รายละเอียด |
|-------------|-----------|
| 🔐 สมัครสมาชิก/ล็อกอิน | Email + Password (bcrypt hash) |
| 🪙 JWT Authentication | Bearer token + refresh token |
| 👥 ข้อมูลแยกรายบุคคล | ทุกไฟล์, กราฟ, แชท, profile แยก user_id |
| 🏠 Landing Page | หน้าแรกแนะนำระบบ + ปุ่ม sign up/login |
| 🧩 Onboarding Quiz | ตั้งค่าโปรไฟล์ตอนสมัครครั้งแรก |

**ไฟล์ใหม่:** `backend/auth.py` — JWT + bcrypt auth system

---

### 📦 v5.1 — Token Security
> **วันที่:** 21 เม.ย. 2569

| ฟีเจอร์ใหม่ | รายละเอียด |
|-------------|-----------|
| 🔄 รีเซ็ตรหัสผ่าน | Self-service password reset |
| 🔑 MCP Token ส่วนตัว | Token แยกรายผู้ใช้ (ไม่ใช่ shared) |
| 🌐 MCP URL แยกผู้ใช้ | `/mcp/{user_secret}` — secret key เฉพาะคน |

---

### 📦 v5.2 — Dual AI + File Sharing
> **วันที่:** 22-23 เม.ย. 2569

| ฟีเจอร์ใหม่ | รายละเอียด |
|-------------|-----------|
| 🤖 Dual AI Model | Gemini 3.1 Pro (จัดการข้อมูล) + Gemini 3 Flash (แชท) |
| 🧹 LLM Text Cleanup | แก้ข้อความ PDF ที่เพี้ยนด้วย AI แทน regex |
| 📎 File Sharing Link | `get_file_link` → ลิงก์ดาวน์โหลดชั่วคราว 30 นาที |
| 📄 Paginated Content | `get_file_content(offset, limit)` — อ่านไฟล์ใหญ่ได้ |
| 🔄 Reprocess File | `reprocess_file` — แปลงไฟล์ใหม่ด้วย OCR + LLM fix |
| 📊 MCP 22 → 23 tools | เพิ่ม get_file_link, get_file_content(v2), reprocess_file |

**ไฟล์ใหม่:** `backend/shared_links.py` — Signed temp download URLs

---

### 📦 v5.3 — Multi-Platform MCP + Bug Fixes
> **Commit:** `e18aac2` | **วันที่:** 25 เม.ย. 2569

| ฟีเจอร์/แก้ไข | รายละเอียด |
|---------------|-----------|
| 🔧 แก้บัค `import os` | `mcp_tools.py` ขาด `import os` ทำให้ list_files, get_file_link, get_file_content ล้ม |
| 🆕 Antigravity MCP Tab | หน้า MCP Setup มี 2 tab: Claude Desktop + Antigravity |
| 🌉 mcp-remote Bridge | config สำหรับ Antigravity ใช้ `npx -y mcp-remote@latest` เป็น stdio ↔ HTTP bridge |
| 📊 MCP 23 เครื่องมือ | อัปเดตจำนวนทั้ง frontend + backend + README |
| 🏗️ Project Cleanup | อัปเดต README v5.3, โครงสร้างไฟล์, line counts ทุกส่วน |

---

### 📦 v5.4 — File Attachment + MCP Tool Annotations
> **Commit:** `898ab55` | **วันที่:** 25 เม.ย. 2569

| ฟีเจอร์ใหม่ | รายละเอียด |
|-------------|----------|
| 📎 `export_file_to_chat` | ส่งไฟล์ต้นฉบับกลับแชทเป็น MCP EmbeddedResource (base64 blob) + fallback signed URL 30 นาที |
| 🏷️ MCP Tool Annotations | ทุก tool มี `readOnlyHint`, `destructiveHint`, `idempotentHint` บอก AI client ว่าต้องขออนุญาตหรือไม่ |
| ✅ 17 tools auto-approve | Read/Search/Export/Pipeline ทำได้เลยไม่ต้องถาม |
| ⚠️ 5 tools confirm | Edit/Write ต้องยืนยันก่อน |
| ⛔ 2 tools destructive | Delete ต้องยืนยันเข้มงวด |
| 📊 MCP 24 เครื่องมือ | เพิ่ม export_file_to_chat |
| 🚀 Server v5.4.0 | อัปเดท MCP server version |

**นโยบายสิทธิ์ v5.4:**
- อ่าน/ค้นหา/Export/Pipeline → **ทำได้เลยไม่ต้องถาม**
- แก้ไข/เขียน/เพิ่มข้อมูล → **ต้องยืนยันก่อน**
- ลบไฟล์/ลบ Pack → **ต้องยืนยันเข้มงวด**

---

## 12. ข้อจำกัดที่ยังมี (Known Limitations) — อัปเดต v5.4

| # | ข้อจำกัด | ความเสี่ยง | แนวทาง |
|---|---------|-----------|--------|
| 1 | ~~ไม่มีระบบ Auth — DEFAULT_USER_ID~~ | ~~High~~ | ✅ **แก้แล้ว v5.0** — JWT + bcrypt Multi-User |
| 2 | ~~Vector index ใน RAM — restart rebuild~~ | ~~Medium~~ | ✅ **แก้แล้ว v4.3** — startup auto-rebuild |
| 3 | Graph rebuild = ล้างทั้งหมด | Medium | Incremental update |
| 4 | ~~Admin password hardcoded~~ | ~~Medium~~ | ✅ **แก้แล้ว v5.0** — Per-user MCP secret |
| 5 | Permissions ใน memory (reset on restart) | Low | Persist to DB |
| 6 | Canvas Beta ยังไม่ implement | Low | v6 |
| 7 | Antigravity ต้องใช้ mcp-remote bridge | Low | รอ native remote MCP support |

---

## 13. สถิติโปรเจกต์ — เปรียบเทียบทุก Version (อัปเดต v5.4)

| รายการ | v0.1 | v2.0 | v3.0 | v4.2 | **v5.4** |
|--------|------|------|------|------|----------|
| **Backend modules** | 8 | 10 | 15 | 17 | **19** |
| **Frontend files** | 3 | 3 | 3 | 3 | **3** |
| **Database tables** | 7 | 10 | 16 | 18 | **18** |
| **API endpoints** | 8 | 16 | ~30 | 40+ | **40+** |
| **Backend code** | ~1,200 | ~2,100 | ~3,660 | ~4,360 | **~5,500 lines** |
| **Frontend code** | ~1,350 | ~2,000 | ~3,113 | ~4,787 | **~7,008 lines** |
| **Total code** | ~2,550 | ~4,100 | ~6,773 | ~9,147 | **~12,508 lines** |
| **MCP Tools** | — | — | — | 21 | **24** |
| **i18n keys** | — | — | 120+ | 170+ | **170+** |
| **Auth** | — | — | — | — | **JWT + bcrypt** |
| **AI Models** | 1 | 1 | 1 | 1 | **2 (Pro + Flash)** |
| **Deployment** | Local | Local | Local | Fly.io | **Fly.io** |
| **MCP Platforms** | — | — | — | Claude | **Claude + Antigravity** |

---

## 14. Version History

| Version | Tag | วันที่ | สรุป |
|---------|-----|-------|------|
| v0.1 | `MVPV1` | 15 เม.ย. 69 | Stable Foundation — Upload, Organize, AI Chat |
| v2.0 | — | 17 เม.ย. 69 | Second Brain — Profile, Packs, Hybrid Search |
| v3.0 | `v3.0` | 18 เม.ย. 69 | Knowledge Workspace — Graph, i18n, Restructure |
| v4.0 | — | 18 เม.ย. 69 | Production Deploy — Fly.io + MCP 5 tools |
| v4.1 | — | 19 เม.ย. 69 | Full MCP — 21 tools + Data Management UX |
| v4.2 | `v4.2` | 19 เม.ย. 69 | Permission System — 4 categories + Admin + Thai |
| v4.3 | — | 19 เม.ย. 69 | Bugfix — Search rebuild + add_note fix |
| v5.0 | — | 20 เม.ย. 69 | Multi-User Auth — JWT + bcrypt + Per-user data |
| v5.1 | — | 21 เม.ย. 69 | Token Security — Password reset + Per-user MCP URL |
| v5.2 | — | 22-23 เม.ย. 69 | Dual AI + LLM Cleanup + File Sharing + 22 tools |
| **v5.3** | — | **25 เม.ย. 69** | **Multi-Platform MCP + Antigravity bridge + 23 tools** |
| **v5.4** | — | **25 เม.ย. 69** | **export_file_to_chat + MCP Annotations + 24 tools** |

---

## 15. วิธีรัน

### Local Development
```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Setup .env
echo OPENROUTER_API_KEY=sk-or-v1-xxxx > .env

# 3. Start server
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000

# 4. Open browser
# http://localhost:8000
```

### Production (Fly.io)
```bash
# Deploy
flyctl deploy --remote-only

# Logs
flyctl logs

# SSH
flyctl ssh console
```

### เชื่อมต่อ MCP (Claude Desktop)
```json
{
  "mcpServers": {
    "project-key": {
      "url": "https://project-key.fly.dev/mcp/{YOUR_SECRET_KEY}"
    }
  }
}
```

### เชื่อมต่อ MCP (Antigravity — ใช้ mcp-remote bridge)
```json
{
  "mcpServers": {
    "project-key": {
      "command": "npx",
      "args": ["-y", "mcp-remote@latest", "https://project-key.fly.dev/mcp/{YOUR_SECRET_KEY}"]
    }
  }
}
```

---

*รายงานจัดทำโดย Antigravity AI · Project KEY v5.4 · 25 เมษายน 2569*
