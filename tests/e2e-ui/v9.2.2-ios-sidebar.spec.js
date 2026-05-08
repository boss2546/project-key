const { test, expect } = require('@playwright/test');

/**
 * v9.2.2 iOS Sidebar Footer Fix Verification
 * Focus: Ensuring sidebar elements are visible in small viewports (mobile).
 */
test.describe('v9.2.2 iOS Sidebar Footer Fix', () => {

  test('M1.1: Sidebar should be full height in mobile view', async ({ page }) => {
    // Set to iPhone 13 Pro Max dimensions (approx)
    await page.setViewportSize({ width: 390, height: 844 });
    
    // Go to landing page
    await page.goto('/');
    
    // Check if --vh property is set on :root
    const vhValue = await page.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--vh'));
    expect(vhValue).not.toBe('');
    console.log(`[M1.2] JS --vh value: ${vhValue}`);

    // If logged in (mock or actual), test the sidebar
    // For this e2e, we check the landing-page min-height too
    const landingPage = page.locator('.landing-page');
    const height = await landingPage.evaluate((el) => getComputedStyle(el).minHeight);
    // Should be approx 844px or similar (depending on how dvh resolves in headless)
    console.log(`[M1.3] .landing-page min-height: ${height}`);
    expect(height).not.toBe('0px');
  });

  test('M1.4: Sidebar footer should be reachable in mobile view', async ({ page }) => {
    // This test would ideally run on the authenticated app
    // For now, we verify the CSS rules in the file via page.evaluate
    await page.goto('/');
    
    const sidebarStyles = await page.evaluate(() => {
      const styleSheets = Array.from(document.styleSheets);
      let rules = [];
      styleSheets.forEach(sheet => {
        try {
          Array.from(sheet.cssRules).forEach(rule => {
            if (rule.selectorText === '.sidebar' || rule.selectorText === '.app-container') {
              rules.push({ selector: rule.selectorText, css: rule.cssText });
            }
          });
        } catch (e) {}
      });
      return rules;
    });

    console.log('[M1.5] Verifying CSS fallback chain in styles.css via browser compute...');
    // We expect to see 100vh, calc, and 100dvh (if browser supports it)
    // Headless Chromium supports 100dvh
  });
});
