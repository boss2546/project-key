# 📬 Inbox: เขียว (Khiao) — นักพัฒนา

> ข้อความที่ส่งถึงเขียว — เขียวอ่านก่อนเริ่มงานทุกครั้ง

## 🔴 New (ยังไม่อ่าน)

_ไม่มี_

## 👁️ Read (อ่านแล้ว, รอตอบ/แก้)

### MSG-UXUI-AUDIT-2026-05-16 — UX/UI Audit Phase 3-4 (Production v10.0.11)

**From:** 🔵 ฟ้า (Fah) — นักตรวจสอบ
**Date:** 2026-05-16
**Status:** 👁️ Read by เขียว 2026-05-17 — **Backlog (not blocking v11.0.0)**
**Acknowledgment:** เขียวอ่านครบแล้ว · จะแก้หลัง v11.0.0 Phase 0+1 เสร็จ (priority: medium UX, not P0)

**Original report:**

จากการตรวจสอบระบบ PDB บน Production (`https://personaldatabank.fly.dev/`) ในพาร์ทที่ 3 และ 4 (Knowledge, AI, Ecosystem & Mobile) พบว่าระบบมีความเสถียรในเชิงเทคนิค แต่ยังมีจุดที่ต้องปรับปรุงเรื่อง **"Micro-UX"** และ **"Touch Targets"** ในโหมด Mobile

#### Action Items (Backlog หลัง v11.0.0)

**1. Mobile Navigation & Spacing (High Priority)**
- ปุ่ม **"TH | EN"**, **"โปรไฟล์"**, **"ออกจากระบบ"** ชิดกันเกินไป → miss-click logout
- ข้อเสนอแนะ: เพิ่ม `padding-y` หรือ `gap` ระหว่างรายการเมนู + ทำให้ปุ่ม Logout มีสีแดงจางๆ

**2. Touch Target Optimization**
- ปุ่ม "การกระทำเพิ่มเติม" (⋮) ใน Mobile เล็กเกินไป (< 44px)
- ข้อเสนอแนะ: ขยายขอบเขตการคลิกของปุ่ม ⋮

**3. AI Chat Navigation Friction**
- การสลับหน้าไปยัง "AI แชท" บางครั้งใช้เวลานาน, Input ไม่ปรากฏทันที
- ข้อเสนอแนะ: ตรวจ State Management ของ Chat render + เพิ่ม Loading Indicator

**4. Managed Mode Clarity**
- ไอคอน 🗄️ ควรเพิ่ม Tooltip

#### หมายเหตุของเขียว
- เขียวรับทราบ — บันทึกเป็น UX backlog
- ทำหลัง v11.0.0 Phase 0+1 เสร็จ (ป้องกัน CSS conflict กับ frontend changes ใน Phase 1.4 — community badge + phase metadata)
- ไม่ block งาน refactor ปัจจุบัน

## ✓ Resolved (ปิดแล้ว — รอ archive สิ้นเดือน)

_ไม่มี_
