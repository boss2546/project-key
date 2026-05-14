# 🟢 Active Production Files — Inventory

> **Purpose:** ระบุไฟล์ทุกตัวที่จำเป็นสำหรับการ run server ใน production (fly.io app `personaldatabank`)
> **Generated:** 2026-05-14
> **Physical snapshot:** [`production-active/`](../../production-active/) (gitignored — 71 code files + real `.env` + template + runbook = 75 files. ดู [production-active/README.md](../../production-active/README.md))
> **Deployment guide:** [`docs/deployment/RUNBOOK.md`](../deployment/RUNBOOK.md) · [`docs/deployment/.env.example`](../deployment/.env.example)
> **Source-of-truth:** [Dockerfile](../../Dockerfile) + [fly.toml](../../fly.toml) + transitively-imported modules from `backend.main:app`
>
> **กฎความเชื่อ:**
> - ไฟล์ใน list นี้ = **ห้ามลบ** จนกว่าจะตรวจสอบใหม่ทั้ง chain
> - ไฟล์ที่ไม่อยู่ใน list = อาจลบได้ (แต่อาจยังจำเป็นสำหรับ dev/test/docs/migration → ตรวจแยก)
> - "Reachable" หมายถึง import transitively จาก [backend/main.py](../../backend/main.py)

---

## 🐳 Container Build — สิ่งที่ Fly.io ใช้สร้าง image

ดู [Dockerfile](../../Dockerfile) บรรทัด 15-22 และ [fly.toml](../../fly.toml)

| File | Role |
|---|---|
| [Dockerfile](../../Dockerfile) | Build recipe (Python 3.11-slim + Tesseract OCR + Poppler) |
| [fly.toml](../../fly.toml) | Fly platform config (app=personaldatabank, region=sin, 2GB RAM, volume=project_key_data) |
| [requirements-fly.txt](../../requirements-fly.txt) | Python deps ที่ container ติดตั้ง (33 packages) |

**Entry point:** `python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000`

**Volume mount:** `/app/data` ← Fly volume `project_key_data` (runtime data ไม่อยู่ใน repo)

---

## 🐍 Backend — 44 Python files (43 modules + __init__.py)

ทุกไฟล์ใน `backend/` ถูก COPY เข้า container ใน Dockerfile บรรทัด 19.
**ทุก 43 modules reachable transitively จาก `main.py`** (ไม่มี dead module)

### Entry point
| File | Role | Imports (backend deps) |
|---|---|---|
| [backend/__init__.py](../../backend/__init__.py) | Python package marker (1 line) | — |
| [backend/main.py](../../backend/main.py) | FastAPI app + ALL HTTP routes (4240 lines, 200+ endpoints) | 33 modules |
| [backend/config.py](../../backend/config.py) | env config, APP_VERSION, BASE_DIR, secrets loading | — |
| [backend/database.py](../../backend/database.py) | SQLAlchemy models (User, File, Cluster, GraphNode, MCPToken, …) + init_db | config |

### Auth & Users
| File | Role |
|---|---|
| [backend/auth.py](../../backend/auth.py) | register/login/JWT/Google login/password reset · uses config, database, email_service |
| [backend/google_login.py](../../backend/google_login.py) | Google Sign-In OAuth flow · uses config |
| [backend/email_service.py](../../backend/email_service.py) | Email delivery via Resend (password reset, notifications) · uses config |
| [backend/profile.py](../../backend/profile.py) | User profile CRUD + completeness · uses database, personality, storage_router |
| [backend/personality.py](../../backend/personality.py) | MBTI/Enneagram validation · no backend deps |

### Storage & Files
| File | Role |
|---|---|
| [backend/storage_router.py](../../backend/storage_router.py) | Route file ops to server vs Drive backend · uses config, database, drive_* |
| [backend/upload_worker.py](../../backend/upload_worker.py) | Background async upload extraction loop (v9.4.0) · uses ai_ingest, database, duplicate_detector, extraction, storage_router |
| [backend/extraction.py](../../backend/extraction.py) | Text extraction PDF/DOCX/images (Tesseract OCR) · uses ai_ingest, llm |
| [backend/ai_ingest.py](../../backend/ai_ingest.py) | Gemini multimodal ingestion (audio/video) · uses extraction |
| [backend/duplicate_detector.py](../../backend/duplicate_detector.py) | Duplicate file detection (v7.1) · uses database, vector_search |
| [backend/vault.py](../../backend/vault.py) | Encrypted secrets vault · no backend deps |
| [backend/markdown_store.py](../../backend/markdown_store.py) | Markdown file storage · uses config |
| [backend/text_chunker.py](../../backend/text_chunker.py) | Text chunking for embeddings · no backend deps |
| [backend/vector_search.py](../../backend/vector_search.py) | TF-IDF in-process search index · no backend deps |
| [backend/signed_urls.py](../../backend/signed_urls.py) | HMAC signed URL generation (v7.6) · uses config |
| [backend/shared_links.py](../../backend/shared_links.py) | Public share link generation · no backend deps |

### Google Drive BYOS (v7.0)
| File | Role |
|---|---|
| [backend/drive_oauth.py](../../backend/drive_oauth.py) | Drive OAuth flow · uses config, drive_layout |
| [backend/drive_storage.py](../../backend/drive_storage.py) | Drive file CRUD operations · uses drive_layout, drive_oauth |
| [backend/drive_sync.py](../../backend/drive_sync.py) | Drive ↔ server sync · uses database, drive_layout, drive_oauth, drive_storage |
| [backend/drive_layout.py](../../backend/drive_layout.py) | Drive folder structure constants · no backend deps |

### AI / Knowledge Graph
| File | Role |
|---|---|
| [backend/llm.py](../../backend/llm.py) | OpenRouter LLM calls (Gemini 2.5 Flash) · uses config, extraction |
| [backend/organizer.py](../../backend/organizer.py) | File clustering + organization · uses config, database, llm, markdown_store, storage_router, text_chunker, vector_search |
| [backend/retriever.py](../../backend/retriever.py) | RAG retrieval for chat · uses context_packs, database, llm, profile, vector_search |
| [backend/graph_builder.py](../../backend/graph_builder.py) | Knowledge graph construction · uses database, llm, storage_router |
| [backend/relations.py](../../backend/relations.py) | File relation suggestions · uses database, llm |
| [backend/metadata.py](../../backend/metadata.py) | File metadata enrichment · uses database, llm |
| [backend/context_packs.py](../../backend/context_packs.py) | Context pack management · uses config, database, llm, vector_search |
| [backend/context_memory.py](../../backend/context_memory.py) | Per-conversation memory · uses database |
| [backend/ai_pack_builder.py](../../backend/ai_pack_builder.py) | AI Pack Builder v9.2 (assisted pack creation) · uses context_packs, database, llm, plan_limits |
| [backend/pack_share.py](../../backend/pack_share.py) | Context pack public sharing · uses config, context_packs, database, plan_limits, signed_urls |

### MCP (Model Context Protocol)
| File | Role |
|---|---|
| [backend/mcp_tokens.py](../../backend/mcp_tokens.py) | MCP token CRUD + validation · uses database |
| [backend/mcp_tools.py](../../backend/mcp_tools.py) | MCP tool registry (calls back into many modules) · uses 14 backend modules |

### Billing & Plans (Stripe)
| File | Role |
|---|---|
| [backend/billing.py](../../backend/billing.py) | Stripe checkout/portal/webhook · uses config, database, plan_limits |
| [backend/plan_limits.py](../../backend/plan_limits.py) | Plan tier enforcement (PLAN_LIMITS, lock/unlock data) · uses config, database |

### Admin
| File | Role |
|---|---|
| [backend/admin.py](../../backend/admin.py) | Admin panel endpoints · uses auth, config, database, line_quota, plan_limits |

### LINE Bot (v8.0)
| File | Role |
|---|---|
| [backend/line_bot.py](../../backend/line_bot.py) | LINE bot webhook + dispatch · uses 14 backend modules |
| [backend/bot_handlers.py](../../backend/bot_handlers.py) | Intent → handler routing · uses bot_adapters, bot_messages, config, database, duplicate_detector, extraction, plan_limits, retriever, signed_urls, storage_router, vector_search |
| [backend/bot_adapters.py](../../backend/bot_adapters.py) | LINE Message API wrapper · uses config, line_quota |
| [backend/bot_messages.py](../../backend/bot_messages.py) | LINE message templates · no backend deps |
| [backend/line_quota.py](../../backend/line_quota.py) | LINE monthly quota tracking · no backend deps |

---

## 🌐 Frontend — `legacy-frontend/` (24 files: 18 root + 6 guide)

ทุกไฟล์ใน `legacy-frontend/` ถูก COPY เข้า container ใน Dockerfile บรรทัด 22.
HTML/JS/CSS เสิร์ฟผ่าน FastAPI routes ใน [main.py:4144-4239](../../backend/main.py#L4144).

### HTML pages (6 files)
ทุกไฟล์มี route map ตรงๆ ใน [main.py](../../backend/main.py)

| File | Route | Referenced JS/CSS |
|---|---|---|
| [legacy-frontend/landing.html](../../legacy-frontend/landing.html) | `/`, `/legacy`, `/reset-password` | landing.css, landing.js, shared.css |
| [legacy-frontend/app.html](../../legacy-frontend/app.html) | `/app` | app.js, styles.css, shared.css, line_ui.js, storage_mode.js |
| [legacy-frontend/admin.html](../../legacy-frontend/admin.html) | `/admin` | admin.js, styles.css, shared.css |
| [legacy-frontend/pricing.html](../../legacy-frontend/pricing.html) | `/pricing` | landing.css, shared.css |
| [legacy-frontend/auth-line.html](../../legacy-frontend/auth-line.html) | `/legacy/auth-line.html` | auth-line.js, styles.css |
| [legacy-frontend/shared_pack.html](../../legacy-frontend/shared_pack.html) | `/legacy/shared_pack.html` | shared_pack.js, shared_pack.css |

### JS (7 files)
| File | Used by |
|---|---|
| [legacy-frontend/landing.js](../../legacy-frontend/landing.js) | landing.html (auth flow + Google login redirect) |
| [legacy-frontend/app.js](../../legacy-frontend/app.js) | app.html (main workspace shell — files, graph, chat, profile, MCP) |
| [legacy-frontend/admin.js](../../legacy-frontend/admin.js) | admin.html (admin panel UI) |
| [legacy-frontend/auth-line.js](../../legacy-frontend/auth-line.js) | auth-line.html (LINE account linking) |
| [legacy-frontend/shared_pack.js](../../legacy-frontend/shared_pack.js) | shared_pack.html (public pack viewer) |
| [legacy-frontend/line_ui.js](../../legacy-frontend/line_ui.js) | app.html (LINE bot connection UI) |
| [legacy-frontend/storage_mode.js](../../legacy-frontend/storage_mode.js) | app.html (BYOS storage mode toggle) |

### CSS (4 files)
| File | Used by |
|---|---|
| [legacy-frontend/landing.css](../../legacy-frontend/landing.css) | landing.html, pricing.html |
| [legacy-frontend/styles.css](../../legacy-frontend/styles.css) | app.html, admin.html, auth-line.html (main app styles) |
| [legacy-frontend/shared.css](../../legacy-frontend/shared.css) | landing.html, app.html, admin.html, pricing.html (shared tokens) |
| [legacy-frontend/shared_pack.css](../../legacy-frontend/shared_pack.css) | shared_pack.html |

### Images (7 files)
| File | Used by |
|---|---|
| [legacy-frontend/line-rich-menu.png](../../legacy-frontend/line-rich-menu.png) | LINE bot rich menu (uploaded via [scripts/setup/setup_line_rich_menu.py](../../scripts/setup/setup_line_rich_menu.py)) |
| `legacy-frontend/guide/chatgpt-{1..6}-*.png` | MCP setup guide in app.html (ChatGPT MCP config screenshots) |

---

## 📦 Runtime Data — NOT in repo (volume-mounted)

ข้อมูลพวกนี้อยู่ใน Fly volume `project_key_data` ที่ mount เป็น `/app/data` — ไม่อยู่ใน git repo และไม่ใช่ส่วนหนึ่งของ deployment artifact

| Path on volume | Created by | Contents |
|---|---|---|
| `/app/data/uploads/` | upload_worker | User-uploaded files (PDF/DOCX/images/audio/video) |
| `/app/data/summaries/` | organizer | AI-generated summaries |
| `/app/data/context_packs/` | context_packs | Context pack markdown files |
| `/app/data/backups/` | manual / scripts | SQLite DB backups |
| `/app/data/projectkey.db` | database.init_db | Main SQLite database (users, files, graph, mcp_tokens, billing, …) |
| `/app/data/.jwt_secret` | auth.py (first run) | JWT signing secret (auto-generated if missing) |
| `/app/data/.mcp_secret` | mcp_tokens | MCP server-wide secret |

> ⚠️ Production data integrity = volume integrity. ห้ามลบ volume โดยไม่มี backup

---

## ❌ NOT in production deployment

ไฟล์/folder เหล่านี้ **ไม่ได้** ถูก COPY เข้า container — เหลือไว้แค่ใน repo (สำหรับ dev/test/docs):

| Path | Why kept in repo |
|---|---|
| [tests/](../../tests/) | 125 pytest + Playwright tests (dev only) |
| [scripts/](../../scripts/) | Smoke tests, e2e verifies, maintenance scripts (dev/CI only) |
| [docs/](../../docs/) | Documentation, including this file |
| [.agent-memory/](../../.agent-memory/) | Multi-agent team memory + plans + history |
| [sandbox/](../../sandbox/) | **landing-v4 experiment** (deletable — see review notes) |
| [backups/](../../backups/) | Local DB snapshots (gitignored runtime artifact) |
| [chroma_db/](../../chroma_db/) | Local vector DB (gitignored runtime, regenerable) |
| [node_modules/](../../node_modules/) | Playwright deps for browser tests (gitignored) |
| [playwright.config.js](../../playwright.config.js) + .standalone.js | Playwright test config |
| [package.json](../../package.json) + lock | Frontend test deps |
| [requirements.txt](../../requirements.txt) | Local dev deps (Docker uses `requirements-fly.txt` instead) |
| [pytest.ini](../../pytest.ini) | pytest config |
| [mcp-proxy.js](../../mcp-proxy.js) | Local MCP proxy for development |
| [skills/](../../skills/) + [skills-lock.json](../../skills-lock.json) | Claude Code skills config |
| [REPORT-*.md](../../docs/reports/) | Release reports |
| [DESIGN.md](../../DESIGN.md), [README.md](../../README.md) | Project docs |

---

## 🔢 Counts Summary

| Category | Files | Notes |
|---|---|---|
| **Container config** | 3 | Dockerfile, fly.toml, requirements-fly.txt |
| **Backend** | 44 | 43 modules + __init__.py, all transitively reachable from main.py |
| **Frontend** | 24 | 6 HTML + 7 JS + 4 CSS + 1 line PNG + 6 guide PNGs |
| **TOTAL PRODUCTION** | **71** | (excludes runtime volume data) |

---

## ✅ Cross-check method

ใช้คำสั่งนี้ verify ทุก backend file ถูก trace แล้ว:

```bash
python -c "
import ast
from pathlib import Path

graph = {}
for f in Path('backend').glob('*.py'):
    if f.name == '__init__.py': continue
    mod = f.stem
    imports = set()
    tree = ast.parse(f.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level == 1:
            if node.module: imports.add(node.module.split('.')[0])
            else: imports.update(a.name for a in node.names)
    graph[mod] = imports

# BFS from main
reachable, todo = set(), ['main']
while todo:
    m = todo.pop()
    if m in reachable or m not in graph: continue
    reachable.add(m)
    todo.extend(graph[m] & set(graph.keys()) - reachable)

unreachable = set(graph) - reachable
print(f'Reachable: {len(reachable)}/{len(graph)}; Unreachable: {sorted(unreachable)}')
"
# Expected output: Reachable: 43/43; Unreachable: []
```

---

## 📝 Last verified

- **Generated:** 2026-05-14
- **Verified entry:** `backend.main:app` via [Dockerfile:32](../../Dockerfile#L32)
- **APP_VERSION at generation:** 9.4.8 (from [backend/config.py](../../backend/config.py))
- **Fly app:** `personaldatabank` (renamed from `project-key` on 2026-05-01)
