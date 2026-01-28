#!/usr/bin/env python3
"""
Demo Authentication Routes - Email capture demo access
Lightweight authentication for public demo without user registration
"""

from flask import Blueprint, request, jsonify, make_response
from flask_cors import cross_origin
import logging
import secrets
import string
import smtplib
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)
demo_auth_bp = Blueprint('demo_auth', __name__)

# In-memory storage for demo verification codes (in production, use Redis)
demo_verification_codes = {}

# Demo sessions storage (in production, use Redis with expiration)
demo_sessions = {}


def load_demo_config():
    """Load demo configuration from config file or environment"""
    config_path = os.environ.get('INSTALL_DIR', '/opt/sting-ce') + '/conf/config.demo.yml'
    demo_config = {
        'enabled': True,
        'mode': 'email_capture',
        'verification': {
            'code_length': 6,
            'code_expiry': 600,  # 10 minutes
            'max_attempts': 3
        },
        'session': {
            'duration': 1800,  # 30 minutes
            'cookie_name': 'sting_demo_session'
        },
        'lead_capture': {
            'enabled': True,
            'export_path': os.environ.get('INSTALL_DIR', '/opt/sting-ce') + '/data/demo_leads.csv'
        },
        'smtp': {
            'host': os.environ.get('SMTP_SERVER', 'smtp-relay.brevo.com'),
            'port': int(os.environ.get('SMTP_PORT', '587')),
            'from': os.environ.get('DEMO_NOREPLY_EMAIL', 'noreply@demo.stingassistant.com'),
            'from_name': 'STING Demo'
        }
    }

    # Try to load from YAML if available
    try:
        import yaml
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config and 'demo_auth' in yaml_config:
                    demo_config.update(yaml_config['demo_auth'])
                if yaml_config and 'demo_ai' in yaml_config:
                    demo_config['demo_ai'] = yaml_config['demo_ai']
    except ImportError:
        pass  # YAML not available, use defaults

    return demo_config


def generate_verification_code(length=6):
    """Generate a numeric verification code"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))


def send_verification_email(email, code, config):
    """Send verification code via email"""
    smtp_config = config.get('smtp', {})
    host = smtp_config.get('host', 'smtp-relay.brevo.com')
    port = smtp_config.get('port', 587)
    from_addr = smtp_config.get('from', 'noreply@demo.stingassistant.com')
    from_name = smtp_config.get('from_name', 'STING Demo')

    subject = "Your STING Demo Verification Code"
    body = f"""
Hi there!

Thanks for trying STING! Your verification code is:

{code}

This code expires in 10 minutes.

If you didn't request this, you can safely ignore this email.

- The STING Team
    """

    msg = f"From: {from_name} <{from_addr}>\nTo: {email}\nSubject: {subject}\n\n{body}"

    try:
        server = smtplib.SMTP(host, port, timeout=10)
        server.starttls()
        server.sendmail(from_addr, [email], msg)
        server.quit()
        logger.info(f"Verification code sent to {email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email: {e}")
        return False


def save_lead(email, config):
    """Save lead email to CSV file"""
    lead_config = config.get('lead_capture', {})
    if not lead_config.get('enabled', True):
        return

    export_path = lead_config.get('export_path', '/opt/sting-ce/data/demo_leads.csv')
    os.makedirs(os.path.dirname(export_path), exist_ok=True)

    timestamp = datetime.utcnow().isoformat()
    with open(export_path, 'a') as f:
        f.write(f"{email},{timestamp}\n")


def create_demo_session(email):
    """Create a demo session for the verified email"""
    session_id = secrets.token_urlsafe(32)
    config = load_demo_config()
    duration = config.get('session', {}).get('duration', 1800)

    demo_sessions[session_id] = {
        'email': email,
        'created_at': datetime.utcnow(),
        'expires_at': datetime.utcnow() + timedelta(seconds=duration)
    }

    return session_id, duration


@demo_auth_bp.route('/api/demo/request-code', methods=['POST'])
@cross_origin(supports_credentials=True)
def request_verification_code():
    """Request a verification code for demo access"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()

        if not email:
            return jsonify({
                'success': False,
                'message': 'Email is required'
            }), 400

        # Basic email validation
        if '@' not in email or '.' not in email:
            return jsonify({
                'success': False,
                'message': 'Please enter a valid email address'
            }), 400

        config = load_demo_config()

        if not config.get('enabled', True):
            return jsonify({
                'success': False,
                'message': 'Demo mode is not enabled'
            }), 503

        # Generate verification code
        code_length = config.get('verification', {}).get('code_length', 6)
        code = generate_verification_code(code_length)

        # Store verification code
        demo_verification_codes[email] = {
            'code': code,
            'created_at': datetime.utcnow(),
            'expires_at': datetime.utcnow() + timedelta(seconds=config['verification']['code_expiry']),
            'attempts': 0
        }

        # Send verification email
        if not send_verification_email(email, code, config):
            return jsonify({
                'success': False,
                'message': 'Failed to send verification code. Please try again.'
            }), 500

        logger.info(f"Verification code requested for demo: {email}")

        return jsonify({
            'success': True,
            'message': 'Verification code sent! Check your email.',
            'expires_in': config['verification']['code_expiry']
        })

    except Exception as e:
        logger.error(f"Error requesting verification code: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500


@demo_auth_bp.route('/api/demo/verify-code', methods=['POST'])
@cross_origin(supports_credentials=True)
def verify_code_and_login():
    """Verify the code and create a demo session"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()

        if not email or not code:
            return jsonify({
                'success': False,
                'message': 'Email and code are required'
            }), 400

        config = load_demo_config()

        # Check if verification code exists and is valid
        stored = demo_verification_codes.get(email)
        if not stored:
            return jsonify({
                'success': False,
                'message': 'No verification code found. Please request a new code.'
            }), 400

        # Check expiration
        if datetime.utcnow() > stored['expires_at']:
            del demo_verification_codes[email]
            return jsonify({
                'success': False,
                'message': 'Verification code has expired. Please request a new one.'
            }), 400

        # Check attempts
        max_attempts = config.get('verification', {}).get('max_attempts', 3)
        if stored['attempts'] >= max_attempts:
            del demo_verification_codes[email]
            return jsonify({
                'success': False,
                'message': 'Too many failed attempts. Please request a new code.'
            }), 400

        # Verify code
        if stored['code'] != code:
            stored['attempts'] += 1
            remaining = max_attempts - stored['attempts']
            return jsonify({
                'success': False,
                'message': f'Invalid code. {remaining} attempts remaining.'
            }), 400

        # Code is valid - create session
        # Clean up verification code
        del demo_verification_codes[email]

        # Save lead
        save_lead(email, config)

        # Create session
        session_id, duration = create_demo_session(email)

        # Create response with session cookie
        response = make_response(jsonify({
            'success': True,
            'message': 'Welcome to the STING demo!',
            'session': {
                'id': session_id,
                'email': email,
                'expires_in': duration
            }
        }))

        cookie_name = config.get('session', {}).get('cookie_name', 'sting_demo_session')
        response.set_cookie(
            cookie_name,
            session_id,
            max_age=duration,
            httponly=True,
            secure=True,
            samesite='Lax'
        )

        logger.info(f"Demo session created for: {email}")

        return response

    except Exception as e:
        logger.error(f"Error verifying code: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'An error occurred. Please try again.'
        }), 500


@demo_auth_bp.route('/api/demo/logout', methods=['POST'])
@cross_origin(supports_credentials=True)
def logout():
    """End demo session"""
    config = load_demo_config()
    cookie_name = config.get('session', {}).get('cookie_name', 'sting_demo_session')

    response = make_response(jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }))

    response.set_cookie(cookie_name, '', max_age=0)

    return response


@demo_auth_bp.route('/api/demo/status', methods=['GET'])
@cross_origin(supports_credentials=True)
def demo_status():
    """Check demo status and features"""
    config = load_demo_config()

    # Check for valid session cookie
    cookie_name = config.get('session', {}).get('cookie_name', 'sting_demo_session')
    session_id = request.cookies.get(cookie_name)

    is_authenticated = False
    email = None

    if session_id and session_id in demo_sessions:
        session_data = demo_sessions[session_id]
        if datetime.utcnow() < session_data['expires_at']:
            is_authenticated = True
            email = session_data['email']
        else:
            # Session expired
            del demo_sessions[session_id]

    return jsonify({
        'demo_enabled': config.get('enabled', True),
        'demo_mode': config.get('mode', 'email_capture'),
        'is_authenticated': is_authenticated,
        'email': email,
        'features': {
            'chat': True,
            'honey_jars': True,
            'guided_tour': True
        },
        'ai_mode': 'informational'  # Demo shows informational messages, not real AI
    })


@demo_auth_bp.route('/api/demo/features', methods=['GET'])
@cross_origin(supports_credentials=True)
def demo_features():
    """Get list of available features in demo mode"""
    config = load_demo_config()

    return jsonify({
        'enabled': config.get('enabled', True),
        'mode': config.get('mode', 'email_capture'),
        'features': [
            {
                'id': 'honey_jars',
                'name': '🍯 Honey Jars',
                'description': 'Containerized knowledge bases with ChromaDB vector search',
                'available': True
            },
            {
                'id': 'bee_chat',
                'name': '🐝 Bee Chat',
                'description': 'Conversational AI connected to your documents',
                'available': True,
                'note': 'Demo mode shows informational responses'
            },
            {
                'id': 'security',
                'name': '🔐 Enterprise Auth',
                'description': 'Ory Kratos with WebAuthn/passkeys and MFA',
                'available': True
            },
            {
                'id': 'pii_detection',
                'name': '🛡️ PII Detection',
                'description': 'Automatic PII detection and protection',
                'available': True
            }
        ],
        'limitations': [
            'Sessions limited to 30 minutes',
            'No file uploads',
            'No data persistence after session ends',
            'Informational AI responses (no real LLM)'
        ]
    })


@demo_auth_bp.route('/api/demo/leads/export', methods=['GET'])
def export_leads():
    """Export collected lead emails (admin only in production)"""
    try:
        config = load_demo_config()
        lead_config = config.get('lead_capture', {})
        export_path = lead_config.get('export_path', '/opt/sting-ce/data/demo_leads.csv')

        if not os.path.exists(export_path):
            return jsonify({
                'success': True,
                'leads': [],
                'message': 'No leads collected yet'
            })

        leads = []
        with open(export_path, 'r') as f:
            for line in f:
                parts = line.strip().split(',')
                if len(parts) >= 2:
                    leads.append({
                        'email': parts[0],
                        'timestamp': parts[1]
                    })

        return jsonify({
            'success': True,
            'leads': leads,
            'total': len(leads)
        })

    except Exception as e:
        logger.error(f"Error exporting leads: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Failed to export leads'
        }), 500


@demo_auth_bp.route('/api/demo/privacy-disclosure', methods=['GET'])
def privacy_disclosure():
    """Get privacy disclosure text"""
    config = load_demo_config()
    disclosure = config.get('privacy_disclosure', '''We collect your email to enable demo access. Your email is used solely for this purpose and is not saved beyond your demo session.

No documents, conversations, or personal data are retained.

This is a demo environment - no data persists after your session ends.''')

    return jsonify({
        'disclosure': disclosure
    })
