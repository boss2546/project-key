// @ts-check
/**
 * v7.5.0 — Standalone Playwright suite (no server required)
 *
 * Loads app.html via file:// + mocks all backend calls.
 * Tests the REAL frontend code path (showUploadResultModal, file render
 * with extraction badges, retry button) — just without a running server.
 *
 * Run: npx playwright test tests/e2e-ui/v7.5.0-standalone.spec.js
 *
 * Why standalone (vs the regular spec): sandbox here blocks port binding,
 * so we test the JS/DOM directly. In CI / dev with a real uvicorn, the
 * regular spec (v7.5.0-upload-resilience.spec.js) covers the full HTTP
 * round-trip.
 */
const { test, expect } = require("@playwright/test");

// App served by playwright.config.standalone.js webServer (Python http.server)
// at http://127.0.0.1:8765/legacy/app.html
const APP_URL = "http://127.0.0.1:8765/legacy/app.html";

// Set fake auth in localStorage BEFORE the page loads, so app.js boots
// into the authed app view instead of the landing page.
async function loadApp(page) {
  await page.addInitScript(() => {
    localStorage.setItem(
      "pdb_token",
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0.fake_signature_for_test"
    );
    localStorage.setItem("pdb_user", JSON.stringify({
      id: "test_user", email: "test@local", name: "Test User"
    }));
    localStorage.setItem("pdb_lang", "th");
  });

  // Mock all API routes (no real backend needed for these tests)
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    if (url.includes("/api/usage")) {
      return route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({
          plan: "free",
          subscription_status: "free",
          limits: { allowed_file_types: ["pdf","txt","png","xlsx"], max_file_size_mb: 200 },
          usage: { context_packs: { used:0, limit:1 }, files: { used:0, limit:5 },
                   storage_mb: { used:0, limit:50 }, ai_summaries: { used:0, limit:5 },
                   exports: { used:0, limit:10 }, refreshes: { used:0, limit:0 }},
          features: { semantic_search: false, version_history_days: 0 },
        }),
      });
    }
    if (url.includes("/api/files") && route.request().method() === "GET") {
      return route.fulfill({
        status: 200, contentType: "application/json",
        body: JSON.stringify({ files: [] }),
      });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });

  await page.goto(APP_URL);
  await page.waitForLoadState("domcontentloaded");
  await page.waitForFunction(() => typeof window.showUploadResultModal === "function", { timeout: 8000 });
}

// ─── 1. showUploadResultModal contract ──────────────────────────────


test("v7.5.0 / standalone / showUploadResultModal exists as window function", async ({ page }) => {
  await loadApp(page);
  const exists = await page.evaluate(() => typeof window.showUploadResultModal === "function");
  expect(exists).toBe(true);
});

test("v7.5.0 / standalone / modal renders with success + per-file skip", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal(
      [{ id: "u1", filename: "ok.txt", filetype: "txt" }],
      [{
        filename: "huge.pdf",
        code: "FILE_TOO_LARGE",
        message: "ไฟล์ใหญ่เกิน 100MB",
        suggestion: "บีบอัดด้วย Smallpdf",
        reason: "ไฟล์ใหญ่เกิน 100MB",
      }]
    );
  });
  await expect(page.locator("#upload-result-modal-overlay")).toBeVisible();
  await expect(page.locator(".upload-result-skip-card")).toContainText("huge.pdf");
  await expect(page.locator(".upload-result-skip-card")).toContainText("100MB");
  await expect(page.locator(".upload-result-skip-card")).toContainText("Smallpdf");
  // Has data-skip-code attribute
  await expect(page.locator(".upload-result-skip-card")).toHaveAttribute("data-skip-code", "FILE_TOO_LARGE");
  // Success summary
  await expect(page.locator(".upload-result-success-text")).toContainText("1");
});

test("v7.5.0 / standalone / each skip code renders correct icon", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal([], [
      { filename: "a.xyz", code: "UNSUPPORTED_TYPE", message: "x", suggestion: "y", reason: "x" },
      { filename: "b.txt", code: "EMPTY_FILE", message: "x", suggestion: "y", reason: "x" },
      { filename: "c.pdf", code: "FILE_TOO_LARGE", message: "x", suggestion: "y", reason: "x" },
    ]);
  });
  await expect(page.locator('.upload-result-skip-card[data-skip-code="UNSUPPORTED_TYPE"]')).toContainText("📄");
  await expect(page.locator('.upload-result-skip-card[data-skip-code="EMPTY_FILE"]')).toContainText("📭");
  await expect(page.locator('.upload-result-skip-card[data-skip-code="FILE_TOO_LARGE"]')).toContainText("📦");
});

test("v7.5.0 / standalone / suggestion shown with label", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal([], [{
      filename: "x.xyz", code: "UNSUPPORTED_TYPE",
      message: "ไฟล์ .xyz ยังไม่รองรับ",
      suggestion: "ลองบันทึกเป็น PDF",
      reason: "ไฟล์ .xyz ยังไม่รองรับ",
    }]);
  });
  const card = page.locator(".upload-result-skip-card");
  await expect(card.locator(".upload-result-skip-suggestion")).toContainText("ลองบันทึกเป็น PDF");
  await expect(card.locator(".upload-result-skip-suggestion strong")).toBeVisible();
});

test("v7.5.0 / standalone / close button dismisses", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal([], [{
      filename: "x.xyz", code: "UNSUPPORTED_TYPE",
      message: "test", suggestion: "test", reason: "test",
    }]);
  });
  await expect(page.locator("#upload-result-modal-overlay")).toBeVisible();
  await page.click("#upload-result-close-btn");
  await expect(page.locator("#upload-result-modal-overlay")).toBeHidden();
});

test("v7.5.0 / standalone / ESC dismisses (v7.2.0 modal pattern)", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal([], [{
      filename: "x.xyz", code: "UNSUPPORTED_TYPE",
      message: "test", suggestion: "test", reason: "test",
    }]);
  });
  await expect(page.locator("#upload-result-modal-overlay")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(page.locator("#upload-result-modal-overlay")).toBeHidden();
});

test("v7.5.0 / standalone / backdrop click dismisses", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal([], [{
      filename: "x.xyz", code: "UNSUPPORTED_TYPE",
      message: "test", suggestion: "test", reason: "test",
    }]);
  });
  await expect(page.locator("#upload-result-modal-overlay")).toBeVisible();
  // Click on overlay corner (not on inner modal)
  await page.locator("#upload-result-modal-overlay").click({ position: { x: 5, y: 5 } });
  await expect(page.locator("#upload-result-modal-overlay")).toBeHidden();
});

test("v7.5.0 / standalone / many skips scroll within modal body", async ({ page }) => {
  await loadApp(page);
  // 20 skip entries → modal body should scroll, not overflow viewport
  await page.evaluate(() => {
    const skips = Array.from({ length: 20 }, (_, i) => ({
      filename: `file_${i}.xyz`, code: "UNSUPPORTED_TYPE",
      message: "test", suggestion: "save as something else", reason: "test",
    }));
    window.showUploadResultModal([], skips);
  });
  const cards = page.locator(".upload-result-skip-card");
  await expect(cards).toHaveCount(20);
  // Modal body should have overflow-y scroll
  const overflowY = await page.locator(".upload-result-modal .modal-body").evaluate((el) => getComputedStyle(el).overflowY);
  expect(overflowY).toBe("auto");
});

// ─── 2. XSS sanity check on filename + suggestion ───────────────────


test("v7.5.0 / standalone / filename with HTML is escaped (XSS protection)", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal([], [{
      filename: '<img src=x onerror="window.__xss_fired=1">.xyz',
      code: "UNSUPPORTED_TYPE", message: "test",
      suggestion: '<script>window.__xss_fired=1</script>',
      reason: "test",
    }]);
  });
  await page.waitForTimeout(200);
  const xssFired = await page.evaluate(() => window.__xss_fired);
  expect(xssFired).toBeUndefined();
  // Filename escaped — appears as text, not parsed as HTML
  const cardText = await page.locator(".upload-result-skip-card").textContent();
  expect(cardText).toContain("<img");
});

// ─── 3. QUOTA_EXCEEDED routes via uploadFiles, not modal ────────────


test("v7.5.0 / standalone / showUpgradeModal exists as separate path for QUOTA", async ({ page }) => {
  await loadApp(page);
  const hasFn = await page.evaluate(() => typeof window.showUpgradeModal === "function" || (typeof showUpgradeModal === "function"));
  // showUpgradeModal exists in the page scope (defined in app.js around line 116)
  expect(hasFn).toBeTruthy();
});

// ─── 4. retryExtraction handler exists + proper route call ──────────


test("v7.5.0 / standalone / retryExtraction is a window function", async ({ page }) => {
  await loadApp(page);
  const exists = await page.evaluate(() => typeof window.retryExtraction === "function");
  expect(exists).toBe(true);
});

test("v7.5.0 / standalone / retryExtraction calls reprocess?mode=reextract", async ({ page }) => {
  await loadApp(page);
  let calledUrl = null;
  await page.route("**/api/files/*/reprocess**", async (route) => {
    calledUrl = route.request().url();
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({ status: "ok", extraction_status: "ok" }),
    });
  });
  await page.evaluate(() => window.retryExtraction("test-file-id"));
  await page.waitForTimeout(500);
  expect(calledUrl).toContain("/api/files/test-file-id/reprocess");
  expect(calledUrl).toContain("mode=reextract");
});

// ─── 5. v7.5.0 i18n keys present ────────────────────────────────────


test("v7.5.0 / standalone / new i18n keys defined for both langs", async ({ page }) => {
  await loadApp(page);
  // page is in TH mode (set via localStorage init)
  const thKeys = await page.evaluate(() => {
    return [
      typeof t === "function" ? t("upload.resultTitle") : null,
      typeof t === "function" ? t("upload.understand") : null,
      typeof t === "function" ? t("upload.suggestionLabel") : null,
    ];
  });
  // Must NOT be the bare key string (= missing translation)
  expect(thKeys[0]).not.toBe("upload.resultTitle");
  expect(thKeys[1]).not.toBe("upload.understand");
  expect(thKeys[2]).not.toBe("upload.suggestionLabel");
});

// ─── 6. CSS regression — extraction badges have distinct colors ────


test("v7.5.0 / standalone / extraction badge classes have distinct background colors", async ({ page }) => {
  await loadApp(page);
  // Inject test badges into DOM
  await page.evaluate(() => {
    document.body.insertAdjacentHTML("beforeend", `
      <span class="extraction-badge extraction-empty" id="b1">x</span>
      <span class="extraction-badge extraction-encrypted" id="b2">x</span>
      <span class="extraction-badge extraction-ocr_failed" id="b3">x</span>
      <span class="extraction-badge extraction-unsupported" id="b4">x</span>
      <span class="extraction-badge extraction-partial" id="b5">x</span>
      <span class="chunk-count-badge" id="b6">📚</span>
    `);
  });
  const colors = await page.evaluate(() =>
    ["b1","b2","b3","b4","b5","b6"].map(id =>
      getComputedStyle(document.getElementById(id)).backgroundColor
    )
  );
  // All 6 must have a non-transparent background
  for (const c of colors) {
    expect(c).not.toBe("rgba(0, 0, 0, 0)");
    expect(c).not.toBe("transparent");
  }
  // All distinct (so user can visually differentiate)
  const distinct = new Set(colors);
  expect(distinct.size).toBe(6);
});

// ─── 7. Full-flow: uploadFiles() → /api/upload mock → modal displays ─


test("v7.5.0 / standalone / uploadFiles() triggers result modal on backend skip response", async ({ page }) => {
  await loadApp(page);

  // Mock /api/upload to return a mixed batch (1 success + 1 skip)
  await page.route("**/api/upload", async (route) => {
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        uploaded: [{ id: "u1", filename: "ok.txt", filetype: "txt", uploaded_at: new Date().toISOString() }],
        count: 1,
        skipped: [{
          filename: "weird.xyz",
          code: "UNSUPPORTED_TYPE",
          message: "ไฟล์ .xyz ยังไม่รองรับ",
          suggestion: "ลองบันทึกเป็น PDF",
          reason: "ไฟล์ .xyz ยังไม่รองรับ",
        }],
      }),
    });
  });

  // Trigger uploadFiles() programmatically with a fake File list
  await page.evaluate(async () => {
    const blob = new Blob(["test content"], { type: "text/plain" });
    const file = new File([blob], "test.txt", { type: "text/plain" });
    // uploadFiles is the async function from app.js
    await window.uploadFiles([file]);
  });

  // Modal should appear after 300ms setTimeout in uploadFiles handler
  await expect(page.locator("#upload-result-modal-overlay")).toBeVisible({ timeout: 3000 });
  await expect(page.locator(".upload-result-skip-card")).toContainText("weird.xyz");
  await expect(page.locator(".upload-result-skip-card")).toHaveAttribute("data-skip-code", "UNSUPPORTED_TYPE");
});


test("v7.5.0 / standalone / uploadFiles() routes QUOTA_EXCEEDED to upgrade modal", async ({ page }) => {
  await loadApp(page);

  await page.route("**/api/upload", async (route) => {
    await route.fulfill({
      status: 200, contentType: "application/json",
      body: JSON.stringify({
        uploaded: [], count: 0,
        skipped: [{
          filename: "extra.txt", code: "QUOTA_EXCEEDED",
          message: "ครบจำนวนไฟล์ที่เก็บได้แล้ว (5 ไฟล์)",
          suggestion: "ลบไฟล์เก่าหรืออัปเกรดแพลน",
          reason: "ครบจำนวนไฟล์ที่เก็บได้แล้ว (5 ไฟล์)",
        }],
      }),
    });
  });

  await page.evaluate(async () => {
    const file = new File(["x"], "test.txt", { type: "text/plain" });
    await window.uploadFiles([file]);
  });

  // Should open upgrade modal, NOT result modal
  await expect(page.locator("#upgrade-modal-overlay")).toBeVisible({ timeout: 3000 });
  await expect(page.locator("#upload-result-modal-overlay")).toBeHidden();
});


// ─── 8. File list render with extraction_status badges ──────────────


test("v7.5.0 / standalone / renderFiles shows extraction_status badge on encrypted file", async ({ page }) => {
  await loadApp(page);

  // Stub out anything that might paint over our test badges
  await page.evaluate(() => {
    // Find file list container
    const container = document.getElementById("files-list") || document.getElementById("file-list");
    if (!container) {
      // Fallback: inject the function call's expected output directly
      document.body.insertAdjacentHTML("beforeend", '<div id="files-list"></div>');
    }
  });

  // Call renderFiles with a fake file that has encrypted status
  await page.evaluate(() => {
    // Some renderers expect global state.files. Set it.
    // Ensure container exists (in case loadApp didn't fully render layout)
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    if (typeof window.renderFileList === "function") {
      window.renderFileList([{
        id: "fake1",
        filename: "secret.pdf",
        filetype: "pdf",
        text_length: 0,
        processing_status: "ready",
        is_locked: false,
        extraction_status: "encrypted",
        chunk_count: 0,
        is_truncated: false,
        storage_location: "server",
      }]);
    }
  });

  // Look for the encrypted badge anywhere in DOM
  const hasEncrypted = await page.evaluate(() =>
    document.querySelector(".extraction-encrypted") !== null
  );
  expect(hasEncrypted).toBe(true);
});


test("v7.5.0 / standalone / renderFiles shows chunk_count badge on big file", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    // Ensure container exists (in case loadApp didn't fully render layout)
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    if (typeof window.renderFileList === "function") {
      window.renderFileList([{
        id: "fake-big",
        filename: "huge_book.pdf",
        filetype: "pdf",
        text_length: 150000,
        processing_status: "ready",
        is_locked: false,
        extraction_status: "ok",
        chunk_count: 10,
        is_truncated: false,
        storage_location: "server",
      }]);
    }
  });
  const hasChunkBadge = await page.evaluate(() =>
    document.querySelector(".chunk-count-badge") !== null
  );
  expect(hasChunkBadge).toBe(true);
  // Badge should mention "10"
  const badgeText = await page.evaluate(() =>
    document.querySelector(".chunk-count-badge")?.textContent || ""
  );
  expect(badgeText).toContain("10");
});


test("v7.5.0 / standalone / renderFiles shows retry button for failed extraction", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    // Ensure container exists (in case loadApp didn't fully render layout)
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    if (typeof window.renderFileList === "function") {
      window.renderFileList([{
        id: "fake-failed",
        filename: "bad.pdf",
        filetype: "pdf",
        text_length: 30,
        processing_status: "ready",
        is_locked: false,
        extraction_status: "ocr_failed",
        chunk_count: 0,
        is_truncated: false,
        storage_location: "server",
      }]);
    }
  });
  const hasRetry = await page.evaluate(() =>
    document.querySelector(".file-action-retry") !== null
  );
  expect(hasRetry).toBe(true);
});


test("v7.5.0 / standalone / no retry button for healthy file", async ({ page }) => {
  await loadApp(page);
  await page.evaluate(() => {
    // Ensure container exists (in case loadApp didn't fully render layout)
    if (!document.getElementById("file-list")) {
      document.body.insertAdjacentHTML("beforeend", '<div id="file-list"></div>');
    }
    if (typeof window.renderFileList === "function") {
      window.renderFileList([{
        id: "fake-ok",
        filename: "good.pdf",
        filetype: "pdf",
        text_length: 5000,
        processing_status: "ready",
        is_locked: false,
        extraction_status: "ok",
        chunk_count: 0,
        is_truncated: false,
        storage_location: "server",
      }]);
    }
  });
  // No badge, no retry button for ok files
  const hasBadge = await page.evaluate(() =>
    document.querySelector(".extraction-badge") !== null
  );
  const hasRetry = await page.evaluate(() =>
    document.querySelector(".file-action-retry") !== null
  );
  expect(hasBadge).toBe(false);
  expect(hasRetry).toBe(false);
});


// ─── 9. Mobile viewport sanity (v7.4.0 regression) ──────────────────


test("v7.5.0 / standalone / mobile viewport — modal still readable", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 667 });
  await loadApp(page);
  await page.evaluate(() => {
    window.showUploadResultModal([], [{
      filename: "test.xyz", code: "UNSUPPORTED_TYPE",
      message: "ไฟล์ไม่รองรับ", suggestion: "save as csv",
      reason: "ไฟล์ไม่รองรับ",
    }]);
  });
  await expect(page.locator("#upload-result-modal-overlay")).toBeVisible();
  // Modal width should fit in mobile (≤ 96vw per CSS @media)
  const modalWidth = await page.locator(".upload-result-modal").evaluate((el) => el.getBoundingClientRect().width);
  expect(modalWidth).toBeLessThanOrEqual(375);
});
