// @ts-check
/**
 * v7.2.0 — UX Critical Hotfixes test suite (12 tests)
 *
 * Sections:
 *   1. Button loading states (saveProfile + sendMessage)
 *   2. Upload progress + beforeunload guard
 *   3. Error toast — never auto-dismiss + close button
 *   4. AI Typing indicator
 *   5. Modal UX — global ESC + backdrop close
 */

const { test, expect } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

// ─── Section 1: Button loading states ───────────────────────────────

test.describe("v7.2.0 / 1. Button loading states", () => {
  test("saveProfile disables button + shows spinner during request", async ({ page }) => {
    await registerAndEnterApp(page);
    // Open profile modal
    await page.click("#profile-trigger");
    await expect(page.locator("#profile-modal")).not.toHaveClass(/hidden/);
    const btn = page.locator("#btn-save-profile");
    await expect(btn).not.toBeDisabled();
    // Mock PUT /api/profile to fulfill after a delay so we can observe
    // the in-flight loading state without depending on real backend.
    await page.route("**/api/profile", async (route, req) => {
      if (req.method() !== "PUT") return route.continue();
      await new Promise((r) => setTimeout(r, 700));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          status: "ok",
          profile: { identity_summary: "", goals: "", working_style: "" },
        }),
      });
    });
    await btn.click();
    // While in-flight: button is disabled and shows spinner inside it
    await expect(btn).toBeDisabled();
    await expect(btn.locator(".loading-spinner")).toBeVisible();
    // After completion: button is re-enabled by the finally block
    await expect(btn).not.toBeDisabled({ timeout: 5000 });
  });

  test("sendMessage replaces send icon with spinner during fetch", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    await page.fill("#chat-input", "hello");
    await page.route("**/api/chat", async (route) => {
      await new Promise((r) => setTimeout(r, 600));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ answer: "hi", injection_summary: "test" }),
      });
    });
    await page.click("#btn-send");
    // While fetch is in-flight, send button is disabled with spinner
    await expect(page.locator("#btn-send")).toBeDisabled();
    await expect(page.locator("#btn-send .loading-spinner")).toBeVisible();
    // After response, button is enabled again
    await expect(page.locator("#btn-send")).not.toBeDisabled({ timeout: 5000 });
  });
});

// ─── Section 2: Upload progress + beforeunload guard ────────────────

test.describe("v7.2.0 / 2. Upload progress + close guard", () => {
  test("upload uses XHR (loading overlay shows %)", async ({ page }) => {
    await registerAndEnterApp(page);
    // Mock /api/upload as a slow XHR so the overlay is visible
    await page.route("**/api/upload", async (route) => {
      await new Promise((r) => setTimeout(r, 800));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ uploaded: [], skipped: [], count: 0 }),
      });
    });
    // Use the hidden file input directly (drag/drop is hard in headless)
    const tmpFile = {
      name: "smoke.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("hello world"),
    };
    await page.setInputFiles("#file-input", tmpFile);
    // While upload runs, overlay should appear with the upload icon
    await expect(page.locator(".loading-overlay-card .upload-icon")).toBeVisible({ timeout: 3000 });
    // Allow for the message to render with our format ("Uploading 1 file(s)... NN%" or TH equiv)
    await expect(page.locator(".loading-overlay-card .loading-message")).toContainText(/%/, { timeout: 3000 });
    // Wait for completion
    await expect(page.locator(".loading-overlay")).toHaveCount(0, { timeout: 8000 });
  });

  test("second upload while first in-flight shows toast info", async ({ page }) => {
    await registerAndEnterApp(page);
    // Make /api/upload deliberately slow so the first call stays in-flight
    // long enough for the second to observe `_uploadInFlight === true`.
    await page.route("**/api/upload", async (route) => {
      await new Promise((r) => setTimeout(r, 2500));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ uploaded: [], skipped: [], count: 0 }),
      });
    });
    // Trigger first upload through the file input (the user's normal flow)
    await page.setInputFiles("#file-input", {
      name: "a.txt",
      mimeType: "text/plain",
      buffer: Buffer.from("x"),
    });
    // First upload is in-flight: loading overlay visible
    await expect(page.locator(".loading-overlay")).toBeVisible({ timeout: 3000 });
    // Now attempt a second upload — it must short-circuit with toast.info
    await page.evaluate(() => {
      const blob = new Blob(["y"], { type: "text/plain" });
      const file = new File([blob], "b.txt", { type: "text/plain" });
      // @ts-ignore — uploadFiles is a global async function declared in app.js
      uploadFiles([file]);
    });
    // Match by text — disambiguate from the v6.1 rebrand notice toast which
    // also has class .toast.info and may still be on screen at this moment.
    const busyToast = page.locator(".toast.info").filter({
      hasText: /กำลังอัปโหลดอยู่|Upload already in progress/i,
    });
    await expect(busyToast).toBeVisible({ timeout: 3000 });
  });
});

// ─── Section 3: Error toast persists ────────────────────────────────

test.describe("v7.2.0 / 3. Error toast", () => {
  test("error toast does NOT auto-dismiss within 5s", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.evaluate(() => {
      // @ts-ignore
      showToast("test error stays", "error");
    });
    await expect(page.locator(".toast.error")).toBeVisible();
    await page.waitForTimeout(5500); // longer than the 4s success-timer
    await expect(page.locator(".toast.error")).toBeVisible();
  });

  test("error toast close (X) button removes toast", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.evaluate(() => {
      // @ts-ignore
      showToast("close me", "error");
    });
    await expect(page.locator(".toast.error")).toBeVisible();
    // toast-container z-index (10000) sits above guide-fab (9998).
    await page.click(".toast.error .toast-close");
    await expect(page.locator(".toast.error")).toHaveCount(0, { timeout: 2000 });
  });

  test("success toast still auto-dismisses after 4s", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.evaluate(() => {
      // @ts-ignore
      showToast("ok", "success");
    });
    await expect(page.locator(".toast.success")).toBeVisible();
    // Wait > 4s — should be gone
    await expect(page.locator(".toast.success")).toHaveCount(0, { timeout: 6000 });
  });
});

// ─── Section 4: AI typing indicator ─────────────────────────────────

test.describe("v7.2.0 / 4. Typing indicator", () => {
  test("typing indicator becomes visible when send is clicked", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    await expect(page.locator("#chat-typing-status")).toHaveClass(/hidden/);
    // Slow the chat endpoint so the indicator is visible long enough to assert
    await page.route("**/api/chat", async (route) => {
      await new Promise((r) => setTimeout(r, 600));
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ answer: "ok", injection_summary: "x" }),
      });
    });
    await page.fill("#chat-input", "hello");
    await page.click("#btn-send");
    await expect(page.locator("#chat-typing-status")).not.toHaveClass(/hidden/, { timeout: 1000 });
    // After response, indicator hidden again
    await expect(page.locator("#chat-typing-status")).toHaveClass(/hidden/, { timeout: 5000 });
  });

  test("typing indicator label changes with language toggle", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    const indicator = page.locator("#chat-typing-status [data-i18n='chat.thinking']");
    const initial = (await indicator.textContent())?.trim();
    await page.click("#lang-toggle");
    await page.waitForTimeout(300);
    const after = (await indicator.textContent())?.trim();
    expect(after).not.toBe(initial);
    expect([initial, after].sort()).toEqual(["AI is thinking...", "AI กำลังคิด..."].sort());
  });
});

// ─── Section 5: Modal UX (ESC + backdrop) ───────────────────────────

test.describe("v7.2.0 / 5. Modal UX", () => {
  test("ESC closes profile modal", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#profile-trigger");
    await expect(page.locator("#profile-modal")).not.toHaveClass(/hidden/);
    await page.keyboard.press("Escape");
    await expect(page.locator("#profile-modal")).toHaveClass(/hidden/);
  });

  test("backdrop click closes profile modal", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#profile-trigger");
    await expect(page.locator("#profile-modal")).not.toHaveClass(/hidden/);
    // Click on the overlay element itself — far from the inner .modal box
    const overlay = page.locator("#profile-modal");
    await overlay.click({ position: { x: 5, y: 5 } });
    await expect(page.locator("#profile-modal")).toHaveClass(/hidden/);
  });

  test("clicking inside modal does NOT close it", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#profile-trigger");
    await expect(page.locator("#profile-modal")).not.toHaveClass(/hidden/);
    // Click any input inside the modal
    const input = page.locator("#profile-modal .modal input, #profile-modal .modal textarea").first();
    await input.click();
    await expect(page.locator("#profile-modal")).not.toHaveClass(/hidden/);
  });
});
