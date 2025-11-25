#!/usr/bin/env python3
"""
QE Bee (Quality Engineering Bee) Worker for STING-CE
A lightweight review agent that validates outputs before delivery to users.

Features:
- PII token validation (checks for unresolved [PII_*] tokens)
- Output quality validation (completeness, coherence)
- LLM-powered review (optional, uses fast model like phi-3)
- Webhook notifications on completion
"""

import os
import sys
import re
import logging
import asyncio
import time
import requests
import json
import hmac
import hashlib
from datetime import datetime
import uuid
import urllib3

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Disable SSL warnings for internal communication
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class QEBeeWorker:
    """
    Quality Engineering Bee - Reviews outputs before user delivery.

    Review Types:
    - PII_CHECK: Verify all PII tokens were deserialized
    - OUTPUT_VALIDATION: Check output completeness and structure
    - QUALITY_CHECK: LLM-powered content quality assessment
    """

    # PII token pattern - matches [PII_TYPE_HASH] format
    PII_TOKEN_PATTERN = re.compile(r'\[PII_[A-Z_]+_[a-f0-9]+\]')

    # Minimum content thresholds
    MIN_REPORT_LENGTH = 500  # Characters
    MIN_RESPONSE_LENGTH = 50  # Characters

    def __init__(self, worker_id: str = None):
        self.worker_id = worker_id or f"qe-bee-{uuid.uuid4().hex[:8]}"
        self.is_running = False

        # Service URLs
        self.app_base_url = os.environ.get('APP_SERVICE_URL', 'https://app:5050')
        self.llm_service_url = os.environ.get('LLM_SERVICE_URL', 'http://external-ai:8091')

        # QE Bee configuration
        self.llm_enabled = os.environ.get('QE_BEE_LLM_ENABLED', 'true').lower() == 'true'
        self.llm_model = os.environ.get('QE_BEE_MODEL', 'phi4')
        self.review_timeout = int(os.environ.get('QE_BEE_TIMEOUT', '30'))
        self.poll_interval = int(os.environ.get('QE_BEE_POLL_INTERVAL', '5'))

        # API endpoints
        self.next_review_url = f"{self.app_base_url}/api/qe-bee/internal/next-review"
        self.complete_review_url = f"{self.app_base_url}/api/qe-bee/internal/complete-review"
        self.get_content_url = f"{self.app_base_url}/api/qe-bee/internal/get-content"

        # Session for API calls
        self.session = requests.Session()

        logger.info(f"🐝 QE Bee Worker {self.worker_id} initialized")
        logger.info(f"   App service: {self.app_base_url}")
        logger.info(f"   LLM service: {self.llm_service_url}")
        logger.info(f"   LLM enabled: {self.llm_enabled}")
        logger.info(f"   Model: {self.llm_model}")

        # Preload/warmup the model if LLM is enabled
        if self.llm_enabled:
            self._warmup_model()

    async def start(self):
        """Start the QE Bee worker loop"""
        self.is_running = True
        logger.info(f"🐝 QE Bee Worker {self.worker_id} started")

        while self.is_running:
            try:
                # Get next review job
                job = self._get_next_review()

                if job:
                    logger.info(f"🔍 Reviewing: {job.get('target_type')} {job.get('target_id')[:8]}...")
                    result = await self._process_review(job)

                    # Submit result
                    self._complete_review(job['id'], result)

                    status_emoji = "✅" if result['passed'] else "❌"
                    logger.info(f"{status_emoji} Review complete: {result['result_code']} - {result.get('result_message', '')[:100]}")
                else:
                    # No jobs, wait before polling again
                    await asyncio.sleep(self.poll_interval)

            except Exception as e:
                logger.error(f"🐝 QE Bee error: {e}")
                await asyncio.sleep(10)

    async def stop(self):
        """Stop the worker gracefully"""
        logger.info(f"🐝 Stopping QE Bee Worker {self.worker_id}")
        self.is_running = False

    def _get_next_review(self) -> dict:
        """Get next review job from the app service"""
        try:
            response = self.session.get(
                self.next_review_url,
                params={'worker_id': self.worker_id},
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('success') and data.get('data', {}).get('job'):
                    return data['data']['job']

            return None

        except Exception as e:
            logger.error(f"Error getting next review: {e}")
            return None

    def _complete_review(self, review_id: str, result: dict) -> bool:
        """Submit review result to app service"""
        try:
            response = self.session.post(
                self.complete_review_url,
                json={
                    'review_id': review_id,
                    'worker_id': self.worker_id,
                    **result
                },
                timeout=30,
                verify=False
            )

            return response.status_code == 200

        except Exception as e:
            logger.error(f"Error completing review: {e}")
            return False

    def _get_content(self, target_type: str, target_id: str) -> dict:
        """Fetch content to review from app service"""
        try:
            response = self.session.get(
                self.get_content_url,
                params={
                    'target_type': target_type,
                    'target_id': target_id
                },
                timeout=30,
                verify=False
            )

            if response.status_code == 200:
                return response.json().get('data', {})

            return None

        except Exception as e:
            logger.error(f"Error fetching content: {e}")
            return None

    async def _process_review(self, job: dict) -> dict:
        """
        Process a review job and return results.

        Returns:
            dict with: passed, result_code, result_message, confidence_score, review_details
        """
        start_time = time.time()
        target_type = job.get('target_type')
        target_id = job.get('target_id')
        review_type = job.get('review_type', 'output_validation')

        # Fetch content to review
        content_data = self._get_content(target_type, target_id)

        if not content_data:
            return {
                'passed': False,
                'result_code': 'REVIEW_ERROR',
                'result_message': 'Failed to fetch content for review',
                'confidence_score': 100,
                'review_details': {'error': 'content_fetch_failed'}
            }

        content = content_data.get('content', '')
        metadata = content_data.get('metadata', {})

        # Initialize findings
        findings = []
        issues = []
        warnings = []

        # Run checks based on review type
        if review_type in ['pii_check', 'output_validation']:
            pii_result = self._check_pii_tokens(content)
            findings.append(pii_result)
            if not pii_result['passed']:
                issues.append(pii_result)

        if review_type in ['output_validation', 'quality_check']:
            completeness_result = self._check_completeness(content, target_type, metadata)
            findings.append(completeness_result)
            if not completeness_result['passed']:
                if completeness_result.get('severity') == 'warning':
                    warnings.append(completeness_result)
                else:
                    issues.append(completeness_result)

        if review_type in ['format_validation', 'output_validation']:
            format_result = self._check_format(content, target_type, metadata)
            findings.append(format_result)
            if not format_result['passed']:
                if format_result.get('severity') == 'warning':
                    warnings.append(format_result)
                else:
                    issues.append(format_result)

        # LLM quality check (if enabled and requested)
        if self.llm_enabled and review_type in ['quality_check']:
            llm_result = await self._llm_quality_check(content, target_type, metadata)
            findings.append(llm_result)
            if not llm_result['passed']:
                issues.append(llm_result)

        # Calculate processing time
        processing_time_ms = int((time.time() - start_time) * 1000)

        # Determine overall result
        if issues:
            # Failed - return most severe issue
            primary_issue = issues[0]
            return {
                'passed': False,
                'result_code': primary_issue.get('code', 'REVIEW_ERROR'),
                'result_message': primary_issue.get('message', 'Review failed'),
                'confidence_score': primary_issue.get('confidence', 90),
                'review_details': {
                    'findings': findings,
                    'issues': issues,
                    'warnings': warnings,
                    'processing_time_ms': processing_time_ms,
                    'model_used': self.llm_model if self.llm_enabled else None
                }
            }
        elif warnings:
            # Pass with warnings
            return {
                'passed': True,
                'result_code': 'PASS_WITH_WARNINGS',
                'result_message': f"Passed with {len(warnings)} warning(s)",
                'confidence_score': 85,
                'review_details': {
                    'findings': findings,
                    'warnings': warnings,
                    'processing_time_ms': processing_time_ms,
                    'model_used': self.llm_model if self.llm_enabled else None
                }
            }
        else:
            # Clean pass
            return {
                'passed': True,
                'result_code': 'PASS',
                'result_message': 'All checks passed',
                'confidence_score': 95,
                'review_details': {
                    'findings': findings,
                    'processing_time_ms': processing_time_ms,
                    'model_used': self.llm_model if self.llm_enabled else None
                }
            }

    def _check_pii_tokens(self, content: str) -> dict:
        """Check for unresolved PII tokens in content"""
        matches = self.PII_TOKEN_PATTERN.findall(content)

        if matches:
            unique_tokens = list(set(matches))
            return {
                'check': 'pii_validation',
                'passed': False,
                'code': 'PII_TOKENS_REMAINING',
                'message': f"Found {len(matches)} unresolved PII token(s): {', '.join(unique_tokens[:5])}{'...' if len(unique_tokens) > 5 else ''}",
                'confidence': 100,
                'details': {
                    'token_count': len(matches),
                    'unique_tokens': unique_tokens[:10],
                    'sample_positions': [content.find(t) for t in unique_tokens[:3]]
                }
            }

        return {
            'check': 'pii_validation',
            'passed': True,
            'code': 'PII_CLEAN',
            'message': 'No unresolved PII tokens found',
            'confidence': 100
        }

    def _check_completeness(self, content: str, target_type: str, metadata: dict) -> dict:
        """Check if content appears complete (not truncated)"""
        min_length = self.MIN_REPORT_LENGTH if target_type == 'report' else self.MIN_RESPONSE_LENGTH

        # Check minimum length
        if len(content.strip()) < min_length:
            return {
                'check': 'completeness',
                'passed': False,
                'code': 'OUTPUT_EMPTY' if len(content.strip()) < 10 else 'OUTPUT_TRUNCATED',
                'message': f"Content too short ({len(content)} chars, minimum {min_length})",
                'confidence': 95,
                'details': {'content_length': len(content), 'min_required': min_length}
            }

        # Check for truncation indicators
        truncation_indicators = [
            content.rstrip().endswith('...') and not content.rstrip().endswith('....'),
            content.rstrip().endswith('…'),
            # Check if ends mid-sentence (no proper ending punctuation)
            len(content) > 100 and not any(content.rstrip().endswith(p) for p in ['.', '!', '?', ':', '"', "'", ')', ']', '`'])
        ]

        if any(truncation_indicators):
            return {
                'check': 'completeness',
                'passed': True,  # Warning, not failure
                'severity': 'warning',
                'code': 'POSSIBLY_TRUNCATED',
                'message': 'Content may be truncated (ends abruptly)',
                'confidence': 70,
                'details': {'ending': content[-50:] if len(content) > 50 else content}
            }

        return {
            'check': 'completeness',
            'passed': True,
            'code': 'COMPLETE',
            'message': 'Content appears complete',
            'confidence': 90
        }

    def _check_format(self, content: str, target_type: str, metadata: dict) -> dict:
        """Check if content follows expected format"""
        if target_type != 'report':
            return {
                'check': 'format',
                'passed': True,
                'code': 'FORMAT_OK',
                'message': 'Format check not applicable',
                'confidence': 100
            }

        # Check for expected report sections
        expected_sections = ['summary', 'executive summary', 'conclusion', 'recommendation']
        found_sections = []
        content_lower = content.lower()

        for section in expected_sections:
            if section in content_lower or f"## {section}" in content_lower or f"# {section}" in content_lower:
                found_sections.append(section)

        if not found_sections:
            return {
                'check': 'format',
                'passed': True,
                'severity': 'warning',
                'code': 'MISSING_SECTIONS',
                'message': 'Report may be missing standard sections (summary, conclusion, etc.)',
                'confidence': 60,
                'details': {'expected': expected_sections, 'found': found_sections}
            }

        # Check for markdown structure
        has_headers = '##' in content or '# ' in content

        return {
            'check': 'format',
            'passed': True,
            'code': 'FORMAT_OK',
            'message': f"Format looks good ({len(found_sections)} sections found)",
            'confidence': 85,
            'details': {'sections_found': found_sections, 'has_headers': has_headers}
        }

    async def _llm_quality_check(self, content: str, target_type: str, metadata: dict) -> dict:
        """Use LLM to assess content quality (fast check)"""
        try:
            # Truncate content for quick review
            review_content = content[:2000] if len(content) > 2000 else content

            prompt = f"""You are a quality assurance reviewer. Quickly assess this {target_type} output.

CONTENT TO REVIEW:
{review_content}

ASSESSMENT CRITERIA:
1. Is the content coherent and readable?
2. Does it appear to be a legitimate response (not error messages or gibberish)?
3. Is it relevant to what was likely requested?

Respond with ONLY a JSON object (no markdown):
{{"passed": true/false, "score": 1-10, "reason": "brief explanation"}}"""

            response = self.session.post(
                f"{self.llm_service_url}/generate",
                json={
                    'model': self.llm_model,
                    'prompt': prompt,
                    'options': {
                        'num_predict': 100,
                        'temperature': 0.1
                    }
                },
                timeout=self.review_timeout,
                verify=False
            )

            if response.status_code == 200:
                result_text = response.json().get('response', '{}')
                # Try to parse JSON from response
                try:
                    # Clean up response - remove markdown if present
                    clean_text = result_text.strip()
                    if clean_text.startswith('```'):
                        clean_text = clean_text.split('```')[1]
                        if clean_text.startswith('json'):
                            clean_text = clean_text[4:]

                    result = json.loads(clean_text)
                    passed = result.get('passed', True)
                    score = result.get('score', 7)
                    reason = result.get('reason', 'LLM review completed')

                    return {
                        'check': 'llm_quality',
                        'passed': passed and score >= 5,
                        'code': 'QUALITY_LOW' if not passed or score < 5 else 'QUALITY_OK',
                        'message': reason,
                        'confidence': min(score * 10, 95),
                        'details': {'llm_score': score, 'llm_passed': passed}
                    }
                except json.JSONDecodeError:
                    # LLM didn't return valid JSON, assume pass
                    return {
                        'check': 'llm_quality',
                        'passed': True,
                        'code': 'QUALITY_OK',
                        'message': 'LLM review completed (non-JSON response)',
                        'confidence': 70,
                        'details': {'raw_response': result_text[:200]}
                    }

            return {
                'check': 'llm_quality',
                'passed': True,
                'code': 'QUALITY_UNKNOWN',
                'message': 'LLM review unavailable, skipping',
                'confidence': 50
            }

        except Exception as e:
            logger.warning(f"LLM quality check failed: {e}")
            return {
                'check': 'llm_quality',
                'passed': True,  # Don't fail on LLM errors
                'code': 'QUALITY_UNKNOWN',
                'message': f'LLM review error: {str(e)[:100]}',
                'confidence': 50
            }

    def _warmup_model(self):
        """Preload the LLM model to avoid cold start delays"""
        try:
            logger.info(f"🔥 Warming up QE Bee model: {self.llm_model}")
            warmup_start = time.time()

            response = self.session.post(
                f"{self.llm_service_url}/ollama/generate",
                json={
                    'model': self.llm_model,
                    'prompt': 'Warmup: respond with OK',
                    'stream': False,
                    'options': {
                        'num_predict': 5,
                        'temperature': 0.1
                    }
                },
                timeout=60,  # Allow more time for initial model loading
                verify=False
            )

            warmup_time = time.time() - warmup_start

            if response.status_code == 200:
                logger.info(f"✅ Model {self.llm_model} warmed up successfully ({warmup_time:.2f}s)")
            else:
                logger.warning(f"⚠️ Model warmup returned status {response.status_code}")

        except Exception as e:
            logger.warning(f"⚠️ Model warmup failed (will retry on first use): {e}")

    def health_check(self) -> bool:
        """Check if the worker is healthy"""
        try:
            response = self.session.get(
                f"{self.app_base_url}/health",
                timeout=10,
                verify=False
            )
            return response.status_code == 200
        except:
            return False


def simple_health_check() -> bool:
    """Lightweight health check for Docker"""
    try:
        app_url = os.environ.get('APP_SERVICE_URL', 'https://app:5050')
        response = requests.get(f"{app_url}/health", timeout=5, verify=False)
        return response.status_code == 200
    except:
        return False


def health_check_main():
    """Entry point for health check"""
    if simple_health_check():
        sys.exit(0)
    else:
        sys.exit(1)


async def main():
    """Main entry point for QE Bee worker"""
    worker = QEBeeWorker()

    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
        await worker.stop()
    except Exception as e:
        logger.error(f"QE Bee crashed: {e}")
        raise


if __name__ == '__main__':
    asyncio.run(main())
