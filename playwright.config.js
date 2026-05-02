// @ts-check
const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/e2e-ui",
  timeout: 30000,
  expect: { timeout: 10000 },
  fullyParallel: false, // sequential — tests share auth state
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.PDB_TEST_URL || "https://personaldatabank.fly.dev",
    screenshot: "only-on-failure",
    trace: "on-first-retry",
    viewport: { width: 1366, height: 768 },
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
});
