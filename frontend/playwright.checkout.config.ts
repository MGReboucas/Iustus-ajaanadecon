import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "../tests/e2e", testMatch: "checkout.spec.cjs", workers: 1, timeout: 45000,
  use: { baseURL: "http://localhost:3022", browserName: "chromium", channel: process.env.PLAYWRIGHT_CHANNEL || "chrome", trace: "off", screenshot: "off" },
  reporter: "list",
  webServer: { command: "npm run dev -- --port 3022", url: "http://localhost:3022/checkout", reuseExistingServer: false, timeout: 60000 },
});
