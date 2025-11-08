"""
Request Classification Service
Determines if a user request should be handled as:
- "chat": Quick inline response in chat
- "report": Queued background processing with report generation
"""

import re
from typing import Tuple, Dict


def estimate_tokens(text: str) -> int:
    """
    Rough token estimation (4 chars per token average)
    For production, use tiktoken for accurate counting
    """
    return len(text) // 4


def extract_word_count_request(user_request: str) -> int:
    """
    Extract explicit word count from requests like:
    - "write 1000 words about..."
    - "give me a 500 word essay..."
    - "2000-word document on..."
    """
    patterns = [
        r'(\d+)[\s-]*words?',           # "1000 words" or "1000-word"
        r'(\d+)\s*word',                 # "500 word essay"
        r'(\d{3,5})\s*w\b',              # "2000w" shorthand
    ]

    for pattern in patterns:
        match = re.search(pattern, user_request.lower())
        if match:
            return int(match.group(1))

    return 0


def classify_request(prompt: str, user_request: str, max_chat_tokens: int = 2000) -> Tuple[str, Dict]:
    """
    Classify user request as 'chat' or 'report' based on expected complexity

    Args:
        prompt: The full prompt being sent to LLM
        user_request: The user's original message
        max_chat_tokens: Maximum tokens for inline chat response

    Returns:
        Tuple of (classification, metadata)
        - classification: "chat" or "report"
        - metadata: Dict with reasoning and estimates
    """

    # Estimate prompt tokens
    prompt_tokens = estimate_tokens(prompt)
    user_request_lower = user_request.lower()

    # Default response estimate
    response_estimate = 500
    reasoning = []

    # ========================================
    # 1. EXPLICIT WORD COUNT REQUESTS
    # ========================================
    word_count = extract_word_count_request(user_request)
    if word_count > 0:
        # Rough conversion: 1 word ≈ 1.3 tokens (English average)
        response_estimate = int(word_count * 1.3)
        reasoning.append(f"Explicit word count: {word_count} words (~{response_estimate} tokens)")

    # ========================================
    # 2. LENGTH INDICATORS
    # ========================================
    length_indicators = {
        # Term: (token_estimate, description)
        'detailed': (1500, "detailed analysis"),
        'comprehensive': (2000, "comprehensive coverage"),
        'in-depth': (1800, "in-depth explanation"),
        'thorough': (1500, "thorough examination"),
        'extensive': (2000, "extensive content"),
        'elaborate': (1500, "elaborate response"),
        'complete': (1500, "complete information"),
        'full': (1200, "full details"),
        'long': (1000, "long-form content"),
    }

    for term, (tokens, desc) in length_indicators.items():
        if term in user_request_lower:
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Length indicator: '{term}' ({desc})")

    # ========================================
    # 3. FORMAT INDICATORS
    # ========================================
    format_indicators = {
        'essay': (2000, "essay format"),
        'report': (2500, "report format"),
        'document': (2000, "document format"),
        'article': (1800, "article format"),
        'white paper': (3000, "white paper format"),
        'research paper': (3500, "research paper format"),
        'guide': (2000, "guide format"),
        'tutorial': (2500, "tutorial format"),
        'walkthrough': (2000, "walkthrough format"),
        'documentation': (2500, "documentation format"),
        'memo': (1000, "memo format"),
        'proposal': (2000, "proposal format"),
        'analysis': (1800, "analysis format"),
        'review': (1500, "review format"),
        'summary': (1200, "summary format"),
        'overview': (1200, "overview format"),
        'breakdown': (1500, "breakdown format"),
    }

    for term, (tokens, desc) in format_indicators.items():
        if term in user_request_lower:
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Format indicator: '{term}' ({desc})")

    # ========================================
    # 4. SCOPE INDICATORS
    # ========================================
    scope_patterns = [
        (r'everything about', 2500, "comprehensive scope"),
        (r'all aspects? (of|about)', 2000, "all aspects requested"),
        (r'complete (guide|overview|breakdown|list)', 2000, "complete coverage"),
        (r'every(thing)? (about|on|related to)', 2500, "everything requested"),
        (r'full (breakdown|analysis|explanation|guide)', 2000, "full treatment"),
        (r'cover (all|everything)', 2000, "cover everything"),
        (r'tell me all about', 2000, "comprehensive request"),
    ]

    for pattern, tokens, desc in scope_patterns:
        if re.search(pattern, user_request_lower):
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Scope indicator: {desc}")

    # ========================================
    # 5. LIST/ENUMERATION INDICATORS
    # ========================================
    list_patterns = [
        (r'list (?:of )?(\d+)', lambda m: int(m.group(1)) * 150, "numbered list"),
        (r'top (\d+)', lambda m: int(m.group(1)) * 150, "top N list"),
        (r'(\d+) (examples?|reasons?|ways?|methods?|steps?)', lambda m: int(m.group(1)) * 120, "enumerated items"),
        (r'multiple (examples?|cases?|scenarios?)', lambda m: 1500, "multiple items"),
        (r'several (examples?|cases?|scenarios?)', lambda m: 1200, "several items"),
        (r'various (examples?|cases?|scenarios?)', lambda m: 1200, "various items"),
        (r'many (examples?|cases?|scenarios?)', lambda m: 1500, "many items"),
    ]

    for pattern, estimator, desc in list_patterns:
        match = re.search(pattern, user_request_lower)
        if match:
            tokens = estimator(match) if callable(estimator) else estimator
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"List indicator: {desc}")

    # ========================================
    # 6. COMPARISON INDICATORS
    # ========================================
    comparison_indicators = {
        'compare': (1800, "comparison requested"),
        'contrast': (1800, "contrast requested"),
        'pros and cons': (1500, "pros/cons analysis"),
        'advantages and disadvantages': (1800, "advantages/disadvantages"),
        'versus': (1500, "versus comparison"),
        'vs.': (1500, "vs comparison"),
        'vs ': (1500, "vs comparison"),
        'differences between': (1500, "differences analysis"),
        'similarities and differences': (1800, "similarities/differences"),
    }

    for term, (tokens, desc) in comparison_indicators.items():
        if term in user_request_lower:
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Comparison indicator: '{term}' ({desc})")

    # ========================================
    # 7. RESEARCH/DEEP DIVE INDICATORS
    # ========================================
    research_indicators = {
        'research': (2000, "research requested"),
        'investigate': (1800, "investigation requested"),
        'explore': (1500, "exploration requested"),
        'deep dive': (2500, "deep dive requested"),
        'examine': (1500, "examination requested"),
        'analyze': (1800, "analysis requested"),
        'study': (1500, "study requested"),
        'evaluate': (1500, "evaluation requested"),
        'assess': (1500, "assessment requested"),
    }

    for term, (tokens, desc) in research_indicators.items():
        if term in user_request_lower:
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Research indicator: '{term}' ({desc})")

    # ========================================
    # 8. STEP-BY-STEP/PROCEDURAL INDICATORS
    # ========================================
    procedural_patterns = [
        (r'step[- ]by[- ]step', 2000, "step-by-step guide"),
        (r'how[- ]to (guide|tutorial)', 2000, "how-to guide"),
        (r'walk me through', 1800, "walkthrough requested"),
        (r'explain (the process|how to)', 1500, "process explanation"),
        (r'show me how', 1500, "demonstration requested"),
    ]

    for pattern, tokens, desc in procedural_patterns:
        if re.search(pattern, user_request_lower):
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Procedural indicator: {desc}")

    # ========================================
    # 9. MULTI-PART/SECTIONED REQUESTS
    # ========================================
    section_patterns = [
        (r'include (sections?|parts?|chapters?)', 2000, "sectioned content"),
        (r'with (sections?|parts?|chapters?)', 2000, "sectioned content"),
        (r'(broken|split) (down|into) (sections?|parts?)', 2000, "sectioned breakdown"),
        (r'(\d+)[- ](part|section|chapter)', lambda m: int(m.group(1)) * 500, "multi-part content"),
    ]

    for pattern, estimator, desc in section_patterns:
        match = re.search(pattern, user_request_lower)
        if match:
            tokens = estimator(match) if callable(estimator) else estimator
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Section indicator: {desc}")

    # ========================================
    # 10. USE CASE / EXAMPLE REQUESTS
    # ========================================
    use_case_patterns = [
        (r'use cases?', 1500, "use cases requested"),
        (r'real[- ]world examples?', 1500, "real-world examples"),
        (r'practical examples?', 1500, "practical examples"),
        (r'case studies', 2000, "case studies requested"),
        (r'scenarios?', 1200, "scenarios requested"),
        (r'applications?', 1200, "applications requested"),
    ]

    for pattern, tokens, desc in use_case_patterns:
        if re.search(pattern, user_request_lower):
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Use case indicator: {desc}")

    # ========================================
    # 11. TECHNICAL DOCUMENTATION INDICATORS
    # ========================================
    technical_indicators = {
        'specification': (2500, "specification document"),
        'architecture': (2000, "architecture documentation"),
        'design document': (2500, "design document"),
        'technical documentation': (2500, "technical docs"),
        'api documentation': (2000, "API documentation"),
        'implementation guide': (2000, "implementation guide"),
        'best practices': (1800, "best practices guide"),
        'guidelines': (1500, "guidelines document"),
    }

    for term, (tokens, desc) in technical_indicators.items():
        if term in user_request_lower:
            response_estimate = max(response_estimate, tokens)
            reasoning.append(f"Technical indicator: '{term}' ({desc})")

    # ========================================
    # CLASSIFICATION DECISION
    # ========================================
    total_tokens = prompt_tokens + response_estimate

    # Determine classification
    if total_tokens > max_chat_tokens:
        classification = "report"
    else:
        classification = "chat"

    # Build metadata
    metadata = {
        'prompt_tokens': prompt_tokens,
        'estimated_response_tokens': response_estimate,
        'total_estimated_tokens': total_tokens,
        'threshold': max_chat_tokens,
        'reasoning': reasoning,
        'word_count_requested': word_count if word_count > 0 else None,
    }

    return classification, metadata


def format_classification_message(classification: str, metadata: Dict) -> str:
    """
    Generate user-friendly message explaining the classification
    """
    if classification == "report":
        message = f"""I'll generate that as a report for you. This request will be queued for processing.

📊 Request Analysis:
• Estimated length: ~{metadata['estimated_response_tokens']} tokens
• Classification: Report (complex/long-form content)
"""
        if metadata['reasoning']:
            message += f"• Detected: {', '.join(metadata['reasoning'][:3])}\n"

        message += "\n✅ Your report will appear in the Reports section shortly and I'll notify you when it's ready."

    else:
        message = f"""Processing your request now...

📊 Request Analysis:
• Estimated length: ~{metadata['estimated_response_tokens']} tokens
• Classification: Chat (quick response)
"""

    return message
