# STING Registration Guide

This guide helps you complete the registration process with Kratos authentication in the STING platform.

## Quick Start

1. Visit http://localhost:8443/register
2. Click the "Go to Registration Form" button (email or passkey option)
3. Complete the registration form
4. Verify your email using the test mail server at http://localhost:8025

> **Important Note:** The registration page uses the React development server's proxy to connect to Kratos. This avoids SSL certificate issues that would occur when connecting directly to Kratos.

## Troubleshooting SSL Certificate Issues

If you encounter SSL certificate errors with messages like `ERR_SSL_PROTOCOL_ERROR` or `This site can't provide a secure connection`, try the following steps:

### Option 1: Use the Test Registration HTML

1. Open `/Volumes/EXT-SSD/DevWorld/STING/test-register.html` directly in your browser
2. Click "Registration via Proxy" button which uses the proxy mode

### Option 2: Accept Certificates Directly

1. Open https://localhost:4433/health/ready in your browser
2. When prompted about the certificate, choose to proceed/accept (varies by browser)
3. Once accepted, go back to http://localhost:8443/register and try again

### Option 3: Use the API Test Script

1. Run the test script: `./test-kratos-api.sh` 
2. The script will output registration flow IDs that you can use directly
3. Visit: http://localhost:8443/register?flow=FLOW_ID (replace FLOW_ID with the ID from the script)

## Viewing Test Emails

All verification emails are sent to the Mailpit test mail server:

1. Visit http://localhost:8025 in your browser
2. Any registration verification emails will appear here
3. Click on the email to view it and follow the verification link

> **Note:** The mail server is running on port 8025, not the standard port 8025 as some documentation might suggest.

## Common Problems and Solutions

### Frontend Proxy Issues

If the React app's proxy to Kratos isn't working, you can restart the frontend service:

```bash
./manage_sting.sh restart frontend
```

### Database Connection Issues

If you see database connection errors in the Kratos logs, restart the database and Kratos:

```bash
./manage_sting.sh restart db kratos
```

### Certificate Not Accepted

If your browser still rejects the certificate after accepting it:

1. Clear your browser cache and cookies
2. Try in an incognito/private browsing window
3. Try a different browser

## Need More Help?

Run the test script to verify Kratos is working properly:

```bash
./test-kratos-api.sh
```

If you continue having issues, check the logs:

```bash
docker-compose logs kratos
docker-compose logs frontend
```