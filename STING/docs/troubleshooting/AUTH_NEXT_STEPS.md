# Authentication Issues - Status & Next Steps

## Current Status (September 2025)

### ✅ What's Working
1. **Email code flow** - Successfully sends codes via Mailpit
2. **TOTP setup** - Fixed CSRF errors by reverting to `/browser` endpoints
3. **Basic authentication** - Users can login with email + code

### ❌ Remaining Issue
**After adding a passkey, user is redirected back to login** instead of continuing to dashboard
- This suggests the session is being invalidated or not properly elevated after passkey registration
- The passkey registration succeeds but the session state doesn't reflect it

## Root Cause Analysis

### The Core Problem
STING has **two parallel WebAuthn/Passkey systems** that are conflicting:
1. **Kratos native WebAuthn** (via `.ory` endpoints)
2. **Custom WebAuthn implementation** (via `/api/webauthn/*` endpoints)

### Why It Redirects to Login After Passkey Registration
When a user registers a passkey:
1. Passkey gets registered (likely in custom system)
2. **Session doesn't get updated to reflect the new authentication method**
3. The enrollment completion handler redirects to dashboard
4. Dashboard protection checks session, finds it insufficient
5. User gets bounced back to login page

This is likely happening in the enrollment flow completion logic or session update after passkey registration.

## Technical Details

### Endpoint Confusion
```
Kratos WebAuthn:
- /.ory/self-service/login/browser (with webauthn method)
- /.ory/self-service/settings/browser (for registration)

Custom WebAuthn:
- /api/webauthn/register/begin
- /api/webauthn/register/complete
- /api/webauthn/authenticate/begin
- /api/webauthn/authenticate/complete
```

### Session Coordination Issues
- Flask sessions (`/api/auth/me`)
- Kratos sessions (`/.ory/sessions/whoami`)
- These need to stay synchronized but often diverge

## Next Steps - Recommended Approach

### Option 1: Use Kratos WebAuthn Exclusively (Recommended)
**Pros:** Single source of truth, less complexity
**Cons:** Need to migrate existing passkeys

1. **Disable custom WebAuthn endpoints**
   - Comment out routes in `/app/routes/webauthn_api_routes.py`
   - Remove custom passkey UI components

2. **Use only Kratos WebAuthn flows**
   - Modify `HybridPasswordlessAuth.jsx` to use Kratos WebAuthn
   - Update `WebAuthnPrompt.jsx` to work with Kratos responses

3. **Fix session coordination**
   - Ensure `/api/auth/me` properly reflects Kratos WebAuthn status
   - Update middleware to handle Kratos WebAuthn AAL properly

### Option 2: Use Custom WebAuthn Exclusively
**Pros:** More control over the flow
**Cons:** Lose Kratos integration benefits

1. **Disable Kratos WebAuthn**
   - Configure Kratos to not offer WebAuthn as a method
   - Remove WebAuthn from Kratos UI nodes

2. **Enhance custom implementation**
   - Ensure it properly updates Kratos sessions
   - Implement AAL2 elevation via custom passkeys

### Option 3: Clear Separation (Complex but Flexible)
**Pros:** Can use both systems
**Cons:** Most complex to maintain

1. **Define clear boundaries**
   - Kratos: Email + TOTP only
   - Custom: Passkeys only

2. **Create coordination layer**
   - After Kratos auth, check for custom passkeys
   - Elevate session appropriately

## Immediate Debug Steps

Before choosing an approach, gather more information:

```bash
# 1. Check what's in Kratos for admin user
curl -k https://localhost:8443/.ory/identities/admin@sting.local

# 2. Check custom passkey database
docker exec -it sting-ce-db psql -U app_user -d sting_app -c "SELECT * FROM passkeys WHERE user_email='admin@sting.local';"

# 3. Test Kratos WebAuthn directly
curl -k https://localhost:8443/.ory/self-service/login/browser \
  -H "Accept: application/json"
# Look for webauthn in the UI nodes

# 4. Check session state after passkey registration
node scripts/test-session-debug.js

# 5. Check enrollment completion logic
# Look for where the redirect happens after passkey setup
grep -r "enrollment.*complete" frontend/src/components/auth/
```

## Likely Problem Location

The issue is probably in one of these files:
1. **`/frontend/src/components/auth/SimpleEnrollment.jsx`** - Enrollment completion handler
2. **`/frontend/src/auth/UnifiedProtectedRoute.jsx`** - Route protection logic that bounces you back
3. **`/app/routes/webauthn_api_routes.py`** - Backend passkey registration not updating session properly

## Files to Focus On

### Critical Files for Investigation
1. `/frontend/src/components/auth/HybridPasswordlessAuth.jsx` - Main auth component
2. `/frontend/src/components/auth/WebAuthnPrompt.jsx` - Passkey prompt UI
3. `/app/routes/webauthn_api_routes.py` - Custom passkey backend
4. `/app/middleware/auth_middleware.py` - Session coordination
5. `/.ory/kratos/config/kratos.yml` - Kratos WebAuthn config

### Test Scripts Available
- `scripts/test-sting-auth-simple.js` - Basic auth flow test
- `scripts/test-session-debug.js` - Session state inspection
- `scripts/verify-code-input.js` - Full auth flow test

## Recommended Next Session Plan

1. **Investigate current state**
   - Check both passkey stores (Kratos vs custom)
   - Identify which system is trying to handle auth

2. **Choose approach**
   - Based on findings, pick Option 1, 2, or 3

3. **Implement fix**
   - Start with minimal changes
   - Test after each change

4. **Create comprehensive test**
   - Email → Code → Passkey registration → Logout → Passkey login
   - Should complete without errors

## Key Insight
The mixing of `/api` and `/browser` endpoints was just one symptom. The real issue is having two competing WebAuthn systems. Until we pick one and stick with it, these problems will persist.

## Emergency Workaround
If you need to use the system immediately:
1. Don't register passkeys
2. Use email + code + TOTP only
3. This avoids the WebAuthn conflict entirely