// @ts-check
/**
 * v7.4.0 — SaaS Responsive Design & Mobile UX (13 tests)
 *
 * Sections:
 *   A. Touch Targets ≥44×44px on phones (WCAG / Apple HIG / Material)
 *   B. Page FAB visible on mobile, hidden on desktop, click delegates
 *   C. File list card view + kebab dropdown on mobile
 *   D. Context Memory kebab dropdown (Edit / Pin / Delete) on every card
 */

const { test, expect } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

// ─── Section A: Touch Targets ───────────────────────────────────────

test.describe("v7.4.0 / A. Touch targets ≥44px (mobile)", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("organize-all button has min-height ≥ 44px", async ({ page }) => {
    await registerAndEnterApp(page);
    const h = await page.locator("#btn-organize-all").evaluate((el) => el.getBoundingClientRect().height);
    expect(h).toBeGreaterThanOrEqual(44);
  });

  test("ctx-modal form-input has min-height ≥ 44px", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(350);
    await page.click("#nav-context-memory");
    await page.waitForTimeout(400);
    // On mobile, #btn-new-context is hidden — open the create modal via the FAB
    await page.click("#fab-ctx");
    await page.waitForTimeout(300);
    const h = await page.locator("#ctx-input-title").evaluate((el) => el.getBoundingClientRect().height);
    expect(h).toBeGreaterThanOrEqual(44);
  });

  test("modal close button has min-height ≥ 44px", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(350);
    await page.click("#profile-trigger");
    await page.waitForTimeout(300);
    const h = await page.locator("#close-profile-modal").evaluate((el) => el.getBoundingClientRect().height);
    expect(h).toBeGreaterThanOrEqual(44);
  });
});

// ─── Section B: Page FAB ────────────────────────────────────────────

test.describe("v7.4.0 / B. Floating Action Button (mobile)", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test("FAB visible on My Data, hidden on Graph", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#fab-my-data")).toBeVisible();
    await page.click("#sidebar-toggle");
    await page.waitForTimeout(350);
    await page.click("#nav-graph");
    await page.waitForTimeout(400);
    // FAB still in DOM but parent #page-my-data is now NOT .active → hidden
    const isVisible = await page.locator("#fab-my-data").isVisible();
    expect(isVisible).toBe(false);
  });

  test("FAB click triggers organize-new", async ({ page }) => {
    await registerAndEnterApp(page);
    let organizeNewCalled = false;
    await page.route("**/api/organize-new", async (route) => {
      organizeNewCalled = true;
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ new_files: 0 }),
      });
    });
    await page.click("#fab-my-data");
    // Wait for the route to actually be invoked
    await page.waitForTimeout(800);
    expect(organizeNewCalled).toBe(true);
  });

  test("page FAB stacks above guide-fab without overlap", async ({ page }) => {
    await registerAndEnterApp(page);
    const fabBox = await page.locator("#fab-my-data").boundingBox();
    const guideBox = await page.locator("#guide-fab").boundingBox();
    expect(fabBox && guideBox).toBeTruthy();
    if (fabBox && guideBox) {
      // Page FAB sits ABOVE the guide FAB — its top must be < guide top
      expect(fabBox.y + fabBox.height).toBeLessThanOrEqual(guideBox.y + 1);
    }
  });
});

test.describe("v7.4.0 / B. Desktop hides page FAB", () => {
  test("desktop viewport keeps FAB hidden", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#fab-my-data")).toBeHidden();
    // The original button is still visible on desktop
    await expect(page.locator("#btn-organize-new")).toBeVisible();
  });
});

// ─── Section C: File List Card View + Kebab ─────────────────────────

test.describe("v7.4.0 / C. File list mobile (card + kebab)", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  async function uploadOneFile(page) {
    await page.setInputFiles("#file-input", {
      name: "v7.4.0-test.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("hello v7.4.0"),
    });
    // Wait for the new file to appear in the list
    await page.waitForSelector(".file-item", { timeout: 15000 });
  }

  test("file-item renders with column layout on mobile", async ({ page }) => {
    await registerAndEnterApp(page);
    await uploadOneFile(page);
    const flexDir = await page.locator(".file-item").first().evaluate(
      (el) => getComputedStyle(el).flexDirection
    );
    expect(flexDir).toBe("column");
  });

  test("kebab button visible on each file card on mobile", async ({ page }) => {
    await registerAndEnterApp(page);
    await uploadOneFile(page);
    await expect(page.locator(".file-item .kebab-btn").first()).toBeVisible();
    // The desktop inline delete should be hidden on mobile
    await expect(page.locator(".file-item .file-action-desktop").first()).toBeHidden();
  });

  test("clicking kebab opens dropdown menu with Delete action", async ({ page }) => {
    await registerAndEnterApp(page);
    await uploadOneFile(page);
    await page.locator(".file-item .kebab-btn").first().click();
    const menu = page.locator(".file-item .kebab-menu").first();
    await expect(menu).not.toHaveClass(/hidden/);
    await expect(menu.locator(".kebab-menu-item")).toContainText(/ลบ|Delete/);
  });

  test("clicking outside closes the kebab menu", async ({ page }) => {
    await registerAndEnterApp(page);
    await uploadOneFile(page);
    await page.locator(".file-item .kebab-btn").first().click();
    await expect(page.locator(".file-item .kebab-menu").first()).not.toHaveClass(/hidden/);
    // Click the page header (outside)
    await page.locator(".page-title").first().click();
    await expect(page.locator(".file-item .kebab-menu").first()).toHaveClass(/hidden/);
  });
});

// ─── Section D: Context Memory Kebab ────────────────────────────────

test.describe("v7.4.0 / D. Context card kebab", () => {
  async function createOneContext(page, openSidebarFirst = false) {
    if (openSidebarFirst) {
      await page.click("#sidebar-toggle");
      await page.waitForTimeout(350);
    }
    await page.click("#nav-context-memory");
    await page.waitForTimeout(400);
    await page.click("#btn-new-context");
    await page.waitForTimeout(300);
    await page.fill("#ctx-input-title", "v7.4.0 ctx");
    await page.fill("#ctx-input-content", "kebab test");
    await page.click("#ctx-modal-save");
    await page.waitForSelector(".ctx-card", { timeout: 15000 });
  }

  test("ctx-card has kebab button (desktop)", async ({ page }) => {
    await registerAndEnterApp(page);
    await createOneContext(page);
    await expect(page.locator(".ctx-card .ctx-kebab").first()).toBeVisible();
  });

  test("kebab opens 3 actions: Edit, Pin, Delete", async ({ page }) => {
    await registerAndEnterApp(page);
    await createOneContext(page);
    await page.locator(".ctx-card .ctx-kebab").first().click();
    const menu = page.locator(".ctx-card .kebab-menu").first();
    await expect(menu).not.toHaveClass(/hidden/);
    const items = menu.locator(".kebab-menu-item");
    await expect(items).toHaveCount(3);
    const labels = await items.allTextContents();
    expect(labels.some((l) => /Edit|แก้ไข/i.test(l))).toBe(true);
    expect(labels.some((l) => /Pin|ปักหมุด/i.test(l))).toBe(true);
    expect(labels.some((l) => /Delete|ลบ/i.test(l))).toBe(true);
  });

  test("kebab Edit action opens the edit modal", async ({ page }) => {
    await registerAndEnterApp(page);
    await createOneContext(page);
    // After saveCtxModal closes the create modal, give loadContexts() a tick to render the card
    await page.waitForTimeout(500);
    await page.locator(".ctx-card .ctx-kebab").first().click();
    // Click the first menu item (Edit) — match by text to be explicit
    await page.locator(".ctx-card .kebab-menu .kebab-menu-item")
      .filter({ hasText: /แก้ไข|Edit/ })
      .first()
      .click();
    await expect(page.locator("#ctx-modal")).not.toHaveClass(/hidden/, { timeout: 5000 });
    await expect(page.locator("#ctx-modal-title")).toContainText(/แก้ไข|Edit/);
  });
});
