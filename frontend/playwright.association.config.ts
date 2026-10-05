import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "../tests/e2e", testMatch: "association.spec.cjs", workers: 1, timeout: 120000,
  use: { browserName: "chromium", channel: process.env.PLAYWRIGHT_CHANNEL || "chrome", trace: "off", screenshot: "off" },
  reporter: "list",
  webServer: [
    { command: "node ../tests/e2e/server.cjs backend", url: "http://127.0.0.1:8011/api/v1/health/", reuseExistingServer: false, timeout: 30000 },
    { command: "node ../tests/e2e/server.cjs frontend", url: "http://localhost:3011/acessar", reuseExistingServer: false, timeout: 30000 },
  ],
});
