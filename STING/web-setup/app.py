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

# Installation timeout configuration
# Prevents runaway installations from consuming resources indefinitely
# 45 minutes should be sufficient for most hardware (can be adjusted via environment variable)
INSTALLATION_TIMEOUT = int(os.environ.get('INSTALLATION_TIMEOUT', '2700'))  # Default: 45 minutes (2700 seconds)

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
    Uses OpenAI-compatible API (works with Ollama, LM Studio, vLLM, etc.)
    Returns: (success: bool, message: str, models: list)
    """
    try:
        # Use OpenAI-compatible API standard (supported by all major LLM servers)
        response = requests.get(f"{endpoint_url}/v1/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = [m['id'] for m in data.get('data', [])]

            if not models:
                return False, "Endpoint reachable but no models found", []

            # If specific model provided, check if it exists
            if model_name and model_name not in models:
                return False, f"Model '{model_name}' not found. Available: {', '.join(models[:5])}", models

            return True, f"Connected successfully. Found {len(models)} model(s).", models
        else:
            return False, f"LLM service returned status {response.status_code}", []

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

        # Try to load with config_loader (validation only)
        _ = load_config(CONFIG_DRAFT_FILE)

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

        # Format as ext4 (requires sudo)
        result = subprocess.run(
            ['sudo', '-n', 'mkfs.ext4', '-F', device],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Format failed: {result.stderr}"

        # Create mount point (requires sudo)
        result = subprocess.run(
            ['sudo', '-n', 'mkdir', '-p', mount_point],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Failed to create mount point: {result.stderr}"

        # Mount (requires sudo)
        result = subprocess.run(
            ['sudo', '-n', 'mount', device, mount_point],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            return False, f"Mount failed: {result.stderr}"

        # Add to /etc/fstab for persistence (requires sudo)
        uuid_result = subprocess.run(
            ['sudo', '-n', 'blkid', '-s', 'UUID', '-o', 'value', device],
            capture_output=True,
            text=True
        )
        if uuid_result.returncode == 0:
            uuid = uuid_result.stdout.strip()
            # Use sudo tee to append to /etc/fstab
            fstab_entry = f"UUID={uuid} {mount_point} ext4 defaults 0 2\n"
            subprocess.run(
                ['sudo', '-n', 'tee', '-a', '/etc/fstab'],
                input=fstab_entry,
                capture_output=True,
                text=True
            )

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

    # Read version from VERSION file
    version = 'unknown'
    version_file = os.path.join(STING_SOURCE, 'VERSION')
    if os.path.exists(version_file):
        try:
            with open(version_file, 'r') as f:
                version = f.read().strip()
        except Exception:
            pass

    return render_template('wizard.html', state=state, version=version)

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get current wizard state"""
    state = load_setup_state()
    state['dev_mode'] = DEV_MODE  # Add dev mode flag to state
    return jsonify(state)

def detect_sting_hostname():
    """
    Detect appropriate STING hostname for WebAuthn/Passkey compatibility

    CRITICAL: For WebAuthn to work, the hostname must match the Kratos RP ID.
    Strategy:
    - VMs with mDNS/Avahi: Prefer hostname.local (easier for remote access, better UX)
    - Other environments: Use IP address as reliable fallback
    """
    import re

    def is_vm():
        """Check if running in a virtual machine"""
        try:
            # Check systemd-detect-virt
            result = subprocess.run(['systemd-detect-virt'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if result.returncode == 0:
                virt_type = result.stdout.strip()
                if virt_type and virt_type != 'none':
                    return True
        except:
            pass

        # Check DMI product name
        try:
            with open('/sys/class/dmi/id/product_name', 'r') as f:
                product = f.read().strip().lower()
                if any(vm in product for vm in ['vmware', 'virtualbox', 'kvm', 'qemu', 'parallels', 'xen']):
                    return True
        except:
            pass

        return False

    def has_mdns():
        """Check if mDNS/Avahi is available"""
        try:
            # Check for Avahi daemon
            result = subprocess.run(['systemctl', 'is-active', 'avahi-daemon'],
                                  stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if result.returncode == 0:
                return True
        except:
            pass

        # Check for macOS Bonjour (always present)
        try:
            result = subprocess.run(['uname'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
            if result.stdout.strip() == 'Darwin':
                return True
        except:
            pass

        return False

    # Strategy 1: For VMs with mDNS, prefer hostname.local (best UX for remote access)
    if is_vm() and has_mdns():
        try:
            short_hostname = subprocess.run(['hostname', '-s'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip().lower()
            if short_hostname and short_hostname != 'localhost':
                # Append .local for mDNS/local network resolution
                return f"{short_hostname}.local"
        except:
            pass

    # Strategy 2: Use primary IP address (reliable fallback)
    try:
        # Try Linux: hostname -I
        result = subprocess.run(['hostname', '-I'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode == 0:
            ips = result.stdout.strip().split()
            if ips:
                primary_ip = ips[0]
                # Validate it's a real IP (not loopback)
                if primary_ip and not primary_ip.startswith('127.') and re.match(r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', primary_ip):
                    return primary_ip
    except:
        pass

    # Strategy 3: Try macOS: ifconfig (since hostname -I doesn't exist on macOS)
    try:
        result = subprocess.run(['ifconfig'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        if result.returncode == 0:
            # Parse ifconfig output for first non-loopback IP
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        ip = parts[1]
                        # Validate it's a real IP (not loopback)
                        if re.match(r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', ip) and not ip.startswith('127.'):
                            return ip
    except:
        pass

    # Strategy 4: Try FQDN as fallback (but filter out .localdomain which is just a placeholder)
    try:
        fqdn = subprocess.run(['hostname', '-f'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()
        if fqdn and '.' in fqdn:
            # Filter out fake/placeholder domains
            if fqdn not in ['localhost', 'localhost.localdomain'] and not fqdn.endswith('.localdomain'):
                # Valid real FQDN
                return fqdn.lower()
    except:
        pass

    # Strategy 5: Try short hostname with .local suffix (requires mDNS)
    try:
        short_hostname = subprocess.run(['hostname', '-s'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip().lower()
        if short_hostname and short_hostname != 'localhost':
            # Append .local for mDNS/local network resolution
            return f"{short_hostname}.local"
    except:
        pass

    # Final fallback: Use localhost
    return 'localhost'

@app.route('/api/system-info', methods=['GET'])
def get_system_info():
    """Get system information for pre-population"""
    try:
        hostname = subprocess.run(['hostname'], capture_output=True, text=True).stdout.strip()
        timezone = subprocess.run(['timedatectl', 'show', '-p', 'Timezone', '--value'],
                                 capture_output=True, text=True).stdout.strip()

        # Get STING hostname with WebAuthn-compatible detection
        sting_hostname = detect_sting_hostname()

        return jsonify({
            'hostname': hostname or 'sting-ce',  # System hostname (for reference)
            'sting_hostname': sting_hostname,     # STING hostname for WebAuthn (the important one)
            'timezone': timezone or 'UTC',
            'ip_address': get_primary_ip()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/hostname-options', methods=['GET'])
def get_hostname_options():
    """Get hostname configuration options with context (like CLI installer)"""
    try:
        import re

        # Reuse helper functions from detect_sting_hostname
        def is_vm():
            """Check if running in a virtual machine"""
            try:
                result = subprocess.run(['systemd-detect-virt'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if result.returncode == 0:
                    virt_type = result.stdout.strip()
                    if virt_type and virt_type != 'none':
                        return True
            except:
                pass

            try:
                with open('/sys/class/dmi/id/product_name', 'r') as f:
                    product = f.read().strip().lower()
                    if any(vm in product for vm in ['vmware', 'virtualbox', 'kvm', 'qemu', 'parallels', 'xen']):
                        return True
            except:
                pass

            return False

        def has_mdns():
            """Check if mDNS/Avahi is available"""
            try:
                result = subprocess.run(['systemctl', 'is-active', 'avahi-daemon'],
                                      stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if result.returncode == 0:
                    return True
            except:
                pass

            try:
                result = subprocess.run(['uname'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                if result.stdout.strip() == 'Darwin':
                    return True
            except:
                pass

            return False

        # Detect platform and capabilities
        platform = 'vm' if is_vm() else 'bare-metal'
        mdns_available = has_mdns()

        # Get detected hostname
        detected_hostname = detect_sting_hostname()

        # Get short hostname for .local option
        short_hostname = None
        try:
            short_hostname = subprocess.run(['hostname', '-s'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip().lower()
            if short_hostname == 'localhost' or not short_hostname:
                short_hostname = None
        except:
            pass

        # Get primary IP
        primary_ip = get_primary_ip()

        # Build options list (similar to CLI)
        options = []

        # Option 1: sting.local (generic .local hostname)
        options.append({
            'value': 'sting.local',
            'label': 'sting.local',
            'description': 'Generic STING hostname',
            'requires_mdns': True,
            'recommended': False,
            'warning': None if mdns_available else 'Requires mDNS/Avahi to be installed'
        })

        # Option 2: localhost (local only)
        options.append({
            'value': 'localhost',
            'label': 'localhost',
            'description': 'Local access only (not suitable for remote access)',
            'requires_mdns': False,
            'recommended': False,
            'warning': 'Not recommended for VMs - remote access will not work'
        })

        # Option 3: Detected hostname (recommended)
        is_ip = re.match(r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', detected_hostname)
        options.append({
            'value': detected_hostname,
            'label': detected_hostname,
            'description': f'Detected {"IP address" if is_ip else "hostname"} (auto-detected)',
            'requires_mdns': detected_hostname.endswith('.local'),
            'recommended': True,
            'warning': None
        })

        # Option 4: Custom (placeholder for user input)
        options.append({
            'value': 'custom',
            'label': 'Custom hostname',
            'description': 'Enter your own hostname or IP address',
            'requires_mdns': False,
            'recommended': False,
            'warning': None
        })

        # Platform-specific guidance
        if platform == 'vm':
            if mdns_available:
                guidance = '.local domains work great for remote VM access with mDNS/Avahi'
                recommendation = 'Use detected hostname (recommended for VMs with mDNS)'
            else:
                guidance = 'IP address recommended, or install Avahi for .local hostname support'
                recommendation = 'Use detected IP or install Avahi for better hostname support'
        else:
            guidance = 'localhost works for local testing, or use your domain/IP for remote access'
            recommendation = 'Use detected value or configure custom domain'

        return jsonify({
            'platform': platform,
            'mdns_available': mdns_available,
            'detected_hostname': detected_hostname,
            'primary_ip': primary_ip,
            'short_hostname': short_hostname,
            'options': options,
            'guidance': guidance,
            'recommendation': recommendation
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

    # Transform system/hostname configuration
    if 'system' in wizard_data:
        system_data = wizard_data['system']
        hostname = system_data.get('hostname', '').strip()
        if hostname:
            config['system']['domain'] = hostname
            # Also update kratos browser_url to match hostname (critical for WebAuthn)
            config['kratos']['browser_url'] = f'https://{hostname}:8443'
            config['kratos']['public_url'] = f'https://{hostname}:4433'

    # Transform LLM configuration
    if 'llm' in wizard_data:
        llm_data = wizard_data['llm']
        config['llm_service']['ollama']['endpoint'] = llm_data.get('endpoint', 'http://localhost:11434')
        config['llm_service']['ollama']['default_model'] = llm_data.get('model', 'phi3:mini')
        config['llm_service']['ollama']['enabled'] = True

        # Also update external_ai endpoint (uses same Ollama endpoint)
        config['llm_service']['external_ai']['ollama_endpoint'] = llm_data.get('endpoint', 'http://localhost:11434')

    # Transform report generation LLM configuration
    if 'report_llm' in wizard_data:
        report_llm_data = wizard_data['report_llm']
        if 'report_generation' not in config['llm_service']:
            config['llm_service']['report_generation'] = {}

        config['llm_service']['report_generation']['endpoint'] = report_llm_data.get('endpoint', 'http://localhost:11434')
        config['llm_service']['report_generation']['model'] = report_llm_data.get('model', 'microsoft/phi-4-reasoning-plus')
        config['llm_service']['report_generation']['fallback_model'] = report_llm_data.get('fallback_model', 'qwen2.5-14b-instruct')
        config['llm_service']['report_generation']['max_tokens'] = int(report_llm_data.get('max_tokens', 16384))

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

        # Read version from VERSION file
        version = 'unknown'
        version_file = os.path.join(STING_SOURCE, 'VERSION')
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r') as f:
                    version = f.read().strip()
            except Exception:
                pass

        installations[install_id]['log'] = f"🐝 Installing STING-CE v{version}\n\n"
        installations[install_id]['log'] += f"✅ Configuration transformed and saved to: {STAGED_CONFIG_PATH}\n"
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

        # Note: Sudo privileges are already acquired by parent install_sting.sh
        # The parent script runs a sudo keepalive process that covers all child processes
        # We rely on that instead of calling sudo -v here (which would prompt on macOS)

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
            # IMPORTANT: Only kill keepalives from failed/aborted installations, NOT the active parent keepalive
            installations[install_id]['log'] += "Cleaning up any stale sudo keepalive processes...\n"
            # More specific pattern to avoid killing the parent installer's keepalive
            subprocess.run(['pkill', '-f', 'sudo-keepalive-wizard.log'], check=False)
        except Exception as e:
            # Non-fatal - continue with installation
            print(f"Warning: Could not check for stale processes: {e}")

        # Start sudo keepalive process in background
        # This refreshes sudo session every 30 seconds during installation
        # More aggressive interval for macOS/WSL2 compatibility
        # IMPORTANT: Don't start a new keepalive - the parent installer already started one!
        # Just verify it's still running
        installations[install_id]['log'] += "Verifying parent sudo keepalive is active...\n"

        keepalive_check = subprocess.run(
            ['pgrep', '-f', 'while true; do sudo -v.*sleep'],
            capture_output=True
        )

        if keepalive_check.returncode == 0:
            installations[install_id]['log'] += f"✅ Parent sudo keepalive is active\n"
            sudo_keepalive = None  # We don't need to manage it
        else:
            # Parent keepalive died - start our own as a backup
            installations[install_id]['log'] += "⚠️  Parent keepalive not found, starting wizard keepalive...\n"

            # First, refresh sudo to establish a session
            refresh_result = subprocess.run(['sudo', '-v'], capture_output=True, text=True)
            if refresh_result.returncode != 0:
                installations[install_id]['log'] += "❌ WARNING: Could not refresh sudo session\n"
                installations[install_id]['log'] += "   Installation may prompt for password\n"

            # Use -n flag to prevent TouchID/password prompts on macOS
            sudo_keepalive = subprocess.Popen(
                ['bash', '-c', 'while true; do sudo -n -v 2>/dev/null || echo "[$(date)] Sudo keepalive refresh failed" >> /tmp/sudo-keepalive-wizard.log; sleep 30; done'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Verify our new keepalive started
            try:
                # Give it a moment to start
                time.sleep(0.5)
                if sudo_keepalive and sudo_keepalive.poll() is None:
                    installations[install_id]['log'] += f"✅ Wizard sudo keepalive active (PID: {sudo_keepalive.pid})\n"
                elif sudo_keepalive:
                    installations[install_id]['log'] += "⚠️  Warning: Wizard sudo keepalive may not have started correctly\n"
            except Exception as e:
                installations[install_id]['log'] += f"⚠️  Warning: Could not verify keepalive status: {e}\n"

        try:
            # Set environment variables for installer
            env = os.environ.copy()
            env['WIZARD_CONFIG_PATH'] = STAGED_CONFIG_PATH

            # Pass STING hostname from wizard to installer (for WebAuthn/Passkey compatibility)
            # This prevents interactive hostname prompt during installation
            sting_hostname = config_data.get('system', {}).get('hostname', '').strip()
            if sting_hostname:
                env['STING_HOSTNAME'] = sting_hostname
                installations[install_id]['log'] += f"🌐 Using hostname for WebAuthn: {sting_hostname}\n"
            else:
                # Fallback to auto-detection if not provided
                env['STING_HOSTNAME'] = detect_sting_hostname()
                installations[install_id]['log'] += f"🌐 Auto-detected hostname: {env['STING_HOSTNAME']}\n"

            # Build installation command with admin creation if requested
            install_cmd = [INSTALLER_SCRIPT, 'install', '--no-prompt']

            # Add admin email if provided (enables automatic admin creation during install)
            if admin_email and admin_email.strip():
                install_cmd.append(f'--admin-email={admin_email.strip()}')
                installations[install_id]['log'] += f"👤 Admin user will be created: {admin_email}\n"
            else:
                installations[install_id]['log'] += "👤 Skipping admin user creation\n"

            with open(install_log_file, 'w') as log_file:
                process = subprocess.Popen(
                    install_cmd,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env
                )

            # Monitor installation progress with timeout
            # This prevents runaway installations from consuming resources indefinitely
            start_time = time.time()

            while process.poll() is None:
                # Check for timeout
                elapsed_time = time.time() - start_time
                if elapsed_time > INSTALLATION_TIMEOUT:
                    installations[install_id]['log'] += f"\n\n❌ INSTALLATION TIMEOUT\n"
                    installations[install_id]['log'] += f"   Installation exceeded {INSTALLATION_TIMEOUT // 60} minute timeout\n"
                    installations[install_id]['log'] += f"   Terminating installation process (PID: {process.pid})\n"

                    # Kill the installation process
                    try:
                        process.terminate()
                        time.sleep(5)  # Give it a chance to terminate gracefully
                        if process.poll() is None:
                            process.kill()  # Force kill if still running
                            installations[install_id]['log'] += "   Force killed installation process\n"
                    except Exception as e:
                        installations[install_id]['log'] += f"   Error killing process: {e}\n"

                    # Clean up sudo keepalive if we started one
                    if sudo_keepalive:
                        try:
                            sudo_keepalive.kill()
                            installations[install_id]['log'] += "   Cleaned up sudo keepalive process\n"
                        except Exception as e:
                            installations[install_id]['log'] += f"   Warning: Could not kill sudo keepalive: {e}\n"

                    installations[install_id]['completed'] = True
                    installations[install_id]['success'] = False
                    installations[install_id]['error'] = f'Installation timeout ({INSTALLATION_TIMEOUT // 60} minutes)'
                    installations[install_id]['status'] = 'Installation timed out'
                    return

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

            # 3. Verify admin account was created (fallback creation if needed)
            # Admin should already be created during installation via --admin-email flag
            # This is just a safety check/fallback
            installations[install_id]['status'] = 'Verifying admin account...'
            installations[install_id]['progress'] = 90

            # Wait for services to be ready
            time.sleep(10)

            # 4. Check if admin was created during installation
            install_dir = get_install_directory()
            admin_check_script = os.path.join(install_dir, 'scripts/admin/check-admin-exists.py')

            admin_exists = False
            if os.path.exists(admin_check_script) and admin_email:
                try:
                    check_result = subprocess.run(
                        ['python3', admin_check_script, '--email', admin_email],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    admin_exists = check_result.returncode == 0
                    if admin_exists:
                        installations[install_id]['log'] += f"\n✅ Admin account verified: {admin_email}\n"
                except Exception as e:
                    installations[install_id]['log'] += f"\nWarning: Could not verify admin: {str(e)}\n"

            # Fallback: Create admin if it doesn't exist (should rarely happen now)
            if not admin_exists and admin_email:
                installations[install_id]['log'] += f"\n⚠️  Admin not found, creating via fallback method...\n"
                admin_script = os.path.join(install_dir, 'scripts/admin/create-new-admin.py')
                if os.path.exists(admin_script):
                    try:
                        admin_result = subprocess.run(
                            ['python3', admin_script, '--email', admin_email, '--passwordless'],
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        installations[install_id]['log'] += f"\n{'='*50}\n"
                        installations[install_id]['log'] += "Creating Admin Account (Fallback)\n"
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
            # Use configured hostname for WebAuthn/Passkey compatibility (must match Kratos RP ID)
            configured_hostname = config_data.get('system', {}).get('hostname', '').strip()
            # Fallback: Try env var (for backward compatibility), then localhost
            redirect_hostname = configured_hostname or os.environ.get('STING_HOSTNAME') or 'localhost'
            installations[install_id]['redirect_url'] = f'https://{redirect_hostname}:8443'
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

            # Cleanup: Kill sudo keepalive process (only if we started one)
            if sudo_keepalive is not None:
                try:
                    installations[install_id]['log'] += "\nStopping wizard sudo keepalive...\n"
                    sudo_keepalive.terminate()
                    sudo_keepalive.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    sudo_keepalive.kill()
                except Exception as e:
                    print(f"Error terminating sudo keepalive: {e}")

                # Also kill wizard keepalive by pattern as a fallback
                try:
                    subprocess.run(['pkill', '-f', 'sudo-keepalive-wizard.log'], check=False, timeout=5)
                except:
                    pass
            # NOTE: We don't kill the parent installer's keepalive - it will clean itself up

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

    # Get admin email, default to admin@<hostname> if not provided or empty
    admin_email = config_data.get('admin', {}).get('email', '').strip()
    if not admin_email:
        # Fallback: use configured hostname for admin email
        hostname = config_data.get('system', {}).get('hostname', 'sting.local')
        admin_email = f'admin@{hostname}'

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

    # Check if sudo re-authentication is needed
    sudo_reauth_needed = os.path.exists('/tmp/sting-setup-state/sudo-reauth-needed')

    return jsonify({
        'log': install_data.get('log', ''),
        'status': install_data.get('status', 'Unknown'),
        'progress': install_data.get('progress', 0),
        'completed': install_data.get('completed', False),
        'success': install_data.get('success', False),
        'error': install_data.get('error'),
        'redirect_url': install_data.get('redirect_url'),
        'admin_email': install_data.get('admin_email'),
        'sudo_reauth_needed': sudo_reauth_needed
    })

@app.route('/api/sudo-reauth', methods=['POST'])
def sudo_reauth():
    """
    Prompt user to re-authenticate sudo credentials
    This creates a sudo prompt on the server terminal
    """
    try:
        # Attempt to refresh sudo credentials interactively
        # This will show a TouchID or password prompt on macOS
        result = subprocess.run(
            ['sudo', '-v'],
            capture_output=True,
            text=True,
            timeout=60  # Give user 60 seconds to authenticate
        )

        if result.returncode == 0:
            # Remove the flag file
            flag_file = '/tmp/sting-setup-state/sudo-reauth-needed'
            if os.path.exists(flag_file):
                os.remove(flag_file)

            return jsonify({
                'success': True,
                'message': 'Sudo credentials refreshed successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to refresh sudo credentials'
            }), 400

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'error': 'Authentication timeout - please try again'
        }), 408
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/shutdown', methods=['POST'])
def shutdown_wizard():
    """Shutdown wizard server gracefully after installation completes"""
    try:
        # Shutdown Flask server
        def shutdown_server():
            import time
            time.sleep(1)  # Give response time to be sent
            os._exit(0)  # Force exit the process

        # Run shutdown in background thread
        import threading
        threading.Thread(target=shutdown_server, daemon=True).start()

        return jsonify({
            'success': True,
            'message': 'Wizard server shutting down...'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'service': 'sting-setup-wizard'})

@app.route('/api/certificate-info')
def certificate_info():
    """
    Demonstration endpoint showing client IP detection for certificate management.
    This shows how we could integrate certificate generation into the wizard flow.
    """
    try:
        # Detect client IP (handles proxy headers)
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        if client_ip and ',' in client_ip:
            client_ip = client_ip.split(',')[0].strip()
        
        # Get server IP/hostname
        server_ip = get_primary_ip()
        
        # Get current STING configuration if available
        try:
            state = load_setup_state()
            config_data = state.get('wizard_data', {})
            sting_hostname = config_data.get('system', {}).get('hostname', '')
        except:
            sting_hostname = ''
        
        # Determine if certificate management is needed
        certificate_needed = (
            client_ip != server_ip and 
            client_ip != 'localhost' and 
            client_ip != '127.0.0.1'
        )
        
        # Detect client platform from User-Agent
        user_agent = request.headers.get('User-Agent', '').lower()
        if 'windows' in user_agent:
            platform = 'windows'
        elif 'mac' in user_agent or 'darwin' in user_agent:
            platform = 'macos'
        elif 'linux' in user_agent:
            platform = 'linux'
        else:
            platform = 'unknown'
        
        return jsonify({
            'client_ip': client_ip,
            'server_ip': server_ip,
            'sting_hostname': sting_hostname or server_ip,
            'certificate_needed': certificate_needed,
            'platform_detected': platform,
            'recommendation': (
                'Certificate installation recommended for seamless WebAuthn authentication'
                if certificate_needed else
                'No certificate installation needed - client and server on same machine'
            ),
            'wizard_integration_ready': True
        })
    
    except Exception as e:
        return jsonify({
            'error': str(e),
            'wizard_integration_ready': False
        }), 500

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
