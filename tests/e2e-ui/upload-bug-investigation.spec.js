// Deeper investigation — capture screenshots + DOM state at every step
const { test, expect } = require('@playwright/test');

const BASE = process.env.PDB_TEST_BASE || 'http://127.0.0.1:8000';
const ADMIN_EMAIL = 'bossok2546@gmail.com';
const ADMIN_PASS = '0898661896za';

test.describe('Upload bug investigation — capture exact UI state', () => {
  test.setTimeout(180000);

  test('I1 · upload + capture state after each step', async ({ page }) => {
    page.on('console', m => console.log(`[browser ${m.type()}]`, m.text()));
    // Capture all 4xx/5xx responses
    page.on('response', r => {
      if (r.status() >= 400) console.log(`[404/5xx] ${r.status()} ${r.request().method()} ${r.url()}`);
    });

    // Login
    await page.goto(BASE + '/');
    await page.click('#btn-show-login');
    await page.fill('#login-email', ADMIN_EMAIL);
    await page.fill('#login-password', ADMIN_PASS);
    await page.click('#btn-login');
    await page.waitForURL(/\/(app|admin)/);
    if (!page.url().includes('/app')) await page.goto(BASE + '/app');
    await page.waitForLoadState('networkidle');

    console.log('\n=== STEP 1: Pre-upload state ===');
    console.log('URL:', page.url());
    const beforeCount = await page.locator('.file-item').count();
    console.log('Files visible:', beforeCount);
    const badge = page.locator('#unprocessed-badge');
    const badgeText = await badge.textContent();
    const badgeStyle = await badge.getAttribute('style');
    console.log('Unprocessed badge:', badgeText, 'style:', badgeStyle);

    // Upload
    const filename = `investig-${Date.now()}.txt`;
    const content = 'Investigation upload\n' + 'lorem.\n'.repeat(30);
    await page.locator('input[type="file"]').first().setInputFiles({
      name: filename, mimeType: 'text/plain', buffer: Buffer.from(content),
    });

    console.log('\n=== STEP 2: Right after setInputFiles ===');
    // Wait a moment for upload to start
    await page.waitForTimeout(500);
    const overlayVisible = await page.locator('.loading-overlay, #loading-overlay').isVisible().catch(() => false);
    console.log('Loading overlay visible:', overlayVisible);

    console.log('\n=== STEP 3: Wait for tray to appear ===');
    const tray = page.locator('.upload-tray');
    await expect(tray).toHaveClass(/is-open/, { timeout: 10000 });
    console.log('Tray opened');
    const trayItems = await page.locator('.upload-tray-item').count();
    console.log('Tray items:', trayItems);

    console.log('\n=== STEP 4: Wait for success banner ===');
    await expect(page.locator('.upload-tray-banner.is-success')).toBeVisible({ timeout: 30000 });
    const bannerText = await page.locator('.upload-tray-banner.is-success').textContent();
    console.log('Banner text:', bannerText);

    console.log('\n=== STEP 5: Tray auto-close ===');
    const closeStart = Date.now();
    await expect(tray).not.toHaveClass(/is-open/, { timeout: 5000 });
    console.log('Tray closed after', Date.now() - closeStart, 'ms (from banner appear)');

    console.log('\n=== STEP 6: File in main list? ===');
    const fileRow = page.locator('.file-item', { hasText: filename });
    await expect(fileRow).toBeVisible({ timeout: 5000 });
    const dotClass = await fileRow.locator('.status-dot').getAttribute('class');
    console.log('Status dot class:', dotClass);

    console.log('\n=== STEP 7: Click file to open detail panel ===');
    await fileRow.click();
    await page.waitForTimeout(800);
    const detailPanel = page.locator('#file-detail-panel');
    const detailVisible = await detailPanel.isVisible().catch(() => false);
    console.log('Detail panel visible:', detailVisible);
    if (detailVisible) {
      const detailText = await detailPanel.textContent();
      console.log('Detail panel text (first 500ch):', detailText.slice(0, 500));
    }

    console.log('\n=== STEP 8: Unprocessed badge update? ===');
    const newBadge = await badge.textContent();
    const newBadgeStyle = await badge.getAttribute('style');
    console.log('Unprocessed badge:', newBadge, 'style:', newBadgeStyle);

    console.log('\n=== STEP 9: After 10s wait — any change? ===');
    await page.waitForTimeout(10000);
    const finalDot = await fileRow.locator('.status-dot').getAttribute('class').catch(() => '?');
    console.log('Status dot after 10s:', finalDot);

    // Always pass — this is investigative
    expect(true).toBe(true);
  });
});
