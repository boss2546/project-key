# 🧠 Agent Memory System — PDB Project

> External "shared brain" สำหรับ AI agents ทำงานในโปรเจกต์ PDB
> **ระบบ Pipeline Sequential** — ปลอดภัยสูง, conflict ต่ำ

---

## 🔄 Pipeline Workflow

```
   User บอก feature
         ↓
   ┌──────────────────┐
   │ 🔴 แดง (นักวางแผน)  │  วาง plan ใน plans/[feature].md
   └────────┬─────────┘
            ↓
       User approve plan ✓
            ↓
   ┌─────────────────────┐
   │ 🟢 เขียว (นักพัฒนา)   │  เขียนโค้ดตาม plan
   └────────┬────────────┘
            ↓
   ┌─────────────────────────┐
   │ 🔵 ฟ้า (นักตรวจสอบ)   │  รีวิว + เขียน tests
   └────────┬────────────────┘
            ↓
        User approve review ✓
            ↓
        Merge → Done
```

---

## 👥 ทีม Agent (3 ตัว, ทำงาน sequential)

| Icon | ชื่อ | บทบาท | Output | Prompt |
|------|------|-------|--------|--------|
| 🔴 | **แดง (Daeng)** | นักวางแผน | Plan file | [prompt-แดง.md](prompts/prompt-แดง.md) |
| 🟢 | **เขียว (Khiao)** | นักพัฒนา | Source code | [prompt-เขียว.md](prompts/prompt-เขียว.md) |
| 🔵 | **ฟ้า (Fah)** | นักตรวจสอบ | Tests + Review | [prompt-ฟ้า.md](prompts/prompt-ฟ้า.md) |

---

## 🚀 Quick Start

### Workflow ของคุณ (User)

```
1. คุณบอก feature ที่ต้องการ
   ↓
2. เปิดแชทใหม่ → paste prompt-แดง.md
   ↓
3. แดงวาง plan → คุณ review
   ↓
4. ถ้าพอใจ → "approve plan" 
   ถ้าไม่ → บอก revise → แดงแก้
   ↓
5. ปิดแชทแดง → เปิดแชทใหม่ → paste prompt-เขียว.md
   ↓
6. เขียว build code → commit
   ↓
7. ปิดแชทเขียว → เปิดแชทใหม่ → paste prompt-ฟ้า.md
   ↓
8. ฟ้า review + เขียน tests
   ↓
9. ฟ้า verdict:
   - ✅ APPROVE → คุณ merge → done
   - ⚠️ NEEDS_CHANGES → กลับไป step 5 (เปิดเขียวใหม่)
```

### ทำไมไม่ใช้แชทเดียวสลับ agent?
- แต่ละ agent มี role ชัด → context ใน chat history สำคัญ
- เปิดแชทใหม่ = clean state → agent อ่าน memory + ทำตามบทบาทตัวเองล้วน
- ไม่สับสน role

---

## 📂 โครงสร้างโฟลเดอร์

```
.agent-memory/
├── README.md                    ← ไฟล์นี้
├── 00-START-HERE.md             ⭐ ทุก agent อ่านก่อนเริ่มเสมอ
├── PROMPTS.md                   📋 Index ของ prompts
│
├── prompts/                     🎯 Bootstrap prompts (copy ไปวางในแชทใหม่)
│   ├── prompt-แดง.md
│   ├── prompt-เขียว.md
│   └── prompt-ฟ้า.md
│
├── plans/                       📝 Feature plans (เขียนโดยแดง)
│   ├── README.md (template)
│   └── archive/                 # Plans ที่ done แล้ว
│
├── project/                     🏛️ ความจำเกี่ยวกับโปรเจกต์
│   ├── overview.md
│   ├── tech-stack.md
│   ├── architecture.md
│   └── decisions.md
│
├── current/                     📊 สถานะปัจจุบัน
│   ├── pipeline-state.md        ⭐ สถานะ pipeline real-time
│   ├── last-session.md
│   ├── active-tasks.md
│   └── blockers.md
│
├── contracts/                   📐 ข้อตกลง
│   ├── api-spec.md
│   ├── data-models.md
│   └── conventions.md
│
├── communication/               💬 ระบบส่งข้อความ (Inbox-based)
│   ├── README.md                # spec ของ inbox system
│   ├── inbox/
│   │   ├── for-แดง.md           # ข้อความถึงแดง
│   │   ├── for-เขียว.md         # ข้อความถึงเขียว
│   │   └── for-ฟ้า.md           # ข้อความถึงฟ้า
│   ├── templates/
│   │   └── review-report.md     # template สำหรับฟ้า
│   └── archive/                 # ข้อความ resolved + legacy
│
└── history/                     📜 ประวัติ
    ├── changelog.md
    └── session-logs/
```

---

## 💡 หลักการสำคัญ

0. **🌟 คุณภาพ > ความเร็ว** — ใช้ token เต็มที่ ไม่ขี้เกียจ ทำดีตั้งแต่แรก
1. **Pipeline Sequential** — agent ทีละคน ห้าม parallel
2. **User เป็น approver** — approve plan + approve review เป็น checkpoint
3. **Plan คือ contract** — เขียวทำตาม plan, ฟ้า review เทียบกับ plan
4. **เจอ bug → ส่งกลับเขียว** — ฟ้าไม่แก้ source เอง
5. **เจอ plan ผิด → ส่งกลับ user/แดง** — เขียวไม่แก้ plan เอง
6. **Memory เป็น handoff mechanism** — agent คุยผ่านไฟล์ ไม่ใช่จำในหัว
7. **Inbox-based messaging** — agent อ่าน inbox/for-ตัวเอง.md ก่อนเริ่มงานเสมอ

---

## ⚖️ ความเสี่ยง vs ความปลอดภัย

| สิ่ง | ระดับ |
|------|-------|
| Merge conflict | 🟢 ต่ำมาก (agent ทำทีละคน) |
| Code drift จาก plan | 🟢 ต่ำ (ฟ้า review เทียบ plan) |
| Memory drift | 🟡 กลาง (ต้อง update ทุก session) |
| User burden | 🟡 กลาง (approve 2 ครั้งต่อ feature) |
| Speed | 🟡 กลาง (ช้ากว่า parallel แต่เร็วกว่า solo) |

---

## 🛠️ Maintenance

- Memory ไม่ตรงกับ code → trust code, update memory
- Plan ที่ done แล้ว → ย้ายไป `plans/archive/`
- Session logs เก่ามาก → archive หรือ ignore ใน git
- Communication ที่ resolved แล้ว → mark status = "resolved" หรือลบ

---

ดู [PROMPTS.md](PROMPTS.md) เพื่อเริ่มต้นใช้งาน 🚀
