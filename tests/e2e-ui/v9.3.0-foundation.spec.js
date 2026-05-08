// @ts-check
// v9.3.0 Phase A — Foundation tokens + canonical atoms
// Verifies: new CSS tokens resolve, atoms exist, no visible regression on landing

const { test, expect } = require("@playwright/test");

const BASE = process.env.PDB_TEST_URL || "http://localhost:8000";

test.describe("@v9.3.0 Phase A — Foundation", () => {
  test("M1.1 — new tokens resolve in :root", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(`console: ${m.text()}`);
    });

    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    const tokens = await page.evaluate(() => {
      const cs = getComputedStyle(document.documentElement);
      return {
        space1: cs.getPropertyValue("--space-1").trim(),
        space4: cs.getPropertyValue("--space-4").trim(),
        radiusLg: cs.getPropertyValue("--radius-lg").trim(),
        radiusPill: cs.getPropertyValue("--radius-pill").trim(),
        elev2: cs.getPropertyValue("--elev-2").trim(),
        easeOut: cs.getPropertyValue("--ease-out").trim(),
        durationBase: cs.getPropertyValue("--duration-base").trim(),
        ringFocus: cs.getPropertyValue("--ring-focus").trim(),
        fs2xl: cs.getPropertyValue("--fs-2xl").trim(),
        zModal: cs.getPropertyValue("--z-modal").trim(),
        accentSoft: cs.getPropertyValue("--accent-soft").trim(),
        // Aliases for previously-undefined tokens
        accentPrimary: cs.getPropertyValue("--accent-primary").trim(),
        bgTertiary: cs.getPropertyValue("--bg-tertiary").trim(),
        // Existing token (for reference)
        accent: cs.getPropertyValue("--accent").trim(),
        accentGlow: cs.getPropertyValue("--accent-glow").trim(),
      };
    });

    // New scale tokens
    expect(tokens.space1).toBe("4px");
    expect(tokens.space4).toBe("16px");
    expect(tokens.radiusLg).toBe("10px");
    expect(tokens.radiusPill).toBe("999px");
    expect(tokens.elev2).toContain("rgba");
    expect(tokens.easeOut).toContain("cubic-bezier");
    expect(tokens.durationBase).toBe("0.2s");
    expect(tokens.ringFocus).toContain("rgba(99, 102, 241");
    expect(tokens.fs2xl).toBe("22px");
    expect(tokens.zModal).toBe("10500");
    expect(tokens.accentSoft).toContain("0.06");

    // Aliases — should resolve to existing tokens (used to be undefined).
    // getPropertyValue returns the raw string (here "#6366f1" / surface-1's rgba).
    expect(tokens.accentPrimary.toLowerCase().replace(/\s/g, "")).toMatch(/^#6366f1$|^rgb\(99,102,241\)$|^var\(--accent\)$/);
    expect(tokens.bgTertiary).toContain("0.03"); // = surface-1 rgba

    // Accent unchanged
    expect(tokens.accent.toLowerCase().replace(/\s/g, "")).toBe("#6366f1");
    // Glow lowered 0.15 → 0.12
    expect(tokens.accentGlow).toContain("0.12");

    expect(errors).toEqual([]);
  });

  test("M1.2 — canonical atoms apply correctly", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Inject test elements + verify computed styles resolve from new atoms
    const result = await page.evaluate(() => {
      const make = (cls) => {
        const el = document.createElement("div");
        el.className = cls;
        document.body.appendChild(el);
        return el;
      };
      const card = make("card");
      const pill = make("status-pill is-active");
      const chip = make("chip");
      const meter = make("meter");
      const skeleton = make("skeleton skeleton-line");
      const panel = make("slide-panel slide-panel-md");

      const out = {
        card: {
          radius: getComputedStyle(card).borderRadius,
          bg: getComputedStyle(card).backgroundColor,
          padding: getComputedStyle(card).padding,
        },
        pill: {
          radius: getComputedStyle(pill).borderRadius,
          bg: getComputedStyle(pill).backgroundColor,
        },
        chip: {
          radius: getComputedStyle(chip).borderRadius,
          border: getComputedStyle(chip).borderWidth,
        },
        meter: {
          radius: getComputedStyle(meter).borderRadius,
          height: getComputedStyle(meter).height,
        },
        skeleton: {
          radius: getComputedStyle(skeleton).borderRadius,
        },
        panel: {
          position: getComputedStyle(panel).position,
          transform: getComputedStyle(panel).transform,
        },
      };
      // Cleanup
      [card, pill, chip, meter, skeleton, panel].forEach((el) => el.remove());
      return out;
    });

    // Card: radius-lg = 10px, padding = space-4 = 16px
    expect(result.card.radius).toBe("10px");
    expect(result.card.padding).toBe("16px");

    // Pill: radius-pill = 999px (browser may report large number)
    expect(parseFloat(result.pill.radius)).toBeGreaterThanOrEqual(100);
    // is-active: green-tinted bg
    expect(result.pill.bg).toContain("rgba(34, 197, 94");

    // Chip: radius-pill, 1px border
    expect(parseFloat(result.chip.radius)).toBeGreaterThanOrEqual(100);
    expect(result.chip.border).toBe("1px");

    // Meter: 6px height, pill radius
    expect(result.meter.height).toBe("6px");

    // Skeleton: radius-sm = 6px
    expect(result.skeleton.radius).toBe("6px");

    // Slide panel: fixed + translateX(100%) when not open
    expect(result.panel.position).toBe("fixed");
    // matrix(...) form for translateX(100%)
    expect(result.panel.transform).toMatch(/matrix/);
  });

  test("M1.3 — focus-visible rule with --ring-focus present in stylesheet", async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Verify CSS rule exists. focus-visible doesn't fire on programmatic focus(),
    // so we inspect stylesheets directly instead of forcing a focus state.
    const ruleFound = await page.evaluate(() => {
      for (const sheet of document.styleSheets) {
        try {
          const rules = sheet.cssRules || sheet.rules;
          if (!rules) continue;
          for (const rule of rules) {
            const text = rule.cssText || "";
            if (text.includes(":focus-visible") && text.includes("--ring-focus")) {
              return text.slice(0, 200);
            }
          }
        } catch (_) {
          // CORS-blocked sheet, skip
        }
      }
      return null;
    });

    expect(ruleFound).not.toBeNull();
    expect(ruleFound).toContain(".btn");
  });

  test("M1.4 — no console errors after load (no broken token refs)", async ({ page }) => {
    const errors = [];
    page.on("pageerror", (e) => errors.push(`pageerror: ${e.message}`));
    page.on("console", (m) => {
      if (m.type() === "error") errors.push(`console: ${m.text()}`);
    });

    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // Filter known noise (gtag/analytics — not foundation issues)
    const real = errors.filter(
      (e) => !/gtag|analytics|ERR_BLOCKED_BY_CLIENT/i.test(e),
    );
    expect(real).toEqual([]);
  });
});
