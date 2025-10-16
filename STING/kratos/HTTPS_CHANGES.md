# Kratos HTTPS Configuration Changes

## Problem
The Kratos authentication service was failing to start properly because of a mismatch between how it was configured (HTTP) and how it was being accessed (HTTPS).

## Changes Made

### 1. Updated Kratos Configuration
- Modified `main.kratos.yml` and `minimal.kratos.yml` to:
  - Change base URLs from `http://0.0.0.0:4433` to `https://localhost:4433`
  - Add TLS configuration to use self-signed certificates
  - Configure HTTPS for both public and admin interfaces

### 2. Updated Docker Configuration
- Added certificate mounts in `docker-compose.yml` to provide SSL certificates to the Kratos container:
  ```yaml
  volumes:
    - ./certs/server.crt:/etc/certs/server.crt:ro
    - ./certs/server.key:/etc/certs/server.key:ro
  ```
- Updated health check to use HTTPS with certificate validation disabled:
  ```yaml
  test: ["CMD-SHELL", "wget --no-check-certificate --no-verbose --spider https://localhost:4434/admin/health/ready || exit 1"]
  ```

### 3. Fixed Health Check in `manage_sting.sh`
- Updated health check to use HTTPS with `-k` flag to ignore certificate validation:
  ```bash
  curl -s -f -k https://localhost:4434/admin/health/ready > /dev/null
  ```

### 4. Updated Configuration Generation
- Modified `config_loader.py` to use HTTPS URLs by default:
  ```python
  public_url = kratos_config.get('public_url', 'https://localhost:4433')
  admin_url = kratos_config.get('admin_url', 'https://localhost:4434')
  ```

### 5. Updated Global Configuration
- Updated `config.yml` to use HTTPS for Kratos URLs:
  ```yaml
  kratos:
    public_url: "https://localhost:4433"
    admin_url: "https://localhost:4434"
  ```

## Verification
After making these changes, verify that:
1. Kratos starts properly with HTTPS
2. The health check passes 
3. The login form loads correctly in the frontend

## Security Note
These changes ensure that all authentication traffic is encrypted, including in development environments. Using HTTPS for authentication services is a security best practice, even when using self-signed certificates for development.