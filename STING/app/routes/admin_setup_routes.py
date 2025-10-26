#!/usr/bin/env python3
"""
Admin Setup Routes - Passwordless Admin Registration
Handles the new Email → Email Code → TOTP → Passkey flow
"""

from flask import Blueprint, request, jsonify, session, current_app
import secrets
import qrcode
import io
import base64
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import logging
import requests
import os
from urllib.parse import quote

logger = logging.getLogger(__name__)

admin_setup_bp = Blueprint('admin_setup', __name__)

# Temporary storage for setup sessions (in production, use Redis or database)
setup_sessions = {}

def _send_email_code(email, code):
    """Send verification code via email using Mailpit/SMTP"""
    try:
        # Get SMTP settings from Kratos config or environment
        smtp_host = os.environ.get('MAILPIT_HOST', 'localhost')
        smtp_port = int(os.environ.get('MAILPIT_PORT', '1025'))
        from_email = os.environ.get('FROM_EMAIL', 'noreply@sting.local')
        from_name = os.environ.get('FROM_NAME', 'STING Platform')
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "STING Admin Setup - Verification Code"
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = email

        # Email content
        text_content = f"""
STING Administrator Setup

Your verification code is: {code}

This code will expire in 10 minutes.

If you did not request this code, please ignore this email.

---
STING Security Platform
        """

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>STING Admin Setup</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .logo {{ color: #f59e0b; font-size: 32px; font-weight: bold; }}
        .code-container {{ background: #f8f9fa; border: 2px solid #e9ecef; border-radius: 8px; text-align: center; padding: 20px; margin: 20px 0; }}
        .code {{ font-size: 32px; font-weight: bold; color: #0066cc; letter-spacing: 4px; font-family: 'Courier New', monospace; }}
        .footer {{ text-align: center; color: #666; font-size: 14px; margin-top: 30px; border-top: 1px solid #eee; padding-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">🛡️ STING</div>
            <h1>Administrator Setup</h1>
        </div>
        
        <p>Hello,</p>
        
        <p>You're setting up an administrator account for STING. Please use the verification code below to continue:</p>
        
        <div class="code-container">
            <div class="code">{code}</div>
        </div>
        
        <p><strong>This code will expire in 10 minutes.</strong></p>
        
        <p>If you did not request this setup, please ignore this email.</p>
        
        <div class="footer">
            <p>STING Security Platform</p>
            <p>Passwordless Authentication • Enhanced Security</p>
        </div>
    </div>
</body>
</html>
        """

        # Attach parts
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            # Mailpit doesn't require authentication
            server.send_message(msg)
            
        logger.info(f"Verification code sent to {email}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")
        return False

def _generate_totp_qr(email, secret):
    """Generate TOTP QR code for authenticator app"""
    try:
        # Create TOTP URL
        issuer = "STING Administrator"
        label = f"{issuer}:{email}"
        totp_url = f"otpauth://totp/{quote(label)}?secret={secret}&issuer={quote(issuer)}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_url)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        # Return as HTML img tag for easy display
        return f'<img src="data:image/png;base64,{img_str}" alt="TOTP QR Code" />'
        
    except Exception as e:
        logger.error(f"Failed to generate TOTP QR code: {e}")
        return None

def _check_admin_exists():
    """Check if admin user already exists"""
    try:
        # This would check your user database
        # For now, we'll check if there are any admin users via Kratos
        kratos_admin_url = current_app.config.get('KRATOS_ADMIN_URL', 'https://localhost:4434')
        
        response = requests.get(
            f"{kratos_admin_url}/admin/identities",
            headers={'Accept': 'application/json'},
            verify=False,
            timeout=5
        )
        
        if response.status_code == 200:
            identities = response.json()
            # Check if any identity has admin role
            for identity in identities:
                traits = identity.get('traits', {})
                if traits.get('role', '').upper() == 'ADMIN':
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to check admin existence: {e}")
        return True  # Assume admin exists on error for security

@admin_setup_bp.route('/admin-setup-status', methods=['GET'])
def admin_setup_status():
    """Check if admin setup is complete"""
    try:
        admin_exists = _check_admin_exists()
        
        return jsonify({
            'setup_complete': admin_exists,
            'setup_required': not admin_exists
        })
        
    except Exception as e:
        logger.error(f"Admin setup status check failed: {e}")
        return jsonify({'error': 'Failed to check setup status'}), 500

@admin_setup_bp.route('/admin-setup-email', methods=['POST'])
def admin_setup_email():
    """Step 1: Initiate admin setup with email"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email address is required'}), 400
        
        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Check if admin already exists
        if _check_admin_exists():
            return jsonify({'error': 'Admin user already exists'}), 400
        
        # Generate 6-digit verification code
        verification_code = ''.join([str(secrets.randbelow(10)) for _ in range(6)])
        
        # Create setup session
        session_id = secrets.token_urlsafe(32)
        setup_sessions[session_id] = {
            'email': email,
            'verification_code': verification_code,
            'created_at': datetime.now(),
            'expires_at': datetime.now() + timedelta(minutes=10),
            'email_verified': False,
            'totp_secret': None,
            'totp_verified': False
        }
        
        # Send verification email
        if _send_email_code(email, verification_code):
            # Store session ID in Flask session
            session['admin_setup_session'] = session_id
            
            return jsonify({
                'success': True,
                'message': f'Verification code sent to {email}',
                'expires_in': 600  # 10 minutes
            })
        else:
            # Clean up session on email failure
            del setup_sessions[session_id]
            return jsonify({'error': 'Failed to send verification email'}), 500
            
    except Exception as e:
        logger.error(f"Admin email setup failed: {e}")
        return jsonify({'error': 'Setup failed'}), 500

@admin_setup_bp.route('/admin-setup-verify-email', methods=['POST'])
def admin_setup_verify_email():
    """Step 2: Verify email code and generate TOTP"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        code = data.get('code', '').strip()
        
        if not email or not code:
            return jsonify({'error': 'Email and verification code are required'}), 400
        
        # Get setup session
        session_id = session.get('admin_setup_session')
        if not session_id or session_id not in setup_sessions:
            return jsonify({'error': 'Invalid or expired setup session'}), 400
        
        setup_session = setup_sessions[session_id]
        
        # Check session expiry
        if datetime.now() > setup_session['expires_at']:
            del setup_sessions[session_id]
            session.pop('admin_setup_session', None)
            return jsonify({'error': 'Verification code expired'}), 400
        
        # Verify email and code match
        if setup_session['email'] != email or setup_session['verification_code'] != code:
            return jsonify({'error': 'Invalid verification code'}), 400
        
        # Generate TOTP secret
        import base64
        totp_secret = base64.b32encode(secrets.token_bytes(20)).decode('utf-8')
        
        # Update session
        setup_session['email_verified'] = True
        setup_session['totp_secret'] = totp_secret
        setup_session['expires_at'] = datetime.now() + timedelta(minutes=30)  # Extend for TOTP setup
        
        # Generate QR code
        qr_code_html = _generate_totp_qr(email, totp_secret)
        
        if not qr_code_html:
            return jsonify({'error': 'Failed to generate TOTP QR code'}), 500
        
        return jsonify({
            'success': True,
            'message': 'Email verified successfully',
            'totp_qr_code': qr_code_html,
            'totp_secret': totp_secret,  # Include for manual entry
            'admin_data': {
                'email': email,
                'role': 'admin'
            }
        })
        
    except Exception as e:
        logger.error(f"Email verification failed: {e}")
        return jsonify({'error': 'Verification failed'}), 500

@admin_setup_bp.route('/admin-setup-totp', methods=['POST'])
def admin_setup_totp():
    """Step 3: Verify TOTP code"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        totp_code = data.get('totp_code', '').strip()
        
        if not email or not totp_code:
            return jsonify({'error': 'Email and TOTP code are required'}), 400
        
        # Get setup session
        session_id = session.get('admin_setup_session')
        if not session_id or session_id not in setup_sessions:
            return jsonify({'error': 'Invalid or expired setup session'}), 400
        
        setup_session = setup_sessions[session_id]
        
        # Check session state
        if not setup_session['email_verified'] or setup_session['email'] != email:
            return jsonify({'error': 'Invalid setup session'}), 400
        
        if datetime.now() > setup_session['expires_at']:
            del setup_sessions[session_id]
            session.pop('admin_setup_session', None)
            return jsonify({'error': 'Setup session expired'}), 400
        
        # Verify TOTP code
        import pyotp
        totp = pyotp.TOTP(setup_session['totp_secret'])
        
        if not totp.verify(totp_code):
            return jsonify({'error': 'Invalid TOTP code'}), 400
        
        # Update session
        setup_session['totp_verified'] = True
        setup_session['expires_at'] = datetime.now() + timedelta(minutes=15)  # Final step
        
        return jsonify({
            'success': True,
            'message': 'TOTP verified successfully'
        })
        
    except Exception as e:
        logger.error(f"TOTP verification failed: {e}")
        return jsonify({'error': 'TOTP verification failed'}), 500

@admin_setup_bp.route('/admin-setup-passkey', methods=['POST'])
def admin_setup_passkey():
    """Step 4: Complete setup with passkey registration"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        # Get setup session
        session_id = session.get('admin_setup_session')
        if not session_id or session_id not in setup_sessions:
            return jsonify({'error': 'Invalid or expired setup session'}), 400
        
        setup_session = setup_sessions[session_id]
        
        # Verify session state
        if (not setup_session['email_verified'] or 
            not setup_session['totp_verified'] or 
            setup_session['email'] != email):
            return jsonify({'error': 'Invalid setup session state'}), 400
        
        if datetime.now() > setup_session['expires_at']:
            del setup_sessions[session_id]
            session.pop('admin_setup_session', None)
            return jsonify({'error': 'Setup session expired'}), 400
        
        # Create admin user via Kratos
        kratos_admin_url = current_app.config.get('KRATOS_ADMIN_URL', 'https://localhost:4434')
        
        # Create identity
        identity_data = {
            "schema_id": "default",
            "traits": {
                "email": email,
                "role": "admin",
                "name": f"Administrator ({email})"
            }
        }
        
        response = requests.post(
            f"{kratos_admin_url}/admin/identities",
            json=identity_data,
            headers={'Content-Type': 'application/json'},
            verify=False,
            timeout=10
        )
        
        if response.status_code != 201:
            logger.error(f"Failed to create admin identity: {response.status_code} {response.text}")
            return jsonify({'error': 'Failed to create admin account'}), 500
        
        identity = response.json()
        logger.info(f"Created admin identity: {identity['id']}")
        
        # TODO: Set up TOTP credentials in Kratos
        # TODO: Initialize WebAuthn/Passkey registration
        
        # Clean up session
        del setup_sessions[session_id]
        session.pop('admin_setup_session', None)
        
        return jsonify({
            'success': True,
            'message': 'Admin setup completed successfully',
            'admin_id': identity['id']
        })
        
    except Exception as e:
        logger.error(f"Passkey setup failed: {e}")
        return jsonify({'error': 'Setup completion failed'}), 500

# Cleanup expired sessions periodically
@admin_setup_bp.before_app_request
def cleanup_expired_sessions():
    """Clean up expired setup sessions"""
    try:
        current_time = datetime.now()
        expired_sessions = [
            session_id for session_id, session_data in setup_sessions.items()
            if current_time > session_data['expires_at']
        ]
        
        for session_id in expired_sessions:
            del setup_sessions[session_id]
            
    except Exception:
        pass  # Don't break the request if cleanup fails