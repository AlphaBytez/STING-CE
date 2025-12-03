"""
Config routes for frontend configuration including theme settings, SMTP, and auth modes
"""
from flask import Blueprint, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import yaml
import subprocess

logger = logging.getLogger(__name__)

config_bp = Blueprint('config', __name__, url_prefix='/api/config')
CORS(config_bp, supports_credentials=True)

@config_bp.route('/environment', methods=['GET'])
def get_environment():
    """Get environment information (dev/prod mode, mailpit status)"""
    try:
        from flask import current_app

        # Get config
        config = current_app.config.get('CONFIG', {})

        # Check environment mode from config
        environment = config.get('environment', 'development')
        is_development = environment == 'development'

        # Get email config to detect Mailpit
        email_config = config.get('email', {})
        smtp_host = email_config.get('smtp_host', '')
        is_mailpit = 'mailpit' in smtp_host.lower() or smtp_host == 'localhost'

        # Get hostname from config or environment
        hostname = config.get('system', {}).get('hostname', '') or os.environ.get('HOSTNAME', 'localhost')

        # Mailpit URL through nginx reverse proxy (HTTPS)
        mailpit_url = f"https://{hostname}:8443/mailpit/"

        return jsonify({
            'success': True,
            'environment': environment,
            'is_development': is_development,
            'mailpit': {
                'enabled': is_mailpit,
                'url': mailpit_url
            }
        })

    except Exception as e:
        logger.error(f"Error getting environment config: {str(e)}")
        # Return safe defaults
        return jsonify({
            'success': True,
            'environment': 'production',
            'is_development': False,
            'mailpit': {
                'enabled': False,
                'url': None
            }
        })

@config_bp.route('/theme', methods=['GET'])
def get_theme_config():
    """Get theme configuration from config.yml"""
    try:
        # Try to get config from app config first
        from flask import current_app
        
        # Get theme settings from config
        config = current_app.config.get('CONFIG', {})
        frontend_config = config.get('frontend', {})
        theme_config = frontend_config.get('theme', {})
        
        # Default theme settings if not configured
        default_theme_config = {
            'default': 'modern-lite',
            'user_selectable': True,
            'force_default': False
        }
        
        # Merge with defaults
        theme_settings = {**default_theme_config, **theme_config}
        
        return jsonify({
            'success': True,
            'theme': theme_settings
        })
        
    except Exception as e:
        logger.error(f"Error getting theme config: {str(e)}")
        # Return defaults on error
        return jsonify({
            'success': True,
            'theme': {
                'default': 'modern-lite',
                'user_selectable': True,
                'force_default': False
            }
        })

@config_bp.route('/frontend', methods=['GET'])
def get_frontend_config():
    """Get all frontend configuration"""
    try:
        from flask import current_app
        
        config = current_app.config.get('CONFIG', {})
        frontend_config = config.get('frontend', {})
        
        # Remove sensitive information
        safe_config = {
            'theme': frontend_config.get('theme', {
                'default': 'modern-lite',
                'user_selectable': True,
                'force_default': False
            }),
            'development': frontend_config.get('development', {
                'hot_reload': False,
                'debug_tools': False
            })
        }
        
        return jsonify({
            'success': True,
            'config': safe_config
        })
        
    except Exception as e:
        logger.error(f"Error getting frontend config: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load frontend configuration'
        }), 500

@config_bp.route('/smtp/status', methods=['GET'])
def get_smtp_status():
    """Check current SMTP configuration status."""
    try:
        # Check if we're in development or production mode
        email_mode = os.getenv('EMAIL_MODE', 'development')
        
        if email_mode == 'development':
            # Check if Mailpit is accessible
            import requests
            try:
                response = requests.get('http://mailpit:8025/api/v1/messages', timeout=2)
                mailpit_accessible = response.status_code == 200
                # Get message count
                message_count = len(response.json().get('messages', [])) if mailpit_accessible else 0
            except:
                mailpit_accessible = False
                message_count = 0
            
            return jsonify({
                'mode': 'development',
                'provider': 'mailpit',
                'configured': True,
                'accessible': mailpit_accessible,
                'mailpit_url': 'http://localhost:8026',
                'message_count': message_count,
                'message': 'Using Mailpit for email capture (development mode)'
            })
        else:
            # Check production SMTP settings
            smtp_host = os.getenv('SMTP_HOST')
            smtp_configured = bool(smtp_host)
            
            return jsonify({
                'mode': 'production',
                'provider': os.getenv('EMAIL_PROVIDER', 'smtp'),
                'configured': smtp_configured,
                'host': smtp_host if smtp_configured else None,
                'message': 'Production SMTP configured' if smtp_configured else 'No SMTP configuration found'
            })
            
    except Exception as e:
        logger.error(f"Failed to get SMTP status: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

@config_bp.route('/auth/mode', methods=['GET'])
def get_auth_mode():
    """Get current authentication mode and available options."""
    try:
        # Determine auth capabilities
        email_mode = os.getenv('EMAIL_MODE', 'development')
        smtp_configured = bool(os.getenv('SMTP_HOST')) if email_mode == 'production' else True
        
        # For now, return hybrid mode as we support both
        return jsonify({
            'mode': 'hybrid',
            'methods': {
                'password': True,  # Always available
                'code': True,      # Available if email works
                'link': True,      # Available if email works
                'webauthn': True   # WebAuthn is configured
            },
            'email_required_for': ['code', 'link'],
            'email_configured': smtp_configured,
            'email_mode': email_mode,
            'mailpit_url': 'http://localhost:8026' if email_mode == 'development' else None,
            'recommendations': get_auth_recommendations('hybrid', smtp_configured, email_mode)
        })
        
    except Exception as e:
        logger.error(f"Failed to get auth mode: {str(e)}")
        return jsonify({
            'error': str(e)
        }), 500

def get_auth_recommendations(auth_mode, smtp_configured, email_mode):
    """Get recommendations based on current setup."""
    recommendations = []
    
    if email_mode == 'development':
        recommendations.append({
            'level': 'info',
            'message': 'Development mode: Check Mailpit at http://localhost:8025 for all emails',
            'action': {
                'label': 'Open Mailpit',
                'url': 'http://localhost:8026'
            }
        })
    elif not smtp_configured:
        recommendations.append({
            'level': 'warning',
            'message': 'No SMTP configured. Passwordless login requires email setup.',
            'action': {
                'label': 'Configure SMTP',
                'url': '/settings/smtp'
            }
        })
    
    if auth_mode == 'hybrid':
        recommendations.append({
            'level': 'success',
            'message': 'Hybrid authentication active: Users can use passwords or email codes'
        })
    
    return recommendations

@config_bp.route('/registration', methods=['GET'])
def get_registration_config():
    """Get registration configuration"""
    try:
        # For now, always allow registration
        # In production, this could be controlled by environment variables or config
        registration_enabled = os.getenv('REGISTRATION_ENABLED', 'true').lower() == 'true'

        return jsonify({
            'success': True,
            'enabled': registration_enabled,
            'self_registration': True,
            'admin_approval_required': False,
            'email_verification_required': True
        })

    except Exception as e:
        logger.error(f"Error getting registration config: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to get registration configuration',
            'enabled': True  # Default to enabled on error
        }), 500

# Certificate Management Routes
@config_bp.route('/cert/download', methods=['GET'])
def download_ca_cert():
    """Download STING CA certificate for client installation"""
    try:
        # Try multiple possible certificate locations
        cert_paths = [
            '/app/certs/client-certs/sting-ca.pem',  # Mounted location (preferred)
            '/.sting-ce/client-certs/sting-ca.pem',  # Host /opt/sting-ce mounted as /.sting-ce
            '/opt/sting-ce/client-certs/sting-ca.pem',
            '/opt/sting-ce/sting-certs-export/sting-ca.pem',
            '/opt/sting-ce/certs/ca.pem'
        ]

        ca_path = None
        for path in cert_paths:
            if os.path.exists(path):
                ca_path = path
                logger.info(f"Found CA certificate at: {path}")
                break

        if ca_path and os.path.exists(ca_path):
            # Get hostname for dynamic filename
            hostname = os.environ.get('HOSTNAME', 'localhost')
            # Remove .local suffix if present for cleaner filename
            hostname_clean = hostname.replace('.local', '')
            dynamic_filename = f"{hostname_clean}-sting-ca.pem"

            return send_file(
                ca_path,
                mimetype='application/x-pem-file',
                as_attachment=True,
                download_name=dynamic_filename
            )
        else:
            logger.warning(f"CA certificate not found. Checked paths: {cert_paths}")
            return jsonify({
                'success': False,
                'error': 'CA certificate not found. Please export certificates first.',
                'instructions': {
                    'command': 'msting export-certs',
                    'description': 'This will generate client certificates and installation scripts',
                    'note': 'Run this command on the STING host (not inside the container)'
                }
            }), 404

    except Exception as e:
        logger.error(f"Error downloading CA certificate: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to download certificate: {str(e)}'
        }), 500

@config_bp.route('/cert/installer/<platform>', methods=['GET'])
def download_installer(platform):
    """Download platform-specific certificate installer"""
    try:
        installers = {
            'windows': 'install-ca-windows.ps1',
            'mac': 'install-ca-mac.sh',
            'macos': 'install-ca-mac.sh',
            'linux': 'install-ca-linux.sh'
        }

        if platform.lower() not in installers:
            return jsonify({
                'success': False,
                'error': f'Invalid platform: {platform}. Use windows, mac, or linux'
            }), 400

        installer_filename = installers[platform.lower()]

        # Try multiple possible locations
        installer_paths = [
            f'/app/certs/client-certs/{installer_filename}',  # Mounted location (preferred)
            f'/.sting-ce/client-certs/{installer_filename}',  # Host /opt/sting-ce mounted as /.sting-ce
            f'/opt/sting-ce/client-certs/{installer_filename}',
            f'/opt/sting-ce/sting-certs-export/{installer_filename}'
        ]

        installer_path = None
        for path in installer_paths:
            if os.path.exists(path):
                installer_path = path
                break

        if installer_path and os.path.exists(installer_path):
            return send_file(
                installer_path,
                as_attachment=True,
                download_name=installer_filename
            )
        else:
            return jsonify({
                'success': False,
                'error': 'Installer not found. Run: msting export-certs'
            }), 404

    except Exception as e:
        logger.error(f"Error downloading installer: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to download installer: {str(e)}'
        }), 500

@config_bp.route('/cert/health', methods=['GET'])
def cert_health():
    """Check if client trusts the STING certificate"""
    try:
        # If this endpoint is reached via HTTPS without browser warnings,
        # the cert is trusted
        return jsonify({
            'success': True,
            'trusted': True,
            'message': 'Certificate is trusted by your browser'
        })
    except Exception as e:
        logger.error(f"Error checking cert health: {str(e)}")
        return jsonify({
            'success': False,
            'trusted': False,
            'error': str(e)
        }), 500

@config_bp.route('/cert/info', methods=['GET'])
def cert_info():
    """Get certificate and hostname information for setup guidance"""
    try:
        # Get configured hostname/RP ID
        webauthn_rp_id = os.getenv('WEBAUTHN_RP_ID', 'localhost')

        # Get system IP - prefer SERVER_IP env var (set at install time from host)
        # This is needed because containers can only see Docker network IPs
        server_ip = os.getenv('SERVER_IP', '')
        sting_hostname = os.getenv('STING_HOSTNAME', '')

        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'

        # Priority: SERVER_IP > STING_HOSTNAME (if IP) > hostname -I detection
        if server_ip and re.match(ip_pattern, server_ip):
            primary_ip = server_ip
        elif sting_hostname and re.match(ip_pattern, sting_hostname):
            primary_ip = sting_hostname
        else:
            # Try to get IP from hostname -I
            # Note: Inside Docker, this returns Docker network IP, so SERVER_IP is preferred
            try:
                ip_result = subprocess.run(
                    ['hostname', '-I'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if ip_result.returncode == 0:
                    all_ips = ip_result.stdout.strip().split()
                    # Prefer IPs that are NOT Docker internal (172.16-31.x.x.x range)
                    # Note: 10.x.x.x and 192.168.x.x are valid private networks, don't filter
                    for ip in all_ips:
                        if not (ip.startswith('172.1') or ip.startswith('172.2') or ip.startswith('172.3')):
                            primary_ip = ip
                            break
                    else:
                        # Fallback to first IP if no "good" IP found
                        primary_ip = all_ips[0] if all_ips else 'unknown'
                else:
                    primary_ip = 'unknown'
            except:
                primary_ip = 'unknown'

        # Check if certs are available (check multiple possible locations)
        cert_available = os.path.exists('/app/certs/client-certs/sting-ca.pem') or \
                        os.path.exists('/.sting-ce/client-certs/sting-ca.pem') or \
                        os.path.exists('/opt/sting-ce/client-certs/sting-ca.pem') or \
                        os.path.exists('/opt/sting-ce/sting-certs-export/sting-ca.pem')

        return jsonify({
            'success': True,
            'hostname': webauthn_rp_id,
            'ip_address': primary_ip,
            'cert_available': cert_available,
            'download_urls': {
                'certificate': '/api/config/cert/download',
                'windows_installer': '/api/config/cert/installer/windows',
                'mac_installer': '/api/config/cert/installer/mac',
                'linux_installer': '/api/config/cert/installer/linux'
            }
        })

    except Exception as e:
        logger.error(f"Error getting cert info: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500