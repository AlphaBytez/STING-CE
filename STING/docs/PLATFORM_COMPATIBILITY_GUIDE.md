# Platform Compatibility Guide

This guide explains how STING handles Docker networking differences across macOS, Linux, and WSL2 platforms.

## The Problem

Different platforms handle Docker host connectivity differently:

- **macOS (Docker Desktop)**: Supports `host.docker.internal` natively
- **WSL2 (Docker Desktop)**: Supports `host.docker.internal`
- **Linux native Docker**: Does NOT support `host.docker.internal`
- **WSL2 (native Docker)**: Does NOT support `host.docker.internal`

This affects services that need to access host-run services (like Ollama running on the host machine).

## The Solution

STING now includes **automatic platform detection** that adapts Docker networking configuration based on your platform.

### How It Works

1. **Platform Detection** (`lib/platform_helper.sh`):
   - Detects if running on macOS, Linux, or WSL2
   - Determines the appropriate Docker host gateway address

2. **Config Loader Integration** (`conf/config_loader.py`):
   - Automatically detects platform during config generation
   - Replaces `host.docker.internal` with platform-specific gateway
   - Generates environment files with correct networking configuration

3. **Docker Compose** (requires manual setup for Linux/WSL2):
   - macOS: Works out of the box
   - Linux/WSL2: Requires `extra_hosts` configuration (see below)

## Platform-Specific Setup

### macOS (Docker Desktop) ✅

**No additional configuration needed!** Everything works out of the box.

```bash
# Just install and run
./install_sting.sh install
```

### Linux Native Docker

**Additional Step Required**: Add `extra_hosts` to services that need host access.

Edit `docker-compose.yml` and add this to services like `nectar-worker`, `external-ai`, and `chatbot`:

```yaml
nectar-worker:
  container_name: sting-ce-nectar-worker
  # ... other configuration ...
  extra_hosts:
    - "host.docker.internal:host-gateway"  # Add this line
```

**Quick Setup**:
```bash
# 1. Run platform helper to confirm Linux detection
./lib/platform_helper.sh info

# 2. Manually add extra_hosts to these services:
#    - nectar-worker
#    - external-ai
#    - chatbot
#    - llm-gateway (if using host Ollama)

# 3. Install as normal
./install_sting.sh install
```

### WSL2

**Check Your Docker Setup First**:

```bash
# Test if you have Docker Desktop or native Docker
docker version | grep -i "Docker Desktop"

# Check platform detection
./lib/platform_helper.sh info
```

#### WSL2 with Docker Desktop ✅
**No additional configuration needed!** Docker Desktop includes `host.docker.internal` support.

#### WSL2 with Native Docker
**Same as Linux setup** - add `extra_hosts` to docker-compose.yml (see Linux section above).

## Using the Platform Helper

The `lib/platform_helper.sh` script provides several useful commands:

### Detect Platform
```bash
./lib/platform_helper.sh detect
# Output: macos, linux, or wsl2
```

### Get Gateway Address
```bash
./lib/platform_helper.sh gateway
# Output: host.docker.internal or host-gateway
```

### Show Platform Info
```bash
./lib/platform_helper.sh info
# Output:
# ─────────────────────────────────────────
#   Platform:              macos
#   Docker Host Gateway:   host.docker.internal
#   Needs extra_hosts:     no
# ─────────────────────────────────────────
```

### Generate Platform Environment
```bash
./lib/platform_helper.sh env ~/.sting-ce/.platform.env
```

### Update Existing Environment Files
```bash
# Update all env files to use correct gateway
./lib/platform_helper.sh update-env ~/.sting-ce/env
```

## Services That Need Host Access

The following services typically need to access host-run services:

| Service | Why It Needs Host Access | Default Port |
|---------|-------------------------|--------------|
| `nectar-worker` | Connects to Ollama on host | Ollama: 11434 |
| `external-ai` | Connects to Ollama on host | Ollama: 11434 |
| `chatbot` | Connects to Ollama on host | Ollama: 11434 |
| `llm-gateway` | Optional proxy to host LLM | Varies |

## Troubleshooting

### Service Can't Connect to Ollama on Host

**Symptom**: Logs show connection refused or timeout errors

**macOS**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check config
grep OLLAMA_URL ~/.sting-ce/env/nectar-worker.env
# Should show: http://host.docker.internal:11434
```

**Linux/WSL2**:
```bash
# 1. Verify platform detection
./lib/platform_helper.sh info

# 2. Check if extra_hosts is configured
docker inspect sting-ce-nectar-worker | grep -A5 ExtraHosts
# Should show: "host.docker.internal": "host-gateway"

# 3. If missing, add to docker-compose.yml:
#    extra_hosts:
#      - "host.docker.internal:host-gateway"

# 4. Recreate container
docker-compose up -d --force-recreate nectar-worker
```

### Wrong Gateway in Environment Files

If config was generated on wrong platform (e.g., generated on macOS, running on Linux):

```bash
# Method 1: Regenerate config
./manage_sting.sh regenerate-env

# Method 2: Use platform helper to update
./lib/platform_helper.sh update-env ~/.sting-ce/env

# Method 3: Fresh installation
./install_sting.sh reinstall
```

### Testing Platform Detection

```bash
# Test on macOS (should show host.docker.internal)
./lib/platform_helper.sh gateway

# Simulate Linux (for testing)
# Edit platform_helper.sh temporarily to return 'linux'
```

## Docker Compose extra_hosts Template

For Linux/WSL2 users, here's a complete service template with `extra_hosts`:

```yaml
nectar-worker:
  container_name: sting-ce-nectar-worker
  build:
    context: .
    dockerfile: Dockerfile.nectar-worker
  env_file:
    - ${INSTALL_DIR}/env/nectar-worker.env
  environment:
    - OLLAMA_URL=http://host.docker.internal:11434
    - OLLAMA_KEEP_ALIVE=30m
  extra_hosts:
    - "host.docker.internal:host-gateway"  # ← This line resolves host access on Linux
  deploy:
    resources:
      limits:
        memory: 512M
        cpus: '1.0'
  networks:
    - sting_local
  depends_on:
    app:
      condition: service_healthy
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9002/health"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 40s
  restart: unless-stopped
```

## Advanced: Multi-Platform Configurations

If you're deploying STING across multiple platforms, you can use environment variables:

```yaml
# docker-compose.yml
nectar-worker:
  environment:
    - OLLAMA_URL=http://${DOCKER_HOST_GATEWAY:-host.docker.internal}:11434
  extra_hosts:
    - "host.docker.internal:host-gateway"  # Safe to include on all platforms
```

```bash
# Set platform-specific gateway
export DOCKER_HOST_GATEWAY=$(./lib/platform_helper.sh gateway)

# Then start services
docker-compose up -d
```

## FAQ

### Q: Do I need extra_hosts on macOS?
**A**: No, macOS Docker Desktop supports `host.docker.internal` natively.

### Q: Will extra_hosts break things on macOS?
**A**: No, it's harmless and will be ignored if `host.docker.internal` already works.

### Q: Can I use 172.17.0.1 instead of host-gateway?
**A**: Yes, but `host-gateway` is more flexible and works across different Docker bridge configurations.

### Q: What if I'm using a custom Docker bridge network?
**A**: The `host-gateway` address will automatically resolve to the correct gateway IP for your network.

### Q: Do all services need extra_hosts?
**A**: No, only services that need to access host-run services (like Ollama). Container-to-container communication works fine without it.

## Summary

| Platform | Config Needed | extra_hosts | Works Out of Box |
|----------|---------------|-------------|------------------|
| macOS (Docker Desktop) | ❌ None | ❌ No | ✅ Yes |
| WSL2 (Docker Desktop) | ❌ None | ❌ No | ✅ Yes |
| Linux (native Docker) | ⚠️ Manual extra_hosts | ✅ Yes | ⚠️ After setup |
| WSL2 (native Docker) | ⚠️ Manual extra_hosts | ✅ Yes | ⚠️ After setup |

**Bottom Line**:
- **macOS/WSL2 with Docker Desktop**: Just install and run!
- **Linux/WSL2 native Docker**: Add `extra_hosts` to services, then install!

## Related Files

- Platform detection: `lib/platform_helper.sh`
- Config generation: `conf/config_loader.py` (lines 322-376, 1656-1659)
- Service implementation: `docs/platform/requirements/service-implementation-checklist.md`
