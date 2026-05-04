/* ═══════════════════════════════════════════════════════════════
   PDB landing-v4 — minimal, smooth-scroll
   ───────────────────────────────────────────────────────────────
   - Pause off-screen videos via IntersectionObserver
   - Top-bar light/dark toggle by intersection
   - Auth modal (real /api/auth/* endpoints)
   - NO GSAP, NO ScrollTrigger, NO sticky/pin — pure flat scroll.
   ═══════════════════════════════════════════════════════════════ */

(() => {
  "use strict";
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ─── 1. Top bar light/dark toggle ──────────────────── */
  const bar = document.querySelector(".bar");
  if (bar && "IntersectionObserver" in window) {
    const sentinels = document.querySelectorAll(".threshold, .story, .pricing, .trust, .cta, .foot");
    const visible = new Set();
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) visible.add(e.target);
        else visible.delete(e.target);
      });
      bar.classList.toggle("is-light", visible.size > 0);
    }, { rootMargin: "-45% 0px -45% 0px" });
    sentinels.forEach(s => io.observe(s));
  }

  /* ─── 2. Pause off-screen videos to keep scroll smooth ── */
  if ("IntersectionObserver" in window) {
    const playObs = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        const v = e.target;
        if (e.isIntersecting) {
          const p = v.play();
          if (p && p.catch) p.catch(() => {});
        } else {
          v.pause();
        }
      });
    }, { threshold: 0.1 });
    document.querySelectorAll("video").forEach(v => playObs.observe(v));
  }

  /* ─── 2b. Hero stage detection — rAF throttled, only fires on stage CHANGE ── */
  /* No GSAP, no ScrollTrigger — just one rAF-throttled scroll listener. */
  const hero = document.querySelector(".hero");
  const stages = document.querySelectorAll(".hero-stage");
  const progressFill = document.getElementById("hero-progress-fill");
  if (hero && stages.length && !reduced) {
    let rafId = null;
    let lastIdx = -1;
    function tick() {
      rafId = null;
      const r = hero.getBoundingClientRect();
      const total = r.height - window.innerHeight;
      let p = -r.top / total;
      if (p < 0) p = 0; if (p > 1) p = 1;
      const idx = Math.min(Math.floor(p * stages.length), stages.length - 1);
      if (idx !== lastIdx) {
        for (let i = 0; i < stages.length; i++) {
          stages[i].classList.toggle("is-active", i === idx);
        }
        lastIdx = idx;
      }
      if (progressFill) progressFill.style.transform = `scaleX(${p})`;
    }
    function onScroll() {
      if (rafId == null) rafId = requestAnimationFrame(tick);
    }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll, { passive: true });
    tick();  /* initial */
  } else if (stages.length) {
    /* reduced motion: show stage 1 only */
    stages[0]?.classList.add("is-active");
  }

  /* ─── 3. Reveal-on-scroll for cards ─────────────────── */
  if (reduced) {
    document.querySelectorAll(".reveal").forEach(el => el.classList.add("is-visible"));
  } else if ("IntersectionObserver" in window) {
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => {
        if (e.isIntersecting) { e.target.classList.add("is-visible"); io.unobserve(e.target); }
      });
    }, { threshold: 0.15, rootMargin: "0px 0px -10% 0px" });
    document.querySelectorAll(".reveal").forEach(el => io.observe(el));
  }

  /* ─── 4. AUTH MODAL ─────────────────────────────────── */
  const modal = document.getElementById("auth-modal");
  const titleEl = document.getElementById("auth-modal-title");
  const formIds = ["login", "register", "forgot", "reset"];
  const titles = { login: "เข้าสู่ระบบ", register: "สมัครสมาชิก", forgot: "ลืมรหัสผ่าน", reset: "ตั้งรหัสผ่านใหม่" };

  function showModal(mode) {
    modal.classList.remove("hidden");
    formIds.forEach(m => {
      document.getElementById(`${m}-form`)?.classList.add("hidden");
      document.getElementById(`${m}-error`)?.classList.add("hidden");
    });
    document.getElementById(`${mode}-form`)?.classList.remove("hidden");
    if (titleEl) titleEl.textContent = titles[mode] || titles.login;
    setTimeout(() => document.querySelector(`#${mode}-form input`)?.focus(), 50);
  }
  function hideModal() { modal.classList.add("hidden"); }

  async function postJSON(url, body) {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json().catch(() => ({}));
    return { ok: res.ok, status: res.status, data };
  }
  function showErr(form, msg) {
    const e = document.getElementById(`${form}-error`);
    if (!e) return;
    e.textContent = msg;
    e.classList.remove("hidden");
  }

  async function doLogin() {
    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;
    if (!email || !password) return showErr("login", "กรุณากรอกอีเมลและรหัสผ่าน");
    try {
      const { ok, data } = await postJSON("/api/auth/login", { email, password });
      if (!ok) return showErr("login", data.detail || "Login failed");
      localStorage.setItem("pdb_token", data.token);
      localStorage.setItem("pdb_user", JSON.stringify(data.user));
      hideModal();
      window.location.href = "/app";
    } catch { showErr("login", "Connection error"); }
  }
  async function doRegister() {
    const name = document.getElementById("register-name").value.trim();
    const email = document.getElementById("register-email").value.trim();
    const password = document.getElementById("register-password").value;
    if (!name || !email || password.length < 6) return showErr("register", "กรอกข้อมูลให้ครบ + รหัสผ่านอย่างน้อย 6 ตัว");
    try {
      const { ok, data } = await postJSON("/api/auth/register", { email, password, name });
      if (!ok) return showErr("register", data.detail || "Registration failed");
      localStorage.setItem("pdb_token", data.token);
      localStorage.setItem("pdb_user", JSON.stringify(data.user));
      hideModal();
      window.location.href = "/app";
    } catch { showErr("register", "Connection error"); }
  }
  let _resetToken = null;
  async function doForgot() {
    const email = document.getElementById("forgot-email").value.trim();
    if (!email) return showErr("forgot", "กรุณากรอกอีเมล");
    try {
      const { ok, data } = await postJSON("/api/auth/request-reset", { email });
      if (!ok) return showErr("forgot", data.detail || "เกิดข้อผิดพลาด");
      if (!data.reset_token) return showErr("forgot", data.message || "ถ้าอีเมลนี้มีบัญชีอยู่ ระบบจะส่งลิงก์รีเซ็ตให้");
      _resetToken = data.reset_token;
      const disp = document.getElementById("reset-email-display");
      if (disp) disp.textContent = data.email || email;
      showModal("reset");
    } catch { showErr("forgot", "ไม่สามารถเชื่อมต่อ"); }
  }
  async function doReset() {
    const np = document.getElementById("reset-new-password").value;
    const cp = document.getElementById("reset-confirm-password").value;
    if (np.length < 6) return showErr("reset", "รหัสผ่านอย่างน้อย 6 ตัว");
    if (np !== cp)     return showErr("reset", "รหัสผ่านไม่ตรงกัน");
    try {
      const { ok, data } = await postJSON("/api/auth/reset-password", { token: _resetToken, new_password: np });
      if (!ok) return showErr("reset", data.detail || "เปลี่ยนรหัสผ่านไม่สำเร็จ");
      localStorage.setItem("pdb_token", data.token);
      localStorage.setItem("pdb_user", JSON.stringify(data.user));
      hideModal();
      window.location.href = "/app";
    } catch { showErr("reset", "ไม่สามารถเชื่อมต่อ"); }
  }

  const wireClick = (id, fn) => document.getElementById(id)?.addEventListener("click", fn);
  const wireSwitch = (id, mode) => document.getElementById(id)?.addEventListener("click", e => { e.preventDefault(); showModal(mode); });

  wireClick("btn-show-login",     () => showModal("login"));
  wireClick("btn-show-register",  () => showModal("register"));
  wireClick("btn-hero-register",  () => showModal("register"));
  wireClick("btn-cta-register",   () => showModal("register"));
  wireClick("btn-pricing-free",   () => showModal("register"));
  wireClick("btn-pricing-starter",() => showModal("register"));
  wireClick("btn-exec-demo",      () => window.open("mailto:hello@personaldatabank.fly.dev?subject=Executive%20Digital%20Twin%20-%20Private%20Demo", "_blank"));
  wireClick("auth-modal-close",   hideModal);
  wireClick("btn-login",          doLogin);
  wireClick("btn-register",       doRegister);
  wireClick("btn-forgot-submit",  doForgot);
  wireClick("btn-reset-submit",   doReset);
  wireSwitch("switch-to-login",         "login");
  wireSwitch("switch-to-register",      "register");
  wireSwitch("switch-to-forgot",        "forgot");
  wireSwitch("switch-forgot-to-login",  "login");
  wireSwitch("switch-reset-to-login",   "login");

  document.addEventListener("keydown", e => { if (e.key === "Escape" && !modal.classList.contains("hidden")) hideModal(); });
  modal?.addEventListener("click", e => { if (e.target === modal) hideModal(); });

  document.getElementById("login-password")?.addEventListener("keydown", e => { if (e.key === "Enter") doLogin(); });
  document.getElementById("register-password")?.addEventListener("keydown", e => { if (e.key === "Enter") doRegister(); });
  document.getElementById("forgot-email")?.addEventListener("keydown", e => { if (e.key === "Enter") doForgot(); });
  document.getElementById("reset-confirm-password")?.addEventListener("keydown", e => { if (e.key === "Enter") doReset(); });

  console.log("%c PDB v4 · flat smooth-scroll ", "background:#d97757;color:#faf7f0;padding:6px 12px;border-radius:4px;font-family:monospace;font-weight:bold");
})();
