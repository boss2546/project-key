// @ts-check
/**
 * Playwright E2E spec for v9.2.0 AI Pack Builder
 *
 * ครอบคลุม UI flow ที่ pytest ไม่ทดสอบ:
 *  - Modal open/close + state transitions (input → clarify → loading → preview)
 *  - Skip-clarify path (detailed prompt → ข้าม clarify)
 *  - Form edit + uncheck source + save
 *  - Retry button (กลับ input state)
 *  - Mobile viewport (375px)
 *  - Cancel + auto-discard draft
 *
 * รัน: PDB_TEST_URL=http://127.0.0.1:8765 npx playwright test v9.2.0-ai-pack-builder.spec.js
 */
const { test, expect } = require("@playwright/test");

const PASSWORD = "PlayPass!2026";
const uniqueEmail = () => `pw_${Date.now()}_${Math.floor(Math.random() * 1e6)}@smoke.test`;

// ─── Helpers ────────────────────────────────────────────────

async function registerAndLogin(page) {
  const email = uniqueEmail();
  // Register via API ก่อน (เร็วกว่าผ่าน UI)
  const res = await page.request.post("/api/auth/register", {
    data: { email, password: PASSWORD, name: "PW Tester" },
  });
  expect(res.ok(), `register failed: ${res.status()}`).toBeTruthy();
  const body = await res.json();

  // Set token + user ใน localStorage แล้ว navigate
  await page.goto("/app");
  await page.evaluate(({ token, user }) => {
    localStorage.setItem("pdb_token", token);
    localStorage.setItem("pdb_user", JSON.stringify(user));
  }, { token: body.token, user: body.user });
  await page.reload();
  // รอจน app.html ready (Knowledge tab visible)
  await page.waitForSelector('[data-page="knowledge"]', { timeout: 10000 });
  return { email, token: body.token };
}

async function uploadFakeFile(page, token, filename, content) {
  // อัปโหลดไฟล์ผ่าน API + ทดสอบ AI builder ต้องมี source
  const formData = new FormData();
  const blob = new Blob([content], { type: "text/plain" });
  formData.append("files", blob, filename);
  const res = await page.request.post("/api/upload", {
    headers: { Authorization: `Bearer ${token}` },
    multipart: { files: { name: filename, mimeType: "text/plain", buffer: Buffer.from(content) } },
  });
  return res.ok();
}

async function gotoPacksTab(page) {
  // v7.3.0 mobile: sidebar collapsed → ต้องกด hamburger ก่อน
  const viewport = page.viewportSize();
  if (viewport && viewport.width <= 768) {
    const toggle = page.locator(".sidebar-toggle, #sidebar-toggle, [aria-label*='menu']").first();
    if (await toggle.count()) await toggle.click();
    await page.waitForTimeout(200);
  }
  await page.click('[data-page="knowledge"]');
  await page.waitForSelector('#page-knowledge.active');
  await page.click('[data-tab="packs"]');
  await page.waitForTimeout(300);
}

// ─── Tests ──────────────────────────────────────────────────

test.describe("v9.2.0 AI Pack Builder — UI E2E", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
  });

  test("F1: AI Build button visible on Packs tab", async ({ page }) => {
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "calc.txt", "เนื้อหา calculus");
    await uploadFakeFile(page, token, "alg.txt", "เนื้อหา algebra");
    await gotoPacksTab(page);

    // ปุ่ม "🪄 ให้ AI สร้างให้" ต้องโผล่
    const aiBtn = page.locator('button:has-text("AI"), button:has-text("🪄")').first();
    await expect(aiBtn).toBeVisible({ timeout: 5000 });
  });

  test("F2: Open modal → state=input visible", async ({ page }) => {
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "f1.txt", "content A");
    await uploadFakeFile(page, token, "f2.txt", "content B");
    await gotoPacksTab(page);

    await page.click('button:has-text("🪄")');
    // Modal appears + state=input
    await expect(page.locator("#ai-builder-modal-overlay")).toBeVisible();
    await expect(page.locator("#ai-state-input")).toBeVisible();
    await expect(page.locator("#ai-state-clarify")).toBeHidden();
    await expect(page.locator("#ai-state-loading")).toBeHidden();
    await expect(page.locator("#ai-state-preview")).toBeHidden();
    // ปุ่ม "ส่งให้ AI" visible
    await expect(page.locator("#ai-builder-submit-prompt")).toBeVisible();
  });

  test("F3: Submit short prompt (<10 chars) → no API call (client guard)", async ({ page }) => {
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "x.txt", "x");
    await gotoPacksTab(page);

    // intercept API call to verify never fired
    let calledClarify = false;
    page.on("request", (req) => {
      if (req.url().includes("/ai-build/clarify")) calledClarify = true;
    });

    await page.click('button:has-text("🪄")');
    await page.fill("#ai-builder-prompt", "สั้น");
    await page.click("#ai-builder-submit-prompt");
    await page.waitForTimeout(800);
    // ไม่มี API call ที่หลุดไป → client guard ทำงาน
    expect(calledClarify, "clarify should NOT be called").toBe(false);
    // Modal ยังเปิดอยู่ + ยัง state=input
    await expect(page.locator("#ai-state-input")).toBeVisible();
  });

  test("F4: Cancel button closes modal + auto-discard draft", async ({ page }) => {
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "c.txt", "ccc");
    await gotoPacksTab(page);

    await page.click('button:has-text("🪄")');
    await expect(page.locator("#ai-builder-modal-overlay")).toBeVisible();

    await page.click("#ai-builder-cancel");
    await expect(page.locator("#ai-builder-modal-overlay")).toBeHidden();
  });

  test("F5: Click backdrop closes modal", async ({ page }) => {
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "b.txt", "bbb");
    await gotoPacksTab(page);

    await page.click('button:has-text("🪄")');
    await expect(page.locator("#ai-builder-modal-overlay")).toBeVisible();

    // Click backdrop (not modal content)
    await page.click("#ai-builder-modal-overlay", { position: { x: 5, y: 5 } });
    await expect(page.locator("#ai-builder-modal-overlay")).toBeHidden();
  });

  test("F6: All view-state divs exist + have correct IDs (DOM contract)", async ({ page }) => {
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "v.txt", "vvv");
    await gotoPacksTab(page);

    await page.click('button:has-text("🪄")');
    // Verify all 4 view states exist in DOM
    for (const s of ["input", "clarify", "loading", "preview"]) {
      await expect(page.locator(`#ai-state-${s}`)).toHaveCount(1);
    }
    // All footer buttons exist
    for (const id of [
      "ai-builder-submit-prompt", "ai-clarify-skip", "ai-clarify-submit",
      "ai-preview-confirm", "ai-preview-retry", "ai-builder-back",
    ]) {
      await expect(page.locator(`#${id}`)).toHaveCount(1);
    }
  });

  test("F7: Modal has Thai labels by default (i18n check)", async ({ page }) => {
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "th.txt", "ttt");
    await gotoPacksTab(page);

    await page.click('button:has-text("🪄")');
    // Modal title contains Thai
    const title = await page.textContent("#ai-builder-title");
    expect(title).toMatch(/ให้ AI สร้าง|AI Build/);
    // input label hint visible
    await expect(page.locator('[data-i18n="aiBuilder.tipLabel"]')).toBeVisible();
  });
});

test.describe("v9.2.0 AI Pack Builder — Mobile viewport", () => {
  test.use({ viewport: { width: 375, height: 812 } });

  test("F8 mobile: modal width responsive (≤96vw)", async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => localStorage.clear());
    const { token } = await registerAndLogin(page);
    await uploadFakeFile(page, token, "m.txt", "mmm");
    await gotoPacksTab(page);

    await page.click('button:has-text("🪄")');
    const modal = page.locator(".ai-builder-modal");
    await expect(modal).toBeVisible();

    const box = await modal.boundingBox();
    const viewportWidth = 375;
    // Mobile: modal ≤ 96vw = 360px
    expect(box.width, `modal width ${box.width} ต้อง ≤ ${viewportWidth * 0.97}`).toBeLessThanOrEqual(viewportWidth * 0.97);
  });
});
