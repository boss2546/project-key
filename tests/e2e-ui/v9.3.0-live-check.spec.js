// @ts-check
// v9.3.0 Live verification — visit /app, read computed styles of REAL elements,
// take screenshots. Prove that changes are applied (or find why not).

const { test, expect } = require("@playwright/test");
const fs = require("fs");
const path = require("path");

const BASE = process.env.PDB_TEST_URL || "http://localhost:8000";
const SHOTS = path.join(__dirname, "..", "..", "v9.3.0-live-shots");
if (!fs.existsSync(SHOTS)) fs.mkdirSync(SHOTS, { recursive: true });

test.describe("@v9.3.0 LIVE — verify changes on real /app", () => {
  test("LIVE.1 — landing root: read real .page-title, nav-item, sidebar styles", async ({ page }) => {
    page.on("pageerror", (e) => console.error("pageerror:", e.message));

    // 1) Visit root (landing or app shell depending on auth)
    await page.goto(BASE);
    await page.waitForLoadState("networkidle");

    // 2) Full-page screenshot
    await page.screenshot({
      path: path.join(SHOTS, "01-root-full.png"),
      fullPage: true,
    });

    // 3) Inspect document for which page is currently visible
    const visibility = await page.evaluate(() => {
      const out = {};
      const ids = [
        "app", "auth-modal", "page-my-data", "page-knowledge",
      ];
      for (const id of ids) {
        const el = document.getElementById(id);
        if (el) {
          out[id] = {
            displayed: getComputedStyle(el).display !== "none" && !el.classList.contains("hidden"),
            classes: el.className,
          };
        } else {
          out[id] = "not-found";
        }
      }
      return out;
    });

    console.log("Page visibility:", JSON.stringify(visibility, null, 2));
    fs.writeFileSync(path.join(SHOTS, "01-visibility.json"), JSON.stringify(visibility, null, 2));

    // 4) Read computed styles of REAL .page-title (if app shell visible)
    const pageTitleStyles = await page.evaluate(() => {
      const titles = document.querySelectorAll(".page-title");
      const found = [];
      titles.forEach((t) => {
        const cs = getComputedStyle(t);
        const after = getComputedStyle(t, "::after");
        found.push({
          text: t.textContent.trim().slice(0, 30),
          visible: t.offsetParent !== null,
          fontSize: cs.fontSize,
          fontWeight: cs.fontWeight,
          letterSpacing: cs.letterSpacing,
          afterContent: after.content,
          afterWidth: after.width,
          afterHeight: after.height,
          afterBackground: after.backgroundImage,
        });
      });
      return found;
    });

    console.log("Real .page-title elements:", JSON.stringify(pageTitleStyles, null, 2));
    fs.writeFileSync(path.join(SHOTS, "01-page-title.json"), JSON.stringify(pageTitleStyles, null, 2));

    // 5) Read computed styles of REAL .sidebar
    const sidebarStyle = await page.evaluate(() => {
      const sb = document.querySelector(".sidebar");
      if (!sb) return null;
      const cs = getComputedStyle(sb);
      return {
        visible: sb.offsetParent !== null,
        background: cs.background,
        backgroundImage: cs.backgroundImage,
      };
    });
    console.log("Real .sidebar:", JSON.stringify(sidebarStyle, null, 2));
    fs.writeFileSync(path.join(SHOTS, "01-sidebar.json"), JSON.stringify(sidebarStyle, null, 2));

    // 6) Read REAL .nav-item.active rail
    const navRail = await page.evaluate(() => {
      const a = document.querySelector(".nav-item.active");
      if (!a) return null;
      const cs = getComputedStyle(a);
      const before = getComputedStyle(a, "::before");
      return {
        text: a.textContent.trim().slice(0, 30),
        bg: cs.backgroundColor,
        color: cs.color,
        beforeContent: before.content,
        beforeWidth: before.width,
        beforeBg: before.backgroundColor,
        beforeBoxShadow: before.boxShadow,
      };
    });
    console.log("Real .nav-item.active rail:", JSON.stringify(navRail, null, 2));
    fs.writeFileSync(path.join(SHOTS, "01-nav-rail.json"), JSON.stringify(navRail, null, 2));

    // 7) Read REAL .main-content background
    const mainStyle = await page.evaluate(() => {
      const m = document.querySelector(".main-content");
      if (!m) return null;
      const cs = getComputedStyle(m);
      return {
        backgroundImage: cs.backgroundImage,
      };
    });
    console.log("Real .main-content:", JSON.stringify(mainStyle, null, 2));
    fs.writeFileSync(path.join(SHOTS, "01-main-content.json"), JSON.stringify(mainStyle, null, 2));

    // 8) Read REAL --accent value
    const tokenAccent = await page.evaluate(() => {
      return {
        accent: getComputedStyle(document.documentElement).getPropertyValue("--accent").trim(),
        gradient: getComputedStyle(document.documentElement).getPropertyValue("--gradient-brand").trim(),
      };
    });
    console.log("Token --accent:", tokenAccent.accent, "gradient:", tokenAccent.gradient);

    // 9) Take focused screenshot of sidebar
    const sidebarEl = page.locator(".sidebar").first();
    if (await sidebarEl.count()) {
      await sidebarEl.screenshot({ path: path.join(SHOTS, "02-sidebar.png") }).catch(() => {});
    }

    // 10) Take focused screenshot of page-header area
    const headerEl = page.locator(".page-header").first();
    if (await headerEl.count()) {
      await headerEl.screenshot({ path: path.join(SHOTS, "03-page-header.png") }).catch(() => {});
    }
  });

  test("LIVE.2 — explicitly visit /app", async ({ page }) => {
    await page.goto(`${BASE}/app`);
    await page.waitForLoadState("networkidle");
    await page.screenshot({
      path: path.join(SHOTS, "04-app-explicit.png"),
      fullPage: true,
    });

    const url = page.url();
    console.log("Final URL after /app:", url);
    fs.writeFileSync(path.join(SHOTS, "04-final-url.txt"), url);
  });
});
