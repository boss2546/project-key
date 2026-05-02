// @ts-check
/**
 * Phase 0 — Baseline Critical Flows
 * Locks current behavior before splitting landing/app.
 * Run: PDB_TEST_URL=http://127.0.0.1:8765 npx playwright test phase0-baseline
 */

const { test, expect } = require("@playwright/test");

const TEST_PASSWORD = "Phase0_Pass!2026";
const TEST_NAME = "Phase0 Tester";

const uniqueEmail = () => `phase0_${Date.now()}_${Math.floor(Math.random() * 1e6)}@smoke.test`;

async function clearAuth(page) {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.removeItem("pdb_token");
    localStorage.removeItem("pdb_user");
  });
  await page.reload();
  await page.waitForLoadState("networkidle");
}

async function registerNewUser(page, email) {
  await clearAuth(page);
  await page.click("#btn-show-register");
  await page.fill("#register-name", TEST_NAME);
  await page.fill("#register-email", email);
  await page.fill("#register-password", TEST_PASSWORD);
  await page.click("#btn-register");
  // After Phase 6 split, register navigates to /app instead of toggling
  await page.waitForURL((url) => url.pathname === "/app", { timeout: 15000 });
  await expect(page.locator("#sidebar")).toBeVisible({ timeout: 10000 });
}

// ─── 1. LANDING PAGE STRUCTURE (current behavior baseline) ─────────────

test.describe("Phase0 / Landing structure", () => {
  test.beforeEach(async ({ page }) => clearAuth(page));

  test("landing page visible when not logged in", async ({ page }) => {
    await expect(page.locator("#landing-page")).toBeVisible();
    // After Phase 5 split, / serves landing.html with NO #app block
    await expect(page.locator("#app")).toHaveCount(0);
    await expect(page.locator("body")).toHaveClass(/show-landing/);
  });

  test("hero, features, pipeline render", async ({ page }) => {
    await expect(page.locator(".hero-title")).toBeVisible();
    await expect(page.locator(".feature-card")).toHaveCount(4);
    await expect(page.locator(".pipeline-step")).toHaveCount(4);
  });

  test("auth trigger buttons exist", async ({ page }) => {
    for (const id of [
      "#btn-show-login",
      "#btn-show-register",
      "#btn-hero-register",
      "#btn-hero-login",
      "#btn-cta-register",
      "#btn-pricing-free",
    ]) {
      await expect(page.locator(id)).toBeAttached();
    }
  });

  test("FAQ section toggles open/close", async ({ page }) => {
    const firstFaq = page.locator(".faq-item").first();
    await firstFaq.scrollIntoViewIfNeeded();
    await firstFaq.click();
    await expect(firstFaq).toHaveClass(/open/);
  });
});

// ─── 2. AUTH MODAL ─────────────────────────────────────────────────────

test.describe("Phase0 / Auth modal", () => {
  test.beforeEach(async ({ page }) => clearAuth(page));

  test("login button opens modal in login mode", async ({ page }) => {
    await page.click("#btn-show-login");
    await expect(page.locator("#auth-modal")).not.toHaveClass(/hidden/);
    await expect(page.locator("#login-form")).not.toHaveClass(/hidden/);
    await expect(page.locator("#register-form")).toHaveClass(/hidden/);
  });

  test("register button opens modal in register mode", async ({ page }) => {
    await page.click("#btn-show-register");
    await expect(page.locator("#auth-modal")).not.toHaveClass(/hidden/);
    await expect(page.locator("#register-form")).not.toHaveClass(/hidden/);
  });

  test("switch login -> register -> forgot links work", async ({ page }) => {
    await page.click("#btn-show-login");
    await page.click("#switch-to-register");
    await expect(page.locator("#register-form")).not.toHaveClass(/hidden/);
    await page.click("#switch-to-login");
    await expect(page.locator("#login-form")).not.toHaveClass(/hidden/);
    await page.click("#switch-to-forgot");
    await expect(page.locator("#forgot-form")).not.toHaveClass(/hidden/);
  });

  test("close button hides modal", async ({ page }) => {
    await page.click("#btn-show-login");
    await page.click("#auth-modal-close");
    await expect(page.locator("#auth-modal")).toHaveClass(/hidden/);
  });
});

// ─── 3. CRITICAL AUTH FLOW: REGISTER -> APP -> LOGOUT -> LANDING ──────

test.describe("Phase0 / Critical auth flow", () => {
  test("register flow lands on app shell", async ({ page }) => {
    const email = uniqueEmail();
    await registerNewUser(page, email);
    expect(new URL(page.url()).pathname).toBe("/app");
    await expect(page.locator("#sidebar-user-email")).toContainText(email);
  });

  test("logout returns to landing", async ({ page }) => {
    const email = uniqueEmail();
    await registerNewUser(page, email);
    await page.click("#btn-logout");
    await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
    await expect(page.locator("#landing-page")).toBeVisible();
  });

  test("login flow after logout works", async ({ page }) => {
    const email = uniqueEmail();
    await registerNewUser(page, email);
    await page.click("#btn-logout");
    await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-login");
    await page.fill("#login-email", email);
    await page.fill("#login-password", TEST_PASSWORD);
    await page.click("#btn-login");
    await page.waitForURL((url) => url.pathname === "/app", { timeout: 15000 });
    await expect(page.locator("#sidebar")).toBeVisible({ timeout: 10000 });
  });

  test("refresh while in app preserves authenticated state", async ({ page }) => {
    const email = uniqueEmail();
    await registerNewUser(page, email);
    expect(new URL(page.url()).pathname).toBe("/app");
    await page.reload();
    await page.waitForLoadState("networkidle");
    expect(new URL(page.url()).pathname).toBe("/app");
    await expect(page.locator("#sidebar")).toBeVisible({ timeout: 15000 });
  });

  test("invalid token in storage redirects to landing", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.setItem("pdb_token", "garbage.token.value");
      localStorage.setItem("pdb_user", JSON.stringify({ email: "x@x", id: 0 }));
    });
    // After invalid token, landing.js's verify loop fails → doLogout → redirects to /
    // Reload to trigger verify path
    await page.reload();
    await expect(page.locator("#landing-page")).toBeVisible({ timeout: 25000 });
  });
});

// ─── 4. APP SHELL: 8 PAGES ROUTING ────────────────────────────────────

test.describe("Phase0 / App page switching", () => {
  test("nav switches between pages", async ({ page }) => {
    await registerNewUser(page, uniqueEmail());
    // Already on /app after registerNewUser; ensure sidebar is ready
    await expect(page.locator("#sidebar")).toBeVisible({ timeout: 10000 });
    const navTargets = [
      ["#nav-knowledge", "#page-knowledge"],
      ["#nav-graph", "#page-graph"],
      ["#nav-chat", "#page-chat"],
      ["#nav-context-memory", "#page-context-memory"],
      ["#nav-mcp-setup", "#page-mcp-setup"],
      ["#nav-tokens", "#page-tokens"],
      ["#nav-mcp-logs", "#page-mcp-logs"],
      ["#nav-my-data", "#page-my-data"],
    ];
    for (const [nav, panel] of navTargets) {
      await page.click(nav);
      await expect(page.locator(panel)).toHaveClass(/active/);
    }
  });
});

// ─── 5. STATIC ASSETS ─────────────────────────────────────────────────

test.describe("Phase0 / Static assets reachable", () => {
  test("styles.css loads", async ({ page }) => {
    const res = await page.request.get("/legacy/styles.css");
    expect(res.status()).toBe(200);
  });
  test("app.js loads", async ({ page }) => {
    const res = await page.request.get("/legacy/app.js");
    expect(res.status()).toBe(200);
  });
  test("/api/auth/me returns 401 without token", async ({ page }) => {
    const res = await page.request.get("/api/auth/me");
    expect(res.status()).toBe(401);
  });
});
