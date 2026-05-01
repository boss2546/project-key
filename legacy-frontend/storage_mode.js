/**
 * Personal Data Bank — Storage Mode (BYOS v7.0.0)
 * 
 * Module ที่จัดการ UI ของ Storage Mode ใน profile modal:
 * - แสดง status (Managed / BYOS Connected / BYOS Disconnected)
 * - Connect / Disconnect Google Drive
 * - Handle OAuth callback redirect params (?drive_connected=true|false)
 * 
 * Dependencies: authFetch(), showToast(), getLang() from app.js
 * Backend: /api/drive/status, /api/drive/oauth/init, /api/drive/disconnect
 */

// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════
let _driveStatus = null;

// ═══════════════════════════════════════════
// INIT — called from initAppData() in app.js
// ═══════════════════════════════════════════

async function initStorageMode() {
  // 1. Check URL params from OAuth callback redirect
  handleDriveCallbackParams();

  // 2. Fetch current drive status
  await refreshDriveStatus();

  // 3. Wire up event listeners
  wireStorageModeEvents();
}


// ═══════════════════════════════════════════
// OAuth Callback Params Handler
// ═══════════════════════════════════════════

function handleDriveCallbackParams() {
  const params = new URLSearchParams(window.location.search);
  const driveConnected = params.get('drive_connected');
  const error = params.get('error');

  if (driveConnected === 'true') {
    showToast(
      getLang() === 'th'
        ? 'เชื่อมต่อ Google Drive สำเร็จ! ไฟล์ของคุณจะซิงค์อัตโนมัติ'
        : 'Google Drive connected! Your files will sync automatically.',
      'success'
    );
    // Clean URL without reload
    window.history.replaceState({}, '', '/');
    // Auto-open profile modal — return user to context before OAuth redirect
    setTimeout(() => {
      const modal = document.getElementById('profile-modal');
      if (modal) modal.classList.remove('hidden');
    }, 800);
  } else if (driveConnected === 'false') {
    const msg = error === 'access_denied'
      ? (getLang() === 'th' ? 'คุณปฏิเสธการเข้าถึง Google Drive' : 'You denied Google Drive access')
      : (getLang() === 'th' ? 'ไม่สามารถเชื่อมต่อ Google Drive ได้' : 'Failed to connect Google Drive');
    showToast(msg, 'error');
    window.history.replaceState({}, '', '/');
  }
}


// ═══════════════════════════════════════════
// Drive Status API
// ═══════════════════════════════════════════

async function refreshDriveStatus() {
  try {
    const res = await authFetch('/api/drive/status');
    if (res.ok) {
      _driveStatus = await res.json();
    } else {
      _driveStatus = { feature_available: false };
    }
  } catch {
    _driveStatus = { feature_available: false };
  }
  renderStorageModeUI();
}


// ═══════════════════════════════════════════
// Connect Drive (OAuth flow)
// ═══════════════════════════════════════════

async function connectDrive() {
  const btn = document.getElementById('btn-connect-drive');
  if (btn) {
    btn.disabled = true;
    btn.textContent = getLang() === 'th' ? 'กำลังเชื่อมต่อ...' : 'Connecting...';
  }

  try {
    const res = await authFetch('/api/drive/oauth/init');
    if (!res.ok) {
      const data = await res.json();
      const errMsg = data?.error?.message || 'OAuth init failed';
      showToast(errMsg, 'error');
      return;
    }
    const data = await res.json();
    if (data.auth_url) {
      // Redirect to Google OAuth consent screen
      window.location.href = data.auth_url;
    } else {
      showToast('No auth URL received', 'error');
    }
  } catch (e) {
    showToast(
      getLang() === 'th' ? 'ไม่สามารถเริ่ม OAuth ได้' : 'Cannot start OAuth flow',
      'error'
    );
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = getLang() === 'th' ? 'เชื่อมต่อ Google Drive' : 'Connect Google Drive';
    }
  }
}


// ═══════════════════════════════════════════
// Disconnect Drive
// ═══════════════════════════════════════════

async function disconnectDrive() {
  const confirmed = confirm(
    getLang() === 'th'
      ? 'ต้องการยกเลิกการเชื่อมต่อ Google Drive?\n\nไฟล์ใน Drive จะไม่ถูกลบ แต่ระบบจะกลับไปใช้ Managed Mode'
      : 'Disconnect Google Drive?\n\nYour Drive files won\'t be deleted, but the system will switch back to Managed Mode.'
  );
  if (!confirmed) return;

  const btn = document.getElementById('btn-disconnect-drive');
  if (btn) {
    btn.disabled = true;
    btn.textContent = getLang() === 'th' ? 'กำลังยกเลิก...' : 'Disconnecting...';
  }

  try {
    const res = await authFetch('/api/drive/disconnect', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ keep_files: true }),
    });

    if (res.ok) {
      showToast(
        getLang() === 'th'
          ? 'ยกเลิกการเชื่อมต่อ Drive แล้ว — กลับสู่ Managed Mode'
          : 'Drive disconnected — switched to Managed Mode',
        'success'
      );
      await refreshDriveStatus();
    } else {
      const data = await res.json();
      showToast(data?.error?.message || 'Disconnect failed', 'error');
    }
  } catch {
    showToast(
      getLang() === 'th' ? 'ไม่สามารถยกเลิกการเชื่อมต่อได้' : 'Cannot disconnect',
      'error'
    );
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.textContent = getLang() === 'th' ? 'ยกเลิกการเชื่อมต่อ' : 'Disconnect';
    }
  }
}


// ═══════════════════════════════════════════
// Render UI
// ═══════════════════════════════════════════

function renderStorageModeUI() {
  const container = document.getElementById('storage-mode-section');
  if (!container) return;

  // If BYOS feature is not available (env vars not set), hide entirely
  if (!_driveStatus || !_driveStatus.feature_available) {
    container.classList.add('hidden');
    return;
  }

  container.classList.remove('hidden');
  const isTH = getLang() === 'th';
  const isConnected = _driveStatus.drive_connected;
  const isBYOS = _driveStatus.storage_mode === 'byos';

  // Status badge
  const statusBadge = document.getElementById('storage-mode-badge');
  if (statusBadge) {
    if (isBYOS && isConnected) {
      statusBadge.className = 'storage-badge storage-badge-byos';
      statusBadge.textContent = 'BYOS';
    } else {
      statusBadge.className = 'storage-badge storage-badge-managed';
      statusBadge.textContent = 'Managed';
    }
  }

  // Status description
  const statusDesc = document.getElementById('storage-mode-desc');
  if (statusDesc) {
    if (isBYOS && isConnected) {
      statusDesc.innerHTML = `
        <div class="storage-connected-info">
          <div class="storage-connected-row">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-success)" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            <span>${isTH ? 'เชื่อมต่อ Google Drive แล้ว' : 'Connected to Google Drive'}</span>
          </div>
          <div class="storage-email">${_driveStatus.drive_email || ''}</div>
          ${_driveStatus.last_sync_at
            ? `<div class="storage-sync-time">${isTH ? 'ซิงค์ล่าสุด' : 'Last sync'}: ${formatRelativeTime(_driveStatus.last_sync_at)}</div>`
            : ''
          }
          <div class="storage-folder">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z"/></svg>
            <span>/${_driveStatus.drive_root_folder_name || 'Personal Data Bank'}/</span>
          </div>
        </div>
      `;
    } else {
      statusDesc.innerHTML = `
        <p class="storage-managed-desc">${isTH
          ? 'ไฟล์เก็บในเซิร์ฟเวอร์ของเรา — เชื่อมต่อ Google Drive เพื่อเก็บข้อมูลในบัญชีของคุณเอง'
          : 'Files stored on our server — connect Google Drive to store data in your own account'
        }</p>
      `;
    }
  }

  // Action buttons
  const actionsEl = document.getElementById('storage-mode-actions');
  if (actionsEl) {
    if (isBYOS && isConnected) {
      actionsEl.innerHTML = `
        <button class="btn btn-outline btn-sm" id="btn-disconnect-drive" onclick="disconnectDrive()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          ${isTH ? 'ยกเลิกการเชื่อมต่อ' : 'Disconnect'}
        </button>
      `;
    } else {
      actionsEl.innerHTML = `
        <button class="btn btn-primary btn-sm" id="btn-connect-drive" onclick="connectDrive()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg>
          ${isTH ? 'เชื่อมต่อ Google Drive' : 'Connect Google Drive'}
        </button>
      `;
    }
  }

  // Testing mode notice
  const noticeEl = document.getElementById('storage-mode-notice');
  if (noticeEl && _driveStatus.oauth_mode === 'testing') {
    noticeEl.classList.remove('hidden');
  }
}


// ═══════════════════════════════════════════
// Event Wiring
// ═══════════════════════════════════════════

function wireStorageModeEvents() {
  // Events are wired via onclick in renderStorageModeUI
  // Nothing to wire here currently — future: Picker integration
}


// ═══════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════

function formatRelativeTime(isoString) {
  if (!isoString) return '';
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    const isTH = getLang() === 'th';

    if (diffMin < 1) return isTH ? 'เมื่อสักครู่' : 'just now';
    if (diffMin < 60) return isTH ? `${diffMin} นาทีที่แล้ว` : `${diffMin}m ago`;
    if (diffHour < 24) return isTH ? `${diffHour} ชั่วโมงที่แล้ว` : `${diffHour}h ago`;
    return isTH ? `${diffDay} วันที่แล้ว` : `${diffDay}d ago`;
  } catch {
    return isoString;
  }
}
