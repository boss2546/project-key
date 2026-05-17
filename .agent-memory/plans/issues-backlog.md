# 📋 Issues Backlog — All 188 Findings from Audit

> **Source:** User-commissioned audit 2026-05-17 (11 explore agents · 6 domains)
> **Status:** 6 critical items in [`fix-plan.md`](./fix-plan.md) (urgent hotfix)
> **This file:** Remaining ~60 items — ทำตอนมีเวลา/ระบบเสถียร
> **Last updated:** 2026-05-18

---

## 📊 Summary

| Severity | Total | In hotfix | Backlog |
|----------|------:|----------:|--------:|
| 🔴 P0 Critical | 24 | 6 | 18 |
| 🟠 P1 High | 34 | 0 | 34 |
| 🟡 P2 Medium | 27 | 0 | 27 |
| 🟢 P3 Low | 23 | 0 | 23 |
| **Total** | **108** | **6** | **102** |

(จริง ๆ มี ~188 ที่ระบุใน audits — ตารางนี้รวม dedupe)

---

## 🔴 P0 Critical — Backlog (18 items deferred)

ทำต่อหลัง hotfix ผ่าน · เรียงตาม impact

### Database integrity
1. **PRAGMA foreign_keys=ON missing** — `database.py:716` — orphan rows possible · → 30min fix
2. **N+1 query admin audit log** — `admin.py:1015` — admin slow on 50+ rows · → 30min
3. **Unbounded SELECT * (4 endpoints)** — `main.py:1732, 1748, 4340, 4603` — OOM at scale · → 4h pagination
4. **No FK ON DELETE CASCADE** — delete user → orphan rows · → 4-6h (table rebuild)
5. **No indexes on user_id columns** — slow filter at scale · → 30min add 5+
6. **`text-embedding-004` deprecated** — `config.py:106` — 404 if v11 enabled · → 15min default fix

### API contract
7. **Stack trace leak via `str(e)`** — 14 endpoints in `main.py` — info disclosure · → 2-4h unified handler
8. **No `response_model` (65+ endpoints)** — schema drift · → 1-2 days
9. **`mcp_secret` in `/api/me` response** — credential leak · → 1h
10. **MCP test endpoint returns 200 on auth fail** — `main.py:4791` — must be 401 · → 15min

### LLM safety
11. **LLM JSON output not validated** — `llm.py:178-191` — silent DB corruption · → 2h Pydantic schema
12. **`max_tokens=16384` no budget** — `llm.py:158` — cost runaway · → 2h per-user budget
13. **LlamaParse `BUDGET_CENTS=0`** — `config.py:336` — unlimited cost · → 1h guard
14. **Gemini Files no explicit cleanup** — `ai_ingest.py:207` — Google storage waste · → 2h delete + DB tracking

### Memory leaks
15. **`_login_fail_history` unbounded** — `main.py:260` — IP key never removed · → 1h cap + LRU
16. **`_user_indexes` TF-IDF unbounded** — `vector_search.py:15` — 25-50MB per heavy user · → 2h LRU
17. **`_STATE` progress tracker unbounded** — `progress_tracker.py:38` — gc_stale not auto · → 1h background task

### Thai language
18. **Thai tokenizer no word segmentation** — `vector_search.py:71` — search recall ~40% on Thai · → 4h PyThaiNLP

---

## 🟠 P1 High — Backlog (34 items)

### Performance / Concurrency
- `SUMMARY_CONCURRENCY=50` + SQLite single-writer = DB lock contention
- N+1 organizer parallel + shared session — `organizer.py:184`
- Single uvicorn worker = CPU 50%
- Embeddings `to_thread` no timeout — `embeddings.py:149`
- No frontend request dedup
- Polling no backoff — `app.js:391`
- Heartbeat starvation in upload worker
- 180s LLM timeout blocks workers

### Reliability / SPOF
- No DB backup policy — Fly volume เสีย = data loss
- `/health` ไม่ตรวจ DB — `main.py:1371`
- Resend / LlamaParse / LINE key เดียว — no fallback
- BackgroundTasks LINE webhook silent fail — `main.py:2164`
- Shared links / MCP permissions in-memory — restart loss
- Single primary Gemini key (#6 in hotfix addresses)

### Security
- MCP `/mcp/{secret}` no rate limit — brute force ได้
- Login throttle in-memory — restart = ลืม + multi-machine bypass
- Password reset no rate limit — `auth.py:327`
- File type validation extension-only — `.exe` rename `.txt` ผ่านได้
- MCP secret never rotates
- JWT HS256 symmetric — leak = invalidate all sessions
- `ALLOW_ADMIN_VIEW_PASSWORD` no alert on enable

### Database
- DateTime no timezone — `database.py:46-50` etc.
- String columns no length limit
- JSON in TEXT columns — can't query
- Audit/usage logs no retention policy

### Frontend
- Unbounded chat memory — 1000 messages = lag
- File list no pagination — `app.js:3038` — 5K files freeze
- Event listener leak in upload tray — `app.js:2465`
- LocalStorage no size check — quota exceed silent
- `onclick` with user input XSS risk — `app.js:3084, 3743`

### Ops
- Dockerfile single-stage + build deps in image (~250MB excess)
- Base image not pinned to digest
- `requirements-fly.txt` uses `>=` — no lock file
- No CI/CD pipeline
- No JSON logging / metrics / Sentry
- `fly.toml` no `kill_timeout` (— #2 partial in hotfix)

---

## 🟡 P2 Medium — Backlog (27 items)

### Workers / Async
- Concurrent DB session use in `organizer.py:184`
- Race condition File.processing_status="processing"
- Task reference loss during worker startup
- Temp file cleanup race in `ai_ingest.py`
- `_AVG_EXTRACT_SEC` no lock (race in metrics)
- No timeout on Gemini file upload poll — `ai_ingest.py:312`
- Organize lock recovery path not re-entrant

### LLM
- Forced Thai output even for English files — `organizer.py:324`
- Hard truncation in chat (2K/6K limits) — `retriever.py:157`
- Clustering only top-3 files sampled
- JSON markdown fence extraction fragile
- No surrogate sanitization in summary path
- Chunk failure inserts placeholder text — `organizer.py:431`
- `LLM_MODEL_PRO` = Flash (TEMP) — `config.py:31`

### Database
- Concurrent writer risk despite WAL
- VACUUM at boot causes startup delay (acceptable)
- Vector BLOB no metadata
- MCPUsageLog / WebhookLog missing user index

### Memory
- Gemini SDK clients module globals, no lifecycle
- `_worker_tasks` task refs leak on restart
- `email_cache` in admin function-local but builds per-request

### API
- No API versioning (`/v1/`)
- 404 vs 403 confusion for locked files
- No 201 Created on resource creation
- No idempotency support
- No Retry-After header (except login)

### Thai
- Encoding fallback `cp874` corrupts UTF-8
- No IME composition handling — frontend
- Thai numerals not handled (input)

---

## 🟢 P3 Low — Backlog (23 items)

### Cleanup
- Deprecated `OPENROUTER_*` constants in `config.py:35-36`
- `EMBEDDING_BATCH_SIZE` duplicated in 2 files
- Hardcoded `personaldatabank.fly.dev` (5+ files)
- 28+ `print()` in `database.py` (should be logger)
- Commented-out code blocks (`duplicate_detector.py:63`)
- Unused `window._usageData` — `app.js:670`

### Code quality
- `init_db()` 634 LOC monster function
- 9 other functions >100 LOC
- No `pyproject.toml` (ruff/black/mypy)
- No pre-commit hooks
- Type hints inconsistent (`dict[str, Any]` 15+)
- Missing docstrings on public functions
- Silent error suppression (10+ sites · `except (_): pass`)

### UX / Frontend
- i18n EN dict ~95% complete (some missing)
- Inline styles in onClick handlers
- Missing escape in onclick string templates
- Stale cache: admin probe flag no TTL
- Some buttons missing disable-during-submit

### CSS / Mobile
- Font stack no Thai-specific (— #2 partial fix later)
- Line height tight for Thai tone marks
- No backend error i18n (always EN)

### Tests
- Test coverage 0.6% (181 tests / 28K LOC)
- 47/51 modules untested
- 126 API endpoints untested
- TestRealAPI uses real Google APIs (flaky)
- No fuzz testing
- No load testing
- No staging environment

---

## 🗺 Domain Coverage

| Domain | Files audited | P0+P1 | In hotfix |
|--------|---------------|------:|----------:|
| Backend core (main.py, auth, admin) | ~6000 LOC | 18 | 3 (#1, #3, #5) |
| Database (schema, queries) | 1300 LOC | 13 | 0 |
| Workers / async | 5 modules | 8 | 0 |
| Security (auth flow, secrets) | 4 modules | 15 | 3 (#1, #3, #4, #5) |
| Deploy / Ops | Dockerfile, fly.toml | 11 | 1 (#2) |
| API contract | main.py endpoints | 14 | 0 |
| LLM safety | llm.py, organizer, ai_ingest | 13 | 0 |
| Memory / cache | 8 modules | 14 | 1 (#6) |
| Thai / i18n | vector_search, frontend | 10 | 0 |
| Test / quality | tests, configs | 9 | 0 |
| Frontend (XSS, pagination, etc.) | legacy-frontend/* | 22 | 1 (#1) |

---

## 🎯 Suggested Future Phases (เผื่อใช้)

ถ้าจะกลับมาทำ backlog แบ่งได้ตามนี้:

### Phase Next 1 — DB + API Foundation (~1 สัปดาห์)
- Foreign keys + indexes + pagination + N+1 fix
- Unified error handler + response_model 20 critical endpoints
- DB ping /health + input validation

### Phase Next 2 — Thai + Memory (~1 สัปดาห์)
- PyThaiNLP tokenizer + Unicode NFC + IME + CSS Thai font
- 5 memory cache cleanup tasks + LRU bounds
- Silent except sweep + print → logger

### Phase Next 3 — Rate Limit + LLM Safety (~1 สัปดาห์)
- Persistent rate limits (login, reset, MCP)
- Per-user token budget + LlamaParse guard + Gemini Files cleanup
- Prompt injection + magic bytes + LLM JSON validation

### Phase Next 4 — Tests + Ops + Refactor (~1 สัปดาห์)
- conftest + integration tests + CI/CD
- DB backup + Fly snapshot + JSON logging
- init_db refactor + cleanup deprecated

### Phase Next 5 — Final UI Test (~1 วัน)
- ฟ้า run 34 scenarios across 7 phases

---

## 📌 When to Revisit

Triggers ที่บอกว่าควรกลับมาทำ backlog:
- **User count > 50** → ทำ pagination + rate limits ก่อน scale issues
- **DB > 1GB** → ทำ indexes + retention policy
- **Multiple Fly machines** → ทำ JWT enforce (จัดการแล้วใน hotfix) + MCP/login persist
- **Cost > $100/month** → ทำ token budget + LlamaParse guard
- **Search complaint จาก Thai users** → ทำ PyThaiNLP tokenizer
- **Bug ในแล้วไม่รู้ว่าเกิดอะไร** → ทำ silent except sweep + JSON logging
- **เปลี่ยนระบบ + กลัวพัง** → ทำ tests + CI/CD ก่อน

---

**End of backlog · 102 items deferred**
