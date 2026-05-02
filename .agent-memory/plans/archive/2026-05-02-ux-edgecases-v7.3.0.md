# Plan: UX Edge-Cases & Mobile Fixes — v7.3.0

**Author:** แดง (Daeng)
**Date:** 2026-05-02
**Status:** `plan_pending_approval` (รอ user ตรวจ — แต่ user authorize full dev mode → จะ implement ตามแผนหลังเขียนเสร็จ)
**Estimated effort:** เขียว ~3-4 ชม. + ฟ้า ~1-1.5 ชม.
**Target version:** v7.3.0
**Priority:** 🟡 High — UX polish + mobile usability
**Foundation:** ต่อยอดจาก commit `dddc74e` (v7.2.0 UX hotfixes)

---

## 🎯 Goal

แก้ 3 edge cases ที่เจอเพิ่มหลัง v7.2.0 ปล่อย:
1. Mobile users (ปัจจุบันใช้งานเกือบไม่ได้ — sidebar 220px กิน viewport เกือบหมด)
2. Form validation feedback บน Context create modal — error toast บอกแต่ไม่ highlight ช่อง
3. Modal โดน guide-drawer (z-index 10000) ทับ — ถ้าเปิดคู่มือค้างไว้

**ผู้ใช้:**
- คนใช้งานบนมือถือ — ปัจจุบัน sidebar เปิดเต็มจอ ทำให้ไม่เห็น content
- คนกรอก form แล้วลืมช่องบังคับ — toast หายไปแล้วต้องเดาว่าลืมช่องไหน
- คนเปิดคู่มือไว้แล้วทำงานต่อ → modal ซ้อนใต้คู่มือเห็นไม่ชัด

**ทำเสร็จแล้วได้อะไร:**
1. Mobile UX ใช้ได้จริง (~30% ของ user เข้าผ่านมือถือ)
2. Form errors ชัดเจน → ลด time-to-fix
3. Modal layering ถูกต้อง → flow ไม่สับสน

---

## 📚 Context

### 3.1 Mobile — Existing State

**ปัจจุบัน:**
- [`legacy-frontend/styles.css:30-53`](../../legacy-frontend/styles.css#L30) — `.app-container { display: flex }` + `.sidebar { width: 220px (var --sidebar-width) }`
- มี `@media (max-width: 768px)` 1 จุดที่ [`styles.css:2697`](../../legacy-frontend/styles.css#L2697) (landing-only — ใน styles.css อยู่แต่ landing rules ถูก strip ไป landing.css แล้ว — ตรวจอีกที)
- **ไม่มี hamburger menu, ไม่มี mobile sidebar pattern** — sidebar คงอยู่เต็ม 220px ทุก viewport
- App.html: sidebar ([app.html:120-235](../../legacy-frontend/app.html#L120)) อยู่ก่อน main-content

**Class structure ที่มี:**
- `.app-container` → flex container
- `.sidebar` → 220px
- `.main-content` → flex: 1

**Mobile breakpoint design (ใหม่):**
- `<768px`: sidebar fixed slide-out + hamburger top-left + backdrop
- toggle ผ่าน class `.sidebar-open` บน `.app-container`
- เมื่อกด nav-item บน mobile → auto-close sidebar
- ESC key ปิด sidebar (เพิ่มใน initGlobalModalUX หรือเฉพาะ)

### 3.2 Context Create Form — Existing State

**Modal HTML** ([app.html:684-726](../../legacy-frontend/app.html#L684)):
- `#ctx-input-title` — text input (required field)
- `#ctx-input-content` — textarea
- `#ctx-input-type` — select (default value: conversation, never empty)
- `#ctx-input-tags` — text input (optional)
- `#ctx-input-pinned` — checkbox

**ปัญหา inline styles:** ทุก input มี `style="...border: 1px solid var(--border)..."` inline → CSS class จะ override ยากต้องใช้ `!important`

**Save handler** ([app.js:3723-3763](../../legacy-frontend/app.js#L3723) `saveCtxModal`):
```js
if (!title) {
 showToast('กรุณาใส่ชื่อ Context', 'error');
 return;
}
```
- ตรวจแค่ title ว่าง → toast แต่ไม่ highlight ช่อง

**Required fields ตาม spec:**
- title — required
- content — แม้ว่า backend อาจรับ empty (TODO: confirm) — เพื่อ UX จะ require ด้วย

**ที่ต้องเพิ่ม:**
- `.is-invalid` class ใน shared.css (because the modal uses .form-input เพียงบางส่วน + inline styles เยอะ → ใช้ generic `.is-invalid` selector ทั่วไป)
- Validate function ใน saveCtxModal — focus ช่องแรกที่ว่าง + add `.is-invalid`
- Clear `.is-invalid` ตอน user พิมพ์ในช่องนั้น (input event)

### 3.3 Z-index Hierarchy — Existing State

**สำรวจปัจจุบัน:**
| Element | Selector | z-index | File |
|---|---|---|---|
| `.modal-overlay` | shared modal backdrop | **100** | shared.css:225 |
| `.file-detail-panel` | slide panel | 200 | styles.css:2071 |
| `.fd-backdrop` | file detail backdrop | 199 | styles.css:2210 |
| `.pack-modal-overlay` | pack create modal | 200 | styles.css:2079 |
| `.dup-modal-overlay` (early) | dup modal | 300 | styles.css:2234 |
| `.dup-modal-overlay` (later) | overrides | **9999** | styles.css:3451 |
| `.upgrade-modal-overlay` | upgrade CTA | 10000 | styles.css:2961 |
| `.loading-overlay` | full-screen loader | 10000 | styles.css:1322 |
| `.guide-fab` | guide FAB | **9998** | styles.css:2705 |
| `.guide-overlay` | guide backdrop | **9999** | styles.css:2717 |
| `.guide-drawer` | guide panel | **10000** | styles.css:2722 |
| `#toast-container` | toasts | **10000** | shared.css:320 (v7.2.0) |

**Conflict (user confirmed):**
- `.modal-overlay` = 100 ≪ `.guide-drawer` = 10000 → modal โดนทับเมื่อ guide drawer เปิด

**New scheme (proposed):**
| Layer | z-index | Notes |
|---|---|---|
| Page content | 1–200 | leave alone |
| Sidebar (mobile) | 9800 | only on `<768px`; below guide |
| Sidebar backdrop (mobile) | 9700 | |
| Sidebar toggle button | 9700 | |
| Guide FAB | 9998 | leave |
| Guide overlay | 9999 | leave |
| Guide drawer | 10000 | leave |
| **Modal overlays** | **10500** | bumped — above guide |
| **Loading overlay** | **10800** | bumped — covers modal during save |
| **Toast container** | **11000** | bumped — always visible (errors during loading) |

**Trade-off:** sidebar (mobile) ที่ 9800 = guide drawer (10000) ทับ sidebar เมื่อทั้งคู่เปิด — acceptable เพราะ user ไม่ค่อยเปิดทั้งคู่พร้อมกัน

---

## 📁 Files to Create / Modify

### Frontend
- [ ] [`legacy-frontend/app.html`](../../legacy-frontend/app.html) (modify)
  - เพิ่ม `<button id="sidebar-toggle">` หลัง `<div id="app">` open tag
  - เพิ่ม `<div id="sidebar-backdrop">`
- [ ] [`legacy-frontend/styles.css`](../../legacy-frontend/styles.css) (modify)
  - **Section 1 (mobile):** new `.sidebar-toggle`, `.sidebar-backdrop`, `@media (max-width: 768px)` rules
  - **Section 3 (z-index):** bump `.upgrade-modal-overlay`, `.loading-overlay`, late `.dup-modal-overlay`
- [ ] [`legacy-frontend/shared.css`](../../legacy-frontend/shared.css) (modify)
  - **Section 3 (z-index):** bump `.modal-overlay` 100 → 10500; bump `#toast-container` 10000 → 11000
  - **Section 2 (validation):** new `.is-invalid` rule (`!important` because inline styles)
  - new media query for `@media (max-width: 768px) { .modal { width: 92vw } }`
- [ ] [`legacy-frontend/app.js`](../../legacy-frontend/app.js) (modify)
  - **Section 1:** new `initSidebarMobile()` — wire toggle button, backdrop, nav-item auto-close
  - **Section 2:** modify `saveCtxModal()` — validate + add `.is-invalid` + focus first empty field
  - **Section 2:** wire `input` event on title/content to clear `.is-invalid` on user typing

### Tests (สำหรับฟ้า + เขียวเขียนเอง)
- [ ] [`tests/e2e-ui/v7.3.0-edgecases.spec.js`](../../tests/e2e-ui/v7.3.0-edgecases.spec.js) (**create**) — 12+ tests:
  - **Section 1** (4 tests): mobile viewport sidebar hidden by default; hamburger reveals sidebar; backdrop click closes; nav-item click closes sidebar on mobile
  - **Section 2** (4 tests): empty title shows .is-invalid; empty content shows .is-invalid; first empty field receives focus; typing clears .is-invalid
  - **Section 3** (3-4 tests): modal-overlay computed z-index > guide-drawer; loading-overlay > modal-overlay; toast-container > everything; opening modal while guide drawer is open → modal visible above

### Memory updates
- [ ] [`.agent-memory/current/pipeline-state.md`](../current/pipeline-state.md) — เพิ่ม v7.3.0 section
- [ ] [`.agent-memory/project/decisions.md`](../project/decisions.md) — เพิ่ม UX-002 (z-index hierarchy)

---

## 🔧 Implementation Plan — 3 sections

---

### Section 1: Mobile Responsive + Hamburger

**1A — `app.html` ([line 121](../../legacy-frontend/app.html#L121) — inside `#app` opening)**

```html
<div id="app" class="app-container hidden">
 <!-- v7.3.0 — Mobile sidebar toggle (hidden on desktop via CSS) -->
 <button id="sidebar-toggle" class="sidebar-toggle" aria-label="Menu" aria-expanded="false">
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
   <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
 </button>
 <div id="sidebar-backdrop" class="sidebar-backdrop"></div>
 <aside class="sidebar" id="sidebar">
  ...
```

**1B — `styles.css` (append in app shell area, near `.sidebar`)**

```css
/* v7.3.0 — Mobile sidebar toggle (hamburger) */
.sidebar-toggle {
  display: none;  /* desktop: hidden */
  position: fixed;
  top: 12px;
  left: 12px;
  z-index: 9700;
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  background: var(--surface-2);
  border: 1px solid var(--border);
  color: var(--text-primary);
  border-radius: 10px;
  cursor: pointer;
  transition: background 0.15s;
}
.sidebar-toggle:hover { background: var(--surface-3); }

.sidebar-backdrop {
  display: none;
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.55);
  z-index: 9700;
  animation: fadeIn 0.2s ease;
}

@media (max-width: 768px) {
  .sidebar-toggle { display: inline-flex; }
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 9800;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
  }
  .app-container.sidebar-open .sidebar {
    transform: translateX(0);
  }
  .app-container.sidebar-open .sidebar-backdrop {
    display: block;
  }
  .main-content {
    padding: 60px 16px 16px;  /* top space for the hamburger */
  }
}
```

**1C — `shared.css` (add inside existing modal section)**

```css
@media (max-width: 768px) {
  .modal {
    width: 92vw;
    max-height: 88vh;
  }
}
```

**1D — `app.js` (new function `initSidebarMobile()`)**

```js
function initSidebarMobile() {
 const toggle = document.getElementById('sidebar-toggle');
 const backdrop = document.getElementById('sidebar-backdrop');
 const container = document.querySelector('.app-container');
 if (!toggle || !backdrop || !container) return;

 const open = () => {
  container.classList.add('sidebar-open');
  toggle.setAttribute('aria-expanded', 'true');
 };
 const close = () => {
  container.classList.remove('sidebar-open');
  toggle.setAttribute('aria-expanded', 'false');
 };
 const isOpen = () => container.classList.contains('sidebar-open');

 toggle.addEventListener('click', () => isOpen() ? close() : open());
 backdrop.addEventListener('click', close);

 // Close after navigating on mobile so the user sees the new page
 document.querySelectorAll('.nav-item[data-page]').forEach(link => {
  link.addEventListener('click', () => {
   if (window.innerWidth <= 768) close();
  });
 });

 // ESC also closes the sidebar (parallel with the modal ESC handler)
 document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && isOpen()) close();
 });
}
```

เรียกใน DOMContentLoaded หลัง `initGlobalModalUX()` ใน `if (document.getElementById('app'))` block.

**Acceptance:**
- [ ] Desktop (>768px): sidebar visible, hamburger hidden
- [ ] Mobile (≤768px): sidebar hidden by default, hamburger visible top-left
- [ ] กด hamburger → sidebar slide-in from left + backdrop visible
- [ ] กด backdrop → sidebar close
- [ ] กด nav item ตอน sidebar เปิด → sidebar close + nav switch
- [ ] กด ESC ตอน sidebar เปิด → close
- [ ] resize window from mobile to desktop ตอน sidebar เปิด → ยังเห็น sidebar ปกติ (CSS naturally adapts)

---

### Section 2: Form Validation UX (ctx-modal)

**2A — `shared.css` (new rule, near .form-input)**

```css
/* v7.3.0 — Invalid field highlight (use !important to override inline styles) */
.is-invalid,
input.is-invalid,
textarea.is-invalid {
  border-color: var(--error) !important;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.15) !important;
}
```

**2B — `app.js` modify `saveCtxModal()` ([app.js:3723](../../legacy-frontend/app.js#L3723))**

```js
async function saveCtxModal() {
 const editId = document.getElementById('ctx-edit-id').value;
 const titleEl = document.getElementById('ctx-input-title');
 const contentEl = document.getElementById('ctx-input-content');
 const title = titleEl.value.trim();
 const content = contentEl.value.trim();
 const ctxType = document.getElementById('ctx-input-type').value;
 const tagsStr = document.getElementById('ctx-input-tags').value;
 const isPinned = document.getElementById('ctx-input-pinned').checked;
 const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

 // v7.3.0 — clear any previous invalid state
 titleEl.classList.remove('is-invalid');
 contentEl.classList.remove('is-invalid');

 // v7.3.0 — validate required fields; mark + focus first empty
 const isTH = getLang() === 'th';
 if (!title) {
  titleEl.classList.add('is-invalid');
  titleEl.focus();
  showToast(isTH ? 'กรุณาใส่ชื่อ Context' : 'Please enter a context title', 'error');
  return;
 }
 if (!content) {
  contentEl.classList.add('is-invalid');
  contentEl.focus();
  showToast(isTH ? 'กรุณาใส่เนื้อหา Context' : 'Please enter context content', 'error');
  return;
 }

 try {
  // ... existing save logic unchanged ...
 }
}
```

**2C — wire input listeners (in DOMContentLoaded for ctx-modal)**

In the existing block at app.js:3799–3815, add:
```js
// v7.3.0 — clear .is-invalid as user starts typing in the field
['ctx-input-title', 'ctx-input-content'].forEach(id => {
 document.getElementById(id)?.addEventListener('input', (e) => {
  e.target.classList.remove('is-invalid');
 });
});
```

**Acceptance:**
- [ ] Empty title → save → title border red + focus + toast
- [ ] Title filled, empty content → save → content border red + focus + toast
- [ ] Both filled → save → success
- [ ] User types in red field → border returns normal
- [ ] Reopen modal → no leftover .is-invalid from previous attempt

---

### Section 3: Z-index Conflict Fix

**3A — `shared.css`** (modify modal-overlay + toast-container)

```css
.modal-overlay {
  /* ... existing rules ... */
  z-index: 10500;  /* was 100 — now sits above guide-drawer (10000) */
}

#toast-container {
  /* ... */
  z-index: 11000;  /* was 10000 — always above modals + loading */
}
```

**3B — `styles.css`** (modify upgrade-modal-overlay, loading-overlay, dup-modal-overlay)

```css
.upgrade-modal-overlay { /* ... */ z-index: 10500; /* was 10000 */ }
.loading-overlay { /* ... */ z-index: 10800; /* was 10000 */ }
.dup-modal-overlay { /* ... */ z-index: 10500; /* was 9999 */ }
.pack-modal-overlay { /* ... */ z-index: 10500; /* was 200 */ }
```

**Acceptance:**
- [ ] Open guide drawer → open profile modal → profile modal visible **above** drawer
- [ ] Open profile → click save → loading overlay visible **above** modal
- [ ] During loading, error fires → toast visible **above** loading overlay
- [ ] No regression: clicking outside modal still closes it (z-index doesn't break event delegation)

---

## 🧪 Test Plan

### New tests — `tests/e2e-ui/v7.3.0-edgecases.spec.js`

```js
test.describe("v7.3.0 / 1. Mobile responsive", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("sidebar hidden by default on mobile", async ({ page }) => { /* ... */ });
  test("hamburger button reveals sidebar", async ({ page }) => { /* ... */ });
  test("backdrop click closes sidebar", async ({ page }) => { /* ... */ });
  test("clicking nav item closes sidebar after navigation", async ({ page }) => { /* ... */ });
  test("modal width fits 92vw on mobile", async ({ page }) => { /* ... */ });
});

test.describe("v7.3.0 / 1. Mobile vs desktop", () => {
  test("desktop hides hamburger", async ({ page }) => {
    // page default 1366x768 — hamburger should not be visible
  });
});

test.describe("v7.3.0 / 2. Context form validation", () => {
  test("empty title marks input invalid + focuses it", async ({ page }) => { /* ... */ });
  test("empty content marks textarea invalid + focuses it", async ({ page }) => { /* ... */ });
  test("typing in invalid field clears the .is-invalid class", async ({ page }) => { /* ... */ });
  test("filling both saves successfully", async ({ page }) => { /* ... */ });
});

test.describe("v7.3.0 / 3. Z-index hierarchy", () => {
  test("modal-overlay computed z-index > 10000", async ({ page }) => { /* ... */ });
  test("toast-container computed z-index > modal-overlay", async ({ page }) => { /* ... */ });
  test("opening modal while guide is open → modal visible", async ({ page }) => { /* ... */ });
});
```

### Regression — ห้ามพังของเดิม
- รัน full suite: phase0-baseline + thorough-pages + thorough-console + thorough-flows + thorough-mobile + phase5-split-html + v7.2.0-uxhotfix
- คาด: 89 + 12 + 12-15 = ~110+ tests pass 100%

### Manual smoke (สำคัญ — user ขอ)
1. **Desktop browser (1366x768):**
   - Sidebar เห็นปกติ ไม่มี hamburger
   - Modal เปิดปกติ
   - Guide drawer เปิดได้, modal ทับด้านบน
2. **Mobile DevTools (iPhone 12 — 390x844):**
   - Sidebar ซ่อน hamburger เห็น
   - กด hamburger → sidebar slide-in
   - กด nav item → sidebar close + page switch
   - Modal กว้าง 92vw พอดีจอ
3. **Tablet (768x1024 borderline):**
   - ที่ exactly 768px → sidebar ยัง show desktop layout (>768 = desktop)
   - ที่ 767 → mobile layout
4. **Form validation:**
   - กด btn-new-context → modal เปิด
   - กด save ทันที → title แดง + focus
   - พิมพ์ title → save → content แดง + focus
   - พิมพ์ทั้งคู่ → save success → modal close

---

## ⚠️ Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | Inline styles ใน ctx-modal override `.is-invalid` | High | ใช้ `!important` (acceptable trade-off) |
| 2 | Sidebar transform animation lag บน low-end mobile | Low | `transition: transform 0.3s cubic-bezier` แค่ transform → cheap on GPU |
| 3 | `nav-item` click handler stack mismatch (existing handler + new mobile close) | Medium | new listener call `close()` ก่อน เก่ารัน `e.preventDefault()` + `switchPage()` — ทำงานเสริมกัน |
| 4 | Bumping z-index = 11000 ของ toast อาจดันสูงเกิน fly.io แสดง warning bar | Low | fly.io banners อยู่นอก app container ไม่กระทบ |
| 5 | Sidebar fixed position บน mobile กิน sidebar height = viewport — sidebar-stats อาจล้น | Medium | sidebar-nav has `overflow-y: auto` — already handles overflow |
| 6 | DOMContentLoaded handler v7.3 init ทำงานก่อน sidebar exist (เช่น app.html ไม่มี #app) | Low | wrapped ใน `if (document.getElementById('app'))` already |
| 7 | resize from mobile → desktop ตอน sidebar-open class ติดอยู่ | Low | desktop CSS ไม่ดู `.sidebar-open` — sidebar render ปกติ; `.sidebar-open` is dead class |
| 8 | guide-drawer (z 10000) + modal (z 10500) ซ้อน — guide overlay click อาจ fire ก่อน modal close | Low | guide overlay click is on guide-overlay element only (matches selector) — does not bubble to modal |

---

## 🚫 Out of Scope

- Sidebar swipe gestures (touch swipe to open/close) — requires touch event handling
- Resizable modal width on desktop
- Dark/light theme switch (modal width same regardless)
- Tablet portrait optimizations (768–900px) — only one breakpoint at 768px
- File detail panel mobile responsive — defer (low priority, panel slides in from right OK on mobile already)
- Profile modal scroll-snap improvement
- Hamburger animation (turning into X) — visual polish

---

## 📋 Checklist for เขียว (Implementation order)

ทำตามลำดับ ความเสี่ยงต่ำ → สูง:

### Phase A — เตรียม (~10 นาที)
- [ ] Verify baseline 89 tests + v7.2.0 12 tests pass
- [ ] สร้าง `tests/e2e-ui/v7.3.0-edgecases.spec.js` skeleton

### Phase B — Section 3: Z-index Fix (~15 นาที — ต่ำสุด)
- [ ] Bump `.modal-overlay` z-index ใน shared.css
- [ ] Bump `#toast-container` ใน shared.css
- [ ] Bump `.upgrade-modal-overlay`, `.loading-overlay`, `.dup-modal-overlay`, `.pack-modal-overlay` ใน styles.css
- [ ] Write 3 tests Section 3 (computed z-index check)
- [ ] Run full regression → ผ่าน
- [ ] Manual: เปิดคู่มือ → เปิด profile → modal อยู่บน

### Phase C — Section 2: Form Validation (~30 นาที)
- [ ] Add `.is-invalid` rule to shared.css
- [ ] Modify `saveCtxModal()` in app.js
- [ ] Add input listeners to clear `.is-invalid`
- [ ] Write 4 tests Section 2
- [ ] Run regression → ผ่าน
- [ ] Manual: กด save modal ว่าง → แดง + focus

### Phase D — Section 1: Mobile + Hamburger (~60 นาที — สูงสุด)
- [ ] Add `<button id="sidebar-toggle">` + `<div id="sidebar-backdrop">` to app.html
- [ ] Add CSS: .sidebar-toggle, .sidebar-backdrop, @media (max-width: 768px) rules
- [ ] Add @media modal { width: 92vw } in shared.css
- [ ] Write `initSidebarMobile()` in app.js
- [ ] Wire init in DOMContentLoaded
- [ ] Write 5+ tests Section 1
- [ ] Run regression → ผ่าน
- [ ] **Manual on real mobile DevTools** (iPhone, Android viewports)

### Phase E — Wrap up
- [ ] Full suite: 89 + 12 + 12-15 ≈ 113-116 tests pass 100%
- [ ] อัปเดต `pipeline-state.md` → state `done`
- [ ] Commit เดียว: `feat(ux): v7.3.0 edge-cases + mobile fixes`
- [ ] Push → Fly auto-deploy

---

## ✅ Done Criteria

- [ ] 3 sections implement ครบ
- [ ] 12-15 tests ใหม่ + 113 เดิม = ~125 tests ผ่าน 100%
- [ ] Manual smoke ผ่านทั้ง desktop + mobile (375x667) + tablet (768x1024)
- [ ] No new console errors
- [ ] z-index hierarchy verified ใน DevTools
- [ ] Memory updates ครบ
- [ ] Commit + push + deploy verified
