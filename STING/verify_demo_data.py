import requests
import os
import json

KNOWLEDGE_URL = os.environ.get('KNOWLEDGE_SERVICE_URL', 'http://knowledge:8090')
API_KEY = os.environ.get('STING_API_KEY', 'sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0')

def verify_data():
    headers = {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
    }
    
    print(f"Connecting to Knowledge Service at {KNOWLEDGE_URL}...")
    
    # 1. List Honey Jars
    try:
        response = requests.get(f"{KNOWLEDGE_URL}/honey-jars", headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"❌ Failed to list honey jars: {response.status_code} - {response.text}")
            return
            
        jars = response.json()
        print(f"✅ Found {len(jars)} honey jars.")
        
        print("--- Existing Jars ---")
        for jar in jars:
            print(f"- {jar['name']} (ID: {jar['id']})")
        print("---------------------")
        
        target_jars = [
            "HR - Benefits Archive",
            "Legal - Contracts Archive",
            "Finance - Invoices Archive",
            "IT - Security Archive",
            "Sales - Proposals Archive"
        ]
        
        found_jars = []
        for jar in jars:
            if jar['name'] in target_jars:
                found_jars.append(jar)
                
        print(f"Found {len(found_jars)} of {len(target_jars)} target demo jars.")
        
        # Check specific IDs from logs if not found in list (likely due to pagination)
        known_ids = {
            "IT - Security Archive (Target)": "3a24772e-6e00-42c8-aab2-e9fbc5e6b2af",
            "Sales - Proposals Archive (Target)": "dde7dece-8a8b-4b3a-8596-6daa188feb07"
        }
        
        for name, jar_id in known_ids.items():
            # Check if we already found it
            if any(j['id'] == jar_id for j in found_jars):
                continue
                
            print(f"\nChecking known jar from logs: {name} ({jar_id})")
            doc_response = requests.get(f"{KNOWLEDGE_URL}/honey-jars/{jar_id}/documents", headers=headers, timeout=10)
            
            if doc_response.status_code == 200:
                docs = doc_response.json()
                
                # Handle dictionary response (wrapped list)
                if isinstance(docs, dict) and 'documents' in docs:
                    docs = docs['documents']
                
                print(f"📂 Jar: {name}")
                print(f"   ID: {jar_id}")
                print(f"   Document Count: {len(docs)}")
                if docs:
                    print(f"   Sample Document: {docs[0].get('filename', 'Unknown')}")
                    print(f"   Sample Content Preview: {str(docs[0].get('content', ''))[:100]}...")
            else:
                print(f"⚠️ Could not list documents for {name}: {doc_response.status_code}")

        for jar in found_jars:
            jar_id = jar['id']
            jar_name = jar['name']
            
            # 2. List Documents in Jar
            # Try standard endpoint patterns
            doc_response = requests.get(f"{KNOWLEDGE_URL}/honey-jars/{jar_id}/documents", headers=headers, timeout=10)
            
            if doc_response.status_code == 200:
                docs = doc_response.json()
                print(f"\n📂 Jar: {jar_name}")
                print(f"   ID: {jar_id}")
                print(f"   Document Count: {len(docs)}")
                if docs:
                    print(f"   Sample Document: {docs[0].get('filename', 'Unknown')}")
            else:
                print(f"⚠️ Could not list documents for {jar_name}: {doc_response.status_code}")
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Error connecting to service: {e}")

if __name__ == "__main__":
    verify_data()
