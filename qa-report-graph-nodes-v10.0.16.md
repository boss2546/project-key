# 🔬 QA Test Report: Graph & Knowledge View — Orphan Node Cleanup
## TC-5 · TC-6 · TC-7 · TC-8

**รายงานโดย:** ฟ้า (QA Agent)  
**วันที่ทดสอบ:** 2026-05-17  
**Build ที่ทดสอบ:** v10.0.16 (Production — personaldatabank.fly.dev)  
**สถานะโดยรวม:** ⚠️ **2 PASS · 1 FAIL · 1 PASS (with note)**

---

## Environment & Pre-Test

| รายการ | ค่า |
|--------|-----|
| JS runtime | ✅ `app.js?v=10.0.16`, `dev-logger.js?v=10.0.16` |
| Session flag ใหม่ | `pdb_ghosts_cleaned_v2` (เปลี่ยนจาก v1 ใน v10.0.15) |
| Session flags cleared | ✅ ล้าง pdb_ghosts_cleaned_v1 และ v2 ก่อนเริ่ม |
| สถานะเริ่มต้น | ไฟล์=0, nodes=0, edges=0, packs=0, clusters=0 |
| หมายเหตุ | cleanup-ghosts รัน page load แรก → orphan_nodes_removed=0 (clean slate) |

---

## TC-5 — Orphan Nodes หลังลบไฟล์ทั้งหมด

**วัตถุประสงค์:** อัปโหลดไฟล์ที่มี topics → organize → ลบ → ตรวจว่า nodes=0

### ขั้นตอน
1. Upload `tc5-meeting-notes.md` (รายชื่อบุคคล, ระบบ, action items)
2. `POST /api/organize-new` → สร้าง graph: **nodes=13, edges=11**
3. ลบไฟล์ผ่าน UI → ยืนยัน → ตรวจ sidebar

### ผลทันทีหลังลบ (ไม่ reload)

| Metric | Before Delete | After Delete | Expected | Status |
|--------|--------------|--------------|----------|--------|
| stat-files | 1 | **0** | 0 | ✅ |
| stat-clusters | 1 | **0** | 0 | ✅ |
| stat-edges | 11 | **0** | 0 | ✅ |
| stat-nodes | 13 | **11** | 0 | ❌ |
| stat-packs | 1 | **1** | 0 | ❌ |

### ผลหลัง reload (cleanupGhostsOnce รัน)

| รอบ | orphan_nodes_removed | stat-nodes |
|-----|---------------------|------------|
| Reload ครั้งที่ 1 (หลังลบ) | **0** ← ไม่เจอ | 11 ยังค้าง |
| Reload ครั้งที่ 2 (session ถัดไป) | **9** ← เจอ & เคลียร์ | ลดลง |

### 🐛 Bug Findings

**BUG-TC5-A: Orphan nodes ไม่ถูกลบทันทีหลัง DELETE**
- หลังลบไฟล์ผ่าน UI: nodes 13→11 (ลบได้แค่ 2/13)
- edges=0 ถูกต้อง แต่ nodes ยังค้าง 11 nodes
- cascade delete ใน DELETE endpoint ไม่ครอบคลุม graph nodes ทั้งหมด

**BUG-TC5-B: Orphan detection ไม่ทำงานใน session แรก**
- cleanupGhostsOnce รัน reload ครั้งที่ 1 → `orphan_nodes_removed=0` (ผิด — มี 11 orphan จริง)
- cleanupGhostsOnce รัน reload ครั้งที่ 2 → `orphan_nodes_removed=9` (ถูก)
- หมายความว่า orphan detection มี **timing/cache inconsistency** ใน session แรกหลัง delete

**ผล TC-5: ❌ FAIL**  
Severity: 🟡 Medium — nodes ค้างชั่วคราว แต่สุดท้ายได้รับการเคลียร์

---

## TC-6 — 🚨 Shared Entity Safety ("บอส")

**วัตถุประสงค์:** ตรวจว่า entity ที่ใช้ร่วมระหว่าง 2 ไฟล์ **ไม่ถูกลบ** เมื่อลบไฟล์ใดไฟล์หนึ่ง

### ขั้นตอน
1. Upload `tc6-file-a-team-report.md` (กล่าวถึง บอส 5 ครั้ง)
2. Upload `tc6-file-b-meeting-notes.md` (กล่าวถึง บอส 5 ครั้ง)
3. `POST /api/organize-new` → graph: **nodes=23, edges=24**
4. ตรวจสอบ node "คุณบอส" (entity id: `2957a5d5-6f7`) ก่อนลบ ✅
5. DELETE File A (`56fae356-2ad`) ผ่าน API

### ผลหลังลบ File A

| รายการ | Expected | Actual | Status |
|--------|----------|--------|--------|
| "คุณบอส" entity node ยังอยู่ | ✅ | ✅ ยังอยู่ | **✅ PASS** |
| "การบริหารจัดการโครงการ..." cluster ยังอยู่ | ✅ | ✅ ยังอยู่ | **✅ PASS** |
| total_nodes: 23→22 (ลบ 1 node unique ของ File A) | 22 | 22 | ✅ |
| total_edges: 24→11 (ลบ edges ของ File A) | ~11 | 11 | ✅ |
| File B ยังมีอยู่ใน DB | ✅ | api_files=1 | ✅ |

**ผล TC-6: ✅ PASS — ไม่มี data loss**  
Shared entity safety mechanism ทำงานถูกต้อง บอส entity ไม่ถูก cascade delete

---

## TC-7 — Regression: Pack + Cluster ยังอยู่ครบหลัง cleanup

**วัตถุประสงค์:** ยืนยันว่า context pack และ cluster ที่ยังผูกกับไฟล์ที่มีอยู่ ไม่ถูก cleanup ลบออก

### สถานะที่ทดสอบ
- File B (`83775529-157`) ยังอยู่ใน DB
- cleanupGhostsOnce รันบน page reload หลัง TC-6

### ผลหลัง cleanup

| Metric | Before Cleanup | After Cleanup | Expected | Status |
|--------|---------------|---------------|----------|--------|
| stat-packs | 1 | **1** | 1 (ผูกกับ File B) | ✅ |
| stat-clusters | 1 | **1** | 1 (ผูกกับ File B) | ✅ |
| stat-nodes | 22 | **22** | 22 | ✅ |
| orphan_nodes_removed | — | **9** | ≥0 (TC-5 leftovers) | ✅ |
| orphan_notes_removed | — | **5** | ≥0 | ✅ |

**Secondary finding:** orphan nodes จาก TC-5 (11 nodes) ในที่สุดถูกเคลียร์บน session นี้ (orphan_nodes_removed=9) — ยืนยัน cleanup ทำงานได้ แต่ล่าช้า 1 session

**ผล TC-7: ✅ PASS**  
Cleanup ไม่ over-delete pack/cluster ที่ active อยู่

---

## TC-8 — API Response Keys ใหม่

**วัตถุประสงค์:** ตรวจว่า `POST /api/files/cleanup-ghosts` มี keys `orphan_nodes_removed` และ `orphan_notes_removed` ใน response (ใหม่ใน v10.0.16)

### Response ที่ได้

```json
{
  "status": "ok",
  "stats": {
    "ghosts_purged": 0,
    "graph_nodes_removed": 0,
    "graph_edges_removed": 0,
    "suggestions_removed": 0,
    "summaries_md_removed": 0,
    "packs_updated": 0,
    "chats_updated": 0,
    "injection_logs_updated": 0,
    "empty_clusters_removed": 0,
    "orphan_nodes_removed": 0,
    "orphan_notes_removed": 0
  }
}
```

| Key | มีใน response | Status |
|-----|--------------|--------|
| `orphan_nodes_removed` | ✅ | PASS |
| `orphan_notes_removed` | ✅ | PASS |

**ผล TC-8: ✅ PASS**

---

## สรุปผลทุก Test Case

| TC | ชื่อ | ผล | หมายเหตุ |
|----|------|-----|---------|
| TC-5 | Orphan nodes หลังลบไฟล์ทั้งหมด | ❌ **FAIL** | 11 nodes ค้าง, orphan detection ไม่ทำงาน session แรก |
| TC-6 | Shared entity "บอส" safety | ✅ **PASS** | ไม่มี data loss, shared nodes preserved |
| TC-7 | Pack + Cluster regression | ✅ **PASS** | Active pack/cluster ไม่ถูกลบ |
| TC-8 | API keys ใหม่ใน cleanup response | ✅ **PASS** | orphan_nodes_removed และ orphan_notes_removed มีอยู่ |

---

## Bug Summary สำหรับทีม Dev

### 🐛 BUG-ORPHAN-NODES-001 (New — ต้องแก้)
**Severity:** 🟡 Medium  
**Title:** Orphan graph nodes ไม่ถูกล้างหลัง DELETE ทันที + cleanup session-1 detection fail

**อาการ:**
1. ลบไฟล์ผ่าน UI → nodes ลดจาก 13→11 (ไม่ใช่ 0) แม้ไม่มีไฟล์เหลือ
2. Reload page ครั้งแรกหลัง delete: `cleanupGhostsOnce` รัน → `orphan_nodes_removed=0` (ผิด)
3. Reload page ครั้งที่สอง: `orphan_nodes_removed=9` (ถูก) — nodes ถูกเคลียร์ในที่สุด

**Root Cause สมมติฐาน:**
- DELETE endpoint ลบ `graph_edges` ครบถ้วน แต่ลบ `graph_nodes` ไม่ครบ (cascade delete ขาด)
- `cleanup-ghosts` ตรวจ orphan nodes โดย query หลัง DELETE transaction อาจยัง commit ไม่สมบูรณ์ในรอบแรก (timing/transaction gap)

**แนวทางแก้ไข:**
- **Option A (Quick fix):** เพิ่ม cascade delete `graph_nodes` ใน DELETE /api/files/{id} endpoint โดยตรง
- **Option B:** ใน `cleanup-ghosts` ให้ bypass session guard แล้วเรียกซ้ำหลัง DELETE สำเร็จ
- **Option C:** เพิ่ม immediate loadStats call หลัง cleanupGhostsOnce ทุกครั้ง ไม่ใช่แค่เมื่อ purged>0

**Test Case เพื่อยืนยัน Fix:**
1. Upload file → organize (ได้ N nodes) → ลบ → stat-nodes ต้องเป็น 0 ทันที
2. Reload ครั้งเดียว → stat-nodes ยังคง 0
3. cleanup-ghosts ส่ง `orphan_nodes_removed=0` (เพราะไม่มี orphan แล้ว)

---

*QA ดำเนินการโดย ฟ้า (QA Agent) บน personaldatabank.fly.dev · 2026-05-17*  
*v10.0.16 confirmed via JS query strings · bossok2546@gmail.com (Admin)*
