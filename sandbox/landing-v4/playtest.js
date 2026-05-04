/* Comprehensive playtest — interact like a real user, find any visible/functional bug */
const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");

const URL = process.env.PDB_SANDBOX_URL || "http://localhost:8765/";
const OUT = path.join(__dirname, "playtest-snapshots");
if (fs.existsSync(OUT)) fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

const findings = [];
function note(sev, where, what) {
  findings.push({ sev, where, what });
  console.log(`  ${sev} [${where}] ${what}`);
}

(async () => {
  let browser;
  try { browser = await chromium.launch({ headless: true, channel: "chrome" }); }
  catch { browser = await chromium.launch({ headless: true }); }

  const errs = [];
  const networkErrs = [];

  /* ════════════════════════════════════════════════════
     PASS 1 — DESKTOP — SLOW SCROLL JOURNEY
     ════════════════════════════════════════════════════ */
  console.log("\n═══ PASS 1: DESKTOP slow scroll ═══");
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  page.on("pageerror", e => errs.push("PAGE: " + e.message));
  page.on("response", res => { if (res.status() >= 400) networkErrs.push(`${res.status()} ${res.url()}`); });

  await page.goto(URL, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(3500);

  const docH = await page.evaluate(() => document.documentElement.scrollHeight);
  console.log(`docH=${docH}`);

  /* Slow scroll: every 250px snap one frame */
  let i = 0;
  for (let y = 0; y <= docH + 500; y += 250) {
    await page.evaluate(yy => window.scrollTo({ top: yy, behavior: "instant" }), y);
    await page.waitForTimeout(420);
    if (i % 3 === 0) {
      await page.screenshot({ path: path.join(OUT, `desk-${String(y).padStart(5, "0")}.png`) });
    }
    /* Sample state every step */
    const state = await page.evaluate(() => {
      const stages = document.querySelectorAll(".hero-stage");
      const activeStage = Array.from(stages).findIndex(s => s.classList.contains("is-active")) + 1;
      const bar = document.querySelector(".bar");
      const sortText = document.querySelector("#story-sort .story-text");
      const recallText = document.querySelector("#story-recall .story-text");
      return {
        activeStage,
        barLight: bar?.classList.contains("is-light"),
        sortVisible: sortText?.classList.contains("is-visible"),
        recallVisible: recallText?.classList.contains("is-visible"),
      };
    });
    /* Stage check removed — v4 is now flat-layout, no stages */
    i++;
  }
  console.log(`captured ${Math.ceil(docH / 750)} desktop scroll snapshots`);

  /* ── 1.5 Layout overlap / gap check ── */
  await page.evaluate(() => window.scrollTo({ top: 0 }));
  await page.waitForTimeout(400);
  const sections = await page.evaluate(() => {
    const sels = ["#hero", ".threshold", "#story-sort", "#story-recall", "#pricing", "#trust", ".cta", ".foot"];
    return sels.map(s => {
      const el = document.querySelector(s);
      if (!el) return { sel: s, missing: true };
      const r = el.getBoundingClientRect();
      return {
        sel: s,
        top: Math.round(window.scrollY + r.top),
        height: Math.round(r.height),
        bottom: Math.round(window.scrollY + r.bottom),
      };
    });
  });
  console.log("\n→ section layout:");
  console.table(sections);
  for (let j = 0; j < sections.length - 1; j++) {
    const a = sections[j];
    const b = sections[j + 1];
    if (a.missing || b.missing) continue;
    const gap = b.top - a.bottom;
    if (gap > 100) note("🟡", "layout-gap", `${a.sel}→${b.sel} gap=${gap}px`);
    if (gap < -10) note("🟠", "layout-overlap", `${a.sel} overlaps ${b.sel} by ${-gap}px`);
  }

  /* ── 1.6 Horizontal overflow check ── */
  const overflow = await page.evaluate(() => {
    const all = document.querySelectorAll("*");
    const out = [];
    for (const el of all) {
      const r = el.getBoundingClientRect();
      if (r.right > window.innerWidth + 1 && r.width > 100) {
        out.push({
          tag: el.tagName + (el.id ? "#" + el.id : "") + (el.className?.toString ? "." + el.className.toString().split(" ")[0] : ""),
          right: Math.round(r.right),
          vw: window.innerWidth,
        });
      }
    }
    return out.slice(0, 5);
  });
  if (overflow.length === 0) console.log("\n→ no horizontal overflow ✓");
  else overflow.forEach((e, i) => note("🟠", "h-overflow", `${e.tag} right=${e.right} > vw=${e.vw}`));

  /* ── 1.7 Hover tests ── */
  console.log("\n→ hover tests");
  const hoverables = ["#btn-show-register", ".price-card-featured", ".exec-card-featured"];
  for (const sel of hoverables) {
    const exists = await page.locator(sel).count();
    if (!exists) { note("🟠", "missing-hover-target", sel); continue; }
    try {
      await page.hover(sel);
      await page.waitForTimeout(300);
    } catch (e) { note("🟠", "hover-failed", `${sel}: ${e.message.slice(0, 80)}`); }
  }
  await page.evaluate(() => window.scrollTo({ top: 0 }));
  await page.waitForTimeout(300);

  /* ── 1.8 Auth modal full flow ── */
  console.log("\n→ auth modal flow");
  await page.click("#btn-show-register");
  await page.waitForTimeout(400);
  let modal = await page.evaluate(() => !document.getElementById("auth-modal").classList.contains("hidden"));
  if (!modal) note("🔴", "auth-open", "Modal didn't open");

  await page.click("#switch-to-login");
  await page.waitForTimeout(300);
  let login = await page.evaluate(() => !document.getElementById("login-form").classList.contains("hidden"));
  if (!login) note("🔴", "auth-switch-login", "switch-to-login failed");

  await page.click("#switch-to-forgot");
  await page.waitForTimeout(300);
  let forgot = await page.evaluate(() => !document.getElementById("forgot-form").classList.contains("hidden"));
  if (!forgot) note("🔴", "auth-switch-forgot", "switch-to-forgot failed");
  /* Try empty submit */
  await page.click("#btn-forgot-submit");
  await page.waitForTimeout(300);
  let errVisible = await page.evaluate(() => !document.getElementById("forgot-error").classList.contains("hidden"));
  if (!errVisible) note("🟠", "auth-empty-validation", "Empty email submit didn't show error");

  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);
  let closed = await page.evaluate(() => document.getElementById("auth-modal").classList.contains("hidden"));
  if (!closed) note("🔴", "auth-esc-close", "ESC didn't close modal");

  /* Backdrop click test */
  await page.click("#btn-show-register");
  await page.waitForTimeout(300);
  await page.mouse.click(20, 200);  /* outside modal-card */
  await page.waitForTimeout(300);
  closed = await page.evaluate(() => document.getElementById("auth-modal").classList.contains("hidden"));
  if (!closed) note("🟠", "auth-backdrop-close", "Backdrop click didn't close");

  /* ── 1.9 Pricing button → modal opens with register form ── */
  await page.evaluate(() => document.querySelector("#pricing")?.scrollIntoView({ block: "start" }));
  await page.waitForTimeout(600);
  await page.click("#btn-pricing-starter");
  await page.waitForTimeout(400);
  const starterModal = await page.evaluate(() => {
    const m = document.getElementById("auth-modal");
    const reg = document.getElementById("register-form");
    return m && !m.classList.contains("hidden") && reg && !reg.classList.contains("hidden");
  });
  if (!starterModal) note("🔴", "pricing-starter-modal", "btn-pricing-starter didn't open register modal");
  await page.keyboard.press("Escape");
  await ctx.close();

  /* ════════════════════════════════════════════════════
     PASS 2 — MOBILE 390×844
     ════════════════════════════════════════════════════ */
  console.log("\n═══ PASS 2: MOBILE 390×844 ═══");
  const mctx = await browser.newContext({
    viewport: { width: 390, height: 844 }, deviceScaleFactor: 2,
    userAgent: "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15"
  });
  const mp = await mctx.newPage();
  mp.on("console", m => { if (m.type() === "error") errs.push("M: " + m.text()); });
  mp.on("pageerror", e => errs.push("M PAGE: " + e.message));
  await mp.goto(URL, { waitUntil: "load", timeout: 30000 });
  await mp.waitForTimeout(3000);

  /* mobile slow scroll */
  const mDocH = await mp.evaluate(() => document.documentElement.scrollHeight);
  console.log(`mobile docH=${mDocH}`);
  for (let y = 0; y <= mDocH; y += 600) {
    await mp.evaluate(yy => window.scrollTo({ top: yy, behavior: "instant" }), y);
    await mp.waitForTimeout(400);
    await mp.screenshot({ path: path.join(OUT, `mob-${String(y).padStart(5, "0")}.png`) });
  }

  /* mobile h-overflow */
  const mOverflow = await mp.evaluate(() => {
    const all = document.querySelectorAll("*");
    const out = [];
    for (const el of all) {
      const r = el.getBoundingClientRect();
      if (r.right > window.innerWidth + 1 && r.width > 80) {
        out.push({
          tag: el.tagName + (el.id ? "#" + el.id : ""),
          right: Math.round(r.right),
          vw: window.innerWidth,
        });
      }
    }
    return out.slice(0, 5);
  });
  if (mOverflow.length) mOverflow.forEach(e => note("🟠", "mobile-overflow", `${e.tag} right=${e.right} > ${e.vw}`));
  else console.log("\n→ mobile: no horizontal overflow ✓");

  /* mobile auth modal */
  await mp.evaluate(() => window.scrollTo({ top: 0 }));
  await mp.waitForTimeout(300);
  await mp.click("#btn-show-register");
  await mp.waitForTimeout(400);
  const mModal = await mp.evaluate(() => !document.getElementById("auth-modal").classList.contains("hidden"));
  if (!mModal) note("🔴", "mobile-modal", "Modal didn't open on mobile");
  else console.log("\n→ mobile modal opens ✓");

  await mctx.close();

  /* ════════════════════════════════════════════════════
     PASS 3 — RAPID RESIZE
     ════════════════════════════════════════════════════ */
  console.log("\n═══ PASS 3: RAPID RESIZE ═══");
  const rctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const rp = await rctx.newPage();
  rp.on("pageerror", e => errs.push("R PAGE: " + e.message));
  await rp.goto(URL, { waitUntil: "load", timeout: 30000 });
  await rp.waitForTimeout(2500);
  for (const w of [1920, 1024, 768, 480, 375, 1440]) {
    await rp.setViewportSize({ width: w, height: 800 });
    await rp.waitForTimeout(700);
    await rp.screenshot({ path: path.join(OUT, `resize-${w}.png`) });
    console.log(`  resized to ${w}px`);
  }
  await rctx.close();
  await browser.close();

  /* ════════════════════════════════════════════════════
     REPORT
     ════════════════════════════════════════════════════ */
  console.log("\n═══ ERRORS DURING PLAY ═══");
  if (errs.length === 0) console.log("  ✓ no js errors");
  else errs.forEach(e => console.log("  🔴 " + e.slice(0, 200)));

  console.log("\n═══ NETWORK FAILURES ═══");
  if (networkErrs.length === 0) console.log("  ✓ no 4xx/5xx");
  else networkErrs.forEach(e => console.log("  🔴 " + e));

  console.log("\n═══ FUNCTIONAL FINDINGS ═══");
  console.log(`Total: ${findings.length}`);
  const sevCounts = findings.reduce((a, f) => { a[f.sev] = (a[f.sev] || 0) + 1; return a; }, {});
  Object.entries(sevCounts).forEach(([k, n]) => console.log(`  ${k} × ${n}`));

  fs.writeFileSync(
    path.join(OUT, "report.md"),
    `# Playtest report\n\n## Errors\n${errs.map(e => "- " + e).join("\n") || "(none)"}\n\n## Network\n${networkErrs.map(e => "- " + e).join("\n") || "(none)"}\n\n## Findings\n${findings.map(f => `- ${f.sev} **${f.where}** — ${f.what}`).join("\n") || "(none)"}\n`
  );
  console.log(`\nReport: ${OUT}/report.md`);
})();
