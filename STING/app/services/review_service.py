#!/usr/bin/env python3
"""
QE Bee Review Service
Manages the review queue and webhook notifications
"""

import logging
import hashlib
import hmac
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy import and_, or_

from app.database import db
from app.models.review_models import (
    ReviewQueue, ReviewHistory, WebhookConfig,
    ReviewTargetType, ReviewType, ReviewStatus, ReviewResultCode
)

logger = logging.getLogger(__name__)


class ReviewService:
    """Service for managing QE Bee review queue and notifications"""

    def __init__(self):
        self.webhook_timeout = 10  # seconds
        self.max_webhook_retries = 3

    def queue_review(
        self,
        target_type: str,
        target_id: str,
        review_type: str = 'output_validation',
        priority: int = 5,
        user_id: str = None,
        webhook_url: str = None
    ) -> Optional[str]:
        """
        Add an item to the review queue.

        Args:
            target_type: Type of item (report, message, document, pii_detection)
            target_id: ID of the item to review
            review_type: Type of review to perform
            priority: Queue priority (1=highest, 10=lowest)
            user_id: Owner of the item
            webhook_url: Optional webhook URL for notification

        Returns:
            Review queue ID or None on error
        """
        try:
            # Convert string enums
            target_type_enum = ReviewTargetType(target_type)
            review_type_enum = ReviewType(review_type)

            # Check if already queued (avoid duplicates)
            existing = ReviewQueue.query.filter(
                and_(
                    ReviewQueue.target_type == target_type_enum,
                    ReviewQueue.target_id == target_id,
                    ReviewQueue.status.in_([ReviewStatus.PENDING, ReviewStatus.REVIEWING])
                )
            ).first()

            if existing:
                logger.info(f"Review already queued for {target_type}:{target_id}")
                return str(existing.id)

            # Create review queue entry
            review = ReviewQueue(
                target_type=target_type_enum,
                target_id=target_id,
                review_type=review_type_enum,
                priority=priority,
                status=ReviewStatus.PENDING,
                user_id=user_id,
                webhook_url=webhook_url
            )

            db.session.add(review)
            db.session.commit()

            logger.info(f"🐝 Queued review: {target_type}:{target_id[:8]}... (priority={priority})")
            return str(review.id)

        except Exception as e:
            logger.error(f"Failed to queue review: {e}")
            db.session.rollback()
            return None

    def get_next_review(self, worker_id: str) -> Optional[Dict]:
        """
        Get the next pending review for a worker.

        Args:
            worker_id: ID of the requesting worker

        Returns:
            Review job dict or None if no jobs available
        """
        try:
            # Find highest priority pending review
            review = ReviewQueue.query.filter(
                ReviewQueue.status == ReviewStatus.PENDING
            ).order_by(
                ReviewQueue.priority.asc(),
                ReviewQueue.created_at.asc()
            ).with_for_update(skip_locked=True).first()

            if not review:
                return None

            # Mark as reviewing
            review.status = ReviewStatus.REVIEWING
            review.worker_id = worker_id
            review.started_at = datetime.utcnow()
            db.session.commit()

            return {
                'id': str(review.id),
                'target_type': review.target_type.value,
                'target_id': review.target_id,
                'review_type': review.review_type.value,
                'priority': review.priority,
                'user_id': review.user_id,
                'webhook_url': review.webhook_url,
                'created_at': review.created_at.isoformat()
            }

        except Exception as e:
            logger.error(f"Failed to get next review: {e}")
            db.session.rollback()
            return None

    def complete_review(
        self,
        review_id: str,
        worker_id: str,
        passed: bool,
        result_code: str,
        result_message: str,
        confidence_score: int,
        review_details: Dict = None
    ) -> bool:
        """
        Mark a review as complete and optionally send webhook.

        Args:
            review_id: ID of the review
            worker_id: ID of the worker
            passed: Whether the review passed
            result_code: Result code (e.g., PASS, PII_TOKENS_REMAINING)
            result_message: Human-readable result message
            confidence_score: Confidence 0-100
            review_details: Additional details dict

        Returns:
            True on success
        """
        try:
            review = ReviewQueue.query.get(review_id)
            if not review:
                logger.error(f"Review not found: {review_id}")
                return False

            # Update review status
            review.status = ReviewStatus.PASSED if passed else ReviewStatus.FAILED
            review.result_code = ReviewResultCode(result_code)
            review.result_message = result_message
            review.confidence_score = confidence_score
            review.review_details = review_details
            review.completed_at = datetime.utcnow()

            # Save to history
            history = ReviewHistory(
                queue_id=review.id,
                target_type=review.target_type,
                target_id=review.target_id,
                review_type=review.review_type,
                result_code=review.result_code,
                result_message=result_message,
                confidence_score=confidence_score,
                review_details=review_details,
                worker_id=worker_id,
                model_used=review_details.get('model_used') if review_details else None,
                processing_time_ms=review_details.get('processing_time_ms') if review_details else None,
                user_id=review.user_id
            )
            db.session.add(history)

            db.session.commit()

            # Send webhook notification
            if review.webhook_url:
                self._send_webhook(review)
            elif review.user_id:
                # Check for user's configured webhooks
                self._send_user_webhooks(review)

            logger.info(f"🐝 Review complete: {review_id[:8]}... -> {result_code}")
            return True

        except Exception as e:
            logger.error(f"Failed to complete review: {e}")
            db.session.rollback()
            return False

    def get_content_for_review(self, target_type: str, target_id: str) -> Optional[Dict]:
        """
        Fetch content to review based on target type.

        Returns:
            Dict with 'content' and 'metadata' keys
        """
        try:
            if target_type == 'report':
                return self._get_report_content(target_id)
            elif target_type == 'message':
                return self._get_message_content(target_id)
            elif target_type == 'document':
                return self._get_document_content(target_id)
            else:
                logger.warning(f"Unknown target type: {target_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to get content for review: {e}")
            return None

    def _get_report_content(self, report_id: str) -> Optional[Dict]:
        """Get report content for review"""
        from app.models.report_models import Report
        from app.services.file_service import FileService

        report = Report.query.get(report_id)
        if not report:
            return None

        # Try to get generated content from file
        content = ""
        if report.result_file_id:
            try:
                file_service = FileService()
                file_data = file_service.get_file(report.result_file_id)
                if file_data and file_data.get('content'):
                    content = file_data['content']
            except:
                pass

        # Fall back to summary if available
        if not content and report.result_summary:
            content = json.dumps(report.result_summary)

        return {
            'content': content,
            'metadata': {
                'report_id': str(report.id),
                'title': report.title,
                'status': report.status.value if report.status else None,
                'template': report.template.name if report.template else None,
                'user_id': str(report.user_id) if report.user_id else None
            }
        }

    def _get_message_content(self, message_id: str) -> Optional[Dict]:
        """Get message content for review"""
        # This would integrate with the messaging database
        # For now, return placeholder
        return {
            'content': '',
            'metadata': {'message_id': message_id}
        }

    def _get_document_content(self, document_id: str) -> Optional[Dict]:
        """Get document content for review"""
        # This would integrate with the document storage
        # For now, return placeholder
        return {
            'content': '',
            'metadata': {'document_id': document_id}
        }

    def _send_webhook(self, review: ReviewQueue) -> bool:
        """Send webhook notification for a review"""
        if not review.webhook_url:
            return False

        try:
            payload = {
                'event': 'review.completed',
                'review_id': str(review.id),
                'target_type': review.target_type.value,
                'target_id': review.target_id,
                'result': {
                    'passed': review.status == ReviewStatus.PASSED,
                    'code': review.result_code.value if review.result_code else None,
                    'message': review.result_message,
                    'confidence': review.confidence_score
                },
                'timestamp': datetime.utcnow().isoformat(),
                'user_id': review.user_id
            }

            response = requests.post(
                review.webhook_url,
                json=payload,
                timeout=self.webhook_timeout,
                headers={'Content-Type': 'application/json'}
            )

            review.webhook_sent = True
            review.webhook_sent_at = datetime.utcnow()
            review.webhook_response_code = response.status_code
            db.session.commit()

            return response.status_code < 400

        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            return False

    def _send_user_webhooks(self, review: ReviewQueue) -> int:
        """Send webhooks to all configured endpoints for a user"""
        if not review.user_id:
            return 0

        configs = WebhookConfig.query.filter(
            and_(
                WebhookConfig.user_id == review.user_id,
                WebhookConfig.is_active == True
            )
        ).all()

        sent_count = 0
        for config in configs:
            # Check filters
            if config.target_types and review.target_type.value not in config.target_types:
                continue
            if config.result_codes and review.result_code.value not in config.result_codes:
                continue

            # Temporarily set webhook URL and send
            review.webhook_url = config.url
            if self._send_webhook(review):
                config.total_sent += 1
                config.last_sent_at = datetime.utcnow()
                sent_count += 1
            else:
                config.total_failed += 1
                config.last_error = f"Failed at {datetime.utcnow().isoformat()}"

        if sent_count > 0:
            db.session.commit()

        return sent_count

    def get_review_stats(self, user_id: str = None) -> Dict:
        """Get review statistics"""
        try:
            query = ReviewHistory.query

            if user_id:
                query = query.filter(ReviewHistory.user_id == user_id)

            total = query.count()
            passed = query.filter(ReviewHistory.result_code == ReviewResultCode.PASS).count()
            passed_warnings = query.filter(ReviewHistory.result_code == ReviewResultCode.PASS_WITH_WARNINGS).count()
            failed = total - passed - passed_warnings

            # Get pending count
            pending_query = ReviewQueue.query.filter(ReviewQueue.status == ReviewStatus.PENDING)
            if user_id:
                pending_query = pending_query.filter(ReviewQueue.user_id == user_id)
            pending = pending_query.count()

            return {
                'total_reviews': total,
                'passed': passed,
                'passed_with_warnings': passed_warnings,
                'failed': failed,
                'pending': pending,
                'pass_rate': round((passed + passed_warnings) / total * 100, 1) if total > 0 else 0
            }

        except Exception as e:
            logger.error(f"Failed to get review stats: {e}")
            return {}

    def get_recent_reviews(self, limit: int = 20, user_id: str = None) -> List[Dict]:
        """Get recent review history"""
        try:
            query = ReviewHistory.query

            if user_id:
                query = query.filter(ReviewHistory.user_id == user_id)

            reviews = query.order_by(ReviewHistory.created_at.desc()).limit(limit).all()

            return [r.to_dict() for r in reviews]

        except Exception as e:
            logger.error(f"Failed to get recent reviews: {e}")
            return []


# Global instance
_review_service = None


def get_review_service() -> ReviewService:
    """Get or create global review service instance"""
    global _review_service
    if _review_service is None:
        _review_service = ReviewService()
    return _review_service
