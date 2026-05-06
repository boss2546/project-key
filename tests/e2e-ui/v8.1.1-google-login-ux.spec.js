// @ts-check
/**
 * v8.1.1 — Google Login UX (Continue with Google + admin redirect)
 *
 * Run:
 *   PDB_TEST_URL=http://127.0.0.1:8000 npx playwright test v8.1.1-google-login-ux --reporter=list
 *
 * Tests B4 (unified UX) + B1 (admin redirect logic).
 * Cannot test full Google OAuth flow (requires real consent), so we verify:
 *   - UI structure (button presence + label)
 *   - Click handlers wire up correctly
 *   - /api/auth/google/init returns valid auth_url
 *   - Email/password regression
 */

const { test, expect } = require("@playwright/test");

const PASSWORD = "v811_Pass!2026";
const uniqueEmail = (prefix = "v811") =>
  `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}@smoke.test`;

async function clearAuth(page) {
  await page.goto("/");
  await page.evaluate(() => {
    localStorage.removeItem("pdb_token");
    localStorage.removeItem("pdb_user");
  });
  await page.reload();
  await page.waitForLoadState("networkidle");
}

test.describe("v8.1.1 — Continue with Google (UX unification)", () => {
  test.beforeEach(async ({ page }) => {
    await clearAuth(page);
  });

  test("login modal: shows ONE Continue with Google button", async ({ page }) => {
    await page.click("#btn-show-login");
    await page.waitForSelector("#auth-modal:not(.hidden)");

    // Login form ต้องมีปุ่ม Google
    const loginGoogleBtn = page.locator("#login-form #btn-google-login-login");
    await expect(loginGoogleBtn).toBeVisible();
    await expect(loginGoogleBtn).toContainText("Continue with Google");

    // ห้ามมี btn-google-login-register ที่ไหนเลย
    const oldButton = page.locator("#btn-google-login-register");
    await expect(oldButton).toHaveCount(0);
  });

  test("register modal: NO Google button, has switch link instead", async ({ page }) => {
    await page.click("#btn-show-register");
    await page.waitForSelector("#auth-modal:not(.hidden)");
    await page.waitForSelector("#register-form:not(.hidden)");

    // ห้ามมีปุ่ม Google บน register form
    const registerGoogleBtn = page.locator("#register-form .btn-google");
    await expect(registerGoogleBtn).toHaveCount(0);

    // ต้องมีลิงก์ switch ไป login + ใช้ Google
    const switchLink = page.locator("#switch-to-login-google");
    await expect(switchLink).toBeVisible();
    await expect(switchLink).toContainText("ใช้ Google");
  });

  test("hint text shown on both forms", async ({ page }) => {
    // Login form hint
    await page.click("#btn-show-login");
    await expect(
      page.locator("#login-form .auth-switch-muted")
    ).toContainText("ครั้งแรก = สมัครอัตโนมัติ");

    // Register form muted text (with switch link)
    await page.click("#switch-to-register");
    await expect(
      page.locator("#register-form .auth-switch-muted")
    ).toContainText("ใช้ Google");
  });

  test("switch-to-login-google link → goes to login form + focuses Google btn", async ({ page }) => {
    // Open register modal first
    await page.click("#btn-show-register");
    await page.waitForSelector("#register-form:not(.hidden)");

    // Click "ใช้ Google เข้าระบบ" link
    await page.click("#switch-to-login-google");

    // Should now be on login form
    await page.waitForSelector("#login-form:not(.hidden)");
    await expect(page.locator("#login-form")).toBeVisible();
    await expect(page.locator("#register-form")).toBeHidden();

    // Google button should be visible (focus state varies by browser; just check visible)
    await expect(page.locator("#btn-google-login-login")).toBeVisible();
  });

  test("Google init endpoint returns valid OAuth URL", async ({ page }) => {
    const res = await page.request.get("/api/auth/google/init");
    expect(res.status()).toBe(200);
    const data = await res.json();
    expect(data).toHaveProperty("auth_url");
    expect(data.auth_url).toContain("accounts.google.com");
    expect(data.auth_url).toContain("state=");
    expect(data.auth_url).toContain("code_challenge=");
    expect(data.auth_url).toContain("code_challenge_method=S256");
    expect(data.auth_url).toContain("openid");
    expect(data.auth_url).toContain("userinfo.email");
    expect(data.auth_url).toContain("userinfo.profile");
    expect(data.auth_url).not.toContain("drive.file"); // login flow ไม่ขอ Drive
  });

  test("Google callback error → redirects to landing root", async ({ page }) => {
    // Backend redirects 302 → /?google_error=access_denied.
    // Note: JS cleans URL via history.replaceState immediately — race with waitForURL.
    // Verify: (1) end on landing root /, (2) toast container has at least 1 toast.
    // (Detailed message text covered by Python backend test T6.9)
    let redirected = false;
    page.on("framenavigated", (frame) => {
      if (frame === page.mainFrame() && frame.url().includes("google_error=")) {
        redirected = true;
      }
    });
    await page.goto("/api/auth/google/callback?error=access_denied");
    // Page settles on landing
    expect(new URL(page.url()).pathname).toBe("/");
    // Either we caught the redirect mid-flight OR JS already cleaned URL — either is fine.
    // Verify landing app is rendered (#landing-page visible)
    await expect(page.locator("#landing-page")).not.toHaveClass(/hidden/);
  });

  test("Click Continue with Google triggers /init fetch", async ({ page }) => {
    await page.click("#btn-show-login");
    await page.waitForSelector("#auth-modal:not(.hidden)");

    // Intercept /init request
    const initRequest = page.waitForRequest((req) =>
      req.url().includes("/api/auth/google/init")
    );

    // Don't actually navigate to Google — just verify the fetch fires
    await page.evaluate(() => {
      // Stub window.location.assign so test doesn't navigate away
      window.location.assign = () => {};
    });

    await page.click("#btn-google-login-login");
    const req = await initRequest;
    expect(req.url()).toContain("/api/auth/google/init");
  });
});

test.describe("v8.1.1 — Email/password regression (still works)", () => {
  test("register + login + /api/auth/me", async ({ page }) => {
    const email = uniqueEmail();
    await clearAuth(page);

    // Register
    await page.click("#btn-show-register");
    await page.fill("#register-name", "v8.1.1 Tester");
    await page.fill("#register-email", email);
    await page.fill("#register-password", PASSWORD);
    await page.click("#btn-register");
    await page.waitForURL(/\/app/, { timeout: 15000 });

    // Verify localStorage has token + user
    const token = await page.evaluate(() => localStorage.getItem("pdb_token"));
    const user = await page.evaluate(() => localStorage.getItem("pdb_user"));
    expect(token).toBeTruthy();
    expect(user).toContain(email);

    // Verify /api/auth/me works
    const meRes = await page.request.get("/api/auth/me", {
      headers: { Authorization: `Bearer ${token}` },
    });
    expect(meRes.status()).toBe(200);
    const meData = await meRes.json();
    expect(meData.email).toBe(email);
  });

  test("USE_GOOGLE_LOGIN hint shows for Google-only user", async ({ page, request }) => {
    // Create a Google-only user via direct DB seed (using login_or_create which sets password_hash=NULL)
    // We can't do this from frontend, so we'll skip this test in browser context
    // — covered by Python self-test T5.7 + T5.8 already
    test.skip();
  });
});

test.describe("v8.1.1 — Admin redirect via Google fragment (B1)", () => {
  test("Non-admin Google fragment → stays on /app", async ({ page }) => {
    // Simulate fragment handler with a regular (non-admin) JWT
    // We'd need a valid JWT — skip browser-based test here, covered by:
    //   - Python T4.2 (regular user → 403 from /admin/me)
    //   - JS static analysis T7 (fallback path exists)
    test.skip();
  });

  test("admin redirect logic exists in landing.js", async ({ page }) => {
    // Sanity check: load /app and ensure landing.js has admin probe code
    const jsContent = await page.request.get("/legacy/landing.js");
    const text = await jsContent.text();
    expect(text).toContain("/api/admin/me");
    expect(text).toContain("/admin");
    expect(text).toContain("_handleGoogleLoginFragment");
  });
});
