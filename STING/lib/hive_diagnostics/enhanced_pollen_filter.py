#!/usr/bin/env python3
"""
🔒 Enhanced Pollen Filter for Bee Support System
Advanced log sanitization with pipeline integration and real-time processing
"""

import re
import os
import json
import logging
import hashlib
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Union
from pathlib import Path

logger = logging.getLogger(__name__)


class EnhancedPollenFilter:
    """Enhanced version of pollen filter with support system integration"""
    
    def __init__(self, config_path: Optional[str] = None):
        """Initialize enhanced pollen filter
        
        Args:
            config_path: Path to custom sanitization config
        """
        self.stats = {
            'files_processed': 0,
            'patterns_matched': 0,
            'bytes_redacted': 0,
            'pii_instances': 0,
            'credential_instances': 0,
            'network_instances': 0
        }
        
        self.patterns = self._initialize_patterns()
        self.realtime_patterns = self._initialize_realtime_patterns()
        
        # Load custom config if provided
        if config_path and os.path.exists(config_path):
            self._load_custom_config(config_path)
    
    def _initialize_patterns(self) -> Dict[str, List[Dict]]:
        """Initialize comprehensive sanitization patterns"""
        return {
            'credentials': [
                {
                    'name': 'password_fields',
                    'pattern': r'(password|passwd|pwd)([=:\s]+)[^\s\n\r]+',
                    'replacement': r'\1\2***PASSWORD_REDACTED***',
                    'confidence': 0.95,
                    'description': 'Password field detection'
                },
                {
                    'name': 'api_keys',
                    'pattern': r'(api[_-]?key|apikey)([=:\s]+)[^\s\n\r]+',
                    'replacement': r'\1\2***API_KEY_REDACTED***',
                    'confidence': 0.98,
                    'description': 'API key detection'
                },
                {
                    'name': 'tokens',
                    'pattern': r'(token|secret|auth[_-]?key)([=:\s]+)[^\s\n\r]+',
                    'replacement': r'\1\2***TOKEN_REDACTED***',
                    'confidence': 0.90,
                    'description': 'Authentication tokens'
                },
                {
                    'name': 'bearer_tokens',
                    'pattern': r'Bearer\s+[A-Za-z0-9\-_\.]+',
                    'replacement': 'Bearer ***BEARER_TOKEN_REDACTED***',
                    'confidence': 0.99,
                    'description': 'Bearer authentication tokens'
                },
                {
                    'name': 'basic_auth',
                    'pattern': r'Basic\s+[A-Za-z0-9+/]+=*',
                    'replacement': 'Basic ***BASIC_AUTH_REDACTED***',
                    'confidence': 0.99,
                    'description': 'Basic authentication headers'
                },
                {
                    'name': 'jwt_tokens',
                    'pattern': r'eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_.]+',
                    'replacement': 'eyJ***JWT_TOKEN_REDACTED***',
                    'confidence': 0.95,
                    'description': 'JWT tokens'
                }
            ],
            
            'pii': [
                {
                    'name': 'email_addresses',
                    'pattern': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'replacement': '***EMAIL_REDACTED***',
                    'confidence': 0.92,
                    'description': 'Email addresses'
                },
                {
                    'name': 'ssn',
                    'pattern': r'\b\d{3}-\d{2}-\d{4}\b',
                    'replacement': '***SSN_REDACTED***',
                    'confidence': 0.95,
                    'description': 'Social Security Numbers'
                },
                {
                    'name': 'phone_numbers',
                    'pattern': r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',
                    'replacement': '***PHONE_REDACTED***',
                    'confidence': 0.85,
                    'description': 'Phone numbers'
                },
                {
                    'name': 'credit_cards',
                    'pattern': r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',
                    'replacement': '***CREDIT_CARD_REDACTED***',
                    'confidence': 0.90,
                    'description': 'Credit card numbers'
                }
            ],
            
            'network': [
                {
                    'name': 'ip_addresses',
                    'pattern': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
                    'replacement': '***IP_REDACTED***',
                    'confidence': 0.85,
                    'description': 'IP addresses'
                },
                {
                    'name': 'mac_addresses',
                    'pattern': r'\b[0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}[:-][0-9A-Fa-f]{2}\b',
                    'replacement': '***MAC_ADDRESS_REDACTED***',
                    'confidence': 0.95,
                    'description': 'MAC addresses'
                },
                {
                    'name': 'private_keys',
                    'pattern': r'-----BEGIN [A-Z ]+-----.*?-----END [A-Z ]+-----',
                    'replacement': '-----BEGIN PRIVATE KEY-----\n***PRIVATE_KEY_REDACTED***\n-----END PRIVATE KEY-----',
                    'confidence': 0.99,
                    'description': 'Private keys and certificates'
                }
            ],
            
            'database': [
                {
                    'name': 'postgres_urls',
                    'pattern': r'postgres://[^@\s]+@[^/\s]+/\w+',
                    'replacement': 'postgres://***USER_REDACTED***@***HOST_REDACTED***/***DB_REDACTED***',
                    'confidence': 0.95,
                    'description': 'PostgreSQL connection strings'
                },
                {
                    'name': 'mysql_urls', 
                    'pattern': r'mysql://[^@\s]+@[^/\s]+/\w+',
                    'replacement': 'mysql://***USER_REDACTED***@***HOST_REDACTED***/***DB_REDACTED***',
                    'confidence': 0.95,
                    'description': 'MySQL connection strings'
                },
                {
                    'name': 'mongodb_urls',
                    'pattern': r'mongodb://[^@\s]+@[^/\s]+/\w+',
                    'replacement': 'mongodb://***USER_REDACTED***@***HOST_REDACTED***/***DB_REDACTED***',
                    'confidence': 0.95,
                    'description': 'MongoDB connection strings'
                }
            ],
            
            'sting_specific': [
                {
                    'name': 'kratos_secrets',
                    'pattern': r'(kratos[_-]?secret|cookie[_-]?secret)([=:\s]+)[^\s\n\r]+',
                    'replacement': r'\1\2***KRATOS_SECRET_REDACTED***',
                    'confidence': 0.95,
                    'description': 'Kratos-specific secrets'
                },
                {
                    'name': 'vault_tokens',
                    'pattern': r'(vault[_-]?token|hvs\.[A-Za-z0-9]+)',
                    'replacement': '***VAULT_TOKEN_REDACTED***',
                    'confidence': 0.95,
                    'description': 'HashiCorp Vault tokens'
                },
                {
                    'name': 'session_tokens',
                    'pattern': r'(session[_-]?id|sessionid)([=:\s]+)[^\s\n\r]+',
                    'replacement': r'\1\2***SESSION_REDACTED***',
                    'confidence': 0.90,
                    'description': 'Session identifiers'
                }
            ]
        }
    
    def _initialize_realtime_patterns(self) -> List[Tuple[str, str]]:
        """Initialize patterns for real-time log streaming sanitization"""
        return [
            # High-priority patterns for real-time processing
            (r'password[=:\s]+[^\s\n]+', 'password=***REDACTED***'),
            (r'token[=:\s]+[^\s\n]+', 'token=***REDACTED***'),
            (r'Bearer\s+[A-Za-z0-9\-_]+', 'Bearer ***REDACTED***'),
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***EMAIL***'),
            (r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '***IP***'),
        ]
    
    def sanitize_content(self, content: str, context: str = 'general') -> Tuple[str, Dict]:
        """
        Sanitize content and return sanitized version with statistics
        
        Args:
            content: Raw content to sanitize
            context: Context for tailored sanitization ('logs', 'config', 'api', etc.)
            
        Returns:
            Tuple of (sanitized_content, sanitization_stats)
        """
        original_length = len(content)
        sanitized_content = content
        matches_found = {}
        
        # Apply pattern groups based on context
        pattern_groups = self._get_patterns_for_context(context)
        
        for group_name in pattern_groups:
            if group_name not in self.patterns:
                continue
                
            group_matches = 0
            for pattern_info in self.patterns[group_name]:
                pattern = pattern_info['pattern']
                replacement = pattern_info['replacement']
                
                # Apply pattern and count matches
                new_content, match_count = re.subn(
                    pattern, replacement, sanitized_content, flags=re.IGNORECASE | re.MULTILINE | re.DOTALL
                )
                
                if match_count > 0:
                    sanitized_content = new_content
                    group_matches += match_count
                    self.stats['patterns_matched'] += match_count
                    
                    # Track by category
                    category_key = f"{group_name}_instances"
                    if category_key in self.stats:
                        self.stats[category_key] += match_count
            
            if group_matches > 0:
                matches_found[group_name] = group_matches
        
        # Update stats
        bytes_redacted = original_length - len(sanitized_content)
        self.stats['bytes_redacted'] += bytes_redacted
        
        sanitization_stats = {
            'original_size': original_length,
            'sanitized_size': len(sanitized_content),
            'bytes_redacted': bytes_redacted,
            'patterns_matched': matches_found,
            'sanitization_effectiveness': len(matches_found) > 0
        }
        
        return sanitized_content, sanitization_stats
    
    def sanitize_file(self, file_path: str, output_path: Optional[str] = None) -> Dict:
        """
        Sanitize a file and optionally save to new location
        
        Args:
            file_path: Path to file to sanitize
            output_path: Optional output path (default: add .sanitized suffix)
            
        Returns:
            Dictionary with sanitization results
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return {'success': False, 'error': str(e)}
        
        # Determine context from file extension/path
        context = self._determine_file_context(file_path)
        
        # Sanitize content
        sanitized_content, stats = self.sanitize_content(content, context)
        
        # Determine output path
        if not output_path:
            path_obj = Path(file_path)
            output_path = str(path_obj.with_suffix(f'.sanitized{path_obj.suffix}'))
        
        # Write sanitized content
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(sanitized_content)
        except Exception as e:
            logger.error(f"Failed to write sanitized file {output_path}: {e}")
            return {'success': False, 'error': str(e)}
        
        self.stats['files_processed'] += 1
        
        return {
            'success': True,
            'input_file': file_path,
            'output_file': output_path,
            'context': context,
            'stats': stats
        }
    
    def sanitize_realtime(self, log_line: str) -> str:
        """
        Fast sanitization for real-time log streaming
        
        Args:
            log_line: Single log line to sanitize
            
        Returns:
            Sanitized log line
        """
        sanitized_line = log_line
        
        for pattern, replacement in self.realtime_patterns:
            sanitized_line = re.sub(pattern, replacement, sanitized_line, flags=re.IGNORECASE)
        
        return sanitized_line
    
    def create_promtail_config(self, output_path: str) -> str:
        """
        Generate Promtail configuration with sanitization pipeline stages
        
        Args:
            output_path: Path to write the Promtail config
            
        Returns:
            Path to generated config file
        """
        promtail_config = {
            "server": {
                "http_listen_port": 9080,
                "grpc_listen_port": 0
            },
            "positions": {
                "filename": "/tmp/positions.yaml"
            },
            "clients": [{
                "url": "http://loki:3100/loki/api/v1/push"
            }],
            "scrape_configs": [{
                "job_name": "sting-sanitized-logs",
                "static_configs": [{
                    "targets": ["localhost"],
                    "labels": {
                        "job": "sting-logs",
                        "sanitized": "true",
                        "__path__": "/var/log/sting/*.log"
                    }
                }],
                "pipeline_stages": self._generate_promtail_pipeline_stages()
            }]
        }
        
        with open(output_path, 'w') as f:
            json.dump(promtail_config, f, indent=2)
        
        logger.info(f"Generated sanitized Promtail config: {output_path}")
        return output_path
    
    def _generate_promtail_pipeline_stages(self) -> List[Dict]:
        """Generate Promtail pipeline stages for log sanitization"""
        stages = []
        
        # Add sanitization stages for high-priority patterns
        for pattern, replacement in self.realtime_patterns[:5]:  # Top 5 patterns
            stages.append({
                "regex": {
                    "expression": f"(?P<sanitized>{pattern})"
                }
            })
            stages.append({
                "template": {
                    "source": "sanitized", 
                    "template": replacement
                }
            })
        
        return stages
    
    def _get_patterns_for_context(self, context: str) -> List[str]:
        """Get appropriate pattern groups for given context"""
        context_mapping = {
            'logs': ['credentials', 'pii', 'network', 'sting_specific'],
            'config': ['credentials', 'database', 'sting_specific'],
            'api': ['credentials', 'pii', 'network'],
            'database': ['credentials', 'database', 'pii'],
            'general': ['credentials', 'pii', 'network', 'database', 'sting_specific']
        }
        
        return context_mapping.get(context, context_mapping['general'])
    
    def _determine_file_context(self, file_path: str) -> str:
        """Determine sanitization context from file path"""
        path_lower = file_path.lower()
        
        if 'config' in path_lower or '.yml' in path_lower or '.yaml' in path_lower:
            return 'config'
        elif 'log' in path_lower:
            return 'logs'
        elif 'api' in path_lower or 'request' in path_lower:
            return 'api'
        elif 'database' in path_lower or 'db' in path_lower or 'sql' in path_lower:
            return 'database'
        else:
            return 'general'
    
    def _load_custom_config(self, config_path: str):
        """Load custom sanitization patterns from config file"""
        try:
            with open(config_path, 'r') as f:
                custom_config = json.load(f)
            
            # Merge custom patterns
            if 'patterns' in custom_config:
                for group, patterns in custom_config['patterns'].items():
                    if group in self.patterns:
                        self.patterns[group].extend(patterns)
                    else:
                        self.patterns[group] = patterns
            
            logger.info(f"Loaded custom sanitization config from {config_path}")
            
        except Exception as e:
            logger.error(f"Failed to load custom config {config_path}: {e}")
    
    def get_sanitization_report(self) -> Dict:
        """Generate comprehensive sanitization report"""
        return {
            'timestamp': datetime.now().isoformat(),
            'statistics': self.stats.copy(),
            'patterns_available': {
                group: len(patterns) for group, patterns in self.patterns.items()
            },
            'realtime_patterns': len(self.realtime_patterns),
            'effectiveness_score': self._calculate_effectiveness_score()
        }
    
    def _calculate_effectiveness_score(self) -> float:
        """Calculate sanitization effectiveness score (0.0-1.0)"""
        if self.stats['files_processed'] == 0:
            return 0.0
        
        # Simple effectiveness based on patterns matched vs files processed
        patterns_per_file = self.stats['patterns_matched'] / self.stats['files_processed']
        
        # Normalize to 0-1 scale (assume 5+ patterns per file = highly effective)
        return min(patterns_per_file / 5.0, 1.0)


def create_sanitization_config_template() -> Dict:
    """Create a template configuration file for custom sanitization rules"""
    return {
        "description": "Custom sanitization patterns for STING support system",
        "version": "1.0",
        "patterns": {
            "custom_credentials": [
                {
                    "name": "custom_api_key",
                    "pattern": r"myservice_key[=:\s]+[^\s\n\r]+",
                    "replacement": "myservice_key=***CUSTOM_KEY_REDACTED***",
                    "confidence": 0.95,
                    "description": "Custom service API keys"
                }
            ],
            "custom_identifiers": [
                {
                    "name": "employee_ids",
                    "pattern": r"EMP\d{6}",
                    "replacement": "***EMPLOYEE_ID_REDACTED***",
                    "confidence": 0.90,
                    "description": "Employee identification numbers"
                }
            ]
        },
        "realtime_patterns": [
            ("custom_pattern_here", "***REDACTED***")
        ]
    }


if __name__ == "__main__":
    # Example usage
    filter = EnhancedPollenFilter()
    
    test_content = """
    2025-01-12 10:30:00 INFO Starting authentication with user admin@company.com
    2025-01-12 10:30:01 DEBUG password=secretpassword123 api_key=abc123xyz
    2025-01-12 10:30:02 INFO Connected to postgres://user:pass@db.company.com/sting_app
    2025-01-12 10:30:03 DEBUG Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiYWRtaW4iOnRydWV9.TJVA95OrM7E2cBab30RMHrHDcEfxjoYZgeFONFh7HgQ
    2025-01-12 10:30:04 ERROR Connection failed for 192.168.1.100:5432
    """
    
    sanitized, stats = filter.sanitize_content(test_content, 'logs')
    
    print("Original content:")
    print(test_content)
    print("\nSanitized content:")  
    print(sanitized)
    print(f"\nSanitization stats:")
    print(json.dumps(stats, indent=2))
    print(f"\nOverall filter stats:")
    print(json.dumps(filter.get_sanitization_report(), indent=2))