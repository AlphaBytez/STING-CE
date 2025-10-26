# STING Passkey Authentication User Guide

This guide provides detailed instructions for implementing, testing, and troubleshooting passkey authentication in your STING application.

## What Are Passkeys?

Passkeys are a modern, passwordless authentication method that leverages WebAuthn (Web Authentication) standard. They offer:

- **Enhanced Security**: Phishing-resistant credentials tied to specific websites
- **Improved User Experience**: No need to remember or type passwords
- **Cross-Platform Support**: Works across devices and operating systems
- **Biometric Verification**: Uses fingerprint, face scan, or device PIN

## Prerequisites

Before using passkeys in STING:

1. **Browser Compatibility**: Ensure you're using a modern browser that supports WebAuthn (Chrome, Firefox, Safari, Edge)
2. **Device Support**: Your device must support biometric authentication or have a secure PIN/pattern
3. **HTTPS**: Your development environment must run on HTTPS (even locally)

## Implementation Status

The STING application has been configured for passkey authentication with the following components:

1. **Dual Authentication System**: 
   - Kratos handles traditional password authentication
   - Custom WebAuthn implementation handles passkey authentication
   - Flask sessions support both authentication methods

2. **Enhanced Login Component**: `PasskeyFirstLogin.jsx` prioritizes passkey authentication
3. **Enhanced Registration**: `EnhancedKratosRegistration.jsx` supports passkey creation after email/password setup
4. **Session Management**: 
   - Flask sessions for passkey authentication (`user_id`, `auth_method`)
   - Kratos sessions for password authentication
   - Auth middleware checks both session types

5. **Current Working State**:
   - ✅ Passkey registration works correctly
   - ✅ Passkey login creates proper Flask sessions
   - ✅ Session validation supports both Kratos and Flask sessions
   - ✅ Dashboard accessible with either authentication method

## Testing Passkey Authentication

### 1. Start STING Services

```bash
./manage_sting.sh start
```

### 2. Register a New Account with Passkey

1. Navigate to https://localhost:8443/register
2. Fill in your email and other required information
3. When prompted to create a passkey, follow the system prompts:
   - On macOS/iOS: Use Touch ID or Face ID
   - On Windows: Use Windows Hello (PIN, fingerprint, or facial recognition)
   - On Android: Use fingerprint, face recognition, or device PIN

### 3. Login with Your Passkey

1. Navigate to https://localhost:8443/login
2. Click "Sign in with Passkey" button
3. When prompted, use your biometric authentication or device PIN
4. You should be redirected to the dashboard upon successful authentication

## Troubleshooting Common Issues

### 1. Dashboard Access Issues

If you're unable to access the dashboard after authenticating:

- **Enable Mock User**: In `MainInterface.js`, ensure the line `createMockUser(); return;` is uncommented
- **Clear Browser Cache**: Clear cookies and localStorage for the site
- **Check Console**: Look for authentication-related errors in browser console

### 2. Registration Problems

If passkey registration fails:

- **Check Browser Support**: Verify your browser supports WebAuthn using [WebAuthn.io](https://webauthn.io/)
- **Inspect Network Calls**: Check for CORS or network errors during registration
- **Try Alternative Browser**: Some browsers have better WebAuthn support than others

### 3. Login Failures

If you can't log in with a passkey:

- **Verify Credentials**: Check if your passkey was successfully registered
- **Test Legacy Login**: Try the fallback password option as a verification
- **Inspect Kratos Logs**: Check for errors in the Kratos service logs

```bash
docker logs sting-kratos
```

### 4. Email Verification Issues

If email verification emails aren't arriving:

- **Check Mailpit**: Access Mailpit at https://localhost:8025
- **Verify SMTP Settings**: Ensure `courier.smtp.connection_uri` in Kratos config points to `smtp://test:test@mailpit:1025/?skip_ssl_verify=true`
- **Restart Mail Service**: Restart the Mailpit container

## Security Considerations

When using passkeys:

1. **Device Security**: Passkeys are only as secure as your device's biometric or PIN security
2. **Account Recovery**: Implement a recovery flow for users who lose access to their devices
3. **Multi-Device Usage**: Consider how users will authenticate across multiple devices

## Advanced Configuration

### Adding Additional Origins

If you need to support additional domains for your application:

```yaml
# In kratos/main.kratos.yml
webauthn:
  enabled: true
  config:
    rp:
      id: yourdomain.com
      display_name: STING Authentication
      origins:
        - https://yourdomain.com
        - https://app.yourdomain.com
        - https://localhost:8443
    passwordless: true
```

### Customizing Registration Flow

To customize the registration sequence:

1. Edit `EnhancedKratosRegistration.jsx` to modify the registration steps
2. Update UI messaging to guide users through the process
3. Consider collecting additional identity information before passkey creation

## Next Steps

To further enhance your implementation:

1. **User Settings Panel**: Allow users to manage their passkeys
2. **Multiple Passkeys**: Support registering multiple passkeys for one account
3. **Recovery Options**: Add SMS or email-based account recovery
4. **SSO Integration**: Implement Single Sign-On alongside passkeys

## Troubleshooting Common Issues

### Session Not Persisting After Passkey Login

**Issue**: Successfully authenticate with passkey but redirected back to login page

**Solutions**:
- Check browser console for cookie errors
- Ensure Flask SECRET_KEY is set in backend configuration
- Verify session cookies are being set with correct domain/path
- Check that auth middleware is loading Flask sessions correctly

### Passkey Registration Fails

**Issue**: "Failed to generate registration options" error

**Solutions**:
- Ensure HTTPS is enabled (passkeys require secure context)
- Check that the backend WebAuthn manager is properly initialized
- Verify database migrations have created PasskeyRegistrationChallenge table
- Check browser console for WebAuthn API errors

### Frontend Not Recognizing Authentication

**Issue**: Backend shows authenticated but frontend doesn't update

**Solutions**:
- Check that `/api/auth/session` endpoint returns correct session data
- Verify KratosProvider is checking both Kratos and Flask sessions
- Clear browser cache and cookies, then try again
- Check Network tab to ensure session endpoint is being called

### Docker Container Issues

**Issue**: Services unhealthy or not starting properly

**Solutions**:
```bash
# Check container health
./manage_sting.sh status

# Restart specific service
./manage_sting.sh restart app
./manage_sting.sh restart frontend

# Check logs for errors
./manage_sting.sh logs app
./manage_sting.sh logs frontend
```

## Architecture Notes

The current implementation uses a dual authentication system:
- **Kratos**: Handles email/password authentication
- **Custom WebAuthn**: Handles passkey authentication
- **Session Management**: Flask sessions support both methods
- **Middleware**: Auth middleware checks both Kratos and Flask sessions

Consider consolidating to a single authentication system in the future for simplicity.

## Resources

- [Kratos WebAuthn Documentation](https://www.ory.sh/docs/kratos/selfservice/flows/webauthn-passwordless)
- [WebAuthn Guide](https://webauthn.guide/)
- [W3C WebAuthn Specification](https://www.w3.org/TR/webauthn-2/)
- [FIDO Alliance Passkeys](https://fidoalliance.org/passkeys/)