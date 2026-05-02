// @ts-check
/**
 * Phase 5 — Verify landing.html and app.html work standalone.
 * - Static checks via raw HTTP request (no JS execution)
 * - Behavior checks via Playwright page navigation
 */

const { test, expect } = require("@playwright/test");

const TEST_PASSWORD = "Phase5_Pass!2026";
const uniqueEmail = () => `p5_${Date.now()}_${Math.floor(Math.random() * 1e6)}@smoke.test`;

// ─── 1. Static structure (no JS execution) ─────────────────────────

test.describe("Phase5 / static file structure", () => {
  test("landing.html contains landing-page, NOT #app block", async ({ request }) => {
    const res = await request.get("/landing.html");
    expect(res.status()).toBe(200);
    const html = await res.text();
    expect(html).toContain('id="landing-page"');
    expect(html).not.toContain('id="app" class="app-container');
  });

  test("app.html contains #app shell, NOT landing-page", async ({ request }) => {
    const res = await request.get("/app.html");
    expect(res.status()).toBe(200);
    const html = await res.text();
    expect(html).toContain('id="app" class="app-container');
    expect(html).not.toContain('id="landing-page"');
  });

  test("both files contain the auth modal", async ({ request }) => {
    const landing = await (await request.get("/landing.html")).text();
    const app = await (await request.get("/app.html")).text();
    expect(landing).toContain('id="auth-modal"');
    expect(app).toContain('id="auth-modal"');
  });
});

// ─── 2. Behavior on landing.html ───────────────────────────────────

async function clearAuth(page, basePath = "/") {
  await page.goto(basePath, { waitUntil: "domcontentloaded" });
  await page.evaluate(() => {
    localStorage.removeItem("pdb_token");
    localStorage.removeItem("pdb_user");
  });
}

test.describe("Phase5 / landing.html behavior", () => {
  // Each test gets a fresh browser context — localStorage starts empty.
  // Don't use addInitScript here: it runs on every navigation (including
  // the post-register redirect) and wipes the just-set token.

  test("hero, features, pipeline render", async ({ page }) => {
    await page.goto("/landing.html");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#landing-page")).toBeVisible();
    await expect(page.locator(".hero-title")).toBeVisible();
    await expect(page.locator(".feature-card")).toHaveCount(4);
  });

  test("auth modal opens with login button", async ({ page }) => {
    await page.goto("/landing.html");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-login");
    await expect(page.locator("#auth-modal")).not.toHaveClass(/hidden/);
    await expect(page.locator("#login-form")).not.toHaveClass(/hidden/);
  });

  test("registering navigates to /app", async ({ page }) => {
    await page.goto("/landing.html");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-register");
    await page.fill("#register-name", "Phase5 Tester");
    await page.fill("#register-email", uniqueEmail());
    await page.fill("#register-password", TEST_PASSWORD);
    // Click and wait for navigation to /app
    await page.click("#btn-register");
    await page.waitForURL((url) => url.pathname === "/app", { timeout: 15000 });
    expect(new URL(page.url()).pathname).toBe("/app");
  });
});

// ─── 3. Behavior on app.html ───────────────────────────────────────

test.describe("Phase5 / app.html behavior", () => {
  test("with no token, app.html redirects to /", async ({ page }) => {
    await page.goto("/", { waitUntil: "domcontentloaded" });
    await page.evaluate(() => {
      localStorage.removeItem("pdb_token");
      localStorage.removeItem("pdb_user");
    });
    await page.goto("/app.html");
    await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
    expect(new URL(page.url()).pathname).toBe("/");
  });

  test("with token, app.html shows sidebar", async ({ page }) => {
    // Register first via legacy /
    await clearAuth(page, "/");
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-register");
    await page.fill("#register-name", "AppHtml Tester");
    await page.fill("#register-email", uniqueEmail());
    await page.fill("#register-password", TEST_PASSWORD);
    await page.click("#btn-register");
    await page.waitForSelector("#app:not(.hidden)", { timeout: 10000 });
    // Navigate to app.html directly
    await page.goto("/app.html");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#sidebar")).toBeVisible({ timeout: 10000 });
    await expect(page.locator("#nav-my-data")).toBeVisible();
  });
});
