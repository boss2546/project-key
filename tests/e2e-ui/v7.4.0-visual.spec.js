// @ts-check
/**
 * v7.4.0 — Visual smoke screenshots for human review.
 * Outputs to tests/v7.4.0-visual/ — mobile + desktop edge states.
 */

const { test } = require("@playwright/test");
const path = require("path");
const fs = require("fs");
const { registerAndEnterApp } = require("./fixtures/auth.js");

const OUT_DIR = path.join(__dirname, "..", "v7.4.0-visual");
if (!fs.existsSync(OUT_DIR)) fs.mkdirSync(OUT_DIR, { recursive: true });
const shot = (page, name, fullPage = false) =>
  page.screenshot({ path: path.join(OUT_DIR, name), fullPage });

const TEST_FILE = {
  name: "v7.4.0-shot.txt",
  mimeType: "text/plain",
  buffer: Buffer.from("hello"),
};

async function uploadOne(page) {
  await page.setInputFiles("#file-input", TEST_FILE);
  await page.waitForSelector(".file-item", { timeout: 15000 });
  await page.waitForTimeout(400);
}

async function createOneCtx(page, openSidebarFirst = false) {
  if (openSidebarFirst) {
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(350);
  }
  await page.click("#nav-context-memory");
  await page.waitForTimeout(400);
  if (openSidebarFirst) {
    await page.click("#fab-ctx");
  } else {
    await page.click("#btn-new-context");
  }
  await page.waitForTimeout(300);
  await page.fill("#ctx-input-title", "Visual smoke");
  await page.fill("#ctx-input-content", "v7.4.0 kebab demo");
  await page.click("#ctx-modal-save");
  await page.waitForSelector(".ctx-card", { timeout: 15000 });
  await page.waitForTimeout(400);
}

test.describe("v7.4.0 / mobile screenshots (375x667)", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("01 — my-data with FAB", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.waitForTimeout(600);
    await shot(page, "01-mobile-my-data-fab.png");
  });

  test("02 — my-data file card with kebab", async ({ page }) => {
    await registerAndEnterApp(page);
    await uploadOne(page);
    await shot(page, "02-mobile-file-card.png");
  });

  test("03 — file kebab menu open", async ({ page }) => {
    await registerAndEnterApp(page);
    await uploadOne(page);
    await page.locator(".file-item .kebab-btn").first().click();
    await page.waitForTimeout(200);
    await shot(page, "03-mobile-file-kebab-open.png");
  });

  test("04 — context-memory with FAB", async ({ page }) => {
    await registerAndEnterApp(page);
    await createOneCtx(page, true);
    await shot(page, "04-mobile-ctx-fab.png");
  });

  test("05 — ctx kebab menu open (3 actions)", async ({ page }) => {
    await registerAndEnterApp(page);
    await createOneCtx(page, true);
    await page.locator(".ctx-card .ctx-kebab").first().click();
    await page.waitForTimeout(200);
    await shot(page, "05-mobile-ctx-kebab-open.png");
  });

  test("06 — ctx-modal inputs (44px touch targets)", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(350);
    await page.click("#nav-context-memory");
    await page.waitForTimeout(400);
    await page.click("#fab-ctx");
    await page.waitForTimeout(300);
    await shot(page, "06-mobile-ctx-modal-44px.png");
  });
});

test.describe("v7.4.0 / desktop unchanged (1366x768)", () => {
  test("10 — desktop my-data shows inline buttons (no FAB)", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.waitForTimeout(600);
    await shot(page, "10-desktop-my-data.png");
  });

  test("11 — desktop ctx-card shows kebab top-right", async ({ page }) => {
    await registerAndEnterApp(page);
    await createOneCtx(page);
    await shot(page, "11-desktop-ctx-kebab.png");
  });
});
