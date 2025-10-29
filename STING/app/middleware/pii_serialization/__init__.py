"""
PII Serialization Middleware

Provides intelligent PII detection, serialization, and deserialization for messages
sent to external AI services. Protects sensitive data while maintaining context.

Architecture:
- Detector: Identifies PII in messages
- Serializer: Converts PII to tokens (e.g., $Person1_first_name_hash)
- Deserializer: Restores PII in responses
- Cache Manager: Redis-based storage with TTL
- Audit Logger: Compliance and debugging

Usage:
    from app.middleware.pii_serialization import PIIMiddleware

    middleware = PIIMiddleware(config)

    # Serialize message before sending to external AI
    serialized_msg, context = await middleware.serialize_message(
        message="John Smith needs help",
        conversation_id="conv_123",
        mode="external"
    )

    # Deserialize response before returning to user
    deserialized_response = await middleware.deserialize_response(
        response="$Person1_first_name_hash can get help here",
        context=context
    )
"""

from .detector import PIIDetector
from .serializer import PIISerializer
from .deserializer import PIIDeserializer
from .cache_manager import PIICacheManager
from .audit_logger import PIIAuditLogger
from .config import PIIProtectionConfig

# Enhanced components (Opus additions)
from .enhanced_deserializer import EnhancedDeserializer
from .improved_cache_manager import ImprovedCacheManager
from .streaming_processor import StreamingPIIProcessor
from .mode_detector import ModeDetector

__version__ = "1.0.2"  # Bumped for mode detection
__all__ = [
    "PIIMiddleware",
    "PIIDetector",
    "PIISerializer",
    "PIIDeserializer",
    "PIICacheManager",
    "PIIAuditLogger",
    "PIIProtectionConfig",
    # Enhanced components
    "EnhancedDeserializer",
    "ImprovedCacheManager",
    "StreamingPIIProcessor",
    "ModeDetector",
]


class PIIMiddleware:
    """
    Main middleware class that orchestrates PII protection.

    Features:
    - Mode-based protection (local vs external)
    - Smart caching with TTL
    - Entity relationship preservation
    - Full audit trail
    - Performance optimized
    """

    def __init__(self, config: dict, redis_client=None):
        """
        Initialize PII middleware with configuration.

        Args:
            config: Security configuration from config.yml
            redis_client: Redis client (will create if None)
        """
        self.config = PIIProtectionConfig(config)
        self.detector = PIIDetector(self.config)
        self.serializer = PIISerializer(self.config)
        self.deserializer = PIIDeserializer(self.config)
        self.cache_manager = PIICacheManager(self.config, redis_client)
        self.audit_logger = PIIAuditLogger(self.config)

    async def serialize_message(
        self,
        message: str,
        conversation_id: str,
        user_id: str = None,
        mode: str = "external",
        error_context: bool = False
    ) -> tuple[str, dict]:
        """
        Serialize PII in a message before sending to AI service.

        Args:
            message: Original message with potential PII
            conversation_id: Unique conversation identifier
            user_id: User identifier (optional)
            mode: Protection mode (local/external)
            error_context: If True, use longer TTL for debugging

        Returns:
            Tuple of (serialized_message, serialization_context)

        Example:
            >>> msg = "John Smith at john@email.com needs help"
            >>> serialized, ctx = await middleware.serialize_message(msg, "conv_123")
            >>> print(serialized)
            "$Person1_first_name_hash at $Person1_email_hash needs help"
        """
        # Check if protection is enabled for this mode
        if not self.config.is_enabled_for_mode(mode):
            return message, {}

        # Detect PII in message
        pii_detections = await self.detector.detect(message, mode)

        if not pii_detections:
            return message, {}

        # Serialize PII to tokens
        serialized_message, pii_map = await self.serializer.serialize(
            message, pii_detections
        )

        # Determine TTL based on error context
        ttl = self.config.get_ttl(error_occurred=error_context)

        # Store in cache
        await self.cache_manager.store_mapping(
            conversation_id=conversation_id,
            pii_map=pii_map,
            ttl=ttl,
            user_id=user_id
        )

        # Audit log
        await self.audit_logger.log_serialization(
            conversation_id=conversation_id,
            user_id=user_id,
            mode=mode,
            pii_count=len(pii_detections),
            ttl=ttl
        )

        context = {
            "conversation_id": conversation_id,
            "pii_serialized": True,
            "pii_count": len(pii_detections),
            "mode": mode,
            "ttl": ttl
        }

        return serialized_message, context

    async def deserialize_response(
        self,
        response: str,
        context: dict
    ) -> str:
        """
        Deserialize PII tokens in AI response back to original values.

        Args:
            response: AI response with potential PII tokens
            context: Context from serialize_message()

        Returns:
            Response with PII tokens replaced with original values

        Example:
            >>> response = "I can help $Person1_first_name_hash with that"
            >>> deserialized = await middleware.deserialize_response(response, ctx)
            >>> print(deserialized)
            "I can help John Smith with that"
        """
        if not context.get("pii_serialized"):
            return response

        conversation_id = context.get("conversation_id")

        # Quick check: does response contain any tokens?
        if "$" not in response or "_hash" not in response:
            return response

        # Retrieve PII mapping from cache
        pii_map = await self.cache_manager.get_mapping(conversation_id)

        if not pii_map:
            # Cache expired or missing - log warning
            await self.audit_logger.log_cache_miss(conversation_id)
            return response

        # Deserialize tokens back to PII
        deserialized_response = await self.deserializer.deserialize(
            response, pii_map
        )

        # Audit log
        await self.audit_logger.log_deserialization(
            conversation_id=conversation_id,
            token_count=len(pii_map)
        )

        return deserialized_response

    async def deserialize_response_with_metadata(
        self,
        response: str,
        context: dict,
        enable_diagnostics: bool = False,
        track_positions: bool = True
    ) -> tuple[str, dict]:
        """
        Deserialize PII tokens with enhanced metadata for visual indicators.

        This enhanced version returns both the deserialized response AND metadata
        about what was protected (positions, types, risk levels) for frontend visualization.

        Args:
            response: AI response with potential PII tokens
            context: Context from serialize_message()
            enable_diagnostics: Include diagnostic information
            track_positions: Track PII positions for visual indicators

        Returns:
            Tuple of (deserialized_response, pii_metadata_dict)
            pii_metadata_dict includes:
                - tokens_found: Number of PII tokens detected
                - tokens_replaced: Number successfully replaced
                - pii_metadata: List of PII annotations with positions, types, risk levels

        Example:
            >>> response = "Hello $Person1_name_hash!"
            >>> deserialized, metadata = await middleware.deserialize_response_with_metadata(response, ctx)
            >>> print(deserialized)
            "Hello John Smith!"
            >>> print(metadata['pii_metadata'][0])
            {
                'deserialized_position': {'start': 6, 'end': 16},
                'pii_type': 'name',
                'risk_level': 'low',
                'deserialized_value': 'John Smith'
            }
        """
        if not context.get("pii_serialized"):
            return response, {'tokens_found': 0, 'pii_metadata': []}

        conversation_id = context.get("conversation_id")

        # Quick check: does response contain any tokens?
        if "$" not in response:
            return response, {'tokens_found': 0, 'pii_metadata': []}

        # Check if enhanced deserializer is available
        if isinstance(self.deserializer, EnhancedDeserializer):
            # Use enhanced deserializer with position tracking
            deserialized_response, metadata = await self.deserializer.deserialize_response(
                response=response,
                context=context,
                enable_diagnostics=enable_diagnostics,
                track_positions=track_positions
            )

            # Audit log
            await self.audit_logger.log_deserialization(
                conversation_id=conversation_id,
                token_count=metadata.get('tokens_replaced', 0)
            )

            return deserialized_response, metadata
        else:
            # Fallback to basic deserializer (no position tracking)
            pii_map = await self.cache_manager.get_mapping(conversation_id)

            if not pii_map:
                await self.audit_logger.log_cache_miss(conversation_id)
                return response, {
                    'error': 'cache_miss',
                    'tokens_found': 0,
                    'pii_metadata': []
                }

            deserialized_response = await self.deserializer.deserialize(response, pii_map)

            # Audit log
            await self.audit_logger.log_deserialization(
                conversation_id=conversation_id,
                token_count=len(pii_map)
            )

            # Return without position metadata (basic mode)
            return deserialized_response, {
                'tokens_found': len(pii_map),
                'tokens_replaced': len(pii_map),
                'pii_metadata': []  # No position tracking in basic mode
            }

    async def extend_cache_ttl(
        self,
        conversation_id: str,
        error_occurred: bool = False
    ):
        """
        Extend cache TTL (e.g., after an error for debugging).

        Args:
            conversation_id: Conversation to extend
            error_occurred: If True, use error TTL
        """
        ttl = self.config.get_ttl(error_occurred=error_occurred)
        await self.cache_manager.extend_ttl(conversation_id, ttl)

    async def clear_cache(self, conversation_id: str):
        """Clear PII cache for a conversation (e.g., on explicit user request)."""
        await self.cache_manager.delete_mapping(conversation_id)
        await self.audit_logger.log_cache_clear(conversation_id)

    async def cleanup(self):
        """Run cleanup to remove expired/old caches."""
        await self.cache_manager.cleanup()
