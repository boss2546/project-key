# 📜 Agent System Changelog

> บันทึกการเปลี่ยนแปลงของระบบ agent memory + decisions ใหญ่ที่ agents ทำ

---

## 2026-05-01 (ฟ้า — BYOS Phase 4 substantial completion)

- 🎨 (ฟ้า) **Phase 4 Frontend UI completed** (`5b80c52`):
  - `legacy-frontend/storage_mode.js` (NEW, 296 lines) — BYOS connect/disconnect UI + OAuth callback handling
  - `legacy-frontend/index.html` — Storage Mode section in profile modal (managed/byos badge + connect button)
  - `legacy-frontend/styles.css` — +133 lines for storage mode section
  - `legacy-frontend/app.js` — wired into bootstrap
- 🔗 (ฟ้า) Wired backend to push data to Drive:
  - `backend/organizer.py` — push summaries to Drive after generation
  - `backend/graph_builder.py` — push graph.json to Drive after build
- 🚀 (ฟ้า) **Bumped APP_VERSION 6.1.0 → 7.0.0** in config.py + smoke test
- ✅ (ฟ้า) 182/182 regression tests still pass
- 👁️ (ฟ้า) Visual E2E verified on localhost:8000

**Pending after Phase 4 commit (ฟ้า WIP in working tree):**
- Continued polish on `drive_oauth.py` + `app.js` + `storage_mode.js`
- Live Google OAuth click-through E2E test (real Drive folder creation)
- Decide encryption key history option (leave 🅰️ vs rebase 🅱️)
- git push + flyctl secrets + flyctl deploy

---

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
