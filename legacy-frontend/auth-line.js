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
