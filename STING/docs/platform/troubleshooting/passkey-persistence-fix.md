# Passkey Persistence Issue - Resolution

## Problem Summary
Users reported that passkeys appeared to register successfully (browser ceremony completed) but were not visible in the PasskeyManager component. The check_passkeys.py script showed NO credentials for any identity.

## Root Cause
The issue was that while passkeys were being stored correctly in the Kratos database, the `/sessions/whoami` endpoint does not return the full credential configuration data (including registered passkeys). This is by design in Kratos for security reasons - sensitive credential data is not included in session responses.

## Database Investigation
Running queries against the database revealed that passkeys WERE being stored:
```sql
SELECT ic.config, i.traits->>'email' as email 
FROM identity_credentials ic 
JOIN identities i ON i.id = ic.identity_id 
JOIN identity_credential_types ict ON ict.id = ic.identity_credential_type_id 
WHERE ict.name = 'webauthn'
```

For admin@sting.local, this showed 3 registered passkeys in the config JSON.

## Solution
Created `PasskeyManagerDirect.jsx` which:
1. Fetches passkey data from the settings flow instead of relying on the session endpoint
2. Parses WebAuthn remove nodes to identify existing passkeys
3. Provides a refresh button to reload passkey data
4. Monitors for new passkeys after registration by re-fetching the settings flow

## Key Differences
- **Old approach**: Expected passkeys in `identity.credentials.webauthn` from session
- **New approach**: Fetches fresh settings flow and parses WebAuthn nodes

## Implementation Details
The settings flow contains remove buttons for each registered passkey:
```javascript
const removeNodes = webauthnNodes.filter(n => 
  n.attributes?.name === 'webauthn_remove' && 
  n.attributes?.type === 'submit'
);
```

Each remove node's value is the credential ID of a registered passkey.

## Files Modified
- Created: `/frontend/src/components/settings/PasskeyManagerDirect.jsx`
- Updated: `/frontend/src/components/user/SecuritySettings.jsx` to use new component

## Testing
After implementing this fix:
1. Existing passkeys should now be visible
2. New passkey registration should work and show immediately
3. Passkey removal should work correctly

## Notes
- The "Could not find a strategy" error from Kratos was misleading - passkeys were being saved
- The issue was purely a display problem in the frontend
- This approach works around Kratos's security design of not exposing credential configs in sessions