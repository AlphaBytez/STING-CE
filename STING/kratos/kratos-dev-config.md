# Kratos Development Configuration Guide

This document explains the Kratos authentication setup for STING development environment.

## Network Configuration

Kratos runs inside Docker and is accessible via:
- Docker network: `kratos:4433` (internal)
- Host machine: `localhost:4433` (exposed port)

## Frontend Integration

The React frontend can access Kratos using:
1. **Via Proxy** (Recommended for development)
   - The frontend includes a proxy in `setupProxy.js` that forwards requests
   - Use empty baseUrl: `const baseUrl = '';`
   - Example: `fetch('/self-service/login/api')`

2. **Direct HTTPS** (Production mode)
   - The frontend can directly connect using HTTPS
   - Set baseUrl: `const baseUrl = 'https://localhost:4433';`
   - Example: `fetch('https://localhost:4433/self-service/login/api')`

3. **Docker Network** (Container-to-container communication)
   - For service-to-service communication within Docker
   - Use the service name: `https://kratos:4433`

## Common Issues

1. **HTTPS Certificate Errors**
   - STING uses self-signed certificates
   - Set `secure: false` in proxy configuration
   - Use `NODE_TLS_REJECT_UNAUTHORIZED=0` for development

2. **CORS Errors**
   - Kratos is configured to allow requests from:
     - http://localhost:3000
     - https://localhost:3000
   - If using different origins, update `kratos.yml`

3. **Connection Refused**
   - Check if Kratos container is running
   - Ensure ports are correctly mapped
   - Verify network connectivity

## Testing Connectivity

Test Kratos health endpoint:
```bash
# From host machine
curl -k https://localhost:4433/health/ready

# From within Docker network
docker exec -it sting-ce-frontend-1 curl -k https://kratos:4433/health/ready
```