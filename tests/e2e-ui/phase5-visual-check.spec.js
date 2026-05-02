// @ts-check
/**
 * Phase 5 — Visual screenshots for the user to inspect.
 * Captures landing.html and app.html standalone renders.
 */

const { test } = require("@playwright/test");
const path = require("path");
const fs = require("fs");

const OUT_DIR = path.join(__dirname, "..", "phase5-visual");
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const TEST_PASSWORD = "Phase5_Vis!2026";
const uniqueEmail = () => `pv_${Date.now()}_${Math.floor(Math.random() * 1e6)}@smoke.test`;

test.describe("Phase5 / visual checks", () => {
  // Each test gets a fresh browser context with empty localStorage.
  // No beforeEach needed — and clearing storage would break the
  // "app.html with auth" test by wiping the token mid-test.

  test("landing.html — top of page", async ({ page }) => {
    await page.goto("/landing.html");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: path.join(OUT_DIR, "landing-top.png") });
  });

  test("landing.html — full page", async ({ page }) => {
    await page.goto("/landing.html");
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: path.join(OUT_DIR, "landing-full.png"), fullPage: true });
  });

  test("landing.html — auth modal open (login)", async ({ page }) => {
    await page.goto("/landing.html");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-login");
    await page.waitForTimeout(400);
    await page.screenshot({ path: path.join(OUT_DIR, "landing-modal-login.png") });
  });

  test("app.html — with auth, shows sidebar", async ({ page }) => {
    // Register on legacy / first
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-register");
    await page.fill("#register-name", "VisualTester");
    await page.fill("#register-email", uniqueEmail());
    await page.fill("#register-password", TEST_PASSWORD);
    await page.click("#btn-register");
    await page.waitForSelector("#app:not(.hidden)", { timeout: 10000 });
    // Now visit app.html directly
    await page.goto("/app.html");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(OUT_DIR, "app-html-my-data.png") });
  });
});
