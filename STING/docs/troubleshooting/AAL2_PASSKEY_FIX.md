# 🔐 AAL2 Passkey Authentication Fix

## Problem
- **Symptom**: Browser freezes after selecting passkey for AAL2 authentication
- **Cause**: Infinite redirect loop between dashboard and login

## Root Cause Analysis

### Authentication Architecture
- **Kratos**: Handles the actual passkey authentication (but doesn't set AAL2 properly for WebAuthn)
- **Flask**: Manages all AAL2 state via session flags (`aal2_verified`, `aal2_method`, etc.)
- **Frontend**: Must coordinate between the two systems

### The Bug
1. User completes passkey authentication through Kratos
2. Frontend redirects to dashboard WITHOUT telling Flask that AAL2 was completed
3. UnifiedProtectedRoute checks `/api/auth/me` which shows `aal2_verified: false`
4. Redirects back to `/login?aal=aal2`
5. Infinite loop → browser freeze

## The Fix

Added a critical API call after successful Kratos passkey authentication:

```javascript
// In useWebAuthn.js, after Kratos passkey succeeds:
const grantResponse = await fetch('/api/auth/grant-aal2-access', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    method: 'passkey',
    return_to: returnTo
  })
});
```

This tells Flask to set the AAL2 session flags, preventing the redirect loop.

## Files Modified
- `/frontend/src/components/auth/refactored/hooks/useWebAuthn.js` - Added grant-aal2-access call

## Testing
After the frontend rebuild completes:
1. Login with email + code (AAL1)
2. When prompted for AAL2, select passkey
3. Complete passkey authentication
4. Should redirect to dashboard WITHOUT freezing

## Key Learning
Kratos doesn't properly handle AAL2 with WebAuthn in a 2FA configuration. Flask manages all AAL2 state, and the frontend MUST explicitly notify Flask when 2FA is completed via the `/api/auth/grant-aal2-access` endpoint.