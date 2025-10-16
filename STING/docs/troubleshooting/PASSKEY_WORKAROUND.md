# Passkey Setup Workaround

## The Issue
When changing password and then trying to set up a passkey, the session gets invalidated causing logout. This is due to Kratos' security behavior when updating identity credentials.

## Root Cause
Kratos invalidates ALL sessions for a user when their password is changed via the Admin API. This is a security feature to prevent session hijacking but causes UX issues.

## Workaround Steps

### Option 1: Two-Login Method (Recommended)
1. Login with default admin password
2. Change password when prompted
3. **Expected: You will be logged out** (this is normal)
4. Clear cookies and login again with new password
5. Now set up passkey - it should work

### Option 2: Skip Password Change
1. If admin already has `force_password_change: false`, skip changing password
2. Go directly to passkey setup
3. Change password later if needed

### Option 3: Use Different User
1. Create a new admin user that doesn't require password change
2. Setup passkey for that user
3. Use that account going forward

## Technical Solutions (For Developers)

### Short-term Fix
Modify the password change endpoint to NOT use Admin API:
- Use Kratos self-service flows instead
- This preserves the session

### Long-term Fix
1. Implement session refresh after password change
2. Or use Kratos hooks to preserve specific sessions
3. Or separate password and identity updates

## Commands to Reset
If you're stuck in a bad state:

```bash
# Clear all sessions
docker exec sting-ce-kratos kratos session list --format json | jq -r '.[] | .id' | xargs -I {} docker exec sting-ce-kratos kratos session delete {}

# Remove force_password_change
python3 scripts/remove_force_password_change.py

# Test login
python3 scripts/test_browser_login.py
```

## Prevention
- Don't logout after changing password without setting up passkey first
- Or setup passkey BEFORE changing password
- Use the grace period system to delay password change