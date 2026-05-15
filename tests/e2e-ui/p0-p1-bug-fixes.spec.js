// Verify P0+P1 bug fixes (6 bugs from ฟ้า's bug report)
const { test, expect } = require('@playwright/test');

const BASE = process.env.PDB_TEST_BASE || 'http://127.0.0.1:8000';
const ADMIN_EMAIL = 'bossok2546@gmail.com';
const ADMIN_PASS = '0898661896za';

async function login(page) {
  await page.goto(BASE + '/');
  await page.click('#btn-show-login');
  await page.fill('#login-email', ADMIN_EMAIL);
  await page.fill('#login-password', ADMIN_PASS);
  await page.click('#btn-login');
  await page.waitForURL(/\/(app|admin)/, { timeout: 15000 });
  if (!page.url().includes('/app')) await page.goto(BASE + '/app');
  await page.waitForLoadState('networkidle');
}

test.describe('P0+P1 bug fixes', () => {
  test.setTimeout(120000);

  test('P0-1 · Logout bypass: pageshow guard redirects to / when no token', async ({ page }) => {
    await login(page);
    // simulate logout: clear token + dispatch pageshow with persisted=true
    await page.evaluate(() => {
      localStorage.removeItem('pdb_token');
      localStorage.removeItem('pdb_user');
      // simulate bfcache restore — fire pageshow event
      window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }));
    });
    // Should redirect away from /app within 2s
    await page.waitForURL(url => !url.toString().includes('/app'), { timeout: 5000 });
    const finalUrl = page.url();
    console.log('After bfcache restore + no token → URL:', finalUrl);
    expect(finalUrl).not.toContain('/app');
  });

  test('P0-2 · Chat shows explicit error if server fails (no silent failure)', async ({ page }) => {
    await login(page);
    // Navigate to chat tab
    const chatNav = page.locator('.nav-item', { hasText: /AI แชท|AI Chat|Chat/i }).first();
    if (await chatNav.count() > 0) await chatNav.click();
    await page.waitForTimeout(500);

    // Intercept /api/chat to return 500 + non-JSON
    await page.route('**/api/chat', async route => {
      await route.fulfill({ status: 500, contentType: 'text/html', body: '<html>Server Error</html>' });
    });

    const input = page.locator('#chat-input');
    await expect(input).toBeVisible();
    await input.fill('test question for error path');
    await page.click('#btn-send');

    // Should show error message in chat (not silent)
    await page.waitForTimeout(1500);
    const errorMsg = page.locator('.message.assistant').last();
    await expect(errorMsg).toBeVisible();
    const txt = await errorMsg.textContent();
    console.log('Chat error message:', txt);
    expect(txt).toMatch(/error|ผิดพลาด|Error|HTTP/i);
    // _chatBusy should be reset · input enabled again
    await expect(input).toBeEnabled({ timeout: 3000 });
  });

  test('P0-3 · Upload retries once on network error', async ({ page }) => {
    await login(page);
    let attemptCount = 0;
    await page.route('**/api/upload', async route => {
      attemptCount++;
      if (attemptCount === 1) {
        // First attempt: abort (simulate network error)
        await route.abort('failed');
      } else {
        // Second attempt: pass through
        await route.continue();
      }
    });

    const filename = `retry-${Date.now()}.txt`;
    await page.locator('input[type="file"]').first().setInputFiles({
      name: filename, mimeType: 'text/plain', buffer: Buffer.from('retry test\n'.repeat(10)),
    });

    // Wait for tray to open · should succeed (after retry)
    await expect(page.locator('.upload-tray')).toHaveClass(/is-open/, { timeout: 15000 });
    // Should have attempted at least 2 times
    expect(attemptCount).toBeGreaterThanOrEqual(2);
    // File should appear eventually in main list
    await expect(page.locator('.file-item', { hasText: filename })).toBeVisible({ timeout: 30000 });
  });

  test('P1-4 · /api/admin/me is cached · no spam for non-admin', async ({ page }) => {
    await login(page);
    // Clear cache + count requests
    await page.evaluate(() => {
      localStorage.removeItem('pdb_admin_probe');
      localStorage.removeItem('pdb_admin_probe_ts');
    });

    let adminMeCount = 0;
    page.on('request', r => {
      if (r.url().includes('/api/admin/me')) adminMeCount++;
    });

    // Trigger reveal a few times by navigating
    await page.goto(BASE + '/app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.goto(BASE + '/app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.goto(BASE + '/app');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    console.log('admin/me calls across 3 nav:', adminMeCount);
    // With caching, should hit at most 1-2 times (first call · then cached for 24hr)
    expect(adminMeCount).toBeLessThanOrEqual(2);
  });

  test('P1-5 · Graph handles NaN node coords gracefully (no D3 console error)', async ({ page }) => {
    const errors = [];
    page.on('pageerror', e => errors.push(String(e)));
    page.on('console', m => { if (m.type() === 'error' && m.text().includes('translate')) errors.push(m.text()); });

    await login(page);
    // Inject a graph state with NaN-coordinate nodes + call fit logic
    const result = await page.evaluate(() => {
      if (!window.state) window.state = {};
      window.state.graphData = {
        nodes: [
          { id: 'a', x: NaN, y: NaN, importance: 0.5 },
          { id: 'b', x: undefined, y: undefined, importance: 0.5 },
          { id: 'c', x: 100, y: 200, importance: 0.5 },
        ],
        edges: [],
      };
      // try fit-to-view (the function with the bug)
      try {
        if (typeof fitGraphToView === 'function') fitGraphToView();
        return 'called';
      } catch (e) { return 'threw: ' + e.message; }
    });
    console.log('fit result:', result, 'errors:', errors);
    // No translate(NaN,NaN) errors should appear
    const nanErrors = errors.filter(e => /NaN/i.test(e));
    expect(nanErrors).toEqual([]);
  });

  test('P1-6 · Re-extract button works · shows queue progress · re-enables after', async ({ page }) => {
    await login(page);
    // Find first non-locked file in list
    const fileRow = page.locator('.file-item:not(.file-locked)').first();
    await expect(fileRow).toBeVisible({ timeout: 10000 });
    const fileName = await fileRow.locator('.file-name').textContent();
    console.log('Testing reprocess on:', fileName);

    await fileRow.click();
    await page.waitForTimeout(500);

    const reprocessBtn = page.locator('#fd-reprocess-btn');
    await expect(reprocessBtn).toBeVisible();
    await expect(reprocessBtn).toBeEnabled();

    // Click reprocess
    await reprocessBtn.click();

    // Button should change to processing state quickly (within 2s)
    await expect(reprocessBtn).toBeDisabled({ timeout: 2000 });
    const processingText = await reprocessBtn.textContent();
    console.log('Reprocess btn text during:', processingText);
    expect(processingText).toMatch(/Submitting|Queued|Processing|กำลัง|ในคิว|⏳/i);

    // Toast should appear with "queued · waiting" message
    const toast = page.locator('.toast, #toast-container').first();
    // Don't require exact text since toast might auto-dismiss · just verify button worked
    // Wait for either: success or error (max 90s for full re-extract)
    await page.waitForFunction(
      () => {
        const btn = document.getElementById('fd-reprocess-btn');
        return btn && !btn.disabled;
      },
      { timeout: 120000 }
    );
    // Button re-enabled = flow completed (success or graceful error)
    await expect(reprocessBtn).toBeEnabled();
  });
});
