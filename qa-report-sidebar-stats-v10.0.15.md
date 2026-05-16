# ✅ QA Test Report: MSG-STATS-GHOSTS-001
## Sidebar Stats Counter — Fix Verification

**รายงานโดย:** ฟ้า (QA Agent)  
**วันที่ทดสอบ:** 2026-05-17  
**Build ที่ทดสอบ:** v10.0.15 (Production — personaldatabank.fly.dev)  
**Bug ที่แก้ไข:** Sidebar stats counter ไม่ sync หลัง Delete File  
**สถานะ:** ✅ **APPROVED — pipeline=resolved**

---

## ยืนยัน Version ที่ Deploy

| รายการ | ผล |
|--------|-----|
| Badge ใน UI | v10.0.14 (HTML span ไม่ถูกอัปเดต — cosmetic only) |
| JS runtime จริง | ✅ `app.js?v=10.0.15`, `dev-logger.js?v=10.0.15`, `storage_mode.js?v=10.0.15` |
| Version ที่ทำงาน | ✅ **v10.0.15** ยืนยันจาก cache-busting query param |

> **หมายเหตุ:** Version badge ใน HTML (`<span class="logo-version">`) ยังแสดง v10.0.14 แต่ไม่ใช่ปัญหา functional — JS code ที่รันจริงเป็น v10.0.15 ทั้งหมด ควรแก้ badge ใน release ถัดไป

---

## สรุป Fix ใน v10.0.15

ทีม Dev เพิ่ม 2 กลไกใน `app.js`:

**1. `loadStats()` เรียกหลัง DELETE** — หลังลบไฟล์สำเร็จ ฟังก์ชันนี้ call `/api/stats` ใหม่และอัปเดต sidebar DOM ทันที

**2. `cleanupGhostsOnce()`** — รันครั้งเดียวต่อ session (ใช้ `sessionStorage: pdb_ghosts_cleaned_v1`) หลัง `loadStats()` โหลดครั้งแรก:
- Call `POST /api/files/cleanup-ghosts`
- ถ้า `ghosts_purged > 0` → log `[cleanup-ghosts]` และ reload stats
- ถ้า 0 ghosts → no-op, ไม่ log (correct behavior)

---

## ผลการทดสอบทีละ Test Case

### TC-1 — Delete → Sidebar อัปเดตทันที
| ขั้นตอน | ผล |
|---------|-----|
| สถานะเริ่มต้น | ไฟล์=1, โหมด=62, แพ็ค=1 (baseline หลัง upload test file) |
| กด ลบ → ยืนยัน | ✅ File list แสดง "ยังไม่มีไฟล์" ทันที |
| Sidebar หลังลบ (ไม่ reload) | ✅ **ไฟล์=0** อัปเดตทันที — ไม่มี stale cache |
| ไม่ต้อง reload page | ✅ ยืนยัน |

**ผล: PASS ✅**

---

### TC-2 — Ghost Cleanup Auto-Trigger
| รายการ | ผล |
|--------|-----|
| `cleanupGhostsOnce()` รันบน page load | ✅ ยืนยัน (`sessionStorage.pdb_ghosts_cleaned_v1 = "1"` ถูกเซ็ต) |
| `POST /api/files/cleanup-ghosts` ถูก call | ✅ ยืนยัน |
| Response | `{"ghosts_purged": 0, "graph_nodes_removed": 0, ...}` |
| Console log `[cleanup-ghosts]` | ไม่ปรากฏ (ถูกต้อง — log เฉพาะเมื่อ purged > 0) |
| Session guard ป้องกัน double-run | ✅ ยืนยัน |

**ผล: PASS ✅**

---

### TC-3 — API Stats Endpoint ตรงกับ Sidebar
| Field | /api/stats | Sidebar DOM | Match |
|-------|-----------|-------------|-------|
| total_files | 0 | stat-files = 0 | ✅ |
| total_clusters | 0 | stat-clusters = 0 | ✅ |
| total_nodes | 62 | stat-nodes = 62 | ✅ |
| total_edges | 0 | stat-edges = 0 | ✅ |
| total_context_packs | 1 | stat-packs = 1 | ✅ |
| active_tokens | 0 | stat-tokens = 0 | ✅ |

API และ Sidebar แสดงค่าตรงกันทุก field

**ผล: PASS ✅**

---

### TC-4 — Regression: Upload → Delete → Stats ปกติ
| ขั้นตอน | ผล |
|---------|-----|
| Upload `qa-test-stats-ghost.txt` ผ่าน `/api/upload` | ✅ สำเร็จ, file_id: `6c9db9ee-7a2` |
| Sidebar หลัง upload | ✅ ไฟล์=1 (อัปเดตหลัง reload) |
| ลบไฟล์ผ่าน UI | ✅ ลบสำเร็จ, toast แสดง |
| Sidebar หลังลบ | ✅ ไฟล์=0 ทันที — ไม่มี regression |
| File list | ✅ "ยังไม่มีไฟล์" |

**ผล: PASS ✅**

---

## สรุปผลการทดสอบ

| Test Case | ผล |
|-----------|-----|
| TC-1: Delete → sidebar อัปเดตทันที | ✅ PASS |
| TC-2: Ghost cleanup log และ session guard | ✅ PASS |
| TC-3: /api/stats ตรงกับ sidebar | ✅ PASS |
| TC-4: Regression — flow ปกติยังทำงาน | ✅ PASS |

**Bug MSG-STATS-GHOSTS-001: RESOLVED** ✅

---

## Secondary Finding (ไม่บล็อก Release)

หลังทดสอบ พบว่า sidebar ยังแสดง:
- **โหมด (stat-nodes) = 62**
- **แพ็ค (stat-packs) = 1**

แม้ไม่มีไฟล์อยู่ในระบบ สาเหตุ: เป็น orphaned graph nodes และ context pack จาก test session ก่อนหน้า (151 files ที่ถูกลบผ่าน UI) ซึ่ง `cleanupGhostsOnce()` ไม่ได้ถูกออกแบบมาจัดการ (cleanup ออกแบบมาสำหรับ "drive ghosts" — ไฟล์ที่ถูกลบฝั่ง Drive แต่ DB record ยังอยู่)

**ข้อเสนอ:** อาจพิจารณา endpoint แยกสำหรับ purge orphaned graph nodes หลัง file deletion หรือ cascade delete ที่ชัดเจนกว่า แต่ไม่ใช่ blocker สำหรับ release นี้

---

## การตรวจสอบ (Comparison กับ Bug Report เดิม)

| Metric | v10.0.14 (bug) | v10.0.15 (fix) |
|--------|----------------|----------------|
| ไฟล์ หลังลบหมด | ❌ 16 (stale) | ✅ 0 (immediate) |
| Reload page แล้วยังค้าง | ❌ ค้าง | ✅ แสดงถูกต้อง |
| API ตรงกับ Sidebar | ❌ ไม่ตรง | ✅ ตรงกัน |
| Ghost cleanup mechanism | ❌ ไม่มี | ✅ cleanupGhostsOnce() |

**VERDICT: APPROVED · pipeline=resolved**

---

*QA ดำเนินการโดย ฟ้า (QA Agent) บน personaldatabank.fly.dev · 2026-05-17*
