# Kratos Integration Guide

This guide explains how the frontend integrates with Ory Kratos for authentication.

## Authentication Flow Overview

The frontend now uses Ory Kratos for all authentication flows:

1. **Login** - Users log in through Kratos and are redirected back to the app with a session
2. **Registration** - New users sign up through Kratos and verify their email
3. **Recovery** - Users can reset their password through Kratos
4. **Verification** - Email verification is handled by Kratos
5. **Settings** - Profile updates and security settings use Kratos flows

## Key Components

### KratosProvider

The `KratosProvider` component (`/frontend/src/auth/KratosProvider.jsx`) is the central authentication state provider. It:

- Manages auth state (isAuthenticated, user identity)
- Provides authentication methods (login, register, recover, logout)
- Handles session checking and verification
- Manages custom user attributes like account type

### Authentication Flow Components

Each authentication flow has two dedicated components:

1. A **Redirect** component that handles redirecting to Kratos and receiving flow IDs:
   - `LoginRedirect`
   - `RegistrationRedirect`
   - `RecoveryRedirect`
   - `VerificationRedirect`

2. A **Form** component that renders the actual form from Kratos flow data:
   - `KratosLogin`
   - `KratosRegister`
   - `KratosRecovery`

### Protected Routes

The `ProtectedRoute` component ensures users are authenticated before accessing protected content. It can also check for specific account types or permissions.

## How Kratos Flows Work

1. User clicks to login/register/etc.
2. Frontend redirects to Kratos flow (e.g., `/self-service/login/browser`)
3. Kratos performs the flow and redirects back with a flow ID
4. Frontend components fetch the flow data and render the appropriate UI
5. User submits the form directly to Kratos
6. Kratos validates, performs the action, and redirects back to the frontend

## Proxy Configuration (Important!)

The React development server uses a proxy to route authentication requests to Kratos. This is a critical component for the proper functioning of authentication.

### Updated Proxy Configuration

We've updated the proxy configuration in `setupProxy.js` to properly handle authentication flows:

```javascript
// Apply to all Kratos API endpoints
app.use(
  [
    '/self-service',
    '/sessions',
    '/identities',
    '/health',
    '/kratos',
    '/.well-known',
    '/ui'
    // Note: We removed '/login' and '/registration' paths from the proxy
  ],
  kratosProxy
);

// Special handling for login and registration API calls
app.use((req, res, next) => {
  const url = req.url;
  
  // If request is to Kratos API endpoints, proxy it
  if (url.startsWith('/self-service/login') || 
      url.startsWith('/self-service/registration') ||
      url.startsWith('/self-service/recovery') ||
      url.startsWith('/self-service/verification')) {
    return kratosProxy(req, res, next);
  }
  
  // Otherwise, let React Router handle it
  next();
});
```

### Key Changes

1. **Removed Direct Path Proxying**: URLs like `/login` and `/registration` are now handled by React Router, not proxied to Kratos.
2. **Selective API Proxying**: Only specific API endpoints are proxied to Kratos to avoid conflicts with frontend routes.
3. **Improved Handling of Flow IDs**: URLs with flow IDs (e.g., `/login?flow=123`) are now properly handled by the React components.

### Why This Matters

The previous configuration was causing 404 errors because:

- URLs like `/login?flow=<id>` were being proxied directly to Kratos
- Kratos doesn't have a `/login` endpoint (it has `/self-service/login/flows`)
- The React components weren't getting a chance to handle these URLs

The new configuration ensures that React Router handles the flow URLs appropriately, allowing our frontend components to fetch and display the correct form data.

## Debug Tools

The `/debug` route provides tools to test authentication flows and diagnose issues. It allows you to:

- Test Kratos connection
- Create login/registration flows
- Get detailed error messages
- Test direct navigation to authentication routes

The debug page has been enhanced to:

1. Create login flows and test the entire flow process
2. Display flow IDs and provide a button to test them
3. Show detailed error messages for troubleshooting
4. Provide more comprehensive environment information

## Security Considerations

- All forms submit directly to Kratos, not through the frontend
- CSRF tokens are included in all forms
- Sessions are managed by Kratos via HTTP-only cookies
- Self-signed certificates are used in development

## Common Issues and Solutions

### 404 Errors for Login Flow URLs

**Problem**: URLs like `/login?flow=<id>` result in 404 errors.

**Solution**: 
- Ensure setupProxy.js is correctly configured to NOT proxy `/login` URLs
- Verify that React Router is handling these URLs through LoginRedirect component
- Check browser console for proxy errors or CORS issues

### Session Not Persisting

**Problem**: User is redirected to login page after successful authentication.

**Solution**:
- Ensure Kratos is configured to set cookies correctly (domain, path, secure flags)
- Verify that `credentials: 'include'` is set on all fetch requests to Kratos
- Check for cookie domain mismatch between Kratos and frontend

### CORS and HTTPS Issues

**Problem**: Browser blocks requests due to CORS or mixed content errors.

**Solution**:
- Kratos should use the same protocol (HTTP/HTTPS) as the frontend
- Add appropriate CORS headers in setupProxy.js for all responses
- When using self-signed certificates in development, set `secure: false` in proxy settings

### Flow Expiration Issues

**Problem**: "Flow expired" errors when trying to use authentication flows.

**Solution**:
- Ensure you're using the flow within the expiration time (default is 15 minutes)
- Check the server time synchronization across containers
- Increase the flow lifetime in Kratos configuration if necessary

## Customizing the Authentication UI

To customize the look and feel of authentication forms:

1. Update the corresponding form components (`KratosLogin`, `KratosRegister`, etc.)
2. Add custom CSS classes to form elements
3. Ensure you maintain all hidden fields (especially CSRF tokens)
4. If substantial customization is needed, consider building fully custom forms that submit to the same Kratos endpoints

## Further Reading

- [Ory Kratos Documentation](https://www.ory.sh/kratos/docs/)
- [Kratos Self-Service Flows](https://www.ory.sh/kratos/docs/self-service)
- [Kratos API Reference](https://www.ory.sh/kratos/docs/reference/api)
- [React Router Documentation](https://reactrouter.com/en/main)