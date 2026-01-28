"""
Adaptive Context Manager
Smart pre-loading and caching system for honey jar contexts
"""

import asyncio
import logging
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import redis
import hashlib

logger = logging.getLogger(__name__)

@dataclass
class UserContextProfile:
    """User's context usage profile for adaptive loading"""
    user_id: str
    email: str
    default_tokens: int = 3000
    priority_jars: List[str] = None
    avg_query_complexity: str = 'medium'
    session_length_avg: int = 15  # minutes
    query_frequency_daily: int = 5
    last_updated: str = None

    def __post_init__(self):
        if self.priority_jars is None:
            self.priority_jars = []
        if self.last_updated is None:
            self.last_updated = datetime.utcnow().isoformat()

@dataclass
class ContextCache:
    """Cached context for a honey jar"""
    jar_id: str
    user_id: str
    content: str
    token_count: int
    generated_at: datetime
    access_count: int = 0
    last_accessed: datetime = None
    cache_tier: str = 'cold'  # hot, warm, cold

class AdaptiveContextManager:
    """
    Intelligent context pre-loading and caching system
    Learns user patterns to optimize Bee Chat performance
    """

    def __init__(self, redis_client, knowledge_service_url: str = "http://knowledge:8090"):
        self.redis = redis_client
        self.knowledge_service_url = knowledge_service_url
        self.context_cache: Dict[str, ContextCache] = {}
        self.user_profiles: Dict[str, UserContextProfile] = {}

        # Cache TTL settings
        self.hot_cache_ttl = 3600    # 1 hour
        self.warm_cache_ttl = 7200   # 2 hours
        self.cold_cache_ttl = 1800   # 30 minutes

        # Context size limits
        self.max_hot_contexts_per_user = 3
        self.max_warm_contexts_per_user = 8

        logger.info("🧠 Adaptive Context Manager initialized")

    async def get_user_profile(self, user_id: str, user_email: str = None) -> UserContextProfile:
        """Get or create user context profile with adaptive baseline"""

        if user_id in self.user_profiles:
            return self.user_profiles[user_id]

        # Try to load from Redis cache
        try:
            cached_profile = self.redis.get(f"context_profile:{user_id}")
            if cached_profile:
                profile_data = json.loads(cached_profile)
                profile = UserContextProfile(**profile_data)
                self.user_profiles[user_id] = profile
                return profile
        except Exception as e:
            logger.warning(f"Failed to load cached profile for {user_id}: {e}")

        # Create new profile with smart defaults
        profile = UserContextProfile(
            user_id=user_id,
            email=user_email or f"user_{user_id}",
            default_tokens=self._calculate_initial_baseline(user_email)
        )

        self.user_profiles[user_id] = profile
        await self._save_user_profile(profile)
        return profile

    def _calculate_initial_baseline(self, user_email: str = None) -> int:
        """Calculate initial context baseline based on user type"""
        if user_email:
            if 'admin' in user_email:
                return 8000  # Admin users get larger context
            elif any(domain in user_email for domain in ['sting.local', 'support']):
                return 6000  # Internal users
        return 3000  # Default for external users

    async def get_adaptive_context_size(self, user_id: str, query_complexity: str = 'medium') -> int:
        """Get dynamic context size based on user patterns and query"""
        profile = await self.get_user_profile(user_id)

        base_tokens = profile.default_tokens

        # Adjust based on query complexity
        complexity_multipliers = {
            'simple': 0.5,   # Quick questions
            'medium': 1.0,   # Normal queries
            'complex': 1.5,  # Multi-step analysis
            'research': 2.0  # Deep research queries
        }

        adjusted_tokens = int(base_tokens * complexity_multipliers.get(query_complexity, 1.0))

        # Cap at reasonable limits
        return min(max(adjusted_tokens, 1000), 12000)

    async def pre_warm_user_contexts(self, user_id: str, user_email: str = None):
        """Pre-load user's frequently accessed honey jar contexts"""
        try:
            profile = await self.get_user_profile(user_id, user_email)
            logger.info(f"🔥 Pre-warming contexts for {profile.email}")

            # Get user's honey jars from knowledge service
            honey_jars = await self._get_user_honey_jars(user_id)

            if not honey_jars:
                logger.info(f"No honey jars found for user {user_id}")
                return

            # Sort by usage/priority
            priority_jars = self._prioritize_jars(honey_jars, profile)

            # Pre-load hot contexts (top 3)
            hot_tasks = []
            for jar in priority_jars[:self.max_hot_contexts_per_user]:
                task = self._pre_load_jar_context(
                    jar['id'], user_id,
                    context_size=profile.default_tokens // 3,
                    tier='hot'
                )
                hot_tasks.append(task)

            # Load hot contexts in parallel
            if hot_tasks:
                await asyncio.gather(*hot_tasks, return_exceptions=True)
                logger.info(f"✅ Pre-loaded {len(hot_tasks)} hot contexts for {profile.email}")

            # Schedule warm contexts in background
            asyncio.create_task(self._pre_load_warm_contexts(priority_jars[3:8], user_id, profile))

        except Exception as e:
            logger.error(f"Error pre-warming contexts for {user_id}: {e}")

    async def _pre_load_jar_context(self, jar_id: str, user_id: str, context_size: int = 2000, tier: str = 'warm'):
        """Pre-load and cache a specific honey jar context"""
        try:
            cache_key = f"context:{user_id}:{jar_id}"

            # Check if already cached
            if cache_key in self.context_cache:
                cached = self.context_cache[cache_key]
                if (datetime.utcnow() - cached.generated_at).seconds < self._get_ttl_for_tier(tier):
                    cached.cache_tier = tier
                    return cached.content

            # Generate context summary
            context_content = await self._generate_jar_context_summary(jar_id, context_size)

            if context_content:
                # Create cache entry
                cache_entry = ContextCache(
                    jar_id=jar_id,
                    user_id=user_id,
                    content=context_content,
                    token_count=len(context_content.split()) * 1.3,  # Rough token estimate
                    generated_at=datetime.utcnow(),
                    cache_tier=tier
                )

                self.context_cache[cache_key] = cache_entry

                # Store in Redis for persistence
                await self._store_context_in_redis(cache_key, cache_entry, tier)

                logger.info(f"📦 Cached {tier} context for jar {jar_id} ({cache_entry.token_count:.0f} tokens)")
                return context_content

        except Exception as e:
            logger.error(f"Failed to pre-load context for jar {jar_id}: {e}")
            return None

    def _get_ttl_for_tier(self, tier: str) -> int:
        """Get cache TTL based on tier"""
        return {
            'hot': self.hot_cache_ttl,
            'warm': self.warm_cache_ttl,
            'cold': self.cold_cache_ttl
        }.get(tier, self.cold_cache_ttl)

    async def get_context_for_query(self, user_id: str, jar_id: str, query: str) -> Optional[str]:
        """Get optimized context for a specific query"""
        try:
            # Determine query complexity
            complexity = self._analyze_query_complexity(query)
            context_size = await self.get_adaptive_context_size(user_id, complexity)

            cache_key = f"context:{user_id}:{jar_id}"

            # Check cache first
            if cache_key in self.context_cache:
                cached = self.context_cache[cache_key]

                # Update access stats
                cached.access_count += 1
                cached.last_accessed = datetime.utcnow()

                # If cached context is sufficient size, use it
                if cached.token_count >= context_size * 0.8:  # 80% threshold
                    logger.info(f"🎯 Using cached context for jar {jar_id} ({cached.token_count:.0f} tokens)")
                    return cached.content

            # Generate fresh context if needed
            logger.info(f"🔄 Generating fresh context for jar {jar_id} ({context_size} tokens)")
            return await self._generate_jar_context_summary(jar_id, context_size)

        except Exception as e:
            logger.error(f"Error getting context for query: {e}")
            return None

    def _analyze_query_complexity(self, query: str) -> str:
        """Analyze query to determine complexity level"""
        query_lower = query.lower()

        # Simple patterns
        simple_indicators = ['what is', 'who is', 'when', 'where', 'how many', 'list']
        if any(indicator in query_lower for indicator in simple_indicators) and len(query.split()) < 8:
            return 'simple'

        # Complex patterns
        complex_indicators = ['analyze', 'compare', 'explain relationship', 'summarize all', 'create report']
        if any(indicator in query_lower for indicator in complex_indicators):
            return 'complex'

        # Research patterns
        research_indicators = ['research', 'comprehensive analysis', 'detailed breakdown', 'investigate']
        if any(indicator in query_lower for indicator in research_indicators) or len(query.split()) > 20:
            return 'research'

        return 'medium'

    def _prioritize_jars(self, honey_jars: List[Dict], profile: UserContextProfile) -> List[Dict]:
        """Sort honey jars by priority for pre-loading"""

        def jar_priority(jar):
            score = 0
            jar_id = jar['id']

            # Boost priority jars
            if jar_id in profile.priority_jars:
                score += 100

            # Boost recently created/updated jars
            if 'updated_at' in jar:
                days_old = (datetime.utcnow() - datetime.fromisoformat(jar['updated_at'])).days
                score += max(0, 30 - days_old)

            # Boost jars with more documents (more likely to be useful)
            doc_count = jar.get('stats', {}).get('document_count', 0)
            score += min(doc_count * 2, 20)

            return score

        return sorted(honey_jars, key=jar_priority, reverse=True)

    async def _pre_load_warm_contexts(self, warm_jars: List[Dict], user_id: str, profile: UserContextProfile):
        """Background task to pre-load warm contexts"""
        try:
            await asyncio.sleep(2)  # Don't block hot loading

            warm_tasks = []
            for jar in warm_jars[:self.max_warm_contexts_per_user]:
                task = self._pre_load_jar_context(
                    jar['id'], user_id,
                    context_size=profile.default_tokens // 6,  # Smaller for warm
                    tier='warm'
                )
                warm_tasks.append(task)

            if warm_tasks:
                await asyncio.gather(*warm_tasks, return_exceptions=True)
                logger.info(f"✅ Pre-loaded {len(warm_tasks)} warm contexts for {profile.email}")

        except Exception as e:
            logger.error(f"Error in background warm context loading: {e}")

    async def _get_user_honey_jars(self, user_id: str) -> List[Dict]:
        """Get user's accessible honey jars from knowledge service"""
        try:
            import httpx
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                # Use service API key for knowledge service access
                headers = {
                    'X-API-Key': 'zluwZxtbqbaMVqQ9ubY/iFXxbTPfjFAFGigIubu7A24=',
                    'X-User-ID': user_id
                }

                response = await client.get(
                    f"{self.knowledge_service_url}/honey-jars",
                    headers=headers
                )

                if response.status_code == 200:
                    data = response.json()
                    return data if isinstance(data, list) else data.get('items', [])
                else:
                    logger.warning(f"Failed to get honey jars for user {user_id}: {response.status_code}")
                    return []

        except Exception as e:
            logger.error(f"Error fetching honey jars for user {user_id}: {e}")
            return []

    async def _generate_jar_context_summary(self, jar_id: str, max_tokens: int = 2000) -> Optional[str]:
        """Generate context summary for a honey jar"""
        try:
            import httpx
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                headers = {'X-API-Key': 'zluwZxtbqbaMVqQ9ubY/iFXxbTPfjFAFGigIubu7A24='}

                # Get jar documents
                response = await client.get(
                    f"{self.knowledge_service_url}/honey-jars/{jar_id}/documents",
                    headers=headers
                )

                if response.status_code != 200:
                    return None

                documents = response.json()
                if not documents:
                    return "This honey jar contains no documents."

                # Generate efficient summary
                summary_parts = [
                    f"Honey Jar Context (ID: {jar_id})",
                    f"Contains {len(documents)} documents:",
                    ""
                ]

                token_budget = max_tokens - 100  # Reserve for header
                tokens_per_doc = min(token_budget // len(documents), 300)

                for doc in documents[:10]:  # Limit to top 10 docs
                    doc_summary = self._generate_document_summary(doc, tokens_per_doc)
                    summary_parts.append(doc_summary)

                    if len('\n'.join(summary_parts).split()) > max_tokens:
                        break

                if len(documents) > 10:
                    summary_parts.append(f"... and {len(documents) - 10} more documents")

                return '\n'.join(summary_parts)

        except Exception as e:
            logger.error(f"Error generating context for jar {jar_id}: {e}")
            return None

    def _generate_document_summary(self, document: Dict, max_tokens: int = 200) -> str:
        """Generate concise document summary"""
        try:
            filename = document.get('filename', 'Unknown')
            content = document.get('content', document.get('preview', ''))

            if not content:
                return f"📄 {filename}: [No preview available]"

            # Extract key information
            words = content.split()
            summary_words = words[:max_tokens] if len(words) > max_tokens else words
            summary = ' '.join(summary_words)

            if len(words) > max_tokens:
                summary += "..."

            return f"📄 {filename}: {summary}"

        except Exception as e:
            return f"📄 {document.get('filename', 'Unknown')}: [Error generating summary]"

    async def _save_user_profile(self, profile: UserContextProfile):
        """Save user profile to Redis"""
        try:
            profile_data = asdict(profile)
            self.redis.setex(
                f"context_profile:{profile.user_id}",
                86400,  # 24 hour TTL
                json.dumps(profile_data)
            )
        except Exception as e:
            logger.error(f"Failed to save profile for {profile.user_id}: {e}")

    async def _store_context_in_redis(self, cache_key: str, cache_entry: ContextCache, tier: str):
        """Store context in Redis with appropriate TTL"""
        try:
            cache_data = {
                'content': cache_entry.content,
                'token_count': cache_entry.token_count,
                'generated_at': cache_entry.generated_at.isoformat(),
                'tier': tier
            }

            ttl = self._get_ttl_for_tier(tier)
            self.redis.setex(cache_key, ttl, json.dumps(cache_data))

        except Exception as e:
            logger.error(f"Failed to store context in Redis: {e}")

    async def update_user_usage_stats(self, user_id: str, query_complexity: str, response_time: float):
        """Update user profile based on actual usage"""
        try:
            profile = await self.get_user_profile(user_id)

            # Update complexity preference
            if query_complexity == 'complex' or query_complexity == 'research':
                profile.default_tokens = min(profile.default_tokens + 200, 10000)
            elif query_complexity == 'simple' and profile.default_tokens > 2000:
                profile.default_tokens = max(profile.default_tokens - 100, 2000)

            # Update query frequency (rolling average)
            profile.query_frequency_daily = int(profile.query_frequency_daily * 0.9 + 1 * 0.1)

            # Save updated profile
            await self._save_user_profile(profile)

        except Exception as e:
            logger.error(f"Error updating usage stats for {user_id}: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_contexts = len(self.context_cache)
        hot_contexts = sum(1 for c in self.context_cache.values() if c.cache_tier == 'hot')
        warm_contexts = sum(1 for c in self.context_cache.values() if c.cache_tier == 'warm')

        return {
            'total_cached_contexts': total_contexts,
            'hot_contexts': hot_contexts,
            'warm_contexts': warm_contexts,
            'cold_contexts': total_contexts - hot_contexts - warm_contexts,
            'memory_usage_mb': sum(len(c.content) for c in self.context_cache.values()) / 1024 / 1024
        }

# Global instance
adaptive_context_manager = None

def get_adaptive_context_manager(redis_client) -> AdaptiveContextManager:
    """Get singleton instance of adaptive context manager"""
    global adaptive_context_manager
    if adaptive_context_manager is None:
        adaptive_context_manager = AdaptiveContextManager(redis_client)
    return adaptive_context_manager