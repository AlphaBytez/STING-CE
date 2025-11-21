"""
QE Bee (Quality Engineering Bee) Routes for STING-CE
Handles review queue management, webhook configuration, and internal worker endpoints.
"""

import logging
from flask import Blueprint, request, jsonify, g
from datetime import datetime
from typing import Optional

from app.database import get_db_session
from app.utils.decorators import require_auth_or_api_key
from app.services.review_service import get_review_service
from app.models.review_models import (
    ReviewQueue, ReviewHistory, WebhookConfig,
    ReviewStatus, ReviewResultCode
)

logger = logging.getLogger(__name__)

# Create blueprint
qe_bee_bp = Blueprint('qe_bee', __name__, url_prefix='/api/qe-bee')


def get_current_user() -> Optional[str]:
    """Get current user ID from either API key or session"""
    if hasattr(g, 'api_key') and g.api_key:
        return str(g.api_key.user_id)
    if hasattr(g, 'user') and g.user:
        return str(g.user.id)

    from app.utils.kratos_client import whoami
    session_cookie = request.cookies.get('ory_kratos_session')
    if session_cookie:
        identity = whoami(session_cookie)
        if identity:
            user_id = identity.get('identity', {}).get('id')
            if user_id:
                return str(user_id)
    return None


def get_user_role() -> str:
    """Get current user role from database"""
    from app.models.user_models import User

    user_id = get_current_user()
    if not user_id:
        return 'user'

    with get_db_session() as session:
        user = session.query(User).filter(User.kratos_id == user_id).first()
        if user:
            if user.is_super_admin:
                return 'super_admin'
            elif user.is_admin:
                return 'admin'
        return 'user'


# ============================================================================
# Public/User Endpoints (require authentication)
# ============================================================================

@qe_bee_bp.route('/stats', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def get_stats():
    """Get review statistics for the current user or all users (admin)"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        user_role = get_user_role()
        review_service = get_review_service()

        # Admins can see all stats, users see only their own
        if user_role in ['admin', 'super_admin'] and request.args.get('all') == 'true':
            stats = review_service.get_review_stats()
        else:
            stats = review_service.get_review_stats(user_id)

        return jsonify({
            'success': True,
            'data': stats
        })

    except Exception as e:
        logger.error(f"Error getting QE Bee stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/history', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def get_history():
    """Get review history for the current user"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        user_role = get_user_role()
        limit = min(int(request.args.get('limit', 20)), 100)

        review_service = get_review_service()

        # Admins can see all history
        if user_role in ['admin', 'super_admin'] and request.args.get('all') == 'true':
            reviews = review_service.get_recent_reviews(limit=limit)
        else:
            reviews = review_service.get_recent_reviews(limit=limit, user_id=user_id)

        return jsonify({
            'success': True,
            'data': {
                'reviews': reviews,
                'count': len(reviews)
            }
        })

    except Exception as e:
        logger.error(f"Error getting QE Bee history: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/queue', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def get_queue():
    """Get current review queue status"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        user_role = get_user_role()

        with get_db_session() as session:
            # Base query
            query = session.query(ReviewQueue)

            # Non-admins only see their own items
            if user_role not in ['admin', 'super_admin']:
                query = query.filter(ReviewQueue.user_id == user_id)

            # Get pending and reviewing items
            pending = query.filter(ReviewQueue.status == ReviewStatus.PENDING).count()
            reviewing = query.filter(ReviewQueue.status == ReviewStatus.REVIEWING).count()

            # Get recent items
            recent = query.order_by(ReviewQueue.created_at.desc()).limit(10).all()

            return jsonify({
                'success': True,
                'data': {
                    'pending': pending,
                    'reviewing': reviewing,
                    'recent_items': [r.to_dict() for r in recent]
                }
            })

    except Exception as e:
        logger.error(f"Error getting QE Bee queue: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/review/<review_id>', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def get_review(review_id: str):
    """Get details of a specific review"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        user_role = get_user_role()

        with get_db_session() as session:
            review = session.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()

            if not review:
                return jsonify({'error': 'Review not found'}), 404

            # Check access (admins can see all, users only their own)
            if user_role not in ['admin', 'super_admin'] and review.user_id != user_id:
                return jsonify({'error': 'Access denied'}), 403

            return jsonify({
                'success': True,
                'data': {
                    'review': review.to_dict()
                }
            })

    except Exception as e:
        logger.error(f"Error getting review {review_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Webhook Configuration Endpoints
# ============================================================================

@qe_bee_bp.route('/webhooks', methods=['GET'])
@require_auth_or_api_key(['admin', 'read'])
def list_webhooks():
    """List user's webhook configurations"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        with get_db_session() as session:
            configs = session.query(WebhookConfig).filter(
                WebhookConfig.user_id == user_id
            ).all()

            return jsonify({
                'success': True,
                'data': {
                    'webhooks': [c.to_dict() for c in configs],
                    'count': len(configs)
                }
            })

    except Exception as e:
        logger.error(f"Error listing webhooks: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/webhooks', methods=['POST'])
@require_auth_or_api_key(['admin', 'write'])
def create_webhook():
    """Create a new webhook configuration"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        # Validate required fields
        if not data.get('name') or not data.get('url'):
            return jsonify({'error': 'name and url are required'}), 400

        # Validate URL (CE: local URLs only)
        url = data['url']
        if not url.startswith('http://') and not url.startswith('https://'):
            return jsonify({'error': 'Invalid URL format'}), 400

        with get_db_session() as session:
            # Check if user already has max webhooks (limit to 5 in CE)
            existing_count = session.query(WebhookConfig).filter(
                WebhookConfig.user_id == user_id
            ).count()

            if existing_count >= 5:
                return jsonify({'error': 'Maximum webhook limit reached (5)'}), 400

            webhook = WebhookConfig(
                user_id=user_id,
                name=data['name'],
                url=url,
                secret=data.get('secret'),
                event_types=data.get('event_types'),
                target_types=data.get('target_types'),
                result_codes=data.get('result_codes'),
                is_active=data.get('is_active', True)
            )

            session.add(webhook)
            session.commit()

            logger.info(f"🐝 Webhook created: {webhook.name} for user {user_id}")

            return jsonify({
                'success': True,
                'data': {
                    'webhook': webhook.to_dict()
                }
            }), 201

    except Exception as e:
        logger.error(f"Error creating webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/webhooks/<webhook_id>', methods=['PUT'])
@require_auth_or_api_key(['admin', 'write'])
def update_webhook(webhook_id: str):
    """Update a webhook configuration"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        with get_db_session() as session:
            webhook = session.query(WebhookConfig).filter(
                WebhookConfig.id == webhook_id,
                WebhookConfig.user_id == user_id
            ).first()

            if not webhook:
                return jsonify({'error': 'Webhook not found'}), 404

            # Update allowed fields
            update_fields = ['name', 'url', 'secret', 'event_types',
                           'target_types', 'result_codes', 'is_active']

            for field in update_fields:
                if field in data:
                    setattr(webhook, field, data[field])

            webhook.updated_at = datetime.utcnow()
            session.commit()

            return jsonify({
                'success': True,
                'data': {
                    'webhook': webhook.to_dict()
                }
            })

    except Exception as e:
        logger.error(f"Error updating webhook {webhook_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/webhooks/<webhook_id>', methods=['DELETE'])
@require_auth_or_api_key(['admin', 'write'])
def delete_webhook(webhook_id: str):
    """Delete a webhook configuration"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        with get_db_session() as session:
            webhook = session.query(WebhookConfig).filter(
                WebhookConfig.id == webhook_id,
                WebhookConfig.user_id == user_id
            ).first()

            if not webhook:
                return jsonify({'error': 'Webhook not found'}), 404

            session.delete(webhook)
            session.commit()

            logger.info(f"🐝 Webhook deleted: {webhook_id}")

            return jsonify({
                'success': True,
                'message': 'Webhook deleted successfully'
            })

    except Exception as e:
        logger.error(f"Error deleting webhook {webhook_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/webhooks/<webhook_id>/test', methods=['POST'])
@require_auth_or_api_key(['admin', 'write'])
def test_webhook(webhook_id: str):
    """Send a test webhook to verify configuration"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        with get_db_session() as session:
            webhook = session.query(WebhookConfig).filter(
                WebhookConfig.id == webhook_id,
                WebhookConfig.user_id == user_id
            ).first()

            if not webhook:
                return jsonify({'error': 'Webhook not found'}), 404

            # Send test payload
            import requests
            test_payload = {
                'event': 'review.test',
                'message': 'This is a test webhook from QE Bee',
                'timestamp': datetime.utcnow().isoformat(),
                'webhook_id': str(webhook.id),
                'user_id': user_id
            }

            try:
                response = requests.post(
                    webhook.url,
                    json=test_payload,
                    timeout=10,
                    headers={'Content-Type': 'application/json'}
                )

                webhook.is_verified = response.status_code < 400
                session.commit()

                return jsonify({
                    'success': True,
                    'data': {
                        'status_code': response.status_code,
                        'verified': webhook.is_verified,
                        'message': 'Test webhook sent successfully' if webhook.is_verified else 'Webhook test failed'
                    }
                })

            except requests.RequestException as req_err:
                return jsonify({
                    'success': False,
                    'error': f'Failed to reach webhook URL: {str(req_err)}'
                }), 400

    except Exception as e:
        logger.error(f"Error testing webhook {webhook_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Admin Endpoints
# ============================================================================

@qe_bee_bp.route('/admin/queue', methods=['GET'])
@require_auth_or_api_key(['admin'])
def admin_get_queue():
    """Admin: Get full queue status"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        user_role = get_user_role()
        if user_role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        with get_db_session() as session:
            # Get counts by status
            pending = session.query(ReviewQueue).filter(
                ReviewQueue.status == ReviewStatus.PENDING
            ).count()

            reviewing = session.query(ReviewQueue).filter(
                ReviewQueue.status == ReviewStatus.REVIEWING
            ).count()

            passed_today = session.query(ReviewQueue).filter(
                ReviewQueue.status == ReviewStatus.PASSED,
                ReviewQueue.completed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).count()

            failed_today = session.query(ReviewQueue).filter(
                ReviewQueue.status == ReviewStatus.FAILED,
                ReviewQueue.completed_at >= datetime.utcnow().replace(hour=0, minute=0, second=0)
            ).count()

            # Get all queue items
            queue_items = session.query(ReviewQueue).order_by(
                ReviewQueue.priority.asc(),
                ReviewQueue.created_at.asc()
            ).limit(50).all()

            return jsonify({
                'success': True,
                'data': {
                    'pending': pending,
                    'reviewing': reviewing,
                    'passed_today': passed_today,
                    'failed_today': failed_today,
                    'queue_items': [item.to_dict() for item in queue_items]
                }
            })

    except Exception as e:
        logger.error(f"Error getting admin queue: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/admin/review/<review_id>/retry', methods=['POST'])
@require_auth_or_api_key(['admin'])
def admin_retry_review(review_id: str):
    """Admin: Retry a failed review"""
    try:
        user_id = get_current_user()
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        user_role = get_user_role()
        if user_role not in ['admin', 'super_admin']:
            return jsonify({'error': 'Admin access required'}), 403

        with get_db_session() as session:
            review = session.query(ReviewQueue).filter(ReviewQueue.id == review_id).first()

            if not review:
                return jsonify({'error': 'Review not found'}), 404

            if review.status not in [ReviewStatus.FAILED, ReviewStatus.ESCALATED]:
                return jsonify({'error': 'Review cannot be retried'}), 400

            # Reset for retry
            review.status = ReviewStatus.PENDING
            review.result_code = None
            review.result_message = None
            review.retry_count += 1
            review.worker_id = None
            review.started_at = None
            review.completed_at = None

            session.commit()

            logger.info(f"🐝 Admin retry: Review {review_id} queued for retry")

            return jsonify({
                'success': True,
                'message': 'Review queued for retry',
                'data': {
                    'review': review.to_dict()
                }
            })

    except Exception as e:
        logger.error(f"Error retrying review {review_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Internal Worker Endpoints (no auth - internal service calls)
# ============================================================================

@qe_bee_bp.route('/internal/next-review', methods=['GET'])
def internal_get_next_review():
    """Internal: Get next pending review for worker"""
    try:
        worker_id = request.args.get('worker_id', f"qe-bee-{datetime.utcnow().timestamp()}")

        review_service = get_review_service()
        job = review_service.get_next_review(worker_id)

        if job:
            logger.debug(f"🐝 Worker {worker_id} assigned review: {job['id'][:8]}...")
            return jsonify({
                'success': True,
                'data': {'job': job}
            })
        else:
            return jsonify({
                'success': True,
                'data': {'job': None}
            })

    except Exception as e:
        logger.error(f"Error getting next review: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/internal/complete-review', methods=['POST'])
def internal_complete_review():
    """Internal: Mark review as complete"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        required_fields = ['review_id', 'worker_id', 'passed', 'result_code',
                          'result_message', 'confidence_score']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'{field} is required'}), 400

        review_service = get_review_service()
        success = review_service.complete_review(
            review_id=data['review_id'],
            worker_id=data['worker_id'],
            passed=data['passed'],
            result_code=data['result_code'],
            result_message=data['result_message'],
            confidence_score=data['confidence_score'],
            review_details=data.get('review_details')
        )

        if success:
            return jsonify({
                'success': True,
                'message': 'Review completed'
            })
        else:
            return jsonify({'error': 'Failed to complete review'}), 500

    except Exception as e:
        logger.error(f"Error completing review: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/internal/get-content', methods=['GET'])
def internal_get_content():
    """Internal: Get content for review"""
    try:
        target_type = request.args.get('target_type')
        target_id = request.args.get('target_id')

        if not target_type or not target_id:
            return jsonify({'error': 'target_type and target_id required'}), 400

        review_service = get_review_service()
        content = review_service.get_content_for_review(target_type, target_id)

        if content:
            return jsonify({
                'success': True,
                'data': content
            })
        else:
            return jsonify({'error': 'Content not found'}), 404

    except Exception as e:
        logger.error(f"Error getting content: {e}")
        return jsonify({'error': 'Internal server error'}), 500


@qe_bee_bp.route('/internal/queue-review', methods=['POST'])
def internal_queue_review():
    """Internal: Queue an item for review (called by report worker, etc.)"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        if not data.get('target_type') or not data.get('target_id'):
            return jsonify({'error': 'target_type and target_id required'}), 400

        review_service = get_review_service()
        review_id = review_service.queue_review(
            target_type=data['target_type'],
            target_id=data['target_id'],
            review_type=data.get('review_type', 'output_validation'),
            priority=data.get('priority', 5),
            user_id=data.get('user_id'),
            webhook_url=data.get('webhook_url')
        )

        if review_id:
            return jsonify({
                'success': True,
                'data': {
                    'review_id': review_id
                }
            }), 201
        else:
            return jsonify({'error': 'Failed to queue review'}), 500

    except Exception as e:
        logger.error(f"Error queuing review: {e}")
        return jsonify({'error': 'Internal server error'}), 500


# ============================================================================
# Health Check
# ============================================================================

@qe_bee_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for QE Bee service"""
    try:
        with get_db_session() as session:
            # Test database connectivity
            session.query(ReviewQueue).limit(1).all()

        return jsonify({
            'status': 'healthy',
            'service': 'qe-bee',
            'timestamp': datetime.utcnow().isoformat()
        })

    except Exception as e:
        logger.error(f"QE Bee health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'service': 'qe-bee',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500
