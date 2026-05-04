/* Final bug-hunt for landing-v4 — verify ScrollTrigger health, all videos load, no errors */
const { chromium } = require("playwright");

const URL = process.env.PDB_SANDBOX_URL || "http://localhost:8765/";

(async () => {
  let browser;
  try { browser = await chromium.launch({ headless: true, channel: "chrome" }); }
  catch { browser = await chromium.launch({ headless: true }); }

  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();

  const errs = [];
  const networkErrs = [];
  page.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  page.on("pageerror", e => errs.push("PAGE: " + e.message));
  page.on("response", res => { if (res.status() >= 400) networkErrs.push(`${res.status()} ${res.url()}`); });

  await page.goto(URL, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(3000);  /* wait for videos to load metadata */

  console.log("\n═══ 1. RUNTIME ═══");
  if (errs.length === 0) console.log("  ✓ No console/page errors");
  else errs.forEach(e => console.log(`  🔴 ${e.slice(0, 150)}`));

  console.log("\n═══ 2. NETWORK ═══");
  if (networkErrs.length === 0) console.log("  ✓ All requests OK");
  else networkErrs.forEach(e => console.log(`  🔴 ${e}`));

  console.log("\n═══ 3. CDN DEPS ═══");
  const deps = await page.evaluate(() => ({
    gsap: !!window.gsap,
    ScrollTrigger: !!window.ScrollTrigger,
  }));
  Object.entries(deps).forEach(([k, v]) => console.log(`  ${v ? "✓" : "🔴"} ${k}`));

  console.log("\n═══ 4. VIDEOS ═══");
  const videos = await page.evaluate(() => {
    const vs = document.querySelectorAll("video");
    return Array.from(vs).map(v => ({
      id: v.id,
      src: v.src,
      duration: v.duration,
      readyState: v.readyState,
      videoW: v.videoWidth,
      videoH: v.videoHeight,
    }));
  });
  videos.forEach(v => {
    const ok = v.duration && !isNaN(v.duration) && v.videoW > 0;
    console.log(`  ${ok ? "✓" : "🔴"} ${v.id}: ${v.duration?.toFixed(2)}s · ${v.videoW}×${v.videoH}`);
  });

  console.log("\n═══ 5. SCROLLTRIGGER instances ═══");
  const triggers = await page.evaluate(() => {
    if (!window.ScrollTrigger) return null;
    return ScrollTrigger.getAll().map(t => ({
      tagId: (t.trigger?.id || t.trigger?.tagName || "?").toString(),
      start: t.start,
      end: t.end,
    }));
  });
  if (!triggers) console.log("  🔴 ScrollTrigger.getAll() null");
  else {
    console.log(`  ✓ ${triggers.length} active triggers`);
    triggers.slice(0, 6).forEach((t, i) => console.log(`    ${i + 1}. ${t.tagId}  start=${t.start}  end=${t.end}`));
  }

  console.log("\n═══ 6. SCROLL JOURNEY (test stage transitions) ═══");
  const totalH = await page.evaluate(() => document.documentElement.scrollHeight);
  console.log(`  docH=${totalH}`);
  for (const y of [0, 600, 1200, 1800, 2400, 3000, 4000, 5000, 6000]) {
    if (y > totalH) break;
    await page.evaluate(yy => window.scrollTo({ top: yy, behavior: "instant" }), y);
    await page.waitForTimeout(500);
    const state = await page.evaluate(() => {
      const stages = document.querySelectorAll(".hero-stage");
      const activeIdx = Array.from(stages).findIndex(s => s.classList.contains("is-active"));
      const heroVid = document.getElementById("hero-video");
      const sortVid = document.getElementById("story-sort-video");
      const recallVid = document.getElementById("story-recall-video");
      const barLight = document.querySelector(".bar")?.classList.contains("is-light");
      return {
        activeStage: activeIdx + 1,
        heroT: heroVid?.currentTime?.toFixed(2),
        sortT: sortVid?.currentTime?.toFixed(2),
        recallT: recallVid?.currentTime?.toFixed(2),
        barLight,
      };
    });
    console.log(`  scroll ${String(y).padStart(4)}px → stage=${state.activeStage} heroT=${state.heroT}s sortT=${state.sortT}s recallT=${state.recallT}s barLight=${state.barLight}`);
  }

  console.log("\n═══ 7. AUTH MODAL ═══");
  await page.evaluate(() => window.scrollTo({ top: 0 }));
  await page.waitForTimeout(300);
  await page.click("#btn-show-register");
  await page.waitForTimeout(400);
  const opened = await page.evaluate(() => !document.getElementById("auth-modal").classList.contains("hidden"));
  console.log(`  ${opened ? "✓" : "🔴"} Modal opens via #btn-show-register`);
  await page.click("#switch-to-login");
  await page.waitForTimeout(300);
  const loginShown = await page.evaluate(() => !document.getElementById("login-form").classList.contains("hidden"));
  console.log(`  ${loginShown ? "✓" : "🔴"} switch-to-login works`);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(300);
  const closed = await page.evaluate(() => document.getElementById("auth-modal").classList.contains("hidden"));
  console.log(`  ${closed ? "✓" : "🔴"} ESC closes`);

  console.log("\n═══ 8. MOBILE 375×667 ═══");
  await page.setViewportSize({ width: 375, height: 667 });
  await page.evaluate(() => window.scrollTo({ top: 0 }));
  await page.waitForTimeout(800);
  const mHero = await page.evaluate(() => {
    const t = document.querySelector(".hero-h1");
    if (!t) return null;
    const r = t.getBoundingClientRect();
    return { w: r.width, vw: window.innerWidth };
  });
  console.log(`  Hero h1: ${mHero?.w}px in ${mHero?.vw}px viewport ${mHero?.w <= mHero?.vw ? "✓" : "🔴 overflow"}`);

  await ctx.close();
  await browser.close();

  console.log("\n═══ FINAL ═══");
  console.log(`Total errors: ${errs.length}, network: ${networkErrs.length}`);
})();
