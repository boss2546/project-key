// @ts-check
/**
 * Personal Data Bank v5.0 — E2E UI Tests (Playwright)
 * ==============================================
 * เทสหน้าเว็บแบบโหมดๆ — ทดสอบทุก interaction ก่อนให้ผู้ใช้จริง
 *
 * Run: npx playwright test
 */

const { test, expect } = require("@playwright/test");

// ─── Test User ───
const TEST_EMAIL = `uitest_${Date.now()}@smoke.test`;
const TEST_PASSWORD = "UiTest_Pass123!";
const TEST_NAME = "UI Smoke Tester";

// ═══════════════════════════════════════════════════
// 1️⃣  LANDING PAGE — หน้าแรกโหลดได้ + เลื่อนได้
// ═══════════════════════════════════════════════════

test.describe("Landing Page", () => {
  test.beforeEach(async ({ page }) => {
    // Clear auth so we see the landing page
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("pdb_token");
      localStorage.removeItem("pdb_user");
    });
    await page.reload();
    await page.waitForLoadState("networkidle");
  });

  test("แสดงหน้า Landing Page สำหรับผู้ไม่ได้ login", async ({ page }) => {
    // Landing page must be visible
    const landing = page.locator("#landing-page");
    await expect(landing).toBeVisible();

    // Hero text
    await expect(page.locator(".hero-title")).toContainText("เปลี่ยนเอกสารของคุณ");

    // Header has logo
    await expect(page.locator(".landing-header .landing-logo")).toBeVisible();
  });

  test("มีปุ่ม สมัครฟรี และ เข้าสู่ระบบ", async ({ page }) => {
    await expect(page.locator("#btn-show-login")).toBeVisible();
    await expect(page.locator("#btn-show-register")).toBeVisible();
    await expect(page.locator("#btn-hero-register")).toBeVisible();
  });

  test("เลื่อนลงเห็น Features, Stats, How it Works, CTA", async ({ page }) => {
    // Scroll to features
    const features = page.locator(".landing-features");
    await features.scrollIntoViewIfNeeded();
    await expect(features).toBeVisible();

    // Stats section
    const stats = page.locator(".landing-stats");
    await stats.scrollIntoViewIfNeeded();
    await expect(stats).toBeVisible();
    await expect(stats).toContainText("21");
    await expect(stats).toContainText("MCP Tools");

    // How it works (steps)
    const steps = page.locator(".steps-grid");
    await steps.scrollIntoViewIfNeeded();
    await expect(steps).toBeVisible();

    // CTA
    const cta = page.locator(".landing-cta");
    await cta.scrollIntoViewIfNeeded();
    await expect(cta).toContainText("พร้อมเปลี่ยนข้อมูลเป็นความรู้");

    // Footer
    const footer = page.locator(".landing-footer");
    await footer.scrollIntoViewIfNeeded();
    await expect(footer).toContainText("Personal Data Bank");
  });

  test("Feature cards แสดงครบ 4 ใบ", async ({ page }) => {
    const cards = page.locator(".feature-card");
    await expect(cards).toHaveCount(4);
    await expect(cards.nth(0)).toContainText("จัดเก็บอัจฉริยะ");
    await expect(cards.nth(1)).toContainText("Knowledge Graph");
    await expect(cards.nth(2)).toContainText("AI Chat");
    await expect(cards.nth(3)).toContainText("MCP");
  });

  test("Pipeline visual แสดง 4 ขั้นตอน", async ({ page }) => {
    const steps = page.locator(".pipeline-step");
    await expect(steps).toHaveCount(4);
  });
});

// ═══════════════════════════════════════════════════
// 2️⃣  AUTH MODAL — สมัคร + เข้าสู่ระบบ
// ═══════════════════════════════════════════════════

test.describe("Auth Modal", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("pdb_token");
      localStorage.removeItem("pdb_user");
    });
    await page.reload();
    await page.waitForLoadState("networkidle");
  });

  test("กด เข้าสู่ระบบ แล้ว modal เปิด", async ({ page }) => {
    await page.click("#btn-show-login");
    const modal = page.locator("#auth-modal");
    await expect(modal).not.toHaveClass(/hidden/);
    await expect(page.locator("#auth-modal-title")).toContainText("เข้าสู่ระบบ");
  });

  test("กด เริ่มต้นฟรี แล้ว modal เปิดเป็น register", async ({ page }) => {
    await page.click("#btn-show-register");
    const modal = page.locator("#auth-modal");
    await expect(modal).not.toHaveClass(/hidden/);
    await expect(page.locator("#auth-modal-title")).toContainText("สมัครสมาชิก");
    await expect(page.locator("#register-form")).not.toHaveClass(/hidden/);
  });

  test("กดปิด modal ได้", async ({ page }) => {
    await page.click("#btn-show-login");
    await expect(page.locator("#auth-modal")).not.toHaveClass(/hidden/);
    await page.click("#auth-modal-close");
    await expect(page.locator("#auth-modal")).toHaveClass(/hidden/);
  });

  test("สลับระหว่าง login ↔ register ได้", async ({ page }) => {
    // Open login
    await page.click("#btn-show-login");
    await expect(page.locator("#login-form")).not.toHaveClass(/hidden/);

    // Switch to register
    await page.click("#switch-to-register");
    await expect(page.locator("#register-form")).not.toHaveClass(/hidden/);
    await expect(page.locator("#login-form")).toHaveClass(/hidden/);

    // Switch back to login
    await page.click("#switch-to-login");
    await expect(page.locator("#login-form")).not.toHaveClass(/hidden/);
    await expect(page.locator("#register-form")).toHaveClass(/hidden/);
  });

  test("Login ผิดรหัสแสดง error", async ({ page }) => {
    await page.click("#btn-show-login");
    await page.fill("#login-email", "nobody@test.com");
    await page.fill("#login-password", "wrong");
    await page.click("#btn-login");
    // Wait for error to appear
    await expect(page.locator("#login-error")).not.toHaveClass(/hidden/, {
      timeout: 5000,
    });
  });

  test("Hero ปุ่ม สมัครฟรี เปิด register modal", async ({ page }) => {
    await page.click("#btn-hero-register");
    await expect(page.locator("#auth-modal")).not.toHaveClass(/hidden/);
    await expect(page.locator("#register-form")).not.toHaveClass(/hidden/);
  });
});

// ═══════════════════════════════════════════════════
// 3️⃣  REGISTER + LOGIN FLOW — Full Journey
// ═══════════════════════════════════════════════════

test.describe("Full Auth Journey", () => {
  test("สมัครสมาชิกใหม่ → เข้า workspace → logout → login กลับ", async ({
    page,
  }) => {
    // ─── Step 1: Go to landing ───
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.removeItem("pdb_token");
      localStorage.removeItem("pdb_user");
    });
    await page.reload();
    await page.waitForLoadState("networkidle");

    // ─── Step 2: Open register ───
    await page.click("#btn-show-register");
    await expect(page.locator("#register-form")).not.toHaveClass(/hidden/);

    // ─── Step 3: Fill and submit register ───
    await page.fill("#register-name", TEST_NAME);
    await page.fill("#register-email", TEST_EMAIL);
    await page.fill("#register-password", TEST_PASSWORD);
    await page.click("#btn-register");

    // ─── Step 4: Should enter workspace ───
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
    await expect(page.locator("#landing-page")).toHaveClass(/hidden/);

    // Sidebar should be visible
    await expect(page.locator("#sidebar")).toBeVisible();

    // User email should appear
    await expect(page.locator("#sidebar-user-email")).toContainText(TEST_EMAIL);

    // ─── Step 5: Logout ───
    await page.click("#btn-logout");
    await expect(page.locator("#landing-page")).not.toHaveClass(/hidden/, {
      timeout: 5000,
    });

    // ─── Step 6: Login back ───
    await page.click("#btn-show-login");
    await page.fill("#login-email", TEST_EMAIL);
    await page.fill("#login-password", TEST_PASSWORD);
    await page.click("#btn-login");

    // Should be back in workspace
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
  });
});

// ═══════════════════════════════════════════════════
// 4️⃣  WORKSPACE NAVIGATION — เปลี่ยนหน้าได้
// ═══════════════════════════════════════════════════

test.describe("Workspace Navigation", () => {
  test.beforeEach(async ({ page }) => {
    // Login via API then set tokens
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    // Wait for app to be visible
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
  });

  test("หน้าแรกเข้า My Data (ข้อมูลของฉัน)", async ({ page }) => {
    await expect(page.locator("#page-my-data")).toHaveClass(/active/);
    await expect(page.locator("#nav-my-data")).toHaveClass(/active/);
  });

  test("กดเมนู Knowledge View", async ({ page }) => {
    await page.click("#nav-knowledge");
    await expect(page.locator("#page-knowledge")).toHaveClass(/active/);
    await expect(page.locator("#nav-knowledge")).toHaveClass(/active/);
    // My Data should not be active
    await expect(page.locator("#nav-my-data")).not.toHaveClass(/active/);
  });

  test("กดเมนู Graph", async ({ page }) => {
    await page.click("#nav-graph");
    await expect(page.locator("#page-graph")).toHaveClass(/active/);
  });

  test("กดเมนู AI Chat", async ({ page }) => {
    await page.click("#nav-chat");
    await expect(page.locator("#page-chat")).toHaveClass(/active/);
    // Welcome message should be visible
    await expect(page.locator(".welcome-message")).toBeVisible();
  });

  test("กดเมนู MCP Setup", async ({ page }) => {
    await page.click("#nav-mcp-setup");
    await expect(page.locator("#page-mcp-setup")).toHaveClass(/active/);
  });

  test("กดเมนู Tokens", async ({ page }) => {
    await page.click("#nav-tokens");
    await expect(page.locator("#page-tokens")).toHaveClass(/active/);
  });

  test("กดเมนู MCP Logs", async ({ page }) => {
    await page.click("#nav-mcp-logs");
    await expect(page.locator("#page-mcp-logs")).toHaveClass(/active/);
  });

  test("กดวนรอบทุกเมนู — ไม่มีหน้าค้างซ้อน", async ({ page }) => {
    const pages = [
      "my-data",
      "knowledge",
      "graph",
      "chat",
      "mcp-setup",
      "tokens",
      "mcp-logs",
    ];

    for (const p of pages) {
      await page.click(`#nav-${p}`);
      await expect(page.locator(`#page-${p}`)).toHaveClass(/active/);

      // All other pages should NOT be active
      for (const other of pages) {
        if (other !== p) {
          await expect(page.locator(`#page-${other}`)).not.toHaveClass(
            /active/
          );
        }
      }
    }
  });
});

// ═══════════════════════════════════════════════════
// 5️⃣  SIDEBAR — Stats + Profile
// ═══════════════════════════════════════════════════

test.describe("Sidebar", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
  });

  test("Stats แสดงตัวเลข", async ({ page }) => {
    await expect(page.locator("#stat-files")).toBeVisible();
    await expect(page.locator("#stat-clusters")).toBeVisible();
    await expect(page.locator("#stat-nodes")).toBeVisible();
    await expect(page.locator("#stat-edges")).toBeVisible();
    await expect(page.locator("#stat-packs")).toBeVisible();
    await expect(page.locator("#stat-tokens")).toBeVisible();
  });

  test("Logo แสดง Personal Data Bank", async ({ page }) => {
    await expect(page.locator(".logo-text")).toContainText("Personal Data Bank");
  });

  test("User email แสดงใน sidebar", async ({ page }) => {
    await expect(page.locator("#sidebar-user-email")).toContainText(TEST_EMAIL);
  });
});

// ═══════════════════════════════════════════════════
// 6️⃣  LANGUAGE TOGGLE — สลับภาษา
// ═══════════════════════════════════════════════════

test.describe("Language Toggle", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
        localStorage.setItem("pdb_lang", "th");
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
  });

  test("เริ่มต้นเป็นภาษาไทย", async ({ page }) => {
    // Nav labels should be Thai
    await expect(page.locator("#nav-my-data .nav-label")).toContainText(
      "ข้อมูลของฉัน"
    );
  });

  test("กดสลับเป็นภาษาอังกฤษ", async ({ page }) => {
    await page.click("#lang-toggle");
    // Nav labels should switch to English
    await expect(page.locator("#nav-my-data .nav-label")).toContainText(
      "My Data"
    );
    await expect(page.locator("#nav-knowledge .nav-label")).toContainText(
      "Knowledge View"
    );
    await expect(page.locator("#nav-chat .nav-label")).toContainText("AI Chat");
  });

  test("กดสลับกลับเป็นไทย", async ({ page }) => {
    await page.click("#lang-toggle"); // → EN
    await page.click("#lang-toggle"); // → TH
    await expect(page.locator("#nav-my-data .nav-label")).toContainText(
      "ข้อมูลของฉัน"
    );
  });
});

// ═══════════════════════════════════════════════════
// 7️⃣  MY DATA PAGE — Upload Zone
// ═══════════════════════════════════════════════════

test.describe("My Data Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
  });

  test("Upload zone แสดงผล", async ({ page }) => {
    await expect(page.locator("#upload-zone")).toBeVisible();
    await expect(page.locator("#upload-zone")).toContainText("ลากไฟล์มาวาง");
  });

  test("ปุ่ม Organize with AI แสดง", async ({ page }) => {
    await expect(page.locator("#btn-organize")).toBeVisible();
  });

  test("ปุ่ม Enrich Metadata แสดง", async ({ page }) => {
    await expect(page.locator("#btn-enrich")).toBeVisible();
  });

  test("File count badge แสดง", async ({ page }) => {
    await expect(page.locator("#file-count-badge")).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════
// 8️⃣  AI CHAT PAGE — UI Elements
// ═══════════════════════════════════════════════════

test.describe("AI Chat Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
    await page.click("#nav-chat");
  });

  test("Chat input แสดง + พิมพ์ได้", async ({ page }) => {
    const input = page.locator("#chat-input");
    await expect(input).toBeVisible();
    await input.fill("ทดสอบพิมพ์ข้อความ");
    await expect(input).toHaveValue("ทดสอบพิมพ์ข้อความ");
  });

  test("Send button แสดง", async ({ page }) => {
    await expect(page.locator("#btn-send")).toBeVisible();
  });

  test("Welcome message แสดง", async ({ page }) => {
    await expect(page.locator(".welcome-message")).toBeVisible();
  });

  test("Context layers chips แสดง", async ({ page }) => {
    await expect(page.locator(".layer-chip")).toHaveCount(5);
  });

  test("Sources panel แสดง", async ({ page }) => {
    await expect(page.locator("#sources-panel")).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════
// 9️⃣  GRAPH PAGE — Canvas + Controls
// ═══════════════════════════════════════════════════

test.describe("Graph Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
    await page.click("#nav-graph");
  });

  test("Graph canvas แสดง", async ({ page }) => {
    await expect(page.locator("#graph-canvas")).toBeVisible();
  });

  test("มี Global/Local toggle", async ({ page }) => {
    await expect(page.locator("#graph-global-btn")).toBeVisible();
    await expect(page.locator("#graph-local-btn")).toBeVisible();
  });

  test("Filter chips แสดง 6 ตัว", async ({ page }) => {
    await expect(page.locator(".filter-chip")).toHaveCount(6);
  });

  test("Zoom controls แสดง", async ({ page }) => {
    await expect(page.locator("#zoom-in-btn")).toBeVisible();
    await expect(page.locator("#zoom-out-btn")).toBeVisible();
    await expect(page.locator("#zoom-fit-btn")).toBeVisible();
  });

  test("ปุ่ม Rebuild Graph แสดง", async ({ page }) => {
    await expect(page.locator("#btn-rebuild-graph")).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════
// 🔟  MCP SETUP PAGE
// ═══════════════════════════════════════════════════

test.describe("MCP Setup Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
    await page.click("#nav-mcp-setup");
  });

  test("MCP Server URL แสดง", async ({ page }) => {
    await expect(page.locator("#mcp-url-value")).toBeVisible();
    // Should contain the fly.dev URL
    await expect(page.locator("#mcp-url-value")).not.toContainText("Loading");
  });

  test("Setup steps แสดง 1, 2, 3", async ({ page }) => {
    const steps = page.locator(".mcp-step-number");
    await expect(steps).toHaveCount(4); // 4 steps including test
  });

  test("Generate Token button แสดง", async ({ page }) => {
    await expect(page.locator("#btn-generate-token")).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════
// 1️⃣1️⃣  KNOWLEDGE VIEW — Tabs
// ═══════════════════════════════════════════════════

test.describe("Knowledge View Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    const res = await page.request.post("/api/auth/login", {
      data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    });
    const data = await res.json();
    await page.evaluate(
      ({ token, user }) => {
        localStorage.setItem("pdb_token", token);
        localStorage.setItem("pdb_user", JSON.stringify(user));
      },
      { token: data.token, user: data.user }
    );
    await page.reload();
    await page.waitForLoadState("networkidle");
    await expect(page.locator("#app")).not.toHaveClass(/hidden/, {
      timeout: 10000,
    });
    await page.click("#nav-knowledge");
  });

  test("Tab Collections, Notes, Packs แสดง", async ({ page }) => {
    await expect(page.locator('[data-tab="collections"]')).toBeVisible();
    await expect(page.locator('[data-tab="notes"]')).toBeVisible();
    await expect(page.locator('[data-tab="packs"]')).toBeVisible();
  });

  test("สลับ tab ได้", async ({ page }) => {
    // Click Notes tab
    await page.click('[data-tab="notes"]');
    await expect(page.locator('[data-tab="notes"]')).toHaveClass(/active/);

    // Click Packs tab
    await page.click('[data-tab="packs"]');
    await expect(page.locator('[data-tab="packs"]')).toHaveClass(/active/);
    await expect(page.locator('[data-tab="notes"]')).not.toHaveClass(/active/);
  });

  test("View toggle Cards/Table แสดง", async ({ page }) => {
    await expect(page.locator("#view-cards")).toBeVisible();
    await expect(page.locator("#view-table")).toBeVisible();
  });
});

// ═══════════════════════════════════════════════════
// 1️⃣2️⃣  PAGE TITLE — <title> ถูกต้อง
// ═══════════════════════════════════════════════════

test.describe("Meta & SEO", () => {
  test("Title tag ถูกต้อง", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveTitle(/Personal Data Bank/);
  });

  test("Meta description มี", async ({ page }) => {
    await page.goto("/");
    const desc = await page.locator('meta[name="description"]').getAttribute("content");
    expect(desc).toBeTruthy();
    expect(desc.length).toBeGreaterThan(10);
  });

  test("Viewport meta มี", async ({ page }) => {
    await page.goto("/");
    const vp = await page.locator('meta[name="viewport"]').getAttribute("content");
    expect(vp).toContain("width=device-width");
  });
});
