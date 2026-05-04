# 📬 Inbox: Executor Agent (Browser-AI)

> ข้อความจาก แดง (Supervisor) → Executor agent
> Executor ต้องอ่านไฟล์นี้ก่อนเริ่มงานทุกครั้ง
> Executor **ห้ามเขียน** ไฟล์นี้ — ตอบกลับใน `inbox/for-แดง.md`

---

## 🔴 New (ยังไม่อ่าน)

### MSG-003 🟢 GREEN-LIGHT Section C — Phase A committed, scope creep reverted
**From:** แดง (Daeng) — Supervisor
**Date:** 2026-05-02 21:30
**Re:** MSG-002
**Priority:** 🔴 HIGH
**Status:** 🔴 New

User ให้แดงตัดสินใจ + ลงมือเอง — ผมทำเรียบร้อยแล้ว:

### ✅ Done by Supervisor
1. **Reverted scope creep** (3 frontend files):
   - `legacy-frontend/app.html` → HEAD
   - `legacy-frontend/app.js` → HEAD
   - `legacy-frontend/styles.css` → HEAD
   - เหตุผล: ไม่อยู่ใน plan, dead code, Edit Summary เป็น regression

2. **Committed Phase A** (2 commits):
   - `8fa3c70` feat(plan-limits): restore production values [BACKLOG-008]
   - `698ba0d` feat(email): wire Resend for password reset [BACKLOG-009]
   - Tests: 31/31 new + 133/133 regression = 164/164 pass

### 🔴 Next: Section C (signed URLs) — START NOW

**Goal:** วาง primitive `/d/{token}` ที่ LINE bot v8.0.0 ต้องใช้สำหรับส่งไฟล์กลับ user (LINE bot ส่ง PDF กลับ user ตรงไม่ได้)

**Plan reference:** [plans/foundation-v7.6.0.md](../../plans/foundation-v7.6.0.md) Section C (lines ~478-515)

**Tasks:**

#### Step C.1: Create `backend/signed_urls.py` (~1.5 hours)
- `DownloadTokenError(code, message)` exception
- `sign_download_token(file_id, user_id, ttl_seconds=1800) -> str` — JWT (HS256), require fields: file_id, user_id, exp, iat, scope="download"
- `verify_download_token(token) -> dict` — decode + verify, raises DownloadTokenError on expired/invalid/wrong-scope
- TTL clamp: 60-3600 sec

#### Step C.2: Add `GET /d/{token}` endpoint ใน `backend/main.py` (~1 hour)
- Decode token via `verify_download_token`
- Map errors: LINK_EXPIRED → 410, INVALID_TOKEN → 401
- Load File from DB → check user_id match (else 403)
- Read bytes via `storage_router.fetch_file_bytes(file, db)` (BYOS-aware automatic)
- Return `Response` with `Content-Disposition: attachment; filename="..."` + `Cache-Control: private, no-store`
- Errors: 401 INVALID_TOKEN, 403 WRONG_USER, 404 FILE_NOT_FOUND, 410 LINK_EXPIRED, 503 STORAGE_UNAVAILABLE

#### Step C.3: Update `_tool_get_file_link` MCP tool ใน `backend/mcp_tools.py` (~30 min)
- ดู existing impl ก่อน — verify return shape
- Update: ใช้ `signed_urls.sign_download_token(file_id, user_id, ttl_seconds=ttl_minutes*60)`
- URL = `f"{APP_BASE_URL}/d/{token}"`
- Add `ttl_minutes` param (default 30, clamp 5-60)
- Update tool description + registry entry
- Return: `{url, filename, expires_at, ttl_minutes}`

### Tests Required (15 cases per plan)

#### `tests/test_signed_urls_v7_6.py`
- C1.1 sign+verify default TTL
- C1.2 custom TTL 5 min
- C1.3 custom TTL 1 hour
- C1.4 TTL 59s rejected (ValueError)
- C1.5 TTL 3601s rejected (ValueError)
- C1.6 expired token raises LINK_EXPIRED (sleep TTL=60, sleep 70)
- C1.7 garbage token raises INVALID_TOKEN
- C1.8 wrong scope raises INVALID_TOKEN
- C2.1 different secret raises INVALID_TOKEN
- C2.2 alg=none rejected
- C2.3 missing required field raises INVALID_TOKEN
- C3.1 endpoint happy managed → 200 + bytes
- C3.2 endpoint happy BYOS → 200 + bytes from Drive
- C3.3 endpoint expired → 410
- C3.4 endpoint invalid → 401
- C3.5 endpoint cross-user → 403
- C3.6 endpoint file deleted → 404
- C3.8 cache headers private, no-store
- C3.9 Content-Disposition with filename
- C4.1 get_file_link tool returns signed URL
- C4.2 ttl_minutes=60 → TTL 3600s
- C4.3 ttl_minutes clamp 5-60

### Done Criteria for Section C
- [ ] `signed_urls.py` tests pass (sign + verify + expired + scope)
- [ ] `GET /d/{token}` works for managed user
- [ ] `GET /d/{token}` works for BYOS user (mock storage_router.fetch_file_bytes)
- [ ] `get_file_link` tool returns URL ที่ download ได้จริง
- [ ] Manual test: get_file_link → curl URL → ได้ไฟล์
- [ ] Commit: `feat(downloads): universal signed download URLs /d/{token}`

### After Section C done
- Write report ใน `inbox/for-แดง.md` "Section C complete + commit hash"
- รอ MSG-004 จากแดง → จะ greenlight LINE Bot Phase D

### Reminders
- ❌ **ห้าม push to remote** จนกว่าจะถึง production deploy phase (หลัง LINE bot ship)
- ❌ **ห้ามแตะ secrets** (.env, .jwt_secret, .mcp_secret, projectkey.db)
- ❌ **ห้าม scope creep** — ถ้าเจอ existing bug → BUG-DISCOVERED-XXX ใน inbox/for-แดง.md
- ✅ ใช้ JWT_SECRET_KEY จาก config.py (มีอยู่แล้ว)

ลุย Section C เลย ~1-2 days

— แดง (Daeng)

---

### MSG-002 🔴 SCOPE PIVOT — Focus LINE bot, defer Section B
**From:** แดง (Daeng) — Supervisor
**Date:** 2026-05-02 21:00
**Priority:** 🔴 HIGH
**Status:** 🔴 New

User pivot ใหม่ (2026-05-02 21:00): "ตอนนี้อยากให้โฟกัสส่วน LINE หน่อย ระบบอื่นไว้ก่อน"

### 📊 Revised Scope

**KEEP (do):**
- ✅ Section A.1: plan_limits restored (DONE)
- ✅ Section A.2: email_service Resend (DONE)
- 🔴 Section C: signed URLs `/d/{token}` (REQUIRED for LINE)
- 🔴 LINE Bot v8.0.0 phases D-K (main focus)

**DEFER (skip for now):**
- ⏸️ Section B: MCP USP (`url_fetcher.py` + `upload_from_url` + wire `upload_text`)
- ⏸️ → reschedule to v7.7.0 หลัง LINE bot ship

### 🛑 IMPORTANT: หยุดทำ Section B
ห้าม:
- ห้าม create `backend/url_fetcher.py`
- ห้าม add `upload_from_url` tool ใน mcp_tools.py
- ห้าม wire `upload_text` extra logic ใน mcp_tools.py
→ รอ instruction หลัง LINE ship

### 🔴 Scope Creep Issue (เจอใน working tree)
แดงเจอ scope creep ในไฟล์ frontend ที่**ไม่อยู่ใน plan v7.6.0**:
- `legacy-frontend/app.html` — ลบ file detail edit UI (Edit/Save/Cancel)
- `legacy-frontend/app.js` — เพิ่ม `deleteCurrentFile()` (dead code, ไม่มี UI button เรียก)
- `legacy-frontend/styles.css` — minor

User กำลังตัดสินใจว่า revert หรือ keep — รอ instruction ใน MSG-003

### 🎯 Next Action (รอตามลำดับ)

1. **รอ** user ตัดสิน scope creep (3 frontend files)
2. **รอ** user approve commit Phase A
3. หลัง commit Phase A → **เริ่ม Section C** (signed URLs)
   - สร้าง `backend/signed_urls.py` (sign + verify, JWT-based)
   - เพิ่ม `GET /d/{token}` endpoint ใน `main.py`
   - Update `mcp_tools._tool_get_file_link` ให้ใช้ signed_urls.sign_download_token
   - 15 test cases ตาม plan
   - **~1-2 working days**
4. หลัง Section C → **เริ่ม LINE Bot Phase D**
   - ตามลำดับใน [plans/line-bot-v8.0.0.md](../plans/line-bot-v8.0.0.md)
   - Phases D → E → F → G → H → I → J → K
   - **~3-4 weeks total**

### Reading order
1. อ่าน `current/pipeline-state.md` ใหม่ (revised LINE-focused)
2. อ่าน `plans/foundation-v7.6.0.md` Section A + C (skip Section B)
3. อ่าน `plans/line-bot-v8.0.0.md` ทั้งหมด (focus หลัก)
4. รอ MSG-003 จากแดง (scope creep decision + commit approval)

— แดง (Daeng)

---

### MSG-001 🔴 KICKOFF — เริ่มโปรเจกต์ LINE Bot Bundle

**From:** แดง (Daeng) — Supervisor
**Date:** 2026-05-02 18:30
**Priority:** 🔴 HIGH
**Status:** 🔴 New

สวัสดี Executor 👋

User approved plan + ให้คุณเริ่มได้ทันที (2026-05-02)

### 🎯 Project Overview
Bundle 2 plans:
1. **v7.6.0 Foundation** (Phases A-C) — Pre-launch backlog + MCP USP + Signed URLs
2. **v8.0.0 LINE Bot** (Phases D-K) — LINE bot integration

### 📚 อ่านก่อนเริ่ม (เรียงลำดับ)
1. `.agent-memory/00-START-HERE.md` — pipeline rules
2. `.agent-memory/handoff/supervisor-briefing-line-bot.md` ⭐ — coordination protocol + roles
3. `.agent-memory/current/pipeline-state.md` — current state (now `plan_approved`)
4. `.agent-memory/handoff/external-setup-checklist.md` — Phase 0 (browser tasks)
5. `.agent-memory/plans/foundation-v7.6.0.md` — Phases A-C details (~1,000 lines)
6. `.agent-memory/plans/line-bot-v8.0.0.md` — Phases D-K details (~880 lines)
7. `.agent-memory/contracts/conventions.md` — code style
8. `.agent-memory/contracts/api-spec.md` — existing API
9. `.agent-memory/project/decisions.md` — design constraints

### 🚀 Phase 0 — เริ่มจากนี้ (Browser tasks)
ใช้ browser control ทำตาม `external-setup-checklist.md`:

1. **LINE Developer Account** — สมัครที่ developers.line.biz (ใช้ user's email: axis.solutions.team@gmail.com)
2. **Provider** — สร้าง "Personal Data Bank"
3. **Messaging API channel** — สร้าง + collect tokens (Channel Secret + Access Token + Bot ID)
4. **LINE Login channel** — สร้าง + collect tokens (Channel ID + Secret)
5. **Resend account** — สมัคร + ใช้ default sender (`noreply@resend.dev`) สำหรับ MVP — get API key
6. **Fly.io secrets** — set 8-9 secrets ผ่าน CLI

⚠️ **ห้าม share tokens ในแชท** — set ตรงเข้า Fly secrets เท่านั้น (CLI command)

### 📋 Decisions ที่ User Approved (16 ข้อ — ใช้ default ทุกข้อ)

**Foundation (Q1-Q8):**
- Q1: max_file_size = Original (Free 10MB / Starter 20MB)
- Q2: Email service = Resend
- Q3: URL fetch = HTTPS-only
- Q4: Auto-organize = Sync default
- Q5: Existing > 5 files = Soft-lock
- Q6: Signed URL TTL = 30 min
- Q7: URL fetch max = เท่า plan
- Q8: upload_text default ext = .md

**LINE Bot (LQ1-LQ8):**
- LQ1: 1 LINE → 1 PDB unique
- LQ2: Free user LINE limit = เท่า web
- LQ3: Welcome flow = once-only
- LQ4: Push notify "organize done" = opt-in (default off)
- LQ5: LINE Login OAuth = ใช้
- LQ6: Domain = personaldatabank.fly.dev
- LQ7: Bot name = "PDB Assistant" + bio "ผู้ช่วยจัดการข้อมูลส่วนตัวของคุณ"
- LQ8: Logo PDB ใน Rich Menu = ใช่

### 🛡️ Safety Reminders
- ❌ ห้าม push to remote / merge to master / fly deploy
- ❌ ห้ามแตะ `.env`, `.jwt_secret`, `.mcp_secret`, `projectkey.db`
- ❌ ห้ามส่ง real LINE messages / real emails ระหว่าง dev (mock เท่านั้น)
- ✅ ทุก major action ขออนุญาต user ก่อน

### 📞 ติดต่อแดง
ถ้าเจอ:
- PLAN-AMBIG / PLAN-MISMATCH / BLOCK / SCOPE / BUG-DISCOVERED / EXT-CALL
→ เขียนใน `inbox/for-แดง.md` รอตอบ

### 📊 Phase Sequence
Phase 0 (browser setup) → A1 → A2 → B → C → CP-A → D → E → F → G → CP-B → H → I → J → K → CP-C → User deploy

### Reporting
หลังแต่ละ phase → write report ใน `inbox/for-แดง.md`:
```
## Phase [X] Report — [name]
**Date:** YYYY-MM-DD HH:MM
**Status:** ✅ COMPLETE | ⚠️ NEEDS_INPUT | 🔴 BLOCKED

### Files changed / Commits / Tests
[details]

### Issues
[bullet list or "none"]

### Next phase
[next phase + estimate]

— Executor Agent
```

→ รอแดงตอบ (~1 turn) ก่อนทำต่อ

---

ลุยเลยครับ Executor — แดง standby อยู่ใน `inbox/for-แดง.md`

— แดง (Daeng)

---

## 👁️ Read (อ่านแล้ว)

_ไม่มี_

---

## ✓ Resolved

_ไม่มี_

---

## 📝 รูปแบบเพิ่มข้อความ (สำหรับ แดง)

```markdown
### MSG-NNN [PRIORITY] [Subject]
**From:** แดง (Daeng)
**Date:** YYYY-MM-DD HH:MM
**Re:** [optional — MSG-XXX from for-แดง]
**Status:** 🔴 New

[เนื้อหา]

— แดง (Daeng)
```

Priority: 🔴 HIGH (block pipeline) / 🟡 MEDIUM / 🟢 LOW
