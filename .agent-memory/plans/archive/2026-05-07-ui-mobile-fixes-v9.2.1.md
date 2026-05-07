# Plan: UI Mobile Critical Fixes — v9.2.1

> **Status:** `plan_pending_approval`
> **Author:** 🔴 แดง (Daeng) — 2026-05-07
> **Foundation:** v9.2.0 master (after AI Pack Builder ships) — base APP_VERSION 9.2.0
> **Version bump:** 9.2.0 → **9.2.1** (UI patch — frontend-only, no API/schema)
> **Scope philosophy:** Mobile usability + a11y correctness — NO new features. ทุกอย่างเป็น "ของเดิมที่ตกหล่น" ที่ Playwright audit เจอ
> **Estimated effort:** เขียว ~10-12 ชม. (1.5 day) + ฟ้า ~2 ชม. (regression + smoke)
> **Risk:** 🟢 Low — additive CSS + light HTML/JS, ไม่กระทบ data flow / API / contract
> **Filename note:** ไฟล์ plan ยังเป็น `ui-mobile-fixes-v9.1.1.md` (filename historical) แต่ ship เป็น **v9.2.1** เพราะ base = v9.2.0 ที่ build เสร็จแล้ว
>
> **Verification model:** **Milestone-driven** — เขียวต้อง pass Playwright milestone (Mx.y) ก่อน move ไป fix ถัดไป. ดู section "🧪 Milestone-driven Verification Strategy" ด้านล่าง

---

## 🎯 Goal & Context

### Why
จาก Playwright mobile audit 2026-05-07 (3 viewports × 14 pages × 5 audit dimensions):

| Severity | Found | กระทบ |
|----------|-------|------|
| **🔴 P0 — Critical** | 9 issues | ปุ่มสำคัญใช้งานไม่ได้บนมือถือ (save profile, generate token, zoom graph, ดู chat input, ปิด modal) |
| **🟠 P1 — Touch targets <44px** | 35+ buttons | กดผิด/พลาดง่าย, ผิด WCAG 2.5.5 + Apple HIG + Material 3 |
| **🟠 P1 — Responsive overflow** | 5 spots | header_actions ล้นขอบจอที่ 320px-393px |
| **🟡 P1 — Vertical scroll trap** | 1 (profile modal) | content 1900px ใน modal 600px → user หา save button ยาก |
| **🟡 P2 — A11y** | 396 occurrences | screen reader ใช้ไม่ได้ (label association, aria-label) |

**Total: ~50 unique fixes**

### User vision (verbatim 2026-05-07)
> "ตรวจสอบอีก มีอีกขอแบบละเอียดๆ" → "วางแผนแก้ไขปัญหาทั้งหมด แบบละเอียด"

→ User ขอ comprehensive fix — ไม่ใช่ patch บางส่วน

### Goals
1. **Mobile UX ใช้ได้จริง** — ปุ่มสำคัญทุกตัวกดได้, ไม่ถูกบัง, ไม่หายข้างจอ
2. **WCAG 2.5.5 compliance** — ทุก clickable ≥44×44px ใน mobile breakpoint
3. **A11y baseline** — screen reader users (NVDA/VoiceOver/TalkBack) ใช้ระบบได้
4. **Backward compat** — ไม่กระทบ desktop UX (≥769px ทำงานเหมือนเดิม)
5. **No regression** — ทุก existing test ผ่าน + audit re-run = 0 violations

### Non-goals (เลื่อน v9.3.0+)
- ❌ Browser compat (Firefox `:has()`, iOS 100vh fix, backdrop-filter fallback) — research-heavy, ทำแยก
- ❌ Performance pass (SVG sprite, font subsetting, orb animation off ที่ low-end, D3 lazy load)
- ❌ Variable font + `cv01/ss03` per DESIGN.md aspirational
- ❌ Light theme toggle
- ❌ DESIGN.md aspirational tokens migration
- ❌ Refactor inline style → class
- ❌ Cache-bust version strategy (?v= drift)

---

## 📁 Files to Create / Modify

| File | Action | Reason |
|------|--------|--------|
| [legacy-frontend/shared.css](../../legacy-frontend/shared.css) | **modify** | ขยาย mobile media query (44px rule) ให้ครอบ `.nav-item / .toggle-btn / .copy-btn / .btn-history / .chip / .lang-toggle / .zoom-btn / .toast-close / select.form-input / .btn-logout` (~50 lines เพิ่ม) |
| [legacy-frontend/styles.css](../../legacy-frontend/styles.css) | **modify** | (1) `.guide-fab` hide rule เมื่อ modal open (2) `.sources-panel` mobile collapse (3) `.chat-container` mobile flex-direction column (4) `#toast-container` reposition above FAB (5) header_actions wrap rules ของ context-memory + mcp-logs + graph + mcp-setup + (6) .modal scroll affordance shadow (7) `.guide-fab` z-index ลด (~120 lines) |
| [legacy-frontend/app.html](../../legacy-frontend/app.html) | **modify** | (1) เพิ่ม `aria-label` ให้ icon-only buttons 12 ตัว (2) เพิ่ม `id` + `for` ให้ทุก label-input pair (~30 จุด) (3) เพิ่ม `class="nav-tabs profile-tabs"` + 4 tab sections ใน profile modal สำหรับ split (4) เพิ่ม `.scroll-shadow` เป็น affordance |
| [legacy-frontend/landing.html](../../legacy-frontend/landing.html) | **modify** | เพิ่ม `for=` กับ login/register/forgot/reset form labels (~12 inputs) |
| [legacy-frontend/admin.html](../../legacy-frontend/admin.html) | **modify** | label-for + aria-label ให้ admin form inputs (~6 inputs) |
| [legacy-frontend/app.js](../../legacy-frontend/app.js) | **modify** | (1) เพิ่ม `_isAnyModalOpen()` helper + `body.modal-open` toggle (2) profile modal tab switching logic (3) sources-panel mobile toggle button + state (~60 lines) |
| [legacy-frontend/landing.js](../../legacy-frontend/landing.js) | **modify** | `body.modal-open` toggle ตอน showAuthModal (~3 lines) |
| [backend/config.py](../../backend/config.py) | **modify** | `APP_VERSION = "9.1.1"` |
| [legacy-frontend/app.html](../../legacy-frontend/app.html) version label | **modify** | sidebar logo-version `v9.1.1` |
| [scripts/ui_mobile_audit.py](../../scripts/) | **create** | Wrapper script เรียก Playwright + parse JSONL → return non-zero ถ้าเจอ regression (สำหรับ ฟ้า + CI ภายหลัง) (~80 lines) |
| [tests/e2e-ui/v9.1.1-mobile-fixes.spec.js](../../tests/e2e-ui/) | **create** | 18-case visual regression spec (ฟ้าใช้) — re-run audit + assert specific bugs fixed |

**ไม่แตะ:** backend/* (ยกเว้น config.py), database, MCP, billing, plan_limits, auth, drive, line, ai_pack_builder

**Cleanup ก่อน commit:**
- ลบ `tests/e2e-ui/mobile-audit-temp.spec.js` (audit artifact ไม่ใช่ test ถาวร)
- ลบ `tests/e2e-ui/mobile-audit-deep.spec.js` (เก็บ spec ใหม่ใน `v9.2.1-milestones.spec.js` แทน)
- ลบ `tests/e2e-ui/mobile-audit-results/` + `tests/e2e-ui/mobile-audit-deep-results/` (artifact dirs)

---

## 🧪 Milestone-driven Verification Strategy

> **กฎหลัก (per User 2026-05-07):** "เช็คด้วย Playwright ทุก milestone ทุกการแก้ไข" — เขียวต้อง verify ผ่าน Playwright ก่อน move ไป fix ถัดไป ไม่ใช่ทำทั้งหมดแล้วค่อย test ตอนจบ

### ทำไมต้อง milestone-by-milestone?
- 🎯 **Catch regression ทันที** — ถ้า fix M2.3 ทำลาย M1.1 จะรู้ภายในนาที ไม่ใช่หลัง 12 ชม.
- 🎯 **Confidence แต่ละ commit** — แต่ละ commit ของ 6 logical groups ผ่าน spec ของตัวเองก่อน
- 🎯 **ฟ้า review เร็ว** — แต่ละ milestone มี proof artifact (screenshot + assertion log)
- 🎯 **Single source of truth** — `tests/e2e-ui/v9.2.1-milestones.spec.js` เป็น contract ที่ทุก agent อ่านได้

### Milestone naming convention

```
M<phase>.<step>  (เช่น M1.1, M1.2, M2.3, M5.2)
M<phase>.<step>.<viewport>  (เช่น M2.1.320 = touch target ที่ 320 viewport)
```

| Milestone | Viewport ที่ test | Fix scope |
|-----------|------------------|-----------|
| M1.1 — Hide guide-fab | 320 / 375 / 393 | guide-fab + body.modal-open observer |
| M1.2 — Chat sources mobile | 320 / 375 / 393 | sources-panel collapse + toggle btn |
| M1.3 — Toast reposition | 320 / 375 / 393 | toast-container bottom: 160px |
| M2.1 — Sidebar nav 44px | 320 / 375 / 393 | nav-item / lang-toggle / profile-trigger / btn-logout |
| M2.2 — Toggle btn 44px | 320 / 375 / 393 | view-toggle / graph-mode toggle |
| M2.3 — Copy/zoom/icon 44px | 320 / 375 / 393 | copy-btn / zoom-btn / btn-icon / btn-history |
| M2.4 — Chip + select 44px | 320 / 375 / 393 | filter-chip / file-filter chip / select.form-input |
| M2.5 — Toast close 44px | 320 / 375 / 393 | .toast-close (×) |
| M3.1 — Context Memory header | 320 / 375 | header_actions wrap |
| M3.2 — MCP Logs filter | 320 / 375 / 393 | log-filters wrap |
| M3.3 — Graph header | 320 / 480 | view-toggle + rebuild wrap |
| M3.4 — MCP Setup card | 320 | step-card padding + code-block |
| M4.1 — Profile modal tabs | 320 / 375 | 4 tabs visible + switch |
| M4.2 — Save button always visible | 320 / 375 | btn-save-profile in modal-footer |
| M5.1 — Label associations | (a11y, viewport-agnostic) | input.form-input + matching `<label for=>` |
| M5.2 — Icon button aria-labels | (a11y, viewport-agnostic) | icon-only btn + aria-label |
| M6.1 — Final regression | 320 / 375 / 393 | Re-run audit → 0 P0/P1 violations |
| M6.2 — Desktop no regression | 1366 | All buttons + modals + chat ทำงานเหมือนเดิม |

### Workflow ของเขียว ตอน build

```
สำหรับแต่ละ milestone Mx.y:
  1. เขียน CSS/HTML/JS fix
  2. รัน: npx playwright test --grep "Mx.y" --reporter=list
  3. ถ้า fail → debug → repeat
  4. ถ้า pass → commit → move ไป Mx.(y+1)
```

### Single command สำหรับ milestone

```bash
# Run individual milestone
PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test --grep "@M1.1" --reporter=list

# Run all of phase 1
PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test --grep "@M1\." --reporter=list

# Run everything (final integration)
PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test v9.2.1-milestones --reporter=list
```

### Spec file structure ([tests/e2e-ui/v9.2.1-milestones.spec.js](../../tests/e2e-ui/))

ฟ้า/เขียว สร้างไฟล์เดียว — ใช้ `test.describe` per phase, `test()` per milestone, `@tag` annotation สำหรับ `--grep`:

```js
test.describe("Phase 1 — P0 Critical", () => {
  test("M1.1 — guide-fab hidden when any modal open @M1.1 @P0 @phase1", async ({ page }) => { ... });
  test("M1.2 — chat sources panel mobile collapse + toggle @M1.2 @P0 @phase1", async ({ page }) => { ... });
  test("M1.3 — toast container above page-fab @M1.3 @P0 @phase1", async ({ page }) => { ... });
});

test.describe("Phase 2 — Touch Targets", () => {
  for (const vp of MOBILE_VIEWPORTS) {
    test.describe(`@ ${vp.width}x${vp.height}`, () => {
      test.use({ viewport: vp });
      test("M2.1 — sidebar nav 44px @M2.1 @P1 @phase2", async ({ page }) => { ... });
      // ...
    });
  }
});

// ... etc.
```

### Auto-runner script ([scripts/check_milestone.py](../../scripts/))

```python
"""v9.2.1 — Milestone runner. รัน Playwright milestones ตามลำดับ.
แสดง progress + stop ที่ first failure (fail-fast).

Usage:
  python scripts/check_milestone.py            # all milestones
  python scripts/check_milestone.py M1.1       # one milestone
  python scripts/check_milestone.py phase1     # all M1.*
  python scripts/check_milestone.py --until M3.4  # until M3.4
"""
import subprocess, sys, json
from pathlib import Path

MILESTONES = [
    ("M1.1", "guide-fab hidden when modal open"),
    ("M1.2", "chat sources mobile collapse + toggle"),
    ("M1.3", "toast above page-fab"),
    ("M2.1", "sidebar nav 44px"),
    ("M2.2", "toggle btn 44px"),
    ("M2.3", "copy/zoom/icon 44px"),
    ("M2.4", "chip + select 44px"),
    ("M2.5", "toast-close 44px"),
    ("M3.1", "context memory header wrap"),
    ("M3.2", "mcp logs filter wrap"),
    ("M3.3", "graph header wrap"),
    ("M3.4", "mcp setup card padding"),
    ("M4.1", "profile modal 4 tabs"),
    ("M4.2", "save button always visible"),
    ("M5.1", "label associations"),
    ("M5.2", "icon button aria-labels"),
    ("M6.1", "final mobile audit clean"),
    ("M6.2", "desktop no regression"),
]

def run_milestone(tag, desc):
    print(f"\n{'='*70}\n🎯 {tag} — {desc}\n{'='*70}")
    res = subprocess.run(
        ["npx", "playwright", "test", "--grep", f"@{tag}", "--reporter=list"],
        env={"PDB_TEST_URL": "http://127.0.0.1:8000", **__import__("os").environ},
    )
    return res.returncode == 0

def main():
    args = sys.argv[1:]
    targets = MILESTONES
    if args:
        if args[0] == "--until":
            stop = args[1]
            targets = []
            for m in MILESTONES:
                targets.append(m)
                if m[0] == stop: break
        elif args[0].startswith("phase"):
            num = args[0][5:]
            targets = [m for m in MILESTONES if m[0].startswith(f"M{num}.")]
        else:
            targets = [m for m in MILESTONES if m[0] == args[0]]

    failed = []
    for tag, desc in targets:
        if not run_milestone(tag, desc):
            failed.append(tag)
            print(f"❌ {tag} FAILED — stopping (fail-fast)")
            break
    if failed:
        print(f"\n{len(failed)}/{len(targets)} milestones failed: {failed}")
        return 1
    print(f"\n✅ All {len(targets)} milestones passed")
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

---

## 🛠️ Step-by-Step Implementation (สำหรับเขียว)

### Phase 1 — P0 Critical Bug Fixes (~3 ชม.)

#### 1.1 `#guide-fab` ทับปุ่มสำคัญ (most critical)

**Bug:** `.guide-fab` (bottom:24, right:24, z-index:9998) บัง:
- Profile modal save/close buttons
- Graph zoom in/out/fit buttons
- MCP Setup generate token + copy URL
- Context Memory FAB
- Toast container

**Fix:** Hide guide-fab เมื่อมี overlay/modal active หรือเมื่อ user อยู่หน้าที่มี FAB อยู่แล้ว

**CSS — เพิ่มใน [styles.css](../../legacy-frontend/styles.css) ตอนท้าย section "GUIDE SYSTEM":**

```css
/* v9.1.1 — Hide guide-fab when modal/sidebar open or page has its own FAB.
   Reason: guide-fab (z-index 9998) was covering save buttons in profile modal,
   zoom controls in graph, copy/generate in mcp-setup, and the page-fab on
   my-data + context-memory. Now toggled via body class set by JS. */
body.modal-open .guide-fab,
body.sidebar-open .guide-fab,
.app-container.sidebar-open ~ .guide-fab {
  display: none !important;
}

/* Also hide on mobile when current page has its own FAB
   (.page-fab is bottom:88, guide-fab bottom:24 — they don't overlap directly,
   but the chrome looks crowded; on phones we prefer one CTA at a time) */
@media (max-width: 768px) {
  .page-fab + ~ .guide-fab,
  body:has(.page.active .page-fab:not([style*="display:none"])) .guide-fab {
    display: none;
  }
}

/* Lower z-index so even if visible, modal-overlay (10500) covers it */
.guide-fab { z-index: 9000; }  /* was 9998 */
```

**JS — เพิ่ม `_isAnyModalOpen()` helper + body class toggle ใน [app.js](../../legacy-frontend/app.js):**

```js
// v9.1.1 — Toggle body.modal-open whenever any modal-overlay is shown.
// Why: .guide-fab needs to hide when ANY modal opens (save profile button,
// generate token, etc. were being covered by the floating help button).
function _toggleModalOpenClass() {
  const anyOpen = !![...document.querySelectorAll('.modal-overlay, .pack-modal-overlay, .dup-modal-overlay, .upgrade-modal-overlay')]
    .find(el => !el.classList.contains('hidden') && el.style.display !== 'none');
  document.body.classList.toggle('modal-open', anyOpen);
}

// MutationObserver จะ trigger ทุกครั้งที่ class ของ overlay เปลี่ยน
// (.classList.add/remove('hidden') เป็น primary mechanism ในโค้ดเดิม)
function _initModalOpenObserver() {
  const observer = new MutationObserver(_toggleModalOpenClass);
  document.querySelectorAll('.modal-overlay, .pack-modal-overlay, .dup-modal-overlay, .upgrade-modal-overlay').forEach(el => {
    observer.observe(el, { attributes: true, attributeFilter: ['class', 'style'] });
  });
  // Initial sync
  _toggleModalOpenClass();
}
```

เรียก `_initModalOpenObserver()` ใน `initAppData()` (หลัง modal observers อื่น)
และใน `landing.js` ตอน `initAuth()` (เพราะ auth modal อยู่ landing page เช่นกัน)

**🧪 Milestone M1.1 verify:**

```js
// tests/e2e-ui/v9.2.1-milestones.spec.js
test("M1.1 — guide-fab hidden when modal open @M1.1 @P0 @phase1", async ({ page }) => {
  await registerAndEnterApp(page);
  // Baseline: guide-fab visible after login
  await expect(page.locator("#guide-fab")).toBeVisible();
  // Open profile modal
  const hamburger = page.locator("#sidebar-toggle");
  if (await hamburger.isVisible()) await hamburger.click();
  await page.click("#profile-trigger");
  await page.waitForTimeout(500);
  // Verify body has modal-open class
  await expect(page.locator("body")).toHaveClass(/modal-open/);
  // Verify guide-fab is NOT visible (display: none)
  await expect(page.locator("#guide-fab")).not.toBeVisible();
  // Verify save button is reachable (not obscured by guide-fab bbox)
  const saveBtn = page.locator("#btn-save-profile");
  await expect(saveBtn).toBeVisible();
  const fabBox = await page.locator("#guide-fab").boundingBox();
  const saveBox = await saveBtn.boundingBox();
  if (fabBox && saveBox) {
    // No intersection
    const intersects = !(saveBox.x + saveBox.width < fabBox.x ||
                         fabBox.x + fabBox.width < saveBox.x ||
                         saveBox.y + saveBox.height < fabBox.y ||
                         fabBox.y + fabBox.height < saveBox.y);
    expect(intersects).toBe(false);
  }
  // Close modal — verify guide-fab returns
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);
  await expect(page.locator("body")).not.toHaveClass(/modal-open/);
  await expect(page.locator("#guide-fab")).toBeVisible();
});
```

**Run:** `npx playwright test --grep "@M1.1"` — เขียวรันก่อนคอมมิต ต้อง pass ก่อน move ไป M1.2

#### 1.2 Chat sources-panel ตกจอ (mobile)

**Bug:** `.sources-panel { width: 300px }` อยู่ side-by-side กับ `.chat-main` ผ่าน `.chat-container { display: flex }` — ไม่มี mobile rule ใดๆ → panel โผล่ออกขวา 300px ที่ทุก viewport ≤768

**Fix:** Stack vertical + collapse-to-button on mobile

**CSS — เพิ่มใน [styles.css](../../legacy-frontend/styles.css) ใต้ section "AI CHAT":**

```css
/* v9.1.1 — Mobile chat: stack chat-main + sources, hide sources by default.
   User reveals sources via toggle button in chat-header. */
@media (max-width: 768px) {
  .chat-container {
    flex-direction: column;
  }
  .chat-main { width: 100%; }
  .sources-panel {
    width: 100%;
    max-height: 50vh;
    border-left: none;
    border-top: 1px solid var(--border);
    display: none;  /* hidden by default — show via toggle */
  }
  .sources-panel.is-revealed { display: flex; }
  .chat-toggle-sources {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 6px 10px;
    border-radius: 6px;
    background: var(--surface-1);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    font-size: 12px;
    cursor: pointer;
  }
  .chat-toggle-sources.is-active {
    background: var(--accent-glow);
    color: var(--accent);
    border-color: var(--accent);
  }
}

/* Hide toggle button on desktop */
.chat-toggle-sources { display: none; }
```

**HTML — เพิ่มปุ่มใน [app.html](../../legacy-frontend/app.html#L713) chat-header:**

```html
<div class="chat-header">
  <div>
    <h1 class="page-title" data-i18n="chat.title">AI Chat</h1>
    <p class="page-subtitle" data-i18n="chat.subtitle">...</p>
  </div>
  <!-- v9.1.1 — toggle sources panel on mobile -->
  <button class="chat-toggle-sources" id="chat-toggle-sources"
          aria-label="แสดงหลักฐานที่ AI ใช้" type="button">
    📊 <span data-i18n="chat.toggleSources">หลักฐาน</span>
  </button>
  <div class="profile-indicator" ...>...</div>
</div>
```

**JS — เพิ่มใน [app.js](../../legacy-frontend/app.js) `initChat()`:**

```js
// v9.1.1 — Mobile sources panel toggle
document.getElementById('chat-toggle-sources')?.addEventListener('click', () => {
  const panel = document.getElementById('sources-panel');
  const btn = document.getElementById('chat-toggle-sources');
  if (!panel) return;
  const open = panel.classList.toggle('is-revealed');
  btn.classList.toggle('is-active', open);
  btn.setAttribute('aria-expanded', String(open));
});
```

**i18n — เพิ่มใน I18N dict:**
- `'chat.toggleSources': 'หลักฐาน'` (TH) / `'Evidence'` (EN)

**🧪 Milestone M1.2 verify:**

```js
test.describe("M1.2 — chat sources mobile collapse @M1.2 @P0 @phase1", () => {
  for (const vp of [{w:320,h:568}, {w:375,h:667}, {w:393,h:851}]) {
    test(`@ ${vp.w}x${vp.h}`, async ({ page }) => {
      await page.setViewportSize({ width: vp.w, height: vp.h });
      await registerAndEnterApp(page);
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-chat");
      await page.waitForTimeout(500);
      // sources-panel ต้องไม่ visible by default
      await expect(page.locator("#sources-panel")).not.toBeVisible();
      // toggle button ต้อง visible + clickable
      const toggle = page.locator("#chat-toggle-sources");
      await expect(toggle).toBeVisible();
      const tBox = await toggle.boundingBox();
      expect(tBox?.height).toBeGreaterThanOrEqual(44);
      // Click → sources-panel visible
      await toggle.click();
      await page.waitForTimeout(300);
      await expect(page.locator("#sources-panel.is-revealed")).toBeVisible();
      await expect(toggle).toHaveAttribute("aria-expanded", "true");
      // sources-panel + chat-main ต้อง stack vertically (sources.top > chat-main.bottom)
      const main = await page.locator(".chat-main").boundingBox();
      const src = await page.locator("#sources-panel").boundingBox();
      if (main && src) expect(src.y).toBeGreaterThan(main.y);
      // Click again → hide
      await toggle.click();
      await page.waitForTimeout(300);
      await expect(page.locator("#sources-panel")).not.toBeVisible();
    });
  }
});

// Desktop guard
test("M1.2 — desktop: sources panel always visible @M1.2 @desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await registerAndEnterApp(page);
  await page.click("#nav-chat");
  await page.waitForTimeout(500);
  await expect(page.locator("#sources-panel")).toBeVisible();
  await expect(page.locator("#chat-toggle-sources")).not.toBeVisible();
});
```

**Run:** `npx playwright test --grep "@M1.2"` — verify ทั้ง 3 mobile + desktop guard ก่อน commit

#### 1.3 Toast container reposition (overlap กับ FAB)

**Bug:** `#toast-container { bottom: 20px; right: 20px; z-index: 11000 }` ทับ `.page-fab` (bottom:88, right:20) บางส่วน + บัง guide-fab

**Fix:** Reposition mobile toast above page-fab + add safe spacing

**CSS — เพิ่มใน [shared.css](../../legacy-frontend/shared.css) ตอนท้าย:**

```css
/* v9.1.1 — Mobile toast stacking: lift above page-fab (bottom:88) + guide-fab.
   Desktop unchanged. */
@media (max-width: 768px) {
  #toast-container {
    bottom: 160px;       /* clears page-fab + guide-fab + 16px buffer */
    right: 12px;
    left: 12px;
    align-items: stretch;
  }
  .toast {
    max-width: none;     /* full width on phone */
  }
}
```

**🧪 Milestone M1.3 verify:**

```js
test("M1.3 — toast above page-fab + guide-fab @M1.3 @P0 @phase1", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await registerAndEnterApp(page);
  // Trigger a toast (rebrand notice auto on first login or click upload)
  // Force toast via JS
  await page.evaluate(() => window.showToast?.("test toast", "info"));
  await page.waitForTimeout(300);
  const toast = page.locator("#toast-container .toast").first();
  await expect(toast).toBeVisible();
  const toastBox = await toast.boundingBox();
  const pageFab = await page.locator("#fab-my-data").boundingBox();
  const guideFab = await page.locator("#guide-fab").boundingBox();
  // Toast bottom must clear both FABs
  if (toastBox && pageFab) expect(toastBox.y + toastBox.height).toBeLessThan(pageFab.y);
  if (toastBox && guideFab) {
    const intersects = !(toastBox.y + toastBox.height < guideFab.y ||
                         guideFab.y + guideFab.height < toastBox.y);
    expect(intersects).toBe(false);
  }
});
```

**Run:** `npx playwright test --grep "@M1.3"` → ผ่าน → commit Phase 1 → run `npx playwright test --grep "@phase1"` (3 tests รวม)

---

### Phase 2 — Touch Targets ≥44×44 (~3 ชม.)

#### 2.1 Sidebar nav-item / lang-toggle / profile-trigger

**Bug:** `.nav-item` 35px tall, `#lang-toggle` 30px, `#profile-trigger` 35px — ทุกตัวอยู่ใน mobile sidebar

**Fix:** เพิ่ม min-height ใน mobile media query

**CSS — เพิ่มใน [shared.css:317-348](../../legacy-frontend/shared.css#L317) ภายใน existing `@media (max-width: 768px)` block:**

```css
@media (max-width: 768px) {
  /* ... existing rules ... */

  /* v9.1.1 — Apple HIG / Material 3 / WCAG 2.5.5 */
  .nav-item,
  .profile-trigger {
    min-height: 44px;
    padding: 10px 12px;     /* was 7px 12px */
  }

  .lang-toggle {
    min-height: 44px;
    padding: 10px 12px;     /* was 6px 12px */
    font-size: 13px;        /* was 12px */
  }

  /* Logout button — was 24×24, bumped to 40×40 (still inside sidebar-user-info row) */
  .btn-logout {
    min-width: 40px;
    min-height: 40px;
    padding: 8px;
  }
}
```

**🧪 Milestone M2.1 verify:**

```js
// Shared helper สำหรับ touch target (เก็บ top of spec file)
async function assertTouchTarget(page, selector, minW = 44, minH = 44, viewportW = 375) {
  await page.setViewportSize({ width: viewportW, height: 667 });
  const el = page.locator(selector).first();
  await expect(el).toBeVisible();
  const box = await el.boundingBox();
  expect(box, `${selector} bounding box null`).not.toBeNull();
  expect(box.width, `${selector} width ${box.width} < ${minW}`).toBeGreaterThanOrEqual(minW);
  expect(box.height, `${selector} height ${box.height} < ${minH}`).toBeGreaterThanOrEqual(minH);
}

test.describe("M2.1 — sidebar nav 44px @M2.1 @P1 @phase2", () => {
  for (const vp of [320, 375, 393]) {
    test(`@${vp}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.waitForTimeout(300);
      // 9 nav items
      for (const id of ["nav-my-data", "nav-knowledge", "nav-graph", "nav-chat", "nav-context-memory", "nav-mcp-setup", "nav-tokens", "nav-mcp-logs"]) {
        await assertTouchTarget(page, `#${id}`, 44, 44, vp);
      }
      await assertTouchTarget(page, "#lang-toggle", 44, 44, vp);
      await assertTouchTarget(page, "#profile-trigger", 44, 44, vp);
      await assertTouchTarget(page, "#btn-logout", 40, 40, vp);
      await assertTouchTarget(page, "#sidebar-toggle", 44, 44, vp);
    });
  }
});
```

**Run:** `npx playwright test --grep "@M2.1"` ก่อน move ไป M2.2

#### 2.2 Toggle buttons (Cards/Table/Global/Local)

**Bug:** `.toggle-btn` 27px tall

**CSS — เพิ่มใน [shared.css](../../legacy-frontend/shared.css) `@media (max-width: 768px)`:**

```css
@media (max-width: 768px) {
  .toggle-btn {
    min-height: 44px;
    padding: 10px 16px;     /* was 6px 14px */
  }
}
```

**🧪 Milestone M2.2 verify:**

```js
test.describe("M2.2 — toggle buttons 44px @M2.2 @P1 @phase2", () => {
  for (const vp of [320, 375, 393]) {
    test(`@${vp}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      // Knowledge view → Cards/Table toggle
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-knowledge");
      await page.waitForTimeout(400);
      await assertTouchTarget(page, "#view-cards", 44, 44, vp);
      await assertTouchTarget(page, "#view-table", 44, 44, vp);
      // Graph → Global/Local toggle
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-graph");
      await page.waitForTimeout(400);
      await assertTouchTarget(page, "#graph-global-btn", 44, 44, vp);
      await assertTouchTarget(page, "#graph-local-btn", 44, 44, vp);
    });
  }
});
```

**Run:** `npx playwright test --grep "@M2.2"`

#### 2.3 Copy buttons / Zoom buttons / Icon buttons

**CSS — เพิ่ม:**

```css
@media (max-width: 768px) {
  .copy-btn {
    min-width: 44px;
    min-height: 44px;
  }
  .zoom-btn {
    min-width: 44px;
    min-height: 44px;
    font-size: 18px;        /* was 16px */
  }
  .btn-icon {
    min-width: 44px;
    min-height: 44px;
    padding: 10px;
  }
  .btn-history {
    min-height: 44px;
    padding: 10px 14px;
    font-size: 13px;
  }
}
```

**🧪 Milestone M2.3 verify:**

```js
test.describe("M2.3 — copy/zoom/icon/history 44px @M2.3 @P1 @phase2", () => {
  for (const vp of [320, 375, 393]) {
    test(`@${vp}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      const hamburger = page.locator("#sidebar-toggle");
      // Graph zoom buttons
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-graph");
      await page.waitForTimeout(400);
      await assertTouchTarget(page, "#zoom-in-btn", 44, 44, vp);
      await assertTouchTarget(page, "#zoom-out-btn", 44, 44, vp);
      await assertTouchTarget(page, "#zoom-fit-btn", 44, 44, vp);
      // MCP Setup copy buttons
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-mcp-setup");
      await page.waitForTimeout(400);
      await assertTouchTarget(page, "#btn-copy-url", 44, 44, vp);
      await assertTouchTarget(page, "#btn-copy-config", 44, 44, vp);
      // Profile → personality → history button
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#profile-trigger");
      await page.waitForTimeout(500);
      // (สำหรับหลัง M4 split tabs, เปลี่ยนเป็นคลิก tab "บุคลิกภาพ")
      await page.click('[data-ptab="personality"]').catch(() => {
        return page.click("#personality-section > summary").catch(() => {});
      });
      await page.waitForTimeout(300);
      await assertTouchTarget(page, ".btn-history", 44, 44, vp);
      // Cluster edit btn-icon (require ≥1 cluster — skip if none)
      // — defer to manual check
    });
  }
});
```

**Run:** `npx playwright test --grep "@M2.3"`

#### 2.4 Filter chips + filter chips + select dropdowns

**CSS — เพิ่ม:**

```css
@media (max-width: 768px) {
  .chip,
  .filter-chip {
    min-height: 44px;
    padding: 10px 16px;     /* was 6px 14px / 4px 10px */
  }
  select.form-input,
  .log-filter-select {
    min-height: 44px;
    padding: 12px 14px;     /* was 7px 12px */
    font-size: 14px;
  }
}
```

**🧪 Milestone M2.4 verify:**

```js
test.describe("M2.4 — chip + select 44px @M2.4 @P1 @phase2", () => {
  for (const vp of [320, 375, 393]) {
    test(`@${vp}px`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      // file-filter chips บน My Data (vault feature)
      await assertTouchTarget(page, '.file-filter-chips .chip[data-kind="all"]', 44, 44, vp);
      await assertTouchTarget(page, '.file-filter-chips .chip[data-kind="processed"]', 44, 44, vp);
      // Graph filter-chip
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-graph");
      await page.waitForTimeout(400);
      const chips = await page.locator(".filter-chip").all();
      for (const c of chips.slice(0, 3)) {
        const box = await c.boundingBox();
        if (box) expect(box.height).toBeGreaterThanOrEqual(44);
      }
      // MCP Logs select dropdowns
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-mcp-logs");
      await page.waitForTimeout(400);
      await assertTouchTarget(page, "#log-filter-tool", 44, 44, vp);
      await assertTouchTarget(page, "#log-filter-status", 44, 44, vp);
      // Context Memory select
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-context-memory");
      await page.waitForTimeout(400);
      await assertTouchTarget(page, "#ctx-filter-type", 44, 44, vp);
    });
  }
});
```

**Run:** `npx playwright test --grep "@M2.4"`

#### 2.5 Toast close button

**CSS — เพิ่มใน [shared.css](../../legacy-frontend/shared.css) `@media (max-width: 768px)`:**

```css
@media (max-width: 768px) {
  .toast-close {
    min-width: 44px;
    min-height: 44px;
    font-size: 22px;
    padding: 10px;
  }
}
```

**🧪 Milestone M2.5 verify:**

```js
test("M2.5 — toast-close 44px @M2.5 @P1 @phase2", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await registerAndEnterApp(page);
  // Force a toast (error type — has × button per v7.2.0)
  await page.evaluate(() => window.showToast?.("test error", "error"));
  await page.waitForTimeout(300);
  await assertTouchTarget(page, ".toast-close", 44, 44, 375);
});
```

**Run:** `npx playwright test --grep "@M2.5"` → ผ่าน → commit Phase 2 → run `npx playwright test --grep "@phase2"` (15 tests รวม 5 substeps × 3 viewports)

---

### Phase 3 — Responsive Overflow Fixes (~2 ชม.)

#### 3.1 Context Memory header_actions wrap

**Bug:** search input 200px + select 127px + button = 335px ล้นที่ 320

**CSS — เพิ่มใน [styles.css](../../legacy-frontend/styles.css) ใต้ `#page-context-memory`:**

```css
/* v9.1.1 — Context Memory header: wrap on narrow viewports */
@media (max-width: 768px) {
  #page-context-memory .header-actions {
    flex-wrap: wrap;
    gap: 8px;
    width: 100%;
  }
  #page-context-memory .header-actions #ctx-search {
    flex: 1 1 100%;
    width: 100%;
    max-width: none;
  }
  #page-context-memory .header-actions select {
    flex: 1 1 calc(50% - 4px);
  }
  #page-context-memory .header-actions #btn-new-context {
    flex: 1 1 calc(50% - 4px);
    justify-content: center;
  }
}
```

**HTML — ลบ inline `style="width:200px"` จาก [app.html:801](../../legacy-frontend/app.html#L801)** (อยู่ inline, override class)

**🧪 Milestone M3.1 verify:**

```js
test.describe("M3.1 — Context Memory header wrap @M3.1 @P1 @phase3", () => {
  for (const vp of [320, 375, 393]) {
    test(`@${vp}px no overflow`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-context-memory");
      await page.waitForTimeout(400);
      // header_actions ต้องไม่ overflow
      const result = await page.evaluate((vw) => {
        const ha = document.querySelector("#page-context-memory .header-actions");
        if (!ha) return { ok: false, reason: "no header-actions" };
        const rect = ha.getBoundingClientRect();
        return { ok: rect.right <= vw + 1, right: rect.right, vw };
      }, vp);
      expect(result.ok, JSON.stringify(result)).toBe(true);
      // ทุก child element เห็น (search + select + btn-new-context)
      await expect(page.locator("#ctx-search")).toBeVisible();
      await expect(page.locator("#ctx-filter-type")).toBeVisible();
      await expect(page.locator("#btn-new-context")).toBeVisible();
    });
  }
});
```

**Run:** `npx playwright test --grep "@M3.1"`

#### 3.2 MCP Logs filter row wrap

**Bug:** select × 2 + button "รีเฟรช" ล้น

**CSS:**

```css
/* v9.1.1 — MCP Logs filter row wrap */
@media (max-width: 768px) {
  .log-filters {
    flex-wrap: wrap;
    gap: 8px;
  }
  .log-filter-select {
    flex: 1 1 calc(50% - 4px);
    min-width: 0;
  }
  #btn-refresh-logs {
    flex: 1 1 100%;
    justify-content: center;
  }
}
```

**🧪 Milestone M3.2 verify:**

```js
test.describe("M3.2 — MCP Logs filter wrap @M3.2 @P1 @phase3", () => {
  for (const vp of [320, 375, 393]) {
    test(`@${vp}px refresh button visible`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-mcp-logs");
      await page.waitForTimeout(400);
      // refresh button bbox ต้องอยู่ใน viewport
      const btn = page.locator("#btn-refresh-logs");
      const box = await btn.boundingBox();
      expect(box?.x + box?.width).toBeLessThanOrEqual(vp + 1);
      // และต้อง clickable (ไม่ถูก clip)
      await btn.click();
      await page.waitForTimeout(200);
    });
  }
});
```

**Run:** `npx playwright test --grep "@M3.2"`

#### 3.3 Graph header_actions wrap (320px specific)

**CSS:**

```css
/* v9.1.1 — Graph header: wrap view-toggle + rebuild on narrow viewports */
@media (max-width: 480px) {
  #page-graph .page-header {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  #page-graph .header-actions {
    flex-wrap: wrap;
    gap: 8px;
  }
  #page-graph .header-actions .view-toggle {
    flex: 1 1 100%;
  }
  #page-graph .header-actions #btn-rebuild-graph {
    flex: 1 1 100%;
    justify-content: center;
  }
}
```

**🧪 Milestone M3.3 verify:**

```js
test.describe("M3.3 — Graph header wrap @M3.3 @P1 @phase3", () => {
  for (const vp of [320, 375, 480]) {
    test(`@${vp}px rebuild visible`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#nav-graph");
      await page.waitForTimeout(400);
      const btn = page.locator("#btn-rebuild-graph");
      await expect(btn).toBeVisible();
      const box = await btn.boundingBox();
      expect(box?.x + box?.width).toBeLessThanOrEqual(vp + 1);
      // view-toggle ต้องอยู่ใน viewport
      const toggle = page.locator("#page-graph .view-toggle");
      const tBox = await toggle.boundingBox();
      expect(tBox?.x + tBox?.width).toBeLessThanOrEqual(vp + 1);
    });
  }
});
```

**Run:** `npx playwright test --grep "@M3.3"`

#### 3.4 MCP Setup card padding (320px specific)

**CSS:**

```css
/* v9.1.1 — MCP Setup: tighter padding ที่ 320px viewport */
@media (max-width: 480px) {
  .mcp-step-card {
    padding: 14px;          /* was 20px */
    gap: 12px;              /* was 16px */
  }
  .mcp-step-content {
    min-width: 0;           /* allow flex shrink */
  }
  .mcp-platform-tabs {
    flex-wrap: wrap;
  }
  .code-block code {
    font-size: 11px;        /* was 12px */
    word-break: break-all;
  }
}
```

**🧪 Milestone M3.4 verify:**

```js
test("M3.4 — MCP Setup card no overflow @M3.4 @P1 @phase3", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await registerAndEnterApp(page);
  const hamburger = page.locator("#sidebar-toggle");
  if (await hamburger.isVisible()) await hamburger.click();
  await page.click("#nav-mcp-setup");
  await page.waitForTimeout(500);
  // ทุก step-card ต้องอยู่ใน viewport
  const cards = await page.locator(".mcp-step-card").all();
  for (const c of cards) {
    const box = await c.boundingBox();
    if (box) expect(box.x + box.width).toBeLessThanOrEqual(320 + 1);
  }
  // code-block ต้อง word-break (ไม่ horizontal scroll)
  const code = page.locator(".code-block code").first();
  if (await code.isVisible()) {
    const overflowing = await code.evaluate((el) => el.scrollWidth > el.clientWidth + 1);
    expect(overflowing).toBe(false);
  }
});
```

**Run:** `npx playwright test --grep "@M3.4"` → ผ่าน → commit Phase 3 → run `npx playwright test --grep "@phase3"` (10 tests)

#### 3.5 Other inline-style cleanup (cosmetic but P1)

ลบ inline `style=` ที่ block responsive flow:
- [app.html:801](../../legacy-frontend/app.html#L801) `style="width:200px..."` → ใช้ class
- [app.html:802-808](../../legacy-frontend/app.html#L802) `style="padding:8px 12px..."` → class
- [app.html:551, 848, 858, 884](../../legacy-frontend/app.html) `style="display:flex..."` → class

**Pattern:** สร้าง class `.form-input-condensed` + `.form-row-2col` ใน styles.css แล้วใช้แทน

---

### Phase 4 — Profile Modal Tab Split (~1.5 ชม.)

**Bug:** profile modal มี content รวม ~1900px ใน max-height: 90vh (~600px) — user ต้อง scroll 3+ pages ในเฟรม + ปุ่ม "บันทึกโปรไฟล์" อยู่ก้น modal เห็นยาก

**Fix:** แบ่งเป็น 4 tabs ภายใน modal: **Account** / **Profile** / **Personality** / **Connectors**

**HTML — refactor [app.html:1093-1322](../../legacy-frontend/app.html#L1093) profile modal body:**

```html
<div class="modal profile-modal">
  <div class="modal-header">
    <h2 data-i18n="profile.title">My Profile</h2>
    <button class="btn-close" id="close-profile-modal" aria-label="ปิด">&times;</button>
  </div>

  <!-- v9.1.1 — Tab navigation -->
  <nav class="profile-tabs" role="tablist">
    <button class="profile-tab active" data-ptab="account" role="tab">
      <span data-i18n="profile.tab.account">บัญชี</span>
    </button>
    <button class="profile-tab" data-ptab="profile" role="tab">
      <span data-i18n="profile.tab.profile">โปรไฟล์</span>
    </button>
    <button class="profile-tab" data-ptab="personality" role="tab">
      <span data-i18n="profile.tab.personality">บุคลิกภาพ</span>
    </button>
    <button class="profile-tab" data-ptab="connectors" role="tab">
      <span data-i18n="profile.tab.connectors">เชื่อมต่อ</span>
    </button>
  </nav>

  <div class="modal-body">
    <!-- Tab 1: Account (billing + usage) -->
    <section class="profile-tab-panel active" data-ptab-panel="account">
      <!-- existing billing-section + usage-section content -->
    </section>

    <!-- Tab 2: Profile (5 textareas) -->
    <section class="profile-tab-panel" data-ptab-panel="profile">
      <!-- existing 5 form-groups: identity, goals, style, output, background -->
    </section>

    <!-- Tab 3: Personality (4 systems) -->
    <section class="profile-tab-panel" data-ptab-panel="personality">
      <!-- existing personality-section content (without <details> wrapper) -->
    </section>

    <!-- Tab 4: Connectors (storage mode + LINE) -->
    <section class="profile-tab-panel" data-ptab-panel="connectors">
      <!-- existing storage-mode-section + line-bot-section -->
    </section>
  </div>

  <div class="modal-footer">
    <button class="btn btn-primary" id="btn-save-profile">บันทึกโปรไฟล์</button>
  </div>
</div>
```

**CSS:**

```css
/* v9.1.1 — Profile modal tab split */
.profile-modal {
  width: min(640px, 92vw);
  max-height: 88vh;
  display: flex;
  flex-direction: column;
}

.profile-tabs {
  display: flex;
  gap: 4px;
  padding: 0 20px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-secondary);
}

.profile-tab {
  padding: 12px 16px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  font-family: inherit;
  transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;
}

.profile-tab:hover { color: var(--text-primary); }

.profile-tab.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

.profile-tab-panel {
  display: none;
  animation: fadeIn 0.15s ease;
}

.profile-tab-panel.active { display: block; }

@media (max-width: 480px) {
  .profile-tabs {
    overflow-x: auto;
    flex-wrap: nowrap;
    -webkit-overflow-scrolling: touch;
  }
  .profile-tab {
    flex: 0 0 auto;
    min-height: 44px;
    white-space: nowrap;
  }
}
```

**JS — เพิ่มใน [app.js](../../legacy-frontend/app.js) ใน `initProfile()`:**

```js
// v9.1.1 — Profile modal tab switching
document.querySelectorAll('.profile-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    const target = tab.dataset.ptab;
    document.querySelectorAll('.profile-tab').forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.profile-tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelector(`[data-ptab-panel="${target}"]`)?.classList.add('active');
  });
});
```

**i18n เพิ่ม 4 keys:**
- `'profile.tab.account': 'บัญชี' / 'Account'`
- `'profile.tab.profile': 'โปรไฟล์' / 'Profile'`
- `'profile.tab.personality': 'บุคลิกภาพ' / 'Personality'`
- `'profile.tab.connectors': 'เชื่อมต่อ' / 'Connectors'`

**🧪 Milestone M4.1 verify (tabs work):**

```js
test.describe("M4.1 — profile modal 4 tabs @M4.1 @P1 @phase4", () => {
  for (const vp of [320, 375]) {
    test(`@${vp}px tab switching`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await registerAndEnterApp(page);
      const hamburger = page.locator("#sidebar-toggle");
      if (await hamburger.isVisible()) await hamburger.click();
      await page.click("#profile-trigger");
      await page.waitForTimeout(500);
      // Default tab = account
      await expect(page.locator('[data-ptab="account"]')).toHaveClass(/active/);
      await expect(page.locator('[data-ptab-panel="account"]')).toBeVisible();
      await expect(page.locator('[data-ptab-panel="profile"]')).not.toBeVisible();
      // Switch to Profile tab
      await page.click('[data-ptab="profile"]');
      await page.waitForTimeout(200);
      await expect(page.locator('[data-ptab-panel="profile"]')).toBeVisible();
      await expect(page.locator("#profile-identity")).toBeVisible();
      // Switch to Personality
      await page.click('[data-ptab="personality"]');
      await page.waitForTimeout(200);
      await expect(page.locator("#mbti-type")).toBeVisible();
      // Switch to Connectors
      await page.click('[data-ptab="connectors"]');
      await page.waitForTimeout(200);
      // storage-mode + line-bot sections ต้อง visible (อย่างน้อย 1)
      const storage = page.locator("#storage-mode-section").or(page.locator("#line-bot-section"));
      await expect(storage.first()).toBeVisible();
      // ทุก tab button มี touch target 44px
      for (const t of ["account", "profile", "personality", "connectors"]) {
        await assertTouchTarget(page, `[data-ptab="${t}"]`, 44, 44, vp);
      }
    });
  }
});
```

**🧪 Milestone M4.2 verify (save button always reachable):**

```js
test("M4.2 — save button always reachable @M4.2 @P1 @phase4", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await registerAndEnterApp(page);
  const hamburger = page.locator("#sidebar-toggle");
  if (await hamburger.isVisible()) await hamburger.click();
  await page.click("#profile-trigger");
  await page.waitForTimeout(500);
  const saveBtn = page.locator("#btn-save-profile");
  // ที่ทุก tab → save ปุ่มยังต้อง visible (อยู่ใน modal-footer ที่ sticky)
  for (const tab of ["account", "profile", "personality", "connectors"]) {
    await page.click(`[data-ptab="${tab}"]`);
    await page.waitForTimeout(200);
    await expect(saveBtn).toBeVisible();
    const box = await saveBtn.boundingBox();
    // ต้องอยู่ใน viewport vertically (top < 667)
    expect(box?.y).toBeLessThan(667);
    // และ guide-fab ไม่ทับ (ตาม M1.1 — modal-open hides guide-fab)
    await expect(page.locator("#guide-fab")).not.toBeVisible();
  }
});
```

**Run:** `npx playwright test --grep "@M4\."` → ผ่าน → commit Phase 4 → run `npx playwright test --grep "@phase4"` (3 tests)

**Migration concern:** Existing `<details class="personality-section">` ใช้ collapsible. Tab structure replace นั่น → คง content แต่ลบ `<details><summary>` wrapper. Personality state (open/close) ไม่ persist อยู่แล้ว → ไม่ break

---

### Phase 5 — A11y Baseline (~3 ชม.)

#### 5.1 Label association (`<label for="id">`)

**Bug:** 384 occurrences ของ `<input class="form-input">` ที่มี `<label>` ข้างๆ แต่ **ไม่มี `for=`**

**Pattern fix:** ทุก input/textarea/select ใน form-group → เพิ่ม `id` (ถ้ายังไม่มี) + `for=` บน label

**ตัวอย่าง [app.html:39-43](../../legacy-frontend/app.html#L39):**

```html
<!-- BEFORE -->
<div class="form-group">
  <label>อีเมล</label>
  <input type="email" id="login-email" placeholder="..." class="form-input">
</div>

<!-- AFTER -->
<div class="form-group">
  <label for="login-email">อีเมล</label>
  <input type="email" id="login-email" placeholder="..." class="form-input">
</div>
```

**Files affected:**
- [landing.html](../../legacy-frontend/landing.html): login (3) + register (4) + forgot (1) + reset (3) = 11 inputs
- [app.html](../../legacy-frontend/app.html): pack modal (3) + ctx modal (5) + AI builder (5+) + profile (5) + admin (2) = 20+ inputs
- [admin.html](../../legacy-frontend/admin.html): users-search + filter + 3 modal forms = 6 inputs

**Approach:** เขียวใช้ regex find-replace pattern ใน editor:
```
Find:    <label>([^<]+)</label>\s*<(input|textarea|select)([^>]*?)id="([^"]+)"
Replace: <label for="$4">$1</label>\n<$2$3id="$4"
```
แล้วกวาดทีละไฟล์ verify visually

**🧪 Milestone M5.1 verify (programmatic a11y scan):**

```js
test("M5.1 — every form-input has label association @M5.1 @P2 @phase5", async ({ page }) => {
  // Run on landing + app + admin pages
  const pages = [
    { url: "/", needsAuth: false, name: "landing" },
    { url: "/app", needsAuth: true, name: "app" },
    // /admin requires admin user — skip in this auto-test, verify manually
  ];
  for (const p of pages) {
    if (p.needsAuth) await registerAndEnterApp(page);
    else await page.goto(p.url);
    await page.waitForLoadState("networkidle");
    // Open modal-rich pages: profile + pack + AI builder + ctx
    if (p.needsAuth) {
      // open all dialogs sequentially (each opens, audit, close)
      const triggers = [
        () => page.click("#profile-trigger"),
        () => page.goto("/app").then(() => page.click("#nav-knowledge")).then(() => page.click('.tab-btn[data-tab="packs"]')).then(() => page.click('button:has-text("สร้าง Pack")')),
      ];
      // For each modal we audit then ESC close
    }
    // Programmatically check
    const unlabeled = await page.evaluate(() => {
      const offenders = [];
      document.querySelectorAll("input.form-input, textarea.form-input, select.form-input").forEach((el) => {
        const id = el.id;
        const aria = el.getAttribute("aria-label") || el.getAttribute("aria-labelledby");
        const wrapped = el.closest("label");
        const lblFor = id ? document.querySelector(`label[for="${id}"]`) : null;
        if (!aria && !wrapped && !lblFor) {
          offenders.push({ id: id || "(no-id)", placeholder: el.placeholder?.slice(0, 30) });
        }
      });
      return offenders;
    });
    expect(unlabeled, `Unlabeled inputs on ${p.name}: ${JSON.stringify(unlabeled)}`).toEqual([]);
  }
});
```

**Run:** `npx playwright test --grep "@M5.1"`

#### 5.2 Icon-only button aria-labels

**Bug:** 12 unique icon-only buttons ไม่มี aria-label

**Fix patterns (ตัวอย่าง):**

| Element | Current | Add |
|---------|---------|-----|
| `#close-profile-modal` (×) | `<button class="btn-close">×</button>` | `aria-label="ปิด"` |
| `#btn-send` (send arrow SVG) | `<button class="btn btn-send">` | `aria-label="ส่งข้อความ"` |
| `#fd-close` | `<button class="btn-close"></button>` | `aria-label="ปิด"` |
| `.btn-icon` (cluster edit) | `<button class="btn-icon">✏️</button>` | `aria-label="แก้ไข Collection"` |
| `#btn-copy-url`, `#btn-copy-token`, `#btn-copy-config*` | `<button class="copy-btn">` | `aria-label="คัดลอก URL"` etc. |
| `#close-detail` (graph) | `<button class="btn-close">×</button>` | `aria-label="ปิด detail panel"` |
| `#close-relation-sidebar` | `<button class="btn-close">×</button>` | `aria-label="ปิด"` |
| All `.btn-history` | `<button class="btn-history">ประวัติ</button>` | (มี text แล้ว — ✅ OK ไม่ต้องเพิ่ม) |
| `#btn-logout` | `<button class="btn-logout">` (svg only) | `aria-label="ออกจากระบบ"` |
| `#sidebar-toggle` | `<button class="sidebar-toggle">` (svg) | (มีอยู่แล้ว `aria-label="Menu"` ✅) |

**Files affected:**
- [app.html](../../legacy-frontend/app.html): ~10 buttons
- [admin.html](../../legacy-frontend/admin.html): ~3 buttons
- [landing.html](../../legacy-frontend/landing.html): `#auth-modal-close` (1)

**Bonus:** เพิ่ม `aria-expanded="false"` + JS update บน toggle buttons (chat-toggle-sources, .profile-tab role=tab, etc.) — proper ARIA state

**🧪 Milestone M5.2 verify (icon-only button scan):**

```js
test("M5.2 — every icon-only button has aria-label or visible text @M5.2 @P2 @phase5", async ({ page }) => {
  await registerAndEnterApp(page);
  // Visit each page so all icon buttons render
  for (const nav of ["my-data", "knowledge", "graph", "chat", "context-memory", "mcp-setup", "tokens", "mcp-logs"]) {
    const hamburger = page.locator("#sidebar-toggle");
    if (await hamburger.isVisible()) await hamburger.click();
    await page.click(`#nav-${nav}`).catch(() => {});
    await page.waitForTimeout(400);
    const offenders = await page.evaluate(() => {
      const list = [];
      document.querySelectorAll("button:not([disabled])").forEach((el) => {
        if (el.closest(".hidden") || el.offsetParent === null) return;
        const txt = (el.innerText || el.textContent || "").trim();
        const aria = el.getAttribute("aria-label") || el.getAttribute("title");
        if (!txt && !aria) {
          list.push({ id: el.id || "", cls: (el.className || "").toString().slice(0, 40) });
        }
      });
      return list;
    });
    expect(offenders, `Page ${nav} icon-only buttons missing label: ${JSON.stringify(offenders)}`).toEqual([]);
  }
});
```

**Run:** `npx playwright test --grep "@M5\."` → ผ่าน → commit Phase 5 → run `npx playwright test --grep "@phase5"` (2 tests)

---

### Phase 6 — Final Integration + Memory Update + Version Bump (~0.5 ชม.)

#### 6.1 Final integration milestone — re-run full audit

**🧪 Milestone M6.1 verify (no P0/P1 regression):**

```js
test.describe("M6.1 — final mobile audit clean @M6.1 @phase6", () => {
  for (const vp of [320, 375, 393]) {
    test(`@${vp}px no overflow on any page`, async ({ page }) => {
      await page.setViewportSize({ width: vp, height: 667 });
      await page.goto("/");
      const checkOverflow = async () => await page.evaluate((vw) => {
        const offenders = [];
        document.querySelectorAll("body *").forEach((el) => {
          const r = el.getBoundingClientRect();
          if (r.width === 0 || r.height === 0) return;
          if (r.right > vw + 2) {
            const sel = el.tagName.toLowerCase() + (el.id ? "#" + el.id : "");
            // Skip animated background orbs (intentional)
            if (sel.includes("orb")) return;
            // Skip elements inside `overflow: hidden` containers (e.g. sources-panel hidden)
            const parent = el.parentElement;
            if (parent && getComputedStyle(parent).overflow === "hidden") return;
            offenders.push(sel);
          }
        });
        return [...new Set(offenders)].slice(0, 10);
      }, vp);
      // Public landing
      expect(await checkOverflow()).toEqual([]);
      // Auth
      await registerAndEnterApp(page);
      // Walk through all pages
      const pages = ["my-data", "knowledge", "graph", "chat", "context-memory", "mcp-setup", "tokens", "mcp-logs"];
      for (const nav of pages) {
        const hamburger = page.locator("#sidebar-toggle");
        if (await hamburger.isVisible()) await hamburger.click();
        await page.click(`#nav-${nav}`).catch(() => {});
        await page.waitForTimeout(400);
        const offenders = await checkOverflow();
        expect(offenders, `Page ${nav} @${vp}: ${JSON.stringify(offenders)}`).toEqual([]);
      }
    });
  }
});
```

#### 6.2 Desktop no-regression milestone

**🧪 Milestone M6.2 verify (desktop unchanged):**

```js
test("M6.2 — desktop 1366px unchanged @M6.2 @phase6 @desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await registerAndEnterApp(page);
  // 1. Sidebar always visible (no hamburger)
  await expect(page.locator("#sidebar")).toBeVisible();
  await expect(page.locator("#sidebar-toggle")).not.toBeVisible();
  // 2. Guide FAB always visible
  await expect(page.locator("#guide-fab")).toBeVisible();
  // 3. Chat: sources-panel always visible (no toggle button)
  await page.click("#nav-chat");
  await page.waitForTimeout(400);
  await expect(page.locator("#sources-panel")).toBeVisible();
  await expect(page.locator("#chat-toggle-sources")).not.toBeVisible();
  // 4. Profile modal: 4 tabs work
  await page.click("#profile-trigger");
  await page.waitForTimeout(500);
  await expect(page.locator('[data-ptab="account"]')).toBeVisible();
  // Save button reachable
  await expect(page.locator("#btn-save-profile")).toBeVisible();
  await page.keyboard.press("Escape");
  // 5. Existing thorough-mobile + thorough-pages specs still pass — separate run
});
```

**Run:** `npx playwright test --grep "@M6\."` → final integration check ก่อน push

#### 6.3 [scripts/check_milestone.py](../../scripts/check_milestone.py) — already specified ใน strategy section

ดู structure ที่ "Milestone-driven Verification Strategy" ด้านบน — script orchestrate milestone ตามลำดับ + fail-fast

#### 6.4 [tests/e2e-ui/v9.2.1-milestones.spec.js](../../tests/e2e-ui/) — โครงสร้างไฟล์

ฟ้าสร้างไฟล์เดียวรวม **18 milestones × 1-3 viewports each = ~38 test cases**:

```js
// tests/e2e-ui/v9.2.1-milestones.spec.js
const { test, expect } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

// Shared helper
async function assertTouchTarget(page, sel, minW = 44, minH = 44, vp = 375) {
  await page.setViewportSize({ width: vp, height: 667 });
  const el = page.locator(sel).first();
  await expect(el).toBeVisible();
  const box = await el.boundingBox();
  expect(box.width, `${sel} w=${box.width} < ${minW}`).toBeGreaterThanOrEqual(minW);
  expect(box.height, `${sel} h=${box.height} < ${minH}`).toBeGreaterThanOrEqual(minH);
}

// ─── Phase 1 — P0 Critical (3 milestones) ───
test.describe("Phase 1 — P0 Critical @phase1", () => {
  test("M1.1 — guide-fab hidden when modal open @M1.1 @P0", async ({ page }) => { /* ... */ });
  test.describe("M1.2 — chat sources mobile @M1.2 @P0", () => { /* 3 viewports + desktop guard */ });
  test("M1.3 — toast above page-fab @M1.3 @P0", async ({ page }) => { /* ... */ });
});

// ─── Phase 2 — Touch Targets (5 milestones × 3 viewports = 15 tests) ───
test.describe("Phase 2 — Touch Targets @phase2", () => {
  // M2.1 — sidebar nav 44px (3 viewports)
  // M2.2 — toggle-btn 44px (3 viewports)
  // M2.3 — copy/zoom/icon/history 44px (3 viewports)
  // M2.4 — chip + select 44px (3 viewports)
  // M2.5 — toast-close 44px (1 test)
});

// ─── Phase 3 — Responsive Overflow (4 milestones × varied viewports = 10 tests) ───
test.describe("Phase 3 — Responsive Overflow @phase3", () => {
  // M3.1 — context memory header (3 viewports)
  // M3.2 — mcp logs filter (3 viewports)
  // M3.3 — graph header (3 viewports)
  // M3.4 — mcp setup card (1 test @ 320)
});

// ─── Phase 4 — Profile Modal Tabs (2 milestones = 3 tests) ───
test.describe("Phase 4 — Profile Modal @phase4", () => {
  // M4.1 — 4 tabs switch (2 viewports)
  // M4.2 — save button reachable (1 test)
});

// ─── Phase 5 — A11y (2 milestones = 2 tests) ───
test.describe("Phase 5 — A11y @phase5", () => {
  // M5.1 — label associations (programmatic scan)
  // M5.2 — icon-only button aria-label (programmatic scan)
});

// ─── Phase 6 — Final Integration (2 milestones = 4 tests) ───
test.describe("Phase 6 — Final Integration @phase6", () => {
  // M6.1 — no overflow on any page (3 viewports)
  // M6.2 — desktop unchanged (1 test)
});
```

**Total: ~38 test cases ใน spec file เดียว**, runtime ~2-3 นาทีบน localhost

#### 6.6 Version bump

- [backend/config.py](../../backend/config.py) `APP_VERSION = "9.2.1"` (รุ่น base = v9.2.0)
- [legacy-frontend/app.html](../../legacy-frontend/app.html) sidebar `<span class="logo-version">v9.2.1</span>`
- Cache-bust: เพิ่ม `?v=9.2.1` ทุก stylesheet/script reference (3 stylesheets + 4 scripts × 4 HTML files) — ใช้ shell oneliner: `find legacy-frontend -name '*.html' -exec sed -i 's/?v=[0-9.]*/?v=9.2.1/g' {} +`

#### 6.7 Memory updates

- `current/pipeline-state.md` → state `built_pending_review`
- `current/last-session.md` → summary
- `history/session-logs/2026-05-07-ui-mobile-fixes-v9.2.1.md`

#### 6.8 Cleanup

- ลบ `tests/e2e-ui/mobile-audit-temp.spec.js`
- ลบ `tests/e2e-ui/mobile-audit-deep.spec.js`
- ลบ `tests/e2e-ui/mobile-audit-results/` + `tests/e2e-ui/mobile-audit-deep-results/`

---

## 🧪 Milestone Index (สำหรับฟ้า + เขียว reference)

> รายการ milestone ทั้งหมดที่ Playwright spec ต้องครอบคลุม. Spec ตำแหน่ง: [tests/e2e-ui/v9.2.1-milestones.spec.js](../../tests/e2e-ui/) — ฟ้าเขียน, เขียวรันก่อน commit

### Index ของ 18 Milestones (~38 test cases)

| Milestone | Phase | Severity | Verify | # tests | Tags |
|-----------|-------|----------|--------|---------|------|
| **M1.1** | 1 | P0 | guide-fab hidden when modal/sidebar open | 1 | `@M1.1 @P0 @phase1` |
| **M1.2** | 1 | P0 | chat sources mobile collapse + toggle | 4 (3vp + desktop) | `@M1.2 @P0 @phase1` |
| **M1.3** | 1 | P0 | toast above page-fab + guide-fab | 1 | `@M1.3 @P0 @phase1` |
| **M2.1** | 2 | P1 | sidebar nav-item / lang / profile / logout 44px | 3 (3vp) | `@M2.1 @P1 @phase2` |
| **M2.2** | 2 | P1 | toggle-btn (Cards/Table/Global/Local) 44px | 3 | `@M2.2 @P1 @phase2` |
| **M2.3** | 2 | P1 | copy / zoom / icon / history 44px | 3 | `@M2.3 @P1 @phase2` |
| **M2.4** | 2 | P1 | chip + select 44px (file-filter, graph filter, mcp logs, ctx) | 3 | `@M2.4 @P1 @phase2` |
| **M2.5** | 2 | P1 | toast-close (×) 44px | 1 | `@M2.5 @P1 @phase2` |
| **M3.1** | 3 | P1 | Context Memory header_actions wrap (no overflow) | 3 | `@M3.1 @P1 @phase3` |
| **M3.2** | 3 | P1 | MCP Logs filter row wrap + refresh visible | 3 | `@M3.2 @P1 @phase3` |
| **M3.3** | 3 | P1 | Graph header wrap (320/375/480) | 3 | `@M3.3 @P1 @phase3` |
| **M3.4** | 3 | P1 | MCP Setup card no overflow + word-break | 1 | `@M3.4 @P1 @phase3` |
| **M4.1** | 4 | P1 | Profile 4 tabs switch + 44px tabs | 2 (320/375) | `@M4.1 @P1 @phase4` |
| **M4.2** | 4 | P1 | Save button always reachable + guide-fab not blocking | 1 | `@M4.2 @P1 @phase4` |
| **M5.1** | 5 | P2 | Every form-input has `<label for=>` or aria-label | 1 (programmatic scan) | `@M5.1 @P2 @phase5` |
| **M5.2** | 5 | P2 | Every icon-only button has aria-label or visible text | 1 (8 pages scan) | `@M5.2 @P2 @phase5` |
| **M6.1** | 6 | — | Final: 0 horizontal overflow on any page | 3 (3vp) | `@M6.1 @phase6` |
| **M6.2** | 6 | — | Desktop 1366px: no regression (sidebar/guide-fab/sources visible) | 1 | `@M6.2 @phase6 @desktop` |

### How เขียว use this

```bash
# Single milestone (during implementation)
PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test --grep "@M1.1"

# All of one phase (after committing the phase)
PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test --grep "@phase1"

# Auto-runner with fail-fast (recommended)
python scripts/check_milestone.py M1.1
python scripts/check_milestone.py phase1
python scripts/check_milestone.py --until M3.4

# Final integration run before commit "chore"
PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test v9.2.1-milestones --reporter=list
```

### How ฟ้า reviews

1. รัน `python scripts/check_milestone.py` (full sweep) → ทุก milestone ต้อง pass
2. Manual smoke (Group G ด้านล่าง) บนของจริง
3. Regression specs (Group F) ต้อง pass

### Group F: Regression spec (รวม run หลัง M6.1+M6.2 ผ่าน)

- ✅ Existing `thorough-mobile.spec.js` + `thorough-pages.spec.js` + `v7.x specs` + `v9.2.0-ai-pack-builder.spec.js` ยัง pass
- ✅ `scripts/context_pack_correctness_smoke.py` ผ่าน (v9.0.1 regression)
- ✅ `scripts/admin_e2e_test.py` ผ่าน (v8.2.0 regression)
- ✅ Python syntax + JS syntax clean

### Group G: Manual smoke (User เป็นคนทำ post-merge)

- 📱 Real iPhone SE (1st gen) 320px — open profile + save / open generate token / zoom graph / open chat + toggle sources
- 📱 Real Pixel 5 — verify all P0 + chat sources toggle + 4 profile tabs swipe
- 📱 Real Android low-end (e.g. Galaxy A14) — verify scroll smoothness + toast no overlap FAB
- 💻 Desktop 1366px Chrome/Firefox/Safari — verify NO regression (sidebar always visible, guide-fab visible on most pages, sources-panel side-by-side)
- 🔍 NVDA / VoiceOver — verify form inputs read with label name + icon buttons announce purpose

---

## ✅ Done Criteria — Milestone-by-milestone

ตาราง 18 milestones ต้อง ✅ ทุกข้อก่อนนับ "done":

### Phase 1 (3 milestones — commit ก่อน move ไป Phase 2)
- [ ] **M1.1** ✅ — `npx playwright test --grep "@M1.1"` PASS
- [ ] **M1.2** ✅ — PASS (3 viewports + desktop guard)
- [ ] **M1.3** ✅ — PASS
- [ ] Phase 1 sweep: `--grep "@phase1"` PASS (~5 tests)
- [ ] Commit: `fix(ui): hide guide-fab + mobile chat sources + toast reposition [v9.2.1]`

### Phase 2 (5 milestones)
- [ ] **M2.1** ✅ — sidebar nav 44px (3 viewports)
- [ ] **M2.2** ✅ — toggle-btn 44px (3 viewports)
- [ ] **M2.3** ✅ — copy/zoom/icon/history 44px (3 viewports)
- [ ] **M2.4** ✅ — chip + select 44px (3 viewports)
- [ ] **M2.5** ✅ — toast-close 44px
- [ ] Phase 2 sweep: `--grep "@phase2"` PASS (~13 tests)
- [ ] Commit: `fix(ui): touch targets 44px (Apple HIG / WCAG 2.5.5) [v9.2.1]`

### Phase 3 (4 milestones)
- [ ] **M3.1** ✅ — Context Memory header wrap (3 viewports)
- [ ] **M3.2** ✅ — MCP Logs filter wrap (3 viewports)
- [ ] **M3.3** ✅ — Graph header wrap (3 viewports)
- [ ] **M3.4** ✅ — MCP Setup card no overflow @ 320
- [ ] Phase 3 sweep: `--grep "@phase3"` PASS (~10 tests)
- [ ] Commit: `fix(ui): responsive header wraps + inline-style cleanup [v9.2.1]`

### Phase 4 (2 milestones)
- [ ] **M4.1** ✅ — Profile 4 tabs switch (2 viewports)
- [ ] **M4.2** ✅ — Save button always reachable
- [ ] Phase 4 sweep: `--grep "@phase4"` PASS (3 tests)
- [ ] Commit: `feat(ui): profile modal split into 4 tabs [v9.2.1]`

### Phase 5 (2 milestones)
- [ ] **M5.1** ✅ — Every form-input has label association
- [ ] **M5.2** ✅ — Every icon-only button has aria-label
- [ ] Phase 5 sweep: `--grep "@phase5"` PASS (2 tests)
- [ ] Commit: `fix(a11y): label associations + aria-labels [v9.2.1]`

### Phase 6 (final integration)
- [ ] **M6.1** ✅ — Final mobile audit clean (3 viewports)
- [ ] **M6.2** ✅ — Desktop 1366px no regression
- [ ] Phase 6 sweep: `--grep "@phase6"` PASS (4 tests)
- [ ] Full milestone sweep: `python scripts/check_milestone.py` PASS
- [ ] Existing regression: thorough-mobile + thorough-pages + v7.x + v9.2.0-ai-pack-builder ยังผ่าน
- [ ] APP_VERSION bump 9.2.0 → 9.2.1 + cache-bust `?v=9.2.1` ทุก asset
- [ ] Memory updates: pipeline-state.md + last-session.md + session log
- [ ] Cleanup: temp audit specs + result dirs deleted
- [ ] Commit: `chore: bump APP_VERSION 9.2.1 + milestone spec + memory + cleanup [v9.2.1]`

---

## ⚠️ Risks / Open Questions

### Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|-----------|
| **R1** | `body.modal-open` toggle ผิด timing → guide-fab ไม่หายตอน modal เปิด | 🟠 Medium | MutationObserver + initial sync ใน `_initModalOpenObserver()` + manual smoke 6 modals ครบทุกตัว |
| **R2** | `:has()` selector ใน CSS ไม่ support บน Firefox <121 / Safari <15.4 | 🟡 Low | Backup ผ่าน `body.modal-open` class (JS-set) ที่ทำงานบนทุก browser → CSS `:has()` rule เป็น progressive enhancement |
| **R3** | Profile modal tab split — JS state ของ personality history (count badge) อาจ break เมื่อย้ายจาก `<details>` → `<section>` | 🟠 Medium | เก็บ `id` ของ history-count + functions เดิมไว้ทุกตัว — ทดสอบ 4 system history modals |
| **R4** | Touch target ขยาย 44px อาจทำให้ sidebar nav-items กิน vertical space เกินจอที่ 320×568 | 🟡 Low | `.sidebar-nav { overflow-y: auto }` มีอยู่แล้ว → scroll ภายใน sidebar OK |
| **R5** | `#chat-toggle-sources` button ใน chat-header อาจชนกับ `#chat-typing-status` indicator | 🟡 Low | typing-status `position: relative` + flex layout — โผล่ inline ไม่ overlap; verify ใน T-A5 manual |
| **R6** | Cache-bust `?v=9.1.1` change — user ที่มี SW cache อาจไม่ refresh | 🟢 Trivial | Hard refresh ครั้งแรกหลัง deploy (deploy notes) |
| **R7** | Label `for=id` regex find-replace อาจพลาด edge case (label nested หรือ multi-line) | 🟡 Low | Verify ทีละไฟล์ visually + grep `<label>(?![^<]*for=)` หาที่ตกหล่น |
| **R8** | Profile modal tabs ที่ 320px แคบมาก — 4 tabs label ยาว ("เชื่อมต่อ" 8 chars) อาจล้น | 🟢 Trivial | `.profile-tabs { overflow-x: auto }` + `flex: 0 0 auto` allow scroll horizontal — pattern เดียวกับ `.knowledge-tabs` |

### Open Questions (มี default ทุกข้อ)

| Q# | Question | Default | User override? |
|---|---------|---------|---------------|
| **Q1** | ปุ่ม `#chat-toggle-sources` ตำแหน่งไหน? (header / floating / sticky bottom) | **Header** (chat-header right side, ตาม pattern profile-indicator) | ระบุ override |
| **Q2** | Profile modal tab order? | **Account → Profile → Personality → Connectors** (frequency: บัญชี+โปรไฟล์ใช้บ่อยกว่า) | ระบุ override |
| **Q3** | Hide guide-fab บน modal เปิด — ใช้ JS body class หรือ CSS `:has()` only? | **Both** — JS เป็น primary (cross-browser), CSS `:has()` เป็น progressive enhancement | confirm |
| **Q4** | Touch target ขยาย 44px กระทบ desktop หรือไม่? | **No** — rule อยู่ใน `@media (max-width: 768px)` เท่านั้น | confirm |
| **Q5** | Sources-panel mobile = hide-by-default หรือ collapse-by-default (peek visible)? | **Hide-by-default** + reveal button — ลดความ cluttered | ระบุ override |
| **Q6** | Cleanup temp audit specs (mobile-audit-temp + mobile-audit-deep) — ลบ หรือ archive? | **ลบทิ้ง** — archive ใน git history พอ | ระบุ override |
| **Q7** | Ship v9.2.1 หลัง v9.2.0 ship แล้ว หรือ bundle? | **Ship v9.2.1 หลัง v9.2.0** — ลำดับ: user push v9.2.0 → ตรวจ AI builder ใน production → เริ่ม build v9.2.1 → ship | ระบุ override |
| **Q8** | Bottom 160px ของ toast-container บน mobile — เกินไปไหม (เหลือ ~408px content area ที่ 568px จอ)? | **Acceptable** — toast นานๆ ครั้ง, content scroll ได้ | ระบุ override |

---

## 📝 Notes for เขียว (gotchas + reuse patterns)

### Gotchas

1. **`body.modal-open` toggle ต้องตอบสนองทันที** — ใช้ MutationObserver ไม่ใช่ event listener (เพราะ legacy code ใช้ `.classList.add('hidden')` กระจายในหลาย function — ไม่มี single dispatch point)
2. **`#guide-fab` เปิดด้วย `style="display:none"` inline ใน HTML** — ต้องตรวจ `getComputedStyle` หรือ check `.hidden` + style ก่อนตัดสินใจ visible
3. **Cleanup HTML inline `style=` ก่อน apply CSS class** — มิฉะนั้น `style="width:200px"` จะ override flex rule
4. **Personality `<details>` → `<section>`** — ต้องเก็บ `id="personality-section"` + `id` ของ block เดิมไว้ (`block-mbti`, `block-enneagram`, etc.) ที่ JS reference
5. **`for=id` ต้อง match ID จริง** — verify ไม่มี typo (cd app.js + grep `getElementById\(['"][^'"]+['"]\)` cross-check กับ HTML)
6. **profile-tabs scroll horizontal บน 320** — `.profile-tabs { overflow-x: auto; -webkit-overflow-scrolling: touch }` + ลิ้น scrollbar `::-webkit-scrollbar { display: none }` (sidebar pattern)
7. **`bottom: 160px` ของ #toast-container** — เพิ่ม `@supports (padding: env(safe-area-inset-bottom))` rule สำหรับ iPhone notch (`bottom: calc(160px + env(safe-area-inset-bottom))`)
8. **Cache-bust ?v= update** — ใช้ sed/perl ทุกไฟล์ HTML แทน manual: `find legacy-frontend -name '*.html' -exec sed -i 's/?v=[0-9.]*/?v=9.2.1/g' {} +`
9. **Test order matters ใน mobile-fixes.spec.js** — login ก่อนเปิดหน้าต้อง auth (registerAndEnterApp helper)
10. **APP_VERSION bump ที่ 2 ที่** — `backend/config.py` + `legacy-frontend/app.html` sidebar label (memory v8.2.0 audit catch ว่า admin.html version drift)

### Reuse patterns

- ดู [shared.css:317-348](../../legacy-frontend/shared.css#L317-L348) — existing `@media (max-width: 768px)` 44px rule pattern → ขยายตาม
- ดู [styles.css:1656-1697](../../legacy-frontend/styles.css#L1656-L1697) — `.knowledge-tabs` + `.tab-btn` pattern → reuse สำหรับ `.profile-tabs` + `.profile-tab`
- ดู [styles.css:84-105](../../legacy-frontend/styles.css#L84-L105) — sidebar-toggle + backdrop pattern (mobile slide-in) → reference
- ดู [tests/e2e-ui/thorough-mobile.spec.js](../../tests/e2e-ui/thorough-mobile.spec.js) — viewport setup template
- ดู [tests/e2e-ui/v9.2.0-ai-pack-builder.spec.js](../../tests/e2e-ui/v9.2.0-ai-pack-builder.spec.js) — naming convention + structure

### Out-of-scope guard (ระหว่าง build อย่าทำ)

- ❌ Refactor inline styles → class wholesale (เก็บไว้ v9.3.0)
- ❌ DESIGN.md aspirational tokens (Inter Variable cv01/ss03)
- ❌ Light theme toggle
- ❌ Variable font subsetting
- ❌ SVG sprite consolidation
- ❌ D3 lazy load
- ❌ Cache strategy beyond `?v=` query string
- ❌ Browser compat A1-A8 (Firefox `:has()`, iOS 100vh, backdrop-filter)
- ❌ Profile modal restructure beyond tab split (e.g. inline edit mode)

ถ้าเจอประเด็นใหม่ที่ต้องตัดสิน → แจ้งผ่าน [inbox/for-แดง.md](../communication/inbox/for-แดง.md) ก่อนตัดสินใจ

---

## 📋 Pipeline Next

1. 🔴 **User review plan** — answer Q1-Q8 (หรือยอมรับ default ทุกข้อ)
2. 🟢 **User push v9.2.0 ก่อน** (4 commits ที่ค้างอยู่ + chore commit)
3. 🟢 **เขียวเริ่ม build v9.2.1** — Phase 1 → 6 milestone-by-milestone:
   - แต่ละ milestone: เขียน fix → `npx playwright test --grep "@Mx.y"` → pass → commit phase
   - เขียวต้อง pass ทุก milestone Mx.y ใน phase ก่อน move ไป phase ถัดไป
4. 🟢 **เขียว self-test final** — `python scripts/check_milestone.py` (ทุก 18 milestones) + manual smoke desktop
5. 🔵 **ฟ้า review** — verify ทุก milestone + regression suite (existing specs) + commit messages + memory + visual smoke 3 real devices
6. 🔴 **User approve + push + deploy** v9.2.1

---

## 📊 Why this plan is good (self-check)

- ✅ **Scope ชัด** — 50 fixes × 6 phases × 18 milestones × ~38 test cases
- ✅ **Milestone-driven verification** — เขียวรู้ทันทีว่า fix ตัวไหนทำลายอะไร (fail-fast)
- ✅ **Audit-driven** — ทุก fix mapped ไป Playwright finding (concrete, ไม่ใช่ guess)
- ✅ **No scope creep** — ตัด browser compat / perf / DESIGN.md aspirational ออก clearly
- ✅ **Backward compat** — desktop unchanged (ทุก rule ใน `@media (max-width: 768px)`)
- ✅ **Reusable patterns** — extend existing `@media` rule + tab pattern + observer pattern
- ✅ **Risks ระบุ + mitigation ครบ** — 8 risks × all mitigated
- ✅ **CSS code samples** — เขียวคัดลอกใช้ได้ตรงๆ ลด ambiguity
- ✅ **Defaults ชัด** — Q1-Q8 มี default ทุกข้อ user ไม่ตอบก็ proceed ได้
- ✅ **Verification path** — Playwright spec + Python wrapper ที่ ฟ้า/CI ใช้ตรวจ regression ได้
