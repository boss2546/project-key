/**
 * Personal Data Bank (PDB) v6.1.0 — Frontend Logic
 * Multi-User Knowledge Workspace + PDB Connector Layer
 */

// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════
const state = {
 currentPage: 'my-data',
 graphMode: 'global', // global | local
 localNodeId: null,
 graphData: { nodes: [], edges: [] },
 simulation: null,
 selectedNodeId: null,
 filters: {
 source_file: true, entity: true, tag: true,
 project: true, context_pack: true, person: true,
 },
 knowledgeTab: 'collections',
 // v4 — MCP state
 mcpInfo: null,
 mcpLastToken: null,
 // v5.0 — Auth state
 authToken: localStorage.getItem('projectkey_token') || null,
 currentUser: JSON.parse(localStorage.getItem('projectkey_user') || 'null'),
};

// ═══════════════════════════════════════════
// AUTH — v5.0
// ═══════════════════════════════════════════

/** Wrapper for fetch() that adds JWT auth header */
async function authFetch(url, options = {}) {
 if (!options.headers) options.headers = {};
 if (state.authToken) {
 options.headers['Authorization'] = `Bearer ${state.authToken}`;
 }
 let res;
 try {
 res = await fetch(url, options);
 } catch (err) {
 // Network error — server down or no internet
 hideLoadingOverlay();
 showToast(getLang() === 'th' ? ' ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่' : ' Cannot connect to server. Please try again.', 'error');
 throw err;
 }
 if (res.status === 401) {
 // Token expired or invalid — logout with message
 hideLoadingOverlay();
 doLogout();
 showToast(getLang() === 'th' ? ' เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่' : ' Session expired. Please log in again.', 'error');
 throw new Error('Session expired');
 }
 return res;
}

// ═══════════════════════════════════════════
// UPGRADE MODAL — v5.9.3 Quota CTA
// ═══════════════════════════════════════════
function showUpgradeModal(message) {
 // Remove existing modal if any
 document.getElementById('upgrade-modal-overlay')?.remove();
 const overlay = document.createElement('div');
 overlay.id = 'upgrade-modal-overlay';
 overlay.className = 'upgrade-modal-overlay';
 overlay.innerHTML = `
 <div class="upgrade-modal">
 <div class="upgrade-modal-icon"></div>
 <h3 class="upgrade-modal-title">${getLang() === 'th' ? 'อัปเกรดแพลนของคุณ' : 'Upgrade Your Plan'}</h3>
 <p class="upgrade-modal-message">${message}</p>
 <div class="upgrade-modal-actions">
 <button class="btn btn-primary upgrade-modal-btn" onclick="window.location.href='/pricing'">
 ${getLang() === 'th' ? 'ดูแพลน Starter — ฿99/เดือน' : 'View Starter Plan — ฿99/mo'}
 </button>
 <button class="btn btn-outline upgrade-modal-dismiss" onclick="this.closest('.upgrade-modal-overlay').remove()">
 ${getLang() === 'th' ? 'ไว้ทีหลัง' : 'Maybe Later'}
 </button>
 </div>
 </div>
 `;
 overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
 document.body.appendChild(overlay);
}

// ═══════════════════════════════════════════
// LOADING OVERLAY — v5.1 Premium animations
// ═══════════════════════════════════════════

let _loadingOverlayEl = null;
let _loadingTimer = null;
let _loadingStartTime = 0;
let _loadingSafetyTimeout = null;

function showLoadingOverlay(message = 'Loading...', type = 'default') {
 _loadingStartTime = Date.now();
 
 // Remove existing
 if (_loadingOverlayEl) _loadingOverlayEl.remove();
 if (_loadingTimer) clearInterval(_loadingTimer);
 if (_loadingSafetyTimeout) clearTimeout(_loadingSafetyTimeout);
 
 const icons = {
 upload: `<svg class="loading-icon upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>`,
 ai: `<div class="loading-icon ai-brain">
 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
 <path d="M12 2a7 7 0 017 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 01-2 2h-4a2 2 0 01-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 017-7z"/>
 <line x1="9" y1="22" x2="15" y2="22"/><line x1="10" y1="2" x2="10" y2="7"/><line x1="14" y1="2" x2="14" y2="7"/>
 </svg>
 </div>`,
 default: `<div class="loading-icon default-spinner"></div>`,
 };

 const overlay = document.createElement('div');
 overlay.className = 'loading-overlay';
 overlay.innerHTML = `
 <div class="loading-overlay-card">
 ${icons[type] || icons.default}
 <div class="loading-message">${message.replace(/\\n/g, '<br>')}</div>
 <div class="loading-progress-bar"><div class="loading-progress-fill"></div></div>
 <div class="loading-elapsed">0s</div>
 </div>
 `;
 document.body.appendChild(overlay);
 _loadingOverlayEl = overlay;

 // Animate in
 requestAnimationFrame(() => overlay.classList.add('visible'));

 // Update elapsed time
 _loadingTimer = setInterval(() => {
 const elapsed = Math.floor((Date.now() - _loadingStartTime) / 1000);
 const elapsedEl = overlay.querySelector('.loading-elapsed');
 if (elapsedEl) elapsedEl.textContent = `${elapsed}s`;
 }, 1000);

 // Safety timeout — auto-dismiss after 3 minutes to prevent stuck overlay
 _loadingSafetyTimeout = setTimeout(() => {
 hideLoadingOverlay();
 showToast(getLang() === 'th' ? '⏱ หมดเวลา — กรุณาลองใหม่' : '⏱ Timed out — please try again', 'error');
 }, 180000);
}

function hideLoadingOverlay() {
 if (_loadingTimer) { clearInterval(_loadingTimer); _loadingTimer = null; }
 if (_loadingSafetyTimeout) { clearTimeout(_loadingSafetyTimeout); _loadingSafetyTimeout = null; }
 if (_loadingOverlayEl) {
 _loadingOverlayEl.classList.add('fade-out');
 setTimeout(() => { _loadingOverlayEl?.remove(); _loadingOverlayEl = null; }, 300);
 }
}

// ═══════════════════════════════════════════

function showLanding() {
 document.getElementById('landing-page').classList.remove('hidden');
 document.getElementById('app').classList.add('hidden');
 document.getElementById('auth-modal').classList.add('hidden');
 document.body.classList.add('show-landing');
}

function showApp() {
 document.getElementById('landing-page').classList.add('hidden');
 document.getElementById('app').classList.remove('hidden');
 document.body.classList.remove('show-landing');
 // Update sidebar user info
 const emailEl = document.getElementById('sidebar-user-email');
 if (emailEl && state.currentUser) {
 emailEl.textContent = state.currentUser.email || '';
 }
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
 localStorage.setItem('projectkey_token', data.token);
 localStorage.setItem('projectkey_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 showApp();
 initAppData();
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
 localStorage.setItem('projectkey_token', data.token);
 localStorage.setItem('projectkey_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 // Redirect to pricing page immediately after registration
 window.location.href = '/pricing?welcome=1';
 return; // stop here — don't showApp/initAppData
 } catch (e) {
 errorEl.textContent = 'Connection error';
 errorEl.classList.remove('hidden');
 }
}

function doLogout() {
 state.authToken = null;
 state.currentUser = null;
 localStorage.removeItem('projectkey_token');
 localStorage.removeItem('projectkey_user');
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
 errorEl.textContent = data.detail || 'ไม่พบบัญชีนี้';
 errorEl.classList.remove('hidden');
 return;
 }
 // Save reset token and move to reset form
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
 localStorage.setItem('projectkey_token', data.token);
 localStorage.setItem('projectkey_user', JSON.stringify(data.user));
 document.getElementById('auth-modal').classList.add('hidden');
 showToast(' เปลี่ยนรหัสผ่านสำเร็จ!', 'success');
 _resetToken = null;
 showApp();
 initAppData();
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
 // Verify token is still valid
 fetch('/api/auth/me', { headers: { 'Authorization': `Bearer ${state.authToken}` } })
 .then(r => {
 if (r.ok) { showApp(); initAppData(); }
 else { doLogout(); }
 })
 .catch(() => doLogout());
 } else {
 showLanding();
 }
}

function initAppData() {
 loadStats();
 loadFiles();
 loadBillingInfo();
 loadUsageInfo();
 initGuideSystem();
 initBilling();
 setTimeout(detectOnboardingProgress, 3000);
 maybeShowRebrandNotice();
 // v7.0 — BYOS Storage Mode (loads Drive status for profile modal)
 if (typeof initStorageMode === 'function') initStorageMode();
}

// แสดง toast แจ้ง rebrand ครั้งเดียวต่อ browser (v6.1.0)
// เหตุผล: user เก่าที่จำชื่อเดิมจะได้รู้ว่าเปลี่ยนชื่อ + Claude Desktop config เดิมยังใช้ได้
function maybeShowRebrandNotice() {
 const REBRAND_NOTICE_KEY = 'pdb_rebrand_notice_seen';
 if (localStorage.getItem(REBRAND_NOTICE_KEY)) return;
 if (!state.currentUser) return;
 const msg = getLang() === 'th'
 ? 'เราเปลี่ยนชื่อเป็น "Personal Data Bank" แล้ว — ฟีเจอร์เดิมและ Claude Desktop config ของคุณยังใช้งานได้ปกติ'
 : 'We rebranded to "Personal Data Bank" — all features and your existing Claude Desktop config still work as before';
 showToast(msg, 'info');
 localStorage.setItem(REBRAND_NOTICE_KEY, '1');
}

// ═══════════════════════════════════════════
// USAGE DISPLAY — v5.9.3
// ═══════════════════════════════════════════
async function loadUsageInfo() {
 try {
 const res = await authFetch('/api/usage');
 if (!res.ok) return;
 const data = await res.json();
 window._usageData = data;
 renderUsageBars(data);
 updateUploadHint(data);
 updateSidebarStats(data);
 } catch (e) { console.error('Usage load error:', e); }
}

function renderUsageBars(data) {
 const container = document.getElementById('usage-bars-container');
 if (!container) return;
 const u = data.usage;
 const isTh = getLang() === 'th';

 const bars = [
 { label: isTh ? 'ไฟล์' : 'Files', used: u.files.used, limit: u.files.limit, icon: '' },
 { label: isTh ? 'พื้นที่' : 'Storage', used: u.storage_mb.used, limit: u.storage_mb.limit, unit: 'MB', icon: '' },
 { label: 'Context Packs', used: u.context_packs.used, limit: u.context_packs.limit, icon: '' },
 { label: isTh ? 'สรุป AI / เดือน' : 'AI Summary / mo', used: u.ai_summaries.used, limit: u.ai_summaries.limit, icon: '' },
 { label: isTh ? 'Export / เดือน' : 'Export / mo', used: u.exports.used, limit: u.exports.limit, icon: '' },
 ];

 container.innerHTML = bars.map(b => {
 const pct = b.limit > 0 ? Math.min(100, Math.round((b.used / b.limit) * 100)) : 0;
 const full = pct >= 100;
 const warn = pct >= 80;
 const unit = b.unit || '';
 const color = full ? '#ef4444' : warn ? '#f59e0b' : '#818cf8';
 return `<div class="usage-bar-row">
 <div class="usage-bar-label"><span>${b.icon} ${b.label}</span><span class="usage-bar-count" style="color:${color}">${b.used}${unit}/${b.limit}${unit}</span></div>
 <div class="usage-bar-track"><div class="usage-bar-fill" style="width:${pct}%;background:${color}"></div></div>
 </div>`;
 }).join('');

 // Show plan badge
 const planEl = document.getElementById('usage-plan-label');
 if (planEl) planEl.textContent = data.plan === 'starter' ? ' Starter' : '🆓 Free';
}

function updateUploadHint(data) {
 const maxMB = data.limits.max_file_size_mb || 20;
 const types = Array.isArray(data.limits.allowed_file_types)
 ? data.limits.allowed_file_types.map(t => t.toUpperCase()).join(', ')
 : 'PDF, TXT, MD, DOCX';
 const isTh = getLang() === 'th';
 const hint = isTh
 ? `รองรับ ${types} (สูงสุด ${maxMB} MB)`
 : `Supports ${types} (max ${maxMB} MB)`;
 const el = document.getElementById('upload-hint');
 if (el) el.textContent = hint;

 // v5.9.3 — Sensitive data warning
 const warnEl = document.getElementById('upload-sensitive-warning');
 if (!warnEl) {
 const parent = el?.parentElement;
 if (parent) {
 const warn = document.createElement('div');
 warn.id = 'upload-sensitive-warning';
 warn.className = 'upload-sensitive-warning';
 warn.innerHTML = isTh
 ? ' กรุณาอย่าอัปโหลดข้อมูลส่วนบุคคลที่อ่อนไหว เช่น บัตรประชาชน, หนังสือเดินทาง, ข้อมูลทางการเงิน หรือเวชระเบียน'
 : ' Please do not upload sensitive data such as ID cards, passports, financial statements, or medical records';
 parent.appendChild(warn);
 }
 }
}

function updateSidebarStats(data) {
 const u = data.usage;
 const el = (id) => document.getElementById(id);
 if (el('stat-files')) el('stat-files').textContent = `${u.files.used}/${u.files.limit}`;
 if (el('stat-packs')) el('stat-packs').textContent = `${u.context_packs.used}/${u.context_packs.limit}`;
}

// ═══════════════════════════════════════════
// BILLING — v5.9.2
// ═══════════════════════════════════════════

function initBilling() {
 document.getElementById('btn-upgrade-starter')?.addEventListener('click', () => window.location.href = '/pricing');
 document.getElementById('btn-manage-billing')?.addEventListener('click', doOpenPortal);
 // Plan modal buttons
 document.getElementById('close-plan-modal')?.addEventListener('click', closePlanModal);
 document.getElementById('btn-plan-free')?.addEventListener('click', closePlanModal);
 document.getElementById('btn-plan-starter')?.addEventListener('click', () => { closePlanModal(); doStarterCheckout(); });
 // Close on overlay click
 document.getElementById('plan-modal')?.addEventListener('click', (e) => {
 if (e.target.id === 'plan-modal') closePlanModal();
 });
}

function showPlanModal() {
 document.getElementById('plan-modal')?.classList.remove('hidden');
}

function closePlanModal() {
 document.getElementById('plan-modal')?.classList.add('hidden');
}

async function loadBillingInfo() {
 try {
 const res = await authFetch('/api/billing/info');
 if (!res.ok) return;
 const info = await res.json();
 updateBillingUI(info);
 } catch (e) {
 // Silently fail — billing info is non-critical
 }
}

function updateBillingUI(info) {
 const badge = document.getElementById('billing-plan-badge');
 const name = document.getElementById('billing-plan-name');
 const detail = document.getElementById('billing-plan-detail');
 const upgradeBtn = document.getElementById('btn-upgrade-starter');
 const manageBtn = document.getElementById('btn-manage-billing');
 if (!badge) return;

 const isFree = info.plan === 'free';
 const isStarter = info.subscription_status === 'starter_active';
 const isPastDue = info.subscription_status === 'starter_past_due';
 const isCanceled = info.cancel_at_period_end;

 // Badge
 badge.textContent = isFree ? 'Free' : 'Starter';
 badge.className = 'billing-plan-badge ' + (isFree ? 'badge-free' : 'badge-starter');
 name.textContent = 'Personal AI Context';

 // Detail text
 if (isFree) {
 detail.textContent = getLang() === 'th' ? 'แพลนปัจจุบัน: Free — อัปเกรดเพื่อปลดล็อกฟีเจอร์เพิ่ม' : 'Current plan: Free — Upgrade to unlock more features';
 } else if (isPastDue) {
 detail.textContent = getLang() === 'th' ? ' การชำระเงินมีปัญหา — กรุณาอัปเดตวิธีการชำระเงิน' : ' Payment issue — please update your payment method';
 detail.style.color = '#f59e0b';
 } else if (isCanceled) {
 const endDate = info.current_period_end ? new Date(info.current_period_end).toLocaleDateString('th-TH') : '';
 detail.textContent = getLang() === 'th' ? ' Starter (ยกเลิกแล้ว — ใช้ได้ถึง ' + endDate + ')' : ' Starter (cancelled — active until ' + endDate + ')';
 detail.style.color = '#f59e0b';
 } else if (isStarter) {
 const endDate = info.current_period_end ? new Date(info.current_period_end).toLocaleDateString('th-TH') : '';
 detail.textContent = getLang() === 'th' ? ' Starter — ต่ออายุ: ' + endDate : ' Starter — renews: ' + endDate;
 detail.style.color = '#818cf8';
 }

 // Buttons
 if (isFree) {
 upgradeBtn.style.display = 'inline-flex';
 manageBtn.style.display = info.has_stripe_customer ? 'inline-flex' : 'none';
 } else {
 upgradeBtn.style.display = 'none';
 manageBtn.style.display = 'inline-flex';
 manageBtn.textContent = getLang() === 'th' ? 'จัดการการชำระเงิน' : 'Manage Billing';
 }
}

async function doStarterCheckout() {
 try {
 showLoadingOverlay(getLang() === 'th' ? 'กำลังเปิด Stripe Checkout...' : 'Opening Stripe Checkout...', 'default');
 const res = await authFetch('/api/billing/create-checkout-session', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ plan: 'starter' }),
 });
 const data = await res.json();
 hideLoadingOverlay();
 if (!res.ok) {
 showToast(data.detail || 'Checkout failed', 'error');
 return;
 }
 // Redirect to Stripe Checkout
 window.location.href = data.checkout_url;
 } catch (e) {
 hideLoadingOverlay();
 showToast(getLang() === 'th' ? ' ไม่สามารถเปิดหน้าชำระเงินได้' : ' Could not open checkout', 'error');
 }
}

async function doOpenPortal() {
 try {
 showLoadingOverlay(getLang() === 'th' ? 'กำลังเปิดหน้าจัดการ...' : 'Opening billing portal...', 'default');
 const res = await authFetch('/api/billing/create-portal-session', { method: 'POST' });
 const data = await res.json();
 hideLoadingOverlay();
 if (!res.ok) {
 showToast(data.detail || 'Portal failed', 'error');
 return;
 }
 window.location.href = data.portal_url;
 } catch (e) {
 hideLoadingOverlay();
 showToast(getLang() === 'th' ? ' ไม่สามารถเปิดหน้าจัดการได้' : ' Could not open portal', 'error');
 }
}

// Check for billing success/cancelled on page load
function checkBillingRedirect() {
 const path = window.location.pathname;
 if (path === '/billing/success') {
 showToast(getLang() === 'th' ? ' อัปเกรดสำเร็จ! ยินดีต้อนรับสู่ Starter plan' : ' Upgrade successful! Welcome to Starter plan', 'success');
 // Clean URL
 window.history.replaceState({}, '', '/');
 // Reload billing info
 setTimeout(loadBillingInfo, 1000);
 } else if (path === '/billing/cancelled') {
 showToast(getLang() === 'th' ? 'ยกเลิกการชำระเงิน — คุณยังอยู่แพลน Free' : 'Payment cancelled — you are still on Free plan', 'info');
 window.history.replaceState({}, '', '/');
 }
}

// Node family color map
const NODE_COLORS = {
 source_file: '#ffd54f', entity: '#ff8a65', tag: '#4fc3f7',
 project: '#81c784', context_pack: '#4dd0e1', person: '#b39ddb',
 note: '#aed581', cluster: '#81c784',
};

// ═══════════════════════════════════════════
// i18n — BILINGUAL SYSTEM (TH / EN)
// ═══════════════════════════════════════════
const I18N = {
 th: {
 // Navigation
 'nav.myData': 'ข้อมูลของฉัน',
 'nav.knowledge': 'มุมมองความรู้',
 'nav.graph': 'กราฟ',
 'nav.chat': 'AI แชท',
 'nav.profile': 'โปรไฟล์',
 'nav.connectorSection': 'Connector',
 'nav.mcpSetup': 'ตั้งค่า MCP',
 'nav.tokens': 'โทเค็น',
 'nav.mcpLogs': 'บันทึกการใช้งาน',

 // Stats
 'stat.files': 'ไฟล์',
 'stat.collections': 'คอลเลกชัน',
 'stat.nodes': 'โหนด',
 'stat.relations': 'ความสัมพันธ์',
 'stat.packs': 'แพ็ก',
 'stat.tokens': 'โทเค็น',

 // My Data page
 'myData.title': 'ข้อมูลของฉัน',
 'myData.subtitle': 'พื้นที่ข้อมูลส่วนตัวของคุณ',
 'myData.organizeAll': 'จัดระเบียบทั้งหมด',
 'myData.organizeNew': 'จัดระเบียบไฟล์ใหม่',
 'myData.uploadText': 'ลากไฟล์มาวาง หรือ คลิกเพื่อเลือกไฟล์',
 'myData.uploadHint': 'รองรับ PDF, TXT, MD, DOCX (สูงสุด 20 MB)',
 'myData.allFiles': 'ไฟล์ทั้งหมด',
 'myData.noFiles': 'ยังไม่มีไฟล์ — เพิ่มไฟล์เข้าพื้นที่ส่วนตัวของคุณ',
 'myData.delete': 'ลบ',

 // Knowledge page
 'knowledge.title': 'มุมมองความรู้',
 'knowledge.subtitle': 'ข้อมูลที่ถูกจัดเป็นระบบความรู้แล้ว',
 'knowledge.collections': 'Collections',
 'knowledge.notes': 'Notes & สรุป',
 'knowledge.packs': 'Context Packs',
 'knowledge.emptyCollections': 'ยังไม่มี Collections — จัดระเบียบไฟล์ก่อน',
 'knowledge.emptyPacks': 'ยังไม่มี Context Packs',
 'knowledge.emptyNotes': 'ยังไม่มี Notes & Entities — สร้างกราฟก่อน',
 'knowledge.loadFailed': 'โหลดข้อมูลล้มเหลว',
 'knowledge.organize': 'จัดระเบียบไฟล์ก่อนเพื่อสร้างระบบความรู้',

 // Graph page
 'graph.globalTitle': 'Global Graph',
 'graph.globalSubtitle': 'มุมมองความเชื่อมโยงภาพรวม',
 'graph.localTitle': 'Local Graph',
 'graph.localSubtitle': 'มุมมองแบบเฉพาะจุด',
 'graph.searchPlaceholder': 'ค้นหา node...',
 'graph.filterFile': 'ไฟล์',
 'graph.rebuild': 'สร้างกราฟใหม่',
 'graph.emptyTitle': 'ยังไม่มี Knowledge Graph',
 'graph.emptyHint': 'จัดระเบียบไฟล์ก่อนเพื่อสร้างกราฟ',
 'graph.selectLocal': 'เลือก node จาก Global Graph ก่อน',

 // Detail panel
 'detail.summary': 'สรุป',
 'detail.metadata': 'Metadata',
 'detail.relations': 'ความสัมพันธ์',
 'detail.showLocal': 'แสดงกราฟเฉพาะจุด',
 'detail.askAi': 'ถาม AI เกี่ยวกับสิ่งนี้',
 'detail.noSummary': 'ไม่มีสรุป',

 // Chat page
 'chat.title': 'AI แชท',
 'chat.subtitle': 'AI ใช้ข้อมูล ความสัมพันธ์ และบริบทของคุณในการตอบ',
 'chat.welcome': 'สวัสดี! ถามอะไรก็ได้เกี่ยวกับข้อมูลของคุณ',
 'chat.welcomeSub': 'AI จะใช้ Profile, Context Packs, Files, และ Knowledge Graph ในการตอบ',
 'chat.placeholder': 'ถามเกี่ยวกับข้อมูลของคุณ...',
 'chat.profileNotSet': 'ยังไม่ตั้งค่า',
 'chat.profileActive': 'เปิดใช้งาน',

 // Sources panel
 'sources.title': 'หลักฐานที่ใช้',
 'sources.profile': ' โปรไฟล์',
 'sources.packs': ' Context Packs',
 'sources.files': ' ไฟล์ที่ใช้',
 'sources.graph': ' Nodes & Edges',
 'sources.reasoning': ' เหตุผลในการเลือก',
 'sources.evidence': ' Evidence Graph',

 // Profile modal
 'profile.title': ' โปรไฟล์ของฉัน',
 'profile.identity': 'ฉันเป็นใคร',
 'profile.goals': 'เป้าหมายของฉัน',
 'profile.style': 'สไตล์การทำงาน',
 'profile.output': 'ต้องการคำตอบแบบไหน',
 'profile.background': 'บริบทสำคัญ',
 'profile.save': 'บันทึกโปรไฟล์',
 'profile.identityPh': 'เช่น นักศึกษาปริญญาโท สาขาวิทยาศาสตร์...',
 'profile.goalsPh': 'เช่น ทำวิจัยเกี่ยวกับ...',
 'profile.stylePh': 'เช่น ชอบข้อมูลที่เป็นระบบ...',
 'profile.outputPh': 'เช่น สรุปสั้นๆ ตรงประเด็น...',
 'profile.backgroundPh': 'เช่น กำลังทำโปรเจกต์...',
 // v6.0 — Personality
 'personality.title': 'บุคลิกภาพ',
 'personality.optional': '(ไม่บังคับ)',
 'personality.pdpa': ' ลิงก์ "ทำที่..." จะพาคุณไปยังเว็บไซต์ภายนอก — โปรดดูนโยบายความเป็นส่วนตัวของเว็บนั้นๆ',
 'personality.history': 'ประวัติ',
 'personality.viewHistory': 'ดูประวัติการอัปเดต',
 'personality.notSet': 'ไม่ระบุ',
 'personality.mbti.type': 'ประเภท',
 'personality.mbti.identity': 'Identity',
 'personality.mbti.identityHint': 'สำหรับ NERIS เท่านั้น',
 'personality.mbti.source': 'ที่มาของผล',
 'personality.mbti.selfReport': 'ฉันเดาเอง',
 'personality.enneagram.core': 'Core',
 'personality.enneagram.wing': 'Wing',
 'personality.enneagram.wingHint': 'เลือก Core ก่อน',

 // Confirm modal
 'confirm.cancel': 'ยกเลิก',
 'confirm.ok': 'ยืนยัน',

 // Toasts / dynamic
 'toast.uploaded': 'อัปโหลดเรียบร้อย',
 'toast.deleted': 'ลบเรียบร้อย',
 'toast.profileSaved': 'บันทึกโปรไฟล์เรียบร้อย',
 'toast.organized': 'จัดระเบียบเรียบร้อย',
 'toast.organizedNew': 'จัดระเบียบไฟล์ใหม่เรียบร้อย',
 'toast.noNewFiles': 'ไม่มีไฟล์ใหม่ที่ต้องจัดระเบียบ',
 'toast.graphBuilt': 'สร้างกราฟเรียบร้อย',
 'toast.error': 'เกิดข้อผิดพลาด',
 'toast.tokenGenerated': 'สร้าง Token เรียบร้อย',
 'toast.tokenRevoked': 'ยกเลิก Token เรียบร้อย',
 'toast.copied': 'คัดลอกแล้ว',
 'toast.testSuccess': 'เชื่อมต่อสำเร็จ!',
 'toast.testFailed': 'เชื่อมต่อล้มเหลว',

 // MCP Setup page
 'mcp.setupTitle': 'ตั้งค่าตัวเชื่อมต่อ Claude',
 'mcp.setupSubtitle': 'เชื่อมต่อข้อมูล Personal Data Bank ของคุณไปยัง Claude ผ่าน Remote MCP',
 'mcp.notConfigured': 'ยังไม่ได้ตั้งค่า',
 'mcp.configured': 'เชื่อมต่อแล้ว',
 'mcp.noActiveToken': 'ยังไม่มี Token ที่เปิดใช้งาน',
 'mcp.step1Title': 'Connector URL (มี Key ในตัว)',
 'mcp.step1Desc': 'คัดลอก URL นี้ไปวางใน Claude — URL มี Secret Key ฝังอยู่แล้ว',
 'mcp.step2Title': 'สร้าง Access Token',
 'mcp.step2Desc': 'สร้าง Bearer token สำหรับ REST API',
 'mcp.step3Title': 'ตั้งค่าใน AI Client',
 'mcp.step3Desc': 'เลือกแพลตฟอร์มแล้วคัดลอก config',
 'mcp.antigravityDesc': 'เพิ่มในไฟล์ mcp_config.json (ใช้ mcp-remote bridge)',
 'mcp.step4Title': 'ทดสอบการเชื่อมต่อ',
 'mcp.step4Desc': 'ตรวจสอบว่า connector ทำงานถูกต้อง',
 'mcp.generateToken': 'สร้าง Token',
 'mcp.tokenWarning': 'บันทึก token นี้ตอนนี้ — จะไม่แสดงอีกครั้ง',
 'mcp.testConnection': 'ทดสอบการเชื่อมต่อ',
 'mcp.availableTools': 'เครื่องมือทั้งหมด',
 'mcp.scope': 'อ่าน+เขียน',
 'mcp.toolEnabled': 'เปิดใช้งาน',
 'mcp.toolDisabled': 'ปิดใช้งาน',
 // Tool descriptions (Thai)
 'tool.get_profile': 'ดูโปรไฟล์ผู้ใช้ รวมถึงตัวตน เป้าหมาย สไตล์การทำงาน และความชอบ',
 'tool.list_files': 'แสดงรายการไฟล์ทั้งหมดในฐานความรู้ พร้อมข้อมูล แท็ก และสรุปย่อ',
 'tool.get_file_content': 'ดูเนื้อหาข้อความของไฟล์ (สูงสุด 5000 ตัวอักษร)',
 'tool.get_file_summary': 'ดูสรุปที่ AI สร้าง หัวข้อหลัก และข้อเท็จจริงสำคัญของไฟล์',
 'tool.list_collections': 'แสดงคอลเลกชันที่ AI จัดกลุ่ม พร้อมไฟล์และสรุป',
 'tool.list_context_packs': 'แสดงรายการ Context Pack (กลุ่มความรู้ที่สกัดแล้ว)',
 'tool.get_context_pack': 'ดู Context Pack ตาม ID พร้อมเนื้อหาทั้งหมด',
 'tool.search_knowledge': 'ค้นหาฐานความรู้แบบ Semantic + Keyword ผสม ได้ไฟล์ แพ็ก และโหนดกราฟ',
 'tool.explore_graph': 'สำรวจกราฟความรู้ ดูภาพรวมโหนดทั้งหมด หรือดูความเชื่อมโยงของโหนดเฉพาะ',
 'tool.get_overview': 'ดูภาพรวมระบบ จำนวนไฟล์ คอลเลกชัน แพ็ก โหนด และเส้นเชื่อม',
 'tool.create_context_pack': 'สร้าง Context Pack ใหม่จากไฟล์ที่เลือก ประเภท: profile, study, work, project',
 'tool.add_note': 'อัพเดทสรุปของไฟล์ ใช้เพิ่มโน้ตหรือปรับปรุงสรุปที่ AI สร้าง',
 'tool.update_file_tags': 'อัพเดทแท็กของไฟล์ ใช้จัดระเบียบและจำแนกหมวดหมู่',
 'tool.upload_text': 'อัพโหลดข้อความเป็นไฟล์ใหม่ (Claude สามารถสร้างไฟล์ความรู้ได้)',
 'tool.update_profile': 'อัพเดทโปรไฟล์ผู้ใช้ (ตัวตน เป้าหมาย สไตล์ ความชอบ)',
 'tool.delete_file': 'ลบไฟล์และข้อมูลที่เกี่ยวข้องทั้งหมด (สรุป ข้อมูลเชิงลึก คลัสเตอร์)',
 'tool.delete_pack': 'ลบ Context Pack',
 'tool.run_organize': 'รันไปป์ไลน์ AI แบบเต็ม: สรุป จัดกลุ่ม สร้างกราฟ',
 'tool.build_graph': 'สร้างกราฟความรู้ใหม่จากข้อมูลทั้งหมด',
 'tool.enrich_metadata': 'รัน AI เสริมข้อมูลเมตา (แท็ก ความละเอียดอ่อน ความสด)',
 'tool.admin_login': 'ยืนยันรหัสผ่านแอดมิน เพื่อเข้าถึงเครื่องมือที่ปิดอยู่',

 // Token Management page
 'tokens.title': 'จัดการ Token',
 'tokens.subtitle': 'จัดการ access tokens สำหรับ AI connectors ภายนอก',
 'tokens.newToken': 'สร้าง Token ใหม่',
 'tokens.empty': 'ยังไม่มี token — สร้างได้จากหน้า MCP Setup',
 'tokens.revoke': 'ยกเลิก',
 'tokens.active': 'ใช้งาน',
 'tokens.revoked': 'ยกเลิกแล้ว',
 'tokens.created': 'สร้างเมื่อ',
 'tokens.lastUsed': 'ใช้ล่าสุด',
 'tokens.never': 'ยังไม่เคยใช้',
 'tokens.confirmRevoke': 'ต้องการยกเลิก token นี้?',

 // MCP Logs page
 'logs.title': 'บันทึก MCP',
 'logs.subtitle': 'ติดตามการใช้งาน connector และแก้ไขปัญหา',
 'logs.allTools': 'ทุกเครื่องมือ',
 'logs.allStatus': 'ทุกสถานะ',
 'logs.refresh': 'รีเฟรช',
 'logs.colTime': 'เวลา',
 'logs.colTool': 'เครื่องมือ',
 'logs.colStatus': 'สถานะ',
 'logs.colLatency': 'เวลาตอบ',
 'logs.colDetails': 'รายละเอียด',
 'logs.empty': 'ยังไม่มีบันทึก — การใช้งาน connector จะแสดงที่นี่',
 },

 en: {
 // Navigation
 'nav.myData': 'My Data',
 'nav.knowledge': 'Knowledge View',
 'nav.graph': 'Graph',
 'nav.chat': 'AI Chat',
 'nav.profile': 'My Profile',
 'nav.connectorSection': 'Connector',
 'nav.mcpSetup': 'MCP Setup',
 'nav.tokens': 'Tokens',
 'nav.mcpLogs': 'MCP Logs',

 // Stats
 'stat.files': 'Files',
 'stat.collections': 'Collections',
 'stat.nodes': 'Nodes',
 'stat.relations': 'Relations',
 'stat.packs': 'Packs',
 'stat.tokens': 'Tokens',

 // My Data page
 'myData.title': 'My Data',
 'myData.subtitle': 'Your personal data space',
 'myData.organizeAll': 'Organize All',
 'myData.organizeNew': 'Organize New Files',
 'myData.uploadText': 'Drag files here or click to select',
 'myData.uploadHint': 'Supports PDF, TXT, MD, DOCX (max 20 MB)',
 'myData.allFiles': 'All Files',
 'myData.noFiles': 'No files yet — add files to your personal space',
 'myData.delete': 'Delete',

 // Knowledge page
 'knowledge.title': 'Knowledge View',
 'knowledge.subtitle': 'Your organized knowledge system',
 'knowledge.collections': 'Collections',
 'knowledge.notes': 'Notes & Summaries',
 'knowledge.packs': 'Context Packs',
 'knowledge.emptyCollections': 'No Collections yet — organize files first',
 'knowledge.emptyPacks': 'No Context Packs yet',
 'knowledge.emptyNotes': 'No Notes & Entities — build graph first',
 'knowledge.loadFailed': 'Failed to load data',
 'knowledge.organize': 'Organize files first to build knowledge system',

 // Graph page
 'graph.globalTitle': 'Global Graph',
 'graph.globalSubtitle': 'Overview of all connections',
 'graph.localTitle': 'Local Graph',
 'graph.localSubtitle': 'Node-focused neighborhood view',
 'graph.searchPlaceholder': 'Search nodes...',
 'graph.filterFile': 'File',
 'graph.rebuild': 'Rebuild Graph',
 'graph.emptyTitle': 'No Knowledge Graph yet',
 'graph.emptyHint': 'Organize files first to build graph',
 'graph.selectLocal': 'Select a node from Global Graph first',

 // Detail panel
 'detail.summary': 'Summary',
 'detail.metadata': 'Metadata',
 'detail.relations': 'Relations',
 'detail.showLocal': 'Show Local Graph',
 'detail.askAi': 'Ask AI about this',
 'detail.noSummary': 'No summary',

 // Chat page
 'chat.title': 'AI Chat',
 'chat.subtitle': 'AI uses your data, relations, and context to respond',
 'chat.welcome': 'Hi! Ask anything about your data',
 'chat.welcomeSub': 'AI uses Profile, Context Packs, Files, and Knowledge Graph to answer',
 'chat.placeholder': 'Ask about your data...',
 'chat.profileNotSet': 'Not set',
 'chat.profileActive': 'Active',

 // Sources panel
 'sources.title': 'Evidence Used',
 'sources.profile': ' Profile',
 'sources.packs': ' Context Packs',
 'sources.files': ' Files Used',
 'sources.graph': ' Nodes & Edges',
 'sources.reasoning': ' Reasoning',
 'sources.evidence': ' Evidence Graph',

 // Profile modal
 'profile.title': ' My Profile',
 'profile.identity': 'Who am I',
 'profile.goals': 'My Goals',
 'profile.style': 'Work Style',
 'profile.output': 'Answer Preference',
 'profile.background': 'Important Context',
 'profile.save': 'Save Profile',
 'profile.identityPh': 'e.g. Graduate student in Science...',
 'profile.goalsPh': 'e.g. Researching about...',
 'profile.stylePh': 'e.g. Prefer structured data...',
 'profile.outputPh': 'e.g. Short and to the point...',
 'profile.backgroundPh': 'e.g. Working on a project...',
 // v6.0 — Personality
 'personality.title': 'Personality',
 'personality.optional': '(optional)',
 'personality.pdpa': ' "Take it at..." links will open external sites — please review their privacy policies.',
 'personality.history': 'History',
 'personality.viewHistory': 'View update history',
 'personality.notSet': 'Not set',
 'personality.mbti.type': 'Type',
 'personality.mbti.identity': 'Identity',
 'personality.mbti.identityHint': 'NERIS only',
 'personality.mbti.source': 'Source',
 'personality.mbti.selfReport': 'Self-report',
 'personality.enneagram.core': 'Core',
 'personality.enneagram.wing': 'Wing',
 'personality.enneagram.wingHint': 'Pick Core first',

 // Confirm modal
 'confirm.cancel': 'Cancel',
 'confirm.ok': 'Confirm',

 // Toasts / dynamic
 'toast.uploaded': 'Upload complete',
 'toast.deleted': 'Deleted successfully',
 'toast.profileSaved': 'Profile saved',
 'toast.organized': 'Organization complete',
 'toast.organizedNew': 'New files organized',
 'toast.noNewFiles': 'No new files to organize',
 'toast.graphBuilt': 'Graph built successfully',
 'toast.error': 'An error occurred',
 'toast.tokenGenerated': 'Token generated successfully',
 'toast.tokenRevoked': 'Token revoked',
 'toast.copied': 'Copied to clipboard',
 'toast.testSuccess': 'Connection successful!',
 'toast.testFailed': 'Connection failed',

 // MCP Setup page
 'mcp.setupTitle': 'Claude Connector Setup',
 'mcp.setupSubtitle': 'Connect your Personal Data Bank data to Claude via remote MCP',
 'mcp.notConfigured': 'Not configured',
 'mcp.configured': 'Connected',
 'mcp.noActiveToken': 'No active token',
 'mcp.step1Title': 'Connector URL (Key included)',
 'mcp.step1Desc': 'Copy this URL to Claude — it contains your Secret Key',
 'mcp.step2Title': 'Generate Access Token',
 'mcp.step2Desc': 'Create a Bearer token for REST API access',
 'mcp.step3Title': 'Configure AI Client',
 'mcp.step3Desc': 'Choose your platform and copy the config',
 'mcp.antigravityDesc': 'Add to mcp_config.json (uses mcp-remote bridge)',
 'mcp.step4Title': 'Test Connection',
 'mcp.step4Desc': 'Verify your connector setup is working',
 'mcp.generateToken': 'Generate Token',
 'mcp.tokenWarning': 'Save this token now — it won\'t be shown again',
 'mcp.testConnection': 'Test Connection',
 'mcp.availableTools': 'Available Tools',
 'mcp.scope': 'read+write',
 'mcp.toolEnabled': 'Enabled',
 'mcp.toolDisabled': 'Disabled',

 // Token Management page
 'tokens.title': 'Token Management',
 'tokens.subtitle': 'Manage access tokens for external AI connectors',
 'tokens.newToken': 'New Token',
 'tokens.empty': 'No tokens yet — generate one from MCP Setup',
 'tokens.revoke': 'Revoke',
 'tokens.active': 'Active',
 'tokens.revoked': 'Revoked',
 'tokens.created': 'Created',
 'tokens.lastUsed': 'Last used',
 'tokens.never': 'Never used',
 'tokens.confirmRevoke': 'Revoke this token?',

 // MCP Logs page
 'logs.title': 'MCP Logs',
 'logs.subtitle': 'Track connector tool usage and debug issues',
 'logs.allTools': 'All Tools',
 'logs.allStatus': 'All Status',
 'logs.refresh': 'Refresh',
 'logs.colTime': 'Time',
 'logs.colTool': 'Tool',
 'logs.colStatus': 'Status',
 'logs.colLatency': 'Latency',
 'logs.colDetails': 'Details',
 'logs.empty': 'No logs yet — connector usage will appear here',
 }
};

// Get current language — default TH
function getLang() {
 return localStorage.getItem('projectkey_lang') || 'th';
}

// Get translation string
function t(key) {
 const lang = getLang();
 return I18N[lang]?.[key] || I18N['en']?.[key] || key;
}

// Apply translations to all [data-i18n] elements
function applyLanguage(lang) {
 localStorage.setItem('projectkey_lang', lang);
 document.documentElement.lang = lang;

 // Update all data-i18n elements
 document.querySelectorAll('[data-i18n]').forEach(el => {
 const key = el.getAttribute('data-i18n');
 const translated = I18N[lang]?.[key] || I18N['en']?.[key] || el.textContent;
 el.textContent = translated;
 });

 // Update placeholders
 const searchInput = document.getElementById('graph-search-input');
 if (searchInput) searchInput.placeholder = t('graph.searchPlaceholder');

 const chatInput = document.getElementById('chat-input');
 if (chatInput) chatInput.placeholder = t('chat.placeholder');

 // Update profile placeholders
 const phMap = {
 'profile-identity': 'profile.identityPh',
 'profile-goals': 'profile.goalsPh',
 'profile-style': 'profile.stylePh',
 'profile-output': 'profile.outputPh',
 'profile-background': 'profile.backgroundPh',
 };
 for (const [id, key] of Object.entries(phMap)) {
 const el = document.getElementById(id);
 if (el) el.placeholder = t(key);
 }

 // Update toggle button labels
 const labelEl = document.getElementById('lang-label');
 const altEl = document.getElementById('lang-alt');
 if (labelEl) labelEl.textContent = lang === 'th' ? 'TH' : 'EN';
 if (altEl) altEl.textContent = lang === 'th' ? 'EN' : 'TH';
}

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
 // Apply saved language immediately
 applyLanguage(getLang());

 // Language toggle button
 document.getElementById('lang-toggle')?.addEventListener('click', () => {
 const newLang = getLang() === 'th' ? 'en' : 'th';
 applyLanguage(newLang);
 // Re-render dynamic content with new language
 if (state.authToken) {
 loadFiles();
 if (state.mcpInfo) renderMCPTools(state.mcpInfo.available_tools || []);
 }
 });

 // Init all UI handlers (these don't need auth)
 initNavigation();
 initUpload();
 initProfile();
 initChat();
 initGraphControls();
 initKnowledgeTabs();
 initMCP();

 // Auth system — decides whether to show landing or app
 initAuth();

 // Check for billing redirect (success/cancelled)
 checkBillingRedirect();
});

// ═══════════════════════════════════════════
// NAVIGATION
// ═══════════════════════════════════════════
function initNavigation() {
 document.querySelectorAll('.nav-item[data-page]').forEach(link => {
 link.addEventListener('click', e => {
 e.preventDefault();
 switchPage(link.dataset.page);
 });
 });
}

function switchPage(page) {
 state.currentPage = page;
 document.querySelectorAll('.nav-item[data-page]').forEach(el => el.classList.remove('active'));
 document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
 document.querySelectorAll('.page').forEach(el => el.classList.remove('active'));
 document.getElementById(`page-${page}`)?.classList.add('active');

 if (page === 'knowledge') loadKnowledge();
 if (page === 'graph') loadGraph();
 if (page === 'chat') loadProfile();
 if (page === 'mcp-setup') loadMCPSetup();
 if (page === 'tokens') loadTokens();
 if (page === 'mcp-logs') loadMCPLogs();
 if (page === 'context-memory') loadContexts();
}

// ═══════════════════════════════════════════
// STATS
// ═══════════════════════════════════════════
async function loadStats() {
 try {
 const res = await authFetch('/api/stats');
 const data = await res.json();
 // Note: stat-files and stat-packs get overridden by loadUsageInfo with limits
 document.getElementById('stat-files').textContent = data.total_files;
 document.getElementById('stat-clusters').textContent = data.total_clusters;
 document.getElementById('stat-nodes').textContent = data.total_nodes || 0;
 document.getElementById('stat-edges').textContent = data.total_edges || 0;
 document.getElementById('stat-packs').textContent = data.total_context_packs;
 document.getElementById('stat-tokens').textContent = data.active_tokens || 0;
 const dot = document.getElementById('profile-dot');
 if (dot) dot.className = `profile-status-dot ${data.profile_set ? 'active' : ''}`;
 } catch (e) { console.error('Stats error:', e); }
}

// ═══════════════════════════════════════════
// FILE UPLOAD & LIST
// ═══════════════════════════════════════════
function initUpload() {
 const zone = document.getElementById('upload-zone');
 const input = document.getElementById('file-input');

 zone.addEventListener('click', () => input.click());
 zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('drag-over'); });
 zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
 zone.addEventListener('drop', e => {
 e.preventDefault();
 zone.classList.remove('drag-over');
 uploadFiles(e.dataTransfer.files);
 });
 input.addEventListener('change', () => { uploadFiles(input.files); input.value = ''; });

 document.getElementById('btn-organize-all')?.addEventListener('click', runOrganizeAll);
 document.getElementById('btn-organize-new')?.addEventListener('click', runOrganizeNew);
 loadUnprocessedCount();
}

async function uploadFiles(fileList) {
 const form = new FormData();
 for (const f of fileList) form.append('files', f);
 const count = fileList.length;
 showLoadingOverlay(getLang() === 'th' ? `กำลังอัปโหลด ${count} ไฟล์...` : `Uploading ${count} file(s)...`, 'upload');
 try {
 const res = await authFetch('/api/upload', { method: 'POST', body: form });
 const data = await res.json();
 if (data.count > 0) {
 showToast(`${t('toast.uploaded')} ${data.count} ${t('stat.files').toLowerCase()}`, 'success');
 }
 // Show skipped files — check if quota-related
 if (data.skipped && data.skipped.length > 0) {
 const quotaSkip = data.skipped.find(s => s.reason && s.reason.includes('ขีดจำกัด'));
 if (quotaSkip) {
 setTimeout(() => showUpgradeModal(quotaSkip.reason), 300);
 } else {
 const names = data.skipped.map(s => `${s.filename}: ${s.reason}`).join(', ');
 setTimeout(() => showToast(` ${getLang() === 'th' ? 'ข้ามไฟล์' : 'Skipped'}: ${names}`, 'error'), 500);
 }
 }
 loadFiles();
 loadStats();
 loadUnprocessedCount();
 loadUsageInfo();
 } catch (e) { /* authFetch handles toast */ }
 hideLoadingOverlay();
}

async function loadFiles() {
 try {
 const res = await authFetch('/api/files');
 const data = await res.json();
 renderFileList(data.files);
 document.getElementById('file-count-badge').textContent = data.files.length;
 } catch (e) { console.error('Load files error:', e); }
}

function renderFileList(files) {
 const container = document.getElementById('file-list');
 if (!files.length) {
 container.innerHTML = `<div class="empty-state"><p>${t('myData.noFiles')}</p></div>`;
 return;
 }
 container.innerHTML = files.map(f => {
 const tags = (f.tags || []).map(tag => `<span class="tag-chip">${tag}</span>`).join('');
 const freshness = f.freshness && f.freshness !== 'current' ? `<span class="freshness-badge ${f.freshness}">${f.freshness}</span>` : '';
 const sot = f.source_of_truth ? '<span class="sot-badge"> Source of Truth</span>' : '';
 const locked = f.is_locked ? '<span class="locked-badge" title="' + (f.locked_reason || 'Locked') + '"></span>' : '';
 const lockedClass = f.is_locked ? ' file-locked' : '';
 return `
 <div class="file-item${lockedClass}" data-id="${f.id}" onclick="openFileDetail('${f.id}')">
 <div class="file-icon ${f.filetype}">${f.filetype.toUpperCase()}${locked}</div>
 <div class="file-info">
 <div class="file-name">${f.filename}${f.is_locked ? ' <span class="locked-label">' + (getLang() === 'th' ? 'ล็อค' : 'Locked') + '</span>' : ''}</div>
 <div class="file-meta">
 <span>${f.text_length?.toLocaleString() || 0} chars</span>
 <span class="status-dot ${f.processing_status}"></span>
 ${freshness} ${sot}
 </div>
 ${tags ? `<div class="file-tags">${tags}</div>` : ''}
 </div>
 <div class="file-actions">
 <button class="btn-sm" onclick="event.stopPropagation(); deleteFile('${f.id}')">${t('myData.delete')}</button>
 </div>
 </div>`;
 }).join('');
}

async function deleteFile(id) {
 if (!await showConfirm(getLang() === 'th' ? 'ต้องการลบไฟล์นี้?' : 'Delete this file?')) return;
 try {
 await authFetch(`/api/files/${id}`, { method: 'DELETE' });
 showToast(t('toast.deleted'), 'success');
 closeFileDetail();
 loadFiles();
 loadStats();
 } catch (e) { showToast(t('toast.error'), 'error'); }
}


// ─── File Detail Panel ───

let _fdBackdrop = null;

async function openFileDetail(fileId) {
 const panel = document.getElementById('file-detail-panel');
 _currentFileId = fileId;

 // Create backdrop if not exists
 if (!_fdBackdrop) {
 _fdBackdrop = document.createElement('div');
 _fdBackdrop.className = 'fd-backdrop';
 _fdBackdrop.addEventListener('click', closeFileDetail);
 document.body.appendChild(_fdBackdrop);
 }

 // Show panel + backdrop
 panel.classList.remove('hidden');
 requestAnimationFrame(() => {
 panel.classList.add('visible');
 _fdBackdrop.classList.add('visible');
 });

 // Set loading state
 document.getElementById('fd-filename').textContent = 'Loading...';
 document.getElementById('fd-summary').textContent = '...';
 document.getElementById('fd-topics').innerHTML = '';
 document.getElementById('fd-facts').innerHTML = '';
 document.getElementById('fd-why').textContent = '';
 document.getElementById('fd-content').textContent = '';

 try {
 // Fetch summary data
 const res = await authFetch(`/api/summary/${fileId}`);
 if (res.ok) {
 const d = await res.json();
 document.getElementById('fd-icon').textContent = d.filetype?.toUpperCase() || '?';
 document.getElementById('fd-filename').textContent = d.filename;
 document.getElementById('fd-cluster').textContent = d.cluster || '—';
 const stars = ''.repeat(Math.min(5, Math.round(d.importance_score / 20)));
 document.getElementById('fd-importance').textContent = `${stars} ${d.importance_label}`;
 document.getElementById('fd-summary').textContent = d.summary_text || 'No summary yet';
 document.getElementById('fd-topics').innerHTML = (d.key_topics || []).map(t => `<span class="chip">${t}</span>`).join('');
 document.getElementById('fd-facts').innerHTML = (d.key_facts || []).map(f => `<li>${f}</li>`).join('');
 document.getElementById('fd-why').textContent = d.why_important || '—';
 } else {
 document.getElementById('fd-summary').textContent = getLang() === 'th'
 ? 'ยังไม่มี Summary — กด "จัดระเบียบด้วย AI" ก่อน'
 : 'No summary yet — click "Organize with AI" first';
 }

 // Fetch file content for preview
 const contentRes = await authFetch(`/api/files/${fileId}/content`);
 if (contentRes.ok) {
 const c = await contentRes.json();
 if (!document.getElementById('fd-filename').textContent || document.getElementById('fd-filename').textContent === 'Loading...') {
 document.getElementById('fd-icon').textContent = c.filetype?.toUpperCase() || '?';
 document.getElementById('fd-filename').textContent = c.filename;
 }
 document.getElementById('fd-content').textContent = c.text
 ? c.text.substring(0, 3000) + (c.text.length > 3000 ? '\n\n... (truncated)' : '')
 : getLang() === 'th' ? 'ไม่มีเนื้อหา' : 'No content available';
 }
 } catch (e) {
 console.error('File detail load error:', e);
 document.getElementById('fd-summary').textContent = 'Error loading details';
 }
}

function closeFileDetail() {
 const panel = document.getElementById('file-detail-panel');
 panel.classList.remove('visible');
 if (_fdBackdrop) _fdBackdrop.classList.remove('visible');
 setTimeout(() => panel.classList.add('hidden'), 300);
 toggleSummaryEdit(false); // reset edit mode
}

// Close button
document.getElementById('fd-close')?.addEventListener('click', closeFileDetail);

// v5.2 — Download original file
document.getElementById('fd-download-btn')?.addEventListener('click', () => {
 if (!_currentFileId) return;
 // Direct download via browser — opens the file download
 window.open(`/api/files/${_currentFileId}/download`, '_blank');
});

// v5.2 — Reprocess file (OCR + Thai fix)
document.getElementById('fd-reprocess-btn')?.addEventListener('click', async () => {
 if (!_currentFileId) return;
 const btn = document.getElementById('fd-reprocess-btn');
 btn.disabled = true;
 btn.innerHTML = '⏳ Processing...';
 try {
 const res = await authFetch(`/api/files/${_currentFileId}/reprocess`, { method: 'POST' });
 const data = await res.json();
 if (data.status === 'ok') {
 showToast(getLang() === 'th'
 ? ` Re-extract สำเร็จ! ${data.old_text_length} → ${data.new_text_length} ตัวอักษร`
 : ` Re-extracted! ${data.old_text_length} → ${data.new_text_length} chars`, 'success');
 // Reload file detail to show new content
 openFileDetail(_currentFileId);
 } else {
 showToast(data.detail || 'Reprocess failed', 'error');
 }
 } catch (e) {
 showToast(getLang() === 'th' ? ' Re-extract ล้มเหลว' : ' Reprocess failed', 'error');
 }
 btn.disabled = false;
 btn.innerHTML = ' Re-extract';
});

// ─── Summary Edit Mode ───

let _currentFileId = null;

function toggleSummaryEdit(editing) {
 const editBtn = document.getElementById('fd-edit-btn');
 const editActions = document.getElementById('fd-edit-actions');
 const summaryView = document.getElementById('fd-summary');
 const summaryEdit = document.getElementById('fd-summary-edit');
 const whyView = document.getElementById('fd-why');
 const whyEdit = document.getElementById('fd-why-edit');

 if (editing) {
 // Enter edit mode — copy current text to textareas
 summaryEdit.value = summaryView.textContent;
 whyEdit.value = whyView.textContent;
 summaryView.classList.add('hidden');
 summaryEdit.classList.remove('hidden');
 whyView.classList.add('hidden');
 whyEdit.classList.remove('hidden');
 editBtn.classList.add('hidden');
 editActions.classList.remove('hidden');
 summaryEdit.focus();
 } else {
 // Exit edit mode
 summaryView.classList.remove('hidden');
 summaryEdit.classList.add('hidden');
 whyView.classList.remove('hidden');
 whyEdit.classList.add('hidden');
 editBtn.classList.remove('hidden');
 editActions.classList.add('hidden');
 }
}

async function saveSummaryEdit() {
 if (!_currentFileId) return;

 const summaryText = document.getElementById('fd-summary-edit').value.trim();
 const whyImportant = document.getElementById('fd-why-edit').value.trim();
 const saveBtn = document.getElementById('fd-save-btn');
 saveBtn.disabled = true;
 saveBtn.textContent = '...';

 try {
 const res = await authFetch(`/api/summary/${_currentFileId}`, {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 summary_text: summaryText,
 why_important: whyImportant
 })
 });
 if (!res.ok) throw new Error('Save failed');

 // Update display
 document.getElementById('fd-summary').textContent = summaryText;
 document.getElementById('fd-why').textContent = whyImportant;
 toggleSummaryEdit(false);
 showToast(getLang() === 'th' ? 'บันทึก Summary แล้ว' : 'Summary saved', 'success');
 } catch (e) {
 showToast(getLang() === 'th' ? 'บันทึกล้มเหลว' : 'Save failed', 'error');
 }
 saveBtn.disabled = false;
 saveBtn.textContent = ' Save';
}

async function loadUnprocessedCount() {
 try {
 const res = await authFetch('/api/unprocessed-count');
 if (!res.ok) return;
 const data = await res.json();
 const badge = document.getElementById('unprocessed-badge');
 if (badge) {
 if (data.unprocessed > 0) {
 badge.textContent = data.unprocessed;
 badge.style.display = 'inline-flex';
 } else {
 badge.style.display = 'none';
 }
 }
 } catch (e) { /* silent */ }
}

async function runOrganizeAll() {
 const btn = document.getElementById('btn-organize-all');
 btn.disabled = true;
 btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังจัดระเบียบ...' : 'Organizing...'}`;
 showLoadingOverlay(getLang() === 'th' ? ' AI กำลังวิเคราะห์และจัดกลุ่มไฟล์ทั้งหมด...\nอาจใช้เวลา 30-60 วินาที' : ' AI is analyzing and organizing ALL files...\nThis may take 30-60 seconds', 'ai');
 try {
 const res = await authFetch('/api/organize', { method: 'POST' });
 if (res.status === 403) {
 const err = await res.json();
 hideLoadingOverlay();
 showUpgradeModal(err.detail || 'Quota exceeded');
 btn.disabled = false;
 btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg> <span data-i18n="myData.organizeAll">${t('myData.organizeAll')}</span>`;
 return;
 }
 const data = await res.json();
 showToast(`${t('toast.organized')} (${data.graph?.nodes || 0} nodes, ${data.graph?.edges || 0} edges)`, 'success');
 loadFiles();
 loadStats();
 loadUnprocessedCount();
 loadUsageInfo();
 } catch (e) { showToast(t('toast.error'), 'error'); }
 hideLoadingOverlay();
 btn.disabled = false;
 btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2"/></svg> <span data-i18n="myData.organizeAll">${t('myData.organizeAll')}</span>`;
}

async function runOrganizeNew() {
 const btn = document.getElementById('btn-organize-new');
 btn.disabled = true;
 btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังจัดระเบียบไฟล์ใหม่...' : 'Organizing new files...'}`;
 showLoadingOverlay(getLang() === 'th' ? ' AI กำลังจัดระเบียบไฟล์ที่อัปโหลดใหม่...' : ' AI is organizing new files...', 'ai');
 try {
 const res = await authFetch('/api/organize-new', { method: 'POST' });
 if (res.status === 403) {
 const err = await res.json();
 hideLoadingOverlay();
 showUpgradeModal(err.detail || 'Quota exceeded');
 btn.disabled = false;
 btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> <span data-i18n="myData.organizeNew">${t('myData.organizeNew')}</span><span class="badge-count" id="unprocessed-badge" style="display:none;">0</span>`;
 return;
 }
 const data = await res.json();
 if (data.new_files === 0) {
 showToast(t('toast.noNewFiles'), 'info');
 } else {
 showToast(`${t('toast.organizedNew')} (${data.new_files} ไฟล์)`, 'success');
 loadFiles();
 loadStats();
 }
 loadUnprocessedCount();
 loadUsageInfo();
 } catch (e) { showToast(t('toast.error'), 'error'); }
 hideLoadingOverlay();
 btn.disabled = false;
 btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> <span data-i18n="myData.organizeNew">${t('myData.organizeNew')}</span><span class="badge-count" id="unprocessed-badge" style="display:none;">0</span>`;
 loadUnprocessedCount();
}

// ═══════════════════════════════════════════
// KNOWLEDGE VIEW
// ═══════════════════════════════════════════
function initKnowledgeTabs() {
 document.querySelectorAll('.tab-btn').forEach(btn => {
 btn.addEventListener('click', () => {
 document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
 btn.classList.add('active');
 state.knowledgeTab = btn.dataset.tab;
 loadKnowledge();
 });
 });
}

async function loadKnowledge() {
 const container = document.getElementById('knowledge-content');
 if (state.knowledgeTab === 'collections') {
 try {
 const res = await authFetch('/api/clusters');
 const data = await res.json();
 if (!data.clusters.length) {
 container.innerHTML = `<div class="empty-state"><p>${t('knowledge.emptyCollections')}</p></div>`;
 return;
 }
 container.innerHTML = data.clusters.map(c => `
 <div class="cluster-card" data-cluster-id="${c.id}">
 <div class="cluster-card-header">
 <div class="cluster-title" id="ct-title-${c.id}"> ${escapeHtml(c.title)} <span class="badge">${c.file_count}</span></div>
 <button class="btn-icon" onclick="editCluster('${c.id}', '${escapeHtml(c.title).replace(/'/g, "\\'")}', '${escapeHtml(c.summary || '').replace(/'/g, "\\'").replace(/\n/g, '\\n')}')" title="Edit"></button>
 </div>
 <div class="cluster-summary" id="ct-summary-${c.id}">${escapeHtml(c.summary || '')}</div>
 <div class="cluster-files">
 ${c.files.map(f => `<span class="cluster-file-chip">${f.filename}</span>`).join('')}
 </div>
 </div>`).join('');
 } catch (e) { container.innerHTML = `<div class="empty-state"><p>${t('knowledge.loadFailed')}</p></div>`; }
 } else if (state.knowledgeTab === 'packs') {
 try {
 const res = await authFetch('/api/context-packs');
 const data = await res.json();
 const createBtnLabel = getLang() === 'th' ? '+ สร้าง Pack' : '+ Create Pack';
 const emptyMsg = getLang() === 'th' ? 'ยังไม่มี Context Pack — สร้างเพื่อจัดกลุ่มข้อมูลให้ AI' : 'No context packs yet — create one to bundle data for AI';

 let html = `<div class="packs-header">
 <span>${data.count || 0} pack${data.count !== 1 ? 's' : ''}</span>
 <button class="btn btn-primary" onclick="openCreatePackModal()">${createBtnLabel}</button>
 </div>`;

 if (!data.packs.length) {
 html += `<div class="empty-state"><p>${emptyMsg}</p></div>`;
 } else {
 html += data.packs.map(p => `
 <div class="pack-card" data-pack-id="${p.id}">
 <div class="pack-card-header">
 <div class="pack-card-title"> ${escapeHtml(p.title)}</div>
 <div class="pack-card-actions">
 <button onclick="regeneratePack('${p.id}')" title="Regenerate"></button>
 <button class="btn-danger" onclick="deletePack('${p.id}')" title="Delete"></button>
 </div>
 </div>
 <div class="pack-card-summary">${escapeHtml(p.summary_text?.substring(0, 200) || '')}${p.summary_text?.length > 200 ? '...' : ''}</div>
 <div class="pack-card-meta">
 <span class="badge">${p.type}</span>
 ${p.created_at ? `<span>${formatDate(p.created_at)}</span>` : ''}
 </div>
 </div>`).join('');
 }
 container.innerHTML = html;
 } catch (e) { container.innerHTML = `<div class="empty-state"><p>${t('knowledge.loadFailed')}</p></div>`; }
 } else if (state.knowledgeTab === 'notes') {
 try {
 const res = await authFetch('/api/graph/nodes?family=entity');
 const data = await res.json();
 if (!data.nodes.length) {
 container.innerHTML = `<div class="empty-state"><p>${t('knowledge.emptyNotes')}</p></div>`;
 return;
 }
 container.innerHTML = data.nodes.map(n => `
 <div class="cluster-card" style="cursor:pointer" onclick="showNodeInGraph('${n.id}')">
 <div class="cluster-title">
 <span class="dot" style="background:${NODE_COLORS[n.node_family] || '#888'}"></span>
 ${n.label}
 <span class="badge">${n.object_type}</span>
 </div>
 </div>`).join('');
 } catch (e) { container.innerHTML = `<div class="empty-state"><p>${t('knowledge.loadFailed')}</p></div>`; }
 }
}

function showNodeInGraph(nodeId) {
 state.localNodeId = nodeId;
 state.graphMode = 'local';
 switchPage('graph');
}

// ─── Collection Editing ───

function editCluster(clusterId, currentTitle, currentSummary) {
 const card = document.querySelector(`[data-cluster-id="${clusterId}"]`);
 if (!card || card.querySelector('.cluster-edit-form')) return; // already editing

 const titleEl = card.querySelector('.cluster-title');
 const summaryEl = card.querySelector('.cluster-summary');
 const headerEl = card.querySelector('.cluster-card-header');

 // Replace title with input
 const titleInput = document.createElement('input');
 titleInput.type = 'text';
 titleInput.value = currentTitle;
 titleInput.className = 'form-input';
 titleInput.style.marginBottom = '8px';

 // Replace summary with textarea
 const summaryTextarea = document.createElement('textarea');
 summaryTextarea.value = currentSummary.replace(/\\n/g, '\n');
 summaryTextarea.className = 'fd-edit-textarea';
 summaryTextarea.style.minHeight = '60px';

 // Add save/cancel buttons
 const actions = document.createElement('div');
 actions.className = 'cluster-edit-form';
 actions.style.cssText = 'display:flex;gap:6px;margin-top:8px';
 const saveBtn = document.createElement('button');
 saveBtn.className = 'btn btn-primary btn-sm';
 saveBtn.textContent = ' Save';
 saveBtn.onclick = () => saveCluster(clusterId, titleInput.value, summaryTextarea.value);
 const cancelBtn = document.createElement('button');
 cancelBtn.className = 'btn btn-outline btn-sm';
 cancelBtn.textContent = 'Cancel';
 cancelBtn.onclick = () => loadKnowledge();
 actions.appendChild(saveBtn);
 actions.appendChild(cancelBtn);

 // Hide originals, show inputs
 titleEl.classList.add('hidden');
 summaryEl.classList.add('hidden');
 headerEl.querySelector('.btn-icon').classList.add('hidden');
 titleEl.after(titleInput);
 summaryEl.after(summaryTextarea);
 summaryTextarea.after(actions);
 titleInput.focus();
}

async function saveCluster(clusterId, newTitle, newSummary) {
 try {
 const res = await authFetch(`/api/clusters/${clusterId}`, {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ title: newTitle.trim(), summary: newSummary.trim() })
 });
 if (!res.ok) throw new Error('Save failed');
 showToast(getLang() === 'th' ? 'บันทึก Collection แล้ว' : 'Collection saved', 'success');
 loadKnowledge(); // refresh
 } catch (e) {
 showToast(getLang() === 'th' ? 'บันทึกล้มเหลว' : 'Save failed', 'error');
 }
}

// ─── Context Pack Management ───

async function openCreatePackModal() {
 const overlay = document.getElementById('pack-modal-overlay');
 overlay.classList.remove('hidden');

 // Reset form
 document.getElementById('pack-title-input').value = '';
 document.getElementById('pack-type-select').value = 'project';

 // Load files for selection
 try {
 const res = await authFetch('/api/files');
 const data = await res.json();
 const fileList = document.getElementById('pack-file-list');
 if (!data.files.length) {
 fileList.innerHTML = `<p class="text-muted" style="padding:12px">${getLang() === 'th' ? 'ไม่มีไฟล์' : 'No files'}</p>`;
 return;
 }
 fileList.innerHTML = data.files.map(f => `
 <label class="pack-file-item">
 <input type="checkbox" value="${f.id}">
 <span class="file-icon ${f.filetype}" style="width:28px;height:28px;font-size:10px">${f.filetype.toUpperCase()}</span>
 <span class="pf-name">${f.filename}</span>
 </label>
 `).join('');
 } catch (e) {
 document.getElementById('pack-file-list').innerHTML = '<p class="text-muted" style="padding:12px">Error loading files</p>';
 }
}

function closePackModal() {
 document.getElementById('pack-modal-overlay').classList.add('hidden');
}

async function submitCreatePack() {
 const title = document.getElementById('pack-title-input').value.trim();
 const type = document.getElementById('pack-type-select').value;
 const checkboxes = document.querySelectorAll('#pack-file-list input[type="checkbox"]:checked');
 const fileIds = Array.from(checkboxes).map(cb => cb.value);

 if (!title) {
 showToast(getLang() === 'th' ? 'กรุณาตั้งชื่อ Pack' : 'Please enter a pack name', 'error');
 return;
 }
 if (!fileIds.length) {
 showToast(getLang() === 'th' ? 'กรุณาเลือกไฟล์อย่างน้อย 1 ไฟล์' : 'Please select at least 1 file', 'error');
 return;
 }

 const btn = document.getElementById('pack-create-btn');
 btn.disabled = true;
 btn.textContent = getLang() === 'th' ? 'กำลังสร้าง...' : 'Creating...';

 try {
 const res = await authFetch('/api/context-packs', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ title, type, source_file_ids: fileIds, source_cluster_ids: [] })
 });
 if (res.status === 403) {
 const err = await res.json();
 closePackModal();
 showUpgradeModal(err.detail || 'Pack limit reached');
 btn.disabled = false;
 btn.textContent = getLang() === 'th' ? 'สร้าง Pack' : 'Create Pack';
 return;
 }
 if (!res.ok) {
 const err = await res.json();
 throw new Error(err.detail || 'Failed');
 }
 showToast(getLang() === 'th' ? `สร้าง Pack "${title}" สำเร็จ!` : `Pack "${title}" created!`, 'success');
 closePackModal();
 loadKnowledge();
 loadStats();
 loadUsageInfo();
 } catch (e) {
 showToast(`Error: ${e.message}`, 'error');
 }
 btn.disabled = false;
 btn.textContent = getLang() === 'th' ? 'สร้าง Pack' : 'Create Pack';
}

async function deletePack(packId) {
 if (!await showConfirm(getLang() === 'th' ? 'ลบ Context Pack นี้?' : 'Delete this context pack?')) return;
 try {
 await authFetch(`/api/context-packs/${packId}`, { method: 'DELETE' });
 showToast(getLang() === 'th' ? 'ลบ Pack แล้ว' : 'Pack deleted', 'success');
 loadKnowledge();
 loadStats();
 } catch (e) { showToast(t('toast.error'), 'error'); }
}

async function regeneratePack(packId) {
 try {
 showToast(getLang() === 'th' ? 'กำลัง regenerate...' : 'Regenerating...', 'info');
 const res = await authFetch(`/api/context-packs/${packId}/regenerate`, { method: 'POST' });
 if (res.status === 403) {
 const err = await res.json();
 showUpgradeModal(err.detail || 'Refresh limit reached');
 return;
 }
 if (res.ok) {
 showToast(getLang() === 'th' ? 'Regenerate สำเร็จ!' : 'Pack regenerated!', 'success');
 loadKnowledge();
 loadUsageInfo();
 } else {
 showToast(getLang() === 'th' ? 'Regenerate ล้มเหลว' : 'Regeneration failed', 'error');
 }
 } catch (e) { showToast(t('toast.error'), 'error'); }
}

// Pack modal event listeners
document.getElementById('pack-modal-close')?.addEventListener('click', closePackModal);
document.getElementById('pack-cancel-btn')?.addEventListener('click', closePackModal);
document.getElementById('pack-create-btn')?.addEventListener('click', submitCreatePack);
document.getElementById('pack-modal-overlay')?.addEventListener('click', (e) => {
 if (e.target === e.currentTarget) closePackModal();
});

// ═══════════════════════════════════════════
// GRAPH (Obsidian-style)
// ═══════════════════════════════════════════
let _zoomBehavior = null;

function getNodeRadius(d) {
 return 5 + (d.importance || 0.5) * 12;
}

function initGraphControls() {
 document.getElementById('graph-global-btn')?.addEventListener('click', () => {
 state.graphMode = 'global';
 document.getElementById('graph-global-btn').classList.add('active');
 document.getElementById('graph-local-btn').classList.remove('active');
 document.getElementById('local-controls').classList.add('hidden');
 document.getElementById('graph-page-title').textContent = t('graph.globalTitle');
 document.getElementById('graph-page-subtitle').textContent = t('graph.globalSubtitle');
 loadGraph();
 });

 document.getElementById('graph-local-btn')?.addEventListener('click', () => {
 state.graphMode = 'local';
 document.getElementById('graph-local-btn').classList.add('active');
 document.getElementById('graph-global-btn').classList.remove('active');
 document.getElementById('local-controls').classList.remove('hidden');
 document.getElementById('graph-page-title').textContent = t('graph.localTitle');
 document.getElementById('graph-page-subtitle').textContent = t('graph.localSubtitle');
 loadGraph();
 });

 document.getElementById('btn-rebuild-graph')?.addEventListener('click', async () => {
 const btn = document.getElementById('btn-rebuild-graph');
 btn.disabled = true;
 btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังสร้าง...' : 'Building...'}`;
 showLoadingOverlay(getLang() === 'th' ? ' AI กำลังสร้าง Knowledge Graph...\nวิเคราะห์ความสัมพันธ์ระหว่างไฟล์' : ' AI is building Knowledge Graph...\nAnalyzing relationships between files', 'ai');
 try {
 await authFetch('/api/graph/build', { method: 'POST' });
 showToast(t('toast.graphBuilt'), 'success');
 loadGraph();
 loadStats();
 } catch (e) { showToast(t('toast.error'), 'error'); }
 hideLoadingOverlay();
 btn.disabled = false;
 btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg> <span data-i18n="graph.rebuild">${t('graph.rebuild')}</span>`;
 });

 document.querySelectorAll('.filter-chip').forEach(chip => {
 chip.addEventListener('click', () => {
 chip.classList.toggle('active');
 const family = chip.dataset.family;
 state.filters[family] = chip.classList.contains('active');
 renderGraph();
 });
 });

 // Debounced search with zoom-to-node
 let searchTimeout;
 document.getElementById('graph-search-input')?.addEventListener('input', e => {
 clearTimeout(searchTimeout);
 searchTimeout = setTimeout(() => {
 const q = e.target.value.toLowerCase().trim();
 if (!q) {
 // Clear search — restore all
 d3.selectAll('.graph-node').classed('dimmed', false).classed('neighbor', false);
 d3.selectAll('.graph-edge-line').classed('dimmed', false).classed('highlighted', false);
 return;
 }
 // Find matching nodes
 const matchIds = new Set();
 d3.selectAll('.graph-node').each(function(d) {
 if (d.label.toLowerCase().includes(q)) matchIds.add(d.id);
 });
 // Dim non-matching, highlight matching
 d3.selectAll('.graph-node')
 .classed('dimmed', d => !matchIds.has(d.id))
 .classed('neighbor', d => matchIds.has(d.id));
 d3.selectAll('.graph-edge-line')
 .classed('dimmed', d => !matchIds.has(d.source.id) && !matchIds.has(d.target.id))
 .classed('highlighted', d => matchIds.has(d.source.id) || matchIds.has(d.target.id));
 // Zoom to first match
 if (matchIds.size && _zoomBehavior) {
 const firstMatch = state.graphData.nodes.find(n => matchIds.has(n.id));
 if (firstMatch && firstMatch.x !== undefined) {
 const svg = d3.select('#graph-svg');
 const container = document.getElementById('graph-canvas');
 const w = container.clientWidth, h = container.clientHeight;
 svg.transition().duration(500).call(
 _zoomBehavior.transform,
 d3.zoomIdentity.translate(w/2 - firstMatch.x * 1.5, h/2 - firstMatch.y * 1.5).scale(1.5)
 );
 }
 }
 }, 250);
 });

 document.getElementById('depth-slider')?.addEventListener('input', e => {
 document.getElementById('depth-value').textContent = e.target.value;
 if (state.graphMode === 'local' && state.localNodeId) loadGraph();
 });

 document.getElementById('close-detail')?.addEventListener('click', () => {
 document.getElementById('detail-panel').classList.add('hidden');
 state.selectedNodeId = null;
 d3.selectAll('.graph-node').classed('selected', false);
 });

 document.getElementById('detail-open-local')?.addEventListener('click', () => {
 if (state.selectedNodeId) {
 state.localNodeId = state.selectedNodeId;
 state.graphMode = 'local';
 document.getElementById('graph-local-btn').click();
 }
 });

 document.getElementById('detail-ask-ai')?.addEventListener('click', () => {
 const label = document.getElementById('detail-label').textContent;
 switchPage('chat');
 document.getElementById('chat-input').value = getLang() === 'th' ? `อธิบายเกี่ยวกับ "${label}" ให้หน่อย` : `Tell me about "${label}"`;
 document.getElementById('chat-input').focus();
 });

 // Zoom controls
 document.getElementById('zoom-in-btn')?.addEventListener('click', () => {
 const svg = d3.select('#graph-svg');
 if (_zoomBehavior) svg.transition().duration(300).call(_zoomBehavior.scaleBy, 1.4);
 });
 document.getElementById('zoom-out-btn')?.addEventListener('click', () => {
 const svg = d3.select('#graph-svg');
 if (_zoomBehavior) svg.transition().duration(300).call(_zoomBehavior.scaleBy, 0.7);
 });
 document.getElementById('zoom-fit-btn')?.addEventListener('click', fitGraphToView);
}

function fitGraphToView() {
 if (!state.graphData.nodes.length || !_zoomBehavior) return;
 const svg = d3.select('#graph-svg');
 const container = document.getElementById('graph-canvas');
 const w = container.clientWidth, h = container.clientHeight;
 const nodes = state.graphData.nodes.filter(n => n.x !== undefined);
 if (!nodes.length) return;

 const xExtent = d3.extent(nodes, d => d.x);
 const yExtent = d3.extent(nodes, d => d.y);
 const dx = (xExtent[1] - xExtent[0]) || 100;
 const dy = (yExtent[1] - yExtent[0]) || 100;
 const cx = (xExtent[0] + xExtent[1]) / 2;
 const cy = (yExtent[0] + yExtent[1]) / 2;
 const scale = Math.min(0.85 * w / dx, 0.85 * h / dy, 2);

 svg.transition().duration(500).ease(d3.easeCubicOut).call(
 _zoomBehavior.transform,
 d3.zoomIdentity.translate(w/2 - cx * scale, h/2 - cy * scale).scale(scale)
 );
}

async function loadGraph() {
 let url = '/api/graph/global';
 if (state.graphMode === 'local' && state.localNodeId) {
 const depth = document.getElementById('depth-slider')?.value || 1;
 url = `/api/graph/neighborhood/${state.localNodeId}?depth=${depth}`;
 }

 try {
 const res = await authFetch(url);
 const data = await res.json();
 state.graphData = { nodes: data.nodes || [], edges: data.edges || [] };

 const empty = document.getElementById('graph-empty');
 if (!state.graphData.nodes.length) {
 empty?.classList.remove('hidden');
 d3.select('#graph-svg').selectAll('*').remove();
 return;
 }
 empty?.classList.add('hidden');
 renderGraph();
 } catch (e) {
 console.error('Graph load error:', e);
 }
}

function renderGraph() {
 // Wait for DOM layout to complete (page may have just switched from display:none)
 requestAnimationFrame(() => _doRenderGraph());
}

function _doRenderGraph() {
 const svg = d3.select('#graph-svg');
 svg.selectAll('*').remove();

 const container = document.getElementById('graph-canvas');
 let width = container.clientWidth;
 let height = container.clientHeight;
 
 // Fallback: if container hasn't laid out yet, use parent or default
 if (width < 100 || height < 100) {
 const parent = container.parentElement;
 width = parent?.clientWidth || window.innerWidth - 240;
 height = parent?.clientHeight || window.innerHeight - 120;
 }
 // Final safety fallback
 if (width < 100) width = 800;
 if (height < 100) height = 500;

 // ── Filter nodes by family
 const visibleFamilies = Object.keys(state.filters).filter(k => state.filters[k]);
 const nodes = state.graphData.nodes.filter(n =>
 visibleFamilies.includes(n.node_family) || visibleFamilies.includes(n.object_type)
 );
 const nodeIds = new Set(nodes.map(n => n.id));
 const edges = state.graphData.edges.filter(e => nodeIds.has(e.source?.id || e.source) && nodeIds.has(e.target?.id || e.target));

 // Update info overlay
 const ncEl = document.getElementById('graph-node-count');
 const ecEl = document.getElementById('graph-edge-count');
 if (ncEl) ncEl.textContent = nodes.length;
 if (ecEl) ecEl.textContent = edges.length;

 // ── Build adjacency map (for neighbor highlight)
 const adjacency = new Map();
 nodes.forEach(n => adjacency.set(n.id, new Set()));
 edges.forEach(e => {
 const sid = e.source?.id || e.source;
 const tid = e.target?.id || e.target;
 if (adjacency.has(sid)) adjacency.get(sid).add(tid);
 if (adjacency.has(tid)) adjacency.get(tid).add(sid);
 });

 // ── Count connections per node (for force strength)
 const linkCount = new Map();
 edges.forEach(e => {
 const sid = e.source?.id || e.source;
 const tid = e.target?.id || e.target;
 linkCount.set(sid, (linkCount.get(sid) || 0) + 1);
 linkCount.set(tid, (linkCount.get(tid) || 0) + 1);
 });

 // ── Zoom behavior
 let currentZoom = 1;
 const zoom = d3.zoom()
 .scaleExtent([0.15, 5])
 .on('zoom', e => {
 g.attr('transform', e.transform);
 currentZoom = e.transform.k;
 // Label culling based on zoom level (Obsidian-style)
 nodeGroup.selectAll('.graph-node').classed('hide-label', d => {
 if (currentZoom > 1.0) return false; // Show all at high zoom
 if (currentZoom > 0.5) return (d.importance || 0.5) < 0.6; // Only important at mid zoom
 return true; // Hide all labels at low zoom
 });
 });

 svg.call(zoom);
 _zoomBehavior = zoom;

 const g = svg.append('g');

 // ── SVG Defs: Glow filter
 const defs = svg.append('defs');
 const glowFilter = defs.append('filter').attr('id', 'nodeGlow').attr('x', '-50%').attr('y', '-50%').attr('width', '200%').attr('height', '200%');
 glowFilter.append('feGaussianBlur').attr('stdDeviation', '4').attr('result', 'blur');
 const merge = glowFilter.append('feMerge');
 merge.append('feMergeNode').attr('in', 'blur');
 merge.append('feMergeNode').attr('in', 'SourceGraphic');

 // ── Simulation (tuned for stability)
 const simulation = d3.forceSimulation(nodes)
 .force('link', d3.forceLink(edges).id(d => d.id)
 .distance(d => 55 + (d.weight || 0.5) * 45)
 .strength(d => {
 const sc = linkCount.get(d.source?.id || d.source) || 1;
 const tc = linkCount.get(d.target?.id || d.target) || 1;
 return 1 / Math.min(sc, tc);
 })
 )
 .force('charge', d3.forceManyBody()
 .strength(d => -60 - (d.importance || 0.5) * 100)
 .distanceMax(350)
 )
 .force('center', d3.forceCenter(width / 2, height / 2).strength(0.04))
 .force('collision', d3.forceCollide().radius(d => getNodeRadius(d) + 5).iterations(2))
 .force('x', d3.forceX(width / 2).strength(0.025))
 .force('y', d3.forceY(height / 2).strength(0.025))
 .alphaDecay(0.03)
 .velocityDecay(0.45);

 state.simulation = simulation;

 // ── PRE-COMPUTE: Run 120 ticks for instant stability (Obsidian pattern)
 simulation.stop();
 for (let i = 0; i < 120; i++) simulation.tick();

 // ── Draw edges
 const linkGroup = g.append('g');
 const link = linkGroup.selectAll('line')
 .data(edges)
 .join('line')
 .attr('class', 'graph-edge-line')
 .attr('stroke', 'rgba(255,255,255,0.05)')
 .attr('stroke-width', d => Math.max(0.5, (d.weight || 0.5) * 1.5))
 .attr('x1', d => d.source.x)
 .attr('y1', d => d.source.y)
 .attr('x2', d => d.target.x)
 .attr('y2', d => d.target.y);

 // ── Draw nodes
 const nodeGroup = g.append('g');
 const node = nodeGroup.selectAll('g')
 .data(nodes)
 .join('g')
 .attr('class', 'graph-node')
 .attr('transform', d => `translate(${d.x},${d.y})`)
 .call(d3.drag()
 .on('start', (e, d) => {
 if (!e.active) simulation.alphaTarget(0.15).restart();
 d.fx = d.x; d.fy = d.y;
 })
 .on('drag', (e, d) => { d.fx = e.x; d.fy = e.y; })
 .on('end', (e, d) => {
 if (!e.active) simulation.alphaTarget(0);
 // Sticky drag — keep pinned (Obsidian behavior)
 // Node stays where user dropped it
 })
 )
 .on('click', (e, d) => { e.stopPropagation(); selectNode(d); })
 .on('mouseenter', (e, d) => handleNodeHover(d, true, adjacency))
 .on('mouseleave', (e, d) => handleNodeHover(d, false, adjacency));

 // Glow circle (outer, colored, blurred)
 node.append('circle')
 .attr('class', 'node-glow')
 .attr('r', d => getNodeRadius(d) + 8)
 .attr('fill', d => NODE_COLORS[d.node_family] || '#888')
 .attr('filter', 'url(#nodeGlow)');

 // Core circle
 node.append('circle')
 .attr('class', 'node-core')
 .attr('r', d => getNodeRadius(d))
 .attr('fill', d => NODE_COLORS[d.node_family] || '#888')
 .attr('fill-opacity', 0.85)
 .attr('stroke', d => NODE_COLORS[d.node_family] || '#888')
 .attr('stroke-opacity', 0.3)
 .attr('stroke-width', 1.5);

 // Label
 node.append('text')
 .text(d => d.label.length > 16 ? d.label.substring(0, 16) + '…' : d.label)
 .attr('dy', d => getNodeRadius(d) + 14)
 .attr('font-size', '9px');

 // Center node highlight for local graph
 if (state.graphMode === 'local' && state.localNodeId) {
 node.filter(d => d.id === state.localNodeId)
 .select('.node-core')
 .attr('stroke', 'white')
 .attr('stroke-width', 3)
 .attr('stroke-opacity', 1);
 }

 // Apply initial label culling
 node.classed('hide-label', d => (d.importance || 0.5) < 0.6);

 // ── Continue simulation at low alpha for minor micro-adjustments
 simulation.alpha(0.08).restart();

 simulation.on('tick', () => {
 link
 .attr('x1', d => d.source.x)
 .attr('y1', d => d.source.y)
 .attr('x2', d => d.target.x)
 .attr('y2', d => d.target.y);
 node.attr('transform', d => `translate(${d.x},${d.y})`);
 });

 // Click on empty space → deselect
 svg.on('click', () => {
 state.selectedNodeId = null;
 document.getElementById('detail-panel').classList.add('hidden');
 d3.selectAll('.graph-node').classed('selected', false);
 });

 // Fit to view after a short delay
 setTimeout(fitGraphToView, 200);
}

// ── Hover: Dim All + Highlight Neighbors (Obsidian behavior)
function handleNodeHover(d, isEntering, adjacency) {
 const tooltip = document.getElementById('graph-tooltip');

 if (isEntering) {
 const neighbors = adjacency.get(d.id) || new Set();

 // Dim all nodes except hovered + neighbors
 d3.selectAll('.graph-node')
 .classed('dimmed', n => n.id !== d.id && !neighbors.has(n.id))
 .classed('neighbor', n => neighbors.has(n.id));

 // Dim all edges except those connecting to hovered node
 d3.selectAll('.graph-edge-line')
 .classed('dimmed', e => e.source.id !== d.id && e.target.id !== d.id)
 .classed('highlighted', e => e.source.id === d.id || e.target.id === d.id)
 .attr('stroke', e => {
 if (e.source.id === d.id || e.target.id === d.id) {
 return NODE_COLORS[d.node_family] || '#888';
 }
 return 'rgba(255,255,255,0.05)';
 });

 // Show tooltip
 if (tooltip) {
 document.getElementById('tooltip-label').textContent = d.label;
 document.getElementById('tooltip-type').textContent = `${d.object_type} · ${((d.importance || 0.5) * 100).toFixed(0)}%`;
 tooltip.classList.remove('hidden');
 // Position near mouse
 const container = document.getElementById('graph-canvas');
 const rect = container.getBoundingClientRect();
 const svgEl = document.getElementById('graph-svg');
 const pt = svgEl.createSVGPoint();
 pt.x = d.x; pt.y = d.y;
 const ctm = svgEl.querySelector('g')?.getCTM();
 if (ctm) {
 const transformed = pt.matrixTransform(ctm);
 tooltip.style.left = Math.min(transformed.x + 15, rect.width - 260) + 'px';
 tooltip.style.top = Math.min(transformed.y - 10, rect.height - 60) + 'px';
 }
 }
 } else {
 // Restore all
 d3.selectAll('.graph-node').classed('dimmed', false).classed('neighbor', false);
 d3.selectAll('.graph-edge-line')
 .classed('dimmed', false)
 .classed('highlighted', false)
 .attr('stroke', 'rgba(255,255,255,0.05)');

 // Hide tooltip
 if (tooltip) tooltip.classList.add('hidden');
 }
}

async function selectNode(d) {
 state.selectedNodeId = d.id;

 // Highlight
 d3.selectAll('.graph-node').classed('selected', false);
 d3.selectAll('.graph-node').filter(n => n.id === d.id).classed('selected', true);

 // Show detail panel
 const panel = document.getElementById('detail-panel');
 panel.classList.remove('hidden');

 document.getElementById('detail-label').textContent = d.label;

 const badge = document.getElementById('detail-type');
 badge.textContent = d.object_type;
 badge.style.background = (NODE_COLORS[d.node_family] || '#888') + '20';
 badge.style.color = NODE_COLORS[d.node_family] || '#888';

 // Fetch detail
 try {
 const res = await authFetch(`/api/graph/nodes/${d.id}`);
 const detail = await res.json();

 document.getElementById('detail-summary').textContent = detail.summary || t('detail.noSummary');

 // Metadata
 const metaGrid = document.getElementById('detail-metadata');
 metaGrid.innerHTML = `
 <span class="meta-key">Type</span><span class="meta-value">${detail.object_type}</span>
 <span class="meta-key">Importance</span><span class="meta-value">${(detail.importance * 100).toFixed(0)}%</span>
 <span class="meta-key">Freshness</span><span class="meta-value">${(detail.freshness * 100).toFixed(0)}%</span>
 `;

 // Relations
 const relDiv = document.getElementById('detail-relations');
 const allRels = [
 ...detail.outgoing.map(r => ({ ...r, dir: '→', label: r.target_label, type: r.edge_type })),
 ...detail.incoming.map(r => ({ ...r, dir: '←', label: r.source_label, type: r.edge_type })),
 ];

 if (allRels.length) {
 relDiv.innerHTML = allRels.slice(0, 10).map(r => `
 <div class="relation-item">
 <span>${r.dir}</span>
 <span style="flex:1">${r.label}</span>
 <span class="relation-type-label">${r.type}</span>
 </div>`).join('');
 } else {
 relDiv.innerHTML = `<span style="font-size:12px;color:var(--text-muted)">${getLang() === 'th' ? 'ไม่มีความสัมพันธ์' : 'No relations'}</span>`;
 }
 } catch (e) {
 console.error('Node detail error:', e);
 }
}

// ═══════════════════════════════════════════
// AI CHAT
// ═══════════════════════════════════════════
function initChat() {
 const input = document.getElementById('chat-input');
 const sendBtn = document.getElementById('btn-send');

 sendBtn?.addEventListener('click', sendMessage);
 input?.addEventListener('keydown', e => {
 if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
 });
}

let _chatBusy = false;
async function sendMessage() {
 if (_chatBusy) return; // Prevent double-send
 const input = document.getElementById('chat-input');
 const sendBtn = document.getElementById('btn-send');
 const question = input.value.trim();
 if (!question) return;
 
 _chatBusy = true;
 input.value = '';
 localStorage.setItem('pk_chat_used', '1');
 input.disabled = true;
 if (sendBtn) sendBtn.disabled = true;

 // Add user message
 addMessage(question, 'user');

 // Show loading
 const loadingId = addMessage(`<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังคิด...' : 'Thinking...'}`, 'assistant', true);

 try {
 const res = await authFetch('/api/chat', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ question }),
 });
 const data = await res.json();

 // Replace loading with answer
 removeMessage(loadingId);
 const msgHtml = `${data.answer}
 <div class="injection-badge"> ${data.injection_summary || 'Context injected'}</div>`;
 addMessage(msgHtml, 'assistant', true);

 // Update sources panel
 updateSourcesPanel(data);
 } catch (e) {
 removeMessage(loadingId);
 addMessage(getLang() === 'th' ? 'เกิดข้อผิดพลาดในการเชื่อมต่อ AI' : 'Error connecting to AI', 'assistant', true);
 } finally {
 _chatBusy = false;
 input.disabled = false;
 if (sendBtn) sendBtn.disabled = false;
 input.focus();
 }
}

let msgCounter = 0;
function addMessage(content, role, isHtml = false) {
 const id = `msg-${++msgCounter}`;
 const container = document.getElementById('chat-messages');
 const welcome = container.querySelector('.welcome-message');
 if (welcome) welcome.remove();

 const div = document.createElement('div');
 div.className = `message ${role}`;
 div.id = id;
 div.innerHTML = `<div class="message-bubble">${isHtml ? content : escapeHtml(content)}</div>`;
 container.appendChild(div);
 container.scrollTop = container.scrollHeight;
 return id;
}

function removeMessage(id) {
 document.getElementById(id)?.remove();
}

function updateSourcesPanel(data) {
 // Profile
 document.getElementById('src-profile').innerHTML = data.profile_used
 ? `<span class="source-chip"> ${getLang() === 'th' ? 'โปรไฟล์ถูกใช้' : 'Profile used'}</span>`
 : `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;

 // Packs
 const packs = data.context_packs_used || [];
 document.getElementById('src-packs').innerHTML = packs.length
 ? packs.map(p => `<span class="source-chip"> ${p.title}</span>`).join('')
 : `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;

 // Files
 const files = data.files_used || [];
 document.getElementById('src-files').innerHTML = files.length
 ? files.map(f => `<span class="source-chip"> ${f.filename}</span>`).join('')
 : `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;

 // Graph (v3)
 const nodesUsed = data.nodes_used || [];
 const edgesUsed = data.edges_used || [];
 if (nodesUsed.length || edgesUsed.length) {
 document.getElementById('src-graph').innerHTML =
 nodesUsed.map(n => `<span class="source-chip" style="border-color:${NODE_COLORS[n.type] || '#888'}33;color:${NODE_COLORS[n.type] || '#888'}"> ${n.label}</span>`).join('') +
 edgesUsed.map(e => `<span class="source-chip">↔ ${e.source} → ${e.target} (${e.type})</span>`).join('');
 } else {
 document.getElementById('src-graph').innerHTML = `<span style="color:var(--text-muted)">${getLang() === 'th' ? 'ไม่ได้ใช้' : 'Not used'}</span>`;
 }

 // Reasoning
 document.getElementById('src-reasoning').textContent = data.reasoning || '—';

 // Evidence Graph
 renderEvidenceGraph(data);
}

function renderEvidenceGraph(data) {
 const svg = d3.select('#evidence-graph-svg');
 svg.selectAll('*').remove();

 const files = data.files_used || [];
 const packs = data.context_packs_used || [];
 if (!files.length && !packs.length) return;

 const nodes = [];
 const edges = [];

 // Center: question
 nodes.push({ id: 'q', label: 'Question', family: 'entity', x: 140, y: 100 });

 files.forEach((f, i) => {
 const id = `f${i}`;
 nodes.push({ id, label: f.filename?.substring(0, 15) || f.id, family: 'source_file' });
 edges.push({ source: 'q', target: id });
 });

 packs.forEach((p, i) => {
 const id = `p${i}`;
 nodes.push({ id, label: p.title?.substring(0, 15) || p.id, family: 'context_pack' });
 edges.push({ source: 'q', target: id });
 });

 if (data.profile_used) {
 nodes.push({ id: 'prof', label: 'Profile', family: 'person' });
 edges.push({ source: 'q', target: 'prof' });
 }

 // Simple force simulation
 const sim = d3.forceSimulation(nodes)
 .force('link', d3.forceLink(edges).id(d => d.id).distance(50))
 .force('charge', d3.forceManyBody().strength(-60))
 .force('center', d3.forceCenter(140, 100))
 .stop();

 for (let i = 0; i < 100; i++) sim.tick();

 svg.selectAll('line')
 .data(edges)
 .join('line')
 .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
 .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
 .attr('stroke', 'rgba(255,255,255,0.15)')
 .attr('stroke-width', 1);

 const nodeG = svg.selectAll('g')
 .data(nodes)
 .join('g')
 .attr('transform', d => `translate(${d.x},${d.y})`);

 nodeG.append('circle')
 .attr('r', 6)
 .attr('fill', d => NODE_COLORS[d.family] || '#888')
 .attr('fill-opacity', 0.8);

 nodeG.append('text')
 .text(d => d.label)
 .attr('dy', 16)
 .attr('text-anchor', 'middle')
 .attr('fill', 'rgba(255,255,255,0.5)')
 .attr('font-size', '8px');
}

// ═══════════════════════════════════════════
// PROFILE (v6.0 — เพิ่ม 4 personality systems + history)
// ═══════════════════════════════════════════
const PERSONALITY_SYSTEMS = ['mbti', 'enneagram', 'clifton', 'via'];
let _personalityRef = null; // cached reference data — loaded ครั้งแรกที่เปิด modal

function initProfile() {
 document.getElementById('profile-trigger')?.addEventListener('click', async (e) => {
 e.preventDefault();
 document.getElementById('profile-modal').classList.remove('hidden');
 // โหลด reference data (cached) → fill dropdowns ครั้งเดียว → fetch profile
 await ensurePersonalityReference();
 await loadProfile();
 });

 document.getElementById('close-profile-modal')?.addEventListener('click', () => {
 document.getElementById('profile-modal').classList.add('hidden');
 });

 document.getElementById('btn-save-profile')?.addEventListener('click', saveProfile);

 // Enneagram core change → recalc valid wings (รวม wrap-around 9→1, 1→9)
 document.getElementById('enneagram-core')?.addEventListener('change', (e) => {
 updateEnneagramWingOptions(parseInt(e.target.value) || null);
 });

 // History modal — เปิดเมื่อคลิก ประวัติ ของแต่ละระบบ
 document.querySelectorAll('.btn-history').forEach(btn => {
 btn.addEventListener('click', () => openPersonalityHistory(btn.dataset.system));
 });
 document.getElementById('close-personality-history')?.addEventListener('click', () => {
 document.getElementById('personality-history-modal').classList.add('hidden');
 });
}

// ─── Reference data (cache ใน sessionStorage) ───
async function ensurePersonalityReference() {
 if (_personalityRef) return _personalityRef;
 // Cache key มี version เพื่อ invalidate ถ้า theme list เปลี่ยน (ดู plan: Notes for เขียว)
 const cacheKey = 'personality_ref_v1';
 const cached = sessionStorage.getItem(cacheKey);
 if (cached) {
 try {
 _personalityRef = JSON.parse(cached);
 populatePersonalityDropdowns(_personalityRef);
 return _personalityRef;
 } catch (e) {
 sessionStorage.removeItem(cacheKey);
 }
 }
 try {
 // endpoint นี้ public — ใช้ fetch ตรงเพื่อไม่ต้อง JWT
 const res = await fetch('/api/personality/reference');
 if (!res.ok) throw new Error('reference fetch failed');
 _personalityRef = await res.json();
 sessionStorage.setItem(cacheKey, JSON.stringify(_personalityRef));
 populatePersonalityDropdowns(_personalityRef);
 return _personalityRef;
 } catch (e) {
 console.error('Personality reference load failed:', e);
 return null;
 }
}

function populatePersonalityDropdowns(ref) {
 if (!ref) return;

 // MBTI types
 const mbtiSel = document.getElementById('mbti-type');
 if (mbtiSel && mbtiSel.options.length <= 1) {
 ref.mbti.types.forEach(t => {
 const opt = document.createElement('option');
 opt.value = t; opt.textContent = t;
 mbtiSel.appendChild(opt);
 });
 }

 // Enneagram cores (1-9 with TH/EN labels)
 const enCore = document.getElementById('enneagram-core');
 if (enCore && enCore.options.length <= 1) {
 Object.entries(ref.enneagram.types).forEach(([k, v]) => {
 const opt = document.createElement('option');
 opt.value = k;
 opt.textContent = `${k} — ${v.th} / ${v.en}`;
 enCore.appendChild(opt);
 });
 }

 // Clifton + VIA — populate <datalist> สำหรับ searchable dropdown
 ensureDatalist('clifton-themes-datalist', ref.clifton.all);
 ensureDatalist('via-strengths-datalist', ref.via.all);

 // Render 5 rank rows สำหรับ Clifton + VIA
 renderRankList('clifton-rank-list', 'clifton', 'clifton-themes-datalist');
 renderRankList('via-rank-list', 'via', 'via-strengths-datalist');

 // Test links
 renderTestLinks('mbti-test-links', ref.mbti.test_links);
 renderTestLinks('enneagram-test-links', ref.enneagram.test_links);
 renderTestLinks('clifton-test-links', ref.clifton.test_links);
 renderTestLinks('via-test-links', ref.via.test_links);
}

function ensureDatalist(id, options) {
 if (document.getElementById(id)) return;
 const dl = document.createElement('datalist');
 dl.id = id;
 options.forEach(name => {
 const opt = document.createElement('option');
 opt.value = name;
 dl.appendChild(opt);
 });
 document.body.appendChild(dl);
}

function renderRankList(containerId, system, datalistId) {
 const container = document.getElementById(containerId);
 if (!container || container.children.length > 0) return;
 for (let i = 1; i <= 5; i++) {
 const row = document.createElement('div');
 row.className = 'personality-rank-row';
 const label = document.createElement('span');
 label.className = 'personality-rank-label';
 label.textContent = `#${i}`;
 const input = document.createElement('input');
 input.type = 'text';
 input.id = `${system}-rank-${i}`;
 input.setAttribute('list', datalistId);
 input.placeholder = `อันดับ ${i}`;
 input.autocomplete = 'off';
 row.appendChild(label);
 row.appendChild(input);
 container.appendChild(row);
 }
}

function renderTestLinks(containerId, links) {
 const container = document.getElementById(containerId);
 if (!container) return;
 container.textContent = ''; // clear (ไม่ใช้ innerHTML ตามกฎ XSS)
 links.forEach(link => {
 const a = document.createElement('a');
 a.href = link.url;
 a.target = '_blank';
 a.rel = 'noopener noreferrer'; // กัน window.opener leak ตามกฎ plan
 a.className = 'test-link-chip ' + (link.cost === 'free' ? 'is-free' : 'is-paid');
 // ใช้ textContent กัน XSS + เพื่อ render "&" ใน "Appreciation of Beauty & Excellence" ถูก
 a.textContent = `↗ ${link.name} (${link.cost === 'free' ? 'ฟรี' : link.cost})`;
 if (link.note) a.title = link.note;
 container.appendChild(a);
 });
}

function updateEnneagramWingOptions(core) {
 const wingSel = document.getElementById('enneagram-wing');
 if (!wingSel) return;
 // Clear existing options เหลือเฉพาะ placeholder
 wingSel.textContent = '';
 const placeholder = document.createElement('option');
 placeholder.value = '';
 placeholder.textContent = '— ไม่ระบุ —';
 wingSel.appendChild(placeholder);

 if (!core) {
 wingSel.disabled = true;
 return;
 }
 // wrap-around: core=9 → wings (8,1), core=1 → wings (9,2)
 const left = core > 1 ? core - 1 : 9;
 const right = core < 9 ? core + 1 : 1;
 [left, right].forEach(w => {
 const opt = document.createElement('option');
 opt.value = String(w);
 opt.textContent = String(w);
 wingSel.appendChild(opt);
 });
 wingSel.disabled = false;
}

async function loadProfile() {
 try {
 const res = await authFetch('/api/profile');
 const p = await res.json();
 // Existing 5 text fields
 document.getElementById('profile-identity').value = p.identity_summary || '';
 document.getElementById('profile-goals').value = p.goals || '';
 document.getElementById('profile-style').value = p.working_style || '';
 document.getElementById('profile-output').value = p.preferred_output_style || '';
 document.getElementById('profile-background').value = p.background_context || '';

 // ─── v6.0 — Personality fields ───
 // MBTI
 if (p.mbti && p.mbti.type) {
 const parts = p.mbti.type.split('-');
 document.getElementById('mbti-type').value = parts[0] || '';
 document.getElementById('mbti-identity').value = parts[1] || '';
 document.getElementById('mbti-source').value = p.mbti.source || '';
 } else {
 document.getElementById('mbti-type').value = '';
 document.getElementById('mbti-identity').value = '';
 document.getElementById('mbti-source').value = '';
 }
 // Enneagram (recalc wing options ตาม core)
 if (p.enneagram && p.enneagram.core) {
 document.getElementById('enneagram-core').value = String(p.enneagram.core);
 updateEnneagramWingOptions(p.enneagram.core);
 document.getElementById('enneagram-wing').value = p.enneagram.wing ? String(p.enneagram.wing) : '';
 } else {
 document.getElementById('enneagram-core').value = '';
 updateEnneagramWingOptions(null);
 }
 // Clifton Top 5
 for (let i = 1; i <= 5; i++) {
 const inp = document.getElementById(`clifton-rank-${i}`);
 if (inp) inp.value = (p.clifton_top5 && p.clifton_top5[i - 1]) || '';
 }
 // VIA Top 5
 for (let i = 1; i <= 5; i++) {
 const inp = document.getElementById(`via-rank-${i}`);
 if (inp) inp.value = (p.via_top5 && p.via_top5[i - 1]) || '';
 }

 // อัปเดต history badges ของ 4 ระบบ (ขอ count ล่วงหน้าเพื่อตัดสินใจว่าจะแสดง badge)
 refreshAllHistoryCounts();

 // chat header indicator (เดิม) — รวม personality เป็น "Active" criterion ด้วย
 const isSet = !!(p.identity_summary || p.goals || p.mbti || p.enneagram || p.clifton_top5 || p.via_top5);
 const indicator = document.getElementById('chat-profile-status');
 if (indicator) indicator.textContent = isSet ? 'Active' : 'Not set';
 const dot = document.querySelector('.chat-header .profile-dot');
 if (dot) dot.className = `profile-dot ${isSet ? 'active' : ''}`;
 } catch (e) { console.error('Profile load error:', e); }
}

// ─── Input collectors (กลับ null = ไม่ส่ง field, undefined = clear ผ่าน null) ───
function getMbtiInput() {
 const type = document.getElementById('mbti-type').value;
 if (!type) return null;
 const identity = document.getElementById('mbti-identity').value;
 const source = document.getElementById('mbti-source').value || 'self_report';
 const fullType = identity ? `${type}-${identity}` : type;
 return { type: fullType, source };
}
function getEnneagramInput() {
 const core = parseInt(document.getElementById('enneagram-core').value);
 if (!core) return null;
 const wingRaw = document.getElementById('enneagram-wing').value;
 const wing = wingRaw ? parseInt(wingRaw) : null;
 return { core, wing };
}
function _collectRankInputs(system) {
 const out = [];
 for (let i = 1; i <= 5; i++) {
 const v = (document.getElementById(`${system}-rank-${i}`)?.value || '').trim();
 if (v) out.push(v);
 }
 return out;
}
function getCliftonInput() {
 const top5 = _collectRankInputs('clifton');
 if (top5.length === 0) return null;
 if (new Set(top5).size !== top5.length) {
 showToast('CliftonStrengths Top 5: ห้ามเลือกซ้ำ', 'error');
 return undefined; // sentinel — ห้าม save
 }
 return top5;
}
function getViaInput() {
 const top5 = _collectRankInputs('via');
 if (top5.length === 0) return null;
 if (new Set(top5).size !== top5.length) {
 showToast('VIA Top 5: ห้ามเลือกซ้ำ', 'error');
 return undefined;
 }
 return top5;
}

async function saveProfile() {
 const cliftonVal = getCliftonInput();
 const viaVal = getViaInput();
 // sentinel undefined = duplicate detected client-side → abort
 if (cliftonVal === undefined || viaVal === undefined) return;

 const data = {
 identity_summary: document.getElementById('profile-identity').value,
 goals: document.getElementById('profile-goals').value,
 working_style: document.getElementById('profile-style').value,
 preferred_output_style: document.getElementById('profile-output').value,
 background_context: document.getElementById('profile-background').value,
 // v6.0 — personality (ส่งทั้ง 4 เพื่อให้ partial-update detect การ clear/set ได้ครบ)
 mbti: getMbtiInput(),
 enneagram: getEnneagramInput(),
 clifton_top5: cliftonVal,
 via_top5: viaVal,
 };
 try {
 const res = await authFetch('/api/profile', {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(data),
 });
 if (!res.ok) {
 // backend ส่ง 400 พร้อม detail สำหรับ INVALID_MBTI_TYPE / INVALID_ENNEAGRAM_WING etc
 let msg = t('toast.error');
 try {
 const err = await res.json();
 if (err.detail) msg = ` ${err.detail}`;
 } catch (_) {}
 showToast(msg, 'error');
 return;
 }
 showToast(t('toast.profileSaved'), 'success');
 document.getElementById('profile-modal').classList.add('hidden');
 loadStats();
 } catch (e) { showToast(t('toast.error'), 'error'); }
}

// ═══════════════════════════════════════════
// PERSONALITY HISTORY (v6.0)
// ═══════════════════════════════════════════
async function refreshAllHistoryCounts() {
 // เรียกแค่ครั้งเดียวพอ — backend คืน count รวม ก็ใช้ได้ แต่เราต้องการแยก system → 4 fetch parallel
 await Promise.all(PERSONALITY_SYSTEMS.map(async (sys) => {
 try {
 const res = await authFetch(`/api/profile/personality/history?system=${sys}&limit=1`);
 if (!res.ok) return;
 const data = await res.json();
 // count=1 = มี history อย่างน้อย 1 entry → เราเรียก count แท้อีกที
 // เพื่อประหยัด — ขอ limit=200 (ซึ่งคือ max) แล้วเอา count
 const fullRes = await authFetch(`/api/profile/personality/history?system=${sys}&limit=200`);
 if (!fullRes.ok) return;
 const fullData = await fullRes.json();
 const badge = document.getElementById(`${sys}-history-count`);
 if (!badge) return;
 const c = fullData.count || 0;
 if (c > 0) {
 badge.textContent = String(c);
 badge.hidden = false;
 } else {
 badge.hidden = true;
 }
 } catch (_) { /* swallow — history badge ไม่ critical */ }
 }));
}

const SYSTEM_LABELS = {
 mbti: 'MBTI', enneagram: 'Enneagram',
 clifton: 'CliftonStrengths', via: 'VIA Character Strengths',
};

async function openPersonalityHistory(system) {
 const modal = document.getElementById('personality-history-modal');
 const title = document.getElementById('personality-history-title');
 const list = document.getElementById('personality-history-list');
 // Clear data เก่าก่อน fetch ใหม่ — กัน flash ตามกฎ plan
 list.textContent = '';
 title.textContent = ` ${getLang() === 'th' ? 'ประวัติ' : 'History'}: ${SYSTEM_LABELS[system] || system}`;
 modal.classList.remove('hidden');

 try {
 const res = await authFetch(`/api/profile/personality/history?system=${system}&limit=200`);
 if (!res.ok) {
 list.textContent = ' โหลดประวัติไม่สำเร็จ';
 return;
 }
 const data = await res.json();
 if (!data.history || data.history.length === 0) {
 const empty = document.createElement('p');
 empty.className = 'history-empty';
 empty.textContent = getLang() === 'th' ? 'ยังไม่มีประวัติ' : 'No history yet';
 list.appendChild(empty);
 return;
 }
 data.history.forEach(entry => {
 list.appendChild(renderHistoryEntry(system, entry));
 });
 } catch (e) {
 list.textContent = ' Error: ' + (e.message || e);
 }
}

function renderHistoryEntry(system, entry) {
 const div = document.createElement('div');
 div.className = 'history-entry';

 // Date
 const dateEl = document.createElement('div');
 dateEl.className = 'history-date';
 const dt = entry.recorded_at ? new Date(entry.recorded_at) : null;
 dateEl.textContent = dt ? ' ' + dt.toLocaleString('th-TH') : ' —';
 div.appendChild(dateEl);

 // Value (ใช้ textContent กัน XSS + render "&" ใน VIA ได้ถูก)
 const valEl = document.createElement('div');
 valEl.className = 'history-value';
 valEl.textContent = formatHistoryValue(system, entry.data);
 div.appendChild(valEl);

 // Source
 const srcEl = document.createElement('div');
 srcEl.className = 'history-source';
 const srcLabel = entry.source === 'mcp_update'
 ? (getLang() === 'th' ? 'อัปเดตจาก: Claude/Antigravity (MCP)' : 'Updated via: Claude/Antigravity (MCP)')
 : (getLang() === 'th' ? 'อัปเดตจาก: เว็บไซต์ Personal Data Bank' : 'Updated via: Personal Data Bank web');
 srcEl.textContent = srcLabel;
 div.appendChild(srcEl);

 return div;
}

function formatHistoryValue(system, data) {
 if (!data) return '—';
 if (data.cleared) return getLang() === 'th' ? ' ล้างค่า' : ' Cleared';
 if (system === 'mbti') {
 return `${data.type || '—'} (${data.source || 'self_report'})`;
 }
 if (system === 'enneagram') {
 const wing = data.wing ? `w${data.wing}` : '';
 return `${data.core}${wing}`;
 }
 if (system === 'clifton' || system === 'via') {
 const list = data.top5 || [];
 return list.join(', ');
 }
 return JSON.stringify(data);
}

// ═══════════════════════════════════════════
// UTILITIES
// ═══════════════════════════════════════════
function showToast(message, type = 'info') {
 const container = document.getElementById('toast-container');
 const toast = document.createElement('div');
 toast.className = `toast ${type}`;
 toast.textContent = message;
 container.appendChild(toast);
 setTimeout(() => toast.remove(), 4000);
}

function showConfirm(message) {
 return new Promise(resolve => {
 const modal = document.getElementById('confirm-modal');
 document.getElementById('confirm-message').textContent = message;
 modal.classList.remove('hidden');

 const ok = document.getElementById('confirm-ok');
 const cancel = document.getElementById('confirm-cancel');

 const cleanup = (result) => {
 modal.classList.add('hidden');
 ok.removeEventListener('click', onOk);
 cancel.removeEventListener('click', onCancel);
 resolve(result);
 };

 const onOk = () => cleanup(true);
 const onCancel = () => cleanup(false);

 ok.addEventListener('click', onOk);
 cancel.addEventListener('click', onCancel);
 });
}

function escapeHtml(text) {
 const div = document.createElement('div');
 div.textContent = text;
 return div.innerHTML;
}

// ═══════════════════════════════════════════
// MCP / CONNECTOR LAYER (v4)
// ═══════════════════════════════════════════

function initMCP() {
 // MCP Setup page
 const labelInput = document.getElementById('mcp-token-label');
 labelInput?.addEventListener('focus', () => {
 if (labelInput.value === 'Claude Connector') labelInput.value = '';
 });

 document.getElementById('btn-copy-url')?.addEventListener('click', () => {
 const url = document.getElementById('mcp-url-value')?.textContent;
 if (url && url !== 'Loading...') copyToClipboard(url);
 });

 document.getElementById('btn-generate-token')?.addEventListener('click', generateMCPToken);

 document.getElementById('btn-copy-token')?.addEventListener('click', () => {
 const token = document.getElementById('mcp-token-value')?.textContent;
 if (token) copyToClipboard(token);
 });

 document.getElementById('btn-copy-config')?.addEventListener('click', () => {
 const config = document.getElementById('mcp-config-json')?.textContent;
 if (config && config !== 'Loading...') copyToClipboard(config);
 });

 document.getElementById('btn-test-connection')?.addEventListener('click', testMCPConnection);

 // Token Management page
 document.getElementById('btn-new-token')?.addEventListener('click', () => {
 switchPage('mcp-setup');
 document.getElementById('mcp-token-label')?.focus();
 });

 // MCP Logs page
 document.getElementById('btn-refresh-logs')?.addEventListener('click', loadMCPLogs);
 document.getElementById('log-filter-tool')?.addEventListener('change', loadMCPLogs);
 document.getElementById('log-filter-status')?.addEventListener('change', loadMCPLogs);
}


// ─── MCP SETUP PAGE ───

// Platform tab switcher (v5.3)
function switchMcpTab(platform) {
 // Toggle tab buttons
 document.querySelectorAll('.mcp-tab').forEach(t => t.classList.remove('active'));
 document.getElementById(`tab-${platform}`)?.classList.add('active');
 // Toggle panels
 document.querySelectorAll('.mcp-tab-content').forEach(p => p.classList.remove('active'));
 document.getElementById(`panel-${platform}`)?.classList.add('active');
}

async function loadMCPSetup() {
 try {
 // Load MCP info
 const res = await authFetch('/api/mcp/info');
 const info = await res.json();
 state.mcpInfo = info;

 // Set server URL — use the secured connector URL with secret
 const connectorUrl = info.mcp_connector_url || info.mcp_server_url;
 document.getElementById('mcp-url-value').textContent = connectorUrl;

 // Build config JSON — simplified for Claude Custom Connector
 const configObj = {
 "mcpServers": {
 "personal-data-bank": {
 "url": connectorUrl
 }
 }
 };
 document.getElementById('mcp-config-json').textContent = JSON.stringify(configObj, null, 2);

 // Build Antigravity config — uses mcp-remote bridge (v5.3)
 const agConfigObj = {
 "mcpServers": {
 "personal-data-bank": {
 "command": "npx",
 "args": ["-y", "mcp-remote@latest", connectorUrl]
 }
 }
 };
 const agEl = document.getElementById('mcp-config-antigravity');
 if (agEl) agEl.textContent = JSON.stringify(agConfigObj, null, 2);

 // Copy button for Antigravity config
 document.getElementById('btn-copy-config-ag')?.addEventListener('click', () => {
 const config = document.getElementById('mcp-config-antigravity')?.textContent;
 if (config) navigator.clipboard.writeText(config);
 showToast(t('toast.copied'));
 });

 // Render available tools
 const tools = info.available_tools || [];
 renderMCPTools(tools);
 const countEl = document.getElementById('mcp-tools-count');
 if (countEl) countEl.textContent = tools.length;

 // Check token status
 const tokRes = await authFetch('/api/mcp/tokens');
 const tokData = await tokRes.json();
 const activeTokens = (tokData.tokens || []).filter(t => t.is_active);

 const statusDot = document.getElementById('mcp-status-dot');
 const statusText = document.getElementById('mcp-status-text');
 const statusMeta = document.getElementById('mcp-status-meta');

 if (activeTokens.length > 0) {
 statusDot.className = 'mcp-status-dot active';
 statusText.textContent = t('mcp.configured');
 statusMeta.textContent = `${activeTokens.length} ${activeTokens.length === 1 ? 'token' : 'tokens'} · ${info.scope}`;
 } else {
 statusDot.className = 'mcp-status-dot active';
 statusText.textContent = t('mcp.configured');
 statusMeta.textContent = `secured · ${info.scope}`;
 }

 } catch (e) {
 console.error('MCP setup load error:', e);
 }
}

function renderMCPTools(tools) {
 const grid = document.getElementById('mcp-tools-grid');
 if (!grid) return;

 const toolIcons = {
 'get_profile': '', 'list_files': '', 'get_file_content': '',
 'get_file_summary': '', 'list_collections': '', 'list_context_packs': '',
 'get_context_pack': '', 'search_knowledge': '', 'explore_graph': '',
 'create_context_pack': '', 'add_note': '', 'update_file_tags': '',
 'get_overview': '',
 'admin_login': '', 'delete_file': '', 'delete_pack': '',
 'run_organize': '', 'build_graph': '', 'enrich_metadata': '',
 'update_profile': '', 'upload_text': '',
 };

 const categoryLabels = {
 read: { icon: '', en: 'Read & Search', th: 'อ่านและค้นหา' },
 edit: { icon: '', en: 'Create & Edit', th: 'สร้างและแก้ไข' },
 delete: { icon: '', en: 'Delete', th: 'ลบข้อมูล' },
 pipeline: { icon: '', en: 'AI Pipeline', th: 'ประมวลผล AI' },
 };

 // Group tools by category
 const groups = {};
 tools.forEach(tool => {
 const cat = tool.category || 'other';
 if (!groups[cat]) groups[cat] = [];
 groups[cat].push(tool);
 });

 // Load saved permissions
 const savedPerms = JSON.parse(localStorage.getItem('mcp_tool_permissions') || '{}');

 let html = '';
 const order = ['read', 'edit', 'delete', 'pipeline'];
 for (const cat of order) {
 if (!groups[cat]) continue;
 const label = categoryLabels[cat] || { icon: '', en: cat, th: cat };
 const langLabel = getLang() === 'th' ? label.th : label.en;

 html += `<div class="mcp-tools-category">
 <div class="mcp-category-header">
 <span>${label.icon} ${langLabel}</span>
 <span class="badge">${groups[cat].length}</span>
 </div>`;

 groups[cat].forEach(tool => {
 const isEnabled = savedPerms[tool.name] !== false; // default: enabled
 const toolDesc = t(`tool.${tool.name}`) !== `tool.${tool.name}` ? t(`tool.${tool.name}`) : tool.description;
 html += `
 <div class="mcp-tool-card ${!isEnabled ? 'disabled' : ''}">
 <div class="mcp-tool-header">
 <span class="mcp-tool-icon">${toolIcons[tool.name] || ''}</span>
 <code class="mcp-tool-name">${tool.name}</code>
 <label class="toggle-switch">
 <input type="checkbox" ${isEnabled ? 'checked' : ''} onchange="toggleToolPermission('${tool.name}', this.checked)">
 <span class="toggle-slider"></span>
 </label>
 </div>
 <p class="mcp-tool-desc">${toolDesc}</p>
 ${tool.params && tool.params.length ? `
 <div class="mcp-tool-params">
 ${tool.params.filter(p => p.name !== 'admin_key').map(p => `<span class="mcp-param-chip">${p.name}: ${p.type}${p.required ? ' *' : ''}</span>`).join('')}
 </div>
 ` : ''}
 </div>`;
 });

 html += '</div>';
 }

 grid.innerHTML = html;
}

function toggleToolPermission(toolName, enabled) {
 const perms = JSON.parse(localStorage.getItem('mcp_tool_permissions') || '{}');
 perms[toolName] = enabled;
 localStorage.setItem('mcp_tool_permissions', JSON.stringify(perms));

 // Save to backend
 authFetch('/api/mcp/permissions', {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ permissions: perms }),
 }).catch(e => console.error('Save permissions error:', e));

 // Toggle card look
 // Re-render after toggle for clean state
 const label = enabled ? t('mcp.toolEnabled') : t('mcp.toolDisabled');
 showToast(`${toolName}: ${label}`, enabled ? 'success' : 'info');

 // Re-render
 if (state.mcpInfo) renderMCPTools(state.mcpInfo.available_tools || []);
}


async function generateMCPToken() {
 const labelInput = document.getElementById('mcp-token-label');
 const label = labelInput?.value?.trim() || 'Claude Connector';

 const btn = document.getElementById('btn-generate-token');
 btn.disabled = true;
 btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังสร้าง...' : 'Generating...'}`;

 try {
 const res = await authFetch('/api/mcp/tokens', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ label }),
 });
 const data = await res.json();

 if (data.raw_token) {
 state.mcpLastToken = data.raw_token;

 // Show token display
 const display = document.getElementById('mcp-token-display');
 display.classList.remove('hidden');
 document.getElementById('mcp-token-value').textContent = data.raw_token;

 // Update config JSON with real token
 if (state.mcpInfo) {
 const configObj = {
 "mcpServers": {
 "personal-data-bank": {
 "url": state.mcpInfo.mcp_server_url,
 "headers": {
 "Authorization": `Bearer ${data.raw_token}`
 }
 }
 }
 };
 document.getElementById('mcp-config-json').textContent = JSON.stringify(configObj, null, 2);
 }

 showToast(t('toast.tokenGenerated'), 'success');
 loadStats();
 loadMCPSetup();
 }
 } catch (e) {
 showToast(t('toast.error'), 'error');
 }

 btn.disabled = false;
 btn.innerHTML = `<span data-i18n="mcp.generateToken">${t('mcp.generateToken')}</span>`;
}


async function testMCPConnection() {
 const btn = document.getElementById('btn-test-connection');
 const resultDiv = document.getElementById('mcp-test-result');

 // Need a token to test — check state first, then fallback to displayed token
 let token = state.mcpLastToken;
 if (!token) {
 // Try to get from the token display element (if user just generated one)
 const tokenEl = document.getElementById('mcp-token-display');
 if (tokenEl) token = tokenEl.textContent.trim();
 }

 if (!token || !token.startsWith('pk_')) {
 resultDiv.classList.remove('hidden');
 resultDiv.className = 'mcp-test-result warning';
 resultDiv.innerHTML = `<span class="test-icon"></span> <span>${getLang() === 'th' ? 'กรุณาสร้าง token ก่อน (ขั้นตอนที่ 2)' : 'Please generate a token first (Step 2)'}</span>`;
 return;
 }

 btn.disabled = true;
 btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'ทดสอบ...' : 'Testing...'}`;

 try {
 // IMPORTANT: Use fetch() NOT authFetch() — we need to send the MCP token
 // as the Authorization header, not the user's JWT token
 const res = await fetch('/api/mcp/test', {
 method: 'POST',
 headers: { 'Authorization': `Bearer ${token}` },
 });
 const data = await res.json();

 resultDiv.classList.remove('hidden');
 if (data.status === 'success') {
 resultDiv.className = 'mcp-test-result success';
 resultDiv.innerHTML = `<span class="test-icon"></span> <span>${t('toast.testSuccess')} — ${data.token_label} (${data.scope})</span>`;
 showToast(t('toast.testSuccess'), 'success');
 } else {
 resultDiv.className = 'mcp-test-result error';
 resultDiv.innerHTML = `<span class="test-icon"></span> <span>${data.message || t('toast.testFailed')}</span>`;
 showToast(t('toast.testFailed'), 'error');
 }
 } catch (e) {
 resultDiv.classList.remove('hidden');
 resultDiv.className = 'mcp-test-result error';
 resultDiv.innerHTML = `<span class="test-icon"></span> <span>${t('toast.testFailed')}: ${e.message}</span>`;
 }

 btn.disabled = false;
 btn.innerHTML = `<span data-i18n="mcp.testConnection">${t('mcp.testConnection')}</span>`;
}


function copyToClipboard(text) {
 navigator.clipboard.writeText(text).then(() => {
 showToast(t('toast.copied'), 'success');
 }).catch(() => {
 // Fallback
 const ta = document.createElement('textarea');
 ta.value = text;
 document.body.appendChild(ta);
 ta.select();
 document.execCommand('copy');
 ta.remove();
 showToast(t('toast.copied'), 'success');
 });
}


// ─── TOKEN MANAGEMENT PAGE ───

async function loadTokens() {
 try {
 const res = await authFetch('/api/mcp/tokens');
 const data = await res.json();
 renderTokenList(data.tokens || []);
 } catch (e) {
 console.error('Load tokens error:', e);
 }
}

function renderTokenList(tokens) {
 const container = document.getElementById('token-list');
 if (!tokens.length) {
 container.innerHTML = `<div class="empty-state"><p>${t('tokens.empty')}</p></div>`;
 return;
 }

 container.innerHTML = tokens.map(tok => {
 const isActive = tok.is_active;
 const statusClass = isActive ? 'active' : 'revoked';
 const statusLabel = isActive ? t('tokens.active') : t('tokens.revoked');
 const lastUsed = tok.last_used_at ? formatTimeAgo(tok.last_used_at) : t('tokens.never');
 const created = tok.created_at ? formatDate(tok.created_at) : '—';

 return `
 <div class="token-card ${statusClass}">
 <div class="token-card-header">
 <div class="token-card-label">
 <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
 <span>${tok.label}</span>
 </div>
 <span class="token-status-pill ${statusClass}">${statusLabel}</span>
 </div>
 <div class="token-card-meta">
 <div class="token-meta-item">
 <span class="token-meta-label">${t('tokens.created')}</span>
 <span class="token-meta-value">${created}</span>
 </div>
 <div class="token-meta-item">
 <span class="token-meta-label">${t('tokens.lastUsed')}</span>
 <span class="token-meta-value">${lastUsed}</span>
 </div>
 <div class="token-meta-item">
 <span class="token-meta-label">Scope</span>
 <span class="token-meta-value">${tok.scope}</span>
 </div>
 </div>
 ${isActive ? `
 <div class="token-card-actions">
 <button class="btn btn-sm btn-danger-outline" onclick="revokeTokenAction('${tok.id}')">
 <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg>
 ${t('tokens.revoke')}
 </button>
 </div>
 ` : `
 <div class="token-card-actions">
 <span class="token-revoked-info">${tok.revoked_at ? formatDate(tok.revoked_at) : ''}</span>
 </div>
 `}
 </div>
 `;
 }).join('');
}

async function revokeTokenAction(tokenId) {
 if (!await showConfirm(t('tokens.confirmRevoke'))) return;

 try {
 await authFetch(`/api/mcp/tokens/${tokenId}`, { method: 'DELETE' });
 showToast(t('toast.tokenRevoked'), 'success');
 loadTokens();
 loadStats();
 } catch (e) {
 showToast(t('toast.error'), 'error');
 }
}


// ─── MCP LOGS PAGE ───

async function loadMCPLogs() {
 const toolFilter = document.getElementById('log-filter-tool')?.value || '';
 const statusFilter = document.getElementById('log-filter-status')?.value || '';

 let url = '/api/mcp/logs?limit=100';
 if (toolFilter) url += `&tool=${toolFilter}`;
 if (statusFilter) url += `&status=${statusFilter}`;

 try {
 const res = await authFetch(url);
 const data = await res.json();
 renderMCPLogs(data.logs || []);
 } catch (e) {
 console.error('Load MCP logs error:', e);
 }
}

function renderMCPLogs(logs) {
 const tbody = document.getElementById('log-table-body');
 if (!logs.length) {
 tbody.innerHTML = `
 <tr class="log-empty-row">
 <td colspan="5">
 <div class="empty-state"><p>${t('logs.empty')}</p></div>
 </td>
 </tr>`;
 return;
 }

 const toolIcons = {
 'get_profile': '',
 'list_context_packs': '',
 'get_context_pack': '',
 'search_knowledge': '',
 'get_file_summary': '',
 };

 tbody.innerHTML = logs.map(log => {
 const isError = log.status === 'error';
 const icon = toolIcons[log.tool_name] || '';
 const time = log.created_at ? formatDateTime(log.created_at) : '—';
 const details = isError ? log.error_message : (log.request_summary || '—');

 return `
 <tr class="${isError ? 'log-row-error' : ''}">
 <td class="log-time">${time}</td>
 <td>
 <span class="log-tool-chip">${icon} ${log.tool_name}</span>
 </td>
 <td>
 <span class="log-status-pill ${log.status}">${log.status}</span>
 </td>
 <td class="log-latency">${log.latency_ms}ms</td>
 <td class="log-details" title="${escapeHtml(details)}">${escapeHtml(details).substring(0, 60)}${details.length > 60 ? '…' : ''}</td>
 </tr>
 `;
 }).join('');
}


// ─── TIME FORMATTING HELPERS ───

function formatDate(isoStr) {
 try {
 const d = new Date(isoStr);
 return d.toLocaleDateString(getLang() === 'th' ? 'th-TH' : 'en-US', {
 month: 'short', day: 'numeric', year: 'numeric'
 });
 } catch { return isoStr; }
}

function formatDateTime(isoStr) {
 try {
 const d = new Date(isoStr);
 return d.toLocaleString(getLang() === 'th' ? 'th-TH' : 'en-US', {
 month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
 });
 } catch { return isoStr; }
}

function formatTimeAgo(isoStr) {
 try {
 const d = new Date(isoStr);
 const now = new Date();
 const diffMs = now - d;
 const diffMins = Math.floor(diffMs / 60000);
 const diffHrs = Math.floor(diffMs / 3600000);
 const diffDays = Math.floor(diffMs / 86400000);

 if (diffMins < 1) return getLang() === 'th' ? 'เมื่อกี้' : 'Just now';
 if (diffMins < 60) return `${diffMins}m ago`;
 if (diffHrs < 24) return `${diffHrs}h ago`;
 if (diffDays < 7) return `${diffDays}d ago`;
 return formatDate(isoStr);
 } catch { return isoStr; }
}


// ═══════════════════════════════════════════
// CONTEXT MEMORY — v5.5 (OpenClaw-inspired)
// ═══════════════════════════════════════════

let _ctxCache = [];
let _ctxViewId = null;

async function loadContexts() {
 const grid = document.getElementById('ctx-grid');
 if (!grid) return;

 const search = document.getElementById('ctx-search')?.value || '';
 const ctxType = document.getElementById('ctx-filter-type')?.value || '';

 let url = `/api/contexts?limit=50`;
 if (search) url += `&search=${encodeURIComponent(search)}`;
 if (ctxType) url += `&context_type=${encodeURIComponent(ctxType)}`;

 try {
 const res = await authFetch(url);
 const data = await res.json();
 _ctxCache = data.contexts || [];

 if (_ctxCache.length === 0) {
 grid.innerHTML = `<div class="empty-state"><p> ยังไม่มี Context — AI จะเริ่มบันทึกให้อัตโนมัติเมื่อคุณใช้งาน</p></div>`;
 return;
 }

 // Sort: pinned first, then by updated_at
 const sorted = [..._ctxCache].sort((a, b) => {
 if (a.is_pinned && !b.is_pinned) return -1;
 if (!a.is_pinned && b.is_pinned) return 1;
 return new Date(b.updated_at) - new Date(a.updated_at);
 });

 grid.innerHTML = sorted.map(c => _renderCtxCard(c)).join('');
 } catch (err) {
 console.error('loadContexts error:', err);
 }
}

function _renderCtxCard(c) {
 const typeLabels = { conversation: ' สนทนา', project: ' โปรเจกต์', task: ' งาน', note: ' บันทึก' };
 const label = typeLabels[c.context_type] || ' อื่นๆ';
 const pinnedClass = c.is_pinned ? ' pinned' : '';
 const pinIcon = c.is_pinned ? '' : '';
 const tags = (c.tags || []).slice(0, 4).map(t => `<span class="ctx-tag">${escapeHtml(t)}</span>`).join('');
 const time = c.updated_at ? formatTimeAgo(c.updated_at) : '';
 const summary = escapeHtml(c.summary || '').substring(0, 180);
 const cid = c.context_id;

 return `<div class="ctx-card${pinnedClass}" onclick="viewContext('${cid}')">
 <div class="ctx-card-header">
 <span class="ctx-card-title">${escapeHtml(c.title)}</span>
 ${pinIcon ? `<span class="ctx-pin-badge">${pinIcon}</span>` : ''}
 </div>
 <div class="ctx-card-summary">${summary}</div>
 <div class="ctx-card-meta">
 <span class="ctx-type-badge ${c.context_type}">${label}</span>
 ${tags}
 <span class="ctx-card-time">${time}</span>
 </div>
 </div>`;
}

// ─── View Context (full content) ───
async function viewContext(id) {
 const c = _ctxCache.find(x => x.context_id === id);
 if (!c) return;
 _ctxViewId = id;

 const titleEl = document.getElementById('ctx-view-title');
 const bodyEl = document.getElementById('ctx-view-body');

 titleEl.textContent = c.title || 'Context';

 try {
 const res = await authFetch(`/api/contexts/${id}`);
 const data = await res.json();
 // API returns full context object directly (not wrapped in contexts[])
 const content = data.content || data.contexts?.[0]?.content || c.summary || 'ไม่มีเนื้อหา';
 bodyEl.textContent = content;
 } catch (e) {
 bodyEl.textContent = c.summary || 'ไม่มีเนื้อหา';
 }

 document.getElementById('ctx-view-modal').classList.remove('hidden');
}

// ─── Create / Edit Modal ───
function openCtxModal(editId) {
 const modal = document.getElementById('ctx-modal');
 document.getElementById('ctx-edit-id').value = editId || '';
 document.getElementById('ctx-input-title').value = '';
 document.getElementById('ctx-input-content').value = '';
 document.getElementById('ctx-input-type').value = 'conversation';
 document.getElementById('ctx-input-tags').value = '';
 document.getElementById('ctx-input-pinned').checked = false;

 if (editId) {
 document.getElementById('ctx-modal-title').textContent = ' แก้ไข Context';
 const c = _ctxCache.find(x => x.context_id === editId);
 if (c) {
 document.getElementById('ctx-input-title').value = c.title || '';
 document.getElementById('ctx-input-type').value = c.context_type || 'conversation';
 document.getElementById('ctx-input-tags').value = (c.tags || []).join(', ');
 document.getElementById('ctx-input-pinned').checked = c.is_pinned || false;
 // Load full content
 authFetch(`/api/contexts/${editId}`)
 .then(r => r.json())
 .then(data => {
 const content = data.content || data.contexts?.[0]?.content || '';
 document.getElementById('ctx-input-content').value = content;
 })
 .catch(() => {});
 }
 } else {
 document.getElementById('ctx-modal-title').textContent = ' สร้าง Context ใหม่';
 }

 modal.classList.remove('hidden');
}

function editContext(id) { openCtxModal(id); }

async function saveCtxModal() {
 const editId = document.getElementById('ctx-edit-id').value;
 const title = document.getElementById('ctx-input-title').value.trim();
 const content = document.getElementById('ctx-input-content').value.trim();
 const ctxType = document.getElementById('ctx-input-type').value;
 const tagsStr = document.getElementById('ctx-input-tags').value;
 const isPinned = document.getElementById('ctx-input-pinned').checked;
 const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

 if (!title) {
 showToast('กรุณาใส่ชื่อ Context', 'error');
 return;
 }

 try {
 let res;
 if (editId) {
 res = await authFetch(`/api/contexts/${editId}`, {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ title, content, context_type: ctxType, tags, is_pinned: isPinned }),
 });
 } else {
 res = await authFetch('/api/contexts', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ title, content, context_type: ctxType, tags, is_pinned: isPinned }),
 });
 }
 if (!res.ok) {
 const err = await res.json();
 showToast(err.detail || 'เกิดข้อผิดพลาด', 'error');
 return;
 }
 document.getElementById('ctx-modal').classList.add('hidden');
 showToast(editId ? ' อัปเดต Context แล้ว' : ' สร้าง Context ใหม่แล้ว', 'success');
 loadContexts();
 } catch (e) {
 showToast('เกิดข้อผิดพลาด: ' + e.message, 'error');
 }
}

async function togglePin(id, pinState) {
 try {
 const res = await authFetch(`/api/contexts/${id}`, {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ is_pinned: pinState }),
 });
 if (!res.ok) {
 const err = await res.json();
 showToast(err.detail || err.message || 'Pin ไม่สำเร็จ — สูงสุด 3 อัน', 'error');
 return;
 }
 showToast(pinState ? ' ปักหมุดแล้ว' : ' ถอดหมุดแล้ว', 'success');
 loadContexts();
 } catch (e) {
 showToast('เกิดข้อผิดพลาด', 'error');
 }
}

async function deleteCtx(id) {
 const ok = await showConfirm(getLang() === 'th' ? 'ลบ Context นี้ถาวร?' : 'Delete this context permanently?');
 if (!ok) return;

 try {
 await authFetch(`/api/contexts/${id}`, { method: 'DELETE' });
 document.getElementById('ctx-view-modal')?.classList.add('hidden');
 showToast(' ลบ Context แล้ว', 'success');
 loadContexts();
 } catch (e) {
 showToast('ลบไม่สำเร็จ', 'error');
 }
}

// ─── Event Listeners ───
document.addEventListener('DOMContentLoaded', () => {
 // Search & filter with debounce
 let _ctxSearchTimer;
 document.getElementById('ctx-search')?.addEventListener('input', () => {
 clearTimeout(_ctxSearchTimer);
 _ctxSearchTimer = setTimeout(loadContexts, 400);
 });
 document.getElementById('ctx-filter-type')?.addEventListener('change', loadContexts);

 // Create button
 document.getElementById('btn-new-context')?.addEventListener('click', () => openCtxModal());

 // Modal controls
 document.getElementById('ctx-modal-close')?.addEventListener('click', () => document.getElementById('ctx-modal').classList.add('hidden'));
 document.getElementById('ctx-modal-cancel')?.addEventListener('click', () => document.getElementById('ctx-modal').classList.add('hidden'));
 document.getElementById('ctx-modal-save')?.addEventListener('click', saveCtxModal);

 // View modal controls
 document.getElementById('ctx-view-close')?.addEventListener('click', () => document.getElementById('ctx-view-modal').classList.add('hidden'));
 document.getElementById('ctx-view-edit')?.addEventListener('click', () => {
 document.getElementById('ctx-view-modal').classList.add('hidden');
 if (_ctxViewId) editContext(_ctxViewId);
 });
 document.getElementById('ctx-view-delete')?.addEventListener('click', () => {
 if (_ctxViewId) deleteCtx(_ctxViewId);
 });

 // Close modals on overlay click
 ['ctx-modal', 'ctx-view-modal'].forEach(mid => {
 document.getElementById(mid)?.addEventListener('click', (e) => {
 if (e.target.classList.contains('modal-overlay')) e.target.classList.add('hidden');
 });
 });
});



// ═══════════════════════════════════════════
// GUIDE SYSTEM — Simple Text + Images
// ═══════════════════════════════════════════

function initGuideSystem() {
 const fab = document.getElementById('guide-fab');
 const drawer = document.getElementById('guide-drawer');
 const overlay = document.getElementById('guide-overlay');
 const closeBtn = document.getElementById('guide-close');
 if (!fab || !drawer) return;

 fab.style.display = 'flex';
 fab.addEventListener('click', openGuide);
 closeBtn?.addEventListener('click', closeGuide);
 overlay?.addEventListener('click', closeGuide);
 document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeGuide(); });

 document.querySelectorAll('.guide-tab').forEach(tab => {
 tab.addEventListener('click', () => {
 document.querySelectorAll('.guide-tab').forEach(t => t.classList.remove('active'));
 tab.classList.add('active');
 renderGuideTab(tab.dataset.tab);
 });
 });

 renderGuideTab('usage');
}

function openGuide() {
 const drawer = document.getElementById('guide-drawer');
 const overlay = document.getElementById('guide-overlay');
 if (!drawer) return;
 overlay.style.display = 'block';
 drawer.style.display = 'flex';
 requestAnimationFrame(() => { drawer.classList.add('open'); });
}

function closeGuide() {
 const drawer = document.getElementById('guide-drawer');
 const overlay = document.getElementById('guide-overlay');
 if (!drawer) return;
 drawer.classList.remove('open');
 setTimeout(() => { drawer.style.display = 'none'; overlay.style.display = 'none'; }, 300);
}

function renderGuideTab(tab) {
 const el = document.getElementById('guide-content');
 if (!el) return;

 if (tab === 'usage') {
 el.innerHTML = `
 <div class="guide-section">
 <h3> ข้อมูลของฉัน</h3>
 <div class="guide-item">
 <strong> อัปโหลดไฟล์</strong>
 <p>ลากไฟล์มาวางในกรอบ หรือคลิกเพื่อเลือกไฟล์ รองรับ PDF, TXT, MD, DOCX (สูงสุด 20 MB)</p>
 </div>
 <div class="guide-item">
 <strong> จัดระเบียบไฟล์ใหม่</strong>
 <p>AI วิเคราะห์เฉพาะไฟล์ที่เพิ่งอัปโหลด สร้างสรุป แท็ก และจัดกลุ่มอัตโนมัติ เร็วกว่าจัดทั้งหมด</p>
 </div>
 <div class="guide-item">
 <strong> จัดระเบียบทั้งหมด</strong>
 <p>รีเซ็ตและจัดกลุ่มไฟล์ทั้งหมดใหม่ตั้งแต่ต้น ใช้เมื่อต้องการอัปเดตโครงสร้างทั้งระบบ</p>
 </div>
 <div class="guide-item">
 <strong> ดูรายละเอียด/แก้สรุป</strong>
 <p>คลิกที่ไฟล์เพื่อดูสรุป AI, key topics, key facts แก้ไขสรุปได้ตามต้องการ</p>
 </div>
 </div>

 <div class="guide-section">
 <h3> มุมมองความรู้</h3>
 <div class="guide-item">
 <strong> คอลเลกชัน</strong>
 <p>ดูกลุ่มเอกสารที่ AI จัดให้อัตโนมัติ แต่ละกลุ่มมีชื่อและสรุปเนื้อหา</p>
 </div>
 <div class="guide-item">
 <strong> Context Packs</strong>
 <p>สร้างชุดความรู้สำหรับแชร์หรือใช้กับ AI หลายแพลตฟอร์ม</p>
 </div>
 </div>

 <div class="guide-section">
 <h3> กราฟความรู้</h3>
 <div class="guide-item">
 <strong> มุมมอง Global</strong>
 <p>เห็นภาพรวมความเชื่อมโยงของเอกสารทั้งหมด ซูมเข้า-ออก ลากจัดตำแหน่งได้</p>
 </div>
 <div class="guide-item">
 <strong> มุมมอง Local</strong>
 <p>คลิกโหนดเพื่อดูเฉพาะเอกสารที่เชื่อมโยงกัน เห็นรายละเอียดของแต่ละโหนด</p>
 </div>
 </div>

 <div class="guide-section">
 <h3> AI แชท</h3>
 <div class="guide-item">
 <strong> ถาม-ตอบ AI</strong>
 <p>ถามคำถามเกี่ยวกับเอกสารของคุณ AI จะตอบพร้อมอ้างอิงแหล่งที่มาจากไฟล์จริง</p>
 </div>
 <div class="guide-item">
 <strong> หลักฐานอ้างอิง</strong>
 <p>ทุกคำตอบมีลิงก์ไปยังเอกสารต้นฉบับ คลิกดูได้เลย ตรวจสอบความถูกต้องได้</p>
 </div>
 </div>

 <div class="guide-section">
 <h3> Context Memory</h3>
 <div class="guide-item">
 <strong> บันทึกบริบท</strong>
 <p>บันทึกสิ่งที่คุยกับ AI ไว้ ใช้ต่อได้ทุกแพลตฟอร์ม (Claude, Antigravity, ChatGPT)</p>
 </div>
 <div class="guide-item">
 <strong> ปักหมุด</strong>
 <p>ปักหมุดบริบทสำคัญ AI จะเห็นข้อมูลนี้เสมอทุกครั้งที่คุยกัน</p>
 </div>
 </div>

 <div class="guide-section">
 <h3> ตั้งค่า MCP / โทเค็น</h3>
 <div class="guide-item">
 <strong> สร้างโทเค็น</strong>
 <p>สร้าง Token สำหรับเชื่อมต่อ Claude Desktop, Antigravity หรือแพลตฟอร์มอื่น</p>
 </div>
 <div class="guide-item">
 <strong> เครื่องมือ 30 ตัว</strong>
 <p>ดูรายการเครื่องมือ MCP ทั้งหมด เช่น ค้นไฟล์, อ่านไฟล์, สร้างไฟล์, ดูกราฟ ฯลฯ</p>
 </div>
 <div class="guide-item">
 <strong> บันทึกการใช้งาน</strong>
 <p>ดูประวัติการเรียกใช้เครื่องมือ MCP ว่าใครเรียกอะไร เมื่อไหร่</p>
 </div>
 </div>
 `;
 } else if (tab === 'connect') {
 el.innerHTML = `
 <div class="guide-section">
 <h3> Claude Desktop</h3>
 <div class="guide-item">
 <p><strong>ขั้นตอนที่ 1:</strong> กดปุ่ม "คัดลอก Config" ด้านล่าง</p>
 <p><strong>ขั้นตอนที่ 2:</strong> เปิด Claude Desktop → Settings → Developer → Edit Config</p>
 <p><strong>ขั้นตอนที่ 3:</strong> วางข้อความที่คัดลอก แล้วบันทึก</p>
 <p><strong>ขั้นตอนที่ 4:</strong> รีสตาร์ท Claude Desktop → พิมพ์ "ดูไฟล์ทั้งหมด" ทดสอบ</p>
 <button class="guide-copy-btn" id="copy-claude"> คัดลอก Config (Claude)</button>
 </div>
 </div>

 <div class="guide-section">
 <h3> Antigravity</h3>
 <div class="guide-item">
 <p><strong>ขั้นตอนที่ 1:</strong> เปิด Antigravity → Settings → MCP Servers</p>
 <p><strong>ขั้นตอนที่ 2:</strong> กด + Add Server → ใส่ชื่อ "Personal Data Bank"</p>
 <p><strong>ขั้นตอนที่ 3:</strong> กด "คัดลอก Config" แล้ววาง URL ของ server</p>
 <p><strong>ขั้นตอนที่ 4:</strong> กด Save → ทดสอบโดยพิมพ์ "list_files"</p>
 <button class="guide-copy-btn" id="copy-antigravity"> คัดลอก Config (Antigravity)</button>
 </div>
 </div>

 <div class="guide-section">
 <h3> ChatGPT</h3>
 <div class="guide-item">
 <img src="/guide/chatgpt-2-settings.png" alt="กดชื่อบัญชี เลือกการตั้งค่า" loading="lazy">
 <p><strong>ก่อนเริ่ม:</strong> ต้องเปิดโหมดนักพัฒนาก่อน (Developer Mode)</p>
 <p><strong>ขั้นตอนที่ 1:</strong> กดที่ชื่อบัญชีผู้ใช้ (มุมบนขวา) → เลือก "การตั้งค่า"</p>
 <img src="/guide/chatgpt-3-apps.png" alt="เลือกแอป" loading="lazy">
 <p><strong>ขั้นตอนที่ 2:</strong> เลือก "แอป" ในเมนูซ้าย</p>
 <img src="/guide/chatgpt-4-applist.png" alt="กดสร้างแอป" loading="lazy">
 <p><strong>ขั้นตอนที่ 3:</strong> กด "การตั้งค่าขั้นสูง" → กดปุ่ม "สร้างแอป"</p>
 <img src="/guide/chatgpt-5-create.png" alt="สร้างแอปใหม่" loading="lazy">
 <p><strong>ขั้นตอนที่ 4:</strong> ตั้งชื่อ เช่น "Personal Data Bank" แล้วใส่ MCP Server URL ด้านล่าง</p>
 <p><strong>ขั้นตอนที่ 5:</strong> การพิสูจน์ตัวตน → เลือก "ไม่พิสูจน์ตัวตน"</p>
 <p><strong>ขั้นตอนที่ 6:</strong> กดปุ่ม "ฉันเข้าใจและฉันต้องการดำเนินการต่อ" → สร้างเสร็จ!</p>
 <p><strong>วิธีใช้:</strong> เปิดแชทใหม่ → กด "เพิ่มเติม" → เลือกแอปที่สร้างไว้</p>
 <img src="/guide/chatgpt-6-use.png" alt="กดเพิ่มเติม เลือกแอป" loading="lazy">
 <button class="guide-copy-btn" id="copy-chatgpt"> คัดลอก MCP URL (ChatGPT)</button>
 </div>
 </div>
 `;

 // Copy Config buttons
 document.querySelectorAll('.guide-copy-btn').forEach(btn => {
 btn.addEventListener('click', async () => {
 const mcpUrl = location.origin + '/mcp';
 let text;
 if (btn.id === 'copy-chatgpt') {
 text = mcpUrl;
 } else {
 text = JSON.stringify({ "mcpServers": { "personal-data-bank": { "url": mcpUrl } } }, null, 2);
 }
 const origLabel = btn.textContent;
 try {
 await navigator.clipboard.writeText(text);
 btn.textContent = ' คัดลอกแล้ว!';
 setTimeout(() => { btn.textContent = origLabel; }, 2000);
 } catch(e) { btn.textContent = ' คัดลอกไม่ได้'; }
 });
 });

 } else if (tab === 'examples') {
 el.innerHTML = `
 <div class="guide-section">
 <h3> เริ่มต้นใช้งาน</h3>
 <div class="guide-item">
 <strong>อัปโหลดเอกสารชุดแรก</strong>
 <p>ลากไฟล์มาวางในหน้า "ข้อมูลของฉัน" → กด จัดระเบียบไฟล์ใหม่</p>
 </div>
 <div class="guide-item">
 <strong>ตั้งค่าโปรไฟล์</strong>
 <p>คลิก "โปรไฟล์" ที่ sidebar ซ้ายล่าง → กรอกข้อมูล → กด Save</p>
 </div>
 </div>

 <div class="guide-section">
 <h3> จัดการข้อมูล</h3>
 <div class="guide-item">
 <strong>หาเอกสารที่เกี่ยวข้อง</strong>
 <p>ไปหน้า AI แชท แล้วพิมพ์: <code>หาข้อมูลเกี่ยวกับ [หัวข้อ]</code></p>
 </div>
 <div class="guide-item">
 <strong>ดูความสัมพันธ์ของเอกสาร</strong>
 <p>ไปหน้ากราฟ → คลิกโหนด → ดูเส้นเชื่อมระหว่างเอกสาร</p>
 </div>
 <div class="guide-item">
 <strong>แก้สรุปที่ AI ทำ</strong>
 <p>คลิกไฟล์ → แก้ไข Summary → กดบันทึก</p>
 </div>
 </div>

 <div class="guide-section">
 <h3> ใช้งาน AI</h3>
 <div class="guide-item">
 <strong>สรุปข้อมูลทั้งหมด</strong>
 <p>พิมพ์ในแชท: <code>สรุปข้อมูลทั้งหมดของฉันให้หน่อย</code></p>
 </div>
 <div class="guide-item">
 <strong>เปรียบเทียบเอกสาร</strong>
 <p>พิมพ์ในแชท: <code>เปรียบเทียบ [ไฟล์ A] กับ [ไฟล์ B]</code></p>
 </div>
 <div class="guide-item">
 <strong>สร้าง Context Pack</strong>
 <p>พิมพ์ในแชท: <code>สร้างแพ็คความรู้เรื่อง [หัวข้อ]</code></p>
 </div>
 <div class="guide-item">
 <strong>บันทึกบริบท</strong>
 <p>พิมพ์ในแชท: <code>บันทึก context สรุปงานวันนี้</code></p>
 </div>
 </div>

 <div class="guide-section">
 <h3> ใช้ผ่าน MCP (Claude/Antigravity)</h3>
 <div class="guide-item">
 <strong>ค้นไฟล์</strong>
 <p>พิมพ์: <code>ค้นหาข้อมูลเกี่ยวกับ [หัวข้อ] จากไฟล์ของฉัน</code></p>
 </div>
 <div class="guide-item">
 <strong>อ่านไฟล์เต็ม</strong>
 <p>พิมพ์: <code>อ่านเนื้อหาไฟล์ [ชื่อไฟล์] ให้หน่อย</code></p>
 </div>
 <div class="guide-item">
 <strong>สร้างไฟล์ใหม่</strong>
 <p>พิมพ์: <code>สร้างไฟล์ชื่อ [ชื่อ] เนื้อหาคือ [...]</code></p>
 </div>
 <div class="guide-item">
 <strong>ดูโปรไฟล์</strong>
 <p>พิมพ์: <code>ดูโปรไฟล์ของฉัน</code></p>
 </div>
 </div>
 `;
 }
}
