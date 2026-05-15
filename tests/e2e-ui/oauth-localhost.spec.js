const { test, expect } = require('@playwright/test');

test.describe('Google OAuth Localhost Verification', () => {

  // T-OAUTH-1: Auth init returns Google URL ที่มี localhost redirect
  test('T-OAUTH-1: auth init returns google URL with localhost callback', async ({ request }) => {
    const r = await request.get('http://127.0.0.1:8000/api/auth/google/init');
    expect(r.status()).toBe(200);
    const body = await r.json();
    expect(body.auth_url).toContain('accounts.google.com');
    const url = new URL(body.auth_url);
    const redirect = url.searchParams.get('redirect_uri');
    console.log('Detected redirect_uri:', redirect);
    expect(redirect).toMatch(/127\.0\.0\.1:8000|localhost:8000/);
    expect(redirect).toContain('/api/auth/google/callback');
  });

  // T-OAUTH-2: Skip for manual verification
  test.skip('T-OAUTH-2: Full Google login flow (Manual Smoke Test required)', async () => {
    // Google blocks automated logins
  });

  // T-OAUTH-3: Callback rejects invalid state CSRF token
  test('T-OAUTH-3: callback rejects forged state', async ({ request }) => {
    const r = await request.get(
      'http://127.0.0.1:8000/api/auth/google/callback?code=fake&state=invalid',
      { maxRedirects: 0 }
    );
    expect(r.status()).toBe(302);
    const location = r.headers()['location'];
    expect(location).toContain('google_error=invalid_state');
  });

  // T-OAUTH-4: Missing params handled gracefully
  test('T-OAUTH-4: callback redirects with error on missing params', async ({ request }) => {
    const r = await request.get(
      'http://127.0.0.1:8000/api/auth/google/callback',
      { maxRedirects: 0 }
    );
    expect(r.status()).toBe(302);
    expect(r.headers()['location']).toContain('google_error=missing_params');
  });

  // T-OAUTH-5: User-cancelled flow (Google sent ?error=)
  test('T-OAUTH-5: callback handles user cancelling consent', async ({ request }) => {
    const r = await request.get(
      'http://127.0.0.1:8000/api/auth/google/callback?error=access_denied',
      { maxRedirects: 0 }
    );
    expect(r.status()).toBe(302);
    expect(r.headers()['location']).toContain('google_error=access_denied');
  });

});
