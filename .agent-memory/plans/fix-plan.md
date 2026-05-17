# 🛠 Fix Plan — Unified · เขียวคนเดียว

> **Created:** 2026-05-18 · **Owner:** เขียวคนเดียว (me) · **Reviewer:** ฟ้า
> **Total milestones:** 60 · **Total days:** 16 sprint-days (~3 สัปดาห์)
> **Closes:** 188 audit findings → production-ready

---

## 🎯 Mission

User audit ระบบเจอ **188 findings** (24 P0, 34 P1) → ห้ามเปิด public launch
แผนนี้ทำให้ระบบพร้อมเปิด public ภายใน 3-4 สัปดาห์

ทำงานคนเดียว ไม่มี A/B coordination
รวบ Sprint ละไม่กี่ theme ทำให้ focus ชัด

---

## 📅 Sprint Roadmap

| Sprint | Theme | Days | Milestones |
|--------|-------|-----:|:----------:|
| **0** | Security Emergency | 1 | 10 |
| **1** | DB + API Contract | 5 | 10 |
| **2** | Thai + Memory + LLM Safety | 5 | 16 |
| **3** | Rate Limit + Frontend | 5 | 12 |
| **4** | Tests + Ops | 5 | 12 |
| **F** | ฟ้า Final UI Test | 1 | — |

**Sprint 0 = วันแรก emergency** · Sprint 1-4 ตามคิว · จบด้วย ฟ้า final UI

---

## 🚦 Rules

1. **1 branch / sprint:** `fix/sprint-0`, `fix/sprint-1`, ...
2. **Commit tag:** `[S0.X]`, `[S1.X]`, ...
3. **Deploy:** ปลาย sprint เท่านั้น (Sprint 0 เป็นข้อยกเว้น — emergency)
4. **Migration:** ทุก ALTER TABLE → backup ก่อน + try/except + idempotent
5. **Backwards compat:** API change ต้อง grace period 30 วัน
6. **Test first:** มี test ก่อน implement (TDD where reasonable)
7. **Sprint end:** ส่งฟ้า review ผ่าน `for-ฟ้า.md` ทุก sprint

---

# 🚨 Sprint 0 — Security Emergency (Day 1, ~6 ชม.)

## Goal
ปิดรู security ที่ public-facing risk ทันที — deploy หลังเสร็จ

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S0.1** | Rotate secrets ทั้งหมด (OpenRouter, Stripe, Google OAuth, Picker, LlamaCloud, GoogleAPI) + clean `.env` จาก git history | smoke test ทุก integration · `git log --all -- .env` empty | 2-3h |
| **S0.2** | `PRAGMA foreign_keys=ON` + SQLAlchemy event listener | `_test_database.py::test_fk_enabled` · result == 1 | 30min |
| **S0.3** | Drop `plaintext_password` — Phase 1 stop writes + Phase 2 ลบ endpoint (Phase 3 DROP COLUMN รอ 24h) | `_test_auth.py::test_no_plaintext_on_register` · admin endpoint 404 | 1h |
| **S0.4** | JWT secret env enforce — Fly machine fail-hard ถ้าไม่ตั้ง | `_test_config.py::test_jwt_fails_hard_on_fly_no_env` | 45min |
| **S0.5** | ADMIN_PASSWORD soft fail — warn + admin endpoint 503 (ไม่ sys.exit) | `_test_config.py::test_no_admin_password_warns_not_crashes` | 45min |
| **S0.6** | Chat XSS fix — ลบ `isHtml` flag · ใช้ `textContent` หรือ escape เสมอ (`legacy-frontend/app.js:5118`) | inject `<script>` ใน LLM response → escape | 30min |
| **S0.7** | `EMBEDDING_MODEL` default → `gemini-embedding-001` (`text-embedding-004` deprecate) | `_test_embeddings.py::TestRealAPI` ผ่าน (3072-d) | 15min |
| **S0.8** | Dockerfile `USER non-root` + `HEALTHCHECK` | `docker run` user != root · HEALTHCHECK pass | 30min |
| **S0.9** | `fly.toml` `kill_signal="SIGTERM"` + `kill_timeout="30s"` | rolling deploy ไม่ตัดเชื่อมโยง mid-upload | 15min |
| **S0.10** | `.dockerignore` + `.gitignore` clean (`.env`, `__pycache__`, `.venv`, secrets files) | image ไม่มี secret files · `git status -i` ปกติ | 15min |

### Sprint 0 Acceptance Gate
- [ ] Secrets rotated · `/health` 200 หลัง rotate · LLM/login/Drive/LINE smoke pass
- [ ] `.env` หายจาก git history
- [ ] FK enforcement on · plaintext_password Phase 1+2 done
- [ ] JWT env enforce active บน Fly
- [ ] ADMIN_PASSWORD missing = warn (not crash)
- [ ] Chat XSS test pass
- [ ] Container ไม่รัน root
- [ ] Deploy `v10.0.30-sprint0` + smoke pass
- [ ] ส่งฟ้า review

---

# 🛠 Sprint 1 — DB + API Contract (5 days)

## Goal
แก้ DB perf ที่ทำให้ระบบช้า/พังที่ scale + สร้าง consistent API contract

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S1.1** | Pagination `/api/files` (cursor-based, default limit=50, max=200) | 120 files → page 1 (50) + cursor + page 2 (50) + page 3 (20) | 3h |
| **S1.2** | Pagination `/api/clusters` + `/api/export` (chunked stream) + `delete-account` (batch 500) | export 5K files ใน <30s ไม่ OOM · delete-account ไม่ timeout | 4h |
| **S1.3** | Fix N+1 admin audit log (`admin.py:1015-1033`) → JOIN | query count 50 → ≤2 ต่อ 50 rows | 1h |
| **S1.4** | Add indexes: `files(user_id)`, `clusters(user_id)`, `context_packs(user_id)`, `graph_nodes(user_id, object_type)`, `audit_logs(user_id, created_at)` | `EXPLAIN QUERY PLAN` ใช้ index · 5x faster บน 10K rows | 1h |
| **S1.5** | FK `ON DELETE CASCADE` (table rebuild for SQLite) | delete user → ทุก child rows หาย | 4-6h |
| **S1.6** | DB ping ใน `/health` (timeout 2s, return 503 ถ้า fail) | DB down → 503 · DB up → 200 (latency <50ms) | 1h |
| **S1.7** | Unified error handler — `{"error":{"code","message","request_id"}}` + sweep 14 `str(e)` sites + middleware request_id | 500 ไม่มี stack trace · all status code return unified shape | 4-6h |
| **S1.8** | ลบ `mcp_secret` จาก `/api/me` + new endpoint `/api/mcp/credentials` (require password reauth) | `/api/me` response ไม่มี mcp_secret · wrong password → 401 | 1h |
| **S1.9** | MCP test endpoint `/api/mcp/test` คืน 401 (ไม่ใช่ 200 OK) ตอน auth fail | invalid auth → status_code == 401 | 15min |
| **S1.10** | Input validation: `ChatRequest.question` max_length=5000, file upload size check actual bytes (not Content-Length), pagination bounds | 422 บน invalid · Content-Length โกง → reject | 2h |

### Sprint 1 Acceptance Gate
- [ ] 4 endpoints มี pagination · stream + batch ใช้ได้
- [ ] N+1 audit log fix
- [ ] 5 indexes present · `EXPLAIN` confirm
- [ ] FK CASCADE verified
- [ ] /health ตรวจ DB
- [ ] No `str(e)` ใน main.py · unified error shape ทั่ว
- [ ] mcp_secret ไม่ leak · MCP test 401
- [ ] Input validation strict
- [ ] Deploy `v10.0.31-sprint1` + smoke pass
- [ ] ส่งฟ้า review

---

# 🇹🇭 Sprint 2 — Thai + Memory + LLM Safety (5 days)

## Goal
แก้ search ไทยที่พังเชิงโครงสร้าง + memory leaks + LLM output safety

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S2.1** | PyThaiNLP `word_tokenize` ใน `vector_search.py:_tokenize()` | "การจัดการข้อมูล" → ≥3 tokens · search recall benchmark ≥80% | 3h |
| **S2.2** | Unicode NFC normalization ใน `duplicate_detector.py:normalize_text()` (use `unicodedata.normalize('NFC', text)`) | NFC vs NFD ของ "ที่" → hash เท่ากัน | 30min |
| **S2.3** | CSS `font-family: 'Noto Sans Thai', 'Inter', ...` + line-height 1.7 บน body | iOS Safari render ไทยครบ · tone mark ไม่ทับ | 1h |
| **S2.4** | IME composition events: ฟัง `compositionstart`/`compositionend` ก่อน fire search/chat input handlers | พิมพ์ "ข้อมูล" ผ่าน Thai IME → search fire ครั้งเดียวหลังจบ | 2h |
| **S2.5** | Encoding fallback: ใช้ `chardet` detect ก่อน fallback (`extraction.py:564`) | UTF-8/cp874 file detect ถูก · ไม่ garble | 2h |
| **S2.6** | progress_tracker `gc_stale()` auto-run ทุก 2 นาที ผ่าน asyncio background task | mock 1000 stale → cleanup task ตัดเหลือ 0 ใน 5 นาที | 1h |
| **S2.7** | `_shared_links` async cleanup task ทุก 5 นาที | dict size stable หลัง 1000 link + 30 นาที | 1h |
| **S2.8** | `_STATE_CACHE` (OAuth) periodic cleanup ทุก 5 นาที | stale states หายใน 10 นาที | 1h |
| **S2.9** | TF-IDF LRU cache `_user_indexes` max 100 files/user | user มี 200 files → cache ≤100 · soak test 24h RSS stable | 2h |
| **S2.10** | `_login_fail_history` cap 10K IPs + LRU eviction | 11K IPs → cap ที่ 10K | 1h |
| **S2.11** | Silent except sweep — เพิ่ม `logger.exception()` ทุกที่ที่เจอ `except: pass` (10+ sites) | `grep -E "except.*:\s*pass"` = 0 lines | 3h |
| **S2.12** | LLM JSON schema validation — Pydantic validate output ก่อนเก็บ DB (`llm.py:152-191`) | inject `"score":"very high"` → reject + retry หรือ default | 2h |
| **S2.13** | Per-user token budget (DB table `user_token_usage` + check ก่อน LLM call) | user เกิน quota → 429 + clear message | 3h |
| **S2.14** | LlamaParse budget guard — check spend ก่อนเรียก API (`LLAMAPARSE_BUDGET_CENTS` enforce) | mock spend → block ก่อน API call | 1h |
| **S2.15** | Gemini Files explicit cleanup — `files.delete()` หลังใช้ + DB tracking | upload → use → delete · Gemini list ไม่มี stale | 2h |
| **S2.16** | Prompt injection escape: escape user question ก่อนใส่ใน LLM prompt (`retriever.py:424`) | "ignore previous instructions" → LLM ทำตาม system prompt | 1h |

### Sprint 2 Acceptance Gate
- [ ] Thai search recall ≥80%
- [ ] NFC dedup works
- [ ] CSS ไทย render ดีบน iOS
- [ ] IME composition handled
- [ ] Encoding detect ถูก
- [ ] 4 memory caches มี cleanup task
- [ ] TF-IDF + login throttle bounded
- [ ] Silent except = 0
- [ ] LLM JSON validate
- [ ] Token + LlamaParse budget guards
- [ ] Gemini Files cleanup
- [ ] Prompt injection mitigated
- [ ] Deploy `v10.0.32-sprint2` + smoke pass
- [ ] ส่งฟ้า review

---

# 🛡 Sprint 3 — Rate Limit + Frontend (5 days)

## Goal
Persistent rate limits + frontend hardening + LLM model upgrade

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S3.1** | Login throttle DB persist (table `login_attempts`) — restart survives | 5 fails → restart → 6th still blocked | 3h |
| **S3.2** | Password reset rate limit — 5/hour/email + 10/hour/IP | 6 reset/hour → 429 | 1h |
| **S3.3** | MCP `/mcp/{secret}` rate limit + auto-rotate on 100 fail/hour | brute force → 429 + lock 1h + audit log | 3h |
| **S3.4** | MCP permissions persist to DB (`mcp_permissions` table) — restart survives | disable tool → restart → ยัง disabled | 2h |
| **S3.5** | Chunk retry jitter (`organizer.py:427`) — `random.random()` jitter ±20% | mock 3 chunks fail → retry timing variance | 1h |
| **S3.6** | File magic bytes validation — `python-magic` verify content vs extension | `.exe` rename `.txt` → reject · genuine pdf accept | 2h |
| **S3.7** | `LLM_MODEL_PRO` default → `gemini-2.5-pro` (ลบ TEMP comment) + quality regression test | summary quality benchmark Pro vs Flash | 1h |
| **S3.8** | Frontend XSS hardening — `onclick="${f.id}"` → `data-id="${escapeHtml(f.id)}"` + event delegation | filename มี `'"><script>` → no XSS · click ทำงาน | 3h |
| **S3.9** | Frontend pagination — file list (50/page virtual scroll) + cluster list + graph nodes | 5K files = render 50 · scroll 60fps · LCP <2.5s | 4h |
| **S3.10** | Polling backoff — organize status poll: 500ms→5s exponential, max 20 retries | backend 500 → frontend backoff · recover ตอน restart | 2h |
| **S3.11** | localStorage size check — try-catch wrapper · graceful fallback ถ้า quota exceeded | mock quota exceed → no crash · log warning | 1h |
| **S3.12** | Button disable + request dedup — ทุก async op + AbortController on duplicate click | double-click submit → request ส่งครั้งเดียว | 2h |

### Sprint 3 Acceptance Gate
- [ ] Rate limits persist across restart
- [ ] MCP brute force blocked
- [ ] Magic bytes catch fake .txt
- [ ] LLM_MODEL_PRO = Pro · quality ≥ Flash baseline
- [ ] No XSS via onclick
- [ ] Frontend lists scroll smooth ที่ 5K items
- [ ] Polling has backoff
- [ ] Double-click safe
- [ ] Deploy `v10.0.33-sprint3` + smoke pass
- [ ] ส่งฟ้า review

---

# 🧪 Sprint 4 — Tests + Ops (5 days)

## Goal
สร้าง test infrastructure + CI/CD + observability + backup strategy

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **S4.1** | `conftest.py` fixtures: `db_engine`, `db_session`, `client`, `user`, `user_token`, `admin_user`, `admin_token` | All sprint 4 tests ใช้ fixtures นี้ได้ | 3h |
| **S4.2** | Auth integration tests ≥15: register → verify → login → refresh → reset → logout + edge cases | 15/15 pass | 4h |
| **S4.3** | Endpoint integration tests ≥20: /api/files CRUD + /api/clusters + /api/organize-new + permission isolation + multi-tenant | 20/20 pass | 6h |
| **S4.4** | DB integration tests: migration safety + concurrent write (WAL) + FK cascade verification | All migrations idempotent · WAL behavior verified | 2h |
| **S4.5** | `pyproject.toml`: ruff + black + mypy + pytest config | `ruff check`, `mypy backend/`, `pytest` ทั้งหมดผ่าน | 2h |
| **S4.6** | GitHub Actions `.github/workflows/test.yml` — lint + test + secret-scan (detect-secrets) | PR triggers all checks · green ก่อน merge | 2h |
| **S4.7** | Pre-commit hooks: detect-secrets + ruff | `git commit` ใส่ secret = block | 1h |
| **S4.8** | Dependencies pin + lock file (`pip-tools` → `requirements.lock`) | reproducible build · exact versions | 2h |
| **S4.9** | Base image digest pin: `python:3.11.9-slim@sha256:...` | Dockerfile FROM มี `@sha256:` | 30min |
| **S4.10** | JSON structured logging — middleware + formatter | Fly logs parsable JSON · มี timestamp + level + request_id | 2h |
| **S4.11** | DB backup strategy: daily `scripts/backup.py` + `scripts/test_restore.py` | restore drill ผ่าน · verify schema + row counts | 3h |
| **S4.12** | Fly volume snapshot policy — daily snapshot + retention 14 days | `flyctl volumes snapshots list` แสดง snapshot | 30min |

### Sprint 4 Acceptance Gate
- [ ] conftest.py fixtures complete
- [ ] ≥35 integration tests pass
- [ ] CI green บน PR
- [ ] Secret scan block ใน pre-commit
- [ ] Deps pinned + lock file
- [ ] Base image digest pinned
- [ ] JSON logging on Fly
- [ ] DB backup tested · restore verified
- [ ] Fly snapshots active
- [ ] Coverage ≥25% (จาก 0.6%)
- [ ] Deploy `v10.0.34-sprint4` (final pre-launch)
- [ ] ส่งฟ้า **FINAL** review

---

# 🔵 ฟ้า Final UI Test (Phase F)

หลัง Sprint 4 จบ — ฟ้า run comprehensive UI test ก่อน public launch

## Phase 1 — Pre-flight (10 นาที)
- `/health` = 200 + version ตรง + DB ping ok
- Footer version chip ตรง
- CSP / CORS headers ตามที่ตั้ง

## Phase 2 — Security (30 นาที)
- XSS injection ใน chat → escape (S0.6, S3.8)
- Upload `.exe` rename `.txt` → reject (S3.6)
- MCP wrong secret 10 ครั้ง → 429 (S3.3)
- Password reset spam → 429 (S3.2)
- `/api/me` response ไม่มี `mcp_secret` (S1.8)
- Error 500 ไม่หลุด stack trace (S1.7)
- DB ไม่มี `plaintext_password` column (S0.3 Phase 3)
- `git log -- .env` empty (S0.1)

## Phase 3 — Thai Language (45 นาที)
- Search "ข้อมูล" hit ไฟล์ "การจัดการข้อมูล" (S2.1)
- 2 ไฟล์ NFC vs NFD → duplicate detect flag (S2.2)
- iOS Safari render ตัวอักษรไทย + tone mark ไม่ทับ (S2.3)
- พิมพ์ search ไทยผ่าน IME → search ไม่ fire ก่อนพิมพ์จบ (S2.4)
- Chat ภาษาไทย → AI ตอบ Thai ดี + cite sources

## Phase 4 — Performance (60 นาที)
- Upload 50 ไฟล์ → analyze "(ขนาน 50)" + เสร็จใน <30s
- Upload 100 ไฟล์ → /api/files default limit=50 + cursor (S1.1)
- Browser scroll 5K file list → smooth 60fps (S3.9)
- Soak test 30 นาที + organize 10 ครั้ง → RSS stable (S2.6-S2.10)
- Admin audit log 100 rows → load <2s (S1.3)
- Backend kill → polling backoff → recover (S3.10)

## Phase 5 — Reliability + Backup (30 นาที)
- flyctl stop primary → JWT ยังถูก (S0.4)
- flyctl volume snapshot list → active (S4.12)
- flyctl logs → JSON format (S4.10)
- Rollback test: `flyctl releases rollback` → previous live

## Phase 6 — LLM Safety (30 นาที)
- Upload weird file → JSON output validate · DB no corruption (S2.12)
- Prompt injection "ignore previous" → LLM ทำตาม system prompt (S2.16)
- Gemini Files list = no stale (S2.15)
- Token budget exceed → 429 + message (S2.13)

## Phase 7 — End-to-End (45 นาที)
- Register → verify email → login → upload PDF → analyze → chat → share → MCP add
- Mobile (real iPhone) — ทุกขั้น
- LINE bot — webhook receive + reply

## Verdict Format
```
### MSG-FIX-PLAN-FINAL — UI Test Verdict
**Tested phases:** 1-7 (34 scenarios)
**Status:** ✅ APPROVED-FOR-LAUNCH / ❌ NEEDS-CHANGES
**Pass rate:** XX / 34
**Blockers:** [HIGH/MED/LOW + repro steps]
**Performance numbers:**
- 50 files analyze: NN seconds
- /api/files load (100 files): NN ms
- Admin audit 100 rows: NN ms
**Production readiness:** GO / NO-GO
```

---

# ⚠️ Risk Notes (จุดที่ต้องระวังเป็นพิเศษ)

| Item | Risk | Mitigation |
|------|------|-----------|
| S0.1 git filter-repo | DESTRUCTIVE — corrupt local repo | Backup `.git` ก่อนทำ + test บน clone |
| S0.3 Phase 3 DROP COLUMN | data loss | Pre-migration backup · รอ 24h หลัง Phase 1+2 |
| S0.4 JWT enforce | Fly machine refuse start | Stage `JWT_SECRET_KEY` ก่อน deploy code |
| S1.5 FK CASCADE table rebuild | SQLite ALTER limitation | Pre-migration backup · test บน staging clone · PRAGMA off ระหว่าง rebuild |
| S1.7 sweep 14 `str(e)` sites | regression on error responses | unit test cover all paths |
| S2.1 PyThaiNLP add dep | image size +30MB · cold start ช้า | Lazy import + benchmark startup |
| S2.13 Token budget | over-restrictive blocks normal use | Generous limits + admin override |
| S3.7 LLM_MODEL_PRO → Pro | cost +5x · summary differ | A/B test ก่อน + rollback ได้ |
| S4.6 GitHub Actions CI | tests flake บน CI | run locally ก่อน push · headless mode |

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
| Indexes on user_id | 0 | 5+ |
| FKs without CASCADE | ~30 | 0 |
| Memory leaks (unbounded caches) | 5 | 0 |
| Thai search recall | ~40% | ≥80% |
| `/health` DB-aware | No | Yes |
| Container runs root | Yes | No |
| `.env` in git history | Yes | No |
| Daily DB backup | No | Yes |

---

# 📞 Communication

- **เริ่ม sprint:** อัพเดท `pipeline-state.md` → `sprint_X_active`
- **ทุกเช้า:** อ่าน `for-เขียว.md` inbox (ถ้า user มี note)
- **End of milestone:** commit + push + เช็คใน plan
- **End of sprint:** ส่งฟ้า ผ่าน `for-ฟ้า.md` (MSG ใหม่ ต่อ sprint)
- **Sprint deploy:** Combined deploy ปลาย sprint (ยกเว้น S0)
- **Blocker:** flag ใน `for-User.md` ถ้าติด > 2 ชม.

---

# 🎯 Definition of Done (ต่อ milestone)

1. ✅ Code committed + push (commit tag `[SX.Y]`)
2. ✅ Unit/integration test pass (Sprint 4 setup CI · ก่อนหน้านั้น run local)
3. ✅ Smoke test prod manual (post-deploy)
4. ✅ Plan file checkbox tick
5. ✅ Memory state updated

---

# ✅ Definition of Done (per Sprint)

1. ✅ ทุก milestone ใน sprint = green checkbox
2. ✅ Sprint acceptance gate ครบ
3. ✅ Deploy + smoke pass
4. ✅ ฟ้า review = APPROVED (หรือ APPROVED WITH NOTES ที่ defer)
5. ✅ pipeline-state.md update → next sprint

---

# 🎉 Definition of Done (Plan complete)

1. ✅ ทุก 4 sprint = APPROVED
2. ✅ ฟ้า Final UI Test = APPROVED-FOR-LAUNCH (Phase 1-7, 34 scenarios)
3. ✅ Coverage ≥25% (baseline 0.6%)
4. ✅ Pre-launch checklist:
   - [ ] DNS configured
   - [ ] Privacy policy + ToS updated
   - [ ] Beta user feedback กลับมา positive
   - [ ] Sentry/observability watching (Sprint 4)
   - [ ] Backup tested + restore drill ผ่าน
5. → **Public launch announce**

---

**End of plan — เริ่ม Sprint 0 ได้เลย**
