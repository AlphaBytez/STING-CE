# Kratos Native WebAuthn Migration Tasks

## Overview
Migrate from custom WebAuthn implementation to Kratos's native WebAuthn support while maintaining a passkey-first user experience.

## Current State Analysis

### Backend Components to Remove/Update
- [ ] `/app/routes/webauthn_routes.py` - Custom WebAuthn endpoints
- [ ] `/app/services/webauthn_manager.py` - Custom WebAuthn service
- [ ] `/app/models/passkey_models.py` - Custom passkey database models
- [ ] Database tables: `passkeys`, `passkey_registration_challenges`

### Frontend Components to Update
- [ ] `/frontend/src/components/auth/PasskeyFirstLogin.jsx` - Currently uses custom API
- [ ] `/frontend/src/components/auth/EnhancedKratosLogin.jsx` - Mixed approach
- [ ] `/frontend/src/components/auth/EnhancedKratosRegistration.jsx` - Custom passkey registration
- [ ] `/frontend/src/components/settings/PasskeySettings.jsx` - Passkey management UI
- [ ] Multiple other passkey components in `/frontend/src/components/auth/`

### Session Management to Simplify
- [ ] `/app/middleware/auth_middleware.py` - Remove Flask session checking for passkeys
- [ ] `/app/routes/auth_routes.py` - Update session endpoint to only check Kratos
- [ ] `/frontend/src/auth/KratosProvider.jsx` - Remove dual session logic

## Migration Tasks

### Phase 1: Update Kratos Configuration ✓
- [x] Enable WebAuthn in kratos.yml
- [x] Configure proper origins and RP settings
- [ ] Test WebAuthn is working with test user

### Phase 2: Create New Frontend Components
1. **Create Passkey-First Login Component**
   - [ ] Create `/frontend/src/components/auth/KratosPasskeyFirst.jsx`
   - [ ] Uses Kratos login flow API
   - [ ] Identifier-first approach (email → passkey → password fallback)
   - [ ] Integrates with Kratos WebAuthn script

2. **Update Registration Flow**
   - [ ] Modify registration to use Kratos flow
   - [ ] After password creation, prompt for WebAuthn setup
   - [ ] Use Kratos settings flow for WebAuthn registration

3. **Update Settings/Security Page**
   - [ ] Use Kratos settings flow for WebAuthn management
   - [ ] Remove custom passkey CRUD operations
   - [ ] Show existing WebAuthn credentials from Kratos

### Phase 3: Update Backend
1. **Remove Custom WebAuthn Code**
   - [ ] Delete custom WebAuthn routes
   - [ ] Remove WebAuthn manager service
   - [ ] Clean up passkey models

2. **Simplify Auth Middleware**
   - [ ] Remove Flask session checking
   - [ ] Only validate Kratos sessions
   - [ ] Update `g.user` loading logic

3. **Update Session Endpoint**
   - [ ] Remove dual session logic
   - [ ] Return only Kratos session info
   - [ ] Ensure proper auth method tracking

### Phase 4: Database Cleanup
- [ ] Create migration to drop custom passkey tables
- [ ] Ensure no foreign key constraints remain
- [ ] Archive any existing passkey data if needed

### Phase 5: Testing & Verification
- [ ] Test new user registration with WebAuthn
- [ ] Test existing user WebAuthn setup
- [ ] Test passkey login flow
- [ ] Test password fallback
- [ ] Verify session management works correctly
- [ ] Test logout functionality

## API Endpoints to Update

### Remove These Endpoints
```
POST /api/webauthn/registration/begin
POST /api/webauthn/registration/complete
POST /api/webauthn/authentication/begin
POST /api/webauthn/authentication/complete
DELETE /api/webauthn/credentials/{credential_id}
GET /api/webauthn/credentials
```

### Update These Endpoints
```
GET /api/auth/session - Remove Flask session logic
POST /api/auth/logout - Ensure only Kratos logout
```

## Frontend API Calls to Update

### Current Custom Calls
```javascript
// These need to be replaced:
apiClient.post('/api/webauthn/registration/begin')
apiClient.post('/api/webauthn/authentication/begin')
```

### New Kratos Flow Calls
```javascript
// Replace with:
kratosApi.get('/self-service/login/browser')
kratosApi.post('/self-service/login?flow={flowId}')
kratosApi.get('/self-service/settings/browser')
```

## Configuration Files to Update
- [ ] Remove WebAuthn-specific environment variables
- [ ] Update docker-compose.yml if any WebAuthn services
- [ ] Update any WebAuthn-related configuration in config.yml

## Documentation to Update
- [ ] Update PASSKEY_USERS_GUIDE.md
- [ ] Update API documentation
- [ ] Update architecture diagrams
- [ ] Create migration guide for any existing users

## Rollback Plan
1. Keep custom implementation code in a separate branch
2. Database migrations should be reversible
3. Test thoroughly in staging before production
4. Have quick switch mechanism if issues arise

## Success Criteria
- [ ] Users can register with email/password then add passkey
- [ ] Users can login with passkey as primary method
- [ ] Password remains as fallback option
- [ ] All sessions managed by Kratos only
- [ ] No custom WebAuthn code remaining
- [ ] Clean, maintainable codebase

## Notes
- Kratos v1.3.1 requires password before WebAuthn setup
- This is actually more secure (two-factor approach)
- Focus on UX to make passkey feel primary despite technical requirement