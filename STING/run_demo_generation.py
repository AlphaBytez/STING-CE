import sys
import os
import logging
from flask import Flask

# Add /opt/sting-ce to path
sys.path.append('/opt/sting-ce')

from app import create_app
from app.routes.demo_routes import _create_sample_documents, _create_comprehensive_honey_jars

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_generation():
    app = create_app()
    with app.app_context():
        print("Starting manual demo generation...")
        
        # 1. Ensure jars exist (idempotent-ish)
        print("Creating honey jars...")
        _create_comprehensive_honey_jars()
        
        # 2. Generate documents
        print("Generating documents (comprehensive)...")
        count = _create_sample_documents('comprehensive')
        print(f"Successfully created {count} documents.")

if __name__ == "__main__":
    run_generation()
