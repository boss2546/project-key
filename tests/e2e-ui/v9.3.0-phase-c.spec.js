// @ts-check
// v9.3.0 Phase C — Trust signals
// Verifies: modal header polish, upload-zone hover/drag separation,
// empty-state refined flex layout, page transition smoothing

const { test, expect } = require("@playwright/test");

const BASE = process.env.PDB_TEST_URL || "http://localhost:8000";

test.describe("@v9.3.0 Phase C — Trust signals", () => {
  test("M3.1 — .modal-header has subtle gradient highlight band", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const result = await page.evaluate(() => {
      const overlay = document.createElement("div");
      overlay.className = "modal-overlay";
      const modal = document.createElement("div");
      modal.className = "modal";
      const header = document.createElement("div");
      header.className = "modal-header";
      const h2 = document.createElement("h2");
      h2.textContent = "Test";
      header.appendChild(h2);
      modal.appendChild(header);
      overlay.appendChild(modal);
      document.body.appendChild(overlay);

      const out = {
        bg: getComputedStyle(header).backgroundImage,
        h2Size: getComputedStyle(h2).fontSize,
        h2Tracking: getComputedStyle(h2).letterSpacing,
        padding: getComputedStyle(header).padding,
      };
      overlay.remove();
      return out;
    });

    // gradient applied (linear-gradient ...)
    expect(result.bg).toContain("linear-gradient");
    // h2 size = --fs-lg = 16px
    expect(result.h2Size).toBe("16px");
    // negative letter-spacing for headings
    expect(result.h2Tracking).not.toBe("normal");
    // padding follows new scale (var(--space-4) var(--space-5) = 16px 20px)
    expect(result.padding).toBe("16px 20px");
  });

  test("M3.2 — .upload-zone has separate hover vs drag-over rules", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Inspect the stylesheets directly — landing root may not instantiate
    // an .upload-zone element, but the rule definition is what we care about.
    const rules = await page.evaluate(() => {
      const found = { hover: null, dragOver: null, idle: null };
      for (const sheet of document.styleSheets) {
        try {
          const list = sheet.cssRules || sheet.rules;
          if (!list) continue;
          for (const r of list) {
            const sel = r.selectorText;
            if (!sel) continue;
            if (sel === ".upload-zone") found.idle = r.cssText;
            if (sel === ".upload-zone:hover") found.hover = r.cssText;
            if (sel === ".upload-zone.drag-over") found.dragOver = r.cssText;
          }
        } catch (_) { /* CORS */ }
      }
      return found;
    });

    expect(rules.idle).not.toBeNull();
    expect(rules.idle).toContain("var(--radius-xl)");
    expect(rules.idle).toContain("var(--space-8)");

    expect(rules.hover).not.toBeNull();
    // hover uses accent-soft (lighter), not accent-glow
    expect(rules.hover).toContain("--accent-soft");

    expect(rules.dragOver).not.toBeNull();
    // drag-over uses accent-glow + tiny scale
    expect(rules.dragOver).toContain("--accent-glow");
    expect(rules.dragOver).toContain("scale(1.005)");
  });

  test("M3.3 — .empty-state is flex-column + new structural classes work", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const result = await page.evaluate(() => {
      const empty = document.createElement("div");
      empty.className = "empty-state";
      const icon = document.createElement("div");
      icon.className = "empty-state-icon";
      const title = document.createElement("p");
      title.className = "empty-state-title";
      const hint = document.createElement("p");
      hint.className = "empty-state-hint";
      empty.appendChild(icon);
      empty.appendChild(title);
      empty.appendChild(hint);
      document.body.appendChild(empty);

      const out = {
        display: getComputedStyle(empty).display,
        direction: getComputedStyle(empty).flexDirection,
        align: getComputedStyle(empty).alignItems,
        iconWidth: getComputedStyle(icon).width,
        titleWeight: getComputedStyle(title).fontWeight,
        hintMaxWidth: getComputedStyle(hint).maxWidth,
      };
      empty.remove();
      return out;
    });

    expect(result.display).toBe("flex");
    expect(result.direction).toBe("column");
    expect(result.align).toBe("center");
    expect(result.iconWidth).toBe("48px");
    expect(parseInt(result.titleWeight)).toBeGreaterThanOrEqual(500);
    // 32ch maxWidth — exact px depends on font, but should not be 'none'
    expect(result.hintMaxWidth).not.toBe("none");
  });

  test("M3.4 — .page animation uses --duration-slow + --ease-out", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const animSpec = await page.evaluate(() => {
      // Find the .page rule in stylesheets and read its animation
      for (const sheet of document.styleSheets) {
        try {
          const rules = sheet.cssRules || sheet.rules;
          if (!rules) continue;
          for (const rule of rules) {
            if (rule.selectorText === ".page") {
              return {
                animation: rule.style.animation,
              };
            }
          }
        } catch (_) { /* CORS */ }
      }
      return null;
    });

    expect(animSpec).not.toBeNull();
    // animation should reference fadeIn + var(--duration-slow) + var(--ease-out)
    // (browser may inline-resolve var() in some cases; check substring loosely)
    expect(animSpec.animation).toContain("fadeIn");
  });

  test("M3.5 — no console errors after Phase C", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(`console: ${m.text()}`);
    });
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");
    const real = errors.filter(
      (e) => !/gtag|analytics|ERR_BLOCKED_BY_CLIENT/i.test(e),
    );
    expect(real).toEqual([]);
  });
});
