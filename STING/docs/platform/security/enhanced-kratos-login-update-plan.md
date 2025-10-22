# EnhancedKratosLogin Update Plan

## Current State Analysis
The component currently:
1. Tries to use Kratos WebAuthn (lines 91-117 load Kratos script)
2. Falls back to custom WebAuthn implementation (lines 266-437)
3. Has mixed approaches causing confusion

## Key Changes Needed

### 1. Remove Custom WebAuthn Implementation
- Remove lines 266-437 (handleStingPasskeyAuth function)
- Remove custom API imports and calls
- Remove simplewebauthn library usage

### 2. Properly Use Kratos Login Flow
- Initialize Kratos login flow properly
- Submit identifier first to check available methods
- Let Kratos handle WebAuthn authentication

### 3. Implement Identifier-First Flow
```javascript
// Step 1: User enters email
// Step 2: Submit to Kratos with method=password, empty password
// Step 3: Kratos returns available methods
// Step 4: If WebAuthn available, show passkey button
// Step 5: If not, show password field
```

### 4. Use Kratos WebAuthn Script Properly
- The script is already being loaded (good!)
- Need to properly trigger it based on flow state
- Let Kratos handle the browser WebAuthn API

### 5. Simplify State Management
Current state variables to keep:
- flowData (Kratos flow)
- isLoading
- error
- email (for identifier-first)
- showPasswordField

Remove:
- showPasskeyEmailForm
- passkeyEmail
- isAuthenticating
- All custom WebAuthn states

### 6. Update Form Rendering
- Render based on Kratos flow UI nodes
- Check for WebAuthn availability in flow
- Show appropriate UI based on flow state

## Implementation Steps

1. **Clean up imports** - Remove unused custom WebAuthn imports
2. **Simplify state** - Remove custom WebAuthn states
3. **Update flow initialization** - Properly start Kratos flow
4. **Implement identifier-first** - Email → Check methods → Show UI
5. **Use Kratos nodes** - Render UI based on flow nodes
6. **Test thoroughly** - Ensure both passkey and password work