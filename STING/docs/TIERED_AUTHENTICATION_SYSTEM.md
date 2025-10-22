# Tiered Authentication System

**Complete Implementation Guide for STING's Enterprise-Grade Security**

## 🎯 Overview

STING's Tiered Authentication System implements a progressive security model that treats **"passkeys as secure API keys"** with 4-tier protection levels. This system provides enterprise-grade security without friction for routine operations.

## 🏗️ Architecture

### Core Philosophy
- **AMR-Based Logic**: Uses Authentication Method Reference instead of confusing AAL levels
- **Session Persistence**: 5-minute authentication caching prevents double-prompts
- **Progressive Security**: Security requirements scale with operation sensitivity
- **Recovery-First**: Built-in recovery codes for business continuity

### Mental Model
Think of authentication like secure API tokens:
- **Tier 1**: Public operations (no token required)
- **Tier 2**: Basic operations (any valid token)
- **Tier 3**: Sensitive operations (secure token required)
- **Tier 4**: Critical operations (dual-factor token required)

## 🔐 Authentication Tiers

### Tier 1: Public Operations
**Requirements**: None
**Examples**: Health checks, static content, public documentation

```python
# No decorator required
@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy'})
```

### Tier 2: Basic Operations
**Requirements**: Any authentication method (email, passkey, TOTP)
**Examples**: View API keys, upload files, basic CRUD operations

```python
@require_auth_method(['webauthn', 'totp', 'email'])  # Tier 2
@app.route('/api/keys', methods=['GET'])
def list_api_keys():
    # Implementation
```

### Tier 3: Sensitive Operations
**Requirements**: Secure authentication (passkey OR TOTP only)
**Examples**: Create/delete API keys, delete files, modify settings

```python
@require_auth_method(['webauthn', 'totp'])  # Tier 3
@app.route('/api/keys', methods=['POST'])
def create_api_key():
    # Implementation
```

### Tier 4: Critical Operations
**Requirements**: Dual-factor authentication (passkey/TOTP + email confirmation)
**Examples**: Bulk operations, admin actions, account recovery

```python
@require_dual_factor(['webauthn', 'totp'], ['email'])  # Tier 4
@app.route('/api/keys/bulk-delete', methods=['DELETE'])
def bulk_delete_api_keys():
    # Implementation
```

## 🛠️ Implementation Components

### Backend Components

#### 1. Decorators (`app/utils/decorators.py`)
```python
# Tier 2: Basic auth required
@require_auth_method(['webauthn', 'totp', 'email'])

# Tier 3: Secure auth required
@require_auth_method(['webauthn', 'totp'])

# Tier 4: Dual-factor required
@require_dual_factor(['webauthn', 'totp'], ['email'])
```

#### 2. Session Caching
- **Duration**: 5 minutes for each operation tier
- **Storage**: Flask session with Redis backend
- **Markers**: `tier_2_auth_time`, `tier_3_auth_time`, etc.

#### 3. Recovery Codes (`app/models/recovery_code_models.py`)
- **Format**: `XXXX-XXXX-XXXX` (12 characters)
- **Quantity**: 10 codes per user
- **Usage**: One-time use with audit logging
- **Expiration**: 1 year from generation

#### 4. Audit Logging (`app/models/audit_log_models.py`)
- **Events**: All authentication attempts and security operations
- **Storage**: PostgreSQL with indexed queries
- **Retention**: 365 days (configurable)
- **Compliance**: GDPR/HIPAA ready

### Frontend Components

#### 1. Tiered Auth Utilities (`frontend/src/utils/tieredAuth.js`)
```javascript
// Check if user can perform an operation
const canProceed = await checkOperationAuth('CREATE_API_KEY', 2);

// Handle return from authentication flow
const justAuthenticated = handleReturnFromAuth('CREATE_API_KEY');

// Clear authentication markers after success
clearAuthMarker('CREATE_API_KEY');
```

#### 2. Operation Definitions
```javascript
export const OPERATIONS = {
  CREATE_API_KEY: {
    name: 'CREATE_API_KEY',
    tier: 2,
    description: 'Create new API key'
  },
  DELETE_API_KEY: {
    name: 'DELETE_API_KEY',
    tier: 3,
    description: 'Delete API key'
  }
};
```

#### 3. Enhanced Error Handling
- **Structured Errors**: Type-specific error handling
- **User Feedback**: Clear, actionable error messages
- **Debug Info**: Detailed logging for development

## 🚀 Usage Examples

### Adding Tiered Auth to New Routes

#### Step 1: Choose Appropriate Tier
```python
# Tier 2: Basic file upload
@file_bp.route('/upload', methods=['POST'])
@require_auth_method(['webauthn', 'totp', 'email'])
def upload_file():
    pass

# Tier 3: File deletion
@file_bp.route('/<file_id>', methods=['DELETE'])
@require_auth_method(['webauthn', 'totp'])
def delete_file(file_id):
    pass

# Tier 4: Bulk file deletion
@file_bp.route('/bulk-delete', methods=['DELETE'])
@require_dual_factor(['webauthn', 'totp'], ['email'])
def bulk_delete_files():
    pass
```

#### Step 2: Add Audit Logging
```python
from app.utils.audit_logger import AuditLogger

# Log successful operations
AuditLogger.log_security_event(
    description=f"File '{filename}' uploaded by {user.email}",
    severity=AuditSeverity.MEDIUM,
    user=user,
    details={'filename': filename, 'file_size': size}
)
```

#### Step 3: Frontend Integration
```javascript
// Pre-check authentication before showing form
const handleCreateClick = async () => {
    const canProceed = await checkOperationAuth('CREATE_ITEM', 2);
    if (canProceed) {
        setShowCreateModal(true);
    }
    // User redirected to auth if needed
};

// Handle form submission with pre-verified auth
const submitForm = async (data) => {
    // No additional auth check needed - already verified
    const response = await api.post('/api/items', data);
    clearAuthMarker('CREATE_ITEM'); // Clear after success
};
```

### Recovery Code Implementation

#### Generate Recovery Codes
```bash
curl -X POST https://localhost:5050/api/recovery/codes/generate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"count": 10}'
```

#### Use Recovery Code
```bash
curl -X POST https://localhost:5050/api/recovery/codes/verify \
  -H "Content-Type: application/json" \
  -d '{
    "code": "A1B2-C3D4-E5F6",
    "user_id": "kratos-user-id"
  }'
```

## 📊 Monitoring & Analytics

### Audit Log Queries
```python
# Get user activity
activity = AuditLog.get_user_activity(user_id, days=30)

# Get security events
security_events = AuditLog.get_security_events(
    severity=AuditSeverity.HIGH,
    days=7
)

# Cleanup old logs
deleted_count = AuditLog.cleanup_old_logs(days=365)
```

### Key Metrics
- **Authentication Success Rate**: Successful vs failed attempts
- **Tier Distribution**: Which tiers are used most frequently
- **Recovery Code Usage**: How often backup authentication is needed
- **Session Duration**: Average time between authentications

## 🧪 Testing

### Automated Testing
```bash
# Run comprehensive test suite
node scripts/test-tiered-auth-system.js

# Test specific operations
node scripts/test-api-key-flow.js
```

### Manual Testing Checklist
- [ ] **API Key Creation**: Test Tier 2 authentication requirement
- [ ] **File Operations**: Verify tiered requirements for upload/delete
- [ ] **Recovery Codes**: Generate, use, and revoke codes
- [ ] **Session Persistence**: Verify 5-minute caching works
- [ ] **Error Handling**: Test network failures and invalid auth
- [ ] **Audit Logging**: Verify events are recorded correctly

## 🔧 Configuration

### Environment Variables
```bash
# Session configuration
REDIS_URL=redis://redis:6379/0
SESSION_PERMANENT=false
SESSION_COOKIE_SECURE=true

# Authentication tiers
TIER_2_CACHE_DURATION=300  # 5 minutes
TIER_3_CACHE_DURATION=300  # 5 minutes
TIER_4_CACHE_DURATION=60   # 1 minute (more secure)

# Recovery codes
RECOVERY_CODE_EXPIRY_DAYS=365
MAX_RECOVERY_CODES_PER_USER=10

# Audit logging
AUDIT_LOG_RETENTION_DAYS=365
AUDIT_LOG_CLEANUP_INTERVAL=86400  # Daily
```

### Database Tables
```sql
-- Recovery codes table
CREATE TABLE recovery_codes (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    user_email VARCHAR(255) NOT NULL,
    code_hash VARCHAR(255) NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT NOW(),
    used_at TIMESTAMP,
    is_used BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMP NOT NULL
);

-- Audit logs table
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_id VARCHAR(255),
    user_email VARCHAR(255),
    ip_address VARCHAR(45),
    message TEXT NOT NULL,
    details JSONB,
    success BOOLEAN DEFAULT TRUE
);

-- Create indexes for performance
CREATE INDEX idx_recovery_codes_user_id ON recovery_codes(user_id);
CREATE INDEX idx_audit_logs_user_timestamp ON audit_logs(user_id, timestamp);
CREATE INDEX idx_audit_logs_event_type ON audit_logs(event_type);
```

## 🔒 Security Considerations

### Best Practices
1. **Principle of Least Privilege**: Start with lower tiers, escalate only when needed
2. **Session Timeout**: Keep authentication caching short (5 minutes max)
3. **Recovery Codes**: Treat like passwords - secure storage required
4. **Audit Everything**: Log all authentication events for compliance
5. **Regular Review**: Monitor tier usage patterns for optimization

### Threat Mitigation
- **Credential Stuffing**: Rate limiting on authentication endpoints
- **Session Hijacking**: Secure cookies with SameSite=Strict
- **Recovery Code Abuse**: One-time use with IP tracking
- **Privilege Escalation**: Explicit tier requirements prevent bypass

## 📈 Future Enhancements

### Planned Features
1. **Risk-Based Authentication**: Dynamic tier requirements based on user behavior
2. **Device Trust**: Remember trusted devices for reduced friction
3. **Conditional Access**: Location and time-based authentication policies
4. **Advanced Analytics**: ML-powered fraud detection
5. **API Rate Limiting**: Per-tier rate limits for enhanced security

### Integration Opportunities
- **SIEM Integration**: Export audit logs to security systems
- **Identity Providers**: SSO integration with tiered requirements
- **Mobile Apps**: Push notification-based authentication
- **Hardware Tokens**: FIDO2 hardware key support

## 📚 Additional Resources

- [Frontend Tiered Auth Utils](../frontend/src/utils/tieredAuth.js)
- [Backend Decorators](../app/utils/decorators.py)
- [Audit Logger](../app/utils/audit_logger.py)
- [Recovery Code Models](../app/models/recovery_code_models.py)
- [Test Suite](../scripts/test-tiered-auth-system.js)

---

**Last Updated**: September 2025
**Version**: 1.0.0
**Status**: Production Ready

This implementation successfully transforms STING from traditional 2FA into a modern, tiered authentication platform that provides enterprise-grade security with consumer-grade user experience.