# STING Passwordless Authentication System

## Overview

STING implements a comprehensive passwordless authentication system that prioritizes security while providing a seamless user experience. The system leverages modern authentication standards including WebAuthn, TOTP, and email-based verification through Ory Kratos.

## Architecture

### Core Components

1. **Ory Kratos** - Identity and user management service
2. **WebAuthn/Passkeys** - Biometric and hardware key authentication
3. **TOTP (Time-based One-Time Passwords)** - Authenticator app support
4. **Email Verification** - Magic links and verification codes
5. **Recovery Codes** - Backup authentication method

## Features Implemented

### 1. WebAuthn Authentication Prompts

**Component**: `WebAuthnPrompt.jsx`  
**Hook**: `useWebAuthnPrompt.js`

The WebAuthn prompt system provides secure biometric authentication for sensitive operations:

- **Report Protection**: Automatically prompts for authentication when accessing reports containing:
  - Financial data
  - PII (Personally Identifiable Information)
  - Compliance information
  - Documents marked as sensitive

- **Smart Detection**: The system intelligently determines when authentication is required based on:
  - Document classification
  - User role and permissions
  - Data sensitivity levels
  - Regulatory requirements

- **Fallback Options**: If biometric authentication fails or is unavailable:
  - TOTP via authenticator app
  - Email verification code
  - Recovery codes

### 2. Admin Setup Flow (Passwordless)

**Component**: `AdminSetupFlow.jsx`  
**Backend**: `admin_setup_routes.py`

The new admin registration process follows a secure, passwordless flow:

```
Email Registration → Email Verification (6-digit code) → TOTP Setup → Passkey Registration
```

#### Step 1: Email Registration
- Admin provides their email address
- System generates a unique verification code
- Code sent via configured SMTP (Mailpit for development)

#### Step 2: Email Verification
- User enters 6-digit verification code
- Session established upon successful verification
- Temporary access granted for setup completion

#### Step 3: TOTP Configuration
- QR code generated for authenticator apps
- Support for Google Authenticator, Authy, etc.
- User verifies setup with initial TOTP code

#### Step 4: Passkey Registration
- WebAuthn ceremony initiated
- Biometric or hardware key registered
- Multiple passkeys can be added for redundancy

### 3. Enhanced TOTP Login Flow

**Fixed Issues**:
- Corrected `method` parameter detection for TOTP submissions
- Fixed auto-submission handling for 6-digit codes
- Improved error messaging and user feedback
- Added proper AAL2 (Authentication Assurance Level 2) flow support

**Key Improvements**:
```javascript
// Automatic method detection based on form content
if (params.has('totp_code')) {
  params.append('method', 'totp');
} else if (params.has('lookup_secret')) {
  params.append('method', 'lookup_secret');
} else {
  params.append('method', 'password');
}
```

### 4. Theme-Aware Components

All authentication components support STING's three theme modes:

#### Modern Theme
- Glass morphism effects
- Blue accent colors
- Smooth transitions and animations
- Semi-transparent overlays

#### Retro Terminal Theme
- Monospace fonts
- Green terminal colors
- No rounded corners
- ASCII art decorations
- CRT-style effects

#### Retro Performance Theme
- Yellow/amber STING brand colors
- Minimal animations (performance-optimized)
- High contrast for readability
- No heavy effects or transitions

## API Endpoints

### Admin Setup Endpoints

```python
POST /api/auth/admin-setup-email
  - Initiates admin setup with email
  - Sends verification code
  - Returns: session_id, expires_in

POST /api/auth/admin-setup-verify-email
  - Verifies email code
  - Returns: totp_qr_code, totp_secret

POST /api/auth/admin-setup-totp
  - Verifies TOTP setup
  - Returns: success status

POST /api/auth/admin-setup-passkey
  - Completes setup with passkey registration
  - Creates admin identity in Kratos
  - Returns: admin_id
```

### TOTP Status Endpoint

```python
GET /api/auth/totp-status
  - Checks if user has TOTP configured
  - Returns: is_admin, has_totp, setup_required
```

## Security Features

### 1. Session Management
- Secure session tokens with httpOnly cookies
- Automatic session refresh
- Configurable session lifetime (default: 24h)

### 2. CSRF Protection
- Token validation on all state-changing operations
- Automatic token rotation
- SameSite cookie attributes

### 3. Rate Limiting
- Failed login attempt throttling
- Verification code request limits
- API endpoint protection

### 4. Encryption
- All sensitive data encrypted at rest
- TLS/HTTPS for all communications
- Secure key storage in Vault

## Configuration

### Kratos Configuration (kratos.yml)

```yaml
selfservice:
  methods:
    webauthn:
      enabled: true
      config:
        passwordless: true
        rp:
          id: localhost
          display_name: STING Platform
    totp:
      enabled: true
      config:
        issuer: STING Authentication
    code:
      enabled: true
      config:
        lifespan: 15m
    link:
      enabled: true
      config:
        lifespan: 1h
```

### Email Configuration (Mailpit for Development)

```yaml
courier:
  smtp:
    connection_uri: smtp://mailpit:1025/?skip_ssl_verify=true&disable_starttls=true
    from_address: noreply@sting.local
    from_name: STING Platform
```

## Development Setup

### Prerequisites

1. **Mailpit** - Email testing service
   ```bash
   docker run -d -p 1025:1025 -p 8025:8025 axllent/mailpit
   ```

2. **Kratos** - Identity service
   ```bash
   docker-compose up kratos kratos-migrate
   ```

### Testing Authentication Flows

1. **Admin Setup**: Navigate to `/admin-setup`
2. **TOTP Login**: Use existing admin account with TOTP enabled
3. **WebAuthn Testing**: Access any report marked as "sensitive"
4. **Email Verification**: Check Mailpit UI at `http://localhost:8026`

## Troubleshooting

### Common Issues

1. **TOTP Code Not Accepted**
   - Ensure device time is synchronized
   - Check authenticator app is using correct secret
   - Verify issuer name matches configuration

2. **WebAuthn Not Available**
   - Confirm HTTPS is enabled (required for WebAuthn)
   - Check browser compatibility
   - Verify domain configuration in Kratos

3. **Email Not Received**
   - Check Mailpit is running
   - Verify SMTP configuration
   - Review Kratos courier logs

### Debug Logging

Enable debug logging in components:

```javascript
console.log('🔐 WebAuthnPrompt:', debugInfo);
console.log('🔐 TOTPSetupNudge:', statusData);
console.log('🔐 AdminSetupFlow:', stepProgress);
```

## Migration Guide

### From Password-Based to Passwordless

1. **Existing Users**:
   - Prompted to set up TOTP on next login
   - WebAuthn registration offered after TOTP setup
   - Passwords remain as fallback during transition

2. **New Users**:
   - Automatically use passwordless flow
   - No password field presented
   - Email verification required for all accounts

3. **Admin Accounts**:
   - TOTP mandatory
   - WebAuthn strongly recommended
   - Higher session security requirements

## Future Enhancements

### Planned Features

1. **Hardware Security Keys**
   - YubiKey support
   - FIDO2 compliance
   - Multi-key management

2. **Risk-Based Authentication**
   - Device fingerprinting
   - Location-based checks
   - Behavioral analysis

3. **Single Sign-On (SSO)**
   - SAML 2.0 support
   - OAuth 2.0 / OpenID Connect
   - Active Directory integration

4. **Enhanced Recovery Options**
   - Social recovery
   - Trusted contacts
   - Time-delayed recovery

## Support

For issues or questions regarding passwordless authentication:

1. Check the [Troubleshooting](#troubleshooting) section
2. Review Kratos logs: `docker logs sting-ce-kratos`
3. File an issue at: https://github.com/stingce/sting/issues

## License

This authentication system is part of the STING platform and follows the same licensing terms as the main project.