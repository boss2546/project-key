// @ts-check
// v9.3.0 Phase B — Atom refinement (visible cascade)
// Verifies: nav rail, loading-overlay re-tinted, tabular-nums, uppercase removed

const { test, expect } = require("@playwright/test");

const BASE = process.env.PDB_TEST_URL || "http://localhost:8000";

test.describe("@v9.3.0 Phase B — Atom refinement", () => {
  test("M2.1 — .nav-item.active has 3px accent rail (::before, Phase D bumped from 2px)", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Inject sidebar context: nav-item with .active
    const railOk = await page.evaluate(() => {
      const nav = document.createElement("a");
      nav.className = "nav-item active";
      nav.href = "#";
      nav.textContent = "test";
      document.body.appendChild(nav);
      const styles = getComputedStyle(nav, "::before");
      const out = {
        position: styles.position,
        width: styles.width,
        bg: styles.backgroundColor,
        boxShadow: styles.boxShadow,
        content: styles.content,
      };
      nav.remove();
      return out;
    });

    expect(railOk.position).toBe("absolute");
    expect(railOk.width).toBe("3px");
    // Phase E1: accent color changed to #4F46E5 = rgb(79,70,229)
    expect(railOk.bg.toLowerCase().replace(/\s/g, "")).toContain("rgb(79,70,229)");
    // Phase D: glow box-shadow added for visibility on dark sidebar
    expect(railOk.boxShadow).toContain("79, 70, 229");
    expect(railOk.content).not.toBe("none");
  });

  test("M2.2 — loading-overlay re-tinted to brand indigo (no purple)", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const result = await page.evaluate(() => {
      // Inject loading-overlay-card
      const el = document.createElement("div");
      el.className = "loading-overlay-card";
      document.body.appendChild(el);
      const styles = getComputedStyle(el);
      const out = {
        border: styles.borderColor,
        boxShadow: styles.boxShadow,
      };
      el.remove();
      return out;
    });

    // border was purple #a78bfa rgba(139,92,246) → now indigo rgba(99,102,241)
    expect(result.border.replace(/\s/g, "")).toContain("99,102,241");
    // box-shadow contains indigo glow
    expect(result.boxShadow).toContain("99, 102, 241");
    expect(result.boxShadow).not.toContain("139, 92, 246");
  });

  test("M2.3 — tabular-nums applied to .stat-value, .badge-count, td", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const result = await page.evaluate(() => {
      const make = (cls, tag = "div") => {
        const el = document.createElement(tag);
        el.className = cls;
        document.body.appendChild(el);
        return el;
      };
      const sv = make("stat-value");
      const bc = make("badge-count");
      const tbl = document.createElement("table");
      const td = document.createElement("td");
      tbl.appendChild(td);
      document.body.appendChild(tbl);

      const out = {
        statValue: getComputedStyle(sv).fontVariantNumeric,
        badgeCount: getComputedStyle(bc).fontVariantNumeric,
        td: getComputedStyle(td).fontVariantNumeric,
      };
      sv.remove(); bc.remove(); tbl.remove();
      return out;
    });

    expect(result.statValue).toContain("tabular-nums");
    expect(result.badgeCount).toContain("tabular-nums");
    expect(result.td).toContain("tabular-nums");
  });

  test("M2.4 — uppercase removed from .nav-section-label, .log-table th, .fd-section h3", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const result = await page.evaluate(() => {
      const navLabel = document.createElement("span");
      navLabel.className = "nav-section-label";
      document.body.appendChild(navLabel);

      const tbl = document.createElement("table");
      tbl.className = "log-table";
      const thead = document.createElement("thead");
      const tr = document.createElement("tr");
      const th = document.createElement("th");
      tr.appendChild(th); thead.appendChild(tr); tbl.appendChild(thead);
      document.body.appendChild(tbl);

      const fdSection = document.createElement("div");
      fdSection.className = "fd-section";
      const h3 = document.createElement("h3");
      fdSection.appendChild(h3);
      document.body.appendChild(fdSection);

      const out = {
        navLabel: getComputedStyle(navLabel).textTransform,
        navLabelTracking: getComputedStyle(navLabel).letterSpacing,
        thTransform: getComputedStyle(th).textTransform,
        h3Transform: getComputedStyle(h3).textTransform,
      };
      navLabel.remove(); tbl.remove(); fdSection.remove();
      return out;
    });

    expect(result.navLabel).toBe("none");
    expect(result.navLabelTracking).toBe("normal");
    expect(result.thTransform).toBe("none");
    expect(result.h3Transform).toBe("none");
  });

  test("M2.5 — .page-header.is-sticky declared (opt-in for long pages)", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const result = await page.evaluate(() => {
      const el = document.createElement("div");
      el.className = "page-header is-sticky";
      document.body.appendChild(el);
      const cs = getComputedStyle(el);
      const out = {
        position: cs.position,
        top: cs.top,
        zIndex: cs.zIndex,
      };
      el.remove();
      return out;
    });

    expect(result.position).toBe("sticky");
    expect(result.top).toBe("0px");
    expect(parseInt(result.zIndex)).toBeGreaterThanOrEqual(50);
  });

  test("M2.6 — no console errors after Phase B (cascade still clean)", async ({ page }) => {
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
