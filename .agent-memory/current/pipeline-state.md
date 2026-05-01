# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current Features (PARALLEL MODE — per user instruction 2026-04-30)

> **Pipeline override:** User สั่งให้ทำ 2 features parallel — ฟ้าทำ v6.1.0 review/test/fix/commit/push, เขียวเริ่ม v7.0.0 BYOS foundation. Default rule "1 feature at a time" suspended for this round.

### 🔵 v6.1.0 Rebrand — owned by ฟ้า
**State:** `review_passed` ✅ — ฟ้า reviewed + fixed version drift + APPROVED (2026-04-30)
**Branch:** `rebrand-pdb-v6.1.0` (5 commits by เขียว + 1 fix by ฟ้า = 6 total)
**Authority:** ฟ้า may fix small UI bugs herself + commit + push (per user override)
**Verdict:** ✅ APPROVE — ready for user to merge to master + deploy

### 🟢 v7.0.0 Google Drive BYOS — handed off to ฟ้า (2026-04-30, per user)
**State:** `phase_4_ui_complete` ✅ — Phase 4.1 (Frontend UI) + 4.3 (Drive wiring) DONE by ฟ้า (2026-04-30); 182/182 tests PASS; Visual E2E OK
**Owner:** ฟ้า (Fah) — full dev mode (per user override "ส่งต่อให้ฟ้าทำเลย dev เองต่อด้วย")
**Authority:** ฟ้า may dev + commit + push (no review-back-to-เขียว required for routine work)
**Handoff MSG:** ดู MSG-006 ใน [inbox/for-ฟ้า.md](../communication/inbox/for-ฟ้า.md) ⭐
**Owner:** เขียว (Khiao)
**Plan file:** [plans/google-drive-byos.md](../plans/google-drive-byos.md) (still uses "Project KEY" branding — แดง will revise; new code uses "Personal Data Bank" already)
**Branch:** `byos-v7.0.0-foundation` (4 BYOS commits, ready for end-to-end live test)

**✅ Credentials integrated 2026-04-30:**
- ฟ้า GCP setup ผ่านครบ 6 steps (Project / APIs / OAuth Consent / Client ID / API Key / Project Number)
- 4 credentials + DRIVE_TOKEN_ENCRYPTION_KEY (เขียว generate) → ใส่ใน `.env` (gitignored)
- `is_byos_configured() == True` verified
- 5 BYOS endpoints unlocked from 503
- `/api/drive/oauth/init` produces valid 541-char Google auth URL (drive.file scope + CSRF + offline + consent ครบ)

**✅ Build summary (Phase 1 + Phase 2):**
- 4 backend modules: drive_layout, drive_oauth, drive_storage, drive_sync (~900 lines)
- 5 endpoints: drive/status, oauth/init, oauth/callback, disconnect, storage-mode
- Schema migration: users.storage_mode + drive_connections + files.drive_*
- 4 mock smoke tests = 90/90 PASS (foundation 26 + storage 20 + sync 24 + oauth 20)
- docs/BYOS_SETUP.md admin guide (270 lines)
- .env.example BYOS section + safety notes

**✅ Phase 3 done (2026-04-30 by เขียว, commit a1c8f72):**
- backend/storage_router.py — 9 best-effort helpers
- profile.py wired (push profile.json to Drive after DB commit)
- OAuth callback wired (auto-flip storage_mode + init folder layout)
- byos_router_smoke.py 16/16 PASS

**🚨 Security note (2026-04-30, fixed in 58e8b9d):**
- เขียว committed actual encryption key in docs/BYOS_SETUP.md (3 occurrences) → leaked at commit d75d5ea
- Fixed forward: replaced with placeholder + rotated .env to new key
- Old key still in git history at d75d5ea — **inert** (no DB row uses it)
- Branch NOT pushed yet → ฟ้า decide before first push:
  (a) leave history (no real damage), or
  (b) rebase d75d5ea to amend (clean history, force-push required)

**Pending (BYOS feature activation — sandbox blocks secret writes):**
- Set 6 Fly.io secrets (user runs `flyctl secrets set` in own terminal — script ready)
- After secrets set → Fly auto-restarts → BYOS endpoints transition from 503 → 200
- Live OAuth click-through E2E (browser-based, by user/ฟ้า)

**Already done in this session:**
- ✅ Phase 1+2+3 backend (เขียว, mock-tested 90/90)
- ✅ Phase 4 frontend (ฟ้า, commit `5b80c52`)
- ✅ PKCE + logout debounce + UX (ฟ้า WIP committed by เขียว, `fb515db`)
- ✅ 182/182 regression PASS (3 times this session)
- ✅ Branch pushed to GitHub (origin/byos-v7.0.0-foundation = fb515db)
- ✅ Memory updates (12 files refreshed)

**Known issues (flagged):**
- Encryption key in `d75d5ea` history — already on remote (was pushed by ฟ้า earlier). Old key inert (rotated). Rebase + force-push possible if user wants clean history.
- Plan revision by แดง (37 brand occurrences in plan file) — non-blocking, can run parallel

**Blockers waiting on แดง (non-blocking):**
- Plan revision (37 occurrences "Project KEY" → "Personal Data Bank")
- 4 open questions: Q-A webhook, Q-B existing folder merge, Q-C drive full Phase 2, Q-D OneDrive/Dropbox

### Original v6.1.0 metadata (kept for reference)
**Owner (build):** เขียว (Khiao)
**Started:** 2026-04-30
**Started:** 2026-04-30
**Plan file:** [plans/rebrand-pdb.md](../plans/rebrand-pdb.md)
**Readiness notes:** [plans/rebrand-pdb-readiness-notes.md](../plans/rebrand-pdb-readiness-notes.md)
**Build branch:** `rebrand-pdb-v6.1.0`
**Handoff MSG:** ดู MSG-004 ใน [inbox/for-ฟ้า.md](../communication/inbox/for-ฟ้า.md) ⭐

### Timeline
- 2026-04-30 — User เห็น plan BYOS ใช้ "Project KEY" ทุกที่ → ขอ rebrand ก่อนเพื่อกันต้องตามแก้ทีหลัง
- 2026-04-30 — แดงสำรวจ scope: 256 occurrences ใน 50 files
- 2026-04-30 — Lock 7 decisions (defaults):
  - Q1: Display "Personal Data Bank" + Code/short "PDB"
  - Q2: Keep `project-key.fly.dev` (Fly.io app name constraint)
  - Q3: Keep `projectkey.db` filename (internal, no user impact)
  - Q4: MCP `serverInfo.name = "personal-data-bank"`
  - Q5: Keep repo name (defer)
  - Q6: UI ไทย = "ธนาคารข้อมูลส่วนตัว", Code/EN = "Personal Data Bank"
  - Q7: Keep current logo
- 2026-04-30 — แดงเขียน plan rebrand ครบ + handoff MSG-003 → เขียว
- 2026-04-30 — User approve plan → state: `plan_approved` → รอเขียวเริ่ม build
- 2026-04-30 — เขียวอ่าน plan + ทุกไฟล์ที่เกี่ยวข้องทีละบรรทัด → grep 343 hits ใน 52 files → เจอ ~56 actual changes (~141 KEEP) → **เจอ 6 จุดที่ plan ไม่ครอบคลุม** (email domain, MCP template key, projectkey_lang, fixtures, test BASE URL, branch strategy) → เขียนสรุปลง [readiness notes](../plans/rebrand-pdb-readiness-notes.md)
- 2026-04-30 — User บอกว่ามีงานอื่นแทรก → state: `paused` รอ resume
- 2026-04-30 — User กลับมาตอบ 3 คำถาม:
  - **Q1 (email):** ไม่ได้เป็นเจ้าของ projectkey.dev → CHANGE 6 mailto → `axis.solutions.team@gmail.com` (สำคัญทางธุรกิจ — email เก่าตายมานานแล้ว!)
  - **Q2 (MCP template):** CHANGE → `personal-data-bank` (consistency กับ serverInfo.name)
  - **Q6 (uncommitted):** Option ก — chore commit `.agent-memory/` + leftovers บน master ก่อน → branch ใหม่สะอาด
  - Q3/Q4/Q5 ใช้ default — ไม่ต้องตอบ
- 2026-04-30 — แดงส่ง MSG-004 → state: `plan_approved` → เขียว resume ได้ทันที (~67 actual changes รวม Q1+Q2 — time budget ยังคง 3 ชม.)
- 2026-04-30 — เขียว resume → chore commit `89d1b44` บน master (commit `.agent-memory/` + scripts + tests/test_personality_review.py) → branch ใหม่ `rebrand-pdb-v6.1.0` จาก master สะอาด
- 2026-04-30 — เขียวลุย Plan Step 1-10:
  - Step 1: grep snapshot baseline = 201 hits ใน 38 files
  - Step 2: Backend rebrand 13 จุด ใน 8 ไฟล์ + APP_VERSION 6.0.0 → 6.1.0
  - Step 3: Frontend rebrand index.html (9 edits) + pricing.html (6 edits) + app.js (10 edits incl. 4 MCP template + 3 i18n + 1 docstring + 2 instruction text) → 0 hits remain
  - Step 4: Config (package.json name + version + description, .env.example header)
  - Step 5: Tests (test_production.py 3, ui.spec.js 4, test_full_e2e.py 1) → 0 hits remain
  - Step 6: Docs (README.md 8 incl. MCP templates, USER_GUIDE_V3.md 3)
  - Step 7: Memory (project/overview.md 2 changes — drop "Project KEY" name + version 5.9.3 → 6.1.0)
  - Step 8: New `maybeShowRebrandNotice()` ใน app.js + flag `pdb_rebrand_notice_seen`
  - Step 9: Verify — grep 201→159 (เหลือเฉพาะ historical PRDs + plan files + intentional release notes) + Python compileall OK + JS syntax OK + TestClient GET / contains "Personal Data Bank" + zero "Project KEY"
- 2026-04-30 — เขียว build เสร็จ → commit `6e14e63` (21 files, +210/-71) → state: `built_pending_review` → ส่ง MSG-004 ใน inbox/for-ฟ้า.md
- 2026-04-30 — เขียวเทสเบื้องต้น (in-process TestClient — sandbox blocked port binding):
  - 21/21 smoke tests pass (frontend rendering 5 + app metadata 2 + module imports 1 + auth/MCP e2e 4 + KEEP invariants 9)
  - **MCP /initialize end-to-end verified:** serverInfo.name='personal-data-bank' + version='6.1.0' ✅
  - Caught 1 issue: served app.js เคยมี literal "Project KEY" ใน WHY comment → fix `312658e` (1 file, +1/-1)
- 2026-04-30 — รอ user สั่งให้เปิดฟ้า review

### Notes
- Time budget เดิม: ~3 ชม. (1/3 วัน) — งาน mechanical
- 7 ที่ที่ "ห้ามแตะ": fly.toml, projectkey.db, localStorage keys, MCP secret URL path, domain, historical PRDs, user-generated content
- Critical regression: login flow, MCP existing user, Stripe webhook, AI chat, file upload
- หลัง rebrand merge เสร็จ → แดงจะ revise plan `google-drive-byos.md` (37 occ) ให้ใช้ "Personal Data Bank" → ถ้า user อยากเริ่ม BYOS หลังจากนั้นได้เลย

### 🔄 Resume Steps (เมื่อ user พร้อมกลับมาทำต่อ)
1. อ่าน [rebrand-pdb-readiness-notes.md](../plans/rebrand-pdb-readiness-notes.md) — sections "TL;DR", "6 Decision Points", "Resume Protocol"
2. User ตอบ 6 ข้อ (หรือ confirm "ใช้ default ทั้งหมด")
3. Update state: `paused` → `building`
4. ทำตาม Plan Step 1-10 (ตาม resume protocol ใน notes)

---

## 📋 Up Next (Queue)

### v7.0.0 — Google Drive BYOS (Bring Your Own Storage)
**State:** `plan_pending_approval` (rebrand finishes first)
**Plan file:** [plans/google-drive-byos.md](../plans/google-drive-byos.md)
**ETA:** ~1 สัปดาห์ dev (หลัง rebrand) — Testing Mode skip Google verification
**Branding หลัง rebrand:** ต้อง update plan ก่อน (37 occ)

### Timeline
- 2026-04-30 — User ปรึกษาเรื่องใช้ Google Drive 5TB Pro เป็น storage
- 2026-04-30 — แดงเสนอ 3 Options (Drive ส่วนตัวบริษัท / R2 / ลูกค้าใช้ Drive ของตัวเอง) → user เลือก Option C
- 2026-04-30 — เปรียบเทียบ Full Drive (A) vs Hybrid (B) → user เลือก B หลังเห็น 8-มิติ analysis
- 2026-04-30 — Lock 4 critical decisions:
  - **Q1:** Coexist 2 modes (Managed + BYOS) — ไม่บังคับใคร
  - **Q2:** `drive.file` scope + Google Picker (drive เต็มไว้ Phase 2 — verification + $25K-85K/yr CASA)
  - **Q3:** Transparent JSON ใน Drive (ไม่ encrypt — trust + debug ง่าย)
  - **Q4:** 2-way sync (upload UI หรือ Drive ก็ได้ ทั้ง 2 ทาง)
- 2026-04-30 — แดงเขียน plan ครบ → state: plan_pending_approval
- 2026-04-30 v2 — User ตัดสินใจ skip Google verification สำหรับ MVP:
  - เหตุผล: ยังไม่ขายจริง ทดสอบภายในกับคนรู้จัก
  - **Strategy: Testing Mode** (ไม่ใช่ Production-Unverified)
    - ✅ ไม่มี warning, UX สะอาด
    - ✅ ไม่ต้อง privacy policy URL / domain verification / demo video
    - ⚠️ Refresh token หมดอายุ 7 วัน (acceptable สำหรับ beta users)
    - ⚠️ Cap 100 test users (ระบุ email ใส่)
  - **Verification submit ทีหลัง** เมื่อพร้อม public launch
  - **MVP timeline ใหม่: 1 สัปดาห์!** (จากเดิม 5-6 wk)

### Notes
- 2 features จะ coexist กับ Personality Profile (เพิ่งเสร็จ v6.0.0) — ไม่กระทบกัน
- BYOS เป็น feature ขนาดใหญ่: dev 3-4 weeks + OAuth verification 2-4 weeks (parallel)
- **OAuth verification ต้องเริ่ม submit ทันที** — ก่อน build เสร็จ — เพื่อไม่ให้ block launch
- Cap 100 users ตอน "Unverified" → ทำ closed beta ได้
- Open Questions ใน plan: 4 (Q-A real-time webhook, Q-B existing folder merge, Q-C drive full Phase 2, Q-D OneDrive/Dropbox)
- Differentiator vs Claude/ChatGPT: "Your data stays in YOUR Drive — verifiable"
- หลัง BYOS launch → market position เป็น PDPA-first / user-sovereign

---

## 📜 History (Completed Features)

### v6.0.0 — Personality Profile (MBTI / Enneagram / CliftonStrengths / VIA) + History
**State:** `done` (deployed 2026-04-30)
**Plan:** [plans/personality-profile.md](../plans/personality-profile.md)

**Feature:** Personality Profile (MBTI / Enneagram / CliftonStrengths / VIA Strengths) + History
**Status:** ✅ deployed live as v6.0.0
**Started:** 2026-04-29 / Completed: 2026-04-30

### Timeline
- 2026-04-29 — User บอก feature → แดงเริ่ม research + plan
- 2026-04-29 — Research personality systems (4 ระบบ) ด้วย general-purpose agent
- 2026-04-29 — แดงเขียน plan ครบ → state: plan_pending_approval (มี 6 open questions)
- 2026-04-30 — User ตอบ Q1-Q6 → แดง revise plan:
  - **Q1: Drop VIA** → MVP เหลือ 3 ระบบ (MBTI + Enneagram + CliftonStrengths)
  - **Q3: เพิ่ม History feature** → table `personality_history` + endpoint + UI history modal
  - Q2/Q4/Q5/Q6 ไม่กระทบ scope
- 2026-04-30 — Plan revision เสร็จ → user approve ✅
- 2026-04-30 — แดงส่ง handoff message MSG-001 ใน inbox/for-เขียว.md → state: `plan_approved` → ส่งต่อให้เขียว
- 2026-04-30 — เขียวเริ่มทำงาน: เจอ conflict ระหว่าง plan file (v1) กับ MSG-001 (v2) → halt → ขอ resolution
- 2026-04-30 — User delegate decision ให้แดง → แดงตัดสินใจ **FINAL v3 = 4 ระบบ (MBTI+Enneagram+Clifton+VIA) + History** (รวม v1's 4 systems + v2's history feature)
- 2026-04-30 — แดง re-write plan file ให้ตรง v3 + ส่ง MSG-002 ปลด blocker เขียว
- 2026-04-30 — เขียวอ่าน MSG-002 + plan v3 ครบ → ย้าย MSG-001/002 → Read → state: `building` → เริ่ม Step 1
- 2026-04-30 — เขียว build เสร็จ Step 1-7 + self-test 19/19 pass → state: `built_pending_review` → ส่งต่อฟ้าผ่าน MSG-003
- 2026-04-30 — ฟ้า review code 8 files / 1,642 lines → API tests 25/25 pass + browser UI test 10/10 pass → state: `review_passed` ✅
- 2026-04-30 — User polish 3 commits (UI emoji + dropdown bg) + เขียว housekeeping commit
- 2026-04-30 — Bump version → `v6.0.0` (commit `3f4b4b9`) → push 18 commits ขึ้น GitHub master
- 2026-04-30 — Deploy ขึ้น Fly.io production (https://project-key.fly.dev/) → smoke test ผ่าน: HTTP 200, /api/personality/reference 16/34/24 ครบ, Swagger reports v6.0.0 → state: `done`

### Notes
- Open Questions ใน plan = 0 (ตอบครบแล้ว ✅)
- **FINAL scope = 4 ระบบ + history**:
  - MBTI (16 types — 16personalities ฟรี / mbtionline เสียเงิน)
  - Enneagram (9 types + wing — Truity/Eclectic ฟรี / RHETI เสียเงิน)
  - CliftonStrengths (Top 5 จาก 34 themes — Gallup เสียเงินเท่านั้น, ไม่มีฟรี)
  - **VIA Character Strengths** (Top 5 จาก 24 strengths — viacharacter.org ฟรี official)
- Trademark constraint สำคัญ: ห้าม copy MBTI/CliftonStrengths descriptions ลง UI/LLM. Enneagram/VIA OK paraphrase
- Migration safe: additive only — เพิ่ม 5 columns ใน user_profiles + table personality_history
- MCP `get_profile` คืนทุกอย่างพร้อมกันในการเรียกครั้งเดียว: 4 ระบบ + summary + active_contexts

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

## 📋 รูปแบบ entry (เมื่อมี feature ใหม่)

```markdown
**Feature:** Export ข้อมูลเป็น JSON
**State:** `building`
**Owner:** เขียว (Khiao)
**Started:** 2026-04-29 14:00
**Plan file:** plans/export-json.md

### Timeline
- 2026-04-29 14:00 — User บอก feature → state: planning
- 2026-04-29 14:30 — แดง plan เสร็จ → state: plan_pending_approval
- 2026-04-29 14:35 — User approve → state: plan_approved
- 2026-04-29 14:40 — เขียวเริ่ม build → state: building

### Notes
[ข้อความที่ agent ฝากไว้ระหว่างทำงาน]
```

---

## 📜 History (10 features ล่าสุด)

_ยังไม่มี — โปรเจกต์เพิ่งใช้ pipeline system_

---

## ⚠️ กฎสำคัญ

1. **ห้าม 2 features อยู่ใน pipeline พร้อมกัน** — ทำทีละ feature
2. **State เปลี่ยน → update ที่นี่ทันที** — ห้ามรอ
3. **Agent ที่ไม่ใช่ owner ปัจจุบัน** → อย่าเริ่มทำงาน รอจนกว่าจะถึงรอบตัวเอง
4. **User เป็นคนสั่งให้เริ่ม pipeline ใหม่ (กลับ idle → planning)**
