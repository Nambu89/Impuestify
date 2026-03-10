import { defineConfig } from '@playwright/test';
import * as path from 'path';

const AUTH_DIR = path.join(__dirname, 'tests/e2e/.auth');

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 120000,
  retries: 1,
  reporter: [['list'], ['html', { outputFolder: 'test-results/html', open: 'never' }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'https://impuestify.com',
    screenshot: 'on',
    trace: 'retain-on-failure',
    video: 'off',
    ignoreHTTPSErrors: true,
  },
  projects: [
    // Auth setup — runs first, obtains JWT tokens
    {
      name: 'auth-setup',
      testMatch: /auth\.setup\.ts/,
    },
    // Tests as particular user
    {
      name: 'particular',
      use: {
        browserName: 'chromium',
        channel: 'chrome',
        storageState: path.join(AUTH_DIR, 'particular.json'),
      },
      dependencies: ['auth-setup'],
      testIgnore: /auth\.setup\.ts|qa-session.*autonomo/,
    },
    // Tests as autonomo user
    {
      name: 'autonomo',
      use: {
        browserName: 'chromium',
        channel: 'chrome',
        storageState: path.join(AUTH_DIR, 'autonomo.json'),
      },
      dependencies: ['auth-setup'],
      testMatch: /qa-session.*autonomo|t04/,
    },
  ],
  outputDir: 'test-results/artifacts',
});
