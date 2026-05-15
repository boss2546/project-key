const { test, expect } = require('@playwright/test');

test.describe('Dev Logger — floating overlay', () => {
  test('mounts on landing + exposes API + captures fetch', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    await page.goto('http://127.0.0.1:8000/');

    // Public API exists
    const apiKeys = await page.evaluate(() => Object.keys(window.__pdbDevLogger || {}));
    expect(apiKeys).toEqual(expect.arrayContaining(['show', 'hide', 'full', 'clear', 'entries', 'pause']));

    // Floating button visible
    await expect(page.locator('#__pdb-dev-btn')).toBeVisible();

    // No page errors thrown during init
    expect(errors).toEqual([]);

    // Trigger a fetch (the page's own /api/auth/me probe should already log too,
    // but force a deterministic one)
    await page.evaluate(async () => {
      try { await fetch('/api/healthz/queue'); } catch (_) {}
    });

    // Open panel via API → row should appear
    await page.evaluate(() => window.__pdbDevLogger.show());
    await expect(page.locator('#__pdb-dev-panel')).toBeVisible();

    const entries = await page.evaluate(() => window.__pdbDevLogger.entries().length);
    expect(entries).toBeGreaterThan(0);

    // Fullscreen via shortcut
    await page.keyboard.press('Control+Shift+L');
    await expect(page.locator('#__pdb-dev-full')).toBeVisible();
    // Esc closes
    await page.keyboard.press('Escape');
    await expect(page.locator('#__pdb-dev-full')).toHaveCount(0);
  });

  test('mounts on /app page too (follows user across pages)', async ({ page }) => {
    await page.goto('http://127.0.0.1:8000/app');
    await expect(page.locator('#__pdb-dev-btn')).toBeVisible();
    const hasApi = await page.evaluate(() => typeof window.__pdbDevLogger?.show === 'function');
    expect(hasApi).toBe(true);
  });
});
