import { defineConfig } from '@playwright/test';
import { readFileSync } from 'node:fs';

if (!process.env['JOBHUNTER_E2E_CONFIG'])
  throw new Error('Run backend/scripts/frontend_e2e.py to prepare the isolated API fixture.');
const config = JSON.parse(readFileSync(process.env['JOBHUNTER_E2E_CONFIG'], 'utf8')) as {
  baseURL: string;
};
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  retries: 0,
  reporter: 'list',
  use: {
    baseURL: config.baseURL,
    channel: 'chrome',
    headless: true,
    ignoreHTTPSErrors: true,
    trace: 'off',
    screenshot: 'off',
    viewport: { width: 1440, height: 1000 },
  },
  webServer: {
    command: 'npm run preview',
    url: config.baseURL,
    ignoreHTTPSErrors: true,
    reuseExistingServer: false,
    timeout: 90000,
  },
});
