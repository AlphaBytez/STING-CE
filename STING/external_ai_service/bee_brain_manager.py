#!/usr/bin/env python3
"""
Bee Brain Manager - Dynamically loads versioned bee_brain knowledge bases

Handles:
- Version detection and compatibility checking
- Automatic fallback to compatible versions
- Caching for performance
- Update triggers
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any
from packaging import version as pkg_version

logger = logging.getLogger(__name__)

class BeeBrainManager:
    """Manages versioned bee_brain knowledge bases"""

    def __init__(self, bee_brains_dir: Optional[Path] = None, sting_version: Optional[str] = None):
        # Default paths
        if bee_brains_dir is None:
            self.bee_brains_dir = Path(__file__).parent / "bee_brains"
        else:
            self.bee_brains_dir = bee_brains_dir

        # Ensure directory exists
        self.bee_brains_dir.mkdir(parents=True, exist_ok=True)

        # STING version
        if sting_version is None:
            self.sting_version = self._read_sting_version()
        else:
            self.sting_version = sting_version

        # Cache
        self.loaded_brain = None
        self.loaded_version = None

        logger.info(f"BeeBrainManager initialized: STING v{self.sting_version}, Brain dir: {self.bee_brains_dir}")

    def _read_sting_version(self) -> str:
        """Read STING version from VERSION file"""
        version_file = Path(__file__).parent.parent / "VERSION"
        if version_file.exists():
            try:
                return version_file.read_text().strip()
            except Exception as e:
                logger.warning(f"Could not read VERSION file: {e}")

        logger.warning("VERSION file not found, defaulting to 1.0.0")
        return "1.0.0"

    def list_available_versions(self) -> list:
        """List all available bee_brain versions"""
        versions = []

        for brain_file in self.bee_brains_dir.glob("bee_brain_v*.json"):
            # Extract version from filename: bee_brain_v1.0.0.json
            version_str = brain_file.stem.replace("bee_brain_v", "")
            versions.append(version_str)

        # Sort versions using semantic versioning
        try:
            versions.sort(key=lambda v: pkg_version.parse(v), reverse=True)
        except Exception as e:
            logger.warning(f"Could not sort versions: {e}")
            versions.sort(reverse=True)

        return versions

    def find_compatible_version(self, sting_version: str) -> Optional[str]:
        """Find the best compatible bee_brain version for STING version"""
        available_versions = self.list_available_versions()

        if not available_versions:
            logger.warning("No bee_brain versions available")
            return None

        try:
            sting_ver = pkg_version.parse(sting_version)
            sting_major = sting_ver.major

            # Find highest version with matching major version
            for brain_version in available_versions:
                brain_ver = pkg_version.parse(brain_version)
                if brain_ver.major == sting_major:
                    logger.info(f"Found compatible version: {brain_version} for STING {sting_version}")
                    return brain_version

            # If no matching major version, check compatibility matrix
            logger.warning(f"No matching major version found for STING {sting_version}")

            # Load latest version and check its compatibility
            latest_version = available_versions[0]
            brain_data = self.load_brain_version(latest_version)

            if brain_data:
                compat = brain_data.get("sting_version_compatibility", {})
                min_ver = compat.get("min", "0.0.0")
                max_ver = compat.get("max", "999.999.999")

                if pkg_version.parse(min_ver) <= sting_ver <= pkg_version.parse(max_ver):
                    logger.info(f"Using latest version {latest_version} (compatible: {min_ver}-{max_ver})")
                    return latest_version

            logger.warning(f"No compatible version found, using latest: {available_versions[0]}")
            return available_versions[0]

        except Exception as e:
            logger.error(f"Error finding compatible version: {e}")
            # Fallback to latest
            return available_versions[0] if available_versions else None

    def load_brain_version(self, brain_version: str) -> Optional[Dict[str, Any]]:
        """Load a specific bee_brain version"""
        brain_file = self.bee_brains_dir / f"bee_brain_v{brain_version}.json"

        if not brain_file.exists():
            logger.error(f"Bee brain file not found: {brain_file}")
            return None

        try:
            with open(brain_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading bee brain {brain_version}: {e}")
            return None

    def load_brain(self, force_reload: bool = False) -> Optional[Dict[str, Any]]:
        """Load the appropriate bee_brain for current STING version"""

        # Return cached version if available
        if self.loaded_brain and not force_reload:
            logger.debug(f"Returning cached bee brain v{self.loaded_version}")
            return self.loaded_brain

        # Find compatible version
        compatible_version = self.find_compatible_version(self.sting_version)

        if not compatible_version:
            logger.error("No compatible bee_brain version found")
            return None

        # Load the brain
        logger.info(f"Loading bee brain v{compatible_version} for STING v{self.sting_version}")
        brain_data = self.load_brain_version(compatible_version)

        if brain_data:
            self.loaded_brain = brain_data
            self.loaded_version = compatible_version
            logger.info(f"Successfully loaded bee brain v{compatible_version}")
            return brain_data

        logger.error(f"Failed to load bee brain v{compatible_version}")
        return None

    def get_core_knowledge(self) -> str:
        """Get core knowledge as a text string (for LLM system prompt)"""
        brain = self.load_brain()
        if not brain:
            return ""

        core = brain.get("core_knowledge", {})

        # Concatenate all core knowledge sections
        sections = []
        for section_name, section_content in core.items():
            sections.append(section_content)

        return "\n\n".join(sections)

    def get_documentation(self, path: Optional[str] = None) -> Any:
        """Get documentation (entire tree or specific path)"""
        brain = self.load_brain()
        if not brain:
            return {}

        docs = brain.get("documentation", {})

        if path:
            # Navigate to specific path
            parts = path.split('/')
            current = docs
            for part in parts:
                if isinstance(current, dict) and part in current:
                    current = current[part]
                else:
                    return None
            return current

        return docs

    def search_documentation(self, query: str, limit: int = 5) -> list:
        """Search documentation for relevant content"""
        brain = self.load_brain()
        if not brain:
            return []

        docs = brain.get("documentation", {})
        results = []

        def search_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    search_recursive(value, f"{path}/{key}" if path else key)
            elif isinstance(obj, str):
                # Simple keyword search
                if query.lower() in obj.lower():
                    # Extract context around match
                    idx = obj.lower().find(query.lower())
                    start = max(0, idx - 100)
                    end = min(len(obj), idx + 100)
                    context = obj[start:end]

                    results.append({
                        "path": path,
                        "context": context,
                        "relevance": obj.lower().count(query.lower())
                    })

        search_recursive(docs)

        # Sort by relevance
        results.sort(key=lambda x: x["relevance"], reverse=True)

        return results[:limit]

    def get_metadata(self) -> Dict[str, Any]:
        """Get bee_brain metadata"""
        brain = self.load_brain()
        if not brain:
            return {}

        return {
            "version": brain.get("version"),
            "loaded_version": self.loaded_version,
            "sting_version": self.sting_version,
            "compatibility": brain.get("sting_version_compatibility"),
            "metadata": brain.get("metadata"),
            "created_at": brain.get("created_at")
        }

    def reload(self) -> bool:
        """Force reload of bee_brain (useful after updates)"""
        logger.info("Reloading bee brain...")
        self.loaded_brain = None
        self.loaded_version = None
        brain = self.load_brain(force_reload=True)
        return brain is not None
