# STING Passkey Implementation Guide

This guide provides detailed instructions for implementing WebAuthn/passkey authentication in your STING application. It covers both frontend and backend setup, troubleshooting steps, and testing procedures.

## Overview

Passkeys (based on the WebAuthn standard) provide a modern, phishing-resistant authentication method that works across devices using biometrics or device PINs. This implementation:

1. Supports registration with passkeys as a second factor
2. Prioritizes passkey login while maintaining password fallback
3. Works with the standard Kratos configuration

## Prerequisites

Before implementing passkeys:

- STING must be installed and running (including Kratos authentication)
- Frontend must be running on HTTPS (localhost is fine for testing)
- Self-signed certificates should be properly configured
- WebAuthn API must be supported by your browser

## Implementation Steps

### 1. Frontend Components Setup

1. **Add Authentication Components**
   
   Copy these React components to your `frontend/src/components/auth` directory:

   - `DirectPasskeyRegistration.jsx` - Password registration with passkey setup
   - `DirectPasskeyLogin.jsx` - WebAuthn-first login with password fallback
   - `DebugPage.jsx` - Testing and troubleshooting page

2. **Update Routes**
   
   Update your `AppRoutes.js` file to include the new components:

   ```jsx
   import DirectPasskeyRegistration from './components/auth/DirectPasskeyRegistration';
   import DirectPasskeyLogin from './components/auth/DirectPasskeyLogin';
   
   // Inside your Routes component
   <Route path="/login" element={<DirectPasskeyLogin />} />
   <Route path="/register" element={<DirectPasskeyRegistration />} />
   <Route path="/debug" element={<DebugPage />} />
   ```

3. **Add Passkey Test Page**
   
   Create a standalone HTML page at `frontend/public/passkey-test.html` to directly test WebAuthn browser support.

### 2. Kratos Configuration

The standard Kratos configuration already supports WebAuthn, but we need to ensure it's properly enabled:

1. **Check Schema Configuration**
   
   Make sure your `identity.schema.json` includes WebAuthn as a credential type:

   ```json
   "credentials": {
     "password": {
       "identifier": true
     },
     "webauthn": {
       "identifier": true
     }
   }
   ```

2. **Enable WebAuthn in Kratos Config**
   
   In `kratos.yml` or equivalent configuration file:

   ```yaml
   selfservice:
     methods:
       webauthn:
         enabled: true
         config:
           rp:
             id: localhost
             display_name: STING Authentication
             origins:
               - https://localhost:8443
               - https://localhost:4433
           passwordless: true
   ```

### 3. Testing and Verifying

1. **Browser Support Check**
   
   Visit `/passkey-test.html` to verify your browser supports WebAuthn.

2. **Registration Flow**
   
   - Visit `/register` to start the registration flow
   - Create an account with email and password
   - Set up a passkey when prompted
   - Verify the account creation and passkey setup in logs

3. **Login Flow**
   
   - Visit `/login` to start the login flow
   - Verify passkey login is offered first
   - Try both passkey and password login

4. **Debugging**
   
   Visit `/debug` to:
   - Check Kratos connection status
   - View authentication status
   - Try individual authentication flows

## How It Works

### Registration Process

The registration flow happens in two steps:

1. **Account Creation**
   
   The user creates an account with email and password (required by Kratos).

2. **Passkey Setup**
   
   After account creation, the component starts a settings flow to add a WebAuthn credential:
   
   - Retrieves the WebAuthn registration trigger
   - Executes the WebAuthn flow, prompting for biometrics
   - Registers the credential with Kratos

### Login Process

The login flow attempts WebAuthn first:

1. **WebAuthn Detection**
   
   Component checks if WebAuthn is supported by the browser.

2. **WebAuthn Login**
   
   If supported, offers passkey login as the primary option:
   
   - Retrieves WebAuthn login trigger from Kratos
   - Executes the trigger to start authentication
   - Prompts for biometric verification

3. **Password Fallback**
   
   If WebAuthn is not available or fails, offers password login.

## Common Issues and Solutions

### Email Verification Issues

Email verification emails should be sent by Kratos to your configured mail service (e.g., Mailpit).

Checking Mailpit:
- Access the Mailpit UI at `https://localhost:8025`
- Look for verification emails there

### WebAuthn Not Working

If WebAuthn isn't working:

1. Verify browser support with `/passkey-test.html`
2. Check for console errors during WebAuthn operations
3. Ensure you're using HTTPS (required for WebAuthn)
4. Check Kratos logs for WebAuthn-related errors

### Dashboard Integration Issues

If dashboard doesn't appear after authentication:

1. Check browser console for errors
2. Verify the `localStorage` user object is being set
3. Check Kratos session status in the debug page
4. Try enabling the mock user in `MainInterface.js`

## Advanced Configuration

### Multiple Domains

To support multiple domains (e.g., production and staging):

```yaml
webauthn:
  # ...
  config:
    rp:
      origins:
        - https://app.example.com
        - https://staging.example.com
```

### Custom Registration Flow

To customize the registration experience:

1. Modify `DirectPasskeyRegistration.jsx` to include additional fields
2. Update the payload in `submitPasswordRegistration` function
3. Adjust the UI elements to match your design

## Security Considerations

1. **Secure Context**: WebAuthn only works in secure contexts (HTTPS or localhost)
2. **Recovery Options**: Always provide alternative recovery methods
3. **Password Fallback**: Maintain password login as fallback
4. **Session Management**: Configure appropriate session lifetimes

## Resources

- [WebAuthn.io](https://webauthn.io/) - Test and learn about WebAuthn
- [Ory Kratos Documentation](https://www.ory.sh/docs/kratos)
- [W3C WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [Web Authentication API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Web_Authentication_API)

---

This guide provides a comprehensive overview of implementing WebAuthn/passkey authentication in STING. For specific issues or customizations, refer to the browser console logs and Kratos documentation.