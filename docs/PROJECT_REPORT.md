# 📋 Project KEY — รายงานสรุป MVP v3.0 (Final)

> **วันที่จัดทำ:** 18 เมษายน 2569  
> **อัพเดทล่าสุด:** 18 เมษายน 2569 (13:25 น.)  
> **เวอร์ชัน:** MVP v3.0 (Knowledge Workspace) — **Final Release**  
> **Git Tag:** `v3.0` | **Commit:** `8122383`  
> **เวอร์ชันก่อนหน้า:** MVP v2.0 (Second Brain Chat Layer) → MVP v0.1 (Stable Foundation)  
> **สถานะ:** ✅ Production-ready (single-user, local deployment)  
> **จัดทำโดย:** Antigravity AI + ทีมพัฒนา  
> **Repository:** https://github.com/boss2546/project-key

---

## 1. Vision & เป้าหมายโปรเจกต์

> **v0.1: "พื้นที่ข้อมูลส่วนตัว — ปลอดภัย เป็นระบบ เรียกค้นได้ทันที"**  
> **v2.0: "Second Brain — AI ที่เข้าใจตัวคุณ เข้าใจบริบท และตอบได้อย่างต่อเนื่อง"**  
> **v3.0: "Knowledge Workspace — เห็นความเชื่อมโยง สำรวจด้วยกราฟ AI ตอบอย่างมีหลักฐาน"**

### วิวัฒนาการของระบบ

```
v0.1: Store → Organize → Summarize → AI Chat (file-level)
v2.0: Store → Organize → Summarize → Profile + Context Packs → Auto Inject → AI Chat (multi-layer)
v3.0: Store → Organize → Summarize → Profile + Packs → Metadata Enrich → Graph Build
      → Graph Explore → Relations → Graph-aware AI Chat (7-layer, evidence-backed)
```

### สิ่งที่เปลี่ยนจาก v2.0 → v3.0

| ด้าน | v2.0 | v3.0 |
|------|------|------|
| **โครงสร้างข้อมูล** | ไฟล์ + Clusters (flat) | Knowledge Graph (nodes + typed edges) |
| **Metadata** | filename, type, importance เท่านั้น | + tags, aliases, sensitivity, freshness, source_of_truth |
| **ความเชื่อมโยง** | ไม่มี — ดูได้ทีละ cluster | Backlinks, outgoing links, suggested relations |
| **การสำรวจ** | รายการไฟล์ + clusters | Global/Local Graph Visualization (D3.js) |
| **AI Context** | Profile + Packs + Files (5 layers) | + Graph Nodes + Graph Edges (7 layers) |
| **ความโปร่งใส** | แสดง 4 layers + reasoning | + Nodes Used + Relations Used + Evidence Graph |
| **UI** | 3 หน้า (My Data, Collections, AI Chat) | 4 หน้า (My Data, Knowledge View, Graph, AI Chat) |
| **Visualization** | ไม่มี | D3.js Force-directed Graph (zoom, pan, search, filter) |
| **Node Types** | — | 6 ประเภท: File, Entity, Tag, Collection, Pack, Person |

---

## 2. สรุประบบ Functional Requirements

### Requirements เดิม (v0.1 + v2.0) — ยังคงทำงานครบ

| รหัส | Requirement | สถานะ |
|------|-------------|--------|
| FR-1 | อัปโหลดไฟล์ (PDF, TXT, MD, DOCX) | ✅ ครบ + file size validation |
| FR-2 | เก็บ metadata และ extracted text | ✅ ครบ |
| FR-3 | ดึงข้อความจากไฟล์ (extraction) | ✅ ครบ |
| FR-4 | แสดงรายการไฟล์พร้อม metadata | ✅ ครบ — **+ metadata badges v3** |
| FR-5 | จัดกลุ่มไฟล์ด้วย AI (clustering) | ✅ ครบ |
| FR-6 | ให้คะแนนความสำคัญ (importance scoring) | ✅ ครบ |
| FR-7 | ระบุ Primary Candidate | ✅ ครบ |
| FR-8 | สร้าง Markdown summary ต่อไฟล์ | ✅ ครบ |
| FR-9 | AI Chat พร้อม Retrieval | ✅ ครบ — **Graph-aware Injection v3** |
| FR-10 | แสดง Source Transparency | ✅ ครบ — **6-layer transparency panel + Evidence Graph** |
| FR-11 | Privacy (single-user isolation) | ⚠️ `DEFAULT_USER_ID` (no auth) |
| FR-12 | 👤 User Profile | ✅ ครบ |
| FR-13 | 📦 Context Packs | ✅ ครบ |
| FR-14 | 🔍 Hybrid Search | ✅ ครบ |
| FR-15 | 🧠 Auto Context Injection | ✅ ครบ — **v3: 7-layer injection** |
| FR-16 | 📊 Context Injection Log | ✅ ครบ — **+ node_ids_used, edge IDs** |
| FR-17 | 🔒 API Key Security (.env) | ✅ ครบ |
| FR-18 | 📏 File Size Validation (20 MB) | ✅ ครบ |

### Requirements ใหม่ (v3.0) 🆕

| รหัส | Requirement | สถานะ |
|------|-------------|--------|
| FR-19 | 🏷️ Metadata Expansion — tags, aliases, sensitivity, freshness, source_of_truth | ✅ ครบ — LLM enrichment + manual edit |
| FR-20 | 🔗 Knowledge Graph — auto-build nodes + typed edges จากไฟล์ | ✅ ครบ — 6 node types, 5+ edge types |
| FR-21 | 🔍 Entity Extraction — ดึง entities จาก summaries ด้วย LLM | ✅ ครบ — ดึง entity nodes อัตโนมัติ |
| FR-22 | 📡 Backlinks & Outgoing Links — ดูความสัมพันธ์ทุกทิศทาง | ✅ ครบ |
| FR-23 | 💡 Suggested Relations — ระบบแนะนำลิงก์ใหม่ + accept/dismiss | ✅ ครบ — heuristic-based |
| FR-24 | 🌍 Global Graph Visualization — D3.js force-directed ภาพรวม | ✅ ครบ — zoom, pan, search, filters |
| FR-25 | 🎯 Local Graph — neighborhood view รอบ node ที่เลือก | ✅ ครบ — depth slider 1-3 hops |
| FR-26 | 📋 Detail Panel — แสดงข้อมูล node + summary + relations | ✅ ครบ — slide-in panel |
| FR-27 | 🧠 Graph-aware AI — inject graph nodes/edges ในบริบท AI | ✅ ครบ — nodes_used + edges_used ใน response |
| FR-28 | 📊 Evidence Graph — mini graph ใน sources panel | ✅ ครบ — D3.js mini visualization |
| FR-29 | 🔗 Graph Lenses API — save/recall graph filter presets | ✅ ครบ (API ready) |
| FR-30 | 🪄 Auto Graph Build — สร้างกราฟอัตโนมัติเมื่อ organize | ✅ ครบ — trigger หลัง organize |
| FR-31 | 🌐 Bilingual i18n — ระบบ 2 ภาษา (ไทย/อังกฤษ) | ✅ ครบ — **120+ keys, localStorage, toggle** |
| FR-32 | 🔄 Language Toggle — ปุ่มสลับภาษาแบบ real-time | ✅ ครบ — Globe icon + TH\|EN pill design |

---

## 3. Architecture & Tech Stack (v3.0)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (v3.0)                               │
│   index.html + app.js + styles.css + D3.js v7 (CDN)                 │
│   Vanilla HTML / CSS / JavaScript + D3.js Force Simulation           │
│                                                                       │
│   ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌────────────┐│
│   │ My Data      │ │Knowledge View│ │ Graph        │ │ AI Chat    ││
│   │ + Metadata   │ │ + 3 Tabs     │ │ + Global     │ │ + 7-Layer  ││
│   │   Badges     │ │ (Collections │ │ + Local      │ │   Evidence ││
│   │ + Enrich     │ │  Notes       │ │ + Detail     │ │ + Evidence ││
│   │   Button     │ │  Packs)      │ │   Panel      │ │   Graph    ││
│   └──────────────┘ └──────────────┘ └──────────────┘ └────────────┘│
│   ┌──────────────────────────────────────────────────────────────┐  │
│   │ Modals: Profile + Confirm | Toast Notifications              │  │
│   └──────────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────────────┘
                       │  HTTP REST API (fetch)
┌──────────────────────▼──────────────────────────────────────────────┐
│                        BACKEND (v3.0)                                 │
│   FastAPI v0.115.6 + Uvicorn v0.34.0                                 │
│   Python 3.10 — 14 modules, ~30 API endpoints                        │
│                                                                       │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐     │
│  │ main.py    │  │organizer │  │ retriever.py │  │ llm.py    │     │
│  │ ~30 API    │  │ (AI pipe)│  │ (7-LAYER     │  │ OpenRouter│     │
│  │ endpoints  │  │          │  │  INJECTION)  │  │ wrapper   │     │
│  └────────────┘  └──────────┘  └──────────────┘  └───────────┘     │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐  ┌───────────┐     │
│  │ profile.py │  │context_  │  │vector_search │  │extraction │     │
│  │ User       │  │packs.py  │  │ Hybrid Mode  │  │ (text)    │     │
│  │ Profile    │  │ Context  │  │              │  │           │     │
│  └────────────┘  └──────────┘  └──────────────┘  └───────────┘     │
│  ┌────────────┐  ┌──────────┐  ┌──────────────┐                     │
│  │graph_      │  │relations │  │ metadata.py  │   ← 🆕 v3 modules │
│  │builder.py  │  │.py       │  │ LLM enrich   │                     │
│  │ 🆕 Auto    │  │ 🆕 Back/ │  │ 🆕 Tags,     │                     │
│  │ graph      │  │ Outgoing/│  │ Sensitivity  │                     │
│  │ construct  │  │ Suggest  │  │ Freshness    │                     │
│  └────────────┘  └──────────┘  └──────────────┘                     │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────────┐
│                        DATA LAYER (v3.0)                              │
│  SQLite (projectkey.db) — async via aiosqlite                        │
│  SQLAlchemy 2.0 ORM (Async) — 16 tables (+6 ใหม่)                   │
│  Filesystem: uploads/ + summaries/ + context_packs/                  │
│  .env — API key storage (python-dotenv)                              │
└──────────────────────┬──────────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────────┐
│                     EXTERNAL DEPENDENCIES                             │
│  OpenRouter API → google/gemini-2.5-flash (LLM)                     │
│  D3.js v7 (CDN) — Force-directed Graph Visualization                 │
│  (Clustering, Scoring, Summary, Entity Extraction,                   │
│   Metadata Enrich, Pack Gen, Graph-aware Chat)                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. โครงสร้างไฟล์โปรเจกต์ (v3.0 Final)

```
Project KEY/
├── .env                        # 🔒 API key (ไม่ commit)
├── .gitignore                  # ป้องกัน .env, DB, uploads, node_modules
├── README.md                   # 🆕 Project overview + quick start
├── index.html                  # 🔀 UI หลัก (4 หน้า + 2 modals + i18n)
├── app.js                      # 🔀 Frontend logic (v3 — 1,283 lines + D3.js + i18n)
├── styles.css                  # 🔀 Design system (v3 — 1,387 lines)
├── requirements.txt            # Python dependencies (11 packages)
├── projectkey.db               # SQLite database (16 tables) — gitignored
│
├── backend/                    # ⚙️ FastAPI backend (15 modules)
│   ├── __init__.py
│   ├── main.py                 # FastAPI app — ~30 API endpoints
│   ├── database.py             # SQLAlchemy models — 16 tables
│   ├── config.py               # Configuration — dotenv + paths
│   ├── profile.py              # User Profile service
│   ├── context_packs.py        # Context Pack service
│   ├── retriever.py            # 7-layer graph-aware injection
│   ├── graph_builder.py        # 🆕 Auto graph construction + entity extraction
│   ├── relations.py            # 🆕 Backlinks, outgoing, suggestions
│   ├── metadata.py             # 🆕 LLM metadata enrichment
│   ├── vector_search.py        # Hybrid search (TF-IDF + keyword)
│   ├── organizer.py            # AI clustering + scoring + summarization
│   ├── extraction.py           # Text extraction (PDF/TXT/MD/DOCX)
│   ├── markdown_store.py       # บันทึก/อ่าน .md summary files
│   └── llm.py                  # OpenRouter API wrapper
│
├── docs/                       # 📚 เอกสารโปรเจกต์ (จัดระเบียบแล้ว)
│   ├── PROJECT_REPORT.md       # ← ไฟล์นี้
│   ├── prd/                    # PRD ทุก version (v1, v2, v3)
│   ├── guides/                 # User Guide v3
│   └── screenshots/            # UI screenshots (8 ภาพ)
│
├── tests/                      # 🧪 ชุดทดสอบทั้งหมด
│   ├── e2e/                    # End-to-end tests (2 files)
│   ├── testsprite/             # TestSprite automated tests (29 TC)
│   └── fixtures/               # Test data files (8 files)
│
├── uploads/                    # ไฟล์ดิบที่อัปโหลด (gitignored)
├── summaries/                  # Markdown summaries ต่อไฟล์ (gitignored)
└── chroma_db/                  # Vector store (gitignored)
```

---

## 5. Database Schema (v3.0) — 16 ตาราง

### ตารางเดิม (v0.1 + v2.0) — ยังคงใช้งาน

```
users              → id, name, created_at
files              → id, user_id, filename, filetype, raw_path,
                     uploaded_at, extracted_text, processing_status,
                     tags (JSON), aliases (JSON), sensitivity,     ← 🆕 v3 columns
                     freshness, source_of_truth, version            ← 🆕 v3 columns
clusters           → id, user_id, title, summary, created_at
file_cluster_map   → file_id, cluster_id, relevance_score
file_insights      → file_id, importance_score, importance_label,
                     is_primary_candidate, why_important
file_summaries     → file_id, md_path, summary_text,
                     key_topics (JSON), key_facts (JSON),
                     why_important, suggested_usage
chat_queries       → id, user_id, question, answer,
                     selected_cluster_ids, selected_file_ids,
                     retrieval_modes, reasoning, created_at
user_profiles      → user_id (FK), identity_summary, goals,
                     working_style, preferred_output_style,
                     background_context, updated_at
context_packs      → id, user_id, type, title, summary_text, md_path,
                     source_file_ids (JSON), source_cluster_ids (JSON)
context_injection_logs → id, chat_query_id (FK), profile_used, context_pack_ids,
                         file_ids, cluster_ids, injection_summary, retrieval_reason,
                         node_ids_used (JSON), edge_ids_used (JSON)   ← 🆕 v3 columns
```

### ตารางใหม่ (v3.0) — 6 ตาราง 🆕

```
graph_nodes        → id, user_id, object_type (source_file/entity/tag/cluster/pack/person),
                     object_id, label, description, node_family,
                     importance_score (0.0-1.0), freshness_score (0.0-1.0),
                     metadata_json, created_at, updated_at

graph_edges        → id, user_id, source_node_id (FK), target_node_id (FK),
                     edge_type (contains/mentions/has_tag/semantically_related/derived_from),
                     weight (0.0-1.0), confidence (0.0-1.0),
                     evidence_text, created_by (auto/user/llm), created_at

note_objects       → id, user_id, title, content, tags (JSON), linked_file_ids (JSON),
                     created_at, updated_at

suggested_relations → id, user_id, source_node_id (FK), target_node_id (FK),
                      suggested_type, confidence, reason, status (pending/accepted/dismissed),
                      created_at

graph_lenses       → id, user_id, name, type, filter_json, layout_json, created_at

canvas_objects     → id, user_id, canvas_name, object_type, ref_id,
                     position_x, position_y, width, height, style_json, created_at
```

### ความสัมพันธ์ (v3.0)

```
User ← 1:1 → UserProfile
User ← 1:N → File ← 1:1 → FileInsight
                   ← 1:1 → FileSummary
                   ← N:M → Cluster (via FileClusterMap)
User ← 1:N → ContextPack
User ← 1:N → GraphNode ← N:M → GraphNode (via GraphEdge)
User ← 1:N → NoteObject
User ← 1:N → SuggestedRelation
User ← 1:N → GraphLens
ChatQuery ← 1:1 → ContextInjectionLog
```

---

## 6. API Endpoints (v3.0) — ~30 endpoints

### Endpoints เดิม (v0.1 + v2.0 — ปรับปรุง)

| Method | Path | คำอธิบาย | v3 Changes |
|--------|------|----------|------------|
| `POST` | `/api/upload` | อัปโหลดไฟล์ | — |
| `POST` | `/api/organize` | AI pipeline (cluster+score+summarize) | **+auto graph build + metadata enrich** |
| `GET` | `/api/files` | รายการไฟล์ | **+tags, sensitivity, freshness, sot** |
| `DELETE` | `/api/files/{id}` | ลบไฟล์ | — |
| `GET` | `/api/clusters` | รายการ clusters | — |
| `GET` | `/api/summary/{id}` | Summary ต่อไฟล์ | — |
| `POST` | `/api/chat` | AI Chat | **Graph-aware injection** |
| `GET` | `/api/stats` | สถิติภาพรวม | **+nodes, edges, suggestions, graph_built** |
| `GET` | `/api/profile` | ดึง Profile | — |
| `PUT` | `/api/profile` | อัปเดต Profile | — |
| `GET` | `/api/context-packs` | รายการ Packs | — |
| `POST` | `/api/context-packs` | สร้าง Pack | — |
| `GET` | `/api/context-packs/{id}` | ดึง Pack เดียว | — |
| `DELETE` | `/api/context-packs/{id}` | ลบ Pack | — |
| `POST` | `/api/context-packs/{id}/regenerate` | Regenerate Pack | — |
| `DELETE` | `/api/reset` | Reset ทั้งหมด | **+clear graph/nodes/edges/suggestions** |

### Endpoints ใหม่ (v3.0) — 14 endpoints 🆕

| Method | Path | คำอธิบาย |
|--------|------|----------|
| `POST` | `/api/graph/build` | สร้าง/rebuild Knowledge Graph |
| `GET` | `/api/graph/global` | ดึง graph ทั้งหมดสำหรับ visualization |
| `GET` | `/api/graph/nodes` | รายการ nodes (filter by family) |
| `GET` | `/api/graph/nodes/{id}` | รายละเอียด node + relations |
| `GET` | `/api/graph/neighborhood/{id}` | N-hop neighborhood (depth 1-3) |
| `GET` | `/api/graph/edges` | รายการ edges (filter by type) |
| `GET` | `/api/relations/backlinks/{id}` | Backlinks ที่ชี้มาที่ node |
| `GET` | `/api/relations/outgoing/{id}` | Outgoing links จาก node |
| `GET` | `/api/suggestions` | Suggested relations (pending) |
| `POST` | `/api/suggestions/{id}/accept` | Accept suggestion → สร้าง edge จริง |
| `POST` | `/api/suggestions/{id}/dismiss` | Dismiss suggestion |
| `GET` | `/api/metadata/{file_id}` | ดึง metadata ของไฟล์ |
| `PUT` | `/api/metadata/{file_id}` | อัปเดต metadata (manual) |
| `POST` | `/api/metadata/enrich` | Enrich metadata ทุกไฟล์ด้วย LLM |
| `GET` | `/api/lenses` | รายการ Graph Lenses |

### Chat Response Format (v3.0)

```json
{
  "answer": "...",
  "cluster": { "id": "...", "title": "...", "summary": "..." },
  "files_used": [
    { "id": "...", "filename": "project_nova_plan.md", "importance_label": "high", "is_primary": true }
  ],
  "context_packs_used": [
    { "id": "...", "type": "study", "title": "..." }
  ],
  "profile_used": true,
  "retrieval_modes": { "file_id": "summary" },
  "reasoning": "อธิบายเหตุผลการเลือกข้อมูลเป็นภาษาไทย",
  "injection_summary": "โปรไฟล์ผู้ใช้ + 3 ไฟล์ + 14 graph nodes + 15 relations",
  "nodes_used": [
    { "id": "...", "label": "knowledge graph", "type": "tag" },
    { "id": "...", "label": "ai personal assistant", "type": "tag" }
  ],
  "edges_used": [
    { "source": "project_nova_plan.md", "target": "knowledge graph", "type": "has_tag", "evidence": "..." },
    { "source": "meeting_notes_sprint5.md", "target": "การพัฒนา knowledge graph", "type": "has_tag", "evidence": "..." }
  ]
}
```

---

## 7. AI Pipeline อธิบายละเอียด (v3.0)

### 7.1 Organization + Graph Pipeline — ขยายจาก v2

```
POST /api/organize
     │
     ├─ 1. โหลดไฟล์ทั้งหมด
     ├─ 2. LLM จัดกลุ่ม (clustering)
     ├─ 3. LLM ให้คะแนน (importance scoring)
     ├─ 4. LLM สร้างสรุป (summarization)
     ├─ 5. TF-IDF index (vector search)
     │
     ├─── 🆕 6. Metadata Enrichment ──────────────────────┐
     │         สำหรับแต่ละไฟล์:                              │
     │         ├─ ส่ง summary ไป LLM                        │
     │         ├─ ดึง tags, sensitivity, freshness           │
     │         └─ บันทึกลง File model                        │
     │                                                       │
     ├─── 🆕 7. Graph Build ──────────────────────────────┐ │
     │         ├─ สร้าง File Nodes (1 per file)             │ │
     │         ├─ สร้าง Cluster Nodes (1 per cluster)       │ │
     │         ├─ สร้าง Pack Nodes (1 per context pack)     │ │
     │         ├─ LLM Entity Extraction จาก summaries       │ │
     │         │   └─ ดึง entities → สร้าง Entity/Tag nodes  │ │
     │         ├─ สร้าง Edges:                               │ │
     │         │   ├─ contains (cluster → file)              │ │
     │         │   ├─ has_tag (file → tag)                   │ │
     │         │   ├─ mentions (file → entity)               │ │
     │         │   └─ semantically_related (file ↔ file)     │ │
     │         └─ รายงาน: N nodes, M edges                   │ │
     │                                                       │ │
     └─── 🆕 8. Suggestion Generation ───────────────────┘ │
               ├─ หาไฟล์ที่อาจเชื่อมโยงกัน                    │
               ├─ Heuristic: shared tags, co-occurrence         │
               └─ สร้าง SuggestedRelation records               │
```

### 7.2 Graph Builder Details (`graph_builder.py`) 🆕

```
build_full_graph(db, user_id):
  1. เคลียร์ nodes/edges เก่า
  2. สร้าง File Nodes:
     - 1 node ต่อ 1 ไฟล์ที่ status = "ready"
     - importance_score จาก file_insight (0-100 → 0.0-1.0)
     - description จาก summary_text[:200]
  3. สร้าง Cluster Nodes:
     - 1 node ต่อ 1 cluster
     - สร้าง "contains" edges → files ใน cluster
  4. สร้าง Context Pack Nodes:
     - 1 node ต่อ 1 pack
  5. LLM Entity Extraction:
     - ส่ง summaries ทั้งหมดไป LLM
     - ดึง entities (คน, โปรเจกต์, องค์กร, concept)
     - สร้าง Entity/Tag nodes
     - สร้าง "has_tag" edges
  6. Semantic Similarity:
     - เปรียบเทียบ summaries คู่ต่อคู่
     - สร้าง "semantically_related" edges (overlap > threshold)
  7. return { nodes: N, edges: M }
```

### 7.3 Metadata Enrichment (`metadata.py`) 🆕

```
enrich_file_metadata(db, file):
  1. ส่ง summary + key_topics ไป LLM
  2. LLM ตอบกลับ JSON:
     {
       "tags": ["knowledge graph", "AI", "การจัดการข้อมูล"],
       "sensitivity": "normal",  // normal | sensitive | confidential
       "freshness": "current"    // current | aging | stale
     }
  3. บันทึกลง File model (tags, sensitivity, freshness)
```

### 7.4 Relations Management (`relations.py`) 🆕

```
get_backlinks(db, node_id):    → edges ที่ target = node_id
get_outgoing(db, node_id):     → edges ที่ source = node_id
get_suggestions(db, user_id):  → pending suggestions

generate_suggestions(db, user_id):
  1. หาไฟล์ที่อยู่ cluster เดียวกัน
  2. หาไฟล์ที่ share tags มากกว่า 2
  3. สร้าง SuggestedRelation (type, confidence, reason)

accept_suggestion(db, id):  → สร้าง GraphEdge จริง + set status = accepted
dismiss_suggestion(db, id): → set status = dismissed
```

### 7.5 Graph-aware Retrieval (`retriever.py`) — ยกเครื่อง v3

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
     ├─── 🆕 Layer 6: Graph Node Lookup ─────────────────────
     │         สำหรับแต่ละ file ที่ถูกเลือก:
     │         ├── หา GraphNode ของไฟล์
     │         ├── ดึง outgoing edges (has_tag, mentions, etc.)
     │         ├── ดึง incoming edges (backlinks)
     │         ├── เก็บ nodes_used + edges_used (limit 5 per file)
     │         └── สร้าง KNOWLEDGE GRAPH RELATIONSHIPS context
     │
     ├─── 🆕 Layer 7: Graph Context Injection ───────────────
     │         เพิ่มข้อความ:
     │         === KNOWLEDGE GRAPH RELATIONSHIPS ===
     │           file.md --[has_tag]--> knowledge graph: evidence
     │           file.md --[has_tag]--> AI: evidence
     │         ลงใน context block (ถ้ายังไม่เกิน MAX_CONTEXT_CHARS)
     │
     ├─── Assemble Context Block (priority: Profile → Packs → Files → Graph)
     │    └── Token budget: max 12,000 chars
     │
     ├─── Generate Answer (LLM + graph relationships + user style)
     │
     ├─── Log Injection (+ node_ids_used, edge_ids_used)
     │
     └─── Return: answer + files + packs + profile + nodes_used + edges_used
```

---

## 8. Knowledge Graph — รายละเอียด

### Node Types (6 ประเภท)

| Node Family | สี | ตัวอย่าง | ที่มา |
|-------------|-----|---------|-------|
| `source_file` | 🟡 เหลือง `#ffd54f` | research_knowledge_graph.md | สร้างจากไฟล์ที่อัปโหลด |
| `entity` | 🟠 ส้ม `#ff8a65` | ดร.สมชาย วิจัยดี | LLM entity extraction |
| `tag` | 🔵 ฟ้า `#4fc3f7` | knowledge graph, AI | LLM topic extraction |
| `project` | 🟢 เขียว `#81c784` | ภาพรวมและแผนงานฯ (cluster) | สร้างจาก clusters |
| `context_pack` | 🟦 ฟ้าเข้ม `#4dd0e1` | NOVA Research Context | สร้างจาก context packs |
| `person` | 🟣 ม่วง `#b39ddb` | วิภา ข้อมูลศาสตร์ | LLM entity extraction |

### Edge Types (5 ประเภท)

| Edge Type | ตัวอย่าง | ที่มา |
|-----------|---------|-------|
| `contains` | cluster → file | File อยู่ใน cluster |
| `has_tag` | file → tag | LLM extracted tag |
| `mentions` | file → entity | LLM entity extraction |
| `semantically_related` | file ↔ file | Summary similarity |
| `derived_from` | pack → file | Context pack source |

### สถิติกราฟจากข้อมูลทดสอบ (5 ไฟล์)

| รายการ | จำนวน |
|--------|-------|
| **Total Nodes** | 31 |
| **Total Edges** | 34 |
| File Nodes | 5 |
| Collection Nodes | 2 |
| Tag Nodes | 24 |
| `contains` edges | 5 |
| `has_tag` edges | 25 |
| `semantically_related` edges | 4 |

---

## 9. UI/UX สรุป (v3.0)

### 4 หน้าหลัก

| หน้า | ฟีเจอร์ v2.0 | ฟีเจอร์ใหม่ v3.0 |
|------|-------------|-------------------|
| **My Data** | Upload + file list + packs | + 🆕 Metadata badges (tags, freshness, sensitivity, SOT), "Enrich Metadata" button |
| **Knowledge View** 🆕 | (เดิมชื่อ Collections) | 3 tabs: Collections / Notes & Summaries / Context Packs |
| **Graph** 🆕 | (ไม่มีใน v2) | Global/Local toggle, search, 6 filter chips, D3.js force simulation, detail panel |
| **AI Chat** | Chat + Sources Panel | + Nodes & Edges section, injection badge แสดง graph data, 🆕 Evidence Graph (D3.js mini vis) |

### UI Components ใหม่ (v3.0) 🆕

| Component | ตำแหน่ง | หน้าที่ |
|-----------|---------|---------|
| **Graph Canvas** | Graph page | D3.js force-directed visualization, zoom/pan, drag |
| **Detail Panel** | Graph page (right) | Node info, summary, metadata grid, relations list, actions |
| **Filter Chips** | Graph page (top) | Toggle visibility: ไฟล์ / Entity / Tag / Collection / Pack / Person |
| **Search Input** | Graph page (top-left) | พิมพ์ค้นหา → highlight/dim nodes |
| **Global/Local Toggle** | Graph page (top-right) | สลับระหว่าง Global Graph ↔ Local Graph |
| **Depth Slider** | Graph page (Local mode) | ปรับ depth 1-3 hops ของ neighborhood |
| **Knowledge Tabs** | Knowledge View | 3 tabs: Collections / Notes / Packs |
| **Metadata Badges** | My Data file list | แสดง tags, freshness, sensitivity, source_of_truth |
| **Evidence Graph** | AI Chat sources panel | Mini D3.js graph แสดง evidence structure |
| **Nodes & Edges Section** | AI Chat sources panel | แสดง graph nodes + relations ที่ AI ใช้ |
| **Enrich Metadata Button** | My Data header | Trigger LLM metadata enrichment |
| **Rebuild Graph Button** | Graph header | Trigger knowledge graph rebuild |
| **Language Toggle** 🆕 | Sidebar footer | 🌐 Globe icon + TH\|EN pill, สลับภาษาแบบ real-time |

### Design System (v3.0)

| ด้าน | รายละเอียด |
|------|-----------|
| **Color Scheme** | Dark mode `#0a0e1a` base, `#111827` secondary |
| **Node Colors** | 🟡 File / 🟠 Entity / 🔵 Tag / 🟢 Collection / 🟦 Pack / 🟣 Person |
| **Layer Colors** | 👤 Profile = Purple / 📦 Packs = Blue / 📁 Collections = Green / 📄 Files = Yellow / 🔗 Graph = Orange |
| **Typography** | Google Inter (300-700) |
| **Effects** | Glassmorphism, radial gradient for graph bg |
| **Animations** | fadeIn, slideUp, slideIn, pulse, spin |
| **Graph Rendering** | D3.js v7 force simulation, zoom, pan, drag, node selection |
| **i18n** 🆕 | 120+ translation keys (TH/EN), `data-i18n` DOM binding, `localStorage` persistence |

---

## 10. การทดสอบ E2E — MVP v3.0

### ข้อมูลทดสอบ

- 5 ไฟล์ .md (research, project plan, meeting notes, tech spec, study notes)
- เนื้อหาเกี่ยวกับ โปรเจกต์ NOVA, Knowledge Graph, ทีมงาน (ดร.สมชาย, วิภา ฯลฯ)
- ข้อมูลเชื่อมโยงกัน: คนเดียวกัน, โปรเจกต์เดียวกัน, หัวข้อเดียวกัน

### ผลการทดสอบแบบเต็ม Flow

| # | Test | ขั้นตอน | ผล | Evidence |
|---|------|---------|-----|----------|
| 1 | 📤 Upload | อัปโหลด 5 ไฟล์ .md | ✅ **PASS** | 5/5 สำเร็จ, extract text ครบ |
| 2 | 🧠 Organize + Graph | คลิก "จัดระเบียบด้วย AI" | ✅ **PASS** | 2 clusters, 5 files ready, **31 nodes, 34 edges** |
| 3 | 📊 Stats API | GET /api/stats | ✅ **PASS** | `total_nodes: 31, total_edges: 34, graph_built: true` |
| 4 | 📋 Knowledge View - Collections | เปิด tab Collections | ✅ **PASS** | 2 clusters แสดงพร้อมไฟล์ภายใน |
| 5 | 📋 Knowledge View - Notes | เปิด tab Notes | ✅ **PASS** | แสดง entity nodes ที่ extract ได้ |
| 6 | 🌍 Global Graph | เปิดหน้า Graph | ✅ **PASS** | 31 nodes visible, สี color-coded ถูกต้อง, edges เชื่อมต่อ |
| 7 | 🔍 Graph Search | พิมพ์ "NOVA" ใน search | ✅ **PASS** | Nodes ที่ match highlight, ที่เหลือ dim |
| 8 | 🎨 Graph Filters | Toggle "Tag" off | ✅ **PASS** | Tag nodes ซ่อน, เหลือเฉพาะ file + cluster |
| 9 | 📋 Detail Panel | คลิก node "project_nova_plan.md" | ✅ **PASS** | แสดง: type=SOURCE_FILE, summary, metadata, relations |
| 10 | 🔗 Graph API | GET /api/graph/global | ✅ **PASS** | 31 nodes + 34 edges ในรูปแบบ JSON |
| 11 | 👤 Profile | บันทึก profile | ✅ **PASS** | Profile Active, dot เขียว |
| 12 | 💬 AI Chat | ถาม "สรุปโปรเจกต์ NOVA ให้หน่อย" | ✅ **PASS** | AI ตอบเป็นภาษาไทย, อ้างอิงไฟล์ถูกต้อง |
| 13 | 🔗 Graph-aware Injection | ตรวจ chat response | ✅ **PASS** | `nodes_used: 14, edges_used: 15` — AI ใช้ graph data! |
| 14 | 📊 Injection Summary | ตรวจ injection_summary | ✅ **PASS** | "โปรไฟล์ผู้ใช้ + 3 ไฟล์ + 14 graph nodes + 15 relations" |
| 15 | 📋 Sources Panel | ตรวจ Sources Panel ด้านขวา | ✅ **PASS** | แสดง Profile ✅, Files 3, Nodes 14, Relations 15 |
| 16 | 🗑️ Reset | DELETE /api/reset | ✅ **PASS** | ล้างข้อมูลทั้งหมด + graph data |

### API Verification (ตัวอย่าง Response จริง)

```
injection_summary: "โปรไฟล์ผู้ใช้ + 3 ไฟล์ + 14 graph nodes + 15 relations"

Layer 1 — Profile:     ✅ ใช้ (profile_used: true)
Layer 2 — Packs:       — (ยังไม่มี)
Layer 3 — Collections: ✅ "ภาพรวมและแผนงานโปรเจกต์ NOVA"
Layer 4 — Files:       ✅ project_nova_plan.md (summary, high)
                       ✅ meeting_notes_sprint5.md (summary, high)
                       ✅ tech_spec_knowledge_graph.md (summary, high)
Layer 5-6 — Graph:     ✅ 14 tag nodes (ai personal assistant, knowledge graph, ...)
                       ✅ 15 has_tag edges (file → tag with evidence)
Layer 7 — Injection:   ✅ Graph relationships injected as context
```

---

## 11. สิ่งที่เปลี่ยนแปลงจาก v2.0 → v3.0 (Changelog)

### A. ไฟล์ใหม่ (5 ไฟล์)

| ไฟล์ | หน้าที่ | จำนวนบรรทัด |
|------|---------|-------------|
| `backend/graph_builder.py` | สร้าง Knowledge Graph อัตโนมัติ + LLM entity extraction | 566 |
| `backend/relations.py` | Backlinks, outgoing, suggested relations + accept/dismiss | 230 |
| `backend/metadata.py` | LLM metadata enrichment (tags, sensitivity, freshness) | 159 |
| `docs/prd/Project_KEY_PRD_MVP_v3.md` | PRD เวอร์ชัน 3.0 ครบถ้วน | 668 |
| `README.md` 🆕 | Project overview + quick start + structure diagram | 73 |

### B. ไฟล์ที่แก้ไขเยอะ (6 ไฟล์ — rewritten)

| ไฟล์ | การเปลี่ยนแปลงหลัก | บรรทัด |
|------|-------------------|--------|
| `backend/database.py` | +6 ORM models, +6 metadata columns on File | 277 |
| `backend/main.py` | **Major rewrite** — +14 new endpoints, auto graph trigger | 694 |
| `backend/retriever.py` | **Major rewrite** — +Layer 5-7 graph-aware injection | 441 |
| `index.html` | **Full rewrite** — 4 pages, D3.js, graph canvas, i18n `data-i18n` | 443 |
| `styles.css` | **Full rewrite** — v3 design system, node colors, graph, toggle | 1,387 |
| `app.js` | **Full rewrite** — D3.js, knowledge tabs, evidence graph, **i18n engine** | 1,283 |

### C. ระบบ i18n Bilingual (เพิ่มในเซสชันสุดท้าย) 🆕

| Component | รายละเอียด |
|-----------|------------|
| **I18N Dictionary** | 120+ translation keys ครอบคลุม TH + EN |
| **`getLang()` / `t(key)`** | Helper functions ดึงภาษาจาก `localStorage` |
| **`applyLanguage(lang)`** | อัพเดท DOM ทั้งหน้าแบบ real-time |
| **Data-i18n Binding** | Static elements ทุกตัวมี `data-i18n` attribute |
| **Dynamic Translation** | ปุ่ม, toast, placeholders, modals ทุกจุดใช้ `t()` |
| **Language Toggle** | Globe icon + TH\|EN pill — สลับทันที |
| **Persistence** | `localStorage('projectkey_lang')` จำข้ามรอบ |
| **Bug Fixed** | Variable shadowing `.map(t =>)` → `.map(tag =>)` |

### D. การจัดระเบียบโปรเจกต์ (Project Restructure) 🆕

| ก่อน | หลัง | เหตุผล |
|------|------|--------|
| PRD.md, Project_KEY_PRD_v2.md, v3.md ที่ root | `docs/prd/` | รวมเอกสาร PRD ไว้ที่เดียว |
| USER_GUIDE_V3.md ที่ root | `docs/guides/` | แยกคู่มือออก |
| PROJECT_REPORT.md ที่ root | `docs/` | เอกสารอยู่ใน docs |
| test_files/ + test_files_v3/ สองโฟลเดอร์ | `tests/fixtures/` | รวม test data เข้าที่เดียว |
| testsprite_tests/ | `tests/testsprite/` | จัดกลุ่มทดสอบ |
| test_*.py ที่ root | `tests/e2e/` | ไม่รกที่ root |
| context_packs/ (ว่าง) | ❌ ลบ | ไม่จำเป็น |
| ไม่มี README | ✅ สร้าง `README.md` | มาตรฐานโปรเจกต์ |

### E. ข้อจำกัดจาก v2.0 ที่แก้ไขแล้ว

| # | ข้อจำกัด v2.0 | สถานะ v3.0 |
|---|--------------|------------|
| 1 | ไม่เห็นความเชื่อมโยงระหว่างไฟล์ | ✅ **แก้แล้ว** — Knowledge Graph |
| 2 | ไม่มี metadata มากพอ | ✅ **แก้แล้ว** — tags, sensitivity, freshness, SOT |
| 3 | AI ไม่ใช้ความสัมพันธ์ | ✅ **แก้แล้ว** — Graph-aware injection |
| 4 | ดูข้อมูลได้แค่ list/cards | ✅ **แก้แล้ว** — Graph visualization |
| 5 | UI ภาษาไทยอย่างเดียว | ✅ **แก้แล้ว** — Bilingual TH/EN |
| 6 | โครงสร้างไฟล์รก | ✅ **แก้แล้ว** — จัดระเบียบ docs/, tests/ |

---

## 12. ข้อจำกัดที่ยังมีอยู่ (Known Limitations v3.0)

| # | ข้อจำกัด | ความเสี่ยง | แนวทาง Next Version |
|---|---------|-----------|-------------------|
| 1 | **ไม่มีระบบ Auth** — DEFAULT_USER_ID | High (ถ้า deploy shared) | JWT / OAuth2 |
| 2 | **Vector index ใน RAM** — restart rebuild | Medium | ChromaDB / persist |
| 3 | **Entity extraction ใช้ LLM** — อาจไม่ consistent | Medium | Fine-tune prompt / NER model |
| 4 | **Graph rebuild = ล้างทั้งหมด** | Medium | Incremental update |
| 5 | **Canvas Beta** — ยังไม่ implement UI | Low | v3.1 |
| 6 | **Graph Lenses** — API ready แต่ยังไม่มี UI | Low | v3.1 |
| 7 | **ไม่มี encryption** — ไฟล์เก็บ plaintext | Low (local) | Encrypt at rest |
| 8 | **Single-threaded organize** | Low (MVP scale) | Background tasks |

---

## 13. วิธีรัน

### Prerequisites

```bash
# Python 3.10+
pip install -r requirements.txt
```

### Setup .env

```bash
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

### Quick Start Guide (v3.0)

1. **ตั้งค่า Profile** — คลิก "My Profile" ที่ sidebar → กรอกข้อมูล → Save
2. **อัปโหลดไฟล์** — ลากวางที่ Upload Zone หรือคลิกเลือก
3. **จัดระเบียบ + สร้างกราฟ** — คลิก "จัดระเบียบด้วย AI" (รอ 30-120 วินาที)
   - ระบบจะ: cluster → score → summarize → enrich metadata → build graph → generate suggestions
4. **สำรวจ Knowledge View** — ดู Collections, Notes, Context Packs
5. **สำรวจ Graph** — เปิดหน้า Graph → ดู Global Graph → คลิก node → ดู Detail Panel
6. **ค้นหาใน Graph** — พิมพ์ในช่อง search → toggle filter chips → สลับ Global/Local
7. **ถาม AI** — ไปหน้า AI Chat → ถามคำถาม → ดู Sources Panel + Nodes & Edges + Evidence Graph

---

## 14. Roadmap — Next Steps

### P0 — Graph Intelligence (v3.1)

- [ ] Canvas Beta — drag & arrange nodes + notes
- [ ] Graph Lenses UI — Theme/Bridge/Foundation presets
- [ ] Incremental Graph Update — ไม่ต้อง rebuild ทั้งหมด
- [ ] Person Node Enhancement — ใช้ NER แทน LLM

### P1 — Trust & Auth

- [ ] Authentication (JWT / session-based)
- [ ] Persist TF-IDF index ลง disk
- [ ] Rate limiting ที่ API endpoints สำคัญ

### P2 — Intelligence

- [ ] Auto Context Pack — สร้างอัตโนมัติเมื่อ organize เสร็จ
- [ ] AI-suggested Profile — LLM แนะนำ fields จากไฟล์
- [ ] Conversation Memory — จำบทสนทนาข้ามรอบ
- [ ] Cross-file Entity Resolution — merge entities ที่อ้างถึงคนเดียวกัน

### P3 — UX Enhancement

- [ ] Search bar ในหน้า My Data
- [ ] Full-text file viewer
- [ ] Export graph as image/PDF
- [ ] Mobile-responsive layout

### P4 — DevOps

- [ ] Docker Compose (backend + frontend)
- [ ] GitHub Actions CI pipeline
- [ ] Production deployment guide

---

## 15. สถิติโปรเจกต์

| รายการ | v0.1 | v2.0 | v3.0 (Final) |
|--------|------|------|------|
| **Backend modules** | 8 files | 10 files | **15 files (+5)** |
| **Frontend files** | 3 files | 3 files | **3 files (rewritten)** |
| **Database tables** | 7 tables | 10 tables | **16 tables (+6)** |
| **API endpoints** | 8 endpoints | 16 endpoints | **~30 endpoints (+14)** |
| **Python dependencies** | 10 packages | 11 packages | **11 packages** |
| **Backend code** | ~1,200 lines | ~2,100 lines | **3,660 lines** |
| **Frontend code** | ~1,350 lines | ~2,000 lines | **3,113 lines** |
| **Total code** | ~2,550 lines | ~4,100 lines | **6,773 lines** |
| **LLM calls per organize** | 3 (cluster+score+summary) | 3 | **5 (+metadata+entity)** |
| **LLM calls per chat** | 2 (select+answer) | 2 | **2 (+graph layer in context)** |
| **Graph nodes (9 files)** | — | — | **33** |
| **Graph edges (9 files)** | — | — | **56** |
| **Node types** | — | — | **6** |
| **Edge types** | — | — | **5** |
| **i18n keys** | — | — | **120+** |
| **Languages** | TH only | TH only | **TH + EN** |
| **TestSprite TCs** | — | 15 | **29** |
| **E2E tests passed** | 9/15 (60%) | 7/7 (100%) | **16/16 (100%)** |
| **Git tags** | — | v2.0 | **v3.0** |

### สถิติไฟล์ Frontend (v3.0 Final)

| ไฟล์ | บรรทัด | หน้าที่หลัก |
|------|--------|----------|
| `app.js` | 1,283 | D3.js graph + i18n engine + 120 translation keys + chat + file list |
| `styles.css` | 1,387 | Dark theme + graph styles + node colors + toggle + animations |
| `index.html` | 443 | 4 pages + modals + data-i18n attributes + D3.js CDN |

### สถิติไฟล์ Backend (v3.0)

| ไฟล์ | บรรทัด | หน้าที่หลัก |
|------|--------|----------|
| `main.py` | 694 | ~30 API endpoints |
| `graph_builder.py` | 566 | Knowledge graph auto-build + entity extraction |
| `retriever.py` | 441 | 7-layer graph-aware RAG retrieval |
| `vector_search.py` | 286 | Hybrid TF-IDF + keyword search |
| `database.py` | 277 | 16 SQLAlchemy ORM models |
| `context_packs.py` | 272 | Context pack CRUD + generation |
| `organizer.py` | 261 | AI clustering + scoring + summarization |
| `relations.py` | 230 | Backlinks, outgoing, suggestions |
| `metadata.py` | 159 | LLM metadata enrichment |
| `markdown_store.py` | 135 | Summary file I/O |
| `extraction.py` | 127 | PDF/TXT/MD/DOCX text extraction |
| `profile.py` | 106 | User profile CRUD |
| `llm.py` | 81 | OpenRouter API wrapper |
| `config.py` | 24 | Environment config |

---

## 16. i18n Bilingual System — รายละเอียด 🆕

### Architecture

```
┌─────────────────────────────────────┐
│  I18N Dictionary (app.js)           │
│  ├── th: { 120+ keys }             │
│  └── en: { 120+ keys }             │
├─────────────────────────────────────┤
│  applyLanguage(lang)                │
│  ├── querySelectorAll([data-i18n])  │
│  ├── Update input placeholders      │
│  ├── Update toggle button state     │
│  └── Re-render dynamic file list    │
├─────────────────────────────────────┤
│  localStorage('projectkey_lang')    │
│  └── Persists across page refreshes │
└─────────────────────────────────────┘
```

### Translation Coverage

| Section | จำนวน Keys | ตัวอย่าง (TH → EN) |
|---------|-----------|--------------------|
| Navigation | 5 | ข้อมูลของฉัน → My Data |
| Stats | 5 | ไฟล์ → Files |
| My Data | 10 | ลากไฟล์มาวาง → Drag files here... |
| Knowledge View | 6 | คอลเลกชัน → Collections |
| Graph | 10 | กราฟรวม → Global Graph |
| AI Chat | 8 | ถามเกี่ยวกับข้อมูล → Ask about your data |
| Profile Modal | 8 | ฉันเป็นใคร → Who am I |
| Sources Panel | 8 | หลักฐานที่ใช้ → Evidence Used |
| Toasts/Dynamic | 15+ | อัปโหลดเรียบร้อย → Upload complete |
| Detail Panel | 3 | ไม่มีสรุป → No summary |

### Bug Fixes (i18n)

| Bug | สาเหตุ | การแก้ |
|-----|--------|--------|
| ปุ่ม Delete ไม่แปล | `.map(t =>)` shadow global `t()` | เปลี่ยนเป็น `.map(tag =>)` |
| Flag emoji render ผิดบน Windows | 🇹🇭/🇺🇸 ไม่ support | ใช้ Globe SVG icon + text แทน |
| ไฟล์ list ไม่ re-render ตอนสลับภาษา | toggle ไม่เรียก loadFiles() | เพิ่ม `loadFiles()` ใน toggle handler |

---

## 17. สรุปภาพรวม

MVP v3.0 (Final) คือการเปลี่ยน Project KEY จาก **"ที่เก็บข้อมูลอัจฉริยะ"** ไปเป็น **"พื้นที่ทำงานความรู้"** ที่ผู้ใช้สามารถ:

1. **มองเห็นภาพรวมความรู้** ผ่าน Knowledge Graph (D3.js)
2. **สำรวจความเชื่อมโยง** ระหว่างไฟล์ คน หัวข้อ และโปรเจกต์
3. **ค้นพบความสัมพันธ์ใหม่** ผ่าน Suggested Relations
4. **ถาม AI อย่างมีหลักฐาน** — AI อ้างอิง nodes, edges, evidence จากกราฟ
5. **จัดระเบียบ metadata** ด้วย AI enrichment อัตโนมัติ
6. **ใช้งาน 2 ภาษา** 🆕 — สลับ ไทย/อังกฤษ ได้ทันทีด้วยปุ่มเดียว

ทั้งหมดนี้สร้างบน architecture เดิมของ v2.0 โดยไม่ breaking changes ใดๆ  
โปรเจกต์ถูกจัดระเบียบใหม่ พร้อม README.md, docs/, tests/ ตามมาตรฐาน

### Version History

| Version | Tag | Commit | วันที่ | สรุป |
|---------|-----|--------|-------|------|
| v0.1 | — | `41be76e` | 15 เม.ย. 69 | Stable Foundation — Upload, Organize, AI Chat |
| v2.0 | — | `e92ae1b` | 17 เม.ย. 69 | Second Brain — Profile, Context Packs, Hybrid Search |
| v3.0 | `v3.0` | `8122383` | 18 เม.ย. 69 | Knowledge Workspace — Graph, i18n, Restructure |

---

*รายงานจัดทำโดย Antigravity AI · Project KEY MVP v3.0 Final · อัพเดท 18 เมษายน 2569 (13:25 น.)*
