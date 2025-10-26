// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * Playwright configuration for STING E2E tests
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './',

  // Maximum time one test can run
  timeout: 90 * 1000, // 90 seconds (to allow time for email delivery)

  expect: {
    timeout: 10000, // 10 seconds for expect assertions
  },

  // Run tests in files in parallel
  fullyParallel: false, // Sequential for login tests to avoid race conditions

  // Fail the build on CI if you accidentally left test.only in the source code
  forbidOnly: !!process.env.CI,

  // Retry on CI only
  retries: process.env.CI ? 2 : 1,

  // Number of workers (use 1 for sequential login tests)
  workers: 1,

  // Reporter to use
  reporter: [
    ['html', { outputFolder: 'playwright-report', open: 'never' }],
    ['list'],
    ['json', { outputFile: 'test-results/results.json' }],
  ],

  // Shared settings for all projects
  use: {
    // Base URL for tests
    baseURL: process.env.STING_URL || 'https://captain-den.local:8443',

    // Collect trace when retrying the failed test
    trace: 'on-first-retry',

    // Screenshot on failure
    screenshot: 'only-on-failure',

    // Video on failure
    video: 'retain-on-failure',

    // Ignore HTTPS errors (self-signed certificates)
    ignoreHTTPSErrors: true,

    // Viewport size
    viewport: { width: 1280, height: 720 },

    // Default timeout for actions (click, fill, etc.)
    actionTimeout: 10000,

    // Default timeout for navigation
    navigationTimeout: 30000,
  },

  // Configure projects for major browsers
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },

    // Uncomment to test on Firefox and Safari
    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },
    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    // Test against mobile viewports
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: { ...devices['iPhone 12'] },
    // },
  ],

  // Output folder for test artifacts
  outputDir: 'test-results/',

  // Web server configuration (if needed)
  // webServer: {
  //   command: 'npm run start',
  //   url: 'https://captain-den.local:8443',
  //   reuseExistingServer: !process.env.CI,
  //   ignoreHTTPSErrors: true,
  // },
});
