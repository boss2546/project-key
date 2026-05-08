// @ts-check
// v9.3.0 Phase D + E — Visible bank-grade refinements
// Phase D: page-title prominence, card idle shadow, sidebar gradient,
//          nav rail thicker+glow (covered in phase-b update), bg radial
// Phase E1-E4: PDB indigo (deeper), brand-navy, gradient-brand, typography

const { test, expect } = require("@playwright/test");

const BASE = process.env.PDB_TEST_URL || "http://localhost:8000";

test.describe("@v9.3.0 Phase D+E — visible refinements", () => {
  test("M4.1 — Phase E1: --accent is PDB indigo (#4F46E5), brand-navy + gradient-brand defined", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const tokens = await page.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      return {
        accent: cs.getPropertyValue("--accent").trim(),
        accentHover: cs.getPropertyValue("--accent-hover").trim(),
        accentGlow: cs.getPropertyValue("--accent-glow").trim(),
        accentSoft: cs.getPropertyValue("--accent-soft").trim(),
        ringFocus: cs.getPropertyValue("--ring-focus").trim(),
        brandNavy: cs.getPropertyValue("--brand-navy").trim(),
        gradientBrand: cs.getPropertyValue("--gradient-brand").trim(),
        gradientBrandSoft: cs.getPropertyValue("--gradient-brand-soft").trim(),
      };
    });

    expect(tokens.accent.toLowerCase()).toBe("#4f46e5");
    expect(tokens.accentHover.toLowerCase()).toBe("#6366f1");
    // accent-glow + soft retinted to new indigo (rgb 79,70,229)
    expect(tokens.accentGlow).toContain("79, 70, 229");
    expect(tokens.accentSoft).toContain("79, 70, 229");
    expect(tokens.ringFocus).toContain("79, 70, 229");
    // E1 brand-navy
    expect(tokens.brandNavy.toLowerCase()).toBe("#0f172a");
    // E2 brand gradient — browser resolves var() at compute time, so check
    // the resolved indigo hexes (PDB indigo + lighter)
    expect(tokens.gradientBrand).toContain("linear-gradient");
    expect(tokens.gradientBrand.toLowerCase()).toMatch(/#4f46e5|rgb\(79, 70, 229\)/);
    expect(tokens.gradientBrandSoft).toContain("linear-gradient");
  });

  test("M4.2 — Phase D: .page-title is 28px, weight 600, with ::after gradient underline", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const result = await page.evaluate(() => {
      const t = document.createElement("h1");
      t.className = "page-title";
      t.textContent = "Test";
      document.body.appendChild(t);
      const styles = getComputedStyle(t);
      const after = getComputedStyle(t, "::after");
      const out = {
        size: styles.fontSize,
        weight: styles.fontWeight,
        tracking: styles.letterSpacing,
        display: styles.display,
        position: styles.position,
        afterContent: after.content,
        afterPosition: after.position,
        afterWidth: after.width,
        afterHeight: after.height,
        afterBackground: after.backgroundImage,
      };
      t.remove();
      return out;
    });

    expect(result.size).toBe("28px");
    expect(parseInt(result.weight)).toBe(600);
    expect(result.display).toBe("inline-block");
    expect(result.position).toBe("relative");
    // ::after underline: 32px wide, 2px tall, gradient bg
    expect(result.afterContent).not.toBe("none");
    expect(result.afterPosition).toBe("absolute");
    expect(result.afterWidth).toBe("32px");
    expect(result.afterHeight).toBe("2px");
    expect(result.afterBackground).toContain("linear-gradient");
  });

  test("M4.3 — Phase E3: .sidebar has subtle premium gradient overlay", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const rule = await page.evaluate(() => {
      for (const sheet of document.styleSheets) {
        try {
          const list = sheet.cssRules || sheet.rules;
          if (!list) continue;
          for (const r of list) {
            if (r.selectorText === ".sidebar") return r.cssText;
          }
        } catch (_) { /* CORS */ }
      }
      return null;
    });

    expect(rule).not.toBeNull();
    // sidebar bg should now be a gradient + var(--bg-secondary) layered
    expect(rule).toContain("linear-gradient(180deg");
    expect(rule).toContain("rgba(255, 255, 255, 0.025)");
    expect(rule).toContain("var(--bg-secondary)");
  });

  test("M4.4 — Phase D: .main-content has radial-gradient depth", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const rules = await page.evaluate(() => {
      const found = [];
      for (const sheet of document.styleSheets) {
        try {
          const list = sheet.cssRules || sheet.rules;
          if (!list) continue;
          for (const r of list) {
            if (r.selectorText === ".main-content") found.push(r.cssText);
          }
        } catch (_) { /* CORS */ }
      }
      return found;
    });

    expect(rules.length).toBeGreaterThan(0);
    // At least one .main-content rule should have radial-gradient bg
    const hasRadial = rules.some((r) => r.includes("radial-gradient(900px"));
    expect(hasRadial).toBe(true);
  });

  test("M4.5 — Phase D2: cards have idle elev-1 shadow", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Inject a .cluster-card and check it has box-shadow at idle
    const result = await page.evaluate(() => {
      const card = document.createElement("div");
      card.className = "cluster-card";
      document.body.appendChild(card);
      const shadow = getComputedStyle(card).boxShadow;
      card.remove();
      return shadow;
    });

    // Should have a non-none box-shadow (elev-1 = "0 1px 2px rgba(0,0,0,0.20)")
    expect(result).not.toBe("none");
    expect(result).toContain("rgba(0, 0, 0");
  });

  test("M4.6 — no console errors after Phase D+E", async ({ page }) => {
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
