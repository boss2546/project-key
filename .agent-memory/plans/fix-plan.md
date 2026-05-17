# 🛠 Fix Plan v2 — Unified · เขียวคนเดียว

> **Created:** 2026-05-18 (v2 = revised after self-review)
> **Owner:** เขียวคนเดียว (me) · **Reviewer:** ฟ้า
> **Total milestones:** 66 · **Total days:** ~17-18 sprint-days (~3.5 สัปดาห์)
> **Closes:** 188 audit findings → production-ready
> **Changelog v1→v2:** +6 milestones · sequencing fixes · Sprint 2 rebalanced · deploy procedure · staging plan

---

## 🎯 Mission

User audit ระบบเจอ **188 findings** (24 P0, 34 P1) → ห้ามเปิด public launch
แผนนี้ทำให้ระบบพร้อมเปิด public ภายใน ~3.5 สัปดาห์

---

## 📅 Sprint Roadmap

| Sprint | Theme | Days | Milestones |
|--------|-------|-----:|:----------:|
| **0** | Security Emergency | 1.5 | 11 |
| **1** | DB + API Contract | 5 | 12 |
| **2** | Thai + Memory + Silent Errors | 5 | 12 |
| **3** | Rate Limit + LLM Safety + Frontend | 5 | 16 |
| **4** | Tests + Ops + Refactor | 5 | 15 |
| **F** | ฟ้า Final UI Test | 1 | 34 scenarios |

**Sprint 0 = วันแรก (อาจล้นวันที่ 2)** · Sprint 1-4 ตามคิว · จบด้วย ฟ้า final UI

---

## 🚦 Rules

1. **1 branch / sprint:** `fix/sprint-0`, `fix/sprint-1`, ...
2. **Commit tag:** `[S0.X]`, `[S1.X]`, ...
3. **Deploy:** ปลาย sprint เท่านั้น (Sprint 0 = emergency) — ดู Deploy Procedure ด้านล่าง
4. **Migration:** ทุก ALTER TABLE → backup ก่อน + try/except + idempotent
5. **Backwards compat:** API change ต้องมี grace period 30 วัน
6. **Test first:** มี test ก่อน implement (TDD where reasonable)
7. **Sprint end:** ส่งฟ้า review ผ่าน `for-ฟ้า.md` ทุก sprint
8. **CHANGELOG.md:** Update ทุก milestone end (1 บรรทัด)
9. **Cost guard:** ตั้ง Google Cloud + Fly budget alert $X/day ก่อนเริ่ม Sprint 1 (S1.X test load มาก)

---

## 🚀 Sprint Deploy Procedure

ทุก sprint end ใช้ procedure นี้:

1. **Pre-deploy** (~30 min)
   - `flyctl postgres backup create` (หรือ `flyctl ssh sftp get projectkey.db backup.db`)
   - Tag release: `git tag v10.0.XX-sprintN`
   - Update CHANGELOG.md
2. **Deploy** (~5 min)
   - `flyctl deploy --remote-only`
   - Watch logs: `flyctl logs -a personaldatabank --tail`
3. **Smoke test** (~5 min)
   - `/health` 200 + version ตรง
   - Login + 1 upload + 1 chat + admin endpoint
4. **Cool-down monitor** (30 min)
   - watch logs for errors
   - ถ้าเจอ regression: `flyctl releases rollback`
5. **Close sprint** (5 min)
   - Update `pipeline-state.md`
   - Send `for-ฟ้า.md` MSG
   - Wait ฟ้า APPROVED ก่อน open next sprint branch

---

## 🧪 Staging / Test Environment

**Migration-heavy items (S0.2, S0.3 Phase 3, S1.5 FK rebuild) ต้อง test ก่อน prod:**

Options:
- **A** สร้าง `personaldatabank-staging` Fly app + clone prod DB (1-time setup, ~$5/mo)
- **B** Local Docker + clone DB (free แต่ container ไม่เหมือน Fly env 100%)
- **C** SQL dry-run on local DB clone (rehearsal เฉพาะ migration script)

**แนะนำ B** สำหรับเริ่ม + escalate ถ้าเจอ Fly-specific issues

---

# 🚨 Sprint 0 — Security Emergency (1.5 days, ~10 ชม.)

## Goal
ปิดรู security ที่ public-facing risk + เตรียม schema ที่ sprint หลังๆ ใช้

> **Sequence:** S0.0 (clean orphans + audit) → S0.1 (rotate) → schema work (S0.2 → S0.0a → S0.10) → security code (S0.3-S0.9) → S0.11 deploy

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S0.0** | Audit orphan rows ก่อน enable FK (`SELECT COUNT(*) FROM files WHERE user_id NOT IN (SELECT id FROM users)` เป็นต้น 5 ตาราง) → ลบหรือ assign ถ้าเจอ | orphan count = 0 ทุกตาราง · log result | 30min |
| **S0.0a** | Schema pre-create migrations: `login_attempts`, `mcp_permissions`, `user_token_usage` (เปล่าๆ — ใช้ใน Sprint 2-3) | `PRAGMA table_info` ทั้ง 3 tables ปรากฏ | 30min |
| **S0.1** | Rotate secrets ทั้งหมด (OpenRouter, Stripe, Google OAuth, Picker, LlamaCloud, GoogleAPI) + clean `.env` จาก git history | smoke test ทุก integration · `git log --all -- .env` empty | 2-3h |
| **S0.2** | `PRAGMA foreign_keys=ON` + SQLAlchemy event listener | `_test_database.py::test_fk_enabled` result == 1 | 30min |
| **S0.3** | Drop `plaintext_password` Phase 1 (stop writes) + Phase 2 (remove endpoint + `ALLOW_ADMIN_VIEW_PASSWORD` flag) — **Phase 3 = S1.0** | `_test_auth.py::test_no_plaintext_on_register` · admin endpoint 404 | 1h |
| **S0.4** | JWT secret env enforce — Fly machine fail-hard ถ้าไม่ตั้ง | `_test_config.py::test_jwt_fails_hard_on_fly_no_env` | 45min |
| **S0.5** | ADMIN_PASSWORD soft fail — warn + admin endpoint 503 (ไม่ sys.exit) | `_test_config.py::test_no_admin_password_warns_not_crashes` | 45min |
| **S0.6** | Chat XSS fix — ลบ `isHtml` flag · ใช้ `textContent`/escape เสมอ (`legacy-frontend/app.js:5118`) | inject `<script>` ใน LLM response → escape · pentest pass | 30min |
| **S0.7** | `EMBEDDING_MODEL` default → `gemini-embedding-001` (verify no Fly env override กระทบ prod) | `_test_embeddings.py::TestRealAPI` ผ่าน (3072-d) | 15min |
| **S0.8** | Dockerfile `USER non-root` + `HEALTHCHECK` + `.dockerignore` clean | `docker run` user != root · HEALTHCHECK pass · image ไม่มี `.env*` | 30min |
| **S0.9** | `fly.toml` `kill_signal="SIGTERM"` + `kill_timeout="30s"` | rolling deploy ไม่ตัดเชื่อมโยง mid-upload | 15min |
| **S0.10** | `.gitignore` clean (`.env`, `__pycache__`, `.venv`, secrets files, `*.db`) + pre-commit skeleton | `git status -i` ปกติ · pre-commit installed (config ใน S4) | 15min |
| **S0.11** | Set `GEMINI_API_KEY_BACKUP` on Fly + verify failover (smoke test 429 path) | `flyctl secrets list` มี backup · failover log แสดง switch | 30min |

### Sprint 0 Acceptance Gate
- [ ] Orphan rows audit clean
- [ ] 3 future tables pre-created
- [ ] Secrets rotated · all smoke pass · `.env` หายจาก git history
- [ ] FK enforce on · plaintext_password Phase 1+2 done
- [ ] JWT env enforce active บน Fly · ADMIN_PASSWORD soft fail
- [ ] Chat XSS test pass · pentest 1 round
- [ ] Container non-root · `.dockerignore` clean
- [ ] Backup Gemini key active · failover verified
- [ ] Deploy `v10.0.30-sprint0` + smoke pass
- [ ] CHANGELOG updated
- [ ] ส่งฟ้า review

---

# 🛠 Sprint 1 — DB + API Contract (5 days)

## Goal
แก้ DB perf + สร้าง consistent API contract

> **Sequence:** S1.0 (DROP COLUMN — รอ S0.3 ครบ 24h) → S1.7 (unified error first) → S1.1-S1.6 + S1.8-S1.11 (ใช้ error shape ใหม่)
> **Frontend coordination:** S1.1, S1.2, S1.7, S1.8 — เปลี่ยน frontend ใน same commit เสมอ

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S1.0** | Drop `plaintext_password` Phase 3 (COLUMN DROP after S0.3 Phase 1+2 deploy 24h) | `PRAGMA table_info(users)` ไม่มี `plaintext_password` | 1h |
| **S1.7** | Unified error handler — `{"error":{"code","message","request_id"}}` + middleware request_id + sweep 14 `str(e)` sites (do FIRST) | 500 ไม่มี stack trace · all status code unified shape · request_id in response headers | 4-6h |
| **S1.1** | Pagination `/api/files` (cursor-based, default 50, max 200) **+ frontend** update fetch loop + show "Load more" | 120 files → page 1 (50) + cursor + page 2 (50) + page 3 (20) | 4h |
| **S1.2** | Pagination `/api/clusters` + `/api/export` (chunked stream) + `delete-account` (batch 500) **+ frontend** | export 5K files <30s ไม่ OOM · delete-account ไม่ timeout | 4h |
| **S1.3** | Fix N+1 admin audit log (`admin.py:1015-1033`) → JOIN | query count 50 → ≤2 · admin audit 100 rows load <2s | 1h |
| **S1.4** | Add indexes: `files(user_id)`, `clusters(user_id)`, `context_packs(user_id)`, `graph_nodes(user_id, object_type)`, `audit_logs(user_id, created_at)` | `EXPLAIN QUERY PLAN` ใช้ index · 5x faster benchmark 10K rows | 1h |
| **S1.5** | FK `ON DELETE CASCADE` table rebuild — **test บน local clone DB ก่อน prod** | delete user → ทุก child rows หาย · pre-migration backup verified | 6h |
| **S1.6** | DB ping ใน `/health` (timeout 2s, 503 ถ้า fail) | DB down → 503 · DB up → 200 (latency <50ms) | 1h |
| **S1.8** | ลบ `mcp_secret` จาก `/api/me` + new `/api/mcp/credentials` (require password reauth) **+ frontend** prompt password | `/api/me` no mcp_secret · wrong password → 401 | 2h |
| **S1.9** | MCP test endpoint `/api/mcp/test` คืน 401 (ไม่ 200) ตอน auth fail | invalid auth → 401 | 15min |
| **S1.10** | Input validation: `ChatRequest.question` max_length=5000, file upload size actual bytes, pagination bounds (ge=1, le=200) | 422 บน invalid · Content-Length โกง → reject | 2h |
| **S1.11** | `response_model` สำหรับ **20 critical endpoints** (ระบุชัดข้างล่าง) | OpenAPI schema ทุก endpoint · no sensitive field leak | 6h |

### 20 critical endpoints for S1.11
```
1.  GET  /api/me                     → MeResponse
2.  POST /api/auth/login             → AuthTokenResponse
3.  POST /api/auth/register          → AuthTokenResponse
4.  POST /api/auth/refresh           → AuthTokenResponse
5.  POST /api/auth/request-reset     → MessageResponse
6.  POST /api/auth/reset-password    → MessageResponse
7.  GET  /api/files                  → FileListResponse (paginated)
8.  GET  /api/files/{id}             → FilePublic
9.  POST /api/files/{id}/retry       → FilePublic
10. DELETE /api/files/{id}           → DeleteResponse
11. GET  /api/clusters               → ClusterListResponse
12. POST /api/chat                   → ChatResponse
13. POST /api/organize               → OrganizeStatusResponse
14. POST /api/organize-new           → OrganizeStatusResponse
15. POST /api/upload                 → UploadResponse
16. GET  /api/context-packs          → ContextPackListResponse
17. POST /api/mcp/credentials        → MCPCredentialsResponse
18. GET  /api/admin/users            → AdminUserListResponse (paginated)
19. GET  /api/healthz/queue          → QueueHealthResponse
20. GET  /api/usage                  → UsageResponse
```

### Sprint 1 Acceptance Gate
- [ ] plaintext_password column gone (S1.0)
- [ ] Unified error shape ทุก endpoint (S1.7) · request_id middleware active
- [ ] 4 endpoints มี pagination + frontend update · stream + batch ทำงาน
- [ ] N+1 audit fix · 5 indexes present · FK CASCADE verified
- [ ] /health DB-aware
- [ ] mcp_secret ไม่ leak · MCP test 401
- [ ] Input validation strict
- [ ] 20 endpoints มี response_model + OpenAPI schema complete
- [ ] Deploy `v10.0.31-sprint1` per procedure
- [ ] CHANGELOG updated · ส่งฟ้า review

---

# 🇹🇭 Sprint 2 — Thai + Memory + Silent Errors (5 days)

## Goal
แก้ search ไทยที่พังโครงสร้าง + memory leaks + silent error sweep

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S2.1** | PyThaiNLP `word_tokenize` ใน `vector_search.py:_tokenize()` + bench corpus 50 queries | "การจัดการข้อมูล" → ≥3 tokens · recall ≥80% (baseline 40%) | 4h |
| **S2.2** | Unicode NFC ใน `duplicate_detector.py:normalize_text()` | NFC vs NFD ของ "ที่" → hash เท่ากัน · 5 Thai pair tests | 30min |
| **S2.3** | CSS `font-family: 'Noto Sans Thai', 'Inter', ...` + line-height 1.7 + Google Fonts CDN | iOS Safari 11 render ครบ · tone mark ไม่ทับ | 1h |
| **S2.4** | IME composition: ฟัง `compositionstart`/`compositionend` ก่อน fire search/chat handlers | พิมพ์ "ข้อมูล" ผ่าน Thai IME → search fire 1 ครั้ง | 2h |
| **S2.5** | Encoding fallback: `chardet` detect ก่อน fallback chain (`extraction.py:564`) | UTF-8 + cp874 fixtures decode ถูกต้อง · ไม่ garble | 2h |
| **S2.6** | progress_tracker `gc_stale()` auto-run ทุก 2 นาที ผ่าน asyncio background task | mock 1000 stale → cleanup ตัดเหลือ 0 ใน 5 นาที | 1h |
| **S2.7** | `_shared_links` periodic cleanup ทุก 5 นาที | dict size stable หลัง 1000 link + 30 นาที (soak test) | 1h |
| **S2.8** | `_STATE_CACHE` (OAuth) periodic cleanup ทุก 5 นาที | stale states หายใน 10 นาที | 1h |
| **S2.9** | TF-IDF LRU `_user_indexes` max 100 files/user | user 200 files → cache ≤100 · 24h soak RSS stable | 3h |
| **S2.10** | `_login_fail_history` cap 10K IPs + LRU eviction (interim ก่อน S3.1 DB persist) | 11K IPs → cap ที่ 10K · eviction policy correct | 1h |
| **S2.11** | Silent except sweep — `logger.exception()` ทุก `except: pass` (10+ sites) + replace 28+ `print()` ใน database.py → `logger.*()` | `grep -E "except.*:\s*pass"` = 0 · `grep "print(" backend/database.py` = 0 | 4h |
| **S2.12** | LLM JSON schema validation — map ทุก callers + Pydantic validate + retry once + log on fail | inject bad type → reject + retry · log entry มี | 3h |

### Sprint 2 Acceptance Gate
- [ ] Thai search recall ≥80% (golden corpus)
- [ ] NFC dedup works · 5 Thai pair tests pass
- [ ] CSS Thai font render ดีบน iOS · screenshot diff approved
- [ ] IME composition handled · manual test ผ่าน
- [ ] Encoding detect ถูก
- [ ] 4 memory caches มี cleanup task · 24h soak RSS stable
- [ ] TF-IDF LRU + login throttle bounded
- [ ] Silent except = 0 · print() in database.py = 0
- [ ] LLM JSON validate
- [ ] Deploy `v10.0.32-sprint2` per procedure
- [ ] CHANGELOG updated · ส่งฟ้า review

---

# 🛡 Sprint 3 — Rate Limit + LLM Safety + Frontend (5 days)

## Goal
Persistent rate limits + LLM cost/safety + frontend hardening

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S3.1** | Login throttle DB persist (`login_attempts` table — S0.0a) — restart survives | 5 fails → restart → 6th still blocked | 3h |
| **S3.2** | Password reset rate limit — 5/hour/email + 10/hour/IP | 6 reset/hour → 429 | 1h |
| **S3.3** | MCP `/mcp/{secret}` rate limit + auto-rotate on 100 fail/hour | brute force → 429 · lock 1h · audit log + email alert | 3h |
| **S3.4** | MCP permissions persist to DB (`mcp_permissions` table — S0.0a) — restart survives | disable tool → restart → ยัง disabled | 2h |
| **S3.5** | Per-user token budget (`user_token_usage` table — S0.0a) — check ก่อน LLM call | user เกิน quota → 429 · monthly reset · admin override | 4h |
| **S3.6** | LlamaParse budget guard — check `cost_cents_30d_total` ก่อนเรียก API | mock spend ใกล้ cap → block | 1h |
| **S3.7** | Gemini Files explicit cleanup — `files.delete()` หลังใช้ + DB tracking + `api_key_suffix` (key affinity) | upload → use → delete · list ไม่มี stale · key affinity preserved | 3h |
| **S3.8** | Prompt injection escape: escape user question ใน `retriever.py:424` | "ignore previous instructions" → LLM ทำตาม system prompt | 1h |
| **S3.9** | Chunk retry jitter (`organizer.py:427`) — `random.random()` ±20% | mock 3 chunks fail → retry timing variance ≥20% | 1h |
| **S3.10** | File magic bytes — `python-magic` verify content vs ext | `.exe` rename `.txt` → reject · genuine PDF accept | 2h |
| **S3.11** | `LLM_MODEL_PRO` → `gemini-2.5-pro` + quality regression test (A/B 10 sample) | Pro ≥80% rated better than Flash baseline | 2h |
| **S3.12** | Frontend XSS hardening — `onclick="${f.id}"` → `data-id="${escapeHtml(f.id)}"` + event delegation | filename มี `'"><script>` → no XSS · click ทำงาน | 3h |
| **S3.13** | Frontend pagination — file list (50/page virtual scroll) + cluster + graph | 5K files render 50 · scroll 60fps · LCP <2.5s | 4h |
| **S3.14** | Polling backoff — organize status: 500ms→5s exponential, max 20 retries | backend 500 → frontend backoff · recover ตอน restart | 2h |
| **S3.15** | localStorage size check — try-catch wrapper + size estimate · graceful fallback | mock quota exceed → no crash · log warning | 1h |
| **S3.16** | Button disable + AbortController on duplicate click | double-click submit → 1 request ส่ง · concurrent abort works | 2h |

### Sprint 3 Acceptance Gate
- [ ] Rate limits persist across restart (login + reset + MCP)
- [ ] MCP brute force blocked + alert
- [ ] Token + LlamaParse budget guards active
- [ ] Gemini Files cleanup + key affinity preserved
- [ ] Prompt injection mitigated
- [ ] Magic bytes catch fake files
- [ ] LLM_MODEL_PRO = Pro · quality regression pass
- [ ] No XSS via onclick · frontend lists smooth at 5K
- [ ] Polling has backoff · double-click safe
- [ ] Deploy `v10.0.33-sprint3` per procedure
- [ ] CHANGELOG updated · ส่งฟ้า review

---

# 🧪 Sprint 4 — Tests + Ops + Refactor (5 days)

## Goal
Test infrastructure + CI/CD + observability + backup strategy + cleanup tech debt

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S4.1** | `conftest.py` fixtures: `db_engine`, `db_session`, `client`, `user`, `user_token`, `admin_user`, `admin_token` + test data fixtures (Thai/EN samples) | All tests ใช้ fixtures ได้ · 5K file fixture script ทำงาน | 3h |
| **S4.2** | Auth integration tests ≥15 (register → verify → login → refresh → reset → logout + edge cases) | 15/15 pass | 4h |
| **S4.3** | Endpoint integration tests ≥20 (/api/files CRUD + clusters + organize + permission isolation + multi-tenant) | 20/20 pass | 6h |
| **S4.4** | DB integration tests (migration safety + concurrent write WAL + FK cascade) | All migrations idempotent · WAL verified | 2h |
| **S4.5** | `pyproject.toml`: ruff + black + mypy + pytest config | `ruff check`, `mypy backend/`, `pytest` ทั้งหมดผ่าน | 2h |
| **S4.6** | GitHub Actions `.github/workflows/test.yml` — lint + test + secret-scan (detect-secrets) | PR triggers all checks · green ก่อน merge | 2h |
| **S4.7** | Pre-commit hooks: detect-secrets + ruff (S0.10 prep) | `git commit` ใส่ secret = block | 1h |
| **S4.8** | Dependencies pin + lock file (`pip-tools` → `requirements.lock`) | reproducible build · exact versions | 2h |
| **S4.9** | Base image digest pin (`python:3.11.9-slim@sha256:...`) | Dockerfile FROM มี `@sha256:` | 30min |
| **S4.10** | JSON structured logging — middleware + formatter + request_id correlation | Fly logs parsable JSON · timestamp + level + request_id | 2h |
| **S4.11** | DB backup strategy: daily `scripts/backup.py` + `scripts/test_restore.py` + Fly volume snapshot policy | restore drill pass · volume snapshots active | 3h |
| **S4.12** | Refactor `init_db()` 634 LOC → versioned migrations `backend/migrations/000X_*.py` (alembic-style minimal) | Old DB upgrade ผ่าน · fresh install ผ่าน · each migration ≤100 LOC | 6h |
| **S4.13** | Remove `OPENROUTER_API_KEY` + `OPENROUTER_BASE_URL` deprecated constants + hardcoded `personaldatabank.fly.dev` → use `APP_BASE_URL` | `grep OPENROUTER backend/` = 0 · `grep personaldatabank backend/` ≤ 1 (in APP_BASE_URL default) | 1h |
| **S4.14** | Audit log retention job (`scripts/audit_log_cleanup.py` daily, 90-day retention) | run script → old logs ลบ · row count ลดลง | 1h |
| **S4.15** | Documentation pass: update `CLAUDE.md` schema + API + config sections · update README test running · add `runbooks/deploy.md` + `runbooks/restore.md` | docs match current state | 2h |

### Sprint 4 Acceptance Gate
- [ ] conftest.py fixtures + test data complete
- [ ] ≥35 integration tests pass · coverage ≥25%
- [ ] CI green บน PR · secret scan pre-commit work
- [ ] Deps pinned + lock · base image digest
- [ ] JSON logging on Fly
- [ ] DB backup tested · restore drill ผ่าน · Fly snapshots active
- [ ] init_db refactored · old + fresh install both work
- [ ] Deprecated constants removed
- [ ] Audit log retention working
- [ ] Docs updated
- [ ] Deploy `v10.0.34-sprint4` (final pre-launch) per procedure
- [ ] CHANGELOG updated · ส่งฟ้า FINAL review

---

# 🔵 Sprint F — ฟ้า Final UI Test (Day 18)

ฟ้า run comprehensive UI test ก่อน public launch · 34 scenarios across 7 phases

## Phase 1 — Pre-flight (10 min)
1. `/health` 200 + version ตรง + DB ping ok
2. Footer version chip ตรง
3. CSP / CORS headers ตามที่ตั้ง

## Phase 2 — Security (30 min)
4. XSS injection ใน chat → escape (S0.6, S3.12)
5. Upload `.exe` rename `.txt` → reject (S3.10)
6. MCP wrong secret 10 ครั้ง → 429 (S3.3)
7. Password reset spam → 429 (S3.2)
8. `/api/me` response ไม่มี `mcp_secret` (S1.8)
9. Error 500 ไม่หลุด stack trace (S1.7)
10. DB ไม่มี `plaintext_password` column (S1.0)
11. `git log -- .env` empty (S0.1)
12. Pre-commit secret scan block test (S4.7)

## Phase 3 — Thai Language (45 min)
13. Search "ข้อมูล" hit ไฟล์ "การจัดการข้อมูล" (S2.1)
14. NFC vs NFD ของ "ที่" → duplicate detect flag (S2.2)
15. iOS Safari render ตัวอักษรไทย + tone mark ไม่ทับ (S2.3)
16. Thai IME composition → search fire 1 ครั้ง (S2.4)
17. Chat ภาษาไทย → AI ตอบ Thai ดี + cite sources

## Phase 4 — Performance (60 min)
18. Upload 50 ไฟล์ → analyze "(ขนาน 50)" + เสร็จ <30s
19. /api/files default limit=50 + cursor (S1.1)
20. Browser scroll 5K file list → 60fps (S3.13)
21. 30-min soak + 10 organize cycles → RSS stable (S2.6-2.10)
22. Admin audit 100 rows load <2s (S1.3)
23. Backend kill → polling backoff → recover (S3.14)

## Phase 5 — Reliability + Backup (30 min)
24. JWT secret enforced — restart Fly → tokens ถูกต้อง (S0.4)
25. flyctl volume snapshots active (S4.11)
26. flyctl logs JSON format (S4.10)
27. Rollback test `flyctl releases rollback` → previous live

## Phase 6 — LLM Safety (30 min)
28. Bad LLM output → JSON validate · DB no corruption (S2.12)
29. Prompt injection → LLM ทำตาม system (S3.8)
30. Gemini Files list = no stale (S3.7)
31. Token budget exceed → 429 (S3.5)

## Phase 7 — End-to-End (45 min)
32. Register → verify → login → upload PDF → analyze → chat → share → MCP add
33. Mobile (real iPhone) — ทุกขั้น
34. LINE bot — webhook receive + reply

### Verdict Format
```
### MSG-FIX-PLAN-FINAL — UI Test Verdict
**Tested phases:** 1-7 (34 scenarios)
**Status:** ✅ APPROVED-FOR-LAUNCH / ❌ NEEDS-CHANGES
**Pass rate:** XX / 34
**Blockers:** ...
**Performance numbers:** [50 files NN s · /api/files NN ms · admin audit NN ms]
**Production readiness:** GO / NO-GO
```

---

# ⚠️ Risk Notes (จุดที่ต้องระวังเป็นพิเศษ)

| Item | Risk | Mitigation |
|------|------|-----------|
| S0.1 git filter-repo | DESTRUCTIVE · corrupt local repo | Backup `.git` ก่อน · test clone |
| S0.0 / S0.0a schema | migration ก่อน app deploy = mismatch | run script offline ก่อน + verify ก่อน S0.2 |
| S0.3 / S1.0 plaintext drop | data loss ถ้า rebuild ผิด | pre-migration backup + 24h gap |
| S0.4 JWT enforce | Fly machine refuse start | Stage `JWT_SECRET_KEY` ก่อน deploy code |
| S1.5 FK CASCADE rebuild | SQLite limitation · risky | test บน local clone · backup · PRAGMA off ระหว่าง rebuild |
| S1.7 sweep 14 sites | regression on error responses | unit test cover all paths |
| S2.1 PyThaiNLP add dep | image size +30MB · cold start ช้า | lazy import + benchmark startup |
| S2.9 TF-IDF LRU | search recall regression ถ้า evict ผิด | invariant test · LRU = warm cache |
| S3.5 Token budget | over-restrictive blocks normal use | generous limits + admin override |
| S3.11 LLM_MODEL_PRO | cost +5x · summary differ | A/B test ก่อน · rollback path ready |
| S4.6 GitHub Actions | tests flake บน CI | run locally first · headless mode |
| S4.12 init_db refactor | break existing migration | keep old `init_db` as fallback 1 sprint |

---

# 📊 Success Metrics

| Metric | Baseline | Target |
|--------|---------:|-------:|
| P0 findings closed | 0 / 24 | 24 / 24 |
| P1 findings closed | 0 / 34 | 34 / 34 |
| Test coverage | 0.6% | ≥25% |
| `str(e)` in main.py | 14 | 0 |
| Endpoints with response_model (critical 20) | 0 | 20 |
| `except: pass` sites | 10+ | 0 |
| `print()` in database.py | 28+ | 0 |
| Indexes on user_id | 0 | 5+ |
| FKs without CASCADE | ~30 | 0 |
| Memory leaks (unbounded caches) | 5 | 0 |
| Thai search recall (golden corpus) | ~40% | ≥80% |
| `/health` DB-aware | No | Yes |
| Container runs root | Yes | No |
| `.env` in git history | Yes | No |
| Daily DB backup | No | Yes |
| Hardcoded `personaldatabank.fly.dev` | 5+ | ≤ 1 |

---

# 📞 Communication

- **Start sprint:** Update `pipeline-state.md` → `sprint_X_active`
- **Daily:** Read `for-เขียว.md` inbox + check user notes
- **End of milestone:** Commit + push + tick checkbox in plan + CHANGELOG line
- **End of sprint:** Send `for-ฟ้า.md` MSG · wait APPROVED before next sprint
- **Sprint deploy:** Combined per procedure (ยกเว้น S0 emergency)
- **Blocker:** Flag ใน `for-User.md` ถ้าติด > 2 ชม.

---

# 🎯 Definition of Done (per milestone)

1. ✅ Code committed + push (tag `[SX.Y]`)
2. ✅ Test pass (S4 setup CI · ก่อนหน้าใช้ local pytest)
3. ✅ Smoke test prod manual (post-deploy)
4. ✅ Plan checkbox tick
5. ✅ CHANGELOG.md line added
6. ✅ Memory state updated

---

# ✅ Definition of Done (per Sprint)

1. ✅ ทุก milestone = green checkbox
2. ✅ Sprint Acceptance Gate ครบ
3. ✅ Deploy ตาม procedure · smoke pass · cool-down 30 min ok
4. ✅ ฟ้า review = APPROVED (หรือ APPROVED WITH NOTES ที่ defer ชัดเจน)
5. ✅ pipeline-state.md → next sprint

---

# 🎉 Definition of Done (Plan complete)

1. ✅ Sprint 0-4 ทุก sprint = APPROVED
2. ✅ ฟ้า Final UI Test (Sprint F) = APPROVED-FOR-LAUNCH (Phase 1-7, 34/34 pass)
3. ✅ Coverage ≥25%
4. ✅ Pre-launch checklist:
   - [ ] DNS configured
   - [ ] Privacy policy + ToS updated · GDPR/PDPA review with legal
   - [ ] Status page setup (status.personaldatabank.fly.dev)
   - [ ] Support email setup (support@personaldatabank.fly.dev)
   - [ ] Initial admin user setup documented (`runbooks/admin-setup.md`)
   - [ ] User communication template — maintenance / incident
   - [ ] Backup tested + restore drill ผ่าน (S4.11)
   - [ ] Beta user feedback positive
5. → **Public launch announce**

---

**End of plan v2 — เริ่ม Sprint 0 ได้เลย**
