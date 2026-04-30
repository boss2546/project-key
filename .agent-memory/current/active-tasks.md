# 🎯 Active Tasks (Pipeline Mode)

> ระบบ Pipeline Sequential — ทำทีละ feature, agent ทีละคน
> Source of truth คือ [pipeline-state.md](pipeline-state.md) — ไฟล์นี้เป็น overview

---

## 🔄 Current Pipeline

ดู [pipeline-state.md](pipeline-state.md) สำหรับสถานะ real-time

**Active feature:** _ยังไม่มี — รอ user มอบหมาย_

---

## 📋 Backlog (Features ที่จะทำในอนาคต)

> User เพิ่ม features ที่นี่ก่อน → เลือกทำทีละตัว

_ยังไม่มี backlog_

### รูปแบบเพิ่ม backlog item
```markdown
- [ ] [BACKLOG-001] [ชื่อ feature]
  - Priority: 🔴 High / 🟡 Medium / 🟢 Low
  - Description: [สั้นๆ]
  - Estimated effort: S / M / L
```

---

## ✅ Completed Features (10 ล่าสุด)

_ยังไม่มี completed features ในระบบ pipeline_

### รูปแบบ completed entry
```markdown
- [x] [FEAT-001] Export ข้อมูลเป็น JSON
  - Plan: [archive/2026-04-29-export-json.md](../plans/archive/2026-04-29-export-json.md)
  - Built by: เขียว
  - Reviewed by: ฟ้า
  - Merged: 2026-04-29 16:30
```

---

## ⚠️ ระบบ Pipeline ทำงานยังไง

```
1. User เลือก feature จาก backlog
2. แดง วาง plan
3. User approve plan
4. เขียว build code
5. ฟ้า review + เขียน tests
6. User approve review
7. Merge → ย้ายไป Completed
8. กลับไปขั้น 1
```

**สำคัญ:** มี **1 feature ใน pipeline เท่านั้น**ในแต่ละช่วงเวลา
- ไม่มี parallel work
- ทำเสร็จทีละตัว → เพิ่มความปลอดภัย ลด conflict
