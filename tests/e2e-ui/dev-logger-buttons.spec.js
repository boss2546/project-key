// แตะทุกปุ่ม + คำสั่งทุกตัวของ dev-logger เพื่อ verify ว่าทำงานครบ
const { test, expect } = require('@playwright/test');

const BASE = 'http://127.0.0.1:8000';

test.describe('Dev Logger — every button + every keyboard shortcut', () => {

  test.beforeEach(async ({ page, context }) => {
    // ให้ Clipboard API ใช้ได้ใน Playwright
    await context.grantPermissions(['clipboard-read', 'clipboard-write']);
    await page.goto(BASE + '/');
    // wait for dev-logger to mount
    await expect(page.locator('#__pdb-dev-btn')).toBeVisible();
  });

  test('B1 · floating button click → opens compact panel', async ({ page }) => {
    await expect(page.locator('#__pdb-dev-panel')).toHaveCount(0);
    await page.click('#__pdb-dev-btn');
    await expect(page.locator('#__pdb-dev-panel')).toBeVisible();
  });

  test('B2 · floating button click again → closes panel', async ({ page }) => {
    await page.click('#__pdb-dev-btn');
    await expect(page.locator('#__pdb-dev-panel')).toBeVisible();
    await page.click('#__pdb-dev-btn');
    await expect(page.locator('#__pdb-dev-panel')).toHaveCount(0);
  });

  // ── compact panel buttons ──

  test('B3 · compact panel "Close (✕)" button → closes panel', async ({ page }) => {
    await page.click('#__pdb-dev-btn');
    const closeBtn = page.locator('#__pdb-dev-panel .pdb-dev-actions button').last();
    await expect(closeBtn).toHaveText('✕');
    await closeBtn.click();
    await expect(page.locator('#__pdb-dev-panel')).toHaveCount(0);
  });

  test('B4 · compact "Pause (⏸)" button toggles paused state', async ({ page }) => {
    await page.click('#__pdb-dev-btn');
    const pauseBtn = page.locator('#__pdb-dev-panel .pdb-dev-actions button').first();
    await expect(pauseBtn).toHaveText('⏸');
    await pauseBtn.click();
    // re-rendered — should now show ▶ (resume icon)
    const resumeBtn = page.locator('#__pdb-dev-panel .pdb-dev-actions button').first();
    await expect(resumeBtn).toHaveText('▶');
    // click again → resume
    await resumeBtn.click();
    await expect(page.locator('#__pdb-dev-panel .pdb-dev-actions button').first()).toHaveText('⏸');
  });

  test('B5 · compact "Full (⛶)" button opens fullscreen', async ({ page }) => {
    await page.click('#__pdb-dev-btn');
    const fullBtn = page.locator('#__pdb-dev-panel .pdb-dev-actions button').nth(1);
    await expect(fullBtn).toHaveText('⛶');
    await fullBtn.click();
    await expect(page.locator('#__pdb-dev-full')).toBeVisible();
  });

  test('B6 · compact "Copy" copies log JSON to clipboard + flash toast', async ({ page }) => {
    // generate a fetch first so there's something to copy
    await page.evaluate(() => fetch('/api/personality/reference').catch(() => {}));
    await page.click('#__pdb-dev-btn');
    await page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Copy' }).click();
    // wait for flash to appear
    await expect(page.locator('text=/คัดลอก/')).toBeVisible({ timeout: 3000 });
    // clipboard should contain JSON array
    const clip = await page.evaluate(() => navigator.clipboard.readText());
    expect(clip.startsWith('[')).toBe(true);
    const parsed = JSON.parse(clip);
    expect(Array.isArray(parsed)).toBe(true);
    expect(parsed.length).toBeGreaterThan(0);
  });

  test('B7 · compact "Clear" wipes logs via 2-click confirm pattern', async ({ page }) => {
    // pause logger to keep state stable during the test (avoid background polling noise)
    await page.evaluate(() => window.__pdbDevLogger.pause(true));
    await page.evaluate(() => console.log('marker before clear'));
    const before = await page.evaluate(() => window.__pdbDevLogger.entries().length);
    expect(before).toBeGreaterThan(0);

    await page.click('#__pdb-dev-btn');
    // 1st click → button flips to "Sure?"
    await page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Clear' }).click();
    await expect(page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Sure?' })).toBeVisible();
    // 2nd click → actually clear
    await page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Sure?' }).click();
    const after = await page.evaluate(() => window.__pdbDevLogger.entries().length);
    expect(after).toBe(0);
    await expect(page.locator('#__pdb-dev-panel .pdb-dev-empty')).toBeVisible();
  });

  test('B8 · compact "Clear" single-click does NOT wipe (armed state only)', async ({ page }) => {
    await page.evaluate(() => window.__pdbDevLogger.pause(true));
    await page.evaluate(() => console.log('marker keep'));
    const before = await page.evaluate(() => window.__pdbDevLogger.entries().length);

    await page.click('#__pdb-dev-btn');
    // 1st click only → arms but does NOT clear
    await page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Clear' }).click();
    await expect(page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Sure?' })).toBeVisible();
    const stillThere = await page.evaluate(() => window.__pdbDevLogger.entries().length);
    expect(stillThere).toBe(before);  // unchanged after just 1 click
  });

  test('B8b · armed state reverts to "Clear" after 3-second timeout', async ({ page }) => {
    await page.evaluate(() => window.__pdbDevLogger.pause(true));
    await page.evaluate(() => console.log('marker timeout'));
    await page.click('#__pdb-dev-btn');
    await page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Clear' }).click();
    await expect(page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Sure?' })).toBeVisible();
    // wait 3.2s for timeout
    await page.waitForTimeout(3200);
    await expect(page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Clear' })).toBeVisible();
    await expect(page.locator('#__pdb-dev-panel .pdb-dev-actions button', { hasText: 'Sure?' })).toHaveCount(0);
  });

  // ── keyboard shortcuts ──

  test('B9 · Ctrl+Shift+L opens fullscreen', async ({ page }) => {
    await expect(page.locator('#__pdb-dev-full')).toHaveCount(0);
    await page.keyboard.press('Control+Shift+L');
    await expect(page.locator('#__pdb-dev-full')).toBeVisible();
  });

  test('B10 · Ctrl+Shift+L again closes fullscreen', async ({ page }) => {
    await page.keyboard.press('Control+Shift+L');
    await expect(page.locator('#__pdb-dev-full')).toBeVisible();
    await page.keyboard.press('Control+Shift+L');
    await expect(page.locator('#__pdb-dev-full')).toHaveCount(0);
  });

  test('B11 · Escape closes fullscreen', async ({ page }) => {
    await page.keyboard.press('Control+Shift+L');
    await expect(page.locator('#__pdb-dev-full')).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(page.locator('#__pdb-dev-full')).toHaveCount(0);
  });

  // ── fullscreen buttons ──

  test('B12 · fullscreen "Close (✕)" button closes', async ({ page }) => {
    await page.keyboard.press('Control+Shift+L');
    await page.locator('#__pdb-dev-full button', { hasText: /Close/i }).click();
    await expect(page.locator('#__pdb-dev-full')).toHaveCount(0);
  });

  test('B13 · fullscreen filter buttons work (All/Fetch/Click/Storage/Meta/Error/Warn/Form/Nav/Log)', async ({ page }) => {
    // generate variety
    await page.evaluate(() => {
      console.log('test log line');
      console.warn('test warn line');
      console.error('test error line');
      try { fetch('/api/personality/reference'); } catch (_) {}
      localStorage.setItem('__test_key', 'hello');
      localStorage.removeItem('__test_key');
    });
    await page.waitForTimeout(200);

    await page.keyboard.press('Control+Shift+L');
    await expect(page.locator('#__pdb-dev-full')).toBeVisible();

    const filters = ['All', 'Fetch', 'Log', 'Warn', 'Error', 'Click', 'Form', 'Storage', 'Nav', 'Meta/Perf'];
    for (const f of filters) {
      await page.locator('#__pdb-dev-full .pdb-dev-filter button', { hasText: new RegExp('^' + f + '$') }).click();
      // verify active class flipped (one filter button has .active)
      const activeText = await page.locator('#__pdb-dev-full .pdb-dev-filter button.active').textContent();
      expect(activeText).toBe(f);
    }
  });

  test('B14 · fullscreen search input filters live', async ({ page }) => {
    await page.evaluate(() => {
      console.log('UNIQUE_NEEDLE_marker_xyz');
      console.log('other normal line');
    });
    await page.keyboard.press('Control+Shift+L');
    await page.fill('#__pdb-dev-full input.pdb-dev-search', 'UNIQUE_NEEDLE_marker_xyz');
    // only matching rows should remain
    const rowCount = await page.locator('#__pdb-dev-full .pdb-dev-frow').count();
    expect(rowCount).toBeGreaterThan(0);
    // every visible row contains the needle
    const texts = await page.locator('#__pdb-dev-full .pdb-dev-frow').allTextContents();
    for (const txt of texts) {
      expect(txt.toLowerCase()).toContain('unique_needle_marker_xyz');
    }
  });

  test('B15 · fullscreen Pause/Resume button toggles', async ({ page }) => {
    await page.keyboard.press('Control+Shift+L');
    const pauseBtn = page.locator('#__pdb-dev-full button', { hasText: /Pause/i });
    await pauseBtn.click();
    // now should be "Resume"
    await expect(page.locator('#__pdb-dev-full button', { hasText: /Resume/i })).toBeVisible();
    await page.locator('#__pdb-dev-full button', { hasText: /Resume/i }).click();
    await expect(page.locator('#__pdb-dev-full button', { hasText: /Pause/i })).toBeVisible();
  });

  test('B16 · fullscreen "Copy All" button works', async ({ page }) => {
    await page.evaluate(() => console.log('row for fullscreen copy'));
    await page.keyboard.press('Control+Shift+L');
    await page.locator('#__pdb-dev-full button', { hasText: 'Copy All' }).click();
    await expect(page.locator('text=/คัดลอก/')).toBeVisible({ timeout: 3000 });
    const clip = await page.evaluate(() => navigator.clipboard.readText());
    expect(clip).toContain('row for fullscreen copy');
  });

  test('B17 · fullscreen "Clear All" wipes via 2-click confirm pattern', async ({ page }) => {
    await page.evaluate(() => window.__pdbDevLogger.pause(true));
    await page.evaluate(() => console.log('about to be cleared'));
    await page.keyboard.press('Control+Shift+L');
    // 1st click → arms
    await page.locator('#__pdb-dev-full button', { hasText: 'Clear All' }).click();
    await expect(page.locator('#__pdb-dev-full button', { hasText: 'Sure?' })).toBeVisible();
    // 2nd click → wipes
    await page.locator('#__pdb-dev-full button', { hasText: 'Sure?' }).click();
    const after = await page.evaluate(() => window.__pdbDevLogger.entries().length);
    expect(after).toBe(0);
  });

  test('B18 · clicking row in fullscreen expands detail · click again collapses', async ({ page }) => {
    await page.evaluate(() => console.log('row to expand'));
    await page.keyboard.press('Control+Shift+L');
    // filter to just our log line for predictability
    await page.fill('#__pdb-dev-full input.pdb-dev-search', 'row to expand');
    const firstRow = page.locator('#__pdb-dev-full .pdb-dev-frow').first();
    await firstRow.click();
    await expect(firstRow.locator('.pdb-dev-fdetail')).toBeVisible();
    await firstRow.click();
    await expect(firstRow.locator('.pdb-dev-fdetail')).toHaveCount(0);
  });

  // ── public API ──

  test('B19 · window.__pdbDevLogger.{show,hide,full,closeFull,pause,clear,copy,entries} all callable', async ({ page }) => {
    const api = await page.evaluate(() => {
      const L = window.__pdbDevLogger;
      const types = {};
      ['show', 'hide', 'full', 'closeFull', 'pause', 'clear', 'copy', 'entries'].forEach(k => {
        types[k] = typeof L[k];
      });
      return types;
    });
    for (const k of Object.keys(api)) expect(api[k]).toBe('function');
  });

  test('B20 · API show/hide/full/closeFull toggle DOM correctly', async ({ page }) => {
    await page.evaluate(() => window.__pdbDevLogger.show());
    await expect(page.locator('#__pdb-dev-panel')).toBeVisible();
    await page.evaluate(() => window.__pdbDevLogger.hide());
    await expect(page.locator('#__pdb-dev-panel')).toHaveCount(0);
    await page.evaluate(() => window.__pdbDevLogger.full());
    await expect(page.locator('#__pdb-dev-full')).toBeVisible();
    await page.evaluate(() => window.__pdbDevLogger.closeFull());
    await expect(page.locator('#__pdb-dev-full')).toHaveCount(0);
  });
});
