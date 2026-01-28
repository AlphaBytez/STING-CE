#!/usr/bin/env python3
"""
Configuration check script for STING platform.
Ensures config.yml exists and provides speed optimization guidance.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the conf directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config_loader import check_config_exists, logger

def main():
    parser = argparse.ArgumentParser(description='Check and initialize STING configuration')
    parser.add_argument('--config-path', 
                       default='conf/config.yml',
                       help='Path to config.yml file (default: conf/config.yml)')
    parser.add_argument('--project-root',
                       default='.',
                       help='Project root directory (default: current directory)')
    parser.add_argument('--speed-tips',
                       action='store_true',
                       help='Show speed optimization tips')
    
    args = parser.parse_args()
    
    # Resolve paths
    project_root = Path(args.project_root).resolve()
    config_path = project_root / args.config_path
    
    print(f"🔍 Checking configuration at: {config_path}")
    
    # Check if config exists
    if not check_config_exists(str(config_path)):
        print("❌ Configuration check failed!")
        sys.exit(1)
    
    print("✅ Configuration check passed!")
    
    if args.speed_tips:
        show_speed_optimization_tips()
    
def show_speed_optimization_tips():
    """Display speed optimization guidance."""
    import platform
    is_macos = platform.system() == 'Darwin'
    
    print("\n" + "="*60)
    print("🚀 SPEED OPTIMIZATION TIPS")
    if is_macos:
        print("🍎 Apple Silicon Optimized")
    print("="*60)
    
    if is_macos:
        print("\n📱 Your macOS system can use these optimizations:")
        
        print("\n1️⃣  Apple Silicon Performance Profile (recommended):")
        print("   llm_service:")
        print("     performance:")
        print("       profile: \"apple_silicon\"      # Optimized for Mac")
        print("     hardware:")
        print("       device: \"mps\"                # Metal Performance Shaders")
        print("       precision: \"fp16\"            # Apple Silicon excels at fp16")
        
        print("\n2️⃣  Use the Mac-optimized speed preset:")
        print("   speed_preset: \"apple_silicon_balanced\"  # Already in config.yml.default.mac")
        
        print("\n3️⃣  Take advantage of unified memory:")
        print("   llm_service:")
        print("     model_lifecycle:")
        print("       max_loaded_models: 3         # Keep more models in memory")
        print("       preload_on_startup: true     # Load at startup")
        print("       idle_timeout: 180            # 3 hours (unified memory advantage)")
        
        print("\n4️⃣  Enhanced chatbot performance:")
        print("   chatbot:")
        print("     performance:")
        print("       max_concurrent_requests: 8   # Apple Silicon can handle more")
        print("       cache_ttl: 600               # 10-minute cache")
        print("       use_neural_engine: true      # Use Neural Engine if available")
        
        print("\n🍎 Apple Silicon Pro Tips:")
        print("   • MPS acceleration is automatic and highly optimized")
        print("   • fp16 operations are ~2x faster than fp32 on Apple Silicon")
        print("   • Unified memory allows keeping multiple models loaded")
        print("   • Neural Engine can accelerate certain operations")
        print("   • No quantization needed - Apple Silicon handles full models well")
        
        print("\n📋 Quick Setup for Mac:")
        print("   1. Use config.yml.default.mac as your template")
        print("   2. It comes pre-configured with apple_silicon_balanced preset")
        print("   3. Restart STING to apply optimizations")
        
    else:
        print("\n📝 Edit your config.yml file to optimize for speed:")
        
        print("\n1️⃣  Choose a Performance Profile:")
        print("   llm_service:")
        print("     performance:")
        print("       profile: \"speed_optimized\"  # For maximum speed")
        print("       # OR profile: \"vm_optimized\"   # For balanced speed/memory")
        
        print("\n2️⃣  Enable Model Preloading:")
        print("   llm_service:")
        print("     model_lifecycle:")
        print("       preload_on_startup: true     # Load models at startup")
        print("       development_mode: true       # Keep all models loaded")
        print("       idle_timeout: 0              # Never unload models")
        
        print("\n3️⃣  Use Speed Presets (uncomment in config.yml):")
        print("   # For maximum speed:")
        print("   speed_preset: \"maximum_speed\"")
        print("   ")
        print("   # For balanced performance:")
        print("   speed_preset: \"balanced\"")
        
        print("\n4️⃣  Chatbot-specific optimizations:")
        print("   chatbot:")
        print("     model: \"tinyllama\"              # Use fastest model")
        print("     performance:")
        print("       enable_response_cache: true   # Cache responses")
        print("       cache_ttl: 600                # Cache for 10 minutes")
        
        print("\n💡 Pro Tips:")
        print("   • More RAM = keep more models loaded simultaneously")
        print("   • SSD storage improves model loading times")
        print("   • CUDA/MPS acceleration automatically detected")
        print("   • int8 quantization reduces memory usage by ~75%")
    
    print("\n🔧 After editing config.yml, restart STING:")
    print("   ./manage_sting.sh restart")
    
    print("\n🎯 Available Configuration Templates:")
    print("   • config.yml.default     - General purpose")
    if is_macos:
        print("   • config.yml.default.mac - Apple Silicon optimized (recommended for you)")
    
    print("\n" + "="*60)

if __name__ == "__main__":
    main()