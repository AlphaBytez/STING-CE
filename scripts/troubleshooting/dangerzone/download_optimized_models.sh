#!/bin/bash

# Download Optimized Small Models for STING
# Including DeepSeek models for enhanced reasoning capabilities

set -e

MODELS_DIR=${STING_MODELS_DIR:-"/Users/captain-wolf/Downloads/llm_models"}
HF_TOKEN=${HF_TOKEN:-""}

echo "🚀 Downloading Optimized Small Models for STING"
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
        # Install huggingface-cli if not available
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

echo "Starting downloads (optimized model set)..."

# 1. DialoGPT-medium (~345MB) - Fast conversational AI
download_model "microsoft/DialoGPT-medium" "DialoGPT-medium" "345MB"

# 2. DeepSeek-R1-Distill (~1.5GB) - Excellent reasoning in small package
download_model "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B" "DeepSeek-R1-Distill-Qwen-1.5B" "1.5GB"

# 3. TinyLlama (~2.2GB) - Well-balanced general purpose
download_model "TinyLlama/TinyLlama-1.1B-Chat-v1.0" "TinyLlama-1.1B-Chat" "2.2GB"

# Optional models
echo ""
echo "📦 Optional Models:"
echo "1. Phi-2 (2.7GB) - Microsoft's efficient model"
echo "2. DeepSeek-7B-Chat (7GB) - Larger chat model with better quality"
echo "3. Phi-3 Mini (7GB) - Latest from Microsoft"
echo ""
read -p "Download optional models? [y/N]: " download_optional

if [[ $download_optional =~ ^[Yy]$ ]]; then
    # Ask for each model individually
    read -p "Download Phi-2 (2.7GB)? [y/N]: " download_phi2
    if [[ $download_phi2 =~ ^[Yy]$ ]]; then
        download_model "microsoft/phi-2" "phi-2" "2.7GB"
    fi
    
    read -p "Download DeepSeek-7B-Chat (7GB)? [y/N]: " download_deepseek7b
    if [[ $download_deepseek7b =~ ^[Yy]$ ]]; then
        download_model "deepseek-ai/deepseek-llm-7b-chat" "deepseek-llm-7b-chat" "7GB"
    fi
    
    read -p "Download Phi-3 Mini (7GB)? [y/N]: " download_phi3
    if [[ $download_phi3 =~ ^[Yy]$ ]]; then
        download_model "microsoft/Phi-3-mini-4k-instruct" "phi-3-mini-4k" "7GB"
    fi
fi

echo ""
echo "🎉 Download Complete!"
echo "====================="
echo ""
echo "📊 Model Summary:"
echo "Core Models (Always Downloaded):"
echo "- DialoGPT-medium: 345MB, optimized for conversation"
echo "- DeepSeek-R1-1.5B: 1.5GB, excellent reasoning capabilities"
echo "- TinyLlama: 2.2GB, balanced general purpose"
echo ""
echo "💾 Total space used: $(du -sh "$MODELS_DIR" | cut -f1)"
echo ""
echo "🚀 Next Steps:"
echo "1. Run installation with small models: ./manage_sting.sh install --model-mode small"
echo "2. Or use the small models configuration: docker compose -f docker-compose.yml -f docker-compose.small-models.yml up -d"
echo ""
echo "💡 Model Selection Guide:"
echo "- For reasoning tasks: Use DeepSeek-R1-1.5B"
echo "- For fast responses: Use DialoGPT-medium"
echo "- For general chat: Use TinyLlama"
echo ""
echo "⚡ To switch models after installation:"
echo "   export ACTIVE_MODEL=deepseek-1.5b  # or tinyllama, dialogpt"
echo "   docker compose restart llm-gateway"