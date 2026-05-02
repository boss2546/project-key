# 🔄 Pipeline State

> **ไฟล์สำคัญที่สุด** — บอกว่า feature ปัจจุบันถึงไหนแล้วใน pipeline
> ทุก agent ต้องอ่านก่อนเริ่มทำงาน + update เมื่อเสร็จงาน

---

## 🎯 Current Pipeline State: `idle`

### 🟢 v7.2.0 UX Critical Hotfixes — DONE ✅ (2026-05-02)

**State:** `done` ✅ — implemented + 12 v7.2.0 tests + 89 regression all pass
**Plan file:** [plans/ux-hotfixes-v7.2.0.md](../plans/ux-hotfixes-v7.2.0.md)
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

### v7.1.5 — Dedupe UX Quick Wins (NEW — 2026-05-02)
**State:** `plan_pending_approval` ⏳
**Owner (plan):** แดง (Daeng)
**Plan file:** [plans/dedupe-ux-v7.1.5.md](../plans/dedupe-ux-v7.1.5.md)
**Foundation:** patch บน v7.1.0 dedupe (commits `cd114dd` + `0adcaf1`) — frontend-only
**ETA:** เขียว ~2-3 ชม. + ฟ้า ~1 ชม.

### Scope (2 fixes แก้ pain ใหญ่ที่สุด)
- **P1 → A1:** Per-file action ใน popup — radio per row + 2 quick actions (เก็บทั้งหมด/ข้ามทั้งหมด)
- **P2 → A2:** Undo toast 5 วิ — กดผิดได้ (client-side delay, ยังไม่เรียก API)

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
- รอ user approve → queue หลัง v7.2.0

---

## ✅ Recently Completed (เรียงจากใหม่ไปเก่า)

### v7.1.0 — Duplicate Detection on Organize-new (2026-05-01)
**State:** `done` ✅ — merged + deployed
**Plan:** [plans/duplicate-detection.md](../plans/duplicate-detection.md)
**Build by:** เขียว (round 1 upload + round 2 pivot per DUP-003)
**Review by:** ฟ้า — APPROVE 2026-05-01 (REVIEW-002, 87/87 tests + 106/106 BYOS regression)
**Merged:** master commits `cd114dd` (feat) + `0adcaf1` (pivot) + `c047657` (e2e tests) + `6467b3a` (memory)
**Pivot rationale:** trigger ย้าย upload→organize-new ตาม user override → Risk #9 หาย (intra-batch SEMANTIC ทำงานได้)

### v7.0.0 → v7.0.1 — Google Drive BYOS (2026-05-01)
**State:** `done` ✅ — deployed + 5 follow-up fixes already on master
**Plan:** [plans/google-drive-byos.md](../plans/google-drive-byos.md) (post-cleanup ใช้ "Personal Data Bank" ทุกที่)
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
**Plan:** [plans/rebrand-pdb.md](../plans/rebrand-pdb.md)
**Build by:** เขียว 5 commits (76/76 smoke pass)
**Review by:** ฟ้า — APPROVE + version drift fix `1b7fd98`
**Merged:** master commits `6e14e63` (feat) + later `d2f92da` (localStorage migration) + `0182c06` (domain rename)
**Note:** original plan locked `project-key.fly.dev` แต่ user later renamed Fly.io app → `personaldatabank.fly.dev` (ee8699d)

### v6.0.0 — Personality Profile (MBTI/Enneagram/Clifton/VIA + History) (2026-04-30)
**State:** `done` ✅ — deployed
**Plan:** [plans/personality-profile.md](../plans/personality-profile.md)
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
