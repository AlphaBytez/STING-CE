#!/usr/bin/env python3
"""
Pollination Engine - Semantic Search and Retrieval
Handles intelligent search across Honey Jar knowledge bases with context awareness
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncio

logger = logging.getLogger(__name__)

class PollinationEngine:
    """Intelligent search engine for Honey Jar knowledge bases"""
    
    def __init__(self, honeycomb_manager):
        self.honeycomb_manager = honeycomb_manager
        self.search_cache = {}
        self.suggestion_cache = {}
        
    async def search(
        self,
        query: str,
        honey_jar_ids: List[str],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across specified Honey Pots
        
        Args:
            query: Search query
            honey_jar_ids: List of Honey Jar IDs to search
            top_k: Number of results to return
            filters: Optional metadata filters
            
        Returns:
            List of search results with content, metadata, and scores
        """
        try:
            logger.info(f"Searching across {len(honey_jar_ids)} Honey Pots for: {query}")
            
            # Use honeycomb manager to search multiple collections
            results = await self.honeycomb_manager.search_multiple_collections(
                collection_ids=honey_jar_ids,
                query=query,
                top_k=top_k,
                filters=filters
            )
            
            # Enhance results with additional metadata
            enhanced_results = []
            for result in results:
                enhanced_result = {
                    "content": result["content"],
                    "metadata": result["metadata"],
                    "score": result["score"],
                    "honey_jar_id": result["collection_id"],
                    "honey_jar_name": await self._get_honey_jar_name(result["collection_id"]),
                    "search_timestamp": datetime.utcnow().isoformat()
                }
                enhanced_results.append(enhanced_result)
            
            logger.info(f"Found {len(enhanced_results)} results")
            return enhanced_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    async def get_suggestions(
        self,
        query: str,
        honey_jar_id: Optional[str] = None
    ) -> List[str]:
        """
        Get search query suggestions based on content analysis
        
        Args:
            query: Partial query to suggest completions for
            honey_jar_id: Optional specific Honey Jar to get suggestions from
            
        Returns:
            List of suggested query completions
        """
        try:
            # Check cache first
            cache_key = f"{query}_{honey_jar_id or 'all'}"
            if cache_key in self.suggestion_cache:
                return self.suggestion_cache[cache_key]
            
            # Generate suggestions based on common patterns
            suggestions = []
            
            # Basic keyword suggestions
            if "how" in query.lower():
                suggestions.extend([
                    f"{query} to install",
                    f"{query} to configure",
                    f"{query} to setup",
                    f"{query} to use"
                ])
            elif "what" in query.lower():
                suggestions.extend([
                    f"{query} is",
                    f"{query} are the requirements",
                    f"{query} does this do",
                    f"{query} features are available"
                ])
            elif len(query) > 3:
                # For longer queries, suggest related terms
                suggestions.extend([
                    f"{query} guide",
                    f"{query} tutorial",
                    f"{query} documentation",
                    f"{query} examples"
                ])
            
            # Cache suggestions
            self.suggestion_cache[cache_key] = suggestions[:5]
            
            return suggestions[:5]
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return []
    
    async def get_bee_context(
        self,
        query: str,
        user: Dict[str, Any],
        conversation_id: Optional[str] = None,
        max_context_length: int = 2000
    ) -> List[Dict[str, Any]]:
        """
        Get relevant context for Bee from accessible Honey Pots
        
        Args:
            query: User's query to Bee
            user: User information with permissions
            conversation_id: Optional conversation ID for context
            max_context_length: Maximum characters of context to return
            
        Returns:
            List of relevant context chunks for Bee
        """
        try:
            # Get user's accessible Honey Pots
            # This would normally query the hive_manager, for now using mock data
            accessible_honey_jars = await self._get_user_honey_jars(user)
            
            if not accessible_honey_jars:
                return []
            
            # Search across accessible Honey Pots
            results = await self.search(
                query=query,
                honey_jar_ids=accessible_honey_jars,
                top_k=3,  # Limit for context
                filters={"accessible_to_bee": True}
            )
            
            # Format context for Bee
            context_chunks = []
            total_length = 0
            
            for result in results:
                content = result["content"]
                if total_length + len(content) > max_context_length:
                    # Truncate to fit within limit
                    remaining_length = max_context_length - total_length
                    content = content[:remaining_length] + "..."
                
                context_chunk = {
                    "content": content,
                    "source": result["honey_jar_name"],
                    "honey_jar_id": result["honey_jar_id"],
                    "score": result["score"],
                    "metadata": {
                        "search_query": query,
                        "conversation_id": conversation_id,
                        "retrieved_at": datetime.utcnow().isoformat()
                    }
                }
                
                context_chunks.append(context_chunk)
                total_length += len(content)
                
                if total_length >= max_context_length:
                    break
            
            logger.info(f"Generated {len(context_chunks)} context chunks for Bee")
            return context_chunks
            
        except Exception as e:
            logger.error(f"Failed to get Bee context: {e}")
            return []
    
    async def search_with_reranking(
        self,
        query: str,
        honey_jar_ids: List[str],
        top_k: int = 5,
        rerank_by: str = "relevance"
    ) -> List[Dict[str, Any]]:
        """
        Advanced search with result reranking
        
        Args:
            query: Search query
            honey_jar_ids: Honey Pots to search
            top_k: Number of results
            rerank_by: Reranking strategy (relevance, recency, popularity)
            
        Returns:
            Reranked search results
        """
        try:
            # Get initial results
            results = await self.search(query, honey_jar_ids, top_k * 2)
            
            # Apply reranking strategy
            if rerank_by == "recency":
                results = self._rerank_by_recency(results)
            elif rerank_by == "popularity":
                results = self._rerank_by_popularity(results)
            else:
                # Default: already ranked by relevance
                pass
            
            return results[:top_k]
            
        except Exception as e:
            logger.error(f"Reranked search failed: {e}")
            raise
    
    def _rerank_by_recency(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank results by document recency"""
        def get_recency_score(result):
            metadata = result.get("metadata", {})
            # Combine relevance score with recency
            relevance = result.get("score", 0)
            # Mock recency scoring - would use actual timestamps
            recency = 0.1  # Default recency boost
            return relevance + recency
        
        return sorted(results, key=get_recency_score, reverse=True)
    
    def _rerank_by_popularity(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rerank results by document popularity/access frequency"""
        def get_popularity_score(result):
            metadata = result.get("metadata", {})
            relevance = result.get("score", 0)
            # Mock popularity scoring - would use actual access stats
            popularity = 0.05  # Default popularity boost
            return relevance + popularity
        
        return sorted(results, key=get_popularity_score, reverse=True)
    
    async def _get_honey_jar_name(self, honey_jar_id: str) -> str:
        """Get display name for a Honey Jar ID"""
        # This would normally query the hive_manager
        # For now, return a formatted name
        return f"Honey Jar {honey_jar_id[-8:]}"
    
    async def _get_user_honey_jars(self, user: Dict[str, Any]) -> List[str]:
        """Get list of Honey Jar IDs accessible to user"""
        # Mock implementation - would normally check permissions
        return ["default", "public", "user_specific"]
    
    async def analyze_search_patterns(
        self,
        user_id: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Analyze user's search patterns for personalization
        
        Args:
            user_id: User to analyze
            days: Number of days to analyze
            
        Returns:
            Search pattern analysis
        """
        try:
            # Mock analysis - would normally query search logs
            return {
                "top_queries": [
                    "installation guide",
                    "configuration help",
                    "API documentation"
                ],
                "preferred_honey_jars": ["technical", "guides"],
                "search_frequency": "daily",
                "avg_results_per_search": 3.2,
                "success_rate": 0.85
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze search patterns: {e}")
            return {}
    
    def clear_cache(self):
        """Clear search and suggestion caches"""
        self.search_cache.clear()
        self.suggestion_cache.clear()
        logger.info("Pollination engine caches cleared")