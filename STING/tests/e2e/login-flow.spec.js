// @ts-check
const { test, expect } = require('@playwright/test');
const axios = require('axios');

/**
 * E2E Test for STING Login Flow with Email Verification
 *
 * This test validates the complete login flow including:
 * 1. Navigation to login page
 * 2. Email submission
 * 3. Extracting verification code from Mailpit
 * 4. Entering code and completing login
 * 5. Verifying dashboard access
 */

// Configuration
const config = {
  stingUrl: process.env.STING_URL || 'https://captain-den.local:8443',
  mailpitUrl: process.env.MAILPIT_URL || 'http://10.0.0.158:8025',
  testEmail: process.env.TEST_EMAIL || 'admin@sting.local',
  maxCodeWaitTime: 30000, // 30 seconds
  codeCheckInterval: 2000, // 2 seconds
};

/**
 * Extract verification code from Mailpit
 * @param {string} email - Email address to check for
 * @param {Date} afterTime - Only check emails after this time
 * @returns {Promise<string|null>} Verification code or null
 */
async function getVerificationCodeFromMailpit(email, afterTime) {
  try {
    console.log(`[Mailpit] Checking for emails to ${email}...`);

    // Get all messages from Mailpit
    const response = await axios.get(`${config.mailpitUrl}/api/v1/messages`);

    if (!response.data || !response.data.messages) {
      console.log('[Mailpit] No messages found');
      return null;
    }

    // Find the most recent email to our test address after the specified time
    const messages = response.data.messages
      .filter(msg => {
        const toAddress = msg.To && msg.To[0] && msg.To[0].Address;
        const msgTime = new Date(msg.Created);
        return toAddress === email && msgTime > afterTime;
      })
      .sort((a, b) => new Date(b.Created) - new Date(a.Created));

    if (messages.length === 0) {
      console.log('[Mailpit] No matching messages found');
      return null;
    }

    const latestMessage = messages[0];
    console.log(`[Mailpit] Found message: ${latestMessage.Subject}`);
    console.log(`[Mailpit] Snippet: ${latestMessage.Snippet}`);

    // Get full message content
    const messageDetail = await axios.get(
      `${config.mailpitUrl}/api/v1/message/${latestMessage.ID}`
    );

    // Extract code from HTML or text content
    const htmlContent = messageDetail.data.HTML || '';
    const textContent = messageDetail.data.Text || latestMessage.Snippet || '';

    // Try multiple regex patterns to extract the code
    const patterns = [
      /code:\s*(\d{6})/i,           // "code: 123456"
      /following code:\s*(\d{6})/i, // "following code: 123456"
      /code is:\s*(\d{6})/i,        // "code is: 123456"
      /(\d{6})/,                     // Any 6-digit number
    ];

    for (const pattern of patterns) {
      const matchHtml = htmlContent.match(pattern);
      if (matchHtml && matchHtml[1]) {
        console.log(`[Mailpit] ✅ Extracted code from HTML: ${matchHtml[1]}`);
        return matchHtml[1];
      }

      const matchText = textContent.match(pattern);
      if (matchText && matchText[1]) {
        console.log(`[Mailpit] ✅ Extracted code from text: ${matchText[1]}`);
        return matchText[1];
      }
    }

    console.log('[Mailpit] ⚠️ Could not extract code from message');
    console.log('[Mailpit] HTML:', htmlContent.substring(0, 200));
    console.log('[Mailpit] Text:', textContent.substring(0, 200));

    return null;
  } catch (error) {
    console.error('[Mailpit] Error fetching code:', error.message);
    return null;
  }
}

/**
 * Wait for verification code to arrive in Mailpit
 * @param {string} email - Email address to check
 * @param {Date} afterTime - Only check emails after this time
 * @returns {Promise<string>} Verification code
 */
async function waitForVerificationCode(email, afterTime) {
  const startTime = Date.now();

  while (Date.now() - startTime < config.maxCodeWaitTime) {
    const code = await getVerificationCodeFromMailpit(email, afterTime);

    if (code) {
      return code;
    }

    console.log(`[Mailpit] Waiting for code... (${Math.round((Date.now() - startTime) / 1000)}s elapsed)`);
    await new Promise(resolve => setTimeout(resolve, config.codeCheckInterval));
  }

  throw new Error(`Verification code not received within ${config.maxCodeWaitTime / 1000} seconds`);
}

test.describe('STING Login Flow', () => {
  // Configure browser to ignore HTTPS certificate errors (self-signed certs)
  test.use({
    ignoreHTTPSErrors: true,
  });

  test('should complete full login flow with email verification', async ({ page }) => {
    console.log('\n=== Starting STING Login Test ===\n');
    console.log(`STING URL: ${config.stingUrl}`);
    console.log(`Mailpit URL: ${config.mailpitUrl}`);
    console.log(`Test Email: ${config.testEmail}`);
    console.log('');

    // Record the time before we start (for filtering Mailpit messages)
    const testStartTime = new Date();

    // Step 1: Navigate to login page
    console.log('[Test] Step 1: Navigating to login page...');
    await page.goto(`${config.stingUrl}/login`);

    // Wait for page to load and take screenshot
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'test-results/01-login-page.png', fullPage: true });
    console.log('[Test] ✅ Login page loaded');

    // Verify we're on the login page
    await expect(page).toHaveURL(/.*\/login/);

    // Step 2: Enter email address
    console.log(`[Test] Step 2: Entering email address: ${config.testEmail}`);

    // Try multiple selectors to find the email input
    const emailSelectors = [
      'input[name="identifier"]',
      'input[type="email"]',
      'input[placeholder*="email" i]',
      'input#identifier',
      'input[autocomplete="email"]',
    ];

    let emailInput = null;
    for (const selector of emailSelectors) {
      try {
        emailInput = await page.locator(selector).first();
        if (await emailInput.isVisible({ timeout: 2000 })) {
          console.log(`[Test] Found email input with selector: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!emailInput || !(await emailInput.isVisible())) {
      await page.screenshot({ path: 'test-results/error-no-email-input.png', fullPage: true });
      throw new Error('Could not find email input field');
    }

    await emailInput.fill(config.testEmail);
    await page.screenshot({ path: 'test-results/02-email-entered.png', fullPage: true });
    console.log('[Test] ✅ Email entered');

    // Step 3: Submit the form
    console.log('[Test] Step 3: Submitting login form...');

    // Record time just before submission (for Mailpit filtering)
    const beforeSubmitTime = new Date();

    // Try multiple methods to submit
    const submitSelectors = [
      'button[type="submit"]',
      'button:has-text("Continue")',
      'button:has-text("Log in")',
      'button:has-text("Sign in")',
      'input[type="submit"]',
    ];

    let submitted = false;
    for (const selector of submitSelectors) {
      try {
        const submitBtn = await page.locator(selector).first();
        if (await submitBtn.isVisible({ timeout: 2000 })) {
          console.log(`[Test] Found submit button with selector: ${selector}`);
          await submitBtn.click();
          submitted = true;
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!submitted) {
      // Try pressing Enter as fallback
      await emailInput.press('Enter');
      console.log('[Test] Submitted form with Enter key');
    }

    // Wait for navigation or code input page
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'test-results/03-after-submit.png', fullPage: true });
    console.log('[Test] ✅ Form submitted');

    // Step 4: Get verification code from Mailpit
    console.log('[Test] Step 4: Waiting for verification code from Mailpit...');
    const verificationCode = await waitForVerificationCode(config.testEmail, beforeSubmitTime);
    console.log(`[Test] ✅ Verification code received: ${verificationCode}`);

    // Step 5: Enter verification code
    console.log('[Test] Step 5: Entering verification code...');

    // Try multiple selectors for code input
    const codeSelectors = [
      'input[name="code"]',
      'input[type="text"][autocomplete="one-time-code"]',
      'input[inputmode="numeric"]',
      'input[placeholder*="code" i]',
      'input#code',
    ];

    let codeInput = null;
    for (const selector of codeSelectors) {
      try {
        codeInput = await page.locator(selector).first();
        if (await codeInput.isVisible({ timeout: 5000 })) {
          console.log(`[Test] Found code input with selector: ${selector}`);
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!codeInput || !(await codeInput.isVisible())) {
      await page.screenshot({ path: 'test-results/error-no-code-input.png', fullPage: true });
      throw new Error('Could not find verification code input field');
    }

    await codeInput.fill(verificationCode);
    await page.screenshot({ path: 'test-results/04-code-entered.png', fullPage: true });
    console.log('[Test] ✅ Verification code entered');

    // Step 6: Submit verification code
    console.log('[Test] Step 6: Submitting verification code...');

    // Try to find and click submit button
    submitted = false;
    for (const selector of submitSelectors) {
      try {
        const submitBtn = await page.locator(selector).first();
        if (await submitBtn.isVisible({ timeout: 2000 })) {
          await submitBtn.click();
          submitted = true;
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (!submitted) {
      await codeInput.press('Enter');
    }

    // Wait for successful login redirect
    await page.waitForLoadState('networkidle');
    await page.screenshot({ path: 'test-results/05-after-code-submit.png', fullPage: true });
    console.log('[Test] ✅ Verification code submitted');

    // Step 7: Verify we're logged in and on the dashboard
    console.log('[Test] Step 7: Verifying successful login...');

    // Wait a bit for any redirects
    await page.waitForTimeout(2000);

    const currentUrl = page.url();
    console.log(`[Test] Current URL: ${currentUrl}`);

    // Check if we're on dashboard or post-login page
    const successPatterns = ['/dashboard', '/post-registration', '/home'];
    const isLoggedIn = successPatterns.some(pattern => currentUrl.includes(pattern));

    if (!isLoggedIn) {
      await page.screenshot({ path: 'test-results/error-not-logged-in.png', fullPage: true });
      console.error(`[Test] ❌ Login failed - Current URL: ${currentUrl}`);
      throw new Error(`Login did not redirect to expected page. Current URL: ${currentUrl}`);
    }

    await page.screenshot({ path: 'test-results/06-logged-in.png', fullPage: true });
    console.log('[Test] ✅ Successfully logged in!');
    console.log(`[Test] Final URL: ${currentUrl}`);

    // Step 8: Additional verification - check for user-specific elements
    console.log('[Test] Step 8: Verifying dashboard elements...');

    // Look for common dashboard elements (adjust based on your actual UI)
    const dashboardIndicators = [
      'nav', // Navigation bar
      '[data-testid="user-menu"]',
      'button:has-text("Logout")',
      'a:has-text("Dashboard")',
    ];

    let foundDashboardElement = false;
    for (const selector of dashboardIndicators) {
      try {
        const element = await page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 })) {
          console.log(`[Test] ✅ Found dashboard element: ${selector}`);
          foundDashboardElement = true;
          break;
        }
      } catch (e) {
        continue;
      }
    }

    if (foundDashboardElement) {
      console.log('[Test] ✅ Dashboard elements verified');
    } else {
      console.log('[Test] ⚠️ Could not verify specific dashboard elements (may be normal)');
    }

    // Final screenshot
    await page.screenshot({ path: 'test-results/07-final-state.png', fullPage: true });

    console.log('\n=== ✅ STING Login Test PASSED ===\n');
  });

  test('should show error for invalid email format', async ({ page }) => {
    console.log('\n=== Testing Invalid Email Format ===\n');

    await page.goto(`${config.stingUrl}/login`);
    await page.waitForLoadState('networkidle');

    const emailInput = await page.locator('input[name="identifier"], input[type="email"]').first();
    await emailInput.fill('not-an-email');

    const submitBtn = await page.locator('button[type="submit"]').first();
    await submitBtn.click();

    // Check for error message
    const hasError = await page.locator('text=/invalid|error|please enter a valid/i').isVisible({ timeout: 5000 });

    await page.screenshot({ path: 'test-results/invalid-email-error.png', fullPage: true });

    expect(hasError).toBeTruthy();
    console.log('[Test] ✅ Invalid email validation works');
  });
});

// Export for use in other tests
module.exports = {
  getVerificationCodeFromMailpit,
  waitForVerificationCode,
  config,
};
