# 🐛 Bug Report: Sidebar Stats Counter ไม่ sync หลัง Delete File

**รายงานโดย:** ฟ้า (QA Agent)  
**วันที่:** 2026-05-17  
**Version:** v10.0.14 (Production — personaldatabank.fly.dev)  
**Severity:** 🟡 Medium — UI misleading แต่ไม่ crash

---

## สรุปปัญหา

เมื่อลบไฟล์ผ่านหน้า UI แล้ว **Sidebar Stats Counter** (ไฟล์ / โหมด / ความสัมพันธ์ / คอลเลกชัน) **ไม่อัปเดตให้ตรงกับ DB จริง** ในขณะที่ File List (รายการไฟล์ในหน้าหลัก) แสดงถูกต้อง

---

## Steps to Reproduce

1. Login เป็น user ที่มีไฟล์ในระบบ
2. ไปหน้า "ข้อมูลของฉัน"
3. ลบไฟล์ทีละไฟล์ผ่านปุ่ม **ลบ → ยืนยัน** จนหมดทุกไฟล์
4. สังเกต sidebar ซ้ายล่าง (ไฟล์ / โหมด / คอลเลกชัน / ความสัมพันธ์)

---

## Expected vs Actual

| Stats | Expected (หลังลบหมด) | Actual (ที่พบ) |
|-------|----------------------|----------------|
| ไฟล์ทั้งหมด (file list) | 0 | ✅ 0 — ถูกต้อง |
| ไฟล์ (sidebar) | 0 | ❌ **16** — ค้างอยู่ |
| โหมด (sidebar) | 0 | ❌ **89** — ค้างอยู่ |
| ความสัมพันธ์ (sidebar) | 0 | ❌ **57** — ค้างอยู่ |
| คอลเลกชัน (sidebar) | 0 | ❌ **11** — ค้างอยู่ |

**หมายเหตุ:** หลัง reload page ค่า sidebar ยังค้างอยู่เหมือนเดิม — ไม่ใช่แค่ render delay

---

## Root Cause Analysis (สมมติฐาน)

Sidebar stats น่าจะดึงข้อมูลจาก endpoint คนละตัวกับ file list หรืออาจมี **server-side cache** ที่ไม่ถูก invalidate หลัง DELETE สำเร็จ

ให้ตรวจสอบใน `backend/main.py` หรือ endpoint ที่ return stats เหล่านี้:
- `ไฟล์` count
- `โหมด` (topics) count  
- `ความสัมพันธ์` (relations) count
- `คอลเลกชัน` count

และตรวจว่า DELETE file endpoint (`DELETE /api/files/{file_id}`) ทำการ **invalidate / recalculate** ค่าเหล่านี้หรือไม่

---

## พฤติกรรมที่ทำงานถูกต้อง (สำหรับอ้างอิง)

จากการทดสอบลบ 151 ไฟล์ทีละอัน พบว่า:

- ✅ **File list** อัปเดตทันทีหลังลบแต่ละไฟล์
- ✅ **Toast** "ลบเรียบร้อย · กำลังเคลียร์ Google Drive" แสดงทุกครั้ง
- ✅ **Google Drive cleanup** ทำงาน (async background)
- ✅ ลบไฟล์ที่มี topics/relations → topics/relations ลดลงทันที **ระหว่างการลบ** (แสดงว่า DB ลบถูกต้อง)
- ❌ **Sidebar counter** ค้างค่าเก่าไว้ ไม่ sync กับ DB จริง โดยเฉพาะหลังจากลบจำนวนมาก

---

## Scope ของบัค

| กรณี | มีบัคไหม |
|------|----------|
| ลบไฟล์ 1-2 ไฟล์ | อาจไม่เห็น (counter อาจอัปเดตทีหลัง) |
| ลบไฟล์จำนวนมากต่อเนื่อง | ❌ **เห็นชัด** — sidebar ค้าง |
| หลัง reload page | ❌ ยังค้างอยู่ |
| หลัง logout/login ใหม่ | ต้องทดสอบเพิ่ม |

---

## แนวทางแก้ไข (สำหรับทีม Dev)

### Option A — Quick Fix (แนะนำ)
หลัง DELETE file สำเร็จ ให้ frontend เรียก **stats endpoint** ใหม่เพื่อ refresh sidebar

```js
// หลัง delete สำเร็จ
await refreshSidebarStats(); // เรียก /api/stats หรือ endpoint ที่ return ค่า counts
```

### Option B — Backend Fix
ถ้า stats ถูก cache ไว้ที่ backend ให้ **invalidate cache** ทุกครั้งที่มีการ DELETE file

### Option C — Realtime
ใช้ polling หรือ WebSocket push สำหรับ stats update (overkill สำหรับตอนนี้)

---

## Test Case สำหรับยืนยันการแก้ไข

1. Login → มีไฟล์ 10+ ไฟล์
2. จด stats sidebar ก่อนลบ
3. ลบไฟล์ทั้งหมด
4. ✅ ตรวจว่า sidebar แสดง 0 ทุก field
5. ✅ Reload page แล้ว sidebar ยังแสดง 0

---

**สิ่งที่ไม่ใช่บัค (ปิดไว้):** file list แสดง 0 ถูกต้อง, Google Drive cleanup ทำงานปกติ, ไม่มี data leak หรือ orphaned records พบในการทดสอบ
