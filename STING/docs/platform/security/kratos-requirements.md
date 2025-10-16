# Kratos v1.3.1 Requirements & Configuration Guide

## Overview
This document outlines the specific requirements and configuration patterns for Ory Kratos v1.3.1 in the STING platform, focusing on WebAuthn/Passkey authentication and AAL (Authenticator Assurance Level) requirements.

## Version Information
- **Kratos Version**: v1.3.1 (config) / v1.3.0 (runtime)
- **WebAuthn Support**: Full WebAuthn Level 2 support
- **AAL Support**: AAL1 and AAL2 levels supported

## Key Kratos Concepts

### Authenticator Assurance Levels (AAL)
- **AAL1**: Single factor authentication (email codes, passwords)
- **AAL2**: Multi-factor authentication (WebAuthn + AAL1, TOTP + AAL1)

### Important: AAL vs Registration
- **Registration**: Creating a WebAuthn credential (settings flow)
- **Authentication**: Using a WebAuthn credential (login flow)
- **Critical**: Registration alone does NOT upgrade session to AAL2
- **Required**: Must authenticate WITH the credential to achieve AAL2

## WebAuthn Configuration

### Current Working Configuration
```yaml
selfservice:
  methods:
    webauthn:
      enabled: true
      config:
        passwordless: true  # Enables WebAuthn as primary auth method
        rp:
          id: localhost
          display_name: STING Platform
          origins:
          - https://localhost:8443
          - http://localhost:8443
```

### WebAuthn Registration Flow
1. User initiates settings flow: `GET /.ory/self-service/settings/browser`
2. Frontend finds WebAuthn trigger node in flow UI
3. Form submission triggers WebAuthn credential creation
4. **Critical**: Must allow Kratos to complete the flow naturally
5. Credential stored in `session.identity.credentials.webauthn.config.credentials[]`

### WebAuthn Authentication Flow (AAL2)
1. User initiates login flow with `?aal=aal2`
2. Kratos provides WebAuthn challenge
3. User completes WebAuthn authentication
4. Session upgraded to `authenticator_assurance_level: "aal2"`

## Critical Implementation Details

### ❌ What NOT to Do
- **Don't hijack form submissions** - prevents Kratos from saving credentials
- **Don't block all redirects** - breaks Kratos flow completion
- **Don't assume registration = AAL2** - registration is AAL1, authentication is AAL2

### ✅ What TO Do
- **Work WITH Kratos flows** - let forms submit naturally
- **Monitor session changes** - check `identity.credentials.webauthn` for completion
- **Handle redirects gracefully** - allow Kratos to complete its process
- **Implement proper AAL step-up** - use dedicated AAL2 authentication

## Session Structure

### Successful WebAuthn Registration
```javascript
session.identity.credentials.webauthn = {
  config: {
    credentials: [
      {
        id: "credential_id",
        display_name: "Admin Passkey",
        // ... other WebAuthn data
      }
    ]
  }
}
```

### Authentication Methods History
```javascript
session.authentication_methods = [
  { method: 'code', aal: 'aal1', completed_at: '...' },      // Email
  { method: 'webauthn', aal: 'aal2', completed_at: '...' }   // Passkey auth (AAL2)
]
```

## STING-Specific Requirements

### Admin User Flow
1. **Initial Login**: Email code (AAL1)
2. **AAL2 Requirement**: Detected by role check
3. **Passkey Setup**: If no WebAuthn credentials exist
4. **AAL2 Authentication**: Use passkey to upgrade session
5. **Dashboard Access**: Only with AAL2 session

### Frontend Implementation Patterns

#### Correct Passkey Registration
```javascript
// 1. Get settings flow
const flow = await axios.get('/.ory/self-service/settings/browser');

// 2. Find WebAuthn trigger
const trigger = flow.ui.nodes.find(n => 
  n.group === 'webauthn' && 
  n.attributes?.name === 'webauthn_register_trigger'
);

// 3. Create form with ALL flow inputs
const form = document.createElement('form');
form.action = flow.ui.action;
form.method = 'POST';

// 4. Let form submit naturally - DON'T prevent default
form.onsubmit = async (e) => {
  e.preventDefault();
  // Trigger WebAuthn, but let Kratos handle the rest
  await window.oryWebAuthnRegistration(options);
};
```

#### Session Monitoring
```javascript
// Check for credential creation
const session = await fetch('/.ory/sessions/whoami').then(r => r.json());
const hasWebAuthn = session.identity?.credentials?.webauthn?.config?.credentials?.length > 0;
const aalLevel = session.authenticator_assurance_level; // 'aal1' or 'aal2'
```

## Troubleshooting Common Issues

### Issue: Passkey Registration Appears to Work But No Credentials Saved
**Cause**: Form submission was hijacked, preventing Kratos from processing
**Solution**: Allow natural form submission, monitor session for completion

### Issue: WebAuthn Authentication Gives AAL1 Instead of AAL2
**Cause**: Using registration flow instead of authentication flow
**Solution**: Use login flow with `?aal=aal2` parameter

### Issue: Redirect Loops During Registration
**Cause**: Overly aggressive redirect prevention
**Solution**: Allow Kratos settings flows to complete naturally

## Configuration Validation

### Required Environment
- HTTPS enabled (WebAuthn requirement)
- Valid domain configuration in `rp.origins`
- Proper certificate setup for localhost development

### Testing Checklist
- [ ] Registration creates credentials in session
- [ ] Authentication upgrades session to AAL2
- [ ] AAL requirements properly enforced
- [ ] Passkey works across browser sessions

## References
- [Ory Kratos WebAuthn Documentation](https://www.ory.sh/docs/kratos/mfa/webauthn-fido)
- [Ory Kratos AAL Documentation](https://www.ory.sh/docs/kratos/mfa/aal)
- [WebAuthn Specification](https://w3c.github.io/webauthn/)

---
**Last Updated**: August 2025
**Kratos Version**: v1.3.1
**Status**: WebAuthn registration fixed, AAL2 authentication pending