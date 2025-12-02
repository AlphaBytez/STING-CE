# DNS Troubleshooting Guide for STING-CE

## Problem

When installing STING-CE on Windows/WSL, you may encounter DNS resolution errors during Docker builds:

```
Temporary failure in name resolution
Could not resolve host: pypi.org
Failed to establish a new connection
```

## Root Cause

Windows/WSL systems sometimes have DNS configuration issues where:
- The host system (Windows) can resolve DNS correctly
- WSL can resolve DNS correctly
- But Docker containers during build **cannot** resolve DNS

This is a known issue with Docker on Windows/WSL and affects many projects, not just STING.

## Automatic Fix (Recommended)

STING-CE v1.0+ automatically configures Docker BuildKit to use public DNS servers (Google DNS, Cloudflare) during builds via the `buildkitd.toml` configuration file.

This fix is **transparent** and **cross-platform** - it works on:
- ✅ Windows/WSL
- ✅ macOS  
- ✅ Linux

No manual Docker configuration is needed!

## If Issues Persist

If you still see DNS errors after updating to the latest version:

### Quick Test

```bash
./fix_dns.sh --check-only
```

This will test DNS resolution and report any issues.

### Automatic Fix

```bash
./fix_dns.sh
```

This will:
1. Test DNS resolution
2. Configure `/etc/resolv.conf` with public DNS servers
3. Prevent WSL from overwriting the configuration
4. Re-test to verify the fix worked

### Manual Fix

#### For WSL Users

1. Edit WSL configuration:
   ```bash
   sudo nano /etc/wsl.conf
   ```

2. Add or update the network section:
   ```ini
   [network]
   generateResolvConf = false
   ```

3. Edit DNS configuration:
   ```bash
   sudo nano /etc/resolv.conf
   ```

4. Replace contents with:
   ```
   nameserver 8.8.8.8
   nameserver 8.8.4.4
   nameserver 1.1.1.1
   ```

5. Make it immutable (prevents WSL from overwriting):
   ```bash
   sudo chattr +i /etc/resolv.conf
   ```

6. Restart WSL (from PowerShell):
   ```powershell
   wsl --shutdown
   ```

7. Reopen WSL and test:
   ```bash
   nslookup pypi.org
   ping google.com
   ```

#### For Docker Desktop Users (Windows)

1. Open Docker Desktop settings
2. Go to "Docker Engine"
3. Add DNS configuration:
   ```json
   {
     "dns": ["8.8.8.8", "8.8.4.4"]
   }
   ```
4. Click "Apply & Restart"

**Note:** This approach requires manual configuration on every machine and is not recommended. Use the automatic BuildKit configuration instead.

## How STING Fixes This

STING-CE uses a `buildkitd.toml` file that configures Docker's BuildKit builder with DNS servers:

```toml
[dns]
  nameservers = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]
  options = ["ndots:0"]
  searchDomains = []
```

This configuration is automatically applied when the installer creates the BuildKit builder:

```bash
docker buildx create --name builder --driver docker-container --config buildkitd.toml --use
```

## Why This Approach is Better

1. **No Docker Daemon Configuration**: Users don't need to modify Docker settings
2. **Project-Specific**: Only affects STING builds, not all Docker operations
3. **Cross-Platform**: Works on Windows, macOS, and Linux
4. **Transparent**: Users don't need to do anything
5. **Maintainable**: Configuration is version-controlled in the repository

## Verification

After installation, you can verify BuildKit is using the correct DNS:

```bash
# Inspect the builder
docker buildx inspect builder

# The output should show the buildkitd.toml config is being used
```

## Related Issues

This fix addresses:
- pip install failures during Python container builds
- apt-get failures during system package installation  
- curl/wget failures during file downloads
- git clone failures during source checkouts

## Additional Resources

- [Docker BuildKit DNS Configuration](https://github.com/moby/buildkit/blob/master/docs/buildkitd.toml.md)
- [WSL DNS Issues](https://github.com/microsoft/WSL/issues/5256)
- [Docker Desktop DNS](https://docs.docker.com/desktop/networking/#dns-resolution)

## Getting Help

If you continue to experience DNS issues:

1. Run `./fix_dns.sh --check-only` to diagnose the problem
2. Check the [STING-CE Issues](https://github.com/AlphaBytez/STING-CE/issues) for similar problems
3. Create a new issue with:
   - Output from `./fix_dns.sh --check-only`
   - Output from `docker buildx inspect builder`
   - Your platform (Windows version, WSL version, Docker version)
