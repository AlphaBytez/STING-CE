# Plan to Remove Custom WebAuthn Implementation

## Current State
- **Kratos WebAuthn**: Configured and enabled with passwordless mode
- **Custom WebAuthn**: Running in parallel at `/api/webauthn/*` endpoints
- **Problem**: User `olliec@sting.ai` has passkey in custom system but no credentials in Kratos

## Migration Steps

### 1. Disable Custom WebAuthn Routes
- Comment out or remove WebAuthn blueprint registration in `app/__init__.py`
- Remove `/api/webauthn/*` endpoints from `app/routes/webauthn_routes.py`

### 2. Update Frontend Components
- Remove custom passkey API calls
- Use only Kratos WebAuthn flow
- Update PasskeySettings to use Kratos settings API

### 3. Clean Up Database
- Remove custom passkey tables (optional, can keep for history)
- Ensure users have proper Kratos identities

### 4. Update Auth Middleware
- Remove Flask session checks for passkey auth
- Rely only on Kratos sessions

### 5. Components to Update/Remove
- `/components/settings/PasskeySettings.jsx` - Update to use Kratos
- `/components/common/PasskeySetupNudge.jsx` - Update or remove
- `/components/debug/PasskeyDebugPanel.jsx` - Remove
- All archived passkey components - Already archived

## Benefits
- Single authentication system
- Proper session management
- Consistent auth methods
- Simpler codebase

## Risks
- Existing passkeys won't work (users need to re-register)
- Need to ensure Kratos WebAuthn works properly first