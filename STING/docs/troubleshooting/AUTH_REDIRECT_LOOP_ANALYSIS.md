# Authentication Redirect Loop - Root Cause Analysis

## The Infinite Loop Pattern

After successful email+code authentication:
1. User completes authentication, Kratos sets `sting_recent_auth` marker
2. Kratos redirects to `/dashboard`
3. SimpleProtectedRoute renders, sees marker + cookies but `isAuthenticated=false`
4. Shows loading screen: "Authentication provider not ready"
5. KratosProviderRefactored's useEffect detects marker and removes it
6. KratosProviderRefactored calls checkSession()
7. checkSession() makes async call to `/api/auth/me`
8. **CRITICAL**: While waiting for response, SimpleProtectedRoute keeps checking
9. SimpleProtectedRoute now sees: no marker (removed), `isAuthenticated=false`
10. Redirects to login OR shows infinite loading

## The Core Problem

There are TWO separate issues creating this loop:

### Issue 1: Response Structure Mismatch
KratosProviderRefactored expects:
```javascript
response.data.identity  // Kratos structure
```

But Flask `/api/auth/me` returns:
```javascript
response.data.authenticated  // boolean
response.data.user          // user object
```

Result: checkSession() never sets identity, so `isAuthenticated` stays false forever.

### Issue 2: Race Condition with Marker Removal
The `sting_recent_auth` marker is removed BEFORE authentication completes:
- Marker removed immediately on detection
- checkSession() is async and takes time
- SimpleProtectedRoute sees no marker + no auth = redirect to login

## Why This Keeps Breaking

This architecture has multiple moving parts that must stay synchronized:
1. Kratos session cookies
2. Flask session coordination
3. `sting_recent_auth` sessionStorage marker
4. React context state updates
5. Multiple providers (KratosProvider, UnifiedAuth)
6. Route protection logic

Any change to one component breaks the delicate timing.

## The Solution Applied

### Fix 1: Handle Flask Response Structure
```javascript
// In KratosProviderRefactored.jsx checkSession()
if (response.status === 200 && response.data.authenticated) {
  // Convert Flask response to expected structure
  const user = response.data.user;
  const compatibleIdentity = {
    id: user.kratos_id || user.id,
    traits: {
      email: user.email,
      role: user.role,
      name: user.name
    }
  };
  setIdentity(compatibleIdentity);
  setSession(sessionData);
}
```

### Fix 2: Better Marker Timing
```javascript
// Don't remove marker until AFTER session is established
useEffect(() => {
  const recentAuth = sessionStorage.getItem('sting_recent_auth');
  if (recentAuth && !session && !isLoading) {
    // Check session first, THEN remove marker
    checkSession().then(() => {
      sessionStorage.removeItem('sting_recent_auth');
    });
  }
}, [session, isLoading]); // Add dependencies
```

## Testing Checklist
- [ ] Clear all browser storage
- [ ] Complete email+code auth
- [ ] Verify redirect to dashboard
- [ ] No infinite loading screen
- [ ] No redirect back to login
- [ ] Session properly established

---
*Analysis Date: September 18, 2025*