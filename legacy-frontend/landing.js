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
 window.location.href = '/app';
 return false;
 }
 document.getElementById('landing-page')?.classList.add('hidden');
 appEl.classList.remove('hidden');
 document.body.classList.remove('show-landing');
 // Update sidebar user info
 const emailEl = document.getElementById('sidebar-user-email');
 if (emailEl && state.currentUser) {
 emailEl.textContent = state.currentUser.email || '';
 }
 return true;
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

 try {
 const res = await fetch('/api/auth/login', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ email, password }),
 });
 const data = await res.json();
 if (!res.ok) {
 errorEl.textContent = data.detail || 'Login failed';
 errorEl.classList.remove('hidden');
 return;
 }
 // Save auth
 state.authToken = data.token;
 state.currentUser = data.user;
 localStorage.setItem('pdb_token', data.token);
 localStorage.setItem('pdb_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 _isInitVerified = true;
 if (showApp()) initAppData();
 } catch (e) {
 errorEl.textContent = 'Connection error';
 errorEl.classList.remove('hidden');
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
 return;
 }
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

function initAuth() {
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
 if (state.authToken && state.currentUser) {
 // Show app shell immediately (ไม่ให้ user เห็น landing page flash)
 // If showApp triggered a redirect, the destination page will run its
 // own initAuth+verify; bail out here to avoid aborted in-flight fetches.
 if (!showApp()) return;
 // Verify token is still valid — retry up to 5 times for Fly.io cold-start
 (async () => {
  let verified = false;
  for (let attempt = 0; attempt < 5; attempt++) {
  try {
   const r = await fetch('/api/auth/me', { headers: { 'Authorization': `Bearer ${state.authToken}` } });
   if (r.ok) { verified = true; break; }
   if (r.status === 401) { break; } // definitive: token invalid
   // 502/503/500 = server waking up — retry
   console.log(`[auth] verify attempt ${attempt+1}/5 failed (${r.status}), retrying...`);
   await new Promise(ok => setTimeout(ok, 2000));
  } catch (e) {
   // network error (cold start) — retry
   console.log(`[auth] verify attempt ${attempt+1}/5 network error, retrying...`);
   await new Promise(ok => setTimeout(ok, 2000));
  }
  }
  if (verified) {
  _isInitVerified = true;
  initAppData();
  } else {
  doLogout(); // token หมดอายุจริง → กลับ landing
  }
 })();
 } else {
 showLanding();
 }
}
