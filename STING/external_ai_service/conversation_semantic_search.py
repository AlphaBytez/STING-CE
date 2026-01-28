#!/usr/bin/env python3
"""
Conversation Semantic Search - ChromaDB-based semantic search for conversation history

This module enables intelligent retrieval of relevant past conversation messages
using vector embeddings, complementing the keyword-based filtering in conversation_cache.py.

Benefits:
- Find semantically similar messages even without keyword overlap
- Better context retrieval for follow-up questions
- Reduces tangents by providing relevant prior context
"""

import os
import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    logger.warning("ChromaDB not available - conversation semantic search disabled")
    CHROMADB_AVAILABLE = False


class ConversationSemanticSearch:
    """Semantic search for conversation history using ChromaDB.

    This provides an additional layer of context retrieval beyond the
    keyword-based filtering in ConversationCache. Use for:
    - Finding semantically related past discussions
    - Retrieving context for follow-up questions
    - Identifying topic continuity vs topic changes
    """

    COLLECTION_NAME = "bee_conversations"

    def __init__(
        self,
        chroma_host: str = None,
        chroma_port: int = None
    ):
        """Initialize ChromaDB client for conversation search.

        Args:
            chroma_host: ChromaDB host (default: from env or 'chroma')
            chroma_port: ChromaDB port (default: from env or 8000)
        """
        self.enabled = False
        self.client = None
        self.collection = None

        if not CHROMADB_AVAILABLE:
            logger.warning("ChromaDB not installed - semantic search disabled")
            return

        # Get connection details from environment or defaults
        host = chroma_host or os.getenv("CHROMA_HOST", "chroma")
        port = chroma_port or int(os.getenv("CHROMA_PORT", "8000"))

        try:
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=Settings(anonymized_telemetry=False)
            )
            # Test connection
            self.client.heartbeat()
            logger.info(f"✅ ConversationSemanticSearch connected to ChromaDB at {host}:{port}")
            self.enabled = True

            # Get or create collection
            self._init_collection()

        except Exception as e:
            logger.error(f"❌ Failed to connect to ChromaDB for conversation search: {e}")
            self.enabled = False

    def _init_collection(self):
        """Initialize or get the conversations collection."""
        if not self.enabled:
            return

        try:
            # Try to get existing collection
            try:
                self.collection = self.client.get_collection(name=self.COLLECTION_NAME)
                logger.info(f"📚 Loaded existing conversation collection: {self.COLLECTION_NAME}")
            except Exception:
                # Create new collection with cosine similarity
                self.collection = self.client.create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={
                        "description": "Bee conversation history for semantic search",
                        "hnsw:space": "cosine"  # Use cosine similarity
                    }
                )
                logger.info(f"📚 Created new conversation collection: {self.COLLECTION_NAME}")
        except Exception as e:
            logger.error(f"Failed to initialize conversation collection: {e}")
            self.enabled = False

    def _generate_id(self, conversation_id: str, message_content: str, timestamp: str) -> str:
        """Generate unique ID for a message."""
        hash_input = f"{conversation_id}:{message_content}:{timestamp}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    async def index_message(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        timestamp: str = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Index a conversation message for semantic search.

        Args:
            conversation_id: Unique conversation identifier
            user_id: User who owns this conversation
            role: 'user' or 'assistant'
            content: Message content
            timestamp: ISO timestamp (default: now)
            metadata: Additional metadata

        Returns:
            True if indexed successfully
        """
        if not self.enabled or not self.collection:
            return False

        # Skip very short messages (not useful for semantic search)
        if len(content.strip()) < 10:
            return True  # Not an error, just skip

        try:
            ts = timestamp or datetime.now().isoformat()
            doc_id = self._generate_id(conversation_id, content, ts)

            # Build metadata
            msg_metadata = {
                "conversation_id": conversation_id,
                "user_id": user_id,
                "role": role,
                "timestamp": ts,
                "content_length": len(content),
            }
            if metadata:
                msg_metadata.update(metadata)

            # Truncate very long messages for indexing
            index_content = content[:2000] if len(content) > 2000 else content

            # Add to collection (upsert to handle duplicates)
            self.collection.upsert(
                documents=[index_content],
                metadatas=[msg_metadata],
                ids=[doc_id]
            )

            logger.debug(f"Indexed message {doc_id[:8]} for conversation {conversation_id[:8]}")
            return True

        except Exception as e:
            logger.error(f"Failed to index message: {e}")
            return False

    async def search_conversation(
        self,
        query: str,
        conversation_id: str,
        n_results: int = 5,
        min_score: float = 0.3
    ) -> List[Dict[str, Any]]:
        """Search for relevant messages within a specific conversation.

        Args:
            query: Search query (current user message)
            conversation_id: Conversation to search within
            n_results: Maximum results to return
            min_score: Minimum similarity score (0-1)

        Returns:
            List of relevant messages with scores
        """
        if not self.enabled or not self.collection:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"conversation_id": conversation_id}
            )

            # Format and filter results
            formatted = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    score = 1.0 - distance  # Convert distance to similarity

                    if score >= min_score:
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        formatted.append({
                            "content": doc,
                            "role": metadata.get("role", "unknown"),
                            "timestamp": metadata.get("timestamp", ""),
                            "score": score,
                            "metadata": metadata
                        })

            logger.debug(f"Found {len(formatted)} relevant messages in conversation {conversation_id[:8]}")
            return formatted

        except Exception as e:
            logger.error(f"Conversation search failed: {e}")
            return []

    async def search_user_history(
        self,
        query: str,
        user_id: str,
        n_results: int = 10,
        min_score: float = 0.4
    ) -> List[Dict[str, Any]]:
        """Search across all conversations for a user.

        Useful for finding related discussions from past conversations.

        Args:
            query: Search query
            user_id: User to search for
            n_results: Maximum results
            min_score: Minimum similarity score

        Returns:
            List of relevant messages from any conversation
        """
        if not self.enabled or not self.collection:
            return []

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"user_id": user_id}
            )

            formatted = []
            if results and results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i] if results['distances'] else 1.0
                    score = 1.0 - distance

                    if score >= min_score:
                        metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                        formatted.append({
                            "content": doc,
                            "conversation_id": metadata.get("conversation_id", ""),
                            "role": metadata.get("role", "unknown"),
                            "timestamp": metadata.get("timestamp", ""),
                            "score": score
                        })

            return formatted

        except Exception as e:
            logger.error(f"User history search failed: {e}")
            return []

    async def delete_conversation(self, conversation_id: str) -> bool:
        """Delete all indexed messages for a conversation.

        Args:
            conversation_id: Conversation to delete

        Returns:
            True if successful
        """
        if not self.enabled or not self.collection:
            return False

        try:
            self.collection.delete(
                where={"conversation_id": conversation_id}
            )
            logger.info(f"Deleted indexed messages for conversation {conversation_id[:8]}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete conversation from index: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self.enabled:
            return {"enabled": False, "reason": "ChromaDB not available"}

        try:
            count = self.collection.count() if self.collection else 0
            return {
                "enabled": True,
                "collection": self.COLLECTION_NAME,
                "indexed_messages": count
            }
        except Exception as e:
            return {"enabled": True, "error": str(e)}


# Global instance
_semantic_search: Optional[ConversationSemanticSearch] = None


def get_conversation_semantic_search() -> ConversationSemanticSearch:
    """Get or create global conversation semantic search instance."""
    global _semantic_search
    if _semantic_search is None:
        _semantic_search = ConversationSemanticSearch()
    return _semantic_search
