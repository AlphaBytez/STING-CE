# Login Flow Cleanup

## Issues Found

1. **Too Many Login Components**: 20+ different login components causing confusion
2. **Dual Auth Checks**: UnifiedAuthProvider checks both Kratos and custom auth
3. **Multiple Redirects**: Various components redirect to different login pages
4. **Enrollment Flow**: UnifiedProtectedRoute redirects to /enrollment for password changes

## Components Archived

### Unused Login Components
- `auth/LoginRedirect.jsx`
- `auth/KratosLogin.jsx`
- `components/auth/PasswordChangeLogin.jsx`
- `components/auth/SimpleLogin.jsx`
- `components/auth/KratosNativeLogin.jsx`
- `components/auth/SimplifiedKratosLogin.jsx`

## Active Components

### Login
- **Primary**: `EnhancedKratosLogin.jsx` - Main login component with identifier-first flow
- **Route**: `/login`

### Authentication Flow
1. User visits protected route
2. `UnifiedProtectedRoute` checks authentication
3. If not authenticated → redirect to `/login`
4. `EnhancedKratosLogin` handles:
   - Email entry (identifier-first)
   - Password or WebAuthn/Passkey detection
   - Login submission to Kratos

## Fix Applied

### UnifiedAuthProvider
- Removed custom auth check to `/api/auth/me` (no longer needed)
- Now relies solely on Kratos authentication
- Simplified to prevent multiple redirects
- Removed axios import and useState for custom auth state
- Provider now only passes through Kratos authentication state

### Result
- Single login flow through Kratos
- No more conflicting auth checks
- Clear authentication path
- Should eliminate the multiple login page issue