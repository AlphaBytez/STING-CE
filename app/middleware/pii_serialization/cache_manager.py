"""
PII Cache Manager

Manages Redis-based caching of PII mappings with TTL and cleanup.

Features:
- Redis pipeline for performance
- Automatic TTL management
- Memory pressure handling
- LRU cleanup
"""

import redis.asyncio as redis
import json
import time
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PIICacheManager:
    """
    Manages PII mapping cache in Redis with intelligent TTL and cleanup.

    Uses Redis hash structures for efficient storage and retrieval.
    Implements memory pressure handling and LRU cleanup.
    """

    def __init__(self, config, redis_client=None):
        """
        Initialize cache manager.

        Args:
            config: PIIProtectionConfig instance
            redis_client: Redis client (will create if None)
        """
        self.config = config
        self.redis = redis_client or self._create_redis_client()

    def _create_redis_client(self):
        """Create Redis client for PII cache."""
        redis_db = self.config.get_redis_db()
        return redis.Redis(
            host='redis',
            port=6379,
            db=redis_db,
            decode_responses=True
        )

    async def store_mapping(
        self,
        conversation_id: str,
        pii_map: Dict[str, str],
        ttl: int,
        user_id: str = None
    ):
        """
        Store PII mapping in cache with TTL.

        Uses Redis pipeline for atomic operations.

        Args:
            conversation_id: Conversation identifier
            pii_map: Token -> value mapping
            ttl: Time to live in seconds
            user_id: User identifier (optional, for user tracking)
        """
        cache_key = self._get_cache_key(conversation_id)
        meta_key = self._get_meta_key(conversation_id)

        try:
            # Use pipeline for atomic operations
            async with self.redis.pipeline() as pipe:
                # Store PII mapping
                pipe.hset(cache_key, mapping=pii_map)

                # Set TTL
                pipe.expire(cache_key, ttl)

                # Store metadata
                metadata = {
                    "created_at": int(time.time()),
                    "ttl": ttl,
                    "pii_count": len(pii_map),
                    "user_id": user_id or "unknown"
                }
                pipe.hset(meta_key, mapping=metadata)
                pipe.expire(meta_key, ttl)

                # Add to user's conversation set (for cleanup)
                if user_id:
                    user_set_key = f"sting:pii:user:{user_id}:conversations"
                    pipe.sadd(user_set_key, conversation_id)
                    pipe.expire(user_set_key, ttl + 3600)  # Extra hour

                await pipe.execute()

            logger.debug(
                f"Stored PII mapping for {conversation_id}: "
                f"{len(pii_map)} items, TTL={ttl}s"
            )

        except Exception as e:
            logger.error(f"Failed to store PII mapping: {e}")
            raise

    async def get_mapping(
        self,
        conversation_id: str
    ) -> Optional[Dict[str, str]]:
        """
        Retrieve PII mapping from cache.

        Args:
            conversation_id: Conversation identifier

        Returns:
            PII mapping dict, or None if not found/expired
        """
        cache_key = self._get_cache_key(conversation_id)

        try:
            pii_map = await self.redis.hgetall(cache_key)

            if pii_map:
                logger.debug(
                    f"Retrieved PII mapping for {conversation_id}: "
                    f"{len(pii_map)} items"
                )
                return pii_map
            else:
                logger.warning(f"PII mapping not found for {conversation_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to retrieve PII mapping: {e}")
            return None

    async def extend_ttl(self, conversation_id: str, new_ttl: int):
        """
        Extend TTL for a conversation's PII mapping.

        Args:
            conversation_id: Conversation identifier
            new_ttl: New TTL in seconds
        """
        cache_key = self._get_cache_key(conversation_id)
        meta_key = self._get_meta_key(conversation_id)

        try:
            async with self.redis.pipeline() as pipe:
                pipe.expire(cache_key, new_ttl)
                pipe.expire(meta_key, new_ttl)
                pipe.hset(meta_key, "ttl", new_ttl)
                await pipe.execute()

            logger.info(f"Extended TTL for {conversation_id} to {new_ttl}s")

        except Exception as e:
            logger.error(f"Failed to extend TTL: {e}")

    async def delete_mapping(self, conversation_id: str):
        """
        Delete PII mapping from cache.

        Args:
            conversation_id: Conversation identifier
        """
        cache_key = self._get_cache_key(conversation_id)
        meta_key = self._get_meta_key(conversation_id)

        try:
            async with self.redis.pipeline() as pipe:
                pipe.delete(cache_key)
                pipe.delete(meta_key)
                await pipe.execute()

            logger.info(f"Deleted PII mapping for {conversation_id}")

        except Exception as e:
            logger.error(f"Failed to delete PII mapping: {e}")

    async def cleanup(self):
        """
        Run cleanup to remove old/expired caches based on memory pressure.

        Strategy:
        1. Check memory usage
        2. If over threshold, evict oldest success caches
        3. Keep error caches longer (for debugging)
        """
        try:
            # Get all PII cache keys
            pattern = "sting:pii:conv:*:map"
            keys = []
            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if not keys:
                return

            # Check memory usage
            memory_info = await self.redis.info("memory")
            used_memory_mb = memory_info.get("used_memory", 0) / (1024 * 1024)
            max_memory_mb = self.config.get_max_cache_size_mb()

            if used_memory_mb < max_memory_mb * 0.9:
                # Under 90% capacity - no cleanup needed
                return

            logger.warning(
                f"PII cache memory pressure: {used_memory_mb:.1f}MB / {max_memory_mb}MB"
            )

            # Get metadata for all caches
            cache_info = []
            for key in keys:
                conv_id = key.split(":")[3]  # Extract conversation_id
                meta_key = self._get_meta_key(conv_id)
                metadata = await self.redis.hgetall(meta_key)

                if metadata:
                    cache_info.append({
                        "conversation_id": conv_id,
                        "created_at": int(metadata.get("created_at", 0)),
                        "has_error": metadata.get("error_count", "0") != "0"
                    })

            # Sort by creation time (oldest first), but prioritize non-error caches
            cache_info.sort(key=lambda x: (x["has_error"], x["created_at"]))

            # Delete oldest 25% of non-error caches
            to_delete = int(len(cache_info) * 0.25)
            for cache in cache_info[:to_delete]:
                if not cache["has_error"]:
                    await self.delete_mapping(cache["conversation_id"])

            logger.info(f"Cleaned up {to_delete} PII cache entries")

        except Exception as e:
            logger.error(f"Cleanup failed: {e}")

    def _get_cache_key(self, conversation_id: str) -> str:
        """Get Redis key for PII mapping."""
        return f"sting:pii:conv:{conversation_id}:map"

    def _get_meta_key(self, conversation_id: str) -> str:
        """Get Redis key for cache metadata."""
        return f"sting:pii:conv:{conversation_id}:meta"
