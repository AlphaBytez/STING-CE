# Mac Email Verification Fix

## Issue
Email verification through Mailpit doesn't work on Mac due to Docker Desktop networking differences. While it works on WSL2/Linux, Mac's Docker Desktop runs in a VM which adds an extra network translation layer.

## Symptoms
- Verification emails are not sent when requested from Settings
- No emails appear in Mailpit (http://localhost:8026)
- Courier messages table remains empty
- Works fine on WSL2/Linux but not on Mac

## Root Cause
The Kratos courier configuration uses `smtp://mailpit:1025` which should work, but there appears to be an issue with the courier worker not processing messages on Mac's Docker environment.

## Workaround

### For Admin User
If you need to verify the admin email to access features like passkey setup:

```bash
# Run the manual verification script
python3 scripts/manual_verify_admin.py
```

This will directly update the database to mark the admin email as verified.

### After Running the Script
1. Log out and log back in
2. You should now be able to set up passkeys in Settings
3. All admin features should be accessible

## Permanent Fix (In Progress)
We're investigating:
1. Why the courier worker isn't processing messages on Mac
2. Potential differences in Docker networking between Mac and Linux
3. Alternative SMTP configurations that work reliably across platforms

## Testing Email Functionality
To test if Mailpit is receiving emails:

```bash
# Check Mailpit UI
open http://localhost:8026

# Check if Mailpit is running
docker ps | grep mailpit

# Test SMTP connection from Kratos
docker exec sting-ce-kratos nc -zv mailpit 1025

# Check courier messages in database
docker exec sting-ce-db psql -U postgres -d sting_app -c "SELECT COUNT(*) FROM courier_messages;"
```

## Note
This is a Mac-specific issue. Email verification works correctly on WSL2/Linux environments.