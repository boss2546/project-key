// @ts-check
// Standalone Playwright config for v7.5.0 frontend tests.
// Uses Python http.server to serve static files (no FastAPI backend needed —
// API calls are mocked by tests via page.route).
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e-ui",
  testMatch: /v7\.5\.0-standalone\.spec\.js/,
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://127.0.0.1:8765",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "python tests/e2e-ui/_static_server.py",
    url: "http://127.0.0.1:8765/legacy/app.html",
    timeout: 10000,
    reuseExistingServer: false,
    stdout: "pipe",
    stderr: "pipe",
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
});
