# 📘 Project KEY — รายงานเทคนิคฉบับสมบูรณ์ (v4.3)

> **จัดทำสำหรับ:** ผู้เชี่ยวชาญ / Technical Reviewers / Architects  
> **วันที่:** 19 เมษายน 2569  
> **เวอร์ชัน:** v4.3  
> **Production:** https://personaldatabank.fly.dev/  
> **Repository:** https://github.com/boss2546/project-key

---

## 1. Executive Summary

**Project KEY** คือ Personal Knowledge Workspace ที่แก้ปัญหา "ข้อมูลกระจัดกระจาย + AI ไม่เข้าใจบริบทส่วนตัว"

ระบบแปลงไฟล์ดิบ (PDF, TXT, MD, DOCX) ผ่าน AI Pipeline ให้กลายเป็น:
- **Knowledge Graph** — ความเชื่อมโยงระหว่าง entities
- **Vectorized Data** — TF-IDF index สำหรับ semantic search
- **Structured Metadata** — tags, sensitivity, freshness, importance

จากนั้นใช้ **RAG 7 ชั้น** และ **MCP 21 tools** เพื่อให้ AI ภายนอก (Claude Desktop) ดึงข้อมูลส่วนตัวไปใช้ได้

### วิสัยทัศน์ 4 เสาหลัก
1. **Preservation** — เก็บรักษาข้อมูลอย่างปลอดภัย
2. **Privacy** — ข้อมูลอยู่ในมือผู้ใช้เสมอ
3. **Structure** — จัดระเบียบด้วย AI อัตโนมัติ
4. **Seamless Use** — AI เข้าถึงข้อมูลได้ทันที

### Version History
```
v0.1  → Personal Data Bank — อัปโหลด จัดเก็บ สรุป AI Chat
v2.0  → Second Brain — Profile + Context Packs + Hybrid Search
v3.0  → Knowledge Workspace — Graph + i18n + Project Restructure
v4.0  → Production Deploy — Fly.io + MCP 5 tools
v4.1  → Full MCP — 21 tools + Data Management UX
v4.2  → Permission System — 4 categories + Admin bypass + Thai bilingual
v4.3  → Bugfix — Search index auto-rebuild + DB fallback + add_note fix
```

---

## 2. System Architecture

### Tech Stack

| Layer | Technology | หมายเหตุ |
|-------|-----------|----------|
| Frontend | Vanilla JS + HTML + CSS | 4,787 lines, no framework |
| Data Viz | D3.js v7 | Force-directed graph layout |
| Backend | Python FastAPI + Uvicorn | Async, 17 modules, 4,474 lines |
| Database | SQLite (aiosqlite) | 18 tables, single-file DB |
| Search | Custom TF-IDF (in-memory) | Auto-rebuild on startup |
| LLM | OpenRouter → Gemini 2.5 Flash | ใช้วิเคราะห์/สรุป/จัด entity |
| Deploy | Docker + Fly.io | Singapore region, 64MB image |
| AI Bridge | MCP Streamable HTTP | 21 tools, JSON-RPC 2.0 |

### Architecture Diagram
```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Vanilla JS)                     │
│  index.html (691L) + app.js (1,980L) + styles.css (2,116L) │
│  ┌─────┐ ┌──────┐ ┌───────┐ ┌──────┐ ┌─────┐ ┌──────────┐ │
│  │MyData│ │Collec│ │ Graph │ │ Chat │ │Prof.│ │MCP Setup │ │
│  └──┬──┘ └──┬───┘ └──┬────┘ └──┬───┘ └──┬──┘ └────┬─────┘ │
└─────┼───────┼────────┼─────────┼────────┼─────────┼────────┘
      │       │        │         │        │         │
      ▼       ▼        ▼         ▼        ▼         ▼
┌─────────────────────────────────────────────────────────────┐
│                FastAPI Backend (main.py 923L)                │
│                    46 API Endpoints                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐  │
│  │organizer │ │retriever │ │graph_    │ │  mcp_tools    │  │
│  │  238L    │ │  378L    │ │builder   │ │    895L       │  │
│  │          │ │ 7-layer  │ │  567L    │ │  21 tools     │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬────────┘  │
│       │            │            │               │           │
│  ┌────▼────┐  ┌────▼────┐  ┌───▼────┐   ┌─────▼──────┐    │
│  │vector_  │  │  llm    │  │database│   │ mcp_tokens │    │
│  │search   │  │  69L    │  │  251L  │   │   106L     │    │
│  │ 233L    │  │OpenRoute│  │18 table│   │ Bearer JWT │    │
│  └─────────┘  └─────────┘  └───┬────┘   └────────────┘    │
└─────────────────────────────────┼───────────────────────────┘
                                  ▼
                    ┌──────────────────────┐
                    │  SQLite (projectkey  │
                    │  .db) + Fly Volume   │
                    │  /app/data/          │
                    └──────────────────────┘
```

---

## 3. Data Pipeline (Core Logic)

ข้อมูลไหลผ่าน 4 ขั้นตอนหลัก:

### Step 1: Ingestion (`extraction.py` — 110L)
```
User Upload → extract_text() → Plaintext → File table (status="uploaded")
```
- รองรับ: PDF (PyPDF2), DOCX (python-docx), TXT, MD
- จำกัดขนาด: 10MB ต่อไฟล์
- Output: `File.extracted_text` + `File.processing_status = "uploaded"`

### Step 2: Organization Pipeline (`organizer.py` — 238L)
```
กด "Organize with AI" → LLM สรุป → Clustering → TF-IDF Index
```
1. **Summarization:** ส่ง text ให้ LLM สรุป 5 องค์ประกอบ:
   - `summary_text` — สรุปย่อ
   - `key_topics` — หัวข้อสำคัญ (JSON array)
   - `key_facts` — ข้อเท็จจริงสำคัญ (JSON array)
   - `why_important` — ทำไมไฟล์นี้สำคัญ
   - `suggested_usage` — แนะนำวิธีใช้
2. **Importance Scoring:** LLM ให้คะแนน 0-100 + label (high/medium/low)
3. **Clustering:** LLM เทียบกับ Cluster ที่มี ถ้าไม่เข้ากลุ่ม → สร้างใหม่
4. **TF-IDF Indexing:** chunk text (500 chars, 100 overlap) → คำนวณ TF-IDF → เก็บ RAM

### Step 3: Graph Building (`graph_builder.py` — 567L)
```
build_full_graph() → Clear เก่า → สร้าง Nodes → Extract Entities → สร้าง Edges
```
**Phase 1 — สร้าง Nodes:**
- Files → `source_file` nodes (importance จาก FileInsight)
- Clusters → `cluster` nodes (family: project)
- Context Packs → `context_pack` nodes

**Phase 2 — Extract Tags:**
- ดึง key_topics จาก summaries → filter เฉพาะ tag ที่ปรากฏใน 2+ ไฟล์
- LLM สร้าง description ภาษาไทยให้แต่ละ tag
- Dynamic importance: `0.3 + (connections / total_files) * 0.6`

**Phase 3 — Extract Entities via LLM:**
- ส่ง summaries ทั้งหมดให้ LLM → แยก entities (person/project/concept/organization)
- สร้าง `entity` nodes + edges `mentions` เชื่อมกับ source files

**Phase 4 — สร้าง Edges:**
- `belongs_to`: File → Cluster
- `has_tag`: File → Tag
- `mentions`: File → Entity
- `contains`: Context Pack → File
- `derived_from`: Pack → Cluster

### Step 4: Metadata Enrichment (`metadata.py` — 129L)
```
enrich_all_files() → LLM วิเคราะห์ → อัพเดต tags, sensitivity, freshness
```
- `sensitivity`: normal / sensitive / confidential
- `freshness`: current (≤7d) / aging (≤30d) / stale (>30d)
- `source_of_truth`: boolean
- `aliases`: ชื่อเรียกอื่นของเอกสาร

---

## 4. RAG Retrieval Logic (`retriever.py` — 378L)

AI Chat ใช้ **7-Layer Context Injection** ก่อนส่งคำถามไป LLM:

```
Layer 1: User Profile (ตัวตน สไตล์ เป้าหมาย)
Layer 2: Active Context Packs (ความรู้สรุปเฉพาะทาง)
Layer 3: LLM Context Selection (เลือกไฟล์ที่เกี่ยวข้อง)
Layer 4: Hybrid Search (TF-IDF + Keyword ผสม)
Layer 5: Graph Relationships (1-hop neighbors ของไฟล์ที่ใช้)
Layer 6: Prompt Assembly (รวม <CONTEXT_LAYER> ทั้งหมด)
Layer 7: LLM Generation (ตอบ + อ้างอิง source files)
```

**Token Budget:** MAX_CONTEXT_CHARS = 12,000 chars  
**File Retrieval Modes:**
- `summary` — default, ใช้สำหรับคำถามทั่วไป
- `excerpt` — ส่ง 2,000 chars แรก สำหรับรายละเอียดเฉพาะ
- `raw` — ส่ง 6,000 chars สำหรับต้องการเนื้อหาจริง

**Graph Injection:** เมื่อได้ไฟล์ที่เกี่ยวข้อง → หา GraphNode → ดึง edges ขาออก/ขาเข้า (จำกัด 5 per file) → เพิ่ม relationship context ใน prompt

---

## 5. Database Schema (18 Tables)

### Core Data
| Table | Columns สำคัญ | หน้าที่ |
|-------|-------------|--------|
| `users` | id, name | ผู้ใช้ (ปัจจุบัน DEFAULT_USER_ID) |
| `files` | id, user_id, filename, filetype, extracted_text, processing_status, tags, sensitivity, freshness, source_of_truth | ไฟล์ + metadata |
| `file_summaries` | file_id, summary_text, key_topics, key_facts, why_important | สรุป AI |
| `file_insights` | file_id, importance_score (0-100), importance_label, is_primary_candidate | คะแนนสำคัญ |
| `clusters` | id, user_id, title, summary | กลุ่มที่ AI จัดให้ |
| `file_cluster_map` | file_id, cluster_id, relevance_score | Many-to-Many mapping |

### Knowledge & Profile
| Table | หน้าที่ |
|-------|--------|
| `user_profiles` | identity_summary, goals, working_style, preferred_output_style, background_context |
| `context_packs` | type (profile/study/work/project), title, summary_text, source_file_ids |
| `chat_queries` | question, answer, selected_file_ids, reasoning |
| `context_injection_logs` | profile_used, file_ids, node_ids_used — full transparency |

### Knowledge Graph
| Table | Columns สำคัญ | หน้าที่ |
|-------|-------------|--------|
| `graph_nodes` | object_type, object_id, label, node_family, importance_score (0-1) | Node ในกราฟ |
| `graph_edges` | source_node_id, target_node_id, edge_type, weight, confidence, evidence_text | ความสัมพันธ์ |
| `note_objects` | type (note/entity/concept), title, summary, aliases | Knowledge objects |
| `suggested_relations` | source→target, relation_type, confidence, status (pending/accepted/dismissed) | AI แนะนำ |
| `graph_lenses` | name, type (theme/bridge/foundation), filter_json | บันทึก view config |
| `canvas_objects` | title, json_payload | Canvas workspace (future) |

### MCP Connector
| Table | หน้าที่ |
|-------|--------|
| `mcp_tokens` | token_hash (SHA-256), label, scope, is_active, last_used_at | Bearer tokens |
| `mcp_usage_logs` | tool_name, request_summary, status, latency_ms, error_message | Usage tracking |

---

## 6. MCP Connector & Claude Integration

### สถาปัตยกรรม
```
Claude Desktop ──JSON-RPC 2.0──▶ /mcp/{secret_key} ──▶ FastAPI
                                                         │
                                     ┌───────────────────┘
                                     ▼
                              validate_token()
                                     │
                              check_permission()
                                     │
                              call_tool(name, args)
                                     │
                              log_usage()
                                     │
                                     ▼
                              JSON Response
```

### Security Model (3 ชั้น)
1. **URL Secret:** `/mcp/{secret_key}` — auto-generated, เก็บใน `.mcp_secret`
2. **Bearer Token:** SHA-256 hashed, สร้างจาก UI, revocable
3. **Permission Toggle:** เปิด/ปิด tool แต่ละตัวจาก UI

### 21 MCP Tools (4 หมวด)

**📖 Read & Search (10 tools):**
| Tool | Input | Output |
|------|-------|--------|
| `get_overview` | — | files, collections, packs count, graph stats |
| `get_profile` | — | identity, goals, working_style |
| `list_files` | — | array of file metadata (15 fields each) |
| `get_file_content` | file_id | content (จำกัด 5,000 chars, truncated flag) |
| `get_file_summary` | file_id | summary, key_topics, key_facts, why_important |
| `list_collections` | — | clusters with file lists |
| `list_context_packs` | — | packs with short_summary |
| `get_context_pack` | pack_id | full summary_text + source_file_ids |
| `search_knowledge` | query, limit | matched_files + matched_packs + matched_nodes |
| `explore_graph` | node_id?, depth? | overview or neighborhood |

**✏️ Create & Edit (5 tools):**
| Tool | Input | Output |
|------|-------|--------|
| `upload_text` | content, filename | file_id, text_length |
| `add_note` | file_id, summary_text | updated (auto-creates FileSummary if none) |
| `update_file_tags` | file_id, tags[] | updated tags |
| `update_profile` | identity/goals/style | updated_fields |
| `create_context_pack` | file_ids[], title, type | pack_id |

**🗑️ Delete (2 tools):**
| Tool | Input | Output |
|------|-------|--------|
| `delete_file` | file_id | deleted (cascade: summary, insights, clusters) |
| `delete_pack` | pack_id | deleted |

**⚙️ AI Pipeline (4 tools):**
| Tool | Input | Output |
|------|-------|--------|
| `run_organize` | — | files_processed, clusters_created |
| `build_graph` | — | nodes, edges count |
| `enrich_metadata` | — | enriched count, total_files, message |
| `admin_login` | admin_key | authenticated or denied |

### Permission & Admin Bypass Logic
```python
# ตรวจสอบ permission ก่อนทุก tool call:
if tool is disabled:
    if admin_key provided and admin_key == "1234":
        → bypass, execute tool
    else:
        → return "Tool is disabled"
else:
    → execute tool normally
```

---

## 7. Frontend Architecture

### 7 หน้าหลัก (Single Page App)
| หน้า | ID | ฟีเจอร์หลัก |
|------|-----|-----------|
| My Data | `page-data` | Upload, file list, file detail panel, edit tags/summary |
| Collections | `page-collections` | AI clusters, edit title/summary |
| Knowledge Graph | `page-graph` | D3.js force-directed, global/local views |
| AI Chat | `page-chat` | RAG chat, evidence graph, injection transparency |
| Profile | `page-profile` | 5 profile fields |
| Context Packs | `page-packs` | CRUD packs, type selection |
| MCP Setup | `page-mcp` | Token generation, tool permissions toggle, config copy |

### i18n System (170+ keys)
- `data-i18n` attribute สำหรับ static DOM elements
- `t(key)` function สำหรับ dynamic content
- `applyLanguage()` — อัพเดต DOM ทั้งหมด real-time ไม่ refresh
- Language setting persist ใน `localStorage`

---

## 8. Deployment & Infrastructure

### Docker (64MB image)
```dockerfile
FROM python:3.11-slim
# No gcc needed — lightweight deps only
COPY requirements-fly.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY index.html app.js styles.css ./
ENV DATA_DIR=/app/data
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Fly.io Config
- **Region:** Singapore (`sin`)
- **VM:** shared-cpu-1x, 512MB RAM
- **Auto-stop:** machines stop when idle, auto-start on request
- **Persistent Volume:** `project_key_data` → `/app/data/` (DB + uploads + summaries)
- **HTTPS:** forced

### Startup Sequence
```
1. init_db() — สร้าง 18 tables ถ้ายังไม่มี
2. Create default user
3. Rebuild TF-IDF search index จาก DB (v4.3 fix)
   → โหลดไฟล์ที่ status="ready" → index_file() ทุกตัว
   → ทำให้ search_knowledge ใช้ได้ทันทีหลัง restart
```

---

## 9. API Endpoints (46 routes)

### Data Management
| Method | Path | หน้าที่ |
|--------|------|--------|
| POST | `/api/upload` | อัปโหลดไฟล์ |
| POST | `/api/organize` | รัน AI pipeline |
| GET | `/api/files` | รายการไฟล์ทั้งหมด |
| GET | `/api/files/{id}/content` | เนื้อหาไฟล์ |
| DELETE | `/api/files/{id}` | ลบไฟล์ |
| GET | `/api/clusters` | รายการ clusters |
| PUT | `/api/clusters/{id}` | แก้ไข cluster |
| GET | `/api/summary/{id}` | สรุปไฟล์ |
| PUT | `/api/summary/{id}` | แก้ไขสรุป |

### AI & Knowledge
| Method | Path | หน้าที่ |
|--------|------|--------|
| POST | `/api/chat` | AI Chat (7-layer RAG) |
| POST | `/api/graph/build` | สร้าง Knowledge Graph |
| GET | `/api/graph/global` | ข้อมูลกราฟทั้งหมด |
| GET | `/api/graph/nodes/{id}` | รายละเอียด node |
| GET | `/api/graph/neighborhood/{id}` | Neighbors ของ node |
| GET | `/api/suggestions` | AI-suggested relations |

### Profile & Packs
| Method | Path | หน้าที่ |
|--------|------|--------|
| GET/PUT | `/api/profile` | อ่าน/แก้โปรไฟล์ |
| GET/POST | `/api/context-packs` | รายการ/สร้าง packs |
| GET/DELETE | `/api/context-packs/{id}` | ดู/ลบ pack |

### MCP Connector
| Method | Path | หน้าที่ |
|--------|------|--------|
| GET | `/api/mcp/info` | MCP status + secret URL |
| POST | `/api/mcp/tokens` | สร้าง bearer token |
| GET | `/api/mcp/tokens` | รายการ tokens |
| DELETE | `/api/mcp/tokens/{id}` | revoke token |
| POST | `/api/mcp/tools/call` | เรียก tool (via API) |
| GET | `/api/mcp/logs` | usage logs |
| GET/PUT | `/api/mcp/permissions` | อ่าน/แก้ permission toggles |
| POST | `/mcp/{secret}` | MCP Streamable HTTP endpoint |

---

## 10. วิธีใช้งาน

### A. ติดตั้ง Local
```bash
git clone https://github.com/boss2546/project-key.git
cd project-key
pip install -r requirements.txt
echo OPENROUTER_API_KEY=sk-or-v1-xxx > .env
python -m uvicorn backend.main:app --port 8000
# เปิด http://localhost:8000
```

### B. Deploy Production
```bash
# ติดตั้ง flyctl แล้ว set secret
flyctl secrets set OPENROUTER_API_KEY=sk-or-v1-xxx
flyctl deploy --remote-only
# Live: https://personaldatabank.fly.dev/
```

### C. เชื่อมต่อ Claude Desktop
1. เปิดหน้า MCP Setup → คลิก "Generate Token"
2. Copy JSON config ที่แสดง
3. วางใน `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "project-key": {
      "type": "streamable-http",
      "url": "https://personaldatabank.fly.dev/mcp/{SECRET_KEY}"
    }
  }
}
```
4. Restart Claude → ทดสอบ: "สแกนฐานความรู้ของฉันผ่าน Project KEY"

### D. Workflow แนะนำ
```
1. Upload ไฟล์ (PDF/TXT/MD/DOCX)
2. กด "Organize with AI" → สรุป + จัดกลุ่ม + สร้าง index
3. กด "Build Graph" → สร้าง Knowledge Graph
4. สำรวจ Graph → ดูความเชื่อมโยง
5. ใช้ AI Chat → ถามคำถามเกี่ยวกับข้อมูล
6. สร้าง Context Pack → รวบรวมความรู้เฉพาะทาง
7. เชื่อม Claude → ใช้ MCP ดึงข้อมูลอัตโนมัติ
```

---

## 11. ผลการทดสอบ MCP (Claude Sonnet 4.6)

| สถานะ | จำนวน | รายละเอียด |
|-------|--------|-----------|
| ✅ PASS | 21/21 | ทุกฟังก์ชันทำงานสมบูรณ์ (หลัง v4.3 fix) |
| 🔧 Fixed v4.3 | 3 | search_knowledge, add_note, enrich_metadata |

### Bugs ที่แก้ไขใน v4.3
| Bug | Root Cause | Fix |
|-----|-----------|-----|
| search_knowledge ว่างเปล่า | TF-IDF index ใน RAM หายตอน restart | Startup auto-rebuild + DB fallback |
| add_note ต้อง organize ก่อน | ไม่มี FileSummary record | Auto-create summary record |
| enrich_metadata ไม่บอกเหตุผล | Response ไม่มี context | เพิ่ม total_files + message |

---

## 12. Known Limitations & Next Steps

| # | ข้อจำกัด | ความเสี่ยง | แนวทาง |
|---|---------|-----------|--------|
| 1 | ไม่มี Auth — DEFAULT_USER_ID | High | JWT / OAuth2 |
| 2 | ~~Search index หาย~~ | ~~Medium~~ | ✅ แก้แล้ว v4.3 |
| 3 | Graph rebuild ล้างทั้งหมด | Medium | Incremental update |
| 4 | Admin password hardcoded "1234" | Medium | Environment variable |
| 5 | Permissions ใน memory | Low | Persist to DB |
| 6 | Canvas Beta ยัง no-op | Low | v5 |

### สำหรับ Expert Review
- หากสเกล >50,000 ไฟล์ ควรย้าย TF-IDF เป็น **ChromaDB** หรือ **pgvector**
- ควรเพิ่ม JWT Authentication สำหรับ Multi-User
- ควรเปลี่ยน Admin password เป็น Environment Variable
- ควรเพิ่ม rate limiting สำหรับ MCP endpoint

---

## 13. Project Statistics

| Metric | Value |
|--------|-------|
| **Backend modules** | 17 Python files |
| **Backend lines** | 4,474 lines |
| **Frontend lines** | 4,787 lines (JS+HTML+CSS) |
| **Total codebase** | ~9,261 lines |
| **API endpoints** | 46 routes |
| **MCP tools** | 21 tools |
| **DB tables** | 18 tables |
| **i18n keys** | 170+ translations (TH/EN) |
| **Docker image** | 64 MB |
| **Test cases** | 29 (TestSprite E2E) |
| **Production** | Fly.io Singapore |

---

*รายงานจัดทำโดย Antigravity AI · Project KEY v4.3 · 19 เมษายน 2569*
