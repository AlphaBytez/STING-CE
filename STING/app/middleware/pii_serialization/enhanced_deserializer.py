"""
Enhanced PII Deserializer with Fallback and Diagnostics
"""
import asyncio
import logging
import re
from typing import Dict, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)

class EnhancedDeserializer:
    """Enhanced deserializer with fallback mechanisms and diagnostics"""

    def __init__(self, cache_manager):
        self.cache_manager = cache_manager
        self.token_pattern = re.compile(r'\$[A-Za-z]+\d+_[a-z_]+_[a-f0-9]{4}')
        self.fallback_store = {}  # Local fallback for cache misses
        self.diagnostics = {
            'cache_hits': 0,
            'cache_misses': 0,
            'fallback_hits': 0,
            'unresolved_tokens': []
        }

    async def deserialize_response(
        self,
        response: str,
        context: Dict[str, any],
        enable_diagnostics: bool = True,
        track_positions: bool = True
    ) -> Tuple[str, Dict]:
        """
        Deserialize response with enhanced error handling, diagnostics, and position tracking.

        Args:
            response: Text containing PII tokens
            context: Context dict with conversation_id and optional pii_mapping
            enable_diagnostics: Whether to include diagnostic information
            track_positions: Whether to track positions of deserialized PII for visual indicators

        Returns:
            Tuple of (deserialized_response, diagnostics_info)
            diagnostics_info includes pii_metadata for frontend visual indicators
        """
        conversation_id = context.get('conversation_id')
        if not conversation_id:
            logger.warning("No conversation_id in context, returning original response")
            return response, {'error': 'no_conversation_id'}

        # Find all tokens in the response
        tokens = self.token_pattern.findall(response)
        if not tokens:
            return response, {
                'tokens_found': 0,
                'pii_metadata': []  # Empty metadata for frontend
            }

        logger.info(f"Found {len(tokens)} tokens to deserialize")

        # Get PII mapping from cache
        pii_mapping = await self._get_pii_mapping_with_fallback(conversation_id, context)

        # Track deserialization results
        replaced_count = 0
        missed_tokens = []
        pii_metadata = []  # NEW: Track position and type info for visual indicators

        # Build a list of token replacements with positions
        replacements = []
        for token in set(tokens):  # Use set to avoid duplicate processing
            original_value = None
            source = None

            if token in pii_mapping:
                original_value = pii_mapping[token]
                source = 'cache'
                self.diagnostics['cache_hits'] += 1
            elif token in self.fallback_store.get(conversation_id, {}):
                original_value = self.fallback_store[conversation_id][token]
                source = 'fallback'
                self.diagnostics['fallback_hits'] += 1
            else:
                # Cache miss - try reconstruction
                missed_tokens.append(token)
                self.diagnostics['cache_misses'] += 1
                self.diagnostics['unresolved_tokens'].append({
                    'token': token,
                    'timestamp': datetime.now().isoformat(),
                    'conversation_id': conversation_id
                })

                original_value = self._attempt_reconstruction(token)
                source = 'reconstructed' if original_value else None

            if original_value:
                replacements.append({
                    'token': token,
                    'value': original_value,
                    'source': source
                })
                replaced_count += 1

        # Process replacements and track positions
        working_response = response
        cumulative_offset = 0  # Track how positions shift as we replace

        for replacement in replacements:
            token = replacement['token']
            value = replacement['value']

            if track_positions:
                # Find all occurrences of this token
                import re as regex
                for match in regex.finditer(regex.escape(token), working_response):
                    token_start = match.start()
                    token_end = match.end()

                    # Calculate position in final deserialized text
                    # (accounting for length differences from previous replacements)
                    final_start = token_start + cumulative_offset
                    final_end = final_start + len(value)

                    # Extract PII type and determine risk level
                    pii_type = self._extract_pii_type(token)
                    risk_level = self._determine_risk_level(pii_type)

                    pii_metadata.append({
                        'original_position': {'start': token_start, 'end': token_end},
                        'deserialized_position': {'start': final_start, 'end': final_end},
                        'token': token,
                        'deserialized_value': value,
                        'pii_type': pii_type,
                        'risk_level': risk_level,
                        'confidence': 0.95,  # High confidence for cache hits
                        'source': replacement['source']
                    })

                    # Update cumulative offset for next replacements
                    cumulative_offset += (len(value) - len(token))

            # Perform the actual replacement
            working_response = working_response.replace(token, value, 1)  # Replace first occurrence

        # Log diagnostics if enabled
        if enable_diagnostics and missed_tokens:
            logger.warning(
                f"Failed to deserialize {len(missed_tokens)} tokens: {missed_tokens[:5]}..."
                f"\nDiagnostics: {self.diagnostics}"
            )

        return working_response, {
            'tokens_found': len(tokens),
            'tokens_replaced': replaced_count,
            'tokens_missed': len(missed_tokens),
            'missed_tokens': missed_tokens[:10] if enable_diagnostics else [],
            'pii_metadata': pii_metadata,  # NEW: Position and type info for frontend
            'diagnostics': self.diagnostics if enable_diagnostics else {}
        }

    async def _get_pii_mapping_with_fallback(
        self,
        conversation_id: str,
        context: Dict
    ) -> Dict[str, str]:
        """Get PII mapping with multiple fallback strategies"""

        # Primary: Try cache
        try:
            mapping = await self.cache_manager.get_pii_mapping(conversation_id)
            if mapping:
                return mapping
        except Exception as e:
            logger.error(f"Cache retrieval failed: {e}")

        # Secondary: Check context for embedded mapping
        if 'pii_mapping' in context:
            mapping = context['pii_mapping']
            # Store in fallback for future use
            self.fallback_store[conversation_id] = mapping
            return mapping

        # Tertiary: Check if mapping exists in alternate cache DB
        try:
            # Try different Redis DB or key pattern
            alternate_mapping = await self._check_alternate_cache(conversation_id)
            if alternate_mapping:
                return alternate_mapping
        except Exception as e:
            logger.error(f"Alternate cache check failed: {e}")

        # No mapping found
        logger.warning(f"No PII mapping found for conversation {conversation_id}")
        return {}

    async def _check_alternate_cache(self, conversation_id: str) -> Optional[Dict]:
        """Check alternate cache locations for PII mapping"""
        # Check different key patterns that might be used
        alternate_keys = [
            f"sting:pii:conv:{conversation_id}:map",
            f"pii:conversation:{conversation_id}",
            f"chat:pii:{conversation_id}"
        ]

        for key in alternate_keys:
            try:
                mapping = await self.cache_manager.get_raw(key)
                if mapping:
                    logger.info(f"Found PII mapping in alternate location: {key}")
                    return mapping
            except:
                continue

        return None

    def _attempt_reconstruction(self, token: str) -> Optional[str]:
        """
        Attempt to reconstruct a reasonable placeholder when PII can't be restored.
        This provides a better UX than showing raw tokens.
        """
        # Parse token structure: $EntityType#_type_hash
        match = re.match(r'\$([A-Za-z]+)(\d+)_([a-z_]+)_([a-f0-9]{4})', token)
        if not match:
            return None

        entity_type, entity_num, pii_type, _ = match.groups()

        # Generate user-friendly placeholder based on type
        placeholders = {
            'name': f'[Name {entity_num}]',
            'email': f'[Email {entity_num}]',
            'phone': f'[Phone {entity_num}]',
            'address': f'[Address {entity_num}]',
            'ssn': '[SSN]',
            'credit_card': '[Credit Card]',
            'bank_account': '[Bank Account]',
            'ip_address': f'[IP Address {entity_num}]',
            'medical_record': '[Medical Record]',
            'account_number': f'[Account {entity_num}]',
            'date_of_birth': '[Date of Birth]'
        }

        return placeholders.get(pii_type, f'[{pii_type.replace("_", " ").title()}]')

    def _extract_pii_type(self, token: str) -> str:
        """
        Extract PII type from token structure.

        Token format: $EntityType#_pii_type_hash
        Example: $Person1_name_a3f5 -> 'name'
        """
        match = re.match(r'\$([A-Za-z]+)(\d+)_([a-z_]+)_([a-f0-9]{4})', token)
        if match:
            return match.group(3)  # Returns 'name', 'email', 'ssn', etc.
        return 'unknown'

    def _determine_risk_level(self, pii_type: str) -> str:
        """
        Determine risk level based on PII type.

        Risk levels align with compliance frameworks (HIPAA, GDPR, PCI-DSS).
        """
        # High-risk PII: Financial, medical, government IDs
        high_risk = [
            'ssn', 'social_security_number',
            'credit_card', 'bank_account',
            'medical_record', 'patient_id', 'mrn',
            'drivers_license', 'passport',
            'dea_number', 'npi_number'
        ]

        # Medium-risk PII: Contact info, identifiers
        medium_risk = [
            'email', 'phone', 'phone_number',
            'date_of_birth', 'dob',
            'account_number', 'employee_id',
            'ip_address', 'mac_address',
            'medical_condition', 'diagnosis'
        ]

        # Low-risk PII: Names, addresses (still protected, but less sensitive)
        # Everything else defaults to low risk

        if pii_type in high_risk:
            return 'high'
        elif pii_type in medium_risk:
            return 'medium'
        else:
            return 'low'

    def get_diagnostics_report(self) -> str:
        """Generate a diagnostic report for troubleshooting"""
        report = f"""
PII Deserialization Diagnostics Report
======================================
Cache Hits: {self.diagnostics['cache_hits']}
Cache Misses: {self.diagnostics['cache_misses']}
Fallback Hits: {self.diagnostics['fallback_hits']}
Unresolved Tokens: {len(self.diagnostics['unresolved_tokens'])}

Recent Unresolved Tokens:
{chr(10).join(str(t) for t in self.diagnostics['unresolved_tokens'][-10:])}

Recommendations:
- Check Redis connectivity and TTL settings
- Verify conversation_id consistency
- Consider increasing cache TTL in config.yml
- Enable fallback storage for critical conversations
"""
        return report