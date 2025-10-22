# Authentication Redirect Loop Fix

## Problem
After successful email + code authentication, users were immediately redirected back to login page despite having valid AAL1 session.

## Root Cause Analysis

### The Race Condition
1. User completes auth → `sting_recent_auth` marker is set by useKratosFlow.js
2. User redirects to /dashboard
3. KratosProviderRefactored detects the marker and IMMEDIATELY removes it (line 142)
4. KratosProviderRefactored starts async `checkSession()` call
5. SimpleProtectedRoute renders and checks auth state BEFORE checkSession() completes
6. At this moment:
   - `isAuthenticated` = false (KratosProvider hasn't updated yet)
   - `isRecentlyAuthenticated` = false (marker was just removed)
   - `hasAnyCookies` might be false (cookies not detected properly)
7. Result: Redirect to login

## Fixes Applied

### 1. KratosProviderRefactored.jsx
**Problem**: Removed `sting_recent_auth` marker too early
```javascript
// OLD: Removed marker before checkSession() completed
sessionStorage.removeItem('sting_recent_auth');
checkSession();

// NEW: Only remove after successful session check
checkSession().then(() => {
  console.log('🔄 Session refresh complete, clearing marker');
  sessionStorage.removeItem('sting_recent_auth');
}).catch(() => {
  sessionStorage.removeItem('sting_recent_auth');
});
```

### 2. SimpleProtectedRoute.jsx - Better Cookie Detection
**Problem**: Cookie detection was unreliable
```javascript
// OLD: Simple string check that could fail
const hasKratosCookie = document.cookie.includes('ory_kratos_session');

// NEW: Proper cookie parsing
const cookies = document.cookie.split(';').reduce((acc, cookie) => {
  const [key, value] = cookie.trim().split('=');
  acc[key] = value;
  return acc;
}, {});

const hasKratosCookie = cookies['ory_kratos_session'] &&
                        cookies['ory_kratos_session'].length > 0;
```

### 3. SimpleProtectedRoute.jsx - Stale Marker Cleanup
**Problem**: Old markers could get stuck and cause issues
```javascript
// NEW: Clean up stale auth markers
useEffect(() => {
  if (recentAuth) {
    const authTime = parseInt(recentAuth);
    if (Date.now() - authTime > 30000) { // Clear if older than 30 seconds
      console.log('🧹 Clearing stale auth marker');
      sessionStorage.removeItem('sting_recent_auth');
    }
  }
}, [recentAuth]);
```

### 4. Reduced Auth Sync Timeout
Changed from 5 minutes to 30 seconds for faster detection and cleanup.

## Testing
After applying these fixes:
1. Clear browser state: `sessionStorage.clear(); localStorage.clear()`
2. Navigate to https://localhost:8443/login
3. Enter admin@sting.local
4. Complete email + code authentication
5. Should reach dashboard without redirect loop

## Key Insights
- The `sting_recent_auth` marker acts as a bridge during the async session check
- Removing it too early breaks the bridge before providers can sync
- Cookie detection needs proper parsing to be reliable
- Stale markers must be cleaned up to prevent future issues

---
*Fixed: September 18, 2025*