# WSL2 Session Persistence Fix

## Problem
After restarting Docker services with `msting restart`, users get CSRF errors and 401 unauthorized errors because:
1. Kratos sessions are not properly persisting across restarts
2. Browser still has old session cookies that don't match any valid sessions

## Immediate Workaround
1. Clear browser cookies for localhost
   - Press F12 → Application → Storage → Clear site data
   - Or in Chrome: Settings → Privacy → Clear browsing data → Cookies for localhost
2. Login again at https://localhost:8443/login

## Root Cause
The Kratos DSN in kratos.yml has a hardcoded password that doesn't match the actual database password "postgres". This prevents proper session persistence.

## Permanent Fix
Update `/mnt/c/Development/STING-CE/STING/kratos/kratos.yml`:
```yaml
dsn: postgresql://postgres:postgres@db:5432/sting_app?sslmode=disable
```

This ensures Kratos can properly connect to the database and persist sessions across restarts.

## Alternative Solutions
1. Configure Kratos to use Redis for session storage (faster but requires additional setup)
2. Add a startup script that clears all browser sessions on restart
3. Implement a session migration tool that preserves sessions across restarts