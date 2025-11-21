#!/usr/bin/env python3
"""
Conversation Store - Abstract interface for persistent conversation storage.

This module provides a pluggable architecture for conversation persistence:
- PostgresConversationStore: Current implementation (PostgreSQL + Redis cache)
- Future: ScyllaConversationStore, CockroachConversationStore, etc.

The store handles:
1. PostgreSQL as source of truth (persistent)
2. Redis as hot cache (24h TTL, fast reads)
3. ChromaDB for semantic indexing (via ConversationSemanticSearch)
"""

import os
import json
import logging
import asyncio
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any
from datetime import datetime
from uuid import UUID, uuid4

import asyncpg
import redis

logger = logging.getLogger(__name__)


def string_to_uuid(s: str) -> UUID:
    """Convert any string to a deterministic UUID.

    If the string is already a valid UUID, returns it as-is.
    Otherwise, generates a UUID5 from the string using a namespace.
    """
    try:
        return UUID(s)
    except (ValueError, AttributeError):
        # Generate deterministic UUID from string using namespace
        namespace = UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # URL namespace
        hash_bytes = hashlib.md5(f"sting:{s}".encode()).digest()
        return UUID(bytes=hash_bytes)


class ConversationStore(ABC):
    """Abstract base class for conversation storage backends."""

    @abstractmethod
    async def create_conversation(
        self,
        user_id: str,
        conversation_type: str = "bee_chat",
        bot_id: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> str:
        """Create a new conversation and return its ID."""
        pass

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation metadata by ID."""
        pass

    @abstractmethod
    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Add a message to a conversation."""
        pass

    @abstractmethod
    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 20,
        before: Optional[datetime] = None
    ) -> List[Dict]:
        """Get messages from a conversation, ordered by time descending."""
        pass

    @abstractmethod
    async def list_conversations(
        self,
        user_id: str,
        status: str = "active",
        limit: int = 50
    ) -> List[Dict]:
        """List conversations for a user."""
        pass

    @abstractmethod
    async def update_conversation(
        self,
        conversation_id: str,
        **kwargs
    ) -> bool:
        """Update conversation metadata."""
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: str, hard: bool = False) -> bool:
        """Delete a conversation (soft delete by default)."""
        pass


class PostgresConversationStore(ConversationStore):
    """
    PostgreSQL-backed conversation store with Redis caching.

    Architecture:
    - PostgreSQL: Source of truth, persistent storage
    - Redis: Hot cache for recent conversations (24h TTL)

    Connection pooling and async operations for performance.
    """

    REDIS_PREFIX = "bee:conversation:"
    REDIS_TTL = 86400  # 24 hours

    def __init__(
        self,
        pg_dsn: Optional[str] = None,
        redis_host: Optional[str] = None,
        redis_port: Optional[int] = None
    ):
        """
        Initialize the PostgreSQL conversation store.

        Args:
            pg_dsn: PostgreSQL connection string (default: from env)
            redis_host: Redis host (default: from env)
            redis_port: Redis port (default: from env)
        """
        # PostgreSQL connection settings
        self.pg_dsn = pg_dsn or os.getenv(
            "MESSAGING_DATABASE_URL",
            f"postgresql://{os.getenv('POSTGRES_USER', 'app_user')}:"
            f"{os.getenv('POSTGRES_PASSWORD', 'app_password')}@"
            f"{os.getenv('POSTGRES_HOST', 'db')}:"
            f"{os.getenv('POSTGRES_PORT', '5432')}/"
            f"sting_messaging"
        )

        # PostgreSQL connection pool (initialized lazily)
        self._pg_pool: Optional[asyncpg.Pool] = None

        # Redis connection
        self._redis: Optional[redis.Redis] = None
        self._redis_host = redis_host or os.getenv("REDIS_HOST", "redis")
        self._redis_port = redis_port or int(os.getenv("REDIS_PORT", 6379))

        self._initialized = False

    async def _ensure_initialized(self):
        """Ensure connections are established."""
        if self._initialized:
            return

        # Initialize PostgreSQL connection pool
        try:
            self._pg_pool = await asyncpg.create_pool(
                self.pg_dsn,
                min_size=2,
                max_size=10,
                command_timeout=30
            )
            logger.info("✅ PostgreSQL conversation store connected")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

        # Initialize Redis connection
        try:
            self._redis = redis.Redis(
                host=self._redis_host,
                port=self._redis_port,
                decode_responses=True,
                socket_connect_timeout=5
            )
            self._redis.ping()
            logger.info("✅ Redis cache connected for conversation store")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available, running without cache: {e}")
            self._redis = None

        self._initialized = True

    def _cache_key(self, conversation_id: str) -> str:
        """Generate Redis cache key for a conversation."""
        return f"{self.REDIS_PREFIX}{conversation_id}"

    async def _cache_messages(self, conversation_id: str, messages: List[Dict]):
        """Cache messages in Redis."""
        if not self._redis:
            return
        try:
            key = self._cache_key(conversation_id)
            # Store as list of JSON strings (most recent first)
            pipe = self._redis.pipeline()
            pipe.delete(key)
            for msg in messages:
                pipe.rpush(key, json.dumps(msg, default=str))
            pipe.expire(key, self.REDIS_TTL)
            pipe.execute()
        except Exception as e:
            logger.warning(f"Failed to cache messages: {e}")

    async def _get_cached_messages(self, conversation_id: str, limit: int) -> Optional[List[Dict]]:
        """Get messages from Redis cache."""
        if not self._redis:
            return None
        try:
            key = self._cache_key(conversation_id)
            cached = self._redis.lrange(key, 0, limit - 1)
            if cached:
                return [json.loads(msg) for msg in cached]
        except Exception as e:
            logger.warning(f"Failed to get cached messages: {e}")
        return None

    async def _invalidate_cache(self, conversation_id: str):
        """Invalidate Redis cache for a conversation."""
        if not self._redis:
            return
        try:
            self._redis.delete(self._cache_key(conversation_id))
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")

    async def create_conversation(
        self,
        user_id: str,
        conversation_type: str = "bee_chat",
        bot_id: Optional[str] = None,
        settings: Optional[Dict] = None
    ) -> str:
        """Create a new conversation and return its ID."""
        await self._ensure_initialized()

        conversation_id = str(uuid4())
        settings_json = json.dumps(settings or {})

        async with self._pg_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO conversations (id, user_id, bot_id, conversation_type, settings)
                VALUES ($1, $2, $3, $4, $5)
                """,
                string_to_uuid(conversation_id),
                string_to_uuid(user_id),
                string_to_uuid(bot_id) if bot_id else None,
                conversation_type,
                settings_json
            )

        logger.info(f"Created conversation {conversation_id[:8]} for user {user_id[:8]}")
        return conversation_id

    async def get_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Get conversation metadata by ID."""
        await self._ensure_initialized()

        async with self._pg_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, user_id, bot_id, title, conversation_type, status,
                       is_pinned, settings, summary, created_at, updated_at,
                       last_message_at, deleted_at
                FROM conversations
                WHERE id = $1 AND deleted_at IS NULL
                """,
                string_to_uuid(conversation_id)
            )

        if not row:
            return None

        return {
            "id": str(row["id"]),
            "user_id": str(row["user_id"]),
            "bot_id": str(row["bot_id"]) if row["bot_id"] else None,
            "title": row["title"],
            "conversation_type": row["conversation_type"],
            "status": row["status"],
            "is_pinned": row["is_pinned"],
            "settings": json.loads(row["settings"]) if row["settings"] else {},
            "summary": json.loads(row["summary"]) if row["summary"] else None,
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
            "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
        }

    async def add_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """Add a message to a conversation."""
        await self._ensure_initialized()

        try:
            # Convert IDs to UUIDs (handles both UUID strings and arbitrary strings)
            conv_uuid = string_to_uuid(conversation_id)
            user_uuid = string_to_uuid(user_id)

            # Check if conversation exists, create if not
            conv = await self.get_conversation(conversation_id)
            if not conv:
                # Auto-create conversation with the deterministic UUID
                async with self._pg_pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO conversations (id, user_id, conversation_type)
                        VALUES ($1, $2, 'bee_chat')
                        ON CONFLICT (id) DO NOTHING
                        """,
                        conv_uuid,
                        user_uuid
                    )

            metadata_json = json.dumps(metadata or {})

            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO messages (conversation_id, role, content, metadata)
                    VALUES ($1, $2, $3, $4)
                    """,
                    conv_uuid,
                    role,
                    content,
                    metadata_json
                )

            # Invalidate cache so next read gets fresh data
            await self._invalidate_cache(conversation_id)

            logger.debug(f"Added {role} message to conversation {conversation_id[:8]}")
            return True

        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return False

    async def get_messages(
        self,
        conversation_id: str,
        limit: int = 20,
        before: Optional[datetime] = None
    ) -> List[Dict]:
        """Get messages from a conversation, ordered by time ascending."""
        await self._ensure_initialized()

        # Convert conversation_id to UUID for lookup
        conv_uuid = string_to_uuid(conversation_id)

        # Skip Redis cache for now - PostgreSQL is source of truth
        # TODO: Fix cache population to include all messages, not just latest
        # if not before:
        #     cached = await self._get_cached_messages(conversation_id, limit)
        #     if cached:
        #         logger.info(f"📜 Cache hit for conversation {conversation_id[:8]}: {len(cached)} messages")
        #         return cached

        # Query PostgreSQL
        async with self._pg_pool.acquire() as conn:
            if before:
                rows = await conn.fetch(
                    """
                    SELECT id, role, content, metadata, created_at
                    FROM messages
                    WHERE conversation_id = $1 AND created_at < $2 AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT $3
                    """,
                    conv_uuid,
                    before,
                    limit
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, role, content, metadata, created_at
                    FROM messages
                    WHERE conversation_id = $1 AND deleted_at IS NULL
                    ORDER BY created_at DESC
                    LIMIT $2
                    """,
                    conv_uuid,
                    limit
                )

        messages = []
        for row in reversed(rows):  # Reverse to get chronological order
            messages.append({
                "id": str(row["id"]),
                "role": row["role"],
                "content": row["content"],
                "metadata": json.loads(row["metadata"]) if row["metadata"] else {},
                "timestamp": row["created_at"].isoformat() if row["created_at"] else None,
            })

        # Cache the result
        if not before and messages:
            await self._cache_messages(conversation_id, messages)

        logger.debug(f"Loaded {len(messages)} messages from PostgreSQL for {conversation_id[:8]}")
        return messages

    async def list_conversations(
        self,
        user_id: str,
        status: str = "active",
        limit: int = 50
    ) -> List[Dict]:
        """List conversations for a user."""
        await self._ensure_initialized()

        async with self._pg_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, title, conversation_type, status, is_pinned,
                       created_at, last_message_at
                FROM conversations
                WHERE user_id = $1 AND status = $2 AND deleted_at IS NULL
                ORDER BY is_pinned DESC, last_message_at DESC
                LIMIT $3
                """,
                string_to_uuid(user_id),
                status,
                limit
            )

        return [
            {
                "id": str(row["id"]),
                "title": row["title"],
                "conversation_type": row["conversation_type"],
                "status": row["status"],
                "is_pinned": row["is_pinned"],
                "created_at": row["created_at"].isoformat() if row["created_at"] else None,
                "last_message_at": row["last_message_at"].isoformat() if row["last_message_at"] else None,
            }
            for row in rows
        ]

    async def update_conversation(
        self,
        conversation_id: str,
        **kwargs
    ) -> bool:
        """Update conversation metadata."""
        await self._ensure_initialized()

        allowed_fields = {"title", "status", "is_pinned", "settings", "summary"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return False

        # Build dynamic UPDATE query
        set_clauses = []
        values = []
        for i, (field, value) in enumerate(updates.items(), start=1):
            if field in ("settings", "summary"):
                set_clauses.append(f"{field} = ${i}::jsonb")
                values.append(json.dumps(value))
            else:
                set_clauses.append(f"{field} = ${i}")
                values.append(value)

        values.append(string_to_uuid(conversation_id))

        query = f"""
            UPDATE conversations
            SET {", ".join(set_clauses)}
            WHERE id = ${len(values)} AND deleted_at IS NULL
        """

        try:
            async with self._pg_pool.acquire() as conn:
                await conn.execute(query, *values)
            return True
        except Exception as e:
            logger.error(f"Failed to update conversation: {e}")
            return False

    async def delete_conversation(self, conversation_id: str, hard: bool = False) -> bool:
        """Delete a conversation (soft delete by default)."""
        await self._ensure_initialized()

        try:
            async with self._pg_pool.acquire() as conn:
                if hard:
                    # Hard delete - cascades to messages
                    await conn.execute(
                        "DELETE FROM conversations WHERE id = $1",
                        string_to_uuid(conversation_id)
                    )
                else:
                    # Soft delete
                    await conn.execute(
                        "UPDATE conversations SET deleted_at = NOW(), status = 'deleted' WHERE id = $1",
                        string_to_uuid(conversation_id)
                    )

            await self._invalidate_cache(conversation_id)
            logger.info(f"Deleted conversation {conversation_id[:8]} (hard={hard})")
            return True

        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False

    async def close(self):
        """Close connections."""
        if self._pg_pool:
            await self._pg_pool.close()
        if self._redis:
            self._redis.close()


# Global instance
_conversation_store: Optional[PostgresConversationStore] = None


def get_conversation_store() -> PostgresConversationStore:
    """Get or create global conversation store instance."""
    global _conversation_store
    if _conversation_store is None:
        _conversation_store = PostgresConversationStore()
    return _conversation_store
