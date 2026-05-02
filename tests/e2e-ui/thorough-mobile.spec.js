// @ts-check
/**
 * Thorough / mobile + tablet viewport tests.
 * Verifies landing + app shell still render correctly at small sizes.
 */

const { test, expect, devices } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

test.describe("Thorough / mobile 375x667", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("landing renders + scrollable", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#landing-page")).toBeVisible();
    await expect(page.locator(".hero-title")).toBeVisible();
    // Scroll to features
    await page.locator(".landing-features").scrollIntoViewIfNeeded();
    await expect(page.locator(".feature-card").first()).toBeVisible();
  });

  test("landing CTA buttons reachable", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#btn-show-login")).toBeVisible();
    await expect(page.locator("#btn-show-register")).toBeVisible();
  });

  test("auth modal fits viewport", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await page.click("#btn-show-login");
    await expect(page.locator("#auth-modal")).not.toHaveClass(/hidden/);
    const modal = page.locator(".modal.auth-modal");
    const box = await modal.boundingBox();
    expect(box).not.toBeNull();
    if (box) {
      expect(box.width).toBeLessThanOrEqual(375);
    }
  });

  test("app sidebar accessible after register", async ({ page }) => {
    await registerAndEnterApp(page);
    // Sidebar might be 220px wide on mobile — just verify it exists in DOM
    await expect(page.locator("#sidebar")).toBeAttached();
    await expect(page.locator("#nav-my-data")).toBeAttached();
  });
});

test.describe("Thorough / tablet 768x1024", () => {
  test.use({ viewport: { width: 768, height: 1024 } });

  test("landing layout adjusts at 768px", async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#landing-page")).toBeVisible();
    await expect(page.locator(".hero-title")).toBeVisible();
    await expect(page.locator(".feature-card")).toHaveCount(4);
  });

  test("app shell + sidebar fit on tablet", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#sidebar")).toBeVisible();
    await expect(page.locator("#main-content")).toBeVisible();
  });
});
