# STING Authentication Guide

## Overview

This guide summarizes STING's passwordless authentication system. For complete technical details, see:
- `docs/features/PASSWORDLESS_AUTHENTICATION.md` - Comprehensive authentication architecture
- `docs/KRATOS_INTEGRATION_GUIDE.md` - Ory Kratos implementation details  
- `docs/guides/PASSKEY_QUICKSTART.md` - Quick setup guide
- `docs/KRATOS_PASSKEY_GUIDE.md` - WebAuthn/FIDO2 configuration

STING uses a modern, passwordless authentication system built on Ory Kratos, providing secure and user-friendly access to your platform.

## Authentication Methods

### 1. Email Magic Links (Primary)
- Enter your email address on the login page
- Receive a secure link via email
- Click the link to authenticate instantly
- No passwords to remember or manage

### 2. Biometric Authentication (Recommended)
- **TouchID/FaceID**: Use your device's built-in biometrics
- **Windows Hello**: Facial recognition or fingerprint on Windows
- **Platform Authenticators**: Built into your device for maximum security
- Provides AAL2 (Authenticator Assurance Level 2) security

### 3. Hardware Security Keys
- **FIDO2/WebAuthn**: Industry-standard security keys
- **YubiKey**: Popular hardware security key brand
- **Cross-platform**: Works on any device with USB or NFC
- Ultimate security for high-value accounts

### 4. TOTP (Time-based One-Time Passwords)
- **Authenticator Apps**: Google Authenticator, Authy, 1Password
- **Backup Codes**: Secure recovery when your device isn't available
- **Six-digit codes**: Change every 30 seconds for security

## Security Levels

### AAL1 (Single Factor)
- Email magic link authentication
- Platform authenticators (biometrics)
- Basic access to most features

### AAL2 (Two Factor)
- Required for administrative functions
- Sensitive data access
- User management operations
- Uses TOTP as second factor

## Setup Guide

### First-Time Login
1. Visit the STING login page
2. Enter your email address
3. Check your email for a magic link
4. Click the link to complete authentication
5. You'll be redirected to complete your profile

### Setting Up Biometric Authentication
1. Go to **Settings > Security**
2. Click **Add Biometric**
3. Follow your device's prompts (TouchID, FaceID, etc.)
4. Your biometric data stays on your device - never sent to our servers
5. Test the setup by logging out and back in

### Setting Up TOTP
1. Navigate to **Settings > Security**
2. Click **Set up TOTP Authentication**
3. Scan the QR code with your authenticator app
4. Enter the six-digit verification code
5. Save your backup codes in a secure location

### Adding Hardware Keys
1. In **Settings > Security**, click **Add Hardware Key**
2. Insert your security key when prompted
3. Follow the on-screen instructions
4. Test the key by using it to authenticate

## Account Recovery

### If You Lose Access
1. **Contact Support**: Email support@alphabytez.com
2. **Provide Verification**: Identity verification may be required
3. **Reset Process**: An admin can initiate account recovery
4. **Re-setup Security**: You'll need to set up your security methods again

### Admin Recovery Options
- **Recovery Token**: 15-minute temporary access tokens
- **Recovery Secret**: Emergency master secret for critical situations
- **TOTP Disable**: Remove TOTP requirement for locked accounts
- **CLI Tools**: Command-line recovery utilities

## Best Practices

### Security Recommendations
1. **Use Multiple Methods**: Set up both biometric and TOTP authentication
2. **Keep Backup Codes**: Store TOTP backup codes securely offline
3. **Regular Reviews**: Check your security settings monthly
4. **Update Devices**: Keep your devices and browsers updated
5. **Secure Email**: Ensure your email account has strong security

### What NOT to Do
- Don't share magic links with others
- Don't use the same device for multiple accounts without proper separation
- Don't ignore security warnings from your authenticator
- Don't screenshot QR codes or backup codes

## Troubleshooting

### Common Issues

#### "Invalid or Expired Magic Link"
- Links expire after 15 minutes for security
- Request a new link if yours has expired
- Check your spam folder for the email

#### "Biometric Authentication Failed"
- Ensure your device supports WebAuthn
- Try using a different browser
- Clear your browser's cache and cookies
- Re-register your biometric if the issue persists

#### "TOTP Code Invalid"
- Check that your device's clock is accurate
- Try the next code if the current one doesn't work
- Ensure you're using the correct authenticator app
- Use a backup code if available

#### "Hardware Key Not Detected"
- Ensure the key is properly inserted
- Try a different USB port
- Check browser compatibility (Chrome, Firefox, Safari, Edge)
- Some keys require touching/pressing to activate

### Browser Support
- **Chrome**: Full support for all features
- **Firefox**: Full support for all features
- **Safari**: Full support (requires iOS 14+ or macOS 11+)
- **Edge**: Full support for all features
- **Mobile Browsers**: Varies by device and OS version

## Technical Details

### Security Standards
- **FIDO2/WebAuthn**: Industry-standard biometric and hardware key authentication
- **OAuth 2.0**: Secure authorization framework
- **OpenID Connect**: Identity layer on top of OAuth 2.0
- **PKCE**: Proof Key for Code Exchange for additional security

### Privacy Features
- **No Password Storage**: We never store or handle passwords
- **Local Biometrics**: Biometric data never leaves your device
- **Encrypted Sessions**: All authentication sessions are encrypted
- **Audit Logging**: All authentication events are logged for security

For technical support or questions about authentication, contact our support team at support@alphabytez.com.