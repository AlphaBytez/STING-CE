# STING Testing Infrastructure

This document describes the comprehensive testing infrastructure for STING Community Edition.

## 🎭 Playwright End-to-End Testing

STING includes a robust Playwright-based testing suite for automated browser testing, UI auditing, and authentication flow validation.

### Quick Start

```bash
# Install dependencies
npm install playwright

# Install browsers
playwright install chromium firefox

# Run authentication flow test
node scripts/test-sting-playwright.js

# Run complete auth flow with email code extraction
node scripts/test-full-auth-flow.js

# Investigate Kratos form issues
node scripts/investigate-kratos-issue.js
```

### Test Scripts Overview

| Script | Purpose | Features |
|--------|---------|----------|
| `test-sting-playwright.js` | Basic authentication flow testing | SSL bypass, form detection, screenshots |
| `test-full-auth-flow.js` | Complete login flow with email codes | Mailpit integration, automatic code extraction |
| `investigate-kratos-issue.js` | Deep debugging for form submission issues | Network monitoring, CSRF validation, detailed logging |

### Key Features

#### 🔐 SSL Certificate Handling
- Automatic bypass of self-signed certificates
- Support for both HTTP and HTTPS
- Fallback mechanisms for certificate issues

#### 📧 Email Integration
- Automatic email code extraction from Mailpit
- Real-time email monitoring during tests
- Support for magic link workflows

#### 🖼️ Visual Testing
- Automatic screenshot capture at key steps
- Full-page screenshots for debugging
- Before/after state comparison

#### 🌐 Network Monitoring
- Complete request/response logging
- CSRF token validation
- Form data inspection
- Error response analysis

### Configuration

#### Browser Settings
```javascript
const browser = await chromium.launch({ 
  headless: false,  // Show browser for debugging
  ignoreHTTPSErrors: true,
  args: [
    '--ignore-ssl-errors=yes',
    '--ignore-certificate-errors',
    '--allow-running-insecure-content',
    '--disable-web-security',
    '--allow-insecure-localhost'
  ]
});
```

#### Context Configuration
```javascript
const context = await browser.newContext({
  ignoreHTTPSErrors: true,
  acceptDownloads: true,
  bypassCSP: true
});
```

### Debugging Features

#### Debug Mode
Enable comprehensive logging by setting:
```javascript
localStorage.setItem('aal_debug', 'true');
```

#### Session Storage Management
Tests automatically clear stale session storage to prevent authentication loops:
```javascript
sessionStorage.clear();
sessionStorage.removeItem('needsAAL2Redirect');
sessionStorage.removeItem('aalCheckCompleted');
```

## 📊 Test Outputs

### Screenshots
- `sting-01-homepage.png` - Initial page load
- `sting-02-login-page.png` - Login form state
- `sting-03-after-submit.png` - Post-submission state
- `auth-*-*.png` - Authentication flow stages
- `kratos-*-*.png` - Kratos debugging screenshots

### Reports
- `kratos-investigation-report.json` - Detailed network and form analysis
- Browser console logs with STING debug messages
- Network request/response logs

## 🧪 Testing Scenarios

### Authentication Flow Testing
1. **Login Form Validation**
   - Email input detection
   - Form submission handling
   - CSRF token validation

2. **Magic Link Flow**
   - Email code generation
   - Automatic code extraction
   - Code verification

3. **Enrollment Flow**
   - Redirect to enrollment after authentication
   - SimpleEnrollment component loading
   - 2FA setup validation

4. **Session Management**
   - SessionStorage state clearing
   - AAL2 redirect prevention
   - Login loop detection

### Common Issues Detected
- Missing CSRF tokens
- Invalid flow IDs
- Network connectivity issues
- Session storage corruption
- Certificate validation errors

## 🚀 CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Playwright Tests
  run: |
    npm install playwright
    playwright install chromium
    node scripts/test-sting-playwright.js
  env:
    STING_BASE_URL: https://localhost:8443
```

### Docker Testing
```bash
# Run tests in Docker container
docker run --rm -v $(pwd):/workspace \
  --network sting_local \
  mcr.microsoft.com/playwright:focal \
  /bin/bash -c "cd /workspace && node scripts/test-sting-playwright.js"
```

## 🔧 Troubleshooting

### Common Issues

#### Browser Launch Fails
```bash
# Install missing dependencies
playwright install-deps chromium
```

#### Certificate Errors
- Tests include comprehensive SSL bypass
- Check browser args configuration
- Verify ignoreHTTPSErrors is enabled

#### Form Submission Fails
- Check CSRF tokens in network logs
- Verify Kratos flow initialization
- Review browser console for JavaScript errors

#### Email Code Extraction Fails
- Ensure Mailpit is running on port 8026
- Check email delivery in Mailpit UI
- Verify regex pattern for code extraction

### Debug Commands

```bash
# Check Playwright installation
playwright --version

# List installed browsers
playwright list-browsers

# Run with debug logging
DEBUG=playwright:* node scripts/test-sting-playwright.js

# Check Mailpit API
curl http://localhost:8026/api/v1/messages
```

## 📁 File Organization

For STING Community Edition, tests will be organized as:

```
tests/
├── e2e/
│   ├── auth/
│   │   ├── login-flow.spec.js
│   │   ├── enrollment.spec.js
│   │   └── aal2-stepup.spec.js
│   ├── ui/
│   │   ├── dashboard.spec.js
│   │   └── navigation.spec.js
│   └── api/
│       └── endpoints.spec.js
├── utils/
│   ├── mailpit.js
│   ├── browser-setup.js
│   └── test-helpers.js
└── config/
    ├── playwright.config.js
    └── test-data.json
```

## 📚 Additional Resources

- [Playwright Documentation](https://playwright.dev/)
- [STING Authentication Guide](./AUTHENTICATION.md)
- [Mailpit API Documentation](https://mailpit.axllent.org/docs/api/)
- [Kratos Self-Service API](https://www.ory.sh/docs/kratos/reference/api)

---

**Note**: This testing infrastructure was developed to solve persistent authentication issues and provides comprehensive debugging capabilities for STING Community Edition development.