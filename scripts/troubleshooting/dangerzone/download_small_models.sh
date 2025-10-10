#!/bin/bash

# Download Small, Fast Models for STING
# These models are much faster and require less memory

set -e

MODELS_DIR=${STING_MODELS_DIR:-"/Users/captain-wolf/Downloads/llm_models"}
HF_TOKEN=${HF_TOKEN:-""}

echo "🚀 Downloading Small, Fast Models for STING"
echo "Models directory: $MODELS_DIR"
echo "============================================"

# Create models directory
mkdir -p "$MODELS_DIR"
cd "$MODELS_DIR"

# Function to download model
download_model() {
    local repo_id=$1
    local local_name=$2
    local size=$3
    
    echo ""
    echo "📦 Downloading $local_name ($size)"
    echo "Repository: $repo_id"
    echo "-----------------------------------"
    
    if [ -d "$local_name" ]; then
        echo "✅ $local_name already exists, skipping..."
        return 0
    fi
    
    if command -v huggingface-cli >/dev/null 2>&1; then
        # Use huggingface-cli if available
        if [ -n "$HF_TOKEN" ]; then
            huggingface-cli download "$repo_id" --local-dir "$local_name" --token "$HF_TOKEN"
        else
            huggingface-cli download "$repo_id" --local-dir "$local_name"
        fi
    else
        # Fallback to git clone
        echo "Installing huggingface-cli..."
        pip install huggingface_hub[cli] || python3 -m pip install huggingface_hub[cli]
        
        if [ -n "$HF_TOKEN" ]; then
            huggingface-cli download "$repo_id" --local-dir "$local_name" --token "$HF_TOKEN"
        else
            huggingface-cli download "$repo_id" --local-dir "$local_name"
        fi
    fi
    
    echo "✅ Downloaded $local_name successfully!"
}

# Download small models (in order of size - smallest first)
echo ""
echo "📋 Planned downloads:"
echo "  ✓ DialoGPT-medium (~345MB) - Great for conversation"
echo "  ✓ TinyLlama (~2.2GB) - Small but capable"
echo ""

# Ask about optional models before downloading anything
echo "📦 Optional models:"
read -p "  Download Phi-2 (~2.7GB) - Microsoft's efficient model? [Y/n]: " download_phi2
read -p "  Download Phi-3 Mini (~7GB) - Better quality responses? [y/N]: " download_phi3

echo ""
echo "Starting downloads..."
echo "===================="

# 1. DialoGPT-medium (~345MB) - Great for conversation
download_model "microsoft/DialoGPT-medium" "DialoGPT-medium" "345MB"

# 2. TinyLlama (~2.2GB) - Small but capable
download_model "TinyLlama/TinyLlama-1.1B-Chat-v1.0" "TinyLlama-1.1B-Chat" "2.2GB"

# 3. Phi-2 (~2.7GB) - Microsoft's efficient model (optional)
if [[ ! $download_phi2 =~ ^[Nn]$ ]]; then
    download_model "microsoft/phi-2" "phi-2" "2.7GB"
fi

# 4. Phi-3 Mini (optional, larger but still reasonable)
if [[ $download_phi3 =~ ^[Yy]$ ]]; then
    download_model "microsoft/Phi-3-mini-4k-instruct" "phi-3-mini-4k" "7GB"
fi

echo ""
echo "🎉 Download Complete!"
echo "====================="
echo ""
echo "📊 Downloaded Models:"
echo "- DialoGPT-medium: 345MB, great for chat"
echo "- TinyLlama: 2.2GB, balanced performance" 
if [[ ! $download_phi2 =~ ^[Nn]$ ]]; then
    echo "- Phi-2: 2.7GB, Microsoft's efficient model"
fi
if [[ $download_phi3 =~ ^[Yy]$ ]]; then
    echo "- Phi-3 Mini: 7GB, higher quality responses"
fi
echo ""
echo "💾 Total space used: $(du -sh "$MODELS_DIR" | cut -f1)"
echo ""
echo "🚀 Next Steps:"
echo "1. Restart STING services: docker compose restart"
echo "2. Test chatbot: curl -X POST http://localhost:8081/chat/message \\"
echo "   -H 'Content-Type: application/json' \\"
echo "   -d '{\"message\": \"Hello!\", \"user_id\": \"test\"}'"
echo ""
echo "⚡ For GPU acceleration, see: docs/PERFORMANCE_ADMIN_GUIDE.md"