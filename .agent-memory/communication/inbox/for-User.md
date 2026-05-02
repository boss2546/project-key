# 📬 Inbox: User (Boss / พี่)

> ข้อความสรุปสำหรับ user — รายงาน + สิ่งที่ต้องตัดสินใจ + คำถาม
> Agents เขียนที่นี่เมื่อต้องการ user attention โดยไม่บังคับ block pipeline

---

## 🔴 STATUS — 2026-05-02 (cleanup session — multi-role โดย Claude)

### TL;DR — งานค้างเก็บเสร็จเกือบหมดแล้ว

**ที่ทำเสร็จในรอบนี้ (autonomous):**
- ✅ **Memory sync** — pipeline-state.md / active-tasks.md / 4 inboxes / changelog.md ตรงกับ master จริงแล้ว
- ✅ **rebrand_smoke_v6.1.0.py** — แก้ version hardcode → ใช้ `APP_VERSION` dynamic + แก้ stale invariants (localStorage `pdb_*`, fly.toml volume `project_key_data`, app.html post-split)
  - **77/77 PASS** ✅ (เดิม 68/76 = 8 fail → ตอนนี้ 0 fail + เพิ่ม 1 case ใหม่)
- ✅ **plans/google-drive-byos.md** — rebrand 37 occurrences "Project KEY"→"Personal Data Bank" + domain `project-key.fly.dev`→`personaldatabank.fly.dev` + KEEP `projectkey.db` (DB filename)
- ✅ **Inbox cleanup** — 9 stale MSGs ย้าย Read→Resolved (3 ใน เขียว + 6 ใน ฟ้า + 1 ใน แดง)
- ✅ **Local merged branches** — ลบ 4 branches ที่ verified merged เข้า master (`rebrand-pdb-v6.1.0`, `byos-v7.0.0-foundation`, `dedupe-v7.1.0`, `backup-pre-fixes-20260428-235745`)

**ที่พี่ต้องตัดสินใจก่อน production launch (BACKLOG ใหม่):**
- 🔴 **BACKLOG-008** — `backend/plan_limits.py:15-42` ตอนนี้ testing mode (999999 ทุก field). ต้น values เก่าจาก commit `d8b0d54` diff อยู่ใน [active-tasks.md](../../current/active-tasks.md) แล้ว — จะ restore ค่าเดิม หรือ revise (พ่วง pricing strategy)?
- 🔴 **BACKLOG-009** — `backend/auth.py:249-282` password reset ตอนนี้ return `reset_token` ใน JSON response ตรงๆ (ไม่ส่ง email). ต้องเลือก email service ก่อน wire:
  - 🟢 **Resend** (แนะนำ) — free 3000/เดือน + reference อยู่ใน `.design-ref/`
  - 🟡 SendGrid — free 100/วัน
  - 🟡 Gmail SMTP — ฟรีแต่ deliverability ไม่ดี

**Pipeline state ตอนนี้:** `plan_pending_approval` — v7.2.0 UX Hotfixes (แดงเขียนแผนเสร็จแล้ว ระหว่าง cleanup session) — รอพี่ approve plan ก่อนเขียวเริ่ม build

— Claude (multi-role: แดง+เขียว+ฟ้า cleanup session)

---

## 📂 Archive: เก่ากว่านี้ (เก็บไว้เผื่อ reference)

### 🔵 REVIEW-002 — v7.1.0 Duplicate Detection ✅ APPROVED (2026-05-01)

**From:** ฟ้า (Fah) — นักตรวจสอบ
**Status:** ✅ Resolved — merged + deployed (commit `cd114dd` + `0adcaf1` pivot + `6467b3a` review approval)

**สรุป:**
- Code ตรงตาม plan 100% — ไม่มีอะไรนอก scope
- **87/87 dedupe tests PASS** (33 smoke + 54 e2e)
- **106/106 BYOS regression PASS** — zero regression
- Security: cross-user safety verified (defense-in-depth), XSS กัน, no hardcoded secrets
- Performance: 10-file batch = 0.23 วินาที

**Non-blocking item (cleanup session ทำให้แล้ว):**
- ✅ `rebrand_smoke_v6.1.0.py` ใช้ `APP_VERSION` dynamic แล้ว

— ฟ้า (Fah) 🔵

---

### 🟢 STATUS — 2026-05-01 (ฟ้า BYOS deploy)

- ✅ **v7.1.0 Dedupe**: merged + deployed
- ✅ **v6.1.0 Rebrand**: merged + deployed (+ later domain rename to personaldatabank.fly.dev)
- ✅ **v7.0.0 BYOS**: deployed + 5 follow-up fixes already on master
- 📊 **Test coverage**: 267+/273 tests pass (some test drift expected, see fixture cleanup)

---

## 📋 Quick reference: agent prompts

อยากเปิด chat ใหม่ → ดู `.agent-memory/prompts/`:
- `prompt-แดง.md` — นักวางแผน (use ถ้าต้องการ plan ใหม่)
- `prompt-เขียว.md` — นักพัฒนา (use ถ้าต้องการ build feature ใหม่)
- `prompt-ฟ้า.md` — นักตรวจสอบ (use ถ้าต้องการ review/test/fix)

---

## 📝 รูปแบบเพิ่มข้อความใน inbox นี้

```markdown
## YYYY-MM-DD — [topic]
**From:** [agent name]
**Status:** 🔴 New / 👁️ Read / ✓ Resolved

[เนื้อหา]
```

Agent ใหม่อ่านไฟล์นี้ตอนเริ่ม session → user เห็นรายการใหม่หลังจบงาน
