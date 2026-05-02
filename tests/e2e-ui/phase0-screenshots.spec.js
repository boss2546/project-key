// @ts-check
/**
 * Phase 0 — Baseline screenshots
 * Run: PDB_TEST_URL=http://127.0.0.1:8765 npx playwright test phase0-screenshots
 *
 * Saves to tests/baseline/ on first run; compares to saved on subsequent runs.
 * After completing each phase, re-run and inspect any visual diffs in test-results/.
 */

const { test, expect } = require("@playwright/test");
const path = require("path");
const fs = require("fs");

const BASELINE_DIR = path.join(__dirname, "..", "baseline");
if (!fs.existsSync(BASELINE_DIR)) fs.mkdirSync(BASELINE_DIR, { recursive: true });

const TEST_PASSWORD = "Phase0_Pass!2026";
const uniqueEmail = () => `shot_${Date.now()}_${Math.floor(Math.random() * 1e6)}@smoke.test`;

async function clearAuth(page) {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.removeItem("pdb_token");
    localStorage.removeItem("pdb_user");
  });
  await page.reload();
  await page.waitForLoadState("networkidle");
}

async function registerAndLogin(page) {
  await clearAuth(page);
  const email = uniqueEmail();
  await page.click("#btn-show-register");
  await page.fill("#register-name", "Screenshot Tester");
  await page.fill("#register-email", email);
  await page.fill("#register-password", TEST_PASSWORD);
  await page.click("#btn-register");
  await page.waitForSelector("#app:not(.hidden)", { timeout: 10000 });
}

test.describe("Phase0 / Baseline screenshots", () => {
  test("01 — landing top", async ({ page }) => {
    await clearAuth(page);
    await page.screenshot({ path: path.join(BASELINE_DIR, "01-landing-top.png") });
  });

  test("02 — landing full", async ({ page }) => {
    await clearAuth(page);
    await page.screenshot({ path: path.join(BASELINE_DIR, "02-landing-full.png"), fullPage: true });
  });

  test("03 — auth modal login", async ({ page }) => {
    await clearAuth(page);
    await page.click("#btn-show-login");
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(BASELINE_DIR, "03-auth-modal-login.png") });
  });

  test("04 — auth modal register", async ({ page }) => {
    await clearAuth(page);
    await page.click("#btn-show-register");
    await page.waitForTimeout(300);
    await page.screenshot({ path: path.join(BASELINE_DIR, "04-auth-modal-register.png") });
  });

  test("05 — app my-data", async ({ page }) => {
    await registerAndLogin(page);
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(BASELINE_DIR, "05-app-my-data.png") });
  });

  test("06 — app knowledge", async ({ page }) => {
    await registerAndLogin(page);
    await page.click("#nav-knowledge");
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(BASELINE_DIR, "06-app-knowledge.png") });
  });

  test("07 — app graph", async ({ page }) => {
    await registerAndLogin(page);
    await page.click("#nav-graph");
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(BASELINE_DIR, "07-app-graph.png") });
  });

  test("08 — app chat", async ({ page }) => {
    await registerAndLogin(page);
    await page.click("#nav-chat");
    await page.waitForTimeout(800);
    await page.screenshot({ path: path.join(BASELINE_DIR, "08-app-chat.png") });
  });

  test("09 — app mcp-setup", async ({ page }) => {
    await registerAndLogin(page);
    await page.click("#nav-mcp-setup");
    await page.waitForTimeout(1000);
    await page.screenshot({ path: path.join(BASELINE_DIR, "09-app-mcp-setup.png") });
  });
});
