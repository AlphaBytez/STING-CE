# STING Service Startup Resilience

## Overview

STING includes enhanced service startup resilience to handle common issues during installation and updates, such as:
- Services failing to start due to dependency timing
- Containers stuck in "created" state
- Port conflicts preventing service startup
- Network timeouts during image pulls
- Services exiting unexpectedly

## How It Works

### Automatic Resilience

When you run `./manage_sting.sh install`, `update`, or `start`, STING automatically:

1. **Checks service dependencies** - Services start in the correct order based on their dependencies
2. **Retries failed services** - Up to 3 attempts with intelligent backoff
3. **Performs health checks** - Verifies services are actually responding, not just running
4. **Detects port conflicts** - Identifies when required ports are already in use
5. **Handles container states** - Manages containers stuck in "created" or "exited" states

### Service Dependencies

Services are started in this order to respect dependencies:
1. Infrastructure: `postgres`, `redis`
2. Authentication: `kratos`, `kratos-migrate`
3. Core services: `mailpit`, `app`
4. Frontend: `frontend`
5. AI services: `chatbot`, `knowledge`
6. Gateway: `nginx`

## Manual Recovery Tool

If services fail to start automatically, use the interactive recovery tool:

```bash
./scripts/recover_services.sh
```

This provides an interactive menu with options to:
- View detailed service status
- Check system resources and port conflicts
- Attempt automatic recovery
- View service logs
- Recreate specific services
- Perform full system restart

## Common Issues and Solutions

### Services Stuck in "Created" State

**Symptom**: Services show as created but not running after update/install.

**Solution**: The enhanced startup automatically detects and starts these services. If it fails:
```bash
# Manual recovery
./scripts/recover_services.sh
# Select option 3 for automatic recovery
```

### Port Conflicts

**Symptom**: Services fail to start with "port already allocated" errors.

**Solution**: 
1. Check what's using the port:
   ```bash
   ./scripts/recover_services.sh
   # Select option 2 to check system resources
   ```
2. Stop conflicting services or change STING ports in `.env` files

### Network Timeouts

**Symptom**: Image pulls fail with timeout errors (like in your example).

**Solution**:
1. Check your Docker proxy settings
2. Retry with better network connection
3. The enhanced startup will automatically retry failed pulls

### Service Health Issues

**Symptom**: Service running but not responding to health checks.

**Solution**: The recovery tool can recreate unhealthy services:
```bash
./scripts/recover_services.sh
# Select option 5 to recreate specific service
```

## Configuration

### Retry Settings

You can modify retry behavior by editing `/lib/service_startup_resilience.sh`:
```bash
MAX_RETRIES=3        # Number of retry attempts
RETRY_DELAY=5        # Seconds between retries
```

### Health Check URLs

Health check endpoints are defined in the resilience script:
```bash
HEALTH_CHECKS[app]="https://localhost:5050/health"
HEALTH_CHECKS[frontend]="https://localhost:8443"
HEALTH_CHECKS[chatbot]="http://localhost:5005/health"
# etc...
```

## Troubleshooting

### Enable Debug Logging

For more detailed output during startup:
```bash
DEBUG=true ./manage_sting.sh start
```

### Check Service Logs

View logs for a specific service:
```bash
docker logs sting-ce-<service-name> --tail 50
```

### Manual Service Start

If automatic recovery fails, start services manually:
```bash
# Start a specific service
docker start sting-ce-frontend

# Or recreate it
docker compose up -d frontend --force-recreate
```

### Full System Reset

As a last resort, perform a full reset:
```bash
./manage_sting.sh stop
./manage_sting.sh cleanup
./manage_sting.sh install
```

## Integration with manage_sting.sh

The enhanced resilience is automatically integrated into:
- `./manage_sting.sh install` - Ensures all services start after installation
- `./manage_sting.sh update` - Handles services that fail during updates
- `./manage_sting.sh start` - Recovers any failed services

No additional configuration is needed - it works automatically!

## For Developers

### Adding New Services

When adding new services, update the dependency map in `/lib/service_startup_resilience.sh`:

```bash
# Add your service dependencies
SERVICE_DEPS[myservice]="postgres redis app"

# Add health check if applicable
HEALTH_CHECKS[myservice]="http://localhost:PORT/health"
```

### Custom Recovery Logic

You can add service-specific recovery logic by extending the `start_service_with_retry` function in the resilience script.

## Support

If you continue experiencing startup issues:
1. Run the recovery tool and note any error messages
2. Check the [STING documentation](https://github.com/STING-Framework/STING)
3. Report issues with full error logs and recovery tool output