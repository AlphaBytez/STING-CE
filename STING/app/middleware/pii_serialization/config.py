"""
PII Protection Configuration

Handles mode-based configuration for PII protection (local vs external).

Provides:
- Mode detection and settings
- PII type filtering per mode
- TTL configuration
- Memory limits
"""

from typing import List, Optional
from .detector import PIIType


class PIIProtectionConfig:
    """
    Configuration manager for PII protection middleware.

    Handles different protection levels for local vs external AI services.
    """

    def __init__(self, security_config: dict):
        """
        Initialize with security config from config.yml.

        Args:
            security_config: The 'security' section from config.yml
        """
        self.config = security_config.get("message_pii_protection", {})

        # Cache commonly accessed values
        self._enabled = self.config.get("enabled", True)
        self._serialization = self.config.get("serialization", {})
        self._modes = self.config.get("modes", {})
        self._audit = self.config.get("audit", {})
        self._performance = self.config.get("performance", {})

    def is_enabled_for_mode(self, mode: str) -> bool:
        """
        Check if PII protection is enabled for a specific mode.

        Args:
            mode: Protection mode (local/external)

        Returns:
            True if protection is enabled
        """
        if not self._enabled:
            return False

        if not self._serialization.get("enabled", True):
            return False

        # Check mode-specific settings
        mode_config = self._modes.get(mode, {})
        return mode_config.get("enabled", False)

    def get_pii_types_for_mode(self, mode: str) -> List[PIIType]:
        """
        Get list of PII types to detect for a mode.

        Args:
            mode: Protection mode (local/external)

        Returns:
            List of PIIType enums to detect
        """
        mode_config = self._modes.get(mode, {})
        pii_type_names = mode_config.get("pii_types", [])

        # Convert string names to PIIType enums
        pii_types = []
        for name in pii_type_names:
            try:
                pii_type = PIIType(name)
                pii_types.append(pii_type)
            except ValueError:
                # Unknown PII type - skip
                pass

        return pii_types

    def get_ttl(self, error_occurred: bool = False) -> int:
        """
        Get cache TTL based on success/error state.

        Args:
            error_occurred: True if an error occurred

        Returns:
            TTL in seconds
        """
        cache_ttl = self._serialization.get("cache_ttl", {})

        if error_occurred:
            return cache_ttl.get("on_error", 3600)  # 1 hour default
        else:
            return cache_ttl.get("default", 300)  # 5 min default

    def get_redis_db(self) -> int:
        """Get Redis database number for PII cache."""
        return self._serialization.get("redis_db", 3)

    def get_max_cache_size_mb(self) -> int:
        """Get maximum cache size in MB."""
        cache_ttl = self._serialization.get("cache_ttl", {})
        return cache_ttl.get("max_total_size_mb", 50)

    def get_max_per_user(self) -> int:
        """Get max conversations cached per user."""
        cache_ttl = self._serialization.get("cache_ttl", {})
        return cache_ttl.get("max_per_user", 50)

    def should_log_serialization(self) -> bool:
        """Check if serialization events should be logged."""
        return self._audit.get("log_serialization_events", True)

    def should_log_deserialization(self) -> bool:
        """Check if deserialization events should be logged."""
        return self._audit.get("log_deserialization_events", True)

    def should_log_cache_ops(self) -> bool:
        """Check if cache operations should be logged."""
        return self._audit.get("log_cache_operations", False)

    def get_audit_retention_days(self) -> int:
        """Get audit log retention period in days."""
        return self._audit.get("retention_days", 90)

    def is_async_serialization_enabled(self) -> bool:
        """Check if async serialization is enabled."""
        return self._performance.get("async_serialization", True)

    def get_protection_level(self, mode: str) -> str:
        """
        Get protection level for a mode.

        Args:
            mode: Protection mode

        Returns:
            Protection level string (minimal/standard/strict)
        """
        mode_config = self._modes.get(mode, {})
        return mode_config.get("protection_level", "standard")

    def get_token_format(self) -> str:
        """Get token format template."""
        return self._serialization.get(
            "token_format",
            "${EntityType}{Instance}_{PIIType}_hash"
        )
