// Replicate user's complaint: "พออัพโหลดเสร็จแล้ว ไฟล์มันค้าง 'ว่าจะขึ้นโชใน UI ว่าอัพโหลดเสร็จแล้ว'"
// = After upload finishes, tray stuck showing "upload completed"
const { test, expect } = require('@playwright/test');

const BASE = process.env.PDB_TEST_BASE || 'http://127.0.0.1:8000';
const ADMIN_EMAIL = 'bossok2546@gmail.com';
const ADMIN_PASS = '0898661896za';

test.describe('Upload tray flow — full UI replication', () => {
  test.setTimeout(120000);

  async function login(page) {
    await page.goto(BASE + '/');
    await page.click('#btn-show-login');
    await page.fill('#login-email', ADMIN_EMAIL);
    await page.fill('#login-password', ADMIN_PASS);
    await page.click('#btn-login');
    // admin redirects to /admin · go to /app explicitly
    await page.waitForURL(/\/(app|admin)/, { timeout: 15000 });
    if (!page.url().includes('/app')) await page.goto(BASE + '/app');
    await page.waitForLoadState('networkidle');
    // make sure My Data tab is active
    const myDataNav = page.locator('.nav-item').filter({ hasText: /ข้อมูลของฉัน|My Data/i }).first();
    if (await myDataNav.count() > 0) await myDataNav.click();
    await page.waitForTimeout(500);
  }

  test('U1 · upload via UI · tray opens · shows "อัปโหลดเสร็จ" · auto-closes within 7s', async ({ page }) => {
    const consoleErrors = [];
    page.on('pageerror', e => consoleErrors.push(String(e)));
    page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });

    await login(page);

    // Find file input (hidden inside dropzone)
    const input = page.locator('input[type="file"]').first();
    await expect(input).toBeAttached();

    // Upload a small file
    const content = `Upload tray test ${Date.now()}\n` + 'lorem ipsum.\n'.repeat(10);
    const filename = `tray-test-${Date.now()}.txt`;
    await input.setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(content) });

    // Tray should appear (open)
    const tray = page.locator('.upload-tray');
    await expect(tray).toHaveClass(/is-open/, { timeout: 5000 });

    // File row should appear in tray
    await expect(page.locator(`.upload-tray-list .upload-tray-item`)).toBeVisible({ timeout: 5000 });

    // Wait for the success banner "อัปโหลดเสร็จ"
    const banner = page.locator('.upload-tray-banner.is-success');
    await expect(banner).toBeVisible({ timeout: 30000 });
    const bannerText = await banner.textContent();
    console.log('Banner text:', bannerText);

    // CRITICAL — verify auto-close within 7s of banner appearing
    // v10.0.x: banner shows + setTimeout 5s + buffer 2s (เดิม 2s · เพิ่มให้ user เห็น/กด CTA)
    await expect(tray).not.toHaveClass(/is-open/, { timeout: 8000 });

    // File should be in main file list now
    const fileItem = page.locator('.file-item', { hasText: filename });
    await expect(fileItem).toBeVisible({ timeout: 5000 });

    // No upload-related console errors (filter admin.js init NETWORK_ERROR · unrelated)
    const uploadErrors = consoleErrors.filter(e => !/admin\.js|admin init/i.test(e));
    expect(uploadErrors).toEqual([]);
  });

  test('U3 · upload 3 files at once · all should appear · tray auto-closes once all done', async ({ page }) => {
    await login(page);
    const input = page.locator('input[type="file"]').first();
    const ts = Date.now();
    const files = [
      { name: `multi-${ts}-1.txt`, mimeType: 'text/plain', buffer: Buffer.from('content 1\n'.repeat(20)) },
      { name: `multi-${ts}-2.txt`, mimeType: 'text/plain', buffer: Buffer.from('content 2\n'.repeat(20)) },
      { name: `multi-${ts}-3.txt`, mimeType: 'text/plain', buffer: Buffer.from('content 3\n'.repeat(20)) },
    ];
    await input.setInputFiles(files);

    const tray = page.locator('.upload-tray');
    await expect(tray).toHaveClass(/is-open/, { timeout: 5000 });

    // Wait for success banner
    await expect(page.locator('.upload-tray-banner.is-success')).toBeVisible({ timeout: 60000 });

    // Tray should auto-close within 8s (v10.0.x extended timer 2s → 5s + buffer)
    await expect(tray).not.toHaveClass(/is-open/, { timeout: 8000 });

    // All 3 files in main list
    for (const f of files) {
      await expect(page.locator('.file-item', { hasText: f.name })).toBeVisible({ timeout: 5000 });
    }
  });

  test('U4 · upload then click "จัดระเบียบไฟล์ใหม่" · overlay shows phase + file reaches ready', async ({ page }) => {
    await login(page);
    const input = page.locator('input[type="file"]').first();
    const filename = `org-after-${Date.now()}.txt`;
    const content = 'This is content for organize test ' + '\n' + 'lorem ipsum dolor.\n'.repeat(40);
    await input.setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(content) });

    // Wait for upload tray to close (file = 'uploaded')
    await expect(page.locator('.upload-tray')).not.toHaveClass(/is-open/, { timeout: 30000 });

    // Click "จัดระเบียบไฟล์ใหม่" button
    const orgBtn = page.locator('#btn-organize-new');
    await expect(orgBtn).toBeEnabled({ timeout: 5000 });
    await orgBtn.click();

    // Overlay should appear with loading state
    await expect(page.locator('.loading-overlay, #loading-overlay')).toBeVisible({ timeout: 3000 });

    // Wait until organize completes (overlay hides) — give 60s for LLM
    await expect(page.locator('.loading-overlay, #loading-overlay')).not.toBeVisible({ timeout: 90000 });

    // File should now be in 'ready' status (organized + summarized)
    const fileRow = page.locator('.file-item', { hasText: filename });
    await expect(fileRow).toBeVisible();
    const dotClass = await fileRow.locator('.status-dot').getAttribute('class');
    console.log('After organize · status dot:', dotClass);
    // expect ready (post-summary) or organized (no summary needed)
    expect(dotClass).toMatch(/(ready|organized|uploaded)/);
    expect(dotClass).not.toMatch(/processing/);
  });

  test('U2 · upload + immediate organize · file should reach "ready" state · no permanent stuck', async ({ page }) => {
    await login(page);
    const input = page.locator('input[type="file"]').first();
    const content = `organize test ${Date.now()}\n` + 'this is the test file content\n'.repeat(20);
    const filename = `org-test-${Date.now()}.txt`;
    await input.setInputFiles({ name: filename, mimeType: 'text/plain', buffer: Buffer.from(content) });

    // Wait for tray to close (upload done)
    const tray = page.locator('.upload-tray');
    await expect(tray).not.toHaveClass(/is-open/, { timeout: 30000 });

    // File should appear in list with status (not "processing")
    const fileRow = page.locator('.file-item', { hasText: filename });
    await expect(fileRow).toBeVisible({ timeout: 10000 });

    // Get the file ID from data attribute
    const fileId = await fileRow.getAttribute('data-id');
    expect(fileId).toBeTruthy();
    console.log('Uploaded file id:', fileId);

    // Check status dot class — should be 'uploaded' or 'ready' (NOT 'processing'/'extracting'/'queued')
    const statusDot = fileRow.locator('.status-dot');
    const dotClass = await statusDot.getAttribute('class');
    console.log('Status dot class:', dotClass);
    expect(dotClass).toMatch(/(uploaded|ready|organized)/);
    expect(dotClass).not.toMatch(/(queued|extracting|processing|error)/);
  });
});
