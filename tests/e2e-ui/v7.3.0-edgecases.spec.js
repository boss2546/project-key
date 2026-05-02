// @ts-check
/**
 * v7.3.0 — UX Edge-Cases & Mobile Fixes (12 tests)
 *
 * Sections:
 *   1. Mobile responsive — hamburger, sidebar slide-out, modal width
 *   2. Form validation UX — .is-invalid + auto-focus on ctx-modal
 *   3. Z-index hierarchy — modals above guide-drawer, toast above all
 */

const { test, expect } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

// ─── Section 1: Mobile responsive ───────────────────────────────────

test.describe("v7.3.0 / 1. Mobile responsive (375x667)", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("hamburger visible + sidebar hidden by default", async ({ page }) => {
    await registerAndEnterApp(page);
    const toggle = page.locator("#sidebar-toggle");
    await expect(toggle).toBeVisible();
    // Sidebar exists but is translated off-screen — its bounding box has x < 0
    const sidebar = page.locator("#sidebar");
    const box = await sidebar.boundingBox();
    expect(box).not.toBeNull();
    if (box) expect(box.x).toBeLessThan(0);
  });

  test("clicking hamburger reveals sidebar (slides into viewport)", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    // After CSS transition, sidebar x should be ≥ 0
    await page.waitForTimeout(400);
    const box = await page.locator("#sidebar").boundingBox();
    expect(box).not.toBeNull();
    if (box) expect(box.x).toBeGreaterThanOrEqual(0);
    await expect(page.locator(".app-container")).toHaveClass(/sidebar-open/);
    // Backdrop should be visible
    await expect(page.locator("#sidebar-backdrop")).toBeVisible();
  });

  test("clicking backdrop closes sidebar", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(300);
    // The sidebar (220px wide) covers the left edge of the backdrop;
    // click further to the right where only the backdrop is on top.
    await page.click("#sidebar-backdrop", { position: { x: 320, y: 400 } });
    await page.waitForTimeout(400);
    await expect(page.locator(".app-container")).not.toHaveClass(/sidebar-open/);
  });

  test("clicking nav item closes sidebar after navigation", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(300);
    await page.click("#nav-knowledge");
    await page.waitForTimeout(400);
    await expect(page.locator(".app-container")).not.toHaveClass(/sidebar-open/);
    // And the page should have switched
    await expect(page.locator("#page-knowledge")).toHaveClass(/active/);
  });

  test("ESC closes sidebar on mobile", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(300);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400);
    await expect(page.locator(".app-container")).not.toHaveClass(/sidebar-open/);
  });

  test("modal width fits the mobile viewport (<= viewport width)", async ({ page }) => {
    await registerAndEnterApp(page);
    // On mobile the sidebar is off-screen, so the profile trigger inside it
    // isn't clickable. Open the sidebar first, then trigger the modal.
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(350);
    await page.click("#profile-trigger");
    await expect(page.locator("#profile-modal")).not.toHaveClass(/hidden/);
    const modalBox = await page.locator("#profile-modal .modal").boundingBox();
    expect(modalBox).not.toBeNull();
    if (modalBox) {
      // Must fit inside the 375px viewport. Our @media rule pins width
      // to 92vw on phones; use viewport width as the upper bound to
      // guard against any future regression.
      expect(modalBox.width).toBeLessThanOrEqual(375);
    }
  });
});

test.describe("v7.3.0 / 1. Desktop hides hamburger", () => {
  test("desktop viewport keeps the hamburger hidden", async ({ page }) => {
    await registerAndEnterApp(page);
    // Default Playwright viewport is 1366x768 — hamburger should be display:none
    await expect(page.locator("#sidebar-toggle")).toBeHidden();
    // And sidebar is visible in the static layout
    await expect(page.locator("#sidebar")).toBeVisible();
  });
});

// ─── Section 2: Form validation UX ──────────────────────────────────

test.describe("v7.3.0 / 2. Context create form validation", () => {
  test("empty title gets .is-invalid + receives focus", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.click("#btn-new-context");
    await expect(page.locator("#ctx-modal")).not.toHaveClass(/hidden/);
    // Click save with everything empty
    await page.click("#ctx-modal-save");
    const titleEl = page.locator("#ctx-input-title");
    await expect(titleEl).toHaveClass(/is-invalid/);
    expect(await titleEl.evaluate((el) => el === document.activeElement)).toBe(true);
  });

  test("empty content (after title filled) marks textarea invalid + focused", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.click("#btn-new-context");
    await page.fill("#ctx-input-title", "Hello");
    await page.click("#ctx-modal-save");
    const contentEl = page.locator("#ctx-input-content");
    await expect(contentEl).toHaveClass(/is-invalid/);
    expect(await contentEl.evaluate((el) => el === document.activeElement)).toBe(true);
  });

  test("typing in invalid field clears the .is-invalid class", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.click("#btn-new-context");
    await page.click("#ctx-modal-save");
    await expect(page.locator("#ctx-input-title")).toHaveClass(/is-invalid/);
    await page.fill("#ctx-input-title", "x");
    await expect(page.locator("#ctx-input-title")).not.toHaveClass(/is-invalid/);
  });

  test("filling both fields saves successfully", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.click("#btn-new-context");
    await page.fill("#ctx-input-title", "Phase D test");
    await page.fill("#ctx-input-content", "some content");
    await page.click("#ctx-modal-save");
    await expect(page.locator("#ctx-modal")).toHaveClass(/hidden/, { timeout: 5000 });
  });
});

// ─── Section 3: Z-index hierarchy ───────────────────────────────────

test.describe("v7.3.0 / 3. Z-index hierarchy", () => {
  test("modal-overlay z-index > guide-drawer (10000)", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#profile-trigger");
    const z = await page.locator("#profile-modal").evaluate(
      (el) => parseInt(getComputedStyle(el).zIndex, 10)
    );
    expect(z).toBeGreaterThan(10000);
  });

  test("toast-container z-index > modal-overlay", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#profile-trigger");
    const modalZ = await page.locator("#profile-modal").evaluate(
      (el) => parseInt(getComputedStyle(el).zIndex, 10)
    );
    const toastZ = await page.locator("#toast-container").evaluate(
      (el) => parseInt(getComputedStyle(el).zIndex, 10)
    );
    expect(toastZ).toBeGreaterThan(modalZ);
  });

  test("opening modal while guide drawer is open keeps modal visible", async ({ page }) => {
    await registerAndEnterApp(page);
    // Open the guide drawer first
    await page.click("#guide-fab");
    await expect(page.locator("#guide-drawer")).toHaveClass(/open/);
    // The guide-overlay (z 9999) blocks normal clicks, so trigger the
    // profile modal programmatically — same as if the user used a
    // shortcut while the guide was up.
    await page.evaluate(() => {
      document.getElementById("profile-modal")?.classList.remove("hidden");
    });
    await expect(page.locator("#profile-modal")).not.toHaveClass(/hidden/);
    // At the modal centre, the topmost element must NOT be guide-drawer.
    const modalBox = await page.locator("#profile-modal .modal").boundingBox();
    expect(modalBox).not.toBeNull();
    if (modalBox) {
      const cx = modalBox.x + modalBox.width / 2;
      const cy = modalBox.y + 30; // header area
      const topElInfo = await page.evaluate(([x, y]) => {
        const el = document.elementFromPoint(x, y);
        let cur = el;
        while (cur && cur !== document.body) {
          if (cur.id === "profile-modal") return "profile-modal";
          if (cur.id === "guide-drawer") return "guide-drawer";
          if (cur.id === "guide-overlay") return "guide-overlay";
          cur = cur.parentElement;
        }
        return el ? el.tagName : null;
      }, [cx, cy]);
      expect(topElInfo).toBe("profile-modal");
    }
  });
});
