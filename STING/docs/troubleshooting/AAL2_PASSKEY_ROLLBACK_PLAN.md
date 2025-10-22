# AAL2 Passkey Rollback Plan

## Critical Issue
Chrome browser crashes/freezes when Touch ID prompt appears during AAL2 authentication. Additionally, AAL2 is being auto-granted without actual passkey verification.

## Root Causes Identified

### 1. Browser Crash (FIXED in staged changes)
- **Problematic commit**: cc31d27f6
- **Issue**: `window.oryWebAuthnLogin` override causing race conditions
- **Fix**: Already removed in staged changes

### 2. AAL2 Auto-Grant Without Verification (CURRENT ISSUE)
- **Problem**: Flask AAL2 is granted immediately when passkey button clicked, before actual biometric verification
- **Evidence**: Network throttling shows Flask verified before any Touch ID prompt
- **Suspect**: Missing AAL2PasskeyVerify.jsx and AAL2TOTPVerify.jsx components in current staged changes

## Session/LocalStorage Issues Found

### Problematic Storage Keys:
1. `sessionStorage.setItem('needsAAL2Redirect', 'true')` - Forces AAL2 redirect
2. `sessionStorage.setItem('aalCheckCompleted', 'true')` - Prevents AAL2 re-check
3. `sessionStorage.setItem('aal2_verified', 'true')` - Auto-grants AAL2 (KEY ISSUE)

### Clear Browser State Script
```javascript
// Run in browser console to reset AAL2 state
sessionStorage.removeItem('needsAAL2Redirect');
sessionStorage.removeItem('aalCheckCompleted');
sessionStorage.removeItem('aal2_verified');
sessionStorage.removeItem('aal2_setup_complete');
sessionStorage.removeItem('aal2_return_url');
localStorage.removeItem('sting-aal2-preference');
console.log('✅ AAL2 state cleared');
```

## Working State Reference
- **Last working commit**: 28403cb65 (August 29, 2025) - "Passkey worked"
- **Key difference**: No AAL2PasskeyVerify.jsx component existed
- **Working flow**: AAL2StepUp → Direct Flask endpoint → Actual passkey prompt

## Current Routing Architecture

### Routes (from AuthenticationWrapper.jsx):
```javascript
<Route path="/security-upgrade" element={<GracefulAAL2StepUp />} />  // New graceful flow
<Route path="/aal2-step-up" element={<AAL2StepUp />} />             // Original strict flow
<Route path="/aal2-verify-passkey" element={<AAL2PasskeyVerify />} /> // Missing in staged
```

### Flow Issue:
1. Admin redirected to `/security-upgrade?aal2_required=true`
2. GracefulAAL2StepUp shows passkey option
3. Click passkey → routes to `/aal2-verify-passkey`
4. AAL2PasskeyVerify.jsx missing or auto-grants without verification

## Fix Requirements After Reinstall

### 1. Restore Proper Passkey Verification
Instead of auto-granting AAL2, trigger actual Kratos WebAuthn ceremony:

```javascript
// AAL2PasskeyVerify.jsx should:
// 1. Initialize Kratos settings flow (NOT login flow with aal=aal2)
const settingsFlow = await fetch('/.ory/self-service/settings/browser', {
  method: 'GET',
  credentials: 'include'
});

// 2. Trigger WebAuthn ceremony
// 3. Wait for actual biometric verification
// 4. ONLY THEN grant Flask AAL2
```

### 2. Fix UnifiedProtectedRoute.jsx AAL2 Check
The current logic at lines 309-349 needs adjustment:
- Don't force immediate redirect with `window.location.href = '/aal2'`
- Use React Router navigation
- Clear stale session storage properly

### 3. Architecture Reminders
- **Flask manages AAL2**, NOT Kratos
- Kratos only validates credentials at AAL1 level
- Flask elevates session to AAL2 after successful verification
- NEVER use `?aal=aal2` parameter (causes Kratos enforcement)

## Components to Review Post-Reinstall

1. **AAL2StepUp.jsx** - Currently uses PasskeyManagerDirect (working)
2. **GracefulAAL2StepUp.jsx** - Check if exists and routing logic
3. **AAL2PasskeyVerify.jsx** - MUST be recreated with proper verification
4. **AAL2TOTPVerify.jsx** - MUST be recreated for TOTP flow

## Testing Checklist

1. [ ] Clear all browser storage before testing
2. [ ] Login as admin@sting.local
3. [ ] Verify redirect to `/security-upgrade` or `/aal2-step-up`
4. [ ] Click passkey button
5. [ ] Verify Touch ID/biometric prompt appears
6. [ ] Verify prompt doesn't auto-dismiss
7. [ ] Complete biometric verification
8. [ ] Verify Flask AAL2 granted AFTER verification
9. [ ] Access dashboard successfully

## Unrelated Features to Preserve

When fixing AAL2, preserve these working features:
- Email + code authentication (AAL1)
- Knowledge service authentication
- PII integration enhancements
- Database migrations
- Docker/Headscale configurations

## Emergency Recovery

If AAL2 issues persist after reinstall:
1. Disable AAL2 enforcement in Flask middleware (app/__init__.py:295)
2. Use `./manage_sting.sh create admin` to create fresh admin
3. Avoid configuring 2FA through Settings UI (creates infinite loops)

## Key Insight
The system worked on Aug 29 without AAL2PasskeyVerify.jsx. The simpler architecture of AAL2StepUp directly calling Flask endpoints was more reliable than the current multi-component flow.

---
*Generated: November 2024*
*Issue: Chrome crashes with Touch ID, AAL2 auto-granted without verification*