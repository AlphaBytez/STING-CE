#!/usr/bin/env python3
"""
Test markdown extraction directly
"""

import markdown
from bs4 import BeautifulSoup

# Test content
test_md = """# Ollama Setup Guide for STING

## Current Status
- External AI service is running and configured
- Ollama is NOT installed on the system
- Installation requires sudo privileges

## Installation Steps

### Option 1: Install in WSL2 (Recommended)
```bash
# Run with sudo
sudo ./scripts/install_ollama.sh
```

This is a test paragraph with some text.
"""

print("Original markdown:")
print(test_md)
print("\n" + "="*50 + "\n")

# Convert to HTML
html = markdown.markdown(test_md)
print("HTML conversion:")
print(html)
print("\n" + "="*50 + "\n")

# Extract text
soup = BeautifulSoup(html, 'html.parser')
text = soup.get_text(separator='\n', strip=True)
print("Extracted text:")
print(text)
print(f"\nExtracted text length: {len(text)}")