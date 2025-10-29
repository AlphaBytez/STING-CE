"""
PII Protection Mode Detection

Intelligently determines which PII protection mode to use based on:
- AI endpoint URL/IP address
- Network location (local/VPN/external)
- Request context (report generation, chat, etc.)
- Request headers (overrides)
"""

import ipaddress
import re
from typing import Optional, Tuple, List
from urllib.parse import urlparse
import logging

logger = logging.getLogger(__name__)


class ModeDetector:
    """Intelligent PII protection mode detection"""

    def __init__(self, config: dict):
        """
        Initialize mode detector with configuration.

        Args:
            config: PII protection config from config.yml
        """
        self.config = config
        self.auto_detection_config = config.get('auto_mode_detection', {})
        self.modes_config = config.get('modes', {})
        self.override_config = config.get('request_overrides', {})

    def detect_mode(
        self,
        endpoint_url: str = None,
        provider: str = "ollama",
        context: str = "chat",
        request_headers: dict = None,
        user_role: str = "user"
    ) -> Tuple[str, dict]:
        """
        Detect appropriate PII protection mode.

        Args:
            endpoint_url: AI service endpoint URL
            provider: AI provider name (ollama, openai, anthropic, etc.)
            context: Request context (chat, report, analysis, etc.)
            request_headers: HTTP headers from request
            user_role: User's role (for override permissions)

        Returns:
            Tuple of (mode_name, mode_config)
            Example: ("trusted", {...mode_config...})
        """
        # 1. Check for request-level override first (highest priority)
        if self.override_config.get('enabled') and request_headers:
            override_mode = self._check_override(request_headers, user_role)
            if override_mode:
                logger.info(f"PII mode override: {override_mode} (user_role: {user_role})")
                return override_mode, self._get_override_config(override_mode, request_headers)

        # 2. Check if context is report generation
        if context in ['report', 'report_generation', 'analysis']:
            report_mode = self.modes_config.get('report', {})
            if report_mode.get('enabled', False):
                logger.info(f"Using 'report' mode for context: {context}")
                return 'report', report_mode

        # 3. Auto-detect based on endpoint if enabled
        if self.auto_detection_config.get('enabled') and endpoint_url:
            detected_mode = self._detect_from_endpoint(endpoint_url)
            if detected_mode:
                mode_config = self.modes_config.get(detected_mode, {})
                logger.info(f"Auto-detected mode '{detected_mode}' from endpoint: {endpoint_url}")
                return detected_mode, mode_config

        # 4. Use provider-based detection
        for mode_name, mode_config in self.modes_config.items():
            applies_to = mode_config.get('applies_to', [])
            if provider in applies_to:
                logger.info(f"Using mode '{mode_name}' for provider: {provider}")
                return mode_name, mode_config

        # 5. Fallback to configured default
        fallback = self.auto_detection_config.get('fallback_mode', 'external')
        fallback_config = self.modes_config.get(fallback, {})
        logger.warning(f"No mode match, using fallback: {fallback}")
        return fallback, fallback_config

    def _detect_from_endpoint(self, endpoint_url: str) -> Optional[str]:
        """
        Detect mode based on endpoint URL/IP.

        Returns:
            Mode name ('local', 'trusted', 'external') or None
        """
        try:
            parsed = urlparse(endpoint_url)
            hostname = parsed.hostname or parsed.netloc

            # Check if it's localhost
            if hostname in ['localhost', '127.0.0.1', '::1']:
                return 'local'

            # Check if it's a trusted domain
            trusted_domains = self.auto_detection_config.get('trusted_domains', [])
            for domain_pattern in trusted_domains:
                if self._match_domain(hostname, domain_pattern):
                    return 'trusted'

            # Check if IP is in trusted network range
            if self._is_ip_address(hostname):
                if self._is_trusted_network(hostname):
                    return 'trusted'

            # External by default
            return 'external'

        except Exception as e:
            logger.error(f"Error detecting mode from endpoint '{endpoint_url}': {e}")
            return None

    def _is_trusted_network(self, ip_str: str) -> bool:
        """Check if IP address is in trusted network ranges."""
        try:
            ip = ipaddress.ip_address(ip_str)
            trusted_networks = self.auto_detection_config.get('trusted_networks', [])

            for network_str in trusted_networks:
                network = ipaddress.ip_network(network_str, strict=False)
                if ip in network:
                    return True

            return False

        except Exception as e:
            logger.debug(f"Error checking trusted network for '{ip_str}': {e}")
            return False

    def _is_ip_address(self, hostname: str) -> bool:
        """Check if hostname is an IP address."""
        try:
            ipaddress.ip_address(hostname)
            return True
        except ValueError:
            return False

    def _match_domain(self, hostname: str, pattern: str) -> bool:
        """
        Match hostname against domain pattern.

        Supports wildcards: *.local, *.tailscale
        """
        if pattern.startswith('*.'):
            # Wildcard matching
            suffix = pattern[1:]  # Remove *
            return hostname.endswith(suffix)
        else:
            # Exact match
            return hostname == pattern

    def _check_override(self, headers: dict, user_role: str) -> Optional[str]:
        """
        Check for request-level PII mode override.

        Returns:
            Override mode name or None
        """
        # Check if user role is allowed to use overrides
        allowed_roles = self.override_config.get('allowed_roles', [])
        if user_role not in allowed_roles:
            return None

        # Check for override header
        override_header = self.override_config.get('require_header', 'X-STING-PII-Override')
        override_value = headers.get(override_header)

        if not override_value:
            return None

        # Parse override value
        # Format: "mode:trusted" or "exclude:person_name,email"
        if override_value.startswith('mode:'):
            mode_name = override_value.split(':', 1)[1]
            if mode_name in self.modes_config:
                return mode_name

        # "exclude:" format returns None here, handled in _get_override_config
        return None

    def _get_override_config(self, override_mode: Optional[str], headers: dict) -> dict:
        """
        Build custom mode config based on override header.

        Supports:
        - mode:trusted -> Use trusted mode config
        - exclude:person_name,email -> Custom config excluding those types
        """
        if override_mode:
            # Simple mode override
            return self.modes_config.get(override_mode, {})

        # Check for "exclude:" format
        override_header = self.override_config.get('require_header', 'X-STING-PII-Override')
        override_value = headers.get(override_header, '')

        if override_value.startswith('exclude:'):
            excluded_types = override_value.split(':', 1)[1].split(',')
            excluded_types = [t.strip() for t in excluded_types]

            # Start with external mode config and remove excluded types
            base_config = self.modes_config.get('external', {}).copy()
            base_pii_types = base_config.get('pii_types', [])

            # Filter out excluded types
            filtered_types = [t for t in base_pii_types if t not in excluded_types]
            base_config['pii_types'] = filtered_types
            base_config['_override_applied'] = True
            base_config['_excluded_types'] = excluded_types

            logger.info(f"PII override: Excluded types {excluded_types} from protection")
            return base_config

        # Fallback to external mode
        return self.modes_config.get('external', {})

    def get_excluded_pii_types(self, headers: dict, user_role: str) -> List[str]:
        """
        Get list of PII types to exclude from protection based on override.

        Returns:
            List of PII type names to exclude
        """
        # Check permissions
        if not self.override_config.get('enabled'):
            return []

        allowed_roles = self.override_config.get('allowed_roles', [])
        if user_role not in allowed_roles:
            return []

        # Parse header
        override_header = self.override_config.get('require_header', 'X-STING-PII-Override')
        override_value = headers.get(override_header, '')

        if override_value.startswith('exclude:'):
            excluded_types = override_value.split(':', 1)[1].split(',')
            return [t.strip() for t in excluded_types]

        return []
