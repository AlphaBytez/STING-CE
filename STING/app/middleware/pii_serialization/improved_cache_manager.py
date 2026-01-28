"""
Improved Cache Manager with Enhanced Error Handling and Diagnostics
"""
import asyncio
import json
import time
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta
import redis.asyncio as redis
import logging

logger = logging.getLogger(__name__)

class ImprovedCacheManager:
    """Enhanced cache manager with better resilience and diagnostics"""

    def __init__(self, redis_url: str = "redis://redis:6379/3"):
        self.redis_url = redis_url
        self.redis_client: Optional[redis.Redis] = None
        self.local_cache: Dict[str, Dict] = {}  # In-memory fallback
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'fallback_used': 0,
            'last_error': None
        }
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

    async def connect(self):
        """Establish Redis connection with retry logic"""
        for attempt in range(self.max_reconnect_attempts):
            try:
                self.redis_client = await redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True
                )
                await self.redis_client.ping()
                logger.info(f"Connected to Redis on attempt {attempt + 1}")
                self.reconnect_attempts = 0
                return
            except Exception as e:
                logger.error(f"Redis connection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(min(2 ** attempt, 30))  # Exponential backoff

        logger.error("Failed to connect to Redis after max attempts, using local fallback")
        self.redis_client = None

    async def store_pii_mapping(
        self,
        conversation_id: str,
        pii_mapping: Dict[str, str],
        ttl: int = 300,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Store PII mapping with enhanced error handling and local fallback.

        Args:
            conversation_id: Unique conversation identifier
            pii_mapping: Token to value mapping
            ttl: Time to live in seconds
            metadata: Additional metadata to store

        Returns:
            Success status
        """
        key = f"sting:pii:conv:{conversation_id}:map"
        meta_key = f"sting:pii:conv:{conversation_id}:meta"

        # Always store in local cache as backup
        self.local_cache[conversation_id] = {
            'mapping': pii_mapping,
            'metadata': metadata or {},
            'expires_at': time.time() + ttl
        }

        # Try Redis storage
        if self.redis_client:
            try:
                async with self.redis_client.pipeline() as pipe:
                    # Store mapping
                    pipe.hset(key, mapping=pii_mapping)
                    pipe.expire(key, ttl)

                    # Store metadata
                    if metadata:
                        pipe.hset(meta_key, mapping={
                            'created_at': datetime.now().isoformat(),
                            'ttl': ttl,
                            'pii_count': len(pii_mapping),
                            **metadata
                        })
                        pipe.expire(meta_key, ttl)

                    await pipe.execute()
                    logger.info(f"Stored {len(pii_mapping)} PII mappings for {conversation_id}")
                    return True

            except Exception as e:
                self.cache_stats['errors'] += 1
                self.cache_stats['last_error'] = str(e)
                logger.error(f"Redis storage failed, using local cache: {e}")
                await self._handle_redis_error()

        # Fallback to local cache only
        self.cache_stats['fallback_used'] += 1
        return True

    async def store_mapping(self, conversation_id: str, pii_map: Dict[str, str], ttl: int, user_id: str = None):
        """
        Compatibility wrapper for PIIMiddleware.
        Delegates to store_pii_mapping with enhanced features.
        """
        return await self.store_pii_mapping(
            conversation_id=conversation_id,
            pii_mapping=pii_map,
            ttl=ttl,
            metadata={'user_id': user_id} if user_id else None
        )

    async def get_mapping(self, conversation_id: str) -> Optional[Dict[str, str]]:
        """
        Compatibility wrapper for PIIMiddleware.
        Delegates to get_pii_mapping.
        """
        return await self.get_pii_mapping(conversation_id)

    async def get_pii_mapping(self, conversation_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieve PII mapping with fallback to local cache.

        Args:
            conversation_id: Unique conversation identifier

        Returns:
            PII mapping dictionary or None
        """
        # Check local cache first (fast path)
        if conversation_id in self.local_cache:
            cache_entry = self.local_cache[conversation_id]
            if cache_entry['expires_at'] > time.time():
                self.cache_stats['hits'] += 1
                logger.debug(f"Local cache hit for {conversation_id}")
                return cache_entry['mapping']
            else:
                # Expired in local cache
                del self.local_cache[conversation_id]

        # Try Redis
        if self.redis_client:
            key = f"sting:pii:conv:{conversation_id}:map"
            try:
                mapping = await self.redis_client.hgetall(key)
                if mapping:
                    self.cache_stats['hits'] += 1
                    # Update local cache
                    self.local_cache[conversation_id] = {
                        'mapping': mapping,
                        'metadata': {},
                        'expires_at': time.time() + 300  # Default TTL
                    }
                    logger.debug(f"Redis cache hit for {conversation_id}")
                    return mapping
            except Exception as e:
                logger.error(f"Redis retrieval failed: {e}")
                await self._handle_redis_error()

        # Cache miss
        self.cache_stats['misses'] += 1
        logger.debug(f"Cache miss for {conversation_id}")
        return None

    async def extend_ttl(self, conversation_id: str, additional_seconds: int = 300) -> bool:
        """
        Extend TTL for active conversations to prevent cache misses.

        Args:
            conversation_id: Conversation to extend
            additional_seconds: Seconds to add to TTL

        Returns:
            Success status
        """
        # Update local cache
        if conversation_id in self.local_cache:
            self.local_cache[conversation_id]['expires_at'] += additional_seconds

        # Update Redis
        if self.redis_client:
            key = f"sting:pii:conv:{conversation_id}:map"
            try:
                ttl = await self.redis_client.ttl(key)
                if ttl > 0:
                    await self.redis_client.expire(key, ttl + additional_seconds)
                    logger.info(f"Extended TTL for {conversation_id} by {additional_seconds}s")
                    return True
            except Exception as e:
                logger.error(f"Failed to extend TTL: {e}")

        return False

    async def batch_get_mappings(self, conversation_ids: List[str]) -> Dict[str, Dict[str, str]]:
        """
        Retrieve multiple PII mappings in batch for efficiency.

        Args:
            conversation_ids: List of conversation IDs

        Returns:
            Dictionary of conversation_id -> pii_mapping
        """
        results = {}

        # Check local cache first
        for conv_id in conversation_ids:
            if conv_id in self.local_cache:
                cache_entry = self.local_cache[conv_id]
                if cache_entry['expires_at'] > time.time():
                    results[conv_id] = cache_entry['mapping']

        # Batch fetch remaining from Redis
        remaining_ids = [cid for cid in conversation_ids if cid not in results]
        if remaining_ids and self.redis_client:
            try:
                async with self.redis_client.pipeline() as pipe:
                    for conv_id in remaining_ids:
                        key = f"sting:pii:conv:{conv_id}:map"
                        pipe.hgetall(key)

                    redis_results = await pipe.execute()
                    for conv_id, mapping in zip(remaining_ids, redis_results):
                        if mapping:
                            results[conv_id] = mapping
                            # Update local cache
                            self.local_cache[conv_id] = {
                                'mapping': mapping,
                                'metadata': {},
                                'expires_at': time.time() + 300
                            }
            except Exception as e:
                logger.error(f"Batch fetch failed: {e}")

        return results

    async def _handle_redis_error(self):
        """Handle Redis connection errors with reconnection logic"""
        self.reconnect_attempts += 1
        if self.reconnect_attempts >= 3:
            logger.warning("Multiple Redis errors detected, attempting reconnection")
            asyncio.create_task(self._reconnect_redis())

    async def _reconnect_redis(self):
        """Attempt to reconnect to Redis in background"""
        await asyncio.sleep(5)  # Wait before reconnecting
        await self.connect()

    async def cleanup_expired(self):
        """Clean up expired entries from local cache"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self.local_cache.items()
            if v['expires_at'] <= current_time
        ]
        for key in expired_keys:
            del self.local_cache[key]

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired local cache entries")

    def get_diagnostics(self) -> Dict:
        """Get cache diagnostics for monitoring"""
        return {
            'cache_stats': self.cache_stats,
            'local_cache_size': len(self.local_cache),
            'redis_connected': self.redis_client is not None,
            'reconnect_attempts': self.reconnect_attempts,
            'timestamp': datetime.now().isoformat()
        }

    async def close(self):
        """Clean up resources"""
        if self.redis_client:
            await self.redis_client.close()
        self.local_cache.clear()