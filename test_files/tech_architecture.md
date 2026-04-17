# Technical Architecture — Project KEY MVP v0.1

## System Overview

Project KEY MVP v0.1 ใช้ architecture แบบ monolith ที่เรียบง่าย เหมาะกับ MVP ที่ต้องเริ่มเร็ว

```
┌──────────────────────────────────────┐
│           Frontend (HTML/JS)          │
│  My Data | Organized View | AI Chat   │
└──────────────┬───────────────────────┘
               │ HTTP/REST
┌──────────────▼───────────────────────┐
│           FastAPI Backend             │
│  Upload | Organize | Chat | Summary   │
├───────────────────────────────────────┤
│  Extraction │ LLM Layer │ Vector Search│
└──────┬────────────┬──────────┬───────┘
       │            │          │
┌──────▼──┐  ┌──────▼──┐  ┌───▼────┐
│ SQLite  │  │OpenRouter│  │TF-IDF  │
│   DB    │  │  (LLM)  │  │ Index  │
└─────────┘  └─────────┘  └────────┘
```

## Component Details

### 1. Frontend Layer

- **Technology:** Vanilla HTML/CSS/JavaScript
- **Design:** Dark mode, Inter font, glassmorphism effects
- **Pages:** 3 screens (My Data, Organized View, AI Chat)
- **Communication:** REST API calls via fetch()
- **No build step required** — served directly by FastAPI

### 2. Backend Layer (FastAPI)

#### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/upload | Upload multiple files |
| GET | /api/files | List all files |
| DELETE | /api/files/:id | Delete a file |
| POST | /api/organize | Trigger AI organization |
| GET | /api/clusters | Get organized clusters |
| GET | /api/summary/:id | Get file summary |
| POST | /api/chat | Ask AI a question |
| GET | /api/stats | Get system statistics |
| DELETE | /api/reset | Clear all data |

### 3. Data Layer

#### SQLite Database (projectkey.db)

Tables:
- `users` — User accounts (single user for MVP)
- `files` — Uploaded files metadata
- `clusters` — AI-generated file groups
- `file_cluster_map` — File-to-cluster mappings
- `file_insights` — Importance scores
- `file_summaries` — Generated summaries + md_path
- `chat_queries` — Chat history with retrieval records

#### File Storage

- **Raw files:** `uploads/` directory
- **Summaries:** `summaries/` directory (.md files with YAML frontmatter)

### 4. AI/ML Layer

#### Document Parsing (Docling)
- IBM Docling for structured PDF/DOCX extraction
- Preserves document hierarchy (headings, tables, lists)
- Fallback to PyPDF2/python-docx if Docling fails

#### LLM Integration (OpenRouter)
- Model: Gemini 2.5 Flash
- Used for: clustering, scoring, summarizing, chat answers
- JSON mode for structured outputs

#### Vector Search (TF-IDF)
- Pure Python implementation (no model downloads)
- Paragraph-aware chunking (500 chars, 100 overlap)
- Cosine similarity scoring
- Thai + English tokenization

### 5. RAG Pipeline

```
User Question
     │
     ▼
┌─────────────┐
│ 1. Context  │ ← LLM selects relevant cluster + files
│   Selection │ ← Chooses retrieval mode (summary/excerpt/raw)
└──────┬──────┘
       ▼
┌─────────────┐
│ 2. Content  │ ← Loads selected content from DB/files
│   Assembly  │ ← Applies vector search for relevance
└──────┬──────┘
       ▼
┌─────────────┐
│ 3. Answer   │ ← LLM generates answer with sources
│  Generation │ ← Returns file references + reasoning
└─────────────┘
```

## Deployment

### Development
```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

### Production (Future)
- Docker Compose สำหรับ containerization
- PostgreSQL แทน SQLite
- S3-compatible storage แทน local filesystem
- Redis สำหรับ caching
