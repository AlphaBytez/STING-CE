# BuildKit Cache Issue and Solutions

## Problem Summary

When using `./manage_sting.sh update <service>`, the Docker BuildKit cache prevents updated code from being included in rebuilt containers, even with `--no-cache` flag.

### Root Causes:
1. **BuildKit enabled**: `DOCKER_BUILDKIT=1` uses aggressive caching
2. **Build context caching**: BuildKit caches file checksums and doesn't detect changes
3. **Cached layers**: Even with `--no-cache`, some layers are reused
4. **File sync issue**: Files may not be copied from project to install directory before build

## Quick Solutions

### Option 1: Use the No-BuildKit Update Script (Recommended)
```bash
# Make script executable
chmod +x ./update_service_nobuildkit.sh

# Update a service
./update_service_nobuildkit.sh app
./update_service_nobuildkit.sh frontend
```

### Option 2: Disable BuildKit Temporarily
```bash
# Disable BuildKit for this session
export DOCKER_BUILDKIT=0

# Then use normal update command
./manage_sting.sh update app
```

### Option 3: Manual Update Process
```bash
# 1. Copy files from project to install directory
rsync -av --delete ./app/ ~/.sting-ce/app/

# 2. Remove old container and image
docker compose -f ~/.sting-ce/docker-compose.yml stop app
docker compose -f ~/.sting-ce/docker-compose.yml rm -f app
docker rmi sting-ce-app:latest

# 3. Build without BuildKit
cd ~/.sting-ce
DOCKER_BUILDKIT=0 docker compose build --no-cache app

# 4. Start the service
docker compose up -d app

# 5. Verify the update
docker exec sting-ce-app grep -c "logout_flow_url" /opt/sting-ce/app/routes/auth_routes.py
```

## Permanent Fixes Applied

### 1. Updated cache_buzzer.sh
- Re-enabled build arguments for cache busting
- Added `BUILDKIT_INLINE_CACHE=0` to disable inline cache
- Added file sync verification before building

### 2. Created verify_file_sync() Function
- Compares files between project and install directories
- Automatically syncs changed files before building
- Provides clear feedback on what files are being updated

## Long-term Solutions

### 1. Update docker.sh to Handle BuildKit Better
```bash
# In build_docker_services() function
if [ "$no_cache" = "true" ]; then
    # Option A: Disable BuildKit for no-cache builds
    export DOCKER_BUILDKIT=0
    
    # Option B: Use BuildKit with proper cache invalidation
    export BUILDKIT_INLINE_CACHE=0
    docker buildx build --no-cache --no-cache-filter --progress=plain
fi
```

### 2. Add Dockerfile Improvements
```dockerfile
# Add cache-busting arguments
ARG CACHEBUST=1
ARG BUILD_DATE

# Use in COPY commands to invalidate cache
COPY --chown=root:root . /opt/sting-ce/app/
RUN echo "Build date: ${BUILD_DATE}"
```

### 3. Implement Proper CI/CD Pipeline
- Use versioned images instead of :latest
- Tag images with git commit hash
- Use multi-stage builds with explicit cache mounts

## Testing the Fix

After updating a service, verify the code is actually updated:

```bash
# For app service - check for new logout code
docker exec sting-ce-app grep -c "logout_flow_url" /opt/sting-ce/app/routes/auth_routes.py
# Should return: 2

# For frontend - check for identifier-first flow
docker exec sting-ce-frontend grep -c "identifier-first" /app/src/components/auth/EnhancedKratosLogin.jsx
# Should return: 3

# Check container creation time
docker inspect sting-ce-app | jq '.[0].Created'
# Should be recent
```

## Prevention

1. **Always verify updates**: After updating, check that new code is in the container
2. **Use version tags**: Instead of :latest, use specific versions
3. **Clear builder cache regularly**: `docker buildx prune -af`
4. **Monitor disk usage**: BuildKit cache can grow large

## Related Files
- `/lib/cache_buzzer.sh` - Main cache management script
- `/lib/docker.sh` - Docker build functions
- `/update_service_nobuildkit.sh` - Quick fix script
- `/.env` - Check if DOCKER_BUILDKIT is set here