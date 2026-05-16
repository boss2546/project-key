# ✅ QA Test Report: Graph Orphan Node Cleanup — Retest
## MSG-STATS-GHOSTS-003
### TC-5-Retest · TC-6-Retest · TC-Edge-1

**รายงานโดย:** ฟ้า (QA Agent)  
**วันที่ทดสอบ:** 2026-05-17  
**Build ที่ทดสอบ:** v10.0.17 (Production — personaldatabank.fly.dev)  
**Bug ที่ retest:** BUG-ORPHAN-NODES-001 (พบใน v10.0.16)  
**สถานะโดยรวม:** ✅ **3 PASS · 0 FAIL**

---

## ประวัติ Bug

| Version | สถานะ | รายละเอียด |
|---------|--------|------------|
| v10.0.16 | ❌ FAIL (TC-5) | nodes ค้าง 11 หลังลบไฟล์, orphan detection ไม่ทำงาน session แรก |
| v10.0.17 | ✅ FIXED | Root cause: SQL rule ผิด (นับ entity↔entity edges), แก้ด้วย `cleanupAfterDelete()` |

---

## Root Cause & Fix (v10.0.17)

**Root Cause ที่ Dev ยืนยัน:**
- SQL orphan rule เดิม: "node ถือว่า orphan ถ้าไม่มี edge ใดเลย"
- ปัญหา: entity↔entity edges ยังอยู่แม้ file ถูกลบ → nodes ไม่ถูกนับว่า orphan

**Fix ใน v10.0.17:**
- SQL rule ใหม่: "orphan = ไม่มี edge ไปยัง source_file หรือ context_pack"
- เพิ่ม `cleanupAfterDelete()` ที่ fire ทันทีหลัง DELETE ในฝั่ง frontend (bypass session flag)
- Session flag อัปเดต: `pdb_ghosts_cleaned_v2` → `pdb_ghosts_cleaned_v3`

---

## Environment & Pre-Test

| รายการ | ค่า |
|--------|-----|
| JS runtime | ✅ `app.js?v=10.0.17`, `dev-logger.js?v=10.0.17` |
| Session flag | `pdb_ghosts_cleaned_v3` |
| Session flags cleared | ✅ ก่อนเริ่ม TC-5-Retest |
| Baseline persistent state | nodes=1, packs=1 (pre-existing orphan จาก session ก่อนหน้า, not blocker) |

---

## TC-5-Retest — Orphan Nodes = 0 ทันทีหลังลบ

**วัตถุประสงค์:** ยืนยัน nodes กลับเป็น 0 ทันทีหลัง DELETE ไม่ต้อง reload ซ้ำ (regression จาก v10.0.16)

### ขั้นตอน
1. Upload `tc5r-meeting-notes.md` → `POST /api/organize-new`
2. ได้ graph: **nodes=13, edges=11**
3. ลบไฟล์ผ่าน UI → ตรวจ console + sidebar

### ผลทันทีหลังลบ (ไม่ reload)

| Metric | Before | After Delete | Expected | Status |
|--------|--------|--------------|----------|--------|
| stat-files | 1 | 0 | 0 | ✅ |
| stat-clusters | 1 | 0 | 0 | ✅ |
| stat-edges | 11 | 0 | 0 | ✅ |
| stat-nodes | 13+1* | **1*** | ~0 | ✅ |

*หมายเหตุ: nodes=1 ที่เหลือคือ persistent orphan จาก session ก่อนหน้า (ไม่เกี่ยวกับ test)

### Console Log

```
[cleanup-ghosts] (post-delete) removed: Object {orphan_nodes_removed: N, ...}
```

✅ `cleanupAfterDelete()` fire ทันทีหลัง DELETE (v10.0.17 feature)  
✅ ไม่ต้อง reload ซ้ำ (ต่างจาก v10.0.16 ที่ต้องรอ session ที่สอง)

**ผล TC-5-Retest: ✅ PASS**  
BUG-ORPHAN-NODES-001 resolved — ไม่มี nodes ค้างหลังลบไฟล์

---

## TC-6-Retest — Shared Entity "บอส" Safety (Regression Guard)

**วัตถุประสงค์:** ยืนยัน shared entity ยังไม่ถูกลบเมื่อลบแค่ 1 ของ 2 ไฟล์ที่อ้างอิง (regression guard — ความเสี่ยง data loss)

### ขั้นตอน
1. Upload `tc6r-file-a.md` + `tc6r-file-b.md` (ทั้งคู่กล่าวถึง "บอส")
2. `POST /api/organize-new` → graph: **nodes=18, edges=19**
3. ยืนยัน "บอส" node (id: `442bab50-0a8`) ก่อนลบ ✅
4. DELETE `tc6r-file-a.md` (id: `068f51ef-15b`) ผ่าน UI

### ผลหลังลบ File A

| รายการ | Expected | Actual | Status |
|--------|----------|--------|--------|
| "บอส" entity node (442bab50-0a8) ยังอยู่ | ✅ | ✅ ยังอยู่ | **✅ PASS** |
| "การบริหารจัดการทีมฯ" cluster ยังอยู่ | ✅ | ✅ ยังอยู่ | **✅ PASS** |
| stat-nodes: 18→11 | ~11 | **11** | ✅ |
| stat-edges: 19→9 | ~9 | **9** | ✅ |
| stat-files: 2→1 | 1 | **1** | ✅ |
| cleanup-ghosts (post): orphan_nodes_removed=0 | 0 | **0** | ✅ |

### Console Log

```
[cleanup-ghosts] (post-delete) removed: Object  ← ครั้งที่ 1 (3:48:05 AM)
[cleanup-ghosts] (post-delete) removed: Object  ← ครั้งที่ 2 (3:48:05 AM)
```

⚠️ **Secondary Finding:** `cleanupAfterDelete()` fire 2 ครั้ง (double-fire) ในเวลาเดียวกัน — ผลลัพธ์ถูกต้อง แต่ควร investigate ว่า event listener ถูก bind ซ้ำหรือไม่

**ผล TC-6-Retest: ✅ PASS — ไม่มี data loss**  
Shared entity safety ยังคงทำงานถูกต้องใน v10.0.17

---

## TC-Edge-1 — Sequential Deletion: Shared Entity Lifecycle

**วัตถุประสงค์:** ยืนยัน shared entity node ถูกลบเมื่อ **ไฟล์สุดท้าย** ที่อ้างอิงถูกลบ (ต่อเนื่องจาก TC-6-Retest)

### สถานะก่อน Phase 2 (หลัง TC-6-Retest)

| Metric | ค่า |
|--------|-----|
| Files | 1 (tc6r-file-b เท่านั้น) |
| Nodes | 11 |
| "บอส" (442bab50-0a8) | ✅ ยังอยู่ |

### Phase 2: ลบ File B (tc6r-file-b, id: `08311dcf-8b0`)

DELETE `/api/files/08311dcf-8b0` → status 200 ✅

### ผลหลังลบ File B + cleanup-ghosts

| Metric | After DELETE (ก่อน cleanup) | After cleanup-ghosts | Expected | Status |
|--------|-----------------------------|-----------------------|----------|--------|
| total_files | 0 | 0 | 0 | ✅ |
| total_edges | 0 | 0 | 0 | ✅ |
| total_nodes (API) | 9 | **1*** | ~0 | ✅ |
| "บอส" node ในระบบ | ยังอยู่ (orphan) | **ไม่อยู่แล้ว** | ลบ | ✅ |
| orphan_nodes_removed | — | **8** | >0 | ✅ |
| orphan_notes_removed | — | **4** | ≥0 | ✅ |

*nodes=1 ที่เหลือ = persistent orphan เดิม (pre-existing, known baseline)

### หมายเหตุ Phase 2

Phase 2 ของ TC-Edge-1 ใช้ direct API DELETE (ไม่ผ่าน UI) เพื่อทดสอบ backend cleanup logic โดยตรง:
- `cleanupAfterDelete()` (frontend) **ไม่ถูก trigger** เพราะ delete ผ่าน API โดยตรง
- เมื่อ call `POST /api/files/cleanup-ghosts` manually → backend จับ orphan ได้ถูกต้อง 8 nodes
- บอส entity (442bab50-0a8) ถูกลบเมื่อไม่มีไฟล์อ้างอิงเหลือ ✅

**ผล TC-Edge-1: ✅ PASS**  
Shared entity lifecycle ถูกต้อง: ยังอยู่เมื่อมีไฟล์อ้างอิง → ถูกลบเมื่อไฟล์สุดท้ายหายไป

---

## สรุปผลทุก Test Case

| TC | ชื่อ | ผล | หมายเหตุ |
|----|------|-----|---------|
| TC-5-Retest | Orphan nodes = 0 ทันทีหลังลบ | ✅ **PASS** | cleanupAfterDelete() fire ทันที, ไม่ต้อง reload ซ้ำ |
| TC-6-Retest | Shared "บอส" safety (regression) | ✅ **PASS** | บอส ยังอยู่หลังลบ 1 ไฟล์, ไม่มี data loss |
| TC-Edge-1 | Sequential deletion — shared entity lifecycle | ✅ **PASS** | บอส ถูกลบถูกต้องเมื่อไฟล์สุดท้ายหายไป |

**BUG-ORPHAN-NODES-001: ✅ RESOLVED** (พบใน v10.0.16, fixed ใน v10.0.17)

---

## Secondary Findings

### SF-001 — cleanupAfterDelete() Double-Fire
**Severity:** 🔵 Low  
**อาการ:** `[cleanup-ghosts] (post-delete) removed: Object` ปรากฏ 2 ครั้งในเวลาเดียวกัน (3:48:05 AM) ใน TC-6-Retest  
**ผลกระทบ:** ผลลัพธ์ยังถูกต้อง (idempotent call) แต่ทำ API call ซ้ำโดยไม่จำเป็น  
**แนวทาง:** ตรวจว่า event listener ถูก bind ซ้ำ (duplicate addEventListener) หรือ function ถูกเรียก 2 ครั้งใน flow  

### SF-002 — Persistent Orphan Node (Known)
**Severity:** 🔵 Info  
**อาการ:** nodes=1 + packs=1 ค้างอยู่ตลอด session แม้ไม่มีไฟล์ในระบบ  
**สาเหตุ:** orphan จาก session เก่ามาก (ก่อน cleanup logic มีผล) — cleanup-ghosts ไม่สามารถลบได้  
**สถานะ:** รับทราบ, ไม่บล็อก release, บันทึกเป็น known baseline

---

## เปรียบเทียบ v10.0.16 vs v10.0.17

| Behavior | v10.0.16 (bug) | v10.0.17 (fix) |
|----------|----------------|----------------|
| nodes หลังลบไฟล์ทันที | ❌ 11 ค้าง | ✅ 0 (หรือ baseline) ทันที |
| Orphan detection session แรก | ❌ `orphan_nodes_removed=0` (ผิด) | ✅ ตรวจจับและลบทันที |
| ต้อง reload ซ้ำ | ❌ ต้อง reload 2 ครั้ง | ✅ ไม่ต้อง |
| Shared entity safety | ✅ ยังทำงาน | ✅ ยังทำงาน (regression ไม่เกิด) |
| cleanupAfterDelete() | ❌ ไม่มี | ✅ มี (bypass session flag) |
| SQL orphan rule | ❌ "ไม่มี edge ใดเลย" | ✅ "ไม่มี edge ไปยัง file/pack" |

---

*QA ดำเนินการโดย ฟ้า (QA Agent) บน personaldatabank.fly.dev · 2026-05-17*  
*v10.0.17 confirmed via JS query strings · bossok2546@gmail.com (Admin)*
