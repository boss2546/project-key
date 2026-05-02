# Plan: UX Critical Hotfixes — v7.2.0

**Author:** แดง (Daeng)
**Date:** 2026-05-02
**Status:** `plan_pending_approval` (รอ user ตรวจก่อนให้เขียวเขียนโค้ด)
**Estimated effort:** เขียว ~2-3 ชม. + ฟ้า ~1 ชม. (test + verify)
**Target version:** v7.2.0
**Priority:** 🔴 Critical — Data Integrity + System Stability
**Scope override:** User สั่งให้ข้ามคิวงานอื่นทั้งหมด

---

## 🎯 Goal

แก้ 5 จุด UX ที่เร่งด่วนที่สุดเพื่อป้องกัน:
- การกดปุ่มซ้ำ (double-submit) จนเกิดข้อมูลซ้ำหรือ quota เปลือง
- User ปิดหน้าจอกลางคันระหว่างอัปโหลด (ไฟล์เสีย, ข้อมูลหาย)
- Toast error หายเร็วเกินไปจน user ไม่ทันเห็น
- ความรู้สึกว่าระบบค้างหรือไม่ตอบสนอง (chat indicator delayed)
- Modal ปิดไม่ได้ด้วย ESC/backdrop ทำให้ flow ติดขัด

**ผู้ใช้:**
- คนทั่วไปที่ใช้งานปกติ — กดปุ่มแล้วคาดหวัง feedback ทันที
- คนใช้ keyboard heavy (กด ESC ปิด modal เป็นนิสัย)
- คนเจอ error แล้วยังไม่ทันอ่าน toast ก็หายไปแล้ว

**ทำเสร็จแล้วได้อะไร:**
1. ลด accidental double-submit → ลด duplicate uploads, double-organize, double-save
2. Error message ไม่ตกหล่น → user รู้ว่าเกิดอะไรขึ้นจริง
3. Chat ดูตอบสนอง = ลด churn ที่ user คิดว่าระบบค้าง
4. Modal flow ลื่นขึ้น = lower friction

---

## 📚 Context

### Existing partial implementations (สำคัญ — ห้ามทำซ้ำ)

| Item | สถานะปัจจุบัน | ต้องเพิ่มอะไร |
|---|---|---|
| **runOrganizeAll** ([app.js:1445](../../legacy-frontend/app.js#L1445)) | ✅ มี `btn.disabled = true` + spinner inside button + showLoadingOverlay | ไม่มีอะไรต้องแก้ — keep as reference pattern |
| **runOrganizeNew** ([app.js:1472](../../legacy-frontend/app.js#L1472)) | ✅ เหมือน runOrganizeAll | ไม่มีอะไรต้องแก้ |
| **sendMessage** ([app.js:2297](../../legacy-frontend/app.js#L2297)) | ⚠️ มี `_chatBusy` lock + disable input/btn + thinking message bubble | เพิ่ม **typing indicator ที่ chat header** + ตรวจจังหวะ render ให้ขึ้นทันที |
| **saveProfile** ([app.js:2744](../../legacy-frontend/app.js#L2744)) | ❌ ไม่มี disable + spinner — กดซ้ำได้ | **เพิ่ม disable + spinner** ตาม pattern runOrganize |
| **uploadFiles** ([app.js:1045](../../legacy-frontend/app.js#L1045)) | ⚠️ ใช้ `showLoadingOverlay('upload')` เต็มหน้าจอ | เพิ่ม **beforeunload guard** + **progress bar with %** จาก XHR upload events |
| **showToast** ([app.js:2897](../../legacy-frontend/app.js#L2897)) | ❌ auto-dismiss 4s ทุก type — รวม error | **error → ไม่ auto-dismiss + ปุ่ม X** |
| **Modal close** | ❌ แต่ละ modal มี btn-close listener แยก, ไม่มี ESC, ไม่มี backdrop click | เพิ่ม **global delegated listener** สำหรับ ESC + backdrop |

### กฎสำคัญ (จาก decisions.md / pattern เดิม)

- ใช้ `getLang() === 'th' ? 'ไทย' : 'English'` สำหรับ inline strings (สั้น) หรือ `t('key')` สำหรับ i18n dict
- โค้ดต้อง null-safe — ทุก `getElementById('x').addEventListener` ต้องเป็น `getElementById('x')?.addEventListener`
- หลังการ split landing/app ([commit cc1ad84](https://github.com/boss2546/project-key/commit/cc1ad84)) — `app.html` คือไฟล์เป้าหมาย index.html ไม่มีแล้ว
- ห้ามแก้ `legacy-frontend/landing.js` ในรอบนี้ (auth flow แยกออกแล้ว — ไม่เกี่ยวกับ 5 ข้อนี้)
- มี Playwright suite 98 tests รัน `PDB_TEST_URL=http://127.0.0.1:8765 npx playwright test` ต้องผ่านครบหลังแก้

---

## 📁 Files to Create / Modify

### Frontend
- [ ] [`legacy-frontend/app.js`](../../legacy-frontend/app.js) (modify — 5 จุด, ดู section 1-5 ด้านล่าง)
- [ ] [`legacy-frontend/shared.css`](../../legacy-frontend/shared.css) (modify) — เพิ่ม `.toast .toast-close`, `.upload-progress`, `.typing-indicator`
- [ ] [`legacy-frontend/styles.css`](../../legacy-frontend/styles.css) (modify) — เพิ่ม style chat-typing-status (ถ้าวางใน app shell)
- [ ] [`legacy-frontend/app.html`](../../legacy-frontend/app.html) (modify) — เพิ่ม `<span id="chat-typing-status">` ใน chat header (Section 4)

### Tests (สำหรับฟ้า)
- [ ] [`tests/e2e-ui/v7.2.0-uxhotfix.spec.js`](../../tests/e2e-ui/v7.2.0-uxhotfix.spec.js) (**create**) — Playwright test 5 sections ตรงกับ 5 ข้อ:
  - sendMessage button disabled while in-flight
  - saveProfile button disabled while in-flight
  - Error toast does NOT auto-dismiss; X button closes
  - Chat typing indicator appears within 100ms of send
  - ESC closes open modal; backdrop click closes modal
- [ ] รัน existing 98 tests ให้ผ่านครบ ห้าม regression

### Memory updates
- [ ] [`.agent-memory/current/pipeline-state.md`](../current/pipeline-state.md) (modify) — เพิ่ม v7.2.0 section state `plan_pending_approval`
- [ ] [`.agent-memory/project/decisions.md`](../project/decisions.md) (modify) — เพิ่ม `UX-001` (error toast policy: never auto-dismiss errors)

---

## 🔧 Implementation Plan — แยก 5 sections

---

### Section 1: Button Loading States (3 ปุ่ม)

**Goal:** ป้องกัน double-submit + ให้ visual feedback

**1A — `saveProfile` ([app.js:2744](../../legacy-frontend/app.js#L2744))**

ปัจจุบัน:
```js
async function saveProfile() {
 const cliftonVal = getCliftonInput();
 const viaVal = getViaInput();
 if (cliftonVal === undefined || viaVal === undefined) return;
 const data = { ... };
 try {
  const res = await authFetch('/api/profile', { ... });
  if (!res.ok) { ... }
  showToast(t('toast.profileSaved'), 'success');
  document.getElementById('profile-modal').classList.add('hidden');
  loadStats();
 } catch (e) { showToast(t('toast.error'), 'error'); }
}
```

หลังแก้:
```js
async function saveProfile() {
 const btn = document.getElementById('btn-save-profile');
 if (btn?.disabled) return; // already in-flight, abort
 const cliftonVal = getCliftonInput();
 const viaVal = getViaInput();
 if (cliftonVal === undefined || viaVal === undefined) return;
 const originalHTML = btn?.innerHTML;
 if (btn) {
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังบันทึก...' : 'Saving...'}`;
 }
 try {
  const data = { ... };
  const res = await authFetch('/api/profile', { ... });
  if (!res.ok) { ... return; }
  showToast(t('toast.profileSaved'), 'success');
  document.getElementById('profile-modal').classList.add('hidden');
  loadStats();
 } catch (e) {
  showToast(t('toast.error'), 'error');
 } finally {
  if (btn) { btn.disabled = false; btn.innerHTML = originalHTML; }
 }
}
```

**Acceptance:**
- [ ] กด "บันทึก Profile" 5 ครั้งติดกันเร็วๆ → POST /api/profile ยิงครั้งเดียว
- [ ] ระหว่างยิงปุ่มแสดง spinner + ข้อความ "กำลังบันทึก..." / "Saving..."
- [ ] หลังเสร็จ (success หรือ error) ปุ่มกลับมาเหมือนเดิม
- [ ] ถ้า validation ฟ้องเอง (cliftonVal undefined) ไม่ต้อง disable ปุ่ม

**1B — `sendMessage` ([app.js:2297](../../legacy-frontend/app.js#L2297))**

ปัจจุบันมี `_chatBusy` + disable แล้ว — แต่ปุ่ม **ไม่มี spinner ใน button**

หลังแก้: เพิ่ม spinner + คืนค่าเดิมใน `finally`
```js
const sendBtn = document.getElementById('btn-send');
const originalSendHTML = sendBtn?.innerHTML;
_chatBusy = true;
input.value = '';
input.disabled = true;
if (sendBtn) {
 sendBtn.disabled = true;
 sendBtn.innerHTML = `<span class="loading-spinner"></span>`;
}
// ... existing logic ...
finally {
 _chatBusy = false;
 input.disabled = false;
 if (sendBtn) { sendBtn.disabled = false; sendBtn.innerHTML = originalSendHTML; }
 input.focus();
}
```

**Acceptance:**
- [ ] กด send 5 ครั้งติดกัน → POST /api/chat ยิงครั้งเดียว (existing _chatBusy ทำได้แล้ว)
- [ ] ปุ่ม send แสดง spinner ระหว่างรอ
- [ ] หลังเสร็จปุ่มกลับมา (มีไอคอน paper plane เดิม)

**1C — `runOrganizeAll` / `runOrganizeNew`**
✅ **ไม่ต้องแก้** — มี pattern ครบแล้ว ([app.js:1445](../../legacy-frontend/app.js#L1445), [app.js:1472](../../legacy-frontend/app.js#L1472))

---

### Section 2: Upload Progress + Close Guard

**Goal:** ป้องกันปิดหน้าจอระหว่างอัปโหลด + แสดงเปอร์เซ็นต์จริง

**2A — `uploadFiles` ([app.js:1045](../../legacy-frontend/app.js#L1045))**

ปัจจุบันใช้ `fetch()` (ไม่ได้ progress events); `showLoadingOverlay` เต็มจอ

หลังแก้: ใช้ `XMLHttpRequest` เพื่อจับ `upload.onprogress` + เพิ่ม `beforeunload` guard

```js
let _uploadInFlight = false;

window.addEventListener('beforeunload', (e) => {
 if (_uploadInFlight) {
  e.preventDefault();
  e.returnValue = ''; // ขึ้น browser default warning
  return '';
 }
});

async function uploadFiles(fileList) {
 if (_uploadInFlight) {
  showToast(getLang() === 'th' ? 'กำลังอัปโหลดอยู่ กรุณารอ' : 'Upload already in progress', 'info');
  return;
 }
 const form = new FormData();
 for (const f of fileList) form.append('files', f);
 const count = fileList.length;
 _uploadInFlight = true;
 showLoadingOverlay(getLang() === 'th' ? `กำลังอัปโหลด ${count} ไฟล์... 0%` : `Uploading ${count} file(s)... 0%`, 'upload');

 try {
  const data = await new Promise((resolve, reject) => {
   const xhr = new XMLHttpRequest();
   xhr.open('POST', '/api/upload');
   if (state.authToken) xhr.setRequestHeader('Authorization', `Bearer ${state.authToken}`);
   xhr.upload.onprogress = (ev) => {
    if (!ev.lengthComputable) return;
    const pct = Math.round((ev.loaded / ev.total) * 100);
    const overlayMsg = document.querySelector('.loading-overlay-card .loading-message');
    if (overlayMsg) {
     overlayMsg.textContent = (getLang() === 'th' ? `กำลังอัปโหลด ${count} ไฟล์... ${pct}%` : `Uploading ${count} file(s)... ${pct}%`);
    }
   };
   xhr.onload = () => {
    if (xhr.status === 401) { reject(new Error('UNAUTHORIZED')); return; }
    try { resolve(JSON.parse(xhr.responseText)); } catch (e) { reject(e); }
   };
   xhr.onerror = () => reject(new Error('NETWORK'));
   xhr.send(form);
  });
  // ... existing post-upload logic (showToast uploaded, skipped handling, loadFiles, ...) ...
 } catch (e) {
  if (e.message === 'UNAUTHORIZED') doLogout();
  else showToast(getLang() === 'th' ? 'อัปโหลดล้มเหลว' : 'Upload failed', 'error');
 } finally {
  _uploadInFlight = false;
  hideLoadingOverlay();
 }
}
```

**หมายเหตุ:** XHR ไม่ผ่าน `authFetch` → ต้อง handle 401 manually + manual auth header (pattern เดียวกับ `authFetch`)

**Acceptance:**
- [ ] อัปโหลดไฟล์ 5MB → loading overlay แสดง % เพิ่มขึ้นจริง 0% → 100%
- [ ] ระหว่างอัปโหลด ลองปิด tab → browser ขึ้น "Are you sure?" warning
- [ ] หลังเสร็จ tab ปิดได้ปกติ
- [ ] ถ้ายิง upload ครั้งที่ 2 ระหว่างครั้งแรกยังไม่เสร็จ → toast info "กำลังอัปโหลดอยู่"

---

### Section 3: Error Toast — Never Auto-Dismiss

**Goal:** Error toast คงอยู่จนกว่า user กด X

**3A — `showToast` ([app.js:2897](../../legacy-frontend/app.js#L2897))**

ปัจจุบัน:
```js
function showToast(message, type = 'info') {
 const container = document.getElementById('toast-container');
 const toast = document.createElement('div');
 toast.className = `toast ${type}`;
 toast.textContent = message;
 container.appendChild(toast);
 setTimeout(() => toast.remove(), 4000);
}
```

หลังแก้:
```js
function showToast(message, type = 'info') {
 const container = document.getElementById('toast-container');
 if (!container) return;
 const toast = document.createElement('div');
 toast.className = `toast ${type}`;
 // ใช้ structure HTML — แต่ escape message กัน XSS
 toast.innerHTML = `<span class="toast-msg"></span><button class="toast-close" aria-label="${getLang() === 'th' ? 'ปิด' : 'Close'}">×</button>`;
 toast.querySelector('.toast-msg').textContent = message;
 toast.querySelector('.toast-close').addEventListener('click', () => toast.remove());
 container.appendChild(toast);
 // Error toast: ไม่มี auto-dismiss — user ต้องกด X เอง
 if (type !== 'error') {
  setTimeout(() => toast.remove(), 4000);
 }
}
```

**3B — CSS ใน `shared.css`**
```css
.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  /* keep existing rules */
}
.toast-msg { flex: 1; }
.toast-close {
  background: none;
  border: none;
  color: var(--text-muted);
  cursor: pointer;
  font-size: 18px;
  line-height: 1;
  padding: 0 4px;
  border-radius: 4px;
}
.toast-close:hover { color: var(--text-primary); background: rgba(255,255,255,0.06); }
```

**Acceptance:**
- [ ] `showToast('ผิดพลาด', 'error')` → toast คงอยู่อย่างน้อย 30 วินาที (ทดสอบรอ)
- [ ] กด X → toast หาย
- [ ] `showToast('ok', 'success')` → ยัง auto-dismiss 4s เหมือนเดิม
- [ ] `showToast('info', 'info')` → ยัง auto-dismiss 4s เหมือนเดิม

---

### Section 4: AI Typing Indicator

**Goal:** แสดง "AI กำลังคิด..." ทันทีที่ส่งคำถาม (ก่อน fetch กลับมา)

**4A — เพิ่ม element ใน app.html (ใน chat header)**

ปัจจุบัน chat header มี `#chat-profile-indicator` ([app.html ~line 580](../../legacy-frontend/app.html))
เพิ่มข้างๆ:
```html
<span id="chat-typing-status" class="chat-typing-status hidden">
 <span class="typing-dots"><span></span><span></span><span></span></span>
 <span data-i18n="chat.thinking">AI กำลังคิด...</span>
</span>
```

**4B — แก้ `sendMessage` ([app.js:2297](../../legacy-frontend/app.js#L2297))**

หลัง `_chatBusy = true;` (line 2304) เพิ่ม:
```js
const typingEl = document.getElementById('chat-typing-status');
typingEl?.classList.remove('hidden');
```

ใน `finally` block:
```js
typingEl?.classList.add('hidden');
```

**หมายเหตุ:** ปัจจุบันมี thinking message bubble ([app.js:2314](../../legacy-frontend/app.js#L2314)) — เก็บไว้ทั้งคู่ (one ที่ chat list, one ที่ header) เพราะ user อาจ scroll ขึ้นไปดู message เก่า

**4C — CSS ใน `styles.css` (app-only)**
```css
.chat-typing-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--accent);
  padding: 4px 10px;
  border-radius: 9999px;
  background: var(--accent-glow);
}
.chat-typing-status.hidden { display: none; }
.typing-dots { display: inline-flex; gap: 3px; }
.typing-dots span {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: var(--accent);
  animation: typingBounce 1.2s ease-in-out infinite;
}
.typing-dots span:nth-child(2) { animation-delay: 0.2s; }
.typing-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes typingBounce {
  0%, 60%, 100% { opacity: 0.3; transform: translateY(0); }
  30% { opacity: 1; transform: translateY(-3px); }
}
```

**4C i18n keys** (เพิ่มใน I18N const):
- `chat.thinking` — TH: "AI กำลังคิด..." | EN: "AI is thinking..."

**Acceptance:**
- [ ] กด send → typing indicator ขึ้นภายใน 100ms (Playwright `waitFor` สั้นๆ)
- [ ] หลังคำตอบกลับมา indicator หาย
- [ ] ตอนกำลัง typing ระหว่าง request ยังคง visible
- [ ] toggle ภาษา → text เปลี่ยนตาม

---

### Section 5: Modal UX — ESC + Backdrop

**Goal:** กด ESC หรือคลิกที่พื้นหลัง backdrop ปิด modal ที่เปิดอยู่ได้

**Modals ที่มีในระบบ:**
| Modal ID | Class | หมายเหตุ |
|---|---|---|
| `auth-modal` | `.modal-overlay` | landing only — landing.js handles ESC ใน landing context (ตัด out of scope) |
| `profile-modal` | `.modal-overlay` | app |
| `personality-history-modal` | `.modal-overlay` | app |
| `plan-modal` | `.modal-overlay` | app |
| `confirm-modal` | `.modal-overlay` | app |
| `ctx-modal` | `.modal-overlay` | app |
| `ctx-view-modal` | `.modal-overlay` | app |
| `pack-modal-overlay` | `.pack-modal-overlay` | app — class ต่างกัน! |
| `dup-modal-overlay` | `.dup-modal-overlay` | app — class ต่างกัน! |

**5A — Global handler ใน `app.js` (ใน DOMContentLoaded หลัง initAuth)**

```js
function initGlobalModalUX() {
 // ESC key — close any visible modal
 document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  const overlays = document.querySelectorAll(
   '.modal-overlay:not(.hidden), .pack-modal-overlay:not(.hidden), .dup-modal-overlay:not(.hidden)'
  );
  if (!overlays.length) return;
  // Close the topmost (last added). Use cleanup if it's confirm-modal
  // (showConfirm Promise resolves cancel to keep contract intact)
  const top = overlays[overlays.length - 1];
  if (top.id === 'confirm-modal') {
   document.getElementById('confirm-cancel')?.click(); // resolves Promise(false)
  } else {
   top.classList.add('hidden');
  }
 });

 // Backdrop click — clicking ON the overlay (not inner .modal) closes
 document.addEventListener('click', (e) => {
  const target = e.target;
  if (!(target instanceof Element)) return;
  if (
   target.classList.contains('modal-overlay') ||
   target.classList.contains('pack-modal-overlay') ||
   target.classList.contains('dup-modal-overlay')
  ) {
   if (target.classList.contains('hidden')) return;
   if (target.id === 'confirm-modal') {
    document.getElementById('confirm-cancel')?.click();
   } else {
    target.classList.add('hidden');
   }
  }
 });
}
```

เรียกใน DOMContentLoaded ([app.js:962 area](../../legacy-frontend/app.js#L962)):
```js
if (document.getElementById('app')) {
 try { initGlobalModalUX(); } catch (e) { console.warn('[init] initGlobalModalUX:', e); }
 // ... existing inits ...
}
```

**Edge cases:**
- `confirm-modal` ใช้ Promise — ถ้าปิดด้วย ESC ต้อง resolve เป็น false (เหมือนกด Cancel) → trigger `#confirm-cancel` click ที่มี cleanup logic อยู่แล้ว
- `auth-modal` อยู่บน landing.html → out of scope รอบนี้ (ถ้าจะทำ ต้องไป landing.js)
- `_pendingDuplicates` ใน `dup-modal` — ปิดผ่าน backdrop ห้ามทิ้ง state; user อาจกลับมาดูใหม่ได้ผ่าน showDuplicateModal() — accept ที่ปิดแล้ว state คงอยู่ใน closure

**Acceptance:**
- [ ] เปิด profile modal → กด ESC → ปิด
- [ ] เปิด profile modal → คลิกที่ backdrop (พื้นที่นอก .modal box) → ปิด
- [ ] เปิด profile modal → คลิกที่ input ภายใน modal → **ไม่** ปิด (target เป็น .modal ไม่ใช่ .modal-overlay)
- [ ] showConfirm() แสดง modal → กด ESC → Promise resolve `false` (เหมือนกด Cancel)
- [ ] หลายๆ modal ซ้อน (ไม่ค่อยเกิด แต่กันไว้) → ปิดทีละชั้น (top first)
- [ ] auth-modal บน landing — out of scope รอบนี้ (ฟ้า/ฉันทำตาม phase ถัดไป)

---

## 🧪 Test Plan (สำหรับฟ้า)

### New tests — สร้างไฟล์ `tests/e2e-ui/v7.2.0-uxhotfix.spec.js`

```js
test.describe("v7.2.0 / 1. Button loading states", () => {
  test("saveProfile disables button + shows spinner", async ({ page }) => { /* ... */ });
  test("sendMessage disables button + shows spinner", async ({ page }) => { /* ... */ });
});

test.describe("v7.2.0 / 2. Upload progress", () => {
  test("upload triggers loading overlay with percentage", async ({ page }) => { /* ... */ });
  test("beforeunload registered during upload", async ({ page }) => { /* ... */ });
});

test.describe("v7.2.0 / 3. Error toast persists", () => {
  test("error toast does not auto-dismiss within 6s", async ({ page }) => { /* ... */ });
  test("close button removes error toast", async ({ page }) => { /* ... */ });
  test("success toast still auto-dismisses", async ({ page }) => { /* ... */ });
});

test.describe("v7.2.0 / 4. Typing indicator", () => {
  test("typing indicator visible during chat fetch", async ({ page }) => { /* ... */ });
  test("typing indicator hidden after response", async ({ page }) => { /* ... */ });
});

test.describe("v7.2.0 / 5. Modal UX", () => {
  test("ESC closes profile modal", async ({ page }) => { /* ... */ });
  test("backdrop click closes profile modal", async ({ page }) => { /* ... */ });
  test("clicking inside modal does NOT close it", async ({ page }) => { /* ... */ });
});
```

### Regression — ห้ามพังของเดิม
- รัน `phase0-baseline thorough-pages thorough-console thorough-flows thorough-mobile` ทั้งหมดต้องผ่าน 100%
- เช็ค console ไม่มี new errors

### Manual smoke (โดยฟ้าหรือ user)
- Open browser → เล่น flow จริงทุก fix:
  1. กด save profile รัวๆ (10 ครั้ง) → ดู Network tab มี POST /api/profile แค่ครั้งเดียว
  2. อัปโหลดไฟล์ใหญ่ (5-10MB) → ดู % progress เพิ่ม + ลอง close tab → confirm dialog
  3. trigger error (เช่น save profile ตอน offline) → toast error อยู่ค้าง 30 วิ → กด X
  4. ส่งคำถาม chat → typing indicator ขึ้นทันทีที่กด send
  5. เปิด profile → กด ESC, click backdrop, click inside → ทดสอบทั้ง 3 case

---

## ⚠️ Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | XHR upload progress ไม่ทำงานถ้า file ใหญ่กว่า server limit (413) | Medium | onload จะได้ status 413 → throw → finally hideLoadingOverlay → toast error คงอยู่ |
| 2 | beforeunload prompt บน Chrome อาจไม่แสดง custom message (browser ignore) | High | Browser default warning ก็พอ — เป้าหมายแค่กันปิดบังเอิญ |
| 3 | Error toast ค้างเยอะถ้ามี network error เกิดติดกัน | Low | User กด X ปิดเอง ตามจุดประสงค์; container scroll ได้ |
| 4 | ESC handler ขัดกับ keyboard navigation ใน input field | Low | ESC ใน input → close modal เป็น natural UX (Mac native pattern) |
| 5 | Backdrop click + drag (เช่นเลือก text จาก modal ลากออก) จะ trigger close | Medium | Use mousedown+mouseup tracking — only close if both happened on overlay (defer ถ้าไม่จำเป็น MVP) |
| 6 | typingEl ยังไม่ render ทันทีที่ click → user ไม่เห็นภายใน 100ms | Low | DOM update sync → re-render frame ใน <16ms; test ด้วย requestAnimationFrame |
| 7 | กระทบ existing 98 Playwright tests (สมมุติ test กดปุ่ม save แล้วคาดว่ายิงทันที) | Medium | รัน full suite หลังแก้ทุก section; ถ้าพังให้ขยาย wait ใน test |

---

## 🚫 Out of Scope (รอ v7.3+ หรือ defer)

- Auth modal ESC/backdrop on **landing.html** (อยู่ใน landing.js — แยกรอบ)
- Optimistic UI (แสดงผลก่อน server confirm)
- Toast queue management (ถ้ามี toast 100 อันจะล้นจอ)
- Skeleton loaders แทน spinner
- Drag-resize/reorder modals
- Keyboard shortcuts สำหรับ submit (Cmd+Enter etc.)
- Chunked upload (resumable upload)
- Service worker offline support

---

## 📋 Checklist for เขียว (Implementation order)

ทำตามลำดับนี้ — สั้นไป ยาว ความเสี่ยงต่ำไปสูง:

### Phase A — เตรียมเทส (~10 นาที)
- [ ] สร้าง `tests/e2e-ui/v7.2.0-uxhotfix.spec.js` skeleton (5 describes ว่าง — implement ในแต่ละ Phase ที่เกี่ยวข้อง)
- [ ] รัน existing 98 tests → ผ่าน 100% (baseline)

### Phase B — Section 3: Error Toast (~20 นาที, ความเสี่ยงต่ำสุด)
- [ ] แก้ `showToast` ใน `app.js`
- [ ] เพิ่ม `.toast-close` CSS ใน `shared.css`
- [ ] เขียน 3 tests Section 3
- [ ] รัน → ผ่าน + 98 regression ต้องไม่พัง

### Phase C — Section 1: Button Loading (~25 นาที)
- [ ] แก้ `saveProfile` (Section 1A)
- [ ] แก้ `sendMessage` (Section 1B — เพิ่ม spinner ใน btn)
- [ ] เขียน 2 tests Section 1
- [ ] รัน → ผ่าน + regression ผ่าน

### Phase D — Section 4: Typing Indicator (~25 นาที)
- [ ] เพิ่ม `<span id="chat-typing-status">` ใน `app.html` chat header
- [ ] เพิ่ม CSS ใน `styles.css` (app-only)
- [ ] เพิ่ม i18n key `chat.thinking` ใน I18N const
- [ ] แก้ `sendMessage` show/hide indicator
- [ ] เขียน 2 tests Section 4
- [ ] รัน → ผ่าน + regression ผ่าน

### Phase E — Section 5: Modal UX (~30 นาที, กระทบ 8 modals)
- [ ] เพิ่ม `initGlobalModalUX()` function ใน `app.js`
- [ ] เรียกใน DOMContentLoaded หลัง app guard
- [ ] เขียน 3 tests Section 5
- [ ] รัน → ผ่าน + regression ผ่าน
- [ ] Manual: เปิดทุก modal (8 ตัว) ลอง ESC + backdrop click ทีละตัว

### Phase F — Section 2: Upload Progress (~40 นาที, ความเสี่ยงสูงสุด — XHR refactor)
- [ ] Refactor `uploadFiles` ใช้ XHR + progress
- [ ] เพิ่ม `_uploadInFlight` flag + beforeunload listener
- [ ] เขียน 2 tests Section 2 (อาจต้อง mock XHR หรือใช้ small file)
- [ ] รัน → ผ่าน + regression ผ่าน
- [ ] Manual: อัปโหลดไฟล์จริง 5MB → ดู % เพิ่ม + ปิด tab ขึ้น warning

### Phase G — Wrap up
- [ ] รัน full suite (98 + 12 = 110 tests) → ผ่าน 100%
- [ ] อัปเดต `pipeline-state.md` → state `code_in_progress` → `e2e_verified` หลังทดสอบ
- [ ] Commit เดียว: `feat(ux): v7.2.0 critical UX hotfixes — 5 fixes`
- [ ] Push → ฟ้า review

---

## ✅ Done Criteria

- [ ] 5 sections implement ครบ
- [ ] 12 ใหม่ + 98 เดิม = 110 tests ผ่าน 100%
- [ ] Manual smoke ผ่านทุก section (เปิดเบราว์เซอร์ทดสอบจริง)
- [ ] No new console errors
- [ ] Memory updates ครบ (pipeline-state, decisions UX-001)
- [ ] Commit pushed + Fly auto-deploy verified
