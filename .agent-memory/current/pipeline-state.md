# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current State: `review_passed` ✅ v9.3.5 BYOS Reconnect UX FINAL (2026-05-10)

**Master HEAD:** v9.3.5 final (10 commits c99616f → 45285cd · all bugs fixed)
**APP_VERSION:** 9.3.5
**Production:** 🔴 still v9.3.1 — รอ user `flyctl deploy` (combined v9.3.2/3/4/5 deploy)
**Mode:** Sequential (แดง→เขียว→ฟ้า) — pipeline complete after re-review loop

### v9.3.5 verdict timeline
1. **Initial review** (rushed TH-only): APPROVE
2. **User-requested re-review** ("เข้าไปตรวจสอบสิว่าทุกอย่างถูกต้องไหม"): NEEDS_CHANGES
   - 🟡 BUG-V935-01: i18n keys missing (EN users saw Thai)
   - 🟢 BUG-V935-02: reconnect button no double-click guard
3. **เขียว fix loop** (3-in-1 mode per user authorization): commit `45285cd`
   - Added 10 i18n entries (5 keys × TH+EN)
   - Added `if (btn.disabled) return; btn.disabled = true;` guard
4. **ฟ้า final re-test:** ✅ **APPROVE FINAL**
   - EN mode verified live via Playwright: title + detail + reconnect + dismiss + notice → all EN ✅
   - TH ↔ EN ↔ TH toggle works ✅
   - Regression: 42/42 PASS ✅

### Final verdict: ✅ APPROVE
- 0 critical / 0 high / 0 medium / 0 low issues
- All bugs from re-review fixed + verified
- Visual proof: `v9_3_5_en_banner_final.png` (EN mode banner correct)

### Pending user action
1. 🔴 **Decide fly.toml** — revert ลง 2048/2 (recommend) หรือ keep 4096/4
2. 🚀 **Deploy:** `git push origin master` + `flyctl deploy --app personaldatabank`
3. 🟡 **STORAGE-007 long-term:** Submit Google OAuth verification (founder external work)

### v9.3.5 build summary
- Backend: 9 helpers patched (storage_router) + drive_sync wrap + endpoint status field
- Frontend: banner + auto-sync after reconnect + visibility polling + reword testing notice + upload-warning toast
- Cache-bust catch-up: `?v=9.3.1 → ?v=9.3.5` (drift จาก v9.3.2/3/4 ที่ไม่เคย bump)
- Plan ref: [plans/v9.3.5-byos-invalid-grant-coverage.md](../plans/v9.3.5-byos-invalid-grant-coverage.md) (v3 — adjusted to actual code)

### Pending user action
1. 🔴 **Decide fly.toml** — revert ลง 2048/2 (recommend) หรือ keep 4096/4
2. 🚀 **Deploy:** `git push origin master` + `flyctl deploy --app personaldatabank`
3. 🟡 **STORAGE-007 long-term:** Submit Google OAuth verification (founder external work)

**v9.4.0 status:** `plan_pending_approval` — DEFER (user สั่งทำแค่ v9.3.5 ก่อน)
**v9.4.0 plan revised 2026-05-10 (v2 post-audit):** [plans/upload-queue-v9.4.0.md](../plans/upload-queue-v9.4.0.md) ⭐ Detailed Proactive Edition + เขียว field-audit fixes
- v1 → v2: เขียวอ่านโค้ดจริงเทียบ plan แล้วเจอ 11 mismatches (3 BLOCKER + 3 MEDIUM + 5 LOW) → แดง 3-in-1 mode revise
- Fixed: M-1 i18n pattern (I18N.th/.en single global · ไม่ใช่ separate vars) · M-3 WAL mode (added explicit code) · M-4 reprocess+promote refactor (เข้า scope · "ไม่ค้าง" 100%) · M-2 func import · M-9 t(key,vars) extension · M-10 safer SQL via SQLAlchemy ORM
- Total scope: Truthfulness Contract (TC-1..6) + Multi-tenant fairness + Per-plan caps + Observability + 7 ADRs + State Machine + FMEA (25) + Rollback (4-tier) + 83 tests
- Effort v2: เขียว ~25-27 ชม. (+3 hrs) + ฟ้า ~8-9 ชม. (+1 hr) = **~33-36 ชม. (~4 วัน)**
- Open Questions: Q1-Q7 (ดูใน plan file)

### Plan A — v9.3.5 BYOS invalid_grant graceful coverage 🩹 [BUILDING]
- **Plan file:** [plans/v9.3.5-byos-invalid-grant-coverage.md](../plans/v9.3.5-byos-invalid-grant-coverage.md)
- **Effort:** ~2-3 ชม. (เขียว) + ~1.5 ชม. (ฟ้า) = ~4 ชม. รวม
- **Risk:** 🟢 LOW (code-only · ไม่มี migration · pattern reuse จาก v9.3.0)
- **Why urgent:** Live test 2026-05-10 พบว่า bossok2546 user เจอ BYOS uploads silent-fail · UI หลอก "เชื่อมต่อแล้ว" · 8 files ติด local
- **Scope:** Patch 8 helpers ใน storage_router.py (extend v9.3.0 pattern) + wrap drive_sync.load_connection

### Plan B — v9.4.0 Upload Queue + Visible Progress 🚀 [FEATURE]
- **Plan file:** [plans/upload-queue-progress-v9.4.0.md](../plans/upload-queue-progress-v9.4.0.md)
- **Effort:** ~18.5 ชม. (เขียว) + ~6 ชม. (ฟ้า) = ~24.5 ชม. รวม (~3 วัน)
- **Risk:** 🟡 MEDIUM (schema migration + worker module + frontend tray)
- **Scope:** แยก upload เป็น save+queue + UI progress tray + worker recovery

**คำแนะนำ:** Plan A ship ก่อน (urgent bug + low risk + ~4 ชม.) → Plan B ตามมา (feature + larger scope)
**ทั้งสอง plans ไม่ conflict กัน** — Plan A patch except blocks ของ push helpers, Plan B restructure upload flow. Apply ได้แยกกันหรือต่อกัน.

### v9.4.0 Goal (1 paragraph)
แยก upload (เร็ว ≤ 200ms) ออกจาก extract (ช้า — OCR/Gemini) เป็น **DB-backed queue + in-process async worker** + **persistent UI tray** ที่ user เห็นทุกขั้นสด ไม่ค้าง + recoverable หลัง server restart + เก็บ extraction stack v9.3.4 เดิมทั้งหมด

### v9.4.0 Scope (ขอบเขต)
- ✅ Upload phase only — organize/AI queue เก็บไว้รอบหน้า
- ✅ DB schema +6 columns (idempotent ADD-only migration)
- ✅ 4 API endpoints: /api/upload (changed shape) + /api/upload-status (new) + /api/upload/{id}/retry (new) + /api/upload/{id}/dismiss-error (new)
- ✅ 1 backend module ใหม่: `backend/upload_worker.py`
- ✅ Frontend Upload Tray (vanilla, ใช้ atom เดิม + token foundation)
- ✅ Backward compat: existing files / organize-new / Drive push ไม่กระทบ
- ❌ ไม่แตะ extraction.py extract logic (เพิ่มแค่ progress_callback parameter)
- ❌ ไม่ใช้ Redis/Celery/WebSocket
- ❌ ไม่สร้าง atom variant ใหม่

### Files
- 5 backend modify + 1 backend create
- 3 frontend modify
- 3 test create (smoke 30 + Playwright 12 + pytest 15 = 57 cases)
- 5 memory updates

### Effort
- เขียว: ~18.5 hrs (~2.5 วัน)
- ฟ้า: ~6 hrs

### Open Questions ที่รอ user ตัดสินใจ
1. Worker concurrency: 1 (default, sequential) หรือ 2?
2. Tray location: bottom-right (default) — confirmed safe (guide-fab hidden แล้ว)
3. Auto-retry attempts ก่อนต้อง manual: 0 (default) / 1 / 3?
4. Rollout: ทันที (default) หรือ feature flag?

### Pending action
- 🔴 **User**: review plan + answer Q1-Q4 หรือยอมรับ default
- 🟢 **เขียว**: รอ user approve → start Step 1 (DB schema)
- 🔵 **ฟ้า**: รอเขียวเสร็จ → run 57 cases + UI Foundation Contract §6 check

---

## 🟢 Recently Done — v9.3.4 LLM/AI BOUNDARY (2026-05-08)

**Master HEAD:** `043cdc3` v9.3.4 LLM + AI ingest surrogate boundary
**APP_VERSION:** **9.3.4**
**Production:** 🔴 still on v9.3.1 (buggy) until user runs `flyctl deploy` — patches v9.3.2/3/4 stacked + ready
**Active patch:** v9.3.4 (LLM + AI ingest sanitize) on top of v9.3.3 (extract_text + DB write boundaries) on top of v9.3.2 (dedup disable)
**Mode:** 3-in-1 (แดง+เขียว+ฟ้า ในคนเดียว) — pipeline complete, รอ user deploy

### v9.3.4 Boundary summary
- llm.py `_call_openrouter` wraps LLM response with `strip_surrogates` (covers call_llm + call_llm_pro + call_llm_json)
- ai_ingest.py `ingest_via_ai` wraps Gemini audio/video transcription output
- APP_VERSION 9.3.3 → 9.3.4
- byos_router_smoke regression: 16/16 PASS

### Bug origin (already fixed, ready to deploy)
- v9.3.1 production: PDF extraction emits lone UTF-16 surrogates → DB write → UnicodeEncodeError (Fly log 12:19:42)
- v9.3.2: disable duplicate detection (compute_content_hash crash path)
- v9.3.3: strip_surrogates at extract_text boundary + 4 DB write sites
- v9.3.4: extend to LLM + AI ingest output (defense-in-depth upstream)

### Patch v9.3.2 summary
- 🚧 Disabled `compute_content_hash` + `find_duplicate_for_file` + `detect_duplicates_for_batch` (3 public functions in duplicate_detector.py)
- ✅ Bug fix: UnicodeEncodeError surrogate crash → no longer 500 on reprocess
- ✅ Memory: DUP-004 + BACKLOG-009 + conventions disabled-features list
- ✅ Re-enable path documented (single-flag flip + smoke test)

### Self-test (เขียว)
- duplicate_detector.py syntax OK · 3 functions return no-op · lone surrogate handled
- byos_router_smoke: 16/16 PASS · byos_foundation_smoke: 26/26 PASS (regression)

### Patch summary
- ✅ P1 cache-bust HTML → `?v=9.3.0`
- ✅ P2 iOS sidebar — verified shipped (no-op)
- ✅ P3 JWT warn-log on production-like deploy
- ✅ P4 Drive `invalid_grant` graceful + UI re-connect button
- ✅ P5 memory sync + archive shipped plan + resolve inbox

### Review tests
- byos_router_smoke: 16/16 PASS · byos_foundation_smoke: 26/26 PASS
- Python + JS syntax: OK · Cache-bust grep: 21/21 refs at `?v=9.3.0`
- Issues: 0 critical / 0 high / 0 medium / 3 low (Phase 2 optional)

### What this patch does
- P1 cache-bust HTML ทั้งหมด → `?v=9.3.0` (แก้ downgrade ใน working tree)
- P2 iOS sidebar Phase 1+2 ให้จบ (CSS fallback chain + JS `_setVh` IIFE)
- P3 JWT_SECRET_KEY warn-log (production-like deploy)
- P4 Drive `invalid_grant` graceful handling + UI re-connect button
- P5 Memory drift cleanup + archive shipped Share Pack plan + resolve stale inbox

### Audit corrections (verified 2026-05-08)
- ❌ Audit "target = ?v=9.2.2" → actual target = `?v=9.3.0` (APP_VERSION ใน config.py)
- ❌ Audit "JWT random per restart" → actual: persist ใน `.jwt_secret` file (volume) · ปัญหาเฉพาะ multi-machine/migrate
- ❌ Audit "iOS sidebar ทำแล้ว" → actual: Phase 3+landing.css ทำแล้ว · Phase 1+2 ยังไม่ทำ

---

## 🟡 Just Built (v9.3.0 — 2026-05-08)

### v9.3.0 Share Context Pack (Detailed Edition) — BUILT in 3-in-1 mode
- **Plan:** [plans/share-pack-v9.3.0.md](../plans/share-pack-v9.3.0.md)
- **Mode:** 3-in-1 single-agent (แดง→เขียว→ฟ้า) per user authorization
- **Author:** แดง→เขียว→ฟ้า — 2026-05-08
- **Foundation:** master HEAD `127b064` (v9.2.1) → 7 commits (M1-M7)
- **APP_VERSION:** 9.2.2 → 9.3.0
- **Self-review verdict:** ✅ APPROVE — 36/36 v9.3.0 + 47/47 regression = **83/83 PASS**

### Commits shipped (5 logical)
- `7805359` feat(db+api): pack_shares table + pack_share module + token signing [M1-M2]
- `7a4b7b9` feat(api): 5 endpoints + 1 HTML route for Pack Share [M3]
- `08ea830` feat(frontend): sender pack card 📤 button + share bar + auto-copy [M4]
- `4fb628e` feat(frontend): recipient /p/{token} preview page + landing redirect [M5+M6]
- `9fa78f8` test(share-pack): comprehensive 36 cases (26 smoke + 10 Playwright) [M7]
- (pending) chore: bump APP_VERSION 9.3.0 + memory updates

### What shipped
**Backend (4 modified + 1 new):**
- `backend/database.py` — PackShare table + indexes
- `backend/pack_share.py` (NEW, ~360 lines) — token sign/verify + 6 ops + cascade-safe atomic claim
- `backend/plan_limits.py` — pack_share_limit_monthly + check helper + anti-abuse counter
- `backend/main.py` — 3 Pydantic models + 5 endpoints + /p/{token} HTML route
- `backend/config.py` — APP_VERSION 9.3.0

**Frontend (4 modified + 3 new):**
- `legacy-frontend/app.html` — version label v9.2.2 → v9.3.0 + ?v= bump
- `legacy-frontend/app.js` — sender pack card 📤 + bar + 6 functions + clipboard
- `legacy-frontend/styles.css` — .pack-share-bar (~70 lines)
- `legacy-frontend/landing.js` — ?return=/p/... handler (post-login redirect)
- `legacy-frontend/shared_pack.html` (NEW) — 4 view states standalone page
- `legacy-frontend/shared_pack.js` (NEW) — preview load + claim flow + auto-claim
- `legacy-frontend/shared_pack.css` (NEW) — responsive design + sticky CTA

**Tests (2 new):**
- `scripts/share_pack_smoke.py` (NEW, 26 cases) — backend smoke
- `tests/e2e-ui/v9.3.0-share-pack.spec.js` (NEW, 10 cases) — Playwright real Chromium

### Test Results (83/83 PASS)
- ✅ 26/26 v9.3.0 backend smoke (M1 schema/token + M2 endpoints + M3 preview/claim + M4 HTML route)
- ✅ 10/10 v9.3.0 Playwright UI (sender DOM + recipient page + E2E redirect)
- ✅ 21/21 v9.0.1 correctness regression
- ✅ 26/26 v9.2.0 AI Builder regression
- ✅ Python syntax 5 files / JS syntax 3 files — clean

### Privacy + cascade guards verified
- ✅ Cloned pack: source_file_ids ≠ owner's (privacy — recipient ไม่ access ไฟล์ owner ตรงๆ)
- ✅ Cross-user revoke: User B ไม่สามารถ revoke share ของ User A → 404 (steal guard)
- ✅ Owner email masked: te****@x.com pattern verified
- ✅ JWT scope=pack_share: payload ไม่มี 'sub' → กัน abuse as login token
- ✅ Atomic view_count: 6 sequential visits → count=6 (no race)
- ✅ File copy on claim: pre-check + atomic + rollback on partial fail (per Risk #1)

### Awaiting User Action
1. 🔴 **Manual smoke test ใน browser** — sender flow + recipient page on real device
2. 🟢 **Push + deploy** — `git push origin master` + `fly deploy` (รวม v9.2.2 + v9.3.0)
3. 🟡 (optional) Frontend integration smoke ที่ต้องมี real organized pack (Playwright limited to DOM contract — full E2E needs LLM-organized pack which requires OpenRouter)

---

## 🟢 Recently Merged (v9.2.2)
- **v9.2.2 — iOS Sidebar Footer Fix (2026-05-08)**
    - **Status:** DONE (Implementation complete, verification tests created)
    - **Fixes:** 100vh bug on iOS Safari, Footer visibility.
    - **Files:** `backend/config.py`, `app.js`, `app.html`, `styles.css`, `shared.css`, `landing.css`.

## 🔴 Previously pending (now BUILT — see above)

### v9.3.0 Share Context Pack (Detailed Edition with milestone verification) — `built_pending_review` (revised 2026-05-08)
- **Plan:** [plans/share-pack-v9.3.0.md](../plans/share-pack-v9.3.0.md)
- **Effort:** เขียว ~2.5 วัน + ฟ้า ~1 วัน
- **Design (per user "ละเอียดจริงๆ มี milestone test ทุกอย่าง UI จริงทั้ง sender + recipient"):**
  - **Sender:** กด 📤 = ลิงก์ copy ทันที + bar เล็ก (toggle "+ แนบไฟล์" / revoke)
  - **Recipient:** เปิด /p/{token} = preview ทันที (no login) → "เก็บ" → register/login → clone เข้า workspace
  - **Cloned pack:** อิสระ (source_file_ids=[] privacy preserved)
  - **No TTL · No email whitelist · No permission tier · clone-only**
- **Schema:** 1 ตาราง `pack_shares`
- **API:** 5 endpoints + 1 HTML page
- **Plan limits:** Free 5/เดือน, Starter 50, Admin unlimited (revoked counts to anti-abuse)
- **7 Milestones:** M1 schema/token · M2 share endpoints · M3 preview/claim · M4 sender UI · M5 recipient UI · M6 integration · M7 polish
- **Tests:** 25 smoke + 35 pytest + **34 Playwright** (12 sender + 14 recipient + 8 integration) = **94 cases total**
- **Per-milestone Playwright verification** ทุก milestone มี real Chromium UI test
- **Privacy:** locked-pack guard, masked owner email (te****@x.com), revocable, source_file_ids=[] clone

**Pending action:** User approve → state `plan_approved` → เขียว build (Milestone-by-Milestone)

---

## 📜 History / Recent Pipeline Actions

### 🟢 v9.2.2 — iOS Sidebar Footer Fix (2026-05-08)
- **Goal:** Fix sidebar footer hidden behind iOS Safari toolbar.
- **Strategy:** Hybrid 3-layer fix (dvh + --vh setter + safe-area padding).
- **Implementation:** Added IIFE to app.js, updated CSS fallback chains, bumped version to 9.2.2.

### 🟢 v9.2.1 — Parallel Upload & Mobile Toast Fix (2026-05-07)
- **Status:** DONE & DEPLOYED
- **Fixes:** Parallel extraction speedup + mobile toast overlap fix.
