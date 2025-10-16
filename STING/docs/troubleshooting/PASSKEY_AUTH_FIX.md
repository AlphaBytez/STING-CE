# Passkey Authentication Fix

## Issue
Passkey authentication is failing with "Failed to complete authentication" error. The root cause is that the Flask session isn't persisting between the `begin` and `complete` authentication requests.

## Root Causes
1. **Session Cookie Domain Mismatch**: The session cookie domain wasn't explicitly set to match the WebAuthn RP ID
2. **Redis Session Persistence**: The session data stored in Redis during `begin` authentication isn't available during `complete` authentication
3. **Session Cookie Configuration**: The cookie might not be sent with cross-origin requests

## Fix Applied
1. Added explicit `SESSION_COOKIE_DOMAIN` configuration in `app/__init__.py` to match WebAuthn RP ID
2. Added debugging to track session persistence issues
3. Enhanced logging in WebAuthn routes to diagnose session problems

## Testing Steps
1. Clear all browser cookies for localhost:8443
2. Login with your credentials
3. Go to Settings > Security
4. Try to login with passkey

## Debugging Commands
```bash
# Check app logs for session issues
docker logs sting_app --tail 100 2>&1 | grep -i "session\|webauthn"

# Test Redis connectivity
docker exec -it sting_redis redis-cli ping

# Check Redis keys
docker exec -it sting_redis redis-cli keys "sting:*"

# Monitor Redis operations in real-time
docker exec -it sting_redis redis-cli monitor
```

## If Issue Persists
1. Check if Redis container is running: `docker ps | grep redis`
2. Verify Redis connectivity from app container
3. Check browser developer tools:
   - Network tab: Verify cookies are sent with requests
   - Application tab: Check cookie values and domains
4. Try using the debug script: `python3 scripts/debug_passkey_auth.py`

## Alternative Workaround
If Redis sessions continue to fail, we could:
1. Switch to database-backed sessions
2. Use challenge storage in the database instead of sessions
3. Implement stateless authentication with signed tokens