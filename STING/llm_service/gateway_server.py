#!/usr/bin/env python3
"""
Gateway Server Entry Point
This starts the LLM Gateway service using the appropriate gateway app
"""

import os
import sys
import uvicorn

# Add the app directory to Python path
sys.path.insert(0, '/app')

# Import the appropriate gateway app
try:
    # Try to use main.py if it exists and has the app
    from gateway.main import app
    print("Using gateway/main.py")
except (ImportError, AttributeError):
    try:
        # Fall back to app.py
        from gateway.app import app
        print("Using gateway/app.py")
    except (ImportError, AttributeError) as e:
        print(f"Error: Could not import gateway app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    
    print(f"Starting LLM Gateway on {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.environ.get("LOG_LEVEL", "info").lower()
    )