# STING-CE Web Setup Wizard

**Enterprise-grade first-run configuration wizard for STING-CE VM deployments**

## 📦 Important: Deployment Location

**This wizard should be moved to the main STING repository at `web-setup/`:**

```
STING-CE/
├── install_sting.sh
├── conf/
├── scripts/
├── web-setup/          ← This wizard directory
│   ├── app.py
│   ├── templates/
│   └── ...
└── ...
```

The wizard uses **relative paths** to auto-discover STING components (installer, config_loader, admin scripts). It must be co-located with the STING source code.

**See [VM_DEPLOYMENT.md](VM_DEPLOYMENT.md) for complete deployment instructions.**

---

## Overview

This web-based setup wizard provides a user-friendly interface for configuring STING-CE on first boot. It guides administrators through:

1. **System Configuration** - Hostname, timezone, network settings
2. **Data Disk Setup** - Detect, format, and mount separate data disk
3. **Admin Account** - Create initial administrator
4. **LLM Configuration** - Configure and test AI backend (Ollama)
5. **Email/SMTP** - Optional email notification setup
6. **SSL/TLS** - Self-signed or custom certificate configuration
7. **Review & Apply** - Final validation and deployment

## Key Features

### Tight Integration with STING

- **Uses `config_loader.py`** - Validates configuration before applying
- **Tests LLM endpoints** - Ensures Ollama is accessible and models are available
- **Disk detection** - Automatically finds unmounted disks for data storage
- **Self-disabling** - Wizard service automatically disables after successful setup

### User-Friendly Interface

- **Step-by-step wizard** - Progress indicator with 7 clear steps
- **Real-time validation** - Test configurations before applying
- **Beautiful UI** - Tailwind CSS with STING's bee-themed colors
- **Responsive design** - Works on desktop and mobile browsers

### Production-Ready

- **Systemd integration** - Runs as a system service
- **Conditional startup** - Only runs if setup not completed
- **State persistence** - Saves progress in case of interruption
- **Security-first** - Runs on port 8080, auto-disables after use

## Architecture

```
web-setup/
├── app.py                    # Flask backend with config validation
├── requirements.txt          # Python dependencies
├── templates/
│   └── wizard.html          # Multi-step wizard UI
└── README.md                # This file

scripts/
├── install-setup-wizard.sh  # Installation script
└── sting-setup-wizard.service  # Systemd unit file
```

## Installation

### On VM Images

1. Copy wizard files to VM during build:
   ```bash
   cp -r web-setup /opt/sting-setup-wizard
   ```

2. Install systemd service:
   ```bash
   ./scripts/install-setup-wizard.sh
   ```

3. On first boot, wizard starts automatically at `http://<vm-ip>:8080`

### Manual Installation

```bash
# Install dependencies
sudo apt-get install python3 python3-pip python3-venv

# Create wizard directory
sudo mkdir -p /opt/sting-setup-wizard
sudo cp -r web-setup/* /opt/sting-setup-wizard/

# Install Python packages
cd /opt/sting-setup-wizard
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Install systemd service
sudo cp scripts/sting-setup-wizard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable sting-setup-wizard
sudo systemctl start sting-setup-wizard
```

## Usage

### First-Run Setup

1. Boot the STING-CE VM
2. Open browser to `http://<vm-ip>:8080`
3. Follow wizard steps:
   - Configure system basics
   - Attach and format data disk
   - Create admin account
   - Configure LLM endpoint (test connection!)
   - (Optional) Configure email
   - Review and apply

4. Wizard validates config with `config_loader.py`
5. On success, STING installs and starts
6. Wizard service automatically disables

### Accessing During Setup

```bash
# Check wizard status
sudo systemctl status sting-setup-wizard

# View wizard logs
sudo journalctl -u sting-setup-wizard -f

# Get VM IP address
hostname -I
```

### Troubleshooting

**Wizard not accessible:**
```bash
# Check service status
sudo systemctl status sting-setup-wizard

# Restart wizard
sudo systemctl restart sting-setup-wizard

# Check firewall (allow port 8080)
sudo ufw allow 8080
```

**LLM test failing:**
- Ensure Ollama is running: `systemctl status ollama`
- Check endpoint URL is correct (default: `http://localhost:11434`)
- Verify models are installed: `ollama list`

**Disk detection not working:**
```bash
# List available disks manually
lsblk

# Ensure disk is not mounted
sudo umount /dev/sdX1

# Re-run detection in wizard
```

## API Endpoints

The wizard exposes several REST API endpoints:

- `GET /api/state` - Get current wizard state
- `GET /api/system-info` - Get system information
- `GET /api/detect-disks` - List unmounted disks
- `POST /api/test-llm` - Test LLM endpoint connectivity
- `POST /api/save-step` - Save wizard step data
- `POST /api/format-disk` - Format and mount data disk
- `POST /api/validate-config` - Validate config with `config_loader.py`
- `POST /api/apply-config` - Apply final configuration and install STING
- `GET /health` - Health check endpoint

## Configuration Validation

The wizard uses STING's `config_loader.py` to validate configuration before applying:

```python
from config_loader import load_config, ConfigurationError

# Validate config
valid, errors = validate_config_with_loader(config_data)

if not valid:
    # Show errors to user
    return jsonify({'errors': errors})

# Config is valid, safe to apply
```

This ensures that **only valid configurations** are applied to the system.

## LLM Endpoint Testing

The wizard can test LLM connectivity before finalizing setup:

```python
# Test Ollama endpoint
success, message, models = test_llm_endpoint(
    endpoint_url="http://localhost:11434",
    model_name="phi3:mini"
)

if not success:
    # Show error to user
    print(f"LLM test failed: {message}")
```

**Benefits:**
- Catches misconfigured endpoints early
- Verifies model availability
- Shows available models to user
- Prevents broken STING installations

## Self-Disable Mechanism

After successful setup, the wizard automatically disables itself:

```python
# Mark setup as complete
state['setup_complete'] = True
save_setup_state(state)

# Disable wizard service
subprocess.run(['systemctl', 'disable', 'sting-setup-wizard'])
```

The systemd service has a condition that prevents it from starting if setup is complete:

```ini
[Unit]
ConditionPathExists=!/var/lib/sting-setup/setup-complete
```

## Security Considerations

- **Root required** - Wizard runs as root to configure system
- **Local access only** - Binds to 0.0.0.0:8080 but should be firewalled
- **Auto-disable** - Service stops after setup to reduce attack surface
- **Password hashing** - Admin passwords hashed with `werkzeug.security`
- **State persistence** - Setup state saved to `/var/lib/sting-setup/`

## Development

### Testing Locally

```bash
# Set STING source path
export STING_SOURCE=/path/to/STING-CE-Fresh

# Run wizard
cd web-setup
python3 app.py

# Access at http://localhost:8080
```

### Modifying Steps

1. Add step HTML to `templates/wizard.html`
2. Add backend logic to `app.py`
3. Update `totalSteps` in JavaScript
4. Add step label to `stepLabels` array

### Adding Validation

```python
# In app.py
def validate_custom_setting(value):
    """Custom validation logic"""
    if not value:
        return False, "Value required"
    return True, ""

# Use in save_step route
valid, error = validate_custom_setting(data['custom'])
if not valid:
    return jsonify({'error': error}), 400
```

## Integration with Packer

For VM image builds, include wizard installation in Packer provisioner:

```hcl
provisioner "shell" {
  inline = [
    "sudo ./scripts/install-setup-wizard.sh",
    "sudo systemctl enable sting-setup-wizard"
  ]
}
```

## Future Enhancements

- [ ] Cloud-init integration for AWS/Azure/GCP
- [ ] Backup/restore wizard state
- [ ] Advanced network configuration (static IP, DNS)
- [ ] Import existing config.yml
- [ ] Pre-flight system checks (CPU, RAM, disk space)
- [ ] Kubernetes/Docker Swarm deployment mode
- [ ] Multi-language support

## License

Part of STING-CE project. See main project LICENSE.

## Support

For issues with the setup wizard, please open an issue in the STING-CE-VM-Builder repository.
