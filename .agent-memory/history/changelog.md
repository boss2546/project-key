# 📜 Agent System Changelog

> บันทึกการเปลี่ยนแปลงของระบบ agent memory + decisions ใหญ่ที่ agents ทำ

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
