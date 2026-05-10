// v8.0.0 — LINE Bot UI module (profile section + connect/disconnect handlers)
// ─────────────────────────────────────────────────────────────────────────────
// อยู่ใน profile modal — ผู้ใช้เห็นสถานะ LINE bot + ผูก/เลิกผูก account
// Backend endpoints:
//   GET /api/line/status       → { feature_available, linked, line_display_name, ... }
//   POST /api/line/connect     → { redirect_url } (start LINE Login OAuth)
//   POST /api/line/disconnect  → soft-unlink current LINE account
//
// Note: connect button → redirect to LINE Login OAuth (server-initiated)
//       OR show QR/instructions to scan bot in LINE app first (mobile flow)

async function loadLineStatus() {
  const section = document.getElementById('line-bot-section');
  if (!section) return;

  try {
    const res = await authFetch('/api/line/status');
    if (!res.ok) {
      // Endpoint ยังไม่ deploy หรือ user ไม่ login — soft fail
      _renderLineStatus({ feature_available: false, linked: false });
      return;
    }
    const data = await res.json();
    _renderLineStatus(data);
  } catch (e) {
    console.warn('[line] status fetch failed:', e);
    _renderLineStatus({ feature_available: false, linked: false });
  }
}

function _renderLineStatus(data) {
  const badge = document.getElementById('line-bot-badge');
  const desc = document.getElementById('line-bot-desc');
  const info = document.getElementById('line-bot-info');
  const btnConnect = document.getElementById('btn-connect-line');
  const btnDisconnect = document.getElementById('btn-disconnect-line');
  const btnOpen = document.getElementById('btn-open-line');
  const notice = document.getElementById('line-bot-notice');
  const noticeText = document.getElementById('line-bot-notice-text');

  // Feature flag — ถ้า server ยังไม่ configure LINE → notice
  if (!data.feature_available) {
    if (badge) badge.textContent = (getLang() === 'th') ? 'ยังไม่พร้อม' : 'Not available';
    if (badge) badge.className = 'line-bot-badge line-bot-badge-disconnected';
    if (info) info.classList.add('hidden');
    if (btnConnect) btnConnect.classList.add('hidden');
    if (btnDisconnect) btnDisconnect.classList.add('hidden');
    if (btnOpen) btnOpen.classList.add('hidden');
    if (notice) notice.classList.remove('hidden');
    if (noticeText) noticeText.textContent = (getLang() === 'th')
      ? 'ระบบ LINE bot ยังไม่ถูกตั้งค่าบนเซิร์ฟเวอร์'
      : 'LINE bot is not configured on this server yet.';
    return;
  }

  // Hide notice when feature available
  if (notice) notice.classList.add('hidden');

  // v9.4.2 (L2) — Capture bot URL for "Open in LINE" + "Connect LINE" buttons
  // Why: openLineChat() + connectLine() อ่านค่านี้ · ก่อนรอบนี้ไม่มีใครเซ็ต → button เงียบ
  window._lineBotUrl = data.bot_url || null;

  if (data.linked) {
    if (badge) {
      badge.textContent = (getLang() === 'th') ? 'เชื่อมแล้ว' : 'Connected';
      badge.className = 'line-bot-badge line-bot-badge-connected';
    }
    if (info) info.classList.remove('hidden');
    if (document.getElementById('line-bot-display-name')) {
      document.getElementById('line-bot-display-name').textContent = data.line_display_name || '—';
    }
    if (document.getElementById('line-bot-linked-at')) {
      document.getElementById('line-bot-linked-at').textContent = formatDate(data.linked_at) || '—';
    }
    if (document.getElementById('line-bot-last-seen')) {
      document.getElementById('line-bot-last-seen').textContent = formatTimeAgo(data.last_seen_at) || '—';
    }
    if (btnConnect) btnConnect.classList.add('hidden');
    if (btnDisconnect) btnDisconnect.classList.remove('hidden');
    if (btnOpen) btnOpen.classList.remove('hidden');
  } else {
    if (badge) {
      badge.textContent = (getLang() === 'th') ? 'ยังไม่เชื่อม' : 'Not linked';
      badge.className = 'line-bot-badge line-bot-badge-disconnected';
    }
    if (info) info.classList.add('hidden');
    if (btnConnect) btnConnect.classList.remove('hidden');
    if (btnDisconnect) btnDisconnect.classList.add('hidden');
    if (btnOpen) btnOpen.classList.add('hidden');
  }
}

async function connectLine() {
  // v9.4.2 (L1) — Direct bot URL open · เลิกใช้ /api/line/connect ที่ส่งกลับ /auth/line
  // โดยไม่มี linkToken (ทำให้ user เจอ error page).
  //
  // Reason: LINE Messaging API linkToken ออกได้เฉพาะหลัง user follow bot
  // (POST /v2/bot/user/{userId}/linkToken). ทำ server-initiated link ไม่ได้.
  // Working flow: user เปิด LINE → เพิ่ม bot → bot ส่ง Flex card with link → ยืนยัน.
  const botUrl = window._lineBotUrl;
  if (!botUrl) {
    showToast(
      getLang() === 'th'
        ? 'LINE bot ยังไม่พร้อมใช้งาน — กรุณารีเฟรชหน้า'
        : 'LINE bot not ready — please refresh the page',
      'error'
    );
    return;
  }
  window.open(botUrl, '_blank');
  showToast(
    getLang() === 'th'
      ? 'เปิด LINE และเพิ่ม bot เป็นเพื่อน · bot จะส่งลิงก์ยืนยันมาให้'
      : 'Open LINE and add the bot · the bot will send a link prompt',
    'info'
  );
}

async function disconnectLine() {
  const ok = await showConfirm(
    getLang() === 'th'
      ? 'ต้องการเลิกเชื่อมบัญชี LINE? คุณจะไม่ได้รับข้อความจาก bot อีก'
      : 'Disconnect LINE? You will no longer receive bot messages.'
  );
  if (!ok) return;

  try {
    const res = await authFetch('/api/line/disconnect', { method: 'POST' });
    if (!res.ok) {
      showToast(getLang() === 'th' ? 'เลิกเชื่อมไม่สำเร็จ' : 'Disconnect failed', 'error');
      return;
    }
    showToast(getLang() === 'th' ? 'เลิกเชื่อม LINE แล้ว' : 'LINE disconnected', 'success');
    loadLineStatus();
  } catch (e) {
    showToast(getLang() === 'th' ? 'เลิกเชื่อมไม่สำเร็จ' : 'Disconnect failed', 'error');
  }
}

function openLineChat() {
  // Open LINE app/web with bot Basic ID
  // Format: https://line.me/R/ti/p/@<basic_id_without_@>
  // Server returns basic_id ใน /api/line/status response (data.bot_basic_id)
  const lineUrl = window._lineBotUrl || null;
  if (lineUrl) {
    window.open(lineUrl, '_blank');
  } else {
    showToast(getLang() === 'th' ? 'กรุณาเปิดแอป LINE แล้วค้นหา bot' : 'Open LINE and search for the bot', 'info');
  }
}
