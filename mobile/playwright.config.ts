import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/ui',
  fullyParallel: false,
  workers: 1,
  timeout: 45000,
  use: { baseURL: 'http://127.0.0.1:8082', trace: 'retain-on-failure', ...devices['iPhone 13'], defaultBrowserType: 'chromium', channel: process.env.PLAYWRIGHT_CHANNEL },
  webServer: {
    command: 'npm run web -- --port 8082',
    url: 'http://127.0.0.1:8082',
    reuseExistingServer: false,
    timeout: 120000,
    env: { EXPO_PUBLIC_API_ORIGIN: 'https://mobile-api.example.test', CI: '1' },
  },
});
