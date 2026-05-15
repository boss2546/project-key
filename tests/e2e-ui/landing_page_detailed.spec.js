const { test, expect } = require('@playwright/test');

test.describe('Landing Page - Detailed UI & Auth Modal Tests', () => {
  
  test.beforeEach(async ({ page }) => {
    // ไปที่หน้า Landing Page
    await page.goto('http://127.0.0.1:8000/');
  });

  test('UI elements should be visible on landing page', async ({ page }) => {
    // เช็ค Header
    await expect(page.locator('.landing-header')).toBeVisible();
    await expect(page.locator('#btn-show-login')).toBeVisible();
    await expect(page.locator('#btn-show-register')).toBeVisible();

    // เช็ค Hero Section
    await expect(page.locator('.hero-title')).toContainText('Start with context');
    await expect(page.locator('#btn-hero-register')).toBeVisible();
    await expect(page.locator('#btn-hero-login')).toBeVisible();

    // เช็ค CTA Section
    await expect(page.locator('#btn-cta-register')).toBeVisible();
  });

  test('Clicking Login buttons should open Auth Modal in Login mode', async ({ page }) => {
    const loginButtons = ['#btn-show-login', '#btn-hero-login'];
    
    for (const btnId of loginButtons) {
      await page.click(btnId);
      await expect(page.locator('#auth-modal')).not.toHaveClass(/hidden/);
      await expect(page.locator('#auth-modal-title')).toHaveText('เข้าสู่ระบบ');
      await expect(page.locator('#login-form')).not.toHaveClass(/hidden/);
      await expect(page.locator('#register-form')).toHaveClass(/hidden/);
      
      // Close modal for next iteration
      await page.click('#auth-modal-close');
      await expect(page.locator('#auth-modal')).toHaveClass(/hidden/);
    }
  });

  test('Clicking Register buttons should open Auth Modal in Register mode', async ({ page }) => {
    const registerButtons = ['#btn-show-register', '#btn-hero-register', '#btn-cta-register'];
    
    for (const btnId of registerButtons) {
      await page.click(btnId);
      await expect(page.locator('#auth-modal')).not.toHaveClass(/hidden/);
      await expect(page.locator('#auth-modal-title')).toHaveText('สมัครสมาชิก');
      await expect(page.locator('#register-form')).not.toHaveClass(/hidden/);
      await expect(page.locator('#login-form')).toHaveClass(/hidden/);
      
      // Close modal for next iteration
      await page.click('#auth-modal-close');
      await expect(page.locator('#auth-modal')).toHaveClass(/hidden/);
    }
  });

  test('Modal switching between Login, Register, and Forgot Password should work', async ({ page }) => {
    await page.click('#btn-show-login');
    
    // Switch to Register
    await page.click('#switch-to-register');
    await expect(page.locator('#auth-modal-title')).toHaveText('สมัครสมาชิก');
    await expect(page.locator('#register-form')).not.toHaveClass(/hidden/);
    await expect(page.locator('#login-form')).toHaveClass(/hidden/);

    // Switch back to Login
    await page.click('#switch-to-login');
    await expect(page.locator('#auth-modal-title')).toHaveText('เข้าสู่ระบบ');
    await expect(page.locator('#login-form')).not.toHaveClass(/hidden/);
    
    // Switch to Forgot Password
    await page.click('#switch-to-forgot');
    await expect(page.locator('#auth-modal-title')).toHaveText('ลืมรหัสผ่าน');
    await expect(page.locator('#forgot-form')).not.toHaveClass(/hidden/);
    await expect(page.locator('#login-form')).toHaveClass(/hidden/);

    // Switch back to Login from Forgot Password
    await page.click('#switch-forgot-to-login');
    await expect(page.locator('#auth-modal-title')).toHaveText('เข้าสู่ระบบ');
    await expect(page.locator('#login-form')).not.toHaveClass(/hidden/);
  });

  test('Login with empty credentials should show error', async ({ page }) => {
    await page.click('#btn-show-login');
    await page.click('#btn-login');
    
    const errorEl = page.locator('#login-error');
    await expect(errorEl).not.toHaveClass(/hidden/);
    // ตรวจสอบว่ามีข้อความ Error โชว์ขึ้นมา (API น่าจะพ่น 422 Unprocessable Entity)
    await expect(errorEl).not.toBeEmpty();
  });

  test('Register with invalid password length should show error', async ({ page }) => {
    await page.click('#btn-show-register');
    
    await page.fill('#register-name', 'Test User');
    await page.fill('#register-email', 'test@example.com');
    await page.fill('#register-password', '123'); // Password too short
    
    await page.click('#btn-register');
    
    const errorEl = page.locator('#register-error');
    await expect(errorEl).not.toHaveClass(/hidden/);
    // คาดหวังข้อความ error จาก Backend
    await expect(errorEl).not.toBeEmpty();
  });

  test('Forgot password with empty email should show error', async ({ page }) => {
    await page.click('#btn-show-login');
    await page.click('#switch-to-forgot');
    
    await page.click('#btn-forgot-submit');
    
    const errorEl = page.locator('#forgot-error');
    await expect(errorEl).not.toHaveClass(/hidden/);
    await expect(errorEl).toHaveText('กรุณากรอกอีเมล');
  });

  // --- DEEP EDGE-CASE TESTS ---

  test('Input data should be cleared when modal is closed and reopened', async ({ page }) => {
    await page.click('#btn-show-login');
    await page.fill('#login-email', 'test@example.com');
    await page.click('#auth-modal-close');
    
    // Reopen
    await page.click('#btn-show-login');
    const emailValue = await page.inputValue('#login-email');
    expect(emailValue).toBe(''); // BUG-EDGE-01: It will fail here if not fixed
  });

  test('Clicking outside the modal should close it', async ({ page }) => {
    await page.click('#btn-show-login');
    await expect(page.locator('#auth-modal')).not.toHaveClass(/hidden/);
    
    // Click on the backdrop (outside the modal box)
    await page.click('.modal-overlay', { position: { x: 10, y: 10 } });
    
    await expect(page.locator('#auth-modal')).toHaveClass(/hidden/); // BUG-EDGE-02: It will fail here if not fixed
  });

  test('Forgot password error state color should not leak across attempts', async ({ page }) => {
    // 1. Submit an existing email to trigger success state (green text)
    // For this test, we simulate the backend returning a success anti-enumeration message
    await page.route('/api/auth/request-reset', async route => {
      const json = { message: "ถ้าอีเมลนี้มีบัญชีอยู่ ระบบจะส่งลิงก์รีเซ็ตให้" };
      await route.fulfill({ status: 200, json });
    });
    
    await page.click('#btn-show-login');
    await page.click('#switch-to-forgot');
    await page.fill('#forgot-email', 'test@example.com');
    await page.click('#btn-forgot-submit');
    
    const errorEl = page.locator('#forgot-error');
    await expect(errorEl).toHaveCSS('color', 'rgb(16, 185, 129)'); // emerald-500 (green)

    // 2. Clear email and submit to trigger empty error
    await page.fill('#forgot-email', '');
    await page.click('#btn-forgot-submit');
    
    await expect(errorEl).toHaveText('กรุณากรอกอีเมล');
    // The color should revert to normal error color (red), not stay green!
    await expect(errorEl).not.toHaveCSS('color', 'rgb(16, 185, 129)'); 
  });

  test('Login should have loading state and disable button to prevent double-click', async ({ page }) => {
    // Intercept API to delay response by 1 second
    await page.route('/api/auth/login', async route => {
      await new Promise(resolve => setTimeout(resolve, 1000));
      await route.fulfill({ status: 401, json: { detail: 'Unauthorized' } });
    });

    await page.click('#btn-show-login');
    await page.fill('#login-email', 'test@example.com');
    await page.fill('#login-password', 'password');
    
    // Click login
    await page.click('#btn-login');
    
    // Check if button is disabled while loading
    const btn = page.locator('#btn-login');
    await expect(btn).toBeDisabled(); // UX-01: Will fail if button is not disabled
  });
});
