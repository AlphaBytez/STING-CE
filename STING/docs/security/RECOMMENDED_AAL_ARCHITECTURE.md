# STING Biometric-First Security Architecture

## New Security Model (September 2025)

STING implements a **biometric-first security architecture** that treats passkeys like "secure API keys" with biometric verification. This eliminates TOTP fatigue while maintaining enterprise security standards.

## Security Levels

### Level 1: Basic Access (AAL1)
**Authentication Methods:**
- Email + Magic Link/OTP Code (primary method)
- **Secure Keys** (passkeys with biometric protection)

**Access Granted:**
- Dashboard navigation
- View non-sensitive data
- Basic user operations

**Mental Model:** Traditional login methods

### Level 2: Biometric Gate (30-minute cache)
**Verification Method:**
- **Touch ID/Face ID verification** (instant tap)
- TOTP fallback (if biometric unavailable)

**Access Granted:**
- Admin operations (`/api/admin`)
- Audit logs (`/api/audit`)
- Reports generation (`/api/reports`)
- System configuration (`/api/system`)
- API key management (`/api/keys`)
- Backup operations (`/api/backup`)

**Mental Model:** Your "secure keys" (passkeys) work like indefinite API keys, but require biometric verification for sensitive operations

### Level 3: Critical Operations (15-minute cache)
**Verification Method:**
- **TOTP required** (no alternatives)

**Access Granted:**
- User account deletion (`/api/user/delete`)
- Account creation (`/api/user/create`)
- Passkey/Secure Key removal (`/api/webauthn/passkey/remove`)

**Mental Model:** True "nuclear" operations that always require TOTP code

## Why This Architecture?

### The Kratos WebAuthn AAL2 Bug
- Kratos v1.3.x has a known bug where WebAuthn cannot be used for AAL2 elevation
- Even with biometric enforcement (`user_verification: required`), Kratos won't provide WebAuthn triggers in AAL2 flows
- This is a Kratos limitation, not a STING implementation issue

## The "Secure Keys" Concept

### Passkeys as Secure API Keys
Think of passkeys as **personal API keys that require biometric authorization**:

- **Like API Keys**: Stored securely, work indefinitely, bypass traditional login
- **Unlike API Keys**: Require biometric verification (Touch ID/Face ID) for sensitive operations
- **Security Model**: Device possession + biometric verification = 2FA in one step

### Comparison to Traditional API Keys

| Feature | Traditional API Keys | Secure Keys (Passkeys) |
|---------|---------------------|------------------------|
| **Creation** | Generate random string | Create cryptographic key pair |
| **Storage** | Server database (hashed) | Device secure enclave |
| **Usage** | Send in headers | Biometric ceremony |
| **Verification** | String comparison | Public key cryptography + biometric |
| **Compromise Risk** | If leaked, full access | Requires physical device + biometric |
| **Expiration** | Manual/time-based | Never (secured by biometric) |

### User Experience Benefits
- **No TOTP fatigue**: Biometric tap instead of 6-digit codes
- **Faster than email**: No inbox checking required
- **More secure than passwords**: Can't be phished or reused
- **Device-bound**: Works offline, doesn't rely on SMS/email delivery

### TOTP for AAL2
- **Reliable**: Works consistently with Kratos AAL2
- **Universal**: Works on all devices with authenticator apps
- **Trade-off**: Requires pulling out phone/device for AAL2 operations

## UX Considerations

### The AAL2 Frequency Problem
Requiring TOTP every 15-30 minutes for admin operations creates significant friction. Consider:

1. **Extend AAL2 Session Duration**
   - Current: 15-30 minutes (banking-level)
   - Recommended: 4-8 hours (enterprise-level)
   - Configure via `privileged_session_max_age` in kratos.yml

2. **Smart AAL2 Requirements**
   - Only require AAL2 for truly sensitive operations
   - Cache AAL2 verification for related operations
   - Group AAL2-required operations together in UI

3. **Alternative Approaches**
   - Consider risk-based authentication (location, device, behavior)
   - Implement "remember this device" for trusted devices
   - Use session-based AAL2 elevation rather than time-based

## Future Improvements

### When Kratos Fixes WebAuthn AAL2
Once the bug is fixed, we can:
1. Re-enable passkey for AAL2 elevation
2. Offer choice between TOTP and Passkey for AAL2
3. Potentially make passkey the preferred AAL2 method

### Hardware Security Keys
Consider adding support for:
- YubiKey
- FIDO2 hardware keys
- These work better with Kratos for AAL2 than platform authenticators

## Implementation Status

### ✅ Implemented (September 2025)
- **Basic Access**: Email + Code OR Secure Keys (passkeys)
- **Biometric Gate**: Touch ID/Face ID for sensitive operations (30-min cache)
- **TOTP Fallback**: For devices without biometric capability
- **Critical Operations**: TOTP-only for account changes (15-min cache)

### 🔧 Technical Implementation
- **Backend**: `@require_biometric_or_api_key` decorator in `/app/utils/decorators.py`
- **Middleware**: Biometric-first checking in `/app/__init__.py`
- **Frontend**: `useBiometricGate` hook in `/frontend/src/hooks/useBiometricGate.js`
- **API Integration**: Uses existing `/api/biometric/record-auth` endpoint

### ⏳ Future Enhancements
- Hardware security key support (YubiKey, FIDO2)
- Risk-based authentication (location, device, behavior)
- "Remember this device" for trusted devices

## Configuration

### Current Settings
```yaml
# kratos.yml
webauthn:
  enabled: true
  config:
    passwordless: false  # Supplemental factor only

totp:
  enabled: true
  config:
    issuer: STING Authentication

# AAL2 session duration (adjust based on security needs)
privileged_session_max_age: 4h  # Recommended for enterprise
```

### Flask AAL2 Management
- Flask manages AAL2 elevation (not Kratos)
- Redis caches AAL2 status
- Session coordination between Kratos and Flask

## Security Trade-offs

### What We Lose
- No biometric AAL2 (would be ideal)
- TOTP fatigue for frequent AAL2 operations
- Mixed authentication systems

### What We Gain
- Working AAL2 elevation today
- Reliable security boundaries
- Clear user experience (TOTP = elevated access)

## Recommendations

1. **For Most Users**: Use email+code for login, TOTP for sensitive operations
2. **For Power Users**: Configure passkey for quick AAL1 login
3. **For Admins**: Accept TOTP requirement, extend session duration
4. **For Enterprise**: Consider 4-8 hour AAL2 sessions to reduce TOTP fatigue

---

*Last Updated: September 2025*
*Status: Production workaround for Kratos WebAuthn AAL2 bug*