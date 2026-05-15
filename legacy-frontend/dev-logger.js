/**
 * PDB Dev Logger — local-only debug overlay
 *
 * จับ fetch / console / window errors / page navigation → แสดงผ่าน floating button
 * ปุ่มลอยอยู่มุมขวาล่างทุกหน้า · กดเปิด compact panel · Ctrl+Shift+L = fullscreen viewer
 *
 * Gating:
 *   - เปิดอัตโนมัติบน localhost / 127.0.0.1 (dev)
 *   - Production ปิดเงียบ เว้นแต่ URL มี ?debug=1
 *
 * Storage: sessionStorage (per-tab · cap 500 entries · ไม่กิน localStorage หลัก)
 *
 * API (window.__pdbDevLogger):
 *   .show() / .hide() / .full() / .clear() / .entries() / .pause(bool)
 *
 * Author-Agent: เขียว (Khiao) · v10.0.0
 */
(function () {
  'use strict';

  // ─── Gating: เฉพาะ dev host หรือ explicit ?debug=1 ───
  const isDevHost = ['localhost', '127.0.0.1', ''].includes(location.hostname);
  const forceEnable = new URLSearchParams(location.search).get('debug') === '1';
  if (!isDevHost && !forceEnable) return;

  // กัน double-init เมื่อ script ถูกโหลดซ้ำจาก SPA-like navigation
  if (window.__pdbDevLogger) return;

  // ─── Constants ───
  const MAX_LOGS = 1000;  // เพิ่มจาก 500 · จับเพิ่มหลายชนิด
  const STORAGE_KEY = '__pdb_dev_logs_v1';
  const STATE_KEY = '__pdb_dev_state_v1';
  const SESSION_KEY = '__pdb_dev_session_v1';
  const BTN_ID = '__pdb-dev-btn';
  const PANEL_ID = '__pdb-dev-panel';
  const FULL_ID = '__pdb-dev-full';
  const STYLE_ID = '__pdb-dev-style';
  const SLOW_FETCH_MS = 500;       // หลัง 500ms = warn (เหลือง)
  const VERY_SLOW_FETCH_MS = 2000; // หลัง 2s = alert (แดง)
  const SESSION_START = Date.now();
  // สร้าง/อ่าน session ID (per-tab · ใช้ sessionStorage)
  let SESSION_ID;
  try {
    SESSION_ID = sessionStorage.getItem(SESSION_KEY);
    if (!SESSION_ID) {
      SESSION_ID = 's_' + SESSION_START.toString(36) + '_' + Math.random().toString(36).slice(2, 8);
      sessionStorage.setItem(SESSION_KEY, SESSION_ID);
    }
  } catch (_) {
    SESSION_ID = 's_' + SESSION_START.toString(36);
  }
  // Sensitive header keys ที่ต้อง mask · กัน token leak ใน clipboard/screenshot
  const SENSITIVE_HEADERS = ['authorization', 'cookie', 'x-api-key', 'x-mcp-token', 'x-jwt-token'];
  // Last user action เก็บไว้ correlate กับ error ถัดไป
  let _lastAction = null;

  // ─── State ───
  const state = {
    logs: [],
    paused: false,
    panelOpen: false,
    fullOpen: false,
    filter: 'all',
    search: '',
    errorCount: 0, // นับ error ใหม่ตั้งแต่เปิด panel ครั้งล่าสุด
  };

  // Load จาก sessionStorage (persist ข้าม navigation ใน tab เดียว)
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (raw) {
      state.logs = JSON.parse(raw);
      if (!Array.isArray(state.logs)) state.logs = [];
    }
    const s = sessionStorage.getItem(STATE_KEY);
    if (s) {
      const parsed = JSON.parse(s);
      if (parsed && typeof parsed === 'object') {
        state.paused = !!parsed.paused;
        state.filter = parsed.filter || 'all';
      }
    }
  } catch (_) {
    state.logs = [];
  }

  function persistLogs() {
    try {
      if (state.logs.length > MAX_LOGS) state.logs = state.logs.slice(-MAX_LOGS);
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state.logs));
    } catch (_) {
      // sessionStorage เต็ม → ตัดครึ่งแล้วลองใหม่ครั้งเดียว
      state.logs = state.logs.slice(-Math.floor(MAX_LOGS / 2));
      try { sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state.logs)); } catch (_) {}
    }
  }

  function persistState() {
    try {
      sessionStorage.setItem(STATE_KEY, JSON.stringify({
        paused: state.paused,
        filter: state.filter,
      }));
    } catch (_) {}
  }

  function addLog(entry) {
    if (state.paused) return;
    entry.t = entry.t || Date.now();
    // ใช้ `_id` (ขีดล่างนำ) เพื่อไม่ชนกับ HTML element's `id` ที่ describeElement() ส่งมา
    // (เดิมใช้ entry.id ทำให้ element id เช่น 'login-email' โดน clobber)
    entry._id = (entry.t.toString(36) + Math.random().toString(36).slice(2, 6));
    state.logs.push(entry);
    if (entry.kind === 'error' || (entry.kind === 'fetch' && entry.status >= 400) || entry.level === 'error') {
      state.errorCount++;
    }
    persistLogs();
    scheduleRender();
  }

  // ─── Render scheduler (rAF debounce ป้องกัน thrashing ตอน log ระเบิด) ───
  let _renderQueued = false;
  function scheduleRender() {
    if (_renderQueued) return;
    _renderQueued = true;
    (window.requestAnimationFrame || setTimeout)(() => {
      _renderQueued = false;
      renderBadge();
      if (state.panelOpen) renderPanel();
      if (state.fullOpen) renderFull();
    }, 50);
  }

  // ────────────────────────────────────────────────────────────
  //  CAPTURE LAYER
  // ────────────────────────────────────────────────────────────

  // ─── Capture: fetch ───
  const _origFetch = window.fetch.bind(window);
  window.fetch = async function (input, init) {
    const url = typeof input === 'string' ? input : (input && input.url) || String(input);
    const method = ((init && init.method) || (input && input.method) || 'GET').toUpperCase();
    const start = performance.now();
    let reqBody = init && init.body;
    if (reqBody && typeof reqBody !== 'string') reqBody = '[non-string body type=' + (reqBody.constructor && reqBody.constructor.name) + ']';
    // จับ request headers · mask sensitive · กัน auth token leak
    const reqHeaders = collectHeaders(init && init.headers);
    const entry = {
      kind: 'fetch',
      method,
      url,
      reqHeaders,
      reqBody: reqBody && reqBody.length > 2000 ? reqBody.slice(0, 2000) + '...[truncated +' + (reqBody.length - 2000) + 'b]' : reqBody,
      reqBodySize: reqBody ? (typeof reqBody === 'string' ? reqBody.length : null) : 0,
      status: null,
      statusText: null,
      durationMs: null,
      resHeaders: null,
      resBody: null,
      resBodySize: null,
      error: null,
      lastAction: _lastAction,  // correlate กับ user action ล่าสุด (helps debug "กดแล้วไม่ทำงาน")
    };
    try {
      const res = await _origFetch(input, init);
      entry.status = res.status;
      entry.statusText = res.statusText;
      entry.durationMs = Math.round(performance.now() - start);
      entry.resHeaders = collectResHeaders(res.headers);
      // best-effort อ่าน body แบบ clone (ไม่กระทบ caller)
      try {
        const ct = (res.headers.get('content-type') || '').toLowerCase();
        const cl = res.headers.get('content-length');
        if (cl) entry.resBodySize = parseInt(cl, 10);
        if (ct.includes('json') || ct.includes('text') || ct.includes('xml') || ct.includes('javascript')) {
          const txt = await res.clone().text();
          if (entry.resBodySize == null) entry.resBodySize = txt.length;
          entry.resBody = txt.length > 4000 ? txt.slice(0, 4000) + '...[truncated +' + (txt.length - 4000) + 'b]' : txt;
        } else if (ct) {
          entry.resBody = `[binary · ${ct}${entry.resBodySize ? ' · ' + entry.resBodySize + 'b' : ''}]`;
        }
      } catch (_) {}
      addLog(entry);
      return res;
    } catch (e) {
      entry.error = String((e && e.message) || e);
      entry.durationMs = Math.round(performance.now() - start);
      addLog(entry);
      throw e;
    }
  };

  function collectHeaders(h) {
    if (!h) return {};
    const out = {};
    try {
      if (h instanceof Headers) {
        h.forEach((v, k) => { out[k.toLowerCase()] = maskSensitive(k, v); });
      } else if (Array.isArray(h)) {
        h.forEach(([k, v]) => { out[String(k).toLowerCase()] = maskSensitive(k, v); });
      } else if (typeof h === 'object') {
        Object.keys(h).forEach(k => { out[k.toLowerCase()] = maskSensitive(k, h[k]); });
      }
    } catch (_) {}
    return out;
  }
  function collectResHeaders(h) {
    if (!h || typeof h.forEach !== 'function') return {};
    const out = {};
    try {
      h.forEach((v, k) => { out[k.toLowerCase()] = v; });
    } catch (_) {}
    return out;
  }
  function maskSensitive(k, v) {
    const key = String(k).toLowerCase();
    if (SENSITIVE_HEADERS.includes(key) && typeof v === 'string' && v.length > 12) {
      return v.slice(0, 8) + '...***[masked ' + v.length + 'ch]';
    }
    return v;
  }

  // ─── Capture: console ───
  ['log', 'info', 'warn', 'error', 'debug'].forEach(level => {
    const orig = console[level].bind(console);
    console[level] = function (...args) {
      try {
        addLog({
          kind: 'console',
          level,
          message: args.map(formatArg).join(' '),
        });
      } catch (_) {}
      return orig(...args);
    };
  });

  function formatArg(a) {
    if (a === null) return 'null';
    if (a === undefined) return 'undefined';
    if (typeof a === 'string') return a;
    if (a instanceof Error) return (a.stack || a.message || String(a));
    try { return JSON.stringify(a); } catch (_) { return String(a); }
  }

  // ─── Capture: window errors ───
  window.addEventListener('error', e => {
    addLog({
      kind: 'error',
      level: 'error',
      message: `${e.message || 'Unknown error'} @ ${e.filename || '?'}:${e.lineno || 0}:${e.colno || 0}`,
      stack: (e.error && e.error.stack) || null,
    });
  });

  window.addEventListener('unhandledrejection', e => {
    const reason = e.reason;
    addLog({
      kind: 'error',
      level: 'unhandledrejection',
      message: 'Unhandled Promise rejection: ' + String((reason && reason.message) || reason),
      stack: (reason && reason.stack) || null,
    });
  });

  // ─── Capture: page nav + session meta ───
  // ใส่ meta entry แรกของ session · มี info ครบสำหรับ debug ("เกิดบนเครื่องอะไร, viewport เท่าไหร่")
  addLog({
    kind: 'meta',
    event: 'page-load',
    url: location.href,
    title: document.title || '(no title)',
    referrer: document.referrer || null,
    sessionId: SESSION_ID,
    userAgent: navigator.userAgent,
    language: navigator.language,
    languages: (navigator.languages || []).slice(0, 5),
    viewport: { w: window.innerWidth, h: window.innerHeight, dpr: window.devicePixelRatio },
    screen: { w: screen.width, h: screen.height, colorDepth: screen.colorDepth },
    online: navigator.onLine,
    cookieEnabled: navigator.cookieEnabled,
    platform: navigator.platform,
    tokenPresent: !!(function () { try { return localStorage.getItem('pdb_token'); } catch (_) { return null; } })(),
    storageUsed: estimateStorageSize(),
  });
  window.addEventListener('beforeunload', () => {
    addLog({ kind: 'nav', event: 'unload', url: location.href, runtimeMs: Date.now() - SESSION_START });
  });

  function estimateStorageSize() {
    try {
      let ls = 0, ss = 0;
      for (let i = 0; i < localStorage.length; i++) {
        const k = localStorage.key(i);
        ls += (k + (localStorage.getItem(k) || '')).length;
      }
      for (let i = 0; i < sessionStorage.length; i++) {
        const k = sessionStorage.key(i);
        ss += (k + (sessionStorage.getItem(k) || '')).length;
      }
      return { localStorage: ls, sessionStorage: ss };
    } catch (_) { return null; }
  }

  // ─── Capture: performance timing (เมื่อ load event เสร็จ) ───
  window.addEventListener('load', () => {
    setTimeout(() => {
      try {
        const nav = performance.getEntriesByType && performance.getEntriesByType('navigation')[0];
        const paints = performance.getEntriesByType && performance.getEntriesByType('paint') || [];
        const fp = paints.find(p => p.name === 'first-paint');
        const fcp = paints.find(p => p.name === 'first-contentful-paint');
        addLog({
          kind: 'perf',
          event: 'page-loaded',
          domContentLoadedMs: nav ? Math.round(nav.domContentLoadedEventEnd - nav.startTime) : null,
          loadEventMs: nav ? Math.round(nav.loadEventEnd - nav.startTime) : null,
          firstPaintMs: fp ? Math.round(fp.startTime) : null,
          firstContentfulPaintMs: fcp ? Math.round(fcp.startTime) : null,
          transferSize: nav ? nav.transferSize : null,
          decodedBodySize: nav ? nav.decodedBodySize : null,
        });
      } catch (_) {}
    }, 100);
  });

  // ─── Capture: clicks (ทุก click ใน document · จับ target info) ───
  // ช่วย debug "กดแล้วไม่ทำงาน" + bind _lastAction ให้ fetch ถัดไป correlate ได้
  document.addEventListener('click', e => {
    const t = e.target;
    if (!t || !t.tagName) return;
    // Skip click ในตัว dev-logger เอง (กัน noise)
    if (t.closest && t.closest('#' + BTN_ID + ', #' + PANEL_ID + ', #' + FULL_ID)) return;
    const info = describeElement(t);
    _lastAction = { type: 'click', at: Date.now(), ...info };
    addLog({
      kind: 'click',
      event: 'click',
      x: e.clientX, y: e.clientY,
      ...info,
    });
  }, true);  // capture phase · จับก่อน handler app

  function describeElement(el) {
    const tag = el.tagName ? el.tagName.toLowerCase() : '?';
    const id = el.id || null;
    const cls = (el.className && typeof el.className === 'string') ? el.className.trim().split(/\s+/).slice(0, 4).join('.') : null;
    let text = '';
    try {
      text = (el.innerText || el.textContent || el.value || el.placeholder || '').trim().slice(0, 60);
    } catch (_) {}
    // build short selector path
    let selector = tag;
    if (id) selector += '#' + id;
    else if (cls) selector += '.' + cls;
    return {
      selector,
      tag,
      id,
      classes: cls,
      text: text || null,
      type: el.type || null,
      name: el.name || null,
      href: el.href || null,
    };
  }

  // ─── Capture: form submits ───
  document.addEventListener('submit', e => {
    const form = e.target;
    if (!form || !form.elements) return;
    const fields = {};
    try {
      Array.from(form.elements).forEach(f => {
        if (!f.name) return;
        // mask password / sensitive fields
        if (f.type === 'password' || /password|secret|token|otp/i.test(f.name)) {
          fields[f.name] = f.value ? '***[' + f.value.length + 'ch]' : '';
        } else {
          fields[f.name] = (f.value || '').slice(0, 200);
        }
      });
    } catch (_) {}
    _lastAction = { type: 'submit', at: Date.now(), formId: form.id || null };
    addLog({
      kind: 'form',
      event: 'submit',
      formId: form.id || null,
      action: form.action || null,
      method: (form.method || 'GET').toUpperCase(),
      fields,
    });
  }, true);

  // ─── Capture: storage changes (localStorage + sessionStorage) ───
  // intercept .setItem + .removeItem + .clear ของทั้ง 2 storages
  ['localStorage', 'sessionStorage'].forEach(name => {
    try {
      const store = window[name];
      if (!store) return;
      const origSet = store.setItem.bind(store);
      const origRem = store.removeItem.bind(store);
      const origClr = store.clear.bind(store);
      store.setItem = function (k, v) {
        // skip dev-logger ของตัวเอง · กัน loop
        if (k === STORAGE_KEY || k === STATE_KEY || k === SESSION_KEY) return origSet(k, v);
        const prev = store.getItem(k);
        addLog({
          kind: 'storage',
          area: name,
          op: prev == null ? 'set' : 'update',
          key: k,
          prevSize: prev == null ? null : prev.length,
          newSize: v == null ? 0 : String(v).length,
          newValuePreview: /token|secret|password|key/i.test(k) ? '***[masked]' : String(v).slice(0, 100),
        });
        return origSet(k, v);
      };
      store.removeItem = function (k) {
        if (k === STORAGE_KEY || k === STATE_KEY || k === SESSION_KEY) return origRem(k);
        addLog({ kind: 'storage', area: name, op: 'remove', key: k });
        return origRem(k);
      };
      store.clear = function () {
        addLog({ kind: 'storage', area: name, op: 'clear', count: store.length });
        return origClr();
      };
    } catch (_) {}
  });
  // 'storage' event = เกิดจาก tab อื่นเปลี่ยน storage
  window.addEventListener('storage', e => {
    addLog({
      kind: 'storage',
      area: e.storageArea === sessionStorage ? 'sessionStorage' : 'localStorage',
      op: 'cross-tab',
      key: e.key,
      newValuePreview: e.newValue ? String(e.newValue).slice(0, 100) : null,
      url: e.url,
    });
  });

  // ─── Capture: online/offline + visibility ───
  window.addEventListener('online', () => addLog({ kind: 'net', event: 'online' }));
  window.addEventListener('offline', () => addLog({ kind: 'net', event: 'offline' }));
  document.addEventListener('visibilitychange', () => {
    addLog({ kind: 'vis', event: document.visibilityState });
  });

  // ─── Capture: route changes (History API + hashchange + popstate) ───
  // SPA-like nav (เช่น sidebar กด → app เปลี่ยน view ผ่าน history.pushState) จะถูกจับครบ
  let _currentUrl = location.href;
  function logRoute(reason) {
    // บันทึกทุก event ที่เกี่ยวกับ navigation · ไม่ dedup based on URL
    // (เดิมเจอ popstate fire ก่อน hashchange → URL ตรงกัน → hashchange ถูก skip)
    const from = _currentUrl;
    const to = location.href;
    _currentUrl = to;
    // skip noise: ถ้า URL ไม่เปลี่ยนเลย + reason เป็น replaceState ที่ replace แบบไม่ขยับ → skip
    if (from === to && reason === 'replaceState') return;
    addLog({
      kind: 'route',
      reason,
      from,
      to,
      hash: location.hash,
      pathname: location.pathname,
      search: location.search,
    });
  }
  const _origPush = history.pushState.bind(history);
  const _origReplace = history.replaceState.bind(history);
  // เรียก logRoute sync หลัง _origPush/Replace (location.href update sync แล้ว)
  // เดิม setTimeout(0) ทำให้สอง calls ติดกันใช้ snapshot location.href อันเดียวกัน → call หลังเจอ "ไม่เปลี่ยน" เลย skip
  history.pushState = function (...args) { const r = _origPush(...args); logRoute('pushState'); return r; };
  history.replaceState = function (...args) { const r = _origReplace(...args); logRoute('replaceState'); return r; };
  window.addEventListener('popstate', () => logRoute('popstate'));
  window.addEventListener('hashchange', () => logRoute('hashchange'));

  // ─── Capture: input focus/blur/change (เห็นว่า user typed ที่ field ไหนบ้าง) ───
  // ใช้ 'focus' + capture=true (ครอบคลุมกว่า focusin · ไม่พึ่ง bubble · catch จาก descendant ทุกระดับ)
  document.addEventListener('focus', e => {
    const t = e.target;
    if (!t || !t.tagName) return;
    if (t.closest && t.closest('#' + BTN_ID + ', #' + PANEL_ID + ', #' + FULL_ID)) return;
    const tag = t.tagName.toLowerCase();
    if (!['input', 'textarea', 'select'].includes(tag)) return;
    addLog({
      kind: 'focus',
      event: 'focus',
      ...describeElement(t),
    });
  }, true);

  document.addEventListener('change', e => {
    const t = e.target;
    if (!t || !t.tagName) return;
    if (t.closest && t.closest('#' + BTN_ID + ', #' + PANEL_ID + ', #' + FULL_ID)) return;
    const tag = t.tagName.toLowerCase();
    if (!['input', 'textarea', 'select'].includes(tag)) return;
    const isSensitive = t.type === 'password' || /password|secret|token|otp/i.test(t.name || '');
    const val = isSensitive
      ? (t.value ? '***[' + t.value.length + 'ch]' : '')
      : (t.type === 'checkbox' || t.type === 'radio' ? t.checked : String(t.value || '').slice(0, 200));
    addLog({
      kind: 'input',
      event: 'change',
      ...describeElement(t),
      value: val,
    });
  }, true);

  // ─── Capture: double-click + contextmenu (right-click) ───
  document.addEventListener('dblclick', e => {
    const t = e.target;
    if (!t || !t.tagName) return;
    if (t.closest && t.closest('#' + BTN_ID + ', #' + PANEL_ID + ', #' + FULL_ID)) return;
    addLog({
      kind: 'click',
      event: 'dblclick',
      x: e.clientX, y: e.clientY,
      ...describeElement(t),
    });
  }, true);
  document.addEventListener('contextmenu', e => {
    const t = e.target;
    if (!t || !t.tagName) return;
    if (t.closest && t.closest('#' + BTN_ID + ', #' + PANEL_ID + ', #' + FULL_ID)) return;
    addLog({
      kind: 'click',
      event: 'contextmenu',
      x: e.clientX, y: e.clientY,
      ...describeElement(t),
    });
  }, true);

  // ─── Capture: scroll milestones (25/50/75/100%) — throttled · 1x per session per milestone ───
  let _scrollMilestones = new Set();
  let _scrollRafQueued = false;
  window.addEventListener('scroll', () => {
    if (_scrollRafQueued) return;
    _scrollRafQueued = true;
    requestAnimationFrame(() => {
      _scrollRafQueued = false;
      const docH = document.documentElement.scrollHeight - window.innerHeight;
      if (docH <= 0) return;
      const pct = Math.round((window.scrollY / docH) * 100);
      const buckets = [25, 50, 75, 100];
      for (const b of buckets) {
        const key = location.pathname + ':' + b;
        if (pct >= b && !_scrollMilestones.has(key)) {
          _scrollMilestones.add(key);
          addLog({ kind: 'scroll', event: 'milestone', percent: b, scrollY: Math.round(window.scrollY), path: location.pathname });
        }
      }
    });
  }, { passive: true });

  // ─── Capture: window resize (debounced 300ms · จับขนาดสุดท้ายเท่านั้น) ───
  let _resizeTimer = null;
  window.addEventListener('resize', () => {
    if (_resizeTimer) clearTimeout(_resizeTimer);
    _resizeTimer = setTimeout(() => {
      addLog({ kind: 'ui', event: 'resize', w: window.innerWidth, h: window.innerHeight });
    }, 300);
  });

  // ─── Capture: toast/alert appearance via MutationObserver (scoped · ไม่ระเบิด) ───
  // จับเฉพาะ container ที่รู้จัก: #toast-container · .modal-overlay (เปิด/ปิด)
  function watchToasts() {
    const targets = [];
    const toastCt = document.getElementById('toast-container');
    if (toastCt) targets.push({ node: toastCt, kind: 'toast' });
    // observe body for modal-overlay class transitions ที่ flip hidden ↔ visible
    if (!targets.length) return;
    targets.forEach(({ node, kind }) => {
      const mo = new MutationObserver(records => {
        for (const r of records) {
          r.addedNodes.forEach(n => {
            if (n.nodeType !== 1) return;
            const txt = (n.innerText || n.textContent || '').trim().slice(0, 200);
            if (!txt) return;
            const cls = (n.className && typeof n.className === 'string') ? n.className : '';
            addLog({
              kind: 'ui',
              event: kind + '-shown',
              classes: cls,
              text: txt,
            });
          });
        }
      });
      mo.observe(node, { childList: true, subtree: false });
    });
  }
  if (document.body) watchToasts();
  else document.addEventListener('DOMContentLoaded', watchToasts, { once: true });

  // ─── Capture: copy/paste/cut (เห็นพฤติกรรม clipboard) ───
  ['copy', 'cut', 'paste'].forEach(evt => {
    document.addEventListener(evt, e => {
      const t = e.target;
      if (!t || !t.tagName) return;
      if (t.closest && t.closest('#' + BTN_ID + ', #' + PANEL_ID + ', #' + FULL_ID)) return;
      addLog({
        kind: 'ui',
        event: evt,
        ...describeElement(t),
      });
    }, true);
  });

  // ────────────────────────────────────────────────────────────
  //  UI LAYER
  // ────────────────────────────────────────────────────────────

  function injectStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = STYLES;
    document.head.appendChild(style);
  }

  const STYLES = `
    /* v10.0.x — P2-9 mobile fix: ปุ่ม dev-logger ขยับขึ้นบนหน้าจอเล็ก
       เพื่อไม่ทับ #toast-container (bottom:20px right:20px z-index 11050) */
    #${BTN_ID} {
      position: fixed; bottom: 18px; right: 18px;
      width: 44px; height: 44px; border-radius: 999px;
      background: #1a1f2e; color: #cbd5e1;
      border: 1px solid #475569;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
      display: flex; align-items: center; justify-content: center;
      cursor: pointer; z-index: 11500;
      font-family: ui-monospace, 'Cascadia Code', Consolas, monospace;
      transition: background 0.15s, border-color 0.15s;
    }
    #${BTN_ID}:hover { background: #232a3d; border-color: #818cf8; color: #e8eaed; }
    #${BTN_ID} .pdb-dev-badge {
      position: absolute; top: -4px; right: -4px;
      min-width: 18px; height: 18px; padding: 0 5px; border-radius: 9px;
      background: #ef4444; color: white; font-size: 10px; font-weight: 700;
      display: flex; align-items: center; justify-content: center;
      font-variant-numeric: tabular-nums; border: 2px solid #0f1419;
    }
    #${BTN_ID} .pdb-dev-badge.hidden { display: none; }

    #${PANEL_ID} {
      position: fixed; bottom: 72px; right: 18px;
      width: min(440px, calc(100vw - 36px));
      height: min(500px, calc(100vh - 120px));
      background: #0f1419; color: #e8eaed;
      border: 1px solid #334155; border-radius: 10px;
      box-shadow: 0 10px 40px rgba(0,0,0,0.6);
      display: flex; flex-direction: column;
      z-index: 11600;
      font-family: ui-monospace, 'Cascadia Code', Consolas, monospace;
      font-size: 11.5px;
    }
    #${PANEL_ID}.hidden { display: none; }
    #${PANEL_ID} .pdb-dev-head {
      display: flex; align-items: center; justify-content: space-between;
      padding: 8px 12px; border-bottom: 1px solid #2d3748;
      background: #151b23; border-radius: 10px 10px 0 0;
    }
    #${PANEL_ID} .pdb-dev-title {
      font-weight: 700; font-size: 11.5px; color: #a5b4fc;
      display: flex; align-items: center; gap: 6px;
    }
    #${PANEL_ID} .pdb-dev-actions { display: flex; gap: 4px; }
    .pdb-dev-btn {
      background: transparent; color: #cbd5e1;
      border: 1px solid #475569; border-radius: 4px;
      padding: 3px 8px; font-size: 11px; cursor: pointer;
      font-family: inherit;
      transition: background 0.12s, border-color 0.12s, color 0.12s;
    }
    .pdb-dev-btn:hover { background: #232a3d; border-color: #818cf8; color: #e8eaed; }
    .pdb-dev-btn.active { background: #6366f1; color: white; border-color: #6366f1; }
    .pdb-dev-btn.danger:hover { border-color: #ef4444; color: #fca5a5; }
    .pdb-dev-btn.armed {
      background: #7f1d1d; color: #fef2f2; border-color: #ef4444; font-weight: 700;
      animation: pdb-dev-pulse 0.8s ease-in-out infinite;
    }
    .pdb-dev-btn.armed:hover { background: #991b1b; }
    @keyframes pdb-dev-pulse {
      0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.6); }
      50% { box-shadow: 0 0 0 4px rgba(239, 68, 68, 0); }
    }
    #${PANEL_ID} .pdb-dev-list {
      flex: 1; overflow-y: auto; padding: 2px 0;
      scrollbar-width: thin; scrollbar-color: #475569 #0f1419;
    }
    #${PANEL_ID} .pdb-dev-list::-webkit-scrollbar { width: 8px; }
    #${PANEL_ID} .pdb-dev-list::-webkit-scrollbar-track { background: #0f1419; }
    #${PANEL_ID} .pdb-dev-list::-webkit-scrollbar-thumb { background: #475569; border-radius: 4px; }
    #${PANEL_ID} .pdb-dev-row {
      padding: 4px 10px; border-bottom: 1px solid #1a1f2e;
      display: grid; grid-template-columns: 68px 58px 1fr; gap: 6px; align-items: start;
      word-break: break-word;
    }
    #${PANEL_ID} .pdb-dev-row:hover { background: #151b23; }
    .pdb-dev-row .t {
      color: #64748b; font-variant-numeric: tabular-nums; font-size: 10.5px;
    }
    .pdb-dev-row .tag {
      font-size: 9.5px; font-weight: 700; text-align: center;
      padding: 1px 4px; border-radius: 3px; line-height: 1.4;
      text-transform: uppercase; letter-spacing: 0.04em;
    }
    .pdb-tag-fetch { background: #1e3a5f; color: #93c5fd; }
    .pdb-tag-log { background: #1f2937; color: #cbd5e1; }
    .pdb-tag-info { background: #0c4a6e; color: #7dd3fc; }
    .pdb-tag-warn { background: #78350f; color: #fbbf24; }
    .pdb-tag-error { background: #7f1d1d; color: #fca5a5; }
    .pdb-tag-debug { background: #1f2937; color: #94a3b8; }
    .pdb-tag-nav { background: #312e81; color: #c4b5fd; }
    .pdb-tag-meta { background: #064e3b; color: #6ee7b7; }
    .pdb-tag-perf { background: #134e4a; color: #5eead4; }
    .pdb-tag-click { background: #1e293b; color: #cbd5e1; }
    .pdb-tag-form { background: #581c87; color: #d8b4fe; }
    .pdb-tag-storage { background: #422006; color: #fcd34d; }
    .pdb-tag-net { background: #831843; color: #f9a8d4; }
    .pdb-tag-vis { background: #1e293b; color: #94a3b8; }
    .pdb-tag-route { background: #4c1d95; color: #ddd6fe; }
    .pdb-tag-focus { background: #14532d; color: #bbf7d0; }
    .pdb-tag-input { background: #134e4a; color: #99f6e4; }
    .pdb-tag-scroll { background: #1e1b4b; color: #c7d2fe; }
    .pdb-tag-ui { background: #3b0764; color: #e9d5ff; }
    .pdb-dev-row .dur.slow { color: #fbbf24; font-weight: 700; }
    .pdb-dev-row .dur.very-slow { color: #fca5a5; font-weight: 700; }
    .pdb-dev-row .msg {
      color: #e8eaed; font-size: 11.5px;
      overflow-wrap: anywhere;
    }
    .pdb-dev-row .msg .status-2xx { color: #86efac; }
    .pdb-dev-row .msg .status-3xx { color: #fde68a; }
    .pdb-dev-row .msg .status-4xx { color: #fca5a5; }
    .pdb-dev-row .msg .status-5xx { color: #fca5a5; font-weight: 700; }
    .pdb-dev-row .msg .url { color: #cbd5e1; }
    .pdb-dev-row .msg .dur { color: #64748b; font-size: 10.5px; }
    #${PANEL_ID} .pdb-dev-empty {
      padding: 24px; text-align: center; color: #64748b;
    }
    #${PANEL_ID} .pdb-dev-hint {
      padding: 6px 12px; font-size: 10px; color: #64748b;
      border-top: 1px solid #2d3748; background: #151b23;
      border-radius: 0 0 10px 10px;
    }
    kbd.pdb-dev-kbd {
      background: #232a3d; color: #cbd5e1;
      padding: 1px 5px; border-radius: 3px;
      font-size: 10px; font-family: inherit;
      border: 1px solid #475569;
    }

    #${FULL_ID} {
      position: fixed; inset: 0;
      background: rgba(15, 20, 25, 0.98);
      z-index: 11700; display: flex; flex-direction: column;
      font-family: ui-monospace, 'Cascadia Code', Consolas, monospace;
      font-size: 12px; color: #e8eaed;
    }
    #${FULL_ID}.hidden { display: none; }
    #${FULL_ID} .pdb-dev-fhead {
      display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
      padding: 10px 16px; border-bottom: 1px solid #2d3748;
      background: #0f1419;
    }
    #${FULL_ID} .pdb-dev-search {
      flex: 1; min-width: 200px;
      background: #1a1f2e; color: #e8eaed;
      border: 1px solid #475569; border-radius: 6px;
      padding: 6px 10px; font-size: 12px;
      font-family: inherit;
    }
    #${FULL_ID} .pdb-dev-search:focus { outline: none; border-color: #818cf8; }
    #${FULL_ID} .pdb-dev-filter { display: flex; gap: 4px; flex-wrap: wrap; }
    #${FULL_ID} .pdb-dev-flist {
      flex: 1; overflow-y: auto; padding: 8px 16px;
    }
    #${FULL_ID} .pdb-dev-frow {
      padding: 8px 12px; margin-bottom: 4px;
      background: #151b23; border-left: 3px solid transparent;
      border-radius: 4px; cursor: pointer;
      display: grid; grid-template-columns: 88px 66px 1fr; gap: 10px; align-items: start;
    }
    #${FULL_ID} .pdb-dev-frow:hover { background: #1a1f2e; }
    #${FULL_ID} .pdb-dev-frow.kind-error { border-left-color: #ef4444; }
    #${FULL_ID} .pdb-dev-frow.kind-fetch-err { border-left-color: #f59e0b; }
    #${FULL_ID} .pdb-dev-frow.kind-fetch-ok { border-left-color: #3b82f6; }
    #${FULL_ID} .pdb-dev-frow.kind-fetch-slow { border-left-color: #fbbf24; background: #1e1a05; }
    #${FULL_ID} .pdb-dev-frow.kind-fetch-very-slow { border-left-color: #ef4444; background: #2a1a1a; }
    #${FULL_ID} .pdb-dev-frow.kind-warn { border-left-color: #f59e0b; }
    #${FULL_ID} .pdb-dev-frow.kind-nav { border-left-color: #8b5cf6; }
    #${FULL_ID} .pdb-dev-frow.kind-meta { border-left-color: #10b981; }
    #${FULL_ID} .pdb-dev-frow.kind-storage { border-left-color: #f59e0b; }
    #${FULL_ID} .pdb-dev-frow.kind-form { border-left-color: #a855f7; }
    #${FULL_ID} .pdb-dev-frow.kind-click { border-left-color: #64748b; }
    #${FULL_ID} .pdb-dev-frow.kind-route { border-left-color: #8b5cf6; background: #1a1730; }
    #${FULL_ID} .pdb-dev-frow.kind-focus { border-left-color: #22c55e; }
    #${FULL_ID} .pdb-dev-frow.kind-scroll { border-left-color: #6366f1; }
    #${FULL_ID} .pdb-dev-frow.kind-ui { border-left-color: #a855f7; }
    #${FULL_ID} .pdb-dev-fdetail {
      grid-column: 1 / -1; margin-top: 8px; padding: 10px;
      background: #0a0e13; border-radius: 4px;
      white-space: pre-wrap; word-break: break-word;
      font-size: 11px; color: #cbd5e1; max-height: 280px; overflow: auto;
      border: 1px solid #1a1f2e;
    }
    #${FULL_ID} .pdb-dev-fdetail .label {
      color: #a5b4fc; font-weight: 700; display: block; margin-top: 6px;
    }
    #${FULL_ID} .pdb-dev-fdetail .label:first-child { margin-top: 0; }
    #${FULL_ID} .pdb-dev-empty {
      padding: 60px 24px; text-align: center; color: #64748b;
    }

    /* v10.0.x — P2-9 fix: ใต้ 500px ขยับปุ่มขึ้น 80px กัน #toast-container overlap (toast: bottom:20px right:20px) */
    @media (max-width: 500px) {
      #${BTN_ID} { bottom: 80px; right: 14px; width: 40px; height: 40px; }
      #${PANEL_ID} { bottom: 130px; right: 14px; width: calc(100vw - 28px); }
    }
  `;

  // ─── DOM builders ───
  function el(tag, props, ...children) {
    const e = document.createElement(tag);
    if (props) {
      for (const k in props) {
        if (k === 'class') e.className = props[k];
        else if (k === 'style') e.style.cssText = props[k];
        else if (k.startsWith('on') && typeof props[k] === 'function') e.addEventListener(k.slice(2), props[k]);
        else if (k === 'html') e.innerHTML = props[k];
        else e.setAttribute(k, props[k]);
      }
    }
    children.flat().forEach(c => {
      if (c == null || c === false) return;
      e.appendChild(typeof c === 'string' ? document.createTextNode(c) : c);
    });
    return e;
  }

  function formatTime(t) {
    const d = new Date(t);
    return `${pad(d.getHours(), 2)}:${pad(d.getMinutes(), 2)}:${pad(d.getSeconds(), 2)}.${pad(d.getMilliseconds(), 3)}`;
  }
  function pad(n, w) { return String(n).padStart(w, '0'); }

  function shortUrl(u) {
    try {
      const url = new URL(u, location.origin);
      if (url.origin === location.origin) return url.pathname + url.search;
      return url.host + url.pathname;
    } catch (_) { return u; }
  }

  function statusClass(s) {
    if (s == null) return '';
    if (s >= 500) return 'status-5xx';
    if (s >= 400) return 'status-4xx';
    if (s >= 300) return 'status-3xx';
    return 'status-2xx';
  }

  // ─── Floating button ───
  function mountButton() {
    if (document.getElementById(BTN_ID)) return;
    const btn = el('button', {
      id: BTN_ID,
      'aria-label': 'PDB Dev Logger',
      title: 'PDB Dev Logger — คลิกเปิด · Ctrl+Shift+L = full view',
      onclick: () => togglePanel(),
    },
      el('span', { html: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>` }),
      el('span', { class: 'pdb-dev-badge hidden' }),
    );
    document.body.appendChild(btn);
    renderBadge();
  }

  function renderBadge() {
    const btn = document.getElementById(BTN_ID);
    if (!btn) return;
    const badge = btn.querySelector('.pdb-dev-badge');
    if (!badge) return;
    if (state.errorCount > 0 && !state.panelOpen) {
      badge.textContent = state.errorCount > 99 ? '99+' : String(state.errorCount);
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }
  }

  // ─── Compact panel ───
  function togglePanel() {
    state.panelOpen = !state.panelOpen;
    if (state.panelOpen) {
      state.errorCount = 0;
      renderPanel();
    } else {
      const p = document.getElementById(PANEL_ID);
      if (p) p.remove();
    }
    renderBadge();
  }

  function renderPanel() {
    let panel = document.getElementById(PANEL_ID);
    if (!panel) {
      panel = el('div', { id: PANEL_ID });
      document.body.appendChild(panel);
    }
    panel.innerHTML = '';

    const head = el('div', { class: 'pdb-dev-head' },
      el('div', { class: 'pdb-dev-title' }, 'PDB Dev', el('span', { style: 'color:#64748b;font-weight:400;font-size:11px;' }, ` · ${state.logs.length}`)),
      el('div', { class: 'pdb-dev-actions' },
        el('button', {
          class: 'pdb-dev-btn' + (state.paused ? ' active' : ''),
          title: state.paused ? 'Resume capture' : 'Pause capture',
          onclick: () => { state.paused = !state.paused; persistState(); renderPanel(); },
        }, state.paused ? '▶' : '⏸'),
        el('button', { class: 'pdb-dev-btn', title: 'Full view (Ctrl+Shift+L)', onclick: () => { openFull(); } }, '⛶'),
        el('button', { class: 'pdb-dev-btn', title: 'Copy all logs as JSON', onclick: copyAll }, 'Copy'),
        el('button', {
          class: 'pdb-dev-btn ' + (_clearArmed ? 'armed' : 'danger'),
          title: _clearArmed ? 'กดอีกครั้งภายใน 3 วินาที เพื่อยืนยันล้าง' : 'Clear all logs',
          onclick: clearAll,
        }, _clearArmed ? 'Sure?' : 'Clear'),
        el('button', { class: 'pdb-dev-btn', title: 'Close', onclick: togglePanel }, '✕'),
      ),
    );
    panel.appendChild(head);

    const list = el('div', { class: 'pdb-dev-list' });
    if (state.logs.length === 0) {
      list.appendChild(el('div', { class: 'pdb-dev-empty' }, 'ยังไม่มี log · ลองโหลดหน้าใหม่หรือทำอะไรในแอป'));
    } else {
      // แสดงล่าสุดอยู่ล่าง · scroll bottom เพื่อเห็นล่าสุดทันที
      const frag = document.createDocumentFragment();
      state.logs.forEach(log => frag.appendChild(renderCompactRow(log)));
      list.appendChild(frag);
    }
    panel.appendChild(list);

    panel.appendChild(el('div', { class: 'pdb-dev-hint' },
      'กด ', el('kbd', { class: 'pdb-dev-kbd' }, 'Ctrl+Shift+L'), ' = full view · ',
      state.paused ? '⏸ paused' : '● capturing',
    ));

    // scroll bottom (เห็นล่าสุดทันที)
    list.scrollTop = list.scrollHeight;
  }

  function renderCompactRow(log) {
    const time = formatTime(log.t);
    const tag = tagFor(log);
    const msg = formatSummary(log, 200);
    return el('div', { class: 'pdb-dev-row' },
      el('div', { class: 't' }, time),
      el('div', { class: 'tag pdb-tag-' + tag }, tag),
      el('div', { class: 'msg', html: msg }),
    );
  }

  function tagFor(log) {
    if (log.kind === 'console') return log.level;
    return log.kind;
  }

  function durClass(ms) {
    if (ms == null) return 'dur';
    if (ms >= VERY_SLOW_FETCH_MS) return 'dur very-slow';
    if (ms >= SLOW_FETCH_MS) return 'dur slow';
    return 'dur';
  }

  function formatSummary(log, maxLen) {
    if (log.kind === 'fetch') {
      const sc = statusClass(log.status);
      const status = log.error
        ? `<span class="status-5xx">ERR</span>`
        : (log.status != null ? `<span class="${sc}">${log.status}</span>` : '<span class="status-3xx">…</span>');
      const dur = log.durationMs != null ? `<span class="${durClass(log.durationMs)}">${log.durationMs}ms</span>` : '';
      return `<span class="url">${escapeHtml(log.method)} ${escapeHtml(shortUrl(log.url))}</span> ${status} ${dur}${log.error ? ' <span class="status-5xx">' + escapeHtml(log.error) + '</span>' : ''}`;
    }
    if (log.kind === 'nav') {
      return `<span class="url">${escapeHtml(log.event)} ${escapeHtml(shortUrl(log.url))}</span>${log.runtimeMs ? ' <span class="dur">' + (log.runtimeMs / 1000).toFixed(1) + 's</span>' : ''}`;
    }
    if (log.kind === 'meta') {
      return `session ${escapeHtml(log.sessionId || '')} · <span class="url">${escapeHtml(log.viewport ? log.viewport.w + '×' + log.viewport.h : '')}</span> · ${log.online ? 'online' : 'offline'} · token=${log.tokenPresent ? '✓' : '✗'}`;
    }
    if (log.kind === 'perf') {
      const fcp = log.firstContentfulPaintMs;
      const load = log.loadEventMs;
      return `<span class="url">FCP=${fcp != null ? fcp + 'ms' : '?'} · load=${load != null ? load + 'ms' : '?'}${log.transferSize ? ' · ' + Math.round(log.transferSize / 1024) + 'kb' : ''}</span>`;
    }
    if (log.kind === 'click') {
      const txt = log.text ? ' "' + log.text.slice(0, 40) + '"' : '';
      const evt = log.event && log.event !== 'click' ? '[' + log.event + '] ' : '';
      return `${escapeHtml(evt)}<span class="url">${escapeHtml(log.selector)}</span>${escapeHtml(txt)}`;
    }
    if (log.kind === 'route') {
      return `<span class="url">${escapeHtml(log.reason)}: ${escapeHtml(shortUrl(log.from))} → ${escapeHtml(shortUrl(log.to))}</span>`;
    }
    if (log.kind === 'focus' || log.kind === 'input') {
      const v = log.value !== undefined ? ' = ' + escapeHtml(String(log.value).slice(0, 60)) : '';
      const txt = log.text ? ' "' + log.text.slice(0, 40) + '"' : '';
      return `<span class="url">[${escapeHtml(log.event)}] ${escapeHtml(log.selector)}</span>${escapeHtml(txt)}${v}`;
    }
    if (log.kind === 'scroll') {
      return `<span class="url">scroll ${log.percent}% on ${escapeHtml(log.path)}</span>`;
    }
    if (log.kind === 'ui') {
      const txt = log.text ? ' "' + escapeHtml(log.text.slice(0, 80)) + '"' : '';
      const dims = (log.w && log.h) ? ` ${log.w}×${log.h}` : '';
      const sel = log.selector ? ' ' + escapeHtml(log.selector) : '';
      return `<span class="url">[${escapeHtml(log.event)}]${dims}${sel}</span>${txt}`;
    }
    if (log.kind === 'form') {
      const fc = log.fields ? Object.keys(log.fields).length : 0;
      return `<span class="url">${escapeHtml(log.method)} ${escapeHtml(log.formId || '(no id)')}</span> ${fc} fields → ${escapeHtml(log.action || '')}`;
    }
    if (log.kind === 'storage') {
      const v = log.newValuePreview != null ? ' = ' + escapeHtml(String(log.newValuePreview).slice(0, 60)) : '';
      return `<span class="url">${escapeHtml(log.area)}.${escapeHtml(log.op)}</span> ${escapeHtml(log.key || '(all)')}${v}`;
    }
    if (log.kind === 'net') return `<span class="url">${escapeHtml(log.event)}</span>`;
    if (log.kind === 'vis') return `<span class="url">visibility = ${escapeHtml(log.event)}</span>`;
    if (log.kind === 'error') {
      return `<span class="status-5xx">${escapeHtml((log.message || '').slice(0, maxLen))}</span>`;
    }
    // console / default
    const text = log.message || '';
    return escapeHtml(text).slice(0, maxLen) + (text.length > maxLen ? '…' : '');
  }

  // ─── Fullscreen viewer ───
  function openFull() {
    state.fullOpen = true;
    renderFull();
  }
  function closeFull() {
    state.fullOpen = false;
    const f = document.getElementById(FULL_ID);
    if (f) f.remove();
  }

  function renderFull() {
    let full = document.getElementById(FULL_ID);
    if (!full) {
      full = el('div', { id: FULL_ID });
      document.body.appendChild(full);
    }
    full.innerHTML = '';

    const filters = [
      { k: 'all', label: 'All' },
      { k: 'fetch', label: 'Fetch' },
      { k: 'console', label: 'Log' },
      { k: 'warn', label: 'Warn' },
      { k: 'error', label: 'Error' },
      { k: 'click', label: 'Click' },
      { k: 'input', label: 'Input' },
      { k: 'form', label: 'Form' },
      { k: 'storage', label: 'Storage' },
      { k: 'route', label: 'Route' },
      { k: 'ui', label: 'UI' },
      { k: 'nav', label: 'Nav' },
      { k: 'meta', label: 'Meta/Perf' },
    ];

    const runtimeMs = Date.now() - SESSION_START;
    const runtimeStr = runtimeMs < 1000 ? runtimeMs + 'ms' : (runtimeMs / 1000).toFixed(1) + 's';
    const head = el('div', { class: 'pdb-dev-fhead' },
      el('div', { class: 'pdb-dev-title', style: 'color:#a5b4fc;font-weight:700;display:flex;flex-direction:column;gap:2px;' },
        el('span', null, 'PDB Dev — Full Log'),
        el('span', { style: 'color:#64748b;font-weight:400;font-size:10.5px;' },
          `${SESSION_ID} · runtime ${runtimeStr} · ${state.logs.length}/${MAX_LOGS} entries${state.paused ? ' · ⏸ paused' : ''}`)
      ),
      el('div', { class: 'pdb-dev-filter' },
        ...filters.map(f => el('button', {
          class: 'pdb-dev-btn' + (state.filter === f.k ? ' active' : ''),
          onclick: () => { state.filter = f.k; persistState(); renderFull(); },
        }, f.label))
      ),
      el('input', {
        class: 'pdb-dev-search',
        type: 'search',
        placeholder: 'ค้นหา (URL, message, status)...',
        value: state.search,
        oninput: e => { state.search = e.target.value; renderFull(); },
      }),
      el('button', {
        class: 'pdb-dev-btn' + (state.paused ? ' active' : ''),
        onclick: () => { state.paused = !state.paused; persistState(); renderFull(); },
      }, state.paused ? '▶ Resume' : '⏸ Pause'),
      el('button', { class: 'pdb-dev-btn', onclick: copyAll }, 'Copy All'),
      el('button', {
        class: 'pdb-dev-btn ' + (_clearArmed ? 'armed' : 'danger'),
        title: _clearArmed ? 'กดอีกครั้งภายใน 3 วินาที เพื่อยืนยันล้าง' : 'Clear all logs',
        onclick: clearAll,
      }, _clearArmed ? 'Sure?' : 'Clear All'),
      el('button', { class: 'pdb-dev-btn', onclick: closeFull, title: 'Close (Esc)' }, '✕ Close'),
    );
    full.appendChild(head);

    const list = el('div', { class: 'pdb-dev-flist' });
    const filtered = state.logs.filter(matchFilter);
    if (filtered.length === 0) {
      list.appendChild(el('div', { class: 'pdb-dev-empty' },
        state.logs.length === 0 ? 'ยังไม่มี log' : 'ไม่พบ log ที่ตรงกับ filter / ค้นหา'
      ));
    } else {
      const frag = document.createDocumentFragment();
      filtered.forEach(log => frag.appendChild(renderFullRow(log)));
      list.appendChild(frag);
    }
    full.appendChild(list);

    list.scrollTop = list.scrollHeight;
  }

  function matchFilter(log) {
    // filter by kind
    const f = state.filter;
    if (f !== 'all') {
      if (f === 'console' && log.kind !== 'console') return false;
      if (f === 'fetch' && log.kind !== 'fetch') return false;
      if (f === 'nav' && log.kind !== 'nav') return false;
      if (f === 'click' && log.kind !== 'click') return false;
      if (f === 'form' && log.kind !== 'form') return false;
      if (f === 'storage' && log.kind !== 'storage') return false;
      if (f === 'route' && log.kind !== 'route') return false;
      if (f === 'input' && !(log.kind === 'input' || log.kind === 'focus')) return false;
      if (f === 'ui' && !(log.kind === 'ui' || log.kind === 'scroll')) return false;
      if (f === 'meta' && !(log.kind === 'meta' || log.kind === 'perf' || log.kind === 'net' || log.kind === 'vis')) return false;
      if (f === 'error' && !(log.kind === 'error' || (log.kind === 'fetch' && (log.status >= 400 || log.error)) || log.level === 'error')) return false;
      if (f === 'warn' && log.level !== 'warn') return false;
    }
    // search
    const s = state.search.trim().toLowerCase();
    if (!s) return true;
    const hay = JSON.stringify(log).toLowerCase();
    return hay.includes(s);
  }

  function renderFullRow(log) {
    let kindCls = '';
    if (log.kind === 'error' || log.level === 'error' || log.level === 'unhandledrejection') kindCls = 'kind-error';
    else if (log.kind === 'fetch') {
      if (log.error || log.status >= 400) kindCls = 'kind-fetch-err';
      else if (log.durationMs != null && log.durationMs >= VERY_SLOW_FETCH_MS) kindCls = 'kind-fetch-very-slow';
      else if (log.durationMs != null && log.durationMs >= SLOW_FETCH_MS) kindCls = 'kind-fetch-slow';
      else kindCls = 'kind-fetch-ok';
    }
    else if (log.level === 'warn') kindCls = 'kind-warn';
    else if (log.kind === 'nav') kindCls = 'kind-nav';
    else if (log.kind === 'meta') kindCls = 'kind-meta';
    else if (log.kind === 'storage') kindCls = 'kind-storage';
    else if (log.kind === 'form') kindCls = 'kind-form';
    else if (log.kind === 'click') kindCls = 'kind-click';
    else if (log.kind === 'route') kindCls = 'kind-route';
    else if (log.kind === 'focus' || log.kind === 'input') kindCls = 'kind-focus';
    else if (log.kind === 'scroll') kindCls = 'kind-scroll';
    else if (log.kind === 'ui') kindCls = 'kind-ui';

    const row = el('div', { class: 'pdb-dev-frow ' + kindCls });
    const tag = tagFor(log);

    row.appendChild(el('div', { class: 't' }, formatTime(log.t)));
    row.appendChild(el('div', { class: 'tag pdb-tag-' + tag }, tag));
    row.appendChild(el('div', { class: 'msg', html: formatSummary(log, 400) }));

    // expand on click
    row.addEventListener('click', () => {
      const existing = row.querySelector('.pdb-dev-fdetail');
      if (existing) { existing.remove(); return; }
      row.appendChild(buildDetail(log));
    });

    return row;
  }

  function buildDetail(log) {
    const d = el('div', { class: 'pdb-dev-fdetail' });
    const lines = [];
    lines.push(`time: ${new Date(log.t).toISOString()}  (+${log.t - SESSION_START}ms from session start)`);
    lines.push(`kind: ${log.kind}` + (log.level ? ` · level: ${log.level}` : ''));
    if (log.kind === 'fetch') {
      lines.push(`method: ${log.method}`);
      lines.push(`url: ${log.url}`);
      if (log.status != null) lines.push(`status: ${log.status} ${log.statusText || ''}`);
      if (log.durationMs != null) {
        let slow = '';
        if (log.durationMs >= VERY_SLOW_FETCH_MS) slow = '  ⚠ VERY SLOW';
        else if (log.durationMs >= SLOW_FETCH_MS) slow = '  ⚠ slow';
        lines.push(`duration: ${log.durationMs}ms${slow}`);
      }
      if (log.reqBodySize != null) lines.push(`req size: ${log.reqBodySize}b`);
      if (log.resBodySize != null) lines.push(`res size: ${log.resBodySize}b`);
      if (log.error) lines.push(`error: ${log.error}`);
      if (log.lastAction) {
        lines.push('');
        lines.push('── last user action before fetch ──');
        lines.push(JSON.stringify(log.lastAction, null, 2));
      }
      if (log.reqHeaders && Object.keys(log.reqHeaders).length) {
        lines.push(''); lines.push('── request headers ──');
        Object.keys(log.reqHeaders).forEach(k => lines.push(`  ${k}: ${log.reqHeaders[k]}`));
      }
      if (log.reqBody) { lines.push(''); lines.push('── request body ──'); lines.push(prettyJsonMaybe(log.reqBody)); }
      if (log.resHeaders && Object.keys(log.resHeaders).length) {
        lines.push(''); lines.push('── response headers ──');
        Object.keys(log.resHeaders).forEach(k => lines.push(`  ${k}: ${log.resHeaders[k]}`));
      }
      if (log.resBody) { lines.push(''); lines.push('── response body ──'); lines.push(prettyJsonMaybe(log.resBody)); }
    } else if (log.kind === 'meta') {
      const keys = ['sessionId', 'url', 'title', 'referrer', 'userAgent', 'language', 'languages',
                    'viewport', 'screen', 'online', 'cookieEnabled', 'platform', 'tokenPresent', 'storageUsed'];
      keys.forEach(k => { if (log[k] !== undefined) lines.push(`${k}: ${JSON.stringify(log[k])}`); });
    } else if (log.kind === 'perf') {
      ['domContentLoadedMs', 'loadEventMs', 'firstPaintMs', 'firstContentfulPaintMs', 'transferSize', 'decodedBodySize']
        .forEach(k => { if (log[k] != null) lines.push(`${k}: ${log[k]}`); });
    } else if (log.kind === 'click') {
      if (log.event && log.event !== 'click') lines.push(`event: ${log.event}`);
      ['selector', 'tag', 'id', 'classes', 'text', 'type', 'name', 'href']
        .forEach(k => { if (log[k] != null) lines.push(`${k}: ${log[k]}`); });
      if (log.x != null || log.y != null) lines.push(`position: (${log.x}, ${log.y})`);
    } else if (log.kind === 'route') {
      lines.push(`reason: ${log.reason}`);
      lines.push(`from: ${log.from}`);
      lines.push(`to: ${log.to}`);
      if (log.pathname) lines.push(`pathname: ${log.pathname}`);
      if (log.search) lines.push(`search: ${log.search}`);
      if (log.hash) lines.push(`hash: ${log.hash}`);
    } else if (log.kind === 'focus' || log.kind === 'input') {
      lines.push(`event: ${log.event}`);
      ['selector', 'tag', 'id', 'classes', 'text', 'type', 'name', 'href']
        .forEach(k => { if (log[k] != null) lines.push(`${k}: ${log[k]}`); });
      if (log.value !== undefined) lines.push(`value: ${log.value}`);
    } else if (log.kind === 'scroll') {
      lines.push(`event: ${log.event}`);
      lines.push(`percent: ${log.percent}%`);
      lines.push(`scrollY: ${log.scrollY}px`);
      lines.push(`path: ${log.path}`);
    } else if (log.kind === 'ui') {
      lines.push(`event: ${log.event}`);
      if (log.w && log.h) lines.push(`size: ${log.w}×${log.h}`);
      if (log.selector) lines.push(`selector: ${log.selector}`);
      if (log.classes) lines.push(`classes: ${log.classes}`);
      if (log.text) lines.push(`text: ${log.text}`);
      if (log.tag) lines.push(`tag: ${log.tag}`);
    } else if (log.kind === 'form') {
      lines.push(`event: ${log.event}`);
      lines.push(`formId: ${log.formId || '(no id)'}`);
      lines.push(`action: ${log.action || ''}`);
      lines.push(`method: ${log.method}`);
      if (log.fields) {
        lines.push(''); lines.push('── form fields (password masked) ──');
        lines.push(JSON.stringify(log.fields, null, 2));
      }
    } else if (log.kind === 'storage') {
      ['area', 'op', 'key', 'prevSize', 'newSize', 'newValuePreview', 'count', 'url']
        .forEach(k => { if (log[k] != null) lines.push(`${k}: ${log[k]}`); });
    } else if (log.kind === 'nav') {
      lines.push(`event: ${log.event}`);
      lines.push(`url: ${log.url}`);
      if (log.title) lines.push(`title: ${log.title}`);
      if (log.runtimeMs != null) lines.push(`runtime: ${log.runtimeMs}ms (${(log.runtimeMs / 1000).toFixed(1)}s)`);
    } else if (log.kind === 'net' || log.kind === 'vis') {
      lines.push(`event: ${log.event}`);
    } else {
      // console / error
      lines.push(''); lines.push(log.message || '');
      if (log.stack) { lines.push(''); lines.push('── stack ──'); lines.push(log.stack); }
    }
    d.textContent = lines.join('\n');
    return d;
  }

  function prettyJsonMaybe(s) {
    try { return JSON.stringify(JSON.parse(s), null, 2); } catch (_) { return s; }
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  }

  // ─── Actions ───
  async function copyAll() {
    const txt = JSON.stringify(state.logs, null, 2);
    try {
      await navigator.clipboard.writeText(txt);
      flash('คัดลอก log แล้ว (' + state.logs.length + ' entries)');
    } catch (_) {
      // fallback: select+copy textarea
      const ta = document.createElement('textarea');
      ta.value = txt;
      ta.style.cssText = 'position:fixed;top:-9999px;';
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand('copy'); flash('คัดลอกแล้ว (fallback)'); } catch (e) { flash('คัดลอกไม่สำเร็จ: ' + e.message); }
      ta.remove();
    }
  }

  // 2-click confirm: ครั้งแรกปุ่มเปลี่ยนเป็น "Sure?" สีแดงเข้ม · กดยืนยันใน 3 วินาที
  // ไม่พึ่ง browser confirm() ที่ user อาจกด Cancel หรือ browser block (เคย report ว่า "Clear ไม่ทำงาน")
  let _clearArmed = false;
  let _clearArmTimer = null;
  function clearAll() {
    if (!_clearArmed) {
      _clearArmed = true;
      if (_clearArmTimer) clearTimeout(_clearArmTimer);
      _clearArmTimer = setTimeout(() => {
        _clearArmed = false;
        _clearArmTimer = null;
        if (state.panelOpen) renderPanel();
        if (state.fullOpen) renderFull();
      }, 3000);
      // re-render เพื่อให้ปุ่ม flip เป็น "Sure?"
      if (state.panelOpen) renderPanel();
      if (state.fullOpen) renderFull();
      return;
    }
    // ยืนยันแล้ว → ล้าง
    _clearArmed = false;
    if (_clearArmTimer) { clearTimeout(_clearArmTimer); _clearArmTimer = null; }
    state.logs = [];
    state.errorCount = 0;
    persistLogs();
    renderBadge();
    if (state.panelOpen) renderPanel();
    if (state.fullOpen) renderFull();
    flash('ล้าง log แล้ว');
  }

  function flash(text) {
    const t = el('div', {
      style: 'position:fixed;bottom:80px;right:18px;background:#1e3a5f;color:#bfdbfe;padding:8px 14px;border-radius:6px;border:1px solid #3b82f6;font-family:ui-monospace,monospace;font-size:12px;z-index:11800;box-shadow:0 4px 12px rgba(0,0,0,0.5);',
    }, text);
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 1800);
  }

  // ─── Keyboard shortcut ───
  document.addEventListener('keydown', e => {
    // Ctrl+Shift+L = open/close full
    if (e.ctrlKey && e.shiftKey && (e.key === 'L' || e.key === 'l')) {
      e.preventDefault();
      if (state.fullOpen) closeFull(); else openFull();
    }
    if (e.key === 'Escape' && state.fullOpen) {
      closeFull();
    }
  });

  // ─── Public API ───
  window.__pdbDevLogger = {
    show: () => { if (!state.panelOpen) togglePanel(); },
    hide: () => { if (state.panelOpen) togglePanel(); },
    full: openFull,
    closeFull,
    clear: clearAll,
    copy: copyAll,
    pause: (v = true) => { state.paused = !!v; persistState(); scheduleRender(); },
    entries: () => state.logs.slice(),
  };

  // ─── Mount UI ───
  function mountUI() {
    if (!document.body) {
      document.addEventListener('DOMContentLoaded', mountUI, { once: true });
      return;
    }
    injectStyles();
    mountButton();
  }
  mountUI();
})();
