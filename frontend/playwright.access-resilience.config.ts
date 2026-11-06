import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: '../tests/e2e',
  testMatch: 'access-resilience.spec.cjs',
  workers: 1,
  timeout: 30000,
  use: { baseURL: 'http://localhost:3417', browserName: 'chromium', channel: process.env.PLAYWRIGHT_CHANNEL || undefined, trace: 'off', screenshot: 'off' },
  reporter: 'list',
  webServer: {
    command: 'node node_modules/next/dist/bin/next start --port 3417',
    url: 'http://localhost:3417/acessar', reuseExistingServer: false, timeout: 30000,
  },
});
