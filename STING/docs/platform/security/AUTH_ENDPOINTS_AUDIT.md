# Authentication Endpoints Audit

## Goal
Ensure ALL authentication is handled by Kratos, removing any custom/hybrid authentication.

## Current State Analysis

### 1. Kratos-Managed Endpoints ✅
- `/self-service/login/*` - Login flows
- `/self-service/registration/*` - Registration flows  
- `/self-service/logout/*` - Logout flows
- `/self-service/recovery/*` - Password recovery
- `/self-service/verification/*` - Email verification
- `/self-service/settings/*` - Account settings (including WebAuthn)
- `/sessions/whoami` - Session validation

### 2. Custom Endpoints (Need Review)

#### In `/api/auth/*` (auth_routes.py):
- [x] `/api/auth/session` - UPDATED: Now only checks Kratos sessions
- [x] `/api/auth/logout` - Uses Kratos logout flow
- [x] `/api/auth/passkey-status` - UPDATED: Only checks Kratos credentials
- [ ] `/api/auth/check-user` - Still checks local DB
- [ ] `/api/auth/status` - Mixed Kratos/custom checks
- [ ] `/api/auth/clear-session` - Manual session clearing
- [ ] `/api/auth/init-session` - Backend session initialization
- [ ] `/api/auth/test-session` - Debug endpoint
- [ ] `/api/auth/quick-logout` - Alternative logout
- [ ] `/api/auth/debug/*` - Various debug endpoints

#### In `/api/webauthn/*` (DISABLED):
- [x] All WebAuthn endpoints disabled by removing blueprint

### 3. Frontend Components Status

#### Using Kratos ✅:
- `EnhancedKratosLogin.jsx` - Uses Kratos flows
- `EnhancedKratosRegistration.jsx` - Uses Kratos flows
- `KratosProvider.jsx` - Main auth context

#### Need Updates:
- [ ] `PasskeySettings.jsx` - Update to use Kratos settings
- [ ] `PasskeySetupNudge.jsx` - Update or remove
- [ ] `SecuritySettings.jsx` - Update to use Kratos settings

### 4. Middleware & Session Management

#### auth_middleware.py:
- Currently checks both Kratos sessions and Flask sessions
- Should be updated to ONLY check Kratos sessions

## Required Changes

### Phase 1: Backend Cleanup ✅
1. [x] Disable custom WebAuthn routes
2. [x] Update `/api/auth/session` to only use Kratos
3. [x] Update `/api/auth/passkey-status` to only check Kratos

### Phase 2: Remove Hybrid Checks
1. [ ] Update `check-user` endpoint to use Kratos admin API
2. [ ] Remove Flask session checks from middleware
3. [ ] Remove all debug/alternative auth endpoints

### Phase 3: Frontend Updates
1. [x] Update PasskeySettings to use Kratos settings API
2. [ ] Remove or update PasskeySetupNudge
3. [x] Ensure all components use KratosProvider

### Phase 4: Database Cleanup
1. [ ] Remove passkey tables (or keep for migration history)
2. [ ] Remove custom auth-related columns from user table
3. [ ] Ensure all users have proper Kratos identities

## Testing Plan

1. **Registration Flow**:
   - Register new user with password
   - Add WebAuthn credential via Kratos settings
   - Verify credential stored in Kratos

2. **Login Flow**:
   - Login with password via Kratos
   - Login with WebAuthn via Kratos
   - Verify proper session creation

3. **Session Management**:
   - Verify session persists across refreshes
   - Verify logout clears Kratos session
   - Verify no Flask sessions created

## Security Considerations

1. **Session Consistency**: Ensure only Kratos manages sessions
2. **CSRF Protection**: Use Kratos CSRF tokens
3. **Cookie Security**: Only Kratos session cookies
4. **API Security**: All API calls must validate Kratos session

## Migration Path for Existing Users

1. Users with custom passkeys need to re-register in Kratos
2. Provide clear messaging about the change
3. Consider temporary migration period with both systems

## Benefits After Migration

1. **Single Source of Truth**: Kratos manages all auth
2. **Better Security**: Professional auth system
3. **Simpler Codebase**: Remove custom auth code
4. **Future-Proof**: Easy to add OAuth, MFA, etc.