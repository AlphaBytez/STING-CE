#!/usr/bin/env python3
"""
Bee Context Manager - Integrates documentation and honey jars for enhanced Bee Chat
"""

import os
import aiohttp
import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class BeeContextManager:
    """Manages context from documentation, brain knowledge, and honey jars for Bee Chat"""

    def __init__(self):
        self.knowledge_service_url = os.getenv("KNOWLEDGE_SERVICE_URL", "http://knowledge:8090")
        self.docs_path = Path(__file__).parent.parent / "docs"

        # NEW: Use BeeBrainManager for versioned knowledge
        try:
            from .bee_brain_manager import BeeBrainManager
            self.brain_manager = BeeBrainManager()
            self.use_versioned_brain = True
            logger.info("Using versioned bee_brain system")
        except Exception as e:
            logger.warning(f"Could not load BeeBrainManager, falling back to legacy: {e}")
            # Fallback to legacy brain
            self.brain_path = Path(__file__).parent / "bee_brain_v2.0.0.md"
            self.use_versioned_brain = False

        # NEW: Initialize conversation cache for memory
        try:
            from conversation_cache import get_conversation_cache
            self.conversation_cache = get_conversation_cache()
            logger.info("✅ Conversation cache initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize conversation cache: {e}")
            self.conversation_cache = None

        # NEW: Initialize ChromaDB knowledge indexer for semantic search
        try:
            from knowledge_indexer import get_knowledge_indexer
            self.knowledge_indexer = get_knowledge_indexer()
            logger.info("✅ Knowledge indexer initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize knowledge indexer: {e}")
            self.knowledge_indexer = None

        # NEW: Initialize conversation semantic search for intelligent context retrieval
        try:
            from conversation_semantic_search import get_conversation_semantic_search
            self.conversation_search = get_conversation_semantic_search()
            logger.info("✅ Conversation semantic search initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize conversation semantic search: {e}")
            self.conversation_search = None

        # NEW: Initialize conversation summarizer for long conversations
        try:
            from conversation_summarizer import get_conversation_summarizer
            self.conversation_summarizer = get_conversation_summarizer()
            logger.info("✅ Conversation summarizer initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize conversation summarizer: {e}")
            self.conversation_summarizer = None

        # NEW: Initialize PostgreSQL conversation store (source of truth)
        self.conversation_store = None
        self._store_init_attempted = False

        self.documentation_cache = {}
        self.honey_jar_cache = {}
        self.brain_knowledge = ""  # Core brain knowledge loaded in memory
        self.brain_loaded = False
        self.use_semantic_search = True  # Use ChromaDB when available
        
    async def load_brain_knowledge(self) -> str:
        """Load Bee brain knowledge from the brain file into memory"""
        if self.brain_loaded and self.brain_knowledge:
            return self.brain_knowledge

        try:
            # NEW: Use versioned bee_brain if available
            if self.use_versioned_brain and hasattr(self, 'brain_manager'):
                self.brain_knowledge = self.brain_manager.get_core_knowledge()
                if self.brain_knowledge:
                    self.brain_loaded = True
                    metadata = self.brain_manager.get_metadata()
                    logger.info(f"Loaded versioned Bee Brain v{metadata.get('loaded_version')}: {len(self.brain_knowledge)} characters")
                    return self.brain_knowledge
                else:
                    logger.warning("Versioned brain returned empty, falling back to legacy")
                    self.use_versioned_brain = False

            # LEGACY: Fallback to hardcoded brain file
            if hasattr(self, 'brain_path') and self.brain_path.exists():
                self.brain_knowledge = self.brain_path.read_text(encoding='utf-8')
                self.brain_loaded = True
                logger.info(f"Loaded legacy Bee Brain: {len(self.brain_knowledge)} characters from {self.brain_path}")
            else:
                logger.warning(f"No Bee Brain available (legacy path: {getattr(self, 'brain_path', 'N/A')})")
                self.brain_knowledge = ""
                self.brain_loaded = True

        except Exception as e:
            logger.error(f"Error loading Bee Brain knowledge: {e}")
            self.brain_knowledge = ""
            self.brain_loaded = True

        return self.brain_knowledge
        
    async def load_documentation(self) -> Dict[str, str]:
        """Load all markdown documentation files"""
        if self.documentation_cache:
            return self.documentation_cache
            
        docs_content = {}
        
        # Key documentation files to prioritize
        priority_docs = [
            "README.md",
            "ARCHITECTURE.md", 
            "DATA_PROTECTION_ARCHITECTURE.md",
            "WORKER_BEE_CONNECTOR_FRAMEWORK.md",
            "REPORT_GENERATION_FRAMEWORK.md",
            "AI_ASSISTANT.md"
        ]
        
        try:
            # Load priority docs from root
            root_path = self.docs_path.parent
            for doc in priority_docs:
                doc_path = root_path / doc
                if doc_path.exists():
                    docs_content[doc] = doc_path.read_text()
                    logger.info(f"Loaded documentation: {doc}")
            
            # Load all markdown files from docs/ directory
            if self.docs_path.exists():
                for md_file in self.docs_path.rglob("*.md"):
                    relative_path = str(md_file.relative_to(self.docs_path.parent))
                    docs_content[relative_path] = md_file.read_text()
                    logger.info(f"Loaded documentation: {relative_path}")
                    
        except Exception as e:
            logger.error(f"Error loading documentation: {e}")
            
        self.documentation_cache = docs_content
        return docs_content
    
    async def get_honey_jar_context(self, query: str, user_id: str, honey_jar_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get relevant context from honey jars"""
        try:
            logger.info(f"Getting honey jar context - URL: {self.knowledge_service_url}, query: {query}, honey_jar_id: {honey_jar_id}")
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "user_id": user_id,
                    "limit": 5,
                    "includeMetadata": True
                }
                
                # If specific honey jar is provided, add it to the payload
                if honey_jar_id:
                    payload["honey_jar_id"] = honey_jar_id
                
                # Try public endpoint first (no auth required)
                public_url = f"{self.knowledge_service_url}/bee/context/public"
                logger.info(f"Trying public endpoint: {public_url}")
                
                async with session.post(public_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        logger.info(f"Got {len(results)} results from public honey jars")
                        if results:
                            return results
                    else:
                        logger.info(f"Public endpoint returned {response.status}, trying authenticated endpoint")
                
                # If no public results or public endpoint failed, try authenticated endpoint
                auth_url = f"{self.knowledge_service_url}/bee/context"
                logger.info(f"Trying authenticated endpoint: {auth_url}")
                
                async with session.post(auth_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        logger.info(f"Got {len(results)} results from authenticated endpoint")
                        return results
                    else:
                        error_text = await response.text()
                        logger.warning(f"Authenticated endpoint failed: {response.status} - {error_text}")
                        # Return empty list but don't fail completely
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching honey jar context: {e}")
            return []
    
    async def search_documentation(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """Search documentation for relevant content using semantic search or keyword fallback"""

        # Try semantic search first if available
        if self.use_semantic_search and self.knowledge_indexer and self.knowledge_indexer.enabled:
            try:
                results = self.knowledge_indexer.search(
                    query=query,
                    n_results=max_results,
                    filter_metadata={"type": "documentation"}
                )
                if results:
                    scores = [f"{r['score']:.2f}" for r in results]
                    logger.info(f"🔍 Found {len(results)} docs via semantic search (scores: {scores})")
                    # Format for compatibility
                    formatted_results = []
                    for r in results:
                        formatted_results.append({
                            "source": r['metadata'].get('source', 'unknown'),
                            "score": r['score'],
                            "snippet": r['content'][:500]  # Truncate to 500 chars
                        })
                    return formatted_results
            except Exception as e:
                logger.warning(f"Semantic search failed, falling back to keyword search: {e}")

        # Fallback to keyword search
        docs = await self.load_documentation()
        results = []

        # Simple keyword search
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for doc_name, content in docs.items():
            content_lower = content.lower()

            # Score based on keyword matches
            score = 0
            for word in query_words:
                score += content_lower.count(word)

            if score > 0:
                # Extract relevant snippet
                snippet = self._extract_snippet(content, query_words, max_length=500)
                results.append({
                    "source": doc_name,
                    "score": score,
                    "snippet": snippet
                })

        # Sort by score and return top results
        results.sort(key=lambda x: x["score"], reverse=True)
        logger.info(f"📚 Found {len(results[:max_results])} docs via keyword search")
        return results[:max_results]
    
    def _extract_snippet(self, content: str, query_words: set, max_length: int = 500) -> str:
        """Extract most relevant snippet from content"""
        lines = content.split('\n')
        
        # Find lines with most keyword matches
        scored_lines = []
        for i, line in enumerate(lines):
            line_lower = line.lower()
            score = sum(1 for word in query_words if word in line_lower)
            if score > 0:
                scored_lines.append((i, score, line))
        
        if not scored_lines:
            # Return first part of content if no matches
            return content[:max_length] + "..." if len(content) > max_length else content
        
        # Get best matching line and surrounding context
        scored_lines.sort(key=lambda x: x[1], reverse=True)
        best_line_idx = scored_lines[0][0]
        
        # Get 2 lines before and after for context
        start_idx = max(0, best_line_idx - 2)
        end_idx = min(len(lines), best_line_idx + 3)
        
        snippet = '\n'.join(lines[start_idx:end_idx])
        
        if len(snippet) > max_length:
            snippet = snippet[:max_length] + "..."
            
        return snippet
    
    def _extract_relevant_brain_context(self, brain_knowledge: str, user_message: str, max_length: int = 1500) -> str:
        """Extract the most relevant sections from brain knowledge based on user query"""
        if not brain_knowledge:
            return ""

        # Try semantic search first if available
        if self.use_semantic_search and self.knowledge_indexer and self.knowledge_indexer.enabled:
            try:
                results = self.knowledge_indexer.search(
                    query=user_message,
                    n_results=3,
                    filter_metadata={"type": "knowledge"}
                )
                if results:
                    # Combine top results
                    context_parts = []
                    total_len = 0
                    for r in results:
                        content = r['content']
                        if total_len + len(content) > max_length:
                            # Truncate if too long
                            remaining = max_length - total_len
                            if remaining > 100:  # Only add if meaningful
                                context_parts.append(content[:remaining] + "...")
                            break
                        context_parts.append(content)
                        total_len += len(content)

                    if context_parts:
                        logger.info(f"🧠 Found {len(context_parts)} brain sections via semantic search")
                        return '\n\n'.join(context_parts)
            except Exception as e:
                logger.warning(f"Semantic brain search failed, falling back to keyword: {e}")

        # Fallback to keyword-based extraction
        lines = brain_knowledge.split('\n')
        query_lower = user_message.lower()
        query_words = set(query_lower.split())
        
        # Keywords that indicate different types of queries
        topic_keywords = {
            'authentication': ['auth', 'login', 'passkey', 'totp', 'kratos', 'webauthn', 'aal2', 'password', 'biometric'],
            'honey_jars': ['honey', 'jar', 'knowledge', 'document', 'storage', 'upload', 'search', 'repository'],
            'architecture': ['architecture', 'service', 'component', 'database', 'postgres', 'redis', 'port', 'api'],
            'security': ['security', 'encryption', 'compliance', 'gdpr', 'hipaa', 'sox', 'pii', 'audit', 'vault'],
            'business': ['business', 'roi', 'cost', 'value', 'enterprise', 'deployment', 'implementation'],
            'troubleshooting': ['error', 'issue', 'problem', 'fix', 'troubleshoot', 'debug', 'help', 'support'],
            'features': ['feature', 'capability', 'function', 'tool', 'integration', 'report']
        }
        
        # Identify the primary topic
        primary_topic = None
        max_matches = 0
        for topic, keywords in topic_keywords.items():
            matches = sum(1 for word in query_words if any(keyword in word for keyword in keywords))
            if matches > max_matches:
                max_matches = matches
                primary_topic = topic
        
        # Extract sections based on topic or use general scoring
        relevant_sections = []
        
        if primary_topic:
            # Look for sections related to the primary topic
            in_relevant_section = False
            current_section = []
            
            for line in lines:
                line_lower = line.lower()
                
                # Check if this line starts a relevant section
                if line.startswith('#') and any(keyword in line_lower for keyword in topic_keywords[primary_topic]):
                    if current_section and in_relevant_section:
                        relevant_sections.append('\n'.join(current_section))
                    current_section = [line]
                    in_relevant_section = True
                elif line.startswith('#'):
                    if current_section and in_relevant_section:
                        relevant_sections.append('\n'.join(current_section))
                    current_section = [line]
                    in_relevant_section = False
                elif in_relevant_section:
                    current_section.append(line)
                elif any(keyword in line_lower for keyword in topic_keywords.get(primary_topic, [])):
                    current_section.append(line)
                    in_relevant_section = True
            
            if current_section and in_relevant_section:
                relevant_sections.append('\n'.join(current_section))
        
        # If no specific sections found or need more content, use general keyword matching
        if not relevant_sections or len('\n'.join(relevant_sections)) < 500:
            scored_lines = []
            for i, line in enumerate(lines):
                line_lower = line.lower()
                score = sum(1 for word in query_words if word in line_lower)
                if score > 0:
                    scored_lines.append((i, score, line))
            
            scored_lines.sort(key=lambda x: x[1], reverse=True)
            
            # Take top scoring lines and add surrounding context
            selected_lines = set()
            for line_idx, score, line in scored_lines[:10]:  # Top 10 scoring lines
                for context_idx in range(max(0, line_idx - 2), min(len(lines), line_idx + 3)):
                    selected_lines.add(context_idx)
            
            # Convert back to text, maintaining order
            general_context = []
            for i in sorted(selected_lines):
                general_context.append(lines[i])
            
            if general_context:
                relevant_sections.append('\n'.join(general_context))
        
        # Combine and limit length
        combined_context = '\n\n'.join(relevant_sections)
        
        if len(combined_context) > max_length:
            combined_context = combined_context[:max_length] + "\n...[Additional STING knowledge available]"
        
        return combined_context if combined_context else brain_knowledge[:max_length] + "..."
    
    async def load_bee_system_prompt(self) -> str:
        """Load the actual Bee system prompt from the container"""
        try:
            # In Docker container, the system prompt is copied to /app/bee_system_prompt.txt
            container_path = Path(__file__).parent / "bee_system_prompt.txt"
            if container_path.exists():
                system_prompt = container_path.read_text(encoding='utf-8')
                logger.info(f"Loaded Bee system prompt from {container_path}")
                return system_prompt
            else:
                logger.warning(f"Bee system prompt not found at {container_path}, using fallback")
                return self._get_fallback_system_prompt()
        except Exception as e:
            logger.error(f"Error loading Bee system prompt: {e}")
            return self._get_fallback_system_prompt()
    
    def _get_fallback_system_prompt(self) -> str:
        """Fallback system prompt that matches Bee's personality"""
        return """You are Bee (B. for short), the primary AI assistant for STING-CE. You are helpful, friendly, professional, and knowledgeable about security and intelligence operations.

## Your Core Identity
- You are a general-purpose AI assistant first and foremost
- You happen to operate within the STING platform, but this doesn't limit your helpfulness
- Answer questions about any topic with equal enthusiasm
- Only reference STING features when they genuinely add value
- Think of yourself as a knowledgeable friend who's available on this secure platform

## Response Guidelines
1. **Be Helpful First**: Answer questions directly and helpfully - treat every query as important
2. **Natural Conversation**: Engage conversationally and build on topics naturally
3. **Stay Professional**: Maintain a friendly, approachable tone while being informative
4. **Be Specific**: Provide actionable, detailed information tailored to the user's needs"""

    async def build_enhanced_prompt(
        self,
        user_message: str,
        user_id: str,
        conversation_id: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        honey_jar_id: Optional[str] = None,
        custom_system_prompt: Optional[str] = None
    ) -> str:
        """Build an enhanced prompt that preserves Bee's personality while adding context

        Args:
            custom_system_prompt: If provided (e.g., for Nectar Bots), use this instead of Bee's prompt

        Performance: Uses asyncio.gather() to parallelize independent operations
        """
        import time
        start_time = time.time()

        # Define async tasks for parallel execution
        async def load_history():
            """Load conversation history with keyword + semantic search + summarization

            Storage hierarchy (read):
            1. PostgreSQL (source of truth) - try first
            2. Redis (hot cache fallback)
            """
            history_with_summary = {"messages": [], "summary": None}
            cached = None

            if conversation_id:
                logger.debug(f"📜 Loading history for conversation: {conversation_id[:8]}...")
                # Try PostgreSQL first (source of truth)
                await self._ensure_conversation_store()
                if self.conversation_store:
                    try:
                        pg_messages = await self.conversation_store.get_messages(
                            conversation_id,
                            limit=30  # Load more to detect when summarization is needed
                        )
                        if pg_messages:
                            cached = pg_messages
                            logger.debug(f"📜 Loaded {len(pg_messages)} messages from PostgreSQL for {conversation_id[:8]}")
                    except Exception as e:
                        logger.warning(f"Failed to load from PostgreSQL, trying Redis: {e}")

                # Fall back to Redis cache if PostgreSQL didn't return data
                if not cached and self.conversation_cache:
                    try:
                        cached = await self.conversation_cache.get_conversation_history(
                            conversation_id,
                            limit=30
                        )
                        if cached:
                            logger.debug(f"📜 Loaded {len(cached)} messages from Redis cache")
                    except Exception as e:
                        logger.warning(f"Failed to load conversation history from Redis: {e}")

                if cached:
                    filtered = cached

                    # For long conversations (>15 messages), summarize older ones
                    if len(cached) > 15 and self.conversation_summarizer:
                        # Split into old (to summarize) and recent (to keep)
                        messages_to_summarize = cached[:-10]  # All but last 10
                        recent_messages = cached[-10:]  # Keep last 10 verbatim

                        try:
                            # Get or generate summary for older messages
                            summary_data = await self.conversation_summarizer.summarize_messages(
                                messages=messages_to_summarize,
                                conversation_id=conversation_id
                            )
                            history_with_summary["summary"] = summary_data
                            filtered = recent_messages
                            logger.info(f"📝 Summarized {len(messages_to_summarize)} older messages, keeping {len(recent_messages)} recent")
                        except Exception as e:
                            logger.warning(f"Summarization failed, using all messages: {e}")

                    # Apply relevance filtering ONLY for long conversations (>20 messages)
                    # For shorter conversations, keep all messages to preserve full context
                    if user_message and len(filtered) > 20 and self.conversation_cache:
                        filtered = await self.conversation_cache.filter_by_relevance(
                            filtered, user_message, keep_recent=10, max_total=20
                        )

                        # If keyword filtering returned few results, try semantic search
                        if len(filtered) < 8 and self.conversation_search and self.conversation_search.enabled:
                            try:
                                semantic_results = await self.conversation_search.search_conversation(
                                    query=user_message,
                                    conversation_id=conversation_id,
                                    n_results=5,
                                    min_score=0.4
                                )
                                if semantic_results:
                                    # Merge semantic results with filtered (avoid duplicates)
                                    existing_content = {m.get('content', '')[:100] for m in filtered}
                                    for sr in semantic_results:
                                        if sr['content'][:100] not in existing_content:
                                            filtered.append({
                                                'role': sr['role'],
                                                'content': sr['content'],
                                                'timestamp': sr['timestamp'],
                                                'metadata': {'source': 'semantic_search', 'score': sr['score']}
                                            })
                                    logger.debug(f"📜 Added {len(semantic_results)} semantic matches to context")
                            except Exception as e:
                                logger.warning(f"Semantic search failed, using keyword results: {e}")

                    history_with_summary["messages"] = filtered
                    logger.debug(f"📜 Using {len(filtered)} messages in context")
                    return history_with_summary

            history_with_summary["messages"] = conversation_history or []
            return history_with_summary

        async def load_system_prompt():
            """Load system prompt (Bee or custom)"""
            if custom_system_prompt:
                logger.debug("Using custom system prompt (Nectar Bot)")
                return custom_system_prompt
            return await self.load_bee_system_prompt()

        async def load_honey_jar():
            """Get honey jar context"""
            return await self.get_honey_jar_context(user_message, user_id, honey_jar_id)

        async def load_docs():
            """Search documentation"""
            return await self.search_documentation(user_message)

        async def load_brain():
            """Load brain knowledge"""
            return await self.load_brain_knowledge()

        # Execute ALL context loading in parallel using asyncio.gather()
        # This saves 200-700ms compared to sequential execution
        results = await asyncio.gather(
            load_history(),
            load_system_prompt(),
            load_honey_jar(),
            load_docs(),
            load_brain(),
            return_exceptions=True  # Don't fail if one task fails
        )

        # Unpack results (handle exceptions gracefully)
        history_result = results[0] if not isinstance(results[0], Exception) else {"messages": conversation_history or [], "summary": None}
        system_prompt = results[1] if not isinstance(results[1], Exception) else "You are Bee, a helpful AI assistant."
        honey_jar_results = results[2] if not isinstance(results[2], Exception) else []
        doc_results = results[3] if not isinstance(results[3], Exception) else []
        brain_knowledge = results[4] if not isinstance(results[4], Exception) else ""

        # Extract messages and summary from history result
        conversation_history = history_result.get("messages", [])
        conversation_summary = history_result.get("summary")

        # Log any exceptions that occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_names = ['history', 'system_prompt', 'honey_jar', 'docs', 'brain']
                logger.warning(f"⚠️ Context task '{task_names[i]}' failed: {result}")

        elapsed = (time.time() - start_time) * 1000
        logger.info(f"⚡ Context loading completed in {elapsed:.0f}ms (parallel)")

        # Build context sections - keep them subtle and supportive
        context_parts = []

        # Add conversation summary FIRST (if we summarized older messages)
        if conversation_summary and conversation_summary.get("summary"):
            summary_text = conversation_summary.get("summary", "")
            topics = conversation_summary.get("topics", [])
            key_points = conversation_summary.get("key_points", [])

            summary_section = "## Earlier in this conversation:\n"
            summary_section += f"{summary_text}\n"
            if topics:
                summary_section += f"Topics discussed: {', '.join(topics[:5])}\n"
            if key_points:
                summary_section += f"Key points: {'; '.join(key_points[:3])}\n"

            context_parts.append(summary_section)
            logger.debug(f"📝 Added conversation summary to context")

        # Add recent conversation history
        if conversation_history:
            if self.conversation_cache:
                formatted_history = self.conversation_cache.format_history_for_prompt(
                    conversation_history,
                    max_tokens=2000  # Limit to ~2000 tokens
                )
            else:
                # Fallback formatting if conversation_cache not available
                formatted_history = "## Recent Conversation:\n" + "\n".join(
                    f"{msg['role'].capitalize()}: {msg['content'][:500]}"
                    for msg in conversation_history[-20:]
                )
            if formatted_history:
                logger.debug(f"📜 Adding {len(formatted_history)} chars of conversation history to context")
                context_parts.append(formatted_history)

        # Add honey jar context (user's personal knowledge)
        if honey_jar_results:
            context_parts.append("\n## Relevant information from your honey jars:")
            for result in honey_jar_results[:2]:  # Limit to keep response focused
                source = result.get('metadata', {}).get('source', 'honey jar')
                content = result.get('content', '')[:300]  # Shorter snippets
                if len(result.get('content', '')) > 300:
                    content += "..."
                context_parts.append(f"From {source}: {content}")
        
        # Add documentation context (brief, helpful)
        if doc_results and any('help' in user_message.lower() or 'how' in user_message.lower() or 'what' in user_message.lower() for _ in [True]):
            context_parts.append("\n## Platform information:")
            for result in doc_results[:1]:  # Just one result to avoid overwhelming
                context_parts.append(f"{result['snippet'][:200]}...")
        
        # Add minimal brain context only if it's clearly a STING platform question
        sting_keywords = ['sting', 'authentication', 'honey jar', 'kratos', 'passkey', 'security']
        if brain_knowledge and any(keyword in user_message.lower() for keyword in sting_keywords):
            brain_snippet = self._extract_relevant_brain_context(brain_knowledge, user_message, max_length=500)
            if brain_snippet and len(brain_snippet.strip()) > 50:
                context_parts.append(f"\n## STING platform context:\n{brain_snippet}")
        
        # Build the prompt using the actual system prompt, not a hard-coded override
        context_section = f"\n\n{chr(10).join(context_parts)}\n" if context_parts else ""

        prompt = f"""{system_prompt}
{context_section}
User: {user_message}

Bee: """

        return prompt

    async def _ensure_conversation_store(self):
        """Lazily initialize PostgreSQL conversation store."""
        if self.conversation_store is not None or self._store_init_attempted:
            return

        self._store_init_attempted = True
        try:
            from conversation_store import get_conversation_store
            self.conversation_store = get_conversation_store()
            logger.info("✅ PostgreSQL conversation store initialized (lazy)")
        except Exception as e:
            logger.warning(f"⚠️ PostgreSQL store not available, using Redis only: {e}")
            self.conversation_store = None

    async def save_message_to_history(
        self,
        conversation_id: str,
        user_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Save a message to conversation history.

        Storage hierarchy:
        1. PostgreSQL (source of truth, persistent)
        2. Redis (hot cache, 24h TTL)
        3. ChromaDB (semantic search index)
        """
        success = False

        # Try PostgreSQL first (source of truth)
        await self._ensure_conversation_store()
        if self.conversation_store:
            try:
                success = await self.conversation_store.add_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    metadata=metadata
                )
                if success:
                    logger.debug(f"💾 Saved message to PostgreSQL: {conversation_id[:8]}")
            except Exception as e:
                logger.error(f"Failed to save message to PostgreSQL: {e}")

        # Also save to Redis cache (fast reads)
        if self.conversation_cache:
            try:
                await self.conversation_cache.add_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    metadata=metadata
                )
            except Exception as e:
                logger.warning(f"Failed to cache message in Redis: {e}")

        # Index in ChromaDB for semantic search
        if self.conversation_search and self.conversation_search.enabled:
            try:
                await self.conversation_search.index_message(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    role=role,
                    content=content,
                    metadata=metadata
                )
                logger.debug(f"📚 Indexed message for semantic search: {conversation_id[:8]}")
            except Exception as e:
                logger.warning(f"Failed to index message in ChromaDB: {e}")

        return success
    
    async def delete_conversation_history(self, conversation_id: str) -> bool:
        """Delete conversation from both Redis and ChromaDB"""
        success = True

        # Delete from Redis
        if self.conversation_cache:
            try:
                await self.conversation_cache.clear_conversation(conversation_id)
            except Exception as e:
                logger.error(f"Failed to delete from Redis: {e}")
                success = False

        # Delete from ChromaDB semantic index
        if self.conversation_search and self.conversation_search.enabled:
            try:
                await self.conversation_search.delete_conversation(conversation_id)
            except Exception as e:
                logger.warning(f"Failed to delete from ChromaDB: {e}")
                # Don't mark as failure - Redis is primary

        return success

    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about context systems (Redis, ChromaDB, etc.)"""
        stats = {
            "conversation_cache": {"enabled": False},
            "semantic_search": {"enabled": False},
            "knowledge_indexer": {"enabled": False},
            "brain_loaded": self.brain_loaded,
        }

        if self.conversation_cache:
            stats["conversation_cache"] = {"enabled": self.conversation_cache.enabled}

        if self.conversation_search:
            stats["semantic_search"] = self.conversation_search.get_stats()

        if self.knowledge_indexer:
            stats["knowledge_indexer"] = {"enabled": self.knowledge_indexer.enabled}

        return stats

    async def get_system_capabilities(self) -> Dict[str, Any]:
        """Get current system capabilities and features"""
        capabilities = {
            "features": {
                "hive_scrambler": {
                    "status": "active",
                    "description": "PII detection and scrambling service",
                    "capabilities": ["SSN", "Credit Card", "Email", "Phone", "API Keys"]
                },
                "honey_jars": {
                    "status": "active", 
                    "description": "Knowledge management system",
                    "capabilities": ["Document storage", "Vector search", "Context retrieval"]
                },
                "report_generation": {
                    "status": "in_development",
                    "description": "AI-powered report generation with privacy protection",
                    "capabilities": ["Template-based reports", "Privacy levels", "Multiple AI providers"]
                },
                "worker_bees": {
                    "status": "planned",
                    "description": "Distributed processing framework",
                    "capabilities": ["Data collection", "ETL processing", "Task automation"]
                }
            },
            "ai_providers": {
                "ollama": {
                    "status": "active",
                    "models": ["phi3:mini", "deepseek-r1:32b", "deepseek-r1:latest"]
                },
                "openai": {
                    "status": "planned"
                },
                "claude": {
                    "status": "planned"
                }
            }
        }
        
        return capabilities


# Test the context manager
if __name__ == "__main__":
    async def test_context_manager():
        manager = BeeContextManager()
        
        # Test documentation loading
        print("Loading documentation...")
        docs = await manager.load_documentation()
        print(f"Loaded {len(docs)} documentation files")
        
        # Test documentation search
        print("\nSearching documentation for 'hive scrambler'...")
        results = await manager.search_documentation("hive scrambler")
        for result in results:
            print(f"- {result['source']} (score: {result['score']})")
        
        # Test building enhanced prompt
        print("\nBuilding enhanced prompt...")
        prompt = await manager.build_enhanced_prompt(
            "How does the Hive Scrambler protect PII?",
            "test_user"
        )
        print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
        
        # Test capabilities
        print("\nSystem capabilities:")
        capabilities = await manager.get_system_capabilities()
        print(json.dumps(capabilities, indent=2))
    
    asyncio.run(test_context_manager())