#!/usr/bin/env python3
"""
Web Search Provider - Self-hosted and external web search for AI context

Primary: SearXNG (self-hosted, no API key required)
Fallback: External APIs (Serper, Brave, Tavily) - require API keys

Local-first design with optional external enhancement.

Features:
- Web search via SearXNG or external APIs
- URL content fetching for deep research
- Context-window aware content sizing (adapts to LLM provider)
- Query sanitization for privacy
- Source quality scoring (authoritative domains ranked higher)
- Duplicate detection and removal
- Smart query reformulation for poor results
"""

import os
import re
import logging
import asyncio
from typing import List, Dict, Optional, Set, Tuple, TYPE_CHECKING
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup

if TYPE_CHECKING:
    from providers import ProviderRegistry

logger = logging.getLogger(__name__)


# Context window tiers for content scaling
# Maps max_tokens ranges to content settings
CONTEXT_TIERS = {
    # Tier 1: Small context (< 8K tokens) - ~4 chars per token estimate
    "small": {
        "max_tokens": 8000,
        "max_content_per_source": 1000,
        "max_results": 2,
        "total_web_budget": 2000,
    },
    # Tier 2: Medium context (8K - 32K tokens) - most local models
    "medium": {
        "max_tokens": 32000,
        "max_content_per_source": 2000,
        "max_results": 3,
        "total_web_budget": 5000,
    },
    # Tier 3: Large context (32K - 128K tokens) - GPT-4, Claude
    "large": {
        "max_tokens": 128000,
        "max_content_per_source": 4000,
        "max_results": 5,
        "total_web_budget": 15000,
    },
    # Tier 4: Huge context (> 128K tokens) - MiniMax, Gemini 1.5
    "huge": {
        "max_tokens": float('inf'),
        "max_content_per_source": 12000,
        "max_results": 10,
        "total_web_budget": 50000,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# SOURCE QUALITY SCORING SYSTEM
# Ranks search results by trustworthiness and relevance
# ═══════════════════════════════════════════════════════════════════════════════

# Authoritative domains get bonus points
AUTHORITATIVE_DOMAINS = {
    # Government
    '.gov': 25,
    '.mil': 20,
    # Education
    '.edu': 20,
    # Established organizations
    '.org': 10,
    # Major trusted sources
    'wikipedia.org': 15,
    'britannica.com': 15,
    'reuters.com': 15,
    'apnews.com': 15,
    'nature.com': 15,
    'sciencedirect.com': 15,
    'pubmed.ncbi.nlm.nih.gov': 20,
    'nih.gov': 20,
    'cdc.gov': 20,
    'who.int': 20,
    'mayoclinic.org': 15,
    'webmd.com': 10,
    'healthline.com': 10,
}

# Low-quality domains get penalized
LOW_QUALITY_DOMAINS = {
    'pinterest.com': -20,
    'quora.com': -10,
    'reddit.com': -5,  # Can be useful but often informal
    'medium.com': -5,   # User-generated, variable quality
    'blogspot.com': -15,
    'wordpress.com': -10,
    'tumblr.com': -20,
    'answers.yahoo.com': -25,
    'ehow.com': -20,
    'wikihow.com': -5,
    'about.com': -15,
    # SEO spam farms
    'articlesbase.com': -30,
    'ezinearticles.com': -30,
    'hubpages.com': -25,
}


def calculate_source_quality_score(result: Dict, query_keywords: List[str]) -> int:
    """
    Calculate a quality score for a search result (0-100).
    
    Factors:
    - Domain authority (+25 for .gov/.edu, +10 for .org)
    - Keyword match in title (+5 per keyword)
    - Snippet length (+15 for detailed snippets)
    - Freshness (+10 for recent dates)
    - Low-quality domain penalty (-30 for spam sites)
    
    Args:
        result: Search result dict with title, snippet, url
        query_keywords: Keywords from the original query
        
    Returns:
        Quality score 0-100
    """
    score = 50  # Base score
    url = result.get('url', '').lower()
    title = result.get('title', '').lower()
    snippet = result.get('snippet', '').lower()
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower().replace('www.', '')
        
        # Check authoritative domains
        for auth_domain, bonus in AUTHORITATIVE_DOMAINS.items():
            if auth_domain in domain or domain.endswith(auth_domain):
                score += bonus
                break
        
        # Check low-quality domains
        for bad_domain, penalty in LOW_QUALITY_DOMAINS.items():
            if bad_domain in domain:
                score += penalty  # penalty is negative
                break
        
        # Keyword matches in title (very important for relevance)
        for keyword in query_keywords:
            if len(keyword) > 3 and keyword.lower() in title:
                score += 5
        
        # Snippet quality
        snippet_len = len(snippet)
        if snippet_len > 200:
            score += 15
        elif snippet_len > 100:
            score += 10
        elif snippet_len > 50:
            score += 5
        elif snippet_len < 20:
            score -= 10  # Very short snippets are suspicious
        
        # Freshness indicators
        current_year = '2026'
        recent_years = ['2025', '2024', '2023']
        if current_year in snippet or current_year in title:
            score += 10
        elif any(year in snippet or year in title for year in recent_years):
            score += 5
        
        # HTTPS bonus
        if parsed.scheme == 'https':
            score += 3
        
    except Exception as e:
        logger.debug(f"Error scoring result: {e}")
    
    # Clamp to 0-100
    return max(0, min(100, score))


def deduplicate_results(results: List[Dict]) -> List[Dict]:
    """
    Remove duplicate and near-duplicate results.
    
    Checks:
    - Exact URL matches
    - Same title + similar domain (near-duplicate)
    - Very similar snippets (>80% overlap)
    
    Returns:
        Deduplicated list of results
    """
    seen_urls: Set[str] = set()
    seen_titles: Dict[str, str] = {}  # title -> domain
    unique_results = []
    
    for result in results:
        url = result.get('url', '')
        title = result.get('title', '').lower().strip()
        
        # Skip exact URL duplicates
        if url in seen_urls:
            continue
        
        # Check for near-duplicate (same title, different URL on same domain)
        if title and len(title) > 10:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower().replace('www.', '')
                base_domain = '.'.join(domain.split('.')[-2:]) if '.' in domain else domain
                
                if title in seen_titles:
                    existing_domain = seen_titles[title]
                    # If same base domain, skip (near-duplicate)
                    if base_domain == existing_domain:
                        logger.debug(f"Skipping near-duplicate: {title[:50]}...")
                        continue
                
                seen_titles[title] = base_domain
            except:
                pass
        
        seen_urls.add(url)
        unique_results.append(result)
    
    return unique_results


def sort_results_by_quality(results: List[Dict], query: str) -> List[Dict]:
    """
    Sort results by quality score (highest first).
    
    Args:
        results: List of search results
        query: Original search query
        
    Returns:
        Sorted list with quality_score added to each result
    """
    # Extract keywords from query
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
                  'of', 'with', 'is', 'are', 'was', 'were', 'be', 'been', 'being'}
    keywords = [w for w in re.findall(r'\b\w+\b', query.lower()) 
                if w not in stop_words and len(w) > 2]
    
    # Score each result
    for result in results:
        result['quality_score'] = calculate_source_quality_score(result, keywords)
    
    # Sort by score (descending)
    return sorted(results, key=lambda x: x.get('quality_score', 0), reverse=True)


class WebSearchProvider:
    """Configurable web search - self-hosted first, external APIs as fallback
    
    Features context-window awareness to automatically scale content fetching
    based on the active LLM provider's capabilities.
    """

    # External API endpoints (fallback only)
    EXTERNAL_PROVIDERS = {
        "serper": "https://google.serper.dev/search",
        "brave": "https://api.search.brave.com/res/v1/web/search",
        "tavily": "https://api.tavily.com/search",
    }

    # Domains to skip for content fetching (paywalls, login walls, etc)
    BLOCKED_DOMAINS = {
        "linkedin.com", "facebook.com", "twitter.com", "x.com",
        "instagram.com", "tiktok.com", "youtube.com",
    }

    # User agent for content fetching - use a real browser UA to avoid blocks
    # Many hospital/medical sites block bot user agents
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self):
        self.enabled = os.getenv("WEB_SEARCH_ENABLED", "false").lower() == "true"
        self.provider = os.getenv("WEB_SEARCH_PROVIDER", "searxng").lower()
        
        # Timeouts - allow more time for comprehensive research queries
        self.timeout = int(os.getenv("WEB_SEARCH_TIMEOUT", "10"))  # Per-request timeout
        self.total_timeout = int(os.getenv("WEB_SEARCH_TOTAL_TIMEOUT", "45"))  # Total operation timeout for multi-query searches
        
        # Content fetching settings (defaults - will be overridden by context-aware sizing)
        self.fetch_content = os.getenv("WEB_SEARCH_FETCH_CONTENT", "true").lower() == "true"
        
        # Default to conservative settings (medium tier)
        # These get updated dynamically based on LLM provider
        self._base_max_results = int(os.getenv("WEB_SEARCH_MAX_RESULTS", "10"))
        self._base_max_content = int(os.getenv("WEB_SEARCH_MAX_CONTENT_LENGTH", "4000"))
        self.max_results = self._base_max_results
        self.max_content_length = self._base_max_content
        
        # Cache for provider context window
        self._provider_max_tokens: Optional[int] = None
        self._current_tier: str = "medium"

        # SearXNG (self-hosted) configuration
        self.searxng_url = os.getenv("SEARXNG_URL", "http://searxng:8080")

        # External API key (only needed for external providers)
        self.api_key = os.getenv("WEB_SEARCH_API_KEY", "")

        if self.enabled:
            if self.provider == "searxng":
                logger.info(f"✅ Web search enabled (self-hosted SearXNG at {self.searxng_url})")
            elif self.api_key:
                logger.info(f"✅ Web search enabled (external: {self.provider})")
            else:
                logger.warning(f"⚠️ Web search enabled but {self.provider} requires API key")
                # Fall back to SearXNG if external provider has no key
                self.provider = "searxng"
                logger.info(f"↩️ Falling back to self-hosted SearXNG")

    def update_context_limits(self, provider_max_tokens: Optional[int] = None):
        """
        Update content limits based on the LLM provider's context window.
        
        This allows the search provider to automatically scale content fetching
        based on how much context the LLM can handle.
        
        Args:
            provider_max_tokens: The max tokens the LLM provider supports.
                                If None, tries to detect from ProviderRegistry.
        """
        if provider_max_tokens is None:
            # Try to get from provider registry
            try:
                from providers import ProviderRegistry
                registry = ProviderRegistry.get_instance()
                primary = registry.get_primary()
                if primary and primary.config:
                    provider_max_tokens = primary.config.max_tokens
                    logger.debug(f"Detected provider context window: {provider_max_tokens} tokens")
            except Exception as e:
                logger.debug(f"Could not detect provider context window: {e}")
        
        if provider_max_tokens is None:
            # Keep defaults
            return
        
        # Cache the detected value
        self._provider_max_tokens = provider_max_tokens
        
        # Determine tier based on max tokens
        if provider_max_tokens < 8000:
            tier = CONTEXT_TIERS["small"]
            self._current_tier = "small"
        elif provider_max_tokens < 32000:
            tier = CONTEXT_TIERS["medium"]
            self._current_tier = "medium"
        elif provider_max_tokens < 128000:
            tier = CONTEXT_TIERS["large"]
            self._current_tier = "large"
        else:
            tier = CONTEXT_TIERS["huge"]
            self._current_tier = "huge"
        
        # Update limits (but respect env var overrides if explicitly set)
        if os.getenv("WEB_SEARCH_MAX_RESULTS") is None:
            self.max_results = tier["max_results"]
        if os.getenv("WEB_SEARCH_MAX_CONTENT_LENGTH") is None:
            self.max_content_length = tier["max_content_per_source"]
        
        logger.info(f"📊 Web search context tier: {self._current_tier} "
                   f"(provider: {provider_max_tokens} tokens, "
                   f"max_results: {self.max_results}, "
                   f"content_per_source: {self.max_content_length} chars)")

    def get_context_budget(self) -> Dict[str, int]:
        """Get the current context budget settings."""
        tier = CONTEXT_TIERS.get(self._current_tier, CONTEXT_TIERS["medium"])
        return {
            "tier": self._current_tier,
            "provider_max_tokens": self._provider_max_tokens,
            "max_results": self.max_results,
            "max_content_per_source": self.max_content_length,
            "total_web_budget": tier["total_web_budget"],
        }

    def _sanitize_query(self, query: str) -> str:
        """Remove PII and sensitive data before sending to search"""
        # Remove email addresses
        sanitized = re.sub(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            '', query
        )
        # Remove IP addresses
        sanitized = re.sub(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', '', sanitized)
        # Remove API keys (common patterns)
        sanitized = re.sub(r'sk[-_][a-zA-Z0-9]{20,}', '', sanitized)
        sanitized = re.sub(r'api[-_]?key[-_:]?\s*[a-zA-Z0-9]{16,}', '', sanitized, flags=re.I)
        # Remove SSN patterns
        sanitized = re.sub(r'\b\d{3}[-.]?\d{2}[-.]?\d{4}\b', '', sanitized)
        # Remove credit card patterns
        sanitized = re.sub(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '', sanitized)
        # Clean up extra whitespace
        sanitized = ' '.join(sanitized.split())
        return sanitized

    async def search(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """
        Search the web and return relevant snippets.

        Args:
            query: Search query (will be sanitized)
            max_results: Override default max results

        Returns:
            List of dicts with keys: title, snippet, url, source
        """
        if not self.enabled:
            return []

        sanitized = self._sanitize_query(query)
        if len(sanitized.strip()) < 5:
            logger.warning("Query too short after sanitization, skipping web search")
            return []

        num_results = max_results or self.max_results

        try:
            # Primary: Self-hosted SearXNG
            if self.provider == "searxng":
                return await self._search_searxng(sanitized, num_results)

            # Fallback: External APIs (require API key)
            if not self.api_key:
                logger.warning(f"No API key for {self.provider}, trying SearXNG fallback")
                return await self._search_searxng(sanitized, num_results)

            if self.provider == "serper":
                return await self._search_serper(sanitized, num_results)
            elif self.provider == "brave":
                return await self._search_brave(sanitized, num_results)
            elif self.provider == "tavily":
                return await self._search_tavily(sanitized, num_results)
            else:
                logger.error(f"Unknown search provider: {self.provider}")
                return []
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            # Try SearXNG as final fallback
            if self.provider != "searxng":
                try:
                    logger.info("Attempting SearXNG fallback...")
                    return await self._search_searxng(sanitized, num_results)
                except Exception as fallback_err:
                    logger.error(f"SearXNG fallback also failed: {fallback_err}")
            return []

    async def _search_searxng(self, query: str, num_results: int) -> List[Dict]:
        """Self-hosted SearXNG meta-search (no API key required)"""
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "format": "json",
                "pageno": 1,
            }
            try:
                async with session.get(
                    f"{self.searxng_url}/search",
                    params=params,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        logger.warning(f"SearXNG returned {response.status}")
                        return []
                    data = await response.json()
                    results = data.get("results", [])
                    return [
                        {
                            "title": r.get("title", ""),
                            "snippet": r.get("content", "")[:500],
                            "url": r.get("url", ""),
                            "source": "searxng"
                        }
                        for r in results[:num_results]
                    ]
            except aiohttp.ClientConnectorError:
                logger.warning("SearXNG service not reachable")
                return []

    async def _search_serper(self, query: str, num_results: int) -> List[Dict]:
        """Serper.dev - Google search results (external, requires API key)"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.EXTERNAL_PROVIDERS["serper"],
                json={"q": query, "num": num_results},
                headers={"X-API-KEY": self.api_key, "Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"Serper returned {response.status}")
                    return []
                data = await response.json()
                return [
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("snippet", ""),
                        "url": r.get("link", ""),
                        "source": "serper"
                    }
                    for r in data.get("organic", [])[:num_results]
                ]

    async def _search_brave(self, query: str, num_results: int) -> List[Dict]:
        """Brave Search API (external, requires API key)"""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                self.EXTERNAL_PROVIDERS["brave"],
                params={"q": query, "count": num_results},
                headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"Brave returned {response.status}")
                    return []
                data = await response.json()
                results = data.get("web", {}).get("results", [])
                return [
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("description", ""),
                        "url": r.get("url", ""),
                        "source": "brave"
                    }
                    for r in results[:num_results]
                ]

    async def _search_tavily(self, query: str, num_results: int) -> List[Dict]:
        """Tavily API - AI-optimized search (external, requires API key)"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.EXTERNAL_PROVIDERS["tavily"],
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "max_results": num_results,
                    "search_depth": "basic"
                },
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            ) as response:
                if response.status != 200:
                    logger.warning(f"Tavily returned {response.status}")
                    return []
                data = await response.json()
                return [
                    {
                        "title": r.get("title", ""),
                        "snippet": r.get("content", "")[:500],
                        "url": r.get("url", ""),
                        "source": "tavily"
                    }
                    for r in data.get("results", [])[:num_results]
                ]

    async def fetch_url_content(self, url: str) -> Optional[Dict]:
        """
        Fetch and extract main content from a URL.
        
        Returns:
            Dict with keys: url, title, content, success, error
        """
        try:
            # Check for blocked domains
            parsed = urlparse(url)
            domain = parsed.netloc.lower().replace("www.", "")
            if any(blocked in domain for blocked in self.BLOCKED_DOMAINS):
                return {
                    "url": url,
                    "title": "",
                    "content": "",
                    "success": False,
                    "error": f"Domain {domain} is blocked (login/paywall)"
                }
            
            # Only fetch http/https
            if parsed.scheme not in ("http", "https"):
                return {
                    "url": url,
                    "title": "",
                    "content": "",
                    "success": False,
                    "error": "Only HTTP/HTTPS URLs supported"
                }
            
            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                    allow_redirects=True,
                    max_redirects=3
                ) as response:
                    if response.status != 200:
                        return {
                            "url": url,
                            "title": "",
                            "content": "",
                            "success": False,
                            "error": f"HTTP {response.status}"
                        }
                    
                    # Check content type
                    content_type = response.headers.get("Content-Type", "")
                    if "text/html" not in content_type and "application/xhtml" not in content_type:
                        return {
                            "url": url,
                            "title": "",
                            "content": "",
                            "success": False,
                            "error": f"Unsupported content type: {content_type}"
                        }
                    
                    html = await response.text()
                    return self._extract_content(url, html)
                    
        except aiohttp.ClientConnectorError:
            return {"url": url, "title": "", "content": "", "success": False, "error": "Connection failed"}
        except asyncio.TimeoutError:
            return {"url": url, "title": "", "content": "", "success": False, "error": "Timeout"}
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return {"url": url, "title": "", "content": "", "success": False, "error": str(e)}

    def _extract_content(self, url: str, html: str) -> Dict:
        """Extract main content from HTML using BeautifulSoup"""
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Get title
            title = ""
            if soup.title:
                title = soup.title.get_text(strip=True)
            
            # Remove unwanted elements
            for tag in soup.find_all(["script", "style", "nav", "header", "footer", 
                                       "aside", "form", "iframe", "noscript", "svg"]):
                tag.decompose()
            
            # Try to find main content area
            main_content = None
            
            # Look for semantic main content
            for selector in ["main", "article", '[role="main"]', ".content", ".post-content", 
                           ".article-content", ".entry-content", "#content", "#main"]:
                main_content = soup.select_one(selector)
                if main_content:
                    break
            
            # Fall back to body if no main content found
            if not main_content:
                main_content = soup.body if soup.body else soup
            
            # Extract text
            text = main_content.get_text(separator="\n", strip=True)
            
            # Clean up the text
            lines = []
            for line in text.split("\n"):
                line = line.strip()
                # Skip very short lines (likely navigation/buttons)
                if len(line) > 20:
                    lines.append(line)
            
            content = "\n".join(lines)
            
            # Truncate to max length
            if len(content) > self.max_content_length:
                content = content[:self.max_content_length] + "..."
            
            return {
                "url": url,
                "title": title,
                "content": content,
                "success": True,
                "error": None
            }
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {e}")
            return {
                "url": url,
                "title": "",
                "content": "",
                "success": False,
                "error": f"Parse error: {str(e)}"
            }

    async def search_and_fetch(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """
        Search and fetch full content from top results.
        
        This is the enhanced search that provides deep context for reports.
        Includes:
        - Total operation timeout to prevent UI blocking
        - Quality scoring and sorting
        - Duplicate detection
        - Smart query reformulation for poor results
        
        Returns:
            List of dicts with keys: title, snippet, url, source, full_content, quality_score
        """
        try:
            # Wrap entire operation in timeout to prevent UI blocking
            return await asyncio.wait_for(
                self._search_and_fetch_impl(query, max_results),
                timeout=self.total_timeout
            )
        except asyncio.TimeoutError:
            logger.warning(f"⚠️ Web search timed out after {self.total_timeout}s, returning partial results")
            # Try to return just search results without content fetching
            try:
                return await asyncio.wait_for(
                    self.search(query, max_results),
                    timeout=5
                )
            except:
                return []
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return []

    def _generate_reformulated_queries(self, original_query: str) -> List[str]:
        """
        Generate alternative query formulations for better results.
        
        Strategies:
        - Add context terms (official, 2024, 2025)
        - Try site-specific searches
        - Simplify overly complex queries
        - Add/remove quotes
        
        Returns:
            List of alternative queries to try
        """
        queries = []
        query_lower = original_query.lower()
        
        # Strategy 1: Add "official" for organization queries
        if not 'official' in query_lower:
            queries.append(f'{original_query} official')
        
        # Strategy 2: Add current year context
        if '2025' not in original_query and '2026' not in original_query:
            queries.append(f'{original_query} 2025')
        
        # Strategy 3: Try site-specific for certain query types
        org_indicators = ['hospital', 'university', 'college', 'company', 'organization', 
                         'foundation', 'institute', 'center', 'clinic']
        if any(ind in query_lower for ind in org_indicators):
            # Try to extract organization name and do site search
            # Look for quoted phrases first
            quoted = re.findall(r'"([^"]+)"', original_query)
            if quoted:
                org_name = quoted[0].lower().replace(' ', '')
                queries.append(f'site:{org_name}.com')
                queries.append(f'site:{org_name}.org')
        
        # Strategy 4: Simplify complex queries
        words = original_query.split()
        if len(words) > 8:
            # Take first 5-6 significant words
            simplified = ' '.join(words[:6])
            queries.append(simplified)
        
        # Strategy 5: Remove quotes if present, add if not
        if '"' in original_query:
            queries.append(original_query.replace('"', ''))
        else:
            # Try quoting the first capitalized phrase
            cap_phrases = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b', original_query)
            if cap_phrases:
                quoted_query = original_query.replace(cap_phrases[0], f'"{cap_phrases[0]}"')
                queries.append(quoted_query)
        
        return queries[:3]  # Return max 3 reformulations

    def _assess_result_quality(self, results: List[Dict]) -> Tuple[bool, str]:
        """
        Assess if search results are good enough or need reformulation.
        
        Returns:
            Tuple of (is_good_enough, reason)
        """
        if not results:
            return False, "no_results"
        
        if len(results) < 2:
            return False, "too_few_results"
        
        # Check average snippet length
        avg_snippet_len = sum(len(r.get('snippet', '')) for r in results) / len(results)
        if avg_snippet_len < 50:
            return False, "short_snippets"
        
        # Check if any high-quality results
        has_quality = False
        for r in results:
            url = r.get('url', '').lower()
            for auth in AUTHORITATIVE_DOMAINS:
                if auth in url:
                    has_quality = True
                    break
            if has_quality:
                break
        
        # If no authoritative sources and few results, try reformulation
        if not has_quality and len(results) < 4:
            return False, "no_authoritative_sources"
        
        return True, "acceptable"

    async def _search_and_fetch_impl(self, query: str, max_results: Optional[int] = None) -> List[Dict]:
        """Internal implementation of search_and_fetch with smart enhancements"""
        
        all_results = []
        seen_urls: Set[str] = set()
        
        # First attempt with original query
        results = await self.search(query, max_results)
        all_results.extend(results)
        seen_urls.update(r.get('url', '') for r in results)
        
        # Assess result quality
        is_good, reason = self._assess_result_quality(results)
        
        # If results are poor, try reformulated queries
        if not is_good:
            logger.info(f"📊 Initial search quality: {reason}, trying reformulations...")
            reformulated = self._generate_reformulated_queries(query)
            
            for alt_query in reformulated:
                if len(all_results) >= 8:  # Stop if we have enough
                    break
                    
                logger.info(f"🔄 Trying reformulated query: '{alt_query}'")
                try:
                    alt_results = await self.search(alt_query, max_results)
                    for r in alt_results:
                        url = r.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)
                except Exception as e:
                    logger.warning(f"Reformulated query failed: {e}")
        
        if not all_results:
            return []
        
        # Deduplicate results
        all_results = deduplicate_results(all_results)
        
        # Sort by quality score
        all_results = sort_results_by_quality(all_results, query)
        
        # Take top results based on max_results
        num_results = max_results or self.max_results
        all_results = all_results[:num_results]
        
        logger.info(f"📊 Final results: {len(all_results)} (scores: {[r.get('quality_score', 0) for r in all_results]})")
        
        # Fetch content if enabled
        if not self.fetch_content:
            return all_results
        
        # Fetch content for each result (with individual timeouts)
        fetch_tasks = [self.fetch_url_content(r["url"]) for r in all_results]
        fetched = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        # Merge fetched content into results
        for i, result in enumerate(all_results):
            if i < len(fetched) and isinstance(fetched[i], dict):
                fetch_result = fetched[i]
                if fetch_result.get("success"):
                    result["full_content"] = fetch_result.get("content", "")
                    # Update title if we got a better one
                    if fetch_result.get("title") and not result.get("title"):
                        result["title"] = fetch_result["title"]
                    logger.info(f"📄 Fetched {len(result.get('full_content', ''))} chars from {result['url']}")
                else:
                    result["full_content"] = ""
                    result["fetch_error"] = fetch_result.get("error", "Unknown error")
                    logger.warning(f"⚠️ Could not fetch {result['url']}: {result['fetch_error']}")
            else:
                result["full_content"] = ""
        
        return all_results

    async def health_check(self) -> Dict:
        """Check if search service is available"""
        if not self.enabled:
            return {"status": "disabled", "provider": None}

        try:
            if self.provider == "searxng":
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        f"{self.searxng_url}/healthz",
                        timeout=aiohttp.ClientTimeout(total=5)
                    ) as response:
                        if response.status == 200:
                            return {"status": "healthy", "provider": "searxng", "self_hosted": True}
                        return {"status": "unhealthy", "provider": "searxng", "error": f"HTTP {response.status}"}
            else:
                # External providers - just check if configured
                if self.api_key:
                    return {"status": "configured", "provider": self.provider, "self_hosted": False}
                return {"status": "unconfigured", "provider": self.provider, "error": "No API key"}
        except Exception as e:
            return {"status": "error", "provider": self.provider, "error": str(e)}

    def get_status(self) -> Dict:
        """Return provider status for admin dashboard"""
        budget = self.get_context_budget()
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "self_hosted": self.provider == "searxng",
            "searxng_url": self.searxng_url if self.provider == "searxng" else None,
            "external_configured": bool(self.api_key) if self.provider != "searxng" else None,
            "fetch_content": self.fetch_content,
            "context_tier": budget["tier"],
            "max_results": budget["max_results"],
            "max_content_per_source": budget["max_content_per_source"],
            "total_web_budget": budget["total_web_budget"],
            "provider_max_tokens": budget["provider_max_tokens"],
        }


# Singleton instance
_web_search_provider: Optional[WebSearchProvider] = None


def get_web_search_provider() -> WebSearchProvider:
    """Get or create the web search provider singleton"""
    global _web_search_provider
    if _web_search_provider is None:
        _web_search_provider = WebSearchProvider()
    return _web_search_provider
