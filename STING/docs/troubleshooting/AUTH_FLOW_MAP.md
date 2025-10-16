# STING Authentication Flow Map
*Last Updated: September 2025*

## 🎯 Overview
STING uses a **passwordless, multi-factor authentication system** combining:
- Email magic links (OTP codes) via Kratos
- TOTP (Time-based One-Time Password) via authenticator apps
- WebAuthn passkeys for biometric authentication
- Aggressive enrollment for incomplete security configurations

## 📊 Authentication State Machine

```mermaid
graph TD
    Start([User Visits App]) --> Check{Authenticated?}
    Check -->|No| Login[/login]
    Check -->|Yes| RouteProtection{Protected Route?}
    
    RouteProtection -->|No| Access[Access Granted]
    RouteProtection -->|Yes| AdminCheck{Admin User?}
    
    AdminCheck -->|No| Access
    AdminCheck -->|Yes| EnrollmentCheck{TOTP + Passkey?}
    
    EnrollmentCheck -->|Both Present| AAL2Check{AAL2 Active?}
    EnrollmentCheck -->|Missing Either| Enrollment[/enrollment - AGGRESSIVE]
    
    AAL2Check -->|Yes| AdminPanel[Admin Panel Access]
    AAL2Check -->|No| AAL2StepUp[/aal2-step-up]
    
    AAL2StepUp --> AdminPanel
    Enrollment --> EnrollmentCheck
```

## 🔐 Complete Admin Creation Flow

### Phase 1: Account Creation
**Command**: `./manage_sting.sh create admin user@domain.com`

**Backend Process**:
1. `scripts/create-new-admin.py` executes
2. Creates Kratos identity with `role: admin` trait
3. Sends magic link email via Mailpit
4. No Flask user created yet (happens on first login)

### Phase 2: First Login
**Route**: `/login` → `HybridPasswordlessAuth.jsx`

**Flow**:
```
1. User enters email
2. System checks for existing passkeys → None found
3. Sends OTP code to email
4. User enters 6-digit code
5. Kratos session created (AAL1)
6. Flask session sync via `/api/auth/sync-kratos-session`
7. User record created in STING database if new
```

**Critical Code** (HybridPasswordlessAuth.jsx:1367-1383):
```javascript
// AGGRESSIVE ENROLLMENT for admins
if (isAdmin && (!hasPasskey || !hasTOTP)) {
    navigate('/enrollment', { 
        state: { 
            from: 'aggressive',
            hasExistingTOTP: hasTOTP,
            userEmail: userEmail,
            authenticated: true
        }
    });
}
```

### Phase 3: Enrollment (AGGRESSIVE)
**Route**: `/enrollment` → `SimpleEnrollment.jsx`

**TOTP Setup**:
```
1. Generates QR code via Kratos
2. User scans with authenticator app
3. Verifies 6-digit TOTP code
4. Kratos stores TOTP configuration
```

**Passkey Registration** (CURRENTLY BROKEN):
```
Current Implementation:
1. Calls /api/webauthn/register/begin
2. Tries to create Kratos settings flow
3. Fails because it expects different flow type
4. Falls back to Kratos WebAuthn (not configured)

What Should Happen:
1. Generate WebAuthn challenge
2. Browser triggers biometric/security key
3. Store credential in STING database
4. Link to user's Kratos identity
```

### Phase 4: Dashboard Access
**Route**: `/dashboard/*` → Protected by `SimpleProtectedRoute.jsx`

**Current Protection** (SimpleProtectedRoute.jsx:37):
```javascript
if (!isAuthenticated) {
    return <Navigate to="/login" />;
}
// No enrollment check - BUG!
```

**Admin Panel Extra Protection** (MainInterface.js:484):
```javascript
<AAL2ProtectedRoute>
    <AdminPanel />
</AAL2ProtectedRoute>
```

## 🐛 Current Issues & Failure Points

### 1. Passkey Registration Failure
**Location**: `/api/webauthn/register/begin` (line 210-239)
**Issue**: Tries to use Kratos settings flow for WebAuthn
**Error**: Returns flow data but frontend can't process it
**Fix Needed**: Implement native WebAuthn without Kratos dependency

### 2. Dashboard Access Without Complete Enrollment
**Location**: `SimpleProtectedRoute.jsx`
**Issue**: Only checks `isAuthenticated`, not enrollment completion
**Impact**: Admins can access dashboard with only TOTP
**Fix Needed**: Add enrollment completion check

### 3. Database Schema Mismatch
**Tables Missing**:
- `passkey_registration_challenges`
- `passkey_authentication_challenges`
- Other passkey-related tables from migrations 003-005

**Fix Needed**: Apply migrations in order

## 🔄 API Call Sequence

### Successful Login + Enrollment Flow
```
1. POST /self-service/login?flow={id}
   → Creates Kratos session
   
2. POST /api/auth/sync-kratos-session
   → Creates Flask session
   → Returns user data
   
3. GET /api/auth/security-gate/status
   → Checks TOTP/Passkey configuration
   → Returns enrollment requirements
   
4. GET /self-service/settings/browser
   → Gets settings flow for TOTP setup
   
5. POST /self-service/settings?flow={id}
   → Saves TOTP configuration
   
6. POST /api/webauthn/register/begin [FAILS]
   → Should create WebAuthn challenge
   → Currently returns wrong flow type
```

## 🚦 Decision Points & Redirects

### Login Component (HybridPasswordlessAuth)
```javascript
// Line 1356: After successful login
if (!response.data.enrollment_required) {
    // Regular user → Dashboard
    navigate('/dashboard');
} else {
    // Admin without 2FA → Enrollment
    navigate('/enrollment');
}
```

### Enrollment Component (SimpleEnrollment)
```javascript
// Line 523: After both methods configured
if (currentStep === 'complete') {
    navigate('/dashboard');
}

// Line 445: Skip button (when TOTP exists)
if (hasTOTPConfigured) {
    navigate('/dashboard'); // BUG: Shouldn't allow
}
```

### Protected Routes
```javascript
// SimpleProtectedRoute: Basic auth check
// AAL2ProtectedRoute: Admin panel only
// Missing: EnrollmentProtectedRoute
```

## 🔧 Required Fixes

### 1. Apply Database Migrations
```bash
docker exec -i sting-ce-db psql -U postgres < database/migrations/002_kratos_user_models.sql
docker exec -i sting-ce-db psql -U postgres < database/migrations/003_passkey_models.sql
docker exec -i sting-ce-db psql -U postgres < database/migrations/005_update_passkey_models.sql
```

### 2. Fix Passkey Registration
Create new endpoint that:
- Generates proper WebAuthn challenge
- Stores in `passkey_registration_challenges` table
- Validates and stores credential
- Works without Kratos dependency

### 3. Add Dashboard Guard
Create `DashboardEnrollmentGuard.jsx`:
```javascript
if (isAdmin && (!hasPasskey || !hasTOTP)) {
    return <Navigate to="/enrollment" />;
}
```

### 4. Fix Skip Button Logic
Don't allow skipping to dashboard if requirements not met:
```javascript
// Remove or disable skip when incomplete
if (!hasPasskey && isAdmin) {
    // Disable skip button
}
```

## 📝 Testing Checklist

### Manual Test Steps
1. [ ] Create admin: `./manage_sting.sh create admin test@example.com`
2. [ ] Check email in Mailpit (http://localhost:8025)
3. [ ] Login with email + code
4. [ ] Verify redirect to /enrollment
5. [ ] Setup TOTP with authenticator app
6. [ ] Attempt passkey registration (currently fails)
7. [ ] Verify cannot access /dashboard without both factors
8. [ ] Verify /dashboard/admin requires AAL2

### Automated Test Coverage Needed
- `test-admin-creation-flow.js` - Full journey test
- `test-enrollment-guard.js` - Verify protection
- `test-passkey-registration.js` - WebAuthn flow
- `test-aal2-stepup.js` - Admin panel access

## 🏗️ Architecture Notes

### Session Hierarchy
1. **Kratos Session** - Primary authentication (cookie: `ory_kratos_session`)
2. **Flask Session** - Application session (synced from Kratos)
3. **AAL Levels** - aal1 (password/email), aal2 (TOTP/passkey)

### Frontend State Management
- `UnifiedAuthProvider` - Main auth context
- `AAL2Provider` - AAL2 state management
- `KratosProviderRefactored` - Kratos API wrapper

### Backend Coordination
- `/api/auth/me` - Session coordination endpoint
- `auth_middleware.py` - Flask/Kratos sync
- `kratos_session.py` - Session utilities

## ⚠️ Critical Warnings

1. **Never bypass `/api/auth/me`** - Breaks session coordination
2. **AAL2 is currently disabled** in Flask middleware (temporary fix)
3. **Passkey tables must exist** before registration can work
4. **Don't trust `hasWebAuthn` checks** - Often false positives

## 🚀 Quick Fixes for Common Issues

### "Login Loop"
```bash
# Clear sessions and restart
docker restart sting-ce-redis sting-ce-kratos sting-ce-app
```

### "Cannot register passkey"
```bash
# Apply passkey migrations
docker exec -i sting-ce-db psql -U postgres < database/migrations/003_passkey_models.sql
```

### "Stuck at enrollment"
```javascript
// Check console for:
// - 405 errors on /api/webauthn/register/begin
// - Missing Flask session
// - Kratos flow conflicts
```

---

**Remember**: For testing, always start with fresh browser session/incognito after service updates!