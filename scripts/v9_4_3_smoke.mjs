// v9.4.3 — LINE UX hardening smoke test
// Run: node scripts/v9_4_3_smoke.mjs
//
// Covers v9.4.3 additions on top of v9.4.2:
//   A1 — Countdown timer in auth-line.html (LINE linkToken TTL = 10 min)
//   B1 — Stale nonce recovery logging in /api/line/confirm-link
//   C1 — Better visibility logs in line_bot.py (_handle_account_link result=failed)
//   L11 — token_hex nonce + URL encode (defensive · LINE spec compliance)

import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const html = fs.readFileSync(path.join(root, 'legacy-frontend/auth-line.html'), 'utf8');
const authLineJs = fs.readFileSync(path.join(root, 'legacy-frontend/auth-line.js'), 'utf8');
const mainPy = fs.readFileSync(path.join(root, 'backend/main.py'), 'utf8');
const lineBotPy = fs.readFileSync(path.join(root, 'backend/line_bot.py'), 'utf8');
const configPy = fs.readFileSync(path.join(root, 'backend/config.py'), 'utf8');

let pass = 0;
let fail = 0;

function t(name, fn) {
  try {
    const ok = fn();
    console.log(`  ${ok ? 'PASS' : 'FAIL'}  ${name}`);
    if (ok) pass++; else fail++;
  } catch (e) {
    console.log(`  FAIL  ${name} -> ${e.message}`);
    fail++;
  }
}

console.log('=== APP_VERSION = 9.4.3 ===');
t('config.py APP_VERSION = "9.4.3"',
  () => /APP_VERSION\s*=\s*"9\.4\.3"/.test(configPy));

console.log('\n=== A1. Countdown timer in auth-line.html ===');
t('Countdown container element present',
  () => html.includes('id="auth-line-countdown"'));
t('Countdown value element present',
  () => html.includes('id="auth-line-countdown-value"'));
t('Default value text "10:00"',
  () => html.includes('>10:00<'));
t('Countdown CSS .warning class defined',
  () => /\.auth-line-countdown\.warning/.test(html));
t('Countdown CSS .expired class defined',
  () => /\.auth-line-countdown\.expired/.test(html));
t('Pulse keyframe defined for warning state',
  () => /@keyframes pulse/.test(html));

t('startCountdown function exists in auth-line.js',
  () => /function\s+startCountdown\s*\(/.test(authLineJs));
t('stopCountdown function exists in auth-line.js',
  () => /function\s+stopCountdown\s*\(/.test(authLineJs));
t('startCountdown(10*60) called for ready state',
  () => /startCountdown\s*\(\s*10\s*\*\s*60\s*\)/.test(authLineJs));
t('stopCountdown called on success',
  () => authLineJs.includes('stopCountdown()'));
t('Warning state triggered at < 2 min remaining',
  () => /remaining\s*<\s*120/.test(authLineJs));
t('Confirm button disabled when expired',
  () => /btnConfirm\.disabled\s*=\s*true/.test(authLineJs));

console.log('\n=== B1. Stale nonce recovery logging in /api/line/confirm-link ===');
const confirmFn = mainPy.match(/async def line_confirm_link[\s\S]*?(?=\n@app\.|^@app\.|\nasync def [a-z]|\Z)/m);
t('line_confirm_link function found',
  () => confirmFn !== null);
const confirmCode = confirmFn ? confirmFn[0] : '';
t('Logs linkToken_len + prefix on entry',
  () => confirmCode.includes('linkToken_len') && confirmCode.includes('prefix'));
t('Detects expired existing nonce + logs stale recovery',
  () => /stale nonce recovered/i.test(confirmCode));
t('Uses token_hex (not token_urlsafe) — alphanumeric per LINE spec',
  () => confirmCode.includes('token_hex') && !/_secrets\.token_urlsafe/.test(confirmCode));
t('URL-encodes linkToken + nonce in redirect (defense in depth)',
  () => /_urlquote\s*\(\s*body\.link_token/.test(confirmCode)
     && /_urlquote\s*\(\s*nonce/.test(confirmCode));

console.log('\n=== C1. Visibility logs in line_bot.py ===');
const handleAcctFn = lineBotPy.match(/async def _handle_account_link[\s\S]*?(?=\nasync def )/m);
t('_handle_account_link function found',
  () => handleAcctFn !== null);
const handleAcctCode = handleAcctFn ? handleAcctFn[0] : '';
t('result != "ok" upgraded to logger.warning (was INFO)',
  () => /if result != "ok":/.test(handleAcctCode)
     && /logger\.warning\([\s\S]{0,300}LINE rejected/.test(handleAcctCode));
t('Warning includes line_user_id + nonce_prefix for diagnosis',
  () => /line_user=%s/.test(handleAcctCode) && /nonce_prefix=%s/.test(handleAcctCode));

console.log('\n=== Cache-bust to v9.4.3 ===');
const htmlFiles = ['admin','app','auth-line','landing','shared_pack'];
for (const f of htmlFiles) {
  const c = fs.readFileSync(path.join(root, `legacy-frontend/${f}.html`), 'utf8');
  const stale = (c.match(/v=9\.4\.2|v9\.4\.2/g) || []).length;
  t(`${f}.html: 0 stale v9.4.2 refs`, () => stale === 0);
}

console.log('\n=== Regression — v9.4.2 fixes still intact ===');
const lineUi = fs.readFileSync(path.join(root, 'legacy-frontend/line_ui.js'), 'utf8');
const appJs = fs.readFileSync(path.join(root, 'legacy-frontend/app.js'), 'utf8');
const landingJs = fs.readFileSync(path.join(root, 'legacy-frontend/landing.js'), 'utf8');
t('L1+L2: connectLine uses window._lineBotUrl',
  () => lineUi.includes('window._lineBotUrl') && lineUi.includes('window.open'));
t('L3: 10 LINE i18n keys still defined ×2 langs',
  () => (appJs.match(/'line\.title'\s*:/g) || []).length === 2);
t('L4: _redirectToPendingLineLink helper still present',
  () => landingJs.includes('function _redirectToPendingLineLink'));
t('L5: applyLanguage still calls loadLineStatus',
  () => /function applyLanguage[\s\S]*?loadLineStatus/.test(appJs));

console.log(`\n${'='.repeat(60)}`);
console.log(`  v9.4.3 RESULT: ${pass} passed / ${fail} failed`);
console.log(`${'='.repeat(60)}`);

process.exit(fail === 0 ? 0 : 1);
