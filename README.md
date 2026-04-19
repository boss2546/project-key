# 🔑 Project KEY — Personal Data Bank

> Personal Knowledge Workspace ที่ใช้ AI จัดระเบียบ วิเคราะห์ และเชื่อมโยงข้อมูลของคุณ  
> **v4.3** — MCP Connector + Permission System + Bilingual (TH/EN)

[![Production](https://img.shields.io/badge/Production-project--key.fly.dev-blue)](https://project-key.fly.dev/)
[![Version](https://img.shields.io/badge/version-4.3-green)]()
[![MCP Tools](https://img.shields.io/badge/MCP_Tools-21-purple)]()

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set API key
echo OPENROUTER_API_KEY=your_key > .env

# 3. Run
python -m uvicorn backend.main:app --port 8000
```

Open [http://localhost:8000](http://localhost:8000)

## Production (Fly.io)

```bash
flyctl deploy --remote-only
# Live at: https://project-key.fly.dev/
```

## Features

- 📁 **My Data** — Upload & manage files (PDF, TXT, MD, DOCX) + File Detail Panel
- 🧠 **AI Organization** — Auto-cluster, summarize, enrich metadata
- 🔗 **Knowledge Graph** — Visual global/local graph with D3.js (38 nodes, 62 edges)
- 💬 **AI Chat** — 7-layer RAG with graph-aware injection + evidence tracking
- 👤 **Profile** — Personalized AI responses based on goals & working style
- 📦 **Context Packs** — Distilled knowledge packs from multiple files
- 🔌 **MCP Connector** — 21 tools for Claude AI integration
- 🔐 **Permission System** — Toggle tools on/off + admin key bypass
- 🌐 **Bilingual** — Thai/English toggle with 170+ translation keys

## MCP Integration

Connect Claude to your data via MCP Streamable HTTP:

```json
{
  "mcpServers": {
    "project-key": {
      "type": "streamable-http",
      "url": "https://project-key.fly.dev/mcp/{YOUR_SECRET_KEY}"
    }
  }
}
```

**21 Tools** in 4 categories:
| Category | Tools |
|----------|-------|
| 📖 Read & Search (10) | get_profile, list_files, get_file_content, get_file_summary, list_collections, list_context_packs, get_context_pack, search_knowledge, explore_graph, get_overview |
| ✏️ Create & Edit (5) | create_context_pack, add_note, update_file_tags, upload_text, update_profile |
| 🗑️ Delete (2) | delete_file, delete_pack |
| ⚙️ AI Pipeline (4) | run_organize, build_graph, enrich_metadata, admin_login |

## Project Structure

```
Project KEY/
├── index.html              # Frontend (691 lines — 7 pages + i18n)
├── app.js                  # Frontend logic (1,980 lines)
├── styles.css              # Dark theme design system (2,116 lines)
├── Dockerfile              # Production container (64 MB)
├── fly.toml                # Fly.io deployment config
│
├── backend/                # FastAPI backend (17 modules)
│   ├── main.py             # 40+ API endpoints + startup index rebuild
│   ├── mcp_tools.py        # 21 MCP tools + dispatcher + permissions
│   ├── mcp_tokens.py       # Bearer token management
│   ├── graph_builder.py    # Knowledge graph + entity extraction
│   ├── retriever.py        # 7-layer graph-aware RAG
│   ├── vector_search.py    # TF-IDF hybrid search
│   ├── database.py         # 18 SQLAlchemy models
│   ├── organizer.py        # AI clustering + scoring
│   ├── context_packs.py    # Context pack generation
│   ├── relations.py        # Backlinks + suggested relations
│   ├── metadata.py         # LLM metadata enrichment
│   ├── extraction.py       # Text extraction (PDF/TXT/MD/DOCX)
│   ├── markdown_store.py   # Summary file I/O
│   ├── profile.py          # User profile CRUD
│   ├── llm.py              # OpenRouter API wrapper
│   └── config.py           # Environment config
│
├── docs/                   # Documentation
│   ├── PROJECT_REPORT.md   # Full report (v0.1 → v4.3)
│   ├── prd/                # PRD v1, v2, v3, v4
│   ├── guides/             # User guides
│   └── screenshots/        # UI screenshots
│
└── tests/                  # All tests
    ├── e2e/                # End-to-end + MCP tests
    ├── testsprite/         # TestSprite automated tests (29 TCs)
    └── fixtures/           # Test data files
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML + Vanilla JS + CSS + D3.js v7 |
| Backend | Python FastAPI + Uvicorn |
| Database | SQLite (18 tables, async via aiosqlite) |
| Search | TF-IDF hybrid (in-memory auto-rebuild) |
| LLM | OpenRouter → Google Gemini 2.5 Flash |
| Deploy | Docker + Fly.io (Singapore region) |
| AI Integration | MCP Streamable HTTP (21 tools) |

## Version History

| Version | Highlights |
|---------|-----------|
| v0.1 | Upload, Organize, AI Chat |
| v2.0 | Profile, Context Packs, Hybrid Search |
| v3.0 | Knowledge Graph, i18n, Project Restructure |
| v4.0 | Fly.io Deploy, MCP 5 tools |
| v4.1 | 21 MCP tools, Data Management UX |
| v4.2 | Permission System, 4 categories, Thai complete |
| v4.3 | Search fix, add_note fix, startup index rebuild |

---

*Built with ❤️ by the Project KEY team*
