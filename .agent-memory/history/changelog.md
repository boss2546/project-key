# 📜 Agent System Changelog

> บันทึกการเปลี่ยนแปลงของระบบ agent memory + decisions ใหญ่ที่ agents ทำ

---

## 2026-05-02 (Claude multi-role Phase 1+2 — health-report-driven cleanup)

- 🔧 **Phase 1 (memory + version sync):**
  - `active-tasks.md` overwrite — Pipeline state aligned to `idle` (ตรงกับ pipeline-state.md), Completed Features เพิ่ม v7.4.0/v7.3.0/v7.2.0/v7.1.5
  - `package.json` version 6.1.0 → 7.1.5 (sync กับ APP_VERSION ใน backend/config.py)
  - `last-session.md` + `changelog.md` updated
  - Result: 3 sources of truth (config.py / package.json / pipeline-state) อยู่ในแนวเดียวกัน
- 🗂️ **Phase 2 (archive 9 shipped plans):**
  - ย้าย 9 plans ไป `plans/archive/` ตาม convention `[YYYY-MM-DD]-[name].md`:
    - 2026-04-30: personality-profile (v6.0.0)
    - 2026-05-01: rebrand-pdb + readiness-notes (v6.1.0), google-drive-byos (v7.0.0), duplicate-detection (v7.1.0)
    - 2026-05-02: dedupe-ux-v7.1.5, ux-hotfixes-v7.2.0, ux-edgecases-v7.3.0, saas-responsive-v7.4.0
  - Update plan refs ใน pipeline-state.md + active-tasks.md (Inbox/session-logs ที่เป็น historical record ไม่แก้)
  - Result: `plans/` มีแค่ README.md (active plans = 0), พร้อมรับ feature ใหม่
- 📊 **Health report findings (driver ของ session นี้):**
  - Backend 12,284 LOC / Frontend 12,519 LOC (main.py + app.js เป็น mega files)
  - Security: zero hardcoded secrets, zero SQL injection risk, zero async/sync mixing
  - Production gap: 17 commits ค้างยังไม่ deploy (master = v7.1.5+v7.2-7.4, prod = v7.1.0)
  - Identified BACKLOG-008/009 เป็น production launch gates (NOT silent tech debt)

---

## 2026-05-02 (Claude multi-role cleanup — autonomous "ดำเนินงานด้วยตัว" session)

- 🧹 (Claude) **Memory drift cleanup** — sync pipeline-state.md / active-tasks.md / 4 inboxes / last-session.md ให้ตรงกับ master จริง (lag อยู่ที่ 2026-05-01 — งานทั้งหมด v6.1.0 / v7.0.0 / v7.0.1 / v7.1.0 + frontend split deploy ไปแล้ว)
- 🧹 (Claude) **Inbox archive** — ย้าย 9 stale MSGs จาก Read/New → Resolved (3 ใน เขียว + 6 ใน ฟ้า — รวมถึง MSG-009 re-review pivot ที่ shipped แล้ว) + รวม section headers ที่ซ้ำกัน
- 🧪 (Claude) **rebrand_smoke_v6.1.0.py fix** — version dynamic via `APP_VERSION` import (4 จุด) + แก้ stale invariants:
  - localStorage keys post-d2f92da migration: `projectkey_*` → `pdb_*` (3 keys)
  - fly.toml volume source: KEEP `project_key_data` (rename = data loss risk)
  - frontend post-split: test `landing.html` + `app.html` แทน `index.html` (4 sites: 2 GET + stray-brand scan)
  - **ผลลัพธ์:** 68/76 → **77/77 PASS** ✅
- 📝 (Claude) **plans/google-drive-byos.md rebrand** — 37 occurrences "Project KEY" → "Personal Data Bank" + `project-key.fly.dev` → `personaldatabank.fly.dev` + KEEP `projectkey.db` + เพิ่ม header note ระบุ status shipped
- 🗂️ (Claude) **Local branch cleanup** — ลบ 4 merged branches: `rebrand-pdb-v6.1.0`, `byos-v7.0.0-foundation`, `dedupe-v7.1.0`, `backup-pre-fixes-20260428-235745` (verified merged + ancestor of master)
- 📋 (Claude) **Pre-launch backlog เพิ่ม** — BACKLOG-008 (plan_limits restore — file: backend/plan_limits.py:15-42) + BACKLOG-009 (email service for password reset — file: backend/auth.py:249-282) — รอ user decision ก่อน production launch
- 🔄 **Note:** ระหว่าง session แดง (อีก process) สร้าง plan v7.2.0 UX Hotfixes → pipeline state เปลี่ยนจาก idle → `plan_pending_approval`

---

## 2026-05-01 (ฟ้า — BYOS Phase 4 E2E verified + critical fixes)

- 🐛 (ฟ้า) **PKCE fix** — `backend/drive_oauth.py`: Google mandates `code_verifier` since 2025; added S256 challenge generation + storage in state cache + pass on token exchange. **This fixed the 500 error on OAuth callback.**
- 🐛 (ฟ้า) **Storage Mode "Loading..." fix** — `app.js`: call `refreshDriveStatus()` every time profile modal opens (not just on page load)
- 🐛 (ฟ้า) **401 spam logout fix** — `app.js`: debounce `doLogout()` in `authFetch` to prevent parallel background fetches from clearing session
- 🐛 (ฟ้า) **Post-OAuth context restore** — `storage_mode.js`: auto-open profile modal after `/?drive_connected=true` redirect
- 🐛 (ฟ้า) **Register → workspace direct** — `app.js`: skip pricing redirect, enter workspace immediately after registration
- ✅ (ฟ้า) **Full OAuth E2E verified on localhost:8000:**
  - Login → Profile → Connect Drive → Google Consent → Callback → BYOS mode
  - Drive folder `/Personal Data Bank/` created + layout initialized
  - API: `storage_mode: byos`, `drive_connected: true`, `drive_email: bossok2546@gmail.com`
  - Storage Mode UI: BYOS badge (green) + disconnect button + testing mode notice
- 🔧 (ฟ้า) GCP Console: added `bossok2546@gmail.com` as test user in OAuth consent screen

---

## 2026-05-01 (ฟ้า — BYOS Phase 4 substantial completion, earlier)

## 2026-04-30 (v7.0 BYOS handoff session)

### Pipeline coordination
- 🔀 **Pipeline override:** User สั่ง parallel mode — ฟ้าทำ v6.1.0 finalization, เขียวเริ่ม v7.0.0 BYOS foundation พร้อมกัน (`c5febe3`)
- 🤝 **ฟ้า authority extended:** UI bug fixes + commit + push (per user override) — ออกจาก default review-only
- 🤝 **ฟ้า further extended (final handoff):** Full dev mode for BYOS Phase 4 + push + deploy (per user "ส่งต่อให้ฟ้าทำเลย dev เองต่อด้วย")

### v6.1.0 Rebrand — `review_passed` → pending merge
- 🎨 (เขียว) Renamed "Project KEY" → "Personal Data Bank" across ~67 files in 21 active files
- 🛠️ (เขียว) Built comprehensive smoke test (76/76 PASS) — `scripts/rebrand_smoke_v6.1.0.py`
- 🐛 (เขียว) Found + fixed leak: literal "Project KEY" in served app.js WHY comment (`312658e`)
- ✅ (ฟ้า) Reviewed UI + fixed pre-existing version drift v6.0.0 → v6.1.0 in footer/CSS (`1b7fd98`)
- 📨 Verdict: APPROVE — branch `rebrand-pdb-v6.1.0` (6 commits) ready for user merge

### v7.0.0 BYOS — `phase_3_complete` → handed to ฟ้า
- 🟢 **Phase 1 Foundation** (`27e6d23`):
  - 4 new backend modules: drive_layout, drive_oauth, drive_storage (CRUD wrapper), drive_sync (sync engine)
  - 5 new endpoints: drive/status, oauth/init, oauth/callback, disconnect, storage-mode
  - Schema migration: `users.storage_mode` + `drive_connections` table + `files.drive_*` + index
  - 26/26 mock smoke tests
- 🟢 **Phase 2 Storage + Sync** (`a9e5209`):
  - drive_storage.py: 15 CRUD methods (upload/download/list/delete/upsert + Google native support)
  - drive_sync.py: push/pull/conflict resolution per Plan Q4 (Drive wins)
  - 44 mock tests added (storage 20 + sync 24)
- 🟢 **Credentials integration** (`7add112`):
  - ฟ้า GCP setup: 4 OAuth credentials via browser (no leak — paste in chat then forward)
  - เขียว generated DRIVE_TOKEN_ENCRYPTION_KEY (Fernet)
  - End-to-end verified: Google auth URL valid (541 chars, all 7 components)
- 🟢 **Phase 3 Storage routing** (`a1c8f72`):
  - storage_router.py: 9 best-effort helpers (push profile/graph/clusters/relations/contexts/summary/extracted + fetch_file_bytes + init_drive_folder_layout)
  - Wired profile.py update_profile (push profile.json after DB commit)
  - Wired OAuth callback (auto-flip storage_mode + init folder layout)
  - main.py: dynamic config resolution `_byos_cfg.is_byos_configured()` (replaces static alias for testability)
  - 16 mock tests
- 🚨 **Security incident + fix** (`58e8b9d`):
  - เขียว committed actual encryption key in `docs/BYOS_SETUP.md` (3 occurrences) at `d75d5ea`
  - Fixed forward: replaced with placeholder + rotated `.env` to new key + verified 182/182 still pass
  - Branch not pushed → leak scope = local git history only → no real damage
  - Decision deferred to ฟ้า: leave (🅰️) or rebase amend (🅱️)
- 🤝 **Final handoff** (`61789fe`):
  - ฟ้า takes over for Phase 4 frontend + live OAuth E2E + push + deploy
  - MSG-006 in inbox/for-ฟ้า.md (~150 lines context)

### Cumulative test suite (mock-based, in-process)
| Suite | Pass |
|---|---|
| rebrand_smoke_v6.1.0 | 76/76 |
| byos_foundation_smoke | 26/26 |
| byos_storage_smoke | 20/20 |
| byos_sync_smoke | 24/24 |
| byos_oauth_smoke | 20/20 |
| byos_router_smoke | 16/16 |
| **TOTAL** | **182/182** |

### Branch state
- `rebrand-pdb-v6.1.0`: 6 commits, review_passed, ready to merge
- `byos-v7.0.0-foundation`: 13 commits ahead of master (5 rebrand inherited + 7 BYOS + 1 ฟ้า version-drift fix), `phase_3_complete`, ready for Phase 4

---

## 2026-04-30 (Personality Profile v6.0.0 — same day, earlier)

- ✅ (เขียว) Built Personality Profile feature: 4 systems (MBTI/Enneagram/CliftonStrengths/VIA) + history table
- ✅ (ฟ้า) Reviewed + tested 25 API tests + 10 browser tests
- 🚀 Deployed to https://project-key.fly.dev/ as v6.0.0 (commit `3f4b4b9`, 18 commits pushed)

---

## 2026-04-29

- 🎉 สร้างระบบ agent-memory พร้อมใช้งาน
- 👥 ตั้งทีม 3 agents (เริ่มต้น): แดง, เขียว, ฟ้า
- 📁 โครงสร้าง `/.agent-memory/` พร้อม contracts, communication, history
- 📋 Bootstrap prompts พร้อม copy ไปวางในแชทใหม่
- 🔄 **เปลี่ยนเป็นระบบ Pipeline Sequential** (ปลอดภัยกว่า parallel)
  - 🔴 แดง = นักวางแผน (read-only + writes plans)
  - 🟢 เขียว = นักพัฒนา (writes source code per plan)
  - 🔵 ฟ้า = นักตรวจสอบ (writes tests + review reports)
- 📝 เพิ่ม `plans/` folder สำหรับ feature plans
- 📊 เพิ่ม `current/pipeline-state.md` เป็น single source of truth สำหรับ pipeline state
- 🛡️ เพิ่ม self-blocking ใน prompts ของเขียว+ฟ้า (เช็ค state ก่อนเริ่ม)

---

## รูปแบบ entry

```markdown
## YYYY-MM-DD
- [icon] [สิ่งที่เกิดขึ้น] (by [ชื่อ agent])
```
