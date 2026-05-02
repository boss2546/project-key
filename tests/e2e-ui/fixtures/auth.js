// @ts-check
/**
 * Shared auth helpers for thorough UI tests.
 */

const PASSWORD = "Thorough_Pass!2026";
const NAME = "Thorough Tester";

const uniqueEmail = (prefix = "ui") =>
  `${prefix}_${Date.now()}_${Math.floor(Math.random() * 1e6)}@smoke.test`;

/** Register a new user via the landing page; ends up at /app. */
async function registerAndEnterApp(page, email = uniqueEmail()) {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await page.click("#btn-show-register");
  await page.fill("#register-name", NAME);
  await page.fill("#register-email", email);
  await page.fill("#register-password", PASSWORD);
  await page.click("#btn-register");
  await page.waitForURL((url) => url.pathname === "/app", { timeout: 15000 });
  await page.waitForLoadState("networkidle");
  // Wait for sidebar to be ready
  await page.waitForSelector("#sidebar", { timeout: 10000 });
  await page.waitForTimeout(500);
  return email;
}

module.exports = { PASSWORD, NAME, uniqueEmail, registerAndEnterApp };
