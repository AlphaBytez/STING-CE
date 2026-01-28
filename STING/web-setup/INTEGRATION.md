# Setup Wizard Integration with STING Installer

## Overview

The web setup wizard **prepares configuration** but **delegates installation** to STING's existing `install_sting.sh` script. This ensures we leverage the battle-tested installation logic in `STING/lib/`.

## Philosophy

**"Configure, Don't Install"**

- Wizard gathers configuration from user
- Validates config with `config_loader.py`
- **Stages files** in correct locations
- Invokes existing `install_sting.sh`
- Installer handles the complex orchestration

## Staging Pipeline

### 1. Configuration Files

**What wizard does:**
```bash
# Wizard writes config.yml to staging location
/var/lib/sting-setup/config.yml  # Wizard's draft

# On "Apply", wizard copies to:
/opt/sting-ce/conf/config.yml     # Where installer expects it
```

**What installer does:**
```bash
# Installer reads /opt/sting-ce/conf/config.yml
# Runs config_loader.py to generate env files
# Starts all STING services
```

### 2. Data Disk

**What wizard does:**
```bash
# Format and mount data disk
mkfs.ext4 /dev/sdb1
mount /dev/sdb1 /data
echo "UUID=... /data ext4 defaults 0 2" >> /etc/fstab

# Update config.yml with data paths:
storage:
  volumes:
    - name: postgres_data
      mount: /data/postgres
    - name: vault_data
      mount: /data/vault
```

**What installer does:**
- Reads storage config from `config.yml`
- Creates volume mount points
- Configures Docker volumes to use `/data/*`

### 3. Admin Account

**What wizard does:**
```bash
# Generate admin credentials file
cat > /var/lib/sting-setup/admin-credentials.json <<EOF
{
  "email": "admin@example.com",
  "password_hash": "bcrypt$$2b$12$...",
  "created_at": "2025-10-15T10:00:00Z"
}
EOF

# Signal installer to create admin
touch /var/lib/sting-setup/create-admin-flag
```

**What installer does:**
```bash
# Check for admin creation flag
if [[ -f /var/lib/sting-setup/create-admin-flag ]]; then
    # Use Kratos API to create admin identity
    # Load credentials from JSON file
    # Create initial admin user
fi
```

### 4. LLM Configuration

**What wizard does:**
```yaml
# Test endpoint, then write to config.yml
llm_service:
  ollama:
    enabled: true
    endpoint: "http://192.168.1.100:11434"
    default_model: "phi3:mini"
```

**What installer does:**
- Starts external_ai_service with endpoint
- Validates connectivity (health checks)
- Downloads models if `auto_install: true`

### 5. SSL Certificates

**What wizard does:**
```bash
# Option 1: Self-signed
# Do nothing - installer generates these

# Option 2: User-provided
# Stage certificates in expected location
mkdir -p /opt/sting-ce/certs
cp uploaded-cert.crt /opt/sting-ce/certs/cert.pem
cp uploaded-key.key /opt/sting-ce/certs/key.pem
```

**What installer does:**
```bash
# Check for existing certs
if [[ ! -f /opt/sting-ce/certs/cert.pem ]]; then
    # Generate self-signed cert
    openssl req -x509 -newkey rsa:4096 ...
fi
```

## Wizard → Installer Handoff

### Final `apply-config` Flow

```python
def apply_config():
    """Apply configuration and invoke installer"""
    state = load_setup_state()
    config = state['config_data']

    # 1. Validate config one last time
    valid, errors = validate_config_with_loader(config)
    if not valid:
        return jsonify({'errors': errors}), 400

    # 2. Stage configuration files
    stage_config_files(config)

    # 3. Stage admin credentials (if needed)
    if 'admin' in config:
        stage_admin_credentials(config['admin'])

    # 4. Stage SSL certificates (if uploaded)
    if config.get('ssl_uploaded'):
        stage_ssl_certificates()

    # 5. Write final config.yml
    with open('/opt/sting-ce/conf/config.yml', 'w') as f:
        yaml.dump(build_sting_config(config), f)

    # 6. Invoke STING installer (this is complex, let it handle orchestration)
    result = subprocess.run(
        ['/opt/sting-ce/install_sting.sh', 'install', '--non-interactive'],
        capture_output=True,
        text=True,
        timeout=1800  # 30 minute timeout
    )

    if result.returncode != 0:
        return jsonify({
            'success': False,
            'error': 'Installation failed',
            'details': result.stderr
        }), 500

    # 7. Mark setup complete
    mark_setup_complete()

    # 8. Disable wizard service
    subprocess.run(['systemctl', 'disable', 'sting-setup-wizard'])

    return jsonify({
        'success': True,
        'message': 'STING installed successfully!',
        'redirect_url': 'https://localhost:8443'
    })
```

## Why This Approach?

### Pros ✅

1. **Leverage existing installer** - Don't reinvent the wheel
2. **Respect complexity** - `STING/lib/` has years of fixes and edge cases
3. **Single source of truth** - One installer to maintain
4. **Separation of concerns** - Wizard = config, Installer = orchestration
5. **Easy to update** - Installer improvements automatically benefit wizard

### Cons ⚠️

1. **Dependency** - Wizard requires STING source at `/opt/sting-ce`
2. **Installer changes** - Must stay compatible with wizard's staging format
3. **Error handling** - Installer errors need to propagate back to wizard UI

## Installer Requirements

For the wizard to work, the STING installer should:

### 1. Accept Non-Interactive Mode

```bash
./install_sting.sh install --non-interactive
```

- Skip user prompts
- Use config from `/opt/sting-ce/conf/config.yml`
- Return 0 on success, non-zero on failure

### 2. Check for Admin Creation Flag

```bash
# In lib/bootstrap.sh or lib/installation.sh
if [[ -f /var/lib/sting-setup/create-admin-flag ]]; then
    create_admin_from_wizard
fi
```

### 3. Respect Data Disk Mounts

```bash
# Don't try to mount /data if already mounted
if mountpoint -q /data; then
    echo "Data disk already mounted (from wizard)"
fi
```

### 4. Clean Up Wizard State

```bash
# After successful install
mark_setup_complete() {
    echo "$(date -Iseconds)" > /var/lib/sting-setup/setup-complete
    systemctl disable sting-setup-wizard
    systemctl stop sting-setup-wizard
}
```

## Testing the Integration

### End-to-End Test

```bash
# 1. Install wizard
sudo ./scripts/install-setup-wizard.sh

# 2. Start wizard
sudo systemctl start sting-setup-wizard

# 3. Complete wizard via browser
# http://localhost:8080

# 4. Verify installer was called
sudo journalctl -u sting-setup-wizard -n 100

# 5. Verify STING is running
sudo /opt/sting-ce/manage_sting.sh status

# 6. Verify wizard is disabled
sudo systemctl status sting-setup-wizard
# Should show: Loaded: loaded (/etc/systemd/system/sting-setup-wizard.service; disabled)
```

### Manual Staging Test

```bash
# Test without invoking installer
cd /opt/sting-setup-wizard

# Run wizard
python3 app.py

# In wizard, complete all steps but DON'T click "Apply"

# Check staged files
ls -la /var/lib/sting-setup/
cat /opt/sting-ce/conf/config.yml
cat /var/lib/sting-setup/admin-credentials.json

# Manually invoke installer
sudo /opt/sting-ce/install_sting.sh install --non-interactive
```

## Future Enhancements

### 1. Pre-flight Checks

Add to wizard before allowing "Apply":

```python
def check_installer_prerequisites():
    """Verify installer can run successfully"""
    checks = [
        ('STING source', os.path.exists('/opt/sting-ce/install_sting.sh')),
        ('Docker installed', shutil.which('docker') is not None),
        ('Disk space', get_free_space('/') > 20 * 1024**3),  # 20GB
        ('Internet connectivity', test_internet()),
    ]

    failed = [name for name, passed in checks if not passed]
    return len(failed) == 0, failed
```

### 2. Progress Streaming

Show installer progress in wizard UI:

```python
# Stream installer output to browser via WebSocket
proc = subprocess.Popen(
    ['/opt/sting-ce/install_sting.sh', 'install'],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

for line in proc.stdout:
    # Send to browser via SSE or WebSocket
    yield f"data: {line}\n\n"
```

### 3. Rollback on Failure

If installer fails, allow user to retry or rollback:

```python
def rollback_configuration():
    """Undo wizard changes if installer fails"""
    # Remove staged config
    os.remove('/opt/sting-ce/conf/config.yml')

    # Unmount data disk
    subprocess.run(['umount', '/data'])

    # Remove admin credentials
    shutil.rmtree('/var/lib/sting-setup')

    # Re-enable wizard
    subprocess.run(['systemctl', 'enable', 'sting-setup-wizard'])
```

## Summary

**Wizard's Job:**
- Gather user input
- Validate configuration
- Stage files in correct locations
- Invoke installer

**Installer's Job:**
- Read staged configuration
- Orchestrate Docker services
- Create admin user
- Start STING platform

**Result:**
- Clean separation of concerns
- Leverages existing battle-tested code
- Easy to maintain and update
- User-friendly configuration experience
