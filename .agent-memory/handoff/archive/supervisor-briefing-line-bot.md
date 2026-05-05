# 🎯 Supervisor Briefing — LINE Bot Project

**Project:** Bundle v7.6.0 Foundation + v8.0.0 LINE Bot
**Supervisor:** 🔴 แดง (Daeng) — planning + checkpoint review + course correction
**Executor:** 🤖 AI Agent (other) — hands-on coding + testing + deployment prep
**User:** 👤 owner — external setup + checkpoint approval + final deploy
**Date:** 2026-05-02

---

## 🎬 Why this briefing exists

User authorize **2-tier execution model:**
- AI Agent (executor) — hands-on coding (frontend + backend + tests)
- แดง (supervisor) — planning, checkpoints, course correction, memory updates
- User — external account setup + checkpoint approval + production deploy

แดงเขียน **briefing นี้ + supporting docs** ให้ทุกคนในทีมรู้:
- ใครทำอะไร
- ต้องส่งมอบเมื่อไหร่
- รายงานอะไรกลับมาบ้าง
- เมื่อไหร่ต้องขออนุญาตก่อนทำต่อ

---

## 👥 Role Definitions

### 🔴 แดง (Supervisor) — บทบาท
**Authority:** read-only on source code + write on `.agent-memory/`

**ทำอะไร:**
1. **Plan ownership** — เป็นคนถือ `plans/foundation-v7.6.0.md` + `plans/line-bot-v8.0.0.md`
2. **Course correction** — ถ้า executor agent หลงทาง / scope creep / blocker → แดงปรับ plan + update instructions
3. **Checkpoint review** — review report ของ executor หลังแต่ละ phase (16 phase รวมทั้ง 2 plans)
4. **Memory updates** — update `pipeline-state.md`, `contracts/api-spec.md`, `project/decisions.md` ตามที่ project progress
5. **Inter-agent communication** — ถ้า executor ส่งข้อความ inbox มา (เช่น "plan ไม่ชัด" / "เจอ edge case") → แดงตอบ
6. **Risk monitoring** — แต่ละ phase ดู risks ใน plan → ถ้า materialize → response

**ห้ามทำ:**
- ❌ เขียน source code
- ❌ Run tests
- ❌ Commit / push / deploy
- ❌ ตัดสินใจ deploy แทน user

### 🤖 AI Agent (Executor) — บทบาท
**Authority:** full code authority — frontend + backend + tests + commits (local)

**ทำอะไร:**
1. **Build all code** — Python (FastAPI) + JavaScript (vanilla) + HTML + CSS
2. **Frontend (UI):**
   - `legacy-frontend/auth-line.html` — LINE account link landing page
   - `legacy-frontend/auth-line.js` — handler logic
   - `legacy-frontend/app.html` — เพิ่ม LINE section ใน profile modal
   - `legacy-frontend/app.js` — `loadLineStatus()`, `disconnectLine()` functions
   - `legacy-frontend/styles.css` — styles สำหรับ LINE UI
   - `legacy-frontend/landing.html` + `landing.js` — cleanup `reset_token` debug display
   - `legacy-frontend/line-rich-menu.png` — design 2500×1686 image (use Figma/Canva, OR generate via SVG-to-PNG)
3. **Backend (server):**
   - `backend/email_service.py` — Resend wrapper
   - `backend/url_fetcher.py` — SSRF-safe URL fetcher
   - `backend/signed_urls.py` — JWT-signed download URLs
   - `backend/line_bot.py` — LINE webhook handler + send/receive
   - `backend/bot_handlers.py` — platform-agnostic command handlers
   - `backend/bot_adapters.py` — BotAdapter abstract + LineBotAdapter
   - `backend/bot_messages.py` — Flex Message builders
   - แก้: `plan_limits.py`, `auth.py`, `mcp_tools.py`, `config.py`, `main.py`, `database.py`
4. **Tests:**
   - 80+ test cases ตาม plan
   - Run pytest + verify pass
   - Smoke scripts in-process
5. **Commits:**
   - Local commits ตาม commit message format ใน plan
   - **ห้าม push ไป remote** จนกว่า user/แดง อนุญาต
6. **Reporting:**
   - หลังแต่ละ phase → ส่ง report ใน `inbox/for-แดง.md`
   - แดงตอบกลับ → execute next phase

**ห้ามทำ:**
- ❌ Push to remote
- ❌ Merge to master
- ❌ `fly deploy` (production)
- ❌ Drop tables / destructive ops
- ❌ Bypass plan โดยไม่ขอ
- ❌ แตะ `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`
- ❌ Take user-facing actions (post LINE messages to real users, send emails to real recipients during dev)

### 👤 User (Owner) — บทบาท
**Authority:** final approver + external account holder

**ทำอะไร:**
1. **Phase 0 — External Setup** (~1-2 ชม.):
   - สมัคร LINE Developer account → Provider → 2 channels
   - สมัคร Resend account → verify DNS
   - Set Fly.io secrets
   - ตามไฟล์ `handoff/external-setup-checklist.md`
2. **Checkpoint approval** — หลังแต่ละ phase major:
   - Review report จากแดง
   - ตอบ "approve next phase" หรือ "ขอแก้ X"
3. **Production deploy** (~30 min):
   - Review final commits + memory state
   - Push to remote
   - `fly deploy`
   - Verify production smoke

**ห้ามทำ (เพื่อความปลอดภัย):**
- ⚠️ Share LINE channel access tokens ใน chat / screenshot
- ⚠️ Commit `.env` ลง git
- ⚠️ Skip checkpoint review (อันตราย)

---

## 📋 Project Scope (Bundle v7.6.0 + v8.0.0)

### Plan A: Foundation v7.6.0 (~2.5 weeks)
ดู [plans/foundation-v7.6.0.md](../plans/foundation-v7.6.0.md) ฉบับเต็ม

**Phases:**
- Phase A1: Restore plan_limits (BACKLOG-008)
- Phase A2: Email service via Resend (BACKLOG-009)
- Phase B: MCP USP (url_fetcher + wire upload_text + add upload_from_url)
- Phase C: Universal signed download URLs (`/d/{token}`)

**Why required first:**
- Plan limits = ป้องกัน abuse + อยู่ใน production stack ก่อน LINE บูม
- Email service = password reset flow ทำงานสมบูรณ์
- Signed URLs = **REQUIRED workaround** สำหรับ LINE bot ส่งไฟล์กลับ user (LINE bot ส่ง PDF ตรงไม่ได้)
- MCP USP = unique value props + tested integration ก่อน LINE adopters มา

### Plan B: LINE Bot v8.0.0 (~3-4 weeks)
ดู [plans/line-bot-v8.0.0.md](../plans/line-bot-v8.0.0.md) ฉบับเต็ม

**Phases:**
- Phase D: Foundation (LINE webhook + signature verify + DB table + config)
- Phase E: Account linking + welcome flow
- Phase F: File upload flow (handle file/image/audio/video events)
- Phase G: Chat / Search / Stats / Get-file
- Phase H: Forward + edge cases
- Phase I: Rich Menu (6-tile)
- Phase J: Profile UI integration + admin status
- Phase K: Manual mobile testing + polish

### Total Timeline
- Phase 0 (external setup): ~1-2 hours (user) — **ทำก่อน executor เริ่ม**
- Phases A-C (Foundation): ~2.5 weeks (executor)
- Phases D-K (LINE Bot): ~3-4 weeks (executor)
- Final review + deploy: ~1-2 days
- **Total: ~6-7 weeks**

---

## 🔄 Collaboration Protocol

### 1. Phase Lifecycle (every phase)

```
[แดง] Phase X kicked off via inbox/for-Executor.md
       ↓
[Executor] อ่าน plan + inbox → start work
       ↓
[Executor] Build code + tests + commits (local only)
       ↓
[Executor] Run all tests → verify pass
       ↓
[Executor] Write report → inbox/for-แดง.md
   - List of files changed
   - Commits made
   - Tests pass count
   - Issues encountered (if any)
   - Suggested next phase
       ↓
[แดง] Review report → 1 of:
   - ✅ Approve → next phase
   - ⚠️ Needs fix → write back to inbox/for-Executor.md
   - 🔄 Plan revision needed → update plan + restart phase
       ↓
[Loop until last phase done]
       ↓
[แดง] Write final review → inbox/for-User.md
       ↓
[User] Review + approve → push + deploy
```

### 2. Communication Channels

| File | Purpose | Who writes | Who reads |
|---|---|---|---|
| `inbox/for-Executor.md` | Tasks/instructions from แดง | แดง | Executor |
| `inbox/for-แดง.md` | Phase reports + questions | Executor | แดง |
| `inbox/for-User.md` | Major checkpoints + final approval requests | แดง | User |
| `current/pipeline-state.md` | Live state | แดง | All |

### 3. Asks-Before-Doing Protocol (Executor must ask)

Executor **ห้ามตัดสินใจเอง** ในเหตุการณ์เหล่านี้ — ต้องเขียนใน `inbox/for-แดง.md` แล้วรอตอบ:

1. **Plan ambiguous** — step ใน plan ไม่ชัด → เขียน "PLAN-AMBIG-XXX" + รอตอบ
2. **Plan vs reality mismatch** — code structure ต่างจาก plan → เขียน "PLAN-MISMATCH-XXX" + รอ
3. **Encountered blocker** — error ที่แก้ไม่ได้ → เขียน "BLOCK-XXX" + รอ
4. **Scope question** — "ควรทำ X เพิ่มไหม?" → เขียน "SCOPE-XXX" + รอ
5. **Discovered bug นอก plan** — เจอ existing bug → เขียน "BUG-DISCOVERED-XXX" + รอ
6. **External call required** — ต้อง hit production / external API → เขียน "EXT-CALL-XXX" + รอ

แดงตอบใน `inbox/for-Executor.md` ภายใน 1 turn → executor ทำต่อ

### 4. Phase Checkpoints (User-required approval)

User ต้อง approve ก่อน executor ทำต่อ:

| Checkpoint | When | Who notifies | What user reviews |
|---|---|---|---|
| **CP-0: External setup done** | Before Phase A | User signals to Executor | All accounts created + tokens in Fly secrets |
| **CP-A: Foundation done** | After Phase A1+A2+B+C | แดง writes inbox/for-User.md | All foundation tests pass + email arrives |
| **CP-B: LINE bot core done** | After Phase D+E+F+G | แดง writes inbox/for-User.md | Manual mobile test on staging |
| **CP-C: Final pre-deploy** | After Phase K | แดง writes inbox/for-User.md | Full review + commits ready to push |
| **CP-D: Production deploy** | After User approves CP-C | User runs `fly deploy` | Verify production smoke |

### 5. Course Correction Protocol

If executor goes off plan:
1. **Detection:** แดง spots in phase report
2. **Pause:** แดง writes `inbox/for-Executor.md` "PAUSE — please don't proceed"
3. **Diagnose:** แดง reads code + plan + identifies gap
4. **Fix:** แดง updates plan OR writes precise instructions
5. **Resume:** Executor reads new instructions + continues
6. **Lesson:** แดง logs in `project/decisions.md` if pattern emerges

---

## 🛡️ Safety Guards

### Code Safety
- ❌ Executor ห้ามแตะ secrets files (`.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`)
- ❌ Executor ห้าม push ไป remote without User approval
- ❌ Executor ห้าม merge ไป master without User approval
- ❌ Executor ห้าม `fly deploy` to production
- ❌ Executor ห้ามรัน `git reset --hard`, `git push --force`, drop tables, `rm -rf`

### External Action Safety
- ⚠️ ห้ามส่ง real LINE messages ไปยัง user จริงระหว่าง dev (ใช้ Account Link testing mode)
- ⚠️ ห้ามส่ง real emails ไปยัง random addresses (mock Resend ใน tests, real email send only ใน manual smoke)
- ⚠️ ห้าม hit production Stripe (ใช้ test keys ใน dev)
- ⚠️ ห้าม share secrets ใน chat / report

### Data Safety
- ✅ Migrations ADD-only (DB-003 invariant)
- ✅ Auto-backup ก่อน migration
- ✅ Test ใช้ test DB ไม่ touch production
- ✅ User confirms DESTRUCTIVE actions explicitly

---

## 📊 Phase Roadmap (Detailed)

### Phase 0 — External Setup (User, ~1-2 hr)
**Owner:** User (with แดง guide)
**Output:** Tokens in Fly secrets + DNS verified
**Checklist:** [handoff/external-setup-checklist.md](external-setup-checklist.md)

### Phase A1 — Restore plan_limits (Executor, ~30 min)
- Edit `backend/plan_limits.py` lines 15-44
- Verify tests pass
- Local commit: `feat(plan-limits): restore production values [BACKLOG-008]`

### Phase A2 — Email service (Executor, ~4 hr)
- Create `backend/email_service.py`
- Wire `request_password_reset()` ใน `auth.py`
- Drop `reset_token` from JSON response
- Frontend cleanup
- Tests
- Commit: `feat(email): wire Resend for password reset [BACKLOG-009]`

### Phase B — MCP USP (Executor, ~5 days)
- B.1: Create `url_fetcher.py` (SSRF defense)
- B.2: Refactor `organize_new_files`
- B.3: Wire `upload_text` properly
- B.4: Add `upload_from_url` tool
- 35 test cases
- Commits: 2 (one for url_fetcher, one for tool wiring)

### Phase C — Signed URLs (Executor, ~2 days)
- C.1: Create `signed_urls.py`
- C.2: Add `GET /d/{token}` endpoint
- C.3: Update `get_file_link` MCP tool
- 15 test cases
- Commit: `feat(downloads): universal signed download URLs /d/{token}`

→ **Checkpoint A: Foundation done** (User approve)

### Phase D — LINE Foundation (Executor, ~3 days)
- D.1: Add `line-bot-sdk-python` to requirements
- D.2: Add config env vars + `is_line_configured()`
- D.3: Add `LineUser` table + migration
- D.4: Create `bot_adapters.py` skeleton (BotAdapter abstract)
- D.5: Create `line_bot.py` skeleton (webhook + signature verify)
- D.6: Add `POST /webhook/line` endpoint
- 5 test cases (signature verify + ack response)

### Phase E — Account Linking + Welcome (Executor, ~3 days)
- E.1: `follow` event handler + linkToken redirect
- E.2: `auth-line.html` + `auth-line.js` frontend
- E.3: `POST /api/line/confirm-link` endpoint
- E.4: `accountLink` webhook handler
- E.5: Welcome flow (3 messages: text + Flex + Quick Reply)
- E.6: Build `bot_messages.py` Flex builders (status card, welcome card)
- 8 test cases

### Phase F — File Upload (Executor, ~5 days)
- F.1: Implement `LineBotAdapter.download_attachment()`
- F.2: Handle `message` events (file/image/video/audio)
- F.3: URL detection in text messages
- F.4: Reuse v7.6.0 upload pipeline (extract + plan limit + BYOS)
- F.5: Reply Flex confirmation card
- F.6: Plan limit error UX (Flex error card)
- 10 test cases

### Phase G — Chat / Search / Stats / Get-file (Executor, ~4 days)
- G.1: Intent detection in `bot_handlers.py`
- G.2: Chat path (call `/api/chat`)
- G.3: Search path (vector_search → Flex carousel)
- G.4: Stats path (DB query → Flex card)
- G.5: Get file back (Flex card + signed URL from Phase C)
- 12 test cases

### Phase H — Forward + Edge Cases (Executor, ~2 days)
- H.1: Forwarded file handling
- H.2: Reply token expiry → push fallback
- H.3: Push quota tracking
- H.4: Standard error Flex builders
- 6 test cases

### Phase I — Rich Menu (Executor, ~2 days)
- I.1: Design Rich Menu image (2500×1686)
- I.2: `scripts/setup_line_rich_menu.py` deploy script
- I.3: Postback handlers
- 4 test cases

### Phase J — Profile UI Integration (Executor, ~1 day)
- J.1: app.html LINE section in profile modal
- J.2: app.js `loadLineStatus()`, `disconnectLine()`
- J.3: Admin status endpoint `GET /api/line/status`
- J.4: `POST /api/line/disconnect`
- 5 test cases

### Phase K — Polish + Mobile Testing (Executor, ~2 days)
- K.1: E2E manual tests on staging (iOS + Android LINE app)
- K.2: Bug fixes from testing
- K.3: Final code review + cleanup
- K.4: Update `contracts/api-spec.md` + `project/decisions.md`
- K.5: Bump APP_VERSION 7.5.0 → 8.0.0 ใน `config.py`
- K.6: Update `pipeline-state.md` → `review_passed`

→ **Checkpoint C: Final pre-deploy** (User approve)

### Phase L — Production Deploy (User, ~30 min)
- L.1: User reviews final commits
- L.2: User pushes to remote
- L.3: User runs `fly deploy`
- L.4: User verifies production smoke (manual mobile test)
- L.5: Update `pipeline-state.md` → `done`

---

## 🎯 Decisions Already Made (8 from foundation + 8 from LINE)

### Foundation v7.6.0 (Q1-Q8)
| # | Q | Decision |
|---|---|---|
| Q1 | max_file_size_mb | Original (Free 10MB / Starter 20MB) |
| Q2 | Email service | Resend |
| Q3 | URL fetch HTTP | HTTPS-only |
| Q4 | Auto-organize | Sync default |
| Q5 | Existing > 5 files | Soft-lock |
| Q6 | Signed URL TTL | 30 min |
| Q7 | URL fetch max | เท่า plan limit |
| Q8 | upload_text default | .md |

### LINE Bot v8.0.0 (LQ1-LQ8)
| # | Q | Decision |
|---|---|---|
| LQ1 | 1 LINE → 1 PDB | 1:1 unique (multi defer) |
| LQ2 | Free user LINE limit | เท่า web (`check_upload_allowed`) |
| LQ3 | Welcome re-show | Once-only (welcomed flag) |
| LQ4 | Push notify "organize done" | Opt-in (default off) |
| LQ5 | LINE Login OAuth | ✅ ใช่ใน v8.0.0 |
| LQ6 | Domain | personaldatabank.fly.dev |
| LQ7 | Bot name + bio | "PDB Assistant" + "ผู้ช่วยจัดการข้อมูลส่วนตัวของคุณ" |
| LQ8 | Logo PDB ใน Rich Menu | ใช่ |

→ **All 16 decisions baked into plans + executor prompt**

---

## ✅ Success Criteria

Project ถือว่าเสร็จเมื่อ:

1. ✅ ทั้ง 11 phases (A1-K) ทำเสร็จ
2. ✅ 80+ tests (Foundation) + 50+ tests (LINE Bot) = **130+ tests pass**
3. ✅ Existing 346/346 tests ยัง pass (no regression)
4. ✅ Manual mobile test ผ่าน iOS + Android LINE app
5. ✅ Production deploy + smoke test pass
6. ✅ Memory updated (pipeline-state, api-spec, decisions)
7. ✅ APP_VERSION bumped 7.5.0 → 8.0.0
8. ✅ All commits have proper message + Author-Agent footer

---

## 📁 Related Documents

- **Plans (what to build):**
  - [plans/foundation-v7.6.0.md](../plans/foundation-v7.6.0.md) — Foundation phases A-C
  - [plans/line-bot-v8.0.0.md](../plans/line-bot-v8.0.0.md) — LINE bot phases D-K
- **Handoff (how to coordinate):**
  - [handoff/supervisor-briefing-line-bot.md](supervisor-briefing-line-bot.md) — this file
  - [handoff/external-setup-checklist.md](external-setup-checklist.md) — User Phase 0 manual
- **Prompts (bootstrap agents):**
  - [prompts/prompt-line-bot-executor.md](../prompts/prompt-line-bot-executor.md) — Executor agent bootstrap
- **Research (background):**
  - [research/competitor-deep-dive.md](../research/competitor-deep-dive.md)
  - [research/chat-bot-platforms-feasibility.md](../research/chat-bot-platforms-feasibility.md)
  - [research/mcp-file-upload-deep-dive.md](../research/mcp-file-upload-deep-dive.md)

---

**End of supervisor briefing.** แดงเป็น single source of truth สำหรับ project coordination — ถ้ามีคำถามไม่ชัดเจน → write `inbox/for-แดง.md`

— แดง (Daeng)
