#!/usr/bin/env python3
"""
Test script for file service functionality.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent / 'app'))

def test_vault_connection():
    """Test Vault connectivity."""
    try:
        from app.utils.vault_file_client import VaultFileClient
        
        print("Testing Vault connection...")
        client = VaultFileClient()
        
        # Test basic connectivity
        if client.vault_manager.client.sys.is_initialized():
            print("✓ Vault is initialized and accessible")
            return True
        else:
            print("✗ Vault is not initialized")
            return False
            
    except Exception as e:
        print(f"✗ Vault connection failed: {e}")
        return False

def test_file_upload():
    """Test file upload functionality."""
    try:
        from app.utils.vault_file_client import VaultFileClient, FileUploadHandler
        
        print("\nTesting file upload...")
        
        # Create test file data
        test_data = b"This is a test file for STING-CE file service"
        test_filename = "test.txt"
        test_user_id = "test-user-123"
        
        # Initialize clients
        vault_client = VaultFileClient()
        upload_handler = FileUploadHandler(vault_client)
        
        # Upload file
        result = upload_handler.upload_file(
            test_data, test_filename, 'user_document', test_user_id
        )
        
        if result['success']:
            print(f"✓ File uploaded successfully: {result['file_id']}")
            
            # Test file retrieval
            file_data = vault_client.retrieve_file(result['file_id'])
            if file_data and file_data['data'] == test_data:
                print("✓ File retrieved successfully and data matches")
                
                # Test file deletion
                if vault_client.delete_file(result['file_id']):
                    print("✓ File deleted successfully")
                    return True
                else:
                    print("✗ File deletion failed")
                    return False
            else:
                print("✗ File retrieval failed or data mismatch")
                return False
        else:
            print(f"✗ File upload failed: {result.get('errors', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"✗ File upload test failed: {e}")
        return False

def test_file_validation():
    """Test file validation."""
    try:
        from app.utils.vault_file_client import FileUploadHandler, VaultFileClient
        
        print("\nTesting file validation...")
        
        vault_client = VaultFileClient()
        upload_handler = FileUploadHandler(vault_client)
        
        # Test valid file
        valid_data = b"Valid test data"
        validation = upload_handler.validate_file(valid_data, "test.txt", "user_document")
        
        if validation['valid']:
            print("✓ Valid file passed validation")
        else:
            print(f"✗ Valid file failed validation: {validation['errors']}")
            return False
        
        # Test oversized file
        large_data = b"x" * (100 * 1024 * 1024)  # 100MB
        validation = upload_handler.validate_file(large_data, "large.txt", "user_document")
        
        if not validation['valid'] and any('too large' in error.lower() for error in validation['errors']):
            print("✓ Oversized file correctly rejected")
        else:
            print("✗ Oversized file validation failed")
            return False
        
        # Test invalid extension
        validation = upload_handler.validate_file(valid_data, "test.exe", "user_document")
        
        if not validation['valid'] and any('extension' in error.lower() for error in validation['errors']):
            print("✓ Invalid extension correctly rejected")
        else:
            print("✗ Invalid extension validation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"✗ File validation test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("STING-CE File Service Test Suite")
    print("=" * 40)
    
    # Set up environment
    if not os.environ.get('DATABASE_URL'):
        os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5433/sting_app'
    
    if not os.environ.get('VAULT_ADDR'):
        os.environ['VAULT_ADDR'] = 'http://localhost:8200'
    
    if not os.environ.get('VAULT_TOKEN'):
        os.environ['VAULT_TOKEN'] = 'root'
    
    # Run tests
    tests = [
        test_vault_connection,
        test_file_upload,
        test_file_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\nTest Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed")
        return 1

if __name__ == '__main__':
    sys.exit(main())