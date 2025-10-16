# EnhancedKratosLogin.jsx Comprehensive Review

## Overview
This component handles the Kratos identifier-first login flow for STING. It was recently cleaned up to use Kratos as the single source of truth for authentication.

## Current Issues Fixed

### 1. Initial Screen UI (FIXED)
- **Problem**: Showed "Sign in with Passkey" and "Or sign in with email" on initial screen
- **Fix**: Removed the custom passkey button from initial screen (line 1060)
- **Result**: Clean initial screen with only "Sign In with Email" button

### 2. Password Separator Logic (FIXED)
- **Problem**: "Or continue with password" showed before identifier submission
- **Fix**: Added conditions to only show separator when:
  - `identifierSubmitted === true`
  - `showPasswordField === true`
  - `getWebAuthnButton()` returns truthy (multiple auth methods available)

## Component Flow

### 1. Initial State (`!flowId`)
```
STING Logo
Sign in to STING
[Admin Notice if applicable]
[Sign In with Email] button
"Don't have an account? Sign up"
```

### 2. After Flow Initialization
- Fetches login flow from Kratos
- Renders form based on flow data
- Handles identifier-first flow

### 3. Identifier Submission
- Submits email with `method: 'password'` 
- Expects 400 status with updated flow data
- Sets `identifierSubmitted: true`
- Shows password field if available

### 4. Password/WebAuthn Selection
- If WebAuthn available: Shows both options with separator
- If only password: Shows password field directly
- Handles form submission to Kratos

## Key Functions

### `handleIdentifierSubmit` (lines 486-642)
- Submits identifier to Kratos
- Handles 400 response as success (contains updated flow)
- Checks for available authentication methods
- Updates UI state based on response

### `handleCustomPasskeyLogin` (lines 339-483) 
- **Currently unused** - was for custom WebAuthn implementation
- Should be removed in cleanup

### `getWebAuthnButton` (lines 205-319)
- Extracts WebAuthn button from Kratos flow nodes
- Handles onclick attributes and scripts
- Returns JSX button element if available

## Remaining Issues

### 1. Unused Code
- `handleCustomPasskeyLogin` function (line 339)
- `handleWebAuthnLogin` function (line 321)
- `hasCustomPasskeys` state variable (line 25)
- Custom passkey-related code that's no longer needed

### 2. Error Handling
- Line 211 & 615: Uses `eval()` which is dangerous
- Should find safer way to execute Kratos scripts

### 3. URL Rewriting
- Lines 523-528: Rewrites action URLs from nginx proxy to direct Kratos
- This might cause issues in production environments

### 4. Authentication Still Failing
- Login with admin@sting.local / Password1! returns "invalid credentials"
- This appears to be a backend/Kratos configuration issue, not frontend

## Recommendations

### 1. Clean up unused code
```javascript
// Remove these:
- const [hasCustomPasskeys, setHasCustomPasskeys] = useState(false);
- handleCustomPasskeyLogin function
- handleWebAuthnLogin function
- All references to custom passkey implementation
```

### 2. Replace eval() usage
```javascript
// Instead of:
eval(node.attributes.onclick);

// Use:
// Parse and execute the function safely
const funcMatch = node.attributes.onclick.match(/(\w+)\((.*)\)/);
if (funcMatch && window[funcMatch[1]]) {
  window[funcMatch[1]](...);
}
```

### 3. Make URL rewriting configurable
```javascript
// Add to component or config:
const KRATOS_DIRECT_ACCESS = process.env.REACT_APP_KRATOS_DIRECT || false;

// Then conditionally rewrite:
if (KRATOS_DIRECT_ACCESS && actionUrl.includes('localhost:8443/self-service')) {
  actionUrl = actionUrl.replace('https://localhost:8443/self-service', kratosUrl + '/self-service');
}
```

### 4. Improve error messages
- Add more specific error handling for different failure scenarios
- Show user-friendly messages for common issues

## Testing Status

### Working ✅
- Initial UI now clean (no passkey button/separator)
- Identifier-first flow transitions correctly
- Frontend handles 400 status properly
- Form submission uses correct content-type

### Not Working ❌
- Authentication with provided credentials fails
- This appears to be a backend/credential issue, not frontend

## Next Steps

1. Remove unused custom passkey code
2. Fix eval() security issues
3. Investigate why authentication fails with correct credentials
4. Test with a newly created user to isolate admin-specific issues