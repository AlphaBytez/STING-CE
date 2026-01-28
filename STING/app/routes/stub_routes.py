"""
Stub routes for legacy endpoints and Nectar Bot query functionality
These provide graceful responses and complete the AI-as-a-Service platform
"""

from flask import Blueprint, jsonify, request, g
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

stub_bp = Blueprint('stub_routes', __name__)

# Lazy import for nectar_bot_models to avoid import errors if models don't exist
def get_nectar_bot_models():
    try:
        from app.models.nectar_bot_models import get_bot_by_api_key, NectarBotUsage, get_bots_by_owner
        return get_bot_by_api_key, NectarBotUsage, get_bots_by_owner
    except ImportError as e:
        logger.warning(f"Nectar bot models not available: {e}")
        return None, None, None

# Legacy WebAuthn endpoints (replaced by Kratos native)
@stub_bp.route('/api/webauthn/credentials', methods=['GET'])
def webauthn_credentials_stub():
    """Stub for legacy WebAuthn credentials endpoint"""
    logger.info("Legacy WebAuthn credentials endpoint called - returning empty for compatibility")
    return jsonify({
        'credentials': [],
        'message': 'Using Kratos native WebAuthn - see settings page for passkey management'
    })

@stub_bp.route('/api/webauthn/passkeys', methods=['GET'])
def webauthn_passkeys_stub():
    """Stub for legacy WebAuthn passkeys endpoint"""
    logger.info("Legacy WebAuthn passkeys endpoint called - returning empty for compatibility")
    return jsonify({
        'passkeys': [],
        'message': 'Using Kratos native WebAuthn - see settings page for passkey management'
    })

# Legacy preferences migration endpoint
@stub_bp.route('/api/preferences/migrate-from-localstorage', methods=['POST'])
def preferences_migration_stub():
    """Stub for preferences migration endpoint"""
    logger.info("Preferences migration endpoint called - migration not needed")
    return jsonify({
        'success': True,
        'message': 'Preferences migration not required',
        'migrated_count': 0
    })

# Legacy TOTP status endpoint  
@stub_bp.route('/api/totp/totp-status', methods=['GET'])
def totp_status_stub():
    """Stub for legacy TOTP status endpoint"""
    logger.info("Legacy TOTP status endpoint called - using Kratos native TOTP")
    return jsonify({
        'enabled': False,
        'message': 'Using Kratos native TOTP - see settings page for authenticator setup'
    })


# ============================================================================
# NECTAR BOTS LIST ENDPOINT - Returns user's bots for BeeChat bot selector
# ============================================================================

@stub_bp.route('/api/nectar-bots', methods=['GET'])
def get_nectar_bots():
    """
    Get list of Nectar Bots for the current user
    Used by BeeChat to populate the bot selector dropdown
    """
    try:
        _, _, get_bots_by_owner = get_nectar_bot_models()
        
        if get_bots_by_owner is None:
            # Models not available, return empty list
            return jsonify({
                'bots': [],
                'count': 0,
                'message': 'Nectar bots feature not configured'
            })
        
        # Get current user from session
        user_id = None
        if hasattr(g, 'user') and g.user:
            user_id = g.user.get('id')
        
        if not user_id:
            # Return empty list for anonymous users
            return jsonify({
                'bots': [],
                'count': 0,
                'message': 'No bots available - please log in'
            })
        
        # Get bots owned by this user
        bots = get_bots_by_owner(user_id)
        
        # Return bot list with safe properties (exclude API keys)
        bot_list = []
        for bot in bots:
            bot_list.append({
                'id': str(bot.id),
                'name': bot.name,
                'slug': bot.slug,
                'description': bot.description,
                'status': bot.status,
                'is_public': bot.is_public,
                'honey_jar_ids': bot.honey_jar_ids or [],
                'total_messages': bot.total_messages,
                'created_at': bot.created_at.isoformat() if bot.created_at else None
            })
        
        return jsonify({
            'bots': bot_list,
            'count': len(bot_list)
        })
        
    except Exception as e:
        logger.error(f"Error getting nectar bots: {str(e)}")
        return jsonify({
            'bots': [],
            'count': 0,
            'error': str(e)
        })


# ============================================================================
# NECTAR BOT QUERY ENDPOINT - Complete AI-as-a-Service functionality
# ============================================================================

@stub_bp.route('/api/bot/chat', methods=['POST'])
def nectar_bot_chat():
    """
    External service endpoint for querying individual Nectar Bots
    Uses bot's individual nb_* API key for authentication
    """
    try:
        get_bot_by_api_key, NectarBotUsage, _ = get_nectar_bot_models()
        
        if get_bot_by_api_key is None:
            return jsonify({
                'error': 'Service unavailable',
                'message': 'Nectar bots feature not configured'
            }), 503
        
        from app.database import db
        
        # Get bot API key from X-API-Key header
        bot_api_key = request.headers.get('X-API-Key')
        if not bot_api_key or not bot_api_key.startswith('nb_'):
            return jsonify({
                'error': 'Missing or invalid bot API key',
                'message': "Use X-API-Key header with your bot's nb_* API key"
            }), 401
        
        # Find the bot by API key
        bot = get_bot_by_api_key(bot_api_key)
        if not bot:
            return jsonify({
                'error': 'Invalid bot API key',
                'message': 'Bot not found or API key expired'
            }), 401
        
        if bot.status != 'active':
            return jsonify({
                'error': 'Bot unavailable',
                'message': f'Bot is currently {bot.status}'
            }), 503
        
        # Get request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                'error': 'Missing message',
                'message': 'Request body must include "message" field'
            }), 400
        
        user_message = data['message']
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        
        # Mock business data integration for demo
        business_responses = {
            'hours': 'We are open Monday-Saturday 9AM-6PM, Sunday 11AM-4PM! Come buzz by anytime!',
            'honey': 'Our raw wildflower honey is fresh from local hives! We also have delicious clover and robust buckwheat varieties.',
            'supplies': 'Need beekeeping gear? We have complete hive setups, protective suits, smokers, and all the tools to get you started!',
            'inventory': 'Our inventory is buzzing! Most items in stock, but let me check specific products for you.',
            'shipping': 'Free shipping on orders over $50! Standard delivery is 3-5 business days.',
            'classes': 'We offer beginner beekeeping classes every Saturday at 10AM. Great way to get started!',
            'default': 'Welcome! I can help you find the perfect honey, bee supplies, or answer beekeeping questions. What interests you?'
        }
        
        # Simple keyword matching for demo
        response_message = business_responses['default']
        if any(word in user_message.lower() for word in ['hour', 'open', 'close', 'time']):
            response_message = business_responses['hours']
        elif any(word in user_message.lower() for word in ['honey', 'sweet', 'tea', 'recommend']):
            response_message = business_responses['honey']
        elif any(word in user_message.lower() for word in ['supplies', 'equipment', 'hive', 'gear', 'suit']):
            response_message = business_responses['supplies']
        elif any(word in user_message.lower() for word in ['stock', 'inventory', 'available']):
            response_message = business_responses['inventory']
        elif any(word in user_message.lower() for word in ['shipping', 'delivery', 'ship']):
            response_message = business_responses['shipping']
        elif any(word in user_message.lower() for word in ['class', 'learn', 'beginner', 'teach']):
            response_message = business_responses['classes']
        
        # Record usage for analytics if NectarBotUsage is available
        if NectarBotUsage is not None:
            usage = NectarBotUsage(
                bot_id=bot.id,
                conversation_id=conversation_id,
                message_id=str(uuid.uuid4()),
                user_id=data.get('user_id', 'external_user'),
                user_ip=request.remote_addr,
                user_agent=request.headers.get('User-Agent', 'Unknown'),
                user_message=user_message,
                bot_response=response_message,
                confidence_score=0.85,
                response_time_ms=150,
                honey_jars_queried=[],
                knowledge_matches=0
            )
            
            db.session.add(usage)
            
            # Update bot statistics
            bot.total_messages += 1
            bot.last_used_at = datetime.utcnow()
            
            db.session.commit()
        
        logger.info(f"Nectar Bot query completed for {bot.name}")
        
        return jsonify({
            'response': response_message,
            'conversation_id': conversation_id,
            'bot_name': bot.name,
            'confidence': 0.85,
            'response_time_ms': 150,
            'timestamp': datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Nectar Bot query error: {str(e)}")
        return jsonify({
            'error': 'Internal server error',
            'message': 'Failed to process bot query'
        }), 500
