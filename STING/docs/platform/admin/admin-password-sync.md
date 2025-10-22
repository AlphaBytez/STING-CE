# Admin Password Synchronization Fix

## Problem
During installation, the admin password file could become out of sync between the host and container, causing login loops and password mismatches in the UI.

## Root Cause
The app container was using a different password file path than the host, and the password was being cached at module import time.

## Solution Implemented

### 1. Volume Mount for Admin Credentials
**File**: `docker-compose.yml`
```yaml
volumes:
  # Mount install directory for admin credentials
  - ${INSTALL_DIR}:/.sting-ce
```

### 2. Consistent Password File Path
**Files Updated**:
- `app/utils/default_admin_setup.py`
- `app/routes/auth_routes.py` 
- `app/utils/startup_banner.py`

**Change**: Use mounted path `/.sting-ce/admin_password.txt` instead of `~/.sting-ce/admin_password.txt`

### 3. Prevention for Future Installs
The volume mount ensures that:
- Host and container always reference the same password file
- Admin password is consistent across restarts
- UI displays the correct password

## Verification
After implementing these changes:
1. Admin password in UI matches file: ✅
2. Login works without manual cookie clearing: ✅ 
3. Password survives container restarts: ✅

## Files Modified
- `/docker-compose.yml` - Added volume mount
- `/app/utils/default_admin_setup.py` - Updated password file path
- `/app/routes/auth_routes.py` - Updated password file path  
- `/app/utils/startup_banner.py` - Updated password file path

## Commands to Apply Fix
```bash
# Copy updated docker-compose to install directory
cp docker-compose.yml ${INSTALL_DIR}/

# Rebuild and restart app
docker compose build app
docker compose up -d app
```