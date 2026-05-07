// @ts-check
/**
 * MOBILE AUDIT (TEMP — research artifact for Daeng v9.3.0 UI audit)
 *
 * Runs every page at 3 mobile viewports and captures:
 *  - Full-page screenshot
 *  - Horizontal overflow detection
 *  - Top offending elements (right > viewport width)
 *  - Vertical overflow inside modal/panel checks
 *
 * Output:
 *   tests/e2e-ui/mobile-audit-results/<viewport>-<page>.png
 *   tests/e2e-ui/mobile-audit-results/_summary.json
 *
 * Run: PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test mobile-audit-temp
 *
 * NOTE: This is a one-off audit, NOT a permanent test. Delete after use.
 */

const { test } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");
const fs = require("fs");
const path = require("path");

const VIEWPORTS = [
  { name: "320-iphone-se-1", width: 320, height: 568 },
  { name: "375-iphone-se-2", width: 375, height: 667 },
  { name: "393-pixel-5", width: 393, height: 851 },
];

const PUBLIC_PAGES = [
  { name: "landing", path: "/", waitFor: "#landing-page" },
  { name: "pricing", path: "/pricing", waitFor: ".plan-card" },
];

const APP_PAGES = [
  { name: "my-data", nav: null },
  { name: "knowledge-collections", nav: "knowledge", subTab: "collections" },
  { name: "knowledge-notes", nav: "knowledge", subTab: "notes" },
  { name: "knowledge-packs", nav: "knowledge", subTab: "packs" },
  { name: "graph", nav: "graph" },
  { name: "chat", nav: "chat" },
  { name: "context-memory", nav: "context-memory" },
  { name: "mcp-setup", nav: "mcp-setup" },
  { name: "tokens", nav: "tokens" },
  { name: "mcp-logs", nav: "mcp-logs" },
];

const RESULTS_DIR = path.join(__dirname, "mobile-audit-results");
if (!fs.existsSync(RESULTS_DIR)) fs.mkdirSync(RESULTS_DIR, { recursive: true });

// Persist findings via filesystem (avoids test-isolation issues)
function appendFinding(f) {
  const file = path.join(RESULTS_DIR, "_findings.jsonl");
  fs.appendFileSync(file, JSON.stringify(f) + "\n");
}

async function checkOverflow(page) {
  return await page.evaluate(() => {
    const docW = document.documentElement.scrollWidth;
    const winW = window.innerWidth;
    const horizScroll = docW > winW + 1;

    const overflowing = [];
    const seen = new Set();
    const allEls = document.querySelectorAll("body *");
    for (const el of allEls) {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) continue;
      if (rect.right > winW + 2) {
        const tag = el.tagName.toLowerCase();
        const cls = (el.className && el.className.toString) ? el.className.toString().split(/\s+/).filter(Boolean).slice(0, 2).join(".") : "";
        const id = el.id ? "#" + el.id : "";
        const sel = `${tag}${id}${cls ? "." + cls : ""}`;
        if (seen.has(sel)) continue;
        seen.add(sel);
        overflowing.push({
          sel,
          right: Math.round(rect.right),
          width: Math.round(rect.width),
          left: Math.round(rect.left),
          text: (el.innerText || "").slice(0, 40).replace(/\n/g, " "),
        });
        if (overflowing.length >= 6) break;
      }
    }
    return { docW, winW, horizScroll, overflowing };
  });
}

for (const vp of VIEWPORTS) {
  test.describe(`mobile-audit @ ${vp.width}x${vp.height}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });
    test.setTimeout(180_000); // long pipeline of pages

    test(`audit ${vp.name}`, async ({ page }) => {
      // ─── Public pages ───
      for (const pp of PUBLIC_PAGES) {
        try {
          await page.goto(pp.path, { waitUntil: "domcontentloaded" });
          await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
          await page.waitForTimeout(600);
          const ovf = await checkOverflow(page);
          const fname = `${vp.name}-public-${pp.name}.png`;
          await page.screenshot({ path: path.join(RESULTS_DIR, fname), fullPage: true });
          appendFinding({ viewport: vp.name, page: pp.name, ...ovf, screenshot: fname });
        } catch (e) {
          appendFinding({ viewport: vp.name, page: pp.name, error: String(e).slice(0, 200) });
        }
      }

      // ─── Auth + app pages ───
      try {
        await registerAndEnterApp(page);
      } catch (e) {
        appendFinding({ viewport: vp.name, page: "REGISTER", error: String(e).slice(0, 200) });
        return;
      }
      await page.waitForTimeout(1000);

      // Initial state = my-data
      const ovfMyData = await checkOverflow(page);
      await page.screenshot({ path: path.join(RESULTS_DIR, `${vp.name}-app-my-data.png`), fullPage: true });
      appendFinding({ viewport: vp.name, page: "app/my-data", ...ovfMyData, screenshot: `${vp.name}-app-my-data.png` });

      for (const ap of APP_PAGES.slice(1)) {
        try {
          // mobile sidebar handling
          const hamburger = page.locator("#sidebar-toggle");
          if (await hamburger.isVisible().catch(() => false)) {
            await hamburger.click();
            await page.waitForTimeout(300);
          }
          await page.click(`#nav-${ap.nav}`, { timeout: 5000 });
          await page.waitForTimeout(700);
          if (ap.subTab) {
            await page.click(`.tab-btn[data-tab="${ap.subTab}"]`, { timeout: 3000 }).catch(() => {});
            await page.waitForTimeout(500);
          }
          const ovf = await checkOverflow(page);
          const fname = `${vp.name}-app-${ap.name}.png`;
          await page.screenshot({ path: path.join(RESULTS_DIR, fname), fullPage: true });
          appendFinding({ viewport: vp.name, page: `app/${ap.name}`, ...ovf, screenshot: fname });
        } catch (e) {
          appendFinding({ viewport: vp.name, page: `app/${ap.name}`, error: String(e).slice(0, 200) });
        }
      }

      // ─── Profile modal ───
      try {
        const hamburger = page.locator("#sidebar-toggle");
        if (await hamburger.isVisible().catch(() => false)) {
          await hamburger.click();
          await page.waitForTimeout(300);
        }
        await page.click("#profile-trigger", { timeout: 3000 });
        await page.waitForTimeout(800);
        const ovf = await checkOverflow(page);
        await page.screenshot({ path: path.join(RESULTS_DIR, `${vp.name}-app-profile-modal.png`), fullPage: true });
        appendFinding({ viewport: vp.name, page: "app/profile-modal", ...ovf, screenshot: `${vp.name}-app-profile-modal.png` });

        // Open Personality section inside profile
        await page.click("#personality-section > summary", { timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(500);
        const ovf2 = await checkOverflow(page);
        await page.screenshot({ path: path.join(RESULTS_DIR, `${vp.name}-app-profile-personality.png`), fullPage: true });
        appendFinding({ viewport: vp.name, page: "app/profile-modal/personality", ...ovf2, screenshot: `${vp.name}-app-profile-personality.png` });
        await page.keyboard.press("Escape");
      } catch (e) {
        appendFinding({ viewport: vp.name, page: "app/profile-modal", error: String(e).slice(0, 200) });
      }

      // ─── Create Pack modal (knowledge → packs) ───
      try {
        const hamburger = page.locator("#sidebar-toggle");
        if (await hamburger.isVisible().catch(() => false)) {
          await hamburger.click();
          await page.waitForTimeout(300);
        }
        await page.click("#nav-knowledge", { timeout: 3000 });
        await page.waitForTimeout(500);
        await page.click('.tab-btn[data-tab="packs"]', { timeout: 3000 });
        await page.waitForTimeout(700);
        // Try open create pack modal
        await page.click('button:has-text("สร้าง Pack")', { timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(500);
        if (await page.locator("#pack-modal-overlay").isVisible().catch(() => false)) {
          const ovf = await checkOverflow(page);
          await page.screenshot({ path: path.join(RESULTS_DIR, `${vp.name}-app-pack-modal.png`), fullPage: false });
          appendFinding({ viewport: vp.name, page: "app/create-pack-modal", ...ovf, screenshot: `${vp.name}-app-pack-modal.png` });
          await page.keyboard.press("Escape");
        }
      } catch (e) {
        appendFinding({ viewport: vp.name, page: "app/create-pack-modal", error: String(e).slice(0, 200) });
      }

      // ─── AI Pack Builder modal ───
      try {
        await page.click('button:has-text("AI สร้างให้")', { timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(500);
        if (await page.locator("#ai-builder-modal-overlay").isVisible().catch(() => false)) {
          const ovf = await checkOverflow(page);
          await page.screenshot({ path: path.join(RESULTS_DIR, `${vp.name}-app-ai-builder-modal.png`), fullPage: false });
          appendFinding({ viewport: vp.name, page: "app/ai-builder-modal", ...ovf, screenshot: `${vp.name}-app-ai-builder-modal.png` });
          await page.keyboard.press("Escape");
        }
      } catch (e) {
        appendFinding({ viewport: vp.name, page: "app/ai-builder-modal", error: String(e).slice(0, 200) });
      }
    });
  });
}
