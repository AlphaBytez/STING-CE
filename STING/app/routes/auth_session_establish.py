# app/routes/auth_session_establish.py
"""
Session establishment endpoint to coordinate Kratos and Flask sessions
after successful authentication. This ensures both systems are synced
before the frontend proceeds.
"""

from flask import Blueprint, request, jsonify, session as flask_session, g
import logging
from app.middleware.auth_middleware import load_user_from_session
from app.utils.kratos_client import whoami
import time
import redis
import json
import os

auth_session_bp = Blueprint('auth_session', __name__)
logger = logging.getLogger(__name__)

# Redis client for session coordination
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://redis:6379/0'))

@auth_session_bp.route('/establish', methods=['POST'])
def establish_session():
    """
    Establish and verify session after Kratos authentication.
    This endpoint ensures both Kratos and Flask sessions are properly synced
    before allowing the frontend to proceed.
    """
    logger.info("Session establishment requested")

    # Allow up to 3 attempts with small delays for cookie propagation
    max_attempts = 3
    attempt = 0

    while attempt < max_attempts:
        attempt += 1

        # Small delay to ensure cookies are set
        if attempt > 1:
            time.sleep(0.5)

        # Try to load user from session
        load_user_from_session()

        if hasattr(g, 'user') and g.user:
            user = g.user
            logger.info(f"Session established for {user.email} on attempt {attempt}")

            # Store session sync state in Redis
            session_key = f"session:sync:{user.id}"
            redis_client.setex(
                session_key,
                30,  # 30 second TTL
                json.dumps({
                    'synced': True,
                    'email': user.email,
                    'timestamp': time.time()
                })
            )

            # Return successful session data
            return jsonify({
                'success': True,
                'authenticated': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'username': user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'role': user.effective_role,
                    'kratos_id': user.kratos_id
                },
                'session_established': True,
                'attempt': attempt
            })

    # If we couldn't establish session after max attempts
    logger.warning(f"Failed to establish session after {max_attempts} attempts")
    return jsonify({
        'success': False,
        'authenticated': False,
        'error': 'Session coordination timeout',
        'attempts': max_attempts
    }), 503  # Service Unavailable

@auth_session_bp.route('/verify', methods=['GET'])
def verify_session():
    """
    Quick endpoint to verify session is established.
    Used by frontend to check if session sync is complete.
    """
    # Load current user
    load_user_from_session()

    if hasattr(g, 'user') and g.user:
        user = g.user

        # Check Redis for sync state
        session_key = f"session:sync:{user.id}"
        sync_state = redis_client.get(session_key)

        return jsonify({
            'verified': True,
            'synced': bool(sync_state),
            'email': user.email
        })

    return jsonify({
        'verified': False,
        'synced': False
    }), 401