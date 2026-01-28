#!/usr/bin/env python3
"""
Bee Context Manager - Integrates documentation and honey jars for enhanced Bee Chat
"""

import os
import re
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
        
        # Service API key for authenticating with knowledge service
        # Uses the development system API key as default for internal service-to-service auth
        self.knowledge_api_key = os.getenv(
            "KNOWLEDGE_SYSTEM_API_KEY", 
            "sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0"  # System API key for internal service auth
        )

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

        # NEW: Initialize web search provider (admin-configurable)
        try:
            from web_search_provider import get_web_search_provider
            self.web_search = get_web_search_provider()
            if self.web_search.enabled:
                # Update context limits based on the active LLM provider
                # This makes web search context-window aware
                self.web_search.update_context_limits()
                budget = self.web_search.get_context_budget()
                logger.info(f"✅ Web search initialized (tier: {budget['tier']}, "
                           f"max_results: {budget['max_results']}, "
                           f"content_per_source: {budget['max_content_per_source']} chars)")
        except Exception as e:
            logger.warning(f"⚠️ Web search provider not available: {e}")
            self.web_search = None

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

    def _is_simple_conversational_query(self, query: str) -> bool:
        """
        Detect simple conversational queries that don't need knowledge lookups.
        These are greetings, thanks, affirmations, etc. that Bee can handle directly.
        """
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        
        # Very short queries (1-3 words) that are just greetings/social
        if len(query_words) <= 3:
            simple_patterns = [
                # Greetings
                'hi', 'hey', 'hello', 'howdy', 'hola', 'sup', 'yo',
                'hi there', 'hey there', 'hello there',
                'good morning', 'good afternoon', 'good evening', 'good night',
                'morning', 'afternoon', 'evening',
                # Thanks
                'thanks', 'thank you', 'thx', 'ty', 'thanks!', 'thank you!',
                'thanks so much', 'thank you so much', 'thanks a lot',
                # Affirmations
                'ok', 'okay', 'sure', 'yes', 'yep', 'yeah', 'yup', 'alright',
                'got it', 'understood', 'makes sense', 'i see',
                # Farewells
                'bye', 'goodbye', 'see ya', 'later', 'cya', 'ttyl',
                # Simple responses
                'cool', 'great', 'nice', 'awesome', 'perfect', 'wonderful',
                'no', 'nope', 'nah',
            ]
            if query_lower in simple_patterns or query_lower.rstrip('!?.') in simple_patterns:
                return True
        
        # Check for greeting patterns even in slightly longer queries
        greeting_starters = ['hi ', 'hey ', 'hello ', 'thanks ', 'thank you ']
        if any(query_lower.startswith(g) for g in greeting_starters) and len(query_words) <= 5:
            return True
        
        return False
    
    async def get_honey_jar_context(self, query: str, user_id: str, honey_jar_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get relevant context from honey jars
        
        IMPORTANT: Only searches if honey_jar_id is provided (user selected specific jars).
        If no honey jars are selected, returns empty list immediately.
        """
        # If no honey jar is selected, skip the search entirely
        # This prevents searching ALL honey jars when user hasn't selected any
        if not honey_jar_id:
            logger.info("⏭️ No honey jar selected - skipping honey jar context lookup")
            return []
        
        try:
            logger.info(f"Getting honey jar context - URL: {self.knowledge_service_url}, query: {query}, honey_jar_id: {honey_jar_id}")
            
            # Prepare authentication headers for knowledge service
            auth_headers = {}
            if self.knowledge_api_key:
                auth_headers["X-API-Key"] = self.knowledge_api_key
                logger.debug("Using API key authentication for knowledge service")
            
            async with aiohttp.ClientSession() as session:
                payload = {
                    "query": query,
                    "user_id": user_id,
                    "limit": 5,
                    "includeMetadata": True,
                    "honey_jar_id": honey_jar_id
                }
                
                # Use authenticated endpoint for specific honey jar access
                auth_url = f"{self.knowledge_service_url}/bee/context"
                logger.info(f"Querying specific honey jar: {honey_jar_id}")
                
                async with session.post(auth_url, json=payload, headers=auth_headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        results = data.get("results", [])
                        logger.info(f"Got {len(results)} results from honey_jar_id: {honey_jar_id}")
                        return results
                    else:
                        error_text = await response.text()
                        logger.warning(f"Honey jar context request failed: {response.status} - {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error fetching honey jar context: {e}")
            return []

    def _extract_search_query(self, user_message: str) -> str:
        """
        Extract a search-friendly query from a user message.
        
        Converts prompts like "Generate a 2000 word report on drone cybersecurity threats"
        into search queries like "drone cybersecurity threats 2024 2025"
        """
        import re
        
        # Remove common prompt instructions
        cleaned = user_message.lower()
        
        # Remove instruction phrases
        remove_patterns = [
            r'^(great|ok|okay|sure|please|can you|could you|i want|i need|i\'d like)[.,!?\s]*',
            r'generate\s+(a\s+)?(comprehensive\s+)?(detailed\s+)?(in-depth\s+)?report',
            r'write\s+(a\s+)?(comprehensive\s+)?(detailed\s+)?(in-depth\s+)?report',
            r'create\s+(a\s+)?(comprehensive\s+)?(detailed\s+)?(in-depth\s+)?report',
            r'\(?\s*minimum\s+\d+[,\s]*\d*\s*words?\s*\)?',
            r'\(?\s*at\s+least\s+\d+[,\s]*\d*\s*words?\s*\)?',
            r'cite\s+(any\s+)?sources?\s*(you\s+reference)?',
            r'include\s+(any\s+)?references?',
            r'(on|about|regarding|analyzing|exploring)\s+how\s+',
            r'explain\s+(which|how|what|why)',
            r'outline\s+a\s+(phased\s+)?implementation',
            r'design\s+a\s+',
            r'propose\s+a\s+',
            r'map\s+\w+\s+capabilities',
        ]
        
        for pattern in remove_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
        
        # Extract key topic phrases - look for noun phrases after "on", "about", "for"
        topic_match = re.search(
            r'(?:on|about|for|regarding)\s+([^.!?]+?)(?:\.|!|\?|$|include|cite|outline|design|propose)',
            user_message, 
            re.IGNORECASE
        )
        
        if topic_match:
            topic = topic_match.group(1).strip()
            # Clean up the topic
            topic = re.sub(r'\s+', ' ', topic)
            # Remove leading articles
            topic = re.sub(r'^(the|a|an)\s+', '', topic, flags=re.IGNORECASE)
            # Limit length
            words = topic.split()[:10]
            cleaned = ' '.join(words)
        
        # Add year context if discussing "current" or "recent" threats
        if any(word in user_message.lower() for word in ['current', 'recent', '2024', '2025', 'latest']):
            if '2024' not in cleaned and '2025' not in cleaned:
                cleaned += ' 2024 2025'
        
        # Remove extra whitespace
        cleaned = ' '.join(cleaned.split())
        
        # If still too long or nonsensical, extract key nouns
        if len(cleaned) > 100 or len(cleaned) < 5:
            # Fallback: extract capitalized words (likely proper nouns/entities)
            # and any quoted phrases
            capitalized = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', user_message)
            quoted = re.findall(r'"([^"]+)"', user_message)
            
            fallback_terms = quoted + capitalized
            if fallback_terms:
                cleaned = ' '.join(list(dict.fromkeys(fallback_terms))[:6])  # Dedupe, limit to 6
        
        logger.debug(f"Extracted search query: '{cleaned}' from: '{user_message[:100]}...'")
        return cleaned.strip() or user_message[:50]  # Last resort: first 50 chars

    async def _ai_optimize_search_query(self, user_message: str) -> dict:
        """
        Use a fast LLM to intelligently analyze the user's request and generate
        optimized search queries with disambiguation.
        
        This solves issues like:
        - "Northside Hospital Atlanta" returning "Northside High School Jacksonville"
        - Generic names matching wrong entities
        - Missing context that confuses search engines
        
        Returns:
            dict with:
                - optimized_queries: list of search-engine-ready queries
                - entity_type: what kind of organization (hospital, school, company)
                - location: specific location if mentioned
                - disambiguation_terms: terms to include to avoid wrong matches
                - negative_terms: terms to exclude (e.g., "high school" when asking about hospital)
        """
        try:
            # Use a fast, cheap model for query optimization
            optimization_prompt = f"""You are a search query optimizer. Analyze this user request and generate optimized web search queries.

USER REQUEST: {user_message}

Your task:
1. Identify the EXACT organization/entity being asked about
2. Determine the entity TYPE (hospital, company, school, government, etc.)
3. Extract the LOCATION if specified
4. Generate 3-5 search queries that will find EXACTLY what the user wants
5. Identify disambiguation terms to AVOID wrong results (e.g., if asking about a hospital, avoid high school results)

CRITICAL: If the user asks about "Northside Hospital Atlanta", your queries must specifically target the HOSPITAL, not schools with "Northside" in the name.

Respond in this EXACT JSON format only:
{{
    "entity_name": "exact name of organization",
    "entity_type": "hospital|company|school|government|nonprofit|other",
    "location": "city, state or region if mentioned",
    "search_queries": [
        "most specific search query with quotes around entity name",
        "entity name + type + location",
        "entity name + topic from request",
        "site:officialdomain.com if guessable",
        "alternative phrasing"
    ],
    "disambiguation_terms": ["terms that MUST appear in results"],
    "negative_terms": ["terms that indicate WRONG results"]
}}

Return ONLY valid JSON, no explanation."""

            # Call LLM using OpenAI-compatible API format (server uses v1 endpoint)
            ollama_url = os.getenv("OLLAMA_URL", "http://100.89.180.16:1234")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{ollama_url}/v1/chat/completions",
                    json={
                        "model": "microsoft/phi-4-mini-reasoning",
                        "messages": [{"role": "user", "content": optimization_prompt}],
                        "max_tokens": 600,
                        "temperature": 0.1
                    },
                    timeout=aiohttp.ClientTimeout(total=20)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"LLM returned status {resp.status}: {error_text}")

                    result = await resp.json()

            # Parse the response (OpenAI format uses choices[0].message.content)
            raw_content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.debug(f"🧠 AI optimizer raw response: {raw_content[:200]}...")

            # Handle potential thinking blocks from reasoning models
            content = raw_content
            if '<thinking>' in content:
                # Extract content between thinking tags or after them
                content = re.sub(r'<thinking>.*?</thinking>', '', content, flags=re.DOTALL).strip()

            # Handle potential markdown code blocks
            if '```json' in content:
                content = content.split('```json')[1].split('```')[0]
            elif '```' in content:
                content = content.split('```')[1].split('```')[0]

            # Try to extract JSON from response
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Try to find JSON object in the text
                json_match = re.search(r'\{[^{}]*"search_queries"[^{}]*\}', content)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                else:
                    raise Exception(f"Could not parse JSON from response: {content[:200]}")
            
            logger.info(f"🧠 AI Query Optimizer: entity='{parsed.get('entity_name')}', "
                       f"type='{parsed.get('entity_type')}', "
                       f"location='{parsed.get('location')}', "
                       f"queries={len(parsed.get('search_queries', []))}")
            
            return parsed
            
        except Exception as e:
            logger.warning(f"🧠 AI query optimization failed (using fallback): {e}")
            return None

    def _extract_multiple_search_queries(self, user_message: str, ai_optimization: dict = None) -> list:
        """
        Extract MULTIPLE search queries for comprehensive research.
        
        This is especially important for queries asking about specific people, 
        organizations, or facts that require precise search terms.
        
        Designed to be sector-agnostic - works for any industry.
        
        Args:
            user_message: The original user query
            ai_optimization: Optional AI-generated query optimization dict
        
        Returns:
            List of search query strings to try (in priority order)
        """
        import re
        
        queries = []
        user_lower = user_message.lower()
        
        # ═══════════════════════════════════════════════════════════════════
        # PRIORITY 1: Use AI-optimized queries if available
        # ═══════════════════════════════════════════════════════════════════
        if ai_optimization and ai_optimization.get('search_queries'):
            ai_queries = ai_optimization['search_queries']
            entity_type = ai_optimization.get('entity_type', '')
            location = ai_optimization.get('location', '')
            negative_terms = ai_optimization.get('negative_terms', [])
            
            logger.info(f"🧠 Using AI-optimized queries: {ai_queries[:3]}")
            
            # Add AI queries with disambiguation
            for q in ai_queries[:5]:
                # Add location if not already present
                if location and location.lower() not in q.lower():
                    q = f"{q} {location}"
                queries.append(q)
            
            # Add negative term exclusions for search engines that support it
            if negative_terms:
                # Create a filtered version of the first query
                base_query = ai_queries[0] if ai_queries else user_message[:50]
                exclusions = ' '.join(f'-"{term}"' for term in negative_terms[:5])
                queries.append(f'{base_query} {exclusions}')

                # Also add site-specific exclusions for common wrong entity types
                for term in negative_terms:
                    term_lower = term.lower()
                    if 'school' in term_lower:
                        queries.append(f'{base_query} -site:greatschools.org -site:niche.com -site:k12.*')
                    if 'university' in term_lower:
                        queries.append(f'{base_query} -site:.edu')
            
            # Still fall through to add some heuristic queries as backup
        
        # ═══════════════════════════════════════════════════════════════════
        # FALLBACK: Heuristic-based query generation
        # ═══════════════════════════════════════════════════════════════════
        
        # Detect if this is a "who" query (asking about people) - universal patterns
        is_who_query = any(kw in user_lower for kw in [
            'who are', 'who is', 'list of', 'names of', 'staff', 'team', 
            'employees', 'members', 'people', 'personnel', 'directory',
            'contact', 'leadership', 'management', 'executives'
        ])
        
        # Detect organization names (capitalized multi-word phrases)
        # This captures "Northside Hospital Atlanta", "Microsoft Corporation", etc.
        org_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        organizations = re.findall(org_pattern, user_message)
        
        # Also try to find organizations mentioned with "at" or "in"
        at_pattern = r'(?:at|in|from|for)\s+([A-Za-z][A-Za-z\s]+?)(?:\s+in\s+|\s+company|\s+organization|\s+group|\s*$|\s*\d)'
        at_matches = re.findall(at_pattern, user_message, re.IGNORECASE)
        for match in at_matches:
            cleaned = match.strip()
            if len(cleaned) > 3 and cleaned not in organizations:
                organizations.append(cleaned)
        
        # CRITICAL: Identify organization type keywords to keep in queries
        # These distinguish "Northside Hospital" from "Northside High School"
        org_type_keywords = ['hospital', 'medical', 'clinic', 'university', 'college', 
                            'company', 'corporation', 'inc', 'llc', 'firm', 'bank',
                            'center', 'institute', 'foundation', 'group', 'services']
        
        org_type_in_query = None
        for kw in org_type_keywords:
            if kw in user_lower:
                org_type_in_query = kw
                break
        
        # Use AI-detected entity type if available
        if ai_optimization and ai_optimization.get('entity_type') and not org_type_in_query:
            org_type_in_query = ai_optimization['entity_type']
        
        # Extract key topic/subject terms (nouns and noun phrases)
        # Remove common stop words and instruction words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                      'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                      'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
                      'could', 'should', 'may', 'might', 'must', 'shall', 'can', 'need',
                      'report', 'write', 'create', 'generate', 'provide', 'give', 'make',
                      'comprehensive', 'detailed', 'about', 'regarding', 'concerning'}
        
        # Extract meaningful words (potential topics/specialties)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', user_message)
        topic_words = [w for w in words if w.lower() not in stop_words]
        
        # Detect years
        years = re.findall(r'\b(202[0-9]|203[0-9])\b', user_message)
        
        # Build search queries based on what we found
        
        # Query 1: FULL organization name quoted (most specific and important)
        # e.g., "Northside Hospital Atlanta" cardiac doctors
        if organizations:
            org = organizations[0]
            if topic_words:
                topics = ' '.join(topic_words[:3])
                queries.append(f'"{org}" {topics}')
            else:
                queries.append(f'"{org}"')
        
        # Query 2: If we have an org type keyword, make sure it's included
        # This prevents "Northside Hospital" from matching "Northside High School"
        if organizations and org_type_in_query:
            org = organizations[0]
            # If org already contains the type, just search with topics
            if org_type_in_query not in org.lower():
                # Add the type explicitly: "Northside" + hospital
                queries.append(f'"{org}" {org_type_in_query}')
            # Also try: organization + type + topic
            if topic_words:
                queries.append(f'{org} {org_type_in_query} {topic_words[0]}')
        
        # Query 3: Organization + staff/directory (for people queries)
        # NOTE: Bing has issues with certain keywords - use specialized queries for reliability
        if is_who_query and organizations:
            org = organizations[0]
            type_suffix = f" {org_type_in_query}" if org_type_in_query else ""

            # Strategy: Use general site-specific searches that work for any organization
            # without hardcoding domain variations
            org_domain = org.lower().replace(' ', '')

            # Basic TLD variations - organizations typically have one main site
            for tld in ['.com', '.org', '.net']:
                queries.append(f'site:{org_domain}{tld} "{org}"')
                queries.append(f'site:{org_domain}{tld} staff')
                queries.append(f'site:{org_domain}{tld} team')

            # For healthcare specifically, add medical-specific queries
            if org_type_in_query in ['hospital', 'medical', 'clinic', 'health']:
                queries.append(f'site:{org_domain}.com "find a doctor"')
                queries.append(f'site:{org_domain}.com "our physicians"')
                queries.append(f'site:{org_domain}.com "medical staff"')
                
                # Healthcare organizations often have specialty-specific subdomains
                # e.g., northsidecvi.com for cardiovascular, northsideradiology.com, etc.
                # Also try common patterns for finding doctor directories
                org_short = org.split()[0].lower()  # First word, e.g., "northside"
                queries.append(f'"{org_short}" cardiologists physicians directory site:.com')
                queries.append(f'"{org_short}" cardiovascular institute doctors')
                queries.append(f'site:{org_short}cvi.com OR site:{org_short}heart.com OR site:{org_short}cardio.com')

            # Fallback: basic org search
            queries.append(f'"{org}"{type_suffix}')
        
        # Query 4: Try organization website search (site-specific is most reliable)
        if organizations:
            org = organizations[0]
            org_domain = org.lower().replace(' ', '')

            # Site-specific searches - most reliable for entity disambiguation
            # Try common TLDs to find the official website
            for tld in ['.com', '.org', '.net', '.io', '.co']:
                queries.append(f'site:{org_domain}{tld}')

            # Force title match for the organization name
            queries.append(f'intitle:{org}')

            # Generic negative patterns for common wrong entity types
            # These work across all sectors, not hardcoded for specific cases
            if ai_optimization and ai_optimization.get('negative_terms'):
                # Use AI-detected negative terms
                for term in ai_optimization['negative_terms'][:3]:
                    queries.append(f'{org} "-{term}"')
            else:
                # Fallback generic exclusions based on entity type
                if org_type_in_query in ['hospital', 'medical', 'clinic', 'health']:
                    # Medical queries should exclude education sites
                    queries.append(f'{org} -school -university -k12')
                elif org_type_in_query in ['university', 'college']:
                    # Education queries should exclude medical facilities
                    queries.append(f'{org} -hospital -clinic -medical center')
        
        # Query 5: Original cleaned query (fallback)
        base_query = self._extract_search_query(user_message)
        if base_query and base_query not in queries:
            queries.append(base_query)
        
        # Add year context to first few queries if specified
        if years:
            year = years[0]
            queries = [f"{q} {year}" if year not in q else q for q in queries[:2]] + queries[2:]
        
        # Deduplicate while preserving order
        seen = set()
        unique_queries = []
        for q in queries:
            q_lower = q.lower().strip()
            if q_lower and q_lower not in seen and len(q_lower) > 3:
                seen.add(q_lower)
                unique_queries.append(q)
        
        logger.info(f"📝 Generated {len(unique_queries)} search queries: {unique_queries[:3]}...")
        return unique_queries[:10]  # Return max 10 queries for comprehensive research

    def _should_trigger_web_search(
        self,
        query: str,
        has_local_context: bool = False,
        force: bool = False
    ) -> tuple[bool, str]:
        """Smart filtering to determine if web search should be triggered.

        Web search is expensive (5+ seconds), so only trigger when truly needed.
        Based on analysis of common LLM query patterns across 15+ categories.

        Query Categories (ordered by frequency):
        1. CONVERSATIONAL - greetings, thanks, yes/no (SKIP)
        2. META/HELP - what can you do, who are you (SKIP - use system knowledge)
        3. FOLLOW-UP - can you explain more, what do you mean (SKIP - use conversation context)
        4. DOCUMENT/DATA - questions about uploaded docs/honey jars (SKIP - use local context)
        5. CODE/TECHNICAL - write code, debug, explain code (SKIP - LLM knowledge sufficient)
        6. CREATIVE - write a poem, story, email draft (SKIP - no external data needed)
        7. SUMMARIZATION - summarize this, TLDR (SKIP - operates on provided content)
        8. MATH/CALCULATION - compute, calculate, solve (SKIP - LLM can do this)
        9. TRANSLATION - translate this to X (SKIP - LLM knowledge sufficient)
        10. FORMAT/CONVERT - convert to JSON, format this (SKIP - structural task)
        11. DEFINITION/EXPLAIN - what is X, define Y (CONDITIONAL - usually static knowledge)
        12. HOW-TO/TUTORIAL - how do I, steps to (CONDITIONAL - may need current best practices)
        13. COMPARISON - X vs Y, pros and cons (CONDITIONAL - may need current product info)
        14. OPINION/ADVICE - should I, recommend (CONDITIONAL - depends on topic currency)
        15. RESEARCH/ANALYSIS - deep dive, investigate (SEARCH - benefits from current data)
        16. CURRENT EVENTS - latest news, recent updates (SEARCH - requires fresh data)
        17. EXPLICIT SEARCH - search for, look up online (SEARCH - user explicitly requested)

        Args:
            query: User's message
            has_local_context: Whether honey jars/docs provided sufficient context
            force: Force web search regardless of other checks (for report generation)

        Returns:
            Tuple of (should_search, reason)
        """
        # CRITICAL: If force=True, always search (used for report generation)
        if force:
            return True, "forced_for_report"
        query_lower = query.lower().strip()
        query_words = query_lower.split()
        word_count = len(query_words)
        
        # =========================================================================
        # CATEGORY 17: EXPLICIT SEARCH REQUESTS - Always trigger
        # =========================================================================
        explicit_search_patterns = [
            r'\b(search|google|bing)\s+(online|the web|internet|for me)\b',
            r'\b(search for|search up|look up|look for|find me|find out about)\b',
            r'\bsearch\s+the\s+(web|internet|news)\b',
            r'\bgoogle\s+(this|that|it)\b',
            r'\bwhat does the (web|internet) say about\b',
        ]
        for pattern in explicit_search_patterns:
            if re.search(pattern, query_lower):
                return True, "explicit_search_request"
        
        # =========================================================================
        # CATEGORY 16: CURRENT EVENTS / TIME-SENSITIVE - Always trigger  
        # =========================================================================
        current_events_patterns = [
            r'\b(latest|newest|most recent|current|today\'?s?|this week\'?s?)\s+(news|updates?|developments?|events?|version|release)\b',
            r'\bwhat\'?s?\s+(happening|going on|new)\s+(with|in|at)\b',
            r'\brecent\s+(news|updates?|developments?|changes?|announcements?)\b',
            r'\b(20[2-3][0-9])\s+(news|updates?|trends?|statistics?|data)\b',  # Year-specific current data
            r'\bhow is .+ (doing|performing|trending)\s+(now|today|currently|this year)\b',
            r'\bbreaking\s+news\b',
            r'\bstock\s+price\b',  # Financial data needs real-time
            r'\bweather\s+(in|for|today|tomorrow)\b',  # Weather is always current
        ]
        for pattern in current_events_patterns:
            if re.search(pattern, query_lower):
                return True, "current_events"
        
        # =========================================================================
        # CATEGORY 1: CONVERSATIONAL - Greetings, thanks, acknowledgments (SKIP)
        # =========================================================================
        conversational_patterns = [
            # Greetings (with optional punctuation/emoji-like patterns)
            r'^(hi+|hello+|hey+|yo|sup|greetings|howdy|hiya)[\s!.,?~]*$',
            r'^(hi|hello|hey)\s+(there|bee|assistant|buddy|friend)[\s!.,?]*$',
            r'^good\s+(morning|afternoon|evening|day|night)[\s!.,?]*$',
            # Farewells
            r'^(bye+|goodbye|later|cya|see ya|take care|good night)[\s!.,?]*$',
            # Thanks/acknowledgments  
            r'^(thanks?|thank\s+you|thx|ty|cheers|appreciated?|much appreciated)[\s!.,?]*$',
            r'^(great|awesome|perfect|excellent|wonderful|fantastic|cool|nice|good|ok(ay)?|alright|got it|understood|makes sense|i see)[\s!.,?]*$',
            # Affirmations/negations
            r'^(yes|no|yeah|yep|yup|nope|nah|sure|of course|definitely|absolutely|certainly)[\s!.,?]*$',
            # Apologies
            r'^(sorry|apologies|my bad|oops)[\s!.,?]*$',
            # Pleasantries
            r'^(how are you|how\'?s it going|what\'?s up)[\s!.,?]*$',
        ]
        for pattern in conversational_patterns:
            if re.match(pattern, query_lower):
                return False, "conversational"
        
        # =========================================================================
        # CATEGORY 2: META/HELP - Questions about the assistant (SKIP)
        # =========================================================================
        meta_patterns = [
            r'^(who|what)\s+(are|is)\s+(you|bee|this|sting)[\s?]*$',
            r'^what\s+(can|do)\s+you\s+(do|help|know|offer)[\s?]*$',
            r'^(can|will|would|could)\s+you\s+help\s+(me|us)[\s?]*$',
            r'^tell\s+me\s+about\s+(yourself|you|your capabilities)[\s?]*$',
            r'^how\s+(do|can)\s+(i|we)\s+use\s+(you|this|sting)[\s?]*$',
            r'^what\s+are\s+your\s+(capabilities|features|functions)[\s?]*$',
            r'^(help|help me|i need help)[\s!?]*$',
            r'^what\s+is\s+(sting|this platform|this tool)[\s?]*$',
        ]
        for pattern in meta_patterns:
            if re.match(pattern, query_lower):
                return False, "meta_question"
        
        # =========================================================================
        # CATEGORY 3: FOLLOW-UP / CLARIFICATION - Use conversation context (SKIP)
        # =========================================================================
        followup_patterns = [
            r'^(can you|could you|please)\s+(explain|elaborate|clarify|expand)\s+(more|further|on that)?\b',
            r'^what\s+(do|did)\s+you\s+mean\s+by\b',
            r'^(tell|say)\s+(me|that)\s+(more|again)\b',
            r'^(go on|continue|keep going|more please)\b',
            r'^(why|how)\s+(is|do|does|did)\s+that\b',
            r'^what\s+about\b',
            r'^and\s+(what|how|why)\b',  # Continuation questions
            r'^(also|additionally|furthermore)\b',
            r'^(can you|could you)\s+give\s+(me\s+)?(an?\s+)?example\b',
        ]
        for pattern in followup_patterns:
            if re.match(pattern, query_lower):
                return False, "followup_question"
        
        # =========================================================================
        # CATEGORY 5: CODE/TECHNICAL - Programming tasks (SKIP)
        # =========================================================================
        code_patterns = [
            r'\b(write|create|generate|make)\s+(a\s+)?(code|script|function|class|program|snippet)\b',
            r'\b(debug|fix|correct|refactor)\s+(this|my|the)?\s*(code|script|function|error|bug)\b',
            r'\b(explain|what does)\s+(this|the)?\s*(code|function|script|snippet)\b',
            r'\bhow\s+(do|can)\s+(i|we)\s+(code|program|implement|write)\b',
            r'\b(python|javascript|java|c\+\+|rust|go|typescript|sql|bash|html|css)\s+(code|script|function)\b',
            r'\bconvert\s+.+\s+to\s+(python|javascript|java|typescript|sql)\b',
            r'\b(regex|regular expression)\s+(for|to|that)\b',
            r'\b(api|endpoint|route|query)\s+(for|to|that)\b',
        ]
        for pattern in code_patterns:
            if re.search(pattern, query_lower):
                return False, "code_task"
        
        # =========================================================================
        # CATEGORY 6: CREATIVE WRITING - No external data needed (SKIP)
        # =========================================================================
        creative_patterns = [
            r'\b(write|create|compose|draft|generate)\s+(a\s+)?(poem|story|song|lyrics|haiku|limerick|joke)\b',
            r'\b(write|create|draft|compose)\s+(a\s+)?(an?\s+)?(email|letter|message|text|memo|note)\b',
            r'\b(write|create|generate)\s+(a\s+)?(creative|fiction|fictional)\b',
            r'\bmake\s+(this|it)\s+(sound|more)\s+(professional|formal|casual|friendly|funny)\b',
            r'\brewrite\s+(this|it)\s+(to|as|in)\b',
            r'\b(brainstorm|come up with)\s+(ideas?|names?|titles?)\b',
        ]
        for pattern in creative_patterns:
            if re.search(pattern, query_lower):
                return False, "creative_writing"
        
        # =========================================================================
        # CATEGORY 7: SUMMARIZATION - Operates on provided content (SKIP)
        # =========================================================================
        summarization_patterns = [
            r'\b(summarize|summary|summarise)\s+(this|the|that|it|these)\b',
            r'\b(tldr|tl;dr|too long)\b',
            r'\bgive\s+me\s+(a\s+)?(brief|short|quick)\s+(summary|overview|rundown)\b',
            r'\bwhat\s+(are\s+)?the\s+(main|key)\s+(points?|takeaways?|ideas?)\b',
            r'\bboil\s+(this|it)\s+down\b',
            r'\bcondense\s+(this|it)\b',
        ]
        for pattern in summarization_patterns:
            if re.search(pattern, query_lower):
                return False, "summarization"
        
        # =========================================================================
        # CATEGORY 8: MATH/CALCULATION - LLM can handle (SKIP)
        # =========================================================================
        math_patterns = [
            r'\b(calculate|compute|solve|evaluate)\s+(this|the|for)?\b',
            r'\bwhat\s+is\s+\d+\s*[\+\-\*\/\^]\s*\d+',  # Basic arithmetic
            r'\b\d+\s*[\+\-\*\/\^]\s*\d+\s*=\s*\?\b',
            r'\b(convert|how many)\s+\d+\s*(meters?|feet|miles?|km|kg|pounds?|celsius|fahrenheit)\b',
            r'\bpercentage\s+of\b',
            r'\b(average|mean|median|sum|total)\s+of\b',
        ]
        for pattern in math_patterns:
            if re.search(pattern, query_lower):
                return False, "math_calculation"
        
        # =========================================================================
        # CATEGORY 9: TRANSLATION - LLM knowledge sufficient (SKIP)
        # =========================================================================
        translation_patterns = [
            r'\btranslate\s+(this|it|the following)?\s*(to|into)\s+\w+\b',
            r'\bhow\s+(do|would)\s+(you|i)\s+say\s+.+\s+in\s+\w+\b',
            r'\bwhat\s+is\s+.+\s+in\s+(spanish|french|german|chinese|japanese|korean|arabic|portuguese|italian|russian)\b',
            r'\b(spanish|french|german|chinese|japanese|korean|arabic|portuguese|italian|russian)\s+(translation|word)\s+for\b',
        ]
        for pattern in translation_patterns:
            if re.search(pattern, query_lower):
                return False, "translation"
        
        # =========================================================================
        # CATEGORY 10: FORMAT/CONVERT - Structural task (SKIP)
        # =========================================================================
        format_patterns = [
            r'\bconvert\s+(this|it)\s+to\s+(json|xml|yaml|csv|markdown|html|pdf)\b',
            r'\bformat\s+(this|it)\s+(as|into|to)\b',
            r'\b(prettify|beautify|format)\s+(this|the|my)\s*(json|xml|code|text)\b',
            r'\bmake\s+(this|it)\s+(a\s+)?(table|list|bullet points?)\b',
            r'\bparse\s+(this|the)\b',
            r'\bextract\s+(the\s+)?(data|information|fields?)\s+from\b',
        ]
        for pattern in format_patterns:
            if re.search(pattern, query_lower):
                return False, "formatting"
        
        # =========================================================================
        # SHORT QUERY CHECK - Very short queries are usually conversational (SKIP)
        # =========================================================================
        if word_count <= 2:
            return False, "too_short"
        
        # =========================================================================
        # CATEGORY 4: DOCUMENT/DATA QUERIES - Use local context if available (SKIP)
        # BUT: Entity queries about specific organizations/people still need web search
        # =========================================================================
        if has_local_context:
            # Check if this is a query about a specific entity that requires current external data
            # These queries need web search even if we have local context
            entity_query_patterns = [
                # Queries about specific people/staff at organizations
                r'\b(who are|who is|list of|names of|doctors?|physicians?|staff|team|employees|members|personnel|directory|leadership|management|executives)\b',
                # Queries about entities with organization type (handles "at Northside Hospital Atlanta")
                # Note: after lower() the query is all lowercase, so use lowercase patterns
                r'\bat\s+(the\s+)?[a-z]+(?:\s+[a-z]+){0,3}\s+(hospital|university|college|school|company|corporation|institute|center|clinic|foundation)\b',
                # Year-specific queries
                r'\b(at|in|for)\s+([a-z]+\s+){1,3}(2024|2025|2026)\b',
                # Medical/care provider queries
                r'\b(specialists?|providers?|medical staff|nurses?|surgeons?|cardiologists?)\b',
                # Report generation requests about specific organizations (comprehensive report about X)
                r'\b(report|analysis|study)\s+(about|on|of)\s+[a-z]+(?:\s+[a-z]+){0,3}\s+(hospital|university|company|corporation|institute|center|clinic)\b',
            ]
            for pattern in entity_query_patterns:
                if re.search(pattern, query_lower):
                    return True, "entity_query_needs_web_search"

            # If NOT an entity query and we have local context, skip web search
            return False, "has_local_context"
        
        # =========================================================================
        # CATEGORY 11: DEFINITION/EXPLAIN - Usually static knowledge (CONDITIONAL)
        # Check if asking about something that changes over time
        # =========================================================================
        definition_patterns = [
            r'^what\s+is\s+(a\s+|an\s+|the\s+)?\w+[\s?]*$',  # Simple "what is X"
            r'^define\s+\w+[\s?]*$',
            r'^(what|who)\s+(is|are|was|were)\s+',
            r'\bexplain\s+(what|how|why)\s+',
        ]
        # Check if it's about a timeless concept (skip search) or current topic (search)
        timeless_indicators = [
            r'\b(definition|meaning|concept|theory|principle|law|formula)\b',
            r'\b(history|historical|origin|etymology)\b',  # Historical = static
        ]
        for pattern in definition_patterns:
            if re.search(pattern, query_lower):
                # If it's clearly about timeless knowledge, skip search
                if any(re.search(t, query_lower) for t in timeless_indicators):
                    return False, "timeless_definition"
                # Otherwise, let it fall through to research checks
        
        # =========================================================================
        # CATEGORY 15: RESEARCH/ANALYSIS - Benefits from current data (SEARCH)
        # =========================================================================
        research_patterns = [
            r'\b(research|investigate|analyze|analysis|deep dive|comprehensive)\s+(on|into|about|of)\b',
            r'\b(best practices?|industry standards?|recommendations?)\s+(for|in|on)\b',
            r'\b(state of the art|cutting edge|latest developments?)\s+(in|for|on)\b',
            r'\b(market|industry|sector)\s+(analysis|overview|landscape|trends?)\b',
            r'\b(compare|comparison|versus|vs\.?|difference between)\s+.+\s+(and|vs\.?|versus)\b',
            r'\b(pros and cons|advantages and disadvantages|benefits and drawbacks)\b',
            r'\b(security|threat|vulnerability|attack|risk)\s+(assessment|analysis|landscape|report)\b',
            r'\b(compliance|regulatory|gdpr|hipaa|pci|sox)\s+(requirements?|standards?|guidelines?)\b',
        ]
        for pattern in research_patterns:
            if re.search(pattern, query_lower):
                return True, "research_query"
        
        # =========================================================================
        # CATEGORY 12 & 14: HOW-TO and OPINION - Check if current info needed
        # =========================================================================
        howto_needing_search = [
            r'\bhow\s+to\s+.+\s+in\s+20[2-3][0-9]\b',  # Year-specific how-to
            r'\bbest\s+way\s+to\s+.+\s+(now|today|currently)\b',
            r'\b(should i|would you recommend)\s+.+\s+(in 20[2-3][0-9]|now|today|currently)\b',
            r'\bwhat\s+(tools?|software|products?|services?)\s+(should|do you recommend)\b',
        ]
        for pattern in howto_needing_search:
            if re.search(pattern, query_lower):
                return True, "howto_current"
        
        # =========================================================================
        # MODERATE LENGTH CHECK - 4-8 words, no research indicators = likely simple Q
        # =========================================================================
        if word_count >= 4 and word_count <= 8:
            # Simple questions that don't need search
            simple_question_starts = [
                r'^what\s+is\s+',
                r'^who\s+is\s+',
                r'^how\s+do\s+(i|you)\s+',
                r'^can\s+(i|you)\s+',
                r'^why\s+(is|are|do|does)\s+',
                r'^when\s+(is|was|did)\s+',
                r'^where\s+(is|are|do)\s+',
            ]
            if any(re.match(p, query_lower) for p in simple_question_starts):
                return False, "simple_question"
        
        # =========================================================================
        # DEFAULT: Skip web search for regular chat
        # Conservative approach - better to be fast than exhaustive
        # =========================================================================
        return False, "default_skip"

    async def get_web_search_context(self, query: str, force: bool = False, has_local_context: bool = False) -> List[Dict[str, str]]:
        """Get context from web search with full content fetching (if enabled by admin)
        
        Uses smart filtering to avoid expensive web searches for simple queries.
        For entity queries (who/what/specific names), uses multiple search queries
        to maximize chances of finding accurate information.
        
        Args:
            query: User's message
            force: Force web search regardless of smart filtering (for reports)
            has_local_context: Whether honey jars provided sufficient context
        """
        if not self.web_search or not self.web_search.enabled:
            return []

        try:
            # Smart filtering - skip web search for conversational/simple queries
            if not force:
                should_search, reason = self._should_trigger_web_search(query, has_local_context)
                if not should_search:
                    logger.info(f"⏭️ Skipping web search (reason: {reason})")
                    return []
            
            # Determine if this needs multi-query search (entity/research queries)
            query_lower = query.lower()
            needs_multi_query = any(kw in query_lower for kw in [
                'who are', 'who is', 'list of', 'names of', 'doctors', 'physicians',
                'staff', 'team', 'employees', 'find', 'directory', 'contact',
                'specialists', 'report', 'research', 'comprehensive'
            ]) or force  # Reports always use multi-query for better research
            
            all_results = []
            seen_urls = set()
            
            # ═══════════════════════════════════════════════════════════════════
            # AI QUERY OPTIMIZATION: Use LLM to generate smarter search queries
            # This prevents issues like "Northside Hospital" → "Northside High School"
            # ═══════════════════════════════════════════════════════════════════
            ai_optimization = None
            if needs_multi_query:
                try:
                    logger.info("🧠 Running AI query optimization...")
                    ai_optimization = await self._ai_optimize_search_query(query)
                except Exception as e:
                    logger.warning(f"🧠 AI optimization skipped: {e}")
            
            if needs_multi_query:
                # Use multiple search queries for comprehensive research
                search_queries = self._extract_multiple_search_queries(query, ai_optimization)
                logger.info(f"🔍 Multi-query search: trying {len(search_queries)} queries")
                
                # Log AI optimization results
                if ai_optimization:
                    logger.info(f"🧠 AI-optimized: entity='{ai_optimization.get('entity_name')}', "
                               f"type='{ai_optimization.get('entity_type')}', "
                               f"negative_terms={ai_optimization.get('negative_terms', [])}")
                
                for i, search_query in enumerate(search_queries):
                    if len(all_results) >= 20:  # Stop if we have enough results
                        logger.info(f"📊 Got {len(all_results)} results, stopping search iteration")
                        break
                    
                    logger.info(f"🔍 Query {i+1}/{len(search_queries)}: '{search_query}'")
                    try:
                        results = await self.web_search.search_and_fetch(search_query)
                        if results:
                            # Filter results if we have AI-detected negative terms
                            if ai_optimization and ai_optimization.get('negative_terms'):
                                negative_terms = [t.lower() for t in ai_optimization['negative_terms']]
                                filtered_results = []
                                for r in results:
                                    title = r.get('title', '').lower()
                                    url = r.get('url', '').lower()
                                    # Skip results that match negative terms
                                    if not any(neg in title or neg in url for neg in negative_terms):
                                        filtered_results.append(r)
                                    else:
                                        logger.info(f"  🚫 Filtered out (negative match): {r.get('title', '')[:50]}")
                                results = filtered_results
                            
                            # Add unique results (avoid duplicates from different queries)
                            for r in results:
                                url = r.get('url', '')
                                if url and url not in seen_urls:
                                    seen_urls.add(url)
                                    all_results.append(r)
                                    logger.debug(f"  ✅ Added: {r.get('title', 'Untitled')[:50]}")
                    except Exception as e:
                        logger.warning(f"Query '{search_query}' failed: {e}")
                        continue
            else:
                # Single query for simple lookups
                search_query = self._extract_search_query(query)
                logger.info(f"🔍 Web search query: '{search_query}'")
                all_results = await self.web_search.search_and_fetch(search_query) or []
            
            if all_results:
                # Log what we got
                fetched_count = sum(1 for r in all_results if r.get("full_content"))
                total_chars = sum(len(r.get("full_content", "")) for r in all_results)
                logger.info(f"🌐 Web search returned {len(all_results)} unique results ({fetched_count} with full content, {total_chars} chars total)")
            
            return all_results[:10]  # Cap at 10 results to avoid overwhelming context
        except Exception as e:
            logger.warning(f"Web search failed: {e}")
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
        custom_system_prompt: Optional[str] = None,
        skip_web_search: bool = False,
        force_web_search: bool = False,
        original_message: Optional[str] = None  # Use original message for web search (before PII serialization)
    ) -> str:
        """Build an enhanced prompt that preserves Bee's personality while adding context

        Args:
            user_message: The user's message/query (PII-serialized for LLM prompt)
            user_id: User identifier
            conversation_id: Optional conversation ID for history loading
            conversation_history: Optional pre-loaded history
            honey_jar_id: Optional specific honey jar to query
            custom_system_prompt: If provided (e.g., for Nectar Bots), use this instead of Bee's prompt
            skip_web_search: Skip web search context (for internal/system calls like title generation)
            force_web_search: Force web search (for reports that benefit from external research)
            original_message: Original user message before PII serialization (used for web search queries)

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

        # Check if this is a simple conversational query that doesn't need context lookups
        # This dramatically speeds up responses for greetings, thanks, etc.
        is_simple_query = self._is_simple_conversational_query(user_message)
        
        if is_simple_query:
            # Fast path: Only load history and system prompt for simple queries
            logger.info(f"⚡ Fast path: skipping knowledge lookups for simple query")
            results = await asyncio.gather(
                load_history(),
                load_system_prompt(),
                return_exceptions=True
            )
            # Pad results to match expected structure
            history_result = results[0] if not isinstance(results[0], Exception) else {"messages": conversation_history or [], "summary": None}
            system_prompt = results[1] if not isinstance(results[1], Exception) else "You are Bee, a helpful AI assistant."
            honey_jar_results = []
            doc_results = []
            brain_knowledge = ""
        else:
            # Full path: Load all context in parallel for substantive queries
            # Phase 1: Load local context in parallel (fast operations)
            # Web search is deferred to Phase 2 after we know if local context was found
            results = await asyncio.gather(
                load_history(),
                load_system_prompt(),
                load_honey_jar(),
                load_docs(),
                load_brain(),
                return_exceptions=True  # Don't fail if one task fails
            )
            
            # Unpack Phase 1 results (handle exceptions gracefully)
            history_result = results[0] if not isinstance(results[0], Exception) else {"messages": conversation_history or [], "summary": None}
            system_prompt = results[1] if not isinstance(results[1], Exception) else "You are Bee, a helpful AI assistant."
            honey_jar_results = results[2] if not isinstance(results[2], Exception) else []
            doc_results = results[3] if not isinstance(results[3], Exception) else []
            brain_knowledge = results[4] if not isinstance(results[4], Exception) else ""
            
            # Log any exceptions that occurred
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    task_names = ['history', 'system_prompt', 'honey_jar', 'docs', 'brain']
                    logger.warning(f"⚠️ Context task '{task_names[i]}' failed: {result}")
        
        # Phase 2: Conditionally trigger web search based on local context availability
        # This avoids expensive web searches when we already have good local data
        web_search_results = []
        if not skip_web_search and not is_simple_query:
            # Check if we have sufficient local context
            has_local_context = bool(honey_jar_results) or bool(doc_results) or bool(brain_knowledge)

            # Use original message for search queries (before PII serialization)
            # Falls back to user_message if original_message not provided
            search_message = original_message if original_message else user_message

            # Smart filtering happens inside get_web_search_context
            # force=True bypasses smart filtering (for reports that benefit from research)
            web_search_results = await self.get_web_search_context(
                search_message,
                force=force_web_search,  # Force for reports, smart filter for chat
                has_local_context=has_local_context
            )

        # Extract messages and summary from history result
        conversation_history = history_result.get("messages", [])
        conversation_summary = history_result.get("summary")

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

        # Add web search context (if enabled and results found)
        # These sources should be cited in reports - we number them for easy reference
        if web_search_results:
            context_parts.append("\n## Web Research Sources - COPY THESE URLs INTO YOUR REFERENCES")
            context_parts.append("="*60)
            context_parts.append("INSTRUCTION: For each source below, copy the FULL URL into your References section.")
            context_parts.append("Format your references as: [Title](https://full-url-here)")
            context_parts.append("="*60)
            source_num = 1
            for result in web_search_results[:5]:  # Allow up to 5 sources for better citation coverage
                title = result.get('title', 'Untitled')
                snippet = result.get('snippet', '')[:250]
                url = result.get('url', '')
                full_content = result.get('full_content', '')
                
                context_parts.append(f"\n--- SOURCE {source_num} ---")
                context_parts.append(f"TITLE: {title}")
                context_parts.append(f"URL TO COPY: {url}")
                context_parts.append(f"USE IN REFERENCES AS: [{title}]({url})")
                
                # Use full content if available, otherwise use snippet
                if full_content:
                    context_parts.append(f"CONTENT:\n{full_content[:2000]}")  # Up to 2000 chars per source
                else:
                    context_parts.append(f"CONTENT: {snippet}...")
                source_num += 1
            
            context_parts.append("\n" + "="*60)
            context_parts.append("END OF WEB SOURCES - Remember to include these URLs in your References!")
            context_parts.append("="*60)

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
        
        # Build the prompt - IMPORTANT: Critical rules come BEFORE system prompt
        # This ensures anti-hallucination and truthfulness take priority over general "be thorough" instructions
        context_section = f"\n\n{chr(10).join(context_parts)}\n" if context_parts else ""

        prompt = f"""=== CRITICAL INSTRUCTIONS (HIGHEST PRIORITY) ===
The following rules override any other instructions. You MUST follow these at all costs:

1. TRUTHFULNESS IS NON-NEGOTIABLE
   - ONLY include names, facts, and details that appear in the provided sources
   - If specific names (doctors, staff, executives, etc.) are NOT in your sources, you MUST say: "I could not find specific names in my research"
   - NEVER fabricate names, titles, credentials, or any information
   - When uncertain, use phrases like "According to sources..." or "Sources indicate..."

2. ADDRESS THE ACTUAL REQUEST
   - If asked about "cardiac doctors at [hospital]" and no doctor names are in sources, report that you couldn't find specific names
   - Do NOT invent people to make the report seem more complete
   - Providing fabricated information is worse than providing less information

3. SOURCE ATTRIBUTION
   - Every factual claim should be traceable to a source above
   - Include proper source citations in your response

=== END CRITICAL INSTRUCTIONS ===

{system_prompt}
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

        # Index in ChromaDB for semantic search (NON-BLOCKING - fire and forget)
        # This runs in background because:
        # 1. PostgreSQL already has the message (source of truth)
        # 2. Redis cache has it for fast retrieval
        # 3. ChromaDB semantic indexing can complete asynchronously
        if self.conversation_search and self.conversation_search.enabled:
            async def _background_index():
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
                    logger.warning(f"Background index failed: {e}")
            
            # Fire and forget - don't await
            asyncio.create_task(_background_index())

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
            "web_search": {"enabled": False},
            "brain_loaded": self.brain_loaded,
        }

        if self.conversation_cache:
            stats["conversation_cache"] = {"enabled": self.conversation_cache.enabled}

        if self.conversation_search:
            stats["semantic_search"] = self.conversation_search.get_stats()

        if self.knowledge_indexer:
            stats["knowledge_indexer"] = {"enabled": self.knowledge_indexer.enabled}

        if self.web_search:
            stats["web_search"] = self.web_search.get_status()

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

    # ═══════════════════════════════════════════════════════════════════════════════
    # CONTEXT USAGE TRACKING & AWARENESS
    # Provides visibility into context window usage and warnings
    # ═══════════════════════════════════════════════════════════════════════════════

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for a text string.
        Uses a simple heuristic: ~4 characters per token for English text.
        This is a rough approximation - actual tokenization varies by model.
        """
        if not text:
            return 0
        # Rough estimate: 1 token ≈ 4 characters for most English text
        # This is conservative - actual tokenizers may use fewer tokens
        return len(text) // 4

    async def get_context_usage(
        self,
        conversation_id: str,
        user_id: str,
        include_honey_jar: bool = False,
        honey_jar_id: str = None
    ) -> Dict[str, Any]:
        """
        Calculate current context window usage for a conversation.
        
        Returns detailed stats about how much of the available context
        window is being used, with warnings and suggestions.
        
        Args:
            conversation_id: The conversation ID to analyze
            user_id: User ID for the conversation
            include_honey_jar: Whether to include honey jar context in calculation
            honey_jar_id: Optional honey jar ID if include_honey_jar is True
            
        Returns:
            Dict with usage stats, warnings, and suggestions
        """
        # Default context window sizes by provider
        # These are conservative estimates - actual may be higher
        CONTEXT_WINDOWS = {
            "minimax": 1000000,  # MiniMax has 1M token context
            "ollama_default": 32768,  # Default for most local models (increased from 8K)
            "ollama_large": 131072,  # Larger local models (128K)
            "phi4": 16384,
            "qwen": 131072,  # Qwen 2.5 has 128K context
        }
        
        # Get the active provider's context window
        # Default to a reasonable 128K for modern models
        max_context = 131072  # 128K tokens as default
        detected_provider = "unknown"
        
        # Try to detect the active provider
        try:
            # Import provider registry to check active provider
            from providers import provider_registry
            primary = provider_registry.get_primary()
            if primary:
                provider_name = primary.name.lower()
                detected_provider = provider_name
                if "minimax" in provider_name:
                    max_context = CONTEXT_WINDOWS["minimax"]
                    logger.debug(f"Detected MiniMax provider - using {max_context} token context")
                elif "phi" in provider_name:
                    max_context = CONTEXT_WINDOWS["phi4"]
                elif "qwen" in provider_name:
                    max_context = CONTEXT_WINDOWS["qwen"]
        except Exception as e:
            logger.debug(f"Could not detect provider for context window: {e}")
        
        # Calculate current usage components
        usage = {
            "system_prompt_tokens": 0,
            "conversation_history_tokens": 0,
            "honey_jar_tokens": 0,
            "web_search_tokens": 0,
            "brain_knowledge_tokens": 0,
            "total_tokens": 0,
            "max_context_tokens": max_context,
            "usage_percentage": 0.0,
            "messages_count": 0,
            "conversation_id": conversation_id,
        }
        
        # 1. System prompt (bee brain knowledge - typically ~3-5K tokens)
        if self.brain_loaded and self.brain_knowledge:
            usage["brain_knowledge_tokens"] = self._estimate_tokens(self.brain_knowledge)
        
        # 2. Load conversation history and count tokens
        conversation_messages = []
        
        # Try PostgreSQL first (source of truth)
        await self._ensure_conversation_store()
        if self.conversation_store:
            try:
                conversation_messages = await self.conversation_store.get_conversation_history(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    limit=100  # Get up to 100 recent messages
                )
            except Exception as e:
                logger.warning(f"Could not load conversation from PostgreSQL: {e}")
        
        # Fallback to Redis cache
        if not conversation_messages and self.conversation_cache:
            try:
                cached = await self.conversation_cache.get_conversation_history(
                    conversation_id=conversation_id,
                    user_id=user_id,
                    max_messages=100
                )
                conversation_messages = cached if cached else []
            except Exception as e:
                logger.warning(f"Could not load conversation from Redis: {e}")
        
        usage["messages_count"] = len(conversation_messages)
        
        # Count tokens in conversation history
        for msg in conversation_messages:
            content = msg.get("content", "")
            usage["conversation_history_tokens"] += self._estimate_tokens(content)
        
        # 3. Honey jar context (if requested)
        if include_honey_jar and honey_jar_id:
            try:
                honey_jar_context = await self.get_honey_jar_context(
                    honey_jar_id=honey_jar_id,
                    query="",  # Empty query to just get size estimate
                    max_chunks=5
                )
                if honey_jar_context:
                    usage["honey_jar_tokens"] = self._estimate_tokens(honey_jar_context)
            except Exception as e:
                logger.warning(f"Could not estimate honey jar context: {e}")
        
        # 4. Web search budget (from web_search_provider settings)
        if self.web_search and self.web_search.enabled:
            budget = self.web_search.get_context_budget()
            # Estimate max web search tokens based on settings
            max_web_chars = budget.get("max_content_per_source", 2000) * budget.get("max_results", 5)
            usage["web_search_tokens"] = self._estimate_tokens("x" * (max_web_chars // 2))  # Estimate half usage
        
        # Calculate total
        usage["total_tokens"] = (
            usage["brain_knowledge_tokens"] +
            usage["conversation_history_tokens"] +
            usage["honey_jar_tokens"] +
            usage["web_search_tokens"]
        )
        
        # Calculate percentage
        usage["usage_percentage"] = round(
            (usage["total_tokens"] / max_context) * 100, 1
        ) if max_context > 0 else 0.0
        
        # Determine status and generate warnings/suggestions
        warnings = []
        suggestions = []
        status = "healthy"
        
        if usage["usage_percentage"] >= 90:
            status = "critical"
            warnings.append("⚠️ Context window nearly full! Responses may be truncated.")
            suggestions.append("Start a new conversation to continue with full context")
            suggestions.append("Consider summarizing this conversation first")
        elif usage["usage_percentage"] >= 75:
            status = "warning"
            warnings.append("⚡ Context window 75% full - conversation getting long")
            suggestions.append("Consider starting a new conversation soon")
        elif usage["usage_percentage"] >= 50:
            status = "moderate"
        
        # Thread length warning
        if usage["messages_count"] >= 50:
            warnings.append(f"📜 Long conversation: {usage['messages_count']} messages")
            suggestions.append("Earlier messages may be summarized for context")
        elif usage["messages_count"] >= 30:
            suggestions.append("Consider starting a new thread for a fresh context")
        
        usage["status"] = status
        usage["warnings"] = warnings
        usage["suggestions"] = suggestions
        
        # User-friendly summary
        usage["summary"] = self._generate_usage_summary(usage)
        
        return usage

    def _generate_usage_summary(self, usage: Dict[str, Any]) -> str:
        """Generate a user-friendly summary of context usage."""
        pct = usage["usage_percentage"]
        msgs = usage["messages_count"]
        
        if pct < 25:
            return f"✅ Plenty of context available ({pct:.0f}% used, {msgs} messages)"
        elif pct < 50:
            return f"📊 Good context usage ({pct:.0f}% used, {msgs} messages)"
        elif pct < 75:
            return f"📈 Moderate usage ({pct:.0f}% used, {msgs} messages)"
        elif pct < 90:
            return f"⚡ High usage ({pct:.0f}% used, {msgs} messages) - consider new thread soon"
        else:
            return f"⚠️ Critical ({pct:.0f}% used, {msgs} messages) - start new conversation"

    def generate_context_warning_message(self, usage: Dict[str, Any]) -> Optional[str]:
        """
        Generate a warning message to show the user if context is getting full.
        Returns None if no warning needed.
        """
        if usage["status"] == "critical":
            return (
                "🔔 **Context Limit Warning**\n\n"
                "This conversation has reached its context limit. I may not be able to "
                "reference earlier parts of our discussion.\n\n"
                "**Suggestions:**\n"
                "• Start a new conversation for fresh context\n"
                "• Ask me to summarize key points from this conversation\n"
            )
        elif usage["status"] == "warning":
            return (
                "💡 **Heads up:** This conversation is getting long. "
                "Consider starting a new thread soon for optimal performance."
            )
        return None


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