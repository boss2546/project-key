# 🚧 Active Blockers

> สิ่งที่ติดอยู่ — ต้องการการตัดสินใจจาก user หรือรอ agent อื่น
> Agent เจอ blocker → เพิ่มที่นี่ + tag คนที่ต้อง resolve

---

## 🔴 Blockers ปัจจุบัน
_ยังไม่มี blockers_

---

## 📋 รูปแบบ blocker entry

```markdown
### [BLOCK-001] ต้องตัดสินใจเรื่อง email service
- **Reported by:** แดง
- **Date:** 2026-04-29
- **Severity:** 🟡 Medium (block password reset feature)
- **Need decision from:** User
- **Options:**
  - SendGrid: ฟรี 100/วัน, setup ง่าย
  - Resend: ฟรี 3000/เดือน, modern API
- **Recommendation:** Resend
- **Status:** Open
```

เมื่อ resolve แล้ว:
- เปลี่ยน Status เป็น `Resolved`
- เก็บไว้ใน history หรือลบหลังจาก 1 week
