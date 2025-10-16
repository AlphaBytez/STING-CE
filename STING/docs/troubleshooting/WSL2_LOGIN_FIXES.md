# WSL2 Login Fixes Documentation

This document details all the fixes applied to resolve login/session persistence issues on WSL2.

## Issues Resolved

1. **Frontend HTTPS configuration mismatch**
2. **Session cookies not being passed between services**
3. **Container networking hostname resolution**
4. **Certificate volume mounting on WSL2**
5. **Frontend port reverting to 3000**
6. **Force password change middleware blocking login**
7. **CSRF token mismatch errors**
8. **Admin user created without password**

## Changes Made

### 1. Frontend Nginx Configuration (`frontend/nginx.https.conf`)

**Changed**: Listen port from 443 to 80 (Docker maps 8443->80)
```nginx
- listen 443 ssl;
+ listen 80 ssl;
```

**Added**: Cookie handling for API proxy
```nginx
# Pass cookies to backend
proxy_set_header Cookie $http_cookie;
proxy_pass_request_headers on;
```

**Added**: Cookie handling for Kratos proxy
```nginx
# Pass cookies to Kratos - critical for session handling
proxy_set_header Cookie $http_cookie;
proxy_pass_request_headers on;

# Pass Set-Cookie headers from Kratos back to client
proxy_pass_header Set-Cookie;
```

**Fixed**: Kratos hostname
```nginx
- proxy_pass https://sting-ce-kratos:4433;
+ proxy_pass https://kratos:4433;
```

### 2. Kratos Configuration (`kratos/kratos.yml`)

**Changed**: All HTTP URLs to HTTPS
```yaml
- base_url: http://localhost:8443
+ base_url: https://localhost:8443

- default_browser_return_url: http://localhost:8443/dashboard
+ default_browser_return_url: https://localhost:8443/dashboard

# And all other UI URLs...
```

**Changed**: Session cookie SameSite policy
```yaml
session:
  cookie:
    name: ory_kratos_session
    domain: localhost
    path: /
-   same_site: None
+   same_site: Lax
```

### 3. Frontend Dockerfile (`frontend/Dockerfile.react-nginx`)

**Changed**: Use HTTPS nginx config
```dockerfile
- COPY nginx.prod.conf /etc/nginx/conf.d/default.conf
+ COPY nginx.https.conf /etc/nginx/conf.d/default.conf
```

### 4. Docker Compose Configuration

The `docker-compose.yml` already includes the network alias fix:
```yaml
kratos:
  networks:
    sting_local:
      aliases:
        - kratos
```

### 5. WSL2 Certificate Fix Script (`scripts/wsl2_fix_certs.sh`)

Created a script to handle certificate volume issues specific to WSL2:
- Checks if running on WSL2
- Copies certificates from Windows mount to Docker volume
- Verifies certificates are properly mounted

### 6. App Environment Configuration (`env/app.env`)

**Added**: KRATOS_PUBLIC_URL environment variable
```bash
KRATOS_PUBLIC_URL=https://kratos:4433
```

This fixes the session proxy endpoint `/api/session/whoami` which was trying to connect to `localhost:4433` instead of the Kratos container.

### 7. Force Password Change Middleware (`app/middleware/force_password_change.py`)

**Added**: Allowed endpoints for admin with force_password_change flag
```python
# Allow essential endpoints for app initialization
'auth.login',
'auth.me',
'auth.admin_notice',
'users.me',
'session.whoami',
'session.session_proxy',
# Allow static resources
'static'
```

### 8. Frontend Port Configuration

**Issue**: Frontend port reverts to 3000 during fresh install
**Root Cause**: The `config.yml.default` and `config.yml.default.mac` templates had port 3000 hardcoded
**Fix**: Updated all configuration templates to use port 8443 by default

The following files were updated:
- `conf/config.yml.default` - Changed all references from port 3000 to 8443
- `conf/config.yml.default.mac` - Changed all references from port 3000 to 8443
- `conf/config.yml.minimal` - Changed REACT_PORT from 3000 to 8443

If you still encounter port 3000 after installation, run:
```bash
./scripts/fix_frontend_port.sh
```

Or manually:
1. Add REACT_PORT=8443 to /opt/sting-ce/.env
2. Update /opt/sting-ce/env/frontend.env to set REACT_PORT="8443"
3. Recreate frontend container: `docker-compose rm -f frontend && docker-compose up -d frontend`

### 9. Cookie SameSite Configuration

**Issue**: CSRF token mismatch - "The request was rejected to protect you from Cross-Site-Request-Forgery"
**Root Cause**: Mismatch between Kratos (SameSite=None) and App (SameSite=None) cookie settings
**Fix**: Updated both to use SameSite=Lax for consistency

Files updated:
- `app/__init__.py` - Changed SESSION_COOKIE_SAMESITE from 'None' to 'Lax'
- `app/config.py` - Changed DevelopmentConfig COOKIE_SETTINGS samesite from 'None' to 'Lax'
- `kratos/kratos.yml` - Changed session.cookie.same_site from 'None' to 'Lax'

### 10. Admin User Password Issue

**Issue**: Admin user created without password during fresh install
**Root Cause**: The admin user was created by some process without credentials
**Fix**: Delete and recreate admin user with password

```bash
# Delete existing admin (replace ID with actual ID)
curl -k -X DELETE https://localhost:4434/admin/identities/<admin-id>

# Create admin with password
PYTHONPATH=/opt/sting-ce python3 /opt/sting-ce/scripts/troubleshooting/dangerzone/create_admin.py \
  --email admin@sting.local --password AdminPassword123!
```

## Fresh Install Instructions

If doing a fresh install, ensure:

1. **Commit these changes**:
   ```bash
   git add frontend/nginx.https.conf kratos/kratos.yml frontend/Dockerfile.react-nginx \
          scripts/wsl2_fix_certs.sh app/middleware/force_password_change.py \
          conf/config.yml.default conf/config.yml.default.mac conf/config.yml.minimal \
          app/__init__.py app/config.py
   git commit -m "fix: WSL2 login and session persistence issues"
   ```

2. **After installation on WSL2**:
   ```bash
   # Run the certificate fix script
   ./scripts/wsl2_fix_certs.sh
   ```

3. **Verify certificates are in volume**:
   ```bash
   docker run --rm -v sting_sting_certs:/certs alpine ls -la /certs/
   ```

4. **Restart services**:
   ```bash
   msting restart
   ```

## Testing

After applying these fixes, test login:
1. Clear all browser cookies for localhost
2. Navigate to https://localhost:8443/login (Note: Port should be 8443, not 3000)
3. Login with admin@sting.local / AdminPassword123!
4. Verify you stay logged in when navigating to dashboard

## Root Causes Summary

The login redirect loop was caused by:
1. Nginx proxy not passing cookies between services
2. HTTP/HTTPS mismatch in Kratos configuration
3. WSL2-specific issue where certificates weren't properly mounted to Docker volumes
4. Force password change middleware blocking all API requests (403 errors)
5. Missing KRATOS_PUBLIC_URL environment variable in app container
6. Frontend port configuration reverting to 3000
7. Cookie SameSite policy mismatch between services
8. Admin user created without password credentials