// @ts-check
/**
 * Console error monitoring — fail when any of the major routes
 * emits a JavaScript error or unhandled rejection.
 *
 * We allow-list known-noisy messages (e.g. failed pre-auth fetches
 * to /api/usage that intentionally return 401 for unauthenticated visits).
 */

const { test, expect } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

const ALLOW_PATTERNS = [
  /401/,                        // expected unauth probes
  /\[auth\] verify attempt/,    // info log from cold-start retry
  /Failed to load resource: the server responded with a status of 4\d{2}/,
  /Failed to load resource: net::ERR_/, // chrome network noise
];

function watchConsole(page) {
  const errors = [];
  page.on("pageerror", (e) => {
    errors.push({ kind: "pageerror", msg: e.message });
  });
  page.on("console", (msg) => {
    if (msg.type() !== "error") return;
    const text = msg.text();
    if (ALLOW_PATTERNS.some((p) => p.test(text))) return;
    errors.push({ kind: "console.error", msg: text });
  });
  return errors;
}

test.describe("Thorough / console errors", () => {
  test("landing.html boots without JS errors", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.waitForTimeout(800);
    expect(errors, JSON.stringify(errors, null, 2)).toHaveLength(0);
  });

  test("auth modal open + close emits no errors", async ({ page }) => {
    const errors = watchConsole(page);
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-login");
    await page.waitForTimeout(200);
    await page.click("#auth-modal-close");
    await page.waitForTimeout(200);
    await page.click("#btn-show-register");
    await page.waitForTimeout(200);
    expect(errors, JSON.stringify(errors, null, 2)).toHaveLength(0);
  });

  test("registering + nav across all 8 pages emits no errors", async ({ page }) => {
    const errors = watchConsole(page);
    await registerAndEnterApp(page);
    const navs = [
      "#nav-knowledge",
      "#nav-graph",
      "#nav-chat",
      "#nav-context-memory",
      "#nav-mcp-setup",
      "#nav-tokens",
      "#nav-mcp-logs",
      "#nav-my-data",
    ];
    for (const sel of navs) {
      await page.click(sel);
      await page.waitForTimeout(400);
    }
    expect(errors, JSON.stringify(errors, null, 2)).toHaveLength(0);
  });

  test("logout + re-login emits no errors", async ({ page }) => {
    const errors = watchConsole(page);
    const email = await registerAndEnterApp(page);
    const password = "Thorough_Pass!2026";
    await page.click("#btn-logout");
    await page.waitForURL((url) => url.pathname === "/", { timeout: 10000 });
    await page.click("#btn-show-login");
    await page.fill("#login-email", email);
    await page.fill("#login-password", password);
    await page.click("#btn-login");
    await page.waitForURL((url) => url.pathname === "/app", { timeout: 15000 });
    expect(errors, JSON.stringify(errors, null, 2)).toHaveLength(0);
  });
});
