// v9.3.0 — Recipient page logic for /p/{token}
// Handles: preview load, expand summary, claim flow, register-then-claim,
// auth redirect, error states (revoked / invalid / pack deleted).

(function () {
 'use strict';

 // Extract token from URL: /p/{token}
 const pathParts = window.location.pathname.split('/').filter(Boolean);
 const TOKEN = pathParts.length >= 2 && pathParts[0] === 'p' ? pathParts[1] : null;

 // State
 let _previewData = null;
 let _summaryExpanded = false;

 // ───── Helpers ─────
 function _showState(name) {
  ['loading', 'error', 'revoked', 'preview'].forEach(s => {
   const el = document.getElementById(`state-${s}`);
   if (el) el.classList.toggle('hidden', s !== name);
  });
 }

 function _showError(title, message) {
  document.getElementById('error-title').textContent = title;
  document.getElementById('error-message').textContent = message;
  _showState('error');
 }

 function _escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
 }

 function _formatBytes(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
 }

 function _showToast(msg, type) {
  type = type || 'info';
  const container = document.getElementById('toast-container');
  if (!container) return;
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = msg;
  container.appendChild(toast);
  if (type !== 'error') {
   setTimeout(() => toast.remove(), 3500);
  }
 }

 // ───── Main flow ─────
 async function loadPreview() {
  if (!TOKEN) {
   _showError('ลิงก์ไม่ถูกต้อง', 'URL ไม่มี token');
   return;
  }
  try {
   const res = await fetch(`/api/shared/pack/${TOKEN}`, {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' },
   });
   if (res.status === 401) {
    _showError('ลิงก์ไม่ถูกต้อง', 'ลิงก์นี้ไม่ใช่ลิงก์ที่ถูกต้อง');
    return;
   }
   if (res.status === 403) {
    _showState('revoked');
    return;
   }
   if (res.status === 404) {
    const err = await res.json();
    _showError('ลิงก์ไม่มีอยู่', err.detail || 'Pack ถูกลบหรือลิงก์ไม่ถูกต้อง');
    return;
   }
   if (!res.ok) {
    _showError('ผิดพลาด', `เกิดข้อผิดพลาด (HTTP ${res.status})`);
    return;
   }
   const data = await res.json();
   _previewData = data;
   _renderPreview(data);
   _showState('preview');

   // Auto-claim if ?autoclaim=1 (came from login redirect)
   const params = new URLSearchParams(window.location.search);
   if (params.get('autoclaim') === '1') {
    // Clear param + claim
    window.history.replaceState({}, '', window.location.pathname);
    setTimeout(() => claimPack(), 500);
   }
  } catch (e) {
   _showError('เชื่อมต่อไม่ได้', 'ไม่สามารถเชื่อมต่อ server ได้ ลองใหม่');
  }
 }

 function _renderPreview(data) {
  const pack = data.pack;
  document.getElementById('pack-title').textContent = pack.title;
  document.getElementById('pack-owner').textContent = pack.owner_email_masked || pack.owner_name || 'ผู้ใช้';
  document.getElementById('pack-type').textContent = `📚 ${pack.type}`;
  document.getElementById('pack-views').textContent = data.view_count || 0;
  document.getElementById('pack-clones').textContent = data.clone_count || 0;
  document.getElementById('pack-intent').textContent = pack.intent || '(ไม่ระบุ)';
  document.getElementById('pack-scope').textContent = pack.scope || '(ไม่ระบุ)';

  // Summary — short by default with expand
  const summaryEl = document.getElementById('pack-summary');
  const expandBtn = document.getElementById('btn-expand-summary');
  summaryEl.textContent = pack.summary_short || pack.summary_full || '';
  if (pack.summary_full && pack.summary_full.length > (pack.summary_short || '').length) {
   expandBtn.classList.remove('hidden');
  }

  // Files
  if (data.include_files && data.files && data.files.length > 0) {
   document.getElementById('files-section').classList.remove('hidden');
   document.getElementById('files-count').textContent = data.files.length;
   const list = document.getElementById('files-list');
   list.innerHTML = data.files.map(f => `
    <div class="shared-file-row">
     <span class="shared-file-icon">📄</span>
     <span class="shared-file-name">${_escapeHtml(f.filename)}</span>
     <span class="shared-file-size">${_formatBytes(f.size_bytes)}</span>
     <a class="shared-file-download btn btn-sm btn-outline" href="${_escapeHtml(f.download_url)}" download="${_escapeHtml(f.filename)}">⬇ ดาวน์โหลด</a>
    </div>
   `).join('');
  }

  // Show register CTA if not logged in
  const token = localStorage.getItem('pdb_token');
  if (!token) {
   document.getElementById('register-cta').classList.remove('hidden');
   const claimBtn = document.getElementById('btn-claim');
   claimBtn.textContent = '➕ Login + เก็บเข้า Workspace ของฉัน';
  }
 }

 // ───── Actions ─────
 window.toggleSummaryExpand = function () {
  if (!_previewData) return;
  const summaryEl = document.getElementById('pack-summary');
  const btn = document.getElementById('btn-expand-summary');
  _summaryExpanded = !_summaryExpanded;
  summaryEl.textContent = _summaryExpanded
   ? _previewData.pack.summary_full
   : _previewData.pack.summary_short;
  btn.textContent = _summaryExpanded ? '▴ ย่อ' : '▾ ดูเต็ม';
 };

 window.claimPack = async function () {
  const token = localStorage.getItem('pdb_token');
  if (!token) {
   // Redirect to landing → register/login → return back with autoclaim
   const returnPath = window.location.pathname;
   window.location.href = `/?return=${encodeURIComponent(returnPath)}&action=claim`;
   return;
  }

  const btn = document.getElementById('btn-claim');
  const originalText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'กำลังเก็บ...';

  try {
   const res = await fetch(`/api/shared/pack/${TOKEN}/claim`, {
    method: 'POST',
    headers: {
     'Content-Type': 'application/json',
     'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify({}),
   });

   if (res.status === 401) {
    // Token expired — redirect to login
    localStorage.removeItem('pdb_token');
    const returnPath = window.location.pathname;
    window.location.href = `/?return=${encodeURIComponent(returnPath)}&action=claim`;
    return;
   }
   if (res.status === 403) {
    const err = await res.json();
    _showToast(err.detail || 'ไม่สามารถเก็บได้ — โควต้าเต็ม', 'error');
    btn.disabled = false;
    btn.textContent = originalText;
    return;
   }
   if (res.status === 404) {
    const err = await res.json();
    _showToast(err.detail || 'ลิงก์หมดอายุ', 'error');
    btn.disabled = false;
    btn.textContent = originalText;
    return;
   }
   if (!res.ok) {
    const err = await res.json();
    _showToast(`Error: ${err.detail || 'unknown'}`, 'error');
    btn.disabled = false;
    btn.textContent = originalText;
    return;
   }
   _showToast('เก็บ Pack สำเร็จ! กำลังพาไป workspace...', 'success');
   // Redirect to /app
   setTimeout(() => {
    window.location.href = '/app';
   }, 1200);
  } catch (e) {
   _showToast('เชื่อมต่อไม่ได้ ลองใหม่', 'error');
   btn.disabled = false;
   btn.textContent = originalText;
  }
 };

 window.registerAndClaim = function () {
  // Redirect to landing with action=claim — landing.js handles flow
  const returnPath = window.location.pathname;
  window.location.href = `/?return=${encodeURIComponent(returnPath)}&action=claim&signup=1`;
 };

 window.closePage = function () {
  // Try window.close first, fallback to redirect home
  try {
   window.close();
   setTimeout(() => {
    if (!window.closed) window.location.href = '/';
   }, 200);
  } catch (e) {
   window.location.href = '/';
  }
 };

 // ───── Init ─────
 document.addEventListener('DOMContentLoaded', loadPreview);
})();
