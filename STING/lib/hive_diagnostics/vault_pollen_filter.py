#!/usr/bin/env python3

"""
🧹 STING Vault-Aware Pollen Filter - Enterprise Log Sanitization
Removes "toxic pollen" (sensitive data) from logs and replaces with Vault references
for enterprise-grade observability while maintaining audit trails.
"""

import re
import os
import sys
import json
import argparse
import logging
import hashlib
import uuid
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
import mimetypes
from dataclasses import dataclass
from enum import Enum

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='🧹🔐 [%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class SensitivityLevel(Enum):
    """Data sensitivity classification"""
    LOW = "low"
    MEDIUM = "medium"  
    HIGH = "high"
    CRITICAL = "critical"

class VaultCategory(Enum):
    """Vault storage categories for different data types"""
    SECRETS = "secrets"
    AUTH = "auth" 
    PII = "pii"
    DATABASE = "db"
    CONVERSATIONS = "conversations"
    NETWORK = "network"
    SYSTEM = "system"

@dataclass
class VaultReference:
    """Represents a Vault reference for sanitized data"""
    category: VaultCategory
    field: str
    hash_value: str
    sensitivity: SensitivityLevel
    
    def to_vault_ref(self) -> str:
        """Generate Vault reference string"""
        return f"<VAULT_REF:sting/data/{self.category.value}/{self.field}:{self.hash_value}>"
    
    def to_audit_entry(self) -> Dict[str, Any]:
        """Generate audit log entry"""
        return {
            "vault_category": self.category.value,
            "field_name": self.field,
            "hash_value": self.hash_value,
            "sensitivity_level": self.sensitivity.value,
            "reference_id": self.hash_value[:16]
        }

class VaultPollenFilter:
    """
    Enhanced Pollen Filter with Vault-aware sanitization capabilities.
    Replaces sensitive data with Vault references while maintaining audit trails.
    """
    
    def __init__(self, config_file: Optional[str] = None, vault_enabled: bool = True):
        self.vault_enabled = vault_enabled
        self.stats = {
            'files_processed': 0,
            'files_filtered': 0,
            'patterns_matched': 0,
            'vault_references_created': 0,
            'bytes_filtered': 0,
            'audit_entries': []
        }
        
        # Vault reference tracking
        self.vault_references: Dict[str, VaultReference] = {}
        self.reference_cache: Dict[str, str] = {}
        
        # Enhanced sensitive data patterns with Vault categorization
        self.patterns = self._get_vault_aware_patterns()
        
        # Load custom patterns if config file provided
        if config_file and os.path.exists(config_file):
            self._load_config(config_file)
    
    def _get_vault_aware_patterns(self) -> Dict[str, List[Dict]]:
        """
        Define Vault-aware patterns for sensitive data detection.
        Each pattern includes vault_category and sensitivity_level.
        """
        return {
            'authentication_secrets': [
                {
                    'regex': r'([Pp]assword[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.AUTH, "password", SensitivityLevel.CRITICAL
                    ),
                    'description': 'Password fields',
                    'vault_category': VaultCategory.AUTH,
                    'sensitivity': SensitivityLevel.CRITICAL
                },
                {
                    'regex': r'([Aa]pi[_-]?[Kk]ey[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.SECRETS, "api_key", SensitivityLevel.HIGH
                    ),
                    'description': 'API keys',
                    'vault_category': VaultCategory.SECRETS,
                    'sensitivity': SensitivityLevel.HIGH
                },
                {
                    'regex': r'([Tt]oken[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.AUTH, "token", SensitivityLevel.HIGH
                    ),
                    'description': 'Authentication tokens',
                    'vault_category': VaultCategory.AUTH,
                    'sensitivity': SensitivityLevel.HIGH
                },
                {
                    'regex': r'([Ss]ecret[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.SECRETS, "secret", SensitivityLevel.CRITICAL
                    ),
                    'description': 'Secret values',
                    'vault_category': VaultCategory.SECRETS,
                    'sensitivity': SensitivityLevel.CRITICAL
                },
                {
                    'regex': r'(Bearer[[:space:]]+)([A-Za-z0-9\-._~+/]+)',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.AUTH, "bearer_token", SensitivityLevel.HIGH
                    ),
                    'description': 'Bearer tokens',
                    'vault_category': VaultCategory.AUTH,
                    'sensitivity': SensitivityLevel.HIGH
                },
                {
                    'regex': r'("session_token"[[:space:]]*:[[:space:]]*")([^"]+)(")',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.AUTH, "session_token", SensitivityLevel.HIGH
                    ),
                    'description': 'Session tokens in JSON',
                    'vault_category': VaultCategory.AUTH,
                    'sensitivity': SensitivityLevel.HIGH
                },
                {
                    'regex': r'("csrf_token"[[:space:]]*:[[:space:]]*")([^"]+)(")',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.AUTH, "csrf_token", SensitivityLevel.MEDIUM
                    ),
                    'description': 'CSRF tokens in JSON',
                    'vault_category': VaultCategory.AUTH,
                    'sensitivity': SensitivityLevel.MEDIUM
                }
            ],
            'database_credentials': [
                {
                    'regex': r'(postgresql://[^:]+:)([^@]+)(@.+)',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.DATABASE, "postgres_password", SensitivityLevel.CRITICAL
                    ),
                    'description': 'PostgreSQL connection strings',
                    'vault_category': VaultCategory.DATABASE,
                    'sensitivity': SensitivityLevel.CRITICAL
                },
                {
                    'regex': r'(mysql://[^:]+:)([^@]+)(@.+)',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.DATABASE, "mysql_password", SensitivityLevel.CRITICAL
                    ),
                    'description': 'MySQL connection strings',
                    'vault_category': VaultCategory.DATABASE,
                    'sensitivity': SensitivityLevel.CRITICAL
                },
                {
                    'regex': r'(VALUES \()([^)]+)(\))',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.DATABASE, "query_values", SensitivityLevel.MEDIUM
                    ),
                    'description': 'SQL INSERT values',
                    'vault_category': VaultCategory.DATABASE,
                    'sensitivity': SensitivityLevel.MEDIUM
                },
                {
                    'regex': r"(= ')([^']+)(')",
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.DATABASE, "param_value", SensitivityLevel.MEDIUM
                    ),
                    'description': 'SQL parameter values',
                    'vault_category': VaultCategory.DATABASE,
                    'sensitivity': SensitivityLevel.MEDIUM
                }
            ],
            'personal_identifiable_info': [
                {
                    'regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(0), VaultCategory.PII, "email_hash", SensitivityLevel.HIGH
                    ),
                    'description': 'Email addresses',
                    'vault_category': VaultCategory.PII,
                    'sensitivity': SensitivityLevel.HIGH
                },
                {
                    'regex': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(0), VaultCategory.PII, "phone_hash", SensitivityLevel.HIGH
                    ),
                    'description': 'Phone numbers',
                    'vault_category': VaultCategory.PII,
                    'sensitivity': SensitivityLevel.HIGH
                },
                {
                    'regex': r'\b\d{3}-\d{2}-\d{4}\b',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(0), VaultCategory.PII, "ssn_hash", SensitivityLevel.CRITICAL
                    ),
                    'description': 'SSN patterns',
                    'vault_category': VaultCategory.PII,
                    'sensitivity': SensitivityLevel.CRITICAL
                },
                {
                    'regex': r'\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(0), VaultCategory.PII, "credit_card_hash", SensitivityLevel.CRITICAL
                    ),
                    'description': 'Credit card numbers',
                    'vault_category': VaultCategory.PII,
                    'sensitivity': SensitivityLevel.CRITICAL
                }
            ],
            'conversation_data': [
                {
                    'regex': r'("user_message"[[:space:]]*:[[:space:]]*")([^"]+)(")',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.CONVERSATIONS, "user_message_hash", SensitivityLevel.HIGH
                    ),
                    'description': 'User messages in conversations',
                    'vault_category': VaultCategory.CONVERSATIONS,
                    'sensitivity': SensitivityLevel.HIGH
                },
                {
                    'regex': r'("bot_response"[[:space:]]*:[[:space:]]*")([^"]+)(")',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(2), VaultCategory.CONVERSATIONS, "bot_response_hash", SensitivityLevel.MEDIUM
                    ),
                    'description': 'Bot responses in conversations',
                    'vault_category': VaultCategory.CONVERSATIONS,
                    'sensitivity': SensitivityLevel.MEDIUM
                }
            ],
            'network_security': [
                {
                    'regex': r'\b(?:10\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(0), VaultCategory.NETWORK, "private_ip_hash", SensitivityLevel.LOW
                    ),
                    'description': 'Private IP addresses (10.x.x.x)',
                    'vault_category': VaultCategory.NETWORK,
                    'sensitivity': SensitivityLevel.LOW
                },
                {
                    'regex': r'\b(?:172\.(?:1[6-9]|2[0-9]|3[01])\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b',
                    'replacement_func': lambda m: self._create_vault_reference(
                        m.group(0), VaultCategory.NETWORK, "private_ip_hash", SensitivityLevel.LOW
                    ),
                    'description': 'Private IP addresses (172.x.x.x)',
                    'vault_category': VaultCategory.NETWORK,
                    'sensitivity': SensitivityLevel.LOW
                }
            ]
        }
    
    def _create_vault_reference(self, sensitive_data: str, category: VaultCategory, 
                              field: str, sensitivity: SensitivityLevel) -> str:
        """
        Create a Vault reference for sensitive data.
        Returns the Vault reference string to replace the sensitive data.
        """
        if not self.vault_enabled:
            # Fallback to simple filtering if Vault is disabled
            return f"[FILTERED-{field.upper()}]"
        
        # Create deterministic hash for the sensitive data
        hash_value = hashlib.sha256(sensitive_data.encode()).hexdigest()[:16]
        
        # Check if we already have a reference for this data
        cache_key = f"{category.value}:{field}:{hash_value}"
        if cache_key in self.reference_cache:
            return self.reference_cache[cache_key]
        
        # Create new Vault reference
        vault_ref = VaultReference(
            category=category,
            field=field,
            hash_value=hash_value,
            sensitivity=sensitivity
        )
        
        # Store for tracking and audit
        self.vault_references[cache_key] = vault_ref
        vault_ref_string = vault_ref.to_vault_ref()
        self.reference_cache[cache_key] = vault_ref_string
        
        # Add to audit trail
        self.stats['audit_entries'].append(vault_ref.to_audit_entry())
        self.stats['vault_references_created'] += 1
        
        logger.debug(f"Created Vault reference for {category.value}.{field}: {hash_value[:8]}...")
        return vault_ref_string
    
    def filter_content(self, content: str, file_path: str = "") -> Tuple[str, bool]:
        """
        Filter content and replace sensitive data with Vault references.
        Returns tuple of (filtered_content, was_modified).
        """
        original_content = content
        modified = False
        
        for category_name, pattern_list in self.patterns.items():
            for pattern_info in pattern_list:
                regex = pattern_info['regex']
                
                # Check if pattern uses replacement function (Vault-aware)
                if 'replacement_func' in pattern_info:
                    def replacer(match):
                        nonlocal modified
                        modified = True
                        self.stats['patterns_matched'] += 1
                        # Get the replacement parts
                        replacement = pattern_info['replacement_func'](match)
                        # Rebuild the full replacement maintaining structure
                        if match.groups():
                            # Preserve non-sensitive parts
                            result = ""
                            group_index = 1
                            for i, group in enumerate(match.groups(), 1):
                                if i == 2:  # Assuming sensitive data is always in group 2
                                    result += replacement
                                else:
                                    result += group if group is not None else ""
                            return result
                        else:
                            return replacement
                    
                    content = re.sub(regex, replacer, content)
                else:
                    # Fallback to simple replacement
                    matches = re.findall(regex, content)
                    if matches:
                        modified = True
                        self.stats['patterns_matched'] += len(matches)
                        content = re.sub(regex, pattern_info.get('replacement', '[FILTERED]'), content)
        
        # Update stats
        if modified:
            self.stats['bytes_filtered'] += len(original_content) - len(content)
            self.stats['files_filtered'] += 1
            logger.debug(f"Filtered content in {file_path}: {self.stats['patterns_matched']} patterns matched")
        
        return content, modified
    
    def filter_file(self, file_path: str, output_path: Optional[str] = None) -> bool:
        """
        Filter a single file and optionally save to output path.
        Returns True if file was modified.
        """
        try:
            file_path = Path(file_path)
            self.stats['files_processed'] += 1
            
            # Skip binary files
            mime_type, _ = mimetypes.guess_type(str(file_path))
            if mime_type and not mime_type.startswith('text/'):
                logger.debug(f"Skipping binary file: {file_path}")
                return False
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
                return False
            
            # Filter content
            filtered_content, was_modified = self.filter_content(content, str(file_path))
            
            # Save filtered content
            if was_modified:
                output_file = output_path or file_path
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(filtered_content)
                logger.info(f"🧹 Filtered: {file_path}")
                return True
            else:
                logger.debug(f"No filtering needed: {file_path}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return False
    
    def filter_directory(self, directory_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Recursively filter all files in a directory.
        Returns statistics about the filtering operation.
        """
        directory = Path(directory_path)
        if not directory.exists() or not directory.is_dir():
            raise ValueError(f"Directory does not exist: {directory_path}")
        
        output_directory = Path(output_dir) if output_dir else directory
        results = {
            'total_files': 0,
            'filtered_files': 0,
            'skipped_files': 0,
            'errors': []
        }
        
        # Process all text files recursively
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                results['total_files'] += 1
                
                try:
                    # Determine output path if different directory
                    if output_dir:
                        relative_path = file_path.relative_to(directory)
                        output_file = output_directory / relative_path
                        output_file.parent.mkdir(parents=True, exist_ok=True)
                    else:
                        output_file = None
                    
                    # Filter the file
                    if self.filter_file(file_path, output_file):
                        results['filtered_files'] += 1
                    else:
                        results['skipped_files'] += 1
                        
                except Exception as e:
                    error_msg = f"Error processing {file_path}: {e}"
                    results['errors'].append(error_msg)
                    logger.error(error_msg)
        
        return results
    
    def generate_audit_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive audit report of the filtering operation.
        """
        return {
            'filtering_statistics': self.stats.copy(),
            'vault_references': [ref.to_audit_entry() for ref in self.vault_references.values()],
            'sensitivity_breakdown': self._get_sensitivity_breakdown(),
            'category_breakdown': self._get_category_breakdown(),
            'recommendations': self._generate_recommendations()
        }
    
    def _get_sensitivity_breakdown(self) -> Dict[str, int]:
        """Get breakdown of vault references by sensitivity level"""
        breakdown = {}
        for ref in self.vault_references.values():
            level = ref.sensitivity.value
            breakdown[level] = breakdown.get(level, 0) + 1
        return breakdown
    
    def _get_category_breakdown(self) -> Dict[str, int]:
        """Get breakdown of vault references by category"""
        breakdown = {}
        for ref in self.vault_references.values():
            category = ref.category.value
            breakdown[category] = breakdown.get(category, 0) + 1
        return breakdown
    
    def _generate_recommendations(self) -> List[str]:
        """Generate security recommendations based on filtering results"""
        recommendations = []
        
        # Check for high-sensitivity data
        critical_count = sum(1 for ref in self.vault_references.values() 
                           if ref.sensitivity == SensitivityLevel.CRITICAL)
        if critical_count > 0:
            recommendations.append(
                f"Found {critical_count} CRITICAL sensitivity items. "
                "Review log handling procedures for these data types."
            )
        
        # Check for PII
        pii_count = sum(1 for ref in self.vault_references.values() 
                       if ref.category == VaultCategory.PII)
        if pii_count > 0:
            recommendations.append(
                f"Detected {pii_count} PII items in logs. "
                "Consider implementing PII detection at log generation time."
            )
        
        # Check for authentication data
        auth_count = sum(1 for ref in self.vault_references.values() 
                        if ref.category == VaultCategory.AUTH)
        if auth_count > 0:
            recommendations.append(
                f"Found {auth_count} authentication-related items. "
                "Review authentication logging practices to avoid credential leakage."
            )
        
        return recommendations
    
    def save_audit_report(self, output_file: str) -> None:
        """Save the audit report to a file"""
        report = self.generate_audit_report()
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"📊 Audit report saved to: {output_file}")

def main():
    """Command-line interface for the Vault Pollen Filter"""
    parser = argparse.ArgumentParser(
        description="🧹🔐 STING Vault-Aware Pollen Filter - Enterprise Log Sanitization"
    )
    parser.add_argument('input', help='Input file or directory to filter')
    parser.add_argument('-o', '--output', help='Output file or directory')
    parser.add_argument('-c', '--config', help='Configuration file')
    parser.add_argument('--vault', action='store_true', default=True, 
                       help='Enable Vault-aware filtering (default: enabled)')
    parser.add_argument('--no-vault', dest='vault', action='store_false',
                       help='Disable Vault-aware filtering')
    parser.add_argument('--audit-report', help='Save audit report to file')
    parser.add_argument('-v', '--verbose', action='store_true', 
                       help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize filter
    filter_engine = VaultPollenFilter(config_file=args.config, vault_enabled=args.vault)
    
    try:
        input_path = Path(args.input)
        
        if input_path.is_file():
            # Filter single file
            logger.info(f"🧹 Filtering file: {input_path}")
            was_modified = filter_engine.filter_file(str(input_path), args.output)
            if was_modified:
                logger.info("✅ File filtering completed")
            else:
                logger.info("ℹ️ No sensitive data found")
        
        elif input_path.is_dir():
            # Filter directory
            logger.info(f"🧹 Filtering directory: {input_path}")
            results = filter_engine.filter_directory(str(input_path), args.output)
            
            # Display results
            logger.info(f"📊 Filtering Results:")
            logger.info(f"  Total files: {results['total_files']}")
            logger.info(f"  Filtered: {results['filtered_files']}")
            logger.info(f"  Skipped: {results['skipped_files']}")
            logger.info(f"  Errors: {len(results['errors'])}")
            
            if results['errors']:
                logger.warning("⚠️ Errors occurred:")
                for error in results['errors']:
                    logger.warning(f"  {error}")
        
        else:
            logger.error(f"❌ Input path does not exist: {input_path}")
            sys.exit(1)
        
        # Display stats
        stats = filter_engine.stats
        logger.info(f"🔐 Vault References Created: {stats['vault_references_created']}")
        logger.info(f"🔍 Patterns Matched: {stats['patterns_matched']}")
        logger.info(f"📝 Bytes Filtered: {stats['bytes_filtered']}")
        
        # Save audit report if requested
        if args.audit_report:
            filter_engine.save_audit_report(args.audit_report)
        
        logger.info("✅ Filtering operation completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()