# Authentication Flow Analysis - Current State

## Entry Points

### 1. Main Login Route: `/login`
- **Component**: `AuthFlowRouter` (wrapped by `AuthProvider`)
- **Initial State**: `currentFlow = 'email'`
- **Provider Chain**:
  - `KratosProviderRefactored` → `UnifiedAuthProvider` → `AuthProvider`

## Step-by-Step Login Flow (Admin User)

### Phase 1: Email Entry
**Component**: `EmailCodeAuth.jsx`

1. User lands on `/login`
2. `AuthFlowRouter` renders `EmailCodeAuth` component
3. User enters email (e.g., `admin@sting.local`)
4. On submit (`handleEmailSubmit`):
   ```javascript
   // Line 91-92: Initialize Kratos flow
   const flow = await initializeFlow(isAAL2);  // Creates /self-service/login/browser flow

   // Line 95-96: Submit identifier
   identifierFormData.append('identifier', userEmail);

   // Line 104: Submit to Kratos
   const identifierResponse = await submitToFlow(flow, identifierFormData);
   ```

### Phase 2: Code Request
**Component**: `EmailCodeAuth.jsx` (continued)

5. After identifier submission:
   ```javascript
   // Line 110-112: Check for code method availability
   const hasCodeMethod = updatedFlow?.ui?.nodes?.some(
     n => n.attributes?.name === 'method' && n.attributes?.value === 'code'
   );
   ```

6. If code method available:
   ```javascript
   // Line 117-119: Request code
   codeFormData.append('identifier', userEmail);
   codeFormData.append('method', 'code');

   // Line 126: Submit code request
   const codeResponse = await submitToFlow(updatedFlow, codeFormData);
   ```

7. On success: `setStep('code')` - UI changes to code input

### Phase 3: Code Verification
**Component**: `EmailCodeAuth.jsx` (`handleCodeSubmit`)

8. User enters 6-digit code
9. On submit:
   ```javascript
   // Line 227-230: Build verification payload
   formData.append('code', code);
   formData.append('method', 'code');
   formData.append('identifier', userEmail);

   // Line 237: Submit to Kratos
   const response = await submitToFlow(flowData, formData);
   ```

### Phase 4: AAL1 Success (Kratos Returns 200)
**Component**: `EmailCodeAuth.jsx` (lines 287-322)

10. **IMPORTANT**: Kratos returns 200 SUCCESS (NOT 422!) because `required_aal: aal1` in kratos.yml
    ```javascript
    // Line 287: Check for success
    if (response.status === 200 || response.data?.state === 'passed_challenge') {

      // Line 291-295: Check for continue_with actions
      const continueWith = response.data?.continue_with;
      if (continueWith) {
        await processContinueWith(continueWith);  // Process Kratos actions
        return;
      }

      // Line 299-322: SECURITY BRIDGE - Check if admin needs AAL2
      if (response.data?.redirect_browser_to) {
        // Check session to see if user is admin
        const sessionCheck = await fetch('/.ory/sessions/whoami');
        const sessionData = await sessionCheck.json();

        // Line 315-321: Override redirect for admin users
        if (sessionData?.identity?.traits?.role === 'admin' &&
            sessionData?.authenticator_assurance_level === 'aal1') {
          // OVERRIDE Kratos redirect - send to security upgrade
          window.location.href = `/security-upgrade?newuser=true&return_to=${returnTo}`;
          return;
        }
      }
    }
    ```

**NOTE**: The 422 code path (lines 240-284) is DEAD CODE - never executed because Kratos only requires AAL1!

### Phase 5A: Continue With Actions (Success Path)
**Component**: `useKratosFlow.js` (`processContinueWith`)

11. If authentication succeeds (lines 287-295):
    ```javascript
    // EmailCodeAuth.jsx Line 291-295
    const continueWith = response.data?.continue_with;
    if (continueWith) {
      await processContinueWith(continueWith);
    }

    // useKratosFlow.js Line 133-138
    if (action.action === 'redirect_browser_to') {
      sessionStorage.setItem('sting_recent_auth', Date.now().toString());
      window.location.href = action.redirect_browser_to;
    }
    ```

### Phase 5B: Protected Route Check
**Component**: `SimpleProtectedRoute.jsx`

12. After redirect to `/dashboard`:
    ```javascript
    // Line 19-21: Get auth state
    const { isAuthenticated, isLoading, identity } = useUnifiedAuth();
    const { session } = useKratos();

    // Line 89: Check authentication with loading safeguard
    if (!isAuthenticated && (hasAnyCookies || isRecentlyAuthenticated) && !isLoading) {
      // Session sync logic...
    }

    // Line 178-184: AAL2 check for admin
    if (isAdmin && isDashboardRoute && !hasAAL2) {
      window.location.href = `/security-upgrade?aal2_required=true`;
    }
    ```

### Phase 6: AAL2 Step-Up (Admin Only)
**Component**: `AAL2StepUp.jsx` or `GracefulAAL2StepUp.jsx`

13. Admin redirected to `/security-upgrade` or `/aal2-step-up`
14. User presented with TOTP or Passkey options
15. After AAL2 verification → Dashboard access

## Provider Chain & Session Management

### KratosProviderRefactored
- **Session Check** (line 33-127): `checkSession()`
  - Calls `/api/auth/me` (NOT `/.ory/sessions/whoami` directly)
  - Has AAL2 fallback logic for Flask session (lines 64-114)
  - Force refresh on recent auth (lines 135-146)

### UnifiedAuthProvider
- Wraps KratosProvider
- Adds unified authentication state
- Coordinates between Kratos and Flask sessions

## Critical Files & Their Roles

1. **AuthFlowRouter.jsx**: Main routing logic for auth flows
2. **EmailCodeAuth.jsx**: Email + code authentication UI and logic
3. **useKratosFlow.js**: Kratos API interactions (submitToFlow, processContinueWith)
4. **SimpleProtectedRoute.jsx**: Route protection and AAL2 enforcement
5. **KratosProviderRefactored.jsx**: Session management and state
6. **kratosConfig.js**: API endpoint configuration (MUST use `/api/auth/me`)

## Key Issues Identified

1. **Multiple AAL2 Routes**: Both `/aal2-step-up` and `/security-upgrade` defined
2. **Session Sync Complexity**: Multiple checks and timeouts for session coordination
3. **Mixed Session Management**: Both Kratos and Flask sessions being managed
4. **Redirect Loops**: Complex logic for handling post-auth redirects

## API Endpoints Used

### Frontend → Backend
- `/api/auth/me` - Session check (Flask coordinated)
- `/.ory/self-service/login/browser` - Kratos flow creation
- `/.ory/self-service/login?flow={id}` - Flow submission
- `/api/aal2/verify` - Redis-based AAL2 verification

### Direct Kratos (via proxy)
- `/.ory/sessions/whoami` - Sometimes called directly (should be avoided)

## Session Storage Keys
- `sting_recent_auth` - Timestamp of recent authentication
- `aal1_completed` - AAL1 completion flag
- `aal1_email` - Email used for AAL1
- `sting_last_passkey_user` - Last passkey user

## Current Flow Summary

### For Non-Admin Users:
```
/login → EmailCodeAuth → Enter Email → Request Code → Enter Code → Submit
  ↓
Kratos Validates → Returns 200 SUCCESS (AAL1 achieved)
  ↓
processContinueWith → Redirects to /dashboard
  ↓
SimpleProtectedRoute → User authenticated → Access granted
```

### For Admin Users:
```
/login → EmailCodeAuth → Enter Email → Request Code → Enter Code → Submit
  ↓
Kratos Validates → Returns 200 SUCCESS (AAL1 achieved)
  ↓
Two possible paths:

Path A (If continue_with exists):
  processContinueWith → Sets sting_recent_auth → Redirects to /dashboard
  ↓
  SimpleProtectedRoute checks Redis AAL2 → No AAL2 → Redirect to /security-upgrade

Path B (If redirect_browser_to exists):
  Security Bridge checks session → Admin with AAL1 detected
  ↓
  OVERRIDES Kratos redirect → Goes directly to /security-upgrade
  ↓
  User completes TOTP/Passkey → Flask sets AAL2 in Redis
  ↓
  Access Dashboard
```

## Phase 7: Enrollment Flow (Fresh Admin User)
**Component**: `GracefulAAL2StepUp.jsx`

When a fresh admin user reaches `/security-upgrade?newuser=true`:

1. **Component State** (lines 14-15):
   ```javascript
   const isNewUserFlow = searchParams.get('newuser') === 'true';
   ```

2. **UI Presentation** (lines 95-102):
   - Shows "Enhance Your Security" title for new users
   - Message: "Welcome! Let's set up enhanced security for your admin account"
   - Two options: Passkey or TOTP authentication

3. **Method Selection** (lines 60-75):
   - User clicks Passkey → redirects to `/aal2-verify-passkey`
   - User clicks TOTP → redirects to `/aal2-verify-totp`

4. **Alternative Actions** (lines 181-195):
   - "Go to Settings → Security" button
   - "Go Back" button
   - Note: No "Skip for now" option (handleSkipForNow exists but not exposed)

5. **Security Requirement** (line 197):
   - Message: "For security, AAL2 authentication is required for admin dashboard access"
   - Admin users CANNOT skip AAL2 enrollment

## Enrollment vs Step-Up Detection

The system differentiates between enrollment and step-up based on:

1. **Query Parameters**:
   - `?newuser=true` → Fresh user enrollment flow
   - `?aal2_required=true` → Existing user step-up

2. **Session State**:
   - Fresh install: No AAL2 methods configured
   - Existing user: Has methods but needs verification

3. **UI Differences**:
   - Enrollment: "Enhance Your Security" / Welcome message
   - Step-up: "Enhanced Security Available" / Re-authenticate message

## Complete Flow for Fresh Admin

```
Fresh Install → Create admin@sting.local
  ↓
/login → EmailCodeAuth → Enter Email → Request Code → Enter Code
  ↓
Kratos Returns 200 SUCCESS (AAL1 achieved)
  ↓
Security Bridge detects admin + AAL1 (EmailCodeAuth.jsx:315-321)
  ↓
Redirects to /security-upgrade?newuser=true
  ↓
GracefulAAL2StepUp shows enrollment UI
  ↓
User must choose: Passkey or TOTP
  ↓
Redirects to /aal2-verify-passkey or /aal2-verify-totp
  ↓
User completes verification
  ↓
Flask sets AAL2 in Redis
  ↓
Access Dashboard
```

## Critical Architecture Facts:
1. **Kratos NEVER returns 422** - configured with `required_aal: aal1`
2. **Flask manages ALL AAL2** - via Redis with `/api/aal2/verify`
3. **Security Bridge** - Frontend overrides Kratos redirects for admin users
4. **Two AAL2 check points**:
   - EmailCodeAuth.jsx lines 315-321 (immediate override)
   - SimpleProtectedRoute.jsx lines 54-85 (Redis check)
5. **No Skip Option** - Admin users MUST complete AAL2 enrollment

---
*Generated: September 18, 2025*