#!/usr/bin/env python3

"""
🧹 STING Pollen Filter - Sensitive Data Sanitization
Removes "toxic pollen" (sensitive data) from honey jars while preserving diagnostic value
"""

import re
import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import mimetypes

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='🧹 [%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class PollenFilter:
    """
    The Pollen Filter removes sensitive information from diagnostic bundles
    while preserving the structure and diagnostic value of logs.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        self.stats = {
            'files_processed': 0,
            'files_filtered': 0,
            'patterns_matched': 0,
            'bytes_filtered': 0
        }
        
        # Default sensitive data patterns
        self.patterns = self._get_default_patterns()
        
        # Load custom patterns if config file provided
        if config_file and os.path.exists(config_file):
            self._load_config(config_file)
    
    def _get_default_patterns(self) -> Dict[str, List[Dict]]:
        """
        Define default patterns for sensitive data detection.
        Each pattern has: regex, replacement, description, confidence
        """
        return {
            'secrets': [
                {
                    'regex': r'([Pp]assword[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement': r'\1[FILTERED-PASSWORD]',
                    'description': 'Password fields',
                    'confidence': 'high'
                },
                {
                    'regex': r'([Aa]pi[_-]?[Kk]ey[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement': r'\1[FILTERED-API-KEY]',
                    'description': 'API keys',
                    'confidence': 'high'
                },
                {
                    'regex': r'([Tt]oken[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement': r'\1[FILTERED-TOKEN]',
                    'description': 'Authentication tokens',
                    'confidence': 'high'
                },
                {
                    'regex': r'([Ss]ecret[s]?[[:space:]]*[=:][[:space:]]*)([^\s\'"]+)',
                    'replacement': r'\1[FILTERED-SECRET]',
                    'description': 'Secret values',
                    'confidence': 'high'
                },
                {
                    'regex': r'([Kk]ey[s]?[[:space:]]*[=:][[:space:]]*)([A-Za-z0-9+/]{20,})',
                    'replacement': r'\1[FILTERED-KEY]',
                    'description': 'Generic keys',
                    'confidence': 'medium'
                },
                {
                    'regex': r'(Bearer[[:space:]]+)([A-Za-z0-9\-._~+/]+)',
                    'replacement': r'\1[FILTERED-BEARER-TOKEN]',
                    'description': 'Bearer tokens',
                    'confidence': 'high'
                }
            ],
            'database': [
                {
                    'regex': r'(postgresql://[^:]+:)([^@]+)(@.+)',
                    'replacement': r'\1[FILTERED-DB-PASSWORD]\3',
                    'description': 'PostgreSQL connection strings',
                    'confidence': 'high'
                },
                {
                    'regex': r'(mysql://[^:]+:)([^@]+)(@.+)',
                    'replacement': r'\1[FILTERED-DB-PASSWORD]\3',
                    'description': 'MySQL connection strings',
                    'confidence': 'high'
                },
                {
                    'regex': r'(mongodb://[^:]+:)([^@]+)(@.+)',
                    'replacement': r'\1[FILTERED-DB-PASSWORD]\3',
                    'description': 'MongoDB connection strings',
                    'confidence': 'high'
                }
            ],
            'personal_info': [
                {
                    'regex': r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                    'replacement': '[FILTERED-EMAIL]',
                    'description': 'Email addresses',
                    'confidence': 'medium'
                },
                {
                    'regex': r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
                    'replacement': '[FILTERED-PHONE]',
                    'description': 'Phone numbers',
                    'confidence': 'medium'
                },
                {
                    'regex': r'\b\d{3}-\d{2}-\d{4}\b',
                    'replacement': '[FILTERED-SSN]',
                    'description': 'SSN patterns',
                    'confidence': 'high'
                }
            ],
            'network': [
                {
                    'regex': r'\b(?:10\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b',
                    'replacement': '[FILTERED-PRIVATE-IP]',
                    'description': 'Private IP addresses (10.x.x.x)',
                    'confidence': 'low'
                },
                {
                    'regex': r'\b(?:172\.(?:1[6-9]|2[0-9]|3[01])\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b',
                    'replacement': '[FILTERED-PRIVATE-IP]',
                    'description': 'Private IP addresses (172.x.x.x)',
                    'confidence': 'low'
                },
                {
                    'regex': r'\b(?:192\.168\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\b',
                    'replacement': '[FILTERED-PRIVATE-IP]',
                    'description': 'Private IP addresses (192.168.x.x)',
                    'confidence': 'low'
                }
            ],
            'certificates': [
                {
                    'regex': r'-----BEGIN [A-Z ]+-----[\s\S]*?-----END [A-Z ]+-----',
                    'replacement': '[FILTERED-CERTIFICATE-DATA]',
                    'description': 'PEM certificate data',
                    'confidence': 'high'
                },
                {
                    'regex': r'([Cc]ert[ifi]*[cate]*[[:space:]]*[=:][[:space:]]*)([A-Za-z0-9+/]{50,})',
                    'replacement': r'\1[FILTERED-CERT]',
                    'description': 'Certificate values',
                    'confidence': 'medium'
                }
            ],
            'hashes': [
                {
                    'regex': r'\b[a-fA-F0-9]{64}\b',
                    'replacement': '[FILTERED-SHA256]',
                    'description': 'SHA256 hashes',
                    'confidence': 'medium'
                },
                {
                    'regex': r'\b[a-fA-F0-9]{40}\b',
                    'replacement': '[FILTERED-SHA1]',
                    'description': 'SHA1 hashes',
                    'confidence': 'medium'
                },
                {
                    'regex': r'\b[a-fA-F0-9]{32}\b',
                    'replacement': '[FILTERED-MD5]',
                    'description': 'MD5 hashes',
                    'confidence': 'low'
                }
            ]
        }
    
    def _load_config(self, config_file: str):
        """Load custom filtering configuration"""
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                
            if 'patterns' in config:
                # Merge custom patterns with defaults
                for category, patterns in config['patterns'].items():
                    if category in self.patterns:
                        self.patterns[category].extend(patterns)
                    else:
                        self.patterns[category] = patterns
                        
            logger.info(f"Loaded custom patterns from {config_file}")
            
        except Exception as e:
            logger.warning(f"Failed to load config {config_file}: {e}")
    
    def _is_text_file(self, file_path: str) -> bool:
        """Determine if file is likely to contain text that should be filtered"""
        try:
            # Check by extension first
            text_extensions = {
                '.log', '.txt', '.yml', '.yaml', '.json', '.env', 
                '.conf', '.config', '.ini', '.properties', '.sh'
            }
            
            if any(file_path.lower().endswith(ext) for ext in text_extensions):
                return True
            
            # Use mimetypes for additional detection
            mime_type, _ = mimetypes.guess_type(file_path)
            if mime_type and mime_type.startswith('text/'):
                return True
            
            # Try to read first few bytes to detect text
            with open(file_path, 'rb') as f:
                chunk = f.read(512)
                
            # If it's mostly printable ASCII, treat as text
            try:
                chunk.decode('utf-8')
                # Check if it contains mostly printable characters
                printable_ratio = sum(32 <= b <= 126 or b in (9, 10, 13) for b in chunk) / len(chunk)
                return printable_ratio > 0.8
            except UnicodeDecodeError:
                return False
                
        except Exception:
            return False
    
    def _filter_content(self, content: str, file_path: str) -> Tuple[str, int]:
        """
        Filter sensitive content from a string.
        Returns (filtered_content, number_of_matches)
        """
        filtered_content = content
        total_matches = 0
        
        for category, patterns in self.patterns.items():
            for pattern_info in patterns:
                regex = pattern_info['regex']
                replacement = pattern_info['replacement']
                
                try:
                    # Use re.MULTILINE and re.DOTALL for better matching
                    matches = re.findall(regex, filtered_content, re.MULTILINE | re.DOTALL)
                    if matches:
                        match_count = len(matches)
                        total_matches += match_count
                        
                        # Apply the replacement
                        filtered_content = re.sub(regex, replacement, filtered_content, flags=re.MULTILINE | re.DOTALL)
                        
                        logger.debug(f"Applied {category} filter to {file_path}: {match_count} matches ({pattern_info['description']})")
                        
                except re.error as e:
                    logger.warning(f"Invalid regex in {category}: {regex} - {e}")
                    continue
        
        return filtered_content, total_matches
    
    def filter_file(self, file_path: str) -> bool:
        """
        Filter a single file.
        Returns True if file was processed (regardless of whether changes were made)
        """
        try:
            if not self._is_text_file(file_path):
                logger.debug(f"Skipping binary file: {file_path}")
                return False
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    original_content = f.read()
            except UnicodeDecodeError:
                # Try with latin-1 encoding as fallback
                with open(file_path, 'r', encoding='latin-1') as f:
                    original_content = f.read()
            
            # Apply filtering
            filtered_content, match_count = self._filter_content(original_content, file_path)
            
            # Update statistics
            self.stats['files_processed'] += 1
            
            if match_count > 0:
                # Write filtered content back
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(filtered_content)
                
                self.stats['files_filtered'] += 1
                self.stats['patterns_matched'] += match_count
                self.stats['bytes_filtered'] += len(original_content) - len(filtered_content)
                
                logger.info(f"Filtered {file_path}: {match_count} sensitive patterns removed")
            else:
                logger.debug(f"No sensitive patterns found in {file_path}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error filtering {file_path}: {e}")
            return False
    
    def filter_directory(self, directory_path: str) -> bool:
        """
        Recursively filter all files in a directory.
        Returns True if successful
        """
        try:
            directory = Path(directory_path)
            if not directory.exists() or not directory.is_dir():
                logger.error(f"Directory not found: {directory_path}")
                return False
            
            logger.info(f"Starting pollen filtering in: {directory_path}")
            
            # Find all files to process
            all_files = []
            for file_path in directory.rglob('*'):
                if file_path.is_file():
                    all_files.append(str(file_path))
            
            logger.info(f"Found {len(all_files)} files to examine")
            
            # Process each file
            for file_path in all_files:
                try:
                    self.filter_file(file_path)
                except Exception as e:
                    logger.warning(f"Skipping {file_path}: {e}")
                    continue
            
            # Report statistics
            logger.info(f"Filtering complete:")
            logger.info(f"  Files examined: {len(all_files)}")
            logger.info(f"  Files processed: {self.stats['files_processed']}")
            logger.info(f"  Files with sensitive data: {self.stats['files_filtered']}")
            logger.info(f"  Total patterns matched: {self.stats['patterns_matched']}")
            logger.info(f"  Bytes filtered: {self.stats['bytes_filtered']}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error filtering directory {directory_path}: {e}")
            return False
    
    def test_patterns(self, test_data: Optional[str] = None) -> bool:
        """
        Test filtering patterns against sample data
        """
        if test_data is None:
            test_data = """
            # Test data for pollen filter validation
            password=secret123
            api_key=abcd1234567890efgh
            DATABASE_URL=postgresql://user:password123@localhost:5432/db
            email: user@example.com
            phone: +1-555-123-4567
            token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
            secret_key=super_secret_value_here
            bearer_token=Bearer abc123def456ghi789
            private_ip=192.168.1.100
            ssh_key=ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ...
            hash=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
            -----BEGIN CERTIFICATE-----
            MIIDXTCCAkWgAwIBAgIJAKMD1234567890
            -----END CERTIFICATE-----
            """
        
        logger.info("🧪 Testing pollen filter patterns...")
        
        filtered_content, match_count = self._filter_content(test_data, "test_data")
        
        print("\n=== ORIGINAL TEST DATA ===")
        print(test_data)
        
        print("\n=== FILTERED TEST DATA ===")
        print(filtered_content)
        
        print(f"\n=== RESULTS ===")
        print(f"Patterns matched: {match_count}")
        print(f"Bytes filtered: {len(test_data) - len(filtered_content)}")
        
        if match_count > 0:
            logger.info(f"✅ Filter test passed: {match_count} patterns detected and filtered")
            return True
        else:
            logger.warning("⚠️  Filter test: No patterns matched - check configuration")
            return False
    
    def generate_filter_report(self, output_file: str):
        """Generate a report of all available filtering patterns"""
        report = {
            'timestamp': str(os.path.getctime(__file__)),
            'total_categories': len(self.patterns),
            'total_patterns': sum(len(patterns) for patterns in self.patterns.values()),
            'categories': {}
        }
        
        for category, patterns in self.patterns.items():
            report['categories'][category] = {
                'pattern_count': len(patterns),
                'patterns': [
                    {
                        'description': p['description'],
                        'confidence': p['confidence'],
                        'regex_length': len(p['regex'])
                    }
                    for p in patterns
                ]
            }
        
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Filter pattern report saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="🧹 STING Pollen Filter - Remove sensitive data from diagnostic bundles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Filter a directory
  python3 pollen_filter.py /path/to/bundle

  # Test filtering patterns
  python3 pollen_filter.py --test

  # Generate pattern report
  python3 pollen_filter.py --report patterns_report.json

  # Use custom filter config
  python3 pollen_filter.py --config custom_filters.json /path/to/bundle
        """
    )
    
    parser.add_argument('path', nargs='?', help='Directory or file to filter')
    parser.add_argument('--config', help='Custom filter configuration file')
    parser.add_argument('--test', action='store_true', help='Test filter patterns')
    parser.add_argument('--report', help='Generate filter pattern report')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize filter
    filter_instance = PollenFilter(config_file=args.config)
    
    if args.test:
        # Run pattern tests
        success = filter_instance.test_patterns()
        sys.exit(0 if success else 1)
    
    if args.report:
        # Generate pattern report
        filter_instance.generate_filter_report(args.report)
        sys.exit(0)
    
    if not args.path:
        parser.print_help()
        print("\n❌ Error: No path specified for filtering")
        sys.exit(1)
    
    # Filter the specified path
    if os.path.isdir(args.path):
        success = filter_instance.filter_directory(args.path)
    elif os.path.isfile(args.path):
        success = filter_instance.filter_file(args.path)
    else:
        logger.error(f"Path not found: {args.path}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()