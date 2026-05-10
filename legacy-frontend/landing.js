/**
 * Personal Data Bank — landing.js
 * ═══════════════════════════════════════════
 * Owns the unauthenticated experience and the landing → app
 * transition (login, register, password reset, modal switching).
 *
 * Loaded by landing.html and app.html (auth-modal lives on both for
 * the post-401 re-login flow). `showApp()` redirects to /app when
 * the current page lacks the #app block; `showLanding()` redirects
 * to / when the current page lacks #landing-page.
 *
 * Cross-script dependencies (defined in app.js as globals):
 *   state, _isInitVerified, _logoutDebounce, authFetch,
 *   showToast, getLang, t, escapeHtml, initAppData
 */

// ╔══════════════════════════════════════════════════════════════
// ║ §B LANDING + AUTH MODULE
// ╚══════════════════════════════════════════════════════════════

// v9.4.2 (L4) — Resume LINE Account Link flow after login
// Why: auth-line.js เซ็ต sessionStorage 'pdb_pending_line_link' = linkToken เมื่อ user
//      ยังไม่ login + คลิกลิงก์จาก LINE bot · แล้ว redirect / · ก่อนรอบนี้ไม่มีใครอ่านกลับ
//      → linkToken หาย → user ต้องเริ่มจาก LINE bot ใหม่ทุกครั้ง.
// Now: ทุก login success path เรียก helper นี้ก่อน showApp() · ถ้ามี pending → กลับไป /auth/line
//      เพื่อให้ user ยืนยัน LINE link ต่อได้ทันที.
function _redirectToPendingLineLink() {
 try {
 const pendingLink = sessionStorage.getItem('pdb_pending_line_link');
 if (!pendingLink) return false;
 sessionStorage.removeItem('pdb_pending_line_link');
 window.location.href = `/auth/line?linkToken=${encodeURIComponent(pendingLink)}`;
 return true;
 } catch (_e) { return false; }
}

// On split pages (landing.html / app.html), some of these elements
// will be missing — call .classList only when the node exists.
function showLanding() {
 // If we're on app.html (no landing block) → redirect to root
 const landing = document.getElementById('landing-page');
 if (!landing) {
 window.location.href = '/';
 return;
 }
 landing.classList.remove('hidden');
 document.getElementById('app')?.classList.add('hidden');
 document.getElementById('auth-modal')?.classList.add('hidden');
 document.body.classList.add('show-landing');
}

// Returns true when the local DOM has #app and we revealed it in place;
// returns false when we triggered a navigation to /app instead — callers
// should NOT run further data-loading code in the redirect case (the
// destination page boots its own initAppData and fetches started here
// would be aborted by the navigation, polluting the console).
function showApp() {
 const appEl = document.getElementById('app');
 if (!appEl) {
 // ไม่ใช่หน้าที่มี #app shell อยู่ใน DOM (เช่นหน้า / landing) → redirect.
 // v8.2.0 — ตรวจ /api/admin/me ก่อน — ถ้าเป็น admin ส่งไป /admin แทน
 _redirectToAppOrAdmin();
 return false;
 }
 // v8.2.0 — ที่หน้า /app: render ตามปกติ ไม่ auto-redirect ไป /admin
 // (admin ใช้ปุ่ม "Admin Panel" ใน sidebar เพื่อสลับเอง — กัน loop ตอน
 // admin คลิก "← กลับไป /app" จากหน้า /admin)
 document.getElementById('landing-page')?.classList.add('hidden');
 appEl.classList.remove('hidden');
 document.body.classList.remove('show-landing');
 const emailEl = document.getElementById('sidebar-user-email');
 if (emailEl && state.currentUser) emailEl.textContent = state.currentUser.email || '';
 return true;
}

// v8.2.0 — Admin-aware redirect: probe /api/admin/me แบบ async
// ถ้า 200 → /admin, ถ้า 403/error → /app
// v9.3.0 — Honor ?return=/p/{token}&action=claim — กลับไป recipient page หลัง login
function _redirectToAppOrAdmin() {
 // v9.3.0 — ถ้ามี ?return=/p/... → กลับไป recipient page (ไม่ผ่าน /app)
 const params = new URLSearchParams(window.location.search);
 const returnPath = params.get('return');
 const action = params.get('action');
 if (returnPath && returnPath.startsWith('/p/')) {
  // ขั้นต่ำ: validate return path ป้องกัน open redirect
  const safeReturnPath = returnPath.replace(/[^a-zA-Z0-9/_.\-]/g, '');
  const target = safeReturnPath + (action === 'claim' ? '?autoclaim=1' : '');
  window.location.href = target;
  return;
 }

 const token = state.authToken || localStorage.getItem('pdb_token');
 if (!token) {
  window.location.href = '/app';
  return;
 }
 fetch('/api/admin/me', {
  headers: { 'Authorization': 'Bearer ' + token },
 })
  .then(res => {
   window.location.href = res.ok ? '/admin' : '/app';
  })
  .catch(() => {
   // Network error — fallback ไป /app ปกติ
   window.location.href = '/app';
  });
}

function showAuthModal(mode) {
 document.getElementById('auth-modal').classList.remove('hidden');
 // Hide all forms first
 document.getElementById('login-form').classList.add('hidden');
 document.getElementById('register-form').classList.add('hidden');
 document.getElementById('forgot-form').classList.add('hidden');
 document.getElementById('reset-form').classList.add('hidden');

 if (mode === 'register') {
 document.getElementById('register-form').classList.remove('hidden');
 document.getElementById('auth-modal-title').textContent = 'สมัครสมาชิก';
 } else if (mode === 'forgot') {
 document.getElementById('forgot-form').classList.remove('hidden');
 document.getElementById('auth-modal-title').textContent = 'ลืมรหัสผ่าน';
 } else if (mode === 'reset') {
 document.getElementById('reset-form').classList.remove('hidden');
 document.getElementById('auth-modal-title').textContent = 'ตั้งรหัสผ่านใหม่';
 } else {
 document.getElementById('login-form').classList.remove('hidden');
 document.getElementById('auth-modal-title').textContent = 'เข้าสู่ระบบ';
 }
 // Clear errors
 document.getElementById('login-error').classList.add('hidden');
 document.getElementById('register-error').classList.add('hidden');
 document.getElementById('forgot-error').classList.add('hidden');
 document.getElementById('reset-error').classList.add('hidden');
}

async function doLogin() {
 const email = document.getElementById('login-email').value.trim();
 const password = document.getElementById('login-password').value;
 const errorEl = document.getElementById('login-error');
 errorEl.classList.add('hidden');
 errorEl.style.color = ''; // reset (อาจถูก set เป็น emerald จาก forgot flow)

 try {
 const res = await fetch('/api/auth/login', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ email, password }),
 });
 const data = await res.json();
 if (!res.ok) {
 // v8.1.0 — Google-only account hint (detail = {error: {code, message}})
 const errCode = data?.detail?.error?.code;
 if (errCode === 'USE_GOOGLE_LOGIN') {
  errorEl.innerHTML = 'บัญชีนี้สมัครด้วย Google — ' +
    '<a href="#" id="login-error-google-link">คลิกเพื่อ Sign in with Google</a>';
  errorEl.classList.remove('hidden');
  document.getElementById('login-error-google-link')?.addEventListener('click', (e) => {
   e.preventDefault();
   doGoogleLogin();
  });
  return;
 }
 // Generic error
 const msg = data?.detail?.error?.message || data.detail || 'Login failed';
 errorEl.textContent = typeof msg === 'string' ? msg : 'Login failed';
 errorEl.classList.remove('hidden');
 return;
 }
 // Save auth
 state.authToken = data.token;
 state.currentUser = data.user;
 localStorage.setItem('pdb_token', data.token);
 localStorage.setItem('pdb_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 if (_redirectToPendingLineLink()) return;  // v9.4.2 (L4)
 _isInitVerified = true;
 if (showApp()) initAppData();
 } catch (e) {
 errorEl.textContent = 'Connection error';
 errorEl.classList.remove('hidden');
 }
}

// v8.1.0 — Google Sign-In trigger
// Frontend ไม่ต้อง redirect ตรง /api/auth/google/init เพราะถ้า server 503 (ยังไม่ configured)
// browser จะแสดง JSON ดิบ — fetch ก่อนแล้ว detect 503 → แสดง toast แทน
async function doGoogleLogin() {
 try {
 const r = await fetch('/api/auth/google/init', {
   headers: { 'Accept': 'application/json' },
 });
 if (r.status === 503) {
  showToast(
   getLang() === 'th'
     ? 'Google Sign-In ยังไม่พร้อมใช้งาน'
     : 'Google Sign-In is not configured',
   'error'
  );
  return;
 }
 if (!r.ok) {
  showToast(
   getLang() === 'th' ? 'เริ่มต้น Google Sign-In ไม่สำเร็จ' : 'Failed to start Google Sign-In',
   'error'
  );
  return;
 }
 const data = await r.json();
 if (data.auth_url) {
  window.location.assign(data.auth_url);
 } else {
  showToast(getLang() === 'th' ? 'ลิงก์ไม่ถูกต้อง' : 'Invalid auth URL', 'error');
 }
 } catch (e) {
 showToast(
   getLang() === 'th' ? 'เชื่อมต่อเซิร์ฟเวอร์ไม่ได้' : 'Cannot connect to server',
   'error'
 );
 }
}

async function doRegister() {
 const name = document.getElementById('register-name').value.trim();
 const email = document.getElementById('register-email').value.trim();
 const password = document.getElementById('register-password').value;
 const errorEl = document.getElementById('register-error');
 errorEl.classList.add('hidden');

 try {
 const res = await fetch('/api/auth/register', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ email, password, name }),
 });
 const data = await res.json();
 if (!res.ok) {
 errorEl.textContent = data.detail || 'Registration failed';
 errorEl.classList.remove('hidden');
 return;
 }
 // Save auth
 state.authToken = data.token;
 state.currentUser = data.user;
 localStorage.setItem('pdb_token', data.token);
 localStorage.setItem('pdb_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 if (_redirectToPendingLineLink()) return;  // v9.4.2 (L4)
 _isInitVerified = true;
 // v7.0.1 — เข้า workspace ทันทีหลัง register (ไม่ redirect ไป pricing)
 // user อัปเกรดได้ภายหลังจาก Profile modal
 if (showApp()) initAppData();
 showToast(
  getLang() === 'th'
    ? 'สมัครสำเร็จ! ยินดีต้อนรับสู่ Personal Data Bank'
    : 'Welcome to Personal Data Bank!',
  'success'
 );
 } catch (e) {
 errorEl.textContent = 'Connection error';
 errorEl.classList.remove('hidden');
 }
}

function doLogout() {
 state.authToken = null;
 state.currentUser = null;
 localStorage.removeItem('pdb_token');
 localStorage.removeItem('pdb_user');
 showLanding();
}

// v5.1 — Password Reset
let _resetToken = null;

async function doForgotPassword() {
 const email = document.getElementById('forgot-email').value.trim();
 const errorEl = document.getElementById('forgot-error');
 errorEl.classList.add('hidden');

 if (!email) {
 errorEl.textContent = 'กรุณากรอกอีเมล';
 errorEl.classList.remove('hidden');
 return;
 }

 try {
 const res = await fetch('/api/auth/request-reset', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ email }),
 });
 const data = await res.json();
 if (!res.ok) {
 errorEl.textContent = data.detail || 'เกิดข้อผิดพลาด';
 errorEl.classList.remove('hidden');
 return;
 }
 // Backend now responds with the same shape regardless of whether the email
 // exists (anti-enumeration). reset_token is only present for real accounts.
 if (!data.reset_token) {
   errorEl.textContent = data.message || 'ถ้าอีเมลนี้มีบัญชีอยู่ ระบบจะส่งลิงก์รีเซ็ตให้';
   errorEl.classList.remove('hidden');
   errorEl.style.color = '#10b981'; // Tailwind emerald-500
   return;
 }
 // Legacy fallback for dev environment (if backend still returns token)
 _resetToken = data.reset_token;
 document.getElementById('reset-email-display').textContent = data.email;
 showAuthModal('reset');
 } catch (e) {
 errorEl.textContent = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์';
 errorEl.classList.remove('hidden');
 }
}

async function doResetPassword() {
 const newPassword = document.getElementById('reset-new-password').value;
 const confirmPassword = document.getElementById('reset-confirm-password').value;
 const errorEl = document.getElementById('reset-error');
 errorEl.classList.add('hidden');

 if (newPassword.length < 6) {
 errorEl.textContent = 'รหัสผ่านต้องมีอย่างน้อย 6 ตัวอักษร';
 errorEl.classList.remove('hidden');
 return;
 }

 if (newPassword !== confirmPassword) {
 errorEl.textContent = 'รหัสผ่านไม่ตรงกัน';
 errorEl.classList.remove('hidden');
 return;
 }

 try {
 const res = await fetch('/api/auth/reset-password', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ token: _resetToken, new_password: newPassword }),
 });
 const data = await res.json();
 if (!res.ok) {
 errorEl.textContent = data.detail || 'เปลี่ยนรหัสผ่านไม่สำเร็จ';
 errorEl.classList.remove('hidden');
 return;
 }
 // Auto-login
 state.authToken = data.token;
 state.currentUser = data.user;
 localStorage.setItem('pdb_token', data.token);
 localStorage.setItem('pdb_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 if (_redirectToPendingLineLink()) return;  // v9.4.2 (L4)
 _isInitVerified = true;
 _resetToken = null;
 // Trigger redirect/show first; let toast render after to avoid the
 // toast DOM keeping the test thread busy when the page is navigating.
 if (showApp()) initAppData();
 showToast('เปลี่ยนรหัสผ่านสำเร็จ!', 'success');
 } catch (e) {
 errorEl.textContent = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์';
 errorEl.classList.remove('hidden');
 }
}

// v8.1.0 — Handle Google Sign-In callback (URL fragment #token=<jwt>)
// Server redirects ที่ /app#token=... หลัง verify สำเร็จ — fragment ไม่ส่งไป server / Referer
function _handleGoogleLoginFragment() {
 const hash = window.location.hash || '';
 if (!hash.startsWith('#token=')) return false;
 const jwt = hash.slice('#token='.length);
 if (!jwt || jwt.split('.').length !== 3) {
  console.warn('[google-login] bad fragment payload, ignoring');
  return false;
 }
 try {
  // Decode JWT payload (no verify — backend already verified ก่อนออก token นี้)
  const payloadB64 = jwt.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
  const padded = payloadB64 + '='.repeat((4 - payloadB64.length % 4) % 4);
  const payload = JSON.parse(atob(padded));
  state.authToken = jwt;
  state.currentUser = {
   id: payload.sub,
   email: payload.email,
   name: payload.name,
   // mcp_secret จะ populate ตอน /api/auth/me ถูกเรียกครั้งแรก (ใน initAppData)
  };
  localStorage.setItem('pdb_token', jwt);
  localStorage.setItem('pdb_user', JSON.stringify(state.currentUser));
  // Clean URL (เอา fragment ออก) — ต้องอยู่ที่ /app
  window.history.replaceState({}, document.title, '/app');
  if (_redirectToPendingLineLink()) return true;  // v9.4.2 (L4)
  // v8.1.2 perf: token เพิ่งออกจาก backend (verified ID token + signed JWT) →
  // เชื่อใจได้ทันที, ไม่ต้อง re-verify ผ่าน /api/auth/me ที่ initAuth ทำต่อ
  _isInitVerified = true;
  // v8.1.2 perf: แสดง app shell + loading overlay ทันทีโดยใช้ JWT payload ที่ decode แล้ว
  // (ก่อนหน้านี้ block ที่ /api/admin/me probe ~200-500ms — ตอนนี้ render ก่อน probe)
  showToast(getLang() === 'th' ? 'เข้าสู่ระบบสำเร็จ! กำลังโหลด...' : 'Signed in! Loading...', 'success');
  // v8.1.1 — admin probe สำหรับ first-arrival จาก Google. cache result ใน sessionStorage
  // เพื่อให้ _revealAdminLinkIfAdmin() ใน app.js ไม่ต้อง fetch ซ้ำ (ประหยัด 1 request)
  fetch('/api/admin/me', { headers: { 'Authorization': 'Bearer ' + jwt } })
   .then(res => {
    // Cache result regardless of admin/non-admin (positive + negative cache)
    try {
     sessionStorage.setItem('pdb_admin_probe', res.ok ? '1' : '0');
     sessionStorage.setItem('pdb_admin_probe_ts', String(Date.now()));
    } catch (_) { /* sessionStorage may be unavailable in private mode */ }
    if (res.ok) {
     window.location.href = '/admin';
    } else {
     // Non-admin: render /app ปกติ
     if (showApp()) initAppData();
    }
   })
   .catch(() => {
    // Network error → fallback ไป /app ปกติ (ไม่ cache เพราะไม่รู้ผลจริง)
    if (showApp()) initAppData();
   });
  return true;
 } catch (e) {
  console.error('[google-login] fragment decode failed:', e);
  return false;
 }
}

// v8.1.0 — Handle Google Sign-In error (?google_error=<reason>)
function _handleGoogleLoginError() {
 const params = new URLSearchParams(window.location.search);
 const gErr = params.get('google_error');
 if (!gErr) return;
 const isTH = getLang() === 'th';
 const messages = {
  access_denied: isTH ? 'คุณยกเลิกการเข้าสู่ระบบ Google' : 'You canceled Google sign-in',
  invalid_state: isTH ? 'ลิงก์หมดอายุ กรุณาลองใหม่' : 'Login link expired — please try again',
  invalid_id_token: isTH ? 'Google ID token ไม่ถูกต้อง' : 'Invalid Google ID token',
  email_not_verified: isTH ? 'อีเมล Google ยังไม่ verified' : 'Google email is not verified',
  google_api_error: isTH ? 'Google API ขัดข้อง กรุณาลองใหม่' : 'Google API error — please retry',
  missing_params: isTH ? 'ลิงก์ callback ไม่สมบูรณ์' : 'Incomplete callback URL',
  account_disabled: isTH ? 'บัญชีนี้ถูกปิดใช้งาน' : 'This account is deactivated',
  internal_error: isTH ? 'เกิดข้อผิดพลาดในระบบ' : 'Internal server error',
 };
 showToast(messages[gErr] || (isTH ? 'เกิดข้อผิดพลาด' : 'An error occurred'), 'error');
 // Clean URL — เอา query param ออก
 const url = new URL(window.location.href);
 url.searchParams.delete('google_error');
 window.history.replaceState({}, document.title, url.pathname + (url.search || '') + url.hash);
}

function initAuth() {
 // v8.1.0 — Google login: fragment handler ต้อง run ก่อน check authToken
 // เพราะ Google callback ส่งกลับมาที่ /app#token=... โดย user ยังไม่มี token ใน localStorage
 if (_handleGoogleLoginFragment()) return;
 _handleGoogleLoginError();

 // v9.3.0 — ถ้า user logged in อยู่แล้ว + มี ?return=/p/... → redirect ไป recipient page ทันที
 // (ไม่ต้องโชว์ landing page หรือ /app)
 const _params = new URLSearchParams(window.location.search);
 const _returnPath = _params.get('return');
 if (_returnPath && _returnPath.startsWith('/p/') && state.authToken) {
  const _action = _params.get('action');
  const _safe = _returnPath.replace(/[^a-zA-Z0-9/_.\-]/g, '');
  window.location.href = _safe + (_action === 'claim' ? '?autoclaim=1' : '');
  return;
 }
 // ถ้ายังไม่ login + มี ?return=/p/... + ?signup=1 → เปิด register modal อัตโนมัติ
 if (_returnPath && _returnPath.startsWith('/p/') && !state.authToken) {
  if (_params.get('signup') === '1') {
   setTimeout(() => showAuthModal('register'), 200);
  } else {
   setTimeout(() => showAuthModal('login'), 200);
  }
 }

 // Landing page buttons
 document.getElementById('btn-show-login')?.addEventListener('click', () => showAuthModal('login'));
 document.getElementById('btn-show-register')?.addEventListener('click', () => showAuthModal('register'));
 document.getElementById('btn-hero-register')?.addEventListener('click', () => showAuthModal('register'));
 document.getElementById('btn-hero-login')?.addEventListener('click', () => showAuthModal('login'));
 document.getElementById('btn-cta-register')?.addEventListener('click', () => showAuthModal('register'));



 // Landing pricing buttons
 document.getElementById('btn-pricing-free')?.addEventListener('click', () => showAuthModal('register'));
 document.getElementById('btn-pricing-starter')?.addEventListener('click', () => {
 if (state.authToken) {
 window.location.href = '/pricing';
 } else {
 showAuthModal('register');
 showToast(getLang() === 'th' ? ' สมัครสมาชิกก่อน แล้วอัปเกรดได้ในโปรไฟล์' : ' Register first, then upgrade from your profile', 'info');
 }
 });

 // Auth modal
 document.getElementById('auth-modal-close')?.addEventListener('click', () => {
 document.getElementById('auth-modal').classList.add('hidden');
 });
 document.getElementById('switch-to-register')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('register'); });
 document.getElementById('switch-to-login')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('login'); });
 document.getElementById('switch-to-forgot')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('forgot'); });
 document.getElementById('switch-forgot-to-login')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('login'); });
 document.getElementById('switch-reset-to-login')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('login'); });
 document.getElementById('btn-login')?.addEventListener('click', doLogin);
 document.getElementById('btn-register')?.addEventListener('click', doRegister);
 // v8.1.1 — Unified Google Sign-In: ปุ่มเดียวบน login form ใช้ได้ทั้งสมัครใหม่ + login
 // (backend login_or_create_google_user คือ "find-or-create" — ไม่ต้องแยก 2 ปุ่ม)
 document.getElementById('btn-google-login-login')?.addEventListener('click', doGoogleLogin);
 // v8.1.1 — link จาก register form → switch ไป login form แล้ว trigger Google
 // (user ที่อยู่หน้า "สมัครสมาชิก" เลือกจะใช้ Google → ไปยังจุดเดียวที่มีปุ่ม)
 document.getElementById('switch-to-login-google')?.addEventListener('click', (e) => {
  e.preventDefault();
  showAuthModal('login');
  // เลื่อนไป login form แล้วโฟกัส Google button (ผู้ใช้เห็นชัดว่าตัวเลือกอยู่ตรงนี้)
  setTimeout(() => document.getElementById('btn-google-login-login')?.focus(), 100);
 });
 document.getElementById('btn-forgot-submit')?.addEventListener('click', doForgotPassword);
 document.getElementById('btn-reset-submit')?.addEventListener('click', doResetPassword);

 // Enter key for login/register/reset
 document.getElementById('login-password')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') doLogin(); });
 document.getElementById('register-password')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') doRegister(); });
 document.getElementById('forgot-email')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') doForgotPassword(); });
 document.getElementById('reset-confirm-password')?.addEventListener('keydown', (e) => { if (e.key === 'Enter') doResetPassword(); });

 // Logout
 document.getElementById('btn-logout')?.addEventListener('click', doLogout);

 // Check if already logged in
 // v7.5.1 — diagnostic logging + 1-retry on 401 to catch transient errors
 console.log('[auth] initAuth — token present:', !!state.authToken, 'user present:', !!state.currentUser);
 if (state.authToken && state.currentUser) {
 // v8.1.2 perf: ถ้า _isInitVerified=true แล้ว (เพิ่งมาจาก Google fragment handler
 // ที่ verify ผ่าน backend แล้ว) → ข้าม /api/auth/me retry loop เพื่อประหยัด
 // 1 round-trip และไม่ duplicate กับ admin probe ที่ทำไปแล้ว
 if (_isInitVerified) {
  console.log('[auth] already verified (Google fragment) — skip /api/auth/me');
  return;
 }
 // Show app shell immediately (ไม่ให้ user เห็น landing page flash)
 // If showApp triggered a redirect, the destination page will run its
 // own initAuth+verify; bail out here to avoid aborted in-flight fetches.
 if (!showApp()) {
  console.log('[auth] showApp redirected — aborting verify on this page');
  return;
 }
 // Verify token is still valid — retry up to 5 times for Fly.io cold-start
 // v7.5.1: 401 also retries ONCE (was: definitive break) to survive transient
 // backend hiccups (e.g. DB connection blip during request) — true expired token
 // will fail twice and still trigger logout
 (async () => {
  let verified = false;
  let unauthorizedCount = 0;
  for (let attempt = 0; attempt < 5; attempt++) {
  try {
   const r = await fetch('/api/auth/me', { headers: { 'Authorization': `Bearer ${state.authToken}` } });
   if (r.ok) {
    console.log(`[auth] verify attempt ${attempt+1}/5 — 200 OK`);
    verified = true;
    break;
   }
   if (r.status === 401) {
    unauthorizedCount++;
    if (unauthorizedCount >= 2) {
     console.warn('[auth] verify got 401 twice — token definitely invalid, will logout');
     break;
    }
    console.log(`[auth] verify attempt ${attempt+1}/5 — 401 (transient?), retrying once...`);
    await new Promise(ok => setTimeout(ok, 1000));
    continue;
   }
   // 502/503/500 = server waking up — retry
   console.log(`[auth] verify attempt ${attempt+1}/5 failed (${r.status}), retrying...`);
   await new Promise(ok => setTimeout(ok, 2000));
  } catch (e) {
   // network error (cold start) — retry
   console.log(`[auth] verify attempt ${attempt+1}/5 network error: ${e.message}, retrying...`);
   await new Promise(ok => setTimeout(ok, 2000));
  }
  }
  if (verified) {
  _isInitVerified = true;
  console.log('[auth] verify SUCCESS — _isInitVerified=true, calling initAppData');
  initAppData();
  } else {
  console.warn('[auth] verify FAILED after retries — calling doLogout');
  doLogout(); // token หมดอายุจริง → กลับ landing
  }
 })();
 } else {
 console.log('[auth] no token or user — showing landing');
 showLanding();
 // v7.6.0 — Handle email password reset link (must run AFTER showLanding)
 const urlParams = new URLSearchParams(window.location.search);
 const tokenFromUrl = urlParams.get('token');
 if (tokenFromUrl && window.location.pathname === '/reset-password') {
   _resetToken = tokenFromUrl;
   showAuthModal('reset');
   window.history.replaceState({}, document.title, '/');
 }
 }
}

// v7.5.1 — Diagnostic helper: paste into DevTools to see auth state
window.__pdb_auth_debug = function() {
 const t = localStorage.getItem('pdb_token');
 const u = localStorage.getItem('pdb_user');
 console.group('🔐 PDB Auth Debug');
 console.log('localStorage pdb_token:', t ? `${t.slice(0, 30)}... (len=${t.length})` : 'NULL');
 console.log('localStorage pdb_user:', u ? u.slice(0, 100) : 'NULL');
 try { console.log('Parsed user:', JSON.parse(u || 'null')); } catch (e) { console.error('Parse fail:', e); }
 console.log('state.authToken:', state.authToken ? `${state.authToken.slice(0, 30)}... (len=${state.authToken.length})` : 'NULL');
 console.log('state.currentUser:', state.currentUser);
 console.log('_isInitVerified:', _isInitVerified);
 console.log('_logoutDebounce:', _logoutDebounce);
 console.groupEnd();
 if (t) {
  fetch('/api/auth/me', { headers: { 'Authorization': `Bearer ${t}` } })
   .then(r => r.json().then(b => console.log(`/api/auth/me → ${r.status}`, b)))
   .catch(e => console.error('/api/auth/me fetch error:', e));
 }
};
