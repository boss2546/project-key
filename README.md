# 🔑 Project KEY — Knowledge Workspace

> Personal Knowledge Engine ที่ใช้ AI จัดระเบียบ วิเคราะห์ และเชื่อมโยงข้อมูลของคุณ

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

## Project Structure

```
Project KEY/
├── index.html              # Frontend — single page app
├── app.js                  # Frontend logic + i18n
├── styles.css              # Styles
├── requirements.txt        # Python dependencies
│
├── backend/                # FastAPI backend
│   ├── main.py             # API routes
│   ├── config.py           # Environment config
│   ├── database.py         # SQLite models
│   ├── llm.py              # LLM client (OpenRouter)
│   ├── extraction.py       # Text extraction (PDF/TXT/MD/DOCX)
│   ├── organizer.py        # AI clustering
│   ├── graph_builder.py    # Knowledge graph builder
│   ├── retriever.py        # RAG retriever
│   ├── vector_search.py    # ChromaDB vector search
│   ├── metadata.py         # Metadata enrichment
│   ├── relations.py        # Relation discovery
│   ├── context_packs.py    # Context pack generation
│   ├── profile.py          # User profile
│   └── markdown_store.py   # Summary storage
│
├── docs/                   # Documentation
│   ├── prd/                # Product requirements
│   ├── guides/             # User guides
│   └── screenshots/        # UI screenshots
│
├── tests/                  # All tests
│   ├── e2e/                # End-to-end tests
│   ├── testsprite/         # TestSprite automated tests
│   └── fixtures/           # Test data files
│
├── uploads/                # User uploaded files (gitignored)
├── summaries/              # AI-generated summaries (gitignored)
├── chroma_db/              # Vector store (gitignored)
└── projectkey.db           # SQLite database (gitignored)
```

## Features

- 📁 **My Data** — Upload & manage files (PDF, TXT, MD, DOCX)
- 🧠 **AI Organization** — Auto-cluster files into collections
- 🔗 **Knowledge Graph** — Visual global/local graph with D3.js
- 💬 **AI Chat** — RAG-powered Q&A with evidence tracking
- 👤 **Profile** — Personalized AI responses
- 🌐 **Bilingual** — Thai/English toggle (🇹🇭 / 🇺🇸)

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML + Vanilla JS + CSS + D3.js |
| Backend | Python FastAPI + Uvicorn |
| Database | SQLite |
| Vector DB | ChromaDB |
| LLM | OpenRouter (Google Gemini) |
