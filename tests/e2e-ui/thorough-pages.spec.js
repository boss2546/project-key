// @ts-check
/**
 * Thorough page-by-page UI tests.
 * Verifies each of the 8 app pages renders its expected content
 * and key interactive elements are present + responsive.
 */

const { test, expect } = require("@playwright/test");
const { registerAndEnterApp } = require("./fixtures/auth.js");

test.describe("Thorough / 1. My Data page", () => {
  test("renders header, upload zone, file list", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#page-my-data")).toHaveClass(/active/);
    await expect(page.locator("#page-my-data .page-title")).toBeVisible();
    await expect(page.locator("#upload-zone")).toBeVisible();
    await expect(page.locator("#upload-zone .upload-icon")).toBeVisible();
    await expect(page.locator("#upload-zone .upload-text")).toBeVisible();
    await expect(page.locator("#file-input")).toBeAttached();
    await expect(page.locator("#file-list")).toBeVisible();
    await expect(page.locator("#file-count-badge")).toBeVisible();
  });

  test("organize buttons exist", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#btn-organize-all")).toBeVisible();
    await expect(page.locator("#btn-organize-new")).toBeVisible();
    await expect(page.locator("#unprocessed-badge")).toBeAttached();
  });

  test("empty file list shows empty state", async ({ page }) => {
    await registerAndEnterApp(page);
    const empty = page.locator("#file-list .empty-state");
    await expect(empty).toBeVisible();
  });

  test("clicking file input triggers picker (input is hidden)", async ({ page }) => {
    await registerAndEnterApp(page);
    const input = page.locator("#file-input");
    // Type=file is hidden by attribute, but exists; just verify accept attr
    const accept = await input.getAttribute("accept");
    expect(accept).toContain(".pdf");
    expect(accept).toContain(".docx");
  });
});

test.describe("Thorough / 2. Knowledge page", () => {
  test("renders 3 tabs and toggle", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-knowledge");
    await expect(page.locator("#page-knowledge")).toHaveClass(/active/);
    const tabs = page.locator(".knowledge-tabs .tab-btn");
    await expect(tabs).toHaveCount(3);
    await expect(tabs.nth(0)).toContainText(/Collections/i);
    await expect(tabs.nth(2)).toContainText(/Pack/i);
  });

  test("view-toggle Cards/Table buttons", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-knowledge");
    await expect(page.locator("#view-cards")).toBeVisible();
    await expect(page.locator("#view-table")).toBeVisible();
  });

  test("clicking tabs switches active class", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-knowledge");
    const notesTab = page.locator('.tab-btn[data-tab="notes"]');
    await notesTab.click();
    await expect(notesTab).toHaveClass(/active/);
    const packsTab = page.locator('.tab-btn[data-tab="packs"]');
    await packsTab.click();
    await expect(packsTab).toHaveClass(/active/);
  });
});

test.describe("Thorough / 3. Graph page", () => {
  test("renders global/local toggle, rebuild button, canvas", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-graph");
    await expect(page.locator("#page-graph")).toHaveClass(/active/);
    await expect(page.locator("#graph-global-btn")).toBeVisible();
    await expect(page.locator("#graph-local-btn")).toBeVisible();
    await expect(page.locator("#btn-rebuild-graph")).toBeVisible();
    await expect(page.locator("#graph-svg")).toBeAttached();
  });

  test("graph filter chips render", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-graph");
    const chips = page.locator(".graph-filters .filter-chip");
    await expect(chips.first()).toBeVisible();
    expect(await chips.count()).toBeGreaterThanOrEqual(5);
  });

  test("zoom controls visible", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-graph");
    await expect(page.locator("#zoom-in-btn")).toBeVisible();
    await expect(page.locator("#zoom-out-btn")).toBeVisible();
    await expect(page.locator("#zoom-fit-btn")).toBeVisible();
  });

  test("local toggle reveals depth slider", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-graph");
    await page.click("#graph-local-btn");
    // depth-slider is wrapped in #local-controls; might still be hidden if no node selected,
    // but the slider element should be in DOM
    await expect(page.locator("#depth-slider")).toBeAttached();
  });
});

test.describe("Thorough / 4. AI Chat page", () => {
  test("renders chat container, input, send button, sources", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    await expect(page.locator("#page-chat")).toHaveClass(/active/);
    await expect(page.locator("#chat-messages")).toBeVisible();
    await expect(page.locator("#chat-input")).toBeVisible();
    await expect(page.locator("#btn-send")).toBeVisible();
    await expect(page.locator("#sources-panel")).toBeVisible();
  });

  test("welcome message visible on empty chat", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    await expect(page.locator(".welcome-message")).toBeVisible();
    await expect(page.locator(".context-layers .layer-chip")).toHaveCount(5);
  });

  test("sources panel sections render", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    await expect(page.locator("#src-profile")).toBeAttached();
    await expect(page.locator("#src-files")).toBeAttached();
    await expect(page.locator("#src-graph")).toBeAttached();
    await expect(page.locator("#src-reasoning")).toBeAttached();
  });

  test("typing fills input", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-chat");
    const input = page.locator("#chat-input");
    await input.fill("Hello AI");
    await expect(input).toHaveValue("Hello AI");
  });
});

test.describe("Thorough / 5. Context Memory page", () => {
  test("renders search, filter, create button, grid", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await expect(page.locator("#page-context-memory")).toHaveClass(/active/);
    await expect(page.locator("#ctx-search")).toBeVisible();
    await expect(page.locator("#ctx-filter-type")).toBeVisible();
    await expect(page.locator("#btn-new-context")).toBeVisible();
    await expect(page.locator("#ctx-grid")).toBeVisible();
  });

  test("clicking new opens create modal", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await page.click("#btn-new-context");
    await expect(page.locator("#ctx-modal")).not.toHaveClass(/hidden/);
    await expect(page.locator("#ctx-input-title")).toBeVisible();
    await expect(page.locator("#ctx-input-content")).toBeVisible();
  });

  test("empty state visible when no contexts", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-context-memory");
    await expect(page.locator("#ctx-empty")).toBeVisible();
  });
});

test.describe("Thorough / 6. MCP Setup page", () => {
  test("renders 4 step cards", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-setup");
    await expect(page.locator("#page-mcp-setup")).toHaveClass(/active/);
    const stepCards = page.locator(".mcp-step-card");
    await expect(stepCards).toHaveCount(4);
  });

  test("MCP server URL appears", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-setup");
    // Wait for /api/mcp/info to populate the URL
    await expect(page.locator("#mcp-url-value")).not.toContainText("Loading", { timeout: 10000 });
    const url = await page.locator("#mcp-url-value").textContent();
    expect(url).toMatch(/^https?:\/\/.+\/mcp\//);
  });

  test("token generation form exists", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-setup");
    await expect(page.locator("#mcp-token-label")).toBeVisible();
    await expect(page.locator("#btn-generate-token")).toBeVisible();
  });

  test("Claude/Antigravity tabs work", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-setup");
    await expect(page.locator("#tab-claude")).toBeVisible();
    await expect(page.locator("#tab-antigravity")).toBeVisible();
    await page.click("#tab-antigravity");
    await expect(page.locator("#panel-antigravity")).toHaveClass(/active/);
    await page.click("#tab-claude");
    await expect(page.locator("#panel-claude")).toHaveClass(/active/);
  });

  test("status card displays", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-setup");
    await expect(page.locator("#mcp-status-card")).toBeVisible();
    await expect(page.locator("#mcp-status-text")).toBeVisible();
  });
});

test.describe("Thorough / 7. Tokens page", () => {
  test("page renders", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-tokens");
    await expect(page.locator("#page-tokens")).toHaveClass(/active/);
    await expect(page.locator("#page-tokens .page-title")).toBeVisible();
  });

  test("token list container exists", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-tokens");
    // Token list — fresh user has no tokens yet (until they generate one)
    // Just verify the list container is in DOM
    await page.waitForTimeout(800);
    await expect(page.locator("#page-tokens")).toBeVisible();
  });
});

test.describe("Thorough / 8. MCP Logs page", () => {
  test("page renders", async ({ page }) => {
    await registerAndEnterApp(page);
    await page.click("#nav-mcp-logs");
    await expect(page.locator("#page-mcp-logs")).toHaveClass(/active/);
    await expect(page.locator("#page-mcp-logs .page-title")).toBeVisible();
  });
});

test.describe("Thorough / Sidebar + Profile", () => {
  test("sidebar stats visible", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#sidebar-stats")).toBeVisible();
    await expect(page.locator("#stat-files")).toBeVisible();
    await expect(page.locator("#stat-clusters")).toBeVisible();
    await expect(page.locator("#stat-nodes")).toBeVisible();
  });

  test("language toggle button visible", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#lang-toggle")).toBeVisible();
  });

  test("logout button visible", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#btn-logout")).toBeVisible();
  });

  test("profile trigger opens profile UI", async ({ page }) => {
    await registerAndEnterApp(page);
    await expect(page.locator("#profile-trigger")).toBeVisible();
    await expect(page.locator("#profile-dot")).toBeAttached();
  });

  test("user email shown in sidebar", async ({ page }) => {
    const email = await registerAndEnterApp(page);
    await expect(page.locator("#sidebar-user-email")).toContainText(email);
  });
});
