# DNS Fix Implementation - Change Log

## Summary

Implemented automatic DNS configuration for Docker BuildKit to resolve "Temporary failure in name resolution" errors on Windows/WSL systems during installation.

## Problem

On Windows/WSL systems, Docker containers during build time may fail to resolve DNS even when the host system and WSL can resolve DNS correctly. This causes:

- `pip install` failures (pypi.org not resolvable)
- `apt-get` failures (package repositories not resolvable)
- `curl`/`wget` failures (download servers not resolvable)

## Solution

### Automatic Fix (Primary)

Added DNS configuration to `buildkitd.toml` that is automatically applied when creating the Docker BuildKit builder. This is:

- ✅ **Transparent**: No user action required
- ✅ **Cross-platform**: Works on Windows, macOS, Linux
- ✅ **Project-specific**: Only affects STING builds
- ✅ **Maintainable**: Version-controlled configuration

### Helper Script (Secondary)

Created `fix_dns.sh` script for diagnosing and fixing system-level DNS issues if they persist.

## Files Changed

### 1. `buildkitd.toml`

**Added DNS configuration block:**

```toml
# DNS configuration for build-time network resolution
# Fixes "Temporary failure in name resolution" on Windows/WSL
[dns]
  nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
  options = ["ndots:0"]
  searchDomains = []
```

**Why this works:**
- BuildKit containers inherit this DNS configuration during builds
- Uses reliable public DNS servers (Google, Cloudflare)
- Bypasses any WSL/Docker DNS misconfiguration

### 2. `lib/docker.sh`

**Updated builder creation to use buildkitd.toml:**

```bash
# Before:
docker buildx create --name builder --driver docker-container --use

# After:
local buildkit_config="$SCRIPT_DIR/buildkitd.toml"
if [ -f "$buildkit_config" ]; then
    docker buildx create --name builder --driver docker-container --config "$buildkit_config" --use
else
    docker buildx create --name builder --driver docker-container --use
fi
```

**Impact:**
- Automatically applies DNS config when builder is created
- Graceful fallback if buildkitd.toml is missing
- No changes needed to build commands

### 3. `lib/cache_buzzer.sh`

**Updated custom builder creation (when enabled) to use buildkitd.toml:**

Similar changes as docker.sh for consistency.

### 4. `fix_dns.sh` (New)

**Diagnostic and repair script:**

- Tests DNS resolution for common hosts
- Automatically configures `/etc/resolv.conf` on WSL
- Prevents WSL from overwriting DNS configuration
- Provides helpful guidance for manual fixes

**Usage:**
```bash
# Test only
./fix_dns.sh --check-only

# Test and fix
./fix_dns.sh
```

### 5. `DNS_TROUBLESHOOTING.md` (New)

**Comprehensive documentation:**

- Explains the problem and root cause
- Documents the automatic fix
- Provides manual fix instructions
- Includes verification steps
- Links to related resources

### 6. `README.md`

**Updated troubleshooting section:**

- Added DNS issues as first troubleshooting item (most common on Windows/WSL)
- Links to detailed troubleshooting guide
- Notes that v1.0+ has automatic fix

## Testing

### Test Scenarios

1. ✅ **Fresh installation on WSL with DNS issues**
   - BuildKit automatically configured with DNS
   - Builds succeed without manual intervention

2. ✅ **Existing installation being rebuilt**
   - If builder exists without DNS config, remove and recreate:
     ```bash
     docker buildx rm builder
     ./manage_sting.sh rebuild
     ```

3. ✅ **System-level DNS issues**
   - `fix_dns.sh` detects and repairs `/etc/resolv.conf`
   - Prevents WSL from overwriting configuration

### Verification

```bash
# Check if builder uses buildkitd.toml
docker buildx inspect builder

# Test DNS from within BuildKit
docker run --rm -it $(docker ps -aq --filter "name=buildx_buildkit_builder") nslookup pypi.org

# Run diagnostic script
./STING/fix_dns.sh --check-only
```

## Migration Notes

### For Existing Users

If you have an existing STING installation experiencing DNS issues:

1. Pull latest changes with this fix
2. Remove existing builder:
   ```bash
   docker buildx rm builder
   ```
3. Rebuild STING:
   ```bash
   cd STING
   ./manage_sting.sh rebuild
   ```

The builder will be recreated with DNS configuration automatically.

### For New Users

No action needed - DNS configuration is automatic on new installations.

## Why Not Docker Daemon Configuration?

We considered but rejected the approach of requiring users to modify Docker Desktop settings because:

1. **Not sustainable**: Requires manual steps on every machine
2. **Platform-specific**: Different on Docker Desktop vs Docker Engine
3. **Affects all containers**: Not project-specific
4. **Hard to document**: Varies by Docker version and OS
5. **Not version-controlled**: Changes lost when reinstalling Docker

The BuildKit configuration approach is superior because it's automatic, portable, and maintainable.

## Related Issues

This fix addresses issues seen in:
- Windows 10/11 with WSL2
- Docker Desktop on Windows
- Some Linux distributions with misconfigured DNS

Does not affect:
- macOS (typically has correct DNS)
- Most native Linux installations
- Cloud/VM deployments with proper DNS

## References

- [BuildKit Configuration Docs](https://github.com/moby/buildkit/blob/master/docs/buildkitd.toml.md)
- [WSL DNS Issues](https://github.com/microsoft/WSL/issues/5256)
- [Docker BuildKit DNS](https://docs.docker.com/build/buildkit/configure/)

## Credits

Fix developed in response to user feedback about installation failures on Windows/WSL systems.

---

**Date**: 2025-10-29  
**Version**: STING-CE v1.0+  
**Author**: AlphaBytez Development Team
