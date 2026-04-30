# 📬 Communication System — Inbox-based

> ระบบส่งข้อความระหว่าง agents (แดง / เขียว / ฟ้า) แบบมี structure
> **เปลี่ยนจาก outbox → inbox** เพื่อให้ agent อ่านที่เดียวก็ครบ

---

## 📂 โครงสร้าง

```
communication/
├── README.md          ← ไฟล์นี้ (spec)
├── inbox/             📬 ข้อความ "ถึง" แต่ละ agent
│   ├── for-แดง.md     
│   ├── for-เขียว.md   
│   └── for-ฟ้า.md     
└── archive/           📦 ข้อความ resolved แล้ว
    └── YYYY-MM.md
```

---

## 🎯 หลักการ

**1. Inbox = ข้อความ "ถึง" agent นั้น**
- แดงเปิดแชท → อ่านแค่ `inbox/for-แดง.md` ก็เห็นทุกอย่างที่ตัวเองต้องดู
- ไม่ต้องไล่อ่าน 3 ไฟล์เหมือนเดิม

**2. แต่ละ inbox มี 3 sections**
- 🔴 **New** — ยังไม่อ่าน (agent ต้องดูก่อน)
- 👁️ **Read** — อ่านแล้ว รอตอบ/แก้
- ✓ **Resolved** — ปิดเรื่องแล้ว (รอ archive)

**3. ส่งข้อความ = เพิ่มใน inbox ของผู้รับ**
- เขียวอยากถามแดง → เขียวเขียนใน `inbox/for-แดง.md` (section 🔴 New)
- ห้ามเขียนใน inbox ตัวเอง

**4. อ่านข้อความ = ย้ายจาก New → Read**
- แดงเปิด `inbox/for-แดง.md` → ย้ายข้อความใหม่ไป Read
- ตอบกลับ → เพิ่มใน inbox ของคนถาม

**5. ปิดเรื่อง = ย้ายไป Resolved**
- ทั้งสองฝ่าย OK แล้ว → ย้ายไป Resolved
- สิ้นเดือน → archive

---

## 📋 Message Format (Required)

```markdown
### MSG-NNN [PRIORITY] [Subject]
**From:** [แดง/เขียว/ฟ้า/User]
**Date:** YYYY-MM-DD HH:MM
**Re:** [optional — reply to MSG-XXX]
**Status:** 🔴 New / 👁️ Read / ✓ Resolved

[เนื้อหาข้อความ]

---
```

### Priority levels
- 🔴 **HIGH** — block pipeline ถ้าไม่ตอบ
- 🟡 **MEDIUM** — สำคัญ ตอบภายใน 1 session
- 🟢 **LOW** — FYI, ไม่ต้องรีบ

### Message ID
- รูปแบบ: `MSG-NNN` (รัน sequential ทั้งระบบ ไม่แยกตาม inbox)
- ดูตัวเลขล่าสุดจาก archive หรือ inbox อื่นๆ → +1

### Reply
- ถ้าเป็นการตอบ → ใส่ `**Re:** MSG-XXX`
- เพื่อตามเรื่องได้ว่าตอบไปยังไง

---

## 🔄 Workflow

### A. ส่งข้อความใหม่
```
1. เปิด inbox/for-[ผู้รับ].md
2. หา MSG-ID ล่าสุด → +1
3. เพิ่มข้อความใหม่ใน section 🔴 New
4. Commit: "msg(daeng→khiao): MSG-XXX subject"
```

### B. อ่าน inbox ของตัวเอง
```
1. ทุก agent เปิดแชทใหม่ → อ่าน inbox/for-[ตัวเอง].md
2. ถ้ามีอะไรใน 🔴 New → อ่าน + ย้ายไป 👁️ Read
3. ตอบ (ถ้าต้อง) → เขียนใน inbox/for-[ผู้ส่ง].md
```

### C. ปิดเรื่อง
```
1. เมื่อปัญหา resolved → ย้ายข้อความไป section ✓ Resolved
2. เปลี่ยน status: 🔴/👁️ → ✓
```

### D. Archive (สิ้นเดือน)
```
1. ย้าย ✓ Resolved → archive/YYYY-MM.md
2. Inbox เหลือแค่ New + Read
```

---

## 💡 ตัวอย่างจริง

### Scenario: เขียวถามแดงเรื่อง plan ไม่ชัด

**Step 1: เขียวเปิด `inbox/for-แดง.md` → เขียนข้อความใหม่**

```markdown
## 🔴 New

### MSG-042 🟡 MEDIUM Plan ไม่ระบุ error case
**From:** เขียว
**Date:** 2026-04-29 15:30
**Status:** 🔴 New

ใน plans/export-json.md ระบุว่าให้ export ไฟล์ทั้งหมด
แต่ถ้า user ไม่มีไฟล์เลย → ควร return [] หรือ 404?

— เขียว
```

**Step 2: แดงเปิดแชทใหม่ → อ่าน `inbox/for-แดง.md`**
- เห็น MSG-042 → ตัดสินใจ → ตอบ

**Step 3: แดงเขียนตอบใน `inbox/for-เขียว.md`**

```markdown
## 🔴 New

### MSG-043 🟡 MEDIUM Re: Plan ไม่ระบุ error case
**From:** แดง
**Date:** 2026-04-29 15:45
**Re:** MSG-042
**Status:** 🔴 New

ใช้ return [] ครับ — ตามหลัก REST endpoint ที่ list resource
ผม update plan แล้วใน Section "Edge Cases"

— แดง
```

**Step 4: แดงย้าย MSG-042 ไป ✓ Resolved ใน inbox ตัวเอง**

**Step 5: เขียวเปิดแชทใหม่ → เห็น MSG-043 → ทำตาม → ย้ายไป Resolved**

---

## ✅ ข้อดีของระบบนี้

1. **อ่านที่เดียว** — agent เปิด inbox ตัวเองเห็นทุกเรื่อง
2. **Status ชัด** — เห็นทันทีว่าอันไหน new / รอตอบ / ปิดแล้ว
3. **Threading** — ดู `Re:` ได้ว่าตอบเรื่องไหน
4. **Priority** — รู้ว่าเรื่องไหนต้องจัดการก่อน
5. **Audit trail** — archive เก็บประวัติได้

---

## 🆚 ก่อน vs หลัง

| | ก่อน (`from-*.md`) | หลัง (`inbox/for-*.md`) |
|---|---|---|
| Agent ต้องอ่านกี่ไฟล์? | 3 ไฟล์ | **1 ไฟล์** |
| Status tracking | ❌ | ✅ (New/Read/Resolved) |
| Priority | ❌ | ✅ (HIGH/MED/LOW) |
| Reply threading | ❌ | ✅ (Re:) |
| Message ID | ❌ | ✅ (MSG-NNN) |
| Archive | ❌ | ✅ (รายเดือน) |
