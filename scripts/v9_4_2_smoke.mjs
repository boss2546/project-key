// v9.4.2 — LINE UX Fixes smoke test (frontend-only · static analysis)
// Run: node scripts/v9_4_2_smoke.mjs
//
// Covers 5 findings (L1-L5) from v9.4.2 plan. Pure static analysis since
// behavior is browser-side · backend untouched.

import fs from 'node:fs';
import path from 'node:path';

const root = process.cwd();
const html = fs.readFileSync(path.join(root, 'legacy-frontend/app.html'), 'utf8');
const appJs = fs.readFileSync(path.join(root, 'legacy-frontend/app.js'), 'utf8');
const lineUi = fs.readFileSync(path.join(root, 'legacy-frontend/line_ui.js'), 'utf8');
const landingJs = fs.readFileSync(path.join(root, 'legacy-frontend/landing.js'), 'utf8');

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

console.log('=== L1. connectLine refactored — opens bot URL directly ===');
const connectFn = lineUi.match(/async function connectLine[\s\S]*?\n\}/)[0];
const connectCode = connectFn.split('\n').filter(l => !l.trim().startsWith('//')).join('\n');
t('connectLine NO call to dead /api/line/connect endpoint',
  () => !connectCode.includes('/api/line/connect'));
t('connectLine NO authFetch (was original POST mechanism)',
  () => !connectCode.includes('authFetch'));
t('connectLine reads window._lineBotUrl',
  () => connectCode.includes('window._lineBotUrl'));
t('connectLine calls window.open',
  () => connectCode.includes('window.open'));
t('connectLine has 2 showToast (error + info)',
  () => (connectCode.match(/showToast/g) || []).length === 2);

console.log('\n=== L2. _renderLineStatus exposes bot_url ===');
t('_renderLineStatus assigns window._lineBotUrl from data.bot_url',
  () => lineUi.includes('window._lineBotUrl = data.bot_url'));
const renderFn = lineUi.match(/function _renderLineStatus[\s\S]*?\n\}/)[0];
t('Assignment is INSIDE _renderLineStatus (not stray top-level)',
  () => renderFn.includes('window._lineBotUrl = data.bot_url'));

console.log('\n=== L3. 10 LINE i18n keys × TH + EN (20 entries) ===');
const lineKeys = new Set();
const re = /data-i18n="(line\.[a-zA-Z]+)"/g;
let m;
while ((m = re.exec(html)) !== null) lineKeys.add(m[1]);
t('app.html declares 10 LINE data-i18n keys',
  () => lineKeys.size === 10);
const expected = ['line.title','line.desc','line.connect','line.disconnect','line.openChat',
                  'line.notConfigured','line.notLinked','line.displayName','line.linkedAt','line.lastSeen'];
for (const k of expected) {
  const escaped = k.replace(/\./g, '\\.');
  const reKey = new RegExp("'" + escaped + "'\\s*:", 'g');
  const count = (appJs.match(reKey) || []).length;
  t(`'${k}' defined twice (TH + EN)`, () => count === 2);
}

console.log('\n=== L4. landing.js _redirectToPendingLineLink helper + 4 callers ===');
t('Helper function _redirectToPendingLineLink exists',
  () => landingJs.includes('function _redirectToPendingLineLink'));
t("Helper reads sessionStorage 'pdb_pending_line_link'",
  () => landingJs.includes("sessionStorage.getItem('pdb_pending_line_link')"));
t('Helper clears sessionStorage after read',
  () => landingJs.includes("sessionStorage.removeItem('pdb_pending_line_link')"));
t('Helper redirects to /auth/line with linkToken query',
  () => /\/auth\/line\?linkToken=\$\{encodeURIComponent\(/.test(landingJs));
const callers = (landingJs.match(/if \(_redirectToPendingLineLink\(\)\)/g) || []).length;
t('Helper called from 4 login success paths',
  () => callers === 4);
const earlyReturns = (landingJs.match(/if \(_redirectToPendingLineLink\(\)\) return( true)?;/g) || []).length;
t('All 4 callers do early return (pre-empt showApp+initAppData)',
  () => earlyReturns === 4);

console.log('\n=== L5. applyLanguage re-renders LINE status ===');
const applyFn = appJs.match(/function applyLanguage\(lang\)[\s\S]*?\n\}/)[0];
t('applyLanguage calls loadLineStatus',
  () => applyFn.includes('loadLineStatus'));
t('Regression: applyLanguage still calls renderStorageModeUI',
  () => applyFn.includes('renderStorageModeUI'));
t('Regression: applyLanguage still calls renderDriveErrorBanner',
  () => applyFn.includes('renderDriveErrorBanner'));

console.log('\n=== Cache-bust to v9.4.2 ===');
const htmlFiles = ['admin','app','auth-line','landing','shared_pack'];
for (const f of htmlFiles) {
  const c = fs.readFileSync(path.join(root, `legacy-frontend/${f}.html`), 'utf8');
  const stale = (c.match(/v=9\.4\.1|v9\.4\.1/g) || []).length;
  t(`${f}.html: 0 stale v9.4.1 refs`, () => stale === 0);
}

console.log(`\n${'='.repeat(60)}`);
console.log(`  v9.4.2 RESULT: ${pass} passed / ${fail} failed`);
console.log(`${'='.repeat(60)}`);

process.exit(fail === 0 ? 0 : 1);
