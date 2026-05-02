# Plan: SaaS Responsive Design & Mobile UX — v7.4.0

**Author:** แดง (Daeng)
**Date:** 2026-05-02
**Status:** `plan_pending_approval` (user authorize full dev mode → จะ build ต่อหลัง plan ส่ง)
**Estimated effort:** เขียว ~3-4 ชม. + ฟ้า ~1.5 ชม.
**Target version:** **v7.4.0** (ไม่ใช่ v7.3.0 — v7.3.0 ship แล้ว commit `62968c6`)
**Priority:** 🟡 High — Mobile usability + SaaS UX standards 2025
**Foundation:** ต่อยอดจาก v7.3.0 (mobile sidebar + form validation + z-index)

---

## 🎯 Goal

ทำให้แอปบนมือถือใช้งาน "เหมือน SaaS ปี 2025" จริงๆ — ไม่ใช่แค่ย่อ desktop ลงมา ตามหลักการ:

- **Touch ergonomics** (Apple HIG + Material Design 3): ทุก tap target ≥ 44×44px
- **Progressive disclosure**: ข้อมูลรองซ่อนใน kebab menu/expand
- **Table-to-Card transformation**: แถวยาวบน desktop → กล่องการ์ดเรียงแนวตั้งบน mobile
- **Floating Action Button** (Material Design): ปุ่ม primary action ลอยมุมขวาล่าง — กดด้วยนิ้วโป้งง่าย

**ผู้ใช้:**
- คนใช้แอปบนมือถือเป็นหลัก (~30-40% ของ traffic ตามสถิติ SaaS ทั่วไป)
- คนหนึ่งมือถือนิ้วโป้ง (เอื้อมไม่ถึงปุ่ม top-right)
- คนเห็นรายการไฟล์/contexts ยาวๆ บนจอ 375px แล้วต้อง scroll horizontal

**ทำเสร็จแล้วได้อะไร:**
1. Tap accuracy ดีขึ้น (มือใหญ่ก็กดถูก) — ลด rage clicks
2. Primary actions เอื้อมถึงด้วยนิ้วโป้ง — workflow ลื่นขึ้น
3. รายการ readable บน mobile — ไม่ต้อง scroll horizontal

---

## ⚠️ Note: 2 ใน 4 sections ที่ user ขอ ทำใน v7.3.0 แล้ว

User prompt ขอ 4 sections — แต่ 2 ตัวทำเสร็จและ ship ไปแล้ว (commit `62968c6`):

| User asked | สถานะ |
|---|---|
| 1. Sidebar Hamburger + off-canvas | ✅ **Done** ใน v7.3.0 |
| 2. Touch 44px + FAB | ❌ ยังไม่ทำ — **v7.4.0 Section A+B** |
| 3. Table → Card View + Kebab | ❌ ยังไม่ทำ — **v7.4.0 Section C+D** |
| 4. Validation `.is-invalid` + Modal z-index | ✅ **Done** ใน v7.3.0 |

→ v7.4.0 scope = Touch + FAB + Card view (Section A-D) เท่านั้น

---

## 📚 Context (Deep Investigation)

### Touch Targets — Current State

ทุกปุ่มและ input ปัจจุบัน:
| Element | Current size | 44px? |
|---|---|---|
| `.btn` ([shared.css:102](../../legacy-frontend/shared.css#L102)) | padding 8/16, font 13 → ~32px | ❌ |
| `.btn-sm` ([shared.css:134](../../legacy-frontend/shared.css#L134)) | padding 5/10, font 11 → ~22px | ❌ |
| `.btn-lg` | padding 14/28, font 15 → ~46px | ✅ |
| `.btn-close` | padding 4 → ~26px | ❌ |
| `.btn-icon` | (similar to btn-close) | ❌ |
| `.form-input` | padding 10/12, font 14 → ~36px | ❌ |
| ctx-modal inputs (inline) | padding 10 → ~36px | ❌ |
| `.nav-item` | padding ~7px → ~32px | ❌ |

→ Almost everything fails 44px on mobile. Need `@media (max-width: 768px)` rules to bump.

### File List — Current State

`renderFileList()` ([app.js:1341](../../legacy-frontend/app.js#L1341)) creates `.file-item` rows:
```html
<div class="file-item" onclick="openFileDetail(...)">
  <div class="file-icon">PDF</div>           <!-- 32×32 -->
  <div class="file-info">
    <div class="file-name">filename.pdf</div>
    <div class="file-meta">12,345 chars · status · badges · storage</div>
    <div class="file-tags">...</div>
  </div>
  <div class="file-actions">
    <button class="btn-sm" onclick="deleteFile(...)">Delete</button>
  </div>
</div>
```

CSS: `display: flex; align-items: center` ([styles.css:409](../../legacy-frontend/styles.css#L409)) — horizontal row.

**Issue on mobile:**
- 32px icon + flex 1 file-info (truncated nowrap) + delete button → file-name gets squeezed
- Tags wrap to multiple lines but compete with file-name space
- Delete button visible but small (btn-sm = 22px tall)

**Mobile design (Card):**
```
┌─────────────────────────────────────┐
│  [PDF]  filename.pdf            [⋮] │  ← icon + name + kebab
│         12,345 chars · ●ready       │  ← meta on its own row
│         ☁️ On your Drive            │  ← storage badge
│         [tag1] [tag2] [tag3]        │  ← tags
└─────────────────────────────────────┘
```

Kebab dropdown actions:
- Open detail (default — same as click on the card except where the kebab handles it)
- Delete

### Context Memory Cards — Current State

`.ctx-card` already a card layout ([styles.css:2633](../../legacy-frontend/styles.css#L2633)) with `display: flex; flex-direction: column`.

**Issue:** `.ctx-card-actions` is `display: none` by default and `display: flex` on `:hover` ([styles.css:2716-2729](../../legacy-frontend/styles.css#L2716)). On touch devices, `:hover` doesn't fire reliably — actions invisible.

`_renderCtxCard()` produces `.ctx-card-actions` with 3 buttons (edit, pin, delete).

**Mobile design:** Replace hover-only with kebab menu visible on mobile + on hover on desktop (current behavior preserved).

### FAB — Existing Patterns

The codebase has 1 FAB already: `.guide-fab` ([styles.css:2757](../../legacy-frontend/styles.css#L2757)) at z-9998 bottom-right. Pattern:
- `position: fixed; bottom: 24px; right: 24px`
- gradient background
- shadow

For per-page FABs, we need to:
- Position differently (above guide-fab — guide-fab is global; page FAB is contextual)
- Visible only on mobile (`@media`)
- Hide existing in-flow buttons on mobile

**Layout idea:**
- guide-fab: bottom-right, z 9998
- page primary FAB (e.g. "+" for upload, "+" for new context): bottom-right but ABOVE guide-fab? Or left side?

Decision: page FAB at **bottom-LEFT** (out of conflict with guide-fab on right). Or single FAB at bottom-right that swaps icon based on current page. Going with **bottom-left** — simpler, no conflict.

Actually re-reading user spec: "ปุ่มลอย ไว้ที่มุมขวาล่าง" — user wants right side. Need to coexist with guide-fab.

Option: stack vertically — page FAB above guide-fab.
```
        bottom: 88px  ← page FAB ("+")
        bottom: 24px  ← guide-fab ("คู่มือ")
```

That works. Both right-aligned, page FAB sits above guide-fab.

---

## 📁 Files to Create / Modify

### Frontend
- [ ] [`legacy-frontend/shared.css`](../../legacy-frontend/shared.css) (modify)
  - **Section A:** `@media (max-width: 768px)` — bump `.btn`, `.btn-sm`, `.form-input`, `.btn-close` to min-height 44px
- [ ] [`legacy-frontend/styles.css`](../../legacy-frontend/styles.css) (modify)
  - **Section A:** ctx-modal inline-styled inputs → use class instead of inline style (refactor)
  - **Section B:** new `.page-fab` class + per-page positioning
  - **Section C:** mobile `.file-item` → card layout
  - **Section D:** mobile `.ctx-card-actions` → always visible (override hover-only)
  - **Section C/D:** new `.kebab-btn`, `.kebab-menu`, `.kebab-menu-item` styles
- [ ] [`legacy-frontend/app.html`](../../legacy-frontend/app.html) (modify)
  - **Section B:** add `<button class="page-fab page-fab-data">+</button>` inside `#page-my-data` and `<button class="page-fab page-fab-ctx">+</button>` inside `#page-context-memory`
- [ ] [`legacy-frontend/app.js`](../../legacy-frontend/app.js) (modify)
  - **Section B:** wire FAB click → trigger same action as their desktop equivalents (organize-new for my-data, btn-new-context for context-memory)
  - **Section C:** modify `renderFileList()` — emit kebab button instead of inline delete on mobile (but works on desktop too)
  - **Section D:** modify `_renderCtxCard()` — emit kebab dropdown
  - **Section C/D:** new global `initKebabMenus()` — delegated click handler + close-on-outside-click + close-on-ESC

### Tests (เขียวเขียนเอง + ฟ้า extend)
- [ ] [`tests/e2e-ui/v7.4.0-saas-responsive.spec.js`](../../tests/e2e-ui/v7.4.0-saas-responsive.spec.js) (**create**) — 14+ tests:
  - **Section A** (3 tests): btn min-height ≥44 on mobile, form-input min-height ≥44, btn-close min-height ≥44
  - **Section B** (3 tests): FAB visible on mobile not desktop, FAB click triggers action, FAB stacks above guide-fab
  - **Section C** (4 tests): file-item is card layout on mobile, kebab button visible, kebab dropdown open/close, kebab delete action works
  - **Section D** (4 tests): ctx-card kebab visible on mobile (not hover-only), kebab edit/pin/delete actions work
- [ ] เพิ่ม **backend pytest run** ใน regression — `python -m pytest tests/test_production.py -v`
- [ ] รัน full Playwright suite (~117 tests รวม v7.4.0)

### Memory updates
- [ ] [`.agent-memory/current/pipeline-state.md`](../current/pipeline-state.md) — เพิ่ม v7.4.0 section
- [ ] [`.agent-memory/project/decisions.md`](../project/decisions.md) — เพิ่ม UX-003 (touch 44px policy + kebab pattern)

---

## 🔧 Implementation Plan — 4 sections

---

### Section A: Touch Targets 44px (mobile only)

**A1 — `shared.css` append after existing `.modal` mobile rule**

```css
/* v7.4.0 — Touch ergonomics: WCAG/Apple HIG ≥44×44px on phones. */
@media (max-width: 768px) {
  .btn,
  .btn-primary,
  .btn-outline,
  .btn-danger,
  .btn-ghost,
  .btn-glass {
    min-height: 44px;
    padding: 10px 18px;
    font-size: 14px;
  }
  .btn-sm {
    min-height: 38px;       /* secondary actions slightly smaller — but still finger-friendly */
    padding: 8px 14px;
    font-size: 12px;
  }
  .btn-close,
  .btn-icon {
    min-width: 44px;
    min-height: 44px;
  }
  .form-input,
  textarea.form-input {
    min-height: 44px;
    padding: 12px 14px;
    font-size: 14px;
  }
}
```

**A2 — `styles.css` for ctx-modal inline inputs**

The ctx-modal inputs use inline `style="padding:10px"` — these inherit nothing from `.form-input`. Two options:
1. Refactor to add `.form-input` class to each input (recommended — cleaner)
2. Override via `@media` with high specificity

Going with **option 1** — modify app.html to add class:
- `<input id="ctx-input-title" class="form-input">` (drop inline style)
- `<textarea id="ctx-input-content" class="form-input">` (drop inline style)
- `<select id="ctx-input-type" class="form-input">` (drop inline style)
- `<input id="ctx-input-tags" class="form-input">` (drop inline style)

This way the @media rule from A1 applies cleanly.

**Acceptance:**
- [ ] DevTools mobile (375x667): btn computed min-height ≥ 44px
- [ ] form-input on ctx-modal min-height ≥ 44px (after class refactor)
- [ ] No regression on desktop (rules are inside @media)

---

### Section B: Floating Action Button (FAB) Pattern

**B1 — `app.html` add page FABs**

Inside `#page-my-data` (after upload zone), add:
```html
<!-- v7.4.0 — Mobile FAB for primary action (organize new files) -->
<button id="fab-my-data" class="page-fab" aria-label="จัดระเบียบไฟล์ใหม่">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/>
  </svg>
</button>
```

Inside `#page-context-memory` (after ctx-grid), add:
```html
<!-- v7.4.0 — Mobile FAB for primary action (new context) -->
<button id="fab-ctx" class="page-fab" aria-label="สร้าง Context">
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
    <path d="M12 5v14M5 12h14"/>
  </svg>
</button>
```

**B2 — `styles.css` FAB style**

```css
/* v7.4.0 — Page primary FAB (mobile only). Stacks above the guide FAB. */
.page-fab {
  display: none; /* hidden on desktop */
  position: fixed;
  bottom: 88px; /* sits above .guide-fab (24px + 56px height + 8px gap) */
  right: 20px;
  z-index: 9700;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: var(--accent);
  color: white;
  border: none;
  cursor: pointer;
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
  align-items: center;
  justify-content: center;
  transition: transform 0.15s, box-shadow 0.15s;
}
.page-fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 28px rgba(99, 102, 241, 0.5);
}
.page-fab:active { transform: scale(0.96); }

@media (max-width: 768px) {
  /* Show FAB on the active page only (parent .page must have .active class) */
  .page.active .page-fab { display: inline-flex; }

  /* Hide the in-flow primary action when FAB is taking over its job */
  .page.active #btn-organize-new,
  .page.active #btn-new-context { display: none; }
}
```

Note: organize-all + upload-zone stay visible — too critical to hide. Only the duplicate primary action gets replaced by FAB.

**B3 — `app.js` wire FAB clicks**

```js
function initPageFABs() {
 // FAB in My Data → trigger Organize New
 document.getElementById('fab-my-data')?.addEventListener('click', () => {
  document.getElementById('btn-organize-new')?.click();
 });
 // FAB in Context Memory → trigger New Context
 document.getElementById('fab-ctx')?.addEventListener('click', () => {
  document.getElementById('btn-new-context')?.click();
 });
}
```

Call in DOMContentLoaded inside `if (document.getElementById('app'))`.

**Acceptance:**
- [ ] Mobile (375x667): FAB visible on my-data page, hidden on knowledge/graph/chat pages
- [ ] Mobile: tap FAB → triggers same handler as desktop button
- [ ] Desktop (1366x768): FAB hidden, original buttons visible
- [ ] FAB sits above guide-fab — no overlap

---

### Section C: File List Card View + Kebab Menu

**C1 — `styles.css` mobile card layout for file-item**

```css
/* v7.4.0 — Mobile card layout: stacked card instead of horizontal row. */
@media (max-width: 768px) {
  .file-item {
    flex-direction: column;
    align-items: stretch;
    padding: 14px 16px;
    gap: 10px;
    position: relative;
  }
  .file-item .file-icon {
    width: 44px;
    height: 44px;
    align-self: flex-start;
  }
  .file-item .file-info {
    width: 100%;
  }
  .file-item .file-name {
    white-space: normal;        /* allow wrapping on cards */
    font-size: 15px;
    line-height: 1.35;
  }
  .file-item .file-meta {
    flex-wrap: wrap;
    font-size: 12px;
  }
  .file-item .file-actions {
    position: absolute;
    top: 14px;
    right: 14px;
  }
}
```

**C2 — Modify `renderFileList()` to use kebab on mobile**

The action button stays as `.btn-sm` Delete on desktop; on mobile, it should be a kebab dropdown.

Cleanest: render BOTH structures and let CSS show/hide based on viewport:
```js
return `
 <div class="file-item${lockedClass}" data-id="${f.id}" onclick="openFileDetail('${f.id}')">
  <div class="file-icon ${f.filetype}">${f.filetype.toUpperCase()}${locked}</div>
  <div class="file-info">...</div>
  <div class="file-actions">
   <!-- Desktop: visible delete button -->
   <button class="btn-sm file-action-desktop" onclick="event.stopPropagation(); deleteFile('${f.id}')">${t('myData.delete')}</button>
   <!-- Mobile: kebab dropdown -->
   <button class="kebab-btn file-action-mobile" onclick="event.stopPropagation(); toggleKebab(event, 'file-${f.id}')" aria-label="More actions">⋮</button>
   <div class="kebab-menu hidden" id="kebab-file-${f.id}">
    <button class="kebab-menu-item" onclick="event.stopPropagation(); deleteFile('${f.id}')">${t('myData.delete')}</button>
   </div>
  </div>
 </div>`;
```

CSS:
```css
.file-action-mobile, .file-action-desktop { /* defaults */ }
@media (min-width: 769px) {
  .file-action-mobile { display: none; }
}
@media (max-width: 768px) {
  .file-action-desktop { display: none; }
}
```

**C3 — Generic Kebab styles (in shared.css)**

```css
/* v7.4.0 — Kebab menu (3-dots dropdown) used on file-list and ctx-card cards */
.kebab-btn {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: transparent;
  border: 1px solid transparent;
  color: var(--text-secondary);
  font-size: 18px;
  line-height: 1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s;
}
.kebab-btn:hover { background: var(--surface-2); color: var(--text-primary); }

@media (max-width: 768px) {
  .kebab-btn { min-width: 44px; min-height: 44px; }
}

.kebab-menu {
  position: absolute;
  top: 100%;
  right: 0;
  min-width: 160px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 10px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  padding: 4px;
  z-index: 1500;
  animation: fadeIn 0.15s ease;
}
.kebab-menu.hidden { display: none; }

.kebab-menu-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 10px 12px;
  font-size: 13px;
  color: var(--text-primary);
  background: none;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.kebab-menu-item:hover { background: var(--surface-2); }
.kebab-menu-item.danger { color: var(--error); }
@media (max-width: 768px) {
  .kebab-menu-item { min-height: 44px; font-size: 15px; }
}
```

**C4 — `app.js` global `initKebabMenus()` + `toggleKebab()`**

```js
let _openKebabId = null;

function toggleKebab(event, id) {
 event?.stopPropagation();
 const menu = document.getElementById(`kebab-${id}`);
 if (!menu) return;
 // Close any other open kebab
 if (_openKebabId && _openKebabId !== id) {
  document.getElementById(`kebab-${_openKebabId}`)?.classList.add('hidden');
 }
 menu.classList.toggle('hidden');
 _openKebabId = menu.classList.contains('hidden') ? null : id;
}

function initKebabMenus() {
 // Click outside any open kebab → close
 document.addEventListener('click', () => {
  if (!_openKebabId) return;
  const open = document.getElementById(`kebab-${_openKebabId}`);
  if (!open || open.classList.contains('hidden')) { _openKebabId = null; return; }
  open.classList.add('hidden');
  _openKebabId = null;
 });
 // ESC closes
 document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && _openKebabId) {
   document.getElementById(`kebab-${_openKebabId}`)?.classList.add('hidden');
   _openKebabId = null;
  }
 });
}
```

Call `initKebabMenus()` in DOMContentLoaded inside `if (document.getElementById('app'))`.

**Acceptance:**
- [ ] Mobile: file-item displays as card (vertical layout)
- [ ] Mobile: kebab button (⋮) visible top-right of card
- [ ] Mobile: tap kebab → menu opens, contains "Delete"
- [ ] Mobile: tap outside → menu closes
- [ ] Mobile: ESC → menu closes
- [ ] Desktop: kebab hidden, inline Delete button visible (legacy behavior preserved)

---

### Section D: Context Memory — Always-Visible Actions on Mobile

Existing `.ctx-card-actions` is hover-only — broken on touch.

**D1 — `styles.css` show actions always on mobile**

```css
@media (max-width: 768px) {
  /* Replace the hover-only flyout with an always-visible kebab on mobile */
  .ctx-card-actions {
    display: flex !important;
    /* simplify position to top-right corner button instead of bottom flyout */
    top: 12px;
    right: 12px;
    bottom: auto;
    background: transparent;
    backdrop-filter: none;
    border: none;
    padding: 0;
  }
  /* Touch target */
  .ctx-card-actions button {
    width: 44px;
    height: 44px;
  }
}
```

**Wait — context already has 3 buttons (edit/pin/delete) in actions box. On mobile, showing all 3 always = clutter. Better: replace with single kebab that opens a menu.**

**D2 — Modify `_renderCtxCard()` to emit kebab on mobile**

Look at current `_renderCtxCard()` to understand structure first, then:
- Desktop: keep 3 inline action buttons (current)
- Mobile: kebab → menu with Edit / Pin/Unpin / Delete

```js
function _renderCtxCard(c) {
 // ... existing card HTML ...
 const actions = `
  <!-- Desktop: 3 inline buttons (current pattern, hover-revealed) -->
  <div class="ctx-card-actions ctx-actions-desktop">
   <button onclick="event.stopPropagation(); editContext('${c.id}')" title="Edit">✎</button>
   <button onclick="event.stopPropagation(); togglePin('${c.id}', ${!c.is_pinned})" title="Pin">${c.is_pinned ? '★' : '☆'}</button>
   <button onclick="event.stopPropagation(); deleteCtx('${c.id}')" title="Delete">🗑</button>
  </div>
  <!-- Mobile: kebab dropdown -->
  <div class="ctx-actions-mobile">
   <button class="kebab-btn" onclick="event.stopPropagation(); toggleKebab(event, 'ctx-${c.id}')" aria-label="Actions">⋮</button>
   <div class="kebab-menu hidden" id="kebab-ctx-${c.id}">
    <button class="kebab-menu-item" onclick="event.stopPropagation(); editContext('${c.id}')">${isTH ? 'แก้ไข' : 'Edit'}</button>
    <button class="kebab-menu-item" onclick="event.stopPropagation(); togglePin('${c.id}', ${!c.is_pinned})">${c.is_pinned ? (isTH ? 'ถอดหมุด' : 'Unpin') : (isTH ? 'ปักหมุด' : 'Pin')}</button>
    <button class="kebab-menu-item danger" onclick="event.stopPropagation(); deleteCtx('${c.id}')">${isTH ? 'ลบ' : 'Delete'}</button>
   </div>
  </div>`;
 // append `actions` inside the card return string
}
```

Add CSS:
```css
.ctx-actions-mobile { display: none; }
.ctx-actions-mobile .kebab-btn { position: absolute; top: 10px; right: 10px; }
@media (max-width: 768px) {
  .ctx-actions-desktop { display: none !important; }
  .ctx-actions-mobile { display: block; }
}
```

**Acceptance:**
- [ ] Mobile: each ctx-card has kebab top-right
- [ ] Mobile: tap kebab → 3 actions visible (Edit, Pin, Delete)
- [ ] Mobile: tap delete → confirms via showConfirm → deletes
- [ ] Desktop: original hover-revealed actions preserved (no regression)

---

## 🧪 Test Plan

### New tests — `tests/e2e-ui/v7.4.0-saas-responsive.spec.js`

```js
test.describe("v7.4.0 / A. Touch targets", () => {
  test.use({ viewport: { width: 375, height: 667 } });
  test("btn min-height >= 44 on mobile", async ({ page }) => { /* ... */ });
  test("form-input min-height >= 44 on mobile", async ({ page }) => { /* ... */ });
  test("btn-close min-height >= 44 on mobile", async ({ page }) => { /* ... */ });
});

test.describe("v7.4.0 / B. Floating Action Button", () => {
  test.use({ viewport: { width: 375, height: 667 } });
  test("FAB visible on My Data, hidden on Graph", async ({ page }) => { /* ... */ });
  test("FAB click triggers organize-new", async ({ page }) => { /* ... */ });
  test("FAB stacks above guide-fab without overlap", async ({ page }) => { /* ... */ });
});

test.describe("v7.4.0 / B. Desktop hides FAB", () => {
  test("desktop viewport keeps FAB hidden", async ({ page }) => { /* ... */ });
});

test.describe("v7.4.0 / C. File card view (mobile)", () => {
  test.use({ viewport: { width: 375, height: 667 } });
  test("file-item flex-direction is column on mobile", async ({ page }) => { /* ... */ });
  test("kebab button visible on each file card", async ({ page }) => { /* ... */ });
  test("kebab opens dropdown menu on click", async ({ page }) => { /* ... */ });
  test("clicking outside closes kebab menu", async ({ page }) => { /* ... */ });
});

test.describe("v7.4.0 / D. Context card actions (mobile)", () => {
  test.use({ viewport: { width: 375, height: 667 } });
  test("ctx-card kebab visible without hover", async ({ page }) => { /* ... */ });
  test("kebab opens 3 actions: Edit, Pin, Delete", async ({ page }) => { /* ... */ });
});
```

### Backend regression (สำคัญ — user emphasize)

```bash
python -m pytest tests/test_production.py -v
```

Must pass to confirm v7.4.0 frontend changes don't break backend contract.

### Frontend full Playwright suite

```bash
PDB_TEST_URL=http://127.0.0.1:8765 npx playwright test \
  phase0-baseline phase5-split-html \
  thorough-pages thorough-console thorough-flows thorough-mobile \
  v7.2.0-uxhotfix v7.3.0-edgecases v7.4.0-saas-responsive
```

Expected: 103 (current) + 13-14 (v7.4.0) ≈ 117 tests pass 100%.

### Manual smoke (real browser, both viewports)
- [ ] Mobile DevTools (375x667): My Data — FAB visible bottom-right, file cards stack, kebab opens
- [ ] Mobile DevTools: Context Memory — FAB visible, ctx-cards have kebab top-right
- [ ] Mobile DevTools: any modal — inputs ≥44px tall (paddings comfortable for thumbs)
- [ ] Desktop (1366x768): no FAB, file rows look identical to v7.3.0
- [ ] Desktop: ctx-card hover still reveals 3-button row

---

## ⚠️ Risks

| # | Risk | Likelihood | Mitigation |
|---|---|---|---|
| 1 | inline styles on ctx-modal inputs prevent 44px rule | High | Refactor to use `.form-input` class (Section A2) |
| 2 | Kebab menu inside `.file-item` with `overflow: hidden` clips dropdown | Medium | `.file-item` doesn't have overflow:hidden — verified |
| 3 | Kebab `position: absolute` relative to `.file-actions` not card → menu off-screen | Medium | parent `.file-actions` `position: relative` is fine; kebab-menu uses `top: 100%; right: 0` |
| 4 | Multiple kebabs open simultaneously | Medium | `_openKebabId` global state — closes previous on new open |
| 5 | FAB at bottom-right covers important page content (last file/card) | Medium | Add `padding-bottom: 80px` to `.main-content` on mobile |
| 6 | Tap on FAB while also dragging-uploading | Low | upload-zone separate area; FAB doesn't intercept drops |
| 7 | Kebab button onclick bubbles to file-item onclick (opens detail) | High | `event.stopPropagation()` on every onclick (already in pattern) |
| 8 | Backend test_production fails because of unrelated env (Stripe keys etc) | Low | Document failure → not blocking if not regression |

---

## 🚫 Out of Scope

- Swipe gestures on cards (e.g., swipe-to-delete) — defer
- Bottom navigation bar (mobile-style nav at bottom replacing sidebar) — defer; current sidebar+hamburger is OK
- Pull-to-refresh — defer
- Skeleton loaders during file list load — defer
- Tablet-specific layout (768-1024px range) — defer; uses desktop layout
- Touch-and-hold context menus — defer
- Long-press to multi-select — defer
- Swipe-to-pin on ctx-card — defer

---

## 📋 Checklist for เขียว

ทำตามลำดับ ความเสี่ยงต่ำ → สูง:

### Phase A — Setup (~10 นาที)
- [ ] Run baseline: 89 tests pass
- [ ] Run baseline: backend pytest pass

### Phase B — Section A: Touch Targets (~25 นาที)
- [ ] Refactor ctx-modal inputs (drop inline style, add `.form-input` class)
- [ ] Add `@media (max-width: 768px)` button + form-input rules to shared.css
- [ ] Write 3 tests A
- [ ] Run regression → ผ่าน

### Phase C — Section B: FAB (~30 นาที)
- [ ] Add `<button class="page-fab">` HTML to my-data + context-memory pages
- [ ] Add `.page-fab` CSS to styles.css
- [ ] Add `initPageFABs()` to app.js + wire in DOMContentLoaded
- [ ] Write 4 tests B
- [ ] Run regression → ผ่าน

### Phase D — Section C: File Card View (~45 นาที)
- [ ] Add mobile @media `.file-item` rules to styles.css
- [ ] Add `.kebab-btn`, `.kebab-menu` styles to shared.css
- [ ] Add `toggleKebab()` + `initKebabMenus()` to app.js
- [ ] Modify `renderFileList()` to emit both desktop + mobile actions
- [ ] Write 4 tests C
- [ ] Run regression → ผ่าน

### Phase E — Section D: Context Card Actions (~30 นาที)
- [ ] Modify `_renderCtxCard()` to emit kebab + dropdown on mobile
- [ ] Add `.ctx-actions-mobile` CSS
- [ ] Write 2 tests D
- [ ] Run regression → ผ่าน

### Phase F — Wrap up
- [ ] Full Playwright suite (~117 tests) pass 100%
- [ ] Backend pytest test_production.py pass
- [ ] Manual smoke on real DevTools (mobile + desktop)
- [ ] Update memory pipeline-state → done
- [ ] Single commit: `feat(ux): v7.4.0 SaaS responsive — touch + FAB + card view`
- [ ] Push

---

## ✅ Done Criteria

- [ ] Sections A-D implement ครบ
- [ ] 13-14 v7.4.0 tests + 103 regression = ~117 tests pass 100%
- [ ] Backend pytest passes (no contract break)
- [ ] Manual smoke ผ่านทั้ง desktop + mobile
- [ ] No new console errors
- [ ] Visual screenshots captured (mobile FAB visible / file card / ctx kebab open)
- [ ] Memory updates ครบ
- [ ] Commit + push + Fly auto-deploy verified
