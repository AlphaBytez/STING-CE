# Administrative Scripts Reference

## Overview

This document catalogs all administrative scripts available in STING CE, their locations, usage, and common scenarios.

## Script Location

All administrative scripts are located in: `scripts/admin/`

**Important:** As of this update, `interface.sh` correctly looks for scripts in `scripts/admin/` with a fallback to legacy `scripts/` location for backwards compatibility.

## Available Scripts

### 1. create-new-admin.py

**Purpose:** Create new admin user accounts

**Location:** `scripts/admin/create-new-admin.py`

**Usage via msting CLI:**
```bash
# Create passwordless admin (recommended - default)
sudo msting create admin admin@example.com

# Create with password (legacy, not recommended)
sudo msting create admin admin@example.com --use-password

# Create with specific password
sudo msting create admin admin@example.com --use-password --password='SecurePass123!'
```

**Direct usage:**
```bash
cd /opt/sting-ce
docker cp scripts/admin/create-new-admin.py sting-ce-app:/tmp/
docker exec sting-ce-app python /tmp/create-new-admin.py --email=admin@example.com
```

**Features:**
- ✅ Passwordless authentication (email-based)
- ✅ Password-based authentication (legacy support)
- ✅ Automatic Kratos identity creation
- ✅ STING database synchronization
- ✅ Admin role assignment

**Output:**
- Admin email
- Authentication method
- First login instructions
- Security setup requirements

---

### 2. create-service-api-key.py

**Purpose:** Create API keys for service-to-service authentication

**Location:** `scripts/admin/create-service-api-key.py`

**Usage:**
```bash
cd /opt/sting-ce
docker cp scripts/admin/create-service-api-key.py sting-ce-app:/tmp/
docker exec sting-ce-app python /tmp/create-service-api-key.py \
    --service-name="External Integration" \
    --description="API access for external service"
```

**Features:**
- Generates secure API keys
- Associates keys with service names
- Stores in STING database
- Returns key for configuration

**Use Cases:**
- External API integrations
- Automated workflows
- Service-to-service authentication
- CI/CD pipeline access

---

### 3. create_claude_user.py

**Purpose:** Create user account specifically configured for Claude AI integration

**Location:** `scripts/admin/create_claude_user.py`

**Usage:**
```bash
cd /opt/sting-ce
docker cp scripts/admin/create_claude_user.py sting-ce-app:/tmp/
docker exec sting-ce-app python /tmp/create_claude_user.py --email=claude@sting.local
```

**Features:**
- Specialized user profile for AI interactions
- Pre-configured permissions for Claude
- Automatic role assignment
- Database synchronization

**Use Cases:**
- Setting up Claude AI integration
- Automated AI-assisted workflows
- Bot account management

---

### 4. reset_admin_password.py

**Purpose:** Reset admin user password (for password-based accounts)

**Location:** `scripts/admin/reset_admin_password.py`

**Usage:**
```bash
cd /opt/sting-ce
docker cp scripts/admin/reset_admin_password.py sting-ce-app:/tmp/
docker exec sting-ce-app python /tmp/reset_admin_password.py \
    --email=admin@example.com \
    --new-password='NewSecurePass123!'
```

**Features:**
- Password reset for existing accounts
- Validates password strength
- Updates Kratos credentials
- Maintains user history

**Use Cases:**
- Forgotten password recovery
- Security incident response
- Credential rotation

**Note:** Only works for password-based accounts. Passwordless accounts don't have passwords to reset.

---

### 5. diagnose_admin_status.sh

**Purpose:** Comprehensive diagnostics for admin account issues

**Location:** `scripts/admin/diagnose_admin_status.sh`

**Usage:**
```bash
cd /opt/sting-ce
./scripts/admin/diagnose_admin_status.sh admin@example.com
```

**What it checks:**
- ✅ Kratos identity existence
- ✅ STING database user record
- ✅ Role assignments
- ✅ Authentication credentials
- ✅ Session status
- ✅ Security settings (TOTP, passkeys)

**Output:**
- Detailed status report
- Identified issues
- Recommended fixes
- Commands to resolve problems

**Use Cases:**
- Troubleshooting login issues
- Verifying account setup
- Pre-migration checks
- Security audits

---

### 6. recover_admin_account.sh

**Purpose:** Automated recovery for broken admin accounts

**Location:** `scripts/admin/recover_admin_account.sh`

**Usage:**
```bash
cd /opt/sting-ce
sudo ./scripts/admin/recover_admin_account.sh admin@example.com
```

**What it does:**
1. Diagnoses the issue
2. Backs up current state
3. Cleans up broken data
4. Recreates admin account
5. Restores valid data
6. Verifies recovery

**Features:**
- ✅ Automatic issue detection
- ✅ Safe backup before changes
- ✅ Database cleanup
- ✅ Kratos identity repair
- ✅ Verification tests

**Use Cases:**
- "Admin exists but can't login"
- Corrupted credentials
- Missing database records
- Orphaned Kratos identities
- Post-migration issues

**Safety:**
- Creates backups before any changes
- Dry-run mode available
- Rollback capability
- Detailed logging

---

## Common Scenarios

### Scenario 1: Fresh Installation - Create First Admin

```bash
# After installation completes
sudo msting create admin admin@yourdomain.com

# Follow the email verification link
# Set up TOTP authentication
# Optionally add passkey
```

### Scenario 2: Admin Can't Login

```bash
# Step 1: Diagnose the issue
cd /opt/sting-ce
./scripts/admin/diagnose_admin_status.sh admin@yourdomain.com

# Step 2: If issues found, recover
sudo ./scripts/admin/recover_admin_account.sh admin@yourdomain.com
```

### Scenario 3: Create Service API Key

```bash
# For external integrations
cd /opt/sting-ce
docker cp scripts/admin/create-service-api-key.py sting-ce-app:/tmp/
docker exec sting-ce-app python /tmp/create-service-api-key.py \
    --service-name="Monitoring System" \
    --description="Prometheus metrics access"

# Save the generated API key securely
```

### Scenario 4: Setup Claude AI Integration

```bash
# Create specialized Claude user
cd /opt/sting-ce
docker cp scripts/admin/create_claude_user.py sting-ce-app:/tmp/
docker exec sting-ce-app python /tmp/create_claude_user.py --email=claude@sting.local

# Configure Claude with credentials
```

### Scenario 5: Password Reset (Legacy Accounts)

```bash
# For password-based accounts only
cd /opt/sting-ce
docker cp scripts/admin/reset_admin_password.py sting-ce-app:/tmp/
docker exec sting-ce-app python /tmp/reset_admin_password.py \
    --email=admin@example.com \
    --new-password='NewPass123!'
```

## Script Development Guidelines

When adding new administrative scripts:

### 1. **Location**
- Always place in `scripts/admin/`
- Use descriptive names
- Follow naming convention: `verb_noun.py` or `verb-noun.sh`

### 2. **Shebang**
```python
#!/usr/bin/env python3
```
```bash
#!/bin/bash
```

### 3. **Documentation**
Include at the top:
```python
"""
Brief description of what the script does

Usage:
    python script_name.py --arg1=value --arg2=value

Arguments:
    --arg1: Description
    --arg2: Description
"""
```

### 4. **Error Handling**
- Use try-except blocks
- Provide meaningful error messages
- Return appropriate exit codes

### 5. **Logging**
- Log all important actions
- Include timestamps
- Use appropriate log levels

### 6. **Security**
- Validate all inputs
- Use secure credential handling
- Never log sensitive data
- Require appropriate privileges

## Troubleshooting

### Script Not Found Error

**Error:**
```
Admin creation script not found
Expected locations:
  - /path/to/scripts/admin/create-new-admin.py
```

**Solution:**
```bash
# Check if scripts exist
ls -la /opt/sting-ce/scripts/admin/

# If missing, copy from source
sudo cp -r /path/to/source/scripts/admin/* /opt/sting-ce/scripts/admin/
```

### Permission Denied

**Error:**
```
Permission denied when executing script
```

**Solution:**
```bash
# Make script executable
sudo chmod +x /opt/sting-ce/scripts/admin/script_name.py

# Or run via interpreter
python /opt/sting-ce/scripts/admin/script_name.py
```

### Docker Container Not Found

**Error:**
```
Error: No such container: sting-ce-app
```

**Solution:**
```bash
# Check if services are running
sudo msting status

# If not running, start services
sudo msting start
```

### Database Connection Error

**Error:**
```
STING database sync error: Connection refused
```

**Solutions:**
1. Check database is running:
   ```bash
   docker ps | grep sting-ce-db
   ```

2. Verify network connectivity:
   ```bash
   docker exec sting-ce-app curl -I http://sting-ce-db:5432
   ```

3. Check database credentials in environment files

## Integration with msting CLI

The `msting` CLI automatically handles script execution for common operations:

```bash
# These commands use the admin scripts internally:
sudo msting create admin <email>              # → create-new-admin.py
sudo msting recreate admin <email>            # → recover + create
sudo msting diagnose admin <email>            # → diagnose_admin_status.sh
```

For direct script access, use the script files in `scripts/admin/`.

## Best Practices

1. **Always Use msting CLI First**
   - The CLI provides proper error handling
   - Handles Docker container communication
   - Includes security checks

2. **Direct Script Usage**
   - Only when CLI doesn't cover your use case
   - For custom automation
   - For debugging purposes

3. **Backup Before Changes**
   - Always backup before running recovery scripts
   - Use `diagnose` before `recover`
   - Test on non-production first

4. **Security**
   - Never commit passwords to git
   - Use strong passwords if not passwordless
   - Rotate API keys regularly
   - Monitor admin account access

## Related Documentation

- [Admin Setup Guide](../guides/ADMIN_SETUP.md)
- [Admin Panel Documentation](ADMIN_PANEL_DOCUMENTATION.md)
- [Authentication Guide](../guides/kratos-integration-guide.md)
- [API Key Management](../api/API_REFERENCE.md)

---

**Last Updated:** 2025-10-10
**Version:** 1.0
**Maintainer:** STING CE Team
