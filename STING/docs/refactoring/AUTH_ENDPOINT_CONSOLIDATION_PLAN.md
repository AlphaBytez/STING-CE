# Authentication Endpoint Consolidation Plan

## Problem Statement
The STING codebase currently has **11+ duplicate/overlapping authentication status endpoints** across multiple blueprints, creating significant technical debt and maintenance burden.

## Current State Analysis

### Duplicate Endpoints Found
```
/api/auth/aal-status         (3 different implementations)
/api/auth/2fa-status         (3 different implementations)
/api/auth/aal-status-v2      (2 different implementations)
/api/auth/aal2/status        (1 implementation)
/api/biometric/aal-status    (1 implementation)
/api/kratos-session/aal-status (1 implementation)
/api/enhanced-webauthn/session/aal-status (1 implementation)
```

### Files with Duplicate Endpoints
- `app/routes/auth_routes.py` - Contains multiple versions
- `app/routes/auth/aal_routes.py` - AAL-specific endpoints
- `app/routes/totp_routes.py` - TOTP-specific 2FA status
- `app/routes/mvp_routes.py` - MVP alias endpoints
- `app/routes/biometric_routes.py` - Biometric AAL status
- `app/routes/auth/kratos_session_routes.py` - Kratos-specific AAL
- `app/routes/enhanced_webauthn_routes.py` - WebAuthn AAL status

### Frontend Usage Patterns
- `SimpleProtectedRoute.jsx` → `/api/auth/aal2/status`
- `ModernEnrollment.jsx` → `/api/auth/aal2/status`
- `AAL2Provider.jsx` → `/api/aal2/status`
- `SecuritySettings.jsx` → `/api/auth/2fa-status` and `/api/auth/aal-status`
- Various other components use different variations

## Root Causes
1. **Conway's Law**: Different developers working on different auth features (biometric, TOTP, WebAuthn, AAL2)
2. **Iterative Development**: Each feature added its own endpoint instead of extending existing ones
3. **Lack of Central Architecture**: No unified auth status API design
4. **Copy-Paste Development**: Similar endpoints duplicated rather than refactored

## Proposed Solution

### Unified Endpoint Design
```python
@auth_bp.route('/api/auth/status', methods=['GET'])
def get_unified_auth_status():
    """
    Single source of truth for all authentication status needs
    """
    return {
        # Core Authentication
        'authenticated': bool,
        'user': {
            'id': str,
            'kratos_id': str,
            'email': str,
            'role': 'admin' | 'user',
            'needs_enrollment': bool
        },

        # AAL Status
        'aal': {
            'current_level': 'aal1' | 'aal2',
            'kratos_aal': 'aal1' | 'aal2',
            'flask_aal2_verified': bool,
            'needs_stepup': bool,
            'stepup_required_for': ['admin_dashboard', 'settings', etc]
        },

        # Configured Methods
        'methods': {
            'configured': {
                'email': bool,
                'passkey': bool,
                'totp': bool,
                'hardware_key': bool,
                'biometric': bool
            },
            'available': {
                # Methods available to configure
                'passkey': bool,
                'totp': bool,
                'hardware_key': bool
            },
            'recently_used': str  # Last method used for auth
        },

        # Session Information
        'session': {
            'id': str,
            'authenticated_at': timestamp,
            'expires_at': timestamp,
            'idle_timeout': int,
            'remember_me': bool
        },

        # Enrollment Status
        'enrollment': {
            'complete': bool,
            'required_methods': ['passkey', 'totp'],
            'missing_methods': ['totp'],
            'can_skip': bool
        },

        # Feature Flags (for frontend UI decisions)
        'features': {
            'biometric_available': bool,
            'hardware_key_supported': bool,
            'passwordless_enabled': bool
        }
    }
```

## Implementation Plan

### Phase 1: Create Unified Endpoint (Week 1)
1. [ ] Create `/api/auth/status` endpoint in new file `app/routes/auth/unified_status.py`
2. [ ] Implement comprehensive data gathering from all sources:
   - Kratos session data
   - Flask session data
   - Redis AAL2 cache
   - Database user info
3. [ ] Add comprehensive logging for debugging
4. [ ] Create unit tests for the new endpoint

### Phase 2: Create Adapter Layer (Week 2)
1. [ ] Create backwards-compatible adapters that call the new unified endpoint
2. [ ] Map old endpoint responses to new format
3. [ ] Add deprecation warnings in logs
4. [ ] Ensure all existing endpoints still work

### Phase 3: Frontend Migration (Weeks 3-4)
1. [ ] Create React hook: `useAuthStatus()` that calls unified endpoint
2. [ ] Update components one by one:
   - [ ] `SimpleProtectedRoute.jsx`
   - [ ] `ModernEnrollment.jsx`
   - [ ] `AAL2Provider.jsx`
   - [ ] `SecuritySettings.jsx`
   - [ ] `AAL2StepUp.jsx`
   - [ ] `AAL2StepUpModal.jsx`
3. [ ] Add feature flag to toggle between old/new endpoints
4. [ ] Test each component thoroughly

### Phase 4: Cleanup (Week 5)
1. [ ] Remove feature flag after successful production testing
2. [ ] Mark old endpoints as deprecated with sunset date
3. [ ] Update API documentation
4. [ ] Remove duplicate endpoint implementations
5. [ ] Clean up unused imports and code

## Benefits
- **50% reduction** in auth-related API code
- **Single source of truth** for auth status
- **Improved performance**: 1 API call instead of 2-3
- **Easier debugging**: One place to add logs/fixes
- **Better consistency**: All components get same data format
- **Reduced complexity**: New developers only need to understand one endpoint

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| Breaking existing functionality | Keep old endpoints working via adapters |
| Missing edge cases | Comprehensive testing with all auth scenarios |
| Performance regression | Cache unified response in Redis |
| Frontend components breaking | Feature flag for gradual rollout |

## Success Metrics
- [ ] All auth status API calls go to single endpoint
- [ ] 0 duplicate endpoint implementations
- [ ] Reduced auth-related bug reports by 30%
- [ ] API response time < 100ms (with caching)
- [ ] All frontend components successfully migrated

## Technical Debt Addressed
- Eliminates 10+ duplicate endpoints
- Removes ~1000 lines of redundant code
- Consolidates 7+ different response formats
- Reduces maintenance burden significantly

## Notes for Implementation
- Consider using Redis caching for the unified response (TTL: 5 seconds)
- Add OpenAPI/Swagger documentation for the new endpoint
- Consider versioning: `/api/v2/auth/status` for future updates
- Add request correlation IDs for debugging auth flows
- Consider adding GraphQL endpoint for selective field queries

## Related Documentation
- Current auth flow: `/docs/auth/AUTHENTICATION_FLOW.md`
- Kratos integration: `/docs/platform/kratos/KRATOS_INTEGRATION.md`
- AAL2 requirements: `/CLAUDE.md` (search for "AAL2")

---
*Created: 2025-09-19*
*Status: Planning*
*Priority: Medium (implement after current auth fixes)*
*Estimated Effort: 3-5 weeks*