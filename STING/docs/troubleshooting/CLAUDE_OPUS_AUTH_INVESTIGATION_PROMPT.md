# Authentication System Investigation and Fix Request

## Context
You are investigating a critical authentication issue in STING, a complex web application with a multi-layered authentication system. After weeks of stable authentication, recent changes have caused an infinite loading screen loop after successful login.

## Current Problem
Users successfully authenticate (email + code) but get stuck in an infinite loading screen showing:
```
"Authentication provider not ready but cookies/recent auth detected, waiting..."
```

## Architecture Overview

### Authentication Layers (All Must Coordinate)
1. **Kratos** - Handles AAL1 (email+code) authentication, sets `ory_kratos_session` cookie
2. **Flask Backend** - Coordinates sessions, enriches with STING database data, manages AAL2 via Redis
3. **React Frontend** - Multiple providers and route protection components
4. **Session Markers** - `sting_recent_auth` in sessionStorage bridges async operations

### Critical Architectural Principle
**Flask manages AAL2, NOT Kratos!** This is by design due to Kratos WebAuthn bugs. Kratos is configured with `required_aal: aal1` and NEVER returns 422 or enforces AAL2.

## Key Files to Investigate

### Frontend Components (Order of Importance)
1. `/frontend/src/auth/KratosProviderRefactored.jsx` - Primary auth provider
   - Lines 33-147: `checkSession()` function
   - Lines 156-175: Session refresh logic with `sting_recent_auth` marker
   - **Issue**: Expects `response.data.identity` but Flask returns `response.data.authenticated` and `response.data.user`

2. `/frontend/src/auth/SimpleProtectedRoute.jsx` - Route protection
   - Lines 174-184: Loading screen condition
   - **Issue**: Shows infinite loading when `isAuthenticated=false` but cookies/markers exist

3. `/frontend/src/auth/AuthenticationWrapper.jsx` - Main app wrapper
   - Controls actual routing (NOT AppRoutes.js which is legacy)

4. `/frontend/src/auth/UnifiedAuthProvider.jsx` - State management wrapper
   - Depends on KratosProviderRefactored

### Backend Endpoints
1. `/app/routes/auth_routes.py` - Flask `/api/auth/me` endpoint
   - Returns: `{authenticated: true, user: {...}, session: {...}}`
   - NOT Kratos format

2. `/app/middleware/auth_middleware.py` - Session coordination
   - Handles Flask + Kratos session sync
   - AAL2 enforcement for admins

### Critical Configuration
- `/frontend/src/utils/kratosConfig.js` - MUST use `/api/auth/me` NOT `/.ory/sessions/whoami`
  - Breaking this causes session coordination failure

## Investigation Steps

### 1. Trace Authentication Flow
```javascript
// In browser console during auth:
1. User enters email → Kratos flow initialized
2. User enters code → Kratos validates
3. Kratos redirects to /dashboard with `sting_recent_auth` marker set
4. SimpleProtectedRoute checks `isAuthenticated` (still false)
5. Shows loading screen
6. KratosProviderRefactored detects marker
7. Calls checkSession() → /api/auth/me
8. Response parsing fails or timing issue
9. Infinite loop begins
```

### 2. Check These Specific Timing Issues
- When is `sting_recent_auth` marker removed? (Should be AFTER session established)
- Does `checkSession()` properly set `identity` and `session` state?
- Are useEffect dependencies correct to prevent infinite re-renders?

### 3. Verify Response Handling
The KratosProviderRefactored expects Kratos format but gets Flask format:
```javascript
// Expected (Kratos):
response.data.identity = {
  id: "...",
  traits: { email: "..." }
}

// Actual (Flask):
response.data = {
  authenticated: true,
  user: {
    id: "...",
    email: "...",
    kratos_id: "..."
  }
}
```

## Previous Fix Attempts (Still Broken)

### Attempt 1: Response Adaptation
Added Flask response handling in KratosProviderRefactored.jsx lines 51-82:
```javascript
if (response.status === 200 && response.data.authenticated) {
  const user = response.data.user;
  const compatibleIdentity = {
    id: user.kratos_id || user.id,
    traits: { email: user.email, role: user.role }
  };
  setIdentity(compatibleIdentity);
  setSession(sessionData);
}
```
**Result**: Still infinite loop

### Attempt 2: Marker Timing Fix
Changed marker removal to happen AFTER checkSession():
```javascript
checkSession().then(() => {
  sessionStorage.removeItem('sting_recent_auth');
});
```
**Result**: Still infinite loop

## Root Cause Hypothesis
The issue appears to be a race condition between:
1. SimpleProtectedRoute checking authentication state
2. KratosProviderRefactored updating that state
3. The `sting_recent_auth` marker lifecycle
4. Multiple re-renders triggering repeated checkSession() calls

## Required Fix Approach

### Immediate Fix (Stop the Bleeding)
1. Fix the response format mismatch completely
2. Ensure checkSession() returns and properly sets state
3. Fix useEffect dependencies to prevent infinite calls
4. Ensure marker removal happens at the right time

### Long-term Architectural Cleanup
1. **Remove duplicate providers**: 5+ auth providers doing similar work
2. **Consolidate route protection**: 5+ route protection components
3. **Standardize naming**: KratosProvider vs KratosProviderRefactored confusion
4. **Single source of truth**: One session management approach
5. **Remove race conditions**: Sequential operations where needed

## Testing the Fix
1. Clear all browser storage: `sessionStorage.clear(); localStorage.clear()`
2. Delete all cookies
3. Navigate to https://localhost:8443/login
4. Enter admin@sting.local
5. Complete email+code authentication
6. Should reach dashboard without infinite loading

## Additional Context

### Git History
- Commit `7e7cf947a` (Sept 5): Added loading screen logic
- Commit `2344ee5f3`: "Fix AAL2 passkey" - major provider changes
- Commit `1c8ec24d3`: Marked as "auth broken state"
- Issue introduced when loading screen improvements combined with provider changes

### Component Inventory
**Active**: KratosProviderRefactored, UnifiedAuthProvider, SimpleProtectedRoute
**Legacy**: KratosProvider.jsx, KratosProvider.old.jsx, KratosAuthProvider.jsx
**Experimental**: CleanUnifiedAuthProvider, HybridProtectedRoute

## Success Criteria
1. User can complete email+code auth and reach dashboard
2. No infinite loading screen
3. No console errors about "provider not ready"
4. Session properly established with both Kratos and Flask
5. Works for both regular users and admins

## Questions to Answer
1. Why does the loading screen condition keep triggering?
2. Is checkSession() actually completing successfully?
3. Are React state updates happening in the correct order?
4. Is there a circular dependency causing re-renders?
5. Should we temporarily disable the loading screen as an emergency fix?

Please investigate systematically and provide:
1. Root cause of the infinite loop
2. Minimal fix to restore authentication
3. Architectural recommendations for cleanup
4. Step-by-step implementation plan

Remember: Flask manages AAL2, Kratos only does AAL1. The `/api/auth/me` endpoint is critical for session coordination. Breaking this coordination is what causes the authentication loops.