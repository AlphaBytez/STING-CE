"""
Honey Jar Context Manager for Nectar Worker
Handles fetching and caching relevant context from Honey Jars
"""

import logging
import hashlib
from typing import Optional, Dict, Any
from cachetools import TTLCache
import httpx

logger = logging.getLogger(__name__)


class HoneyJarContextManager:
    """
    Manages Honey Jar context fetching and caching for Nectar Bots

    Features:
    - Semantic search via Knowledge API
    - TTL-based caching to reduce API calls
    - Access control validation (public/private jars)
    """

    def __init__(self, sting_api_url: str, sting_api_key: str, cache_size: int = 100, ttl: int = 300):
        """
        Initialize Honey Jar Context Manager

        Args:
            sting_api_url: Base URL for STING API
            sting_api_key: API key for internal service calls
            cache_size: Maximum number of cached entries
            ttl: Time-to-live for cache entries in seconds
        """
        self.api_url = sting_api_url
        self.api_key = sting_api_key
        self.cache = TTLCache(maxsize=cache_size, ttl=ttl)

        logger.info(f"Initialized HoneyJarContextManager (cache_size={cache_size}, ttl={ttl}s)")

    def _generate_cache_key(self, jar_id: str, query: str) -> str:
        """Generate cache key from jar_id and query"""
        query_hash = hashlib.md5(query.encode()).hexdigest()[:8]
        return f"{jar_id}:{query_hash}"

    async def get_relevant_context(
        self,
        jar_id: str,
        user_message: str,
        limit: int = 5,
        is_public: bool = False,
        bot_owner_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Fetch relevant context from Honey Jar

        Args:
            jar_id: Honey Jar ID
            user_message: User's message for semantic search
            limit: Maximum number of documents to retrieve
            is_public: Whether the bot is public (for access control)
            bot_owner_id: Bot owner ID (for private bot access control)

        Returns:
            Concatenated relevant document content or None
        """
        cache_key = self._generate_cache_key(jar_id, user_message)

        # Check cache
        if cache_key in self.cache:
            logger.info(f"Cache hit for jar {jar_id}")
            return self.cache[cache_key]

        # Fetch from Knowledge API
        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(
                    f"{self.api_url}/api/knowledge/jars/{jar_id}/search",
                    params={
                        "query": user_message,
                        "limit": limit,
                        "is_public": is_public,
                        "bot_owner_id": bot_owner_id
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=10.0
                )

                if response.status_code == 200:
                    data = response.json()
                    documents = data.get("documents", [])

                    if not documents:
                        logger.info(f"No relevant documents found in jar {jar_id}")
                        return None

                    # Concatenate document content
                    context_parts = []
                    for doc in documents:
                        # Include document title/name if available
                        doc_name = doc.get('name', 'Document')
                        doc_content = doc.get('content', '')

                        if doc_content:
                            context_parts.append(f"[{doc_name}]\n{doc_content}")

                    context = "\n\n".join(context_parts)

                    # Cache the result
                    self.cache[cache_key] = context

                    logger.info(f"Fetched {len(documents)} documents from jar {jar_id}")
                    return context

                elif response.status_code == 403:
                    logger.warning(f"Access denied to Honey Jar {jar_id}")
                    return None

                elif response.status_code == 404:
                    logger.warning(f"Honey Jar {jar_id} not found")
                    return None

                else:
                    logger.error(f"Knowledge API returned {response.status_code} for jar {jar_id}")
                    return None

        except httpx.RequestError as e:
            logger.error(f"Failed to fetch from Knowledge API: {e}")
            return None

        except Exception as e:
            logger.error(f"Unexpected error fetching Honey Jar context: {e}", exc_info=True)
            return None

    def clear_cache(self, jar_id: Optional[str] = None):
        """
        Clear cache for specific jar or entire cache

        Args:
            jar_id: Optional jar ID to clear specific entries
        """
        if jar_id:
            # Clear only entries for this jar
            keys_to_remove = [k for k in self.cache.keys() if k.startswith(f"{jar_id}:")]
            for key in keys_to_remove:
                del self.cache[key]
            logger.info(f"Cleared cache for jar {jar_id}")
        else:
            # Clear entire cache
            self.cache.clear()
            logger.info("Cleared entire Honey Jar cache")
