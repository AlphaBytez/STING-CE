
import os
import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add app directory to path
sys.path.append('/opt/sting-ce')

from app.services.honey_jar_service import HoneyJarService

def test_honey_jar_creation():
    print("Testing HoneyJarService...")
    service = HoneyJarService()
    print(f"Knowledge URL: {service.knowledge_url}")
    print(f"API Key: {service.api_key[:5]}...")

    try:
        jar_id = service.create_honey_jar(
            name="Test Jar from Script",
            description="Testing connectivity",
            jar_type="public",
            tags=["test"]
        )
        if jar_id:
            print(f"SUCCESS: Created jar with ID {jar_id}")
        else:
            print("FAILURE: Failed to create jar (returned None)")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    test_honey_jar_creation()
