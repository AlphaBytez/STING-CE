# STING Troubleshooting Guide

This directory contains scripts and guides to diagnose and fix common issues with STING deployment.

## Authentication Troubleshooting

### Common Login/Registration Issues

#### Browser Error: "Cannot establish connection to Kratos"

**Symptoms:**
- Browser console shows network errors when trying to connect to Kratos
- Login/register forms fail to load
- "Cannot establish connection" or CORS errors in console

**Solutions:**
1. **Check Kratos Service:**
   ```bash
   # Verify Kratos is running
   docker ps | grep kratos
   
   # Check Kratos logs
   docker logs $(docker ps | grep kratos | awk '{print $1}')
   ```

2. **Verify Environment Variables:**
   - Ensure the frontend has the correct Kratos URL:
   ```bash
   # Run the update script
   cd frontend
   ./update-env.sh
   ```

3. **Check CORS Configuration:**
   - Ensure your frontend origin is allowed in Kratos config:
   ```yaml
   # Should be in kratos/main.kratos.yml
   serve:
     public:
       cors:
         allowed_origins:
           - http://localhost:3000
           - https://localhost:3000
   ```

4. **SSL Certificate Issues:**
   - For development, accept the self-signed certificate by visiting:
   ```
   https://localhost:4433/health/ready
   ```
   - Click "Advanced" and "Accept Risk and Continue"

#### Login/Registration Flow Not Working

**Symptoms:**
- Form appears but submission doesn't work
- Redirects don't happen correctly
- Session isn't created
- SSL certificate issues with self-signed certificates

**Solutions:**

1. **Test Direct API Access:**
   ```bash
   # Test login flow initialization
   curl -k https://localhost:4433/self-service/login/api
   
   # Test registration flow
   curl -k https://localhost:4433/self-service/registration/api
   ```

2. **Check Frontend Integration:**
   - Verify that `LoginKratosCustom.jsx` and `SimpleRegistrationPage.jsx` are correctly set up
   - Ensure `window.env.REACT_APP_KRATOS_PUBLIC_URL` is set to 'https://localhost:4433'
   - Check that frontend's `update-env.sh` has proper execute permissions:
   ```bash
   chmod +x frontend/update-env.sh
   ```

3. **Debug Browser Flows:**
   - Open browser developer tools (F12)
   - Watch Network tab during login/registration attempts
   - Look for 4xx or 5xx status codes
   - Check for CORS errors if using browser direct access to Kratos

4. **Check Kratos Configuration:**
   - Verify return URLs are properly configured:
   ```yaml
   # in kratos.yml
   selfservice:
     default_browser_return_url: https://localhost:3000
     allowed_return_urls:
       - https://localhost:3000
       - https://localhost:3000/dashboard
       - https://localhost:3000/login
       - https://localhost:3000/register
     flows:
       login:
         ui_url: https://localhost:3000/login
       registration:
         ui_url: https://localhost:3000/register
   ```

5. **Use Dedicated Testing Scripts:**
   ```bash
   # For API-based testing
   cd kratos && ./test_kratos_registration.sh
   
   # For browser-based testing with interactive prompts
   cd kratos && ./test-browser-registration.sh
   ```

6. **Trust Self-Signed Certificates:**
   - Visit Kratos health endpoint directly in browser to accept certificate:
   ```
   https://localhost:4433/health/ready
   ```
   - Click "Advanced" and "Accept Risk and Continue"
   - Do the same for frontend if needed:
   ```
   https://localhost:3000
   ```

## Environment Setup Issues

### Missing or Incorrect Environment Variables

**Symptoms:**
- "Database is uninitialized" errors
- Connection errors between services
- Authentication failures

**Solutions:**
1. **Fix Environment Files:**
   ```bash
   # Run the environment fix script
   ./troubleshooting/fix_env_issues.sh
   ```

2. **Manually Check Environment Files:**
   ```bash
   # Check if files exist
   ls -la env/
   
   # Create frontend environment file if missing
   echo 'REACT_APP_API_URL=https://localhost:5050
   REACT_APP_KRATOS_PUBLIC_URL=https://localhost:4433
   NODE_ENV=development' > env/frontend.env
   ```

3. **Regenerate All Environment Files:**
   ```bash
   cd conf && python3 config_loader.py -g
   ```

### Container Health Check Failures

**Symptoms:**
- Services fail to start
- Health checks timeout
- "unhealthy" status in `docker ps`

**Solutions:**
1. **Increase Health Check Timeouts:**
   ```bash
   HEALTH_CHECK_START_PERIOD=180s HEALTH_CHECK_TIMEOUT=10s ./manage_sting.sh start
   ```

2. **Check Logs for Specific Issues:**
   ```bash
   docker logs $(docker ps -a | grep kratos | awk '{print $1}')
   ```

3. **Restart Problematic Services:**
   ```bash
   ./manage_sting.sh restart kratos
   ./manage_sting.sh restart frontend
   ```

## Quick Fixes for Common Scenarios

### Full Reset for Authentication Issues

```bash
# Stop all services
./manage_sting.sh stop

# Remove containers and volumes
docker-compose down -v

# Clean Docker environment
docker system prune -f

# Regenerate environment files
cd conf && python3 config_loader.py -g

# Start services with extended health check timeouts
cd .. && HEALTH_CHECK_START_PERIOD=180s ./manage_sting.sh start

# Update frontend environment
cd frontend && ./update-env.sh

# Restart frontend
cd .. && ./manage_sting.sh restart frontend
```

### Fix Frontend Environment Only

```bash
# Update frontend environment variables
cd frontend && ./update-env.sh

# Restart frontend service
cd .. && ./manage_sting.sh restart frontend
```

## Available Troubleshooting Scripts

### `diagnose_docker_issues.sh`
Checks Docker configuration and health to identify problems with containers, networks, or volumes.

### `fix_kratos_configuration.sh`
Fixes common Kratos configuration issues:
- Regenerates 32-character secrets for cookie and cipher
- Ensures environment files exist and have proper permissions
- Creates identity schema if missing
- Fixes database connection strings
- Sets up Docker resources

### `fix_db_password.sh`
Fixes database password configuration issues:
- Updates password in environment files
- Sets hardcoded password in docker-compose.yml
- Creates test database container to verify configuration

### `fix_env_issues.sh`
General environment file fix script:
- Creates missing environment files in /env
- Sets required environment variables with default values
- Fixes file permissions
- Cleans Docker environment

### `fix_env_path_issue.sh`
Addresses inconsistencies in environment file paths:
- Synchronizes between env/ and conf/env/ directories
- Ensures LLM configuration files are in both locations
- Standardizes environment file references

### `fix_install_issues.sh`
Comprehensive fix for installation problems:
- Creates all necessary directories and files
- Sets up Docker network and volumes
- Creates self-signed certificates if needed
- Initializes environment with default values

### `fix_supertokens_env.sh`
Fixes issues related to deprecated SuperTokens environment:
- Removes the deprecated supertokens.env file
- Prevents the file from being created in future 
- Updates configuration to remove SuperTokens references
- Resolves the "msting update frontend" command failure
- Creates a permanent guard file to block regeneration

### `fix-auth-and-dashboard.sh`
Combined fix for both authentication routing and SuperTokens issues:
- Fixes routing conflict between AuthenticationWrapper.jsx and AppRoutes.js
- Updates AuthenticationWrapper to use MainInterface instead of Dashboard directly
- Aligns route paths to use /dashboard/* consistently
- Runs fix_supertokens_env.sh to address environment file issues
- Rebuilds the frontend container to apply all changes

## Common Issues Reference

| Issue | Symptoms | Fix Script |
|-------|----------|------------|
| Kratos validation errors | Errors about cipher/cookie secrets length | `fix_kratos_configuration.sh` |
| Database connection | "Database is uninitialized" errors | `fix_db_password.sh` |
| Environment files | Missing or incorrect env files | `fix_env_issues.sh` |
| Path inconsistencies | Services can't find env files | `fix_env_path_issue.sh` |
| Installation failures | ./manage_sting.sh install fails | `fix_install_issues.sh` |
| Docker networking | Container communication issues | `diagnose_docker_issues.sh` |
| Frontend authentication | Login/registration not working | Update `public/env.js` with correct Kratos URL |
| SuperTokens errors | "msting update frontend" fails with syntax error | `fix_supertokens_env.sh` |
| Dashboard not appearing after login | Original dashboard design missing after login | Fixed by updating AuthenticationWrapper.jsx to use MainInterface |
| SuperTokens component imports | Module not found errors for supertokens-auth-react | Updated all components to use Kratos authentication |

## Knowledge Service & New Components Troubleshooting

### Knowledge Service Issues

#### Knowledge Service Not Starting
**Symptoms:**
- Installation hangs at "Waiting for knowledge..."
- Knowledge service container not running
- Health check fails at http://localhost:8090/health

**Solutions:**
1. **Check if service is running:**
   ```bash
   docker ps | grep knowledge
   docker logs sting-ce-knowledge
   ```

2. **Verify ChromaDB dependency:**
   ```bash
   # ChromaDB must be running first
   docker ps | grep chroma
   curl http://localhost:8000/api/v1/heartbeat
   ```

3. **Restart knowledge service:**
   ```bash
   docker compose restart chroma knowledge
   ```

4. **Check environment configuration:**
   ```bash
   # Verify knowledge.env exists
   ls -la env/knowledge.env
   
   # Check KNOWLEDGE_ENABLED in app service
   docker exec sting-ce-app-1 env | grep KNOWLEDGE
   ```

#### ChromaDB Connection Issues
**Symptoms:**
- Knowledge service logs show "Cannot connect to ChromaDB"
- Vector search not working
- Document embeddings fail

**Solutions:**
1. **Check ChromaDB health:**
   ```bash
   curl http://localhost:8000/api/v1/heartbeat
   docker logs sting-ce-chroma
   ```

2. **Clear ChromaDB data (if corrupted):**
   ```bash
   docker compose down chroma
   docker volume rm sting_chroma_data
   docker compose up -d chroma knowledge
   ```

### Redis & Messaging Service Issues

#### Redis Memory Issues
**Symptoms:**
- "OOM command not allowed when used memory > 'maxmemory'"
- Chatbot responses slow or failing
- Session data not persisting

**Solutions:**
1. **Check Redis memory:**
   ```bash
   docker exec sting-ce-redis redis-cli info memory
   ```

2. **Clear Redis cache:**
   ```bash
   docker exec sting-ce-redis redis-cli FLUSHALL
   ```

3. **Increase memory limit:**
   ```bash
   # Edit docker-compose.yml to increase Redis memory
   # Then restart
   docker compose restart redis
   ```

#### Messaging Service Not Connecting
**Symptoms:**
- Real-time chat not working
- "Cannot connect to messaging service" errors
- Port 8889 not responding

**Solutions:**
1. **Check service health:**
   ```bash
   curl http://localhost:8889/health
   docker logs sting-ce-messaging
   ```

2. **Verify Redis dependency:**
   ```bash
   # Messaging requires Redis
   docker exec sting-ce-redis redis-cli ping
   ```

3. **Restart messaging chain:**
   ```bash
   docker compose restart redis messaging chatbot
   ```

### LLM Gateway Issues

#### LLM Gateway Proxy Not Working (macOS)
**Symptoms:**
- Chatbot shows "LLM service unavailable"
- Port 8085 not responding
- Native LLM service running but not accessible

**Solutions:**
1. **Check native LLM service:**
   ```bash
   ./sting-llm status
   ```

2. **Verify proxy configuration:**
   ```bash
   docker logs sting-ce-llm-gateway-proxy
   curl http://localhost:8085/health
   ```

3. **Test direct connection:**
   ```bash
   # Test native service directly
   curl http://localhost:8086/health
   ```

4. **Restart LLM services:**
   ```bash
   ./sting-llm restart
   docker compose restart llm-gateway-proxy
   ```

### Debug Interface Issues

#### Debug Page Not Loading
**Symptoms:**
- /debug route shows 404
- Debug components missing
- Service status dashboard not appearing

**Solutions:**
1. **Verify debug routes enabled:**
   ```bash
   # Check if debug blueprint is registered
   docker exec sting-ce-app-1 grep -r "debug_bp" /app/
   ```

2. **Check frontend routing:**
   ```bash
   # Ensure debug route exists in AppRoutes.js
   grep -r "debug" frontend/src/components/
   ```

3. **Access debug endpoints directly:**
   ```bash
   # Test backend debug endpoints
   curl https://localhost:5050/api/debug/service-statuses
   ```

## Service Health Monitoring

### Quick Health Check All Services
```bash
#!/bin/bash
# Save as check_all_health.sh

echo "=== STING Service Health Check ==="
echo
echo "Core Services:"
curl -s https://localhost:5050/health -k | jq '.status' || echo "Flask API: OFFLINE"
curl -s https://localhost:4434/admin/health/ready -k | jq '.status' || echo "Kratos: OFFLINE"
docker exec sting-ce-db pg_isready || echo "Database: OFFLINE"
echo
echo "Knowledge System:"
curl -s http://localhost:8090/health | jq '.status' || echo "Knowledge: OFFLINE"
curl -s http://localhost:8000/api/v1/heartbeat | head -c 50 || echo "ChromaDB: OFFLINE"
echo
echo "Support Services:"
docker exec sting-ce-redis redis-cli ping || echo "Redis: OFFLINE"
curl -s http://localhost:8889/health | jq '.status' || echo "Messaging: OFFLINE"
curl -s http://localhost:8888/health | jq '.status' || echo "Chatbot: OFFLINE"
curl -s http://localhost:8085/health | jq '.status' || echo "LLM Gateway: OFFLINE"
```

## Additional Resources

- [Debugging Guide](../docs/DEBUGGING.md)
- [Service Health Monitoring](../docs/SERVICE_HEALTH_MONITORING.md)
- [Kratos Documentation](https://www.ory.sh/docs/kratos)
- [Ory Elements Documentation](https://www.ory.sh/docs/ui)
- [Docker Compose Documentation](https://docs.docker.com/compose/)