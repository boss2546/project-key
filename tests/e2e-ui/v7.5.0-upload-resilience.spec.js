// @ts-check
/**
 * v7.5.0 — Upload Resilience tests
 *
 * Sections:
 *   Phase 1 — Upload Result Modal (per-file actionable skip)
 *
 * Phase 4/2/3 sections added as those phases ship.
 *
 * Run: npx playwright test tests/e2e-ui/v7.5.0-upload-resilience.spec.js
 *
 * Note: tests use page.route() to mock /api/upload responses, so they
 * verify the FRONTEND modal/UI without needing a live backend.
 */

const { test, expect } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

// ─── helpers ────────────────────────────────────────────────────────

async function mockUploadResponse(page, response) {
  await page.route("**/api/upload", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(response),
    });
  });
}

/** Trigger upload modal by simulating a file drop or input change. */
async function triggerUpload(page) {
  // Use the hidden file input — works with mocked upload route
  const handle = await page.$('input[type="file"]');
  if (handle) {
    // setInputFiles requires an actual file; create a tiny placeholder
    const tmpPath = require("path").join(__dirname, "fixtures", "_tmp_upload.txt");
    require("fs").writeFileSync(tmpPath, "placeholder for upload trigger");
    await handle.setInputFiles(tmpPath);
  }
}

// ─── Phase 1: Upload Result Modal ───────────────────────────────────

test.describe("v7.5.0 / Phase1 / Upload Result Modal", () => {
  test("shows per-file skip card with code, message, and suggestion", async ({ page }) => {
    await registerAndEnterApp(page);

    await mockUploadResponse(page, {
      uploaded: [{ id: "u1", filename: "ok.txt", filetype: "txt", uploaded_at: new Date().toISOString() }],
      count: 1,
      skipped: [
        {
          filename: "huge.pdf",
          code: "FILE_TOO_LARGE",
          message: "ไฟล์ใหญ่เกิน 100MB",
          suggestion: "บีบอัดด้วย Smallpdf หรือแยกเป็นไฟล์ย่อย",
          reason: "ไฟล์ใหญ่เกิน 100MB",
        },
      ],
    });

    await triggerUpload(page);
    // Modal opens after 300ms setTimeout
    await expect(page.locator("#upload-result-modal-overlay")).toBeVisible({ timeout: 3000 });

    // Skip card
    const card = page.locator(".upload-result-skip-card");
    await expect(card).toContainText("huge.pdf");
    await expect(card).toContainText("100MB");
    await expect(card).toContainText("Smallpdf");

    // Has data-skip-code attribute
    await expect(card).toHaveAttribute("data-skip-code", "FILE_TOO_LARGE");

    // Success summary visible too
    await expect(page.locator(".upload-result-success-text")).toContainText("1");
  });

  test("UNSUPPORTED_TYPE shows correct icon and suggestion text", async ({ page }) => {
    await registerAndEnterApp(page);

    await mockUploadResponse(page, {
      uploaded: [],
      count: 0,
      skipped: [
        {
          filename: "weird.xyz",
          code: "UNSUPPORTED_TYPE",
          message: "ไฟล์ .xyz ยังไม่รองรับ",
          suggestion: "ลองบันทึกเป็น PDF, Word, หรือ TXT แล้วอัปอีกครั้ง",
          reason: "ไฟล์ .xyz ยังไม่รองรับ",
        },
      ],
    });

    await triggerUpload(page);
    await expect(page.locator("#upload-result-modal-overlay")).toBeVisible({ timeout: 3000 });
    const card = page.locator(".upload-result-skip-card");
    await expect(card).toHaveAttribute("data-skip-code", "UNSUPPORTED_TYPE");
    await expect(card).toContainText("PDF");
  });

  test("EMPTY_FILE skip code renders distinct icon", async ({ page }) => {
    await registerAndEnterApp(page);
    await mockUploadResponse(page, {
      uploaded: [],
      count: 0,
      skipped: [{
        filename: "blank.txt",
        code: "EMPTY_FILE",
        message: "ไฟล์ว่างเปล่า",
        suggestion: "ตรวจว่าไฟล์ไม่เสียหายก่อนอัปใหม่",
        reason: "ไฟล์ว่างเปล่า",
      }],
    });
    await triggerUpload(page);
    await expect(page.locator(".upload-result-skip-card")).toBeVisible({ timeout: 3000 });
    await expect(page.locator(".upload-result-skip-card")).toHaveAttribute("data-skip-code", "EMPTY_FILE");
  });

  test("modal closes via close button", async ({ page }) => {
    await registerAndEnterApp(page);
    await mockUploadResponse(page, {
      uploaded: [],
      count: 0,
      skipped: [{
        filename: "x.xyz",
        code: "UNSUPPORTED_TYPE",
        message: "test",
        suggestion: "do something",
        reason: "test",
      }],
    });
    await triggerUpload(page);
    await expect(page.locator("#upload-result-modal-overlay")).toBeVisible({ timeout: 3000 });
    await page.click("#upload-result-close-btn");
    await expect(page.locator("#upload-result-modal-overlay")).toBeHidden();
  });

  test("modal closes via ESC key (v7.2.0 modal pattern)", async ({ page }) => {
    await registerAndEnterApp(page);
    await mockUploadResponse(page, {
      uploaded: [],
      count: 0,
      skipped: [{
        filename: "x.xyz",
        code: "UNSUPPORTED_TYPE",
        message: "test",
        suggestion: "save as csv",
        reason: "test",
      }],
    });
    await triggerUpload(page);
    await expect(page.locator("#upload-result-modal-overlay")).toBeVisible({ timeout: 3000 });
    await page.keyboard.press("Escape");
    await expect(page.locator("#upload-result-modal-overlay")).toBeHidden();
  });

  test("QUOTA_EXCEEDED routes to upgrade modal (not generic skip modal)", async ({ page }) => {
    await registerAndEnterApp(page);
    await mockUploadResponse(page, {
      uploaded: [],
      count: 0,
      skipped: [{
        filename: "extra.txt",
        code: "QUOTA_EXCEEDED",
        message: "ครบจำนวนไฟล์ที่เก็บได้แล้ว (5 ไฟล์)",
        suggestion: "ลบไฟล์เก่าหรืออัปเกรดแพลน",
        reason: "ครบจำนวนไฟล์ที่เก็บได้แล้ว (5 ไฟล์)",
      }],
    });
    await triggerUpload(page);
    // Should open #upgrade-modal-overlay, NOT #upload-result-modal-overlay
    await expect(page.locator("#upgrade-modal-overlay")).toBeVisible({ timeout: 3000 });
    await expect(page.locator("#upload-result-modal-overlay")).toBeHidden();
  });
});
