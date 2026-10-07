import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "../tests/e2e", testMatch: "proposals.spec.cjs", workers: 1, timeout: 45000,
  use: { baseURL: "http://localhost:3023", browserName: "chromium", channel: process.env.PLAYWRIGHT_CHANNEL || "msedge", trace: "off", screenshot: "off" },
  reporter: "list",
  webServer: { command: "npm run dev -- --port 3023", url: "http://localhost:3023/cliente", reuseExistingServer: false, timeout: 60000 },
});
