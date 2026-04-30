# 🛠️ Tech Stack

## Backend
- **Language:** Python 3.x
- **Framework:** FastAPI (รัน via `uvicorn backend.main:app`)
- **Database:** SQLite (`projectkey.db`) + ChromaDB (vector store ใน `/chroma_db/`)
- **Auth:** JWT (secret อยู่ใน `.jwt_secret`)
- **AI/LLM:** OpenRouter API (configurable models)
- **Payment:** Stripe (subscriptions, webhooks)

### Backend modules หลัก
- `main.py` — entry point + routes
- `auth.py` — JWT authentication
- `billing.py` — Stripe integration
- `database.py` — SQLite connection + queries
- `extraction.py` — extract text from files
- `graph_builder.py` — knowledge graph
- `llm.py` — LLM API client
- `mcp_tools.py` — MCP tool definitions
- `organizer.py` — AI organize logic
- `plan_limits.py` — subscription plan limits
- `relations.py` — file relations

## Frontend
- **Type:** Legacy (vanilla HTML/CSS/JS) — **ยังไม่ใช่ framework**
- **Files:**
  - `legacy-frontend/index.html` — main app
  - `legacy-frontend/app.js` — main JS
  - `legacy-frontend/styles.css` — styles
  - `legacy-frontend/pricing.html` — pricing page
- **API calls:** ผ่าน `fetch()` ปกติ ไม่มี state management library

## Infrastructure
- **Deployment:** Fly.io (`fly.toml`, `Dockerfile`)
- **MCP Proxy:** Node.js (`mcp-proxy.js`)
- **Testing:** pytest + Playwright (`playwright.config.js`)

## Dependencies หลัก
- ดูใน `requirements.txt` (Python)
- ดูใน `package.json` (Node.js — สำหรับ MCP proxy + Playwright)

## Environment Variables (`.env`)
- `OPENROUTER_API_KEY` — required
- Stripe keys (secret, webhook)
- ดู `.env.example` เป็น reference
- **ห้าม commit `.env` ลง git**

## Conventions
- ใช้ Python 3 type hints
- Comments + docstrings เป็นภาษาไทย (สำหรับ business logic)
- Variable names เป็นภาษาอังกฤษ
- Error responses format: `{ "error": { "code": "...", "message": "..." } }` (ตรวจสอบใน `main.py` ว่ายึดตามนี้จริง)
