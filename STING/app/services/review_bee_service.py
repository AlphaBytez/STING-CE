"""
ReviewBee (RBee) Service for STING-CE
Enterprise-grade report review and editing agent with PII-aware processing.

ReviewBee uses a Critic-Revise architecture:
1. A lightweight local model (critic) reviews the generated report
2. The critic identifies issues and generates structured feedback
3. The feedback is appended to the original request
4. The powerful LLM regenerates an improved version

This approach leverages each model's strengths:
- Lightweight model: Fast analysis, issue detection (what it's good at)
- Powerful model: High-quality generation (what it's good at)

Features:
- Critic-based review (not direct editing)
- PII-aware context (can see serialized data for intelligent critique)
- Configurable critique criteria (accuracy, tone, completeness, etc.)
- Iterative refinement with configurable max iterations
- Audit trail of all critiques and revisions
"""

import os
import logging
import asyncio
import json
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field
from enum import Enum
import uuid
import aiohttp

logger = logging.getLogger(__name__)


class ReviewBeeMode(Enum):
    """ReviewBee operation modes"""
    CRITIQUE_ONLY = "critique_only"  # Only generate critique, don't revise
    AUTO_REVISE = "auto_revise"      # Automatically revise if issues found
    THRESHOLD = "threshold"          # Only revise if score below threshold


class CritiqueCategory(Enum):
    """Categories of critique feedback"""
    ACCURACY = "accuracy"
    CLARITY = "clarity"
    COMPLETENESS = "completeness"
    TONE = "tone"
    STRUCTURE = "structure"
    PII_CONCERN = "pii_concern"
    FACTUAL = "factual"
    GRAMMAR = "grammar"
    REQUIREMENTS = "requirements"


@dataclass
class CritiqueFinding:
    """A single finding from the critic model"""
    id: str
    category: CritiqueCategory
    severity: str  # 'minor', 'moderate', 'major'
    description: str
    suggestion: str
    location_hint: Optional[str] = None  # Where in the doc (e.g., "in the executive summary")
    confidence: float = 0.8
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'category': self.category.value,
            'severity': self.severity,
            'description': self.description,
            'suggestion': self.suggestion,
            'location_hint': self.location_hint,
            'confidence': self.confidence
        }
    
    def to_feedback_string(self) -> str:
        """Convert to a string for appending to revision prompt"""
        location = f" ({self.location_hint})" if self.location_hint else ""
        return f"- [{self.category.value.upper()}]{location}: {self.description}. Suggestion: {self.suggestion}"


@dataclass
class CritiqueResult:
    """Result from the critic model"""
    overall_score: float  # 0-1
    category_scores: Dict[str, float]
    findings: List[CritiqueFinding]
    summary: str
    needs_revision: bool
    critic_model: str
    critique_time_seconds: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'overall_score': self.overall_score,
            'category_scores': self.category_scores,
            'findings': [f.to_dict() for f in self.findings],
            'findings_count': len(self.findings),
            'summary': self.summary,
            'needs_revision': self.needs_revision,
            'critic_model': self.critic_model,
            'critique_time_seconds': round(self.critique_time_seconds, 2)
        }
    
    def generate_revision_feedback(self) -> str:
        """Generate the feedback string to append to revision request"""
        if not self.findings:
            return ""
        
        feedback_lines = [
            "\n\n---",
            "REVISION REQUEST FROM REVIEW AGENT:",
            f"Overall Quality Score: {self.overall_score:.0%}",
            "",
            "Issues identified that need to be addressed:",
        ]
        
        # Group by severity
        major = [f for f in self.findings if f.severity == 'major']
        moderate = [f for f in self.findings if f.severity == 'moderate']
        minor = [f for f in self.findings if f.severity == 'minor']
        
        if major:
            feedback_lines.append("\nMAJOR ISSUES (must fix):")
            for finding in major:
                feedback_lines.append(finding.to_feedback_string())
        
        if moderate:
            feedback_lines.append("\nMODERATE ISSUES (should fix):")
            for finding in moderate:
                feedback_lines.append(finding.to_feedback_string())
        
        if minor:
            feedback_lines.append("\nMINOR ISSUES (consider fixing):")
            for finding in minor:
                feedback_lines.append(finding.to_feedback_string())
        
        feedback_lines.extend([
            "",
            "Please regenerate the report addressing the above feedback.",
            "Maintain the same overall structure and intent, but improve quality.",
            "",
            "CRITICAL: Output ONLY the revised report content. Do NOT include any meta-commentary about what you changed, acknowledgment of this feedback, or explanations of your revisions. The output must be a clean, polished report ready for readers.",
            "---"
        ])
        
        return "\n".join(feedback_lines)


@dataclass 
class ReviewBeeResult:
    """Result of a complete ReviewBee review cycle"""
    report_id: str
    review_id: str
    original_content: str
    final_content: str
    critique: CritiqueResult
    revision_performed: bool
    revision_prompt_used: Optional[str]
    total_iterations: int
    total_time_seconds: float
    generator_model: str  # The powerful model used for revision
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'report_id': self.report_id,
            'review_id': self.review_id,
            'critique': self.critique.to_dict(),
            'revision_performed': self.revision_performed,
            'total_iterations': self.total_iterations,
            'total_time_seconds': round(self.total_time_seconds, 2),
            'generator_model': self.generator_model,
            'content_changed': self.original_content != self.final_content,
            'improvement_score': self.critique.overall_score
        }


@dataclass
class ReviewBeeConfig:
    """Configuration for ReviewBee service"""
    # Feature toggle
    enabled: bool = False
    
    # Critic model (lightweight, local)
    critic_model: str = "phi4"  # Fast, good at analysis
    critic_fallback_model: str = "qwen2.5-7b-instruct"
    
    # Generator model (powerful, for revision) - uses same as report generation
    # This is looked up from the LLM service, not configured here
    
    # LLM service URL
    llm_service_url: str = "http://external-ai:8091"
    
    # Review behavior
    mode: ReviewBeeMode = ReviewBeeMode.THRESHOLD
    revision_threshold: float = 0.75  # Only revise if score below this
    max_iterations: int = 2  # Allow iterative refinement for complex reports
    critique_timeout_seconds: int = 30
    revision_timeout_seconds: int = 120
    
    # Critique settings
    enabled_categories: List[CritiqueCategory] = field(default_factory=lambda: [
        CritiqueCategory.ACCURACY,
        CritiqueCategory.CLARITY,
        CritiqueCategory.COMPLETENESS,
        CritiqueCategory.TONE,
        CritiqueCategory.STRUCTURE,
        CritiqueCategory.GRAMMAR
    ])
    
    # Category weights for overall score
    category_weights: Dict[str, float] = field(default_factory=lambda: {
        'clarity': 0.25,
        'completeness': 0.25,
        'accuracy': 0.20,
        'tone': 0.15,
        'structure': 0.15
    })
    
    # PII context settings
    include_pii_context: bool = True
    
    @classmethod
    def from_dict(cls, config: Dict[str, Any]) -> 'ReviewBeeConfig':
        """Create config from dictionary (e.g., from config.yml)"""
        mode_str = config.get('mode', 'threshold')
        mode = ReviewBeeMode(mode_str) if mode_str in [m.value for m in ReviewBeeMode] else ReviewBeeMode.THRESHOLD
        
        categories = []
        for cat in config.get('enabled_categories', []):
            try:
                categories.append(CritiqueCategory(cat))
            except ValueError:
                logger.warning(f"Unknown critique category: {cat}")
        
        return cls(
            enabled=config.get('enabled', False),
            critic_model=config.get('critic_model', 'phi4'),
            critic_fallback_model=config.get('critic_fallback_model', 'qwen2.5-7b-instruct'),
            llm_service_url=config.get('llm_service_url', 'http://external-ai:8091'),
            mode=mode,
            revision_threshold=config.get('revision_threshold', 0.75),
            max_iterations=config.get('max_iterations', 1),
            critique_timeout_seconds=config.get('critique_timeout_seconds', 30),
            revision_timeout_seconds=config.get('revision_timeout_seconds', 120),
            enabled_categories=categories if categories else [
                CritiqueCategory.ACCURACY, CritiqueCategory.CLARITY,
                CritiqueCategory.COMPLETENESS, CritiqueCategory.TONE,
                CritiqueCategory.STRUCTURE, CritiqueCategory.GRAMMAR
            ],
            category_weights=config.get('category_weights', {
                'clarity': 0.25, 'completeness': 0.25, 'accuracy': 0.20,
                'tone': 0.15, 'structure': 0.15
            }),
            include_pii_context=config.get('include_pii_context', True)
        )


class ReviewBeeService:
    """
    ReviewBee - Enterprise Report Review using Critic-Revise Architecture
    
    Flow:
    1. Lightweight critic model reviews content (fast)
    2. Generates structured feedback with specific suggestions
    3. If revision needed, feedback is appended to original prompt
    4. Powerful LLM regenerates with feedback context
    """
    
    def __init__(self, config: Optional[ReviewBeeConfig] = None):
        self.config = config or self._load_config_from_env()
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"🐝 ReviewBee Service initialized (Critic-Revise Architecture)")
        logger.info(f"   Enabled: {self.config.enabled}")
        logger.info(f"   Critic model: {self.config.critic_model}")
        logger.info(f"   Mode: {self.config.mode.value}")
        logger.info(f"   Revision threshold: {self.config.revision_threshold}")
    
    def _load_config_from_env(self) -> ReviewBeeConfig:
        """Load configuration from environment variables"""
        return ReviewBeeConfig(
            enabled=os.environ.get('REVIEW_BEE_ENABLED', 'false').lower() == 'true',
            critic_model=os.environ.get('REVIEW_BEE_CRITIC_MODEL', 'phi4'),
            critic_fallback_model=os.environ.get('REVIEW_BEE_CRITIC_FALLBACK', 'qwen2.5-7b-instruct'),
            llm_service_url=os.environ.get('LLM_SERVICE_URL', 'http://external-ai:8091'),
            mode=ReviewBeeMode(os.environ.get('REVIEW_BEE_MODE', 'threshold')),
            revision_threshold=float(os.environ.get('REVIEW_BEE_THRESHOLD', '0.75')),
            max_iterations=int(os.environ.get('REVIEW_BEE_MAX_ITERATIONS', '2')),
            include_pii_context=os.environ.get('REVIEW_BEE_PII_CONTEXT', 'true').lower() == 'true'
        )
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def is_enabled(self) -> bool:
        """Check if ReviewBee is enabled"""
        return self.config.enabled
    
    async def review_and_revise(
        self,
        report_id: str,
        content: str,
        original_prompt: str,
        pii_context: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        generator_model: Optional[str] = None,
        web_sources: Optional[List[Dict[str, Any]]] = None
    ) -> ReviewBeeResult:
        """
        Review content and optionally revise using Critic-Revise pattern.
        
        Args:
            report_id: ID of the report being reviewed
            content: The generated report content to review
            original_prompt: The original prompt used to generate the report
            pii_context: PII serialization context (for critic awareness)
            user_id: ID of the report owner
            generator_model: Model to use for revision (defaults to report model)
            web_sources: Optional web sources used in generation for fact-checking
            
        Returns:
            ReviewBeeResult with critique and optionally revised content
        """
        review_id = f"rbee-{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        
        logger.info(f"🐝 ReviewBee starting review {review_id} for report {report_id[:8]}...")
        
        if not self.config.enabled:
            logger.debug("ReviewBee is disabled")
            empty_critique = CritiqueResult(
                overall_score=1.0,
                category_scores={},
                findings=[],
                summary="ReviewBee disabled",
                needs_revision=False,
                critic_model="none",
                critique_time_seconds=0
            )
            return ReviewBeeResult(
                report_id=report_id,
                review_id=review_id,
                original_content=content,
                final_content=content,
                critique=empty_critique,
                revision_performed=False,
                revision_prompt_used=None,
                total_iterations=0,
                total_time_seconds=0,
                generator_model="none"
            )
        
        # Multi-pass revision loop
        current_content = content
        previous_score = 0.0
        last_critique = None
        last_revision_prompt = None
        iterations = 0
        
        for iteration in range(self.config.max_iterations):
            iterations = iteration + 1
            
            # Step 1: Run critic model to get feedback
            logger.info(f"🔍 Running critic model ({self.config.critic_model}), iteration {iteration+1}/{self.config.max_iterations}...")
            critique = await self._run_critic(current_content, pii_context, original_prompt=original_prompt, web_sources=web_sources)
            
            # Step 1b: Check extracted requirements and add findings for unmet ones
            requirements = self._extract_requirements(original_prompt)
            if requirements:
                req_findings = self._check_requirements(current_content, requirements)
                if req_findings:
                    critique.findings.extend(req_findings)
                    # Recalculate needs_revision with new findings
                    major_count = len([f for f in critique.findings if f.severity == 'major'])
                    critique.needs_revision = critique.overall_score < self.config.revision_threshold or major_count > 0
            
            last_critique = critique
            
            logger.info(f"📊 Critique complete (iteration {iteration+1}): score={critique.overall_score:.0%}, "
                       f"findings={len(critique.findings)}, needs_revision={critique.needs_revision}")
            
            # Step 2: Determine if revision is needed
            if not self._should_revise(critique):
                break
            
            # Convergence detection: stop if improvement is marginal
            if iteration > 0:
                improvement = critique.overall_score - previous_score
                if improvement < 0.05:
                    logger.info(f"🐝 Converged after {iteration+1} iterations (improvement: {improvement:.2%})")
                    break
            
            previous_score = critique.overall_score
            
            if not original_prompt:
                break
            
            # Step 3: Generate revision by appending feedback to original prompt
            logger.info(f"🔄 Revision needed, generating improved version (iteration {iteration+1})...")
            
            revision_feedback = critique.generate_revision_feedback()
            revision_prompt = original_prompt + revision_feedback
            last_revision_prompt = revision_prompt
            
            # Call the powerful LLM with the augmented prompt
            revised_content = await self._generate_revision(
                revision_prompt,
                generator_model,
                user_id
            )
            
            if revised_content:
                current_content = revised_content
                logger.info(f"✅ Revision complete (iteration {iteration+1})")
            else:
                logger.warning(f"⚠️ Revision failed at iteration {iteration+1}, keeping current content")
                break
        
        total_time = time.time() - start_time
        
        logger.info(f"🐝 ReviewBee complete: score={last_critique.overall_score:.0%}, "
                   f"revised={current_content != content}, iterations={iterations}, time={total_time:.2f}s")
        
        return ReviewBeeResult(
            report_id=report_id,
            review_id=review_id,
            original_content=content,
            final_content=current_content,
            critique=last_critique,
            revision_performed=current_content != content,
            revision_prompt_used=last_revision_prompt if current_content != content else None,
            total_iterations=iterations,
            total_time_seconds=total_time,
            generator_model=generator_model or "default"
        )
    
    def _should_revise(self, critique: CritiqueResult) -> bool:
        """Determine if revision should be performed based on mode and critique"""
        if self.config.mode == ReviewBeeMode.CRITIQUE_ONLY:
            return False
        elif self.config.mode == ReviewBeeMode.AUTO_REVISE:
            return critique.needs_revision
        elif self.config.mode == ReviewBeeMode.THRESHOLD:
            return critique.overall_score < self.config.revision_threshold
        return False
    
    async def _run_critic(
        self,
        content: str,
        pii_context: Optional[Dict[str, Any]],
        original_prompt: Optional[str] = None,
        web_sources: Optional[List[Dict[str, Any]]] = None
    ) -> CritiqueResult:
        """Run the lightweight critic model to analyze content"""
        start_time = time.time()
        
        # Programmatic checks before LLM critic
        programmatic_findings: List[CritiqueFinding] = []
        
        # Content length validation (Fix 3)
        if original_prompt:
            content_words = len(content.split())
            target_words = self._extract_target_word_count(original_prompt)
            
            if target_words and content_words < target_words * 0.8:
                programmatic_findings.append(CritiqueFinding(
                    id="length-check",
                    category=CritiqueCategory.COMPLETENESS,
                    severity="major",
                    description=f"Report is {content_words} words but user requested {target_words}+ words",
                    suggestion=f"Expand the report significantly to reach at least {target_words} words with more detailed analysis, examples, and evidence."
                ))
        
        # Build critic prompt
        pii_note = ""
        if pii_context and self.config.include_pii_context:
            pii_count = pii_context.get('pii_count', 0)
            if pii_count > 0:
                pii_note = f"""
Note: This content has PII protection enabled. {pii_count} PII items were serialized.
You may see [PII_*] tokens - these are INTENTIONAL and should NOT be flagged as errors.
"""
        
        enabled_cats = ', '.join(cat.value for cat in self.config.enabled_categories)
        
        # Truncate for critic (it just needs to assess, not process everything)
        review_content = content[:6000] if len(content) > 6000 else content
        truncated = len(content) > 6000
        
        # Requirements validation section (Fix 1)
        requirements_section = ""
        if original_prompt:
            requirements = self._extract_requirements(original_prompt)
            if requirements:
                req_lines = ["REQUIREMENTS VALIDATION:"]
                req_lines.append("The user's original request included these specific requirements. Evaluate whether they were met:")
                for req_type, req_items in requirements.items():
                    if req_items:
                        req_lines.append(f"  - {req_type}: {', '.join(str(r) for r in req_items)}")
                req_lines.append("Flag any unmet requirements as 'requirements' category findings with severity 'major'.")
                req_lines.append("")
                requirements_section = "\n".join(req_lines)
        
        # Fact-check section (Fix 4)
        fact_check_section = ""
        if web_sources:
            source_lines = ["\nWEB SOURCES USED IN GENERATION:"]
            for i, src in enumerate(web_sources[:5], 1):
                title = src.get('title', 'Unknown')
                snippet = src.get('snippet', '')[:200]
                source_lines.append(f"\n[{i}] {title}: {snippet}")
            source_lines.append("\nFACT-CHECK TASK: Verify claims in the report against these sources. Flag any claims that are NOT supported by the provided sources as 'factual' category findings with severity 'major'.")
            fact_check_section = "\n".join(source_lines)
        
        critic_prompt = f"""You are ReviewBee, a quality assurance critic for enterprise reports.
Analyze the following report and provide structured feedback.
{pii_note}

CONTENT TO REVIEW{' (truncated to 6000 chars)' if truncated else ''}:
```
{review_content}
```

EVALUATION CATEGORIES: {enabled_cats}

{requirements_section}{fact_check_section}
TASK: Evaluate this report and identify specific issues that need improvement.
Focus on actionable feedback - things that can actually be fixed in a revision.

Respond with ONLY a JSON object (no markdown):
{{
    "overall_score": 0.0-1.0,
    "category_scores": {{
        "clarity": 0.0-1.0,
        "completeness": 0.0-1.0,
        "accuracy": 0.0-1.0,
        "tone": 0.0-1.0,
        "structure": 0.0-1.0
    }},
    "summary": "One sentence overall assessment",
    "findings": [
        {{
            "category": "clarity|completeness|accuracy|tone|structure|grammar|factual|pii_concern|requirements",
            "severity": "minor|moderate|major",
            "description": "What the issue is",
            "suggestion": "How to fix it",
            "location_hint": "Where in the document (optional)"
        }}
    ]
}}

If the report is high quality, return high scores and empty/minimal findings.
Be constructive - only flag issues that would meaningfully improve the report."""

        try:
            session = await self._get_session()
            timeout = aiohttp.ClientTimeout(total=self.config.critique_timeout_seconds)
            
            # Use direct Ollama endpoint for the critic (lightweight model)
            response = await session.post(
                f"{self.config.llm_service_url}/ollama/generate",
                json={
                    'model': self.config.critic_model,
                    'prompt': critic_prompt,
                    'options': {
                        'num_predict': 1000,  # Critic response is short
                        'temperature': 0.3   # Low temp for consistent analysis
                    }
                },
                timeout=timeout
            )
            
            if response.status != 200:
                logger.warning(f"Critic request failed: {response.status}")
                return self._default_critique(time.time() - start_time)
            
            result = await response.json()
            response_text = result.get('response', '{}')
            
            # Parse JSON response
            critique_data = self._parse_critic_response(response_text)
            
            # Convert to CritiqueResult
            findings = list(programmatic_findings)  # Start with programmatic checks
            for i, f in enumerate(critique_data.get('findings', [])):
                try:
                    cat_str = f.get('category', 'clarity')
                    category = CritiqueCategory(cat_str) if cat_str in [c.value for c in CritiqueCategory] else CritiqueCategory.CLARITY
                    
                    findings.append(CritiqueFinding(
                        id=f"finding-{i}",
                        category=category,
                        severity=f.get('severity', 'minor'),
                        description=f.get('description', ''),
                        suggestion=f.get('suggestion', ''),
                        location_hint=f.get('location_hint'),
                        confidence=0.8
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse finding {i}: {e}")
            
            overall_score = float(critique_data.get('overall_score', 0.8))
            
            return CritiqueResult(
                overall_score=overall_score,
                category_scores=critique_data.get('category_scores', {}),
                findings=findings,
                summary=critique_data.get('summary', 'Review complete'),
                needs_revision=overall_score < self.config.revision_threshold or len([f for f in findings if f.severity == 'major']) > 0,
                critic_model=self.config.critic_model,
                critique_time_seconds=time.time() - start_time
            )
            
        except asyncio.TimeoutError:
            logger.warning("Critic request timed out")
            return self._default_critique(time.time() - start_time)
        except Exception as e:
            logger.error(f"Critic failed: {e}")
            return self._default_critique(time.time() - start_time)
    
    def _extract_target_word_count(self, prompt: str) -> Optional[int]:
        """Extract target word count from the original prompt"""
        prompt_lower = prompt.lower()
        
        # Explicit word count patterns
        patterns = [
            r'(\d[\d,]+)\+?\s*words',
            r'at\s+least\s+(\d[\d,]+)\s*words',
            r'minimum\s+(?:of\s+)?(\d[\d,]+)\s*words',
        ]
        for pattern in patterns:
            match = re.search(pattern, prompt_lower)
            if match:
                return int(match.group(1).replace(',', ''))
        
        # Keyword-based inference
        keyword_map = {
            'comprehensive': 2000,
            'in-depth': 2500,
            'in depth': 2500,
            'detailed': 1500,
            'thorough': 2000,
            'brief': 500,
            'concise': 500,
            'summary': 800,
        }
        for keyword, word_count in keyword_map.items():
            if keyword in prompt_lower:
                return word_count
        
        return None
    
    def _extract_requirements(self, prompt: str) -> Dict[str, List[str]]:
        """Parse the original prompt for specific user requirements"""
        requirements: Dict[str, List[str]] = {
            'sections': [],
            'word_count': [],
            'deliverables': [],
            'format': [],
        }
        
        prompt_lower = prompt.lower()
        
        # Section requests: numbered lists like "1. ...\n2. ..." or "include X section"
        section_patterns = [
            r'include\s+(?:a\s+)?(.+?)\s+section',
            r'provide\s+(?:a\s+)?(.+?)\s+(?:section|analysis|overview)',
            r'add\s+(?:a\s+)?(.+?)\s+section',
        ]
        for pattern in section_patterns:
            for match in re.finditer(pattern, prompt_lower):
                requirements['sections'].append(match.group(1).strip())
        
        # Numbered list items (e.g., "1. Executive Summary\n2. Gap Analysis")
        numbered_items = re.findall(r'^\s*\d+[\.\)]\s*(.+)', prompt, re.MULTILINE)
        if len(numbered_items) >= 2:
            requirements['sections'].extend(item.strip() for item in numbered_items)
        
        # Word count targets
        target = self._extract_target_word_count(prompt)
        if target:
            requirements['word_count'].append(f"{target}+ words")
        
        # Specific deliverables
        deliverables = [
            'roadmap', 'gap analysis', 'threat model', 'comparison table',
            'risk assessment', 'executive summary', 'action plan', 'timeline',
            'swot analysis', 'cost analysis', 'benchmark', 'recommendation',
            'maturity assessment', 'compliance matrix', 'implementation plan',
        ]
        for d in deliverables:
            if d in prompt_lower:
                requirements['deliverables'].append(d)
        
        # Output format requirements
        format_patterns = {
            'inline citations': r'inline\s+citations?',
            'formal tone': r'formal\s+tone',
            'executive summary': r'executive\s+summary',
            'table of contents': r'table\s+of\s+contents',
            'numbered sections': r'numbered\s+sections?',
            'bullet points': r'bullet\s+points?',
            'markdown': r'(?:in|use|with)\s+markdown',
        }
        for label, pattern in format_patterns.items():
            if re.search(pattern, prompt_lower):
                requirements['format'].append(label)
        
        # Remove empty categories
        return {k: v for k, v in requirements.items() if v}
    
    def _check_requirements(self, content: str, requirements: Dict[str, List[str]]) -> List[CritiqueFinding]:
        """Check content against extracted requirements, return findings for unmet ones"""
        findings: List[CritiqueFinding] = []
        content_lower = content.lower()
        finding_idx = 0
        
        # Check deliverables
        for deliverable in requirements.get('deliverables', []):
            if deliverable not in content_lower:
                findings.append(CritiqueFinding(
                    id=f"req-deliverable-{finding_idx}",
                    category=CritiqueCategory.REQUIREMENTS,
                    severity="major",
                    description=f"Missing required deliverable: '{deliverable}'",
                    suggestion=f"Add a dedicated '{deliverable}' section with substantive content addressing the user's request."
                ))
                finding_idx += 1
        
        # Check section requests
        for section in requirements.get('sections', []):
            section_lower = section.lower().strip()
            if len(section_lower) < 3:
                continue
            # Check for section heading or substantial mention
            if section_lower not in content_lower:
                findings.append(CritiqueFinding(
                    id=f"req-section-{finding_idx}",
                    category=CritiqueCategory.REQUIREMENTS,
                    severity="major",
                    description=f"Missing requested section: '{section}'",
                    suggestion=f"Add a section covering '{section}' as requested by the user."
                ))
                finding_idx += 1
        
        # Check format requirements
        format_checks = {
            'inline citations': [r'\[\d+\]', r'\[source', r'\(source'],
            'table of contents': [r'table of contents', r'## contents'],
            'executive summary': [r'executive summary'],
        }
        for fmt in requirements.get('format', []):
            fmt_lower = fmt.lower()
            if fmt_lower in format_checks:
                patterns = format_checks[fmt_lower]
                if not any(re.search(p, content_lower) for p in patterns):
                    findings.append(CritiqueFinding(
                        id=f"req-format-{finding_idx}",
                        category=CritiqueCategory.REQUIREMENTS,
                        severity="moderate",
                        description=f"Missing required format element: '{fmt}'",
                        suggestion=f"Add '{fmt}' formatting as requested by the user."
                    ))
                    finding_idx += 1
        
        return findings
    
    def _parse_critic_response(self, response_text: str) -> Dict[str, Any]:
        """Parse JSON from critic model response"""
        try:
            clean_text = response_text.strip()
            
            # Remove markdown code blocks if present
            if clean_text.startswith('```'):
                lines = clean_text.split('\n')
                clean_text = '\n'.join(lines[1:])  # Skip first line
                if '```' in clean_text:
                    clean_text = clean_text[:clean_text.rfind('```')]
            
            if clean_text.startswith('json'):
                clean_text = clean_text[4:].strip()
            
            return json.loads(clean_text)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse critic JSON: {e}")
            return {'overall_score': 0.8, 'findings': [], 'summary': 'Parse error'}
    
    def _default_critique(self, elapsed_time: float) -> CritiqueResult:
        """Return a default passing critique when critic fails"""
        return CritiqueResult(
            overall_score=0.85,
            category_scores={},
            findings=[],
            summary="Critic unavailable, assuming acceptable quality",
            needs_revision=False,
            critic_model=self.config.critic_model,
            critique_time_seconds=elapsed_time
        )
    
    async def _generate_revision(
        self,
        revision_prompt: str,
        generator_model: Optional[str],
        user_id: Optional[str]
    ) -> Optional[str]:
        """Generate revised content using the powerful LLM"""
        try:
            session = await self._get_session()
            timeout = aiohttp.ClientTimeout(total=self.config.revision_timeout_seconds)
            
            # Use bee/chat endpoint for revision (routes to powerful model with fallback)
            response = await session.post(
                f"{self.config.llm_service_url}/bee/chat",
                json={
                    'message': revision_prompt,
                    'user_id': user_id or 'review-bee-revision',
                    'context': {
                        'generation_mode': 'report',
                        'skip_web_search': True,
                        'skip_conversation_save': True,
                        'is_revision': True
                    }
                },
                timeout=timeout
            )
            
            if response.status != 200:
                logger.warning(f"Revision request failed: {response.status}")
                return None
            
            result = await response.json()
            return result.get('response', '').strip()
            
        except asyncio.TimeoutError:
            logger.warning("Revision request timed out")
            return None
        except Exception as e:
            logger.error(f"Revision generation failed: {e}")
            return None


# Global service instance
_review_bee_service: Optional[ReviewBeeService] = None


def get_review_bee_service() -> ReviewBeeService:
    """Get or create the global ReviewBee service instance"""
    global _review_bee_service
    if _review_bee_service is None:
        _review_bee_service = ReviewBeeService()
    return _review_bee_service


def init_review_bee_service(config: ReviewBeeConfig) -> ReviewBeeService:
    """Initialize ReviewBee service with specific config"""
    global _review_bee_service
    _review_bee_service = ReviewBeeService(config)
    return _review_bee_service
