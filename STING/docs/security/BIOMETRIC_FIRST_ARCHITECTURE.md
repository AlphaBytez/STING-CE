# STING Biometric-First Security Architecture

## Overview

STING implements a revolutionary **biometric-first security model** that treats passkeys as "secure API keys" with biometric verification. This eliminates TOTP fatigue while exceeding enterprise security standards.

## Core Concept: Passkeys as Secure API Keys

### Traditional API Keys vs Secure Keys

| Aspect | Traditional API Keys | Secure Keys (Passkeys) |
|--------|---------------------|------------------------|
| **Creation** | Generate random string | Cryptographic key pair |
| **Storage** | Server database (hashed) | Device secure enclave |
| **Authorization** | Include in HTTP headers | Biometric ceremony |
| **Verification** | String comparison | Public key crypto + biometric |
| **Compromise** | If leaked = full access | Requires device + biometric |
| **Expiration** | Time/manual expiry | Indefinite (biometric-protected) |
| **Portability** | Copy to any system | Device-bound, non-transferable |

### Security Properties

**Passkeys = Something You Have + Something You Are**
- **Device possession** (something you have)
- **Biometric verification** (something you are)
- **Result**: True 2FA in a single ceremony

**Traditional API Keys = Something You Know**
- Just a secret string
- If compromised, unlimited access until revoked

## Three-Tier Security Model

### Tier 1: Basic Access (AAL1)
**Methods:**
- Email + Magic Link/OTP Code
- Secure Keys (passkey with biometric)

**Access:**
- Dashboard navigation
- View non-sensitive data
- Basic user operations

**Cache:** Session-based (24 hours)

### Tier 2: Biometric Gate (Sensitive Operations)
**Method:**
- Touch ID/Face ID verification
- TOTP fallback for non-biometric devices

**Access:**
- Admin operations
- Audit logs and reports
- System configuration
- API key management
- Backup operations

**Cache:** 30 minutes (extended for better UX)

### Tier 3: Critical Operations (Nuclear Actions)
**Method:**
- TOTP required (no alternatives)

**Access:**
- User account deletion
- Account creation
- Passkey/Secure Key removal
- Email address changes

**Cache:** 15 minutes (shorter for maximum security)

## Implementation Details

### Backend Architecture

```python
# Biometric-first decorator
@require_biometric_or_api_key(['admin', 'write'])
def sensitive_operation():
    # 1. Check API key (bypass all verification)
    # 2. Check biometric verification (30-min cache)
    # 3. Fall back to TOTP AAL2 (15-min cache)
    # 4. Require step-up if neither satisfied
```

### Path Classification

```python
# app/__init__.py middleware
biometric_allowed_paths = [
    '/api/admin',      # Touch ID preferred
    '/api/audit',      # Touch ID preferred
    '/api/reports/',   # Touch ID preferred
    '/api/keys',       # Touch ID preferred
    # ... etc
]

aal2_required_paths = [
    '/api/user/delete',    # TOTP required
    '/api/user/create',    # TOTP required
    # ... critical account operations
]
```

### Frontend Integration

```javascript
// useBiometricGate hook
const { requireBiometric } = useBiometricGate();

// Wrap sensitive operations
const handleSensitiveAction = () => {
  requireBiometric(async () => {
    // Touch ID verification, then proceed
    await performSensitiveOperation();
  });
};
```

## Security Benefits

### Eliminates TOTP Fatigue
- **Before**: TOTP code every 15-30 minutes
- **After**: Touch ID tap every 30 minutes (for sensitive ops only)

### Stronger Than Traditional 2FA
- **Traditional**: Password + TOTP code (both can be phished)
- **Biometric Gate**: Device possession + biometric (phishing-resistant)

### Enterprise Compliance
- Biometric verification meets most enterprise 2FA requirements
- TOTP still available as fallback
- Clear audit trail of authentication methods

## User Experience

### Login Flow
1. **Quick Access**: Touch ID tap → Dashboard (no email checking)
2. **Sensitive Operation**: Another Touch ID tap → Proceed
3. **Critical Operation**: TOTP code required

### Device Scenarios
- **MacBook with Touch ID**: Optimal experience (Touch ID for everything)
- **iPhone/iPad**: Face ID/Touch ID (optimal experience)
- **Non-biometric device**: Email+code login, TOTP for sensitive ops
- **Hardware keys**: Future enhancement (YubiKey support)

## Flask AAL2 Role Reduction

### Before Biometric-First
- Flask managed ALL elevated authentication
- AAL2 required for ALL sensitive operations
- Complex session coordination between Kratos and Flask

### After Biometric-First
- **Biometric verification bypasses Flask AAL2** for most operations
- Flask AAL2 only handles:
  - TOTP fallback scenarios
  - Critical account operations
- **Result**: ~80% reduction in Flask AAL2 complexity

### Architectural Simplification
```
Old: Email → Kratos → Flask AAL2 → TOTP → Operation
New: Email → Biometric Gate → Operation
     (TOTP only for critical operations)
```

## Configuration

### Biometric Cache Duration
```python
# app/decorators/aal2.py
self.biometric_duration = 30 * 60  # 30 minutes
self.aal2_duration = 15 * 60       # 15 minutes (TOTP)
```

### Kratos WebAuthn Settings
```yaml
# conf/kratos/kratos.yml
webauthn:
  enabled: true
  config:
    passwordless: false  # Supplemental factor
    rp:
      id: localhost
      display_name: STING Authentication
```

## Migration Strategy

### Existing Users
- Current TOTP users: Continue working as before
- Current passkey users: Now get biometric gate benefits
- No breaking changes to existing authentication

### New Users
- Encouraged to set up "secure keys" (passkeys)
- TOTP as fallback option
- Clear explanation of biometric benefits

## Monitoring and Logging

### Security Events
- Biometric verification attempts
- Fallback to TOTP usage
- Critical operation access
- Failed verification attempts

### Analytics
- Biometric vs TOTP usage ratios
- Operation completion rates
- Security friction metrics

---

**Implementation Date**: September 2025
**Status**: Production Ready
**Next Review**: October 2025 (assess user adoption and security metrics)