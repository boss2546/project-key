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

// v10.0.0 — Auth helper utilities (extracted to fix MSG-UI-TEST-001..004 from ฟ้า)
// Why: FastAPI 422 ส่ง `detail` เป็น array → `errorEl.textContent = arr` แสดง "[object Object]"
//      ต้อง parse ให้ออกมาเป็น string ที่อ่านรู้เรื่อง.
function _extractDetailMessage(detail, fallback) {
  if (detail === null || detail === undefined || detail === '') return fallback;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const msgs = detail.map(d => (d && (d.msg || d.message)) || (typeof d === 'string' ? d : '')).filter(Boolean);
    return msgs.length ? msgs.join(', ') : fallback;
  }
  if (typeof detail === 'object') {
    return detail.message || detail.msg || detail?.error?.message || fallback;
  }
  return String(detail);
}

// Reset error element ทั้ง text + hidden + inline color
// Why: BUG-LOGIC-01 — สีเขียวจาก forgot-success ค้างต่อใน validation error รอบถัดไป
//      ทุก path ที่ใช้ errorEl ต้องผ่านตัวนี้ก่อน set ข้อความใหม่.
function _resetAuthError(el) {
  if (!el) return;
  el.textContent = '';
  el.classList.add('hidden');
  el.style.color = '';
}

// Toggle button loading state (disable + เปลี่ยน text · เก็บ original text กลับมา restore ได้)
// Why: UX-01 — กันกดซ้ำตอน fetch ยังไม่ตอบกลับ · BUG-LOGIC-02 — keep loading ระหว่าง redirect probe.
function _setBtnLoading(btn, isLoading, loadingText) {
  if (!btn) return;
  if (isLoading) {
    if (!btn.dataset.originalText) btn.dataset.originalText = btn.textContent;
    btn.disabled = true;
    if (loadingText) btn.textContent = loadingText;
  } else {
    btn.disabled = false;
    if (btn.dataset.originalText) {
      btn.textContent = btn.dataset.originalText;
      delete btn.dataset.originalText;
    }
  }
}

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
 // v10.0.x — P1-4 · ลด /api/admin/me 403 spam · ใช้ cache 24hr ก่อน
 try {
  const cached = localStorage.getItem('pdb_admin_probe');
  const ts = parseInt(localStorage.getItem('pdb_admin_probe_ts') || '0', 10);
  if (cached !== null && (Date.now() - ts) < 24 * 3600 * 1000) {
   window.location.href = cached === '1' ? '/admin' : '/app';
   return;
  }
 } catch (_) {}
 fetch('/api/admin/me', {
  headers: { 'Authorization': 'Bearer ' + token },
 })
  .then(res => {
   try {
    localStorage.setItem('pdb_admin_probe', res.ok ? '1' : '0');
    localStorage.setItem('pdb_admin_probe_ts', String(Date.now()));
   } catch (_) {}
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
 // Reset errors (text + hidden + inline color — กันสีเขียวจาก forgot-success ค้าง)
 _resetAuthError(document.getElementById('login-error'));
 _resetAuthError(document.getElementById('register-error'));
 _resetAuthError(document.getElementById('forgot-error'));
 _resetAuthError(document.getElementById('reset-error'));

 // BUG-EDGE-01 · เคลียร์ input ทุกครั้งที่เปิด modal · กัน state leak บนเครื่อง public
 // ยกเว้น reset mode: reset-email-display ไม่ใช่ input · password fields ก็ควรเริ่มว่างอยู่แล้ว
 document.querySelectorAll('#auth-modal input').forEach(el => {
   el.value = '';
   // กัน password toggle ยังเป็น type="text" ค้างจาก session ก่อน
   if (el.dataset.pwdOriginalType) {
     el.type = el.dataset.pwdOriginalType;
   }
 });
 // Reset show/hide password button state กลับเป็น "ซ่อน" (type=password เริ่มต้น)
 document.querySelectorAll('#auth-modal .pwd-toggle').forEach(btn => {
   btn.setAttribute('aria-pressed', 'false');
   btn.setAttribute('aria-label', 'แสดงรหัสผ่าน');
   btn.classList.remove('is-visible');
 });
 // Reset button loading state (เผื่อปิด modal ระหว่าง fetch แล้วเปิดใหม่)
 ['btn-login', 'btn-register', 'btn-forgot-submit', 'btn-reset-submit'].forEach(id => {
   _setBtnLoading(document.getElementById(id), false);
 });
}

async function doLogin() {
 const email = document.getElementById('login-email').value.trim();
 const password = document.getElementById('login-password').value;
 const errorEl = document.getElementById('login-error');
 const btn = document.getElementById('btn-login');
 _resetAuthError(errorEl);

 // BUG-UI-03 · client-side validation ก่อนยิง API
 if (!email || !password) {
   errorEl.textContent = 'กรุณากรอกอีเมลและรหัสผ่าน';
   errorEl.classList.remove('hidden');
   return;
 }

 // UX-01 · disable button + แสดง loading ระหว่างรอ response
 _setBtnLoading(btn, true, 'กำลังเข้าสู่ระบบ...');

 try {
 const res = await fetch('/api/auth/login', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ email, password }),
 });
 const data = await res.json();
 if (!res.ok) {
 // BUG-UI-02 · 422 detail เป็น array → ต้อง parse ก่อน · นำ nested error.message มาก่อน (custom error format)
 const nested = data?.detail?.error?.message;
 errorEl.textContent = nested || _extractDetailMessage(data.detail, 'อีเมลหรือรหัสผ่านไม่ถูกต้อง');
 errorEl.classList.remove('hidden');
 _setBtnLoading(btn, false);
 return;
 }
 // BUG-LOGIC-02 · login สำเร็จ → คงสถานะ loading + เปลี่ยน text เป็น "กำลังพาเข้าสู่ระบบ..."
 // จนกว่า window.location.href จะทำงานเสร็จ (ระหว่าง /api/admin/me probe ใน _redirectToAppOrAdmin)
 _setBtnLoading(btn, true, 'กำลังพาเข้าสู่ระบบ...');
 state.authToken = data.token;
 state.currentUser = data.user;
 localStorage.setItem('pdb_token', data.token);
 localStorage.setItem('pdb_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 if (_redirectToPendingLineLink()) return;  // v9.4.2 (L4)
 _isInitVerified = true;
 if (showApp()) initAppData();
 } catch (e) {
 errorEl.textContent = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์';
 errorEl.classList.remove('hidden');
 _setBtnLoading(btn, false);
 }
}

// Google Sign-In removed in v9.5.0.
// See docs/restoration/google-login-restore.md for full restore guide.

async function doRegister() {
 const name = document.getElementById('register-name').value.trim();
 const email = document.getElementById('register-email').value.trim();
 const password = document.getElementById('register-password').value;
 const errorEl = document.getElementById('register-error');
 const btn = document.getElementById('btn-register');
 _resetAuthError(errorEl);

 // BUG-UI-03 · client-side validation ก่อนยิง API
 if (!name || !email || !password) {
   errorEl.textContent = 'กรุณากรอกข้อมูลให้ครบถ้วน';
   errorEl.classList.remove('hidden');
   return;
 }

 // UX-01 · disable button + แสดง loading
 _setBtnLoading(btn, true, 'กำลังสมัครสมาชิก...');

 try {
 const res = await fetch('/api/auth/register', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ email, password, name }),
 });
 const data = await res.json();
 if (!res.ok) {
 // BUG-UI-01 · 422 detail (Pydantic array) → parse เป็น string · กัน "[object Object]"
 errorEl.textContent = _extractDetailMessage(data.detail, 'สมัครสมาชิกไม่สำเร็จ');
 errorEl.classList.remove('hidden');
 _setBtnLoading(btn, false);
 return;
 }
 // BUG-LOGIC-02 · register สำเร็จ → คง loading state ระหว่าง redirect ไป /app
 _setBtnLoading(btn, true, 'กำลังพาเข้าสู่ระบบ...');
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
 errorEl.textContent = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์';
 errorEl.classList.remove('hidden');
 _setBtnLoading(btn, false);
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
 const btn = document.getElementById('btn-forgot-submit');
 // BUG-LOGIC-01 · _resetAuthError ล้าง color = '' ก่อนทุกครั้ง
 // กันสีเขียวจาก success state รั่วไปยัง validation error รอบถัดไป
 _resetAuthError(errorEl);

 if (!email) {
 errorEl.textContent = 'กรุณากรอกอีเมล';
 errorEl.classList.remove('hidden');
 return;
 }

 _setBtnLoading(btn, true, 'กำลังตรวจสอบ...');

 try {
 const res = await fetch('/api/auth/request-reset', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ email }),
 });
 const data = await res.json();
 if (!res.ok) {
 errorEl.textContent = _extractDetailMessage(data.detail, 'เกิดข้อผิดพลาด');
 errorEl.classList.remove('hidden');
 _setBtnLoading(btn, false);
 return;
 }
 // Backend now responds with the same shape regardless of whether the email
 // exists (anti-enumeration). reset_token is only present for real accounts.
 if (!data.reset_token) {
   errorEl.textContent = data.message || 'ถ้าอีเมลนี้มีบัญชีอยู่ ระบบจะส่งลิงก์รีเซ็ตให้';
   errorEl.classList.remove('hidden');
   errorEl.style.color = '#10b981'; // Tailwind emerald-500 (success state)
   _setBtnLoading(btn, false);
   return;
 }
 // Legacy fallback for dev environment (if backend still returns token)
 _resetToken = data.reset_token;
 document.getElementById('reset-email-display').textContent = data.email;
 showAuthModal('reset');
 } catch (e) {
 errorEl.textContent = 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์';
 errorEl.classList.remove('hidden');
 _setBtnLoading(btn, false);
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

// Google Sign-In callback handlers removed in v9.5.0.
// See docs/restoration/google-login-restore.md for full restore guide.

function initAuth() {
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



 // v9.6.0 — pricing buttons removed (Stripe billing system ถูกลบ)

 // Auth modal
 document.getElementById('auth-modal-close')?.addEventListener('click', () => {
 document.getElementById('auth-modal').classList.add('hidden');
 });
 // BUG-EDGE-02 · คลิก backdrop (พื้นที่ดำรอบ modal) → ปิด modal
 // เช็ค e.target === e.currentTarget เพื่อไม่ให้คลิกใน modal box เผลอปิดด้วย
 const _authModalEl = document.getElementById('auth-modal');
 if (_authModalEl) {
   _authModalEl.addEventListener('click', (e) => {
     if (e.target === e.currentTarget) {
       _authModalEl.classList.add('hidden');
     }
   });
 }
 document.getElementById('switch-to-register')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('register'); });
 document.getElementById('switch-to-login')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('login'); });
 document.getElementById('switch-to-forgot')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('forgot'); });
 document.getElementById('switch-forgot-to-login')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('login'); });
 document.getElementById('switch-reset-to-login')?.addEventListener('click', (e) => { e.preventDefault(); showAuthModal('login'); });
 document.getElementById('btn-login')?.addEventListener('click', doLogin);
 document.getElementById('btn-register')?.addEventListener('click', doRegister);
 document.getElementById('btn-forgot-submit')?.addEventListener('click', doForgotPassword);
 document.getElementById('btn-reset-submit')?.addEventListener('click', doResetPassword);

 // UX-02 · กด Enter ใน email field ก็ submit ฟอร์มได้ · เดิมรองรับแค่ password field
 const _enterPairs = [
   ['login-email', doLogin],
   ['login-password', doLogin],
   ['register-name', doRegister],
   ['register-email', doRegister],
   ['register-password', doRegister],
   ['forgot-email', doForgotPassword],
   ['reset-new-password', doResetPassword],
   ['reset-confirm-password', doResetPassword],
 ];
 _enterPairs.forEach(([id, fn]) => {
   document.getElementById(id)?.addEventListener('keydown', (e) => { if (e.key === 'Enter') fn(); });
 });

 // UX-03 · ปุ่ม show/hide password (eye toggle)
 // ตำแหน่ง: ปุ่มอยู่ใน .pwd-wrap ติดกับ <input type="password"> · toggle type ระหว่าง password ↔ text
 document.querySelectorAll('.pwd-toggle').forEach(btn => {
   btn.addEventListener('click', () => {
     const wrap = btn.closest('.pwd-wrap');
     const input = wrap?.querySelector('input');
     if (!input) return;
     if (!input.dataset.pwdOriginalType) input.dataset.pwdOriginalType = input.type;
     const willShow = input.type === 'password';
     input.type = willShow ? 'text' : 'password';
     btn.setAttribute('aria-pressed', String(willShow));
     btn.setAttribute('aria-label', willShow ? 'ซ่อนรหัสผ่าน' : 'แสดงรหัสผ่าน');
     btn.classList.toggle('is-visible', willShow);
   });
 });

 // Logout
 document.getElementById('btn-logout')?.addEventListener('click', doLogout);

 // v10.0.x — P0-1 · BFCache / Back-button logout bypass guard
 // เดิม: user กด Logout → doLogout() ล้าง localStorage + redirect ไป / · แต่กด "← Back"
 //       browser restore /app จาก bfcache (DOM + JS memory cached) → user เห็นหน้า dashboard
 //       เก่า · API ติด 401 แต่ UI ไม่ kick ออก = ผีดิบกลับหลุม
 // Fix: ทุกครั้งที่หน้า restore (pageshow event.persisted=true) re-verify token จาก localStorage
 //      · ถ้าไม่มี token → force reload ไปหน้า landing ทันที (bfcache fail-safe)
 window.addEventListener('pageshow', (event) => {
  if (event.persisted) {
   const tok = (function () { try { return localStorage.getItem('pdb_token'); } catch (_) { return null; } })();
   if (!tok) {
    // Token cleared (logout happened) แต่ DOM ค้าง · force navigation ไป landing
    console.log('[auth] bfcache restore detected · no token · forcing logout');
    window.location.replace('/');
   }
  }
 });

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
