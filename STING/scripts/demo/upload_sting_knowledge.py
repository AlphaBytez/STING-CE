#!/usr/bin/env python3
"""
Upload STING Platform Knowledge to Honey Jar

This script packages and uploads the versioned STING platform documentation
to the default honey jar for AI-powered knowledge retrieval through Bee Chat.

Usage:
    python3 scripts/upload_sting_knowledge.py [options]
    
Options:
    --update        Update existing honey jar instead of creating new
    --version       Specify version (default: read from version.txt)
    --dry-run       Show what would be uploaded without actually doing it
"""

import os
import sys
import json
import requests
import time
from pathlib import Path
from datetime import datetime
import argparse
import warnings
import urllib3

# Suppress SSL warnings for self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def wait_for_knowledge_service(max_attempts=10, delay=5):
    """Wait for knowledge service to be available"""
    base_urls = [
        "http://localhost:8090",
        "http://knowledge:8090", 
        "http://sting-ce-knowledge:8090"
    ]
    
    for attempt in range(max_attempts):
        for base_url in base_urls:
            try:
                headers = {'X-API-Key': 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0'}
                health_response = requests.get(f"{base_url}/health", timeout=3, headers=headers)
                if health_response.status_code == 200:
                    print(f"✅ Knowledge service available at: {base_url}")
                    return base_url
            except:
                continue
        
        if attempt < max_attempts - 1:
            print(f"⏳ Waiting for knowledge service... ({attempt + 1}/{max_attempts})")
            time.sleep(delay)
    
    print("❌ Knowledge service not available after maximum attempts")
    return None

def load_manifest(knowledge_dir):
    """Load the manifest file"""
    manifest_path = knowledge_dir / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file not found: {manifest_path}")
    
    with open(manifest_path, 'r') as f:
        return json.load(f)

def get_version(knowledge_dir, specified_version=None):
    """Get version from version.txt or parameter"""
    if specified_version:
        return specified_version
    
    version_path = knowledge_dir / "version.txt"
    if version_path.exists():
        return version_path.read_text().strip()
    
    return "1.0.0"  # Default fallback

def create_or_update_honey_jar(base_url, manifest, update_existing=False):
    """Create or update the honey jar"""
    jar_id = manifest["id"]
    jar_data = {
        "name": manifest["name"],
        "description": f"{manifest['description']} (v{manifest['version']})",
        "owner": manifest["honey_jar"]["owner"],
        "type": manifest["honey_jar"]["type"], 
        "status": manifest["honey_jar"]["status"],
        "tags": manifest["tags"],
        "permissions": manifest["honey_jar"]["permissions"],
        "config": manifest["honey_jar"]["config"]
    }
    
    if update_existing:
        # Try to update existing jar
        try:
            headers = {'X-API-Key': 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0'}
            response = requests.put(f"{base_url}/honey-jars/{jar_id}", json=jar_data, timeout=10, headers=headers)
            if response.status_code == 200:
                print(f"✅ Updated honey jar: {jar_data['name']}")
                return jar_id
            elif response.status_code == 404:
                print(f"⚠️  Honey jar not found, creating new one...")
                update_existing = False
            else:
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Failed to update honey jar, creating new one: {e}")
            update_existing = False
    
    if not update_existing:
        # Create new honey jar
        jar_data["id"] = jar_id
        headers = {'X-API-Key': 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0'}
        response = requests.post(f"{base_url}/honey-jars", json=jar_data, timeout=10, headers=headers)
        
        if response.status_code in [200, 201]:
            created_jar = response.json()
            actual_jar_id = created_jar.get('id', jar_id)
            print(f"✅ Created honey jar: {jar_data['name']} (ID: {actual_jar_id})")
            return actual_jar_id
        elif response.status_code == 409:
            print(f"✅ Honey jar already exists: {jar_data['name']}")
            return jar_id
        else:
            print(f"❌ Failed to create honey jar. Status: {response.status_code}, Response: {response.text}")
            response.raise_for_status()
    
    return None  # This should not be reached, but explicit return for safety

def upload_documents(base_url, jar_id, knowledge_dir, manifest, dry_run=False):
    """Upload documents to the honey jar"""
    uploaded_count = 0
    total_docs = sum(len(docs) for docs in manifest["documents"].values())
    
    print(f"📄 Uploading {total_docs} documents to honey jar...")
    
    for category, documents in manifest["documents"].items():
        print(f"\n📂 Category: {category}")
        
        for doc in documents:
            file_path = knowledge_dir / doc["file"]
            
            if not file_path.exists():
                print(f"⚠️  Document not found: {file_path}")
                continue
            
            if dry_run:
                print(f"  📄 [DRY RUN] Would upload: {doc['title']}")
                uploaded_count += 1
                continue
            
            try:
                # Prepare file upload
                with open(file_path, 'rb') as f:
                    files = {'file': (doc['file'], f, 'text/markdown')}
                    
                    # Prepare metadata
                    metadata = {
                        'title': doc['title'],
                        'description': doc['description'],
                        'category': category,
                        'type': doc['type'],
                        'version': manifest['version'],
                        'references': doc.get('references', [])
                    }
                    
                    data = {'metadata': json.dumps(metadata)}
                    
                    # Upload document
                    headers = {'X-API-Key': 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0'}
                    response = requests.post(
                        f"{base_url}/honey-jars/{jar_id}/documents/upload",
                        files=files,
                        data=data,
                        headers=headers,
                        timeout=30,
                        verify=False
                    )
                    
                    if response.status_code in [200, 201]:
                        upload_result = response.json()
                        doc_id = upload_result.get('document_id', 'unknown')
                        print(f"  ✅ Uploaded: {doc['title']} (ID: {doc_id})")
                        uploaded_count += 1
                    else:
                        print(f"  ❌ Failed to upload {doc['title']}: {response.status_code}")
                        if response.text:
                            print(f"     Error: {response.text}")
                            
            except Exception as e:
                print(f"  ❌ Error uploading {doc['title']}: {e}")
    
    return uploaded_count

def verify_upload(base_url, jar_id, expected_count):
    """Verify the upload was successful"""
    try:
        headers = {'X-API-Key': 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0'}
        response = requests.get(f"{base_url}/honey-jars/{jar_id}", timeout=10, headers=headers)
        if response.status_code == 200:
            jar_info = response.json()
            doc_count = jar_info.get('document_count', 0)
            print(f"✅ Honey jar contains {doc_count} documents")
            
            if doc_count >= expected_count:
                print(f"✅ Upload verification successful!")
                return True
            else:
                print(f"⚠️  Expected {expected_count} documents, found {doc_count}")
                return False
        else:
            print(f"❌ Failed to verify upload: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verifying upload: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Upload STING Platform Knowledge to Honey Jar")
    parser.add_argument('--update', action='store_true', help='Update existing honey jar')
    parser.add_argument('--version', help='Specify version (default: read from version.txt)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be uploaded')
    
    args = parser.parse_args()
    
    # Set up paths
    knowledge_dir = project_root / "knowledge" / "sting-platform-docs"
    
    if not knowledge_dir.exists():
        print(f"❌ Knowledge directory not found: {knowledge_dir}")
        sys.exit(1)
    
    print("🐝 STING Platform Knowledge Upload")
    print("=" * 50)
    
    try:
        # Load manifest and version
        manifest = load_manifest(knowledge_dir)
        version = get_version(knowledge_dir, args.version)
        manifest["version"] = version
        
        print(f"📦 Package: {manifest['name']} v{version}")
        print(f"📁 Source: {knowledge_dir}")
        
        if args.dry_run:
            print("🔍 DRY RUN MODE - No actual uploads will be performed")
        
        # Wait for knowledge service
        base_url = wait_for_knowledge_service()
        if not base_url:
            sys.exit(1)
        
        # Create or update honey jar
        jar_id = create_or_update_honey_jar(base_url, manifest, args.update)
        
        # Upload documents
        uploaded_count = upload_documents(base_url, jar_id, knowledge_dir, manifest, args.dry_run)
        
        if not args.dry_run:
            # Verify upload
            total_expected = sum(len(docs) for docs in manifest["documents"].values())
            if verify_upload(base_url, jar_id, total_expected):
                print(f"\n🎉 Successfully uploaded STING Platform Knowledge!")
                print(f"   📊 {uploaded_count} documents uploaded")
                print(f"   🔗 Honey Jar ID: {jar_id}")
                print(f"   🤖 Bee Chat can now answer questions about STING!")
            else:
                print(f"\n⚠️  Upload completed but verification failed")
                print(f"   📊 {uploaded_count} documents uploaded")
        else:
            print(f"\n✅ Dry run completed - would upload {uploaded_count} documents")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()