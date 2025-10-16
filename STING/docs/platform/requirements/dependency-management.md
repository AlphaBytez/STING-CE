# Dependency Management in STING-CE

## Overview

STING-CE uses a flexible dependency management approach that allows platform-specific configurations without breaking Docker Compose.

## Key Changes

### 1. Removed Hard Dependencies

The `llm-gateway` service no longer has hard dependencies on model services:
- Allows Mac to skip model services entirely
- Prevents circular dependency issues
- Enables flexible deployment strategies

### 2. Script-Based Orchestration

Service startup order is now managed by `manage_sting.sh`:
- Platform detection (Mac vs Linux)
- Conditional service startup
- Proper health checking

### 3. Mac-Specific Overrides

The `docker-compose.mac.yml` file provides:
- Stub services to satisfy Docker Compose
- Port forwarding from Docker to native services
- Modified dependency chains

## Platform Behaviors

### macOS
1. Native LLM service starts first (MPS support)
2. Stub services created for compatibility
3. Docker services connect to native via `host.docker.internal`

### Linux
1. Model services start first
2. LLM gateway starts after models
3. All services run in Docker

## Service Startup Order

### Core Services (Both Platforms)
1. Vault (secrets management)
2. Database (PostgreSQL)
3. Mailpit (email testing)
4. Kratos (authentication)
5. Redis (caching)
6. App (backend API)
7. Frontend (React)

### LLM Services (Platform-Specific)

**macOS:**
1. Native LLM service (Python with MPS)
2. Docker stub gateway (port forwarder)
3. Chatbot (connects to native)

**Linux:**
1. Model services (llama3, phi3, zephyr)
2. LLM gateway (depends on models)
3. Chatbot (connects to gateway)

## Troubleshooting

### "Service depends on undefined service"

This occurs when Docker Compose can't resolve dependencies. Solutions:
1. Ensure you're using the management script
2. Check that Mac override is being loaded
3. Verify stub services are defined

### "LLM gateway unhealthy"

On Mac, this might mean:
1. Native service isn't running
2. Port 8085 is blocked
3. Python dependencies missing

Check with:
```bash
./sting-llm status
curl http://localhost:8085/health
```

### Build Failures

If builds fail due to dependencies:
1. Clean Docker state: `docker compose down -v`
2. Remove unused images: `docker system prune`
3. Rebuild: `./manage_sting.sh install`

## Best Practices

1. **Always use the management script** - Don't use `docker compose` directly
2. **Check platform detection** - Run `./check-mac-setup.sh` on Mac
3. **Monitor service health** - Use `./manage_sting.sh status`
4. **Review logs** - Check both Docker and native logs

## Future Improvements

1. **Unified service mesh** - Single orchestration layer
2. **Dynamic dependency resolution** - Runtime dependency checking
3. **Health-based startup** - Wait for actual health, not just "started"
4. **Graceful degradation** - Run without optional services