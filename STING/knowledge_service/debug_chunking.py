#!/usr/bin/env python3
"""
Debug script to test document chunking
"""

import sys
import os
import io
import asyncio
from pathlib import Path
from core.nectar_processor import NectarProcessor
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def test_chunking(file_path: str):
    """Test the chunking process"""
    
    # Check if file exists
    if not os.path.exists(file_path):
        print(f"Error: File not found: {file_path}")
        return
    
    print(f"Testing file: {file_path}")
    print(f"File size: {os.path.getsize(file_path)} bytes")
    
    # Read file content
    with open(file_path, 'rb') as f:
        content = f.read()
    
    print(f"\nFile content preview:")
    print(content[:500].decode('utf-8', errors='replace'))
    print("...")
    
    # Create NectarProcessor
    nectar_processor = NectarProcessor()
    
    # Create mock upload file
    class MockUploadFile:
        def __init__(self, content, filename, content_type):
            self.file = io.BytesIO(content)
            self.filename = filename
            self.content_type = content_type
        
        async def read(self):
            return self.file.read()
    
    mock_file = MockUploadFile(content, os.path.basename(file_path), "text/markdown")
    
    try:
        # Extract text
        print("\n1. Extracting text...")
        extracted_text = await nectar_processor.extract_text(mock_file)
        print(f"Extracted text length: {len(extracted_text)} characters")
        print(f"Text preview: {extracted_text[:200]}...")
        
        # Test different chunking strategies
        strategies = ["sentence", "paragraph", "character"]
        
        for strategy in strategies:
            print(f"\n2. Testing {strategy} chunking strategy...")
            chunks = await nectar_processor.chunk_content(
                extracted_text,
                chunk_size=1000,
                overlap=200,
                strategy=strategy
            )
            
            print(f"Number of chunks: {len(chunks)}")
            if chunks:
                print(f"First chunk length: {len(chunks[0])}")
                print(f"First chunk preview: {chunks[0][:100]}...")
            else:
                print("No chunks generated!")
                
                # Debug: Check if content is being filtered
                print("\nDebugging empty chunks:")
                print(f"- Content stripped length: {len(extracted_text.strip())}")
                print(f"- Content has newlines: {'\\n' in extracted_text}")
                print(f"- Content has paragraphs: {'\\n\\n' in extracted_text}")
                
    except Exception as e:
        print(f"\nError during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python debug_chunking.py <file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    asyncio.run(test_chunking(file_path))