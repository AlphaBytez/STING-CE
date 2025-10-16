"""
Filter Manager for LLM Gateway
Handles content filtering, data leakage prevention, and safety checks
"""

import os
import re
import json
import logging
import importlib
from typing import Dict, Any, List, Tuple, Callable, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.environ.get("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("filter-manager")

class FilterManager:
    """Manages content filtering for LLM responses"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.filters = {}
        self.filter_stats = {}
        self.custom_filters_dir = os.environ.get("CUSTOM_FILTERS_DIR", "./filtering/custom")
        
        # Initialize built-in filters
        self._init_built_in_filters()
        
    def _init_built_in_filters(self) -> None:
        """Initialize the built-in filters based on configuration"""
        # Toxicity filter
        if self.config.get("toxicity", {}).get("enabled", True):
            try:
                from .toxicity_filter import ToxicityFilter
                threshold = self.config.get("toxicity", {}).get("threshold", 0.7)
                self.filters["toxicity"] = ToxicityFilter(threshold=threshold)
                self.filter_stats["toxicity"] = {"checked": 0, "filtered": 0}
                logger.info(f"Toxicity filter initialized with threshold {threshold}")
            except ImportError as e:
                logger.warning(f"Could not initialize toxicity filter: {str(e)}")
        
        # Data leakage filter
        if self.config.get("data_leakage", {}).get("enabled", True):
            try:
                from .data_leakage_filter import DataLeakageFilter
                sensitive_patterns = self.config.get("data_leakage", {}).get("sensitive_patterns", [])
                self.filters["data_leakage"] = DataLeakageFilter(patterns=sensitive_patterns)
                self.filter_stats["data_leakage"] = {"checked": 0, "filtered": 0}
                logger.info(f"Data leakage filter initialized with {len(sensitive_patterns)} patterns")
            except ImportError as e:
                logger.warning(f"Could not initialize data leakage filter: {str(e)}")
    
    def load_custom_filters(self) -> None:
        """Load custom filters from the custom filters directory"""
        custom_filters_path = Path(self.custom_filters_dir)
        if not custom_filters_path.exists():
            logger.info(f"Custom filters directory not found: {self.custom_filters_dir}")
            return
        
        # Load all Python files in the custom filters directory
        for file_path in custom_filters_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
                
            try:
                # Import the module
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Look for filter classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if hasattr(attr, "is_filter") and attr.is_filter:
                        filter_instance = attr()
                        filter_name = getattr(attr, "filter_name", attr_name.lower())
                        self.filters[filter_name] = filter_instance
                        self.filter_stats[filter_name] = {"checked": 0, "filtered": 0}
                        logger.info(f"Loaded custom filter: {filter_name}")
            except Exception as e:
                logger.error(f"Error loading custom filter {file_path.name}: {str(e)}")
    
    def check_text(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Check text against all enabled filters
        
        Args:
            text: The text to check
            
        Returns:
            Tuple of (should_filter, reason)
        """
        for filter_name, filter_instance in self.filters.items():
            try:
                self.filter_stats[filter_name]["checked"] += 1
                should_filter, reason = filter_instance.check(text)
                
                if should_filter:
                    self.filter_stats[filter_name]["filtered"] += 1
                    logger.info(f"Content filtered by {filter_name}: {reason}")
                    return True, f"{filter_name}: {reason}"
            except Exception as e:
                logger.error(f"Error in filter {filter_name}: {str(e)}")
        
        return False, None
    
    def get_stats(self) -> Dict[str, Any]:
        """Get filter statistics"""
        return {
            "filters_enabled": list(self.filters.keys()),
            "filter_stats": self.filter_stats
        }
    
    def register_filter(self, name: str, filter_instance: Any) -> None:
        """Register a new filter at runtime"""
        if hasattr(filter_instance, "check") and callable(filter_instance.check):
            self.filters[name] = filter_instance
            self.filter_stats[name] = {"checked": 0, "filtered": 0}
            logger.info(f"Registered new filter: {name}")
        else:
            logger.error(f"Invalid filter instance for {name}: missing check() method")