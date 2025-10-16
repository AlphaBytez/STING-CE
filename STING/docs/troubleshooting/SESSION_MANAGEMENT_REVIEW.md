# Session Management Architecture Review

## Current State Analysis (September 18, 2025)

### The Problem
Authentication succeeds but users get stuck in infinite loading screen with "Authentication provider not ready but cookies/recent auth detected, waiting..." message.

### Key Components

#### 1. KratosProviderRefactored.jsx
- **Purpose**: Main authentication provider
- **Session Check**: Calls `/api/auth/me` (Flask endpoint)
- **Expected Response**: `response.data.identity` (Kratos format)
- **Actual Response**: `response.data.authenticated` and `response.data.user` (Flask format)
- **Result**: Never sets identity, `isAuthenticated` stays false

#### 2. SimpleProtectedRoute.jsx
- **Purpose**: Route protection and session sync
- **Loading Screen Added**: Commit 7e7cf947a (Sept 5, 2025)
- **Condition**: Shows loading when cookies/recent auth detected but `isAuthenticated=false`
- **Problem**: Creates infinite loop when provider can't set authentication

#### 3. Session Markers
- **`sting_recent_auth`**: SessionStorage marker for recent authentication
- **Purpose**: Bridge during async session establishment
- **Issue**: Removed too early or not properly detected

### Architecture Issues Identified

1. **Response Format Mismatch**
   - Frontend expects Kratos response structure
   - Backend returns Flask-specific format
   - No adaptation layer between them

2. **Race Conditions**
   - Multiple async operations (checkSession, marker removal, state updates)
   - No proper synchronization between components
   - Timing-dependent behavior

3. **Mixed Session Management**
   - Kratos sessions (cookies)
   - Flask sessions (Redis)
   - React context state
   - SessionStorage markers
   - All must stay synchronized

### Git History Analysis

Key commits that affected session management:
- **cc31d27f6**: Added problematic `window.oryWebAuthnLogin` override
- **2344ee5f3**: "Fix AAL2 passkey authentication" - major KratosProvider changes
- **7e7cf947a**: Added loading screen logic to SimpleProtectedRoute
- **1c8ec24d3**: Marked as "auth broken state"

### The Loading Screen Issue

Introduced in commit 7e7cf947a:
```javascript
// If we have authentication signs but provider says not authenticated, show loading
if (!isAuthenticated && (hasAnyCookies || isRecentlyAuthenticated)) {
  console.log('🔒 Authentication provider not ready...');
  return <ColonyLoadingScreen />;
}
```

This was meant to improve UX but created the infinite loop when combined with the provider's inability to properly set authentication state.

### Root Cause

The session management broke when:
1. Loading screen improvements were added (better UX intent)
2. Provider can't handle Flask response format (integration issue)
3. Marker timing doesn't account for async nature (race condition)

## Recommendations

### Short-term Fix
1. ✅ Adapt Flask response to expected format in KratosProvider
2. ✅ Fix marker removal timing (only after session established)
3. ⚠️ Still experiencing issues - need deeper refactor

### Long-term Solution
1. **Unified Response Format**: Standardize API responses
2. **Single Source of Truth**: One session management approach
3. **Proper State Machine**: Handle all authentication states explicitly
4. **Remove Race Conditions**: Sequential operations where needed

### Testing Requirements
- Clear browser state before testing
- Test with fresh install
- Monitor console for infinite loops
- Verify session establishment
- Check marker lifecycle

---
*Review Date: September 18, 2025*