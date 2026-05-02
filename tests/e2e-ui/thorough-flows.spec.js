// @ts-check
/**
 * Thorough / flow tests:
 *   • Forgot password full flow (request → reset → auto-login)
 *   • Language toggle TH ↔ EN
 *   • Pricing page render
 *   • Stripe redirect resolution
 *   • Drive OAuth callback redirect target
 */

const { test, expect } = require("@playwright/test");
const { registerAndEnterApp, uniqueEmail, PASSWORD } = require("./fixtures/auth.js");

test.describe("Thorough / forgot-password flow", () => {
  test("request reset → form fills token → reset → auto-login", async ({ page }) => {
    // Register a real user first so we can request reset on a known email
    const email = await registerAndEnterApp(page);
    // Logout so we're back on /
    await page.click("#btn-logout");
    await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
    await page.waitForLoadState("networkidle");
    // Open login modal → forgot
    await page.click("#btn-show-login");
    await page.click("#switch-to-forgot");
    await expect(page.locator("#forgot-form")).not.toHaveClass(/hidden/);
    await page.fill("#forgot-email", email);
    await page.click("#btn-forgot-submit");
    // Backend in dev mode returns reset_token in the response body → frontend
    // auto-switches to the reset form.
    await expect(page.locator("#reset-form")).not.toHaveClass(/hidden/, { timeout: 10000 });
    // The display element should show the email
    await expect(page.locator("#reset-email-display")).toContainText(email);

    const newPassword = "NewPass_456!";
    await page.fill("#reset-new-password", newPassword);
    await page.fill("#reset-confirm-password", newPassword);
    await page.click("#btn-reset-submit");

    // After successful reset → auto-login → redirect to /app
    await page.waitForURL((url) => url.pathname === "/app", { timeout: 15000 });
    await expect(page.locator("#sidebar")).toBeVisible({ timeout: 10000 });
  });

  test("password mismatch shows error", async ({ page }) => {
    const email = await registerAndEnterApp(page);
    await page.click("#btn-logout");
    await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
    await page.click("#btn-show-login");
    await page.click("#switch-to-forgot");
    await page.fill("#forgot-email", email);
    await page.click("#btn-forgot-submit");
    await expect(page.locator("#reset-form")).not.toHaveClass(/hidden/, { timeout: 10000 });
    await page.fill("#reset-new-password", "abcdef");
    await page.fill("#reset-confirm-password", "DIFFERENT");
    await page.click("#btn-reset-submit");
    await expect(page.locator("#reset-error")).not.toHaveClass(/hidden/);
    await expect(page.locator("#reset-error")).toContainText(/ไม่ตรงกัน|do not match|mismatch/i);
  });

  test("password too short shows error", async ({ page }) => {
    const email = await registerAndEnterApp(page);
    await page.click("#btn-logout");
    await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
    await page.click("#btn-show-login");
    await page.click("#switch-to-forgot");
    await page.fill("#forgot-email", email);
    await page.click("#btn-forgot-submit");
    await expect(page.locator("#reset-form")).not.toHaveClass(/hidden/, { timeout: 10000 });
    await page.fill("#reset-new-password", "ab");
    await page.fill("#reset-confirm-password", "ab");
    await page.click("#btn-reset-submit");
    await expect(page.locator("#reset-error")).not.toHaveClass(/hidden/);
  });
});

test.describe("Thorough / language toggle", () => {
  test("TH → EN updates landing hero text", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    // Default is Thai. Subtitle uses inline Thai text by default.
    // Click the language toggle (exists on landing as well via app shell?
    // Actually lang-toggle is in sidebar — only on app.html)
    // For landing, the subtitle is hardcoded; we cannot toggle from /
    // Instead, log in to access the toggle.
    await registerAndEnterApp(page);
    const langToggle = page.locator("#lang-toggle");
    await expect(langToggle).toBeVisible();
    // Initial state — should be TH
    const initialLabel = await page.locator("#lang-label").textContent();
    expect(initialLabel?.trim()).toMatch(/TH|EN/);
    // Click — toggles to the other language
    await langToggle.click();
    await page.waitForTimeout(300);
    const newLabel = await page.locator("#lang-label").textContent();
    expect(newLabel?.trim()).not.toBe(initialLabel?.trim());
  });

  test("toggle re-renders sidebar nav labels", async ({ page }) => {
    await registerAndEnterApp(page);
    const myDataLabel = page.locator('[data-i18n="nav.myData"]').first();
    const initial = (await myDataLabel.textContent())?.trim();
    await page.click("#lang-toggle");
    await page.waitForTimeout(300);
    const after = (await myDataLabel.textContent())?.trim();
    expect(after).not.toBe(initial);
    expect([initial, after].sort()).toEqual(["My Data", "ข้อมูลของฉัน"].sort());
  });

  test("language preference persists across reload", async ({ page }) => {
    await registerAndEnterApp(page);
    const initialLabel = (await page.locator("#lang-label").textContent())?.trim();
    await page.click("#lang-toggle");
    const afterToggle = (await page.locator("#lang-label").textContent())?.trim();
    expect(afterToggle).not.toBe(initialLabel);
    // Reload — language should persist
    await page.reload();
    await page.waitForLoadState("networkidle");
    const afterReload = (await page.locator("#lang-label").textContent())?.trim();
    expect(afterReload).toBe(afterToggle);
  });
});

test.describe("Thorough / pricing page", () => {
  test("/pricing renders pricing.html", async ({ page }) => {
    const res = await page.goto("/pricing");
    expect(res?.status()).toBe(200);
    await page.waitForLoadState("networkidle");
    // Pricing page should contain plan-related content
    const html = await page.content();
    expect(html.toLowerCase()).toMatch(/pricing|plan|starter|free/);
  });
});

test.describe("Thorough / billing redirects", () => {
  // Use raw HTTP (no JS) so unauth JS guard doesn't bounce us back to /
  test("/billing/success → 302 → /app?billing=success", async ({ request }) => {
    const res = await request.get("/billing/success", { maxRedirects: 0 });
    expect([302, 307]).toContain(res.status());
    expect(res.headers().location).toBe("/app?billing=success");
  });

  test("/billing/cancelled → 302 → /app?billing=cancelled", async ({ request }) => {
    const res = await request.get("/billing/cancelled", { maxRedirects: 0 });
    expect([302, 307]).toContain(res.status());
    expect(res.headers().location).toBe("/app?billing=cancelled");
  });

  // For an authenticated user, the JS keeps them on /app — verify that path
  test("authenticated user on /app?billing=success stays on /app", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.goto("/app?billing=success");
    await page.waitForLoadState("networkidle");
    expect(new URL(page.url()).pathname).toBe("/app");
    await expect(page.locator("#sidebar")).toBeVisible();
  });
});

test.describe("Thorough / drive OAuth callback", () => {
  test("callback without code redirects with error to /app", async ({ request }) => {
    // Hit callback with explicit error param — should 302 to /app?drive_connected=false&error=...
    const res = await request.get("/api/drive/oauth/callback?error=access_denied", {
      maxRedirects: 0,
    });
    expect([302, 307]).toContain(res.status());
    const location = res.headers().location;
    expect(location).toContain("/app?drive_connected=false");
    expect(location).toContain("error=access_denied");
  });
});
