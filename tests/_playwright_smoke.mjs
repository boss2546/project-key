import { chromium } from 'playwright';
import { mkdirSync } from 'node:fs';
import { join } from 'node:path';

const OUT = 'd:/PDB/tests/_smoke_shots';
mkdirSync(OUT, { recursive: true });

const log = (m) => console.log(`[${new Date().toISOString().slice(11, 19)}] ${m}`);

const browser = await chromium.launch({ headless: false, slowMo: 400 });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 } });
const page = await ctx.newPage();

page.on('console', (msg) => log(`browser-console[${msg.type()}]: ${msg.text().slice(0, 200)}`));
page.on('pageerror', (e) => log(`browser-error: ${e.message}`));

try {
  log('1. Navigate to https://personaldatabank.fly.dev/');
  const resp = await page.goto('https://personaldatabank.fly.dev/', { waitUntil: 'networkidle', timeout: 20000 });
  log(`   → HTTP ${resp.status()} · title="${await page.title()}"`);
  await page.screenshot({ path: join(OUT, '01-prod-landing.png'), fullPage: true });
  log('   → screenshot saved: 01-prod-landing.png');

  // Inspect what's on the landing page
  const buttons = await page.locator('button, a.btn, a[role="button"]').all();
  log(`   → found ${buttons.length} clickable button-ish elements`);
  for (let i = 0; i < Math.min(buttons.length, 8); i++) {
    const txt = (await buttons[i].textContent())?.trim().replace(/\s+/g, ' ').slice(0, 60) || '(no text)';
    log(`     [${i}] "${txt}"`);
  }

  log('2. Try clicking the first visible primary CTA');
  const cta = page.locator('button, a.btn, a[role="button"]').filter({ hasText: /เริ่ม|Login|Sign|เข้าสู่|สมัคร|ลอง|Get|Start/i }).first();
  if (await cta.count() > 0) {
    const ctaTxt = (await cta.textContent())?.trim().slice(0, 40);
    log(`   → clicking: "${ctaTxt}"`);
    await cta.click({ trial: false });
    await page.waitForTimeout(1500);
    log(`   → after click: url=${page.url()} · title="${await page.title()}"`);
    await page.screenshot({ path: join(OUT, '02-after-cta-click.png'), fullPage: true });
    log('   → screenshot saved: 02-after-cta-click.png');
  } else {
    log('   → no obvious CTA matched — clicking first visible button instead');
    if (buttons.length > 0) {
      await buttons[0].click().catch((e) => log(`   click failed: ${e.message}`));
      await page.waitForTimeout(1500);
      await page.screenshot({ path: join(OUT, '02-after-fallback-click.png'), fullPage: true });
    }
  }

  log('3. Navigate somewhere fun: https://example.com');
  await page.goto('https://example.com', { waitUntil: 'load' });
  log(`   → title="${await page.title()}"`);
  await page.screenshot({ path: join(OUT, '03-example-com.png') });

  log('4. Click the "More information..." link on example.com');
  const more = page.locator('a').filter({ hasText: /More information/i }).first();
  if (await more.count() > 0) {
    await Promise.all([
      page.waitForLoadState('domcontentloaded'),
      more.click(),
    ]);
    log(`   → navigated to: ${page.url()}`);
    await page.screenshot({ path: join(OUT, '04-after-more-info.png') });
  }

  log('Done. Closing browser in 3s...');
  await page.waitForTimeout(3000);
} catch (e) {
  log(`FATAL: ${e.message}`);
  await page.screenshot({ path: join(OUT, '99-error.png') }).catch(() => {});
  process.exitCode = 1;
} finally {
  await browser.close();
  log('Browser closed.');
}
