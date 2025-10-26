# 🧪 STING Authentication Manual Test Guide

## Test the Login Redirect Loop Fix

### Pre-Test Setup
1. Open Mailpit: http://localhost:8025 (check for emails)
2. Open STING: https://localhost:8443

### Test Steps

#### Step 1: Navigate to Login
- Go to: https://localhost:8443/login
- ✅ **Expected**: Email input field appears
- ❌ **Failure**: Page doesn't load or no email field

#### Step 2: Enter Admin Email
- Enter: `admin@sting.local`
- Click **Submit** or **Send Code**
- ✅ **Expected**: Code input field appears OR redirect to enrollment
- ❌ **Failure**: Error message or stuck on same page

#### Step 3: Check for Magic Link Code
- Go to Mailpit: http://localhost:8025
- ✅ **Expected**: Email with 6-digit code (e.g., 123456)
- ❌ **Failure**: No email received

#### Step 4: Enter Code (if code input appears)
- Enter the 6-digit code from email
- Click **Verify** or **Submit**
- ✅ **Expected**: Redirect to `/enrollment` (NOT back to `/login`)
- ❌ **Failure**: Redirect loop back to login page

#### Step 5: Test Enrollment Page
- If redirected to `/enrollment`:
- ✅ **Expected**: TOTP setup form or enrollment instructions
- ✅ **Expected**: No login loop - stays on enrollment
- ❌ **Failure**: Redirected back to login

## 🎯 What We're Testing

### ✅ SUCCESS INDICATORS:
- Email code gets sent to Mailpit
- After entering code: **Redirected to `/enrollment`**
- Enrollment page loads without redirecting back to login
- No infinite login redirect loop

### ❌ FAILURE INDICATORS:
- After entering code: **Stays on login page**
- After entering code: **Redirects back to `/login`** 
- Login redirect loop detected
- No email received in Mailpit

## 🔧 Components We Fixed

1. **UnifiedProtectedRoute.jsx**: Fixed condition preventing enrollment redirect
2. **SimpleEnrollment.jsx**: New streamlined enrollment component
3. **securityGateService.js**: Always returns currentMethods object
4. **HybridPasswordlessAuth.jsx**: Added enrollment check after login

## 📊 Test Results

| Step | Expected Result | Actual Result | Status |
|------|----------------|---------------|--------|
| Login page loads | Email input visible | | |
| Email submission | Code input or redirect | | |
| Code verification | Redirect to enrollment | | |
| No login loop | Stay on enrollment | | |

## 🚨 If Test Fails

Run these commands to check logs:
```bash
# Check frontend logs
docker logs sting-ce-frontend --tail 20

# Check app logs  
docker logs sting-ce-app --tail 20

# Check Kratos logs
docker logs sting-ce-kratos --tail 20
```

## ✨ Playwright Alternative

If you want to automate this test later, install a different browser automation tool:
```bash
# Install Selenium WebDriver
pip install selenium webdriver-manager

# Or try a simpler approach
npm install puppeteer-core
```