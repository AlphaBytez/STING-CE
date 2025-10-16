# Post-Reinstall Checklist

## Stashed Changes to Apply

### 1. Route Fix (stash@{0})
Simple fix changing `/aal2` to `/aal2-step-up`
```bash
git stash apply stash@{0}
```

### 2. Auth Fixes (stash@{4})
Contains important AAL2 and PasskeyManagerDirect updates
**WARNING**: Also deletes entire backend folder - be selective!
```bash
# Apply auth fixes but exclude backend deletion
git stash show -p stash@{4} -- ':(exclude)STING/backend' | git apply

# Or apply specific files:
git checkout stash@{4} -- STING/frontend/src/components/settings/PasskeyManagerDirect.jsx
git checkout stash@{4} -- STING/frontend/src/contexts/AAL2Provider.jsx
git checkout stash@{4} -- STING/app/decorators/aal2.py
git checkout stash@{4} -- STING/app/middleware/auth_middleware.py
```

## After Applying Stashes

1. **Update services**:
```bash
./manage_sting.sh update app
./manage_sting.sh update frontend
```

2. **Clear browser state** before testing:
```javascript
// Run in browser console
sessionStorage.clear();
localStorage.setItem('aal_debug', 'true');
window.resetAALState && window.resetAALState();
```

3. **Create fresh admin** (if needed):
```bash
./manage_sting.sh create admin admin@sting.local
```

## Testing AAL2

1. Login as admin with email + code
2. Should be redirected to `/aal2-step-up` (not `/aal2`)
3. Click "Use Passkey" button
4. Touch ID prompt should appear without freezing
5. Complete biometric verification
6. Should reach dashboard

## If Issues Persist

### Option A: Pull working components from Aug 29
```bash
git checkout 28403cb65 -- STING/app/routes/biometric_routes.py
git checkout 28403cb65 -- STING/app/services/authorization_service.py
```

### Option B: Fix AAL2PasskeyVerify.jsx
Replace auto-grant logic with actual Kratos WebAuthn trigger

### Option C: Simplify to direct AAL2StepUp
Remove GracefulAAL2StepUp and AAL2PasskeyVerify, use AAL2StepUp directly

## Notes
- The auth-fixes stash (stash@{4}) was created before navigation fixes
- It likely contains working AAL2 code but also removes backend folder
- Be selective when applying to avoid losing other fixes

---
*Created during reinstall - November 2024*