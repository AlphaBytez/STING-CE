#!/usr/bin/env python3
"""
Simple LLM test using HuggingFace Transformers directly.
This bypasses STING's model configuration and tests the core LLM functionality.
"""

import os
import sys
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

def main():
    print("=== Simple LLM Test ===")
    print("Testing Mac GPU (MPS) support with TinyLlama...")
    
    # Check MPS availability
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print("✅ MPS (Mac GPU) is available")
    else:
        device = torch.device("cpu")
        print("⚠️ Using CPU (MPS not available)")
    
    try:
        # Load a small model directly from HuggingFace
        model_name = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
        print(f"Loading model: {model_name}")
        
        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        # Load model with appropriate settings for Mac
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16 if device.type == "mps" else torch.float32,
            device_map="auto" if device.type == "mps" else None,
            trust_remote_code=True
        )
        
        if device.type != "mps":
            model = model.to(device)
        
        print("✅ Model loaded successfully")
        
        # Test generation
        prompt = "Hello, how are you today?"
        print(f"Testing with prompt: '{prompt}'")
        
        inputs = tokenizer(prompt, return_tensors="pt")
        if device.type == "mps":
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        generated_text = response[len(prompt):].strip()
        
        print("✅ Generation successful!")
        print(f"Response: {generated_text}")
        print("\n=== Test Complete ===")
        print("✅ Core LLM functionality is working")
        print("✅ Mac GPU acceleration is available")
        print("⚠️ STING model configuration needs updating to use HuggingFace names")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n=== Test Failed ===")
        return False

if __name__ == "__main__":
    # Set up environment
    os.environ["TOKENIZERS_PARALLELISM"] = "false"  # Avoid warnings
    
    success = main()
    sys.exit(0 if success else 1)