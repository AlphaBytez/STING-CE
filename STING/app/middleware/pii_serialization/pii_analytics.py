"""
PII Analytics Module

Real-time analytics and metrics for PII serialization/deserialization.
Stores metrics in Redis for dashboard visualization.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


class PIIAnalytics:
    """
    Real-time analytics for PII protection operations.
    
    Tracks:
    - Serialization events (count, types, modes)
    - Deserialization events (success, failures)
    - Protection modes used
    - PII types detected
    - Provider distribution
    """

    def __init__(self, redis_client=None):
        """
        Initialize PII analytics.
        
        Args:
            redis_client: Optional Redis client for persistent storage
        """
        self.redis = redis_client
        self.prefix = "sting:pii:analytics:"
        
        # In-memory fallback for when Redis is unavailable
        self._local_metrics = {
            'serialization_count': 0,
            'deserialization_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_pii_items': 0,
            'protection_modes': defaultdict(int),
            'pii_types': defaultdict(int),
            'providers': defaultdict(int),
            'hourly_requests': defaultdict(int),
            'errors': 0,
            'last_updated': None
        }
        
        # Track events for time-series
        self._recent_events: List[Dict] = []
        self._max_events = 1000  # Keep last 1000 events

    async def record_serialization(
        self,
        conversation_id: str,
        user_id: Optional[str],
        mode: str,
        pii_count: int,
        pii_types: List[str],
        provider: str,
        is_cloud_provider: bool
    ):
        """
        Record a PII serialization event.
        
        Args:
            conversation_id: Conversation identifier
            user_id: User identifier
            mode: Protection mode (external, local, trusted)
            pii_count: Number of PII items serialized
            pii_types: List of PII type names
            provider: LLM provider name
            is_cloud_provider: Whether this is a cloud provider
        """
        timestamp = datetime.utcnow()
        hour_key = timestamp.strftime("%Y-%m-%d-%H")
        
        # Update local metrics
        self._local_metrics['serialization_count'] += 1
        self._local_metrics['total_pii_items'] += pii_count
        self._local_metrics['protection_modes'][mode] += 1
        self._local_metrics['providers'][provider] += 1
        self._local_metrics['hourly_requests'][hour_key] += 1
        self._local_metrics['last_updated'] = timestamp.isoformat()
        
        for pii_type in pii_types:
            self._local_metrics['pii_types'][pii_type] += 1
        
        # Add to recent events
        event = {
            'type': 'serialization',
            'conversation_id': conversation_id[:8] + '...' if conversation_id else None,  # Truncate for privacy
            'mode': mode,
            'pii_count': pii_count,
            'pii_types': pii_types,
            'provider': provider,
            'is_cloud': is_cloud_provider,
            'timestamp': timestamp.isoformat()
        }
        self._add_event(event)
        
        # Persist to Redis if available
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.hincrby(f"{self.prefix}counters", "serialization_count", 1)
                pipe.hincrby(f"{self.prefix}counters", "total_pii_items", pii_count)
                pipe.hincrby(f"{self.prefix}modes", mode, 1)
                pipe.hincrby(f"{self.prefix}providers", provider, 1)
                pipe.hincrby(f"{self.prefix}hourly:{hour_key}", "requests", 1)
                
                for pii_type in pii_types:
                    pipe.hincrby(f"{self.prefix}pii_types", pii_type, 1)
                
                await asyncio.to_thread(pipe.execute)
            except Exception as e:
                logger.warning(f"Failed to persist serialization metrics: {e}")

    async def record_deserialization(
        self,
        conversation_id: str,
        tokens_found: int,
        tokens_replaced: int,
        tokens_missed: int
    ):
        """
        Record a PII deserialization event.
        
        Args:
            conversation_id: Conversation identifier
            tokens_found: Number of tokens found in response
            tokens_replaced: Number of tokens successfully replaced
            tokens_missed: Number of tokens that couldn't be replaced
        """
        timestamp = datetime.utcnow()
        
        self._local_metrics['deserialization_count'] += 1
        if tokens_missed == 0 and tokens_found > 0:
            self._local_metrics['cache_hits'] += tokens_replaced
        else:
            self._local_metrics['cache_misses'] += tokens_missed
        self._local_metrics['last_updated'] = timestamp.isoformat()
        
        event = {
            'type': 'deserialization',
            'conversation_id': conversation_id[:8] + '...' if conversation_id else None,
            'tokens_found': tokens_found,
            'tokens_replaced': tokens_replaced,
            'tokens_missed': tokens_missed,
            'success': tokens_missed == 0,
            'timestamp': timestamp.isoformat()
        }
        self._add_event(event)
        
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                pipe.hincrby(f"{self.prefix}counters", "deserialization_count", 1)
                pipe.hincrby(f"{self.prefix}counters", "cache_hits", tokens_replaced)
                pipe.hincrby(f"{self.prefix}counters", "cache_misses", tokens_missed)
                await asyncio.to_thread(pipe.execute)
            except Exception as e:
                logger.warning(f"Failed to persist deserialization metrics: {e}")

    async def record_error(self, error_type: str, conversation_id: Optional[str] = None):
        """Record a PII middleware error."""
        self._local_metrics['errors'] += 1
        
        event = {
            'type': 'error',
            'error_type': error_type,
            'conversation_id': conversation_id[:8] + '...' if conversation_id else None,
            'timestamp': datetime.utcnow().isoformat()
        }
        self._add_event(event)
        
        if self.redis:
            try:
                await asyncio.to_thread(
                    self.redis.hincrby,
                    f"{self.prefix}counters", "errors", 1
                )
            except Exception as e:
                logger.warning(f"Failed to persist error metric: {e}")

    def _add_event(self, event: Dict):
        """Add event to recent events list with size limit."""
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_events:
            self._recent_events = self._recent_events[-self._max_events:]

    async def get_analytics(self) -> Dict[str, Any]:
        """
        Get comprehensive PII analytics.
        
        Returns:
            Dictionary with all analytics data
        """
        # Try Redis first
        if self.redis:
            try:
                return await self._get_redis_analytics()
            except Exception as e:
                logger.warning(f"Redis analytics unavailable: {e}")
        
        # Fall back to local metrics
        return self._get_local_analytics()

    async def _get_redis_analytics(self) -> Dict[str, Any]:
        """Get analytics from Redis."""
        pipe = self.redis.pipeline()
        pipe.hgetall(f"{self.prefix}counters")
        pipe.hgetall(f"{self.prefix}modes")
        pipe.hgetall(f"{self.prefix}providers")
        pipe.hgetall(f"{self.prefix}pii_types")
        
        results = await asyncio.to_thread(pipe.execute)
        
        counters = {k.decode(): int(v) for k, v in (results[0] or {}).items()}
        modes = {k.decode(): int(v) for k, v in (results[1] or {}).items()}
        providers = {k.decode(): int(v) for k, v in (results[2] or {}).items()}
        pii_types = {k.decode(): int(v) for k, v in (results[3] or {}).items()}
        
        total_ops = counters.get('serialization_count', 0) + counters.get('deserialization_count', 0)
        cache_ops = counters.get('cache_hits', 0) + counters.get('cache_misses', 0)
        
        return {
            'summary': {
                'total_operations': total_ops,
                'serializations': counters.get('serialization_count', 0),
                'deserializations': counters.get('deserialization_count', 0),
                'total_pii_items_protected': counters.get('total_pii_items', 0),
                'cache_hit_rate': round(counters.get('cache_hits', 0) / cache_ops * 100, 2) if cache_ops > 0 else 0,
                'error_rate': round(counters.get('errors', 0) / total_ops * 100, 2) if total_ops > 0 else 0,
            },
            'protection_modes': modes,
            'providers': providers,
            'pii_types_detected': pii_types,
            'cache_stats': {
                'hits': counters.get('cache_hits', 0),
                'misses': counters.get('cache_misses', 0),
                'hit_rate': round(counters.get('cache_hits', 0) / cache_ops * 100, 2) if cache_ops > 0 else 0
            },
            'errors': counters.get('errors', 0),
            'recent_events': self._recent_events[-20:],  # Last 20 events
            'source': 'redis',
            'timestamp': datetime.utcnow().isoformat()
        }

    def _get_local_analytics(self) -> Dict[str, Any]:
        """Get analytics from local memory."""
        total_ops = self._local_metrics['serialization_count'] + self._local_metrics['deserialization_count']
        cache_ops = self._local_metrics['cache_hits'] + self._local_metrics['cache_misses']
        
        return {
            'summary': {
                'total_operations': total_ops,
                'serializations': self._local_metrics['serialization_count'],
                'deserializations': self._local_metrics['deserialization_count'],
                'total_pii_items_protected': self._local_metrics['total_pii_items'],
                'cache_hit_rate': round(self._local_metrics['cache_hits'] / cache_ops * 100, 2) if cache_ops > 0 else 0,
                'error_rate': round(self._local_metrics['errors'] / total_ops * 100, 2) if total_ops > 0 else 0,
            },
            'protection_modes': dict(self._local_metrics['protection_modes']),
            'providers': dict(self._local_metrics['providers']),
            'pii_types_detected': dict(self._local_metrics['pii_types']),
            'cache_stats': {
                'hits': self._local_metrics['cache_hits'],
                'misses': self._local_metrics['cache_misses'],
                'hit_rate': round(self._local_metrics['cache_hits'] / cache_ops * 100, 2) if cache_ops > 0 else 0
            },
            'errors': self._local_metrics['errors'],
            'hourly_distribution': dict(self._local_metrics['hourly_requests']),
            'recent_events': self._recent_events[-20:],
            'source': 'local_memory',
            'last_updated': self._local_metrics['last_updated'],
            'timestamp': datetime.utcnow().isoformat()
        }

    async def get_summary_stats(self) -> Dict[str, Any]:
        """Get quick summary statistics for dashboard."""
        analytics = await self.get_analytics()
        
        return {
            'pii_items_protected': analytics['summary']['total_pii_items_protected'],
            'operations_today': analytics['summary']['total_operations'],
            'cache_hit_rate': analytics['cache_stats']['hit_rate'],
            'primary_mode': max(analytics['protection_modes'].items(), key=lambda x: x[1])[0] if analytics['protection_modes'] else 'none',
            'top_pii_types': sorted(
                analytics['pii_types_detected'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:5],
            'top_providers': sorted(
                analytics['providers'].items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            'health': 'healthy' if analytics['summary']['error_rate'] < 5 else 'degraded',
            'timestamp': datetime.utcnow().isoformat()
        }

    def reset_metrics(self):
        """Reset all local metrics (for testing)."""
        self._local_metrics = {
            'serialization_count': 0,
            'deserialization_count': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'total_pii_items': 0,
            'protection_modes': defaultdict(int),
            'pii_types': defaultdict(int),
            'providers': defaultdict(int),
            'hourly_requests': defaultdict(int),
            'errors': 0,
            'last_updated': None
        }
        self._recent_events = []


# Singleton instance
_analytics_instance: Optional[PIIAnalytics] = None


def get_analytics_instance(redis_client=None) -> PIIAnalytics:
    """Get or create the analytics singleton."""
    global _analytics_instance
    if _analytics_instance is None:
        _analytics_instance = PIIAnalytics(redis_client)
    return _analytics_instance
