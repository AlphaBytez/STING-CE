"""
Enhanced External AI Service Integration with Improved PII Handling
This file shows the key changes needed in app.py for seamless PII handling
"""
import asyncio
from typing import Dict, Optional
import logging

# Import enhanced PII components
from app.middleware.pii_serialization.enhanced_deserializer import EnhancedDeserializer
from app.middleware.pii_serialization.streaming_processor import StreamingPIIProcessor
from app.middleware.pii_serialization.improved_cache_manager import ImprovedCacheManager

logger = logging.getLogger(__name__)

class EnhancedPIIMiddleware:
    """
    Enhanced PII Middleware that integrates all optimizations.
    This replaces the standard PIIMiddleware for better performance.
    """

    def __init__(self, config: Dict):
        self.config = config
        self.enabled = config.get('message_pii_protection', {}).get('enabled', True)

        # Initialize enhanced components
        redis_url = f"redis://redis:6379/{config.get('message_pii_protection', {}).get('serialization', {}).get('redis_db', 3)}"
        self.cache_manager = ImprovedCacheManager(redis_url)
        self.deserializer = EnhancedDeserializer(self.cache_manager)
        self.streaming_processor = StreamingPIIProcessor(self.cache_manager)

        # Store active conversations for pre-warming
        self.active_conversations = set()
        self.max_active_conversations = 100

    async def initialize(self):
        """Initialize connections and warm up cache"""
        await self.cache_manager.connect()
        logger.info("Enhanced PII Middleware initialized")

    async def serialize_message(
        self,
        message: str,
        conversation_id: str,
        user_id: str,
        mode: str = "external"
    ) -> tuple[str, Dict]:
        """
        Serialize PII in message before sending to LLM.
        Returns (serialized_message, context_with_mapping)
        """
        if not self.enabled:
            return message, {}

        # Import the standard serializer (reuse existing logic)
        from app.middleware.pii_serialization.serializer import PIISerializer
        from app.middleware.pii_serialization.detector import PIIDetector

        detector = PIIDetector()
        serializer = PIISerializer()

        # Detect PII
        pii_detections = detector.detect_all_pii(message)
        if not pii_detections:
            return message, {}

        # Serialize PII
        serialized_message, pii_mapping = serializer.serialize_pii(message, pii_detections)

        # Store mapping with improved cache manager
        ttl = self.config.get('message_pii_protection', {}).get('serialization', {}).get('cache_ttl', {}).get('default', 300)
        await self.cache_manager.store_pii_mapping(
            conversation_id=conversation_id,
            pii_mapping=pii_mapping,
            ttl=ttl,
            metadata={
                'user_id': user_id,
                'mode': mode,
                'pii_count': len(pii_mapping)
            }
        )

        # Track active conversation
        self.active_conversations.add(conversation_id)
        if len(self.active_conversations) > self.max_active_conversations:
            self.active_conversations.pop()

        # Return context with embedded mapping for fallback
        context = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'pii_mapping': pii_mapping,  # Embed for fallback
            'pii_count': len(pii_mapping)
        }

        logger.info(f"Serialized {len(pii_mapping)} PII items for conversation {conversation_id}")
        return serialized_message, context

    async def deserialize_response(
        self,
        response: str,
        context: Dict,
        enable_diagnostics: bool = False
    ) -> str:
        """
        Deserialize PII in response with enhanced error handling.
        """
        if not self.enabled or not context:
            return response

        # Use enhanced deserializer
        deserialized_response, diagnostics = await self.deserializer.deserialize_response(
            response=response,
            context=context,
            enable_diagnostics=enable_diagnostics
        )

        # Log diagnostics if issues detected
        if diagnostics.get('tokens_missed', 0) > 0:
            logger.warning(
                f"PII deserialization incomplete - "
                f"Replaced: {diagnostics.get('tokens_replaced', 0)}, "
                f"Missed: {diagnostics.get('tokens_missed', 0)}"
            )

            # Extend TTL for problematic conversations
            conversation_id = context.get('conversation_id')
            if conversation_id:
                await self.cache_manager.extend_ttl(conversation_id, 600)  # Extend by 10 min

        return deserialized_response

    async def process_streaming_response(
        self,
        response_stream,
        conversation_id: str
    ):
        """
        Process streaming response with real-time PII deserialization.
        """
        if not self.enabled:
            async for chunk in response_stream:
                yield chunk
            return

        # Pre-fetch mapping for better performance
        pii_mapping = await self.cache_manager.get_pii_mapping(conversation_id)

        async for chunk in self.streaming_processor.process_stream(
            response_stream=response_stream,
            conversation_id=conversation_id,
            pii_mapping=pii_mapping
        ):
            yield chunk

    async def warm_cache_for_active_conversations(self):
        """Pre-warm cache for active conversations"""
        if self.active_conversations:
            await self.streaming_processor.warm_cache(list(self.active_conversations))

    def get_diagnostics(self) -> Dict:
        """Get comprehensive diagnostics"""
        return {
            'cache_diagnostics': self.cache_manager.get_diagnostics(),
            'deserializer_report': self.deserializer.get_diagnostics_report(),
            'active_conversations': len(self.active_conversations),
            'enabled': self.enabled
        }


# Updated bee_chat endpoint with enhanced PII handling
async def enhanced_bee_chat(request, pii_middleware: EnhancedPIIMiddleware):
    """
    Enhanced Bee chat endpoint with improved PII handling.
    This shows the key changes needed in the existing bee_chat function.
    """
    try:
        # ... existing initialization code ...

        # PII Protection: Serialize before sending to LLM
        pii_context = {}
        if pii_middleware:
            try:
                enhanced_prompt, pii_context = await pii_middleware.serialize_message(
                    message=enhanced_prompt,
                    conversation_id=request.conversation_id or f"conv_{int(datetime.now().timestamp())}",
                    user_id=request.user_id,
                    mode="external"
                )

                # Pre-warm cache for better response time
                await pii_middleware.warm_cache_for_active_conversations()

            except Exception as e:
                logger.error(f"PII serialization failed: {e}")
                # Continue without serialization but log for monitoring

        # ... send to Ollama ...
        result = await ollama_client.generate(model_name, enhanced_prompt)

        # ... clean response ...

        # PII Protection: Enhanced deserialization with diagnostics
        if pii_middleware and pii_context:
            try:
                # Enable diagnostics in development/debug mode
                enable_diagnostics = request.debug_mode or os.getenv('DEBUG') == 'true'

                clean_response = await pii_middleware.deserialize_response(
                    response=clean_response,
                    context=pii_context,
                    enable_diagnostics=enable_diagnostics
                )

                # Check diagnostics and log if needed
                if enable_diagnostics:
                    diagnostics = pii_middleware.get_diagnostics()
                    if diagnostics['cache_diagnostics']['cache_stats']['misses'] > 10:
                        logger.warning(f"High cache miss rate detected: {diagnostics}")

            except Exception as e:
                logger.error(f"PII deserialization failed critically: {e}")
                # Return a user-friendly error message
                return {
                    "response": "I apologize, but I encountered an issue processing your request. Please try again.",
                    "error": "pii_processing_failed",
                    "conversation_id": request.conversation_id,
                    "retry_suggested": True
                }

        # ... rest of the response handling ...

        return {
            "response": clean_response.strip(),
            "conversation_id": conversation_id,
            "timestamp": datetime.now().isoformat(),
            "pii_protection_active": bool(pii_context),  # Indicate PII protection status
            # ... other response fields ...
        }

    except Exception as e:
        logger.error(f"Failed to process Bee chat: {e}")
        raise


# Background task for cache maintenance
async def pii_cache_maintenance_task(pii_middleware: EnhancedPIIMiddleware):
    """
    Background task to maintain PII cache health.
    Run this as a background task in the FastAPI app.
    """
    while True:
        try:
            # Clean up expired entries
            await pii_middleware.cache_manager.cleanup_expired()

            # Pre-warm cache for active conversations
            await pii_middleware.warm_cache_for_active_conversations()

            # Log diagnostics periodically
            diagnostics = pii_middleware.get_diagnostics()
            cache_stats = diagnostics['cache_diagnostics']['cache_stats']

            if cache_stats['errors'] > 0:
                logger.warning(f"PII cache errors detected: {cache_stats}")

            # Sleep for 5 minutes
            await asyncio.sleep(300)

        except Exception as e:
            logger.error(f"Cache maintenance task error: {e}")
            await asyncio.sleep(60)  # Retry after 1 minute on error


# Monitoring endpoint for PII system health
async def pii_diagnostics_endpoint(pii_middleware: EnhancedPIIMiddleware):
    """
    Health check endpoint for PII system monitoring.
    Add this as a new endpoint: GET /api/pii/diagnostics
    """
    diagnostics = pii_middleware.get_diagnostics()

    # Calculate health score
    cache_stats = diagnostics['cache_diagnostics']['cache_stats']
    total_requests = cache_stats['hits'] + cache_stats['misses']

    if total_requests > 0:
        hit_rate = cache_stats['hits'] / total_requests
        health_score = "healthy" if hit_rate > 0.8 else "degraded" if hit_rate > 0.5 else "unhealthy"
    else:
        health_score = "no_data"

    return {
        "status": health_score,
        "hit_rate": hit_rate if total_requests > 0 else 0,
        "diagnostics": diagnostics,
        "recommendations": _get_pii_recommendations(diagnostics)
    }


def _get_pii_recommendations(diagnostics: Dict) -> list[str]:
    """Generate recommendations based on diagnostics"""
    recommendations = []

    cache_stats = diagnostics['cache_diagnostics']['cache_stats']

    if cache_stats['misses'] > cache_stats['hits']:
        recommendations.append("High cache miss rate - consider increasing TTL in config.yml")

    if cache_stats['errors'] > 10:
        recommendations.append("Redis connection issues detected - check Redis connectivity")

    if cache_stats['fallback_used'] > 100:
        recommendations.append("Heavy fallback usage - Redis may be unavailable")

    if diagnostics['active_conversations'] > 50:
        recommendations.append("Many active conversations - consider scaling Redis or increasing memory")

    return recommendations