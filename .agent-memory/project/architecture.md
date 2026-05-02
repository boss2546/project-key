# 🏗️ Architecture

## โครงสร้างโฟลเดอร์ (สำคัญ)

```
d:\PDB\
├── backend/              # Python FastAPI backend
│   ├── main.py          # Entry point + routes registration
│   ├── auth.py          # JWT auth logic
│   ├── billing.py       # Stripe integration
│   ├── database.py      # SQLite operations
│   ├── extraction.py    # File text extraction
│   ├── graph_builder.py # Knowledge graph
│   ├── llm.py           # LLM client (OpenRouter)
│   ├── mcp_tools.py     # MCP tool definitions (30 tools)
│   ├── mcp_tokens.py    # MCP auth tokens
│   ├── organizer.py     # AI organize logic
│   ├── plan_limits.py   # Subscription limits
│   ├── relations.py     # File relations
│   ├── markdown_store.py
│   ├── metadata.py
│   ├── profile.py
│   ├── context_memory.py
│   ├── context_packs.py
│   └── config.py        # Config + env vars
│
├── legacy-frontend/      # Vanilla HTML/CSS/JS
│   ├── index.html
│   ├── app.js
│   ├── styles.css
│   ├── pricing.html
│   └── guide/
│
├── chroma_db/           # Vector embeddings (ChromaDB)
├── context_packs/       # Saved context packs
├── docs/                # Documentation
├── skills/              # Claude skills (symlink → .agents/skills/)
├── backups/             # Database backups
├── summaries/           # AI-generated summaries
│
├── projectkey.db        # SQLite database (main)
├── DESIGN.md            # Design decisions
├── README.md            # Project README
├── Dockerfile           # Container build
├── fly.toml             # Fly.io config
├── mcp-proxy.js         # MCP proxy server (Node.js)
├── package.json         # Node deps
├── requirements.txt     # Python deps
├── requirements-fly.txt # Python deps for Fly.io
└── .env                 # Secrets (ห้าม commit)
```

## Data Flow หลัก

### 1. File Upload Flow
```
User → frontend (index.html) → POST /api/upload (main.py)
                              → extraction.py (extract text)
                              → database.py (save metadata)
                              → chroma_db (save embeddings)
```

### 2. AI Organize Flow
```
User triggers → POST /api/organize → organizer.py
                                   → LLM (llm.py)
                                   → graph_builder.py (build graph)
                                   → relations.py (find connections)
                                   → database.py (save results)
```

### 3. MCP Access Flow
```
Claude → mcp-proxy.js → backend MCP endpoints
                      → mcp_tools.py (tool execution)
                      → database.py (read user data)
```

### 4. Billing Flow
```
User → frontend (pricing.html) → Stripe Checkout
                               → Stripe webhook → billing.py
                               → plan_limits.py (update limits)
                               → database.py (save subscription)
```

## Key Design Decisions
ดูรายละเอียดใน [`DESIGN.md`](../../DESIGN.md) (root ของ repo)

ที่ควรรู้:
- ใช้ SQLite (ไม่ใช่ Postgres) — เน้น simplicity, deploy ง่ายบน Fly.io
- ChromaDB embedded (ไม่ใช่ separate service)
- Frontend ยังเป็น legacy — มีแผนจะ migrate แต่ยังไม่ทำ
- Stripe webhooks signed verification เปิดใช้งาน
- v5.9.3 มี locked-data guards บน share/reprocess/regenerate

## Security Boundaries
- `.env`, `.jwt_secret`, `.mcp_secret` — ห้ามแตะหรือ commit
- `projectkey.db` — มีข้อมูลผู้ใช้ ห้าม share
- API endpoints ส่วนใหญ่ต้องผ่าน JWT auth
- Stripe webhook ต้องตรวจ signature
