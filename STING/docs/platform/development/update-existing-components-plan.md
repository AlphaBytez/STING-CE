# Plan to Update Existing Components for Kratos WebAuthn

## Components to Update (Not Replace)

### 1. **PasskeyFirstLogin.jsx**
Currently uses custom WebAuthn API. Update to:
- Keep the same UI/UX flow
- Replace custom API calls with Kratos flow API
- Use Kratos WebAuthn script for browser interaction
- Keep the email → passkey → password fallback logic

### 2. **EnhancedKratosLogin.jsx**
Already tries to use Kratos. Update to:
- Remove custom WebAuthn API fallbacks
- Properly integrate with Kratos WebAuthn flow
- Use Kratos's WebAuthn script loading mechanism

### 3. **EnhancedKratosRegistration.jsx**
Currently adds custom passkeys. Update to:
- After Kratos password registration, redirect to settings
- Use Kratos settings flow to add WebAuthn
- Remove custom passkey creation code

### 4. **PasskeySettings.jsx**
Currently manages custom passkeys. Update to:
- Use Kratos settings flow to list WebAuthn credentials
- Use Kratos settings flow to add/remove credentials
- Remove custom CRUD operations

### 5. **KratosProvider.jsx**
Currently checks dual sessions. Update to:
- Only check Kratos sessions
- Remove Flask session logic
- Simplify authentication state

### 6. **Auth Middleware (Backend)**
Currently checks both session types. Update to:
- Only validate Kratos sessions
- Remove Flask session checking
- Keep the same middleware structure

### 7. **Session Endpoint (Backend)**
Currently returns dual session info. Update to:
- Only return Kratos session information
- Keep the same response structure
- Remove Flask session checks

## Key Changes Summary

### API Calls to Update
```javascript
// OLD: Custom WebAuthn
await apiClient.post('/api/webauthn/authentication/begin', { username: email })

// NEW: Kratos Flow
await kratosApi.post(`/self-service/login?flow=${flowId}`, { 
  method: 'webauthn',
  identifier: email 
})
```

### Session Checks to Update
```javascript
// OLD: Dual session check
if (session.user_id || kratosSession) { ... }

// NEW: Kratos only
if (kratosSession) { ... }
```

### WebAuthn Script Integration
```javascript
// Add to existing components that need WebAuthn
const loadKratosWebAuthnScript = (flow) => {
  const scriptNode = flow.ui.nodes.find(n => 
    n.type === 'script' && n.group === 'webauthn'
  );
  if (scriptNode?.attributes?.src) {
    const script = document.createElement('script');
    script.src = scriptNode.attributes.src;
    document.body.appendChild(script);
  }
};
```

## Benefits of This Approach
1. No new routes or components to manage
2. Existing UI/UX is preserved
3. Gradual migration possible
4. Less code to review and test
5. Easier to track what changed

## After Updates Complete
1. Remove `/app/routes/webauthn_routes.py`
2. Remove `/app/services/webauthn_manager.py`
3. Remove passkey database models
4. Clean up any unused imports
5. Update documentation

## Testing After Each Update
- Component still renders correctly
- Login flow works with existing users
- Registration flow works for new users
- Settings page shows WebAuthn options
- No console errors about missing endpoints