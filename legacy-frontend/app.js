/**
 * Personal Data Bank (PDB) v6.1.0 — Frontend Logic
 * Multi-User Knowledge Workspace + PDB Connector Layer
 *
 * ┌─────────────────────────────────────────────────────────────┐
 * │ SECTION MAP (Phase 1 markers — for upcoming landing/app split)│
 * │   §A SHARED UTILITIES   ~lines    1– 188                     │
 * │   §B LANDING + AUTH     ~lines  189– 481                     │
 * │   §C APP MODULE         ~lines  483– end                     │
 * │ Search markers: "§A SHARED", "§B LANDING/AUTH", "§C APP"     │
 * └─────────────────────────────────────────────────────────────┘
 */

// ╔══════════════════════════════════════════════════════════════
// ║ §A SHARED UTILITIES — used by both landing and app contexts
// ║   • localStorage migration (v7.1 rebrand)
// ║   • global `state` object
// ║   • authFetch wrapper
// ║   • loading overlay + showToast + showConfirm helpers
// ║   • i18n (I18N dict + getLang/applyLanguage/t)
// ║   • escapeHtml + date formatters
// ║ TARGET FOR PHASE 2: most of this moves to shared.css/shared.js or lives in BOTH bundles
// ╚══════════════════════════════════════════════════════════════
// ═══════════════════════════════════════════
// v9.2.2 — iOS VIEWPORT HEIGHT FIX (--vh)
// Fixes "100vh" bug in legacy Safari (< 15.4) where footer is hidden.
// ═══════════════════════════════════════════
(() => {
  const _setVh = () => {
    let vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
  };
  _setVh();
  window.addEventListener('resize', _setVh);
  window.addEventListener('orientationchange', _setVh);
})();

// ═══════════════════════════════════════════
// LOCALSTORAGE MIGRATION (v7.1 rebrand)
// ย้าย key เก่า (projectkey_*) → key ใหม่ (pdb_*)
// เพื่อไม่ให้ผู้ใช้เดิมถูก logout หลัง rebrand
// ═══════════════════════════════════════════
(() => {
 const migrations = [['pdb_token','pdb_token'],['pdb_user','pdb_user'],['pdb_lang','pdb_lang']];
 migrations.forEach(([oldKey, newKey]) => {
  if (!localStorage.getItem(newKey) && localStorage.getItem(oldKey)) {
  localStorage.setItem(newKey, localStorage.getItem(oldKey));
  localStorage.removeItem(oldKey);
  }
 });
})();

// ═══════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════
// `var` (not const) so landing.js can access `state` cross-script.
var state = {
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
 authToken: localStorage.getItem('pdb_token') || null,
 currentUser: JSON.parse(localStorage.getItem('pdb_user') || 'null'),
};

// v7.1 — Duplicate detection: pending matches รอให้ user ตัดสินใจ keep/skip
// ─── เก็บไว้นอก state object เพราะ ephemeral (modal-scoped — ไม่ persist ข้าม session)
let _pendingDuplicates = [];

// ═══════════════════════════════════════════
// AUTH — v5.0
// ═══════════════════════════════════════════

/**
 * Wrapper for fetch() that adds JWT auth header.
 * IMPORTANT: background=true ใช้สำหรับ data-loading calls ที่ไม่ควร logout user
 * ถ้า server ยังไม่พร้อม (cold start). เฉพาะ explicit user actions
 * (เช่น upload, delete) ถึงจะ trigger session-expired logout.
 */
// `var` so landing.js can read/write these cross-script.
var _logoutDebounce = false;
var _isInitVerified = false; // true หลัง /api/auth/me สำเร็จครั้งแรก
async function authFetch(url, options = {}) {
 if (!options.headers) options.headers = {};
 if (state.authToken) {
 options.headers['Authorization'] = `Bearer ${state.authToken}`;
 }
 const isBackground = options._background === true;
 delete options._background; // ไม่ส่งไป fetch จริง
 let res;
 try {
 res = await fetch(url, options);
 } catch (err) {
 // Network error — server down or no internet
 if (!isBackground) {
  hideLoadingOverlay();
  showToast(getLang() === 'th' ? 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่' : 'Cannot connect to server. Please try again.', 'error');
 }
 throw err;
 }
 if (res.status === 401 && _isInitVerified) {
 // Token ถูก sign ด้วย key ที่ valid (เพราะ init verify ผ่านแล้ว)
 // แต่ตอนนี้ server reject → token หมดอายุจริง
 // Defense-in-depth: ถ้า request นี้ยิงไปโดยไม่มี Authorization header
 // (เช่น state.authToken ยัง null ตอน fire) → 401 = expected anonymous, ไม่ใช่
 // session-expired. กัน race ที่ initAuth set token เสร็จ "หลัง" fetch fired
 // แล้วทำให้ doLogout() ลบ token ที่เพิ่ง save (v8.1.1 redirect-loop)
 const sentAuthHeader = options.headers && options.headers['Authorization'];
 if (!sentAuthHeader) {
  return res;
 }
 if (!_logoutDebounce && state.authToken && !isBackground) {
  _logoutDebounce = true;
  hideLoadingOverlay();
  doLogout();
  showToast(getLang() === 'th' ? 'เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่' : 'Session expired. Please log in again.', 'error');
  setTimeout(() => { _logoutDebounce = false; }, 5000);
 }
 if (!isBackground) throw new Error('Session expired');
 }
 return res;
}

// ═══════════════════════════════════════════
// QUOTA LIMIT MODAL — v9.6.0
// ═══════════════════════════════════════════
// (เดิมเป็น Upgrade Modal สำหรับ Stripe — billing ถูกลบใน v9.6.0)
// เก็บชื่อ showUpgradeModal เพราะถูกเรียกหลายที่ — เปลี่ยน body เป็น
// แค่แจ้งเตือนเมื่อเกินโควต้า ไม่มี pricing CTA แล้ว
function showUpgradeModal(message) {
 document.getElementById('upgrade-modal-overlay')?.remove();
 const overlay = document.createElement('div');
 overlay.id = 'upgrade-modal-overlay';
 overlay.className = 'upgrade-modal-overlay';
 overlay.innerHTML = `
 <div class="upgrade-modal">
 <div class="upgrade-modal-icon"></div>
 <h3 class="upgrade-modal-title">${getLang() === 'th' ? 'เกินโควต้าที่กำหนด' : 'Quota Limit Reached'}</h3>
 <p class="upgrade-modal-message">${message}</p>
 <p class="upgrade-modal-message" style="font-size:13px;opacity:.7;margin-top:8px">
 ${getLang() === 'th' ? 'กรุณาติดต่อแอดมินเพื่อขอเพิ่มโควต้า' : 'Please contact admin to request a quota increase.'}
 </p>
 <div class="upgrade-modal-actions">
 <button class="btn btn-primary upgrade-modal-dismiss" onclick="this.closest('.upgrade-modal-overlay').remove()">
 ${getLang() === 'th' ? 'รับทราบ' : 'OK'}
 </button>
 </div>
 </div>
 `;
 overlay.addEventListener('click', (e) => { if (e.target === overlay) overlay.remove(); });
 document.body.appendChild(overlay);
}

// ═══════════════════════════════════════════
// UPLOAD RESULT MODAL (v7.5.0 — per-file actionable skip)
// ═══════════════════════════════════════════
// Why per-file modal vs comma-join toast:
//  - Toast cuts off after ~3 entries on mobile
//  - User can't tell which file failed why → can't act
//  - Each entry now shows code + message + concrete suggestion (e.g. "save as CSV")

function showUploadResultModal(uploaded, skipped) {
 // uploaded: list of {filename, ...} (only need .length for success count)
 // skipped:  list of {filename, code, message, suggestion}
 document.getElementById('upload-result-modal-overlay')?.remove();
 const isTH = getLang() === 'th';
 const successCount = (uploaded || []).length;
 const skipCount = (skipped || []).length;

 const skipIcon = (code) => {
   if (code === 'UNSUPPORTED_TYPE') return '📄';
   if (code === 'FILE_TOO_LARGE') return '📦';
   if (code === 'EMPTY_FILE') return '📭';
   if (code === 'QUOTA_EXCEEDED') return '🔒';
   return '⚠️';
 };

 const successHtml = successCount > 0
   ? `<div class="upload-result-success">
        <div class="upload-result-icon-success">✓</div>
        <div class="upload-result-success-text">${t('upload.successCount').replace('{count}', successCount)}</div>
      </div>`
   : '';

 const skipsHtml = (skipped || []).map(s => `
   <div class="upload-result-skip-card" data-skip-code="${escapeHtml(s.code || 'UNKNOWN')}">
     <div class="upload-result-skip-icon">${skipIcon(s.code)}</div>
     <div class="upload-result-skip-body">
       <div class="upload-result-skip-filename">${escapeHtml(s.filename)}</div>
       <div class="upload-result-skip-message">${escapeHtml(s.message || s.reason || '')}</div>
       ${s.suggestion ? `<div class="upload-result-skip-suggestion"><strong>${t('upload.suggestionLabel')}:</strong> ${escapeHtml(s.suggestion)}</div>` : ''}
     </div>
   </div>
 `).join('');

 const overlay = document.createElement('div');
 overlay.id = 'upload-result-modal-overlay';
 overlay.className = 'modal-overlay upload-result-modal-overlay';
 overlay.style.display = 'flex';
 overlay.innerHTML = `
   <div class="modal upload-result-modal" role="dialog" aria-modal="true" aria-labelledby="upload-result-title">
     <div class="modal-header">
       <h3 id="upload-result-title">${t('upload.resultTitle')}</h3>
     </div>
     <div class="modal-body">
       ${successHtml}
       ${skipCount > 0 ? `<div class="upload-result-skip-header">${t('upload.skippedCount').replace('{count}', skipCount)}</div>` : ''}
       <div class="upload-result-skip-list">${skipsHtml}</div>
     </div>
     <div class="modal-footer">
       <button class="btn btn-primary" id="upload-result-close-btn">${t('upload.understand')}</button>
     </div>
   </div>
 `;

 const close = () => overlay.remove();
 overlay.addEventListener('click', (e) => { if (e.target === overlay) close(); });
 document.body.appendChild(overlay);
 document.getElementById('upload-result-close-btn')?.addEventListener('click', close);

 // ESC key dismiss (v7.2.0 modal pattern)
 const escHandler = (e) => { if (e.key === 'Escape') { close(); document.removeEventListener('keydown', escHandler); } };
 document.addEventListener('keydown', escHandler);
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
 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
 <path d="M12 3l1.6 4.4L18 9l-4.4 1.6L12 15l-1.6-4.4L6 9l4.4-1.6z"/>
 <path d="M19 15l.7 1.8L21.5 17.5l-1.8.7L19 20l-.7-1.8L16.5 17.5l1.8-.7z"/>
 </svg>
 </div>`,
 default: `<div class="loading-icon default-spinner"></div>`,
 };

 const overlay = document.createElement('div');
 overlay.className = 'loading-overlay';
 overlay.innerHTML = `
 <div class="loading-overlay-card">
 <button class="loading-overlay-close" type="button" aria-label="ปิด" title="ปิดหน้าจอนี้">✕</button>
 ${icons[type] || icons.default}
 <div class="loading-message">${message.replace(/\\n/g, '<br>')}</div>
 <div class="loading-progress-bar"><div class="loading-progress-fill"></div></div>
 <div class="loading-elapsed">0s</div>
 </div>
 `;
 document.body.appendChild(overlay);
 _loadingOverlayEl = overlay;

 // v10.0.5 — manual close button (failsafe if polling stalls)
 const closeBtn = overlay.querySelector('.loading-overlay-close');
 if (closeBtn) {
   closeBtn.addEventListener('click', () => {
     hideLoadingOverlay();
   });
 }

 // Animate in
 requestAnimationFrame(() => overlay.classList.add('visible'));

 // Update elapsed time
 _loadingTimer = setInterval(() => {
 const elapsed = Math.floor((Date.now() - _loadingStartTime) / 1000);
 const elapsedEl = overlay.querySelector('.loading-elapsed');
 if (elapsedEl) elapsedEl.textContent = `${elapsed}s`;
 }, 1000);

 // v10.0.10 — Safety timeout extended 3min → 16min (covers watchdog's
 // 15-min hard limit + 1-min grace). This is the absolute hard fallback
 // when the polling loop itself stops firing (rare — e.g. tab killed and
 // restored without bfcache, or _organizeStatusPollHandle was lost). The
 // watchdog inside startOrganizeStatusPoll() is the primary timeout.
 _loadingSafetyTimeout = setTimeout(() => {
 hideLoadingOverlay();
 showToast(getLang() === 'th' ? '⏱ หมดเวลา — กรุณาลองใหม่' : '⏱ Timed out — please try again', 'error');
 }, 16 * 60 * 1000);
}

function hideLoadingOverlay() {
 if (_loadingTimer) { clearInterval(_loadingTimer); _loadingTimer = null; }
 if (_loadingSafetyTimeout) { clearTimeout(_loadingSafetyTimeout); _loadingSafetyTimeout = null; }
 if (_organizeStatusPollHandle) {
   clearTimeout(_organizeStatusPollHandle);
   _organizeStatusPollHandle = null;
 }
 if (_loadingOverlayEl) {
 _loadingOverlayEl.classList.add('fade-out');
 setTimeout(() => { _loadingOverlayEl?.remove(); _loadingOverlayEl = null; }, 300);
 }
}

// v10.0.3 — live organize-new progress poll
// v10.0.5 — Live processing timeline (step-by-step list with checkmarks)
// instead of single-line stuck spinner. Each phase becomes a card; current
// phase shows spinner, completed phases show ✓ with elapsed time.
let _organizeStatusPollHandle = null;
let _organizePhaseHistory = [];   // [{phase, step_th, step_en, started_at_ms, completed_at_ms, current, total}]
let _organizeStartedAtMs = null;

const PHASE_META = {
  starting:    {th: 'เริ่มประมวลผล', en: 'Starting', icon: '▶'},
  scanning:    {th: 'ตรวจหาไฟล์ใหม่', en: 'Scanning files', icon: '🔍'},
  clustering:  {th: 'AI จัดกลุ่มไฟล์', en: 'Clustering', icon: '🧩'},
  summary:     {th: 'AI สรุปไฟล์', en: 'Summarizing', icon: '📝'},
  enrich:      {th: 'เสริม metadata', en: 'Enriching', icon: '✨'},
  graph:       {th: 'สร้าง Knowledge Graph', en: 'Building Graph', icon: '🕸'},
  suggest:     {th: 'สร้าง Suggestions', en: 'Suggestions', icon: '💡'},
  duplicates:  {th: 'ตรวจหาไฟล์ซ้ำ', en: 'Detecting duplicates', icon: '🔁'},
  done:        {th: 'เสร็จสมบูรณ์', en: 'Complete', icon: '✅'},
  error:       {th: 'เกิดข้อผิดพลาด', en: 'Error', icon: '❌'},
};

function _fmtSec(ms) {
  if (ms == null) return '';
  const s = ms / 1000;
  if (s < 10) return s.toFixed(2) + 's';
  if (s < 60) return s.toFixed(1) + 's';
  const m = Math.floor(s / 60), r = Math.round(s % 60);
  return `${m}m${r}s`;
}

function startOrganizeStatusPoll() {
  // v10.0.5 — Frontend renders directly from BACKEND history array.
  // No more polling-race: even if the pipeline finishes between two polls,
  // the backend history retains every phase with its true start/elapsed time.
  _organizePhaseHistory = [];
  _organizeStartedAtMs = Date.now();
  if (_organizeStatusPollHandle) {
    clearTimeout(_organizeStatusPollHandle);
    _organizeStatusPollHandle = null;
  }
  // v10.0.5 — Watchdog: detect genuinely stalled organize and force-close.
  //
  // v10.0.10 — fix false-positive trips on long Gemini summary calls:
  // - Track `phase + current/total` (not just `phase`) so "summary 0/3"
  //   advancing to "summary 1/3" counts as activity. Previously only the
  //   phase string was compared, so a phase that internally progressed
  //   (e.g. summary 0/3 → 1/3 → 2/3) looked stalled because the string
  //   stayed "summary" the whole time.
  // - Extend phase-stall 90s → 240s. Gemini regularly takes 60-140s on a
  //   50k-char PDF — 90s tripped before the first file finished.
  // - Extend hard limit 5min → 15min. A 10-file batch can legitimately
  //   take 8-12 minutes (sequential clustering + parallel-5 summary +
  //   enrich + graph + suggest + duplicate detect).
  let _lastActivitySignature = null;
  let _lastPhaseChangedAt = Date.now();
  const WATCHDOG_PHASE_STALL_MS = 240 * 1000;
  const WATCHDOG_HARD_LIMIT_MS = 15 * 60 * 1000;

  const tick = async () => {
    try {
      if (typeof document !== 'undefined' && document.hidden) {
        _organizeStatusPollHandle = setTimeout(tick, 5000);
        return;
      }
      const res = await authFetch('/api/organize-status');
      if (!res.ok) {
        _organizeStatusPollHandle = setTimeout(tick, 2000);
        return;
      }
      const data = await res.json();
      const snap = data.snapshot;
      // v10.0.6 — Reject stale snapshot from a PREVIOUS organize run.
      // Backend keeps state for ~60s after done, so the first poll right after
      // we click "organize" may see the PREVIOUS run's snapshot before the
      // new POST handler reaches _pt.start(). Without this check, the auto-close
      // path triggers immediately and shows stale badge counts mid-flight.
      //
      // v10.0.9 — also handle `snap === null` (first organize after server
      // restart, or after gc_stale clears state). Without this branch, GET
      // /api/organize-status races ahead of the in-flight POST: backend has
      // no snapshot yet → returns running:false → auto-close fires → overlay
      // disappears while backend is still queueing the real work.
      // Watchdog (90s phase stall) catches the case where backend genuinely
      // never starts.
      const _snapStale = snap && snap.started_at &&
        !isNaN(new Date(snap.started_at).getTime()) &&
        new Date(snap.started_at).getTime() < _organizeStartedAtMs - 500;
      if (!snap || _snapStale) {
        // Backend hasn't called _pt.start() for THIS run yet. Keep polling.
        _organizeStatusPollHandle = setTimeout(tick, 500);
        return;
      }
      // Watchdog: detect stalled phase via composite activity signature
      // (phase:current/total + history length). Any of those advancing means
      // the backend is still alive.
      if (snap && snap.phase) {
        const sig = `${snap.phase}:${snap.current || 0}/${snap.total || 0}:${(snap.history || []).length}`;
        if (sig !== _lastActivitySignature) {
          _lastActivitySignature = sig;
          _lastPhaseChangedAt = Date.now();
        }
      }
      const overallElapsed = Date.now() - _organizeStartedAtMs;
      const phaseStalled = (Date.now() - _lastPhaseChangedAt) > WATCHDOG_PHASE_STALL_MS;
      if (phaseStalled || overallElapsed > WATCHDOG_HARD_LIMIT_MS) {
        console.warn('Organize watchdog tripped — force closing overlay', {signature: _lastActivitySignature, overallElapsed, phaseStalled});
        try { if (typeof showToast === 'function') showToast(getLang() === 'th' ? 'การจัดระเบียบใช้เวลานานเกิน — ปิดอัตโนมัติ' : 'Organize timed out — auto-closed', 'warning'); } catch (_) {}
        if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();
        if (typeof loadFiles === 'function') loadFiles();
        if (typeof loadStats === 'function') loadStats();
        if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount();
        const btn = document.getElementById('btn-organize-new');
        if (btn) btn.disabled = false;
        _organizeStatusPollHandle = null;
        return;
      }
      if (snap && Array.isArray(snap.history) && snap.history.length > 0) {
        // Replace local cache with the authoritative backend history.
        _organizePhaseHistory = snap.history.map(h => ({
          phase: h.phase,
          step_th: h.step_th,
          step_en: h.step_en,
          current: h.current,
          total: h.total,
          is_completed: !!h.is_completed,
          elapsed_sec: h.elapsed_sec || 0,
        }));
        renderOrganizeTimeline();
      } else if (snap) {
        // Fallback for old payload without history
        renderOrganizeTimeline();
        // v10.0.x — P3-11 · ถ้า backend ไม่ส่ง history แต่มี snap.step_th/en → update .loading-message ให้เห็น phase
        // เดิม: overlay text ค้างที่ "AI กำลังจัดระเบียบ..." (initial message) ไม่ขยับเลย
        // ใหม่: sync ข้อความ phase จริงเข้า .loading-message ทุก poll · user เห็นความเคลื่อนไหว
        if (_loadingOverlayEl) {
          const isTH = getLang() === 'th';
          const phaseMsg = isTH ? (snap.step_th || snap.phase) : (snap.step_en || snap.phase);
          const msgEl = _loadingOverlayEl.querySelector('.loading-message');
          if (msgEl && phaseMsg && !msgEl.classList.contains('hidden')) {
            const cleanMsg = String(phaseMsg).replace(/</g, '&lt;');
            if (msgEl.innerHTML !== cleanMsg) msgEl.innerHTML = cleanMsg;
          }
        }
      }
      if (!data.running) {
        // v10.0.5 — Backend says pipeline done. Auto-close overlay after a
        // short grace period (2.5s) so user can read the final "✅ Complete"
        // state. Don't wait for the POST/loadFiles chain — those might be
        // slow or stuck, but the work is genuinely done at this point.
        _organizeStatusPollHandle = setTimeout(() => {
          // Final refresh of timeline (in case state moved between polls)
          authFetch('/api/organize-status').then(r => r.json()).then(d => {
            if (d.snapshot && Array.isArray(d.snapshot.history)) {
              _organizePhaseHistory = d.snapshot.history.map(h => ({
                phase: h.phase,
                step_th: h.step_th,
                step_en: h.step_en,
                current: h.current,
                total: h.total,
                is_completed: !!h.is_completed,
                elapsed_sec: h.elapsed_sec || 0,
              }));
              renderOrganizeTimeline();
            }
          }).catch(() => {});
          // Auto-close overlay after 2.5s grace + always refresh badge/files
          setTimeout(() => {
            if (typeof hideLoadingOverlay === 'function') hideLoadingOverlay();
            if (typeof loadFiles === 'function') loadFiles();
            if (typeof loadStats === 'function') loadStats();
            if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount();
            // Reset organize-new button so it's clickable again
            const btn = document.getElementById('btn-organize-new');
            if (btn && btn.disabled) {
              btn.disabled = false;
              btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> <span data-i18n="myData.organizeNew">${typeof t === 'function' ? t('myData.organizeNew') : 'จัดระเบียบไฟล์ใหม่'}</span><span class="badge-count" id="unprocessed-badge" style="display:none;">0</span>`;
              if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount();
            }
          }, 2500);
          _organizeStatusPollHandle = null;
        }, 600);
        return;
      }
      _organizeStatusPollHandle = setTimeout(tick, 800);  // faster poll, more responsive
    } catch (e) {
      console.warn('organize-status poll error:', e);
      _organizeStatusPollHandle = setTimeout(tick, 2000);
    }
  };
  tick();
}

function renderOrganizeTimeline() {
  if (!_loadingOverlayEl) return;
  const isTH = getLang() === 'th';
  let body = _loadingOverlayEl.querySelector('.organize-timeline');
  if (!body) {
    // Upgrade the overlay: hide default message, inject timeline
    const card = _loadingOverlayEl.querySelector('.loading-overlay-card');
    if (!card) return;
    const msgEl = card.querySelector('.loading-message');
    if (msgEl) msgEl.classList.add('hidden');
    const bar = card.querySelector('.loading-progress-bar');
    if (bar) bar.classList.add('hidden');
    body = document.createElement('div');
    body.className = 'organize-timeline';
    card.insertBefore(body, card.querySelector('.loading-elapsed') || null);
    card.classList.add('loading-overlay-card-wide');
  }

  const title = isTH ? 'กำลังจัดระเบียบ — Live Timeline' : 'Organizing — Live Timeline';
  const rows = _organizePhaseHistory.map((h, i) => {
    const meta = PHASE_META[h.phase] || {th: h.phase, en: h.phase, icon: '•'};
    const isError = h.phase === 'error';
    const isDone = h.is_completed && !isError;
    const isCurrent = !h.is_completed && !isError;
    // Backend gives seconds directly
    const elapsedSec = h.elapsed_sec || 0;
    const elapsedMs = elapsedSec * 1000;

    const stateClass = isError ? 'is-error'
                     : isDone ? 'is-done'
                     : isCurrent ? 'is-current'
                     : 'is-pending';
    const stateIcon = isError ? '✕'
                    : isDone ? '✓'
                    : isCurrent ? '<span class="ot-spinner"></span>'
                    : '○';
    const titleTxt = isTH ? meta.th : meta.en;
    const detailTxt = isTH ? (h.step_th || '') : (h.step_en || '');
    const showDetail = detailTxt && detailTxt !== titleTxt;
    return `
      <div class="ot-row ${stateClass}">
        <div class="ot-state">${stateIcon}</div>
        <div class="ot-body">
          <div class="ot-title">${titleTxt}</div>
          ${showDetail ? `<div class="ot-detail">${detailTxt.replace(/</g,'&lt;')}</div>` : ''}
        </div>
        <div class="ot-time">${_fmtSec(elapsedMs)}</div>
      </div>
    `;
  }).join('');

  const totalElapsed = _organizeStartedAtMs ? Date.now() - _organizeStartedAtMs : 0;
  body.innerHTML = `
    <div class="ot-header">
      <span class="ot-header-title">${title}</span>
      <span class="ot-header-time">รวม ${_fmtSec(totalElapsed)}</span>
    </div>
    <div class="ot-rows">${rows || '<div class="ot-pending">รอเริ่ม...</div>'}</div>
  `;
}

// ═══════════════════════════════════════════

// §B LANDING + AUTH MODULE moved to landing.js (Phase 4)
// landing.js is loaded AFTER app.js in landing.html and app.html
// so it can reference state, _isInitVerified, authFetch, showToast,
// initAppData, getLang, t — all defined here as globals.


// ╔══════════════════════════════════════════════════════════════
// ║ §C APP MODULE — only runs after authentication
// ║   Owns the 8-page shell, sidebar, file management, graph,
// ║   chat, MCP setup, profile, and context memory features.
// ║   After Phase 4–5 this stays in app.js and ships only with
// ║   the /app bundle (not on landing).
// ╚══════════════════════════════════════════════════════════════

function initAppData() {
 // ทุก function ด้านล่างใช้ authFetch — fire-and-forget, ไม่ logout ถ้า fail
 loadStats();
 loadFiles();
 loadUsageInfo();
 // initGuideSystem();  // DISABLED 2026-05-15 · ปุ่ม FAB ทับ dev-logger button · เปิดกลับโดย uncomment + uncomment HTML block ใน app.html
 // v9.6.0 — loadBillingInfo() + initBilling() removed (Stripe ถูกลบ)
 maybeShowRebrandNotice();
 // v7.0 — BYOS Storage Mode (loads Drive status for profile modal)
 if (typeof initStorageMode === 'function') initStorageMode();
 // v8.2.0 — Reveal "Admin Panel" link in sidebar if current user is admin
 _revealAdminLinkIfAdmin();
}

// v8.2.0 — Show sidebar Admin Panel button เฉพาะ admin (best-effort, hidden by default)
// v8.1.2 perf: ใช้ sessionStorage cache จาก Google fragment handler (set ใน landing.js)
// → หลัง Google login ไม่ต้องยิง /api/admin/me ซ้ำ (ประหยัด 1 request, ~200-500ms)
function _revealAdminLinkIfAdmin() {
 const btn = document.getElementById('btn-admin-panel');
 if (!btn) return;
 // v10.0.x — P1-4 · ขยาย TTL จาก 60s → 24hr (admin status เปลี่ยนแทบไม่เคย · ลด /api/admin/me ที่ขึ้น 403 spam ใน console สำหรับ regular users)
 // ใช้ localStorage แทน sessionStorage เพื่อ persist ข้าม tab/reload
 const TTL_MS = 24 * 3600 * 1000;
 try {
  const cached = localStorage.getItem('pdb_admin_probe');
  const ts = parseInt(localStorage.getItem('pdb_admin_probe_ts') || '0', 10);
  if (cached !== null && (Date.now() - ts) < TTL_MS) {
   if (cached === '1') btn.classList.remove('hidden');
   return; // skip network call entirely
  }
 } catch (_) { /* localStorage unavailable */ }
 // Cache miss → fetch (silent on 401/403 · expected for non-admin)
 authFetch('/api/admin/me', { _background: true, _silent401: true })
  .then(res => {
   if (res && res.ok) btn.classList.remove('hidden');
   // Cache result regardless (1=admin · 0=not) เพื่อกัน probe ซ้ำ
   try {
    localStorage.setItem('pdb_admin_probe', res && res.ok ? '1' : '0');
    localStorage.setItem('pdb_admin_probe_ts', String(Date.now()));
   } catch (_) {}
  })
  .catch(() => {
   // Network error · cache as '0' temporarily (1 minute) เพื่อกัน retry storm
   try {
    localStorage.setItem('pdb_admin_probe', '0');
    localStorage.setItem('pdb_admin_probe_ts', String(Date.now() - TTL_MS + 60000));
   } catch (_) {}
  });
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
 const res = await authFetch('/api/usage', { _background: true });
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

// Billing (Stripe) removed in v9.6.0.
// See docs/restoration/billing-restore.md for full restore guide.

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
 // v9.3.5 — BYOS Drive disconnect alert banner + testing-mode notice
 // Why: data-i18n attrs ใน app.html ต้องมี keys ครบทั้ง 2 langs · ไม่งั้น
 // applyLanguage() จะ fallback to el.textContent (Thai default) ทำให้ EN
 // users เห็น Thai ใน banner title + buttons + notice
 'drive.errorBanner.title': 'Google Drive ของคุณหมดอายุการเชื่อมต่อ',
 'drive.errorBanner.detail': 'ไฟล์ใหม่ยังไม่ได้ขึ้น Drive — กดเพื่อเชื่อมต่อใหม่',
 'drive.errorBanner.reconnect': 'เชื่อมต่อใหม่',
 'drive.errorBanner.dismiss': 'ภายหลัง',
 'drive.testingNotice': 'ขณะนี้ระบบเชื่อมต่อ Drive แบบ Beta — การเชื่อมต่อจะหมดอายุทุก 7 วัน · กรุณาเชื่อมต่อใหม่เมื่อแอพแจ้งเตือน',

 // v9.4.0 — Upload Tray (Truthful Visibility)
 'upload.queuedToast':           'เพิ่ม {n} ไฟล์เข้าคิว ✓',
 'upload.tray.title':            'คิว Upload',
 'upload.tray.title_n':          'คิว Upload ({n})',
 'upload.tray.minimize':         'ย่อ',
 'upload.tray.queued':           'รอคิว',
 'upload.tray.working':          'กำลังทำ',
 'upload.tray.failed':           'ล้มเหลว',
 'upload.tray.done':             'เสร็จแล้ว',
 'upload.tray.retry':            'ลองใหม่',
 'upload.tray.dismiss':          'ลบออก',
 'upload.tray.cancel':           'ยกเลิก',
 'upload.tray.position':         'อันดับ {n}',
 'upload.tray.position_of':      'อันดับ {n} จาก {total}',
 'upload.tray.elapsed':          'ใช้เวลา {sec} วินาที',
 'upload.tray.elapsed_min':      'ใช้เวลา {min} นาที',
 'upload.tray.summary_queued':   '{n} รอคิว',
 'upload.tray.summary_extracting': '{n} กำลังทำ',
 'upload.tray.summary_failed':   '{n} ล้มเหลว',
 'upload.tray.system_degraded':  'ระบบประมวลผลล่าช้ากว่าปกติ — เรากำลังตรวจสอบ',
 'upload.tray.system_stopped':   'ระบบประมวลผลหยุด — กรุณาติดต่อแอดมิน',
 'upload.tray.empty_done':       'อัปโหลด + สกัดข้อความเสร็จแล้ว · ขั้นต่อไป: ให้ AI วิเคราะห์',
 'upload.tray.organize_now':     'จัดระเบียบทันที',
 'upload.tray.see_details':      'รายละเอียด',
 'upload.tray.stage_queued':     'เข้าคิว',
 'upload.tray.stage_started':    'เริ่มประมวลผล',
 'upload.tray.stage_completed':  'เสร็จ/ผิดพลาด',
 'upload.tray.attempt':          'ครั้งที่ลอง',

 // v8.1.0 — Google Sign-In
 'auth.signInWithGoogle': 'เข้าสู่ระบบด้วย Google',
 'auth.signUpWithGoogle': 'สมัครสมาชิกด้วย Google',
 'auth.or': 'หรือ',
 'auth.useGoogleHint': 'บัญชีนี้สมัครด้วย Google',
 'auth.emailNotVerified': 'อีเมล Google ยังไม่ verified',

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
 'myData.uploadHint': 'รองรับ เอกสาร / รูปภาพ (OCR ไทย) / Spreadsheet / เสียง + วิดีโอ (AI) / Code · 50+ formats · สูงสุด 200 MB · ครั้งละ 20 ไฟล์',
 'myData.allFiles': 'ไฟล์ทั้งหมด',
 // v9.1.0 — Raw File Vault filter chips
 'myData.filterAll': 'ทั้งหมด',
 'myData.filterProcessed': 'ประมวลผลแล้ว',
 'myData.filterVault': '📦 คลัง',
 'vault.badge': 'คลัง',
 'vault.toastUpload': 'เก็บใน "คลัง" — AI ค้นหาด้วยชื่อไฟล์ได้ แต่อ่านเนื้อหาไม่ได้',
 'vault.tryAnalyze': 'ลองวิเคราะห์',
 'vault.promoteSuccess': 'วิเคราะห์สำเร็จ — ย้ายไป "ประมวลผลแล้ว"',
 'vault.promoteStillVault': 'ยังวิเคราะห์ไม่ได้ — เก็บในคลังต่อไป',
 'myData.noFiles': 'ยังไม่มีไฟล์ — เพิ่มไฟล์เข้าพื้นที่ส่วนตัวของคุณ',
 'myData.delete': 'ลบ',
 'myData.askAi': 'ถาม AI',
 'onboarding.title': 'ยินดีต้อนรับสู่ Personal Data Bank',
 'onboarding.desc': 'เริ่มต้นด้วยการอัปโหลดไฟล์ — หรือเชื่อมต่อ Google Drive เพื่อเก็บข้อมูลใน Drive ของคุณเอง (ปลอดภัย · ควบคุมได้เต็มที่)',
 'onboarding.cta': 'เชื่อมต่อ Drive',

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
 'chat.thinking': 'AI กำลังคิด...',

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

 // v7.5.0 — Upload Result Modal (per-file skip with actionable suggestion)
 'upload.resultTitle': 'ผลการอัปโหลด',
 'upload.successCount': 'อัปโหลดสำเร็จ {count} ไฟล์',
 'upload.skippedCount': 'ข้าม {count} ไฟล์',
 'upload.understand': 'เข้าใจแล้ว',
 'upload.skipUnsupported': 'ไฟล์ไม่รองรับ',
 'upload.skipTooLarge': 'ไฟล์ใหญ่เกิน',
 'upload.skipQuota': 'เกินจำนวนที่เก็บได้',
 'upload.skipEmpty': 'ไฟล์ว่างเปล่า',
 'upload.suggestionLabel': 'คำแนะนำ',
 // v7.5.0 — Batch upload limit warnings
 'upload.batchTooManyTitle': 'อัปครั้งเดียว {count} ไฟล์ — เกินที่แนะนำ',
 'upload.batchRiskyMsg': 'ระบบรองรับครั้งละ 20 ไฟล์ ที่จำนวนนี้อาจช้าหรือ timeout — แบ่งเป็นรอบย่อยจะเสถียรกว่า',
 'upload.batchHardMsg': 'ระบบไม่รองรับการอัปเกิน 50 ไฟล์ในครั้งเดียว — กรุณาแบ่งเป็นรอบย่อย ครั้งละไม่เกิน 20 ไฟล์',
 'upload.batchProceedRisky': 'ดำเนินการต่อ (เสี่ยง)',
 'upload.batchSplit': 'ยกเลิก แบ่งเป็นรอบย่อย',

 // Toasts / dynamic
 'toast.uploaded': 'อัปโหลดเรียบร้อย',
 'toast.deleted': 'ลบเรียบร้อย',
 'toast.deletedCleaningDrive': 'ลบเรียบร้อย · กำลังเคลียร์ Google Drive',
 'toast.deletedDrivePicked': 'ลบจากระบบแล้ว · ไฟล์ต้นฉบับใน Drive ของคุณยังอยู่',
 'toast.profileSaved': 'บันทึกโปรไฟล์เรียบร้อย',

 // v9.4.2 — LINE Bot section (Profile modal)
 'line.title': 'LINE Bot',
 'line.desc': 'เข้าถึง PDB ผ่าน LINE — อัปโหลดไฟล์ ถาม AI ค้นข้อมูลจากมือถือ',
 'line.connect': 'เชื่อม LINE',
 'line.disconnect': 'เลิกเชื่อม',
 'line.openChat': 'เปิดใน LINE',
 'line.notConfigured': 'ระบบ LINE bot ยังไม่ถูกตั้งค่าบนเซิร์ฟเวอร์',
 'line.notLinked': 'ยังไม่เชื่อม',
 'line.displayName': 'ชื่อ LINE:',
 'line.linkedAt': 'เชื่อมเมื่อ:',
 'line.lastSeen': 'ใช้งานล่าสุด:',
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

 // Duplicate detection (v7.1)
 // v7.1.5 — research-backed wording (NN/G + Win11/macOS standards + Material 3 + Thai mobile)
 'dup.title': 'พบไฟล์คล้ายกัน {count} ไฟล์',
 'dup.subtitle': 'ไฟล์ที่อัปโหลดใหม่บางไฟล์มีเนื้อหาคล้ายกับไฟล์ที่มีอยู่แล้ว — เลือกทีละไฟล์ว่าจะเก็บหรือข้าม',
 'dup.labelNew': '(ใหม่)',
 'dup.labelSimilar': 'คล้าย',
 'dup.labelExact': '(ตรงเป๊ะ)',
 'dup.labelMatched': 'ตรงกัน',
 // Per-file radio (Win11 + macOS Finder convention)
 'dup.actionKeep': 'เก็บทั้งคู่',
 'dup.actionSkip': 'ข้ามไฟล์ใหม่',
 // Quick action bar
 'dup.quickKeep': 'เก็บทั้งหมด',
 'dup.quickSkip': 'ข้ามทั้งหมด',
 // Modal close button (NN/G: NOT "ยกเลิก" — no work to discard)
 'dup.cancel': 'ไว้ทีหลัง',
 // Confirm button — verb + count + object (NN/G)
 'dup.confirmKeepAll': 'เก็บทั้งหมด',
 'dup.confirmSkip': 'ข้ามไฟล์ใหม่ {count} ไฟล์',
 // Undo toast — 10s + X dismiss (Material 3 + WCAG 2.2.1)
 'dup.undoTitle': 'จะข้ามไฟล์ใหม่ {count} ไฟล์ใน 10 วิ',
 'dup.undoBtn': 'เลิกทำ',
 'dup.undoNow': 'ข้ามทันที',
 // Toast notifications
 'dup.toastKeptAll': 'เก็บไฟล์ทั้งหมดแล้ว',
 'dup.toastUndone': 'ยกเลิกการข้าม — ไฟล์ทั้งหมดยังอยู่',
 'dup.toastSkipped': 'ข้ามไฟล์ที่ซ้ำ {count} ไฟล์แล้ว',
 'dup.toastError': 'ไม่สามารถข้ามไฟล์ได้ ลองใหม่อีกครั้ง',
 },

 en: {
 // v9.3.5 — BYOS Drive disconnect alert banner + testing-mode notice
 'drive.errorBanner.title': 'Google Drive connection expired',
 'drive.errorBanner.detail': "New files haven't been uploaded to Drive — click to reconnect",
 'drive.errorBanner.reconnect': 'Reconnect',
 'drive.errorBanner.dismiss': 'Later',
 'drive.testingNotice': 'Drive connection is in Beta mode — expires every 7 days · please reconnect when prompted',

 // v9.4.0 — Upload Tray (Truthful Visibility)
 'upload.queuedToast':           '{n} files queued ✓',
 'upload.tray.title':            'Upload Queue',
 'upload.tray.title_n':          'Upload Queue ({n})',
 'upload.tray.minimize':         'Minimize',
 'upload.tray.queued':           'Queued',
 'upload.tray.working':          'Working',
 'upload.tray.failed':           'Failed',
 'upload.tray.done':             'Done',
 'upload.tray.retry':            'Retry',
 'upload.tray.dismiss':          'Dismiss',
 'upload.tray.cancel':           'Cancel',
 'upload.tray.position':         'Position {n}',
 'upload.tray.position_of':      'Position {n} of {total}',
 'upload.tray.elapsed':          'Elapsed {sec}s',
 'upload.tray.elapsed_min':      'Elapsed {min} min',
 'upload.tray.summary_queued':   '{n} queued',
 'upload.tray.summary_extracting': '{n} working',
 'upload.tray.summary_failed':   '{n} failed',
 'upload.tray.system_degraded':  'Processing slower than usual — investigating',
 'upload.tray.system_stopped':   'Processing system stopped — please contact admin',
 'upload.tray.empty_done':       'Uploaded + text extracted · Next: let AI analyze',
 'upload.tray.organize_now':     'Organize now',
 'upload.tray.see_details':      'Details',
 'upload.tray.stage_queued':     'Queued',
 'upload.tray.stage_started':    'Started',
 'upload.tray.stage_completed':  'Completed',
 'upload.tray.attempt':          'Attempt',

 // v8.1.0 — Google Sign-In
 'auth.signInWithGoogle': 'Sign in with Google',
 'auth.signUpWithGoogle': 'Sign up with Google',
 'auth.or': 'OR',
 'auth.useGoogleHint': 'This account uses Google sign-in',
 'auth.emailNotVerified': 'Google email is not verified',

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
 'myData.uploadHint': 'Supports docs / images (OCR) / spreadsheets / audio + video (AI) / code · 50+ formats · max 200 MB · up to 20 files at once',
 'myData.allFiles': 'All Files',
 // v9.1.0 — Raw File Vault filter chips
 'myData.filterAll': 'All',
 'myData.filterProcessed': 'Processed',
 'myData.filterVault': '📦 Vault',
 'vault.badge': 'Vault',
 'vault.toastUpload': 'Stored in "Vault" — AI can search by filename but cannot read content',
 'vault.tryAnalyze': 'Try analyze',
 'vault.promoteSuccess': 'Analyzed successfully — moved to Processed',
 'vault.promoteStillVault': 'Cannot analyze yet — kept in vault',
 'myData.noFiles': 'No files yet — add files to your personal space',
 'myData.delete': 'Delete',
 'myData.askAi': 'Ask AI',
 'onboarding.title': 'Welcome to Personal Data Bank',
 'onboarding.desc': 'Start by uploading a file — or connect Google Drive to keep your data in YOUR Drive (private · full control)',
 'onboarding.cta': 'Connect Drive',

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
 'chat.thinking': 'AI is thinking...',

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

 // v7.5.0 — Upload Result Modal
 'upload.resultTitle': 'Upload Result',
 'upload.successCount': '{count} file(s) uploaded',
 'upload.skippedCount': '{count} file(s) skipped',
 'upload.understand': 'Got it',
 'upload.skipUnsupported': 'Unsupported file',
 'upload.skipTooLarge': 'File too large',
 'upload.skipQuota': 'Quota exceeded',
 'upload.skipEmpty': 'Empty file',
 'upload.suggestionLabel': 'Suggestion',
 // v7.5.0 — Batch upload limit warnings
 'upload.batchTooManyTitle': 'Uploading {count} files at once — over recommended limit',
 'upload.batchRiskyMsg': 'System recommends max 20 files per batch. Larger batches may be slow or time out — splitting into smaller batches is more reliable.',
 'upload.batchHardMsg': 'System does not support uploading more than 50 files at once — please split into smaller batches of up to 20 files.',
 'upload.batchProceedRisky': 'Proceed anyway (risky)',
 'upload.batchSplit': 'Cancel & split',

 // Toasts / dynamic
 'toast.uploaded': 'Upload complete',
 'toast.deleted': 'Deleted successfully',
 'toast.deletedCleaningDrive': 'Deleted · cleaning Google Drive',
 'toast.deletedDrivePicked': 'Removed from system · original Drive file preserved',
 'toast.profileSaved': 'Profile saved',

 // v9.4.2 — LINE Bot section (Profile modal)
 'line.title': 'LINE Bot',
 'line.desc': 'Access PDB through LINE — upload files, ask AI, search knowledge from your phone',
 'line.connect': 'Connect LINE',
 'line.disconnect': 'Disconnect',
 'line.openChat': 'Open in LINE',
 'line.notConfigured': 'LINE bot is not configured on this server yet.',
 'line.notLinked': 'Not linked',
 'line.displayName': 'LINE name:',
 'line.linkedAt': 'Linked:',
 'line.lastSeen': 'Last seen:',
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

 // Duplicate detection (v7.1)
 // v7.1.5 — research-backed wording
 'dup.title': 'Found {count} similar files',
 'dup.subtitle': 'Some uploaded files are similar to existing ones — choose per file what to do',
 'dup.labelNew': '(new)',
 'dup.labelSimilar': 'similar to',
 'dup.labelExact': '(exact)',
 'dup.labelMatched': 'matched',
 'dup.actionKeep': 'Keep both',
 'dup.actionSkip': 'Skip new',
 'dup.quickKeep': 'Keep all',
 'dup.quickSkip': 'Skip all',
 'dup.cancel': 'Later',
 'dup.confirmKeepAll': 'Keep all',
 'dup.confirmSkip': 'Skip {count} new files',
 'dup.undoTitle': 'Skipping {count} new files in 10s',
 'dup.undoBtn': 'Undo',
 'dup.undoNow': 'Skip now',
 'dup.toastKeptAll': 'All files kept',
 'dup.toastUndone': 'Cancelled — all files kept',
 'dup.toastSkipped': 'Skipped {count} duplicate files',
 'dup.toastError': 'Failed to skip — try again',
 }
};

// Get current language — default TH
function getLang() {
 return localStorage.getItem('pdb_lang') || 'th';
}

// Get translation string
// v9.4.0: optional `vars` object for {placeholder} substitution
//   e.g., t('upload.tray.position', { n: 5 }) → "อันดับ 5"
// Backward compat: t(key) without vars works as before
function t(key, vars) {
 const lang = getLang();
 const tr = I18N[lang]?.[key] || I18N['en']?.[key] || key;
 if (!vars) return tr;
 return tr.replace(/\{(\w+)\}/g, (_, k) => vars[k] != null ? vars[k] : `{${k}}`);
}

// Apply translations to all [data-i18n] elements
function applyLanguage(lang) {
 localStorage.setItem('pdb_lang', lang);
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

 // v9.3.5.2 — Re-render dynamic content ที่ใช้ ternary (not data-i18n)
 // Why: applyLanguage updates แค่ [data-i18n] elements · Storage Mode section + banner
 // ใช้ getLang() ternary ใน innerHTML ตอน render → ต้อง re-render ตอน toggle lang
 try { if (typeof renderStorageModeUI === 'function') renderStorageModeUI(); } catch (_e) {}
 try { if (typeof renderDriveErrorBanner === 'function') renderDriveErrorBanner(); } catch (_e) {}
 // v9.4.2 (L5) — LINE bot badge "Connected"/"เชื่อมแล้ว" + notice text ใช้ getLang() ternary
 // ใน line_ui.js · ไม่ใช่ data-i18n → applyLanguage ปรับให้ไม่ได้ · ต้อง re-render ผ่าน loadLineStatus()
 try { if (typeof loadLineStatus === 'function') loadLineStatus(); } catch (_e) {}
}

// ═══════════════════════════════════════════
// v7.4.0 — Kebab menu (3-dots dropdown) — generic for cards
// ═══════════════════════════════════════════
// `toggleKebab(event, id)` opens/closes the menu with id=`kebab-{id}`.
// Only one menu can be open at a time. Outside-click and ESC close it.
let _openKebabId = null;

function toggleKebab(event, id) {
 event?.stopPropagation();
 const menu = document.getElementById(`kebab-${id}`);
 if (!menu) return;
 // Close any other open kebab first
 if (_openKebabId && _openKebabId !== id) {
  document.getElementById(`kebab-${_openKebabId}`)?.classList.add('hidden');
 }
 menu.classList.toggle('hidden');
 _openKebabId = menu.classList.contains('hidden') ? null : id;
}

function initKebabMenus() {
 // Outside-click closes the open kebab. We let the click bubble — the
 // kebab button itself uses event.stopPropagation() so its open click
 // does NOT reach this handler.
 document.addEventListener('click', () => {
  if (!_openKebabId) return;
  const open = document.getElementById(`kebab-${_openKebabId}`);
  if (open && !open.classList.contains('hidden')) open.classList.add('hidden');
  _openKebabId = null;
 });
 // ESC closes
 document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape' || !_openKebabId) return;
  document.getElementById(`kebab-${_openKebabId}`)?.classList.add('hidden');
  _openKebabId = null;
 });
}

// ═══════════════════════════════════════════
// v7.4.0 — Page Floating Action Buttons (mobile)
// ═══════════════════════════════════════════
// Each FAB just forwards its click to the matching desktop button so
// the underlying handler stays the single source of truth.
function initPageFABs() {
 document.getElementById('fab-my-data')?.addEventListener('click', () => {
  document.getElementById('btn-organize-new')?.click();
 });
 document.getElementById('fab-ctx')?.addEventListener('click', () => {
  document.getElementById('btn-new-context')?.click();
 });
}

// ═══════════════════════════════════════════
// v7.3.0 — Mobile sidebar (hamburger + slide-out)
// ═══════════════════════════════════════════
// On screens ≤ 768px the sidebar is hidden by default. The hamburger
// button toggles `.sidebar-open` on the .app-container, which the CSS
// uses to slide the sidebar in and reveal the backdrop.
//
// We also auto-close the sidebar when the user navigates (so the new
// page is visible behind it) and when ESC is pressed.
function initSidebarMobile() {
 const toggle = document.getElementById('sidebar-toggle');
 const backdrop = document.getElementById('sidebar-backdrop');
 const container = document.querySelector('.app-container');
 if (!toggle || !backdrop || !container) return;

 const isOpen = () => container.classList.contains('sidebar-open');
 const open = () => {
  container.classList.add('sidebar-open');
  toggle.setAttribute('aria-expanded', 'true');
 };
 const close = () => {
  container.classList.remove('sidebar-open');
  toggle.setAttribute('aria-expanded', 'false');
 };

 toggle.addEventListener('click', () => isOpen() ? close() : open());
 backdrop.addEventListener('click', close);

 // After the user picks a nav item on mobile, close the sidebar so the
 // newly active page is visible without an extra tap.
 document.querySelectorAll('.nav-item[data-page]').forEach(link => {
  link.addEventListener('click', () => {
   if (window.innerWidth <= 768) close();
  });
 });

 // ESC closes the sidebar (in addition to closing modals via initGlobalModalUX)
 document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && isOpen()) close();
 });
}

// ═══════════════════════════════════════════
// v7.2.0 — Global Modal UX (ESC + backdrop click)
// ═══════════════════════════════════════════
// Closes any open `.modal-overlay`, `.pack-modal-overlay`, or
// `.dup-modal-overlay` when the user presses ESC or clicks on the
// backdrop (the overlay element itself, not its inner `.modal` box).
//
// Special case: `#confirm-modal` is driven by `showConfirm()` which
// returns a Promise; closing it via class toggle alone would leak the
// Promise forever. We click `#confirm-cancel` instead so existing
// cleanup runs and the Promise resolves with `false` (Cancel).
//
// Out of scope: `auth-modal` lives on landing.html (handled by
// landing.js), and `file-detail-panel` uses a different DOM pattern
// (`.fd-backdrop`) — both are intentionally untouched here.
function initGlobalModalUX() {
 const OVERLAY_SELECTOR =
  '.modal-overlay:not(.hidden), .pack-modal-overlay:not(.hidden), .dup-modal-overlay:not(.hidden)';

 const closeOverlay = (overlay) => {
  if (!overlay || overlay.classList.contains('hidden')) return;
  if (overlay.id === 'confirm-modal') {
   document.getElementById('confirm-cancel')?.click();
  } else {
   overlay.classList.add('hidden');
  }
 };

 // ESC closes the topmost open overlay
 document.addEventListener('keydown', (e) => {
  if (e.key !== 'Escape') return;
  const overlays = document.querySelectorAll(OVERLAY_SELECTOR);
  if (!overlays.length) return;
  closeOverlay(overlays[overlays.length - 1]);
 });

 // Backdrop click — only fires when the click target IS the overlay
 // element (clicks inside `.modal` bubble through `e.target = .modal`)
 document.addEventListener('click', (e) => {
  const target = e.target;
  if (!(target instanceof Element)) return;
  if (
   target.classList.contains('modal-overlay') ||
   target.classList.contains('pack-modal-overlay') ||
   target.classList.contains('dup-modal-overlay')
  ) {
   closeOverlay(target);
  }
 });
}

// ═══════════════════════════════════════════
// INIT
// ═══════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
 // Auth system MUST run before applyLanguage() — initAuth() synchronously
 // hydrates state.authToken from localStorage. If applyLanguage() runs first,
 // loadLineStatus() fires /api/line/status without an Authorization header;
 // the resulting 401 races initAuth setting _isInitVerified=true, which makes
 // authFetch's 401 handler call doLogout() and wipe the just-loaded token.
 initAuth?.();

 // Apply saved language immediately (now safe — state.authToken set if fragment present)
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

 // Init all UI handlers — only when the app shell is present.
 // Each init wraps its own queries in `?.` but a few touch DOM
 // unconditionally; guard by app existence as a belt-and-braces.
 if (document.getElementById('app')) {
  try { initGlobalModalUX(); } catch (e) { console.warn('[init] initGlobalModalUX:', e); }
  try { initSidebarMobile(); } catch (e) { console.warn('[init] initSidebarMobile:', e); }
  try { initPageFABs(); } catch (e) { console.warn('[init] initPageFABs:', e); }
  try { initKebabMenus(); } catch (e) { console.warn('[init] initKebabMenus:', e); }
  try { initNavigation(); } catch (e) { console.warn('[init] initNavigation:', e); }
  try { initUpload(); } catch (e) { console.warn('[init] initUpload:', e); }
  // v9.4.0 — auto-open Upload Tray ถ้ามีไฟล์ค้างอยู่จาก session ก่อน (recover after reload)
  try {
    if (window.UploadTray && typeof UploadTray.openIfHasItems === 'function') {
      UploadTray.openIfHasItems();
    }
  } catch (e) { console.warn('[init] UploadTray.openIfHasItems:', e); }
  try { initFileFilterChips(); } catch (e) { console.warn('[init] initFileFilterChips:', e); }
  try { initProfile(); } catch (e) { console.warn('[init] initProfile:', e); }
  try { initChat(); } catch (e) { console.warn('[init] initChat:', e); }
  try { initGraphControls(); } catch (e) { console.warn('[init] initGraphControls:', e); }
  try { initKnowledgeTabs(); } catch (e) { console.warn('[init] initKnowledgeTabs:', e); }
  try { initMCP(); } catch (e) { console.warn('[init] initMCP:', e); }
 }
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
 const res = await authFetch('/api/stats', { _background: true });
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

 // v7.1.5 — Dedupe modal: per-file selector + quick actions + undo flow
 // Cancel = close modal, no action (NN/G "Later" — no work to discard)
 document.getElementById('dup-cancel-btn')?.addEventListener('click', () => {
  hideDuplicateModal();
  _pendingDuplicates = [];
  _dupSelections = {};
 });
 // Confirm = trigger flow (keep all OR show undo toast for skips)
 document.getElementById('dup-confirm-btn')?.addEventListener('click', confirmDupActions);
 // Quick actions = apply same value to all rows
 document.getElementById('dup-quick-keep-all')?.addEventListener('click', () => quickApplyAll('keep'));
 document.getElementById('dup-quick-skip-all')?.addEventListener('click', () => quickApplyAll('skip'));
}

// v7.2.0 — track upload in-flight + warn user before unload
var _uploadInFlight = false;
window.addEventListener('beforeunload', (e) => {
 if (!_uploadInFlight) return;
 // Browsers ignore custom messages but still show their own warning
 // when returnValue is a non-empty string.
 e.preventDefault();
 e.returnValue = '';
 return '';
});

// v9.2.1 — Batch limits (parallel pool 3 + 1 file/request — Fly.io 60s timeout
// no longer the bottleneck for upload itself; organize-new is the next step
// where huge batches still struggle).
//   ≤100 files = silently proceed (parallel-safe)
//   101-500   = warn but allow (organize-new may need to chunk later)
//   >500      = block + force split (memory + organize-new timeout risk)
const BATCH_SAFE_LIMIT = 100;
const BATCH_HARD_LIMIT = 500;

async function uploadFiles(fileList) {
 if (_uploadInFlight) {
  showToast(getLang() === 'th' ? 'กำลังอัปโหลดอยู่ กรุณารอให้เสร็จก่อน' : 'Upload already in progress, please wait', 'info');
  return;
 }
 const count = fileList.length;
 if (count === 0) return;

 // v7.5.0 — Batch size guard
 if (count > BATCH_HARD_LIMIT) {
   await showConfirm(
     t('upload.batchTooManyTitle').replace('{count}', count) + '\n\n' + t('upload.batchHardMsg'),
     { okText: t('upload.batchSplit'), cancelText: null, okOnly: true }
   );
   return;
 }
 if (count > BATCH_SAFE_LIMIT) {
   const proceed = await showConfirm(
     t('upload.batchTooManyTitle').replace('{count}', count) + '\n\n' + t('upload.batchRiskyMsg'),
     { okText: t('upload.batchProceedRisky'), cancelText: t('upload.batchSplit') }
   );
   if (!proceed) return;
 }

 const isTH = getLang() === 'th';
 // v9.4.0 — overlay only ระหว่าง byte upload (extract ย้ายไป background worker)
 // เปลี่ยน "Server processing..." indeterminate phase → ให้ Upload Tray ทำหน้าที่นั้น
 const baseMsg = (pct, done) => isTH
   ? `กำลังส่งไฟล์ขึ้น server... ${done}/${count} ไฟล์ • ${pct}%`
   : `Sending files to server... ${done}/${count} files • ${pct}%`;

 _uploadInFlight = true;
 showLoadingOverlay(baseMsg(0, 0), 'upload');
 const barEl0 = document.querySelector('.loading-overlay-card .loading-progress-bar');
 const fillEl0 = document.querySelector('.loading-overlay-card .loading-progress-fill');
 if (barEl0) barEl0.classList.remove('indeterminate');
 if (fillEl0) fillEl0.style.width = '0%';

 // v9.2.0+ — parallel uploads (concurrency 3, one file/request).
 // v9.4.0: backend = save+queue (return ≤200ms) → no more "processing" phase
 const UPLOAD_CONCURRENCY = 3;
 const fileArr = Array.from(fileList);
 const totalBytes = fileArr.reduce((s, f) => s + (f.size || 0), 0) || 1;
 const loadedBytes = new Array(fileArr.length).fill(0);
 const fileDone = new Array(fileArr.length).fill(false);

 const updateProgressUI = () => {
   const sumLoaded = loadedBytes.reduce((a, b) => a + b, 0);
   const doneCount = fileDone.filter(Boolean).length;
   const pct = Math.min(100, Math.round((sumLoaded / totalBytes) * 100));
   const msgEl = document.querySelector('.loading-overlay-card .loading-message');
   const fill = document.querySelector('.loading-overlay-card .loading-progress-fill');
   if (msgEl) msgEl.textContent = baseMsg(pct, doneCount);
   if (fill) fill.style.width = pct + '%';
 };

 const uploadOne = (file, idx) => new Promise((resolve) => {
   const form = new FormData();
   form.append('files', file);
   const xhr = new XMLHttpRequest();
   xhr.open('POST', '/api/upload');
   if (state.authToken) xhr.setRequestHeader('Authorization', `Bearer ${state.authToken}`);
   xhr.upload.onprogress = (ev) => {
     if (!ev.lengthComputable) return;
     loadedBytes[idx] = ev.loaded;
     updateProgressUI();
   };
   xhr.upload.onload = () => {
     loadedBytes[idx] = file.size || loadedBytes[idx];
     updateProgressUI();
   };
   xhr.onload = () => {
     fileDone[idx] = true;
     updateProgressUI();
     let body = null;
     try { body = JSON.parse(xhr.responseText); } catch (_) {}
     resolve({ status: xhr.status, body, file });
   };
   xhr.onerror = () => {
     fileDone[idx] = true;
     updateProgressUI();
     resolve({ status: 0, body: null, file, networkError: true });
   };
   xhr.send(form);
 });

 // v10.0.x — P0-3 · Auto-retry on transient network error (1 รอบ · 1.5s delay)
 // เดิม: ถ้า ECONNREFUSED ระหว่าง parallel upload → fail ไฟล์นั้นทันที · user เห็น toast error
 // ใหม่: retry อัตโนมัติ 1 ครั้ง · ส่วนใหญ่ recover ได้ (worker glitch / server reload)
 const uploadOneWithRetry = async (file, idx) => {
   const r1 = await uploadOne(file, idx);
   if (!r1.networkError && r1.status !== 0) return r1;
   // network error · wait 1.5s แล้วลอง 1 รอบ
   console.warn('[upload] network error, retrying once:', file.name);
   await new Promise(rs => setTimeout(rs, 1500));
   const r2 = await uploadOne(file, idx);
   if (r2.networkError) console.warn('[upload] retry also failed:', file.name);
   return r2;
 };

 try {
 const results = new Array(fileArr.length);
 let cursor = 0;
 const worker = async () => {
   while (cursor < fileArr.length) {
     const i = cursor++;
     // v10.0.x — P0-3 · ใช้ uploadOneWithRetry แทน uploadOne ตรงๆ
     results[i] = await uploadOneWithRetry(fileArr[i], i);
   }
 };
 const workerCount = Math.min(UPLOAD_CONCURRENCY, fileArr.length);
 await Promise.all(Array.from({ length: workerCount }, worker));

 // Aggregate per-request responses into the shape downstream code expects.
 let unauthorized = false;
 let networkErr = false;
 const aggUploaded = [];
 const aggSkipped = [];
 for (const r of results) {
   if (!r) continue;
   if (r.status === 401) { unauthorized = true; continue; }
   if (r.status === 0 || r.networkError) { networkErr = true; continue; }
   if (r.status >= 400) {
     aggSkipped.push({ filename: r.file.name, code: 'UPLOAD_FAILED',
                       reason: `HTTP ${r.status}`, message: `HTTP ${r.status}` });
     continue;
   }
   if (r.body) {
     if (Array.isArray(r.body.uploaded)) aggUploaded.push(...r.body.uploaded);
     if (Array.isArray(r.body.skipped)) aggSkipped.push(...r.body.skipped);
   }
 }
 if (unauthorized) { const err = new Error('UNAUTHORIZED'); err.status = 401; throw err; }
 if (networkErr && aggUploaded.length === 0) throw new Error('NETWORK');
 const data = { uploaded: aggUploaded, skipped: aggSkipped, count: aggUploaded.length };

 // v9.4.0.2 — Tray IS the feedback channel (no redundant toast at bottom-right)
 // เดิม v9.4.0: showToast + tray → ทั้งสองที่ bottom-right ชนกัน
 // แก้: tray เปิดมาคือ ack แล้ว · toast ที่เหลือ (vault/error/network) ยังโชว์ปกติ
 // เพราะ event เด่นกว่า tray notification + toast z-index 11050 > tray 11000
 if (data.count > 0) {
   if (window.UploadTray && typeof UploadTray.notifyEnqueued === 'function') {
     UploadTray.notifyEnqueued(data.uploaded);
   }
 }
 // v9.1.0 — Vault toast (vault files skip queue, ready immediately)
 const vaultCount = (data.uploaded || []).filter(u => u.file_kind === 'vault_only').length;
 if (vaultCount > 0) {
   setTimeout(() => showToast(`📦 ${vaultCount} ${t('vault.toastUpload')}`, 'info'), 1200);
 }
 if (data.skipped && data.skipped.length > 0) {
   // Quota-related → upgrade modal (preserve v5.9.x flow)
   const quotaSkip = data.skipped.find(s => s.code === 'QUOTA_EXCEEDED');
   if (quotaSkip) {
     setTimeout(() => showUpgradeModal(quotaSkip.message || quotaSkip.reason), 300);
   } else {
     // v7.5.0 — per-file actionable modal with code + suggestion (รวม QUEUE_FULL v9.4.0)
     setTimeout(() => showUploadResultModal(data.uploaded || [], data.skipped), 300);
   }
 }
 // v9.4.0 — main file list refresh ย้ายไป UploadTray (เรียกตอน queue empties)
 // ตรงนี้ refresh เฉพาะ vault files + stats ที่เปลี่ยนทันที (vault ไม่เข้าคิว)
 if (vaultCount > 0) {
   loadFiles();
 }
 loadStats();
 loadUnprocessedCount();
 loadUsageInfo();

 // v9.3.5 — เตือน user ถ้า BYOS connection พังตอน upload (background push silent-fail)
 // Why: backend log warning แต่ user ไม่เห็น · UI ต้องบอกตรงๆ ว่า "ไฟล์ขึ้น server แล้ว
 // แต่ไม่ได้ขึ้น Drive — เชื่อมต่อใหม่ที่แถบเตือนด้านบน"
 try {
  if (window._driveStatus
      && window._driveStatus.feature_available
      && window._driveStatus.storage_mode === 'byos'
      && window._driveStatus.last_sync_status === 'error') {
   showToast(
    isTH
     ? 'ไฟล์อัพโหลดเข้าเซิร์ฟเวอร์แล้ว แต่ยังไม่ได้ขึ้น Drive — กรุณาเชื่อมต่อใหม่ที่แถบเตือนด้านบน'
     : 'Files uploaded to server but not synced to Drive — please reconnect via top banner',
    'warning'
   );
  }
 } catch (_warnErr) { /* defensive — ไม่ block upload flow */ }
 } catch (e) {
  if (e && e.status === 401) {
   // Mirror authFetch's session-expired flow
   if (typeof doLogout === 'function') doLogout();
   showToast(isTH ? 'เซสชันหมดอายุ กรุณาเข้าสู่ระบบใหม่' : 'Session expired. Please log in again.', 'error');
  } else if (e && e.message === 'NETWORK') {
   showToast(isTH ? 'ไม่สามารถเชื่อมต่อเซิร์ฟเวอร์ได้ กรุณาลองใหม่' : 'Cannot connect to server. Please try again.', 'error');
  } else {
   showToast(isTH ? 'อัปโหลดล้มเหลว' : 'Upload failed', 'error');
  }
 } finally {
  _uploadInFlight = false;
  hideLoadingOverlay();
 }
}

// ════════════════════════════════════════════════════════
// UPLOAD TRAY — v9.4.0 (Honest Visibility for Background Queue)
// ════════════════════════════════════════════════════════
// Persistent UI tray ที่บอกความจริงเรื่องคิว upload ทุกขั้น
// ตาม Truthfulness Contract:
//   TC-1: ห้ามโชว์ pct ปลอม → progress_pct_known=false ใช้ indeterminate meter
//   TC-2: แสดง stage timestamps จริง (queued/started/completed) ในรายละเอียด
//   TC-3: why_slow text จาก backend (computed truthful)
//   TC-4: estimated_wait จาก rolling avg ของ worker จริง
//   TC-5: error message ระบุสาเหตุจริง (encrypted/quota/etc.)
//   TC-6: system status banner (degraded/stopped)
//
// Polling 2s · backoff to 5s after 30 ticks (1 min)
// Stops polling เมื่อ tray ปิด / queue ว่าง
// v9.4.3 — i18n boundary: backend คืน error CODE (ENCRYPTED/TIMEOUT/...) → frontend แปล.
// Mirror ของ backend.upload_worker.ERROR_CODES — ทุก code ต้องมีคู่ TH/EN.
// Legacy rows ที่ยังเก็บ Thai ดิบจะ fall-through display raw (no break).
const ERROR_CODE_LABELS = {
 ENCRYPTED:          { th: 'ไฟล์เข้ารหัส — ปลดล็อกก่อนอัปโหลดใหม่',                    en: 'Encrypted file — unlock before re-uploading' },
 FILE_MISSING:       { th: 'ไฟล์ดิบหายไประหว่างประมวลผล — ต้องอัปโหลดใหม่',             en: 'Raw file lost mid-process — re-upload required' },
 TIMEOUT:            { th: 'ประมวลผลใช้เวลานานเกินกำหนด — ลองแบ่งไฟล์เล็กลงหรือกดลองใหม่', en: 'Processing timed out — split file or retry' },
 OUT_OF_MEMORY:      { th: 'ไฟล์ใหญ่เกินที่ระบบรับไหว — ลองแบ่งไฟล์เล็กลง',              en: 'File too large for system memory — split smaller' },
 ENCODING:           { th: 'ไฟล์มี encoding ผิดปกติ — ลอง re-save เป็น UTF-8 แล้วอัปใหม่', en: 'File encoding invalid — re-save as UTF-8 and retry' },
 QUOTA_EXCEEDED:     { th: 'Gemini API ใช้เกินโควต้า — รอเดือนหน้าหรือเปลี่ยนแพลน',     en: 'Gemini quota exceeded — wait next month or upgrade plan' },
 GEMINI_UNAVAILABLE: { th: 'Gemini ตอบช้ากว่าปกติ — กดลองใหม่อีกครั้ง',                  en: 'Gemini service degraded — please retry' },
 GEMINI_AUTH:        { th: 'Gemini API key ไม่ถูกต้อง — ติดต่อแอดมิน',                   en: 'Gemini API key invalid — contact admin' },
 MODEL_DEPRECATED:   { th: 'AI model ปลด/เปลี่ยนชื่อแล้ว — ติดต่อแอดมินอัปเดต GEMINI_FILE_MODEL', en: 'AI model deprecated — admin must update GEMINI_FILE_MODEL' },
 FILE_NOT_ACTIVE:    { th: 'Gemini เตรียมไฟล์ไม่ทัน — กดลองใหม่อีกครั้ง',                en: 'Gemini file not ready — please retry' },
 PERMISSION_DENIED:  { th: 'Gemini API ไม่อนุญาต — ตรวจสอบ key permissions',             en: 'Gemini API denied — check key permissions' },
 CLIENT_ERROR:       { th: 'Gemini ปฏิเสธคำขอ — กดลองใหม่หรือติดต่อแอดมินถ้ายังไม่หาย',  en: 'Gemini rejected request — retry or contact admin' },
 OCR_FAIL:           { th: 'OCR engine ขัดข้อง — ลองอัปใหม่หรือใช้ไฟล์ text แทนรูป',     en: 'OCR engine failed — retry or use a text file' },
 NETWORK:            { th: 'ปัญหาเครือข่าย — กดลองใหม่อีกครั้ง',                          en: 'Network issue — please retry' },
 UNKNOWN:            { th: 'ประมวลผลล้มเหลว — กดลองใหม่หรือติดต่อแอดมิน',                en: 'Processing failed — retry or contact admin' },
};

function localizeError(s) {
 if (!s) return s;
 const lang = getLang();
 const label = ERROR_CODE_LABELS[s];
 if (label) return label[lang] || label.th || s;
 return s;  // legacy raw Thai → display as-is (backwards compat)
}

// progress_step regex translations TH→EN. Worker เขียน Thai ดิบใน DB; ที่ frontend
// match pattern ก่อน render. Pattern miss = fall through display raw (no break).
const STEP_TRANSLATIONS_EN = [
 [/^อันดับที่ (\d+) — กำลังรอคิว$/,                    (m) => `Queue position ${m[1]}`],
 [/^กำลังประมวลผล$/,                                   () => 'Processing'],
 [/^เตรียมประมวลผล$/,                                  () => 'Preparing'],
 [/^อัปโหลด(วิดีโอ|รูป)?ไป Gemini( Files API)?$/,      () => 'Uploading to Gemini'],
 [/^Gemini เตรียมไฟล์ \(([A-Z_]+), (\d+)s\)$/,         (m) => `Gemini preparing (${m[1]}, ${m[2]}s)`],
 [/^Gemini ถอดเสียง( \(.+\))?$/,                       () => 'Gemini transcribing'],
 [/^Gemini วิเคราะห์(วิดีโอ|รูป)( \(.+\))?$/,           () => 'Gemini analyzing'],
 [/^รับผลลัพธ์จาก Gemini$/,                           () => 'Receiving from Gemini'],
 [/^บันทึกผลลัพธ์$/,                                   () => 'Saving result'],
 [/^เปิดรูปภาพ$/,                                      () => 'Opening image'],
 [/^OCR รูปภาพ$/,                                      () => 'OCR image'],
 [/^ประมวลผลข้อความ Thai$/,                           () => 'Post-processing Thai text'],
 [/^ตรวจไฟล์ PDF$/,                                   () => 'Inspecting PDF'],
 [/^กำลังอ่านข้อความในไฟล์$/,                          () => 'Reading file content'],
];

function localizeBackendStep(s) {
 if (!s) return s;
 if (getLang() !== 'en') return s;  // TH passes through unchanged
 for (const [re, fn] of STEP_TRANSLATIONS_EN) {
  const m = s.match(re);
  if (m) return fn(m);
 }
 return s;  // unknown pattern → display raw
}

const UploadTray = (() => {
 let _pollHandle = null;
 let _pollAttempts = 0;
 let _isOpen = false;
 let _lastSnapshot = { active: [], failed: [], summary: { total_active: 0, failed_count: 0 } };
 const _expandedIds = new Set();  // file_id ที่ user click "รายละเอียด"

 const POLL_INTERVAL_MS = 2000;
 const POLL_BACKOFF_AFTER = 30;  // ticks before slow poll
 const POLL_BACKOFF_MS = 5000;

 const $ = (sel, root = document) => root.querySelector(sel);
 const isTH = () => getLang() === 'th';

 // Local HTML escape (ไม่ใช้ globally — UploadTray-only utility)
 function _esc(s) {
   if (s == null) return '';
   return String(s)
     .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
     .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
 }

 function _formatElapsed(sec) {
   if (sec < 60) return t('upload.tray.elapsed', { sec });
   return t('upload.tray.elapsed_min', { min: Math.floor(sec / 60) });
 }

 function _formatTime(iso) {
   try {
     const d = new Date(iso);
     return d.toLocaleString(isTH() ? 'th-TH' : 'en-US', {
       hour: '2-digit', minute: '2-digit', second: '2-digit',
     });
   } catch (e) { return iso; }
 }

 function _ensureDom() {
   if ($('.upload-tray')) return;
   const titleText = t('upload.tray.title');
   const html = `
     <aside class="upload-tray" role="region" aria-label="${_esc(titleText)}">
       <header class="upload-tray-header">
         <h3 class="upload-tray-title">
           <svg class="upload-tray-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
             <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"></path>
             <polyline points="17 8 12 3 7 8"></polyline>
             <line x1="12" y1="3" x2="12" y2="15"></line>
           </svg>
           <span class="upload-tray-title-text">${_esc(titleText)}</span>
         </h3>
         <button class="upload-tray-close" type="button" aria-label="${_esc(t('upload.tray.minimize'))}">
           <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" aria-hidden="true">
             <line x1="6" y1="6" x2="18" y2="18"></line>
             <line x1="6" y1="18" x2="18" y2="6"></line>
           </svg>
         </button>
       </header>
       <div class="upload-tray-banner" hidden></div>
       <ul class="upload-tray-list" role="list"></ul>
       <footer class="upload-tray-footer">
         <span class="upload-tray-summary"></span>
       </footer>
     </aside>
   `;
   document.body.insertAdjacentHTML('beforeend', html);
   $('.upload-tray-close').addEventListener('click', close);
 }

 async function _fetchStatus() {
   try {
     const res = await authFetch('/api/upload-status');
     if (!res.ok) return _lastSnapshot;
     const data = await res.json();
     _lastSnapshot = data;
     return data;
   } catch (e) {
     console.warn('UploadTray fetchStatus error:', e);
     return _lastSnapshot;
   }
 }

 async function openIfHasItems() {
   try {
     const data = await _fetchStatus();
     if ((data.summary && data.summary.total_active > 0)
         || (data.summary && data.summary.failed_count > 0)) {
       open();
     }
   } catch (_) { /* defensive — tray ไม่ open ถ้า /api fail */ }
 }

 function open() {
   if (_isOpen) return;
   _ensureDom();
   $('.upload-tray').classList.add('is-open');
   _isOpen = true;
   _startPolling();
 }

 function close() {
   if (!_isOpen) return;
   const tray = $('.upload-tray');
   if (tray) tray.classList.remove('is-open');
   _isOpen = false;
   _stopPolling();
 }

 function notifyEnqueued(uploadedList) {
   if (!uploadedList || uploadedList.length === 0) return;
   open();
   // Optimistic render — ใส่ไฟล์ที่เพิ่ง enqueue ทันที (ไม่ต้องรอ poll tick แรก)
   const optimistic = uploadedList
     .filter(u => u.processing_status === 'queued')
     .map(u => ({
       id: u.id, filename: u.filename, filetype: u.filetype,
       processing_status: 'queued',
       extraction_status: 'pending',
       queue_position: u.queue_position || 1,
       progress_step: t('upload.tray.position', { n: u.queue_position || 1 }),
       progress_pct: null,
       progress_pct_known: false,
       stages: { queued_at: u.uploaded_at, extract_started_at: null, extract_completed_at: null },
       elapsed_sec: 0,
       attempt_count: 0,
       is_retryable: false,
       why_slow: null,
     }));
   if (optimistic.length === 0) return;
   _lastSnapshot = {
     active: [...optimistic, ...(_lastSnapshot.active || [])],
     failed: _lastSnapshot.failed || [],
     summary: {
       ...(_lastSnapshot.summary || {}),
       total_active: ((_lastSnapshot.summary && _lastSnapshot.summary.total_active) || 0) + optimistic.length,
       queued_count: ((_lastSnapshot.summary && _lastSnapshot.summary.queued_count) || 0) + optimistic.length,
       extracting_count: (_lastSnapshot.summary && _lastSnapshot.summary.extracting_count) || 0,
       failed_count: (_lastSnapshot.summary && _lastSnapshot.summary.failed_count) || 0,
       system_status: (_lastSnapshot.summary && _lastSnapshot.summary.system_status) || 'ok',
     },
   };
   _render(_lastSnapshot);
 }

 function _startPolling() {
   if (_pollHandle) return;
   _pollAttempts = 0;
   const tick = async () => {
     // v10.0.0 -- if the user is on another tab, skip the actual DB hit and
     // re-schedule for a longer interval. Without this, idle background tabs
     // pummel /api/upload-status every 2s forever -- wasted server/DB CPU
     // and user-device battery.
     if (typeof document !== 'undefined' && document.hidden) {
       _pollHandle = setTimeout(tick, POLL_BACKOFF_MS);
       return;
     }

     const data = await _fetchStatus();
     _render(data);
     _pollAttempts++;

     const noActive = !data.summary || data.summary.total_active === 0;
     const noFailed = !data.summary || data.summary.failed_count === 0;

     if (noActive && noFailed) {
       _stopPolling();
       // ทุกอย่างเสร็จ → refresh main list + auto-close
       try {
         if (typeof loadFiles === 'function') loadFiles();
         if (typeof loadStats === 'function') loadStats();
         if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount();
       } catch (e) { console.warn('UploadTray refresh error:', e); }

       // v10.0.x — Context-aware banner + CTA "จัดระเบียบทันที"
       // เดิม: "ทุกไฟล์เสร็จเรียบร้อย" → user งงเพราะ AI ยังไม่ organize · ไฟล์ดู "ค้าง"
       // ใหม่: บอกชัดว่า "อัปโหลด+สกัดข้อความเสร็จ" + ปุ่มคลิก organize ทันที (ไม่ต้องไปหาปุ่ม)
       const banner = $('.upload-tray-banner');
       if (banner) {
         banner.hidden = false;
         banner.className = 'upload-tray-banner is-success';
         banner.innerHTML = `<div>${_esc(t('upload.tray.empty_done'))}</div>
           <button type="button" class="banner-cta" data-action="organize-now">
             <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="13 2 13 9 20 9"/><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/></svg>
             <span>${_esc(t('upload.tray.organize_now'))}</span>
           </button>`;
         const ctaBtn = banner.querySelector('[data-action="organize-now"]');
         if (ctaBtn) {
           ctaBtn.addEventListener('click', () => {
             // เรียก runOrganizeNew (defined ใน global scope) + ปิด tray
             try {
               if (typeof runOrganizeNew === 'function') runOrganizeNew();
               else if (typeof window.runOrganizeNew === 'function') window.runOrganizeNew();
             } catch (e) { console.warn('UploadTray banner CTA → runOrganizeNew failed:', e); }
             close();
           });
         }
       }
       // v10.0.x — Pulse animation on #btn-organize-new for 8 วินาที
       // "หางตา" user หา CTA ในหน้า /app · auto-remove class ออกหลัง 8s
       try {
         const orgBtn = document.getElementById('btn-organize-new');
         if (orgBtn) {
           orgBtn.classList.add('pulse-attention');
           setTimeout(() => orgBtn.classList.remove('pulse-attention'), 8000);
         }
       } catch (_) {}

       // v10.0.x — auto-close timer 2s → 5s (ให้ user มีเวลาเห็น/กด CTA)
       setTimeout(() => close(), 5000);
       return;
     }

     const interval = _pollAttempts > POLL_BACKOFF_AFTER ? POLL_BACKOFF_MS : POLL_INTERVAL_MS;
     _pollHandle = setTimeout(tick, interval);
   };
   tick();

   // v10.0.0 -- when the tab becomes visible again after being hidden,
   // refresh immediately so the user sees current state without waiting
   // for the next backoff tick.
   if (typeof document !== 'undefined' && !UploadTray._visListenerAdded) {
     document.addEventListener('visibilitychange', () => {
       if (!document.hidden && _pollHandle) {
         clearTimeout(_pollHandle);
         _pollHandle = setTimeout(tick, 100);
       }
     });
     UploadTray._visListenerAdded = true;
   }
 }

 function _stopPolling() {
   if (_pollHandle) {
     clearTimeout(_pollHandle);
     _pollHandle = null;
   }
 }

 function _render(data) {
   const list = $('.upload-tray-list');
   const titleEl = $('.upload-tray-title-text');
   const summaryEl = $('.upload-tray-summary');
   const banner = $('.upload-tray-banner');
   if (!list) return;

   const summary = data.summary || {};
   const activeCount = summary.total_active || 0;
   const failedCount = summary.failed_count || 0;
   const totalShow = activeCount + failedCount;

   if (titleEl) {
     titleEl.textContent = totalShow > 0
       ? t('upload.tray.title_n', { n: totalShow })
       : t('upload.tray.title');
   }

   if (summaryEl) {
     const parts = [];
     if (summary.queued_count) parts.push(t('upload.tray.summary_queued', { n: summary.queued_count }));
     if (summary.extracting_count) parts.push(t('upload.tray.summary_extracting', { n: summary.extracting_count }));
     if (failedCount) parts.push(t('upload.tray.summary_failed', { n: failedCount }));
     summaryEl.textContent = parts.join(' • ');
   }

   // System status banner (TC-6)
   if (banner) {
     const status = summary.system_status || 'ok';
     if (status === 'degraded') {
       banner.hidden = false;
       banner.textContent = t('upload.tray.system_degraded');
       banner.className = 'upload-tray-banner is-warning';
     } else if (status === 'stopped') {
       banner.hidden = false;
       banner.textContent = t('upload.tray.system_stopped');
       banner.className = 'upload-tray-banner is-error';
     } else {
       banner.hidden = true;
     }
   }

   // v10.0.x — P3-13 · sort active items by queued_at (เก่าสุด = อันดับ 1)
   //   เดิม: backend ส่งมาแล้วเรียง queued_at asc · แต่ notifyEnqueued() prepend optimistic
   //         ทำให้ใหม่อยู่ก่อน old → ลำดับ 1→3→2 ใน UI
   //   ใหม่: re-sort ตอน render ทุกครั้ง · stable order ตาม queued_at เสมอ
   const sortedActive = [...(data.active || [])].sort((a, b) => {
     const aT = a?.stages?.queued_at ? new Date(a.stages.queued_at).getTime() : 0;
     const bT = b?.stages?.queued_at ? new Date(b.stages.queued_at).getTime() : 0;
     return aT - bT;
   });
   const items = [...sortedActive, ...(data.failed || [])];
   list.innerHTML = items.map(_renderItem).join('');

   // Wire actions
   list.querySelectorAll('[data-cancel-id]').forEach(btn => {
     btn.addEventListener('click', () => _onCancel(btn.dataset.cancelId));
   });
   list.querySelectorAll('[data-retry-id]').forEach(btn => {
     btn.addEventListener('click', () => _onRetry(btn.dataset.retryId));
   });
   list.querySelectorAll('[data-dismiss-id]').forEach(btn => {
     btn.addEventListener('click', () => _onDismiss(btn.dataset.dismissId));
   });
   list.querySelectorAll('[data-toggle-id]').forEach(btn => {
     btn.addEventListener('click', () => {
       const id = btn.dataset.toggleId;
       if (_expandedIds.has(id)) _expandedIds.delete(id);
       else _expandedIds.add(id);
       _render(_lastSnapshot);
     });
   });
 }

 function _renderItem(item) {
   const isFailed = item.processing_status === 'error';
   const isExtracting = item.processing_status === 'extracting';
   const isExpanded = _expandedIds.has(item.id);

   const pillClass = isFailed ? 'is-error' : isExtracting ? 'is-active' : 'is-warning';
   const pillText = isFailed ? t('upload.tray.failed')
                  : isExtracting ? t('upload.tray.working')
                  : t('upload.tray.queued');

   const ext = _esc((item.filetype || '—').toUpperCase());
   const filename = _esc(item.filename);

   let body = '';
   if (isFailed) {
     body = `
       <div class="upload-tray-error" role="alert">
         ${_esc(localizeError(item.extract_error) || (isTH() ? 'ไม่ทราบสาเหตุ' : 'Unknown error'))}
       </div>`;
   } else if (isExtracting) {
     // TC-1 — pct ที่รู้ใช้ determinate, ไม่รู้ใช้ indeterminate
     const meterCls = item.progress_pct_known ? 'meter' : 'meter is-indeterminate';
     const pct = item.progress_pct_known ? Math.max(0, Math.min(100, item.progress_pct || 0)) : 0;
     const fillStyle = item.progress_pct_known ? `width:${pct}%` : '';
     const ariaNow = item.progress_pct_known ? `aria-valuenow="${pct}"` : '';
     body = `
       <div class="upload-tray-step">${_esc(localizeBackendStep(item.progress_step) || '...')}</div>
       <div class="${meterCls}" role="progressbar" ${ariaNow} aria-valuemin="0" aria-valuemax="100">
         <div class="meter-fill" style="${fillStyle}"></div>
       </div>
       ${item.why_slow ? `<div class="upload-tray-whyslow">${_esc(item.why_slow)}</div>` : ''}`;
   } else {
     body = `
       <div class="upload-tray-step">${_esc(localizeBackendStep(item.progress_step) || t('upload.tray.position', { n: item.queue_position }))}</div>
       ${item.why_slow ? `<div class="upload-tray-whyslow">${_esc(item.why_slow)}</div>` : ''}`;
   }

   // Stages (TC-2 truthful timestamps) — collapsed by default, click "รายละเอียด"
   const stages = item.stages || {};
   const stagesHtml = isExpanded ? `
     <dl class="upload-tray-stages">
       <dt>${_esc(t('upload.tray.stage_queued'))}</dt>
       <dd>${stages.queued_at ? _formatTime(stages.queued_at) : '—'}</dd>
       <dt>${_esc(t('upload.tray.stage_started'))}</dt>
       <dd>${stages.extract_started_at ? _formatTime(stages.extract_started_at) : '—'}</dd>
       <dt>${_esc(t('upload.tray.stage_completed'))}</dt>
       <dd>${stages.extract_completed_at ? _formatTime(stages.extract_completed_at) : '—'}</dd>
       <dt>${_esc(t('upload.tray.attempt'))}</dt>
       <dd>${(item.attempt_count || 0) + 1}</dd>
     </dl>
   ` : '';

   const elapsedHtml = (item.elapsed_sec != null && item.elapsed_sec > 0)
     ? `<span class="upload-tray-elapsed">${_formatElapsed(item.elapsed_sec)}</span>`
     : '';

   // v9.4.5 — Cancel button สำหรับ queued/extracting ที่ยังไม่ fail (user ยกเลิกเองได้)
   // v9.4.6 — render Cancel ตราบที่ !isFailed (รวม status อื่นๆ ที่ active เช่น
   // optimistic placeholder ก่อน first poll); backend จะ reject 409 ถ้าไม่ใช่
   // queued/extracting จริง → user เห็น toast "ยกเลิกได้เฉพาะ queued/extracting"
   const actions = isFailed ? `
     <div class="upload-tray-actions">
       ${item.is_retryable ? `<button class="btn btn-sm btn-outline" type="button" data-retry-id="${_esc(item.id)}">${_esc(t('upload.tray.retry'))}</button>` : ''}
       <button class="btn btn-sm btn-ghost" type="button" data-dismiss-id="${_esc(item.id)}">${_esc(t('upload.tray.dismiss'))}</button>
     </div>` : `
     <div class="upload-tray-actions">
       <button class="btn btn-sm btn-outline btn-cancel-upload" type="button" data-cancel-id="${_esc(item.id)}">${_esc(t('upload.tray.cancel'))}</button>
     </div>`;

   return `
     <li class="upload-tray-item" data-file-id="${_esc(item.id)}">
       <div class="upload-tray-item-head">
         <span class="upload-tray-filename" title="${filename}">${filename}</span>
         <span class="status-pill ${pillClass}">${_esc(pillText)}</span>
       </div>
       <div class="upload-tray-meta">
         <span class="upload-tray-ext">${ext}</span>
         ${elapsedHtml}
         <button class="upload-tray-toggle" type="button" data-toggle-id="${_esc(item.id)}" aria-expanded="${isExpanded}">${_esc(t('upload.tray.see_details'))}</button>
       </div>
       ${body}
       ${stagesHtml}
       ${actions}
     </li>`;
 }

 async function _onRetry(fileId) {
   try {
     const res = await authFetch(`/api/upload/${fileId}/retry`, { method: 'POST' });
     if (!res.ok) {
       const err = await res.json().catch(() => ({}));
       const msg = (err.error && err.error.message) || (isTH() ? 'ลองใหม่ไม่ได้' : 'Retry failed');
       showToast(msg, 'error');
       return;
     }
     await _fetchStatus().then(_render);
   } catch (e) {
     showToast(isTH() ? 'เครือข่ายขัดข้อง' : 'Network error', 'error');
   }
 }

 async function _onDismiss(fileId) {
   try {
     await authFetch(`/api/upload/${fileId}/dismiss-error`, { method: 'POST' });
     _expandedIds.delete(fileId);
     await _fetchStatus().then(_render);
   } catch (e) { /* defensive — dismiss fail = next poll cleans */ }
 }

 // v9.4.5 — cancel queued/extracting (ไม่ใช่ error)
 async function _onCancel(fileId) {
   const lang = getLang();
   const confirmMsg = lang === 'th' ? 'ยกเลิกไฟล์นี้จากคิว?' : 'Cancel this file from the queue?';
   if (typeof showConfirm === 'function') {
     if (!await showConfirm(confirmMsg)) return;
   } else if (!confirm(confirmMsg)) {
     return;
   }
   try {
     const res = await authFetch(`/api/upload/${fileId}/cancel`, { method: 'POST' });
     if (!res.ok) {
       const err = await res.json().catch(() => ({}));
       const msg = (err.error && err.error.message) || (lang === 'th' ? 'ยกเลิกไม่ได้' : 'Cancel failed');
       showToast(msg, 'error');
       return;
     }
     _expandedIds.delete(fileId);
     await _fetchStatus().then(_render);
   } catch (e) {
     showToast(lang === 'th' ? 'เครือข่ายขัดข้อง' : 'Network error', 'error');
   }
 }

 return { open, close, openIfHasItems, notifyEnqueued };
})();

// Expose globally for uploadFiles + showApp hooks
window.UploadTray = UploadTray;


// ═══════════════════════════════════════════
// DUPLICATE DETECTION MODAL (v7.1.5 — research-backed UX)
// ═══════════════════════════════════════════
// Wording: NN/G + Win11/macOS standards + Material 3 + Thai mobile convention
// Why per-file selector: P1 — bulk-only ทำให้ user เก็บบางไฟล์/ลบบางไฟล์ไม่ได้
// Why undo toast 10s: P2 — accident recovery + Material 3 + WCAG 2.2.1 require ≥10s for destructive

let _dupSelections = {}; // { new_file_id: 'keep' | 'skip' } — per-row selection
let _pendingSkipTimeout = null; // setTimeout handle สำหรับ undo flow

/**
 * แสดง modal popup เมื่อ backend detect ไฟล์ซ้ำใน /api/organize-new response.
 * อ่าน _pendingDuplicates (ตั้งค่าใน uploadFiles / runOrganizeNew หลัง response).
 *
 * Default ทุก row = "keep" (safe per NN/G — destructive ต้อง opt-in).
 * Render per-row radio + matched topics + similarity bar.
 * ใช้ escapeHtml กัน XSS เพราะ filename มาจาก user input.
 */
function showDuplicateModal() {
 const modal = document.getElementById('dup-modal-overlay');
 if (!modal) return;
 const list = document.getElementById('dup-list');
 if (!list) return;

 // Reset selections — ทุก row = keep by default (safe)
 _dupSelections = {};
 _pendingDuplicates.forEach(d => { _dupSelections[d.new_file_id] = 'keep'; });

 const newLabel = t('dup.labelNew');
 const similarLabel = t('dup.labelSimilar');
 const exactLabel = t('dup.labelExact');
 const matchedLabel = t('dup.labelMatched');
 const keepLabel = t('dup.actionKeep');
 const skipLabel = t('dup.actionSkip');

 // Update title with count
 const titleEl = document.getElementById('dup-modal-title');
 if (titleEl) {
  titleEl.textContent = t('dup.title').replace('{count}', _pendingDuplicates.length);
 }

 list.innerHTML = _pendingDuplicates.map(d => {
 const pct = Math.round((d.similarity || 0) * 100);
 const kindLabel = d.match_kind === 'exact' ? ` ${exactLabel}` : '';
 const topics = (d.matched_topics && d.matched_topics.length > 0)
 ? `<div class="dup-topics">${matchedLabel}: ${d.matched_topics.map(escapeHtml).join(', ')}</div>`
 : '';
 const fid = escapeHtml(d.new_file_id || '');
 return `
 <div class="dup-row" data-file-id="${fid}">
 <div class="dup-new">📄 <strong>${escapeHtml(d.new_filename || '')}</strong> ${newLabel}</div>
 <div class="dup-old">
 <div class="dup-arrow">↪ ${similarLabel} <strong>${escapeHtml(d.match_filename || '')}</strong></div>
 <div class="dup-bar">
 <div class="dup-bar-fill" style="width:${pct}%"></div>
 <div class="dup-bar-label">${pct}%${kindLabel}</div>
 </div>
 ${topics}
 <div class="dup-actions">
 <label class="dup-radio">
 <input type="radio" name="dup-${fid}" value="keep" checked>
 <span>${keepLabel}</span>
 </label>
 <label class="dup-radio">
 <input type="radio" name="dup-${fid}" value="skip">
 <span>${skipLabel}</span>
 </label>
 </div>
 </div>
 </div>
 `;
 }).join('');

 // Wire per-row radio change → update _dupSelections + refresh confirm label
 list.querySelectorAll('input[type="radio"]').forEach(input => {
 input.addEventListener('change', () => {
  const row = input.closest('.dup-row');
  if (row) _dupSelections[row.dataset.fileId] = input.value;
  updateConfirmLabel();
 });
 });

 updateConfirmLabel();
 modal.classList.remove('hidden');
}

/**
 * Update confirm button label เมื่อ selection เปลี่ยน.
 * - 0 skip → "เก็บทั้งหมด" / "Keep all"
 * - N skip → "ข้ามไฟล์ใหม่ N ไฟล์" / "Skip N new files"
 * Per NN/G: button = verb + count + object (กัน user กดแบบ auto-confirm)
 */
function updateConfirmLabel() {
 const btn = document.getElementById('dup-confirm-btn');
 if (!btn) return;
 const skipCount = Object.values(_dupSelections).filter(v => v === 'skip').length;
 if (skipCount === 0) {
 btn.textContent = t('dup.confirmKeepAll');
 } else {
 btn.textContent = t('dup.confirmSkip').replace('{count}', skipCount);
 }
}

/**
 * Quick action — apply same action ทุก row พร้อมกัน.
 * Sync ทั้ง _dupSelections + DOM radio state.
 */
function quickApplyAll(action) {
 _pendingDuplicates.forEach(d => {
 _dupSelections[d.new_file_id] = action;
 const radio = document.querySelector(`input[name="dup-${CSS.escape(d.new_file_id)}"][value="${action}"]`);
 if (radio) radio.checked = true;
 });
 updateConfirmLabel();
}

/**
 * ปิด modal + clear state. Caller ต้องเรียกหลัง resolve action เสมอ.
 */
function hideDuplicateModal() {
 const modal = document.getElementById('dup-modal-overlay');
 if (modal) modal.classList.add('hidden');
}

/**
 * Cancel pending skip API call (กรณี user กด undo ใน toast).
 * Clear timer + remove toast + reset state. Idempotent.
 */
function cancelPendingSkip(toast) {
 if (_pendingSkipTimeout) {
 clearTimeout(_pendingSkipTimeout);
 _pendingSkipTimeout = null;
 }
 if (toast && toast.parentNode) toast.parentNode.removeChild(toast);
 _pendingDuplicates = [];
 _dupSelections = {};
}

/**
 * Confirm action handler — เปลี่ยน radio selections เป็น API call จริง.
 *
 * Flow:
 * 1. ถ้าทุก row = keep → toast "เก็บทั้งหมด" + close (ไม่เรียก API)
 * 2. ถ้ามี skip ≥ 1 → trigger 10-second undo toast (ยังไม่เรียก API)
 *    - User กด undo ภายใน 10 วิ → cancel timer + ไฟล์อยู่ครบ
 *    - User กด ✕ → fire API ทันที (skip queue)
 *    - Timeout ครบ → fire API
 *
 * Why client-side delay (vs soft-delete table):
 *  - ไม่แตะ backend ได้ (per plan goal)
 *  - Trade-off: browser refresh ระหว่าง 10 วิ → ไฟล์ "ที่จะ skip" ยังอยู่ (safe default)
 */
async function confirmDupActions() {
 const skipIds = Object.entries(_dupSelections)
 .filter(([_, action]) => action === 'skip')
 .map(([id, _]) => id);

 hideDuplicateModal();

 // ทุก row = keep → ไม่ต้องเรียก API
 if (skipIds.length === 0) {
 showToast(t('dup.toastKeptAll'), 'success');
 _pendingDuplicates = [];
 _dupSelections = {};
 return;
 }

 // มี skip ≥ 1 → undo toast 10 วิ
 showUndoToast(skipIds);
}

/**
 * Render undo toast พร้อม progress bar countdown 10 วิ.
 * Per Material 3 + WCAG 2.2.1 — destructive ต้องการ recovery window กว้าง.
 *
 * 2 ปุ่ม:
 *  - "เลิกทำ" (Undo) — cancel timer, ไฟล์อยู่ครบ
 *  - "✕" — skip queue, fire API ทันที (สำหรับ user ที่มั่นใจ)
 */
function showUndoToast(skipIds) {
 // Remove existing undo toast if any (prevent stacking)
 const existing = document.getElementById('dup-undo-toast');
 if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
 if (_pendingSkipTimeout) { clearTimeout(_pendingSkipTimeout); _pendingSkipTimeout = null; }

 // Get filenames for preview (max 3 + "+N")
 const filenames = skipIds.map(id => {
 const dup = _pendingDuplicates.find(d => d.new_file_id === id);
 return dup ? dup.new_filename : id;
 });
 const previewNames = filenames.slice(0, 3).join(', ');
 const moreCount = filenames.length - 3;
 const namesLabel = previewNames + (moreCount > 0 ? ` +${moreCount}` : '');

 const titleText = t('dup.undoTitle').replace('{count}', skipIds.length);
 const undoBtnText = t('dup.undoBtn');
 const undoNowTooltip = t('dup.undoNow');

 const toast = document.createElement('div');
 toast.id = 'dup-undo-toast';
 toast.className = 'dup-undo-toast';
 toast.innerHTML = `
 <div class="dup-undo-text">
 <div class="dup-undo-title">${escapeHtml(titleText)}</div>
 <div class="dup-undo-files">${escapeHtml(namesLabel)}</div>
 </div>
 <button class="dup-undo-btn" id="dup-undo-btn" type="button">${escapeHtml(undoBtnText)}</button>
 <button class="dup-undo-close" id="dup-undo-close" type="button" title="${escapeHtml(undoNowTooltip)}" aria-label="${escapeHtml(undoNowTooltip)}">✕</button>
 <div class="dup-undo-progress"><div class="dup-undo-progress-fill"></div></div>
 `;
 document.body.appendChild(toast);

 // Wire undo button — cancel pending API call
 const undoBtn = toast.querySelector('#dup-undo-btn');
 if (undoBtn) {
 undoBtn.addEventListener('click', () => {
 cancelPendingSkip(toast);
 showToast(t('dup.toastUndone'), 'info');
 });
 }

 // Wire ✕ button — fire API immediately (skip queue)
 const closeBtn = toast.querySelector('#dup-undo-close');
 if (closeBtn) {
 closeBtn.addEventListener('click', () => {
 if (_pendingSkipTimeout) { clearTimeout(_pendingSkipTimeout); _pendingSkipTimeout = null; }
 if (toast.parentNode) toast.parentNode.removeChild(toast);
 fireSkipApi(skipIds);
 });
 }

 // 10-second timer → fire API (Material 3 + WCAG 2.2.1 recovery window)
 _pendingSkipTimeout = setTimeout(() => {
 if (toast.parentNode) toast.parentNode.removeChild(toast);
 _pendingSkipTimeout = null;
 fireSkipApi(skipIds);
 }, 10000);
}

/**
 * Fire skip-duplicates API call → refresh UI on success.
 * Called either after 10s timeout OR user clicks ✕ in undo toast.
 *
 * Why catch ทุก error: API call ค้างจะไม่ block UI (toast หายไปแล้ว) — ต้อง
 * แสดง error toast ให้ user รู้ว่าล้มเหลว
 */
async function fireSkipApi(fileIds) {
 try {
 const res = await authFetch('/api/files/skip-duplicates', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ file_ids: fileIds }),
 });
 if (res.ok) {
 const data = await res.json();
 showToast(t('dup.toastSkipped').replace('{count}', data.count || fileIds.length), 'success');
 // Refresh list + stats หลังลบ
 loadFiles();
 loadStats();
 loadUnprocessedCount();
 loadUsageInfo();
 } else {
 showToast(t('dup.toastError'), 'error');
 }
 } catch (e) {
 showToast(t('dup.toastError'), 'error');
 } finally {
 _pendingDuplicates = [];
 _dupSelections = {};
 }
}

// v9.1.0 — current file filter (persisted in localStorage)
let _filesFilterKind = localStorage.getItem('pdb_files_filter_kind') || 'all';

async function loadFiles() {
 try {
 const url = '/api/files?kind=' + encodeURIComponent(_filesFilterKind);
 const res = await authFetch(url, { _background: true });
 const data = await res.json();
 renderFileList(data.files);
 document.getElementById('file-count-badge').textContent = data.files.length;
 // v9.1.0 — update chip counts (load all 3 in parallel for accuracy)
 updateFileFilterCounts();
 // v10.0.x — P3-14 · show onboarding banner ถ้า 0 ไฟล์ (best-effort)
 _maybeShowOnboardingBanner(data.files.length);
 } catch (e) { console.error('Load files error:', e); }
}

// v10.0.x — P3-14 · Onboarding banner logic
// Show เฉพาะ: 0 ไฟล์ + managed mode + Drive feature available + ยังไม่กด dismiss
function _maybeShowOnboardingBanner(fileCount) {
 const banner = document.getElementById('onboarding-banner');
 if (!banner) return;
 const dismissed = (() => { try { return localStorage.getItem('pdb_onboarding_dismissed') === '1'; } catch (_) { return false; } })();
 if (dismissed || fileCount > 0) {
   banner.classList.add('hidden');
   return;
 }
 // เช็ค storage_mode + Drive feature_available · ใช้ window._driveStatus ที่ storage_mode.js set
 const ds = window._driveStatus;
 if (ds && ds.feature_available && ds.storage_mode === 'managed' && !ds.drive_connected) {
   banner.classList.remove('hidden');
 } else if (!ds) {
   // Drive status ยังไม่โหลด · แสดง banner ทั่วไปแบบไม่มี CTA Drive (fallback)
   banner.classList.remove('hidden');
 } else {
   banner.classList.add('hidden');
 }
}

// Wire onboarding buttons (idempotent · only once)
function _wireOnboardingBanner() {
 if (_wireOnboardingBanner._done) return;
 _wireOnboardingBanner._done = true;
 const dismissBtn = document.getElementById('onboarding-dismiss');
 const ctaBtn = document.getElementById('onboarding-cta-drive');
 dismissBtn?.addEventListener('click', () => {
   try { localStorage.setItem('pdb_onboarding_dismissed', '1'); } catch (_) {}
   document.getElementById('onboarding-banner')?.classList.add('hidden');
 });
 ctaBtn?.addEventListener('click', () => {
   // เปิด profile modal แล้วเลื่อนไปส่วน Storage Mode (Drive connect อยู่ตรงนั้น)
   try { localStorage.setItem('pdb_onboarding_dismissed', '1'); } catch (_) {}
   if (typeof window.openProfileModal === 'function') window.openProfileModal();
   else if (typeof openProfileModal === 'function') openProfileModal();
   document.getElementById('onboarding-banner')?.classList.add('hidden');
 });
}
// Auto-wire on DOM ready (idempotent)
if (typeof document !== 'undefined') {
 if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', _wireOnboardingBanner);
 else _wireOnboardingBanner();
}

// v9.1.0 — Update filter chip counts (read from /api/stats — single call)
async function updateFileFilterCounts() {
 try {
   const res = await authFetch('/api/stats', { _background: true });
   const stats = await res.json();
   const total = stats.total_files || 0;
   const processed = stats.processed_files || 0;
   const vault = stats.vault_files || 0;
   const setText = (id, n) => { const el = document.getElementById(id); if (el) el.textContent = n; };
   setText('chip-count-all', total);
   setText('chip-count-processed', processed);
   setText('chip-count-vault', vault);
 } catch (e) { /* best-effort */ }
}

// v9.1.0 — Filter chip click handler
function initFileFilterChips() {
 document.querySelectorAll('#file-filter-chips .chip').forEach(chip => {
   if (chip.dataset.kind === _filesFilterKind) chip.classList.add('active');
   else chip.classList.remove('active');
   chip.addEventListener('click', () => {
     const kind = chip.dataset.kind;
     if (kind === _filesFilterKind) return;
     _filesFilterKind = kind;
     localStorage.setItem('pdb_files_filter_kind', kind);
     // Toggle active class
     document.querySelectorAll('#file-filter-chips .chip').forEach(c => c.classList.toggle('active', c === chip));
     loadFiles();
   });
 });
 // v9.1.0 — Populate chip counts ตั้งแต่ init (ไม่ต้องรอ loadFiles)
 // ลองทันที — ถ้าไม่มี token ก็ catch ได้ (best-effort)
 updateFileFilterCounts();
}
window.updateFileFilterCounts = updateFileFilterCounts;

// v9.1.0 — Promote vault file → processed
async function promoteVaultFile(id) {
 const isTH = getLang() === 'th';
 try {
   showLoadingOverlay(isTH ? 'กำลังลองวิเคราะห์...' : 'Trying to analyze...', 'default');
   const res = await authFetch(`/api/files/${id}/promote`, { method: 'POST' });
   const data = await res.json();
   if (!res.ok) throw new Error(data?.detail?.error?.message || 'Promote failed');
   if (data.promoted) {
     showToast(isTH ? '✅ วิเคราะห์สำเร็จ — ย้ายไป "ประมวลผลแล้ว"' : '✅ Analyzed — moved to processed', 'success');
   } else {
     showToast(isTH ? '⚠️ ยังวิเคราะห์ไม่ได้ — เก็บใน Vault ต่อไป' : '⚠️ Cannot analyze yet — kept in vault', 'info');
   }
   loadFiles();
 } catch (e) {
   showToast(isTH ? 'ลองวิเคราะห์ไม่สำเร็จ' : 'Analysis failed', 'error');
 } finally {
   hideLoadingOverlay();
 }
}
window.promoteVaultFile = promoteVaultFile;

function renderFileList(files) {
 const container = document.getElementById('file-list');
 // v10.0.x — P2-10 · กรอง phantom rows (ไฟล์ที่ failed upload + ไม่มี filename/filetype)
 //   เดิม: ถ้า upload fail แต่ DB row ยังถูก commit → file มี filename="" → render "— —" ค้าง
 //   ใหม่: skip rows ที่ไม่มี filename หรือ id (defensive)
 const cleanFiles = (files || []).filter(f => f && f.id && f.filename && f.filename.trim());
 const skippedCount = (files || []).length - cleanFiles.length;
 if (skippedCount > 0) {
   console.warn(`[renderFileList] skipped ${skippedCount} phantom row(s) without filename`);
 }
 if (!cleanFiles.length) {
 container.innerHTML = `<div class="empty-state"><p>${t('myData.noFiles')}</p></div>`;
 return;
 }
 container.innerHTML = cleanFiles.map(f => {
 const tags = (f.tags || []).map(tag => `<span class="tag-chip">${tag}</span>`).join('');
 const freshness = f.freshness && f.freshness !== 'current' ? `<span class="freshness-badge ${f.freshness}">${f.freshness}</span>` : '';
 const sot = f.source_of_truth ? '<span class="sot-badge"> Source of Truth</span>' : '';
 const locked = f.is_locked ? '<span class="locked-badge" title="' + (f.locked_reason || 'Locked') + '"></span>' : '';
 const lockedClass = f.is_locked ? ' file-locked' : '';
 // v7.0.1 — storage badge: "On Drive" link or "On server" text
 const isThai = getLang() === 'th';
 let storageBadge = '';
 if (f.storage_location === 'drive' && f.drive_web_link) {
 const driveLabel = isThai ? '☁️ บน Drive ของคุณ' : '☁️ On your Drive';
 const driveTip = isThai ? 'เปิดไฟล์ใน Google Drive (แท็บใหม่)' : 'Open file in Google Drive (new tab)';
 storageBadge = `<a class="storage-badge storage-drive" href="${f.drive_web_link}" target="_blank" rel="noopener" title="${driveTip}" onclick="event.stopPropagation()">${driveLabel}</a>`;
 } else {
 const serverLabel = isThai ? '🗄️ บนเซิร์ฟเวอร์' : '🗄️ On server';
 const serverTip = isThai ? 'ไฟล์เก็บบนระบบของเรา (managed mode)' : 'File stored on our system (managed mode)';
 storageBadge = `<span class="storage-badge storage-server" title="${serverTip}">${serverLabel}</span>`;
 }
 // v7.4.0 — Inline Delete on desktop; kebab dropdown on mobile.
 const deleteLabel = t('myData.delete');
 // v7.5.0 — extraction status badge + chunk count badge
 const extStatus = f.extraction_status || 'ok';
 let extBadge = '';
 if (extStatus !== 'ok') {
   const labels = {
     empty: { ico: '📭', th: 'ไม่มีข้อความ', en: 'No text' },
     encrypted: { ico: '🔒', th: 'ติดรหัสผ่าน', en: 'Encrypted' },
     ocr_failed: { ico: '🟠', th: 'อ่านไม่ออก', en: 'Read failed' },
     unsupported: { ico: '❌', th: 'ไม่รองรับ', en: 'Unsupported' },
     partial: { ico: '⚠️', th: 'ไม่สมบูรณ์', en: 'Partial' },
   };
   const meta = labels[extStatus] || labels.partial;
   const lbl = isThai ? meta.th : meta.en;
   extBadge = `<span class="extraction-badge extraction-${extStatus}" title="${lbl}">${meta.ico} ${lbl}</span>`;
 }
 const chunkBadge = (f.chunk_count && f.chunk_count > 0)
   ? `<span class="chunk-count-badge" title="${isThai ? 'แบ่งเป็นหลายส่วนเพื่อวิเคราะห์ครบทุกหน้า' : 'Split into chunks for full analysis'}">📚 ${f.chunk_count} ${isThai ? 'ส่วน' : 'parts'}</span>`
   : '';
 // v10.0.13 — badge "บางส่วนถูกตัด" ถูกถอดออก: flag is_truncated สื่อความผิด
 // (จริงๆ คือ chunk บางตัวล้มเหลวตอน map step ไม่ใช่ "ตัดเนื้อหา").
 // raw text + vector index ยังครบ — UI ไม่ควรทำให้ user เข้าใจผิดว่าข้อมูลหาย.
 // จะกลับมาแก้ retry-on-fail ภายหลัง.
 const truncBadge = '';
 // v7.5.0 — retry button if extract failed (encrypted/empty/ocr_failed/unsupported)
 const canRetry = !f.is_locked && extStatus !== 'ok' && extStatus !== 'partial' && extStatus !== 'vault';
 const retryBtn = canRetry
   ? `<button class="btn-sm file-action-retry" onclick="event.stopPropagation(); window.retryExtraction('${f.id}')" title="${isThai ? 'อ่านไฟล์ใหม่อีกครั้ง' : 'Re-extract'}">${isThai ? 'ลองอ่านใหม่' : 'Retry'}</button>`
   : '';
 // v9.1.0 — Vault badge + try-again-promote button
 const isVault = f.file_kind === 'vault_only';
 const vaultBadge = isVault
   ? `<span class="vault-badge" title="${isThai ? 'เก็บในคลัง — AI อ่านเนื้อหาไม่ได้แต่ค้นหาด้วยชื่อไฟล์ได้' : 'In vault — AI cannot read content but can search by filename'}">📦 ${isThai ? 'คลัง' : 'Vault'}</span>`
   : '';
 const promoteBtn = isVault && !f.is_locked
   ? `<button class="btn-sm file-action-promote" onclick="event.stopPropagation(); window.promoteVaultFile('${f.id}')" title="${isThai ? 'ลองวิเคราะห์อีกครั้ง (เผื่อ AI รองรับแล้ว)' : 'Try analyze (in case AI now supports this)'}">${isThai ? 'ลองวิเคราะห์' : 'Try analyze'}</button>`
   : '';
 return `
 <div class="file-item${lockedClass}${isVault ? ' file-vault' : ''}" data-id="${f.id}" onclick="openFileDetail('${f.id}')">
 <div class="file-icon ${f.filetype}">${f.filetype.toUpperCase()}${locked}</div>
 <div class="file-info">
 <div class="file-name">${f.filename}${f.is_locked ? ' <span class="locked-label">' + (isThai ? 'ล็อค' : 'Locked') + '</span>' : ''}</div>
 <div class="file-meta">
 <span>${f.text_length?.toLocaleString() || 0} chars</span>
 <span class="status-dot ${f.processing_status}"></span>
 ${vaultBadge} ${freshness} ${sot} ${extBadge} ${chunkBadge} ${truncBadge} ${storageBadge}
 </div>
 ${tags ? `<div class="file-tags">${tags}</div>` : ''}
 </div>
 <div class="file-actions">
 ${promoteBtn} ${retryBtn}
 <button class="btn-sm file-action-desktop" onclick="event.stopPropagation(); window.deleteFile('${f.id}')">${deleteLabel}</button>
 <button class="kebab-btn file-action-mobile" onclick="event.stopPropagation(); window.toggleKebab(event, 'file-${f.id}')" aria-label="${isThai ? 'การกระทำเพิ่มเติม' : 'More actions'}">⋮</button>
 <div class="kebab-menu hidden" id="kebab-file-${f.id}">
 ${isVault && !f.is_locked ? `<button class="kebab-menu-item" onclick="event.stopPropagation(); document.getElementById('kebab-file-${f.id}')?.classList.add('hidden'); window.promoteVaultFile('${f.id}')">${isThai ? 'ลองวิเคราะห์' : 'Try analyze'}</button>` : ''}
 ${canRetry ? `<button class="kebab-menu-item" onclick="event.stopPropagation(); document.getElementById('kebab-file-${f.id}')?.classList.add('hidden'); window.retryExtraction('${f.id}')">${isThai ? 'ลองอ่านใหม่' : 'Retry extract'}</button>` : ''}
 <button class="kebab-menu-item danger" onclick="event.stopPropagation(); document.getElementById('kebab-file-${f.id}')?.classList.add('hidden'); window.deleteFile('${f.id}')">${deleteLabel}</button>
 </div>
 </div>
 </div>`;
 }).join('');
}

// v7.5.0 — Retry extraction handler · v10.0.5 — polls /api/upload-status
// for live progress (POST returns ~200ms but worker takes 30-60s for big PDFs)
async function retryExtraction(id) {
 const isTH = getLang() === 'th';
 try {
   showLoadingOverlay(isTH ? 'กำลังส่งคำขออ่านไฟล์ใหม่...' : 'Submitting retry request...', 'default');
   const res = await authFetch(`/api/files/${id}/reprocess?mode=reextract`, { method: 'POST' });
   if (!res.ok) throw new Error(`HTTP ${res.status}`);
   const t0 = Date.now();
   const POLL_MS = 1200;
   const TIMEOUT_MS = 5 * 60 * 1000;
   let lastMsg = null;
   while (Date.now() - t0 < TIMEOUT_MS) {
     await new Promise(r => setTimeout(r, POLL_MS));
     const sres = await authFetch('/api/upload-status');
     if (!sres.ok) continue;
     const sj = await sres.json();
     const active = (sj.active || []).find(f => f.id === id);
     const failed = (sj.failed || []).find(f => f.id === id);
     if (failed) throw new Error(failed.extract_error || 'Retry failed');
     if (!active) break;
     const step = active.progress_step || (isTH ? 'กำลังประมวลผล...' : 'Processing...');
     const pct = active.progress_pct;
     const pctStr = (pct != null && pct >= 0 && pct <= 100) ? ` (${pct}%)` : '';
     const msg = step + pctStr;
     if (msg !== lastMsg && _loadingOverlayEl) {
       const msgEl = _loadingOverlayEl.querySelector('.loading-message');
       if (msgEl) msgEl.textContent = msg;
       const fill = _loadingOverlayEl.querySelector('.loading-progress-fill');
       if (fill && pct != null) fill.style.width = pct + '%';
       lastMsg = msg;
     }
   }
   showToast(isTH ? 'อ่านไฟล์ใหม่เรียบร้อย' : 'Re-extracted successfully', 'success');
   loadFiles();
   if (typeof loadStats === 'function') loadStats();
   if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount();
 } catch (e) {
   showToast((isTH ? 'อ่านไฟล์ใหม่ไม่สำเร็จ: ' : 'Retry failed: ') + (e.message || ''), 'error');
 } finally {
   hideLoadingOverlay();
 }
}
window.retryExtraction = retryExtraction;

async function deleteFile(id) {
 if (!await showConfirm(getLang() === 'th' ? 'ต้องการลบไฟล์นี้?' : 'Delete this file?')) return;
 try {
 const res = await authFetch(`/api/files/${id}`, { method: 'DELETE' });
 // v9.3.5.5 (F23) — แสดงผล Drive cleanup ให้ user เข้าใจสถานะ async cleanup
 let toastKey = 'toast.deleted';
 try {
 const data = await res.json();
 if (data && data.drive_cleanup === 'scheduled') toastKey = 'toast.deletedCleaningDrive';
 else if (data && data.drive_cleanup === 'skipped:drive_picked') toastKey = 'toast.deletedDrivePicked';
 } catch (_) { /* response อาจไม่ใช่ JSON · fallback default */ }
 showToast(t(toastKey), 'success');
 closeFileDetail();
 loadFiles();
 loadStats();
 // v10.0.x — ลบไฟล์ → graph/knowledge/packs ก็ต้องถูก refresh
 // เดิม load เฉพาะ files+stats ทำให้ user เปลี่ยน tab ไปกราฟยังเห็น node ผีของไฟล์ที่ลบ
 // (backend แก้ orphan ใน DELETE handler แล้ว · frontend ต้อง re-fetch ถึงเห็นจริง)
 try { if (typeof loadKnowledge === 'function') loadKnowledge(); } catch (_) {}
 try {
   // invalidate graph cache + reload ถ้าตอนนี้อยู่หน้ากราฟ
   if (state) state.graphData = null;
   if (typeof loadGraph === 'function' && state && state.currentPage === 'graph') loadGraph();
 } catch (_) {}
 try { if (typeof loadContextPacks === 'function') loadContextPacks(); } catch (_) {}
 try { if (typeof loadUnprocessedCount === 'function') loadUnprocessedCount(); } catch (_) {}
 } catch (e) { showToast(t('toast.error'), 'error'); }
}


// ─── File Detail Panel ───

let _fdBackdrop = null;

async function openFileDetail(fileId) {
 // Guard: ป้องกัน undefined/null id (double-call จาก event bubbling)
 if (!fileId || fileId === 'undefined') return;
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

 // v10.0.x — เติม filename + icon จาก DOM ที่มี data อยู่แล้ว · กัน "Loading..." ค้าง
 // เมื่อ summary 404 (ไฟล์ที่ยังไม่ organize) header เคยค้าง "Loading..." จนกว่า content fetch จะกลับมา
 // ใหม่: ดึงจาก .file-item[data-id=X] ที่เห็นใน list ตอนนี้แล้ว → header เต็มทันที
 const rowEl = document.querySelector(`.file-item[data-id="${fileId}"]`);
 const rowName = rowEl?.querySelector('.file-name')?.textContent?.trim() || '';
 const rowIconEl = rowEl?.querySelector('.file-icon');
 const rowIcon = rowIconEl?.textContent?.trim().replace(/\s+/g, '').slice(0, 6) || '';
 // strip "Locked" suffix ถ้ามี (ติดมาจาก line 2566 .locked-label)
 const cleanName = rowName.replace(/\s*(Locked|ล็อค)\s*$/, '').trim();

 // Set loading state · ใช้ filename จริงถ้ามี · ไม่ใช้ "Loading..."
 document.getElementById('fd-filename').textContent = cleanName || 'Loading...';
 document.getElementById('fd-icon').textContent = rowIcon || '?';
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
 document.getElementById('fd-icon').textContent = d.filetype?.toUpperCase() || rowIcon || '?';
 document.getElementById('fd-filename').textContent = d.filename || cleanName;
 document.getElementById('fd-cluster').textContent = d.cluster || '—';
 const stars = ''.repeat(Math.min(5, Math.round(d.importance_score / 20)));
 document.getElementById('fd-importance').textContent = `${stars} ${d.importance_label}`;
 document.getElementById('fd-summary').textContent = d.summary_text || 'No summary yet';
 document.getElementById('fd-topics').innerHTML = (d.key_topics || []).map(t => `<span class="chip">${t}</span>`).join('');
 document.getElementById('fd-facts').innerHTML = (d.key_facts || []).map(f => `<li>${f}</li>`).join('');
 document.getElementById('fd-why').textContent = d.why_important || '—';
 } else {
 // v10.0.x — Summary 404 = ยังไม่ organize · ใช้ DOM data ที่ pre-fill แล้ว + ข้อความที่บอกชัด
 document.getElementById('fd-cluster').textContent = '—';
 document.getElementById('fd-importance').textContent = '—';
 document.getElementById('fd-summary').textContent = getLang() === 'th'
 ? 'ยังไม่มี Summary — กด "จัดระเบียบไฟล์ใหม่" เพื่อให้ AI วิเคราะห์'
 : 'No summary yet — click "Organize new files" to let AI analyze';
 document.getElementById('fd-why').textContent = '—';
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
// v10.0.x — P2-8 · "Ask AI" button: pre-fill chat input + switch to chat page + focus
document.getElementById('fd-ask-ai-btn')?.addEventListener('click', () => {
 if (!_currentFileId) return;
 const isTH = getLang() === 'th';
 // ดึง filename จาก fd-filename (set ตอน openFileDetail)
 const fname = document.getElementById('fd-filename')?.textContent?.trim() || '';
 if (!fname) return;
 const prompt = isTH ? `อธิบายเกี่ยวกับ "${fname}" ให้หน่อย` : `Tell me about "${fname}"`;
 // Close detail panel + switch to chat
 if (typeof closeFileDetail === 'function') closeFileDetail();
 if (typeof switchPage === 'function') switchPage('chat');
 setTimeout(() => {
  const chatInput = document.getElementById('chat-input');
  if (chatInput) {
   chatInput.value = prompt;
   chatInput.focus();
   // adjust textarea height if applicable
   chatInput.dispatchEvent(new Event('input', { bubbles: true }));
  }
 }, 200);
});

document.getElementById('fd-download-btn')?.addEventListener('click', () => {
 if (!_currentFileId) return;
 // Direct download via browser — opens the file download
 window.open(`/api/files/${_currentFileId}/download`, '_blank');
});

// v5.2 / v10.0.x — Reprocess file (OCR + Thai fix)
// v10.0.x — P1-6 fix: backend v9.4.0+ ตอบ async queue format
//   เดิม { status: 'ok', old_text_length, new_text_length }
//   ใหม่ { status: 'ok', file_id, processing_status: 'queued', queue_position, extraction_method }
// Frontend ต้อง poll upload-status เพื่อรอผล · เดิมแสดง "undefined → undefined ตัวอักษร" + ปุ่มไม่กลับมา enable
document.getElementById('fd-reprocess-btn')?.addEventListener('click', async () => {
 if (!_currentFileId) return;
 const btn = document.getElementById('fd-reprocess-btn');
 const isTH = getLang() === 'th';
 const fileId = _currentFileId;
 const originalText = btn.innerHTML;
 btn.disabled = true;
 btn.innerHTML = isTH ? '⏳ กำลังส่งคำขอ...' : '⏳ Submitting...';
 try {
   const res = await authFetch(`/api/files/${fileId}/reprocess?mode=reextract`, { method: 'POST' });
   const data = await res.json().catch(() => ({}));
   if (!res.ok) {
     const errMsg = data?.detail?.error?.message || data?.detail || `HTTP ${res.status}`;
     throw new Error(String(errMsg).slice(0, 200));
   }
   // v9.4.0+ async response · status='ok' + processing_status='queued'
   // → ต้อง poll upload-status รอ worker ทำเสร็จ (เหมือน retryExtraction ที่ row-level)
   const queuePos = data.queue_position;
   btn.innerHTML = isTH
     ? `⏳ ในคิว #${queuePos || 1}...`
     : `⏳ Queued #${queuePos || 1}...`;
   showToast(isTH ? 'ส่งคำขอประมวลผลซ้ำแล้ว · กำลังรอ...' : 'Re-extract queued · waiting...', 'info');

   // Poll upload-status (10s × 60 = 10 min max)
   const t0 = Date.now();
   const TIMEOUT_MS = 10 * 60 * 1000;
   const POLL_MS = 1500;
   while (Date.now() - t0 < TIMEOUT_MS) {
     await new Promise(r => setTimeout(r, POLL_MS));
     const sres = await authFetch('/api/upload-status');
     if (!sres.ok) continue;
     const sj = await sres.json();
     const active = (sj.active || []).find(f => f.id === fileId);
     const failed = (sj.failed || []).find(f => f.id === fileId);
     if (failed) throw new Error(failed.extract_error || (isTH ? 'การประมวลผลล้มเหลว' : 'Extraction failed'));
     if (!active) break;  // done · file ออกจาก active list = uploaded
     const step = active.progress_step || (isTH ? 'กำลังประมวลผล...' : 'Processing...');
     const pct = active.progress_pct;
     btn.innerHTML = (pct != null && pct >= 0 && pct <= 100)
       ? `⏳ ${step} (${pct}%)`
       : `⏳ ${step}`;
   }
   showToast(isTH ? '✓ ประมวลผลซ้ำสำเร็จ' : '✓ Re-extracted successfully', 'success');
   // Refresh detail panel เพื่อแสดง content/extracted_text ใหม่
   if (_currentFileId === fileId) openFileDetail(fileId);
   if (typeof loadFiles === 'function') loadFiles();
 } catch (e) {
   const msg = (e && e.message) ? `: ${e.message}` : '';
   showToast((isTH ? 'ประมวลผลซ้ำไม่สำเร็จ' : 'Reprocess failed') + msg, 'error');
 } finally {
   btn.disabled = false;
   btn.innerHTML = originalText;
 }
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
 // v10.0.x — P2-7 · filename edit
 const filenameView = document.getElementById('fd-filename');
 const filenameEdit = document.getElementById('fd-filename-edit');

 if (editing) {
 // Enter edit mode — copy current text to textareas
 summaryEdit.value = summaryView.textContent;
 whyEdit.value = whyView.textContent;
 if (filenameEdit) filenameEdit.value = filenameView?.textContent?.trim() || '';
 summaryView.classList.add('hidden');
 summaryEdit.classList.remove('hidden');
 whyView.classList.add('hidden');
 whyEdit.classList.remove('hidden');
 filenameView?.classList.add('hidden');
 filenameEdit?.classList.remove('hidden');
 editBtn.classList.add('hidden');
 editActions.classList.remove('hidden');
 filenameEdit?.focus();
 } else {
 // Exit edit mode
 summaryView.classList.remove('hidden');
 summaryEdit.classList.add('hidden');
 whyView.classList.remove('hidden');
 whyEdit.classList.add('hidden');
 filenameView?.classList.remove('hidden');
 filenameEdit?.classList.add('hidden');
 editBtn.classList.remove('hidden');
 editActions.classList.add('hidden');
 }
}

async function saveSummaryEdit() {
 if (!_currentFileId) return;

 const summaryText = document.getElementById('fd-summary-edit').value.trim();
 const whyImportant = document.getElementById('fd-why-edit').value.trim();
 // v10.0.x — P2-7 · filename edit
 const filenameEditEl = document.getElementById('fd-filename-edit');
 const newFilename = filenameEditEl ? filenameEditEl.value.trim() : '';
 const oldFilename = document.getElementById('fd-filename')?.textContent?.trim() || '';
 const saveBtn = document.getElementById('fd-save-btn');
 const isTH = getLang() === 'th';

 // Client-side validation
 if (!newFilename) {
   showToast(isTH ? 'ชื่อไฟล์ห้ามว่าง' : 'Filename cannot be empty', 'error');
   return;
 }
 if (newFilename.length > 255) {
   showToast(isTH ? 'ชื่อไฟล์ยาวเกิน 255 ตัวอักษร' : 'Filename too long (max 255)', 'error');
   return;
 }

 saveBtn.disabled = true;
 saveBtn.textContent = '...';

 try {
 const body = { summary_text: summaryText, why_important: whyImportant };
 // ส่ง filename เฉพาะถ้าเปลี่ยน (ลด round-trip ของ rename branch ใน backend)
 if (newFilename !== oldFilename) body.filename = newFilename;

 const res = await authFetch(`/api/summary/${_currentFileId}`, {
 method: 'PUT',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(body)
 });
 if (!res.ok) {
   const errData = await res.json().catch(() => ({}));
   const msg = errData?.detail?.error?.message || errData?.detail || 'Save failed';
   throw new Error(String(msg).slice(0, 200));
 }

 // Update display
 document.getElementById('fd-summary').textContent = summaryText;
 document.getElementById('fd-why').textContent = whyImportant;
 if (newFilename !== oldFilename) {
   document.getElementById('fd-filename').textContent = newFilename;
   if (typeof loadFiles === 'function') loadFiles();
 }
 toggleSummaryEdit(false);
 showToast(isTH ? 'บันทึกเรียบร้อย' : 'Saved', 'success');
 } catch (e) {
 const msg = (e && e.message) ? `: ${e.message}` : '';
 showToast((isTH ? 'บันทึกล้มเหลว' : 'Save failed') + msg, 'error');
 }
 saveBtn.disabled = false;
 saveBtn.textContent = ' Save';
}

// v10.0.4 — cache last response so badge click can render dropdown without re-fetch
let _unprocessedFilesCache = [];
let _unprocessedTruncated = false;

async function loadUnprocessedCount() {
 try {
 // v10.0.5 — cache-buster query so browser doesn't serve stale count
 const res = await authFetch('/api/unprocessed-count?_=' + Date.now(), {
   cache: 'no-store',
 });
 if (!res.ok) return;
 const data = await res.json();
 const badge = document.getElementById('unprocessed-badge');
 _unprocessedFilesCache = data.files || [];
 _unprocessedTruncated = !!data.files_truncated;
 if (badge) {
   if (data.unprocessed > 0) {
     badge.textContent = data.unprocessed;
     badge.style.display = 'inline-flex';
     // ensure click handler attached once
     if (!badge.dataset.clickWired) {
       badge.addEventListener('click', (e) => {
         e.stopPropagation();
         toggleUnprocessedDropdown();
       });
       badge.dataset.clickWired = '1';
     }
   } else {
     badge.style.display = 'none';
     hideUnprocessedDropdown();
   }
 }
 // If dropdown is open, re-render so it reflects latest list
 const dd = document.getElementById('unprocessed-dropdown');
 if (dd && !dd.classList.contains('hidden')) renderUnprocessedDropdown();
 } catch (e) { /* silent */ }
}

function toggleUnprocessedDropdown() {
  const dd = document.getElementById('unprocessed-dropdown');
  if (!dd) return;
  if (dd.classList.contains('hidden')) {
    renderUnprocessedDropdown();
    dd.classList.remove('hidden');
    // Click outside → close
    setTimeout(() => {
      const handler = (ev) => {
        if (!dd.contains(ev.target) && ev.target.id !== 'unprocessed-badge') {
          hideUnprocessedDropdown();
          document.removeEventListener('click', handler);
        }
      };
      document.addEventListener('click', handler);
    }, 0);
  } else {
    hideUnprocessedDropdown();
  }
}

function hideUnprocessedDropdown() {
  const dd = document.getElementById('unprocessed-dropdown');
  if (dd) dd.classList.add('hidden');
}

function renderUnprocessedDropdown() {
  const dd = document.getElementById('unprocessed-dropdown');
  if (!dd) return;
  const isTH = getLang() === 'th';
  const heading = isTH ? `ไฟล์ที่ยังไม่จัดระเบียบ (${_unprocessedFilesCache.length}${_unprocessedTruncated ? '+' : ''})` : `Unorganized files (${_unprocessedFilesCache.length}${_unprocessedTruncated ? '+' : ''})`;
  const emptyMsg = isTH ? 'ไม่มีไฟล์ที่ค้างจัดระเบียบ' : 'No unorganized files';
  const truncatedNote = isTH ? '... และอื่นๆ (กดจัดระเบียบเพื่อทำให้ครบ)' : '... and more (click organize to process all)';

  if (_unprocessedFilesCache.length === 0) {
    dd.innerHTML = `<div class="unprocessed-dropdown-empty">${emptyMsg}</div>`;
    return;
  }

  const rows = _unprocessedFilesCache.map(f => {
    const safeName = (f.filename || '').replace(/</g, '&lt;');
    const ftype = (f.filetype || '').toUpperCase();
    return `<li class="unprocessed-row" data-id="${f.id}">
      <span class="unprocessed-row-icon">${ftype}</span>
      <span class="unprocessed-row-name" title="${safeName}">${safeName}</span>
    </li>`;
  }).join('');

  dd.innerHTML = `
    <div class="unprocessed-dropdown-header">${heading}</div>
    <ul class="unprocessed-dropdown-list">${rows}</ul>
    ${_unprocessedTruncated ? `<div class="unprocessed-dropdown-footer">${truncatedNote}</div>` : ''}
  `;

  // Click row → scroll to + flash that file in the main list
  dd.querySelectorAll('.unprocessed-row').forEach(row => {
    row.addEventListener('click', () => {
      const id = row.dataset.id;
      hideUnprocessedDropdown();
      const target = document.querySelector(`.file-item[data-id="${id}"]`);
      if (target) {
        target.scrollIntoView({behavior: 'smooth', block: 'center'});
        target.classList.add('flash-highlight');
        setTimeout(() => target.classList.remove('flash-highlight'), 2000);
      }
    });
  });
}

async function runOrganizeAll() {
 const btn = document.getElementById('btn-organize-all');
 btn.disabled = true;
 btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังจัดระเบียบ...' : 'Organizing...'}`;
 showLoadingOverlay(getLang() === 'th' ? ' AI กำลังวิเคราะห์และจัดกลุ่มไฟล์ทั้งหมด...\nอาจใช้เวลา 30-60 วินาที' : ' AI is analyzing and organizing ALL files...\nThis may take 30-60 seconds', 'ai');
 // v10.0.3 — live phase poll (same mechanism as runOrganizeNew)
 startOrganizeStatusPoll();
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
 // v10.0.3 — start live status poll alongside the blocking POST so the
 // overlay reflects current pipeline phase (scanning → clustering →
 // summary N/M → enrich → graph → duplicates → done) instead of staying
 // on the static "AI กำลังจัดระเบียบ..." text for 30-120s.
 startOrganizeStatusPoll();
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
 // v10.0.10 — 409 ORGANIZE_IN_PROGRESS = previous run still working
 // (e.g. watchdog auto-closed prematurely, user clicks again). Don't
 // bail with an error toast — keep the overlay open, let the existing
 // poll keep tracking the in-flight run. Info toast tells user it's
 // already running.
 if (res.status === 409) {
  showToast(
    getLang() === 'th'
      ? 'กำลังจัดระเบียบไฟล์ใหม่อยู่แล้ว — รอสักครู่ ระบบจะแสดงผลเมื่อเสร็จ'
      : 'Organize already running — please wait for the current run to finish',
    'info'
  );
  // Keep overlay open + polling alive; the watchdog/poll will close it
  // when the existing run completes. Reset button so user can see badge.
  btn.disabled = false;
  btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> <span data-i18n="myData.organizeNew">${t('myData.organizeNew')}</span><span class="badge-count" id="unprocessed-badge" style="display:none;">0</span>`;
  return;
 }
 const data = await res.json().catch(() => ({}));
 // v10.0.8 — ตรวจ status ก่อน parse · เดิม: 500 + {detail:...} → showToast(`(${undefined} ไฟล์)`)
 // ตอนนี้: ถ้า response ไม่ใช่ 2xx · หรือ new_files ไม่ใช่ number → แสดง error จริง
 if (!res.ok || typeof data.new_files !== 'number') {
  hideLoadingOverlay();
  const errMsg = (data.detail && typeof data.detail === 'string' ? data.detail :
                  data.detail?.error?.message || data.message ||
                  (getLang() === 'th' ? `จัดระเบียบล้มเหลว (HTTP ${res.status})` : `Organize failed (HTTP ${res.status})`));
  showToast(errMsg, 'error');
  console.error('[organize-new] failed:', res.status, data);
  btn.disabled = false;
  btn.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg> <span data-i18n="myData.organizeNew">${t('myData.organizeNew')}</span><span class="badge-count" id="unprocessed-badge" style="display:none;">0</span>`;
  loadUnprocessedCount();  // refresh badge ในกรณี backend mark file เป็น error
  return;
 }
 if (data.new_files === 0) {
 showToast(t('toast.noNewFiles'), 'info');
 } else {
 showToast(`${t('toast.organizedNew')} (${data.new_files} ไฟล์)`, 'success');
 }
 // v10.0.5 — refresh UI ทุกครั้ง (เดิม refresh เฉพาะตอนมีไฟล์ใหม่ → badge ไม่อัปเดตถ้า
 // partial-fail: organize อ้าง new_files=N แต่จริงๆ summary fail บางตัว → unprocessed คงค้าง)
 loadFiles();
 loadStats();
 loadUnprocessedCount();
 loadUsageInfo();
 // v7.1 — เปิด popup ถ้า backend เจอไฟล์ซ้ำหลัง organize
 // v10.0.5 — ถ้า overlay ยังเปิดอยู่ delay duplicate modal ไม่ให้ stack ทับ
 if (data.duplicates_found && data.duplicates_found.length > 0) {
 _pendingDuplicates = data.duplicates_found;
 const showAfterOverlay = () => {
   if (_loadingOverlayEl) {
     setTimeout(showAfterOverlay, 500);
   } else {
     showDuplicateModal();
   }
 };
 showAfterOverlay();
 }
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
 // v9.2.0 — AI Pack Builder entry point
 const aiBtnLabel = getLang() === 'th' ? '🪄 ให้ AI สร้างให้' : '🪄 AI Build for me';
 const emptyMsg = getLang() === 'th' ? 'ยังไม่มี Context Pack — สร้างเพื่อจัดกลุ่มข้อมูลให้ AI' : 'No context packs yet — create one to bundle data for AI';

 let html = `<div class="packs-header">
 <span>${data.count || 0} pack${data.count !== 1 ? 's' : ''}</span>
 <div class="packs-header-actions" style="display:flex;gap:8px">
  <button class="btn btn-outline" onclick="openAIPackBuilder()">${aiBtnLabel}</button>
  <button class="btn btn-primary" onclick="openCreatePackModal()">${createBtnLabel}</button>
 </div>
 </div>`;

 if (!data.packs.length) {
 html += `<div class="empty-state"><p>${emptyMsg}</p></div>`;
 } else {
 // v9.0.1 — แสดง locked state: opacity drop + 🔒 badge + regenerate disabled
 html += data.packs.map(p => {
 const isLocked = !!p.is_locked;
 const lockedClass = isLocked ? 'is-locked' : '';
 const lockedBadge = isLocked
 ? `<span class="pack-locked-badge" title="${getLang() === 'th' ? 'ล็อค (เกินโควต้าแพลน) — อัปเกรดเพื่อปลดล็อค' : 'Locked (exceeds plan limit) — upgrade to unlock'}">🔒</span>`
 : '';
 const regenTitle = isLocked
 ? (getLang() === 'th' ? 'Pack ล็อคอยู่ — regenerate ไม่ได้' : 'Pack locked — cannot regenerate')
 : 'Regenerate';
 const regenAttr = isLocked ? 'disabled' : '';
 // v9.3.0 — Share button (📤). Disabled if pack locked.
 const shareTitle = isLocked
 ? (getLang() === 'th' ? 'Pack ล็อค — แชร์ไม่ได้' : 'Pack locked — cannot share')
 : (getLang() === 'th' ? 'แชร์ Pack' : 'Share Pack');
 const shareAttr = isLocked ? 'disabled' : '';
 return `
 <div class="pack-card ${lockedClass}" data-pack-id="${p.id}">
 <div class="pack-card-header">
 <div class="pack-card-title">${lockedBadge} ${escapeHtml(p.title)}</div>
 <div class="pack-card-actions">
 <button onclick="sharePack('${p.id}')" title="${shareTitle}" ${shareAttr} aria-label="${shareTitle}">📤</button>
 <button onclick="regeneratePack('${p.id}')" title="${regenTitle}" ${regenAttr}>🔄</button>
 <button class="btn-danger" onclick="deletePack('${p.id}')" title="Delete">🗑</button>
 </div>
 </div>
 <div class="pack-card-summary">${escapeHtml(p.summary_text?.substring(0, 200) || '')}${p.summary_text?.length > 200 ? '...' : ''}</div>
 <div class="pack-card-meta">
 <span class="badge">${p.type}</span>
 ${p.created_at ? `<span>${formatDate(p.created_at)}</span>` : ''}
 </div>
 <div class="pack-share-bar hidden" id="share-bar-${p.id}"></div>
 </div>`;
 }).join('');
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

// ═══════════════════════════════════════════
// v9.3.0 — Pack Share (sender side)
// ═══════════════════════════════════════════

/**
 * sharePack(packId) — สร้าง/Get share link + auto-copy + render bar.
 * Idempotent: กดซ้ำได้ลิงก์เดิม ไม่ count quota เพิ่ม.
 */
async function sharePack(packId) {
 try {
  const res = await authFetch(`/api/context-packs/${packId}/share`, {
   method: 'POST',
   headers: { 'Content-Type': 'application/json' },
   body: JSON.stringify({ include_files: false }),
  });
  if (res.status === 403) {
   const err = await res.json();
   showUpgradeModal(err.detail || 'Quota reached');
   return;
  }
  if (res.status === 400) {
   const err = await res.json();
   showToast(`${err.detail || 'Cannot share'}`, 'error');
   return;
  }
  if (!res.ok) {
   const err = await res.json();
   showToast(`Error: ${err.detail || 'unknown'}`, 'error');
   return;
  }
  const share = await res.json();
  // Auto-copy to clipboard (must be in user-gesture handler)
  await _copyShareLinkToClipboard(share.share_url);
  // Render bar + show
  _renderShareBar(packId, share);
 } catch (e) {
  showToast(t('toast.error'), 'error');
 }
}

async function _copyShareLinkToClipboard(url) {
 try {
  if (navigator.clipboard && navigator.clipboard.writeText) {
   await navigator.clipboard.writeText(url);
  } else {
   // Fallback: textarea + execCommand
   const ta = document.createElement('textarea');
   ta.value = url;
   ta.style.position = 'fixed';
   ta.style.opacity = '0';
   document.body.appendChild(ta);
   ta.select();
   document.execCommand('copy');
   document.body.removeChild(ta);
  }
  showToast(
   getLang() === 'th' ? 'คัดลอกลิงก์แล้ว — ส่งให้เพื่อนได้เลย' : 'Link copied — paste anywhere',
   'success'
  );
 } catch (e) {
  // Clipboard ปิด — แสดงลิงก์ให้ copy เอง
  showToast(
   getLang() === 'th' ? 'คัดลอกอัตโนมัติไม่ได้ — copy ลิงก์เองที่ bar' : 'Auto-copy failed — copy from bar',
   'warning'
  );
 }
}

function _renderShareBar(packId, share) {
 const barId = `share-bar-${packId}`;
 const bar = document.getElementById(barId);
 if (!bar) return;

 const isTH = getLang() === 'th';
 const checked = share.include_files ? 'checked' : '';
 const filesNote = share.include_files
  ? `<div class="pack-share-warning">⚠ ${isTH ? 'ใครเปิดลิงก์จะดาวน์โหลดไฟล์เหล่านี้ได้' : 'Anyone with link can download these files'}</div>`
  : '';

 bar.innerHTML = `
  <div class="pack-share-row">
   <input type="text" class="pack-share-link form-input" value="${escapeHtml(share.share_url)}" readonly id="share-link-${share.share_id}">
   <button class="btn btn-sm btn-outline" onclick="copyShareLink('${share.share_id}')">${isTH ? '📋 คัดลอก' : '📋 Copy'}</button>
  </div>
  <div class="pack-share-stats">
   👁 ${share.view_count || 0} ${isTH ? 'views' : 'views'} · 📥 ${share.clone_count || 0} ${isTH ? 'clones' : 'clones'}
  </div>
  <label class="pack-share-toggle">
   <input type="checkbox" ${checked} onchange="togglePackFiles('${packId}', '${share.share_id}', this.checked)">
   <span>${isTH ? '+ แนบไฟล์ทั้งหมดด้วย' : '+ Attach all files too'}</span>
  </label>
  ${filesNote}
  <div class="pack-share-actions">
   <button class="btn btn-sm btn-danger" onclick="revokePackShare('${packId}', '${share.share_id}')">${isTH ? '🚫 ยกเลิกลิงก์' : '🚫 Revoke link'}</button>
   <button class="btn btn-sm btn-ghost" onclick="closePackShareBar('${packId}')">${isTH ? 'ปิด ▲' : 'Close ▲'}</button>
  </div>
 `;
 bar.classList.remove('hidden');
}

function copyShareLink(shareId) {
 const input = document.getElementById(`share-link-${shareId}`);
 if (input) _copyShareLinkToClipboard(input.value);
}

async function togglePackFiles(packId, shareId, includeFiles) {
 try {
  const res = await authFetch(`/api/context-packs/shares/${shareId}`, {
   method: 'PATCH',
   headers: { 'Content-Type': 'application/json' },
   body: JSON.stringify({ include_files: includeFiles }),
  });
  if (!res.ok) {
   showToast(t('toast.error'), 'error');
   return;
  }
  const share = await res.json();
  _renderShareBar(packId, share);
  // Auto-copy fresh URL (same URL but different state — UX confirm)
  await _copyShareLinkToClipboard(share.share_url);
  const isTH = getLang() === 'th';
  showToast(
   includeFiles
    ? (isTH ? 'ลิงก์มีไฟล์แนบแล้ว' : 'Link now includes files')
    : (isTH ? 'ลิงก์เป็นสรุปอย่างเดียว' : 'Link is summary-only'),
   'info'
  );
 } catch (e) {
  showToast(t('toast.error'), 'error');
 }
}

async function revokePackShare(packId, shareId) {
 try {
  const res = await authFetch(`/api/context-packs/shares/${shareId}`, { method: 'DELETE' });
  if (!res.ok) {
   showToast(t('toast.error'), 'error');
   return;
  }
  closePackShareBar(packId);
  showToast(getLang() === 'th' ? 'ยกเลิกลิงก์แล้ว' : 'Link revoked', 'success');
 } catch (e) {
  showToast(t('toast.error'), 'error');
 }
}

function closePackShareBar(packId) {
 const bar = document.getElementById(`share-bar-${packId}`);
 if (bar) {
  bar.classList.add('hidden');
  bar.innerHTML = '';
 }
}

async function regeneratePack(packId) {
 // v9.0.1 — preflight: ถ้า pack ล็อค ไม่เรียก API (เลี่ยง 403 toast ที่ผู้ใช้สับสน)
 // Backend ยังมี is_locked guard ที่ endpoint อยู่ดี — ฝั่งนี้แค่ early-out ให้ UX ดี
 const card = document.querySelector(`[data-pack-id="${packId}"]`);
 if (card && card.classList.contains('is-locked')) {
 showToast(
 getLang() === 'th'
 ? 'Pack นี้ถูกล็อค — อัปเกรดเป็น Starter เพื่อปลดล็อค'
 : 'This pack is locked — upgrade to Starter to unlock',
 'warning'
 );
 return;
 }
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
// v9.2.0 — AI PACK BUILDER (clarify → propose → confirm)
// ═══════════════════════════════════════════

// State สำหรับ flow ปัจจุบัน — เก็บ session_id + draft_id ระหว่าง view transitions
let _aiBuilderState = {
 sessionId: null,
 draftId: null,
 lastPrompt: '',  // สำหรับ retry button (กลับไป state="input" แสดง prompt เดิม)
};

function _aiSwitchView(stateName) {
 // hide ทุก view + แสดงเฉพาะที่ระบุ
 ['input', 'clarify', 'loading', 'preview'].forEach(s => {
  document.getElementById(`ai-state-${s}`)?.classList.toggle('hidden', s !== stateName);
 });
 // toggle footer buttons ตาม state
 const visibilityMap = {
  input:   { 'ai-builder-submit-prompt': true,  'ai-clarify-skip': false, 'ai-clarify-submit': false, 'ai-preview-confirm': false, 'ai-preview-retry': false, 'ai-builder-back': false },
  clarify: { 'ai-builder-submit-prompt': false, 'ai-clarify-skip': true,  'ai-clarify-submit': true,  'ai-preview-confirm': false, 'ai-preview-retry': false, 'ai-builder-back': true  },
  loading: { 'ai-builder-submit-prompt': false, 'ai-clarify-skip': false, 'ai-clarify-submit': false, 'ai-preview-confirm': false, 'ai-preview-retry': false, 'ai-builder-back': false },
  preview: { 'ai-builder-submit-prompt': false, 'ai-clarify-skip': false, 'ai-clarify-submit': false, 'ai-preview-confirm': true,  'ai-preview-retry': true,  'ai-builder-back': false },
 };
 const map = visibilityMap[stateName] || {};
 Object.entries(map).forEach(([id, show]) => {
  const el = document.getElementById(id);
  if (el) el.classList.toggle('hidden', !show);
 });
}

function openAIPackBuilder() {
 _aiBuilderState = { sessionId: null, draftId: null, lastPrompt: '' };
 document.getElementById('ai-builder-prompt').value = '';
 document.getElementById('ai-clarify-freetext').value = '';
 _aiSwitchView('input');
 document.getElementById('ai-builder-modal-overlay').classList.remove('hidden');
}

async function closeAIPackBuilder() {
 // ถ้ามี draft ค้าง → discard ผ่าน API (cleanup memory)
 if (_aiBuilderState.draftId) {
  try {
   await authFetch(`/api/context-packs/ai-build/drafts/${_aiBuilderState.draftId}`, { method: 'DELETE' });
  } catch (e) { /* silent */ }
 }
 _aiBuilderState = { sessionId: null, draftId: null, lastPrompt: '' };
 document.getElementById('ai-builder-modal-overlay').classList.add('hidden');
}

async function submitAIBuilderPrompt() {
 const prompt = document.getElementById('ai-builder-prompt').value.trim();
 if (prompt.length < 10) {
  showToast(getLang() === 'th' ? 'พิมพ์อธิบายอย่างน้อย 10 ตัวอักษร' : 'Describe with at least 10 characters', 'error');
  return;
 }
 if (prompt.length > 500) {
  showToast(getLang() === 'th' ? 'ข้อความยาวเกิน 500 ตัวอักษร' : 'Text exceeds 500 characters', 'error');
  return;
 }
 _aiBuilderState.lastPrompt = prompt;
 _aiSwitchView('loading');
 document.getElementById('ai-loading-text').textContent =
  getLang() === 'th' ? 'AI กำลังวิเคราะห์... อาจใช้เวลา 5-15 วินาที' : 'AI analyzing... may take 5-15s';

 try {
  const res = await authFetch('/api/context-packs/ai-build/clarify', {
   method: 'POST',
   headers: { 'Content-Type': 'application/json' },
   body: JSON.stringify({ prompt }),
  });
  if (res.status === 403) {
   const err = await res.json();
   showUpgradeModal(err.detail || 'Quota reached');
   _aiSwitchView('input');
   return;
  }
  if (!res.ok) {
   const err = await res.json();
   showToast(`Error: ${err.detail || 'unknown'}`, 'error');
   _aiSwitchView('input');
   return;
  }
  const data = await res.json();
  _aiBuilderState.sessionId = data.session_id;
  if (data.skip_clarify) {
   // AI เข้าใจ prompt ดีพอแล้ว — ข้ามไป /propose ทันที
   showToast(getLang() === 'th' ? 'AI เข้าใจ prompt ของคุณแล้ว — กำลังสร้าง draft...' : 'AI understood your prompt — building draft...', 'info');
   await _aiCallPropose({ skipped: true });
  } else {
   // Render clarify view
   _aiRenderClarify(data);
   _aiSwitchView('clarify');
  }
 } catch (e) {
  showToast(t('toast.error'), 'error');
  _aiSwitchView('input');
 }
}

function _aiRenderClarify(data) {
 document.getElementById('ai-clarify-question').textContent = data.question || '';
 const list = document.getElementById('ai-clarify-options');
 list.innerHTML = (data.options || []).map(opt => `
  <label class="ai-clarify-option" data-option-id="${opt.id}">
   <input type="radio" name="ai-clarify-radio" value="${opt.id}">
   <div class="ai-clarify-option-body">
    <div class="ai-clarify-option-title">${escapeHtml(opt.title || '')}</div>
    <div class="ai-clarify-option-summary">${escapeHtml(opt.summary || '')}</div>
   </div>
  </label>
 `).join('');
 const ftEl = document.getElementById('ai-clarify-freetext');
 ftEl.value = '';
 if (data.freetext_hint) ftEl.placeholder = data.freetext_hint;
}

async function submitClarification() {
 const radio = document.querySelector('input[name="ai-clarify-radio"]:checked');
 const freetext = document.getElementById('ai-clarify-freetext').value.trim();
 let clarification;
 if (freetext) {
  clarification = { freetext };
 } else if (radio) {
  clarification = { selected_option_id: parseInt(radio.value, 10) };
 } else {
  showToast(getLang() === 'th' ? 'เลือกตัวเลือกหรือพิมพ์อธิบายเพิ่ม' : 'Select an option or type a description', 'error');
  return;
 }
 await _aiCallPropose(clarification);
}

async function skipClarify() {
 await _aiCallPropose({ skipped: true });
}

async function _aiCallPropose(clarification) {
 _aiSwitchView('loading');
 document.getElementById('ai-loading-text').textContent =
  getLang() === 'th' ? 'AI กำลังเลือก source + เขียนสรุป...' : 'AI selecting sources + writing summary...';
 try {
  const res = await authFetch('/api/context-packs/ai-build/propose', {
   method: 'POST',
   headers: { 'Content-Type': 'application/json' },
   body: JSON.stringify({
    session_id: _aiBuilderState.sessionId,
    clarification,
   }),
  });
  if (res.status === 403) {
   const err = await res.json();
   showUpgradeModal(err.detail || 'Quota reached');
   _aiSwitchView('input');
   return;
  }
  if (res.status === 404) {
   showToast(getLang() === 'th' ? 'Session หมดอายุ — เริ่มใหม่' : 'Session expired — start over', 'error');
   _aiSwitchView('input');
   return;
  }
  if (!res.ok) {
   const err = await res.json();
   showToast(`Error: ${err.detail || 'unknown'}`, 'error');
   _aiSwitchView('input');
   return;
  }
  const draft = await res.json();
  _aiBuilderState.draftId = draft.draft_id;
  _aiRenderPreview(draft);
  _aiSwitchView('preview');
 } catch (e) {
  showToast(t('toast.error'), 'error');
  _aiSwitchView('input');
 }
}

function _aiRenderPreview(draft) {
 document.getElementById('ai-preview-title').value = draft.title || '';
 document.getElementById('ai-preview-type').value = draft.type || 'project';
 document.getElementById('ai-preview-intent').value = draft.intent || '';
 document.getElementById('ai-preview-scope').value = draft.scope || '';
 document.getElementById('ai-preview-summary').value = draft.summary_text || '';
 const list = document.getElementById('ai-preview-sources');
 list.innerHTML = (draft.sources || []).map(s => `
  <label class="ai-source-checkbox">
   <input type="checkbox" value="${escapeHtml(s.id)}" ${s.included ? 'checked' : ''}>
   <span class="ai-source-kind">${s.kind === 'cluster' ? '📁' : '📄'}</span>
   <span class="ai-source-title">${escapeHtml(s.title || s.id)}</span>
  </label>
 `).join('');
}

async function confirmAIDraft() {
 if (!_aiBuilderState.draftId) return;
 const includedIds = Array.from(document.querySelectorAll('#ai-preview-sources input[type=checkbox]:checked')).map(cb => cb.value);
 if (!includedIds.length) {
  showToast(getLang() === 'th' ? 'เลือก source อย่างน้อย 1 อัน' : 'Select at least 1 source', 'error');
  return;
 }
 const edits = {
  title: document.getElementById('ai-preview-title').value.trim(),
  type: document.getElementById('ai-preview-type').value,
  intent: document.getElementById('ai-preview-intent').value.trim(),
  scope: document.getElementById('ai-preview-scope').value.trim(),
  summary_text: document.getElementById('ai-preview-summary').value.trim(),
  included_source_ids: includedIds,
 };
 if (!edits.title) {
  showToast(getLang() === 'th' ? 'กรุณาตั้งชื่อ Pack' : 'Please enter a pack name', 'error');
  return;
 }
 const btn = document.getElementById('ai-preview-confirm');
 btn.disabled = true;
 try {
  const res = await authFetch('/api/context-packs/ai-build/confirm', {
   method: 'POST',
   headers: { 'Content-Type': 'application/json' },
   body: JSON.stringify({ draft_id: _aiBuilderState.draftId, edits }),
  });
  if (res.status === 403) {
   const err = await res.json();
   showUpgradeModal(err.detail || 'Pack limit reached');
   btn.disabled = false;
   return;
  }
  if (!res.ok) {
   const err = await res.json();
   showToast(`Error: ${err.detail || 'unknown'}`, 'error');
   btn.disabled = false;
   return;
  }
  // Success — pack saved
  const pack = await res.json();
  showToast(getLang() === 'th' ? `สร้าง Pack "${pack.title}" สำเร็จ!` : `Pack "${pack.title}" created!`, 'success');
  _aiBuilderState.draftId = null;  // กัน DELETE ตอน close
  document.getElementById('ai-builder-modal-overlay').classList.add('hidden');
  loadKnowledge();
  loadStats();
  loadUsageInfo();
 } catch (e) {
  showToast(t('toast.error'), 'error');
 }
 btn.disabled = false;
}

async function retryAIDraft() {
 // Discard draft + กลับไป state="input" — prompt เดิมยังอยู่
 if (_aiBuilderState.draftId) {
  try { await authFetch(`/api/context-packs/ai-build/drafts/${_aiBuilderState.draftId}`, { method: 'DELETE' }); }
  catch (e) { /* silent */ }
  _aiBuilderState.draftId = null;
 }
 _aiBuilderState.sessionId = null;
 document.getElementById('ai-builder-prompt').value = _aiBuilderState.lastPrompt;
 _aiSwitchView('input');
}

function backFromClarify() {
 // กลับจาก clarify state → input
 _aiBuilderState.sessionId = null;
 _aiSwitchView('input');
}

// AI Builder modal event listeners
document.getElementById('ai-builder-close')?.addEventListener('click', closeAIPackBuilder);
document.getElementById('ai-builder-cancel')?.addEventListener('click', closeAIPackBuilder);
document.getElementById('ai-builder-modal-overlay')?.addEventListener('click', (e) => {
 if (e.target === e.currentTarget) closeAIPackBuilder();
});
document.getElementById('ai-builder-submit-prompt')?.addEventListener('click', submitAIBuilderPrompt);
document.getElementById('ai-clarify-submit')?.addEventListener('click', submitClarification);
document.getElementById('ai-clarify-skip')?.addEventListener('click', skipClarify);
document.getElementById('ai-builder-back')?.addEventListener('click', backFromClarify);
document.getElementById('ai-preview-confirm')?.addEventListener('click', confirmAIDraft);
document.getElementById('ai-preview-retry')?.addEventListener('click', retryAIDraft);

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
 // v10.0.x — P1-5 · Number.isFinite filter · เดิม `n.x !== undefined` ไม่ดัก NaN
 // ทำให้ d3.extent() คืน [NaN, NaN] → cx/cy = NaN → transform("translate(NaN,NaN)") = D3 error
 const nodes = state.graphData.nodes.filter(n => Number.isFinite(n.x) && Number.isFinite(n.y));
 if (!nodes.length) return;

 const xExtent = d3.extent(nodes, d => d.x);
 const yExtent = d3.extent(nodes, d => d.y);
 const dx = (xExtent[1] - xExtent[0]) || 100;
 const dy = (yExtent[1] - yExtent[0]) || 100;
 const cx = (xExtent[0] + xExtent[1]) / 2;
 const cy = (yExtent[0] + yExtent[1]) / 2;
 // Guard final values · ห้ามให้ NaN/Infinity ผ่านลง translate()
 if (!Number.isFinite(cx) || !Number.isFinite(cy) || !Number.isFinite(dx) || !Number.isFinite(dy)) {
   console.warn('[graph] non-finite values for fit-to-view · skipping zoom', { cx, cy, dx, dy });
   return;
 }
 const scale = Math.min(0.85 * w / dx, 0.85 * h / dy, 2);
 if (!Number.isFinite(scale) || scale <= 0) return;

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
 .attr('transform', d => `translate(${Number.isFinite(d.x) ? d.x : 0},${Number.isFinite(d.y) ? d.y : 0})`)
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
 node.attr('transform', d => `translate(${Number.isFinite(d.x) ? d.x : 0},${Number.isFinite(d.y) ? d.y : 0})`);
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

 // v7.2.0 — show typing indicator + spinner BEFORE the network call so user
 // sees instant feedback (target: visible within next paint frame).
 _chatBusy = true;
 input.value = '';
 localStorage.setItem('pk_chat_used', '1');
 input.disabled = true;
 const originalSendHTML = sendBtn?.innerHTML;
 if (sendBtn) {
  sendBtn.disabled = true;
  sendBtn.innerHTML = `<span class="loading-spinner"></span>`;
 }
 const typingEl = document.getElementById('chat-typing-status');
 typingEl?.classList.remove('hidden');

 // Add user message
 addMessage(question, 'user');

 // v10.0.5 — Show loading with elapsed counter so user knows it's still alive
 // (chat is blocking POST 5-30s; static spinner appears stuck)
 const loadingId = addMessage(`<span class="loading-spinner"></span> <span class="chat-thinking-label">${getLang() === 'th' ? 'กำลังคิด...' : 'Thinking...'}</span> <span class="chat-elapsed" style="color:var(--text-muted);font-size:11px;margin-left:6px;">0s</span>`, 'assistant', true);
 const chatT0 = Date.now();
 const elapsedTimer = setInterval(() => {
   const el = document.querySelector(`#${loadingId} .chat-elapsed`);
   if (!el) { clearInterval(elapsedTimer); return; }
   const s = Math.floor((Date.now() - chatT0) / 1000);
   el.textContent = s + 's';
 }, 1000);

 try {
 const res = await authFetch('/api/chat', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({ question }),
 });
 // v10.0.x — P0-2 · กัน .json() throw ถ้า response เป็น HTML error page
 let data;
 try { data = await res.json(); }
 catch (parseErr) {
   const txt = await res.text().catch(() => '');
   throw new Error(`HTTP ${res.status} · ${(txt || parseErr.message || '').slice(0, 150)}`);
 }

 clearInterval(elapsedTimer);
 // v10.0.x — P0-2 · ถ้า server ตอบ error → แสดงให้ user เห็น (เดิม res.ok=false ก็แสดง data.answer=undefined)
 if (!res.ok || !data.answer) {
   removeMessage(loadingId);
   const errMsg = data?.detail?.error?.message || data?.detail || data?.error || `HTTP ${res.status}`;
   const msg = (getLang() === 'th' ? 'ไม่สามารถตอบคำถามได้: ' : 'Cannot answer: ') + String(errMsg).slice(0, 200);
   addMessage(msg, 'assistant', true);
   return;  // _chatBusy reset ใน finally
 }
 // Replace loading with answer
 removeMessage(loadingId);
 const msgHtml = `${data.answer}
 <div class="injection-badge"> ${data.injection_summary || 'Context injected'}</div>`;
 addMessage(msgHtml, 'assistant', true);

 // Update sources panel
 updateSourcesPanel(data);
 } catch (e) {
 clearInterval(elapsedTimer);
 removeMessage(loadingId);
 // v10.0.x — P0-2 · แสดง error message จริงให้ user · เดิม "เกิดข้อผิดพลาด" ไม่ระบุสาเหตุ
 const detail = (e && e.message) ? ` (${String(e.message).slice(0, 150)})` : '';
 addMessage((getLang() === 'th' ? 'เกิดข้อผิดพลาดในการเชื่อมต่อ AI' : 'Error connecting to AI') + detail, 'assistant', true);
 } finally {
 _chatBusy = false;
 input.disabled = false;
 if (sendBtn) { sendBtn.disabled = false; sendBtn.innerHTML = originalSendHTML; }
 typingEl?.classList.add('hidden');
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
 .attr('transform', d => `translate(${Number.isFinite(d.x) ? d.x : 0},${Number.isFinite(d.y) ? d.y : 0})`);

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
 // v7.0 — Refresh Drive status ทุกครั้งที่เปิด modal (แก้ Loading... stuck)
 if (typeof refreshDriveStatus === 'function') refreshDriveStatus();
 // v8.0.0 — Refresh LINE bot status
 loadLineStatus();
 });

 document.getElementById('close-profile-modal')?.addEventListener('click', () => {
 document.getElementById('profile-modal').classList.add('hidden');
 });

 document.getElementById('btn-save-profile')?.addEventListener('click', saveProfile);

 // v8.0.0 — LINE Bot connect/disconnect handlers
 document.getElementById('btn-connect-line')?.addEventListener('click', connectLine);
 document.getElementById('btn-disconnect-line')?.addEventListener('click', disconnectLine);
 document.getElementById('btn-open-line')?.addEventListener('click', openLineChat);

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
 const btn = document.getElementById('btn-save-profile');
 // v7.2.0 — guard against double-submit while in-flight
 if (btn?.disabled) return;
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
 const originalHTML = btn?.innerHTML;
 if (btn) {
  btn.disabled = true;
  btn.innerHTML = `<span class="loading-spinner"></span> ${getLang() === 'th' ? 'กำลังบันทึก...' : 'Saving...'}`;
 }
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
 finally {
  if (btn) { btn.disabled = false; btn.innerHTML = originalHTML; }
 }
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
// v7.2.0 — UX-001: error toasts must NEVER auto-dismiss; user closes manually.
// success/info still auto-dismiss after 4s.
function showToast(message, type = 'info') {
 const container = document.getElementById('toast-container');
 if (!container) return;
 const toast = document.createElement('div');
 toast.className = `toast ${type}`;
 const msgSpan = document.createElement('span');
 msgSpan.className = 'toast-msg';
 msgSpan.textContent = message;
 toast.appendChild(msgSpan);
 const closeBtn = document.createElement('button');
 closeBtn.className = 'toast-close';
 closeBtn.setAttribute('aria-label', getLang() === 'th' ? 'ปิด' : 'Close');
 closeBtn.textContent = '×';
 closeBtn.addEventListener('click', () => toast.remove());
 toast.appendChild(closeBtn);
 container.appendChild(toast);
 if (type !== 'error') {
  setTimeout(() => toast.remove(), 4000);
 }
}

function showConfirm(message, options = {}) {
 // v7.5.0 — options: { okText?: string, cancelText?: string|null, okOnly?: bool }
 // Backward compat: showConfirm(msg) still works (just message, default i18n labels)
 return new Promise(resolve => {
 const modal = document.getElementById('confirm-modal');
 document.getElementById('confirm-message').textContent = message;
 modal.classList.remove('hidden');

 const ok = document.getElementById('confirm-ok');
 const cancel = document.getElementById('confirm-cancel');

 // Apply custom button labels (fall back to defaults if not provided)
 const origOkText = ok.textContent;
 const origCancelText = cancel.textContent;
 if (options.okText) ok.textContent = options.okText;
 if (options.cancelText !== undefined && options.cancelText !== null) {
   cancel.textContent = options.cancelText;
 }
 // okOnly mode: hide cancel button (user must acknowledge)
 const cancelHidden = options.okOnly === true || options.cancelText === null;
 if (cancelHidden) cancel.classList.add('hidden');

 const cleanup = (result) => {
 modal.classList.add('hidden');
 // Restore original labels + visibility for next caller
 ok.textContent = origOkText;
 cancel.textContent = origCancelText;
 if (cancelHidden) cancel.classList.remove('hidden');
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
 const isTH = getLang() === 'th';

 // v10.0.x — P3-12 · client-side validation · 1-80 chars
 if (!label) {
   showToast(isTH ? 'ชื่อ Token ห้ามว่าง' : 'Token name cannot be empty', 'error');
   labelInput?.focus();
   return;
 }
 if (label.length > 80) {
   showToast(isTH
     ? `ชื่อ Token ยาวเกิน 80 ตัวอักษร (ปัจจุบัน ${label.length})`
     : `Token name too long (max 80, current ${label.length})`, 'error');
   labelInput?.focus();
   return;
 }

 const btn = document.getElementById('btn-generate-token');
 btn.disabled = true;
 btn.innerHTML = `<span class="loading-spinner"></span> ${isTH ? 'กำลังสร้าง...' : 'Generating...'}`;

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

 // Need a token to test — check state first, then fallback to displayed token.
 // Phase 1.5 fix: read from `mcp-token-value` (the <code> element holding only
 // the raw token), NOT `mcp-token-display` (the wrapper that also contains the
 // warning copy — concatenating both produced a malformed Bearer token → 401).
 let token = state.mcpLastToken;
 if (!token) {
 const tokenEl = document.getElementById('mcp-token-value');
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

 // v7.4.0 — kebab menu (Edit / Pin / Delete). On desktop the kebab is
 // visible at the top-right of the card; on mobile it's the only way
 // to reach card-level actions (no flyout-on-hover).
 const isTH = getLang() === 'th';
 const editLabel = isTH ? 'แก้ไข' : 'Edit';
 const pinLabel = c.is_pinned ? (isTH ? 'ถอดหมุด' : 'Unpin') : (isTH ? 'ปักหมุด' : 'Pin');
 const delLabel = isTH ? 'ลบ' : 'Delete';

 // NOTE: inline-onclick scope on a <button> uses an implicit `with`
 // on the form/element, which can shadow global function names like
 // `name`. Use `window.` explicitly so the lookup always falls through.
 return `<div class="ctx-card${pinnedClass}" onclick="window.viewContext('${cid}')">
 <button class="kebab-btn ctx-kebab" onclick="event.stopPropagation(); window.toggleKebab(event, 'ctx-${cid}')" aria-label="${isTH ? 'การกระทำเพิ่มเติม' : 'More actions'}">⋮</button>
 <div class="kebab-menu hidden" id="kebab-ctx-${cid}">
 <button class="kebab-menu-item" onclick="event.stopPropagation(); document.getElementById('kebab-ctx-${cid}')?.classList.add('hidden'); window.editContext('${cid}')">${editLabel}</button>
 <button class="kebab-menu-item" onclick="event.stopPropagation(); document.getElementById('kebab-ctx-${cid}')?.classList.add('hidden'); window.togglePin('${cid}', ${!c.is_pinned})">${pinLabel}</button>
 <button class="kebab-menu-item danger" onclick="event.stopPropagation(); document.getElementById('kebab-ctx-${cid}')?.classList.add('hidden'); window.deleteCtx('${cid}')">${delLabel}</button>
 </div>
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
 const titleEl = document.getElementById('ctx-input-title');
 const contentEl = document.getElementById('ctx-input-content');
 const title = titleEl.value.trim();
 const content = contentEl.value.trim();
 const ctxType = document.getElementById('ctx-input-type').value;
 const tagsStr = document.getElementById('ctx-input-tags').value;
 const isPinned = document.getElementById('ctx-input-pinned').checked;
 const tags = tagsStr ? tagsStr.split(',').map(t => t.trim()).filter(Boolean) : [];

 // v7.3.0 — clear any leftover invalid state from a previous attempt
 titleEl.classList.remove('is-invalid');
 contentEl.classList.remove('is-invalid');

 // v7.3.0 — validate required fields; mark + focus the first empty
 const isTH = getLang() === 'th';
 if (!title) {
 titleEl.classList.add('is-invalid');
 titleEl.focus();
 showToast(isTH ? 'กรุณาใส่ชื่อ Context' : 'Please enter a context title', 'error');
 return;
 }
 if (!content) {
 contentEl.classList.add('is-invalid');
 contentEl.focus();
 showToast(isTH ? 'กรุณาใส่เนื้อหา Context' : 'Please enter context content', 'error');
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

 // v7.3.0 — clear `.is-invalid` as soon as the user types in the field
 ['ctx-input-title', 'ctx-input-content'].forEach(id => {
 document.getElementById(id)?.addEventListener('input', (e) => {
  e.target.classList.remove('is-invalid');
 });
 });

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
