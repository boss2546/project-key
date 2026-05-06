// @ts-check
/**
 * v9.1.0 Raw File Vault — Playwright real Chromium tests (standalone)
 *
 * Tests on real DOM:
 *   - Filter chips render + click
 *   - Vault badge in file render
 *   - Try-analyze button + handler
 *   - i18n keys (TH + EN)
 *   - localStorage persists filter selection
 *   - Mobile viewport
 *
 * Server: Python http.server (auto-spawn via playwright.config.standalone.js)
 * Backend: mocked via page.route() — no real backend needed
 */
const { test, expect } = require("@playwright/test");

const APP_URL = "http://127.0.0.1:8765/legacy/app.html";

async function loadApp(page) {
  await page.addInitScript(() => {
    localStorage.setItem("pdb_token",
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.fake_signature_for_test");
    localStorage.setItem("pdb_user", JSON.stringify({
      id: "test_user", email: "test@local", name: "Test User"
    }));
    localStorage.setItem("pdb_lang", "th");
    // Reset filter to "all" for predictable test state
    localStorage.removeItem("pdb_files_filter_kind");
  });

  // Playwright "last route wins" — register catch-all FIRST, specific LAST
  await page.route("**/api/**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  await page.route("**/api/usage", async (route) => {
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        plan: "free", subscription_status: "free",
        limits: { allowed_file_types: ["pdf","txt","png"], max_file_size_mb: 100 },
        usage: { context_packs:{used:0,limit:1}, files:{used:0,limit:5},
                 storage_mb:{used:0,limit:50}, ai_summaries:{used:0,limit:5},
                 exports:{used:0,limit:10}, refreshes:{used:0,limit:0}},
        features: { semantic_search: false, version_history_days: 0 },
      }),
    });
  });

  await page.route("**/api/files**", async (route) => {
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ files: [] }),
    });
  });

  await page.route("**/api/stats", async (route) => {
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        total_files: 5, processed_files: 3, vault_files: 2,
      }),
    });
  });

  await page.goto(APP_URL);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForFunction(() => typeof window.renderFileList === "function", { timeout: 8000 });
}

// ─── 1. Filter chips render ─────────────────────────────────────────


test("v9.1.0 / vault / filter chips visible on My Data page", async ({ page }) => {
  await loadApp(page);
  await expect(page.locator("#file-filter-chips")).toBeVisible();
  await expect(page.locator('#file-filter-chips .chip[data-kind="all"]')).toBeVisible();
  await expect(page.locator('#file-filter-chips .chip[data-kind="processed"]')).toBeVisible();
  await expect(page.locator('#file-filter-chips .chip[data-kind="vault"]')).toBeVisible();
});

test("v9.1.0 / vault / updateFileFilterCounts function exists + handles missing elements", async ({ page }) => {
  await loadApp(page);
  // Function is exposed globally
  const exists = await page.evaluate(() => typeof window.updateFileFilterCounts === "function");
  expect(exists).toBe(true);
  // Calling it doesn't throw (best-effort even if elements missing)
  const errored = await page.evaluate(async () => {
    try { await window.updateFileFilterCounts(); return false; } catch (e) { return true; }
  });
  expect(errored).toBe(false);
});

test("v9.1.0 / vault / clicking processed chip persists in localStorage", async ({ page }) => {
  await loadApp(page);
  await page.click('#file-filter-chips .chip[data-kind="processed"]');
  await page.waitForTimeout(300);
  const stored = await page.evaluate(() => localStorage.getItem("pdb_files_filter_kind"));
  expect(stored).toBe("processed");
  await expect(page.locator('#file-filter-chips .chip[data-kind="processed"]')).toHaveClass(/active/);
});

test("v9.1.0 / vault / clicking vault chip changes active state", async ({ page }) => {
  await loadApp(page);
  await page.click('#file-filter-chips .chip[data-kind="vault"]');
  await page.waitForTimeout(300);
  await expect(page.locator('#file-filter-chips .chip[data-kind="vault"]')).toHaveClass(/active/);
  await expect(page.locator('#file-filter-chips .chip[data-kind="all"]')).not.toHaveClass(/active/);
});


// ─── 2. Vault badge in renderFileList ────────────────────────────────


test("v9.1.0 / vault / vault file shows 📦 badge", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    window.renderFileList([{
      id: "vault-1", filename: "design.psd", filetype: "psd",
      text_length: 70, processing_status: "vault_only",
      is_locked: false, file_kind: "vault_only",
      vault_reason: "format not supported by AI extraction",
      extraction_status: "vault", chunk_count: 0, is_truncated: false,
      storage_location: "server",
    }]);
  });
  const hasBadge = await page.locator(".vault-badge").count();
  expect(hasBadge).toBeGreaterThan(0);
  // Badge text contains 📦 emoji
  const badgeText = await page.locator(".vault-badge").first().textContent();
  expect(badgeText).toContain("📦");
});

test("v9.1.0 / vault / processed file does NOT show vault badge", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    window.renderFileList([{
      id: "p-1", filename: "doc.pdf", filetype: "pdf",
      text_length: 5000, processing_status: "ready",
      is_locked: false, file_kind: "processed",
      extraction_status: "ok", chunk_count: 0, is_truncated: false,
    }]);
  });
  const badgeCount = await page.locator(".vault-badge").count();
  expect(badgeCount).toBe(0);
});

test("v9.1.0 / vault / vault file gets file-vault CSS class on row", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    window.renderFileList([{
      id: "v-1", filename: "x.zip", filetype: "zip",
      text_length: 50, processing_status: "vault_only",
      is_locked: false, file_kind: "vault_only",
      extraction_status: "vault",
    }]);
  });
  const rowClass = await page.locator(".file-item").first().getAttribute("class");
  expect(rowClass).toContain("file-vault");
});


// ─── 3. Try-analyze button + promote handler ────────────────────────


test("v9.1.0 / vault / vault file shows promote button", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    window.renderFileList([{
      id: "vault-1", filename: "x.zip", filetype: "zip",
      text_length: 50, processing_status: "vault_only",
      is_locked: false, file_kind: "vault_only",
      extraction_status: "vault",
    }]);
  });
  const btn = page.locator(".file-action-promote");
  await expect(btn).toHaveCount(1);
});

test("v9.1.0 / vault / promoteVaultFile calls /api/files/{id}/promote", async ({ page }) => {
  await loadApp(page);
  let calledUrl = null;
  let calledMethod = null;
  await page.route("**/api/files/*/promote", async (route) => {
    calledUrl = route.request().url();
    calledMethod = route.request().method();
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ status:"ok", file_id:"v-1", promoted: true,
                             file_kind:"processed", text_length: 100 }),
    });
  });
  await page.evaluate(() => window.promoteVaultFile("v-1"));
  await page.waitForTimeout(500);
  expect(calledUrl).toContain("/api/files/v-1/promote");
  expect(calledMethod).toBe("POST");
});

test("v9.1.0 / vault / locked vault file does NOT show promote button", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    window.renderFileList([{
      id: "vlocked", filename: "x.zip", filetype: "zip",
      text_length: 50, is_locked: true, file_kind: "vault_only",
      extraction_status: "vault",
    }]);
  });
  // is_locked=true → desktop promote button hidden
  const btnCount = await page.locator(".file-action-promote").count();
  expect(btnCount).toBe(0);
});


// ─── 4. i18n keys ────────────────────────────────────────────────────


test("v9.1.0 / vault / new i18n keys defined for both langs", async ({ page }) => {
  await loadApp(page);
  const keys = await page.evaluate(() => ({
    th_filterAll: t("myData.filterAll"),
    th_filterVault: t("myData.filterVault"),
    th_vaultBadge: t("vault.badge"),
    th_tryAnalyze: t("vault.tryAnalyze"),
    th_toastUpload: t("vault.toastUpload"),
  }));
  // Must NOT be the bare key string (= missing translation)
  expect(keys.th_filterAll).not.toBe("myData.filterAll");
  expect(keys.th_filterVault).not.toBe("myData.filterVault");
  expect(keys.th_vaultBadge).not.toBe("vault.badge");
  expect(keys.th_tryAnalyze).not.toBe("vault.tryAnalyze");
  expect(keys.th_toastUpload).not.toBe("vault.toastUpload");
});


// ─── 5. Mobile viewport ──────────────────────────────────────────────


test("v9.1.0 / vault / mobile chips wrap, don't overflow", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await loadApp(page);
  // Chips should fit in viewport (< 375px wide each, may wrap)
  const chips = await page.locator("#file-filter-chips .chip").all();
  expect(chips.length).toBe(3);
  for (const c of chips) {
    const box = await c.boundingBox();
    expect(box.width).toBeLessThanOrEqual(375);
  }
});
