#!/usr/bin/env python3
"""
Test script to verify knowledge service integration with Bee chatbot
"""

import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from chatbot.bee_server import query_knowledge_service

async def test_knowledge_integration():
    """Test the knowledge service integration"""
    print("Testing knowledge service integration...")
    
    # Test queries
    test_queries = [
        "What are recent honey jar attacks?",
        "Show me SSH login attempts",
        "Any suspicious network activity?",
        "Database intrusion attempts"
    ]
    
    for query in test_queries:
        print(f"\n--- Testing query: {query} ---")
        try:
            result = await query_knowledge_service(query, "test-user")
            if result:
                print(f"✅ Knowledge service returned data:")
                if 'results' in result:
                    print(f"   - Found {len(result['results'])} results")
                    for i, res in enumerate(result['results'][:2], 1):
                        content = res.get('content', res.get('text', ''))[:100]
                        metadata = res.get('metadata', {})
                        source = metadata.get('source', 'unknown')
                        print(f"   - Result {i}: {content}... (from {source})")
                else:
                    print(f"   - Response: {result}")
            else:
                print("⚠️ Knowledge service returned empty response (service may be down)")
        except Exception as e:
            print(f"❌ Error testing query: {str(e)}")
    
    print("\n--- Testing knowledge service health ---")
    from chatbot.bee_server import check_knowledge_service_health
    try:
        is_healthy = await check_knowledge_service_health()
        if is_healthy:
            print("✅ Knowledge service is healthy")
        else:
            print("⚠️ Knowledge service health check failed")
    except Exception as e:
        print(f"❌ Error checking health: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_knowledge_integration())