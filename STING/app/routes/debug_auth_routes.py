"""
Authentication Debug Routes - Diagnostic tools for auth development
Provides endpoints to inspect and fix authentication state without recreation
"""

import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, session
from app.middleware.api_key_middleware import api_key_optional

logger = logging.getLogger(__name__)

debug_auth_bp = Blueprint('debug_auth', __name__)

@debug_auth_bp.route('/user-status', methods=['GET'])
@api_key_optional()
def get_user_status():
    """
    Comprehensive user authentication status for debugging
    """
    try:
        status = {
            'timestamp': datetime.utcnow().isoformat(),
            'flask_session': {},
            'kratos_session': {},
            'database_user': {},
            'totp_status': {},
            'webauthn_status': {},
            'cookies': {},
            'debug_info': {}
        }
        
        # Flask session data
        status['flask_session'] = {
            'user_email': session.get('user_email'),
            'identity_id': session.get('identity_id'),
            'user_role': session.get('user_role'),
            'user_id': session.get('user_id'),
            'auth_method': session.get('auth_method'),
            'authenticated_at': session.get('authenticated_at'),
            'session_id': session.get('session_id'),
            'totp_secret': session.get('totp_secret', 'NOT_SET'),
            'session_keys': list(session.keys()) if hasattr(session, 'keys') else []
        }
        
        # Check Kratos session
        session_cookie = request.cookies.get('ory_kratos_session')
        if session_cookie:
            try:
                from app.utils.kratos_client import whoami
                kratos_response = whoami(session_cookie)
                
                if kratos_response and kratos_response.get('identity'):
                    identity = kratos_response['identity']
                    credentials = identity.get('credentials', {})
                    
                    status['kratos_session'] = {
                        'valid': True,
                        'identity_id': identity.get('id'),
                        'email': identity.get('traits', {}).get('email'),
                        'role': identity.get('traits', {}).get('role'),
                        'aal': kratos_response.get('authenticator_assurance_level'),
                        'credentials': list(credentials.keys()),
                        'totp_configured': 'totp' in credentials and bool(credentials.get('totp', {}).get('identifiers')),
                        'webauthn_configured': 'webauthn' in credentials and bool(credentials.get('webauthn', {}).get('identifiers')),
                        'code_configured': 'code' in credentials
                    }
                else:
                    status['kratos_session'] = {'valid': False, 'error': 'No identity in response'}
            except Exception as e:
                status['kratos_session'] = {'valid': False, 'error': str(e)}
        else:
            status['kratos_session'] = {'valid': False, 'error': 'No session cookie'}
        
        # Check STING database user
        try:
            from app.models.user_models import User
            user_email = status['kratos_session'].get('email') or status['flask_session'].get('user_email')
            
            if user_email:
                db_user = User.query.filter_by(email=user_email).first()
                if db_user:
                    status['database_user'] = {
                        'exists': True,
                        'id': db_user.id,
                        'email': db_user.email,
                        'role': db_user.role,
                        'is_admin': db_user.is_admin,
                        'status': db_user.status,
                        'created_at': db_user.created_at.isoformat() if db_user.created_at else None
                    }
                else:
                    status['database_user'] = {'exists': False, 'searched_email': user_email}
        except Exception as e:
            status['database_user'] = {'error': str(e)}
        
        # Check STING passkeys
        try:
            from app.models.passkey_models import Passkey
            user_email = status['kratos_session'].get('email')
            
            if user_email:
                # Get user ID for passkey lookup
                db_user_id = status['database_user'].get('id')
                if db_user_id:
                    passkeys = Passkey.query.filter_by(user_id=db_user_id).all()
                    status['webauthn_status'] = {
                        'sting_passkeys_count': len(passkeys),
                        'passkeys': [
                            {
                                'id': p.id,
                                'name': p.name,
                                'device_type': p.device_type,
                                'status': p.status,
                                'created_at': p.created_at.isoformat() if p.created_at else None
                            } for p in passkeys
                        ]
                    }
                else:
                    status['webauthn_status'] = {'error': 'No database user ID for passkey lookup'}
        except Exception as e:
            status['webauthn_status'] = {'error': str(e)}
        
        # Cookie analysis
        status['cookies'] = {
            'ory_kratos_session': 'present' if request.cookies.get('ory_kratos_session') else 'missing',
            'sting_session': 'present' if request.cookies.get('session') else 'missing',
            'all_cookies': list(request.cookies.keys())
        }
        
        # Debug recommendations
        recommendations = []
        if not status['flask_session'].get('user_email'):
            recommendations.append("Flask session missing user data - use /fix-session")
        if not status['kratos_session'].get('valid'):
            recommendations.append("Kratos session invalid - user needs to re-login")
        if not status['database_user'].get('exists'):
            recommendations.append("User missing from STING database - check user sync")
        
        status['debug_info'] = {
            'recommendations': recommendations,
            'session_coordination_status': 'OK' if (
                status['flask_session'].get('user_email') and 
                status['kratos_session'].get('valid')
            ) else 'BROKEN'
        }
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Error getting user status: {str(e)}", exc_info=True)
        return jsonify({'error': f'Status check failed: {str(e)}'}), 500

@debug_auth_bp.route('/fix-session', methods=['POST'])
@api_key_optional()
def fix_user_session():
    """
    Fix session coordination between Kratos and Flask
    """
    try:
        # Get user from Kratos session
        session_cookie = request.cookies.get('ory_kratos_session')
        if not session_cookie:
            return jsonify({'error': 'No Kratos session cookie found'}), 400
        
        from app.utils.kratos_client import whoami
        kratos_response = whoami(session_cookie)
        
        if not kratos_response or not kratos_response.get('identity'):
            return jsonify({'error': 'Invalid Kratos session'}), 400
        
        identity = kratos_response['identity']
        user_email = identity.get('traits', {}).get('email')
        identity_id = identity.get('id')
        user_role = identity.get('traits', {}).get('role', 'user')
        
        # Establish Flask session
        session['user_email'] = user_email
        session['identity_id'] = identity_id
        session['user_role'] = user_role
        session['auth_method'] = 'session_fix'
        session['authenticated_at'] = datetime.utcnow().isoformat()
        session['session_id'] = f"debug_fix_{user_email}_{int(datetime.utcnow().timestamp())}"
        
        logger.info(f"🔧 Flask session fixed for user: {user_email}")
        
        return jsonify({
            'success': True,
            'message': f'Session coordination fixed for {user_email}',
            'flask_session': {
                'user_email': session.get('user_email'),
                'identity_id': session.get('identity_id'),
                'user_role': session.get('user_role')
            }
        })
        
    except Exception as e:
        logger.error(f"Error fixing session: {str(e)}", exc_info=True)
        return jsonify({'error': f'Session fix failed: {str(e)}'}), 500

@debug_auth_bp.route('/clear-2fa', methods=['POST'])
@api_key_optional()
def clear_user_2fa():
    """
    Clear user's 2FA configuration for testing (Kratos and STING)
    """
    try:
        data = request.get_json() or {}
        user_email = data.get('email') or session.get('user_email')
        
        if not user_email:
            return jsonify({'error': 'User email required'}), 400
        
        results = {
            'user_email': user_email,
            'kratos_cleanup': {},
            'sting_cleanup': {}
        }
        
        # Clear STING passkeys
        try:
            from app.models.passkey_models import Passkey
            from app.models.user_models import User
            from app import db
            
            db_user = User.query.filter_by(email=user_email).first()
            if db_user:
                passkeys_deleted = Passkey.query.filter_by(user_id=db_user.id).delete()
                db.session.commit()
                results['sting_cleanup']['passkeys_deleted'] = passkeys_deleted
            else:
                results['sting_cleanup']['passkeys_deleted'] = 0
                results['sting_cleanup']['note'] = 'No STING user found'
                
        except Exception as e:
            results['sting_cleanup']['error'] = str(e)
        
        # Note: Kratos 2FA cleanup would require admin API calls
        # For now, focus on STING cleanup
        results['kratos_cleanup']['note'] = 'Kratos cleanup requires admin API - use Kratos admin tools'
        
        logger.info(f"🧹 2FA cleared for user: {user_email}")
        
        return jsonify({
            'success': True,
            'message': f'2FA cleared for {user_email}',
            'results': results
        })
        
    except Exception as e:
        logger.error(f"Error clearing 2FA: {str(e)}", exc_info=True)
        return jsonify({'error': f'2FA clear failed: {str(e)}'}), 500

@debug_auth_bp.route('/test-kratos-flow', methods=['POST'])
@api_key_optional()
def test_kratos_flow():
    """
    Test Kratos flow creation and CSRF handling
    """
    try:
        data = request.get_json() or {}
        flow_type = data.get('flow_type', 'settings')
        
        import requests
        import os
        
        KRATOS_PUBLIC_URL = os.getenv('KRATOS_PUBLIC_URL', 'http://kratos:4433')
        
        # Test flow creation
        if flow_type == 'settings':
            response = requests.get(
                f"{KRATOS_PUBLIC_URL}/self-service/settings/browser",
                headers={'Accept': 'application/json'},
                cookies=request.cookies,
                verify=False
            )
        else:
            return jsonify({'error': 'Unsupported flow type'}), 400
        
        result = {
            'flow_type': flow_type,
            'status_code': response.status_code,
            'success': response.ok,
            'url_called': response.url,
            'headers_sent': dict(response.request.headers) if hasattr(response, 'request') else {},
            'cookies_sent': dict(request.cookies),
        }
        
        if response.ok:
            flow_data = response.json()
            result['flow_data'] = {
                'flow_id': flow_data.get('id'),
                'ui_action': flow_data.get('ui', {}).get('action'),
                'csrf_token': None,
                'available_methods': []
            }
            
            # Extract CSRF token
            for node in flow_data.get('ui', {}).get('nodes', []):
                if node.get('attributes', {}).get('name') == 'csrf_token':
                    result['flow_data']['csrf_token'] = 'found'
                elif node.get('attributes', {}).get('name') == 'method':
                    method_value = node.get('attributes', {}).get('value')
                    if method_value:
                        result['flow_data']['available_methods'].append(method_value)
        else:
            result['error_response'] = response.text[:500]  # First 500 chars
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error testing Kratos flow: {str(e)}", exc_info=True)
        return jsonify({'error': f'Flow test failed: {str(e)}'}), 500