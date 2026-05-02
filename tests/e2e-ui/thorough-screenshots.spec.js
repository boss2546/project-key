// @ts-check
/**
 * Thorough / capture screenshots of every meaningful UI state.
 * Outputs to tests/thorough-screenshots/ for human review.
 */

const { test } = require("@playwright/test");
const path = require("path");
const fs = require("fs");
const { registerAndEnterApp } = require("./fixtures/auth.js");

const OUT_DIR = path.join(__dirname, "..", "thorough-screenshots");
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });

const shot = async (page, name, fullPage = false) => {
  await page.screenshot({ path: path.join(OUT_DIR, name), fullPage });
};

test.describe("Thorough / per-page screenshots", () => {
  test("01 — landing top", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await shot(page, "01-landing-top.png");
  });

  test("02 — landing full", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await shot(page, "02-landing-full.png", true);
  });

  test("03 — auth modal login", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-login");
    await page.waitForTimeout(400);
    await shot(page, "03-auth-modal-login.png");
  });

  test("04 — auth modal register", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-register");
    await page.waitForTimeout(400);
    await shot(page, "04-auth-modal-register.png");
  });

  test("05 — auth modal forgot", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-login");
    await page.click("#switch-to-forgot");
    await page.waitForTimeout(400);
    await shot(page, "05-auth-modal-forgot.png");
  });

  test("10 — app my-data", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.waitForTimeout(800);
    await shot(page, "10-app-my-data.png");
  });

  test("11 — app knowledge", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-knowledge");
    await page.waitForTimeout(800);
    await shot(page, "11-app-knowledge.png");
  });

  test("12 — app graph", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-graph");
    await page.waitForTimeout(1000);
    await shot(page, "12-app-graph.png");
  });

  test("13 — app chat", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    await page.waitForTimeout(800);
    await shot(page, "13-app-chat.png");
  });

  test("14 — app context-memory", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.waitForTimeout(800);
    await shot(page, "14-app-context-memory.png");
  });

  test("15 — app context-memory create modal", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.click("#btn-new-context");
    await page.waitForTimeout(400);
    await shot(page, "15-app-context-create-modal.png");
  });

  test("16 — app mcp-setup", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-setup");
    await page.waitForTimeout(1500);
    await shot(page, "16-app-mcp-setup.png");
  });

  test("17 — app mcp-setup antigravity tab", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-setup");
    await page.click("#tab-antigravity");
    await page.waitForTimeout(800);
    await shot(page, "17-app-mcp-setup-antigravity.png");
  });

  test("18 — app tokens", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-tokens");
    await page.waitForTimeout(800);
    await shot(page, "18-app-tokens.png");
  });

  test("19 — app mcp-logs", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-logs");
    await page.waitForTimeout(800);
    await shot(page, "19-app-mcp-logs.png");
  });

  test("20 — app EN language", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#lang-toggle");
    await page.waitForTimeout(400);
    await shot(page, "20-app-en-language.png");
  });

  test("30 — pricing page", async ({ page }) => {
    await page.goto("/pricing");
    await page.waitForLoadState("networkidle");
    await shot(page, "30-pricing.png", true);
  });
});
