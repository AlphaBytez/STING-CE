#!/usr/bin/env python3
"""
MVP Dashboard Routes - Quick endpoints to get MVP/beta ready
"""

from flask import Blueprint, jsonify, request
from app.utils.decorators import require_auth, require_api_key
from app.database import db
from app.models.user_models import User

mvp_bp = Blueprint('mvp', __name__, url_prefix='/api')

@mvp_bp.route('/auth/2fa-status', methods=['GET'])
@require_auth
def auth_2fa_status():
    """Alias for TOTP 2FA status endpoint"""
    try:
        # Import here to avoid circular imports
        from app.routes.totp_routes import get_2fa_status
        return get_2fa_status()
    except Exception as e:
        return jsonify({
            'has_totp': False,
            'has_passkey': False,
            'error': str(e)
        }), 500

@mvp_bp.route('/dashboard/metrics', methods=['GET'])
@require_auth
def dashboard_metrics():
    """Basic dashboard metrics for MVP"""
    try:
        from flask import g
        user = g.user if hasattr(g, 'user') else None
        
        return jsonify({
            'user_count': 1,
            'document_count': 0,
            'storage_used': '0 MB',
            'api_calls_today': 0,
            'security_events': 0,
            'system_health': 'healthy',
            'last_login': 'now',
            'user': user.email if user else 'unknown'
        })
    except Exception as e:
        return jsonify({
            'user_count': 1,
            'document_count': 0,
            'storage_used': '0 MB',
            'error': str(e)
        }), 200


@mvp_bp.route('/users/profile', methods=['GET'])
@require_auth
def user_profile():
    """Get current user profile"""
    try:
        from flask import g
        user = g.user if hasattr(g, 'user') else None
        
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401
        
        return jsonify({
            'id': user.id,
            'email': user.email,
            'role': getattr(user, 'role', 'user'),
            'created_at': getattr(user, 'created_at', '2024-01-01T00:00:00Z'),
            'last_login': getattr(user, 'last_login', '2024-01-01T00:00:00Z'),
            'is_active': getattr(user, 'is_active', True),
            'metadata': getattr(user, 'metadata', {})
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 403


@mvp_bp.route('/admin/sync-user', methods=['POST'])
@require_api_key  # Use API key auth for admin operations
def sync_user():
    """Sync user between Kratos and STING databases"""
    try:
        data = request.get_json()
        email = data.get('email')
        kratos_id = data.get('kratos_id')
        role = data.get('role', 'user')
        
        if not email or not kratos_id:
            return jsonify({'error': 'Email and kratos_id required'}), 400
        
        # Check if user already exists in STING database
        existing_user = User.query.filter_by(email=email).first()
        
        if existing_user:
            # Update existing user with Kratos ID
            existing_user.kratos_id = kratos_id
            existing_user.role = role
            db.session.commit()
            print(f"✅ Updated existing STING user: {email} with kratos_id: {kratos_id}")
            return jsonify({'message': 'User updated', 'user_id': existing_user.id}), 200
        else:
            # Create new STING user record
            new_user = User(
                email=email,
                kratos_id=kratos_id,
                role=role,
                is_active=True
            )
            db.session.add(new_user)
            db.session.commit()
            print(f"✅ Created new STING user: {email} with kratos_id: {kratos_id}")
            return jsonify({'message': 'User created', 'user_id': new_user.id}), 201
            
    except Exception as e:
        print(f"❌ Database sync error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@mvp_bp.route('/admin/sync-user/<email>', methods=['DELETE'])
@require_api_key
def delete_user(email):
    """Delete user from STING database"""
    try:
        user = User.query.filter_by(email=email).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            print(f"✅ Deleted STING user: {email}")
            return jsonify({'message': 'User deleted'}), 200
        else:
            print(f"ℹ️ STING user not found: {email}")
            return jsonify({'message': 'User not found'}), 404
            
    except Exception as e:
        print(f"❌ Database deletion error: {e}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500