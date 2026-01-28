
import os
import sys
import logging
import requests
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add app directory to path
sys.path.append('/opt/sting-ce')

from app.services.honey_jar_service import HoneyJarService

def list_honey_jars():
    print("Listing Honey Jars...")
    service = HoneyJarService()
    
    headers = {"X-API-Key": service.api_key}
    try:
        response = requests.get(f"{service.knowledge_url}/honey-jars", headers=headers, timeout=10)
        if response.status_code == 200:
            jars = response.json()
            print(f"Found {len(jars)} honey jars:")
            for jar in jars:
                print(f"- {jar.get('name')} (ID: {jar.get('id')})")
        else:
            print(f"Failed to list jars: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"EXCEPTION: {e}")

if __name__ == "__main__":
    list_honey_jars()
