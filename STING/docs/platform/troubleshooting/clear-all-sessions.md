# How to Completely Clear All Sessions

The authentication bypass you're experiencing is because Kratos maintains its own session cookies that persist even after apparent "logout".

## To completely clear all sessions:

### 1. Browser Side:
- Open Developer Tools (F12)
- Go to Application/Storage tab
- Clear ALL cookies for localhost:8443, localhost:4433, localhost:5050
- Clear localStorage
- Clear sessionStorage

### 2. Or use this one-liner in browser console:
```javascript
document.cookie.split(";").forEach(c => document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/"));
localStorage.clear();
sessionStorage.clear();
```

### 3. Backend verification:
Check if you're truly logged out by visiting:
- https://localhost:4433/sessions/whoami

If it returns user data, you're still logged in. If it returns 401, you're logged out.

## Why this happens:

1. **Kratos Session Cookies**: 
   - `ory_kratos_session` - The main session cookie
   - `ory_kratos_session` - Local session variant
   
2. **Cookie Domains**: Cookies are set for different domains/ports and clearing one doesn't clear others

3. **The "bypass" behavior**: When you click "Password Login", it goes to Kratos, which sees you have a valid session and immediately redirects to dashboard without asking for password.

## Proper Logout Flow:
1. Click Logout in the app
2. Clear all cookies as shown above
3. Verify with whoami endpoint
4. Now try login again