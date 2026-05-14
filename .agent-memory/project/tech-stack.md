# 🛠️ Tech Stack

## Backend
- **Language:** Python 3.11 (per Dockerfile)
- **Framework:** FastAPI (รัน via `uvicorn backend.main:app`)
- **Database:** SQLite (`projectkey.db`) + in-process TF-IDF index (vector_search.py)
- **Auth:** JWT (file fallback `.jwt_secret`, ควร set `JWT_SECRET_KEY` env var ใน production)
- **AI/LLM:** OpenRouter API (Gemini models) + Google Gemini direct (multimodal audio/video)
- **Payment:** Stripe (subscriptions, webhooks)
- **Storage:** Local volume OR Google Drive BYOS (per-user choice)
- **Bot:** LINE Messaging API + LINE Login

### Backend modules หลัก (43 modules — all reachable from main.py)
ดู [docs/manifest/ACTIVE-PRODUCTION-FILES.md](../../docs/manifest/ACTIVE-PRODUCTION-FILES.md) สำหรับรายชื่อเต็มพร้อมหน้าที่.

ตัวอย่างที่สำคัญ:
- `main.py` — entry point + 122 HTTP endpoints
- `auth.py`, `google_login.py` — auth (email/password + Google Sign-In)
- `billing.py`, `plan_limits.py` — Stripe + plan enforcement
- `database.py` — SQLAlchemy models + migrations
- `extraction.py`, `ai_ingest.py` — file → text (PDF/DOCX/OCR/audio/video)
- `graph_builder.py`, `relations.py` — knowledge graph
- `llm.py`, `retriever.py`, `organizer.py` — RAG + clustering
- `mcp_tools.py`, `mcp_tokens.py` — MCP server
- `line_bot.py`, `bot_handlers.py`, `bot_adapters.py`, `bot_messages.py`, `line_quota.py` — LINE bot
- `drive_*.py` (4 modules) — Google Drive BYOS
- `upload_worker.py` — async upload extraction loop

## Frontend
- **Type:** Legacy vanilla HTML/CSS/JS (no framework, no bundler)
- **Layout:** [legacy-frontend/](../../legacy-frontend/) — 24 files (6 HTML, 7 JS, 4 CSS, 7 PNG)
- **Entry HTML:** `landing.html`, `app.html`, `admin.html`, `pricing.html`, `auth-line.html`, `shared_pack.html`
- **API calls:** `fetch()` plain, no state-management library
- **Served by:** FastAPI [main.py:4144-4239](../../backend/main.py#L4144) via direct routes + wildcard `/{filename}` catch-all

## Infrastructure
- **Deployment:** Fly.io (`personaldatabank` app, region `sin`, 2GB RAM, volume `project_key_data` → `/app/data`)
- **Container:** `Dockerfile` (Python 3.11-slim + Tesseract OCR + Poppler)
- **Build:** `fly.toml` driven; Dockerfile COPYs only `backend/`, `legacy-frontend/`, `requirements-fly.txt`

## Dependencies
- **Python (Docker):** [requirements-fly.txt](../../requirements-fly.txt) — 33 packages incl. FastAPI, SQLAlchemy, Stripe, google-genai, line-bot-sdk, etc.
- **Local dev .env:** ดู [docs/deployment/.env.example](../../docs/deployment/.env.example) — 37 env vars annotated

## Environment Variables
- Code reads 37 vars total — `OPENROUTER_API_KEY`, Stripe keys, Google OAuth, Drive encryption key, LINE channels, MCP secret, etc.
- Full reference: [docs/deployment/.env.example](../../docs/deployment/.env.example)
- Live values: [.env](../../.env) (gitignored)
- **ห้าม commit `.env`** (triple-protected via .gitignore patterns)

## Conventions
- Python 3 type hints
- Comments + docstrings เป็นภาษาไทย (business logic) อธิบาย "WHY"
- Variable names เป็นภาษาอังกฤษ
- Error format: `{ "error": { "code": "...", "message": "..." } }`
- SQL ใช้ parameterized queries เสมอ
- Validate input ที่ API boundary

## Removed (เคยมี — ถูกลบใน cleanup session 2026-05-14)
- `tests/`, `scripts/` — test infrastructure (pytest + Playwright)
- `pytest.ini`, `playwright.config*.js`, `package.json`, `requirements.txt`, `mcp-proxy.js` — dev tooling
- `sandbox/`, `chroma_db/`, `node_modules/` — experimental / regenerable

ถ้าจะ revive ดูใน git log ก่อน 2026-05-14 หรือ tag `pre-cleanup-2026-05-14`
