# STING E2E Tests

End-to-end tests for STING platform authentication and login flow using Playwright.

## Features

✅ **Complete Login Flow Testing**
- Navigate to login page
- Submit email address
- Extract verification code from Mailpit API
- Enter verification code
- Verify successful dashboard access

✅ **Mailpit Integration**
- Automatically fetches verification codes from Mailpit
- Handles multiple email formats (HTML and text)
- Robust code extraction with multiple regex patterns

✅ **Comprehensive Reporting**
- Screenshots at each step
- HTML test reports
- Video recordings on failure
- Detailed console logging

## Prerequisites

1. **STING Installation Running**
   ```bash
   cd /opt/sting-ce  # or your installation directory
   ./manage_sting.sh start
   ```

2. **Services Must Be Accessible**
   - STING Frontend: `https://captain-den.local:8443` (or your configured hostname)
   - Mailpit API: `http://10.0.0.158:8025` (or your server IP)

3. **Node.js and npm** installed

## Installation

```bash
cd /mnt/c/DevWorld/STING-CE-Public/STING/tests/e2e

# Install dependencies
npm install

# Install Playwright browsers
npx playwright install chromium
```

## Configuration

Tests use environment variables or defaults:

| Variable | Default | Description |
|----------|---------|-------------|
| `STING_URL` | `https://captain-den.local:8443` | STING frontend URL |
| `MAILPIT_URL` | `http://10.0.0.158:8025` | Mailpit API URL |
| `TEST_EMAIL` | `admin@sting.local` | Email address to test |

### Setting Custom Configuration

```bash
# Option 1: Environment variables
export STING_URL=https://your-hostname.local:8443
export MAILPIT_URL=http://your-server-ip:8025
export TEST_EMAIL=test@example.com

# Option 2: Create .env file
cat > .env <<EOF
STING_URL=https://your-hostname.local:8443
MAILPIT_URL=http://your-server-ip:8025
TEST_EMAIL=test@example.com
EOF
```

## Running Tests

### Basic Usage

```bash
# Run all tests (headless)
npm test

# Run with browser visible
npm run test:headed

# Run in debug mode (step through with Playwright Inspector)
npm run test:debug

# Run with UI mode (interactive)
npm run test:ui
```

### Advanced Options

```bash
# Run specific test file
npx playwright test login-flow.spec.js

# Run specific test by name
npx playwright test -g "should complete full login flow"

# Run with specific browser
npx playwright test --project=chromium

# Generate and view test report
npm run test:report
```

## Test Structure

### Main Test: `login-flow.spec.js`

**Test Flow:**
1. Navigate to login page (`/login`)
2. Enter email address
3. Submit form
4. Wait for email in Mailpit (max 30 seconds)
5. Extract verification code from email
6. Enter verification code
7. Submit code
8. Verify redirect to dashboard
9. Check for dashboard UI elements

### Helper Functions

**`getVerificationCodeFromMailpit(email, afterTime)`**
- Fetches messages from Mailpit API
- Filters by recipient email and timestamp
- Extracts 6-digit verification code using regex patterns

**`waitForVerificationCode(email, afterTime)`**
- Polls Mailpit every 2 seconds
- Times out after 30 seconds
- Returns verification code or throws error

## Test Artifacts

All test artifacts are saved to `test-results/`:

```
test-results/
├── 01-login-page.png           # Initial login page
├── 02-email-entered.png        # After entering email
├── 03-after-submit.png         # After form submission
├── 04-code-entered.png         # After entering code
├── 05-after-code-submit.png    # After code submission
├── 06-logged-in.png            # Successful login
├── 07-final-state.png          # Final dashboard state
├── results.json                # Test results JSON
└── videos/                     # Videos (on failure)
```

HTML report: `playwright-report/index.html`

## Troubleshooting

### Test Fails: "Could not find email input field"

**Cause**: Login page UI may have different selectors.

**Solution**: Update selectors in test:
```javascript
const emailSelectors = [
  'input[name="identifier"]',  // Add your actual selector here
  'input[type="email"]',
  // ...
];
```

Check screenshot: `test-results/error-no-email-input.png`

### Test Fails: "Verification code not received"

**Cause**: Email delivery delayed or Mailpit not accessible.

**Solutions:**
1. Check Mailpit is running: `curl http://10.0.0.158:8025/api/v1/messages`
2. Verify email was sent: Visit `http://10.0.0.158:8025` in browser
3. Increase timeout: Edit `maxCodeWaitTime` in config (default 30s)

### Test Fails: "Could not extract code from message"

**Cause**: Email format doesn't match regex patterns.

**Solution**: Check Mailpit UI to see email format, then update regex patterns:
```javascript
const patterns = [
  /code:\s*(\d{6})/i,
  /your code is (\d{6})/i,  // Add your pattern
  // ...
];
```

### Test Fails: "Login did not redirect to expected page"

**Cause**: Login flow changed or hostname mismatch.

**Solutions:**
1. Check actual redirect URL in error screenshot
2. Update success patterns:
   ```javascript
   const successPatterns = ['/dashboard', '/your-page'];
   ```
3. Verify hostname configuration matches test URL

### HTTPS Certificate Errors

**Solution**: Tests already ignore HTTPS errors via `ignoreHTTPSErrors: true`.
If still failing, verify STING is using self-signed certs correctly.

## CI/CD Integration

### GitHub Actions Example

```yaml
name: STING E2E Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd STING/tests/e2e
          npm ci
          npx playwright install --with-deps chromium

      - name: Start STING services
        run: |
          cd STING
          ./manage_sting.sh start
          sleep 30  # Wait for services to be ready

      - name: Run tests
        run: |
          cd STING/tests/e2e
          npm test
        env:
          STING_URL: https://localhost:8443
          MAILPIT_URL: http://localhost:8025
          TEST_EMAIL: admin@sting.local

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: STING/tests/e2e/playwright-report/
```

## Development

### Adding New Tests

Create new test files following the pattern:

```javascript
// @ts-check
const { test, expect } = require('@playwright/test');
const { config } = require('./login-flow.spec.js');

test.describe('My New Test Suite', () => {
  test.use({ ignoreHTTPSErrors: true });

  test('my test case', async ({ page }) => {
    await page.goto(`${config.stingUrl}/my-page`);
    // ... test logic
  });
});
```

### Debugging Tips

1. **Run in headed mode**: See what's happening
   ```bash
   npm run test:headed
   ```

2. **Use Playwright Inspector**: Step through test
   ```bash
   npm run test:debug
   ```

3. **Check screenshots**: Review test-results/*.png

4. **Console logs**: Tests include detailed logging
   ```
   [Test] Step 1: Navigating to login page...
   [Mailpit] Checking for emails...
   ```

5. **Mailpit UI**: Visit http://10.0.0.158:8025 to see emails

## Support

- **GitHub Issues**: https://github.com/AlphaBytez/STING-CE-Public/issues
- **Documentation**: `/mnt/c/DevWorld/STING-CE-Public/STING/docs/`
- **Playwright Docs**: https://playwright.dev/

## License

See main STING project license.
