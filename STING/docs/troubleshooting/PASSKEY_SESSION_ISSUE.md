# Passkey Setup Logout Issue

## Problem
After changing the admin password and attempting to set up a passkey:
1. Passkey setup fails
2. User is logged out

## Root Causes Identified

### 1. Session Invalidation on Password Change
When updating an identity via Kratos Admin API (including password change), Kratos may invalidate all existing sessions for security. This is actually good security practice but causes UX issues.

### 2. Multiple Session Systems
The app uses multiple session systems:
- **Kratos sessions** (`ory_kratos_session` cookie)
- **Flask sessions** (`sting_session` cookie)  
- **WebAuthn sessions** (stored in Flask session)

When Kratos invalidates its session, the app still has Flask session data but can't validate with Kratos, causing authentication failures.

### 3. Cookie Domain/Name Conflicts
- WebAuthn was added separately and might have different session handling
- The app uses `sting_session` for Flask sessions
- Kratos uses `ory_kratos_session`
- Cookie conflicts can cause one to overwrite the other

### 4. Force Password Change Interaction
The `force_password_change` flag clearing happens AFTER the password update, which might cause a race condition:
1. Password updated → Kratos sessions invalidated
2. Try to clear flag → No valid session → Fails
3. User logged out

## Solutions

### Short-term Fix
After changing password, explicitly:
1. Clear all cookies
2. Login again
3. Then set up passkey

### Long-term Fixes

#### Option 1: Preserve Session After Password Change
```python
# In change_password endpoint, after successful password change:
# 1. Get new session from Kratos
# 2. Update cookies
# 3. Continue with same session
```

#### Option 2: Separate WebAuthn Session
Keep WebAuthn sessions completely separate from Kratos sessions to avoid conflicts.

#### Option 3: Session Migration
After password change:
1. Create new Kratos session automatically
2. Migrate Flask session data
3. Update all cookies
4. Continue seamlessly

## Testing
To reproduce:
1. Login as admin with force_password_change
2. Change password
3. Try to add passkey → Should fail and logout

To verify fix:
1. Apply session preservation
2. Change password
3. Add passkey → Should work without logout