# 🐝 Cache Buzzer Admin Guide

## Overview

The Cache Buzzer is a critical administrative tool for STING CE that ensures Docker containers are truly rebuilt from scratch, eliminating persistent cache issues that can cause mysterious bugs and outdated code in running containers.

## The Problem

Docker's caching mechanism, while normally helpful for build speed, can sometimes work against you:

- `docker-compose build --no-cache` doesn't always clear all cache layers
- Intermediate build stages can persist
- Base images may be cached
- Volumes and networks can retain old data
- BuildKit cache can persist across builds

These issues lead to situations where:
- Code changes don't appear in running containers
- Configuration files remain outdated
- "Fixed" bugs mysteriously reappear
- Fresh installs use stale components

## The Solution: Cache Buzzer 🐝

The Cache Buzzer provides aggressive cache clearing with multiple levels of intensity, ensuring your containers are truly fresh.

## Quick Start

```bash
# Validate current container freshness
./manage_sting.sh cache-buzz --validate

# Moderate cache clear and rebuild (recommended for most cases)
./manage_sting.sh cache-buzz

# Full nuclear option - removes everything and rebuilds
./manage_sting.sh cache-buzz --full

# Target specific service
./manage_sting.sh cache-buzz app
```

## Cache Buzzer Modes

### 1. Minimal Mode
```bash
./manage_sting.sh cache-buzz --minimal
```
- Clears Docker build cache only
- Preserves running containers and images
- Fastest option
- Use when: You suspect BuildKit cache issues

### 2. Moderate Mode (Default)
```bash
./manage_sting.sh cache-buzz --moderate
# or simply
./manage_sting.sh cache-buzz
```
- Clears Docker build cache
- Removes dangling images
- Clears BuildKit cache
- Use when: Standard rebuilds aren't picking up changes

### 3. Full Mode
```bash
./manage_sting.sh cache-buzz --full
```
- Stops all STING containers
- Removes all STING containers
- Removes all STING images
- Clears all build caches
- Removes unused volumes
- Complete fresh start
- Use when: Nothing else works or major structural changes

## Advanced Usage

### Target Specific Services

```bash
# Rebuild only the app service
./manage_sting.sh cache-buzz app

# Rebuild only frontend with full cache clear
./manage_sting.sh cache-buzz --full frontend

# Rebuild only Kratos
./manage_sting.sh cache-buzz kratos
```

### Cache Operations Without Rebuild

```bash
# Just clear cache, don't rebuild
./manage_sting.sh cache-buzz --clear-only

# Clear full cache without rebuilding
./manage_sting.sh cache-buzz --full --clear-only
```

### Validation

```bash
# Check container freshness without any changes
./manage_sting.sh cache-buzz --validate
```

The validation tool checks:
- Container creation times
- Critical file presence
- Image ages
- Configuration file availability

## Integration with Other Commands

Cache Buzzer is automatically integrated into STING's build system:

```bash
# These commands now use cache buzzer when --no-cache is specified
./manage_sting.sh build --no-cache
./manage_sting.sh update --no-cache

# Reinstall automatically uses cache buzzer
./manage_sting.sh reinstall              # Uses moderate cache clearing
./manage_sting.sh reinstall --fresh      # Uses full cache clearing
./manage_sting.sh reinstall --cache-full # Force full cache clearing
./manage_sting.sh reinstall --cache-minimal # Use minimal cache clearing
```

### Reinstall Cache Behavior

- **Default reinstall**: Uses moderate cache clearing
- **--fresh reinstall**: Automatically uses full cache clearing for complete refresh
- **Custom levels**: Can override with --cache-minimal, --cache-moderate, or --cache-full

## Troubleshooting Common Issues

### Issue: "Passkey models missing" or similar file errors

**Solution:**
```bash
./manage_sting.sh cache-buzz --full app
```

### Issue: "Identity schema missing" in Kratos

**Solution:**
```bash
./manage_sting.sh cache-buzz --full kratos
```

### Issue: Frontend not reflecting code changes

**Solution:**
```bash
./manage_sting.sh cache-buzz frontend
```

### Issue: Multiple services showing cached data

**Solution:**
```bash
# Nuclear option - full rebuild
./manage_sting.sh cache-buzz --full
```

## Technical Details

### What Cache Buzzer Actually Does

1. **Build Cache Clearing:**
   - `docker builder prune -af`
   - `docker buildx prune -af`

2. **Image Management:**
   - Removes specific STING images when in full mode
   - Clears dangling images in moderate mode

3. **Container Management:**
   - Stops and removes containers in full mode
   - Preserves running containers in other modes

4. **Enhanced Build Process:**
   - Adds `CACHEBUST` build argument with timestamp
   - Uses `--pull` to ensure fresh base images
   - Enables BuildKit for better cache management
   - Uses `--progress plain` for detailed output

### Files Involved

- `/lib/cache_buzzer.sh` - Main cache busting logic
- `/lib/docker.sh` - Enhanced build functions
- `/lib/services.sh` - Service rebuild integration
- `/lib/interface.sh` - Command line interface
- `/lib/validate_containers_simple.sh` - Validation tool

## Best Practices

1. **Regular Validation**: Run `cache-buzz --validate` periodically to ensure container freshness

2. **Before Major Updates**: Always run cache buzzer before major updates or when switching branches

3. **Development Workflow**:
   ```bash
   # After pulling new code
   git pull
   ./manage_sting.sh cache-buzz --validate
   
   # If validation fails
   ./manage_sting.sh cache-buzz
   ```

4. **Production Deployments**: Use full mode for production deployments to ensure consistency

5. **CI/CD Integration**: Include cache buzzer in your CI/CD pipeline:
   ```yaml
   - name: Ensure fresh build
     run: ./manage_sting.sh cache-buzz --full
   ```

## Performance Considerations

- **Minimal mode**: ~30 seconds
- **Moderate mode**: 2-5 minutes (depending on cache size)
- **Full mode**: 10-20 minutes (full rebuild of all services)

Plan accordingly for production systems.

## Security Benefits

Cache Buzzer also provides security benefits:
- Ensures no stale dependencies
- Prevents accidental inclusion of development artifacts
- Guarantees fresh security patches in base images
- Eliminates potential cache poisoning vectors

## Monitoring and Logging

All cache buzzer operations are logged to:
- Console output with color-coded status
- `/logs/manage_sting.log` for detailed logs
- Container validation reports

## Future Enhancements

Planned improvements:
- Automated cache freshness monitoring
- Scheduled cache buzzing for long-running systems
- Integration with health monitoring
- Cache usage metrics and reporting

---

## Quick Reference Card

```bash
# Validation
cache-buzz --validate              # Check freshness

# Cache Clearing
cache-buzz --clear-only           # Clear cache only
cache-buzz --minimal              # Minimal clear + rebuild
cache-buzz                        # Moderate clear + rebuild (default)
cache-buzz --full                 # Full clear + rebuild

# Service Specific
cache-buzz app                    # Rebuild app service
cache-buzz frontend               # Rebuild frontend
cache-buzz kratos                 # Rebuild kratos

# Combinations
cache-buzz --full app             # Full clear + rebuild app only
cache-buzz --minimal --clear-only # Minimal clear, no rebuild
```

---

*"When in doubt, buzz it out!" 🐝*