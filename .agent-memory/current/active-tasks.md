# 🎯 Active Tasks

> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview
> Pipeline ตอนนี้ = `done` (v8.1.0 Google Sign-In ship + push origin/master แล้ว — รอ user fly deploy)

---

## 🔄 Current Pipeline

**State:** `done` ✅ — v8.1.0 Google Sign-In shipped + pushed to origin/master 2026-05-04 (3-in-1 mode by เขียว)

**Recent shipped (master commits):**
- v8.1.0 (2026-05-04) — Google Sign-In + token fragment redirect + USE_GOOGLE_LOGIN UX (6 commits incl. clock-skew fix, 16/16 self-test)
- v8.0.0 → v8.0.7 (2026-05-04) — LINE Bot Integration ครบ Phase D-K
- v7.5.0 (2026-05-02) — Upload Resilience (4 phase, 346/346 tests)

**Master HEAD:** `f8d25e7` (= origin/master, working tree clean)

**Awaiting User (cannot be done by agents):**
- 🚀 `fly deploy` — push v8.0.0 LINE + v8.0.1-7 + v8.1.0 Google รวมกันขึ้น production
- 🔴 Google Cloud Console: เพิ่ม 2 redirect URIs สำหรับ login flow (5 นาที)
- 📱 LINE Rich Menu deploy: `fly ssh console -C "python scripts/setup_line_rich_menu.py"` (one-time, post-deploy)
- 🧪 Manual smoke test: real Google account + real LINE app
- 🔁 Token rotation (LINE Channel Access Token + Resend API key) — Browser Worker noted log exposure
- 📝 Submit OAuth verification ก่อน public >100 users (1-3 วัน, free)

---

## 🚨 Pre-Launch Backlog

### ✅ DONE (shipped on master, ก่อน public launch ใช้งานได้แล้ว)

- [x] **[BACKLOG-008] ✅ Restore plan_limits.py production values** — shipped commit `8fa3c70` (v7.6.0 Phase A1)
  - **⚠️ Evolved:** v8.0.2 commit `1c8d139` ×10 จาก baseline สำหรับ "testing period"
  - Current values: Free 50 files / 500MB / 100MB max ; Starter 500 files / 10GB / 200MB max
  - Original baseline: Free 5/50MB/10MB ; Starter 50/1024MB/20MB
  - **Pre-public-launch decision:** revert ×10 → original baseline หรือคงไว้ (พ่วง pricing strategy)
  - File: [backend/plan_limits.py:15-60](../../backend/plan_limits.py#L15-L60)

- [x] **[BACKLOG-009] ✅ Wire email service for password reset** — shipped commit `698ba0d` (v7.6.0 Phase A2)
  - `backend/email_service.py` — Resend integration + bilingual TH/EN HTML+text templates
  - `backend/auth.py:296-299` — fire-and-forget `asyncio.create_task(send_password_reset_email(...))`
  - Response no longer includes `reset_token` (anti-enumeration preserved)
  - Resend account: axis.solutions.team@gmail.com, sender = noreply@resend.dev (MVP default)

---

## 🚀 Pending Production Deploy

**Master HEAD:** `f8d25e7` v8.1.0 Google Sign-In (= origin/master)
**Production (Fly.io):** unknown — last confirmed v7.1.0 (pre-deploy gap)
**Gap:** ~80+ commits across v7.2.0 → v7.5.0 → v7.6.0 → v8.0.0-7 → v8.1.0

ทำเสร็จบน master + pushed แต่ user ยังไม่ deploy — รอ `flyctl deploy -a personaldatabank`

---

## 📋 Long-term Backlog (deferred ตามเดิม)

- [ ] [BACKLOG-001] BYOS multi-account (personal + work Drive per user)
  - Priority: 🟢 Low (Phase 2 of BYOS roadmap)
  - Estimated effort: M
- [ ] [BACKLOG-002] Real-time sync via Drive Push Notifications webhook
  - Priority: 🟢 Low (currently using poll-based 5-min sync)
  - Estimated effort: M
- [ ] [BACKLOG-003] Full `drive` scope (CASA verification $25K-85K/yr)
  - Priority: 🟢 Low (defer to revenue threshold)
  - Estimated effort: L (incl. verification submission)
- [ ] [BACKLOG-004] BYOS for OneDrive / Dropbox / iCloud
  - Priority: 🟢 Low (Phase 3+)
  - Estimated effort: L per provider
- [ ] [BACKLOG-005] Custom domain (replace `personaldatabank.fly.dev`)
  - Priority: 🟢 Low (deferred)
  - Estimated effort: S (DNS) + M (rotate URL refs)
- [ ] [BACKLOG-006] OAuth verification submission for Google production mode
  - Priority: 🟡 Medium (unblock public launch — pairs with BACKLOG-008/009)
  - Estimated effort: M (Privacy Policy + Demo video + scope justification)
- [ ] [BACKLOG-007] Frontend migration to React/Vue
  - Priority: 🟢 Low (per FE-001 decision — defer)
  - Estimated effort: L

---

## ✅ Completed Features (เรียงจากใหม่ไปเก่า)

- [x] **v7.5.0 — Upload Resilience** (2026-05-02)
  - Plan: [plans/upload-resilience-v7.5.0.md](../plans/upload-resilience-v7.5.0.md)
  - 4 phases (1+4+2+3): image OCR / big-file map-reduce / extraction_status+retry / xlsx-pptx-html-json-rtf
  - 3-in-1 single-agent mode (per user authorization)
  - Tests: 50 pytest + 58 backend E2E + 238 regression = 346/346 PASS (1 skip = no tesseract local)
  - Commits: `8e386b8` (P1) + `9f2a3xx` (P4) + `7f195c3` (P2) + `1c5e33e` (P3) + (final bump)

- [x] **v7.4.0 — SaaS Responsive Design & Mobile UX** (2026-05-02)
  - Plan: [archive/2026-05-02-saas-responsive-v7.4.0.md](../plans/archive/2026-05-02-saas-responsive-v7.4.0.md)
  - 4 fixes: Touch Targets 44px / Page FAB / File List Card View / Context Memory Kebab
  - Tests: 14 v7.4.0 + 103 frontend regression + 52 backend pytest = 169/169 PASS
  - Commit: `b8e8014`

- [x] **v7.3.0 — UX Edge-Cases & Mobile Fixes** (2026-05-02)
  - Plan: [archive/2026-05-02-ux-edgecases-v7.3.0.md](../plans/archive/2026-05-02-ux-edgecases-v7.3.0.md)
  - 3 fixes: Mobile Responsive (sidebar) / Form Validation / Z-index Hierarchy
  - Tests: 14 v7.3.0 + 89 regression = 103 PASS
  - Commit: `62968c6`

- [x] **v7.2.0 — UX Critical Hotfixes** (2026-05-02)
  - Plan: [archive/2026-05-02-ux-hotfixes-v7.2.0.md](../plans/archive/2026-05-02-ux-hotfixes-v7.2.0.md)
  - 5 fixes: Button Loading / Upload Progress / Error Toast / AI Typing / Modal UX
  - Tests: 12 v7.2.0 + 89 regression = 101 PASS
  - Commit: `de34f8f`

- [x] **v7.1.5 — Dedupe UX Quick Wins** (2026-05-02)
  - Plan: [archive/2026-05-02-dedupe-ux-v7.1.5.md](../plans/archive/2026-05-02-dedupe-ux-v7.1.5.md)
  - 2 fixes: Per-file action in popup / Undo toast 10s + X dismiss
  - 3-in-1 mode (single agent full pipeline)
  - Tests: 183/183 regression PASS
  - Commit: `1fb7f40`

- [x] **v7.1.0 — Duplicate Detection on Organize-new** (2026-05-01)
  - Plan: [archive/2026-05-01-duplicate-detection.md](../plans/archive/2026-05-01-duplicate-detection.md)
  - Built by: เขียว (round 1 + pivot DUP-003)
  - Reviewed by: ฟ้า (REVIEW-002, APPROVE 87/87 + 106/106 regression)
  - Merged: master `cd114dd`, `0adcaf1`, `c047657`, `6467b3a`

- [x] **v7.0.0 → v7.0.1 — Google Drive BYOS** (2026-05-01 deploy + 5 follow-up fixes)
  - Plan: [archive/2026-05-01-google-drive-byos.md](../plans/archive/2026-05-01-google-drive-byos.md)
  - Built by: เขียว Phase 1-3 + ฟ้า Phase 4 + E2E (full dev mode authority)
  - Deployed: Fly.io machine 82, 2026-05-01 03:04 UTC
  - Follow-ups: `73f1a96` (raw push), `e1908b8`, `ac9a6e3`, `1449666`, `c04d21c` (sync fixes)

- [x] **v6.1.0 — PDB Rebrand "Project KEY" → "Personal Data Bank"** (2026-04-30 → 2026-05-01)
  - Plan: [archive/2026-05-01-rebrand-pdb.md](../plans/archive/2026-05-01-rebrand-pdb.md)
  - Built by: เขียว (5 commits + 76/76 smoke pass)
  - Reviewed by: ฟ้า (APPROVE + version drift fix `1b7fd98`)
  - Merged: master `6e14e63`, then `d2f92da` (localStorage), `0182c06` (domain), `ee8699d` (Fly.io app)

- [x] **v6.0.0 — Personality Profile (MBTI/Enneagram/Clifton/VIA + History)** (2026-04-30)
  - Plan: [archive/2026-04-30-personality-profile.md](../plans/archive/2026-04-30-personality-profile.md)
  - Built by: เขียว
  - Reviewed by: ฟ้า
  - Merged: 2026-04-30 (commit `3f4b4b9`)

---

## ⚠️ ระบบ Pipeline ทำงานยังไง

```
Default sequential (1 feature at a time):
1. User เลือก feature จาก backlog
2. แดง วาง plan
3. User approve plan
4. เขียว build code
5. ฟ้า review + tests
6. User approve review
7. Merge → ย้ายไป Completed

Parallel override (per user — ใช้ตอน v6.1.0 + v7.0.0):
- 2 features in pipeline simultaneously
- Different agents own different features
- Authority extended (e.g., ฟ้า can dev + commit + push without review-back)

Single-agent 3-in-1 mode (per user authorization — ใช้ตอน v7.1.5):
- 1 agent ทำทั้ง plan + build + review (ไม่มี inter-session reload)
```

Default = sequential. Parallel + 3-in-1 = explicit user override only.
