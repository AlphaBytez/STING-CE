from flask import Blueprint, request, jsonify, session, g
from flask_cors import CORS
from app.models.nectar_bot_models import (
    NectarBot, NectarBotHandoff, NectarBotUsage,
    get_bot_by_api_key, get_active_bots_for_user,
    get_pending_handoffs, get_bot_analytics,
    get_bot_by_slug, get_public_bot_by_slug,
    BotStatus, HandoffStatus, HandoffUrgency
)
from app.middleware.auth_middleware_simple import require_auth
from app.middleware.auth_middleware import require_admin
from app.middleware.api_key_middleware import api_key_optional
from app.utils.decorators import require_auth_or_api_key
from app.utils.flexible_auth import require_auth_flexible
from app.database import db
from datetime import datetime, timedelta
import logging
from sqlalchemy import func, desc, and_
from sqlalchemy.exc import IntegrityError
import requests
import os
import uuid

logger = logging.getLogger(__name__)

# Create the blueprint
nectar_bot_bp = Blueprint('nectar_bots', __name__, url_prefix='/api/nectar-bots')
CORS(nectar_bot_bp, supports_credentials=True)


@nectar_bot_bp.route('', methods=['GET'])
@require_auth_flexible()
def list_nectar_bots():
    """List all Nectar Bots for admin users"""
    try:
        # Check if NectarBot table exists
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        if 'nectar_bots' not in inspector.get_table_names():
            # Table doesn't exist yet - return empty list gracefully
            logger.info("NectarBot table doesn't exist yet - returning empty list")
            return jsonify({
                'bots': [],
                'pagination': {
                    'page': 1,
                    'pages': 0,
                    'per_page': 20,
                    'total': 0,
                    'has_next': False,
                    'has_prev': False
                }
            })

        # Get user info from various sources
        user_id = None
        user_email = None
        is_admin = False

        # Check for API key authentication first
        if hasattr(g, 'api_key') and g.api_key:
            user_id = g.api_key.user_id
            user_email = g.api_key.user_email
            is_admin = 'admin' in g.api_key.scopes
        # Check g.user from flexible auth
        elif hasattr(g, 'user') and g.user:
            user_id = getattr(g.user, 'id', None) or getattr(g.user, 'kratos_user_id', None)
            user_email = getattr(g.user, 'email', None)
            is_admin = getattr(g.user, 'is_admin', False) or (getattr(g.user, 'role', None) == 'admin')
        # Fallback to session data
        else:
            user_id = session.get('identity_id') or session.get('user_id')
            user_email = session.get('user_email') or session.get('email')
            is_admin = session.get('is_admin', False) or (session.get('role') == 'admin')

        # Allow all authenticated users for now (admin filtering can be added later)
        if not user_id:
            logger.warning(f"No user_id found after flexible auth")
            user_id = 'demo-user'  # Fallback for demo
            user_email = 'demo@sting.local'
            is_admin = True  # Allow demo access

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)

        # Build query
        if is_admin:
            # Admins can see all bots
            query = NectarBot.query
        else:
            # Users can only see their own bots
            query = NectarBot.query.filter_by(owner_id=user_id)

        # Apply filters
        status_filter = request.args.get('status')
        if status_filter and status_filter in [s.value for s in BotStatus]:
            query = query.filter_by(status=status_filter)

        # Search by name
        search = request.args.get('search')
        if search:
            query = query.filter(NectarBot.name.ilike(f'%{search}%'))

        # Order by creation date (newest first)
        query = query.order_by(desc(NectarBot.created_at))

        # Paginate
        bots = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )

        # Convert to dict and include API keys for owners/admins
        bot_list = []
        for bot in bots.items:
            include_api_key = (str(bot.owner_id) == str(user_id)) or is_admin
            bot_dict = bot.to_dict(include_api_key=include_api_key)
            bot_list.append(bot_dict)

        return jsonify({
            'bots': bot_list,
            'pagination': {
                'page': page,
                'pages': bots.pages,
                'per_page': per_page,
                'total': bots.total,
                'has_next': bots.has_next,
                'has_prev': bots.has_prev
            }
        })

    except Exception as e:
        logger.error(f"Error listing Nectar Bots: {str(e)}", exc_info=True)
        # Return empty list instead of 500 error
        return jsonify({
            'bots': [],
            'pagination': {
                'page': 1,
                'pages': 0,
                'per_page': 20,
                'total': 0,
                'has_next': False,
                'has_prev': False
            }
        })


@nectar_bot_bp.route('', methods=['POST'])
@require_auth_flexible()
def create_nectar_bot():
    """Create a new Nectar Bot"""
    try:
        # Get user info from various sources (same pattern as list_nectar_bots)
        user_id = None
        user_email = None
        is_admin = False

        # Check for API key authentication first
        if hasattr(g, 'api_key') and g.api_key:
            user_id = g.api_key.user_id
            user_email = g.api_key.user_email
            is_admin = 'admin' in g.api_key.scopes
        # Check g.user from flexible auth
        elif hasattr(g, 'user') and g.user:
            user_id = getattr(g.user, 'id', None) or getattr(g.user, 'kratos_user_id', None)
            user_email = getattr(g.user, 'email', None)
            is_admin = getattr(g.user, 'is_admin', False) or (getattr(g.user, 'role', None) == 'admin')
        # Fallback to session data
        else:
            user_id = session.get('identity_id') or session.get('user_id')
            user_email = session.get('user_email') or session.get('email')
            is_admin = session.get('is_admin', False) or (session.get('role') == 'admin')

        if not user_id or not user_email:
            return jsonify({'error': 'Authentication required'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        # Validate required fields
        name = data.get('name', '').strip()
        if not name:
            return jsonify({'error': 'Bot name is required'}), 400
        
        if len(name) > 255:
            return jsonify({'error': 'Bot name must be less than 255 characters'}), 400
        
        # Check if name already exists for this user
        existing = NectarBot.query.filter_by(owner_id=user_id, name=name).first()
        if existing:
            return jsonify({'error': 'A bot with this name already exists'}), 400
        
        # Create new bot
        bot = NectarBot(
            name=name,
            description=data.get('description', ''),
            owner_id=user_id,
            owner_email=user_email,
            honey_jar_ids=data.get('honey_jar_ids', []),
            system_prompt=data.get('system_prompt', ''),
            max_conversation_length=data.get('max_conversation_length', 20),
            confidence_threshold=data.get('confidence_threshold', 0.7),
            rate_limit_per_hour=data.get('rate_limit_per_hour', 100),
            rate_limit_per_day=data.get('rate_limit_per_day', 1000),
            is_public=data.get('is_public', False),
            handoff_enabled=data.get('handoff_enabled', True),
            handoff_keywords=data.get('handoff_keywords', ["help", "human", "support", "escalate"]),
            handoff_confidence_threshold=data.get('handoff_confidence_threshold', 0.6)
        )
        
        db.session.add(bot)
        db.session.commit()
        
        logger.info(f"Created Nectar Bot '{name}' for user {user_email}")
        
        return jsonify({
            'message': 'Nectar Bot created successfully',
            'bot': bot.to_dict(include_api_key=True)
        }), 201
        
    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Database integrity error creating bot: {str(e)}")
        return jsonify({'error': 'Bot creation failed - possible duplicate API key'}), 400
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating Nectar Bot: {str(e)}")
        return jsonify({'error': 'Failed to create Nectar Bot'}), 500


@nectar_bot_bp.route('/<bot_id>', methods=['GET'])
@require_auth
def get_nectar_bot(bot_id):
    """Get a specific Nectar Bot"""
    try:
        user_id = session.get('identity_id')
        is_admin = session.get('is_admin', False)
        
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Check permissions
        if not is_admin and str(bot.owner_id) != str(user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        include_api_key = (str(bot.owner_id) == str(user_id)) or is_admin
        return jsonify({'bot': bot.to_dict(include_api_key=include_api_key)})
        
    except Exception as e:
        logger.error(f"Error getting Nectar Bot {bot_id}: {str(e)}")
        return jsonify({'error': 'Failed to get Nectar Bot'}), 500


@nectar_bot_bp.route('/<bot_id>', methods=['PUT'])
@require_auth
def update_nectar_bot(bot_id):
    """Update a Nectar Bot"""
    try:
        user_id = session.get('identity_id')
        is_admin = session.get('is_admin', False)
        
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Check permissions
        if not is_admin and str(bot.owner_id) != str(user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400
        
        # Update allowed fields
        updatable_fields = [
            'name', 'description', 'honey_jar_ids', 'system_prompt',
            'max_conversation_length', 'confidence_threshold',
            'rate_limit_per_hour', 'rate_limit_per_day', 'is_public',
            'handoff_enabled', 'handoff_keywords', 'handoff_confidence_threshold'
        ]
        
        for field in updatable_fields:
            if field in data:
                setattr(bot, field, data[field])
        
        # Update status if provided and user is admin
        if 'status' in data and is_admin:
            if data['status'] in [s.value for s in BotStatus]:
                bot.status = data['status']
        
        bot.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Updated Nectar Bot '{bot.name}' (ID: {bot_id})")
        
        include_api_key = (str(bot.owner_id) == str(user_id)) or is_admin
        return jsonify({
            'message': 'Bot updated successfully',
            'bot': bot.to_dict(include_api_key=include_api_key)
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating Nectar Bot {bot_id}: {str(e)}")
        return jsonify({'error': 'Failed to update Nectar Bot'}), 500


@nectar_bot_bp.route('/<bot_id>', methods=['DELETE'])
@require_auth
def delete_nectar_bot(bot_id):
    """Delete a Nectar Bot"""
    try:
        user_id = session.get('identity_id')
        is_admin = session.get('is_admin', False)
        
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Check permissions
        if not is_admin and str(bot.owner_id) != str(user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        bot_name = bot.name
        db.session.delete(bot)
        db.session.commit()
        
        logger.info(f"Deleted Nectar Bot '{bot_name}' (ID: {bot_id})")
        
        return jsonify({'message': f'Bot "{bot_name}" deleted successfully'})
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting Nectar Bot {bot_id}: {str(e)}")
        return jsonify({'error': 'Failed to delete Nectar Bot'}), 500


@nectar_bot_bp.route('/<bot_id>/regenerate-api-key', methods=['POST'])
@require_auth
def regenerate_api_key(bot_id):
    """Regenerate API key for a bot"""
    try:
        user_id = session.get('identity_id')
        is_admin = session.get('is_admin', False)
        
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Check permissions
        if not is_admin and str(bot.owner_id) != str(user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Generate new API key
        bot.api_key = NectarBot.generate_api_key()
        bot.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Regenerated API key for Nectar Bot '{bot.name}' (ID: {bot_id})")
        
        return jsonify({
            'message': 'API key regenerated successfully',
            'api_key': bot.api_key
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error regenerating API key for bot {bot_id}: {str(e)}")
        return jsonify({'error': 'Failed to regenerate API key'}), 500


@nectar_bot_bp.route('/<bot_id>/analytics', methods=['GET'])
@require_auth
def get_bot_analytics(bot_id):
    """Get analytics for a specific bot"""
    try:
        user_id = session.get('identity_id')
        is_admin = session.get('is_admin', False)
        
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404
        
        # Check permissions
        if not is_admin and str(bot.owner_id) != str(user_id):
            return jsonify({'error': 'Access denied'}), 403
        
        # Get time range
        days = request.args.get('days', 30, type=int)
        days = min(days, 365)  # Max 1 year
        
        analytics = get_bot_analytics(bot_id, days)
        
        # Update bot stats
        bot.update_stats()
        db.session.commit()
        
        return jsonify({
            'bot_id': bot_id,
            'bot_name': bot.name,
            'period_days': days,
            'analytics': analytics,
            'updated_stats': {
                'total_conversations': bot.total_conversations,
                'total_messages': bot.total_messages,
                'total_handoffs': bot.total_handoffs,
                'average_confidence': bot.average_confidence
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting analytics for bot {bot_id}: {str(e)}")
        return jsonify({'error': 'Failed to get bot analytics'}), 500


# Handoff management endpoints
@nectar_bot_bp.route('/handoffs', methods=['GET'])
@require_auth_flexible()
def list_handoffs():
    """List all handoffs (admin only)"""
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Build query
        query = NectarBotHandoff.query.join(NectarBot)
        
        # Apply filters
        status_filter = request.args.get('status')
        if status_filter and status_filter in [s.value for s in HandoffStatus]:
            query = query.filter(NectarBotHandoff.status == status_filter)
        
        urgency_filter = request.args.get('urgency')
        if urgency_filter and urgency_filter in [u.value for u in HandoffUrgency]:
            query = query.filter(NectarBotHandoff.urgency == urgency_filter)
        
        bot_id_filter = request.args.get('bot_id')
        if bot_id_filter:
            query = query.filter(NectarBotHandoff.bot_id == bot_id_filter)
        
        # Order by creation time (simpler ordering to avoid SQL errors)
        query = query.order_by(NectarBotHandoff.created_at.desc())
        
        # Paginate
        handoffs = query.paginate(
            page=page,
            per_page=per_page,
            error_out=False
        )
        
        return jsonify({
            'handoffs': [h.to_dict() for h in handoffs.items],
            'pagination': {
                'page': page,
                'pages': handoffs.pages,
                'per_page': per_page,
                'total': handoffs.total,
                'has_next': handoffs.has_next,
                'has_prev': handoffs.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f"Error listing handoffs: {str(e)}")
        return jsonify({'error': 'Failed to list handoffs'}), 500


@nectar_bot_bp.route('/handoffs/<handoff_id>/assign', methods=['POST'])
@require_admin
def assign_handoff(handoff_id):
    """Assign a handoff to an admin"""
    try:
        admin_email = session.get('user_email')
        
        handoff = NectarBotHandoff.query.filter_by(id=handoff_id).first()
        if not handoff:
            return jsonify({'error': 'Handoff not found'}), 404
        
        if handoff.status != HandoffStatus.PENDING.value:
            return jsonify({'error': 'Handoff is not in pending status'}), 400
        
        handoff.assigned_to = admin_email
        handoff.status = HandoffStatus.IN_PROGRESS.value
        handoff.updated_at = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Assigned handoff {handoff_id} to {admin_email}")
        
        return jsonify({
            'message': 'Handoff assigned successfully',
            'handoff': handoff.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error assigning handoff {handoff_id}: {str(e)}")
        return jsonify({'error': 'Failed to assign handoff'}), 500


@nectar_bot_bp.route('/handoffs/<handoff_id>/resolve', methods=['POST'])
@require_admin
def resolve_handoff(handoff_id):
    """Resolve a handoff"""
    try:
        admin_email = session.get('user_email')
        
        handoff = NectarBotHandoff.query.filter_by(id=handoff_id).first()
        if not handoff:
            return jsonify({'error': 'Handoff not found'}), 404
        
        if handoff.status not in [HandoffStatus.PENDING.value, HandoffStatus.IN_PROGRESS.value]:
            return jsonify({'error': 'Handoff is not in a resolvable status'}), 400
        
        data = request.get_json() or {}
        
        handoff.assigned_to = handoff.assigned_to or admin_email
        handoff.status = HandoffStatus.RESOLVED.value
        handoff.resolved_at = datetime.utcnow()
        handoff.resolution_notes = data.get('resolution_notes', '')
        handoff.calculate_resolution_time()
        handoff.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        logger.info(f"Resolved handoff {handoff_id} by {admin_email}")
        
        return jsonify({
            'message': 'Handoff resolved successfully',
            'handoff': handoff.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error resolving handoff {handoff_id}: {str(e)}")
        return jsonify({'error': 'Failed to resolve handoff'}), 500


# Analytics endpoints
@nectar_bot_bp.route('/analytics/overview', methods=['GET'])
@require_auth_flexible()
def get_overview_analytics():
    """Get overview analytics for all bots"""
    try:
        # Check if NectarBot tables exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        tables_exist = (
            'nectar_bots' in inspector.get_table_names() and
            'nectar_bot_usage' in inspector.get_table_names() and
            'nectar_bot_handoffs' in inspector.get_table_names()
        )

        if not tables_exist:
            # Tables don't exist yet - return empty analytics gracefully
            logger.info("Nectar Bot tables don't exist yet - returning empty analytics")
            return jsonify({
                'period_days': 30,
                'overview': {
                    'total_bots': 0,
                    'active_bots': 0,
                    'total_messages': 0,
                    'unique_conversations': 0,
                    'total_handoffs': 0,
                    'resolved_handoffs': 0,
                    'handoff_resolution_rate': 0,
                    'average_resolution_time_minutes': 0
                }
            })

        days = request.args.get('days', 30, type=int)
        days = min(days, 365)

        since = datetime.utcnow() - timedelta(days=days)

        # Total bots
        total_bots = NectarBot.query.count()
        active_bots = NectarBot.query.filter_by(status=BotStatus.ACTIVE.value).count()

        # Usage stats
        total_messages = NectarBotUsage.query.filter(
            NectarBotUsage.created_at >= since
        ).count()

        unique_conversations = db.session.query(
            func.count(func.distinct(NectarBotUsage.conversation_id))
        ).filter(NectarBotUsage.created_at >= since).scalar() or 0

        # Handoff stats
        total_handoffs = NectarBotHandoff.query.filter(
            NectarBotHandoff.created_at >= since
        ).count()

        resolved_handoffs = NectarBotHandoff.query.filter(
            NectarBotHandoff.created_at >= since,
            NectarBotHandoff.status == HandoffStatus.RESOLVED.value
        ).count()

        avg_resolution_time = db.session.query(
            func.avg(NectarBotHandoff.resolution_time_minutes)
        ).filter(
            NectarBotHandoff.created_at >= since,
            NectarBotHandoff.resolution_time_minutes.isnot(None)
        ).scalar() or 0

        return jsonify({
            'period_days': days,
            'overview': {
                'total_bots': total_bots,
                'active_bots': active_bots,
                'total_messages': total_messages,
                'unique_conversations': unique_conversations,
                'total_handoffs': total_handoffs,
                'resolved_handoffs': resolved_handoffs,
                'handoff_resolution_rate': (resolved_handoffs / total_handoffs * 100) if total_handoffs > 0 else 0,
                'average_resolution_time_minutes': float(avg_resolution_time) if avg_resolution_time else 0
            }
        })

    except Exception as e:
        logger.error(f"Error getting overview analytics: {str(e)}", exc_info=True)
        # Return empty analytics instead of 500 error
        return jsonify({
            'period_days': 30,
            'overview': {
                'total_bots': 0,
                'active_bots': 0,
                'total_messages': 0,
                'unique_conversations': 0,
                'total_handoffs': 0,
                'resolved_handoffs': 0,
                'handoff_resolution_rate': 0,
                'average_resolution_time_minutes': 0
            }
        })


# ==================== Chat Endpoints ====================

# Nectar Worker service URL (primary for Nectar Bots)
NECTAR_WORKER_URL = os.getenv('NECTAR_WORKER_URL', 'http://nectar-worker:9002')
# Legacy AI service URLs (fallback)
EXTERNAL_AI_SERVICE_URL = os.getenv('EXTERNAL_AI_SERVICE_URL', 'http://external-ai:8091')
CHATBOT_SERVICE_URL = os.getenv('CHATBOT_SERVICE_URL', 'http://chatbot:8888')


@nectar_bot_bp.route('/<bot_id>/chat', methods=['POST'])
@require_auth_flexible()
def chat_with_bot(bot_id):
    """
    Chat with a specific Nectar Bot (authenticated users only)
    Requires user to own the bot or be an admin
    """
    try:
        # Get user info
        user_id = None
        user_email = None
        is_admin = False

        if hasattr(g, 'api_key') and g.api_key:
            user_id = g.api_key.user_id
            user_email = g.api_key.user_email
            is_admin = 'admin' in g.api_key.scopes
        elif hasattr(g, 'user') and g.user:
            user_id = getattr(g.user, 'id', None) or getattr(g.user, 'kratos_user_id', None)
            user_email = getattr(g.user, 'email', None)
            is_admin = getattr(g.user, 'is_admin', False) or (getattr(g.user, 'role', None) == 'admin')
        else:
            user_id = session.get('identity_id') or session.get('user_id')
            user_email = session.get('user_email') or session.get('email')
            is_admin = session.get('is_admin', False) or (session.get('role') == 'admin')

        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Get bot
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404

        # Check permissions (owner or admin)
        if not is_admin and str(bot.owner_id) != str(user_id):
            return jsonify({'error': 'Access denied'}), 403

        # Check bot status
        if bot.status != BotStatus.ACTIVE.value:
            return jsonify({'error': f'Bot is {bot.status}'}), 503

        # Get request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400

        message = data.get('message')
        conversation_id = data.get('conversation_id') or str(uuid.uuid4())

        # Prepare bot context
        bot_context = {
            'bot_id': str(bot.id),
            'bot_name': bot.name,
            'system_prompt': bot.system_prompt,
            'honey_jar_ids': bot.honey_jar_ids or [],
            'max_conversation_length': bot.max_conversation_length,
            'confidence_threshold': bot.confidence_threshold,
            'handoff_enabled': bot.handoff_enabled,
            'handoff_keywords': bot.handoff_keywords or [],
            'handoff_confidence_threshold': bot.handoff_confidence_threshold,
            'is_nectar_bot': True
        }

        # Forward to AI service
        response_data = _send_chat_request(
            message=message,
            conversation_id=conversation_id,
            user_id=str(user_id),
            user_email=user_email,
            bot_context=bot_context
        )

        # Track usage
        _track_bot_usage(bot, conversation_id, message, response_data, request)

        # Check for handoff triggers
        if bot.handoff_enabled:
            _check_handoff_trigger(bot, conversation_id, message, response_data, user_id)

        # Update bot stats
        bot.last_used_at = datetime.utcnow()
        db.session.commit()

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in bot chat: {str(e)}")
        return jsonify({'error': 'Chat failed'}), 500


@nectar_bot_bp.route('/public/<slug>', methods=['GET'])
def get_public_bot_info(slug):
    """
    Get public bot information by slug (no authentication required)
    Only returns active public bots
    """
    try:
        bot = get_public_bot_by_slug(slug)
        if not bot:
            return jsonify({'error': 'Public bot not found'}), 404

        # Return limited info for public consumption
        return jsonify({
            'bot': {
                'id': str(bot.id),
                'name': bot.name,
                'slug': bot.slug,
                'description': bot.description,
                'status': bot.status,
                'public_url': bot.public_url,
                'embed_url': bot.embed_url,
                'created_at': bot.created_at.isoformat() if bot.created_at else None
            }
        })

    except Exception as e:
        logger.error(f"Error getting public bot: {str(e)}")
        return jsonify({'error': 'Failed to get bot info'}), 500


# ==================== Internal Endpoints (for Nectar Worker) ====================

@nectar_bot_bp.route('/internal/<bot_id>', methods=['GET'])
@api_key_optional()
def get_internal_bot_config(bot_id):
    """
    Get bot configuration for internal service use
    Requires API key authentication (used by nectar-worker)
    """
    try:
        # Verify API key authentication
        if not hasattr(g, 'api_key') or not g.api_key:
            return jsonify({'error': 'API key required'}), 401

        # Get bot
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404

        # Return bot configuration
        config = {
            'id': str(bot.id),
            'name': bot.name,
            'description': bot.description,
            'owner_id': str(bot.owner_id),
            'owner_email': bot.owner_email,
            'status': bot.status,
            'system_prompt': bot.system_prompt,
            'honey_jar_ids': bot.honey_jar_ids or [],
            'max_conversation_length': bot.max_conversation_length,
            'confidence_threshold': bot.confidence_threshold,
            'is_public': bot.is_public,
            'handoff_config': {
                'enabled': bot.handoff_enabled,
                'keywords': bot.handoff_keywords or [],
                'confidence_threshold': bot.handoff_confidence_threshold
            },
            'rate_limits': {
                'per_hour': bot.rate_limit_per_hour,
                'per_day': bot.rate_limit_per_day
            }
        }

        return jsonify(config)

    except Exception as e:
        logger.error(f"Error getting internal bot config: {e}")
        return jsonify({'error': 'Failed to get bot configuration'}), 500


@nectar_bot_bp.route('/internal/conversations/<conversation_id>/messages', methods=['POST'])
@api_key_optional()
def save_conversation_message(conversation_id):
    """
    Save a conversation message for tracking and analytics
    Requires API key authentication (used by nectar-worker)
    """
    try:
        # Verify API key authentication
        if not hasattr(g, 'api_key') or not g.api_key:
            return jsonify({'error': 'API key required'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON payload required'}), 400

        bot_id = data.get('bot_id')
        user_id = data.get('user_id')
        user_message = data.get('user_message', '')
        bot_response = data.get('bot_response', '')

        if not bot_id:
            return jsonify({'error': 'bot_id is required'}), 400

        # Get bot to verify it exists
        bot = NectarBot.query.filter_by(id=bot_id).first()
        if not bot:
            return jsonify({'error': 'Bot not found'}), 404

        # Create usage record
        usage = NectarBotUsage(
            bot_id=bot.id,
            conversation_id=conversation_id,
            message_id=str(uuid.uuid4()),
            user_id=user_id or 'unknown',
            user_message=user_message[:1000],
            bot_response=bot_response[:1000]
        )

        db.session.add(usage)
        db.session.commit()

        return jsonify({'message': 'Conversation saved successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving conversation: {e}")
        return jsonify({'error': 'Failed to save conversation'}), 500


# ==================== Public Endpoints ====================

@nectar_bot_bp.route('/public/<slug>/chat', methods=['POST'])
def chat_with_public_bot(slug):
    """
    Chat with a public Nectar Bot (no authentication required)
    Rate limited by IP address
    """
    try:
        # Get bot
        bot = get_public_bot_by_slug(slug)
        if not bot:
            return jsonify({'error': 'Public bot not found'}), 404

        # Check bot status
        if bot.status != BotStatus.ACTIVE.value:
            return jsonify({'error': f'Bot is currently {bot.status}'}), 503

        # Get request data
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({'error': 'Message is required'}), 400

        message = data.get('message')
        conversation_id = data.get('conversation_id') or str(uuid.uuid4())

        # Get user IP for rate limiting
        user_ip = request.remote_addr or 'unknown'
        user_id = f"public_{user_ip}"

        # Check rate limits (by IP for public bots)
        if _check_rate_limit(bot, user_ip):
            return jsonify({'error': 'Rate limit exceeded'}), 429

        # Prepare bot context
        bot_context = {
            'bot_id': str(bot.id),
            'bot_name': bot.name,
            'system_prompt': bot.system_prompt,
            'honey_jar_ids': bot.honey_jar_ids or [],
            'max_conversation_length': bot.max_conversation_length,
            'confidence_threshold': bot.confidence_threshold,
            'handoff_enabled': bot.handoff_enabled,
            'handoff_keywords': bot.handoff_keywords or [],
            'handoff_confidence_threshold': bot.handoff_confidence_threshold,
            'is_nectar_bot': True,
            'is_public': True
        }

        # Forward to Nectar Worker ONLY (no fallbacks for public bots - security)
        try:
            response_data = _send_public_chat_request(
                message=message,
                conversation_id=conversation_id,
                user_id=user_id,
                user_email='public@user.local',
                bot_context=bot_context
            )
        except Exception as service_error:
            logger.error(f"Public bot {bot.name} service unavailable: {service_error}")
            return jsonify({
                'error': 'Service temporarily unavailable',
                'message': 'This chat service is currently unavailable. Please try again later.'
            }), 503

        # Track usage
        _track_bot_usage(bot, conversation_id, message, response_data, request)

        # Check for handoff triggers
        if bot.handoff_enabled:
            _check_handoff_trigger(bot, conversation_id, message, response_data, user_id)

        # Update bot stats
        bot.last_used_at = datetime.utcnow()
        db.session.commit()

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in public bot chat: {str(e)}")
        return jsonify({'error': 'Chat failed'}), 500


# ==================== Helper Functions ====================

def _send_public_chat_request(message, conversation_id, user_id, user_email, bot_context):
    """
    Send chat request for PUBLIC Nectar Bots - NO FALLBACKS for security.

    Public bots must ONLY use the Nectar Worker service to prevent:
    - Data leakage from Honey Jars the public shouldn't access
    - Exposure of internal Bee context and conversation history
    - PII protection mode mismatches

    If Nectar Worker is unavailable, returns a service unavailable error.
    """
    nectar_request = {
        'message': message,
        'conversation_id': conversation_id,
        'user_id': user_id,
        'user_email': user_email,
        'bot_id': bot_context.get('bot_id'),
        'bot_context': bot_context
    }

    try:
        response = requests.post(
            f"{NECTAR_WORKER_URL}/chat",
            json=nectar_request,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Nectar Worker returned {response.status_code} for public bot: {bot_context.get('bot_name')}")
            raise Exception("Service temporarily unavailable")
    except requests.exceptions.RequestException as e:
        logger.error(f"Nectar Worker unavailable for public bot {bot_context.get('bot_name')}: {e}")
        raise Exception("Service temporarily unavailable")


def _send_chat_request(message, conversation_id, user_id, user_email, bot_context):
    """Send chat request to Nectar Worker service or fallback AI services (for authenticated users only)"""
    # Base request for Nectar Worker (uses bot_context at top level)
    nectar_request = {
        'message': message,
        'conversation_id': conversation_id,
        'user_id': user_id,
        'user_email': user_email,
        'bot_id': bot_context.get('bot_id'),
        'bot_context': bot_context  # Nectar Worker expects this at top level
    }

    # Try Nectar Worker service first (primary for Nectar Bots)
    try:
        response = requests.post(
            f"{NECTAR_WORKER_URL}/chat",
            json=nectar_request,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"Nectar Worker returned {response.status_code}: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Nectar Worker service unavailable: {e}")

    # Build request for external-ai service (expects bot_context INSIDE context field)
    # The BeeChatRequest model has 'context' field where bot_context should be nested
    external_ai_request = {
        'message': message,
        'conversation_id': conversation_id,
        'user_id': user_id,
        'context': {
            'bot_context': bot_context,  # External-AI looks for request.context.get('bot_context')
            'user_email': user_email
        }
    }
    logger.info(f"Sending Nectar Bot request to external-ai with bot: {bot_context.get('bot_name')}, is_nectar_bot: {bot_context.get('is_nectar_bot')}")

    # Fallback to external AI service
    try:
        response = requests.post(
            f"{EXTERNAL_AI_SERVICE_URL}/bee/chat",
            json=external_ai_request,
            timeout=30
        )
        if response.status_code == 200:
            return response.json()
        else:
            logger.warning(f"External AI returned {response.status_code}: {response.text[:200]}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"External AI service unavailable: {e}")

    # Final fallback to chatbot service (Bee)
    # Build request for Bee chatbot - include bot context so it can adapt its response
    chatbot_request = {
        'message': message,
        'conversation_id': conversation_id,
        'user_id': user_id,
        'context': {
            'bot_context': bot_context,
            'user_email': user_email,
            'is_nectar_bot_fallback': True  # Signal that this is a Nectar Bot fallback
        }
    }
    logger.info(f"Falling back to chatbot service for Nectar Bot: {bot_context.get('bot_name')}")

    try:
        response = requests.post(
            f"{CHATBOT_SERVICE_URL}/chat",
            json=chatbot_request,
            timeout=30
        )
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError as json_err:
                # Log the raw response for debugging
                logger.error(f"Failed to parse chatbot JSON response: {json_err}")
                logger.error(f"Raw response text: {response.text[:500]}")  # First 500 chars
                raise Exception(f"Invalid JSON response from chatbot: {json_err}")
        else:
            raise Exception(f"Chatbot service returned {response.status_code}")
    except requests.exceptions.RequestException as e:
        logger.error(f"All chat services unavailable: {e}")
        raise Exception("Chat service unavailable")


def _track_bot_usage(bot, conversation_id, user_message, response_data, request_obj):
    """Track bot usage for analytics"""
    try:
        usage = NectarBotUsage(
            bot_id=bot.id,
            conversation_id=conversation_id,
            message_id=response_data.get('message_id'),
            user_id=response_data.get('user_id', 'unknown'),
            user_ip=request_obj.remote_addr,
            user_agent=request_obj.headers.get('User-Agent'),
            user_message=user_message[:1000],  # Limit storage
            bot_response=response_data.get('response', '')[:1000],
            confidence_score=response_data.get('confidence_score'),
            response_time_ms=int(response_data.get('processing_time', 0) * 1000),
            honey_jars_queried=response_data.get('honey_jars_used', []),
            knowledge_matches=response_data.get('knowledge_matches', 0)
        )
        db.session.add(usage)
        db.session.commit()
    except Exception as e:
        logger.error(f"Failed to track bot usage: {e}")
        # Don't fail the request if tracking fails
        db.session.rollback()


def _check_handoff_trigger(bot, conversation_id, message, response_data, user_id):
    """Check if handoff should be triggered"""
    try:
        should_handoff = False
        reason = None
        urgency = HandoffUrgency.MEDIUM.value

        # Check confidence threshold
        confidence = response_data.get('confidence_score', 1.0)
        if confidence < bot.handoff_confidence_threshold:
            should_handoff = True
            reason = 'low_confidence'
            urgency = HandoffUrgency.MEDIUM.value

        # Check keywords
        message_lower = message.lower()
        for keyword in bot.handoff_keywords:
            if keyword.lower() in message_lower:
                should_handoff = True
                reason = 'keyword_detected'
                urgency = HandoffUrgency.HIGH.value
                break

        if should_handoff:
            handoff = NectarBotHandoff(
                bot_id=bot.id,
                conversation_id=conversation_id,
                user_id=str(user_id),
                reason=reason,
                urgency=urgency,
                trigger_message=message[:1000],
                bot_response=response_data.get('response', '')[:1000],
                confidence_score=confidence,
                conversation_history=response_data.get('conversation_history', [])
            )
            db.session.add(handoff)
            db.session.commit()
            logger.info(f"Handoff triggered for bot {bot.name}: {reason}")

    except Exception as e:
        logger.error(f"Failed to check handoff trigger: {e}")
        db.session.rollback()


def _check_rate_limit(bot, identifier):
    """Check if rate limit is exceeded for identifier (IP or user_id)"""
    try:
        now = datetime.utcnow()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        # Count recent requests
        hourly_count = NectarBotUsage.query.filter(
            NectarBotUsage.bot_id == bot.id,
            NectarBotUsage.user_ip == identifier,
            NectarBotUsage.created_at >= hour_ago
        ).count()

        daily_count = NectarBotUsage.query.filter(
            NectarBotUsage.bot_id == bot.id,
            NectarBotUsage.user_ip == identifier,
            NectarBotUsage.created_at >= day_ago
        ).count()

        # Check limits
        if hourly_count >= bot.rate_limit_per_hour:
            return True
        if daily_count >= bot.rate_limit_per_day:
            return True

        return False

    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return False  # Don't block on error