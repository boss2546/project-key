const { chromium } = require("playwright");
const path = require("path");
const fs = require("fs");
const URL = process.env.PDB_SANDBOX_URL || "http://localhost:8765/";
const OUT = path.join(__dirname, "snapshots");
if (fs.existsSync(OUT)) fs.rmSync(OUT, { recursive: true, force: true });
fs.mkdirSync(OUT, { recursive: true });

(async () => {
  let browser;
  try { browser = await chromium.launch({ headless: true, channel: "chrome" }); }
  catch { browser = await chromium.launch({ headless: true }); }
  const errs = [];
  const networkErrs = [];
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await ctx.newPage();
  page.on("console", m => { if (m.type() === "error") errs.push(m.text()); });
  page.on("pageerror", e => errs.push("PAGE: " + e.message));
  page.on("response", res => { if (res.status() >= 400 && !res.url().includes(".mp4")) networkErrs.push(`${res.status()} ${res.url()}`); });

  await page.goto(URL, { waitUntil: "load", timeout: 30000 });
  await page.waitForTimeout(2200);

  console.log("[desktop 1440×900]");
  const docH = await page.evaluate(() => document.documentElement.scrollHeight);
  console.log(`  docH=${docH}`);

  const shotAt = async (target, name) => {
    if (target === "top")    await page.evaluate(() => window.scrollTo({ top: 0 }));
    else if (target === "bottom") await page.evaluate(() => window.scrollTo({ top: 99999 }));
    else if (typeof target === "number") await page.evaluate(y => window.scrollTo({ top: y }), target);
    else                     await page.evaluate(s => {
      const el = document.querySelector(s);
      if (el) { const r = el.getBoundingClientRect(); window.scrollTo({ top: window.scrollY + r.top }); }
    }, target);
    await page.waitForTimeout(900);
    await page.screenshot({ path: path.join(OUT, `${name}.png`) });
    console.log(`  ✓ ${name}`);
  };

  await shotAt("top",       "01-hero-stage1");
  await shotAt(900,         "02-hero-stage2");
  await shotAt(1700,        "03-hero-stage3");
  await shotAt(".threshold","04-threshold");
  await shotAt("#story-sort", "05-story-sort");
  await shotAt("#story-recall", "06-story-recall");
  await shotAt("#pricing",  "07-pricing");
  await shotAt("#trust",    "08-trust");
  await shotAt(".cta",      "09-cta");
  await shotAt("bottom",    "10-foot");

  await page.evaluate(() => window.scrollTo({ top: 0 }));
  await page.waitForTimeout(300);
  await page.click("#btn-show-register");  /* topbar — always clickable */
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(OUT, "11-modal.png") });
  console.log("  ✓ 11-modal");
  await ctx.close();

  /* mobile */
  const mctx = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2 });
  const mp = await mctx.newPage();
  mp.on("console", m => { if (m.type() === "error") errs.push("MOBILE: " + m.text()); });
  await mp.goto(URL, { waitUntil: "load", timeout: 30000 });
  await mp.waitForTimeout(1800);
  console.log("[mobile 390×844]");
  for (const [name, sel] of [
    ["m01-hero", null], ["m02-threshold", ".threshold"], ["m03-story-sort", "#story-sort"],
    ["m04-story-recall", "#story-recall"], ["m05-pricing", "#pricing"], ["m06-trust", "#trust"], ["m07-cta", ".cta"],
  ]) {
    if (!sel) await mp.evaluate(() => window.scrollTo({ top: 0 }));
    else await mp.evaluate(s => {
      const el = document.querySelector(s);
      if (el) { const r = el.getBoundingClientRect(); window.scrollTo({ top: window.scrollY + r.top }); }
    }, sel);
    await mp.waitForTimeout(700);
    await mp.screenshot({ path: path.join(OUT, `${name}.png`) });
    console.log(`  ✓ ${name}`);
  }
  await mctx.close();
  await browser.close();

  console.log("\n═══ ERRORS ═══");
  if (errs.length === 0) console.log("  ✓ no console/page errors");
  else errs.forEach(e => console.log(`  🔴 ${e.slice(0, 200)}`));
  console.log("\n═══ NETWORK ═══");
  if (networkErrs.length === 0) console.log("  ✓ no 4xx/5xx (excl. expected mp4 404 placeholders)");
  else networkErrs.forEach(e => console.log(`  🔴 ${e}`));
})();
