# 🛠 Fix Plan v3 — 2 Phases · เขียวคนเดียว

> **Created:** 2026-05-18 (v3 = 2-phase consolidation from v2)
> **Owner:** เขียวคนเดียว (me) · **Reviewer:** ฟ้า
> **Total:** 66 milestones · ~17-18 days (~3.5 สัปดาห์) · 2 release checkpoints

---

## 🎯 Mission

User audit เจอ **188 findings** → 24 P0 + 34 P1 ต้องปิดก่อน public launch
แผนนี้แบ่งเป็น **2 พาส**:

| Phase | Outcome | Days | Milestones |
|-------|---------|-----:|-----------:|
| **Phase 1** — Foundation (Safe + Functional) | ระบบใช้งานปลอดภัย · Thai search ใช้ได้ · DB ไม่ระเบิด | ~11 | 35 |
| **Phase 2** — Hardening (Production-Ready) | Rate limits + LLM safety + tests + ops + final UI verify | ~7 | 31 + 34 UI |

แต่ละ phase **deployable** + มี ฟ้า review checkpoint

---

## 🚦 Rules (applies both phases)

1. **1 branch / phase:** `fix/phase-1`, `fix/phase-2`
2. **Commit tag:** `[P1.X]` หรือ `[P2.X]` ตาม sub-block
3. **Migration:** ทุก ALTER → backup ก่อน + try/except + idempotent
4. **Backwards compat:** API change ต้อง grace period 30 วัน
5. **Test first** where reasonable
6. **CHANGELOG.md:** update ทุก milestone end (1 บรรทัด)
7. **Cost guard:** ตั้ง Google Cloud + Fly budget alert ก่อน Phase 1

---

## 🚀 Phase Deploy Procedure

1. **Pre-deploy** (~30 min): backup DB · tag release · update CHANGELOG
2. **Deploy** (~5 min): `flyctl deploy --remote-only` · watch logs
3. **Smoke** (~5 min): /health · login · upload · chat · admin
4. **Cool-down** (30 min): watch logs · rollback if regress (`flyctl releases rollback`)
5. **Close phase**: update `pipeline-state.md` · send `for-ฟ้า.md` MSG · wait APPROVED

## 🧪 Staging

Migration-heavy items ต้องทดสอบบน local DB clone ก่อน prod:
- P1.1.2 (FK pragma) · P1.1.3 (plaintext drop Phase 1+2) · P1.2.1 (Phase 3 DROP COLUMN) · P1.2.5 (FK CASCADE rebuild) · P2.3.12 (init_db refactor)

---

═══════════════════════════════════════════════════════════════

# 🟢 PHASE 1 — Foundation (Day 1-11)

**Goal:** ระบบปลอดภัยพอเปิดให้ trusted users · Thai ใช้ได้ · DB scale ได้
**Outcome:** Deploy `v10.0.32-phase1` · ฟ้า phase review

แบ่ง 3 blocks:
- **Block 1.1** — Security Emergency (Day 1-1.5, 11 items)
- **Block 1.2** — DB + API Contract (Day 2-6, 12 items)
- **Block 1.3** — Thai + Memory + Silent Errors (Day 7-11, 12 items)

---

## 🚨 Block 1.1 — Security Emergency (Day 1-1.5, ~10h)

**Sequence:** P1.1.0 → P1.1.0a → P1.1.1 → P1.1.2 → P1.1.3-1.1.10 → P1.1.11 → emergency deploy

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **P1.1.0** | Audit orphan rows ใน 5 ตาราง · ลบ/assign ถ้าเจอ | orphan count = 0 ทุกตาราง · log result | 30min |
| **P1.1.0a** | Schema pre-create: `login_attempts`, `mcp_permissions`, `user_token_usage` (เปล่าๆ — ใช้ Phase 2) | `PRAGMA table_info` ทั้ง 3 ปรากฏ | 30min |
| **P1.1.1** | Rotate secrets ทั้งหมด + clean `.env` จาก git history | smoke each integration · `git log .env` empty | 2-3h |
| **P1.1.2** | `PRAGMA foreign_keys=ON` + SQLAlchemy event listener | `test_fk_enabled` result == 1 | 30min |
| **P1.1.3** | Drop `plaintext_password` Phase 1+2 (stop writes + remove endpoint) · Phase 3 = P1.2.1 | `test_no_plaintext_on_register` · admin endpoint 404 | 1h |
| **P1.1.4** | JWT secret env enforce — Fly fail-hard ถ้าไม่ตั้ง | `test_jwt_fails_hard_on_fly_no_env` | 45min |
| **P1.1.5** | ADMIN_PASSWORD soft fail — warn + endpoint 503 (ไม่ sys.exit) | `test_no_admin_password_warns` · admin 503 | 45min |
| **P1.1.6** | Chat XSS fix — ลบ `isHtml` flag · escape เสมอ | inject `<script>` → escape | 30min |
| **P1.1.7** | `EMBEDDING_MODEL` default → `gemini-embedding-001` | `TestRealAPI` 3072-d pass | 15min |
| **P1.1.8** | Dockerfile `USER non-root` + HEALTHCHECK + `.dockerignore` | docker run user != root · HEALTHCHECK pass | 30min |
| **P1.1.9** | `fly.toml` `kill_signal="SIGTERM"` + `kill_timeout="30s"` | rolling deploy ไม่ตัด mid-upload | 15min |
| **P1.1.10** | `.gitignore` clean (`.env`, `__pycache__`, `.venv`, `*.db`) + pre-commit skeleton | `git status -i` ปกติ | 15min |
| **P1.1.11** | Set `GEMINI_API_KEY_BACKUP` on Fly · verify failover (smoke 429 path) | secret list มี backup · failover log | 30min |

### Block 1.1 Acceptance
- [ ] Orphans cleared · 3 future tables ready · secrets rotated · git clean
- [ ] FK on · plaintext Phase 1+2 done · JWT enforce · ADMIN soft fail
- [ ] XSS fixed · embedding default · container non-root · kill_timeout · gitignore
- [ ] Backup Gemini key + failover verified
- [ ] Emergency deploy `v10.0.30-phase1.1` (early ship — security)

---

## 🛠 Block 1.2 — DB + API Contract (Day 2-6, ~32h)

**Sequence:** P1.2.0 (wait 24h after P1.1.3) → P1.2.6 (error handler FIRST) → rest

**Frontend coordination:** P1.2.2, P1.2.3, P1.2.6, P1.2.7 — same commit เสมอ

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **P1.2.0** | Drop `plaintext_password` Phase 3 (DROP COLUMN — รอ 24h หลัง P1.1.3 deploy) | `PRAGMA table_info(users)` ไม่มี column | 1h |
| **P1.2.6** | **Unified error handler** (do FIRST) — `{"error":{"code","message","request_id"}}` + middleware + sweep 14 `str(e)` sites | 500 ไม่หลุด stack · all status code unified · request_id in headers | 4-6h |
| **P1.2.1** | Pagination `/api/files` (cursor, 50/page max 200) + frontend "Load more" | 120 files → 3 pages (50+50+20) | 4h |
| **P1.2.2** | Pagination `/api/clusters` + `/api/export` (chunked) + `delete-account` (batch 500) | export 5K files <30s ไม่ OOM | 4h |
| **P1.2.3** | Fix N+1 admin audit log → JOIN | query ≤2 · load 100 rows <2s | 1h |
| **P1.2.4** | 5 indexes: `files(user_id)`, `clusters(user_id)`, `context_packs(user_id)`, `graph_nodes(user_id, object_type)`, `audit_logs(user_id, created_at)` | EXPLAIN ใช้ index · 5x faster on 10K rows | 1h |
| **P1.2.5** | FK `ON DELETE CASCADE` table rebuild (test บน local clone ก่อน) | delete user → child rows หาย | 6h |
| **P1.2.7** | DB ping ใน `/health` (timeout 2s, 503 ถ้า fail) | DB down → 503 · up → 200 (<50ms) | 1h |
| **P1.2.8** | ลบ `mcp_secret` จาก `/api/me` + new `/api/mcp/credentials` (require password) + frontend prompt | `/api/me` no leak · wrong password → 401 | 2h |
| **P1.2.9** | MCP test endpoint → 401 (ไม่ 200) ตอน auth fail | invalid auth → 401 | 15min |
| **P1.2.10** | Input validation: chat max_length=5000, file upload actual bytes, pagination bounds | 422 บน invalid · Content-Length โกง → reject | 2h |
| **P1.2.11** | `response_model` สำหรับ **20 critical endpoints** (list ด้านล่าง) | OpenAPI complete · no sensitive leak | 6h |

### 20 critical endpoints (P1.2.11)
```
1.  GET    /api/me                  → MeResponse
2.  POST   /api/auth/login          → AuthTokenResponse
3.  POST   /api/auth/register       → AuthTokenResponse
4.  POST   /api/auth/refresh        → AuthTokenResponse
5.  POST   /api/auth/request-reset  → MessageResponse
6.  POST   /api/auth/reset-password → MessageResponse
7.  GET    /api/files               → FileListResponse (paginated)
8.  GET    /api/files/{id}          → FilePublic
9.  POST   /api/files/{id}/retry    → FilePublic
10. DELETE /api/files/{id}          → DeleteResponse
11. GET    /api/clusters            → ClusterListResponse
12. POST   /api/chat                → ChatResponse
13. POST   /api/organize            → OrganizeStatusResponse
14. POST   /api/organize-new        → OrganizeStatusResponse
15. POST   /api/upload              → UploadResponse
16. GET    /api/context-packs       → ContextPackListResponse
17. POST   /api/mcp/credentials     → MCPCredentialsResponse
18. GET    /api/admin/users         → AdminUserListResponse (paginated)
19. GET    /api/healthz/queue       → QueueHealthResponse
20. GET    /api/usage               → UsageResponse
```

### Block 1.2 Acceptance
- [ ] plaintext column gone · unified error shape ทุก endpoint · request_id middleware
- [ ] 4 pagination endpoints + frontend · stream + batch ทำงาน
- [ ] N+1 fix · 5 indexes · FK CASCADE · /health DB-aware
- [ ] mcp_secret ไม่ leak · MCP test 401 · input validation
- [ ] 20 response_model

---

## 🇹🇭 Block 1.3 — Thai + Memory + Silent Errors (Day 7-11, ~26h)

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **P1.3.1** | PyThaiNLP `word_tokenize` ใน `vector_search.py` + bench 50 queries | recall ≥80% (baseline 40%) | 4h |
| **P1.3.2** | Unicode NFC ใน `duplicate_detector.py` | NFC vs NFD ของ "ที่" hash เท่ากัน | 30min |
| **P1.3.3** | CSS `'Noto Sans Thai'` ก่อน Inter + line-height 1.7 + Google Fonts | iOS Safari 11 render ครบ · tone mark ไม่ทับ | 1h |
| **P1.3.4** | IME composition: `compositionstart`/`compositionend` ก่อน fire handlers | พิมพ์ "ข้อมูล" → fire 1 ครั้งหลังจบ | 2h |
| **P1.3.5** | Encoding `chardet` detect ก่อน fallback chain | UTF-8 + cp874 fixtures ถูกต้อง | 2h |
| **P1.3.6** | progress_tracker `gc_stale()` auto ทุก 2 นาที | 1000 stale → 0 ใน 5 นาที | 1h |
| **P1.3.7** | `_shared_links` cleanup task ทุก 5 นาที | 1000 link + 30 min soak → stable | 1h |
| **P1.3.8** | OAuth `_STATE_CACHE` cleanup ทุก 5 นาที | stale หายใน 10 นาที | 1h |
| **P1.3.9** | TF-IDF LRU `_user_indexes` max 100/user | 200 files → cache ≤100 · 24h RSS stable | 3h |
| **P1.3.10** | `_login_fail_history` cap 10K IPs LRU (interim ก่อน P2.1.1) | 11K → cap 10K | 1h |
| **P1.3.11** | Silent except sweep — `logger.exception()` ทุก `except: pass` (10+ sites) + `print()` → `logger.*()` ใน database.py (28+ sites) | grep `except.*pass` = 0 · grep `print(` ใน database.py = 0 | 4h |
| **P1.3.12** | LLM JSON schema validation — map callers + Pydantic + retry + log | inject bad type → reject + retry · log entry | 3h |

### Block 1.3 Acceptance
- [ ] Thai recall ≥80% (golden corpus) · NFC dedup · CSS Thai ดี · IME composition · encoding fix
- [ ] 4 memory caches มี cleanup · TF-IDF LRU · login cap · 24h soak RSS stable
- [ ] Silent except = 0 · print = 0 · LLM JSON validate

---

## ✅ Phase 1 Acceptance Gate

- [ ] ทุก milestone Block 1.1-1.3 = green
- [ ] Deploy `v10.0.32-phase1` ตาม procedure
- [ ] Smoke pass · cool-down 30 min · no rollback
- [ ] CHANGELOG updated · pipeline-state → phase 1 complete
- [ ] ส่งฟ้า review · APPROVED ก่อนเริ่ม Phase 2

═══════════════════════════════════════════════════════════════

# 🛡 PHASE 2 — Hardening (Day 12-18)

**Goal:** Production-ready · public launch eligible
**Outcome:** Deploy `v11.0.0` · ฟ้า Final UI Test · GO/NO-GO decision

แบ่ง 3 blocks + Final test:
- **Block 2.1** — Rate Limit + LLM Safety (Day 12-15, 11 items)
- **Block 2.2** — Frontend Hardening (Day 13-15, 5 items)
- **Block 2.3** — Tests + Ops + Refactor (Day 16-18, 15 items)
- **Final** — ฟ้า UI Test 34 scenarios (Day 18)

---

## 🛡 Block 2.1 — Rate Limit + LLM Safety (Day 12-15, ~22h)

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **P2.1.1** | Login throttle DB persist (`login_attempts` table from P1.1.0a) — restart survives | 5 fails → restart → 6th still blocked | 3h |
| **P2.1.2** | Password reset rate limit — 5/hour/email + 10/hour/IP | 6 reset/hour → 429 | 1h |
| **P2.1.3** | MCP `/mcp/{secret}` rate limit + auto-rotate on 100 fail/hour | brute force → 429 + lock 1h + audit + email alert | 3h |
| **P2.1.4** | MCP permissions persist to DB (`mcp_permissions` table) — restart survives | disable → restart → ยัง disabled | 2h |
| **P2.1.5** | Per-user token budget (`user_token_usage` table) — check ก่อน LLM | over quota → 429 · monthly reset · admin override | 4h |
| **P2.1.6** | LlamaParse budget guard — check `cost_cents_30d_total` ก่อน API | mock spend ใกล้ cap → block | 1h |
| **P2.1.7** | Gemini Files explicit cleanup + `api_key_suffix` tracking | upload → use → delete · key affinity preserved | 3h |
| **P2.1.8** | Prompt injection escape ใน `retriever.py:424` | "ignore previous" → LLM ทำตาม system | 1h |
| **P2.1.9** | Chunk retry jitter ±20% | mock 3 chunks fail → timing variance | 1h |
| **P2.1.10** | File magic bytes — `python-magic` verify content vs ext | `.exe` rename `.txt` → reject | 2h |
| **P2.1.11** | `LLM_MODEL_PRO` → `gemini-2.5-pro` + A/B quality regression (10 samples) | Pro ≥80% rated better than Flash | 2h |

---

## 🎨 Block 2.2 — Frontend Hardening (Day 13-15, ~12h, parallel)

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **P2.2.1** | onclick XSS hardening — `data-id` + event delegation | filename มี `'"><script>` → no XSS · click ทำงาน | 3h |
| **P2.2.2** | Frontend pagination — file list (50/page virtual scroll) + cluster + graph | 5K files render 50 · 60fps · LCP <2.5s | 4h |
| **P2.2.3** | Polling backoff — organize status: 500ms→5s exponential, max 20 | backend 500 → backoff · recover ตอน restart | 2h |
| **P2.2.4** | localStorage size check — try-catch + size estimate | mock quota exceed → no crash · log warning | 1h |
| **P2.2.5** | Button disable + AbortController on duplicate click | double-click → 1 request · concurrent abort | 2h |

### Block 2.1+2.2 Combined Acceptance
- [ ] Rate limits persist across restart (login + reset + MCP)
- [ ] Token + LlamaParse budgets active · MCP brute force blocked + alert
- [ ] Gemini Files cleanup + key affinity · prompt injection mitigated · magic bytes
- [ ] LLM_MODEL_PRO = Pro · quality regression pass
- [ ] Frontend no XSS · lists smooth at 5K · polling backoff · double-click safe

---

## 🧪 Block 2.3 — Tests + Ops + Refactor (Day 16-18, ~38h)

| ID | งาน | Test | Time |
|----|-----|------|-----:|
| **P2.3.1** | `conftest.py` fixtures + test data (Thai/EN samples, 5K file seed script) | All tests use fixtures · seed works | 3h |
| **P2.3.2** | Auth integration tests ≥15 (register/verify/login/refresh/reset/logout + edge) | 15/15 pass | 4h |
| **P2.3.3** | Endpoint integration tests ≥20 (files CRUD + clusters + organize + permission isolation + multi-tenant) | 20/20 pass | 6h |
| **P2.3.4** | DB integration tests (migration + concurrent write WAL + FK cascade) | All migrations idempotent · WAL verified | 2h |
| **P2.3.5** | `pyproject.toml`: ruff + black + mypy + pytest config | `ruff check`, `mypy`, `pytest` ผ่าน | 2h |
| **P2.3.6** | GitHub Actions CI: lint + test + secret-scan (detect-secrets) | PR triggers all checks · green ก่อน merge | 2h |
| **P2.3.7** | Pre-commit hooks: detect-secrets + ruff | `git commit` ใส่ secret = block | 1h |
| **P2.3.8** | Dependencies pin + `requirements.lock` (pip-tools) | reproducible build | 2h |
| **P2.3.9** | Base image digest pin (`python:3.11.9-slim@sha256:...`) | Dockerfile FROM มี `@sha256:` | 30min |
| **P2.3.10** | JSON structured logging + request_id correlation | Fly logs parsable JSON | 2h |
| **P2.3.11** | DB backup: daily `scripts/backup.py` + `scripts/test_restore.py` + Fly volume snapshot policy | restore drill ผ่าน · snapshots active | 3h |
| **P2.3.12** | Refactor `init_db()` 634 LOC → versioned migrations `backend/migrations/000X_*.py` | Old DB upgrade + fresh install ผ่าน · each ≤100 LOC | 6h |
| **P2.3.13** | Remove `OPENROUTER_*` deprecated · hardcoded `personaldatabank.fly.dev` → `APP_BASE_URL` | grep OPENROUTER = 0 · grep hardcoded URL ≤ 1 | 1h |
| **P2.3.14** | Audit log retention job (90-day, daily cron) | run script → old logs ลบ · row count ลดลง | 1h |
| **P2.3.15** | Docs pass: update CLAUDE.md + README + `runbooks/deploy.md` + `runbooks/restore.md` | docs match current state | 2h |

### Block 2.3 Acceptance
- [ ] conftest + ≥35 integration tests · coverage ≥25%
- [ ] CI green · secret scan block · deps pinned · digest pinned
- [ ] JSON logging · DB backup tested · snapshots active
- [ ] init_db refactored · deprecated constants removed · audit retention
- [ ] Docs updated

---

## 🔵 Final — ฟ้า UI Test (Day 18, ~4h)

34 scenarios across 7 phases — full test guide:

### Phase 1: Pre-flight (10 min, 3 scenarios)
1. `/health` 200 + version + DB ping
2. Footer version chip ตรง
3. CSP / CORS headers

### Phase 2: Security (30 min, 9 scenarios)
4. XSS injection ใน chat → escape (P1.1.6, P2.2.1)
5. Upload `.exe` rename `.txt` → reject (P2.1.10)
6. MCP wrong secret × 10 → 429 (P2.1.3)
7. Password reset spam → 429 (P2.1.2)
8. `/api/me` ไม่มี `mcp_secret` (P1.2.8)
9. Error 500 ไม่หลุด stack (P1.2.6)
10. DB ไม่มี `plaintext_password` (P1.2.0)
11. `git log -- .env` empty (P1.1.1)
12. Pre-commit secret scan block test (P2.3.7)

### Phase 3: Thai (45 min, 5 scenarios)
13. Search "ข้อมูล" hit "การจัดการข้อมูล" (P1.3.1)
14. NFC vs NFD ของ "ที่" → duplicate flag (P1.3.2)
15. iOS Safari ตัวอักษรไทย + tone mark ไม่ทับ (P1.3.3)
16. Thai IME → search fire 1 ครั้ง (P1.3.4)
17. Chat ภาษาไทย ดี · cite sources

### Phase 4: Performance (60 min, 6 scenarios)
18. Upload 50 ไฟล์ analyze "(ขนาน 50)" <30s
19. /api/files default 50 + cursor (P1.2.1)
20. Browser scroll 5K files 60fps (P2.2.2)
21. 30-min soak + 10 organize → RSS stable (P1.3.6-9)
22. Admin audit 100 rows <2s (P1.2.3)
23. Backend kill → polling backoff → recover (P2.2.3)

### Phase 5: Reliability (30 min, 4 scenarios)
24. JWT enforced · restart Fly → tokens ok (P1.1.4)
25. flyctl volume snapshots active (P2.3.11)
26. flyctl logs JSON format (P2.3.10)
27. Rollback test `flyctl releases rollback`

### Phase 6: LLM Safety (30 min, 4 scenarios)
28. Bad LLM output → validate · DB no corruption (P1.3.12)
29. Prompt injection → LLM ทำตาม system (P2.1.8)
30. Gemini Files list = no stale (P2.1.7)
31. Token budget exceed → 429 (P2.1.5)

### Phase 7: E2E (45 min, 3 scenarios)
32. Register → verify → login → upload → analyze → chat → share → MCP
33. Mobile (real iPhone) — ทุกขั้น
34. LINE bot — webhook + reply

### Verdict
```
### MSG-FIX-PLAN-FINAL — UI Test Verdict
**Tested:** 34 scenarios
**Status:** ✅ APPROVED-FOR-LAUNCH / ❌ NEEDS-CHANGES
**Pass rate:** XX / 34
**Performance numbers:** ...
**Production readiness:** GO / NO-GO
```

---

## ✅ Phase 2 Acceptance Gate

- [ ] ทุก milestone Block 2.1-2.3 = green
- [ ] Final UI Test 34/34 pass (หรือ APPROVED-WITH-NOTES ที่ defer ชัดเจน)
- [ ] Coverage ≥25% (จาก 0.6%)
- [ ] Pre-launch checklist:
  - [ ] DNS configured · Privacy + ToS · GDPR/PDPA review
  - [ ] Status page setup (status.personaldatabank.fly.dev)
  - [ ] Support email setup
  - [ ] Admin setup documented (`runbooks/admin-setup.md`)
  - [ ] Maintenance/incident communication template
  - [ ] Backup tested + restore drill ผ่าน
  - [ ] Beta user feedback positive
- [ ] Deploy `v11.0.0` (final pre-launch release)
- [ ] → **Public launch announce**

═══════════════════════════════════════════════════════════════

# ⚠️ Risk Notes

| Item | Risk | Mitigation |
|------|------|-----------|
| P1.1.1 git filter-repo | DESTRUCTIVE | backup `.git` · test clone |
| P1.1.0/0a schema | migration before app = mismatch | run offline + verify ก่อน P1.1.2 |
| P1.1.3 / P1.2.0 plaintext drop | data loss | pre-migration backup · 24h gap |
| P1.1.4 JWT enforce | Fly refuse start | stage JWT_SECRET_KEY ก่อน deploy code |
| P1.2.5 FK CASCADE rebuild | SQLite limitation · risky | test local clone · backup · PRAGMA off during |
| P1.2.6 sweep `str(e)` 14 sites | regression | unit test all paths |
| P1.3.1 PyThaiNLP add dep | image +30MB · cold start | lazy import + benchmark |
| P1.3.9 TF-IDF LRU | search recall regression | invariant test |
| P2.1.5 Token budget | over-restrictive blocks normal use | generous limits + admin override |
| P2.1.11 LLM_MODEL_PRO | cost +5x · summary differ | A/B test · rollback path |
| P2.3.6 GitHub Actions | tests flake บน CI | run locally first |
| P2.3.12 init_db refactor | break migration | keep old as fallback 1 cycle |

---

# 📊 Success Metrics

| Metric | Baseline | After Phase 1 | After Phase 2 |
|--------|---------:|--------------:|--------------:|
| P0 closed | 0 / 24 | ~18 / 24 | **24 / 24** |
| P1 closed | 0 / 34 | ~20 / 34 | **34 / 34** |
| Test coverage | 0.6% | ~5% | **≥25%** |
| `str(e)` in main.py | 14 | 0 | 0 |
| Endpoints with response_model | 0 | 20 | 20 |
| `except: pass` sites | 10+ | 0 | 0 |
| `print()` in database.py | 28+ | 0 | 0 |
| Indexes on user_id | 0 | 5+ | 5+ |
| FKs without CASCADE | ~30 | 0 | 0 |
| Memory leaks (unbounded caches) | 5 | 0 | 0 |
| Thai search recall | ~40% | **≥80%** | ≥80% |
| `.env` in git history | Yes | **No** | No |
| Container runs root | Yes | **No** | No |
| Daily DB backup | No | No | **Yes** |
| CI/CD pipeline | No | No | **Yes** |
| JSON structured logging | No | No | **Yes** |

---

# 📞 Communication

- **Start phase:** Update `pipeline-state.md`
- **Daily:** Read `for-เขียว.md` inbox · check user notes
- **End of milestone:** Commit + push (tag `[P1.X.Y]` หรือ `[P2.X.Y]`) + CHANGELOG line
- **End of phase:** Send `for-ฟ้า.md` MSG · wait APPROVED before next phase
- **Phase deploy:** Combined per procedure (P1.1 emergency deploys separately)
- **Blocker:** Flag `for-User.md` ถ้าติด > 2 ชม.

---

# 🎯 Definition of Done

## Per milestone
1. ✅ Code committed + push (tag `[PX.Y.Z]`)
2. ✅ Test pass (local pytest หรือ CI ใน Phase 2)
3. ✅ Plan checkbox tick + CHANGELOG line
4. ✅ Memory state updated

## Per Phase
1. ✅ ทุก milestone = green
2. ✅ Acceptance Gate ครบ
3. ✅ Deploy per procedure · cool-down ok
4. ✅ ฟ้า review APPROVED

## Plan complete
1. ✅ Phase 1 + Phase 2 = APPROVED
2. ✅ ฟ้า Final UI Test 34/34
3. ✅ Pre-launch checklist complete
4. → **Public launch announce**

---

**End of plan v3 — 2 phases, deployable, ฟ้า-reviewed**
