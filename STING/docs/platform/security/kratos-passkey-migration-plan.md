# Kratos Passkey Migration Plan

## Current State
- **Custom WebAuthn implementation** in Flask backend (`/app/routes/webauthn_routes.py`)
- **Kratos WebAuthn enabled** but not configured for passwordless
- **Dual session management** (Flask sessions + Kratos sessions)
- **Multiple passkey UI components** trying different approaches

## Goal
Use Kratos's native passkey support exclusively, removing the custom implementation entirely.

## Migration Steps

### Phase 1: Configure Kratos for Passwordless Passkeys

1. **Update kratos.yml** to enable the passkey method:
```yaml
selfservice:
  methods:
    passkey:
      enabled: true
      config:
        rp:
          display_name: "STING Platform"
          id: localhost
          origins:
            - https://localhost:8443
            - https://localhost:3010
    
    # Keep password as fallback
    password:
      enabled: true
      config:
        haveibeenpwned_enabled: false
        identifier_similarity_check_enabled: false
    
    # Disable the webauthn method (replaced by passkey)
    webauthn:
      enabled: false
```

2. **Update identity.schema.json** to properly support passkeys:
```json
{
  "properties": {
    "traits": {
      "properties": {
        "email": {
          "ory.sh/kratos": {
            "credentials": {
              "passkey": {
                "display_name": true,
                "identifier": true
              },
              "password": {
                "identifier": true
              }
            }
          }
        }
      }
    }
  }
}
```

### Phase 2: Update Frontend Components

1. **Create a single Kratos-based login component** that:
   - Initiates a Kratos login flow
   - Checks for passkey availability
   - Offers passkey as the primary option
   - Falls back to password if needed

2. **Remove custom passkey components**:
   - Remove all direct WebAuthn API calls
   - Remove custom passkey registration/login endpoints
   - Use Kratos flows exclusively

3. **Simplify the authentication flow**:
   ```javascript
   // Instead of custom WebAuthn calls:
   const response = await kratosApi.post('/self-service/login/flow', {
     method: 'passkey'
   });
   ```

### Phase 3: Backend Cleanup

1. **Remove custom WebAuthn implementation**:
   - Delete `/app/routes/webauthn_routes.py`
   - Delete `/app/services/webauthn_manager.py`
   - Remove passkey models from database

2. **Simplify auth middleware**:
   - Remove Flask session checking for passkeys
   - Rely only on Kratos session validation

3. **Update session endpoint**:
   - Only check Kratos sessions
   - Remove dual session logic

### Phase 4: Data Migration (if needed)

If users already have passkeys registered with the custom implementation:
1. Export passkey credentials from custom tables
2. Import into Kratos using Admin API
3. Map user associations correctly

## Benefits of This Approach

1. **Single Source of Truth**: Kratos handles all authentication
2. **Better Security**: Kratos's battle-tested implementation
3. **Simpler Codebase**: Remove ~1000+ lines of custom code
4. **Better UX**: Kratos's passkey method supports conditional UI
5. **Easier Maintenance**: Updates come from Kratos releases

## Implementation Priority

1. **High Priority**: Update Kratos configuration to enable passkey method
2. **Medium Priority**: Create new frontend component using Kratos flows
3. **Low Priority**: Clean up custom implementation after verification

## Testing Plan

1. Configure Kratos with passkey method in dev environment
2. Test passkey registration through Kratos flow
3. Test passkey login with conditional UI
4. Verify session management works correctly
5. Test fallback to password authentication

## Rollback Plan

Keep custom implementation disabled but available until Kratos passkey flow is verified working in production.