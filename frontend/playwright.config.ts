import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "../tests/e2e",
  testMatch: "*.spec.cjs",
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: {
    baseURL: `http://localhost:${process.env.IUSTUS_TEST_WEB_PORT || "3000"}`,
    browserName: "chromium",
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    trace: "off", // Não persistir senhas, chaves MFA ou tokens em traces.
    screenshot: "off",
  },
  reporter: "list",
  webServer: [
    { command: "node ../tests/e2e/server.cjs backend", url: "http://127.0.0.1:8000/api/v1/health/", reuseExistingServer: false, timeout: 30000 },
    { command: "node ../tests/e2e/server.cjs frontend", url: "http://localhost:3000/acessar", reuseExistingServer: false, timeout: 30000 },
  ],
});
