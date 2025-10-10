#!/usr/bin/env python3
"""
Test script to verify STING Assistant knowledge base integration
"""

import yaml
import sys
import os

# Add STING modules to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'chatbot'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), 'llm_service'))

def test_knowledge_base_file():
    """Test that the knowledge base file exists and is valid"""
    print("1. Testing knowledge base file...")
    kb_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'conf', 'knowledge_base.yml')
    
    if not os.path.exists(kb_path):
        print(f"   ❌ Knowledge base file not found at {kb_path}")
        return False
    
    try:
        with open(kb_path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['system_identity', 'core_knowledge', 'response_guidelines']
        for section in required_sections:
            if section not in data:
                print(f"   ❌ Missing required section: {section}")
                return False
        
        # Verify STING Assistant identity
        identity = data.get('system_identity', {})
        if identity.get('short_name') != 'STING Assistant':
            print(f"   ❌ Incorrect short name: {identity.get('short_name')}")
            return False
            
        print("   ✅ Knowledge base file is valid")
        print(f"   - Name: {identity.get('name')}")
        print(f"   - Full Name: {identity.get('full_name')}")
        print(f"   - Short Name: {identity.get('short_name')}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error loading knowledge base: {e}")
        return False

def test_chatbot_integration():
    """Test that the chatbot can load and use the knowledge base"""
    print("\n2. Testing chatbot integration...")
    
    try:
        from core.knowledge_base import get_knowledge_base
        
        kb = get_knowledge_base()
        system_prompt = kb.get_system_prompt('bee')
        
        if 'STING Assistant' not in system_prompt:
            print("   ❌ System prompt doesn't contain STING Assistant reference")
            return False
        
        if 'Secure Technological Intelligence and Networking Guardian Assistant' not in system_prompt:
            print("   ❌ System prompt doesn't contain full STING name")
            return False
        
        print("   ✅ Chatbot knowledge base integration working")
        print(f"   - System prompt length: {len(system_prompt)} characters")
        
        # Test context retrieval
        context = kb.get_context_for_query("What is STING?")
        if context:
            print("   ✅ Context retrieval working")
        else:
            print("   ⚠️  No context retrieved for 'What is STING?' query")
            
        return True
        
    except ImportError as e:
        print(f"   ❌ Failed to import chatbot modules: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error testing chatbot integration: {e}")
        return False

def test_llm_service_integration():
    """Test that the LLM service can load and use the knowledge base"""
    print("\n3. Testing LLM service integration...")
    
    try:
        from utils.knowledge_base_loader import get_sting_system_prompt, load_knowledge_base
        
        # Test loading knowledge base
        kb_data = load_knowledge_base()
        if not kb_data:
            print("   ❌ Failed to load knowledge base data")
            return False
        
        # Test system prompt generation
        system_prompt = get_sting_system_prompt()
        
        if 'STING Assistant' not in system_prompt:
            print("   ❌ LLM system prompt doesn't contain STING Assistant reference")
            return False
        
        if 'Secure Technological Intelligence and Networking Guardian Assistant' not in system_prompt:
            print("   ❌ LLM system prompt doesn't contain full STING name")
            return False
        
        print("   ✅ LLM service knowledge base integration working")
        print(f"   - System prompt length: {len(system_prompt)} characters")
        return True
        
    except ImportError as e:
        print(f"   ❌ Failed to import LLM service modules: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error testing LLM service integration: {e}")
        return False

def main():
    """Run all tests"""
    print("=== STING Assistant Knowledge Base Integration Test ===\n")
    
    tests = [
        test_knowledge_base_file,
        test_chatbot_integration,
        test_llm_service_integration
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"   ❌ Test failed with error: {e}")
            results.append(False)
    
    print("\n=== Test Summary ===")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ All tests passed! STING Assistant knowledge base is properly integrated.")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main()