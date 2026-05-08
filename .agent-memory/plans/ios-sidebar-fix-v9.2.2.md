# Plan: iOS Sidebar Footer Visibility Fix — v9.2.2

> **Status:** `plan_pending_approval`
> **Author:** 🔴 แดง (Daeng) — 2026-05-07
> **Foundation:** master HEAD `7a1625d` v9.2.1 (deployed)
> **Version bump:** 9.2.1 → **9.2.2** (CSS+JS patch — mobile-only)
> **Scope philosophy:** **One bug, fixed correctly** — iOS Safari/Chrome ตัด sidebar footer (TH|EN + Profile + email + logout) เพราะ classic 100vh issue. ไม่เกี่ยว layout อื่น
> **Estimated effort:** เขียว ~1-1.5 ชม. + ฟ้า ~0.5 ชม.
> **Risk:** 🟢 Low — additive CSS + 4-line JS, ไม่กระทบ desktop / data / API
>
> **Verification model:** Milestone-driven (ทุก fix → Playwright assert ก่อน commit)

---

## 🎯 Goal & Context

### User-reported evidence (2026-05-07, from real iPhone screenshots)

> "ในหน้าจอของไอโฟนมันมีการตกจอเลย ในส่วนของชื่อผู้ใช้ ต้องใช้พลิกหน้าจอเราถึงจะกดปุ่มได้"

จาก 2 screenshots ที่ user ส่ง:
- **Screenshot 1** (sidebar เปิดใหม่): เห็น header + nav 8 items + sidebar-stats (ไฟล์ 23 / โหนด 46 / แพ็ก 1 / คอลเลกชัน 9 / ความสัมพันธ์ 86 / โทเค็น 3) — แต่ **TH|EN toggle + Profile + bossok2546@gmail.com + logout ไม่ปรากฏ** (อยู่ใต้ Safari/Chrome bottom toolbar)
- **Screenshot 2** (เลื่อน scroll ภายใน sidebar): เห็นทั้ง stats + TH|EN + Profile + email + logout — แต่ user ต้อง scroll/หมุนจอ

### Root cause analysis

**The classic iOS 100vh bug:**

```
┌─────────────────────────┐
│ iOS Safari URL bar      │  ~88px chrome (top)
├─────────────────────────┤
│ ↑                       │
│  Layout viewport (100vh)│  ← `position: fixed; top:0; bottom:0`
│  = full screen including│     ผูกกับขอบ layout
│  chrome                 │
│                         │
│ ▼ sidebar-footer ที่นี่  │  ← พิกัดถูกต้องแต่...
├─────────────────────────┤
│ iOS Safari toolbar      │  ~88px chrome (bottom)
└─────────────────────────┘  ← ...โดน toolbar บัง
```

**ที่อยู่ใน CSS ปัจจุบัน (commit `7a1625d`):**

```css
/* legacy-frontend/styles.css */
.app-container { height: 100vh; overflow: hidden; }    /* line 32 */
.sidebar { height: 100vh; overflow: hidden; }           /* line 51 */

@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;       /* ← anchored to layout viewport, behind iOS toolbar */
    /* ไม่มี height override → inherit 100vh */
  }
}
```

**Why scroll "works" temporarily:** เมื่อ user เลื่อน scroll → iOS chrome หดลง → visual viewport ขยาย → footer โผล่. แต่ผู้ใช้ใหม่ไม่รู้ จึงคิดว่า "ตกจอ"

**ภาษา CSS ไม่มีอะไรช่วย:** ไม่มี `100dvh`, `100svh`, `safe-area-inset-bottom`, `-webkit-fill-available`, JS `--vh` calculation ใน codebase ทั้งหมด (verified 2026-05-07 grep)

### Goals

1. **Sidebar footer ต้องเห็นโดยไม่ scroll** บนทุก iPhone ขนาดมาตรฐาน (SE 320 / 12 mini 375 / 14 393 / Pro Max 430)
2. **ไม่กระทบ desktop** — sidebar ทำงานเหมือนเดิมที่ ≥769px
3. **Cross-browser** — ทำงานบน Safari iOS (12+), Chrome iOS, Android Chrome, Firefox iOS
4. **Backward compat** — Safari < 15.4 ที่ไม่มี `dvh` ต้อง fallback ผ่าน JS

### Non-goals

- ❌ แก้ทุก `100vh` ใน codebase (มี 9 instances) — แก้เฉพาะที่กระทบ sidebar ก่อน
- ❌ แก้ touch targets / responsive overflow / a11y (อยู่ใน plan v9.2.x mobile-fixes ที่ยัง pending)
- ❌ Tabbed profile modal (ก็อยู่ใน plan ใหญ่)
- ❌ Performance optimization

---

## 🔬 Research: Solution Strategies (เลือกหนึ่ง + ผสม)

### Strategy A — `100dvh` (Dynamic Viewport Height)
**Browser support:** Safari 15.4+ (Mar 2022), Chrome 108+, Firefox 101+, Samsung Internet 19+
**Behavior:** เท่ากับ visual viewport — auto-adjust เมื่อ chrome show/hide
**Pros:** Cleanest, single line, no JS
**Cons:** ไม่ support iOS Safari < 15.4 (~5-8% market 2026)

```css
.sidebar { height: 100dvh; }
```

### Strategy B — `100svh` (Small Viewport Height)
**Browser support:** เหมือน `dvh`
**Behavior:** assume max chrome — content fit smallest possible viewport เสมอ
**Pros:** ไม่ jump เมื่อ chrome hide
**Cons:** Wasted space when chrome hidden

### Strategy C — JS `--vh` Custom Property (legacy fallback)
**Browser support:** All
**Behavior:** Set `--vh = window.innerHeight * 0.01` ทุกครั้ง resize/orientation
**Pros:** Universal compatibility, no Safari version concern
**Cons:** Resize/orientation event lag (~100ms flash), JS dependency

```js
function setVh() {
  document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
}
setVh();
window.addEventListener('resize', setVh);
window.addEventListener('orientationchange', setVh);
```
```css
.sidebar { height: calc(var(--vh, 1vh) * 100); }
```

### Strategy D — Safe Area Inset (notch/home indicator)
**Browser support:** Safari 11.1+, Chrome 69+
**Behavior:** Reserve space สำหรับ iPhone notch + home indicator
**Pros:** ครอบคลุม iPhone X+ (notch + home bar)
**Cons:** ไม่แก้ classic 100vh — ใช้ร่วมกับ A/B/C

```css
.sidebar { padding-bottom: env(safe-area-inset-bottom); }
```

### Strategy E — `-webkit-fill-available` (legacy iOS)
**Browser support:** Safari only — non-standard
**Behavior:** WebKit-specific หา visual viewport
**Pros:** ทำงานบน iOS เก่ามาก
**Cons:** Non-standard, deprecated, Firefox/Chrome ไม่รองรับ

### Strategy F — Visual Viewport API
**Browser support:** Safari 13+, Chrome 61+
**Behavior:** ใช้ `window.visualViewport.height` direct
**Pros:** Real-time updates รวม keyboard show/hide
**Cons:** ซับซ้อนเกินสำหรับ patch นี้ — เก็บไว้ v9.3.0+

### 🏆 Recommended: **A + C + D combo (progressive enhancement)**

```css
.sidebar {
  /* Universal fallback (works everywhere) */
  height: 100vh;

  /* JS-set fallback for Safari < 15.4 */
  height: calc(var(--vh, 1vh) * 100);

  /* Modern dvh — overrides above when supported */
  height: 100dvh;

  /* Bottom space for iPhone home indicator + safety buffer */
  padding-bottom: env(safe-area-inset-bottom);
}
```

CSS cascade ทำงาน: ถ้า browser support `dvh` → ใช้ตัวสุดท้าย. ถ้า support แค่ `calc(var(--vh)...)` → ใช้กลาง. ถ้า support แค่ `100vh` → ใช้แรก.

JS `--vh` setter ทำงานทุก browser, ไม่กระทบ — ถ้าใช้ `dvh` แล้ว `--vh` จะถูก ignored เพราะ dvh declared หลัง

---

## 📁 Files to Create / Modify

| File | Action | Reason |
|------|--------|--------|
| [legacy-frontend/styles.css](../../legacy-frontend/styles.css) | **modify** | (1) `.sidebar` line 51: เพิ่ม dvh + var(--vh) fallback (2) `.app-container` line 32: เพิ่ม dvh fallback (3) mobile sidebar block line 86-95: เพิ่ม `padding-bottom: env(safe-area-inset-bottom)` (~15 lines) |
| [legacy-frontend/landing.css](../../legacy-frontend/landing.css) | **modify** | Line 14: `.landing-page { min-height: 100vh; }` → เพิ่ม dvh fallback (~3 lines) |
| [legacy-frontend/shared.css](../../legacy-frontend/shared.css) | **modify** | Line 77: `body { height: 100vh; }` → เพิ่ม dvh + var(--vh) fallback + safe-area (~5 lines) |
| [legacy-frontend/app.js](../../legacy-frontend/app.js) | **modify** | เพิ่ม `_setVh()` + register events (~10 lines) ที่ top ของ §A SHARED UTILITIES (รัน ASAP ก่อน first paint) |
| [legacy-frontend/landing.js](../../legacy-frontend/landing.js) | **modify** | (1) ตรวจ `_setVh` มาจาก app.js แล้ว (loaded ก่อน) — ไม่ต้องเพิ่ม. แต่ถ้าหน้า landing ไม่ load app.js ต้องเพิ่ม. **Verify ก่อน:** `landing.html` loads app.js? ⚠️ ตรวจ |
| [backend/config.py](../../backend/config.py) | **modify** | `APP_VERSION = "9.2.2"` |
| [legacy-frontend/app.html](../../legacy-frontend/app.html) | **modify** | sidebar `<span class="logo-version">v9.2.2</span>` |
| HTML cache-bust | **modify** | `?v=9.2.1` → `?v=9.2.2` ทั้ง 5 HTML files |
| [tests/e2e-ui/v9.2.2-ios-sidebar.spec.js](../../tests/e2e-ui/) | **create** | 6 milestones × ~10 cases — verify ทุก iPhone size + Android + Desktop |

**Verify dependency:**
```bash
grep -l "app.js" legacy-frontend/*.html
```
หาก `landing.html` ไม่โหลด `app.js` → JS `_setVh` ต้องเพิ่มใน `landing.js` ด้วย (~3 lines)

**ไม่แตะ:** Backend logic, database, API, MCP, AI builder, plans อื่น

---

## 🧪 Milestone-driven Verification Strategy

ตาม pattern ที่ user request 2026-05-07: "เช็คด้วย Playwright ทุก milestone ทุกการแก้ไข"

| Milestone | What | Test viewport | # tests |
|-----------|------|---------------|---------|
| **M1.1** | dvh + JS --vh combo applied to .sidebar | 320 / 375 / 393 / 430 | 4 |
| **M1.2** | sidebar-footer visible without scroll | iPhone SE (375×667) + iPhone 14 (393×852) + iPhone Pro Max (430×932) | 3 |
| **M1.3** | safe-area-inset-bottom respected | iPhone with simulated home indicator | 1 |
| **M1.4** | JS fallback path (`--vh` custom property) | All viewports — verify CSS var set | 1 |
| **M1.5** | Resize/orientation event handler | Simulate orientation change | 1 |
| **M1.6** | Desktop no regression | 1366×768 + 1920×1080 | 2 |

**Run individual:** `npx playwright test --grep "@M1.1"`
**Run all:** `npx playwright test v9.2.2-ios-sidebar`

---

## 🛠️ Step-by-Step Implementation

### Phase 1 — CSS dvh fallback chain (~15 min)

**Edit [legacy-frontend/styles.css:30-52](../../legacy-frontend/styles.css#L30):**

```css
/* v9.2.2 — iOS viewport fix: dvh + JS --vh fallback for Safari < 15.4 */
.app-container {
  display: flex;
  /* Fallback chain: 100vh → calc(--vh) → 100dvh */
  height: 100vh;
  height: calc(var(--vh, 1vh) * 100);
  height: 100dvh;
  overflow: hidden;
}

/* ─── SIDEBAR ─── */
.sidebar {
  width: var(--sidebar-width);
  background: var(--bg-secondary);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  /* v9.2.2 — same fallback chain */
  height: 100vh;
  height: calc(var(--vh, 1vh) * 100);
  height: 100dvh;
  overflow: hidden;
}
```

**Edit [legacy-frontend/styles.css:84-105](../../legacy-frontend/styles.css#L84) mobile sidebar:**

```css
@media (max-width: 768px) {
  .sidebar-toggle { display: inline-flex; }
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    /* v9.2.2 — explicit height override (position:fixed + top/bottom may not always fill on iOS) */
    height: 100vh;
    height: calc(var(--vh, 1vh) * 100);
    height: 100dvh;
    /* v9.2.2 — Reserve space for iPhone home indicator (notch on bottom) */
    padding-bottom: env(safe-area-inset-bottom);
    transform: translateX(-100%);
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    z-index: 9800;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.5);
  }
  /* ... rest unchanged ... */
}
```

**Edit [legacy-frontend/shared.css:71-78](../../legacy-frontend/shared.css#L71):**

```css
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  background: var(--bg-primary);
  color: var(--text-primary);
  line-height: 1.6;
  overflow: hidden;
  /* v9.2.2 — fallback chain */
  height: 100vh;
  height: calc(var(--vh, 1vh) * 100);
  height: 100dvh;
}
```

**Edit [legacy-frontend/landing.css:13-21](../../legacy-frontend/landing.css#L13):**

```css
.landing-page {
  /* v9.2.2 — landing scrolls naturally; fallback chain for 100vh */
  min-height: 100vh;
  min-height: calc(var(--vh, 1vh) * 100);
  min-height: 100dvh;
  background: #060a14;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  overflow-x: hidden;
  position: relative;
}
```

### Phase 2 — JS `--vh` setter (~10 min)

**Edit [legacy-frontend/app.js](../../legacy-frontend/app.js) — เพิ่ม block ใหม่ก่อน localStorage migration (line ~28):**

```js
// ═══════════════════════════════════════════
// iOS VIEWPORT FIX (v9.2.2)
// ═══════════════════════════════════════════
// Fallback for Safari < 15.4 ที่ไม่ support 100dvh.
// CSS uses cascading height: 100vh → calc(var(--vh)*100) → 100dvh.
// This block sets --vh to the actual visual viewport so older browsers
// don't render content under iOS Safari URL bar / bottom toolbar.
//
// Why prepend (run before render): if we wait for DOMContentLoaded,
// users see a flash of incorrect layout (sidebar footer hidden) before fix kicks in.
(() => {
  const setVh = () => {
    document.documentElement.style.setProperty('--vh', `${window.innerHeight * 0.01}px`);
  };
  setVh();
  // Re-set on resize (chrome show/hide on scroll, keyboard appear, rotate)
  let timer;
  const debouncedSet = () => {
    clearTimeout(timer);
    timer = setTimeout(setVh, 100);
  };
  window.addEventListener('resize', debouncedSet);
  window.addEventListener('orientationchange', () => {
    // Orientation change needs longer delay — chrome animation completes ~300ms
    setTimeout(setVh, 350);
  });
})();
```

**Verify landing.html loads app.js (ก่อน edit landing.js):**

```bash
grep -n 'src=.*app.js' legacy-frontend/landing.html
```

**ถ้าไม่มี** → เพิ่ม block เดียวกันใน `landing.js` (top of file)
**ถ้ามี** (ตามที่ memory บอกใน "Frontend Architecture") → ไม่ต้องแก้ landing.js

### Phase 3 — Version bump + cache-bust (~5 min)

```bash
# Cache-bust update
find legacy-frontend -name '*.html' -exec sed -i 's/?v=[0-9.]*/?v=9.2.2/g' {} +

# APP_VERSION
sed -i 's/APP_VERSION = "9.2.1"/APP_VERSION = "9.2.2"/' backend/config.py

# Sidebar version label
sed -i 's|<span class="logo-version">v9.2.1</span>|<span class="logo-version">v9.2.2</span>|' legacy-frontend/app.html
```

**Verify:**
```bash
grep -r "9.2.1" legacy-frontend/ backend/config.py | grep -v "v8\|v7"
# Expect: 0 results (all updated to 9.2.2)
```

### Phase 4 — Smoke + spec creation (~30 min)

#### 4.1 Test spec — [tests/e2e-ui/v9.2.2-ios-sidebar.spec.js](../../tests/e2e-ui/)

```js
// @ts-check
const { test, expect, devices } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

const IPHONE_SIZES = [
  { name: "iphone-se-1", w: 320, h: 568 },
  { name: "iphone-12-mini", w: 375, h: 667 },
  { name: "iphone-14", w: 393, h: 852 },
  { name: "iphone-14-pro-max", w: 430, h: 932 },
];

// Helper — open mobile sidebar + return footer reachability
async function openSidebarAndCheckFooter(page) {
  const hamburger = page.locator("#sidebar-toggle");
  if (await hamburger.isVisible()) await hamburger.click();
  await page.waitForTimeout(300);
  const footer = page.locator(".sidebar-footer");
  await expect(footer).toBeAttached();
  const fBox = await footer.boundingBox();
  const vp = page.viewportSize();
  return { footerBottom: fBox?.y + fBox?.height, viewportH: vp?.height };
}

// ─── M1.1: dvh + --vh fallback applied ───
test.describe("M1.1 — dvh fallback chain @M1.1", () => {
  for (const size of IPHONE_SIZES) {
    test(`@${size.w}x${size.h} sidebar height matches viewport`, async ({ page }) => {
      await page.setViewportSize({ width: size.w, height: size.h });
      await registerAndEnterApp(page);
      // Verify --vh CSS variable is set (JS fallback active)
      const vhValue = await page.evaluate(() =>
        getComputedStyle(document.documentElement).getPropertyValue('--vh').trim()
      );
      expect(vhValue, `--vh must be set on ${size.name}`).toMatch(/[0-9.]+px/);
      // Sidebar height should equal viewport height (within 1px tolerance)
      const sidebarH = await page.locator(".sidebar").evaluate(el => el.offsetHeight);
      expect(Math.abs(sidebarH - size.h)).toBeLessThanOrEqual(2);
    });
  }
});

// ─── M1.2: sidebar-footer visible without scroll ───
test.describe("M1.2 — footer visible without scroll @M1.2", () => {
  for (const size of IPHONE_SIZES.slice(1)) { // skip 320 — too cramped, M1.3 handles
    test(`@${size.w}x${size.h}`, async ({ page }) => {
      await page.setViewportSize({ width: size.w, height: size.h });
      await registerAndEnterApp(page);
      const { footerBottom, viewportH } = await openSidebarAndCheckFooter(page);
      // footer.bottom must be ≤ viewport.height (no overflow)
      expect(footerBottom, `footer bottom ${footerBottom} > viewport ${viewportH}`).toBeLessThanOrEqual(viewportH + 2);
      // Footer items must be visible (lang-toggle, profile-trigger, btn-logout)
      await expect(page.locator("#lang-toggle")).toBeVisible();
      await expect(page.locator("#profile-trigger")).toBeVisible();
      await expect(page.locator("#btn-logout")).toBeVisible();
    });
  }
});

// ─── M1.3: 320 iPhone SE 1st gen — content too tall, must scroll inside sidebar ───
test("M1.3 — 320×568 sidebar scrollable when content overflows @M1.3", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 568 });
  await registerAndEnterApp(page);
  const hamburger = page.locator("#sidebar-toggle");
  if (await hamburger.isVisible()) await hamburger.click();
  await page.waitForTimeout(300);
  // sidebar-nav (flex:1) must have overflow-y auto so user can scroll inside
  const overflowY = await page.locator(".sidebar-nav").evaluate(el => getComputedStyle(el).overflowY);
  expect(overflowY).toMatch(/auto|scroll/);
  // After scroll, footer should be visible
  await page.locator(".sidebar-nav").evaluate(el => el.scrollTop = el.scrollHeight);
  await page.waitForTimeout(200);
  await expect(page.locator("#btn-logout")).toBeVisible();
});

// ─── M1.4: JS fallback path verified ───
test("M1.4 — --vh updates on resize @M1.4", async ({ page }) => {
  await page.setViewportSize({ width: 393, height: 852 });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  const before = await page.evaluate(() =>
    parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--vh'))
  );
  expect(before).toBeCloseTo(8.52, 0); // 852 * 0.01
  // Resize down
  await page.setViewportSize({ width: 393, height: 600 });
  await page.waitForTimeout(200);
  const after = await page.evaluate(() =>
    parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--vh'))
  );
  expect(after).toBeCloseTo(6.0, 0);
  expect(after).toBeLessThan(before);
});

// ─── M1.5: orientation change ───
test("M1.5 — orientation change updates --vh @M1.5", async ({ page }) => {
  await page.setViewportSize({ width: 393, height: 852 }); // portrait
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  const portrait = await page.evaluate(() =>
    parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--vh'))
  );
  // Simulate landscape
  await page.setViewportSize({ width: 852, height: 393 });
  await page.evaluate(() => window.dispatchEvent(new Event('orientationchange')));
  await page.waitForTimeout(400); // orientation handler delay
  const landscape = await page.evaluate(() =>
    parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--vh'))
  );
  expect(landscape).toBeCloseTo(3.93, 0);
  expect(landscape).not.toBeCloseTo(portrait, 0);
});

// ─── M1.6: Desktop no regression ───
test("M1.6 — desktop sidebar unchanged @M1.6 @desktop", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await registerAndEnterApp(page);
  // sidebar visible by default (no hamburger)
  await expect(page.locator(".sidebar")).toBeVisible();
  await expect(page.locator("#sidebar-toggle")).not.toBeVisible();
  // Footer items visible without action
  await expect(page.locator("#lang-toggle")).toBeVisible();
  await expect(page.locator("#btn-logout")).toBeVisible();
  // Sidebar height should match viewport
  const sidebarH = await page.locator(".sidebar").evaluate(el => el.offsetHeight);
  expect(Math.abs(sidebarH - 768)).toBeLessThanOrEqual(2);
});

// ─── M1.7 (bonus): Real iOS WebKit emulation ───
test.describe("M1.7 — WebKit/iOS Safari emulation @M1.7", () => {
  test.use({ ...devices['iPhone 14'] });
  test("real device preset — sidebar footer visible", async ({ page }) => {
    await registerAndEnterApp(page);
    const hamburger = page.locator("#sidebar-toggle");
    if (await hamburger.isVisible()) await hamburger.click();
    await page.waitForTimeout(400);
    await expect(page.locator("#btn-logout")).toBeVisible();
    await expect(page.locator("#lang-toggle")).toBeVisible();
  });
});
```

**Note:** M1.7 ใช้ Playwright `devices['iPhone 14']` preset ที่ accurate ที่สุดสำหรับ iOS WebKit emulation. ต้องการ `webkit` browser project ใน playwright.config.js — ถ้าไม่มี ต้องเพิ่ม:

```js
// playwright.config.js — เพิ่ม project
projects: [
  { name: "chromium", use: { browserName: "chromium" } },
  { name: "webkit", use: { browserName: "webkit" } }, // NEW
],
```

#### 4.2 Memory updates

- `current/pipeline-state.md`:
  - Move "v9.2.2 iOS Sidebar Fix" จาก plan_pending → built_pending_review (หลัง build)
- `current/last-session.md`: summary
- `history/session-logs/2026-05-07-ios-sidebar-fix-v9.2.2.md`

#### 4.3 Commits (3 logical)

1. `fix(ui): iOS 100vh fallback chain (dvh + --vh + safe-area) [v9.2.2]`
2. `feat(js): viewport height observer for Safari < 15.4 [v9.2.2]`
3. `chore: bump APP_VERSION 9.2.2 + cache-bust + smoke + memory [v9.2.2]`

---

## ✅ Done Criteria — Milestone-by-milestone

- [ ] **M1.1** ✅ — dvh + --vh applied (4 viewports × `--vh` set + sidebar.height ≈ viewport.h)
- [ ] **M1.2** ✅ — footer visible without scroll @ 375/393/430
- [ ] **M1.3** ✅ — 320×568 sidebar-nav has `overflow-y: auto` + footer reachable via scroll
- [ ] **M1.4** ✅ — `--vh` updates on resize
- [ ] **M1.5** ✅ — `--vh` updates on orientationchange
- [ ] **M1.6** ✅ — Desktop 1366px unchanged
- [ ] **M1.7** ✅ — WebKit/iPhone 14 preset — footer visible
- [ ] Playwright sweep: `npx playwright test v9.2.2-ios-sidebar` ALL PASS
- [ ] Existing regression: `thorough-mobile.spec.js` + `thorough-pages.spec.js` + `v7.x` ยังผ่าน
- [ ] APP_VERSION bump 9.2.1 → 9.2.2 + cache-bust `?v=9.2.2`
- [ ] Memory updates done
- [ ] Commits 3 logical groups

---

## ⚠️ Risks / Open Questions

### Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|-----------|
| **R1** | `100dvh` ไม่ทำงานใน Safari < 15.4 (~5% market 2026) | 🟢 Low | Cascade fallback: `100vh` → `calc(var(--vh)*100)` → `100dvh` — older browsers ใช้ JS path |
| **R2** | JS `--vh` setter race เมื่อ first paint (sidebar render ก่อน JS run) | 🟡 Medium | Block prepended at top of app.js (before localStorage migration + state) — runs synchronously ก่อน DOM render. Inline IIFE = no module loading delay |
| **R3** | `env(safe-area-inset-bottom)` ทำให้ desktop sidebar มี bottom padding เกิน | 🟢 Low | Rule อยู่ใน `@media (max-width: 768px)` เท่านั้น |
| **R4** | Resize event spam ตอน iOS chrome animate show/hide | 🟡 Medium | Debounce 100ms + orientationchange longer 350ms |
| **R5** | landing.js + app.js dual JS path — ถ้า landing.html ไม่ load app.js → JS `--vh` ไม่ทำงานบน landing | 🟡 Medium | Verify ก่อน implement: `grep 'app.js' landing.html`. ถ้าต้อง add ใน landing.js → 3 lines เพิ่ม |
| **R6** | `100dvh` cascade override JS `--vh` ในบราว์เซอร์ใหม่ → user resize chrome → flicker | 🟢 Low | dvh เป็น native property — auto-update ไม่ต้อง JS. JS path inactive when dvh works |
| **R7** | Playwright `devices['iPhone 14']` preset ไม่ simulate URL bar/toolbar — test ยัง limited | 🟠 Medium | Add manual smoke step ใน Done Criteria — user verify บน real iPhone หลัง deploy |
| **R8** | Cache-bust `?v=9.2.2` — user เก่ายังเห็น v9.2.1 cached HTML | 🟢 Trivial | Hard refresh post-deploy (deploy notes) |

### Open Questions (มี default ทุกข้อ)

| Q# | Question | Default |
|---|---------|---------|
| **Q1** | ใช้ dvh + JS combo หรือ dvh only (drop legacy < Safari 15.4)? | **Combo** — universal compat, 5-8% Safari < 15.4 ยังใช้ |
| **Q2** | Apply fallback ที่ทุก `100vh` instance (9 จุด) หรือเฉพาะ sidebar/body/app-container? | **Critical 4 จุด** (sidebar + app-container + body + landing) — graph + chat + page ใช้ flex layout ที่จะ inherit |
| **Q3** | `padding-bottom: env(safe-area-inset-bottom)` apply ที่ sidebar mobile-only หรือ universal? | **Mobile-only** — iPhone home indicator irrelevant ที่ desktop |
| **Q4** | Debounce resize ที่ 100ms หรือ 200ms? | **100ms** — ตอบสนองเร็ว แต่ไม่ thrash |
| **Q5** | Add WebKit project ใน playwright.config.js? | **Yes** — M1.7 test ใช้, future iOS-specific tests ใช้ได้อีก |
| **Q6** | Run iOS sidebar fix ก่อน หรือรวมกับ v9.3.0 Share Pack? | **ก่อน** — bug critical, ผู้ใช้ปัจจุบันได้รับผลกระทบ. Share Pack feature ใหม่ไม่ urgent |
| **Q7** | M1.3 (320×568): scroll inside sidebar OK หรือ collapse stats เพื่อให้ footer fit? | **Scroll OK** — collapse stats ซับซ้อน + 320×568 = iPhone SE 1st gen เก่ามาก, niche |
| **Q8** | landing.css `.landing-page` ก็ apply fallback chain ด้วย? | **Yes** — ถึงแม้ landing scroll ปกติ แต่ `min-height: 100vh` ทำให้ first render ผิดถ้าไม่ fix |

---

## 📝 Notes for เขียว (gotchas + reuse patterns)

### Gotchas

1. **CSS cascade ลำดับสำคัญ** — `100vh` → `calc(var(--vh)*100)` → `100dvh` ตามลำดับนี้. ถ้า dvh declared ก่อน — older browser ที่ ignore dvh ก็ ignore line นี้แต่ใช้ vh ก่อน
2. **JS IIFE ต้องอยู่ก่อน state initialization** — เพราะ `_setVh()` set CSS var ที่ใช้ก่อน first render. ห้ามอยู่ใน `initAppData()` หรือ `DOMContentLoaded`
3. **Debounce timer ต้อง clear ก่อน set ใหม่** — ป้องกัน orphan callbacks
4. **iOS Safari 100vh "feature"** — ไม่ใช่ bug ตามคำของ Apple. เขาตั้งใจให้ fixed elements อยู่ใต้ chrome เพื่อให้ UX scroll-to-hide chrome เป็นไปได้. ดังนั้น `bottom: 0` element โดน chrome บัง = "intended"
5. **`safe-area-inset-bottom` = 0 บน devices ที่ไม่มี notch** — ไม่ทำให้ desktop เพี้ยน
6. **`-webkit-fill-available`** ที่ดูเก่าๆ ใน Stack Overflow → **อย่าใช้** — non-standard, deprecated
7. **Landing page boots ก่อน auth** — landing.html อาจไม่ load app.js (ตรวจ + decision)
8. **Cache-bust apply ทุกไฟล์ HTML** — ใช้ sed oneliner ไม่ใช่ manual edit
9. **`dvh` ทำงานได้ดีเมื่อ user scroll** — เพราะ visual viewport อัพเดทเอง. แต่ครั้งแรก paint อาจใช้ `lvh` (large) → flash brief. JS fallback คือ insurance
10. **Resize event ที่ Android Chrome** — bottom toolbar ก็ hide on scroll เหมือน iOS. JS path ทำงานเหมือนกัน

### Reuse patterns

- ดู [styles.css:52-105](../../legacy-frontend/styles.css#L52) — sidebar mobile rule pattern → modify in place
- ดู [shared.css:317-348](../../legacy-frontend/shared.css#L317) — existing mobile media query → ใส่ rule ใหม่ใน @media block ที่มีอยู่
- ดู [tests/e2e-ui/thorough-mobile.spec.js](../../tests/e2e-ui/thorough-mobile.spec.js) — viewport setup template
- ดู [tests/e2e-ui/v9.2.0-ai-pack-builder.spec.js](../../tests/e2e-ui/v9.2.0-ai-pack-builder.spec.js) — naming + structure
- ดู [docs/iOS-Safari-100vh-issue](https://benfrain.com/youve-set-css-element-100vh-need-set-100dvh) (external research)

### Out-of-scope guard

❌ ไม่แก้ touch targets / responsive overflow / a11y / profile modal split — all queued ใน plan ใหญ่ (ui-mobile-fixes-v9.1.1.md ที่ rewrite เป็น v9.3.x ภายหลัง)
❌ ไม่เพิ่ม Visual Viewport API — เก็บไว้ v9.3.0+
❌ ไม่ refactor 9 `100vh` instances ทั้งหมด — แก้เฉพาะ critical 4 ตัว (sidebar + app-container + body + landing)
❌ ไม่แตะ graph/chat layout ที่ใช้ 100vh — ปัญหาต่างกัน, defer

ถ้าเจอประเด็นใหม่ที่ต้องตัดสิน → แจ้งผ่าน [inbox/for-แดง.md](../communication/inbox/for-แดง.md) ก่อน

---

## 📋 Pipeline Next

1. 🔴 **User review plan** — answer Q1-Q8 (default ทุกข้อ)
2. 🟢 **เขียวเริ่ม build** — Phase 1 (CSS) → M1.1 verify → Phase 2 (JS) → M1.4-1.5 verify → Phase 3 (version) → Phase 4 (spec + memory)
3. 🟢 **เขียว self-test** — `npx playwright test v9.2.2-ios-sidebar` PASS + manual smoke desktop
4. 🔵 **ฟ้า review** — verify 7 milestones + regression + commit messages
5. 🔴 **User push + deploy + manual smoke บน real iPhone** ✅ — verify ปุ่ม logout/email กดได้โดยไม่หมุนจอ

---

## 📊 Why this plan is good (self-check)

- ✅ **Scope ชัด**: 1 bug, 4 files, ~40 lines diff total
- ✅ **Evidence-based**: User screenshots ยืนยัน + grep confirm ไม่มี existing fix
- ✅ **Research-backed**: 6 strategies analyzed, recommended hybrid (A+C+D)
- ✅ **Cross-browser**: dvh (modern) + JS fallback (legacy) + safe-area (notch)
- ✅ **Backward compat**: desktop unchanged (rule mobile-only)
- ✅ **Milestone-driven verification**: 7 milestones × Playwright assert ก่อน commit
- ✅ **Risk + mitigation ครบ**: 8 risks × all mitigated
- ✅ **Defaults ชัด**: Q1-Q8 default ทุกข้อ
- ✅ **Effort เล็ก**: ~1.5 ชม. เขียว + 0.5 ชม. ฟ้า = ship ได้ภายในวันเดียว
