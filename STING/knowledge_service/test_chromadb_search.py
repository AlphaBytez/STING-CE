#!/usr/bin/env python3
"""
Test ChromaDB search functionality
"""

import chromadb
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_search():
    """Test searching in ChromaDB"""
    
    # Connect to ChromaDB
    client = chromadb.HttpClient(host="chroma", port=8000)
    
    # List collections
    collections = client.list_collections()
    logger.info(f"Collections: {[c.name for c in collections]}")
    
    # Find the General Support Knowledge collection
    target_collection = None
    for collection in collections:
        if "1ac709f3_d50b_44c5_ba47_77fca664572b" in collection.name:
            target_collection = collection
            break
    
    if not target_collection:
        logger.error("General Support Knowledge collection not found")
        return
    
    logger.info(f"Using collection: {target_collection.name}")
    
    # Get collection handle
    collection = client.get_collection(target_collection.name)
    
    # Check count
    count = collection.count()
    logger.info(f"Documents in collection: {count}")
    
    # Try different query methods
    queries = [
        "How to install Ollama",
        "Ollama installation",
        "install",
        "setup"
    ]
    
    for query in queries:
        logger.info(f"\nSearching for: '{query}'")
        
        try:
            # Method 1: Query with text
            results = collection.query(
                query_texts=[query],
                n_results=3
            )
            
            if results and results.get('documents'):
                docs = results['documents'][0]
                logger.info(f"  Found {len(docs)} results")
                for i, doc in enumerate(docs[:2]):
                    logger.info(f"  Result {i+1}: {doc[:100]}...")
            else:
                logger.info("  No results found")
                
        except Exception as e:
            logger.error(f"  Query failed: {e}")
            
            # Try alternative query format
            try:
                logger.info("  Trying peek instead...")
                peek_results = collection.peek(limit=5)
                if peek_results and peek_results.get('documents'):
                    logger.info(f"  Collection has {len(peek_results['documents'])} documents")
                    logger.info(f"  First doc: {peek_results['documents'][0][:100]}...")
            except Exception as e2:
                logger.error(f"  Peek also failed: {e2}")

if __name__ == "__main__":
    test_search()