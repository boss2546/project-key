# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current Pipeline State: `review_passed` ✅ (v8.0.0 LINE BOT — READY TO DEPLOY)

### 🎯 LINE-FOCUSED PROJECT — COMPLETE (2026-05-04)

**Pivot:** User เลือก "โฟกัส LINE bot, ระบบอื่นเลื่อน" → Section B (MCP USP) defer ไป v7.7.0
**Outcome:** Foundation (A+C) + LINE Bot (D-K) all built, tested, committed. **274/274 tests pass**.

### 📊 Status Snapshot

| Phase | Plan section | Status |
|---|---|---|
| **A1** Restore plan_limits | foundation-v7.6.0 §A.1 | ✅ **COMMITTED** `8fa3c70` (17 tests pass) |
| **A2** Email service Resend | foundation-v7.6.0 §A.2 | ✅ **COMMITTED** `698ba0d` (14 tests pass) |
| **B** MCP USP (url_fetcher + upload tools) | foundation-v7.6.0 §B | ⏸️ **DEFERRED** to v7.7.0 |
| **C** Universal signed URLs `/d/{token}` | foundation-v7.6.0 §C | ✅ **COMMITTED** `1172d83` (23 tests pass) |
| **D** LINE Bot Foundation | line-bot-v8.0.0 §D | ✅ **COMMITTED** `9834349` (20 tests pass) |
| **J + E (partial)** Profile UI + auth-line landing | line-bot-v8.0.0 §J/§E | ✅ **COMMITTED** `0b9257d` |
| **E (full) + F** Real account link + file/text handlers | line-bot-v8.0.0 §E/§F | ✅ **COMMITTED** `a810daa` (43 tests pass) |
| **G** Text intent dispatch + chat/search/stats | line-bot-v8.0.0 §G | ✅ **COMMITTED** `08008cf` (30 tests pass) |
| **G+** URL_UPLOAD intent | line-bot-v8.0.0 §G | ✅ **COMMITTED** `7b22579` |
| **H + I** Push fallback, quota, group leave, Rich Menu | line-bot-v8.0.0 §H/§I | ✅ **COMMITTED** `ba4df60` (25 tests pass) |
| **K** Polish + version bump + final report | line-bot-v8.0.0 §K | ✅ **THIS COMMIT** (APP_VERSION 8.0.0) |

### ✅ Phase A Shipped (2026-05-02 21:30)

**Commits (2):**
- `8fa3c70` feat(plan-limits): restore production values [BACKLOG-008]
- `698ba0d` feat(email): wire Resend for password reset [BACKLOG-009]

**Test results:** 31/31 new + 133/133 regression = **164/164 pass**

**Scope creep handling:** Reverted (3 frontend files) — file detail edit UI changes + dead code `deleteCurrentFile()` were out-of-scope, now reverted to HEAD per supervisor decision

### ✅ Section C Shipped (2026-05-02 22:30)

**Commit (1):**
- `1172d83` feat(downloads): universal signed download URLs /d/{token}

**Files:**
- backend/signed_urls.py (NEW) — JWT sign + verify
- backend/main.py — GET /d/{token} endpoint (BYOS-aware)
- backend/mcp_tools.py — _tool_get_file_link rewritten + ttl_minutes param
- tests/test_signed_urls_v7_6.py (NEW) — 23 cases

**Test results:** 23/23 new + 156/156 regression = **179/179 pass**

**Built by:** 🔴 แดง (supervisor mode override per user authorization 2026-05-02 22:00 — "งานหลังบ้านคุณทำเลย")

### ✅ Phase D Shipped (2026-05-04 05:30)

**Commit (1):**
- `9834349` feat(line-bot): Phase D foundation — webhook + signature verify + LineUser table [v8.0.0]

**Files:**
- requirements.txt + requirements-fly.txt — line-bot-sdk>=3.11.0
- backend/config.py — LINE config env vars + is_line_configured() + is_line_login_configured()
- backend/database.py — LineUser table + idempotent index migration
- backend/bot_adapters.py (NEW) — BotAdapter abstract + NoopBotAdapter + LineBotAdapter skeleton
- backend/line_bot.py (NEW) — verify_signature (HMAC-SHA256) + handle_line_event dispatcher
- backend/main.py — POST /webhook/line endpoint (503/401/400/200 ack)
- tests/test_line_bot_v8_0_phase_d.py (NEW) — 20 cases

**Test results:** 20/20 new + 176/176 regression = **196/196 pass**

**Behavior:** LINE bot ปิดเงียบเมื่อ env vars ไม่ตั้ง (503 LINE_NOT_CONFIGURED) — ไม่กระทบ existing endpoints

**Built by:** 🔴 แดง (supervisor mode, parallel กับ Browser Worker setup)

### ✅ Phases E-K Shipped (2026-05-04)

**Commits (5):**
- `0b9257d` feat(line-bot): Phase J + E partial — profile UI + account-link landing
- `a810daa` feat(line-bot): Phase E full + Phase F — real account linking + file/text handlers
- `08008cf` feat(line-bot): Phase G — text intent dispatch + parallel-agent E.5 redirect
- `7b22579` feat(line-bot): URL_UPLOAD intent + handle_url_upload
- `ba4df60` feat(line-bot): Phase H + I — push fallback, quota, group leave, Rich Menu

**Test results:** 274/274 (172 LINE-specific + 102 regression)

**What shipped:**
- Real LINE Account Link flow (linkToken + nonce + auth-line.html landing)
- File upload from chat (PDF/DOCX/image/audio → process pipeline)
- Intent detection (Thai+EN): STATS / SEARCH / GET_FILE / HELP / CHAT / URL_UPLOAD
- RAG chat via existing retriever.py
- Reply-token fallback to push API on expiry
- Push quota tracker (200/mo free tier — log at 80% / 100%)
- Group/room join → polite reply + auto-leave (PDB is 1:1 only)
- Rich Menu image (2500×1686 px, 89 KB) + deploy script
- Profile UI section (connect/disconnect LINE in app.html)
- Admin endpoint GET /api/line/admin/quota

### 📅 Final Timeline

- ✅ Section A: DONE (2 commits)
- ✅ Section C: DONE (1 commit)
- ✅ Phase 0 External Setup: DONE (Browser Worker, ~1.5 hr)
- ✅ LINE Bot D-K: DONE (6 commits, 1 build session)
- **Status:** Code complete + tested → **awaiting User push + fly deploy + Rich Menu deploy + mobile smoke test**

### Reference Documents
- **Plan A+C:** [plans/foundation-v7.6.0.md](../plans/foundation-v7.6.0.md) (Section B marked deferred)
- **Plan D-K:** [plans/line-bot-v8.0.0.md](../plans/line-bot-v8.0.0.md) (main focus)
- **Briefing:** [handoff/supervisor-briefing-line-bot.md](../handoff/supervisor-briefing-line-bot.md)
- **External setup:** [handoff/external-setup-checklist.md](../handoff/external-setup-checklist.md)
- **Executor prompt:** [prompts/prompt-line-bot-browser-ai-executor.md](../prompts/prompt-line-bot-browser-ai-executor.md)

### Phase 0 ✅ DONE (2026-05-04 12:19 ICT)
- Browser Worker (Antigravity) ทำเสร็จใน ~1.5 hr
- 9 Fly secrets deployed (LINE_CHANNEL_*, LINE_LOGIN_*, RESEND_*, EMAIL_*, LINE_BOT_*)
- Bot Basic ID: @402wfbfd
- Webhook URL: https://personaldatabank.fly.dev/webhook/line (configured ใน LINE, ยังไม่ deploy code → 404)
- Resend uses default sender (noreply@resend.dev) — MVP
- ⚠️ Action item: User verify "ข้อความตอบกลับอัตโนมัติ" OFF ใน OA Manager
- ⚠️ Security: rotate tokens หลัง deploy + verify (browser logs exposure risk)
- Report: inbox/for-แดง.md

### Awaiting Action
1. ✅ Phase A committed (8fa3c70 + 698ba0d)
2. ✅ Section C committed (1172d83)
3. ✅ Phase D foundation committed (9834349)
4. ✅ Phase J + E partial committed (0b9257d)
5. ✅ Phase 0 external setup done (Browser Worker)
6. ✅ Phase E full + F committed (a810daa)
7. ✅ Phase G + URL_UPLOAD committed (08008cf + 7b22579)
8. ✅ Phase H + I committed (ba4df60)
9. ✅ Phase K committed (this commit) — APP_VERSION 8.0.0 + final report
10. 🔴 **User action — review + push + deploy:**
    - `git push origin master`
    - `fly deploy` (Fly secrets already set in Phase 0)
    - `python scripts/setup_line_rich_menu.py` (after deploy — registers Rich Menu)
    - Manual mobile smoke test (see for-User.md REVIEW-001)

### Production Deploy Note
Phase A เปลี่ยน plan_limits + email — กระทบ user behavior:
- ก่อน fly deploy ต้อง set Fly secrets: `RESEND_API_KEY`, `EMAIL_FROM_ADDRESS`, `EMAIL_FROM_NAME`
- ก่อน deploy ต้อง check existing users ที่มี > 5 ไฟล์ — อาจต้อง soft-lock (BACKLOG: A4 migration)
- **ห้าม fly deploy** จนกว่า Section C + LINE Bot ครบ + user ตรวจ

**Defer deploy until:** v7.6.0 Section C done + v8.0.0 LINE Bot done = **single combined production deploy**

---

### 🔴 v7.6.0 Foundation — `plan_pending_approval` (2026-05-02) ⭐ ACTIVE PLAN (Phase A-C)

**State:** `plan_pending_approval` — แดงเขียน plan เสร็จ รอ user approve
**Plan file:** [plans/foundation-v7.6.0.md](../plans/foundation-v7.6.0.md)
**Author:** แดง (Daeng) — 2026-05-02
**Priority:** 🔴 Critical — Pre-launch backlog ก่อน public launch
**Estimated effort:** เขียว ~10-13 working days (~2-2.5 weeks) + ฟ้า ~3-4 days
**Foundation:** v7.5.0 (DONE) → v7.6.0 Foundation
**Strategic direction:** Foundation-first per user 2026-05-02 — ไม่เพิ่ม external dependency ใหม่ (ไม่มี LINE/Telegram/Discord), strengthen core ก่อน multi-channel

**Scope (3 sections):**

**Section A — Pre-launch Backlog (Layer 1)**
- BACKLOG-008: Restore `plan_limits.py` production values (Free 5 files / 50MB / 10MB max / 1 pack / no semantic; Starter 50/1024MB/20MB/5 packs/semantic)
- BACKLOG-009: Wire email service (Resend) สำหรับ password reset + drop `reset_token` จาก JSON

**Section B — MCP File Ingestion USP (Layer 2)**
- 🆕 `backend/url_fetcher.py` — SSRF-safe URL fetch (block private IPs + force HTTPS + size cap)
- 🔧 Wire `mcp_tools.upload_text` properly — plan limit + content_hash + BYOS push + auto-organize
- 🆕 `mcp_tools.upload_from_url` — main USP tool (Claude/ChatGPT paste URL → server pull → ingest)
- Refactor `organize_new_files` → pure function ใน organizer.py (กัน circular import)

**Section C — Universal Signed Download URLs (Layer 3)**
- 🆕 `backend/signed_urls.py` — JWT signed tokens (TTL 30 min default, max 1 hour)
- 🆕 `GET /d/{token}` — public endpoint (BYOS-aware via storage_router)
- 🔧 Update `mcp_tools.get_file_link` → use signed_urls

**Architecture decisions (baked-in):**
- No new tables — reuse `users`, `files`, `content_hash`, `drive_file_id` ที่มีอยู่
- No new external dependency platforms (no LINE/TG/Discord ในเฟสนี้)
- httpx async (ไม่ใช่ requests sync) สำหรับ url_fetcher
- MCP error format `{error: {code, message, upgrade?}}` consistent across new tools

**Strategic context (จาก competitor research 2026-05-02):**
- PDB unique 5 USPs: auto-organize + graph + MCP + BYOS + personality
- Foundation-first ลด risk + ไม่ผูก LINE policy + USP delivers value ได้ทันที
- Research artifacts: [competitor-deep-dive.md](../research/competitor-deep-dive.md), [mcp-file-upload-deep-dive.md](../research/mcp-file-upload-deep-dive.md), [chat-bot-platforms-feasibility.md](../research/chat-bot-platforms-feasibility.md)

**Open Questions for user (8 ข้อ — มี default แนะนำทุกข้อ):** ดู plan section "Risks / Open Questions"

**Pending action:** User approve plan + ตอบ Q1-Q8 → state เปลี่ยน `plan_approved` → เขียวเริ่ม build

---

### 🟢 v8.0.0 LINE Bot Integration — `plan_pending_approval` (2026-05-02 reactivated) ⭐ ACTIVE (Phase D-K)

**State:** `plan_pending_approval` (was deferred — reactivated 2026-05-02 per supervisor + executor model)
**Plan file:** [plans/line-bot-v8.0.0.md](../plans/line-bot-v8.0.0.md)
**Bundle with:** v7.6.0 Foundation (must complete Phases A-C first)

**Phases (D-K):**
- Phase D — LINE foundation (webhook + DB + adapters skeleton)
- Phase E — Account linking + welcome flow
- Phase F — File upload flow (PDF/DOCX/image/audio handlers)
- Phase G — Chat / Search / Stats / Get-file
- Phase H — Forward + edge cases + push fallback
- Phase I — Rich Menu deploy
- Phase J — Profile UI integration + admin endpoints
- Phase K — Polish + mobile testing + memory updates

**Critical dependency on v7.6.0:**
- **Signed URLs** (Section C of v7.6.0) — REQUIRED workaround for "LINE bot ส่ง PDF กลับ user ไม่ได้"
- Plan limits enforcement
- Email service for password reset (used in account link flow if user resets password)
- MCP upload pattern (reused in bot upload handlers)

**External setup required (User Phase 0):** ดู [handoff/external-setup-checklist.md](../handoff/external-setup-checklist.md)
- LINE Developer + Provider + 2 channels (Messaging API + Login)
- Resend account (or use default sender)
- Fly.io secrets (8-9 secrets total)

---

### 🟢 v7.5.0 Upload Resilience — DONE ✅ (2026-05-02)

**State:** `done` ✅ — single-agent 3-in-1 mode (แดง→เขียว→ฟ้า) per user authorization
**Plan file:** [plans/upload-resilience-v7.5.0.md](../plans/upload-resilience-v7.5.0.md)
**Owner (build+review):** แดง (full pipeline 3-in-1)
**Foundation:** v7.4.0 master HEAD `b8e8014` → v7.5.0 (4 commits)
**Self-review verdict:** ✅ APPROVE — 50 pytest + 58 backend E2E + 238 regression = **346/346 PASS** + 1 skip (no tesseract local)

### Commits shipped
1. `8e386b8` — Phase 1: Fix Bugs (image OCR / structured skip / UI modal)
2. `b8e8014→Phase4` — Phase 4: Big File map-reduce + DB schema + bump 200MB
3. `7f195c3` — Phase 2: Proactive UX (extraction_status + retry + encrypted detect)
4. `1c5e33e` — Phase 3: More formats (xlsx/pptx/html/json/rtf)
5. (final) — APP_VERSION bump 7.1.5 → 7.5.0 + memory updates

### Test results (4-layer per phase, executed in 3-in-1 session)
| Layer | Coverage | Result |
|-------|---------|--------|
| L1 pytest unit | 51 cases (extraction + chunker + organizer + classify + formats) | 50 PASS / 1 skip |
| L2 backend E2E | scripts/upload_resilience_e2e_verify.py — A 13 + B 13 + C 15 + D 17 | 58/58 PASS |
| L3 Playwright | tests/e2e-ui/v7.5.0-upload-resilience.spec.js (6 tests) | spec ready — sandbox blocks port binding so user/CI runs manually |
| L4 manual smoke | 14 items in plan | documented for user verification |
| Regression | 238 backend (dedupe 55 + byos 5×106 + rebrand 77) | 238/238 PASS |

### What shipped
- **Phase 1:** image OCR (png/jpg/jpeg/webp via pytesseract), structured skip schema `{code, message, suggestion}`, per-file actionable result modal, EMPTY_FILE detect, fix size msg bug
- **Phase 4:** smart text chunker (heading→paragraph→sentence→hard fallback) + map-reduce summary for files > 30K chars, DB columns (extraction_status, chunk_count, is_truncated), bump max_file_size_mb to 200
- **Phase 2:** encrypted PDF detect + classify_extraction_status + reprocess endpoint mode=reextract + extraction badges + retry button (desktop inline + mobile kebab)
- **Phase 3:** xlsx/pptx/html/json/rtf extractors with HTML XSS strip security

### Last update: 2026-05-02 (แดง shipped v7.5.0 in 3-in-1 mode, all 4 phases + final bump)

---

### 🟢 v7.4.0 SaaS Responsive Design & Mobile UX — DONE ✅ (2026-05-02)

**State:** `done` ✅ — implemented + 14 v7.4.0 + 103 frontend regression + 52 backend pytest = **169/169 tests pass**
**Plan file:** [archive/2026-05-02-saas-responsive-v7.4.0.md](../plans/archive/2026-05-02-saas-responsive-v7.4.0.md)
**Owner (build):** เขียว (Khiao) — full dev mode
**Priority:** 🟡 High — Mobile usability + SaaS UX standards 2025
**Foundation:** ต่อยอดจาก v7.3.0 commit `62968c6`

**Note:** User asked for v7.3.0 with 4 sections — **2 ใน 4 sections ทำใน v7.3.0 ไปแล้ว** (sidebar hamburger + form validation .is-invalid + z-index modal>guide). v7.4.0 scope = 2 sections ที่เหลือ + ลึกกว่านี้:

**4 fixes (Section A-D):**
1. **Touch Targets 44px** — bump `.btn`, `.btn-sm`, `.btn-close`, `.form-input` to ≥44×44px on `@media (max-width: 768px)` (Apple HIG / Material Design 3)
2. **Page FAB** — primary actions (organize-new, new-context) become floating round button bottom-right above guide-fab on mobile
3. **File List Card View** — `.file-item` → vertical card on mobile + kebab menu (⋮) replacing inline Delete
4. **Context Memory Kebab** — replace hover-only actions with always-visible kebab dropdown on mobile (3 actions: Edit / Pin / Delete)

**Backend impact:** zero — all frontend (CSS + HTML + render functions). User asked to test backend too — will run `python -m pytest tests/test_production.py` as part of regression to confirm no contract break.

**Last update:** 2026-05-02 (แดงเขียนแผน → เขียวเริ่ม build)

---

### 🟢 v7.3.0 UX Edge-Cases & Mobile Fixes — DONE ✅ (2026-05-02)

**State:** `done` ✅ — implemented + 14 v7.3.0 tests + 89 regression all pass = 103 tests 100%
**Plan file:** [archive/2026-05-02-ux-edgecases-v7.3.0.md](../plans/archive/2026-05-02-ux-edgecases-v7.3.0.md)
**Build:** เขียว (this session) — full dev mode per user override

**3 fixes shipped:**
1. ✅ Mobile Responsive — `.sidebar-toggle` hamburger + slide-out sidebar + backdrop + 92vw modals at ≤768px (auto-close on nav click + ESC)
2. ✅ Form Validation UX — `.is-invalid` red border + box-shadow + auto-focus first empty field in ctx-modal; clears `.is-invalid` on user input
3. ✅ Z-index Hierarchy — modal-overlay 10500 / loading 10800 / toast 11000; all bumped above guide-drawer (10000)

**Tests:** 14 new v7.3.0 + 12 v7.2.0 + 89 regression = 103 tests pass 100% on local
**Visual smoke:** 8 screenshots captured (mobile sidebar open/closed/profile-modal/ctx-create + desktop validation states + modal-above-guide)
**Files changed:** 6 (app.html, app.js, shared.css, styles.css + 2 new test specs)

**Last update:** 2026-05-02 (เขียว implement + verify; ready to commit + push)

---

### 🟢 v7.2.0 UX Critical Hotfixes — DONE ✅ (2026-05-02)

**State:** `done` ✅ — implemented + 12 v7.2.0 tests + 89 regression all pass
**Plan file:** [archive/2026-05-02-ux-hotfixes-v7.2.0.md](../plans/archive/2026-05-02-ux-hotfixes-v7.2.0.md)
**Build:** เขียว (this session) — full dev mode per user override
**Commit:** `de34f8f` feat(ux): v7.2.0 critical UX hotfixes — 5 fixes

**5 fixes shipped:**
1. ✅ Button Loading States — saveProfile + sendMessage disable + spinner
2. ✅ Upload Progress — XHR onprogress + beforeunload guard + double-upload toast
3. ✅ Error Toast — never auto-dismiss + close (X) button + z-index 10000
4. ✅ AI Typing Indicator — chat-typing-status in header + 3-dot bounce + i18n
5. ✅ Modal UX — global ESC + backdrop click (8 modals); confirm-modal Promise contract preserved

**Tests:** 12 new v7.2.0 + 89 regression = 101 tests pass 100% on local
**Files changed:** 7 (app.html, app.js, shared.css, styles.css, thorough-pages.spec.js, + 2 new files)

**Last update:** 2026-05-02 (เขียว implement + commit; ready to push)

---

## 📥 Queued (รอคิว — หลัง v7.2.0 เสร็จ)

### v7.1.5 — Dedupe UX Quick Wins (v2 research-backed — 2026-05-02) ✅ DONE (3-in-1 mode)
**State:** `done` ✅ — implemented + 183/183 regression pass + JS/Python syntax clean (single-agent pipeline per user authorization)
**Owner (build+review):** แดง→เขียว→ฟ้า (single agent, full pipeline 3-in-1)
**Plan file:** [archive/2026-05-02-dedupe-ux-v7.1.5.md](../plans/archive/2026-05-02-dedupe-ux-v7.1.5.md) (v2 — wording ผ่าน UX research)
**Foundation:** patch บน v7.1.0 dedupe (`cd114dd` + `0adcaf1`) + ใช้ toast/modal pattern จาก v7.2.0/v7.3.0
**Actual time:** ~30 min (3-in-1 mode, ไม่มี inter-session reload overhead)
**Self-review verdict:** ✅ APPROVE — 183/183 regression + JS syntax + Python compile + i18n keys (20×2 langs) + functions (8/8) verified

### Scope (2 fixes แก้ pain ใหญ่ที่สุด)
- **P1 → A1:** Per-file action ใน popup — radio per row + 2 quick actions (เก็บทั้งหมด/ข้ามทั้งหมด)
- **P2 → A2:** Undo toast **10 วิ** + ปุ่ม X dismiss (ไม่ใช่ 5s) — Material 3 + WCAG 2.2.1

### Wording ผ่าน UX research (v2)
- **NN/G** [Cancel-vs-Close](https://www.nngroup.com/articles/cancel-vs-close/) + [Confirmation Dialogs](https://www.nngroup.com/articles/confirmation-dialog/)
- **OS standards** — Win11 + macOS Finder ใช้ "Skip" / "Keep both" สำหรับ batch (idiomatic)
- **Material 3 + WCAG 2.2.1** — toast ≥10s + manual dismiss สำหรับ destructive
- **Thai mobile convention** (K+/SCB Easy/LINE) — "เลิกทำ" สำหรับ undo, "ปิด"/"ไว้ทีหลัง" สำหรับ non-destructive close
- **Key changes:** "ข้ามไฟล์ใหม่" (ไม่ใช่ "ลบใหม่"), ปุ่ม close = "ไว้ทีหลัง" (ไม่ใช่ "ยกเลิก"), undo = "เลิกทำ" (ไม่ใช่ "เอาคืน"), confirm = verb+count+object ("ข้ามไฟล์ใหม่ 3 ไฟล์")

### Why frontend-only
- Backend `/api/files/skip-duplicates` รับ `file_ids: list` อยู่แล้ว → per-file selector แค่ส่ง subset
- Undo = client-side setTimeout — ไม่ต้องมี soft-delete table

### Defer (Phase 2.2+)
- Replace action button (preserve cluster/tags) — ซับซ้อน
- Library scan endpoint + duplicate dashboard page
- LLM deep diff
- "ไม่ใช่ duplicate" override (dismissal table)
- MCP `find_duplicates` tool
- Drive sync dedupe

### Timeline
- 2026-05-02 — User ถามว่าระบบรองรับ multi-file upload ไหม → แดงสำรวจ implementation จริง (post-pivot DUP-003)
- 2026-05-02 — User ขอ proactive UX plan → แดงเสนอ 4 phase (~5 วัน)
- 2026-05-02 — User ขอ "ง่ายไม่ซับซ้อน แก้จุดปวดใจหลัก" → แดง strip เหลือ 2 fixes (~3 ชม.)
- 2026-05-02 — User ขอ research wording ที่ดีที่สุด → แดง delegate research → revise plan v2 ตาม NN/G + OS standards + Material 3 + Thai mobile convention
- รอ user approve → เริ่ม build (v7.2.0 done แล้ว ไม่ต้อง queue ต่อ)

---

## ✅ Recently Completed (เรียงจากใหม่ไปเก่า)

### v7.1.0 — Duplicate Detection on Organize-new (2026-05-01)
**State:** `done` ✅ — merged + deployed
**Plan:** [archive/2026-05-01-duplicate-detection.md](../plans/archive/2026-05-01-duplicate-detection.md)
**Build by:** เขียว (round 1 upload + round 2 pivot per DUP-003)
**Review by:** ฟ้า — APPROVE 2026-05-01 (REVIEW-002, 87/87 tests + 106/106 BYOS regression)
**Merged:** master commits `cd114dd` (feat) + `0adcaf1` (pivot) + `c047657` (e2e tests) + `6467b3a` (memory)
**Pivot rationale:** trigger ย้าย upload→organize-new ตาม user override → Risk #9 หาย (intra-batch SEMANTIC ทำงานได้)

### v7.0.0 → v7.0.1 — Google Drive BYOS (2026-05-01)
**State:** `done` ✅ — deployed + 5 follow-up fixes already on master
**Plan:** [archive/2026-05-01-google-drive-byos.md](../plans/archive/2026-05-01-google-drive-byos.md) (post-cleanup ใช้ "Personal Data Bank" ทุกที่)
**Build by:** เขียว Phase 1-3 + ฟ้า Phase 4 + E2E (full dev mode authority)
**Deploy:** Fly.io machine 82 — 2026-05-01 03:04 UTC (commit `84f4f74`)
**Post-deploy fixes (v7.0.1):**
- `73f1a96` feat(byos): wire raw-file Drive push + /api/drive/sync + storage badges
- `e1908b8` fix(byos): fallback to extracted_text when raw file missing on Drive push
- `ac9a6e3` fix(byos): convert filetype ext to MIME type in sync push
- `1449666` fix(byos): convert Drive mimeType to extension on pull import
- `c04d21c` fix(byos): push local files to Drive on sync + update storage_source

### v6.1.0 — PDB Rebrand "Project KEY" → "Personal Data Bank" (2026-04-30 → 2026-05-01)
**State:** `done` ✅ — merged + deployed + follow-up rename to `personaldatabank.fly.dev`
**Plan:** [archive/2026-05-01-rebrand-pdb.md](../plans/archive/2026-05-01-rebrand-pdb.md)
**Build by:** เขียว 5 commits (76/76 smoke pass)
**Review by:** ฟ้า — APPROVE + version drift fix `1b7fd98`
**Merged:** master commits `6e14e63` (feat) + later `d2f92da` (localStorage migration) + `0182c06` (domain rename)
**Note:** original plan locked `project-key.fly.dev` แต่ user later renamed Fly.io app → `personaldatabank.fly.dev` (ee8699d)

### v6.0.0 — Personality Profile (MBTI/Enneagram/Clifton/VIA + History) (2026-04-30)
**State:** `done` ✅ — deployed
**Plan:** [archive/2026-04-30-personality-profile.md](../plans/archive/2026-04-30-personality-profile.md)
**Build by:** เขียว (commit `3f4b4b9`)
**Review by:** ฟ้า — APPROVE (25 API + 10 browser tests)

---

## 📜 Recent Master Commits (post-v7.1.0)

```
cc1ad84 refactor(frontend): split monolith into landing.html + app.html  (2026-05-02 area)
a5ee41d fix(ui): ghost backdrop blocking clicks after file detail close
1449666 fix(byos): convert Drive mimeType to extension on pull import
ac9a6e3 fix(byos): convert filetype ext to MIME type in sync push
e1908b8 fix(byos): fallback to extracted_text when raw file missing on Drive push
c04d21c fix(byos): push local files to Drive on sync + update storage_source
6467b3a docs(memory): fah review APPROVE v7.1.0
0adcaf1 refactor(dedupe): pivot trigger upload→organize-new (DUP-003)
c047657 test(dedupe): add E2E verification script — 54 cases
64c7890 docs(memory): v7.1.0 dedupe plan + handoff
cd114dd feat(dedupe): duplicate detection on upload — v7.1.0
d2f92da chore(rebrand): remove ALL 'project-key' references, rename localStorage keys to pdb_*
0182c06 chore: update ALL references from project-key.fly.dev to personaldatabank.fly.dev
8d6ad31 chore: lock RAM at 1024MB in fly.toml
ee8699d chore: update domains to personaldatabank.fly.dev
```

---

## 🚧 Active Blockers

ไม่มี — ดู [blockers.md](blockers.md)

---

## 📋 Pre-launch Backlog (ดู active-tasks.md)

ก่อน production launch ต้องตามเก็บ 2 รายการสำคัญ:
- **BACKLOG-008** — Restore plan_limits.py production values (ตอนนี้ testing mode 999999 ทุก field)
- **BACKLOG-009** — Wire email service for password reset (ตอนนี้ return reset_token ใน JSON ตรงๆ)

ทั้ง 2 ตัวเป็น "production launch gates" — ไม่ใช่ tech debt, รอ user signal launch

---

## 📊 Pipeline States (อ้างอิง)

| State | ความหมาย | ขั้นตอนต่อไป |
|-------|---------|-------------|
| `idle` | ไม่มีงานใน pipeline | รอ user มอบหมาย → เริ่ม planning |
| `planning` | แดงกำลังวาง plan | รอแดงเสร็จ → user approve |
| `plan_pending_approval` | Plan เสร็จ รอ user approve | User บอก approve/revise |
| `plan_approved` | Plan approved พร้อม build | เขียวเริ่ม build |
| `building` | เขียวกำลังเขียน code | รอเขียวเสร็จ |
| `built_pending_review` | Code เสร็จ รอ ฟ้า review | ฟ้าเริ่ม review |
| `reviewing` | ฟ้ากำลัง review + เขียน tests | รอฟ้าเสร็จ |
| `review_passed` | Review ผ่าน รอ user merge | User merge → done |
| `review_needs_changes` | Review เจอปัญหา ต้องกลับไปเขียว | เขียวแก้ → กลับ review |
| `done` | Merged + deployed | กลับ idle |
| `paused` | Pipeline หยุดชั่วคราว | รอ blocker resolve |

---

## ⚠️ กฎสำคัญ

1. **ห้าม 2 features อยู่ใน pipeline พร้อมกัน** (default — user override ได้เป็น parallel)
2. **State เปลี่ยน → update ที่นี่ทันที** — ห้ามรอ
3. **Agent ที่ไม่ใช่ owner ปัจจุบัน** → อย่าเริ่มทำงาน รอจนกว่าจะถึงรอบตัวเอง
4. **User เป็นคนสั่งให้เริ่ม pipeline ใหม่ (กลับ idle → planning)**
