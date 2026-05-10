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
// v9.3.5 — banner dismiss persists แค่ session-only (ไม่ persist ข้าม reload)
// Why: ป้องกัน user กดผิดแล้วลืม banner ค้างจนกว่าจะ reconnect
let _driveBannerDismissedThisSession = false;

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

  // v9.3.5 — Banner UX layer
  wireDriveErrorBanner();
  setupDriveStatusVisibilityPolling();
}


// ═══════════════════════════════════════════
// OAuth Callback Params Handler
// ═══════════════════════════════════════════

function handleDriveCallbackParams() {
  const params = new URLSearchParams(window.location.search);
  const driveConnected = params.get('drive_connected');
  const error = params.get('error');

  if (driveConnected === 'true') {
    const isTH = getLang() === 'th';
    showToast(
      isTH
        ? 'เชื่อมต่อ Google Drive สำเร็จ! กำลังซิงค์ไฟล์ที่ค้าง...'
        : 'Google Drive connected! Syncing pending files...',
      'success'
    );
    // Clean URL without reload
    window.history.replaceState({}, '', '/');

    // v9.3.5 — reset banner dismiss flag (state เพิ่งกลับมา healthy)
    _driveBannerDismissedThisSession = false;

    // v9.3.5 — Auto-trigger sync to push stuck files (ไฟล์ที่ user upload ระหว่าง token พัง)
    // Why: user goal "ดีที่สุด" = 1 click reconnect → ระบบจัดการที่เหลือเอง
    setTimeout(async () => {
      try {
        const syncRes = await authFetch('/api/drive/sync', { method: 'POST' });
        if (syncRes.ok) {
          const syncData = await syncRes.json();
          const stats = syncData.stats || {};
          const pushed = stats.pushed_new || 0;
          const errs = stats.errors || 0;
          if (pushed > 0 && errs === 0) {
            showToast(
              isTH
                ? `✓ ซิงค์ ${pushed} ไฟล์ขึ้น Drive แล้ว`
                : `✓ Synced ${pushed} files to Drive`,
              'success'
            );
          } else if (pushed > 0 && errs > 0) {
            showToast(
              isTH
                ? `ซิงค์ ${pushed} ไฟล์สำเร็จ · ${errs} ไฟล์ล้มเหลว`
                : `Synced ${pushed} files · ${errs} failed`,
              'warning'
            );
          }
        }
        // Refresh status (banner หายเพราะ status='success') + file list (badge update)
        await refreshDriveStatus();
        if (typeof loadFiles === 'function') loadFiles();
      } catch (e) {
        // Silent fail — banner กลับมาถ้า status ยัง error
        console.warn('Auto-sync after reconnect failed:', e);
      }
    }, 1500); // ให้ user เห็น toast แรกก่อน

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
    const res = await authFetch('/api/drive/status', { _background: true });
    if (res.ok) {
      _driveStatus = await res.json();
    } else {
      _driveStatus = { feature_available: false };
    }
  } catch {
    _driveStatus = { feature_available: false };
  }
  // v9.3.5 — expose ให้ app.js เช็คใน upload flow ได้
  try { window._driveStatus = _driveStatus; } catch (_e) {}
  renderStorageModeUI();
  renderDriveErrorBanner();  // v9.3.5 — proactive banner
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
// v9.3.5.1 — Friendly error message helper
// ═══════════════════════════════════════════

/**
 * แปลง raw backend error (เช่น Python tuple "invalid_grant: ('...', {...})")
 * → ข้อความ user-friendly พร้อม HTML-escape
 *
 * Pattern: match keyword ใน error string → return localized text
 * - "invalid_grant" / "expired" / "revoked" → token หมดอายุ
 * - else → generic "พบปัญหา"
 *
 * Why helper: เดิมแสดง raw error แบบ
 *   "invalid_grant: ('invalid_grant: Token has been expired or revoked.', {...})"
 * ซึ่งเป็น Python repr → user งง · technical jargon
 *
 * @param {string} rawErr - last_sync_error จาก backend
 * @param {boolean} isTH - true=Thai, false=English
 * @returns {string} HTML-escaped user-friendly text
 */
function _friendlyDriveErrorReason(rawErr, isTH) {
  const errStr = (rawErr || '').toLowerCase();
  let friendly;
  if (errStr.indexOf('invalid_grant') >= 0
      || errStr.indexOf('expired') >= 0
      || errStr.indexOf('revoked') >= 0) {
    friendly = isTH
      ? 'การเชื่อมต่อหมดอายุ — Google ขอให้ยืนยันสิทธิ์ใหม่'
      : 'Connection expired — Google requires re-authorization';
  } else if (errStr.indexOf('quota') >= 0) {
    friendly = isTH
      ? 'พื้นที่ Drive ไม่พอ — กรุณาเคลียร์พื้นที่หรืออัปเกรด Google'
      : 'Drive quota exceeded — please free up space or upgrade Google';
  } else if (errStr.indexOf('network') >= 0 || errStr.indexOf('timeout') >= 0) {
    friendly = isTH
      ? 'เชื่อมต่อเครือข่ายไม่เสถียร — กรุณาลองใหม่'
      : 'Network unstable — please retry';
  } else {
    friendly = isTH
      ? 'พบปัญหาในการเชื่อมต่อ — กรุณาลองเชื่อมต่อใหม่'
      : 'Connection issue — please try reconnecting';
  }
  // HTML-escape for safe innerHTML insertion (defensive · backend should be safe but better-safe)
  if (typeof escapeHtml === 'function') {
    return escapeHtml(friendly);
  }
  // Fallback if escapeHtml not loaded yet (shouldn't happen — app.js loads after)
  const div = document.createElement('div');
  div.textContent = friendly;
  return div.innerHTML;
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

  // v9.3.0 — invalid_grant / token revoked → render error state with re-connect prompt.
  // Backend marks last_sync_status="error" + last_sync_error when push helpers detect
  // RefreshError. UI surfaces this so user can re-auth without diving into logs.
  const isErrored = isBYOS && isConnected && _driveStatus.last_sync_status === 'error';

  // Status description
  const statusDesc = document.getElementById('storage-mode-desc');
  if (statusDesc) {
    if (isErrored) {
      // v9.3.5.1 — แปลง raw error → user-friendly + HTML-escape (กัน technical jargon โผล่หา user)
      const friendlyReason = _friendlyDriveErrorReason(_driveStatus.last_sync_error, isTH);
      const safeEmail = (typeof escapeHtml === 'function')
        ? escapeHtml(_driveStatus.drive_email || '')
        : (_driveStatus.drive_email || '');
      statusDesc.innerHTML = `
        <div class="storage-connected-info storage-errored">
          <div class="storage-connected-row">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--color-warning, #f59e0b)" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            <span>${isTH ? 'การเชื่อมต่อ Google Drive หมดอายุ' : 'Google Drive connection expired'}</span>
          </div>
          <div class="storage-email">${safeEmail}</div>
          <div class="storage-sync-time storage-error-detail">${isTH ? 'เหตุผล' : 'Reason'}: ${friendlyReason}</div>
          <div class="storage-folder">${isTH
            ? 'กดปุ่มด้านล่างเพื่อเชื่อมต่อใหม่ — ข้อมูลของคุณยังอยู่ครบ'
            : 'Click below to reconnect — your data is intact'
          }</div>
        </div>
      `;
    } else if (isBYOS && isConnected) {
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
    if (isErrored) {
      // v9.3.0 — error state: prominent "เชื่อมต่อใหม่" + secondary disconnect
      actionsEl.innerHTML = `
        <button class="btn btn-primary btn-sm" id="btn-reconnect-drive" onclick="connectDrive()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
          ${isTH ? 'เชื่อมต่อใหม่' : 'Reconnect'}
        </button>
        <button class="btn btn-outline btn-sm" id="btn-disconnect-drive" onclick="disconnectDrive()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
          ${isTH ? 'ยกเลิก' : 'Disconnect'}
        </button>
      `;
    } else if (isBYOS && isConnected) {
      actionsEl.innerHTML = `
        <button class="btn btn-primary btn-sm" id="btn-sync-drive" onclick="syncDriveNow()">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
          ${isTH ? 'ซิงค์ตอนนี้' : 'Sync now'}
        </button>
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
// Sync Drive Now (manual trigger)
// ═══════════════════════════════════════════

async function syncDriveNow() {
  const btn = document.getElementById('btn-sync-drive');
  const isTH = getLang() === 'th';
  if (btn) {
    btn.disabled = true;
    btn.textContent = isTH ? 'กำลังซิงค์...' : 'Syncing...';
  }

  try {
    const res = await authFetch('/api/drive/sync', { method: 'POST' });
    if (res.ok) {
      const data = await res.json();
      const s = data.stats || {};
      const summary = isTH
        ? `ซิงค์เสร็จ — ดึงใหม่ ${s.pulled_new || 0}, อัปเดต ${s.pulled_updated || 0}, ส่ง ${s.pushed_new || 0}, ข้อผิดพลาด ${s.errors || 0}`
        : `Sync done — pulled ${s.pulled_new || 0}, updated ${s.pulled_updated || 0}, pushed ${s.pushed_new || 0}, errors ${s.errors || 0}`;
      showToast(summary, s.errors > 0 ? 'warning' : 'success');
      await refreshDriveStatus();
      // Refresh files list so storage badges update
      if (typeof loadFiles === 'function') loadFiles();
    } else {
      const data = await res.json().catch(() => ({}));
      showToast(data?.detail?.error?.message || (isTH ? 'ซิงค์ล้มเหลว' : 'Sync failed'), 'error');
    }
  } catch {
    showToast(isTH ? 'ไม่สามารถซิงค์ได้' : 'Cannot sync', 'error');
  } finally {
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"/></svg>
        ${isTH ? 'ซิงค์ตอนนี้' : 'Sync now'}
      `;
    }
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
// v9.3.5 — Drive Error Banner (proactive UX)
// ═══════════════════════════════════════════

/**
 * Render banner ที่ top ของ /app เมื่อ last_sync_status='error'
 * (token revoked / Google API down / etc.)
 *
 * เรียกจาก refreshDriveStatus() — ทุกครั้งที่ status update
 * Why: User ไม่ต้องเปิด Profile menu เพื่อรู้ว่า Drive พัง · banner เห็นทันที
 */
function renderDriveErrorBanner() {
  const banner = document.getElementById('drive-error-banner');
  if (!banner) return;

  const isErrored = _driveStatus
    && _driveStatus.feature_available
    && _driveStatus.drive_connected
    && _driveStatus.last_sync_status === 'error';

  // Hidden conditions: ไม่มี error · หรือ user dismiss แล้ว session นี้
  if (!isErrored || _driveBannerDismissedThisSession) {
    banner.classList.add('hidden');
    return;
  }

  // Show banner + translate technical error → user-friendly text
  banner.classList.remove('hidden');
  const detail = document.getElementById('drive-error-banner-detail');
  if (detail) {
    const isTH = getLang() === 'th';
    // v9.3.5.1 — banner detail พิเศษกว่า profile modal (เพิ่ม "ไฟล์ใหม่ยังไม่ได้ขึ้น Drive")
    // เพราะ context banner = top of /app · user เพิ่งทำ action · ต้องบอกผลกระทบชัด
    const errStr = (_driveStatus.last_sync_error || '').toLowerCase();
    if (errStr.indexOf('invalid_grant') >= 0
        || errStr.indexOf('expired') >= 0
        || errStr.indexOf('revoked') >= 0) {
      detail.textContent = isTH
        ? 'การเชื่อมต่อหมดอายุ — ไฟล์ใหม่ยังไม่ได้ขึ้น Drive · กดเพื่อเชื่อมต่อใหม่'
        : 'Connection expired — new files haven\'t been uploaded to Drive · click to reconnect';
    } else {
      detail.textContent = isTH
        ? 'พบปัญหา — กรุณาลองเชื่อมต่อใหม่'
        : 'Connection issue — please try reconnecting';
    }
  }
}

/**
 * Wire ปุ่ม "เชื่อมต่อใหม่" + "ภายหลัง" ใน banner
 * Once-per-session — เรียกตอน initStorageMode
 */
function wireDriveErrorBanner() {
  const reconnectBtn = document.getElementById('drive-error-banner-reconnect');
  const dismissBtn = document.getElementById('drive-error-banner-dismiss');
  const isTH = getLang() === 'th';

  if (reconnectBtn && !reconnectBtn._wired) {
    reconnectBtn.addEventListener('click', () => {
      // v9.3.5 BUG-02 — guard double-click race
      // Why: 600ms toast delay เปิดช่อง user กดซ้ำ → 2 OAuth init requests → 1 stale state
      // Fix: disable ทันทีหลัง click · ไม่ต้อง re-enable เพราะ page redirect ไป Google
      if (reconnectBtn.disabled) return;
      reconnectBtn.disabled = true;

      showToast(
        isTH
          ? 'กำลังพาไป Google เพื่อยืนยันสิทธิ์ — ใช้เวลา 30 วินาที'
          : 'Redirecting to Google for re-authorization — takes 30 seconds',
        'info'
      );
      setTimeout(() => connectDrive(), 600);
    });
    reconnectBtn._wired = true;
  }

  if (dismissBtn && !dismissBtn._wired) {
    dismissBtn.addEventListener('click', () => {
      _driveBannerDismissedThisSession = true;
      const banner = document.getElementById('drive-error-banner');
      if (banner) banner.classList.add('hidden');
    });
    dismissBtn._wired = true;
  }
}

/**
 * Visibility-based polling — refresh status เมื่อ user กลับมา focus tab
 * Why: ไม่ใช้ continuous polling (ประหยัด API call) · trigger แค่เมื่อจำเป็น
 */
function setupDriveStatusVisibilityPolling() {
  // หลัง user สลับ tab กลับมา
  document.addEventListener('visibilitychange', async () => {
    if (document.visibilityState === 'visible') {
      try { await refreshDriveStatus(); } catch (_e) {}
    }
  });
  // หลัง browser focus กลับ window
  window.addEventListener('focus', async () => {
    try { await refreshDriveStatus(); } catch (_e) {}
  });
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
