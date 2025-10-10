#!/usr/bin/env python3
"""
Temporary fix for Bee responses - extracts just the first response
"""
import re

def clean_bee_response(response_text):
    """Extract just Bee's first response from the generated text"""
    
    # If the response starts with "Bot:" or similar, extract just the first response
    if response_text.startswith(("Bot:", "Bee:", "Assistant:")):
        # Find the first response up to the next "User:" or end of first paragraph
        match = re.match(r'^(?:Bot:|Bee:|Assistant:)\s*([^\\n]+?)(?:\\n\\nUser:|\\n\\n|$)', response_text)
        if match:
            return match.group(1).strip()
    
    # If it's a direct response, take just the first sentence or two
    sentences = response_text.split('. ')
    if len(sentences) > 2:
        return '. '.join(sentences[:2]) + '.'
    
    # Otherwise return the first line
    lines = response_text.strip().split('\n')
    return lines[0] if lines else response_text

# Example usage
if __name__ == "__main__":
    test_response = """Bot: Hi there! How can I help you today?

User: I'm interested in setting up a chatbot for my business. How can STING Assistant help?

Bot: STING is an advanced chatbot development platform..."""
    
    cleaned = clean_bee_response(test_response)
    print(f"Original: {test_response[:50]}...")
    print(f"Cleaned: {cleaned}")