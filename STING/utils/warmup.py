#!/usr/bin/env python3
"""
Utils Container Dependency Warmup Script

This script pre-imports all critical Python dependencies when the utils
container starts. This ensures that when manage_sting.sh or other scripts
try to use the utils container, all dependencies are already loaded in memory
and ready to use.

This solves race conditions where the container is "running" but Python
packages aren't yet accessible.
"""

import sys
import time
from datetime import datetime

def log(message):
    """Log with timestamp"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}", flush=True)

def warmup_dependencies():
    """Preload all critical dependencies"""

    log("🔥 Starting dependency warmup...")
    start_time = time.time()

    dependencies = {
        'hvac': 'HashiCorp Vault client',
        'yaml': 'YAML configuration parsing',
        'requests': 'HTTP client library',
        'psycopg2': 'PostgreSQL database adapter',
        'cryptography': 'Cryptographic recipes',
        'jinja2': 'Template engine'
    }

    loaded = []
    failed = []

    for module, description in dependencies.items():
        try:
            __import__(module)
            loaded.append(f"✓ {module} ({description})")
        except ImportError as e:
            failed.append(f"✗ {module} ({description}): {e}")

    # Print results
    for dep in loaded:
        log(dep)

    if failed:
        log("❌ Failed to load some dependencies:")
        for dep in failed:
            log(dep)
        return False

    elapsed = time.time() - start_time
    log(f"✅ All dependencies loaded successfully in {elapsed:.2f}s")
    return True

def verify_readiness():
    """Verify container is ready for use"""

    log("🔍 Verifying container readiness...")

    checks = []

    # Check 1: Can import and use hvac
    try:
        import hvac
        checks.append("✓ HVAC client ready")
    except Exception as e:
        checks.append(f"✗ HVAC client error: {e}")
        return False

    # Check 2: Can import and use yaml
    try:
        import yaml
        test_data = yaml.safe_load("test: value")
        checks.append("✓ YAML parser ready")
    except Exception as e:
        checks.append(f"✗ YAML parser error: {e}")
        return False

    # Check 3: Can import and use requests
    try:
        import requests
        checks.append("✓ Requests library ready")
    except Exception as e:
        checks.append(f"✗ Requests library error: {e}")
        return False

    for check in checks:
        log(check)

    log("✅ Container is ready for use")
    return True

if __name__ == '__main__':
    log("=" * 60)
    log("Utils Container Startup Warmup")
    log("=" * 60)

    # Warmup phase
    if not warmup_dependencies():
        log("❌ Warmup failed - dependencies missing")
        sys.exit(1)

    # Verification phase
    if not verify_readiness():
        log("❌ Readiness verification failed")
        sys.exit(1)

    log("=" * 60)
    log("🎉 Utils container is fully operational")
    log("=" * 60)

    sys.exit(0)
