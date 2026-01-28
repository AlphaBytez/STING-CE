# Quick Start - Testing the Setup Wizard Locally

## Prerequisites

- Python 3.8+
- STING-CE-Fresh source code at `/mnt/c/DevWorld/STING-CE-Fresh` (or adjust `STING_SOURCE`)
- (Optional) Ollama running for LLM endpoint testing

## 1. Install Dependencies

```bash
cd /mnt/c/DevWorld/STING-CE-VM-Builder/web-setup

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt
```

## 2. Set Environment Variable

```bash
# Point to STING source (where config_loader.py lives)
export STING_SOURCE=/mnt/c/DevWorld/STING-CE-Fresh
```

## 3. Run the Wizard

**Note:** In dev mode, the wizard uses `./sting-setup-state/` instead of `/var/lib/sting-setup` (no sudo needed!)

### Option A: Using the helper script

```bash
# Ensure venv is activated and STING_SOURCE is set
source venv/bin/activate
export STING_SOURCE=/mnt/c/DevWorld/STING-CE-Fresh

# Run the helper script (checks everything)
./RUN_LOCAL.sh
```

### Option B: Run directly

```bash
# Make sure you're in web-setup directory
cd /mnt/c/DevWorld/STING-CE-VM-Builder/web-setup

# Activate venv
source venv/bin/activate

# Set STING source
export STING_SOURCE=/mnt/c/DevWorld/STING-CE-Fresh

# Run Flask app
python3 app.py
```

**Output:**
```
 * Serving Flask app 'app'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
 * Running on http://192.168.1.100:8080
```

## 5. Open Browser

Navigate to: **http://localhost:8080**

You should see the STING-CE Setup Wizard!

## 6. Test the Wizard

### Test System Info
- Should auto-populate hostname and timezone
- Should show your current IP address

### Test Disk Detection
- Click "Detect Disks"
- Should show unmounted disks (if any)
- **Don't format** unless you have a test disk!

### Test LLM Endpoint

**With Ollama Running:**
```bash
# In another terminal, start Ollama (if not running)
ollama serve

# In wizard:
# - Enter: http://localhost:11434
# - Click "Test Connection"
# - Should see: ✅ Connected! Found X models
```

**Without Ollama:**
```bash
# In wizard:
# - Enter: http://localhost:11434
# - Click "Test Connection"
# - Should see: ❌ Connection refused - is Ollama running?
```

### Test Config Validation

Complete all steps and click "Next" to reach Review step.

**Wizard will validate configuration with `config_loader.py`:**
- Valid config → Proceed to apply
- Invalid config → Show errors

## 7. Skip Installation (for testing)

**Important:** Don't click "Apply Configuration" unless you want to actually install STING!

The wizard will try to run:
```bash
/opt/sting-ce/install_sting.sh install --non-interactive
```

For testing, just verify the wizard works through step 6 (Review).

## Common Issues

### "config_loader not found"

```bash
# Check STING_SOURCE is set correctly
echo $STING_SOURCE
# Should point to STING-CE-Fresh

# Verify config_loader.py exists
ls $STING_SOURCE/conf/config_loader.py
```

**Fix:**
```bash
export STING_SOURCE=/mnt/c/DevWorld/STING-CE-Fresh
```

### "Permission denied: /var/lib/sting-setup"

```bash
# Create with correct permissions
sudo mkdir -p /var/lib/sting-setup
sudo chown $USER:$USER /var/lib/sting-setup
```

### "Port 8080 already in use"

```bash
# Find what's using port 8080
sudo lsof -i :8080

# Kill the process or edit app.py to use different port
# In app.py, change:
app.run(host='0.0.0.0', port=8090, debug=True)  # Use 8090 instead
```

## Development Mode

### Hot Reload

Flask's debug mode enables auto-reload when you edit files:

```python
# app.py already has:
app.run(host='0.0.0.0', port=8080, debug=True)
```

Just save your changes and Flask will automatically restart!

### Testing API Endpoints

Use `curl` to test endpoints directly:

```bash
# Get system info
curl http://localhost:8080/api/system-info

# Detect disks
curl http://localhost:8080/api/detect-disks

# Test LLM endpoint
curl -X POST http://localhost:8080/api/test-llm \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "http://localhost:11434", "model": "phi3:mini"}'

# Health check
curl http://localhost:8080/health
```

## Testing Config Validation

Create a test config to validate:

```bash
# Create test config
cat > /tmp/test-config.yml <<EOF
system:
  domain: test.local
  protocol: https

llm_service:
  ollama:
    enabled: true
    endpoint: "http://localhost:11434"
    default_model: "phi3:mini"
EOF

# Test validation via Python
python3 << 'PYTHON'
import sys
sys.path.insert(0, '/mnt/c/DevWorld/STING-CE-Fresh/conf')
from config_loader import load_config

try:
    config = load_config('/tmp/test-config.yml')
    print("✅ Config is valid!")
except Exception as e:
    print(f"❌ Config is invalid: {e}")
PYTHON
```

## Next Steps

Once local testing works:

1. **Test on actual VM:**
   ```bash
   # Copy wizard to VM
   scp -r web-setup user@vm-ip:/tmp/

   # SSH to VM and run installer
   ssh user@vm-ip
   sudo /tmp/web-setup/../scripts/install-setup-wizard.sh
   ```

2. **Build VM image with wizard:**
   ```bash
   cd ../packer
   packer build ubuntu-ova.pkr.hcl
   ```

3. **Deploy VM and test end-to-end:**
   - Boot VM
   - Wizard auto-starts
   - Complete setup
   - Verify STING runs

## Debugging Tips

### Enable verbose logging

```python
# In app.py, add at top:
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Check wizard state

```bash
# View saved state
cat /var/lib/sting-setup/setup-state.json

# View draft config
cat /var/lib/sting-setup/config-draft.yml
```

### Reset wizard state

```bash
# Delete state to start over
sudo rm -rf /var/lib/sting-setup/*
```

## Production Deployment

When ready for production:

1. **Disable debug mode:**
   ```python
   # app.py
   app.run(host='0.0.0.0', port=8080, debug=False)
   ```

2. **Use production WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 0.0.0.0:8080 app:app
   ```

3. **Run as systemd service:**
   ```bash
   sudo systemctl enable sting-setup-wizard
   sudo systemctl start sting-setup-wizard
   ```

Happy testing! 🎉
