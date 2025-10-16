# Kratos Registration Troubleshooting

This document provides troubleshooting steps for common issues with the Kratos registration flow in the STING application.

## Common Issues and Solutions

### 1. Registration page doesn't load or shows blank form

**Possible causes:**
- Kratos service is not running
- Frontend can't connect to Kratos
- Configuration issues in main.kratos.yml
- CORS settings preventing frontend access

**Solutions:**
- Verify Kratos is running: `docker ps | grep kratos`
- Check Kratos logs: `docker logs $(docker ps | grep kratos | awk '{print $1}')`
- Verify health endpoint: `curl -k https://localhost:4433/health/ready`
- Run the fix script: `./kratos/fix-registration.sh`

### 2. Registration form submits but returns errors

**Possible causes:**
- Schema validation failures
- CSRF token issues
- Malformed request payload
- Database connection issues

**Solutions:**
- Check browser console for detailed error messages
- Verify the request payload structure in browser developer tools
- Check Kratos logs for validation errors
- Make sure the identity schema matches the payload structure

### 3. WebAuthn (Passkey) registration not working

**Possible causes:**
- Browser doesn't support WebAuthn
- Missing or invalid WebAuthn configuration in main.kratos.yml
- HTTPS issues (WebAuthn requires HTTPS)
- Frontend code errors in handling WebAuthn registration

**Solutions:**
- Test in Chrome or Firefox (latest versions)
- Verify HTTPS is properly configured
- Check the WebAuthn configuration in main.kratos.yml
- Look for WebAuthn-specific errors in browser console

## Testing Registration Flow

Use the provided test scripts to verify the registration flow:

1. Test API-based registration:
```
./kratos/test_kratos_registration.sh
```

2. Test browser-based registration flow:
```
./kratos/test-browser-registration.sh
```

These scripts will show detailed output about the registration process, which can help identify issues.

## Configuration Reference

### Key Configuration Files

1. **Kratos configuration**: `/kratos/main.kratos.yml`
   - Contains all Kratos settings including registration flow configuration

2. **Identity schema**: `/kratos/identity.schema.json`
   - Defines the structure and validation for user identity data

3. **Frontend registration page**: `/frontend/src/auth/RegisterPage.js`
   - Handles the UI and API calls for registration

### Required Environment Variables

Make sure these environment variables are set in your `.env` file or equivalent:

- `KRATOS_PUBLIC_URL`: URL for the Kratos public API (default: https://localhost:4433)
- `POSTGRES_PASSWORD`: Database password for Kratos
- `DOMAIN_NAME`: Your domain name (default: localhost)

## Manual Fix Steps

If the automated fix script doesn't resolve your issues, you can manually apply the fixes:

1. Update the Kratos configuration:
   - Ensure proper indentation in YAML file
   - Check the selfservice.flows.registration section
   - Verify method configurations for password and webauthn

2. Update the frontend code:
   - Check the fetch request configurations
   - Verify CSRF token handling
   - Ensure proper error handling

3. Restart the services:
```
./manage_sting.sh restart kratos
./manage_sting.sh restart frontend
```

## Getting Help

If you're still experiencing issues after trying these troubleshooting steps, please:

1. Check the full logs for Kratos and the frontend
2. Review the Kratos documentation at https://www.ory.sh/docs/kratos
3. Open an issue in the project repository with detailed information about your issue