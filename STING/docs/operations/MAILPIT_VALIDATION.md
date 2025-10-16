# Mailpit Validation System

## Overview

STING's authentication flow depends on email delivery for:
- Email verification codes
- Magic links (passwordless authentication)
- Password recovery emails
- Multi-factor authentication codes

When mailpit (the development email catcher) is misconfigured, **authentication becomes blocked** - users cannot log in or register.

This validation system provides comprehensive automated checks to catch mailpit issues early.

## What Was Fixed

### Previous Issues

1. **Port Mapping Bug**: docker-compose.yml had incorrect mapping `8025:8026` instead of `8025:8025`
   - Mailpit container listens on port 8025
   - Mapping was trying to connect to non-existent port 8026
   - Result: Web UI might load but emails weren't received

2. **Basic Healthcheck**: Only checked if port 1025 was open (`nc -z localhost 1025`)
   - Didn't verify SMTP actually works
   - Didn't check port mapping correctness
   - Didn't test end-to-end email delivery

3. **No Startup Validation**: Issues weren't detected until auth failed
   - Silent failures during installation
   - Manual troubleshooting required
   - Auth blocked without clear diagnosis

## Validation System Components

### 1. Comprehensive Validation Script

**Location**: `/opt/sting-ce/scripts/health/validate_mailpit.py`

**Checks Performed**:
- ✅ Container is running and healthy
- ✅ Port mappings are correct (detects 8026 misconfiguration)
- ✅ SMTP port 1025 is accepting connections
- ✅ Web UI port 8025 is accessible
- ✅ End-to-end email delivery works (full test only)

**Usage**:

```bash
# Full validation with email delivery test
python3 /opt/sting-ce/scripts/health/validate_mailpit.py

# Quick validation (skip email test, for automated checks)
python3 /opt/sting-ce/scripts/health/validate_mailpit.py --quick
```

**Output Example**:
```
======================================================================
STING Mailpit Validation
======================================================================

[INFO] Checking: Container Status...
[✓] Container Status: sting-ce-mailpit	Up 2 minutes (healthy)

[INFO] Checking: Port Mapping...
[✓] Port Mapping: Ports correctly mapped: 1025→1025, 8025→8025

[INFO] Checking: SMTP Port (1025)...
[✓] SMTP Port (1025): SMTP port 1025 is accepting connections

[INFO] Checking: Web UI Port (8025)...
[✓] Web UI Port (8025): Web UI accessible (vv1.21.5, 15 messages)

[INFO] Checking: Email Delivery (End-to-End)...
[✓] Email Delivery (End-to-End): Email delivery working (sent 1, received 1)

======================================================================
[✓] All mailpit validation checks passed!

[INFO] Mailpit Web UI: http://localhost:8025
[INFO] Auth emails will be delivered successfully
======================================================================
```

### 2. Enhanced Docker Healthcheck

**Location**: `docker-compose.yml` (mailpit service)

**Old Healthcheck**:
```yaml
healthcheck:
  test: ["CMD", "nc", "-z", "localhost", "1025"]
```

**New Healthcheck**:
```yaml
healthcheck:
  # Enhanced healthcheck: validates container, ports, and SMTP connectivity
  test: ["CMD-SHELL", "nc -z localhost 1025 && nc -z localhost 8025"]
  interval: 10s
  timeout: 5s
  retries: 5
  start_period: 10s
```

Now checks both SMTP (1025) and Web UI (8025) ports.

### 3. Automatic Post-Startup Validation

**Location**: `lib/services.sh`

Validation runs automatically:
- After `./manage_sting.sh start` (full startup)
- After `./manage_sting.sh restart mailpit` (mailpit-specific restart)

**Implementation**:
```bash
# After mailpit starts
log_message "Validating mailpit configuration for auth flow..."
if python3 "${INSTALL_DIR}/scripts/health/validate_mailpit.py" --quick >/dev/null 2>&1; then
    log_message "✅ Mailpit validation passed - auth emails will be delivered" "SUCCESS"
else
    log_message "⚠️  Mailpit validation failed - run full check for details" "WARNING"
fi
```

## Common Issues Detected

### ❌ Incorrect Port Mapping

**Symptom**:
```
[✗] Port Mapping: ❌ INCORRECT PORT MAPPING: Container port 8026 mapped (should be 8025).
    Mailpit listens on 8025, not 8026!
```

**Fix**:
1. Edit docker-compose.yml
2. Change `- "0.0.0.0:8025:8026"` to `- "0.0.0.0:8025:8025"`
3. Restart: `./manage_sting.sh restart mailpit`

### ❌ Container Not Running

**Symptom**:
```
[✗] Container Status: Container sting-ce-mailpit not found
```

**Fix**:
```bash
# Start mailpit
./manage_sting.sh start mailpit

# Or restart all services
./manage_sting.sh restart
```

### ❌ Port Already in Use (WSL2)

**Symptom**:
```
[✗] SMTP Port (1025): SMTP port 1025 is not accepting connections
```

**Fix**:
```bash
# Run mailpit lifecycle cleanup (handles WSL2 port issues)
/opt/sting-ce/lib/mailpit_lifecycle.sh restart

# Or use manage script which automatically runs cleanup
./manage_sting.sh restart mailpit
```

### ❌ Email Delivery Not Working

**Symptom**:
```
[✗] Email Delivery (End-to-End): Email was sent but not received by mailpit
```

**Possible Causes**:
1. Kratos not configured to use mailpit
2. Network connectivity issue between containers
3. Mailpit database corruption

**Fix**:
```bash
# Check Kratos configuration
cat /opt/sting-ce/env/kratos.env | grep SMTP

# Should show:
# COURIER_SMTP_CONNECTION_URI=smtp://mailpit:1025/?skip_ssl_verify=true

# Restart both Kratos and mailpit
./manage_sting.sh restart kratos
./manage_sting.sh restart mailpit
```

## Manual Testing

### Test Email Delivery

```bash
# Send test email via Python
python3 << 'EOF'
import smtplib
from email.message import EmailMessage

msg = EmailMessage()
msg['Subject'] = 'Test Email'
msg['From'] = 'test@sting.local'
msg['To'] = 'admin@sting.local'
msg.set_content('Testing mailpit email delivery')

with smtplib.SMTP('localhost', 1025) as smtp:
    smtp.send_message(msg)
    print('✅ Email sent')
EOF

# Check if received
curl -s http://localhost:8025/api/v1/messages | python3 -c "import sys, json; print(f\"📧 Total messages: {json.load(sys.stdin)['total']}\")"

# View in browser
open http://localhost:8025  # macOS
xdg-open http://localhost:8025  # Linux
```

### Test Auth Flow

Use the archived test script that simulates a full registration flow:

```bash
# Test registration with email verification
python3 /opt/sting-ce/scripts/archive/test_mailpit_email.py
```

This script:
1. Creates a test registration
2. Waits for verification email
3. Confirms email was received in mailpit

## Integration with Setup Wizard

The setup wizard now automatically validates mailpit after installation:

```python
# In web-setup/app.py - run_installation_background()

# After installation completes
if email_mode in ['dev', 'development']:
    log("Validating mailpit configuration...")
    validation_result = subprocess.run(
        ['python3', '/opt/sting-ce/scripts/health/validate_mailpit.py', '--quick'],
        capture_output=True
    )

    if validation_result.returncode == 0:
        log("✅ Mailpit validation passed")
    else:
        log("⚠️ Mailpit validation failed - auth may not work")
```

## Monitoring and Alerts

### Quick Health Check

```bash
# Just check if mailpit is healthy (fast)
./manage_sting.sh status | grep mailpit
```

### Full Validation

```bash
# Run comprehensive validation
python3 /opt/sting-ce/scripts/health/validate_mailpit.py
```

### Continuous Monitoring

Add to cron for periodic checks:

```bash
# Check mailpit health every 15 minutes
*/15 * * * * python3 /opt/sting-ce/scripts/health/validate_mailpit.py --quick >/dev/null 2>&1 || echo "Mailpit validation failed" | mail -s "STING Alert" admin@example.com
```

## Troubleshooting Workflow

When users report "Cannot log in" or "No verification email":

1. **Quick Check**:
   ```bash
   python3 /opt/sting-ce/scripts/health/validate_mailpit.py --quick
   ```

2. **If validation fails**, run full check for details:
   ```bash
   python3 /opt/sting-ce/scripts/health/validate_mailpit.py
   ```

3. **Check recent logs**:
   ```bash
   docker logs sting-ce-mailpit --tail 50
   docker logs sting-ce-kratos --tail 50
   ```

4. **Verify configuration**:
   ```bash
   # Check email mode
   grep EMAIL_MODE /opt/sting-ce/conf/config.yml

   # Check Kratos SMTP settings
   grep SMTP /opt/sting-ce/env/kratos.env
   ```

5. **Restart with cleanup**:
   ```bash
   ./manage_sting.sh restart mailpit
   ```

6. **Test email delivery**:
   ```bash
   python3 /opt/sting-ce/scripts/archive/test_mailpit_email.py
   ```

## Best Practices

1. **After any mailpit change**: Run full validation
   ```bash
   python3 /opt/sting-ce/scripts/health/validate_mailpit.py
   ```

2. **Before deploying to production**: Verify email works
   ```bash
   # Test with actual SMTP provider (not mailpit)
   # Update config.yml email settings
   # Test password recovery flow
   ```

3. **After OS updates or Docker upgrades**: Re-validate
   - Port bindings can change (especially WSL2)
   - Run mailpit lifecycle cleanup
   - Verify validation passes

4. **Monitor healthcheck status**:
   ```bash
   docker inspect sting-ce-mailpit --format='{{.State.Health.Status}}'
   ```

## Files Changed

- `docker-compose.yml`: Fixed port mapping (8025:8025), enhanced healthcheck
- `scripts/health/validate_mailpit.py`: New comprehensive validation script
- `lib/services.sh`: Added automatic post-startup validation
- `scripts/archive/test_mailpit_email.py`: Fixed port references (8026→8025)

## Summary

This validation system provides:
- ✅ **Proactive detection** of mailpit issues
- ✅ **Automatic validation** after startup/restart
- ✅ **Comprehensive checks** including end-to-end email delivery
- ✅ **Clear error messages** with troubleshooting steps
- ✅ **Port mapping validation** (catches 8026 misconfiguration)

**Result**: Auth flow blockers are caught immediately, not when users try to log in.
