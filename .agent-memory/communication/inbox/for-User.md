# 📬 Inbox: User

> รายงานสรุปจาก agents — เรียงจากใหม่ไปเก่า

---

## ✅ [REVIEW-V10.0.17-CLEAR] clear-ฟ้า session — ปิด 7 MSG ใน inbox

**Date:** 2026-05-17
**By:** 🔵 ฟ้า (Fah) via Claude Code 3-in-1 mode
**Verdict:** ✅ **APPROVE v10.0.17** + groom 6 legacy MSGs

---

### 🎯 หลักของรอบนี้: v10.0.17 stats+ghosts cycle ปิดสมบูรณ์

**Bug:** Sidebar Stats Counter + Orphan Graph Nodes ไม่ sync หลัง DELETE ไฟล์
**3-version fix cycle:**

| Version | Commit | What | QA |
|---|---|---|---|
| v10.0.15 | `dce419f` | purge ghost rows + align stats with files (Phase 1) | ✅ PASS (qa-report-sidebar-stats-v10.0.15.md) |
| v10.0.16 | `5d27453` | purge derived orphan graph nodes (note/entity/tag/...) | ❌ TC-5 FAIL — orphan rule แคบเกิน (entity↔entity edges บัง) |
| v10.0.17 | `04e1372` | SQL stricter: orphan = no edge to source_file/pack + auto cleanupAfterDelete | ✅ **3/3 PASS** (qa-report-graph-nodes-v10.0.17.md) |

### TC-5/TC-6/TC-Edge-1 ผลสรุป (v10.0.17)

- ✅ **TC-5-Retest:** Orphan nodes = 0 ทันทีหลัง DELETE (no reload needed)
- ✅ **TC-6-Retest:** Shared entity "บอส" ยังอยู่หลังลบ 1 ของ 2 ไฟล์ที่อ้างอิง — **no data loss regression**
- ✅ **TC-Edge-1:** Sequential deletion — shared entity ถูกลบเฉพาะตอนไฟล์สุดท้ายหายไป

### Secondary findings (ไม่บล็อก)
- 🔵 **SF-001:** `cleanupAfterDelete()` fire 2 ครั้งใน TC-6 (idempotent ผลถูก แต่ API call ซ้ำ) — ตรวจ duplicate event listener
- 🔵 **SF-002:** Persistent baseline orphan (1 node + 1 pack) จาก session เก่ามาก — cleanup-ghosts ไม่จับ (known)

**BUG-ORPHAN-NODES-001: RESOLVED ✅**

---

### 📋 Inbox groom — ปิด 7 MSG ใน `inbox/for-ฟ้า.md`

| # | MSG | Verdict | Reason |
|---|---|---|---|
| 1 | STATS-GHOSTS-003 | ✅ APPROVE | v10.0.17 retest 3/3 PASS |
| 2 | STATS-GHOSTS-002 | ✅ Superseded by 003 | v10.0.17 SQL strict |
| 3 | STATS-GHOSTS-001 | ✅ APPROVE | v10.0.15 verified |
| 4 | LANDING-UI-FIX-001 | ✅ APPROVE | code shipped in master · verified helpers (`_extractDetailMessage`, `_setBtnLoading`, `_resetAuthError`) + `role="alert"`/`aria-live` × 4 + `pwd-toggle`/`pwd-wrap` × 4 อยู่จริง · Playwright 11/11 PASS (เขียวรายงาน) |
| 5 | OAUTH-LOCALHOST | ⏭️ OBSOLETE | Google Sign-In ถูกลบใน v9.5.0 · `backend/google_login.py` ไม่มีแล้ว · task ไม่เกี่ยวข้องอีก |
| 6 | V940-UPLOAD-QUEUE | ⏭️ ORPHANED | shipped via 3-in-1 v9.4.0→9.4.8 (11 versions, production stable >24h) · acknowledged ใน pipeline-state.md drift notice |
| 7 | V930-PATCH | ⏭️ ORPHANED | shipped to production v9.3.0 · 3-in-1 era |

---

### 📁 Files committed ในรอบนี้

```
A  bug-report-sidebar-stats-cache.md        ← original bug report (v10.0.14)
A  qa-report-sidebar-stats-v10.0.15.md      ← TC-1..4 PASS
A  qa-report-graph-nodes-v10.0.16.md        ← TC-5 FAIL (root cause analysis)
A  qa-report-graph-nodes-v10.0.17.md        ← TC-5/6/Edge-1 PASS (final)
M  .agent-memory/communication/inbox/for-ฟ้า.md  ← banner + 7 MSG retag ✅/⏭️
M  .agent-memory/communication/inbox/for-User.md ← this report
```

**ไม่รวมในรอบนี้ (แดง's parallel work, ยังค้าง working tree):**
- `.agent-memory/current/{pipeline-state,active-tasks,last-session}.md`
- `.agent-memory/plans/organize-refactor-v11.md` (v11 plan)
- `.agent-memory/communication/inbox/for-เขียว.md` (-659 lines, archive cleanup)

---

### 🔄 Next pipeline action

- **Production:** v10.0.17 healthy ที่ `https://personaldatabank.fly.dev`
- **Active plan:** v11.0.0 Organize Refactor — `plan_pending_approval` (ดู `.agent-memory/plans/organize-refactor-v11.md` · รอ user ตอบ Q1-Q7 + approve)
- **Recommended:** User commit แดง's parallel batch ต่อไป (pipeline-state state transition + v11 plan) จะได้ working tree สะอาด

---

# 🔵 Login Test Report — All Methods

**Date:** 2026-05-14
**Tested by:** ฟ้า (Fah) via browser_subagent
**Environment:** `http://127.0.0.1:8000` (local dev v9.4.8)

---

## ✅ ผลสรุปรวม — Login ทุกแบบทำงานถูกต้อง

| # | Test Case | Account | Result | Notes |
|---|---|---|---|---|
| 1 | **Admin Email/Password** | bossok2546@gmail.com | ✅ PASS | Login สำเร็จ → เข้าหน้า "ข้อมูลของฉัน" · เห็น sidebar ครบ · upload limit 200 MB |
| 2 | **Regular User Email/Password** | test1@gmail.com | ✅ PASS | Login สำเร็จ → เข้าหน้า "ข้อมูลของฉัน" · upload limit 100 MB · ไม่เห็น admin panel |
| 3 | **Google Sign-In Redirect** | (OAuth flow) | ✅ PASS | Redirect ไปหน้า Google "เลือกบัญชี ไปยัง Personal Data Bank" ถูกต้อง |
| 4 | **Wrong Password** | bossok2546@gmail.com | ✅ PASS | แสดง "Invalid email or password" · ไม่เปิดเผยว่า email มีอยู่หรือไม่ (security ✓) |
| 5 | **Non-existent Account** | nonexistent@gmail.com | ✅ PASS | แสดง error เดียวกัน (ป้องกัน user enumeration ✓) |
| 6 | **Empty Fields** | (ว่างทั้ง 2) | ✅ PASS | แสดง error เดียวกัน · ไม่ crash |
| 7 | **Logout** | ทั้ง 2 accounts | ✅ PASS | กลับหน้า landing page · session cleared |

---

## 🔍 ข้อสังเกต (ไม่ block · เป็น improvement suggestions)

### 🟡 Medium — Error message ภาษาอังกฤษ
- Login form label เป็นไทย ("อีเมล" / "รหัสผ่าน") แต่ error message เป็น English ("Invalid email or password")
- Suggestion: เปลี่ยนเป็น "อีเมลหรือรหัสผ่านไม่ถูกต้อง" ให้ consistent

### 🟢 Low — ไม่มี client-side validation
- กดปุ่มโดยไม่กรอกอะไรเลย ก็ส่ง request ไป server
- Suggestion: เพิ่ม required attribute ใน email/password fields

### ✅ Good Security Practices
- Error message generic สำหรับทุก failure type → ป้องกัน user enumeration
- Session clear หลัง logout สมบูรณ์
- Google OAuth ใช้ PKCE (S256) + state parameter

---

## 🎯 Verdict: ✅ ALL PASS (7/7)
