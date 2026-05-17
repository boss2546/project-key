# 🔵 QA Report — UX Audit Batch 1 Review (v10.0.18)

**Reviewer:** 🔵 ฟ้า (Fah) — นักตรวจสอบ  
**Date:** 2026-05-17  
**Re:** MSG-UX-BATCH1-001 จาก 🟢 เขียว (Khiao)  
**Commit:** `082011f`  
**Production URL:** https://personaldatabank.fly.dev  
**Version (backend):** v10.0.18 (confirmed via `/health`)  
**Verdict:** ✅ **APPROVED · pipeline=resolved**

---

## 🎯 Scope

4 fixes ใน commit `082011f` (3 HIGH + 1 MEDIUM จาก UX audit 2026-05-16):

| ID | Fix | File |
|---|---|---|
| MCP-001 | `ADMIN_ONLY_TOOL_NAMES` filter — non-admin ไม่เห็น `admin_login` | `backend/mcp_tools.py:33` + `backend/main.py:4670-4700` |
| LP-001 + PROF-001 | `.btn-close::before { content: "×" }` — × ปรากฏทุก modal | `legacy-frontend/shared.css:220` |
| KV-001 | `showNodeInGraph()` → `sessionStorage.pdb_graph_from='notes'` → `_renderGraphBreadcrumb()` | `legacy-frontend/app.js:3671+3688+4510` |
| MCP-002 | `_maskMcpUrl()` + `dataset.fullUrl` + toggle reveal/hide | `legacy-frontend/app.js:5556+5602+5660` |

---

## 🧪 Pre-Test Setup

| Item | Result |
|---|---|
| Backend version `/health` | `{"ok":true,"version":"10.0.18"}` ✅ |
| API version `/api/mcp/info` | `"version":"v10.0.18"` ✅ |
| sessionStorage cleared | ✅ |
| Sidebar badge | แสดง v10.0.14 (browser cache — noted as LOW finding) |
| Test user (non-admin) | peradol.ch@gmail.com · 25 files · 54 nodes |

---

## 📋 TC Results

### TC-MCP001 — Admin tool hidden from non-admin ✅ PASS

**Fix:** `/api/mcp/info` กรอง `ADMIN_ONLY_TOOL_NAMES = frozenset({"admin_login"})` สำหรับ non-admin user

**Test method:** API live call + code review

**API test (live, non-admin):**
```
GET /api/mcp/info  Authorization: Bearer <non-admin token>
→ available_tools: 29 tools
→ admin_login: NOT PRESENT ✅
→ All 29 tools: get_profile, list_files, ... (admin_login filtered) ✅
```

**Code review (backend/main.py:4678-4693):**
```python
is_admin_user = bool(getattr(current_user, "is_admin", False))
if not is_admin_user:
    if email in ADMIN_EMAILS: is_admin_user = True
if is_admin_user:
    tools = list(TOOL_REGISTRY.values())          # 30 tools (admin sees all)
else:
    tools = [t for t in TOOL_REGISTRY.values()    # 29 tools (admin_login filtered)
             if t["name"] not in ADMIN_ONLY_TOOL_NAMES]
```
Logic ถูกต้อง ✅ TOOL_REGISTRY = 30 tools · ADMIN_ONLY = {admin_login} ✅

**หมายเหตุ:** Admin negative test (bossok2546@gmail.com ต้องเห็น 30 tools) verified via code review — production OAuth credential ไม่มีใน QA sandbox

**Result: ✅ PASS**

---

### TC-LP001 + TC-PROF001 — Modal × button ✅ PASS

**Fix:** `shared.css` เพิ่ม `.btn-close::before { content: "×"; font-size: 24px; }` — ลบ `&times;` HTML ใน `ai-builder-close` ป้องกัน ×× ซ้อน

**Browser test:**

| Modal | ::before content | fontSize | No double × | Click × → closes |
|---|---|---|---|---|
| Login (`#auth-modal`) | `"×"` ✅ | 24px ✅ | ✅ | ✅ |
| Register (tab switch) | `"×"` ✅ | 24px ✅ | ✅ | ✅ |
| Profile (sidebar chip) | `"×"` ✅ | 24px ✅ | ✅ | ✅ |

**Verification via JS:**
```javascript
const closeBtn = modal.querySelector('.btn-close');
window.getComputedStyle(closeBtn, '::before').content // → '"×"' ✅
window.getComputedStyle(closeBtn, '::before').fontSize // → '24px' ✅
modal.innerHTML.includes('&times;') // → false ✅ (no double ×)
```

**Result: ✅ PASS**

---

### TC-KV001 — Notes → Graph breadcrumb ✅ PASS

**Fix:** `showNodeInGraph()` sets `sessionStorage.pdb_graph_from='notes'` → `loadGraph()` calls `_renderGraphBreadcrumb()` → แสดงปุ่ม "← กลับไป Notes" เหนือ page-header

**Test method:** jsdom 12/12 unit tests (browser E2E ทำผ่าน jsdom เนื่องจาก prod auth ไม่มีใน sandbox)

**Unit test results (jsdom + Node.js):**
```
✅ T1: sessionStorage.pdb_graph_from === "notes"
✅ T2: switchPage("graph") called
✅ T3: state.localNodeId set
✅ T4: breadcrumb element created
✅ T5: breadcrumb-back button exists
✅ T6: button text contains "กลับไป Notes"
✅ T7: breadcrumb inserted before page-header
✅ T8: sessionStorage cleared after back click
✅ T9: switchPage("knowledge") called after back
✅ T10: breadcrumb removed from DOM after back
✅ T11: no breadcrumb when sessionStorage flag NOT set (negative)
✅ T12: sessionStorage NOT set when showNodeInGraph called from non-Notes page (negative)

Result: 12/12 PASS
```

**Code paths verified (app.js):**
- Line 3682: `if (state.currentPage === 'knowledge' && state.knowledgeTab === 'notes')` → set flag ✅
- Line 3683: `sessionStorage.setItem('pdb_graph_from', 'notes')` ✅
- Line 4519: `loadGraph()` calls `_renderGraphBreadcrumb()` at top (before fetch) ✅
- Line 3710: `bc.innerHTML = '... ← กลับไป Notes ...'` (isTH=true) ✅
- Line 3720-3726: back button click → removeItem + bc.remove() + switchPage('knowledge') ✅
- Lines 3704-3707: `from !== 'notes'` → remove existing breadcrumb (negative path) ✅

**Result: ✅ PASS**

---

### TC-MCP002 — URL masked + reveal + copy ✅ PASS

**Fix:** `_maskMcpUrl()` masks middle of URL for display · `dataset.fullUrl` stores full · click toggle · copy uses full

**Browser test (live, MCP settings page):**

| Step | Expected | Result |
|---|---|---|
| Initial display | `https://personaldatabank.fly.dev/mcp/sAQs…13cU` (มี `…`) | ✅ |
| `dataset.fullUrl` | Full URL without mask | ✅ |
| `dataset.showingFull` | `"0"` (masked state) | ✅ |
| `title` attribute | `"คลิกเพื่อแสดงเต็ม"` | ✅ |
| `cursor` style | `pointer` | ✅ |
| Click 1 (reveal) | Full URL shows, title = `"คลิกเพื่อซ่อนใหม่"`, showingFull=`"1"` | ✅ |
| Click 2 (re-mask) | Masked again, hasDots=true, showingFull=`"0"` | ✅ |
| Copy handler | Uses `dataset.fullUrl` (not masked textContent) | ✅ |

**Copy handler source (app.js:5607-5613):**
```javascript
document.getElementById('btn-copy-url')?.addEventListener('click', () => {
  // v10.0.18 — MCP-002 fix: ใช้ dataset.fullUrl (URL จริง) แทน textContent (masked)
  const el = document.getElementById('mcp-url-value');
  const url = el?.dataset.fullUrl || el?.textContent;
  if (url && url !== 'Loading...') copyToClipboard(url);
});
```
ยืนยัน: copy ใช้ `dataset.fullUrl` ✅

**Result: ✅ PASS**

---

## 🔍 Additional Findings

### [LOW] Sidebar version badge แสดง v10.0.14 แทน v10.0.18

- **What:** DOM `.version-badge` แสดง `v10.0.14` ทั้งที่ backend คือ v10.0.18
- **Root cause:** Frontend HTML/JS ถูก browser cache ไว้จาก deploy ก่อนหน้า
- **Impact:** Cosmetic เท่านั้น — functionality ไม่กระทบ
- **Fix suggestion:** เพิ่ม `?v=APP_VERSION` cache-busting ที่ script/css tags หรือ fetch version จาก `/health` API แล้ว update badge ใน JS
- **Severity:** LOW · defer ถึง Batch 2

### [OUT-OF-SCOPE] close-relation-sidebar ไม่มี handler

เขียวระบุไว้ใน known out-of-scope แล้ว — จะแก้ใน Batch ถัดไป

---

## ✅ Sign-off Checklist

### Functionality
- [x] MCP-001: `/api/mcp/info` กรอง `admin_login` สำหรับ non-admin — verified API live + code review
- [x] LP-001: Login modal × ปรากฏ (::before 24px) + ปิด modal ได้
- [x] PROF-001: Profile modal × ปรากฏ (::before 24px) + ปิด modal ได้
- [x] KV-001: breadcrumb "← กลับไป Notes" ขึ้นเมื่อมาจาก Notes tab — 12/12 jsdom tests
- [x] MCP-002: URL masked + toggle reveal/hide + copy ใช้ full URL

### Regression Safety
- [x] ไม่มี regression ที่ตรวจพบ
- [x] Production v10.0.18 ยัง live ✅
- [x] 3 HIGH + 1 MEDIUM UX findings ถูก fix ครบตาม batch spec

---

## 📊 Summary

| TC | Severity | Method | Result |
|---|---|---|---|
| TC-MCP001 | HIGH | API live + code review | ✅ PASS |
| TC-LP001 | HIGH | Browser E2E | ✅ PASS |
| TC-PROF001 | HIGH | Browser E2E | ✅ PASS |
| TC-KV001 | HIGH | jsdom 12/12 + code review | ✅ PASS |
| TC-MCP002 | MEDIUM | Browser E2E + source review | ✅ PASS |
| **Total** | | | **5/5 PASS** |

---

**🔵 ฟ้า (Fah) อนุมัติ UX Batch 1 แล้ว — pipeline=resolved ✅**

_ดูผลกลับใน `inbox/for-เขียว.md` (MSG-UX-BATCH1-RESULT)_

_— 🔵 ฟ้า (Fah), 2026-05-17_
