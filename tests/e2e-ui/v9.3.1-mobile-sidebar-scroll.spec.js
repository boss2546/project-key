// @ts-check
// v9.3.1 hotfix — verify mobile sidebar is fully scrollable
// (profile/email/logout no longer clipped on small iOS heights)

const { test, expect } = require("@playwright/test");

const BASE = process.env.PDB_TEST_URL || "http://localhost:8000";

test.describe("@v9.3.1 mobile sidebar scroll", () => {
  test.use({
    viewport: { width: 375, height: 600 }, // iPhone SE-ish (worst-case short)
  });

  test("M5.1 — mobile sidebar has overflow-y:auto + iOS smooth-scroll", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Inspect the actual @media (max-width: 768px) .sidebar rule via stylesheets
    const rule = await page.evaluate(() => {
      for (const sheet of document.styleSheets) {
        try {
          const list = sheet.cssRules || sheet.rules;
          if (!list) continue;
          for (const r of list) {
            // CSSMediaRule contains nested rules
            if (r.type === CSSRule.MEDIA_RULE && /max-width:\s*768px/.test(r.conditionText)) {
              const inner = r.cssRules || r.rules;
              for (const ir of inner) {
                if (ir.selectorText === ".sidebar") return ir.cssText;
              }
            }
          }
        } catch (_) { /* CORS */ }
      }
      return null;
    });

    expect(rule).not.toBeNull();
    expect(rule).toContain("overflow-y: auto");
    expect(rule).toContain("safe-area-inset-bottom");

    // Chromium drops -webkit-overflow-scrolling from cssText (it's iOS-only).
    // Verify directly in the source CSS instead.
    const css = await page.evaluate(async () => {
      const r = await fetch("/legacy/shared.css?v=9.3.1");
      return await r.text();
    });
    const stylesCss = await page.evaluate(async () => {
      const r = await fetch("/legacy/styles.css?v=9.3.1");
      return await r.text();
    });
    expect(stylesCss).toContain("-webkit-overflow-scrolling: touch");
  });

  test("M5.2 — .sidebar-nav inside mobile sidebar takes natural height (no nested scroll)", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const rule = await page.evaluate(() => {
      for (const sheet of document.styleSheets) {
        try {
          const list = sheet.cssRules || sheet.rules;
          if (!list) continue;
          for (const r of list) {
            if (r.type === CSSRule.MEDIA_RULE && /max-width:\s*768px/.test(r.conditionText)) {
              const inner = r.cssRules || r.rules;
              for (const ir of inner) {
                if (ir.selectorText === ".sidebar .sidebar-nav") return ir.cssText;
              }
            }
          }
        } catch (_) { /* CORS */ }
      }
      return null;
    });

    expect(rule).not.toBeNull();
    expect(rule).toContain("flex: 0 0 auto");
    expect(rule).toContain("overflow-y: visible");
  });
});
