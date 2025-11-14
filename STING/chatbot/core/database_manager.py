"""
Database Manager for Chatbot
Handles all database operations for conversations, messages, and memory
"""

import asyncio
import asyncpg
import json
import os
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import logging
from uuid import UUID
import uuid
from urllib.parse import quote as url_quote

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Manages database connections and operations for the chatbot.
    Uses PostgreSQL for persistent storage.
    """
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
        self.db_url = self._get_db_url()
        
    def _get_db_url(self) -> str:
        """
        Construct database URL from environment variables.
        Uses DATABASE_URL if available, otherwise constructs from individual vars.
        """
        # Prefer DATABASE_URL if available (already URL-encoded)
        database_url = os.getenv('DATABASE_URL')
        if database_url:
            logger.info(f"Using DATABASE_URL from environment: {database_url[:60]}...")
            return database_url

        # Fallback: construct from individual components with URL encoding
        host = os.getenv('POSTGRES_HOST', 'db')
        port = os.getenv('POSTGRES_PORT', '5432')
        user = os.getenv('POSTGRES_USER', 'postgres')
        password = os.getenv('POSTGRES_PASSWORD', 'postgres')
        database = os.getenv('POSTGRES_DB', 'sting_app')

        # URL-encode password to handle special characters (+, /, =, etc.)
        password_encoded = url_quote(password, safe='')

        constructed_url = f"postgresql://{user}:{password_encoded}@{host}:{port}/{database}"
        logger.info(f"Constructed DATABASE_URL from env vars: {constructed_url[:60]}...")
        return constructed_url
    
    async def initialize(self):
        """
        Initialize database connection pool.
        """
        try:
            self.pool = await asyncpg.create_pool(
                self.db_url,
                min_size=2,
                max_size=10,
                command_timeout=60
            )
            logger.info("Database connection pool initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise
    
    async def close(self):
        """
        Close database connection pool.
        """
        if self.pool:
            await self.pool.close()
            logger.info("Database connection pool closed")
    
    # Conversation Management
    
    async def create_conversation(self, user_id: str, model_type: str = 'bee') -> Dict[str, Any]:
        """
        Create a new conversation.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO conversations (user_id, model_type)
                VALUES ($1, $2)
                RETURNING id, user_id, model_type, started_at, last_activity, 
                          status, metadata, created_at
                """,
                user_id, model_type
            )
            return dict(row)
    
    async def get_conversation(self, conversation_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID.
        """
        # Debug logging
        logger.info(f"get_conversation called with conversation_id='{conversation_id}', type={type(conversation_id)}")
        
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM conversations WHERE id = $1"
            params = [UUID(str(conversation_id))]
            
            if user_id:
                query += " AND user_id = $2"
                params.append(user_id)
            
            row = await conn.fetchrow(query, *params)
            return dict(row) if row else None
    
    async def update_conversation_activity(self, conversation_id: str):
        """
        Update last activity timestamp for a conversation.
        """
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE conversations 
                SET last_activity = CURRENT_TIMESTAMP 
                WHERE id = $1
                """,
                UUID(str(conversation_id))
            )
    
    # Message Management
    
    async def add_message(self, conversation_id: str, role: str, content: str, 
                         metadata: Optional[Dict] = None, sentiment: Optional[Dict] = None,
                         tools_used: Optional[List] = None) -> Dict[str, Any]:
        """
        Add a message to a conversation.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (conversation_id, role, content, metadata, sentiment, tools_used)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, conversation_id, role, content, metadata, sentiment, 
                          tools_used, timestamp, created_at
                """,
                UUID(str(conversation_id)),
                role,
                content,
                json.dumps(metadata or {}),
                json.dumps(sentiment or {}),
                json.dumps(tools_used or [])
            )
            
            # Update conversation activity
            await self.update_conversation_activity(conversation_id)
            
            # Update message count in context
            await conn.execute(
                """
                INSERT INTO conversation_context (conversation_id, context_data, message_count)
                VALUES ($1, $2, 1)
                ON CONFLICT (conversation_id) 
                DO UPDATE SET 
                    message_count = conversation_context.message_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                """,
                UUID(str(conversation_id)),
                json.dumps({})
            )
            
            return dict(row)
    
    async def get_conversation_messages(self, conversation_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get messages for a conversation.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM messages 
                WHERE conversation_id = $1 
                ORDER BY timestamp DESC 
                LIMIT $2
                """,
                UUID(str(conversation_id)),
                limit
            )
            return [dict(row) for row in reversed(rows)]  # Return in chronological order
    
    # Memory Management
    
    async def store_memory(self, user_id: str, memory_type: str, content: str, 
                          importance: float = 0.5, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Store a memory entry.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO memory_entries (user_id, memory_type, content, importance, metadata)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, user_id, memory_type, content, importance, 
                          access_count, metadata, created_at
                """,
                user_id,
                memory_type,
                content,
                importance,
                json.dumps(metadata or {})
            )
            return dict(row)
    
    async def get_user_memories(self, user_id: str, memory_types: Optional[List[str]] = None, 
                               limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get memories for a user.
        """
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM memory_entries WHERE user_id = $1"
            params = [user_id]
            
            if memory_types:
                query += " AND memory_type = ANY($2)"
                params.append(memory_types)
            
            query += " ORDER BY importance DESC, last_accessed DESC LIMIT $" + str(len(params) + 1)
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            
            # Update access count and timestamp
            if rows:
                memory_ids = [row['id'] for row in rows]
                await conn.execute(
                    """
                    UPDATE memory_entries 
                    SET access_count = access_count + 1,
                        last_accessed = CURRENT_TIMESTAMP
                    WHERE id = ANY($1)
                    """,
                    memory_ids
                )
            
            return [dict(row) for row in rows]
    
    # Entity and Fact Management
    
    async def store_entity(self, conversation_id: str, message_id: str, entity_type: str, 
                          entity_value: str, confidence: float = 0.5) -> Dict[str, Any]:
        """
        Store an extracted entity.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO extracted_entities (conversation_id, message_id, entity_type, 
                                              entity_value, confidence)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING id, conversation_id, message_id, entity_type, entity_value, confidence
                """,
                UUID(str(conversation_id)),
                UUID(message_id),
                entity_type,
                entity_value,
                confidence
            )
            return dict(row)
    
    async def store_fact(self, user_id: str, conversation_id: str, fact_type: str,
                        subject: str, predicate: str, object: str, 
                        confidence: float = 0.5) -> Dict[str, Any]:
        """
        Store a learned fact.
        """
        async with self.pool.acquire() as conn:
            # Check if similar fact already exists
            existing = await conn.fetchrow(
                """
                SELECT id, confidence FROM learned_facts
                WHERE user_id = $1 AND fact_type = $2 
                AND subject = $3 AND predicate = $4 AND object = $5
                """,
                user_id, fact_type, subject, predicate, object
            )
            
            if existing:
                # Update confidence if new one is higher
                if confidence > existing['confidence']:
                    await conn.execute(
                        """
                        UPDATE learned_facts 
                        SET confidence = $1, updated_at = CURRENT_TIMESTAMP
                        WHERE id = $2
                        """,
                        confidence, existing['id']
                    )
                return dict(existing)
            else:
                # Insert new fact
                row = await conn.fetchrow(
                    """
                    INSERT INTO learned_facts (user_id, conversation_id, fact_type, 
                                             subject, predicate, object, confidence)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                    RETURNING id, user_id, fact_type, subject, predicate, object, confidence
                    """,
                    user_id,
                    UUID(str(conversation_id)) if conversation_id else None,
                    fact_type,
                    subject,
                    predicate,
                    object,
                    confidence
                )
                return dict(row)
    
    async def get_user_facts(self, user_id: str, fact_types: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Get facts about a user.
        """
        async with self.pool.acquire() as conn:
            query = "SELECT * FROM learned_facts WHERE user_id = $1"
            params = [user_id]
            
            if fact_types:
                query += " AND fact_type = ANY($2)"
                params.append(fact_types)
            
            query += " ORDER BY confidence DESC, updated_at DESC"
            
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    # User Preferences
    
    async def set_user_preference(self, user_id: str, preference_type: str, 
                                 preference_key: str, preference_value: Any) -> Dict[str, Any]:
        """
        Set a user preference.
        """
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO user_preferences (user_id, preference_type, preference_key, preference_value)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (user_id, preference_type, preference_key)
                DO UPDATE SET 
                    preference_value = EXCLUDED.preference_value,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id, user_id, preference_type, preference_key, preference_value
                """,
                user_id,
                preference_type,
                preference_key,
                json.dumps(preference_value)
            )
            return dict(row)
    
    async def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get all preferences for a user.
        """
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT preference_type, preference_key, preference_value 
                FROM user_preferences 
                WHERE user_id = $1
                """,
                user_id
            )
            
            preferences = {}
            for row in rows:
                pref_type = row['preference_type']
                if pref_type not in preferences:
                    preferences[pref_type] = {}
                preferences[pref_type][row['preference_key']] = json.loads(row['preference_value'])
            
            return preferences
    
    # Cleanup and Maintenance
    
    async def cleanup_old_conversations(self, days_to_keep: int = 30) -> int:
        """
        Clean up old conversations.
        """
        async with self.pool.acquire() as conn:
            result = await conn.fetchval(
                "SELECT cleanup_old_conversations($1)",
                days_to_keep
            )
            return result
    
    async def get_conversation_summary(self, conversation_id: str) -> Optional[str]:
        """
        Get a summary of a conversation.
        """
        async with self.pool.acquire() as conn:
            summary = await conn.fetchval(
                "SELECT summarize_conversation($1)",
                UUID(str(conversation_id))
            )
            return summary