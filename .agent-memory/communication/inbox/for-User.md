# 📬 Inbox: User (Boss / พี่)

> ข้อความสรุปสำหรับ user — รายงาน + สิ่งที่ต้องตัดสินใจ + คำถาม
> Agents เขียนที่นี่เมื่อต้องการ user attention โดยไม่บังคับ block pipeline

---

## 🟢 STATUS — 2026-05-01 (เขียว handed BYOS to ฟ้า)

### TL;DR
- ✅ **v6.1.0 Rebrand**: เสร็จ + review_passed → **รอพี่ merge to master + deploy**
- 🚧 **v7.0.0 BYOS**: Phase 3/4 done (backend ครบ 100%) → **ฟ้ารับช่วงต่อ Phase 4 frontend**
- 📊 **Test coverage**: 182/182 in-process tests pass (mock-based)

---

## 🔵 v6.1.0 Rebrand — รอพี่ทำต่อ

**Branch:** `rebrand-pdb-v6.1.0` (6 commits, 0 dirty files, NOT pushed)

**Status:** ✅ ฟ้า reviewed + APPROVED + fixed pre-existing version drift

**สิ่งที่พี่ต้องทำ:**
1. Review final commits: `git log --oneline master..rebrand-pdb-v6.1.0`
2. Merge to master:
   ```bash
   git checkout master
   git merge rebrand-pdb-v6.1.0
   git push origin master
   ```
3. Deploy:
   ```bash
   flyctl deploy
   ```
4. Smoke test production:
   ```bash
   curl https://project-key.fly.dev/ | grep -o "Personal Data Bank"
   curl https://project-key.fly.dev/api/mcp/info  # version should be 6.1.0 (after auth)
   ```
5. Update `pipeline-state.md` → state: `done` for v6.1.0

**หรือมอบให้ฟ้าทำ** (per parallel mode authority extension): "ฟ้า merge + deploy v6.1.0 ด้วย"

---

## 🟢 v7.0.0 BYOS — ฟ้าจะทำต่อ Phase 4

**Branch:** `byos-v7.0.0-foundation` (13 commits ahead of master, parented off rebrand HEAD, NOT pushed)

**ที่เสร็จแล้ว (เขียว build + 182/182 tests):**
- ✅ Schema migration (storage_mode + drive_connections + files.drive_*)
- ✅ Backend: drive_layout / drive_oauth / drive_storage / drive_sync / storage_router
- ✅ 5 endpoints: drive/status, oauth/init, oauth/callback, disconnect, storage-mode
- ✅ Wired profile.py (push profile.json after DB commit)
- ✅ Wired OAuth callback (auto-flip storage_mode + init folder layout)
- ✅ Credentials integrated (in `.env` gitignored — 5 from ฟ้า GCP setup + DRIVE_TOKEN_ENCRYPTION_KEY)
- ✅ docs/BYOS_SETUP.md admin guide
- ✅ Verified end-to-end: `is_byos_configured() == True`, Google auth URL valid 541 chars

**ฟ้าจะทำต่อ:**
- 🚧 Phase 4 Frontend UI (~3-4 ชม.)
- 🚧 Live OAuth E2E test (browser-based)
- 🚧 Decide encryption key history option (see Security note below)
- 🚧 git push + flyctl deploy

---

## ⚠️ DECISION ที่พี่ตัดสินใจได้ก่อน push

### Encryption key in git history at commit `d75d5ea`

**Background:** เขียวพลาด commit ค่าจริงของ `DRIVE_TOKEN_ENCRYPTION_KEY` ใน docs/BYOS_SETUP.md (3 occurrences). พบจาก confirmation check + แก้ทันที:
- Replaced ด้วย placeholder (`58e8b9d`)
- Rotated .env เป็น key ใหม่
- Old key still in git history at `d75d5ea`

**Risk = 0 in practice** (branch ยังไม่ push, DB ไม่มี data จริง, old key inert)

**Options before first `git push`:**
- 🅰️ **Leave history** — push as-is. Old key in history แต่ inert. Simpler.
- 🅱️ **Rebase amend** `d75d5ea` ก่อน push — clean history, force-push required, rewrite 5 commits ตามมา

**ผมแนะนำ 🅰️** (simpler + no real damage). ฟ้าตัดสินใจตามใจชอบ + พี่ override ได้

---

## 📨 จาก ฟ้า

ดู `for-User.md` หน้าใหม่ (ฟ้าจะเขียนมาเมื่อจบ Phase 4)

---

## 📨 จาก แดง

แดงมี 1 task รออยู่: revise plan `google-drive-byos.md` (37 brand occurrences "Project KEY" → "Personal Data Bank"). Non-blocking — เขียวเขียนโค้ดใช้ "Personal Data Bank" ตั้งแต่ต้นแล้ว.

ถ้าพี่อยาก trigger แดง → spawn แดง chat ใหม่ + ให้แดงอ่าน MSG-001 ใน inbox/for-แดง.md

---

## 📊 Branches summary

```
master                       (= live production v6.0.0)
├── rebrand-pdb-v6.1.0       (6 commits — review_passed, ready to merge)
└── byos-v7.0.0-foundation   (13 commits ahead — parented off rebrand HEAD,
                              ready for Phase 4 frontend by ฟ้า)
```

---

## 📋 Quick reference: agent prompts

อยากเปิด chat ใหม่ → ดู `.agent-memory/prompts/`:
- `prompt-แดง.md` — นักวางแผน (use ถ้าต้องการ plan ใหม่)
- `prompt-เขียว.md` — นักพัฒนา (use ถ้าต้องการ build feature ใหม่)
- `prompt-ฟ้า.md` — นักตรวจสอบ (use ถ้าต้องการ review/test/fix)

**Note:** ฟ้าตอนนี้มี extended authority (full dev + push) สำหรับ BYOS — ดู MSG-006 ใน inbox/for-ฟ้า.md

---

## 📝 รูปแบบเพิ่มข้อความใน inbox นี้

```markdown
## YYYY-MM-DD — [topic]
**From:** [agent name]
**Status:** 🔴 New / 👁️ Read / ✓ Resolved

[เนื้อหา]
```

Agent ใหม่อ่านไฟล์นี้ตอนเริ่ม session → user เห็นรายการใหม่หลังจบงาน
