// Verify v10.0.x upload UX improvements:
//  - Banner shows context-aware text + "จัดระเบียบทันที" CTA button
//  - Pulse animation on #btn-organize-new after upload
//  - File detail panel shows filename immediately (no "Loading..." for summary 404)
//  - Detail 404 message points to "จัดระเบียบไฟล์ใหม่"
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
  await page.waitForURL(/\/(app|admin)/);
  if (!page.url().includes('/app')) await page.goto(BASE + '/app');
  await page.waitForLoadState('networkidle');
}

test.describe('Upload UX improvements v10.0.x', () => {
  test.setTimeout(120000);

  test('X1 · banner shows new text + CTA button after upload', async ({ page }) => {
    await login(page);

    const filename = `ux-banner-${Date.now()}.txt`;
    await page.locator('input[type="file"]').first().setInputFiles({
      name: filename, mimeType: 'text/plain',
      buffer: Buffer.from('test content for banner ' + 'lorem\n'.repeat(20)),
    });

    // Wait for banner
    const banner = page.locator('.upload-tray-banner.is-success');
    await expect(banner).toBeVisible({ timeout: 30000 });

    // New banner text mentions "AI" or "วิเคราะห์" or "Next"
    const bannerText = await banner.textContent();
    expect(bannerText).toMatch(/AI|วิเคราะห์|Next|analyze/i);

    // CTA button exists
    const cta = banner.locator('button[data-action="organize-now"]');
    await expect(cta).toBeVisible();
    const ctaText = await cta.textContent();
    expect(ctaText).toMatch(/จัดระเบียบ|Organize/i);
  });

  test('X2 · #btn-organize-new has pulse-attention class after upload', async ({ page }) => {
    await login(page);

    const filename = `ux-pulse-${Date.now()}.txt`;
    await page.locator('input[type="file"]').first().setInputFiles({
      name: filename, mimeType: 'text/plain',
      buffer: Buffer.from('pulse test\n'.repeat(15)),
    });

    // Wait for banner (means upload is done)
    await expect(page.locator('.upload-tray-banner.is-success')).toBeVisible({ timeout: 30000 });

    // Organize button should have pulse-attention class
    const orgBtn = page.locator('#btn-organize-new');
    await expect(orgBtn).toHaveClass(/pulse-attention/, { timeout: 2000 });
  });

  test('X3 · clicking CTA in banner triggers organize-new', async ({ page }) => {
    await login(page);

    let organizeCalled = false;
    page.on('request', r => {
      if (r.url().includes('/api/organize-new') && r.method() === 'POST') {
        organizeCalled = true;
      }
    });

    const filename = `ux-cta-${Date.now()}.txt`;
    await page.locator('input[type="file"]').first().setInputFiles({
      name: filename, mimeType: 'text/plain',
      buffer: Buffer.from('cta test\n'.repeat(15)),
    });

    // Wait for banner CTA
    const cta = page.locator('.upload-tray-banner.is-success button[data-action="organize-now"]');
    await expect(cta).toBeVisible({ timeout: 30000 });

    // Click it
    await cta.click();

    // Tray should close
    await expect(page.locator('.upload-tray')).not.toHaveClass(/is-open/, { timeout: 3000 });

    // organize-new request should have fired
    await page.waitForTimeout(1000);
    expect(organizeCalled).toBe(true);
  });

  test('X4 · file detail panel after upload: filename shows immediately (NOT "Loading..." for 404)', async ({ page }) => {
    await login(page);

    const filename = `ux-detail-${Date.now()}.txt`;
    await page.locator('input[type="file"]').first().setInputFiles({
      name: filename, mimeType: 'text/plain',
      buffer: Buffer.from('detail test\n'.repeat(15)),
    });

    // Wait for tray to close (upload done)
    await expect(page.locator('.upload-tray')).not.toHaveClass(/is-open/, { timeout: 30000 });

    // Click the new file
    const fileRow = page.locator('.file-item', { hasText: filename });
    await expect(fileRow).toBeVisible({ timeout: 5000 });
    await fileRow.click();

    // Detail panel should show filename IMMEDIATELY (within 500ms · before any fetch)
    // Old behavior: shows "Loading..." for ~500ms while fetching
    const fdName = page.locator('#fd-filename');
    await expect(fdName).toBeVisible();
    // wait briefly and check — should NOT be "Loading..."
    await page.waitForTimeout(150);
    const nameNow = await fdName.textContent();
    console.log('Detail filename immediately:', nameNow);
    expect(nameNow).not.toBe('Loading...');
    expect(nameNow).toContain(filename.split('.')[0]);

    // Summary should show 404 message that points to "จัดระเบียบไฟล์ใหม่"
    await page.waitForTimeout(1500);  // wait for fetch to complete
    const summaryText = await page.locator('#fd-summary').textContent();
    console.log('Summary text:', summaryText);
    expect(summaryText).toMatch(/จัดระเบียบไฟล์ใหม่|Organize new files/i);
  });

  test('X5 · status dot CSS exists for all statuses', async ({ page }) => {
    await login(page);

    // Check CSS rules exist for new statuses
    const colors = await page.evaluate(() => {
      const statuses = ['queued', 'extracting', 'uploaded', 'processing', 'organized', 'ready', 'error'];
      const result = {};
      for (const s of statuses) {
        const el = document.createElement('span');
        el.className = `status-dot ${s}`;
        document.body.appendChild(el);
        const bg = getComputedStyle(el).backgroundColor;
        result[s] = bg;
        el.remove();
      }
      return result;
    });
    console.log('status-dot bg colors:', colors);
    // None should be rgba(0,0,0,0) or transparent (i.e. all should have visible background)
    for (const [status, color] of Object.entries(colors)) {
      expect(color, `${status} dot should have color`).not.toBe('rgba(0, 0, 0, 0)');
      expect(color, `${status} dot should have color`).not.toBe('transparent');
    }
  });
});
