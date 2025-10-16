"""
PII Audit Logger

Logs PII serialization/deserialization events for compliance and debugging.

Features:
- Structured logging
- No PII in logs (only metadata)
- Configurable verbosity
- Database audit trail
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class PIIAuditLogger:
    """
    Audit logger for PII protection events.

    Logs serialization, deserialization, and cache events without exposing PII.
    """

    def __init__(self, config):
        """
        Initialize audit logger with configuration.

        Args:
            config: PIIProtectionConfig instance
        """
        self.config = config
        self.should_log_serialization = config.should_log_serialization()
        self.should_log_deserialization = config.should_log_deserialization()
        self.should_log_cache_ops = config.should_log_cache_ops()

    async def log_serialization(
        self,
        conversation_id: str,
        user_id: Optional[str],
        mode: str,
        pii_count: int,
        ttl: int
    ):
        """
        Log PII serialization event.

        Args:
            conversation_id: Conversation identifier
            user_id: User identifier
            mode: Protection mode
            pii_count: Number of PII items serialized
            ttl: Cache TTL applied
        """
        if not self.should_log_serialization:
            return

        logger.info(
            "PII_SERIALIZATION",
            extra={
                "event_type": "pii_serialization",
                "conversation_id": conversation_id,
                "user_id": user_id or "anonymous",
                "mode": mode,
                "pii_count": pii_count,
                "ttl_seconds": ttl,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def log_deserialization(
        self,
        conversation_id: str,
        token_count: int
    ):
        """
        Log PII deserialization event.

        Args:
            conversation_id: Conversation identifier
            token_count: Number of tokens replaced
        """
        if not self.should_log_deserialization:
            return

        logger.info(
            "PII_DESERIALIZATION",
            extra={
                "event_type": "pii_deserialization",
                "conversation_id": conversation_id,
                "token_count": token_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def log_cache_miss(self, conversation_id: str):
        """
        Log cache miss (expired or not found).

        Args:
            conversation_id: Conversation identifier
        """
        logger.warning(
            "PII_CACHE_MISS",
            extra={
                "event_type": "pii_cache_miss",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def log_cache_clear(self, conversation_id: str):
        """
        Log explicit cache clear.

        Args:
            conversation_id: Conversation identifier
        """
        if not self.should_log_cache_ops:
            return

        logger.info(
            "PII_CACHE_CLEAR",
            extra={
                "event_type": "pii_cache_clear",
                "conversation_id": conversation_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def log_protection_disabled(self, mode: str, reason: str):
        """
        Log that protection was disabled for a mode.

        Args:
            mode: Protection mode
            reason: Reason for disabling
        """
        logger.info(
            "PII_PROTECTION_DISABLED",
            extra={
                "event_type": "pii_protection_disabled",
                "mode": mode,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    async def log_error(
        self,
        conversation_id: str,
        error_type: str,
        error_message: str
    ):
        """
        Log PII middleware error.

        Args:
            conversation_id: Conversation identifier
            error_type: Type of error
            error_message: Error message
        """
        logger.error(
            "PII_MIDDLEWARE_ERROR",
            extra={
                "event_type": "pii_middleware_error",
                "conversation_id": conversation_id,
                "error_type": error_type,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
