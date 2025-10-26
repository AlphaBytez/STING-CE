# Testing Kratos Authentication in STING

This guide walks you through testing the Ory Kratos authentication implementation in STING application.

## Overview of Kratos Authentication Flow

Kratos uses a browser-based authentication flow:

1. **Browser Flow**: Browser redirects to Kratos, which returns a session cookie
2. **API Flow**: API-based interactions for applications that can't use cookies

STING uses a mix of these approaches with the frontend handling the UI portion.

## Testing Login Via the UI

### Prerequisites

Ensure all services are running:
```bash
./manage_sting.sh start
```

> **Important:** If you encounter errors like `Database is uninitialized and superuser password is not specified` or `OCI runtime exec failed`, it likely means environment files are missing or have incorrect permissions. Run the fix script:
> ```bash
> ./fix_env_issues.sh
> ```
> This will create necessary environment files with default values in the `/env` directory. See the [Troubleshooting](#troubleshooting) section below for more details.
```

### Step 1: Access the Login Page

1. Open your browser and navigate to `https://localhost:8443`
2. You should be redirected to the login page if not already authenticated

### Step 2: Understand the Login Flow

The login flow in Kratos works as follows:
1. User accesses the login page
2. Frontend contacts Kratos to initialize a login flow
3. Kratos returns a flow ID
4. User enters credentials
5. Frontend submits credentials to Kratos
6. Kratos validates credentials and returns a session

### Step 3: Register a New Account

Since this is a fresh installation, you'll need to create a user first:

1. Click "Register" or navigate to `https://localhost:8443/register`
2. You'll be redirected to Kratos to handle the registration
3. Fill in the registration form:
   - Email: `test@example.com` (use a unique email each time)
   - Password: `TestPassword123!` (minimum 8 characters)
4. Submit the form
5. If successful, you should be redirected to the dashboard or a verification page
6. Check the Mailpit UI at `http://localhost:8025` to find verification emails

For automated testing, you can use the provided scripts:
```bash
# For API-based testing
cd kratos && ./test_kratos_registration.sh

# For browser-based testing with interactive prompts
cd kratos && ./test-browser-registration.sh
```

### Step 4: Log in with the Created Account

1. Navigate to `https://localhost:8443/login`
2. You'll be redirected to Kratos for authentication
3. Enter the credentials:
   - Email: `test@example.com` (the email you registered with)
   - Password: `TestPassword123!` (the password you created)
4. Click "Sign In"
5. You should be redirected to the dashboard if login is successful

If you encounter SSL certificate warnings, click "Advanced" and "Accept Risk and Continue" to proceed.

### Step 5: Inspect the Network Requests (Optional)

To understand what's happening under the hood:

1. Open your browser's developer tools (F12 or Ctrl+Shift+I)
2. Go to the Network tab
3. Clear the current logs
4. Reload the login page
5. Observe the requests:
   - Request to `/self-service/login/browser` to initialize the flow
   - Request to `/self-service/login` when submitting credentials
   - Redirect to your app with a session cookie

## Common Issues and Solutions

### SSL Certificate Errors

You may see browser warnings about invalid certificates since we're using self-signed certs in development:

- Click "Advanced" and "Proceed to localhost" in Chrome
- Click "Accept the Risk and Continue" in Firefox

### Redirect Issues

If redirects aren't working properly:
- Verify the `KRATOS_PUBLIC_URL` and `LOGIN_UI_URL` in the Kratos configuration
- Check that `defaultReturnTo` is set correctly in the Kratos config

### CORS Errors

If you see CORS errors in the console:
- Ensure Kratos's CORS settings include your frontend URL
- Check the `allowed_origins` setting in `kratos.yml`

### Server Communications

If your frontend can't reach Kratos:
- Verify Docker network connectivity
- Check that ports are properly exposed
- Ensure the Kratos service is healthy

## Debugging Tools

### Kratos Admin API

Access the Kratos admin API to inspect current sessions and flows:
```bash
curl -k https://localhost:4434/admin/identities
```

### Kratos Logs

View the Kratos service logs:
```bash
docker logs $(docker ps | grep kratos | awk '{print $1}')
```

### Test Login Flow Directly

Initialize a login flow directly:
```bash
curl -k https://localhost:4433/self-service/login/browser
```

## Next Steps After Successful Login

Once login is working:

1. **Verify session persistence**: Close and reopen the browser to check if you remain logged in
2. **Test logout**: Implement and test the logout functionality
3. **Add session information**: Display user information in the UI
4. **Implement protected routes**: Ensure certain routes are only accessible when authenticated

## Troubleshooting

### Authentication Issues

For detailed troubleshooting of Kratos authentication issues, refer to the [Troubleshooting Guide](./troubleshooting/README.md) in the troubleshooting directory.

Common issues include:
- SSL certificate problems with self-signed certificates
- CORS errors when accessing Kratos directly from the browser
- Redirect errors if URLs are not properly configured
- Problems with session cookies not being properly set or recognized

You can test authentication directly using the provided scripts:
```bash
# Test Kratos registration through API
cd kratos && ./test_kratos_registration.sh

# Test browser-based registration with interactive prompts
cd kratos && ./test-browser-registration.sh
```

### Environment Variable Issues

If you see errors like `Database is uninitialized and superuser password is not specified` or `OCI runtime exec failed` when starting services, follow these steps:

1. Run the environment fix script:
   ```bash
   ./troubleshooting/fix_env_issues.sh
   ```

2. This script will:
   - Create missing environment files in the `/env` directory
   - Set default values for required variables
   - Fix permissions on environment files
   - Clean up Docker environment

3. Verify the environment files:
   ```bash
   ls -la env/
   ```
   
   You should see files like:
   - `db.env` - Database configuration
   - `kratos.env` - Kratos configuration
   - `frontend.env` - Frontend configuration (important for Kratos URL)
   - Other service-specific .env files

4. Check that the frontend environment is correctly set up:
   ```bash
   cat env/frontend.env
   
   # Should contain something like:
   # REACT_APP_API_URL=https://localhost:5050
   # REACT_APP_KRATOS_PUBLIC_URL=https://localhost:4433
   # NODE_ENV=development
   ```

5. If problems persist:
   ```bash
   # Stop all services
   ./manage_sting.sh stop
   
   # Remove all containers and volumes
   docker-compose down -v
   
   # Clean Docker environment
   docker system prune -f
   
   # Regenerate env files
   cd conf && python3 config_loader.py -g
   
   # Start services again
   cd .. && ./manage_sting.sh start
   
   # Update frontend environment
   cd frontend && ./update-env.sh
   cd .. && ./manage_sting.sh restart frontend
   ```

### Container Health Check Failures

If containers fail to start properly due to health check failures:

1. Check container logs:
   ```bash
   docker logs $(docker ps -a | grep db | awk '{print $1}')
   docker logs $(docker ps -a | grep kratos | awk '{print $1}')
   ```

2. Verify network connectivity:
   ```bash
   docker network inspect sting_local
   ```

3. Try running with extended health check timeouts:
   ```bash
   HEALTH_CHECK_START_PERIOD=180s HEALTH_CHECK_TIMEOUT=10s ./manage_sting.sh start
   ```

### Database Initialization Issues

If the database fails to initialize correctly:

1. Check if the database container is running:
   ```bash
   docker ps | grep db
   ```

2. Verify the database initialization scripts:
   ```bash
   ls -la docker-entrypoint-initdb.d/
   ```

3. Try rebuilding the database container:
   ```bash
   ./manage_sting.sh rebuild db
   ```

## Resources

- [Kratos Documentation](https://www.ory.sh/docs/kratos/concepts/ui-user-interface)
- [Ory Developer Guides](https://www.ory.sh/docs/guides) 
- [Self-Service Flows & User Interface](https://www.ory.sh/docs/kratos/concepts/ui-user-interface)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Environment Variables](https://github.com/docker-library/docs/blob/master/postgres/README.md#environment-variables)