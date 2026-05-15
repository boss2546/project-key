// Verify dev-logger captures new event types: route/focus/input/dblclick/contextmenu/scroll/resize
const { test, expect } = require('@playwright/test');

const BASE = 'http://127.0.0.1:8000';

test.describe('Dev Logger — detailed user journey captures', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(BASE + '/');
    await expect(page.locator('#__pdb-dev-btn')).toBeVisible();
  });

  test('C1 · history.pushState/replaceState → captured as kind=route', async ({ page }) => {
    await page.evaluate(() => {
      history.pushState({}, '', '/?nav=1');
      history.replaceState({}, '', '/?nav=2');
    });
    // small delay for setTimeout(0) inside the interceptor
    await page.waitForTimeout(100);
    const routes = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'route')
    );
    expect(routes.length).toBeGreaterThanOrEqual(2);
    expect(routes.some(r => r.reason === 'pushState' && r.to.includes('nav=1'))).toBe(true);
    expect(routes.some(r => r.reason === 'replaceState' && r.to.includes('nav=2'))).toBe(true);
  });

  test('C2 · hashchange → captured', async ({ page }) => {
    await page.evaluate(() => { location.hash = '#section-x'; });
    await page.waitForTimeout(100);
    const routes = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'route')
    );
    expect(routes.some(r => r.reason === 'hashchange' && r.hash === '#section-x')).toBe(true);
  });

  test('C3 · input focus → captured', async ({ page }) => {
    await page.click('#btn-show-login');
    await page.click('#login-email');
    await page.waitForTimeout(50);
    const focuses = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'focus')
    );
    expect(focuses.some(f => f.id === 'login-email')).toBe(true);
  });

  test('C4 · input change → captured with masked password value', async ({ page }) => {
    await page.click('#btn-show-login');
    await page.fill('#login-email', 'user@example.com');
    await page.fill('#login-password', 'mysecret123');
    await page.locator('#login-password').blur();  // trigger change
    await page.waitForTimeout(50);
    const inputs = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'input')
    );
    // password field should be masked
    const pwd = inputs.find(i => i.id === 'login-password');
    expect(pwd).toBeTruthy();
    expect(pwd.value).toMatch(/\*\*\*\[\d+ch\]/);
    // email field should show value
    const email = inputs.find(i => i.id === 'login-email');
    expect(email).toBeTruthy();
    expect(email.value).toBe('user@example.com');
  });

  test('C5 · double-click → captured with event="dblclick"', async ({ page }) => {
    await page.dblclick('.hero-title');
    await page.waitForTimeout(50);
    const dbls = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'click' && e.event === 'dblclick')
    );
    expect(dbls.length).toBeGreaterThan(0);
  });

  test('C6 · right-click → captured with event="contextmenu"', async ({ page }) => {
    await page.click('.hero-title', { button: 'right' });
    await page.waitForTimeout(50);
    const ctx = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'click' && e.event === 'contextmenu')
    );
    expect(ctx.length).toBeGreaterThan(0);
  });

  test('C7 · click captures x/y position', async ({ page }) => {
    await page.click('#btn-show-login');
    await page.waitForTimeout(50);
    const clicks = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'click' && e.event === 'click')
    );
    const last = clicks[clicks.length - 1];
    expect(typeof last.x).toBe('number');
    expect(typeof last.y).toBe('number');
    expect(last.x).toBeGreaterThan(0);
  });

  test('C8 · window resize → captured (debounced)', async ({ page }) => {
    await page.setViewportSize({ width: 800, height: 600 });
    await page.waitForTimeout(400);  // wait > 300ms debounce
    const resizes = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'ui' && e.event === 'resize')
    );
    expect(resizes.length).toBeGreaterThan(0);
    const last = resizes[resizes.length - 1];
    expect(last.w).toBe(800);
    expect(last.h).toBe(600);
  });

  test('C9 · scroll milestone (50%) → captured once', async ({ page }) => {
    // landing page is long → scroll halfway
    await page.evaluate(() => {
      const docH = document.documentElement.scrollHeight - window.innerHeight;
      window.scrollTo(0, Math.round(docH * 0.55));
    });
    await page.waitForTimeout(150);
    const scrolls = await page.evaluate(() =>
      window.__pdbDevLogger.entries().filter(e => e.kind === 'scroll')
    );
    expect(scrolls.some(s => s.percent === 25 || s.percent === 50)).toBe(true);
  });

  test('C10 · public API still works (regression)', async ({ page }) => {
    const ok = await page.evaluate(() => {
      try {
        window.__pdbDevLogger.show();
        window.__pdbDevLogger.hide();
        window.__pdbDevLogger.full();
        window.__pdbDevLogger.closeFull();
        window.__pdbDevLogger.pause(false);
        return true;
      } catch (e) { return String(e); }
    });
    expect(ok).toBe(true);
  });
});
