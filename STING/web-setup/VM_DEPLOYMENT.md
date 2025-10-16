# VM Deployment Guide for STING Setup Wizard

## Overview

The STING Setup Wizard runs **before** STING is installed, so it needs to know where the STING source code is located on the VM.

## Directory Structure on VM

```
/opt/sting-ce-source/          # STING source code (placed during VM build)
├── install_sting.sh           # Installer script
├── conf/
│   └── config_loader.py       # Config validator
├── scripts/
│   └── admin/
│       └── create-new-admin.py
├── web-setup/                 # ⭐ Setup wizard (part of STING repo)
│   ├── app.py
│   ├── templates/
│   │   └── wizard.html
│   ├── static/
│   │   ├── sting-logo.png
│   │   └── sting-logo.webp
│   └── requirements.txt
└── ... (rest of STING source)

/var/lib/sting-setup/          # Wizard state directory
├── setup-state.json           # Wizard progress
├── config.yml                 # Staged config (wizard writes here)
└── install-*.log              # Installation logs

/opt/sting-ce/                 # STING install directory (created by installer)
├── conf/
│   └── config.yml             # Final config (copied from staged)
└── ... (installed STING)
```

**Key Point:** The wizard lives **inside** the STING repository at `web-setup/`, so it can use relative paths to find all STING components!

## VM Build Process (Packer)

### 1. Copy STING Source to VM (includes wizard!)

In your Packer template:

```hcl
provisioner "file" {
  source      = "/path/to/STING-CE-Fresh/"
  destination = "/tmp/sting-source"
}

provisioner "shell" {
  inline = [
    "sudo mkdir -p /opt/sting-ce-source",
    "sudo cp -r /tmp/sting-source/* /opt/sting-ce-source/",
    "sudo chmod +x /opt/sting-ce-source/install_sting.sh",

    # Install wizard dependencies
    "cd /opt/sting-ce-source/web-setup",
    "sudo pip3 install -r requirements.txt"
  ]
}
```

### 2. Configure Wizard Service

```hcl
provisioner "file" {
  source      = "./scripts/sting-setup-wizard.service"
  destination = "/tmp/sting-setup-wizard.service"
}

provisioner "shell" {
  inline = [
    "sudo mv /tmp/sting-setup-wizard.service /etc/systemd/system/",
    "sudo systemctl daemon-reload",
    "sudo systemctl enable sting-setup-wizard"
  ]
}
```

### 3. Systemd Service File

**`/etc/systemd/system/sting-setup-wizard.service`:**

```ini
[Unit]
Description=STING-CE Setup Wizard
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/sting-ce-source/web-setup
Environment="DEV_MODE=false"
# STING_SOURCE auto-detected from script location (parent dir)
ExecStart=/usr/bin/python3 /opt/sting-ce-source/web-setup/app.py
Restart=no

[Install]
WantedBy=multi-user.target
```

**Key Changes:**
- `WorkingDirectory` is now `/opt/sting-ce-source/web-setup`
- No need to set `STING_SOURCE` - auto-detected from script location!
- Wizard auto-discovers STING source as parent directory

## How It Works

### Wizard Startup

1. **User boots VM** → Wizard auto-starts on port 8080
2. **User completes wizard** → Configuration saved to `/var/lib/sting-setup/config.yml`
3. **User clicks "Apply"** → Wizard invokes installer

### Installation Flow

```
Wizard writes config
    ↓
/var/lib/sting-setup/config.yml (staged)
    ↓
Wizard invokes: /opt/sting-ce-source/install_sting.sh install
    ↓
Installer checks for WIZARD_CONFIG_PATH env var
    ↓
Installer copies staged config to /opt/sting-ce/conf/config.yml
    ↓
Installer proceeds with STING installation
    ↓
STING services start with wizard's config
```

## Environment Variables

The wizard uses these environment variables:

### `STING_SOURCE` (Optional - Auto-detected!)
- **Purpose:** Location of STING source code on VM
- **Auto-detection:** Parent directory of wizard script
  - Wizard at: `/opt/sting-ce-source/web-setup/app.py`
  - Auto-detected: `/opt/sting-ce-source/`
- **Override:** Set manually only if wizard is NOT in `web-setup/` subdirectory
- **Used for:**
  - Finding `install_sting.sh`
  - Finding `conf/config_loader.py` for validation
  - Finding `scripts/admin/create-new-admin.py`

**Recommended:** Don't set this - let auto-detection work! ✅

### `DEV_MODE` (Optional)
- **Purpose:** Enable development mode (skips actual installation)
- **Values:** `true` or `false`
- **Default:** `true`
- **Production:** Set to `false` in systemd service

### `WIZARD_CONFIG_PATH` (Auto-set by wizard)
- **Purpose:** Tell installer where to find staged config
- **Value:** `/var/lib/sting-setup/config.yml`
- **Set by:** Wizard passes this to installer subprocess
- **Don't set manually!**

## Installer Integration

The STING installer should check for wizard config:

```bash
# In install_sting.sh
if [ -n "$WIZARD_CONFIG_PATH" ] && [ -f "$WIZARD_CONFIG_PATH" ]; then
    echo "Using wizard-provided configuration..."
    mkdir -p /opt/sting-ce/conf
    cp "$WIZARD_CONFIG_PATH" /opt/sting-ce/conf/config.yml
else
    echo "No wizard config found, using defaults..."
fi
```

## Testing Locally

### Development Mode (DEV_MODE=true)

```bash
cd web-setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

export STING_SOURCE=/mnt/c/DevWorld/STING-CE-Fresh
export DEV_MODE=true

python3 app.py
# Open http://localhost:8080
```

**In dev mode:**
- ✅ Wizard runs and collects config
- ✅ Config validation works (uses config_loader.py)
- ✅ LLM endpoint testing works
- ❌ Installation is **simulated** (doesn't actually install)
- 📄 Config written to `./sting-setup-state/config.yml`

### Production Mode (DEV_MODE=false)

```bash
export STING_SOURCE=/opt/sting-ce-source  # Must exist!
export DEV_MODE=false

python3 app.py
```

**In production mode:**
- ✅ Wizard runs and collects config
- ✅ Installation **actually runs**
- 📄 Config written to `/var/lib/sting-setup/config.yml`
- 🚀 Invokes `/opt/sting-ce-source/install_sting.sh install`

## Troubleshooting

### "Installer not found"

**Error:**
```
FileNotFoundError: Installer not found: /opt/sting-ce-source/install_sting.sh
```

**Fix:**
- Ensure STING source is deployed to VM
- Check `STING_SOURCE` environment variable
- Verify `install_sting.sh` exists and is executable

### "config_loader not available"

**Error:**
```
WARNING: config_loader.py not available - validation disabled
```

**Fix:**
- Ensure `STING_SOURCE` points to STING source code
- Check that `conf/config_loader.py` exists

### Admin creation fails

**Error:**
```
Warning: Could not create admin: [Errno 2] No such file or directory
```

**Fix:**
- Ensure services are running before admin creation
- Check that `scripts/admin/create-new-admin.py` exists
- Verify Kratos and STING containers are healthy

## Summary

**Key Points:**
1. ✅ Wizard is **part of STING repository** at `web-setup/`
2. ✅ Place entire STING source on VM (includes wizard!)
3. ✅ Wizard auto-detects STING source (parent directory)
4. ✅ Wizard writes config to staging location (`/var/lib/sting-setup/config.yml`)
5. ✅ Wizard invokes `../install_sting.sh` (relative path)
6. ✅ Installer copies staged config to install location
7. ✅ Never hardcode `/opt/sting-ce/` paths in wizard (doesn't exist yet!)

**Deployment is Simple:**
```bash
# 1. Copy STING source to VM (includes wizard in web-setup/)
sudo cp -r /path/to/STING-CE-Fresh /opt/sting-ce-source

# 2. Install wizard dependencies
cd /opt/sting-ce-source/web-setup
sudo pip3 install -r requirements.txt

# 3. Enable wizard service
sudo systemctl enable sting-setup-wizard
sudo systemctl start sting-setup-wizard

# 4. Open http://<vm-ip>:8080 and complete setup!
```

**No manual environment configuration needed!** The wizard finds everything via relative paths. 🐝🚀
