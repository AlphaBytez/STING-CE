# Passwordless Authentication in STING

## Overview

STING implements a modern, passwordless authentication system that prioritizes security and user experience. Users can authenticate using:

1. **Passkeys (WebAuthn)** - Biometric authentication using device capabilities
2. **Email OTP** - One-time codes sent via email
3. **SMS OTP** - One-time codes sent via SMS (requires phone number)

## Architecture

### Authentication Flow
```
User → Login Page → Kratos → Authentication Method → Session → Dashboard
```

### Components

1. **Frontend Components**
   - `/frontend/src/components/auth/Login.jsx` - Main login page with glass morphism UI
   - `/frontend/src/components/auth/PasswordlessLogin.jsx` - Advanced passwordless flow with 2FA
   - `/frontend/src/components/settings/PasskeySettings.jsx` - Manage passkeys

2. **Backend Services**
   - **Ory Kratos** - Identity management and authentication
   - **MailHog** - Email testing service (development)
   - **SMS Mock** - SMS testing service (development)

3. **Configuration Files**
   - `/kratos/kratos.yml` - Main Kratos configuration
   - `/kratos/identity.schema.json` - User identity schema
   - `/kratos/courier-templates/` - Email/SMS templates

## User Experience

### First-Time Users

1. User enters email address
2. System checks if account exists
3. If new user:
   - Prompted to add phone number (2FA requirement)
   - Receives verification code via email
   - Account created upon successful verification
4. If existing user:
   - Receives login code via email/SMS
   - Enters code to authenticate

### Returning Users with Passkeys

1. Click "Sign in with Passkey"
2. Browser prompts for biometric/device authentication
3. Instant login upon successful verification

### Security Features

- **No passwords** - Eliminates password-related vulnerabilities
- **2FA by default** - Users must have at least 2 authentication methods
- **Time-limited codes** - OTP codes expire after 15 minutes
- **Rate limiting** - Prevents brute force attacks
- **Secure sessions** - HttpOnly, Secure, SameSite cookies

## Implementation Details

### Kratos Configuration

```yaml
selfservice:
  methods:
    webauthn:
      enabled: true
      config:
        passwordless: true
        rp:
          id: localhost
          display_name: STING Authentication
    
    code:
      enabled: true
      config:
        lifespan: 15m
```

### Identity Schema

```json
{
  "traits": {
    "email": {
      "type": "string",
      "format": "email",
      "ory.sh/kratos": {
        "credentials": {
          "password": { "identifier": true },
          "webauthn": { "identifier": true },
          "code": { "identifier": true }
        }
      }
    },
    "phone": {
      "type": "string",
      "pattern": "^\\+[1-9]\\d{1,14}$",
      "ory.sh/kratos": {
        "credentials": {
          "code": { "identifier": true, "via": "sms" }
        }
      }
    }
  }
}
```

### Frontend Integration

```javascript
// Initialize login flow
const response = await fetch(`${kratosUrl}/self-service/login/api`);
const flow = await response.json();

// Request OTP code
await fetch(`${kratosUrl}/self-service/login/flows/${flow.id}`, {
  method: 'POST',
  body: JSON.stringify({
    method: 'code',
    identifier: email
  })
});

// Verify code
await fetch(`${kratosUrl}/self-service/login/flows/${flow.id}`, {
  method: 'POST',
  body: JSON.stringify({
    method: 'code',
    code: otpCode
  })
});
```

## Testing

### Development Setup

1. **Start services**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
   ```

2. **Access testing UIs**:
   - Email: http://localhost:8025 (MailHog)
   - SMS: http://localhost:8030 (SMS Mock)
   - App: https://localhost:8443

3. **Test authentication**:
   ```bash
   ./kratos/test-passwordless-otp.sh
   ```

### Test Scenarios

1. **New User Registration**
   - Enter new email → Add phone → Verify code → Account created

2. **Existing User Login**
   - Enter email → Receive code → Verify → Logged in

3. **Passkey Authentication**
   - Click passkey button → Authenticate with device → Logged in

4. **2FA Enforcement**
   - Users without passkeys must provide phone number
   - Users with passkeys can use email as second factor

## Production Deployment

### Email Configuration

Replace MailHog with production email service:

```yaml
courier:
  smtp:
    connection_uri: smtps://apikey:SG.xxx@smtp.sendgrid.net:465
```

### SMS Configuration

Configure production SMS provider:

```yaml
courier:
  sms:
    enabled: true
    from: "STING"
    request_config:
      url: https://api.twilio.com/2010-04-01/Accounts/xxx/Messages.json
      method: POST
      auth:
        type: basic
        user: AC_ACCOUNT_SID
        password: AUTH_TOKEN
```

### Security Checklist

- [ ] Enable HTTPS for all endpoints
- [ ] Configure proper CORS settings
- [ ] Set secure cookie attributes
- [ ] Implement rate limiting
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Monitor failed authentication attempts

## Troubleshooting

### Common Issues

1. **"Failed to initialize login flow"**
   - Check Kratos is running: `docker ps`
   - Verify CORS configuration
   - Check browser console for errors

2. **Codes not received**
   - Check email service (MailHog: http://localhost:8025)
   - Verify SMTP configuration
   - Check Kratos logs: `docker logs sting-ce-kratos`

3. **Passkey not working**
   - Ensure HTTPS is enabled
   - Check browser compatibility
   - Verify WebAuthn configuration

### Debug Tools

- **Debug Page**: https://localhost:8443/debug
- **Kratos Admin API**: https://localhost:4434
- **Test Scripts**: `/kratos/test-*.sh`

## Future Enhancements

1. **Social Login** - OAuth providers (Google, GitHub, etc.)
2. **Magic Links** - Click-to-login email links
3. **Backup Codes** - Recovery codes for account access
4. **Device Management** - View and revoke trusted devices
5. **Risk-Based Authentication** - Additional verification for suspicious activity