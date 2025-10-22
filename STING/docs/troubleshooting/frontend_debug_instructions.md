# 🔍 Frontend Authentication Debug Instructions

## Quick Debug Steps

### 1. **Enable Debug Mode**
Open browser console and run:
```javascript
localStorage.setItem('aal_debug', 'true');
window.location.reload();
```

### 2. **Reset Authentication State** (if stuck)
```javascript
// Emergency reset function
window.resetAALState();
```

### 3. **Check Current Authentication State**
```javascript
// Check Kratos session
fetch('/.ory/sessions/whoami', { credentials: 'include' })
  .then(r => r.json())
  .then(data => console.log('Kratos Session:', {
    email: data.identity?.traits?.email,
    aal: data.authenticator_assurance_level,
    active: data.active,
    methods: data.authentication_methods
  }))
  .catch(e => console.log('No Kratos session:', e));

// Check Flask session  
fetch('/api/auth/me', { credentials: 'include' })
  .then(r => r.json())
  .then(data => console.log('Flask Session:', data))
  .catch(e => console.log('No Flask session:', e));
```

## Expected Behavior After Fixes

1. **Email + Code Login**: Should work and give dashboard access
2. **TOTP after Email**: Should work and give full admin access  
3. **Passkey Login**: Should work for direct authentication

## Common Issues & Solutions

### Issue: "Stuck in authentication loop"
**Solution**: 
```javascript
// Clear all auth state and start fresh
sessionStorage.clear();
localStorage.removeItem('sting-aal2-preference');
window.resetAALState();
```

### Issue: "Database errors in console"
**Status**: ✅ Fixed - database migration completed

### Issue: "Can't access dashboard after successful TOTP"
**Debug**: Enable debug mode and check console for routing decisions

## What to Look For in Console

With debug mode enabled, you should see:
- `🔄 UnifiedProtectedRoute RENDER` messages
- `🔍 AAL2 ENFORCEMENT DEBUG` logs  
- `🛡️ Security Gate` status messages
- `🔐` authentication flow logs

## Next Steps

1. Try logging in with email + TOTP
2. Enable debug mode if issues persist
3. Share console logs if authentication still fails

The database issues have been resolved, so authentication should now work properly.