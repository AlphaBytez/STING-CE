#!/usr/bin/env python3
"""
Wrapper script to properly generate configuration files.
This ensures load_config() is called before processing.
"""

import sys
import os
from config_loader import ConfigurationManager

def main():
    if len(sys.argv) < 2:
        print("Usage: generate_configs.py config.yml [--mode MODE]")
        return 1
    
    config_file = sys.argv[1]
    mode = 'development'
    
    # Parse mode if provided
    if '--mode' in sys.argv:
        mode_idx = sys.argv.index('--mode')
        if mode_idx + 1 < len(sys.argv):
            mode = sys.argv[mode_idx + 1]
    
    try:
        # Initialize manager
        manager = ConfigurationManager(config_file, mode=mode)
        
        # CRITICAL: Load the config file first!
        manager.load_config()
        
        # Process the config
        manager.process_config()
        
        # Generate env files
        manager.generate_env_file()
        
        print("Configuration generation completed successfully")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())