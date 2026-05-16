/**
 * PDB Admin Panel — v8.2.0
 *
 * แชร์ไฟล์ของตัวเอง (ไม่ใช่ s่วนของ app.js) เพื่อความเป็นอิสระ
 *
 * Sections:
 *   §A  Auth guard + state
 *   §B  Tab routing + nav
 *   §C  Dashboard tab
 *   §D  Users tab
 *   §E  Modals (change plan / reset password / show password / confirm)
 *   §F  Audit log tab
 *   §G  Toast / utils (REUSE shared.css .toast)
 */

// ═══════════════════════════════════════════
// §A — Auth guard + state
// ═══════════════════════════════════════════

const ADMIN = {
  token: localStorage.getItem('pdb_token'),
  me: null,  // {id, email, name, is_admin, effective_plan}
  users: { page: 1, pageSize: 20, total: 0, totalPages: 1, query: '', filter: '', list: [] },
  audit: { eventType: '', limit: 50, offset: 0 },
};

async function adminFetch(url, opts = {}) {
  if (!opts.headers) opts.headers = {};
  if (ADMIN.token) opts.headers['Authorization'] = `Bearer ${ADMIN.token}`;
  let res;
  try {
    res = await fetch(url, opts);
  } catch (err) {
    throw new Error('NETWORK_ERROR');
  }
  if (res.status === 401) {
    localStorage.removeItem('pdb_token');
    localStorage.removeItem('pdb_user');
    window.location.href = '/';
    throw new Error('Unauthorized');
  }
  if (res.status === 403) {
    // v10.0.19 — LP-004 fix: silent redirect + self-correct stale cache.
    // เดิม: แสดงข้อความ "คุณไม่ใช่ admin — กำลังพากลับ" 1.5s บน background ดำ →
    //   user เห็นกระพริบน่าตกใจ. สาเหตุที่ landed ที่ /admin คือ pdb_admin_probe
    //   cache='1' (stale) ใน landing.js _redirectToAppOrAdmin
    // ใหม่: clear cache (ถ้า user เคยเป็น admin แล้วถูกถอด, cache จะถูก correct
    //   ครั้งนี้ → ครั้งถัดไป go to root จะไป /app ตรงๆ ไม่ bounce อีก) +
    //   replace() แทน href (ไม่เก็บ /admin ใน history → กดย้อนกลับไม่กลับมาที่นี่)
    try {
      localStorage.setItem('pdb_admin_probe', '0');
      localStorage.setItem('pdb_admin_probe_ts', String(Date.now()));
    } catch (_) {}
    const loadingEl = document.getElementById('admin-loading');
    if (loadingEl) loadingEl.innerHTML = '';
    window.location.replace('/app');
    throw new Error('NOT_ADMIN');
  }
  return res;
}

// v10.0.19 — sync version badge จาก backend /health (HTML hardcoded ค่าเริ่มต้น
// แต่ browser cache HTML นาน → badge stale หลัง deploy)
async function _syncAdminVersionBadge() {
  try {
    const res = await fetch('/health', { cache: 'no-store' });
    if (!res.ok) return;
    const data = await res.json();
    const v = data && data.version;
    if (!v) return;
    const badge = document.getElementById('admin-logo-pill');
    if (badge) badge.textContent = 'Admin · v' + v;
  } catch (_) { /* network blip ok · keep hardcoded fallback */ }
}

async function init() {
  _syncAdminVersionBadge();
  if (!ADMIN.token) {
    window.location.href = '/';
    return;
  }
  try {
    const res = await adminFetch('/api/admin/me');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    ADMIN.me = await res.json();
    // v10.0.x · set admin probe cache เพื่อให้ dev-logger.js เห็นว่าเป็น admin (gate ที่หน้าอื่น)
    try {
      localStorage.setItem('pdb_admin_probe', '1');
      localStorage.setItem('pdb_admin_probe_ts', String(Date.now()));
    } catch (_) {}
    document.getElementById('admin-email').textContent = ADMIN.me.email || ADMIN.me.id;
    document.getElementById('admin-loading').classList.add('hidden');
    document.getElementById('admin-shell').classList.remove('hidden');
    setupNav();
    setupModals();
    loadDashboard();
  } catch (e) {
    if (e.message !== 'NOT_ADMIN' && e.message !== 'Unauthorized') {
      console.error('[admin init]', e);
      document.getElementById('admin-loading').innerHTML =
        '<p>โหลดข้อมูลไม่สำเร็จ — กรุณารีเฟรชหน้านี้</p>';
    }
  }
}

// ═══════════════════════════════════════════
// §B — Tab routing + nav
// ═══════════════════════════════════════════

function setupNav() {
  document.querySelectorAll('.admin-tab').forEach(btn => {
    btn.onclick = () => switchTab(btn.dataset.tab);
  });
  document.getElementById('btn-back-to-app').onclick = () => { window.location.href = '/app'; };
  document.getElementById('btn-admin-logout').onclick = () => {
    localStorage.removeItem('pdb_token');
    localStorage.removeItem('pdb_user');
    window.location.href = '/';
  };
  document.getElementById('admin-users-search').addEventListener('input', debounce(() => {
    ADMIN.users.query = document.getElementById('admin-users-search').value.trim();
    ADMIN.users.page = 1;
    loadUsers();
  }, 300));
  document.getElementById('admin-users-filter').onchange = () => {
    ADMIN.users.filter = document.getElementById('admin-users-filter').value;
    ADMIN.users.page = 1;
    loadUsers();
  };
  document.getElementById('admin-users-refresh').onclick = () => loadUsers();
  document.getElementById('admin-users-prev').onclick = () => {
    if (ADMIN.users.page > 1) { ADMIN.users.page--; loadUsers(); }
  };
  document.getElementById('admin-users-next').onclick = () => {
    if (ADMIN.users.page < ADMIN.users.totalPages) { ADMIN.users.page++; loadUsers(); }
  };
  document.getElementById('admin-audit-filter').onchange = () => {
    ADMIN.audit.eventType = document.getElementById('admin-audit-filter').value;
    ADMIN.audit.offset = 0;
    loadAuditLogs();
  };
  document.getElementById('admin-audit-refresh').onclick = () => loadAuditLogs();
}

function switchTab(tab) {
  document.querySelectorAll('.admin-tab').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  document.querySelectorAll('.admin-tab-content').forEach(s => {
    s.classList.toggle('active', s.id === `admin-tab-${tab}`);
  });
  if (tab === 'dashboard') loadDashboard();
  if (tab === 'users') loadUsers();
  if (tab === 'audit') loadAuditLogs();
}

// ═══════════════════════════════════════════
// §C — Dashboard
// ═══════════════════════════════════════════

async function loadDashboard() {
  try {
    const res = await adminFetch('/api/admin/stats');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    document.getElementById('stat-total-users').textContent = data.users.total;
    document.getElementById('stat-users-breakdown').textContent =
      `Free ${data.users.by_plan.free} · Starter ${data.users.by_plan.starter} · Admin ${data.users.by_plan.admin}`;
    document.getElementById('stat-active-users').textContent = data.users.active;
    document.getElementById('stat-inactive-users').textContent = data.users.inactive;
    document.getElementById('stat-signups-today').textContent = data.users.signups_today;
    document.getElementById('stat-signups-week').textContent = data.users.signups_this_week;
    document.getElementById('stat-signups-month').textContent = data.users.signups_this_month;
    document.getElementById('stat-total-files').textContent = data.files.total;
    document.getElementById('stat-storage').textContent = data.files.total_storage_mb;
    document.getElementById('stat-stripe-active').textContent = data.subscriptions.starter_active;
    document.getElementById('stat-stripe-pastdue').textContent = data.subscriptions.starter_past_due;
    document.getElementById('stat-stripe-canceled').textContent = data.subscriptions.starter_canceled;
    document.getElementById('stat-line-used').textContent = data.line.push_quota_used;
    document.getElementById('stat-line-limit').textContent = data.line.push_quota_limit;
    document.getElementById('stat-line-percent').textContent = data.line.push_quota_percent;
    document.getElementById('stat-line-linked').textContent = data.line.linked_users;
    const checkedAt = data.system.checked_at ? new Date(data.system.checked_at).toLocaleString('th-TH') : '—';
    document.getElementById('admin-checked-at').textContent = checkedAt;
    document.getElementById('admin-db-size').textContent = data.system.db_size_mb;
  } catch (e) {
    showToast('โหลด stats ไม่สำเร็จ: ' + e.message, 'error');
  }
}

// ═══════════════════════════════════════════
// §D — Users
// ═══════════════════════════════════════════

async function loadUsers() {
  const tbody = document.getElementById('admin-users-tbody');
  tbody.innerHTML = '<tr><td colspan="8" class="text-muted">กำลังโหลด...</td></tr>';
  try {
    const params = new URLSearchParams({
      page: String(ADMIN.users.page),
      page_size: String(ADMIN.users.pageSize),
    });
    if (ADMIN.users.query) params.set('q', ADMIN.users.query);
    if (ADMIN.users.filter) params.set('plan', ADMIN.users.filter);
    const res = await adminFetch(`/api/admin/users?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    ADMIN.users.total = data.total;
    ADMIN.users.totalPages = data.total_pages || 1;
    ADMIN.users.list = data.users || [];
    renderUsersTable(data.users);
    document.getElementById('admin-users-page-info').textContent =
      `หน้า ${data.page}/${data.total_pages || 1} (${data.total} คน)`;
    document.getElementById('admin-users-prev').disabled = data.page <= 1;
    document.getElementById('admin-users-next').disabled = data.page >= (data.total_pages || 1);
  } catch (e) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-muted">โหลดไม่สำเร็จ: ${escapeHtml(e.message)}</td></tr>`;
  }
}

function renderUsersTable(users) {
  const tbody = document.getElementById('admin-users-tbody');
  if (!users || users.length === 0) {
    tbody.innerHTML = '<tr><td colspan="8" class="text-muted">ไม่มีผู้ใช้</td></tr>';
    return;
  }
  tbody.innerHTML = users.map(u => `
    <tr data-user-id="${escapeHtml(u.id)}">
     <td>${escapeHtml(u.email || '—')}</td>
     <td>${escapeHtml(u.name || '—')}</td>
     <td>${planBadge(u.effective_plan)}${u.manual_plan_override ? ' <span class="badge-stripe">manual</span>' : ''}</td>
     <td>${u.stripe_subscription_id ? `<span class="badge-stripe">${escapeHtml(u.subscription_status || '')}</span>` : '—'}</td>
     <td>${u.file_count || 0}</td>
     <td>${u.created_at ? new Date(u.created_at).toLocaleDateString('th-TH') : '—'}</td>
     <td>${u.is_active ? '<span class="badge-active">Active</span>' : '<span class="badge-inactive">Inactive</span>'}</td>
     <td class="admin-user-actions">
      <button class="btn btn-sm" data-action="plan" data-uid="${escapeHtml(u.id)}">Plan</button>
      <button class="btn btn-sm" data-action="view-password" data-uid="${escapeHtml(u.id)}" title="ดูรหัสผ่าน (TEST PHASE)">ดูรหัส</button>
      <button class="btn btn-sm" data-action="password" data-uid="${escapeHtml(u.id)}">รีเซ็ตรหัส</button>
      <button class="btn btn-sm" data-action="active" data-uid="${escapeHtml(u.id)}" data-value="${u.is_active ? '0' : '1'}">${u.is_active ? 'Deactivate' : 'Reactivate'}</button>
      <button class="btn btn-sm" data-action="admin" data-uid="${escapeHtml(u.id)}" data-value="${u.is_admin ? '0' : '1'}">${u.is_admin ? 'Demote' : 'Promote'}</button>
      <button class="btn btn-sm btn-danger" data-action="delete" data-uid="${escapeHtml(u.id)}" title="ลบบัญชี (irreversible)">ลบ</button>
     </td>
    </tr>
  `).join('');

  // Attach handlers via event delegation (single listener)
  tbody.querySelectorAll('button[data-action]').forEach(btn => {
    btn.onclick = () => handleUserAction(btn.dataset.action, btn.dataset.uid, btn.dataset.value);
  });
}

function planBadge(plan) {
  const cls = { free: 'badge-free', starter: 'badge-starter', admin: 'badge-admin' }[plan] || '';
  return `<span class="badge ${cls}">${escapeHtml(plan || '—')}</span>`;
}

function handleUserAction(action, userId, value) {
  const user = ADMIN.users.list.find(u => u.id === userId);
  if (!user) { showToast('ไม่พบผู้ใช้', 'error'); return; }
  if (action === 'plan') return openChangePlan(user);
  if (action === 'password') return openResetPassword(user);
  if (action === 'view-password') return openViewPassword(user);  // v10.0.x · TEST PHASE
  if (action === 'active') return openConfirmActive(user, value === '1');
  if (action === 'admin') return openConfirmAdmin(user, value === '1');
  if (action === 'delete') return openDeleteUser(user);  // v10.0.x · hard delete
}

// ═══════════════════════════════════════════
// §E — Modals
// ═══════════════════════════════════════════

function setupModals() {
  // Close handlers (X button + Cancel) · v10.0.x · เพิ่ม modal-delete-user + modal-view-password
  ['modal-change-plan', 'modal-reset-password', 'modal-confirm-action', 'modal-delete-user', 'modal-view-password'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    const closeBtn = document.getElementById(`${id}-close`);
    const cancelBtn = document.getElementById(`${id}-cancel`);
    if (closeBtn) closeBtn.onclick = () => closeModal(id);
    if (cancelBtn) cancelBtn.onclick = () => closeModal(id);
    // Backdrop click — close
    el.addEventListener('click', (e) => {
      if (e.target.id === id) closeModal(id);
    });
  });

  // Change plan confirm
  document.getElementById('modal-change-plan-confirm').onclick = submitChangePlan;
  // Reset password confirm + generate
  document.getElementById('modal-reset-password-confirm').onclick = submitResetPassword;
  document.getElementById('modal-reset-password-generate').onclick = () => {
    document.getElementById('modal-reset-password-input').value = generateRandomPassword(12);
  };
  // Show password copy + close
  document.getElementById('modal-password-copy').onclick = copyPasswordToClipboard;
  document.getElementById('modal-password-shown-close').onclick = () => closeModal('modal-password-shown');
  // Confirm action OK
  document.getElementById('modal-confirm-ok').onclick = submitConfirmAction;
  // v10.0.x · Delete user confirm
  document.getElementById('modal-delete-confirm-btn')?.addEventListener('click', submitDeleteUser);
  // v10.0.x · View password (TEST PHASE) · submit + copy
  document.getElementById('modal-view-password-submit')?.addEventListener('click', submitViewPassword);
  document.getElementById('modal-view-password-copy')?.addEventListener('click', copyViewedPassword);

  // ESC key closes any open modal
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-overlay:not(.hidden)').forEach(m => m.classList.add('hidden'));
    }
  });
}

function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
function closeModal(id) { document.getElementById(id).classList.add('hidden'); }

// ── Change plan ──
async function openChangePlan(user) {
  const modal = document.getElementById('modal-change-plan');
  modal.dataset.userId = user.id;
  document.getElementById('modal-change-plan-email').textContent = user.email || user.id;
  document.getElementById('modal-change-plan-current').textContent = user.effective_plan;
  document.getElementById('modal-change-plan-select').value = user.effective_plan;
  document.getElementById('modal-change-plan-reason').value = '';
  // Fetch detail to know stripe_active
  const warning = document.getElementById('modal-change-plan-warning');
  warning.classList.add('hidden');
  try {
    const res = await adminFetch(`/api/admin/users/${encodeURIComponent(user.id)}`);
    if (res.ok) {
      const data = await res.json();
      if (data.stripe_active) {
        warning.classList.remove('hidden');
        warning.textContent = '⚠️ User คนนี้มี Stripe subscription กำลังใช้งาน — downgrade เป็น Free จะถูกบล็อก';
      }
    }
  } catch (_) { /* best-effort */ }
  openModal('modal-change-plan');
}

async function submitChangePlan() {
  const modal = document.getElementById('modal-change-plan');
  const userId = modal.dataset.userId;
  const plan = document.getElementById('modal-change-plan-select').value;
  const reason = document.getElementById('modal-change-plan-reason').value.trim();
  if (!reason) { showToast('กรุณากรอกเหตุผล', 'error'); return; }

  const btn = document.getElementById('modal-change-plan-confirm');
  const origLabel = btn.textContent;
  btn.disabled = true;
  btn.innerHTML = '<span class="loading-spinner" style="margin-right:6px"></span>กำลังบันทึก...';
  try {
    const res = await adminFetch(`/api/admin/users/${encodeURIComponent(userId)}/plan`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ plan, reason }),
    });
    const data = await res.json();
    if (!res.ok) {
      const msg = data?.detail?.error?.message || data?.detail || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    showToast(`เปลี่ยน plan สำเร็จ: ${data.old_plan} → ${data.new_plan}`, 'success');
    closeModal('modal-change-plan');
    loadUsers();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = origLabel;
  }
}

// ── Reset password ──
function openResetPassword(user) {
  if (!user.email && !user.id) return;
  const modal = document.getElementById('modal-reset-password');
  modal.dataset.userId = user.id;
  document.getElementById('modal-reset-password-email').textContent = user.email || user.id;
  document.getElementById('modal-reset-password-input').value = '';
  document.getElementById('modal-reset-password-reason').value = '';
  openModal('modal-reset-password');
}

async function submitResetPassword() {
  const modal = document.getElementById('modal-reset-password');
  const userId = modal.dataset.userId;
  const newPassword = document.getElementById('modal-reset-password-input').value;
  const reason = document.getElementById('modal-reset-password-reason').value.trim();
  if (!newPassword || newPassword.length < 6) {
    showToast('รหัสผ่านต้องมีอย่างน้อย 6 ตัว', 'error');
    return;
  }
  if (!reason) { showToast('กรุณากรอกเหตุผล', 'error'); return; }

  const btn = document.getElementById('modal-reset-password-confirm');
  btn.disabled = true;
  try {
    const res = await adminFetch(`/api/admin/users/${encodeURIComponent(userId)}/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ new_password: newPassword, reason }),
    });
    const data = await res.json();
    if (!res.ok) {
      const msg = data?.detail?.error?.message || data?.detail || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    closeModal('modal-reset-password');
    // Show password one-time modal
    document.getElementById('modal-password-shown-email').textContent = data.user_email || userId;
    document.getElementById('admin-password-display').textContent = data.new_password_shown_once;
    openModal('modal-password-shown');
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

async function copyPasswordToClipboard() {
  const text = document.getElementById('admin-password-display').textContent;
  try {
    await navigator.clipboard.writeText(text);
    showToast('คัดลอกแล้ว ✓', 'success');
  } catch (_) {
    // Fallback — select text manually (works on most browsers)
    const range = document.createRange();
    range.selectNode(document.getElementById('admin-password-display'));
    window.getSelection().removeAllRanges();
    window.getSelection().addRange(range);
    showToast('เลือกข้อความแล้ว — กด Ctrl+C เพื่อคัดลอก', 'info');
  }
}

// ── Confirm active toggle ──
function openConfirmActive(user, makeActive) {
  const modal = document.getElementById('modal-confirm-action');
  modal.dataset.action = 'active';
  modal.dataset.userId = user.id;
  modal.dataset.value = makeActive ? '1' : '0';
  document.getElementById('modal-confirm-title').textContent = makeActive ? 'Reactivate User' : 'Deactivate User';
  document.getElementById('modal-confirm-message').textContent =
    `${makeActive ? 'เปิดใช้งาน' : 'ระงับ'} ผู้ใช้ ${user.email || user.id}?`;
  document.getElementById('modal-confirm-reason').value = '';
  openModal('modal-confirm-action');
}

// ── Confirm admin toggle ──
function openConfirmAdmin(user, makeAdmin) {
  const modal = document.getElementById('modal-confirm-action');
  modal.dataset.action = 'admin';
  modal.dataset.userId = user.id;
  modal.dataset.value = makeAdmin ? '1' : '0';
  document.getElementById('modal-confirm-title').textContent = makeAdmin ? 'Promote to Admin' : 'Demote from Admin';
  document.getElementById('modal-confirm-message').textContent =
    `${makeAdmin ? 'เลื่อนเป็น Admin' : 'ลดสิทธิ์จาก Admin'}: ${user.email || user.id}?`;
  document.getElementById('modal-confirm-reason').value = '';
  openModal('modal-confirm-action');
}

async function submitConfirmAction() {
  const modal = document.getElementById('modal-confirm-action');
  const action = modal.dataset.action;  // "active" | "admin"
  const userId = modal.dataset.userId;
  const value = modal.dataset.value === '1';
  const reason = document.getElementById('modal-confirm-reason').value.trim();
  if (!reason) { showToast('กรุณากรอกเหตุผล', 'error'); return; }

  const url = `/api/admin/users/${encodeURIComponent(userId)}/${action}`;
  const btn = document.getElementById('modal-confirm-ok');
  btn.disabled = true;
  try {
    const res = await adminFetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value, reason }),
    });
    const data = await res.json();
    if (!res.ok) {
      const msg = data?.detail?.error?.message || data?.detail || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    showToast('สำเร็จ ✓', 'success');
    closeModal('modal-confirm-action');
    loadUsers();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.disabled = false;
  }
}

// ═══════════════════════════════════════════
// §E.4 — View user password (v10.0.x · TEST PHASE ONLY)
// ═══════════════════════════════════════════

function openViewPassword(user) {
  const modal = document.getElementById('modal-view-password');
  if (!modal) { showToast('View-password modal ไม่พร้อม', 'error'); return; }
  modal.dataset.userId = user.id;
  document.getElementById('modal-view-password-email').textContent = user.email || '(no email)';
  document.getElementById('modal-view-password-name').textContent = user.name || '—';
  document.getElementById('modal-view-password-reason').value = '';
  // Reset display
  document.getElementById('modal-view-password-result').classList.add('hidden');
  document.getElementById('modal-view-password-result-value').textContent = '';
  openModal('modal-view-password');
}

async function submitViewPassword() {
  const modal = document.getElementById('modal-view-password');
  const userId = modal.dataset.userId;
  const reason = document.getElementById('modal-view-password-reason').value.trim();
  if (!reason) { showToast('กรุณากรอกเหตุผล', 'error'); return; }

  const btn = document.getElementById('modal-view-password-submit');
  btn.disabled = true;
  btn.textContent = 'กำลังดึง...';
  try {
    // ใช้ AdminToggleRequest schema ที่ backend ใช้ซ้ำ: value=false (ignored), reason=str
    const res = await adminFetch(`/api/admin/users/${encodeURIComponent(userId)}/view-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ value: false, reason }),
    });
    const data = await res.json();
    if (!res.ok) {
      const msg = data?.detail?.error?.message || data?.detail || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    const result = document.getElementById('modal-view-password-result');
    const valueEl = document.getElementById('modal-view-password-result-value');
    result.classList.remove('hidden');
    if (data.password_available && data.password) {
      valueEl.textContent = data.password;
      valueEl.style.color = '#fef2f2';
      result.classList.remove('is-warning');
    } else {
      valueEl.textContent = data.hint || 'ไม่มีรหัสผ่านเก็บไว้ · ใช้ Reset Password เพื่อตั้งใหม่';
      valueEl.style.color = '#fbbf24';
      result.classList.add('is-warning');
    }
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'ดูรหัสผ่าน';
  }
}

async function copyViewedPassword() {
  const val = document.getElementById('modal-view-password-result-value').textContent;
  if (!val) return;
  try {
    await navigator.clipboard.writeText(val);
    showToast('คัดลอกรหัสผ่านแล้ว', 'success');
  } catch (e) {
    showToast('คัดลอกไม่สำเร็จ: ' + e.message, 'error');
  }
}

// ═══════════════════════════════════════════
// §E.5 — Delete user (v10.0.x · hard delete + cascade)
// ═══════════════════════════════════════════

function openDeleteUser(user) {
  const modal = document.getElementById('modal-delete-user');
  if (!modal) {
    showToast('Delete modal ไม่พร้อม', 'error');
    return;
  }
  modal.dataset.userId = user.id;
  modal.dataset.userEmail = (user.email || '').toLowerCase();
  document.getElementById('modal-delete-target-email').textContent = user.email || '(no email)';
  document.getElementById('modal-delete-target-name').textContent = user.name || '—';
  document.getElementById('modal-delete-target-files').textContent = user.file_count || 0;
  // แสดง email ที่ user ต้องพิมพ์ใน confirm field (ไม่ใช่ placeholder "email" generic)
  const expectedEmailEl = document.getElementById('modal-delete-expected-email');
  if (expectedEmailEl) expectedEmailEl.textContent = user.email || '(no email)';
  document.getElementById('modal-delete-confirm-input').value = '';
  document.getElementById('modal-delete-reason').value = '';
  openModal('modal-delete-user');
}

async function submitDeleteUser() {
  const modal = document.getElementById('modal-delete-user');
  const userId = modal.dataset.userId;
  const expectedEmail = modal.dataset.userEmail;
  const confirmEmail = document.getElementById('modal-delete-confirm-input').value.trim().toLowerCase();
  const reason = document.getElementById('modal-delete-reason').value.trim();

  if (confirmEmail !== expectedEmail) {
    showToast('Email ที่กรอกไม่ตรงกับบัญชีที่จะลบ', 'error');
    return;
  }
  if (!reason) {
    showToast('กรุณากรอกเหตุผล', 'error');
    return;
  }

  const btn = document.getElementById('modal-delete-confirm-btn');
  btn.disabled = true;
  btn.textContent = 'กำลังลบ...';
  try {
    const res = await adminFetch(`/api/admin/users/${encodeURIComponent(userId)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm_email: confirmEmail, reason }),
    });
    const data = await res.json();
    if (!res.ok) {
      const msg = data?.detail?.error?.message || data?.detail || `HTTP ${res.status}`;
      throw new Error(msg);
    }
    const stats = data.stats || {};
    const detail = [
      `files=${stats.files_deleted || 0}`,
      `disk=${(stats.files_disk_removed || 0) + (stats.summaries_disk_removed || 0)}`,
      `tables=${(stats.tables_purged || []).length}`,
    ].join(' · ');
    showToast(`ลบบัญชี ${data.deleted_user_email} แล้ว · ${detail}`, 'success');
    closeModal('modal-delete-user');
    loadUsers();
    loadDashboard();
  } catch (e) {
    showToast(e.message, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'ลบถาวร';
  }
}

// ═══════════════════════════════════════════
// §F — Audit log
// ═══════════════════════════════════════════

async function loadAuditLogs() {
  const list = document.getElementById('admin-audit-list');
  list.innerHTML = '<p class="text-muted">กำลังโหลด...</p>';
  try {
    const params = new URLSearchParams({
      limit: String(ADMIN.audit.limit),
      offset: String(ADMIN.audit.offset),
    });
    if (ADMIN.audit.eventType) params.set('event_type', ADMIN.audit.eventType);
    const res = await adminFetch(`/api/admin/audit-logs?${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.logs || data.logs.length === 0) {
      list.innerHTML = '<p class="text-muted">ยังไม่มีรายการ</p>';
      return;
    }
    list.innerHTML = data.logs.map(log => `
      <div class="admin-audit-row">
        <div class="audit-time">${log.created_at ? new Date(log.created_at).toLocaleString('th-TH') : '—'}</div>
        <div class="audit-event"><strong>${escapeHtml(log.event_type || '')}</strong></div>
        <div class="audit-user">${escapeHtml(log.user_email || log.user_id || '—')}</div>
        <div class="audit-detail">
          ${log.old_value ? `<span class="audit-old">${escapeHtml(log.old_value)}</span> → ` : ''}
          <span class="audit-new">${escapeHtml(log.new_value || '')}</span>
        </div>
        <div class="audit-by">โดย: ${escapeHtml(log.triggered_by || 'system')}</div>
      </div>
    `).join('');
  } catch (e) {
    list.innerHTML = `<p class="text-muted">โหลดไม่สำเร็จ: ${escapeHtml(e.message)}</p>`;
  }
}

// ═══════════════════════════════════════════
// §G — Toast + utils (REUSE shared.css .toast pattern)
// ═══════════════════════════════════════════

function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str).replace(/[&<>"']/g, s =>
    ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[s]));
}

function showToast(msg, type = 'info') {
  const t = document.createElement('div');
  t.className = `toast ${type}`;  // matches shared.css: .toast.success/.error/.info
  t.innerHTML = `
    <div class="toast-msg"></div>
    <button class="toast-close" type="button" aria-label="ปิด">&times;</button>
  `;
  t.querySelector('.toast-msg').textContent = msg;
  t.querySelector('.toast-close').onclick = () => t.remove();
  document.getElementById('toast-container').appendChild(t);
  // Auto-dismiss success/info; error stays until user closes (match v7.2.0 UX)
  if (type !== 'error') {
    setTimeout(() => { t.remove(); }, 4000);
  }
}

function debounce(fn, wait) {
  let timer;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), wait);
  };
}

function generateRandomPassword(length) {
  // Mixed alphanum (no easily-confused chars: 0/O, 1/l/I)
  const chars = 'abcdefghjkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let out = '';
  const arr = new Uint32Array(length);
  if (window.crypto && window.crypto.getRandomValues) {
    window.crypto.getRandomValues(arr);
    for (let i = 0; i < length; i++) out += chars[arr[i] % chars.length];
  } else {
    for (let i = 0; i < length; i++) out += chars[Math.floor(Math.random() * chars.length)];
  }
  return out;
}

// Bootstrap
init();
