# STING Passkey Implementation Guide

This guide explains how to use WebAuthn/passkeys as the primary authentication method in STING, along with how to resolve common authentication issues.

## Passkey Authentication in STING

We've configured Kratos to support passwordless WebAuthn (passkeys) as a primary authentication method. This offers several advantages:

1. **Enhanced Security**: Passkeys are phishing-resistant and more secure than passwords
2. **Improved User Experience**: No passwords to remember or type
3. **Platform Integration**: Works with Apple, Google, and Windows authentication systems
4. **Biometric Verification**: Uses fingerprint, face recognition, or device PIN

## Configuration Changes

The following changes have been made to enable passkey authentication:

1. **Kratos Configuration Update**:
   ```yaml
   # In main.kratos.yml
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
         passwordless: true  # Enable passwordless login with passkeys
   ```

2. **React Components for Passkey Authentication**:
   - `EnhancedKratosLogin.jsx`: Prioritizes passkey login while maintaining password as fallback
   - `EnhancedKratosRegistration.jsx`: Guides users through registration with passkey setup

3. **Updated Routing**:
   - Routes configured to use the enhanced components
   - Proper handling of flow IDs in login URLs

## Testing Passkey Authentication

To test passkey authentication:

1. **Start the STING services**:
   ```bash
   ./manage_sting.sh start
   ```

2. **Access the login page**:
   Visit https://localhost:8443/login

3. **Choose "Sign in with Passkey"**:
   If your device supports WebAuthn, you'll be prompted to use your biometric or device PIN

4. **Register a new passkey**:
   If you don't have a passkey yet, complete registration first at https://localhost:8443/register

## Troubleshooting Common Issues

### Authentication Issues

If you experience 404 errors or other authentication issues:

1. **Check the browser console** for errors related to authentication or CORS
2. **Ensure proxy settings are correct** in `frontend/src/setupProxy.js`
3. **Verify your browser supports WebAuthn** - Chrome, Firefox, Safari, and Edge should work
4. **Try the debug page** at https://localhost:8443/debug to diagnose Kratos connectivity

### Dashboard Not Appearing

If the dashboard doesn't appear after authentication:

1. **Check Kratos session status** using the debug page
2. **Verify MainInterface.js** is correctly checking for authentication
3. **Try the mock user option** by uncommenting the `createMockUser()` line in MainInterface.js

### Passkey Detection Issues

If passkeys aren't being detected:

1. **Ensure your device has biometric capabilities** or a secure PIN
2. **Check browser permissions** for biometric access
3. **Try a different browser** to see if it's a browser-specific issue

## Fallback Options

Even with passkeys enabled, these fallback methods are still available:

1. **Password Authentication**: Traditional email/password login remains available
2. **Legacy Login Page**: Available at `/login-legacy` for backward compatibility

## Next Steps for Integration

To fully integrate passkeys into your authentication flow:

1. **Update your database models** to store WebAuthn credential information
2. **Add user settings** for managing multiple passkeys
3. **Implement recovery flows** for users who lose access to their devices
4. **Decide on your SSO strategy** and how it will coexist with passkeys

## Technical Documentation

For a deeper understanding of the integration, see:

- [Kratos WebAuthn Documentation](https://www.ory.sh/docs/kratos/selfservice/flows/webauthn-passwordless)
- [WebAuthn Guide](https://webauthn.guide/)
- [Browser Support for WebAuthn](https://caniuse.com/webauthn)