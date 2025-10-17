#!/usr/bin/env python3
"""
STING-CE VM Setup Wizard
Flask application for first-run configuration with config_loader.py integration
"""
import os
import sys
import json
import yaml
import subprocess
import shutil
from pathlib import Path
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import generate_password_hash
import requests
from datetime import datetime
import secrets
import threading
import uuid
import time

# Determine paths relative to this script
# Wizard should be located at: <STING-SOURCE>/web-setup/app.py
# So STING source is the parent directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
STING_SOURCE = os.environ.get('STING_SOURCE') or os.path.dirname(SCRIPT_DIR)

# Add STING conf directory to path for config_loader import
sys.path.insert(0, os.path.join(STING_SOURCE, 'conf'))

try:
    from config_loader import load_config, ConfigurationError
    CONFIG_LOADER_AVAILABLE = True
except ImportError:
    CONFIG_LOADER_AVAILABLE = False
    print("WARNING: config_loader.py not available - validation disabled")

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

# Setup paths - use local directory for development
DEV_MODE = os.environ.get('DEV_MODE', 'true').lower() == 'true'
# Use /tmp for production to avoid permission issues (wizard runs as regular user)
SETUP_DIR = './sting-setup-state' if DEV_MODE else '/tmp/sting-setup-state'
SETUP_STATE_FILE = os.path.join(SETUP_DIR, 'setup-state.json')
CONFIG_DRAFT_FILE = os.path.join(SETUP_DIR, 'config-draft.yml')

# In production, the wizard writes config to staging location
# The installer will copy it to final location: /opt/sting-ce/conf/config.yml
STAGED_CONFIG_PATH = os.path.join(SETUP_DIR, 'config.yml')

# Installer script location (from STING source, not install directory)
INSTALLER_SCRIPT = os.path.join(STING_SOURCE, 'install_sting.sh')

# Global dict to track ongoing installations
installations = {}

def get_install_directory():
    """
    Get the STING installation directory based on platform and environment.
    Uses same logic as installation.sh to ensure consistency.
    """
    # Check if INSTALL_DIR is set in environment
    if 'INSTALL_DIR' in os.environ:
        return os.environ['INSTALL_DIR']

    # Platform-specific defaults (matches installation.sh logic)
    import platform as plat
    if plat.system() == 'Darwin':  # macOS
        return os.path.join(os.path.expanduser('~'), '.sting-ce')
    else:  # Linux and others
        return '/opt/sting-ce'

def ensure_setup_dir():
    """Create setup state directory"""
    os.makedirs(SETUP_DIR, exist_ok=True)

def load_setup_state():
    """Load wizard progress state"""
    ensure_setup_dir()
    if os.path.exists(SETUP_STATE_FILE):
        with open(SETUP_STATE_FILE, 'r') as f:
            return json.load(f)
    return {
        'current_step': 1,
        'completed_steps': [],
        'config_data': {}
    }

def save_setup_state(state):
    """Save wizard progress state"""
    ensure_setup_dir()
    with open(SETUP_STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)

def test_llm_endpoint(endpoint_url, model_name=None):
    """
    Test LLM endpoint connectivity and model availability
    Supports both Ollama and OpenAI-compatible endpoints (LM Studio, vLLM, etc.)
    Returns: (success: bool, message: str, models: list)
    """
    try:
        # Try OpenAI-compatible endpoint first (LM Studio, vLLM, etc.)
        response = requests.get(f"{endpoint_url}/v1/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m['id'] for m in data.get('data', [])]

            if model_name and model_name not in models:
                return False, f"Model '{model_name}' not found. Available: {', '.join(models[:5])}", models

            return True, f"Connected successfully (OpenAI-compatible). Found {len(models)} models.", models
    except:
        pass  # Try Ollama endpoint next

    try:
        # Try Ollama API tags endpoint
        response = requests.get(f"{endpoint_url}/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m['name'] for m in data.get('models', [])]

            if model_name and model_name not in models:
                return False, f"Model '{model_name}' not found. Available: {', '.join(models)}", models

            return True, f"Connected successfully (Ollama). Found {len(models)} models.", models
    except requests.exceptions.Timeout:
        return False, "Connection timeout - endpoint not responding", []
    except requests.exceptions.ConnectionError:
        return False, "Connection refused - is the LLM service running?", []
    except Exception as e:
        return False, f"Error: {str(e)}", []

def validate_config_with_loader(config_data):
    """
    Validate configuration using config_loader.py
    Returns: (valid: bool, errors: list)
    """
    if not CONFIG_LOADER_AVAILABLE:
        return True, []  # Skip validation if loader not available

    try:
        # Write temporary config file
        ensure_setup_dir()
        with open(CONFIG_DRAFT_FILE, 'w') as f:
            yaml.dump(config_data, f)

        # Try to load with config_loader
        loaded_config = load_config(CONFIG_DRAFT_FILE)

        # If we get here, config is valid
        return True, []
    except ConfigurationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Validation error: {str(e)}"]

def detect_disks():
    """
    Detect available unmounted disks for data storage
    Returns: list of disk info dicts
    """
    try:
        # Run lsblk to find unmounted disks
        result = subprocess.run(
            ['lsblk', '-J', '-o', 'NAME,SIZE,TYPE,MOUNTPOINT'],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return []

        data = json.loads(result.stdout)
        disks = []

        for device in data.get('blockdevices', []):
            if device.get('type') == 'disk':
                # Check for unmounted partitions
                for child in device.get('children', []):
                    if not child.get('mountpoint'):
                        disks.append({
                            'device': f"/dev/{child['name']}",
                            'size': child['size'],
                            'name': child['name']
                        })

        return disks
    except Exception as e:
        print(f"Error detecting disks: {e}")
        return []

def is_safe_to_format(device):
    """
    Check if device is safe to format (not system/boot/mounted disk)
    Returns: (safe: bool, reason: str)
    """
    import re

    # Validate device path format
    if not re.match(r'^/dev/[a-z]+[0-9]+$', device):
        return False, "Invalid device path format"

    # Check if device exists
    if not os.path.exists(device):
        return False, f"Device {device} does not exist"

    # Get list of safe unmounted disks
    safe_disks = detect_disks()
    safe_devices = [d['device'] for d in safe_disks]

    if device not in safe_devices:
        return False, f"Device {device} is not in the list of safe unmounted disks"

    # Check if currently mounted (race condition protection)
    try:
        mount_check = subprocess.run(
            ['findmnt', '-n', '-o', 'TARGET', device],
            capture_output=True,
            text=True
        )
        if mount_check.returncode == 0 and mount_check.stdout.strip():
            return False, f"Device {device} is currently mounted at {mount_check.stdout.strip()}"
    except:
        pass

    # Check if it's a system partition (root, boot, swap)
    try:
        # Get all critical mount points
        lsblk_result = subprocess.run(
            ['lsblk', '-n', '-o', 'NAME,MOUNTPOINT', device],
            capture_output=True,
            text=True
        )

        if lsblk_result.returncode == 0:
            output = lsblk_result.stdout
            critical_mounts = ['/', '/boot', '/boot/efi', '[SWAP]', '/home', '/usr', '/var']

            for mount in critical_mounts:
                if mount in output:
                    return False, f"Device {device} contains critical mount point: {mount}"
    except:
        pass

    # Check if device is part of root disk
    try:
        # Get the root device
        root_result = subprocess.run(
            ['findmnt', '-n', '-o', 'SOURCE', '/'],
            capture_output=True,
            text=True
        )

        if root_result.returncode == 0:
            root_device = root_result.stdout.strip()
            # Extract base device (e.g., /dev/sda1 -> /dev/sda)
            device_base = re.sub(r'[0-9]+$', '', device)
            root_base = re.sub(r'[0-9]+$', '', root_device)

            if device_base == root_base:
                return False, f"Device {device} is on the same disk as root filesystem ({root_device})"
    except:
        pass

    return True, "Device is safe to format"


def format_and_mount_disk(device, mount_point='/data'):
    """
    Format disk as ext4 and mount it (WITH SAFETY CHECKS)
    Returns: (success: bool, message: str)
    """
    try:
        # CRITICAL: Validate device is safe to format
        is_safe, reason = is_safe_to_format(device)
        if not is_safe:
            return False, f"⛔ SAFETY CHECK FAILED: {reason}"

        # Format as ext4
        result = subprocess.run(
            ['mkfs.ext4', '-F', device],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Format failed: {result.stderr}"

        # Create mount point
        os.makedirs(mount_point, exist_ok=True)

        # Mount
        result = subprocess.run(
            ['mount', device, mount_point],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Mount failed: {result.stderr}"

        # Add to /etc/fstab for persistence
        uuid_result = subprocess.run(
            ['blkid', '-s', 'UUID', '-o', 'value', device],
            capture_output=True,
            text=True
        )
        if uuid_result.returncode == 0:
            uuid = uuid_result.stdout.strip()
            with open('/etc/fstab', 'a') as f:
                f.write(f"UUID={uuid} {mount_point} ext4 defaults 0 2\n")

        return True, f"✓ Disk {device} formatted and mounted at {mount_point}"
    except Exception as e:
        return False, f"Error: {str(e)}"

# ============================================================================
# ROUTES - Wizard Pages
# ============================================================================

@app.route('/')
def index():
    """Main wizard page"""
    state = load_setup_state()
    return render_template('wizard.html', state=state)

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current wizard state"""
    state = load_setup_state()
    state['dev_mode'] = DEV_MODE  # Add dev mode flag to state
    return jsonify(state)

@app.route('/api/system-info', methods=['GET'])
def get_system_info():
    """Get system information for pre-population"""
    try:
        hostname = subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
        timezone = subprocess.run(['timedatectl', 'show', '-p', 'Timezone', '--value'],
                                 capture_output=True, text=True).stdout.strip()

        return jsonify({
            'hostname': hostname or 'sting-ce',
            'timezone': timezone or 'UTC',
            'ip_address': get_primary_ip()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/detect-disks', methods=['GET'])
def api_detect_disks():
    """API endpoint to detect available disks"""
    disks = detect_disks()
    return jsonify({'disks': disks})

@app.route('/api/test-llm', methods=['POST'])
def api_test_llm():
    """Test LLM endpoint connectivity"""
    data = request.json
    endpoint = data.get('endpoint')
    model = data.get('model')

    if not endpoint:
        return jsonify({'success': False, 'message': 'Endpoint required'}), 400

    success, message, models = test_llm_endpoint(endpoint, model)
    return jsonify({
        'success': success,
        'message': message,
        'models': models
    })

@app.route('/api/save-step', methods=['POST'])
def save_step():
    """Save data from a wizard step"""
    data = request.json
    step_num = data.get('step')
    step_data = data.get('data')

    state = load_setup_state()

    # Update config data
    state['config_data'].update(step_data)

    # Mark step as completed
    if step_num not in state['completed_steps']:
        state['completed_steps'].append(step_num)

    # Move to next step
    if step_num == state['current_step']:
        state['current_step'] = step_num + 1

    save_setup_state(state)

    return jsonify({'success': True, 'state': state})

@app.route('/api/format-disk', methods=['POST'])
def api_format_disk():
    """Format and mount data disk"""
    data = request.json
    device = data.get('device')

    if not device:
        return jsonify({'success': False, 'message': 'Device required'}), 400

    success, message = format_and_mount_disk(device)
    return jsonify({'success': success, 'message': message})

@app.route('/api/validate-config', methods=['POST'])
def validate_config():
    """Validate configuration using config_loader.py"""
    data = request.json
    config_data = data.get('config')

    valid, errors = validate_config_with_loader(config_data)

    return jsonify({
        'valid': valid,
        'errors': errors
    })

def transform_wizard_data_to_config(wizard_data):
    """
    Transform wizard data structure to config.yml format

    Wizard uses flat structure: wizard_data.llm.endpoint
    Config.yml uses nested: config.llm_service.ollama.endpoint

    This ensures wizard-tested configuration is actually used!
    """
    # Load default config.yml as base
    default_config_path = os.path.join(STING_SOURCE, 'conf', 'config.yml')

    with open(default_config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Transform LLM configuration
    if 'llm' in wizard_data:
        llm_data = wizard_data['llm']
        config['llm_service']['ollama']['endpoint'] = llm_data.get('endpoint', 'http://localhost:11434')
        config['llm_service']['ollama']['default_model'] = llm_data.get('model', 'phi3:mini')
        config['llm_service']['ollama']['enabled'] = True

        # Also update external_ai endpoint (uses same Ollama endpoint)
        config['llm_service']['external_ai']['ollama_endpoint'] = llm_data.get('endpoint', 'http://localhost:11434')

    # Transform admin configuration
    if 'admin' in wizard_data:
        admin_data = wizard_data['admin']
        # Admin config is handled separately via create-new-admin.py
        # Just store for reference
        config.setdefault('_wizard_metadata', {})['admin_email'] = admin_data.get('email', 'admin@sting.local')

    # Transform email configuration
    if 'email' in wizard_data:
        email_data = wizard_data['email']
        if 'mail' not in config:
            config['mail'] = {}
        config['mail']['enabled'] = True
        config['mail']['smtp_host'] = email_data.get('host', '')
        config['mail']['smtp_port'] = int(email_data.get('port', 587))
        config['mail']['smtp_user'] = email_data.get('username', '')
        config['mail']['smtp_password'] = email_data.get('password', '')

    # Transform SSL configuration
    if 'ssl' in wizard_data:
        ssl_data = wizard_data['ssl']
        # SSL cert paths are set during installation
        config.setdefault('_wizard_metadata', {})['ssl_enabled'] = ssl_data.get('enabled', False)

    # Transform data disk configuration
    if 'data_disk' in wizard_data:
        disk_data = wizard_data['data_disk']
        config.setdefault('_wizard_metadata', {})['data_disk_mount'] = disk_data.get('mount_point', '/data')

    return config

def run_installation_background(install_id, config_data, admin_email):
    """Run installation in background thread with logging"""
    install_log_file = os.path.join(SETUP_DIR, f'install-{install_id}.log')

    try:
        installations[install_id]['status'] = 'Preparing configuration...'
        installations[install_id]['progress'] = 10

        # 1. Transform wizard data to config.yml format
        # CRITICAL: Wizard uses flat structure, config.yml uses nested structure
        # This ensures wizard-tested configuration (like LLM endpoint) is actually used!
        transformed_config = transform_wizard_data_to_config(config_data)

        # 2. Write config.yml to staging location
        # Installer will copy this to /opt/sting-ce/conf/config.yml
        os.makedirs(SETUP_DIR, exist_ok=True)
        with open(STAGED_CONFIG_PATH, 'w') as f:
            yaml.dump(transformed_config, f, default_flow_style=False, sort_keys=False)

        installations[install_id]['log'] = f"✅ Configuration transformed and saved to: {STAGED_CONFIG_PATH}\n"
        installations[install_id]['log'] += f"🤖 LLM endpoint: {config_data.get('llm', {}).get('endpoint', 'N/A')}\n"
        installations[install_id]['log'] += f"🤖 LLM model: {config_data.get('llm', {}).get('model', 'N/A')}\n\n"

        # 2. Dev mode - simulate installation without running actual installer
        if DEV_MODE:
            installations[install_id]['log'] += "\n" + "="*60 + "\n"
            installations[install_id]['log'] += "DEV MODE - Simulated Installation\n"
            installations[install_id]['log'] += "="*60 + "\n\n"
            installations[install_id]['log'] += "✅ Configuration validated and saved\n"
            installations[install_id]['log'] += f"📄 Config file: {STAGED_CONFIG_PATH}\n"
            installations[install_id]['log'] += f"👤 Admin email: {admin_email}\n"
            installations[install_id]['log'] += f"🤖 LLM endpoint: {config_data.get('llm', {}).get('endpoint', 'N/A')}\n"
            installations[install_id]['log'] += f"🤖 LLM model: {config_data.get('llm', {}).get('model', 'N/A')}\n\n"
            installations[install_id]['log'] += "="*60 + "\n"
            installations[install_id]['log'] += "To install STING in production:\n"
            installations[install_id]['log'] += "="*60 + "\n\n"
            installations[install_id]['log'] += "1. Deploy STING source code to VM (e.g., /opt/sting-ce-source/)\n"
            installations[install_id]['log'] += "2. Deploy this wizard to the VM\n"
            installations[install_id]['log'] += "3. Set STING_SOURCE environment variable to source location\n"
            installations[install_id]['log'] += "4. Run wizard with DEV_MODE=false\n"
            installations[install_id]['log'] += "5. Wizard will automatically invoke installer\n\n"
            installations[install_id]['log'] += "OR manually install with:\n"
            installations[install_id]['log'] += f"   export WIZARD_CONFIG_PATH={STAGED_CONFIG_PATH}\n"
            installations[install_id]['log'] += f"   sudo {INSTALLER_SCRIPT} install\n\n"

            installations[install_id]['status'] = 'Dev mode - installation skipped'
            installations[install_id]['progress'] = 100
            installations[install_id]['completed'] = True
            installations[install_id]['success'] = True
            installations[install_id]['redirect_url'] = None
            installations[install_id]['admin_email'] = admin_email
            return

        installations[install_id]['status'] = 'Starting STING installation...'
        installations[install_id]['progress'] = 20

        # 3. Production mode - Run actual STING installation with logging
        if not os.path.exists(INSTALLER_SCRIPT):
            raise FileNotFoundError(
                f"Installer not found: {INSTALLER_SCRIPT}\n"
                f"STING_SOURCE should point to STING source code location.\n"
                f"Current STING_SOURCE: {STING_SOURCE}"
            )

        # Pre-acquire sudo privileges before installation
        # This prevents sudo password prompts during installation
        # (web UI can't handle interactive sudo prompts)
        try:
            installations[install_id]['status'] = 'Acquiring sudo privileges...'
            subprocess.run(['sudo', '-v'], check=True, capture_output=True)
            installations[install_id]['log'] += "✅ Sudo privileges acquired\n"
        except subprocess.CalledProcessError:
            raise RuntimeError(
                "Failed to acquire sudo privileges.\n"
                "The STING installer requires sudo access.\n"
                "Please run the wizard with: sudo python3 app.py\n"
                "Or use CLI installation instead: ./install_sting.sh --cli"
            )

        # Check for existing/partial installation and clean up automatically
        installations[install_id]['status'] = 'Checking for existing installation...'

        # Get platform-specific installation directory
        install_dir = get_install_directory()

        # Check INSTALL directory (platform-aware), NOT source directory
        has_install_dir = os.path.exists(os.path.join(install_dir, 'docker-compose.yml'))

        container_check = subprocess.run(
            ['docker', 'ps', '-a', '--filter', 'name=sting-ce', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        has_containers = 'sting-ce' in container_check.stdout

        volume_check = subprocess.run(
            ['docker', 'volume', 'ls', '--filter', 'name=sting', '--format', '{{.Name}}'],
            capture_output=True, text=True
        )
        has_volumes = 'sting' in volume_check.stdout

        # Also clean up stale wizard temp files from previous failed installations
        if os.path.exists(SETUP_DIR) and not DEV_MODE:
            installations[install_id]['log'] += "Cleaning up stale wizard temporary files...\n"
            try:
                import shutil
                shutil.rmtree(SETUP_DIR)
                os.makedirs(SETUP_DIR, exist_ok=True)
            except Exception as e:
                installations[install_id]['log'] += f"Warning: Could not clean temp dir: {e}\n"

        if has_install_dir or has_containers or has_volumes:
            installations[install_id]['log'] += "\n⚠️ EXISTING INSTALLATION DETECTED\n"
            if has_install_dir:
                installations[install_id]['log'] += f"  • Installation directory exists: {install_dir}\n"
            if has_containers:
                container_count = len(container_check.stdout.strip().split('\n'))
                installations[install_id]['log'] += f"  • Found {container_count} STING container(s)\n"
            if has_volumes:
                volume_count = len(volume_check.stdout.strip().split('\n'))
                installations[install_id]['log'] += f"  • Found {volume_count} STING volume(s)\n"

            installations[install_id]['log'] += "\nAutomatically cleaning up existing installation...\n"

            # Run uninstall --purge with sudo (required for cleanup)
            uninstall_script = os.path.join(STING_SOURCE, 'manage_sting.sh')

            # Check if script exists
            if not os.path.exists(uninstall_script):
                raise RuntimeError(
                    f"Cleanup script not found: {uninstall_script}\n"
                    f"Cannot automatically clean up existing installation.\n"
                    f"Please manually run: ./manage_sting.sh uninstall --purge"
                )

            uninstall_result = subprocess.run(
                ['sudo', 'bash', uninstall_script, 'uninstall', '--purge'],
                capture_output=True, text=True, timeout=120
            )

            if uninstall_result.returncode == 0:
                installations[install_id]['log'] += "✅ Cleanup successful! Continuing with fresh installation...\n\n"
            else:
                error_output = uninstall_result.stderr or uninstall_result.stdout or "No error output"
                installations[install_id]['log'] += f"Cleanup failed with exit code {uninstall_result.returncode}\n"
                installations[install_id]['log'] += f"Output: {error_output}\n"
                raise RuntimeError(
                    f"Failed to clean up existing installation.\n"
                    f"Error: {error_output}\n"
                    f"Please manually run: sudo ./manage_sting.sh uninstall --purge"
                )

        # Kill any stale installation processes and sudo keepalives before starting new one
        try:
            # Kill stale installation processes
            stale_check = subprocess.run(
                ['pgrep', '-f', 'install_sting.sh install'],
                capture_output=True,
                text=True
            )
            if stale_check.returncode == 0 and stale_check.stdout.strip():
                stale_pids = stale_check.stdout.strip().split('\n')
                installations[install_id]['log'] += f"⚠️ Found {len(stale_pids)} stale installation process(es)\n"
                installations[install_id]['log'] += "Cleaning up stale processes...\n"
                subprocess.run(['sudo', 'kill', '-9'] + stale_pids, check=False)
                installations[install_id]['log'] += "✅ Stale processes cleaned up\n"

            # Kill any stale sudo keepalive processes from previous installations
            installations[install_id]['log'] += "Cleaning up any stale sudo keepalive processes...\n"
            subprocess.run(['pkill', '-f', 'while true; do sudo -v; sleep'], check=False)
        except Exception as e:
            # Non-fatal - continue with installation
            print(f"Warning: Could not check for stale processes: {e}")

        # Start sudo keepalive process in background
        # This refreshes sudo session every 50 seconds during installation
        sudo_keepalive = subprocess.Popen(
            ['bash', '-c', 'while true; do sudo -v; sleep 50; done'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        try:
            # Set environment variable so installer knows where to find staged config
            env = os.environ.copy()
            env['WIZARD_CONFIG_PATH'] = STAGED_CONFIG_PATH

            with open(install_log_file, 'w') as log_file:
                process = subprocess.Popen(
                    [INSTALLER_SCRIPT, 'install'],
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env
                )

            # Monitor installation progress
            while process.poll() is None:
                time.sleep(2)
                # Read log file to update progress
                try:
                    with open(install_log_file, 'r') as f:
                        log_content = f.read()
                        installations[install_id]['log'] = log_content

                        # Simple progress estimation based on log content
                        if 'docker' in log_content.lower():
                            installations[install_id]['progress'] = 40
                            installations[install_id]['status'] = 'Installing Docker services...'
                        if 'building' in log_content.lower():
                            installations[install_id]['progress'] = 60
                            installations[install_id]['status'] = 'Building containers...'
                        if 'starting' in log_content.lower():
                            installations[install_id]['progress'] = 80
                            installations[install_id]['status'] = 'Starting services...'
                except Exception as e:
                    print(f"Error reading log: {e}")

            returncode = process.wait()

            # Read final log
            with open(install_log_file, 'r') as f:
                final_log = f.read()
                installations[install_id]['log'] = final_log

            # Check if installation actually succeeded despite non-zero exit
            # (e.g., permission warnings that are non-fatal)
            installation_succeeded = 'STING installation completed successfully' in final_log

            if returncode != 0 and not installation_succeeded:
                installations[install_id]['completed'] = True
                installations[install_id]['success'] = False
                installations[install_id]['error'] = 'Installation script failed'
                return
            elif returncode != 0 and installation_succeeded:
                # Installation succeeded but with warnings
                installations[install_id]['log'] += '\n\n⚠️  Installation completed with warnings (non-fatal)\n'

            installations[install_id]['status'] = 'Creating admin account...'
            installations[install_id]['progress'] = 90

            # 3. Wait for services to be ready (up to 60 seconds)
            time.sleep(10)  # Give services time to start

            # 4. Create admin account using create-new-admin.py
            # Use INSTALL_DIR not STING_SOURCE (files are now in /opt/sting-ce after rsync)
            install_dir = get_install_directory()
            admin_script = os.path.join(install_dir, 'scripts/admin/create-new-admin.py')
            if os.path.exists(admin_script) and admin_email:
                try:
                    admin_result = subprocess.run(
                        ['python3', admin_script, '--email', admin_email, '--passwordless'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    installations[install_id]['log'] += f"\n\n{'='*50}\n"
                    installations[install_id]['log'] += "Creating Admin Account\n"
                    installations[install_id]['log'] += f"{'='*50}\n\n"
                    installations[install_id]['log'] += admin_result.stdout

                    if admin_result.returncode != 0:
                        installations[install_id]['log'] += f"\n\nWarning: Admin creation failed: {admin_result.stderr}"
                        installations[install_id]['log'] += f"\nYou can create admin manually: ./manage_sting.sh create admin {admin_email}"
                except Exception as e:
                    installations[install_id]['log'] += f"\n\nWarning: Could not create admin: {str(e)}"
                    installations[install_id]['log'] += f"\nYou can create admin manually: ./manage_sting.sh create admin {admin_email}"

            # 5. Mark setup as complete
            state = load_setup_state()
            state['setup_complete'] = True
            state['setup_date'] = datetime.now().isoformat()
            save_setup_state(state)

            # 6. Disable and stop this setup wizard service (production only)
            if not DEV_MODE:
                # Disable prevents autostart on reboot
                subprocess.run(['sudo', 'systemctl', 'disable', 'sting-setup-wizard'], check=False)
                # Stop kills the running service
                subprocess.run(['sudo', 'systemctl', 'stop', 'sting-setup-wizard'], check=False)
                installations[install_id]['log'] += "\n✓ Setup wizard service disabled and stopped\n"

            installations[install_id]['completed'] = True
            installations[install_id]['success'] = True
            installations[install_id]['progress'] = 100
            installations[install_id]['status'] = 'Installation complete!'
            # Always set redirect URL even if admin creation failed
            # Use detected host IP for VMs/remote access, fallback to localhost
            host_ip = os.environ.get('STING_HOST_IP', 'localhost')
            installations[install_id]['redirect_url'] = f'https://{host_ip}:8443'
            installations[install_id]['admin_email'] = admin_email if admin_email else ''

        finally:
            # Cleanup: Kill installation process if still running
            try:
                if process.poll() is None:  # Process still running
                    installations[install_id]['log'] += "\n⚠️ Terminating installation process...\n"
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            except Exception as e:
                print(f"Error terminating installation process: {e}")

            # Cleanup: Kill sudo keepalive process
            try:
                sudo_keepalive.terminate()
                sudo_keepalive.wait(timeout=5)
            except:
                sudo_keepalive.kill()

    except Exception as e:
        installations[install_id]['completed'] = True
        installations[install_id]['success'] = False
        installations[install_id]['error'] = str(e)
        installations[install_id]['log'] += f"\n\nFatal error: {str(e)}"

@app.route('/api/apply-config', methods=['POST'])
def apply_config():
    """
    Apply final configuration and start STING services
    Runs installation in background and returns install_id for log streaming
    """
    state = load_setup_state()
    config_data = state['config_data']

    # Get admin email, default to admin@sting.local if not provided or empty
    admin_email = config_data.get('admin', {}).get('email', '').strip()
    if not admin_email:
        admin_email = 'admin@sting.local'

    # Final validation
    valid, errors = validate_config_with_loader(config_data)
    if not valid:
        return jsonify({'success': False, 'errors': errors}), 400

    # Generate install ID
    install_id = str(uuid.uuid4())

    # Initialize installation tracking
    installations[install_id] = {
        'status': 'Initializing...',
        'progress': 0,
        'log': '',
        'completed': False,
        'success': False,
        'admin_email': admin_email
    }

    # Start installation in background thread
    thread = threading.Thread(
        target=run_installation_background,
        args=(install_id, config_data, admin_email)
    )
    thread.daemon = True
    thread.start()

    return jsonify({
        'install_id': install_id,
        'message': 'Installation started'
    })

@app.route('/api/install-log/<install_id>', methods=['GET'])
def get_install_log(install_id):
    """Stream installation logs for given install_id"""
    if install_id not in installations:
        return jsonify({'error': 'Installation not found'}), 404

    install_data = installations[install_id]

    return jsonify({
        'log': install_data.get('log', ''),
        'status': install_data.get('status', 'Unknown'),
        'progress': install_data.get('progress', 0),
        'completed': install_data.get('completed', False),
        'success': install_data.get('success', False),
        'error': install_data.get('error'),
        'redirect_url': install_data.get('redirect_url'),
        'admin_email': install_data.get('admin_email')
    })

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'sting-setup-wizard'})

def get_primary_ip():
    """Get primary IP address"""
    try:
        result = subprocess.run(
            ['hostname', '-I'],
            capture_output=True,
            text=True
        )
        ips = result.stdout.strip().split()
        return ips[0] if ips else '127.0.0.1'
    except:
        return '127.0.0.1'

if __name__ == '__main__':
    ensure_setup_dir()
    # Get port from environment or default to 8335 (BEES!)
    wizard_port = int(os.environ.get('WIZARD_PORT', 8335))
    app.run(host='0.0.0.0', port=wizard_port, debug=True)
