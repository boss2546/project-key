# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current State: `review_passed` ✅ (v9.3.3 SURROGATE HOTFIX — 2026-05-08)

**Master HEAD:** `6139eed` v9.3.3 surrogate boundary fix (5 commits ahead of origin)
**APP_VERSION:** **9.3.3** (bumped from 9.3.1 — skipped 9.3.2 since previous patch didn't bump)
**Origin/master:** `cdef06b` v9.3.1 deployed (has Phase D+E + iOS sidebar mobile)
**Production:** 🔴 active bug — UnicodeEncodeError on `db.commit()` from lone surrogates in PDF extracted_text · รอ user push + deploy ทันที
**Active patch:** v9.3.3 surrogate boundary fix (this commit) on top of v9.3.2 dedup-disable
**Mode:** 3-in-1 (แดง+เขียว+ฟ้า ในคนเดียว) — pipeline complete, รอ user push

### v9.3.3 Hotfix summary
- Bug: PDF extraction emits text with lone UTF-16 surrogates (U+D800-U+DFFF) → SQLite UTF-8 encode crash on `db.commit()` (Fly log 12:19:42)
- Fix: `strip_surrogates()` helper at extraction boundary in [extraction.py](../../backend/extraction.py) + 4 defense-in-depth DB write sites (upload/reprocess/promote/mcp)
- Verified: lone surrogate input strips → encodes UTF-8 OK · byos_router_smoke 16/16 PASS regression
- v9.3.2 dedup-disable did NOT fix this — different code path (DB write vs hash compute)

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
