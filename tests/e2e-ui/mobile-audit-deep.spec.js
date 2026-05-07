// @ts-check
/**
 * MOBILE AUDIT DEEP (TEMP — research artifact for Daeng v9.3.0)
 *
 * Goes BEYOND horizontal overflow. Detects:
 *   1. Touch targets < 44×44 px (Apple HIG / Material Design 3)
 *   2. Element overlap (FAB/toast/kebab vs interactive controls)
 *   3. Console errors per page (JS errors, warnings)
 *   4. Network failures (4xx/5xx + failed requests)
 *   5. Missing a11y attrs (icon-only btn without aria-label, img without alt)
 *   6. Vertical clipping inside scroll containers (content cut off)
 *   7. Long-text stress (extreme filename/profile field length)
 *
 * Run: PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test mobile-audit-deep
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

const APP_PAGES = [
  { name: "my-data", nav: null },
  { name: "knowledge-collections", nav: "knowledge", subTab: "collections" },
  { name: "knowledge-packs", nav: "knowledge", subTab: "packs" },
  { name: "graph", nav: "graph" },
  { name: "chat", nav: "chat" },
  { name: "context-memory", nav: "context-memory" },
  { name: "mcp-setup", nav: "mcp-setup" },
  { name: "tokens", nav: "tokens" },
  { name: "mcp-logs", nav: "mcp-logs" },
];

const RESULTS_DIR = path.join(__dirname, "mobile-audit-deep-results");
if (!fs.existsSync(RESULTS_DIR)) fs.mkdirSync(RESULTS_DIR, { recursive: true });

function append(file, obj) {
  fs.appendFileSync(path.join(RESULTS_DIR, file), JSON.stringify(obj) + "\n");
}

// ─── Touch target audit ───
async function auditTouchTargets(page) {
  return await page.evaluate(() => {
    const MIN = 44;
    const SELECTORS = "button, a, input[type=button], input[type=submit], [role=button], select, [onclick]";
    const small = [];
    document.querySelectorAll(SELECTORS).forEach((el) => {
      const rect = el.getBoundingClientRect();
      // Only audit visible elements
      if (rect.width === 0 || rect.height === 0) return;
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") return;
      // Skip hidden inside .hidden parent
      if (el.closest(".hidden")) return;
      const tooSmall = rect.width < MIN || rect.height < MIN;
      if (tooSmall) {
        const tag = el.tagName.toLowerCase();
        const id = el.id ? "#" + el.id : "";
        const cls = (el.className && el.className.toString) ? el.className.toString().split(/\s+/).filter(Boolean).slice(0, 2).join(".") : "";
        const text = (el.innerText || el.value || "").trim().slice(0, 25).replace(/\n/g, " ");
        small.push({
          sel: `${tag}${id}${cls ? "." + cls : ""}`,
          w: Math.round(rect.width),
          h: Math.round(rect.height),
          text,
        });
      }
    });
    return small.slice(0, 20);
  });
}

// ─── Overlap detection (FAB vs interactive controls) ───
async function auditOverlap(page) {
  return await page.evaluate(() => {
    function intersects(a, b) {
      return !(a.right < b.left || b.right < a.left || a.bottom < b.top || b.bottom < a.top);
    }
    function toRect(el) {
      const r = el.getBoundingClientRect();
      return { left: r.left, right: r.right, top: r.top, bottom: r.bottom, w: r.width, h: r.height };
    }
    function isVisible(el) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) return false;
      const s = window.getComputedStyle(el);
      return s.display !== "none" && s.visibility !== "hidden" && parseFloat(s.opacity) > 0.01;
    }
    const overlaps = [];
    // Fixed-position overlay elements
    const overlayCandidates = [
      "#guide-fab",
      ".page.active .page-fab",
      "#toast-container .toast",
      ".sidebar-toggle",
    ];
    const overlays = [];
    overlayCandidates.forEach((sel) => {
      document.querySelectorAll(sel).forEach((el) => {
        if (isVisible(el)) overlays.push({ sel, el, rect: toRect(el) });
      });
    });
    // Interactive elements that should not be obscured
    const interactiveSel = "button:not(.hidden), a.btn:not(.hidden), .nav-item, .filter-chip, .tab-btn, .chip, input.form-input";
    const interactives = [];
    document.querySelectorAll(interactiveSel).forEach((el) => {
      if (!isVisible(el)) return;
      if (el.closest(".hidden")) return;
      interactives.push({ el, rect: toRect(el) });
    });
    // Cross-check overlaps
    for (const ov of overlays) {
      for (const iv of interactives) {
        if (ov.el === iv.el) continue;
        if (intersects(ov.rect, iv.rect)) {
          // Skip if interactive is INSIDE overlay (e.g. button inside toast)
          if (ov.el.contains(iv.el)) continue;
          const tag = iv.el.tagName.toLowerCase();
          const id = iv.el.id ? "#" + iv.el.id : "";
          const text = (iv.el.innerText || "").trim().slice(0, 25).replace(/\n/g, " ");
          overlaps.push({
            overlay: ov.sel,
            covered: `${tag}${id}`,
            text,
            covRect: { L: Math.round(iv.rect.left), R: Math.round(iv.rect.right), T: Math.round(iv.rect.top), B: Math.round(iv.rect.bottom) },
          });
          if (overlaps.length >= 10) break;
        }
      }
      if (overlaps.length >= 10) break;
    }
    return overlaps;
  });
}

// ─── A11y audit (icon-only buttons, missing alt, form labels) ───
async function auditA11y(page) {
  return await page.evaluate(() => {
    const issues = { iconBtnNoLabel: [], imgNoAlt: [], inputNoLabel: [] };
    // Icon-only buttons (no text content, no aria-label)
    document.querySelectorAll("button:not([disabled]), a.btn-close, .btn-icon, .copy-btn").forEach((el) => {
      const rect = el.getBoundingClientRect();
      if (rect.width === 0 || rect.height === 0) return;
      if (el.closest(".hidden")) return;
      const txt = (el.innerText || "").trim();
      const aria = el.getAttribute("aria-label") || el.getAttribute("title");
      if (!txt && !aria) {
        const id = el.id ? "#" + el.id : "";
        issues.iconBtnNoLabel.push({ sel: el.tagName.toLowerCase() + id, html: el.outerHTML.slice(0, 80) });
      }
    });
    // <img> without alt
    document.querySelectorAll("img:not([alt])").forEach((el) => {
      issues.imgNoAlt.push({ src: el.src.slice(0, 60) });
    });
    // <input> without <label> (form-input class)
    document.querySelectorAll("input.form-input, textarea.form-input").forEach((el) => {
      const id = el.id;
      if (!id) {
        issues.inputNoLabel.push({ name: el.name || "no-id", placeholder: el.placeholder });
        return;
      }
      const lbl = document.querySelector(`label[for="${id}"]`);
      const wrapped = el.closest("label");
      const aria = el.getAttribute("aria-label") || el.getAttribute("aria-labelledby");
      if (!lbl && !wrapped && !aria) {
        issues.inputNoLabel.push({ id, placeholder: el.placeholder });
      }
    });
    return {
      iconBtnNoLabel: issues.iconBtnNoLabel.slice(0, 10),
      imgNoAlt: issues.imgNoAlt.slice(0, 10),
      inputNoLabel: issues.inputNoLabel.slice(0, 10),
    };
  });
}

// ─── Vertical clipping inside scroll containers ───
async function auditVerticalClipping(page) {
  return await page.evaluate(() => {
    const clipped = [];
    // Look at scrollable containers
    const scrollables = document.querySelectorAll(".modal-body, .file-detail-body, .sources-body, .pack-modal-body, .knowledge-content");
    scrollables.forEach((el) => {
      if (el.scrollHeight > el.clientHeight + 4) {
        const sel = el.tagName.toLowerCase() + (el.id ? "#" + el.id : "") + "." + (el.className || "").toString().split(/\s+/)[0];
        clipped.push({
          sel,
          scrollHeight: el.scrollHeight,
          clientHeight: el.clientHeight,
          overflow: el.scrollHeight - el.clientHeight,
        });
      }
    });
    return clipped;
  });
}

for (const vp of VIEWPORTS) {
  test.describe(`mobile-audit-deep @ ${vp.width}x${vp.height}`, () => {
    test.use({ viewport: { width: vp.width, height: vp.height } });
    test.setTimeout(180_000);

    test(`deep audit ${vp.name}`, async ({ page }) => {
      // Capture console + network errors
      const consoleErrors = [];
      const networkFailed = [];
      page.on("console", (msg) => {
        if (msg.type() === "error" || msg.type() === "warning") {
          consoleErrors.push({ type: msg.type(), text: msg.text().slice(0, 200) });
        }
      });
      page.on("pageerror", (err) => {
        consoleErrors.push({ type: "pageerror", text: String(err).slice(0, 200) });
      });
      page.on("requestfailed", (req) => {
        networkFailed.push({ url: req.url().slice(0, 100), failure: req.failure()?.errorText });
      });
      page.on("response", (res) => {
        if (res.status() >= 400 && res.status() < 600) {
          // Skip favicon noise
          if (res.url().includes("favicon")) return;
          networkFailed.push({ url: res.url().slice(0, 100), status: res.status() });
        }
      });

      // ─── Public landing first (capture errors from public flow) ───
      await page.goto("/", { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 8000 }).catch(() => {});
      await page.waitForTimeout(800);
      append("touch.jsonl", { vp: vp.name, page: "landing", small: await auditTouchTargets(page) });
      append("overlap.jsonl", { vp: vp.name, page: "landing", overlaps: await auditOverlap(page) });
      append("a11y.jsonl", { vp: vp.name, page: "landing", ...(await auditA11y(page)) });

      // ─── Auth + app pages ───
      try {
        await registerAndEnterApp(page);
      } catch (e) {
        append("errors.jsonl", { vp: vp.name, where: "register", error: String(e).slice(0, 200) });
        return;
      }
      await page.waitForTimeout(1500);

      // initial my-data
      const collectAudits = async (label) => {
        append("touch.jsonl", { vp: vp.name, page: label, small: await auditTouchTargets(page) });
        append("overlap.jsonl", { vp: vp.name, page: label, overlaps: await auditOverlap(page) });
        append("a11y.jsonl", { vp: vp.name, page: label, ...(await auditA11y(page)) });
        append("vclip.jsonl", { vp: vp.name, page: label, clipped: await auditVerticalClipping(page) });
      };

      await collectAudits("app/my-data");

      for (const ap of APP_PAGES.slice(1)) {
        try {
          const hamburger = page.locator("#sidebar-toggle");
          if (await hamburger.isVisible().catch(() => false)) {
            await hamburger.click();
            await page.waitForTimeout(300);
          }
          await page.click(`#nav-${ap.nav}`, { timeout: 5000 });
          await page.waitForTimeout(600);
          if (ap.subTab) {
            await page.click(`.tab-btn[data-tab="${ap.subTab}"]`, { timeout: 3000 }).catch(() => {});
            await page.waitForTimeout(400);
          }
          await collectAudits(`app/${ap.name}`);
        } catch (e) {
          append("errors.jsonl", { vp: vp.name, where: `app/${ap.name}`, error: String(e).slice(0, 200) });
        }
      }

      // ─── Profile modal — open + audit + personality ───
      try {
        const hamburger = page.locator("#sidebar-toggle");
        if (await hamburger.isVisible().catch(() => false)) {
          await hamburger.click();
          await page.waitForTimeout(300);
        }
        await page.click("#profile-trigger", { timeout: 3000 });
        await page.waitForTimeout(800);
        await collectAudits("app/profile-modal");
        await page.click("#personality-section > summary", { timeout: 3000 }).catch(() => {});
        await page.waitForTimeout(400);
        await collectAudits("app/profile-personality");
        await page.keyboard.press("Escape");
      } catch (e) {
        append("errors.jsonl", { vp: vp.name, where: "profile", error: String(e).slice(0, 200) });
      }

      // ─── Long-text stress test on My Data + Profile ───
      try {
        const hamburger = page.locator("#sidebar-toggle");
        if (await hamburger.isVisible().catch(() => false)) {
          await hamburger.click();
          await page.waitForTimeout(300);
        }
        await page.click("#nav-context-memory");
        await page.waitForTimeout(500);
        // Type extremely long text into ctx-search to test input overflow
        const longString = "A".repeat(200);
        const searchEl = page.locator("#ctx-search");
        if (await searchEl.isVisible()) {
          await searchEl.fill(longString);
          await page.waitForTimeout(300);
          await collectAudits("app/context-memory-longtext");
        }
      } catch (e) {
        append("errors.jsonl", { vp: vp.name, where: "longtext", error: String(e).slice(0, 200) });
      }

      // Persist console + network logs
      append("console.jsonl", { vp: vp.name, errors: consoleErrors.slice(0, 30) });
      append("network.jsonl", { vp: vp.name, failed: networkFailed.slice(0, 30) });
    });
  });
}
