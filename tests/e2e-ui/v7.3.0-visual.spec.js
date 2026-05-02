// @ts-check
/**
 * v7.3.0 — Visual smoke screenshots for human review.
 * Outputs to tests/v7.3.0-visual/ — desktop + mobile + edge case states.
 */

const { test } = require("@playwright/test");
const path = require("path");
const fs = require("fs");
const { registerAndEnterApp } = require("./fixtures/auth.js");

const OUT_DIR = path.join(__dirname, "..", "v7.3.0-visual");
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
const shot = (page, name, fullPage = false) =>
  page.screenshot({ path: path.join(OUT_DIR, name), fullPage });

test.describe("v7.3.0 / mobile screenshots (375x667)", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("01 — mobile landing", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await shot(page, "01-mobile-landing.png");
  });

  test("02 — mobile app sidebar closed (hamburger visible)", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.waitForTimeout(500);
    await shot(page, "02-mobile-sidebar-closed.png");
  });

  test("03 — mobile app sidebar open (slide-in + backdrop)", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(500);
    await shot(page, "03-mobile-sidebar-open.png");
  });

  test("04 — mobile profile modal (92vw fit)", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(400);
    await page.click("#profile-trigger");
    await page.waitForTimeout(500);
    await shot(page, "04-mobile-profile-modal.png");
  });

  test("05 — mobile context create modal", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(300);
    await page.click("#nav-context-memory");
    await page.waitForTimeout(400);
    await page.click("#btn-new-context");
    await page.waitForTimeout(500);
    await shot(page, "05-mobile-ctx-create.png");
  });
});

test.describe("v7.3.0 / desktop edge cases", () => {
  test("10 — ctx-modal validation invalid state", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.waitForTimeout(400);
    await page.click("#btn-new-context");
    await page.waitForTimeout(300);
    // Click save with everything empty → title becomes red
    await page.click("#ctx-modal-save");
    await page.waitForTimeout(300);
    await shot(page, "10-ctx-validation-empty-title.png");
  });

  test("11 — ctx-modal validation: title filled, content empty", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.waitForTimeout(300);
    await page.click("#btn-new-context");
    await page.fill("#ctx-input-title", "My note");
    await page.click("#ctx-modal-save");
    await page.waitForTimeout(300);
    await shot(page, "11-ctx-validation-empty-content.png");
  });

  test("12 — guide drawer + profile modal layered correctly", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#guide-fab");
    await page.waitForTimeout(400);
    await page.evaluate(() => {
      document.getElementById("profile-modal")?.classList.remove("hidden");
    });
    await page.waitForTimeout(400);
    await shot(page, "12-modal-above-guide.png");
  });
});
