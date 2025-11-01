# STING Setup for Codespaces, VMs, and Port Forwarding

This guide explains how to set up STING in environments with port forwarding, such as GitHub Codespaces, Gitpod, or custom VMs where the external URL differs from the internal hostname.

## The Problem

When accessing STING through a forwarded URL (e.g., `https://xxx-8443.app.github.dev` in Codespaces), authentication redirects may fail because:

1. The Kratos configuration is set up for a specific hostname (usually `localhost` or an IP)
2. After successful login, Kratos redirects to the configured URL instead of the forwarded URL
3. This results in "redirect to localhost" errors

## The Solution

STING now includes **dynamic URL detection** that automatically uses the current browser URL for authentication redirects. This works seamlessly in all environments without code changes.

### What Was Changed

1. **Frontend Changes:**
   - Created utility functions in `frontend/src/utils/kratosConfig.js`:
     - `buildReturnUrl()` - Builds URLs based on current browser location
     - `buildFlowUrl()` - Builds authentication flow URLs with dynamic return_to

   - Updated authentication components to use dynamic URLs:
     - `SimplifiedKratosLogin.jsx` - Login flow
     - `SimpleAAL2StepUp.jsx` - AAL2 step-up authentication
     - `ProtectedRoute.jsx` - Route protection
     - `EnhancedKratosRegistration.jsx` - Registration flow
     - `RegisterPage.js` - Registration page
     - `EnhancedKratosLogin.jsx` - Enhanced login

2. **Backend Changes:**
   - No code changes required
   - Kratos configuration needs to allow the forwarded URLs

## Setup Instructions

### GitHub Codespaces

1. **Start STING** in your Codespace

2. **Add your Codespace URL to Kratos allowed URLs:**
   ```bash
   cd /opt/sting-ce
   bash scripts/setup/add_allowed_return_url.sh
   ```

   The script will auto-detect your Codespaces URL and prompt you to add it.

3. **Access STING** using your Codespaces forwarded URL:
   ```
   https://[codespace-name]-8443.app.github.dev
   ```

### Gitpod

1. **Start STING** in your Gitpod workspace

2. **Add your Gitpod URL:**
   ```bash
   cd /opt/sting-ce
   bash scripts/setup/add_allowed_return_url.sh
   ```

   The script will auto-detect your Gitpod URL.

3. **Access STING** using your Gitpod URL:
   ```
   https://8443-[workspace-id].gitpod.io
   ```

### Custom VM or Port Forwarding

1. **Identify your external URL** (e.g., `https://vm.example.com:8443`)

2. **Add the URL to Kratos:**
   ```bash
   cd /opt/sting-ce
   bash scripts/setup/add_allowed_return_url.sh
   ```

   When prompted, enter your custom URL.

3. **Access STING** using your external URL

## How It Works

### Dynamic URL Detection (Frontend)

The frontend now dynamically constructs return URLs based on `window.location.origin`:

```javascript
// Old approach - hardcoded
const returnUrl = 'https://localhost:8443/dashboard';

// New approach - dynamic
const returnUrl = buildReturnUrl('/dashboard');
// In Codespaces: https://xxx-8443.app.github.dev/dashboard
// In local dev: http://localhost:8443/dashboard
```

### Authentication Flow

1. User accesses STING via forwarded URL (e.g., `https://xxx-8443.app.github.dev`)
2. Frontend detects current origin from browser
3. When initializing login flow, passes dynamic `return_to` parameter:
   ```
   /.ory/self-service/login/browser?return_to=https://xxx-8443.app.github.dev/dashboard
   ```
4. Kratos validates the `return_to` URL against `allowed_return_urls`
5. After successful authentication, Kratos redirects to the correct URL
6. User stays on the forwarded URL throughout the entire flow

### Kratos Configuration

The `add_allowed_return_url.sh` script adds the following URLs to Kratos:

```yaml
selfservice:
  allowed_return_urls:
    - https://your-url.example.com
    - https://your-url.example.com/
    - https://your-url.example.com/dashboard
    - https://your-url.example.com/login
    - https://your-url.example.com/register
    - https://your-url.example.com/post-registration
    - https://your-url.example.com/dashboard/settings
    - https://your-url.example.com/dashboard/reports
    - https://your-url.example.com/*
```

## Manual Configuration (Alternative)

If you prefer to manually configure Kratos:

1. **Edit Kratos configuration:**
   ```bash
   nano /opt/sting-ce/kratos/kratos.yml
   ```

2. **Add your URLs to `allowed_return_urls`:**
   ```yaml
   selfservice:
     allowed_return_urls:
       # ... existing URLs ...
       - https://your-forwarded-url.com
       - https://your-forwarded-url.com/*
   ```

3. **Add to CORS origins:**
   ```yaml
   serve:
     public:
       cors:
         allowed_origins:
           # ... existing origins ...
           - https://your-forwarded-url.com
   ```

4. **Restart Kratos:**
   ```bash
   docker compose restart kratos
   ```

## Troubleshooting

### Still redirecting to localhost

1. **Check Kratos configuration:**
   ```bash
   docker compose exec kratos cat /etc/config/kratos/kratos.yml | grep -A 20 allowed_return_urls
   ```

2. **Verify your URL is in the list**

3. **Check browser console for errors:**
   - Open DevTools (F12)
   - Look for the log message: `🔗 Dynamic return URL: ...`
   - Verify it matches your forwarded URL

### Authentication flow errors

1. **Check Kratos logs:**
   ```bash
   docker compose logs kratos | grep -i error
   ```

2. **Look for CORS errors** in browser console

3. **Verify the return_to URL is in allowed list**

### WebAuthn/Passkey issues in forwarded environments

WebAuthn requires HTTPS and a valid domain. Some forwarding services may not support WebAuthn:

1. **Use email code authentication** as a fallback
2. **Check if your forwarding service supports WebAuthn**
3. **Ensure the RP ID matches your domain** in Kratos configuration

## Security Considerations

### Production Deployments

For production, be specific about allowed URLs:

```yaml
allowed_return_urls:
  - https://sting.yourdomain.com
  - https://sting.yourdomain.com/dashboard
  # Don't use wildcards like /* in production
```

### Development/Testing

For development environments, wildcards are acceptable:

```yaml
allowed_return_urls:
  - https://*.app.github.dev  # Codespaces
  - https://*.gitpod.io       # Gitpod
  - http://localhost:8443/*   # Local dev
```

## Additional Resources

- [Ory Kratos Documentation](https://www.ory.sh/docs/kratos/)
- [Ory Kratos Self-Service Flows](https://www.ory.sh/docs/kratos/self-service)
- [STING Authentication Guide](../platform/security/authentication-guide.md)

## Summary

The dynamic URL detection system ensures STING works seamlessly across all deployment scenarios:

- ✅ Local development (localhost)
- ✅ GitHub Codespaces
- ✅ Gitpod
- ✅ Custom VMs with port forwarding
- ✅ Cloud deployments
- ✅ Kubernetes with ingress

No code changes are required when moving between environments - the frontend automatically adapts to the current URL.
