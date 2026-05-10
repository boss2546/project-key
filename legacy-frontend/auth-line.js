// v8.0.0 — LINE Bot Account Link Landing Page
// ─────────────────────────────────────────────────────────────────────────────
// User flow:
// 1. User เพิ่ม PDB bot ใน LINE → bot ส่ง welcome + ปุ่ม "เชื่อมบัญชี"
// 2. User กดปุ่ม → เปิด LINE in-app browser ไปที่ /auth/line?linkToken=xxx
// 3. หน้านี้:
//    a. ตรวจ pdb_token ใน localStorage
//    b. ถ้ามี → show "ยืนยัน" + POST /api/line/confirm-link
//    c. ถ้าไม่มี → show "เข้าสู่ระบบก่อน" → redirect to /
// 4. หลังยืนยัน success → redirect ไป LINE deep link (line://oaMessage/...)
//    หรือกลับไป LINE app
//
// Phase D scope: skeleton UI + token check + confirm placeholder
// Phase E scope: full LINE Account Link nonce flow + accountLink webhook trigger

(function() {
  const stateEl = document.getElementById('auth-line-state');
  const stateTextEl = document.getElementById('auth-line-state-text');
  const actionsEl = document.getElementById('auth-line-actions');
  const btnConfirm = document.getElementById('btn-confirm-link');
  const btnLogin = document.getElementById('btn-login-first');
  const linkCancel = document.getElementById('link-cancel');
  // v9.4.3 — Countdown timer elements (LINE linkToken TTL = 10 นาที)
  const countdownEl = document.getElementById('auth-line-countdown');
  const countdownValueEl = document.getElementById('auth-line-countdown-value');
  let countdownInterval = null;

  function setState(text, kind) {
    if (stateTextEl) stateTextEl.textContent = text;
    if (stateEl) {
      stateEl.classList.remove('error', 'success');
      if (kind) stateEl.classList.add(kind);
      // Remove spinner if final state
      if (kind === 'error' || kind === 'success') {
        const spinner = stateEl.querySelector('.auth-line-spinner');
        if (spinner) spinner.remove();
      }
    }
  }

  function showActions() {
    if (actionsEl) actionsEl.style.display = '';
  }

  // v9.4.3 — Countdown timer for LINE linkToken (10-min TTL per LINE spec)
  // Why: user ใหม่ที่ต้อง register ก่อนอาจไม่ทันเวลา · countdown แจ้งเตือนชัดเจน
  // ทำให้รู้ว่าต้องเร่ง · ถ้าหมดเวลา → ส่ง user กลับไปขอลิงก์ใหม่จาก LINE bot
  function startCountdown(durationSec) {
    if (!countdownEl || !countdownValueEl) return;
    countdownEl.style.display = '';
    let remaining = durationSec;
    const tick = () => {
      const min = Math.floor(remaining / 60);
      const sec = remaining % 60;
      countdownValueEl.textContent = `${min}:${String(sec).padStart(2, '0')}`;
      // < 2 นาที → warning state (pulse + red)
      if (remaining < 120 && remaining > 0) {
        countdownEl.classList.add('warning');
      }
      // หมดเวลา → expired state + disable confirm button
      if (remaining <= 0) {
        countdownEl.classList.remove('warning');
        countdownEl.classList.add('expired');
        countdownValueEl.textContent = '0:00';
        if (btnConfirm) {
          btnConfirm.disabled = true;
          btnConfirm.textContent = 'ลิงก์หมดอายุ — กลับไปขอใหม่จาก LINE bot';
        }
        if (countdownInterval) {
          clearInterval(countdownInterval);
          countdownInterval = null;
        }
        return;
      }
      remaining -= 1;
    };
    tick();  // immediate first tick
    countdownInterval = setInterval(tick, 1000);
  }

  function stopCountdown() {
    if (countdownInterval) {
      clearInterval(countdownInterval);
      countdownInterval = null;
    }
    if (countdownEl) countdownEl.style.display = 'none';
  }

  function getQueryParam(name) {
    const params = new URLSearchParams(window.location.search);
    return params.get(name);
  }

  function getToken() {
    return localStorage.getItem('pdb_token');
  }

  async function init() {
    const linkToken = getQueryParam('linkToken');
    const pdbToken = getToken();

    // Phase D: ถ้าไม่มี linkToken → แสดง message + ส่งกลับ LINE
    if (!linkToken) {
      setState('ไม่พบ linkToken — กรุณาเริ่มจาก LINE bot', 'error');
      showActions();
      btnConfirm.style.display = 'none';
      btnLogin.style.display = 'none';
      return;
    }

    // ตรวจ login state
    if (!pdbToken) {
      setState('คุณต้องเข้าสู่ระบบ Personal Data Bank ก่อน', '');
      showActions();
      btnConfirm.style.display = 'none';
      btnLogin.style.display = '';
      btnLogin.addEventListener('click', () => {
        // เก็บ linkToken ใน sessionStorage แล้วส่งกลับมาหน้านี้
        sessionStorage.setItem('pdb_pending_line_link', linkToken);
        window.location.href = '/';
      });
      return;
    }

    // ตรวจ user info จาก localStorage
    let userEmail = '—';
    try {
      const user = JSON.parse(localStorage.getItem('pdb_user') || '{}');
      userEmail = user.email || '—';
    } catch (e) { /* ignore */ }

    setState(`พร้อมเชื่อมบัญชี: ${userEmail}`, 'success');
    showActions();
    // v9.4.3 — Start countdown · LINE linkToken TTL = 10 นาที
    // Note: เราไม่รู้ว่า linkToken issue ไปนานแค่ไหนแล้ว · assume worst case 10 min full
    // (จริงๆ อาจน้อยกว่าถ้า user รอนานหลังกด link จาก LINE) · เป็นการแจ้งเตือนเชิง defensive
    startCountdown(10 * 60);
    btnConfirm.addEventListener('click', () => doConfirmLink(linkToken, pdbToken));
  }

  async function doConfirmLink(linkToken, pdbToken) {
    setState('กำลังเชื่อมบัญชี...', '');
    btnConfirm.disabled = true;

    try {
      const res = await fetch('/api/line/confirm-link', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + pdbToken,
        },
        body: JSON.stringify({ link_token: linkToken }),
      });
      const data = await res.json();
      if (!res.ok) {
        const msg = data?.detail?.error?.message || data?.detail || 'เชื่อมบัญชีไม่สำเร็จ';
        setState(msg, 'error');
        btnConfirm.disabled = false;
        return;
      }

      setState('เชื่อมบัญชีสำเร็จ! กำลังกลับไป LINE...', 'success');
      stopCountdown();  // v9.4.3 — stop ticking once we hand off to LINE
      // Redirect ไป LINE deep link หรือ window.close ถ้าเปิดมาจาก in-app browser
      if (data.redirect_url) {
        setTimeout(() => { window.location.href = data.redirect_url; }, 1200);
      } else {
        // Fallback — ปิด tab/window (LINE in-app browser usually allows)
        setTimeout(() => {
          try { window.close(); } catch (e) { /* ignore */ }
          // ถ้า close ไม่ได้ → redirect to home
          setTimeout(() => { window.location.href = '/'; }, 500);
        }, 1200);
      }
    } catch (e) {
      setState('เชื่อมต่อเซิร์ฟเวอร์ไม่สำเร็จ', 'error');
      btnConfirm.disabled = false;
    }
  }

  // Run init on DOMContentLoaded
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
