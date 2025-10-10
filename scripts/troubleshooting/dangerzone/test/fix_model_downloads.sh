#!/bin/bash
# Script to fix model download issues by ensuring proper environment and permissions

set -e

# Navigate to STING directory
cd "$(dirname "$0")"

# Check current environment
if [ -f ".env" ]; then
    echo "Found .env file in project root"
    # Extract token without revealing it
    HF_TOKEN_VAL=$(grep -E '^[[:space:]]*HF_TOKEN=' ".env" | cut -d'=' -f2- | tr -d "'\""| tr -d ' ')
    if [ -n "$HF_TOKEN_VAL" ]; then
        echo "✅ HF_TOKEN found in .env file"
        export HF_TOKEN="$HF_TOKEN_VAL"
    else
        echo "❌ No HF_TOKEN found in .env file"
        echo "Please run: ./set_hf_token.sh"
        exit 1
    fi
else
    echo "❌ No .env file found"
    echo "Creating empty .env file"
    touch .env
    
    echo "Please run: ./set_hf_token.sh"
    exit 1
fi

# Make sure ./set_hf_token.sh is executable
chmod +x ./set_hf_token.sh

# Fix permissions on temporary directories
echo "Ensuring temporary directories have correct permissions..."
TEMP_DIRS=(
    "/tmp/model_downloads"
    "/tmp/sting_model_downloads"
)

for dir in "${TEMP_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Cleaning up existing directory: $dir"
        rm -rf "$dir"
    fi
    
    echo "Creating directory with proper permissions: $dir"
    mkdir -p "$dir"
    chmod 777 "$dir"  # Ensure everyone can write to it
done

# Modify download parameters in model_downloader.py
echo "Updating model download parameters for better reliability..."
sed -i.bak 's/resume_download=True/resume_download=True, local_files_only=False, retry=3/g' llm_service/utils/model_downloader.py

# Make a direct modification to the manage_sting.sh script to ensure HF_TOKEN is properly passed
echo "Fixing HF_TOKEN passing in manage_sting.sh..."
grep -q "# Re-export HF_TOKEN right before model download" manage_sting.sh || {
    sed -i.bak '/log_message "Downloading LLM models..."/a\\n    # Re-export HF_TOKEN right before model download - added by fix script\n    if [ -f ".env" ]; then\n        HF_TOKEN_FROM_ENV=$(grep -E "^HF_TOKEN=" ".env" | cut -d"=" -f2- | tr -d "\\"\\"\'\\"\\" " | tr -d " ")\n        if [ -n "$HF_TOKEN_FROM_ENV" ]; then\n            export HF_TOKEN="$HF_TOKEN_FROM_ENV"\n            log_message "Re-set HF_TOKEN from .env file right before model download"\n        fi\n    fi\n' manage_sting.sh
}

# Create a custom model download script that guarantees environment variables are correct
echo "Creating a guaranteed model download script..."
cat > download_models_directly.sh << 'EOF'
#!/bin/bash
# Script to directly download models with guaranteed environment setup

set -e

# Get the token from .env
if [ -f ".env" ]; then
    HF_TOKEN_VAL=$(grep -E '^[[:space:]]*HF_TOKEN=' ".env" | cut -d'=' -f2- | tr -d "'\""| tr -d ' ')
    if [ -n "$HF_TOKEN_VAL" ]; then
        export HF_TOKEN="$HF_TOKEN_VAL"
        echo "Using HF_TOKEN from .env file"
    fi
fi

# Create and configure Python virtual environment
VENV_DIR="${HOME}/.sting-ce/venv"
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtualenv
source "$VENV_DIR/bin/activate"

# Install required packages
echo "Installing required packages..."
pip install --upgrade pip
pip install --upgrade huggingface_hub transformers tqdm

# Create temporary directory with proper permissions
TEMP_DIR="/tmp/sting_model_downloads"
rm -rf "$TEMP_DIR"
mkdir -p "$TEMP_DIR"
chmod 777 "$TEMP_DIR"

# Get model directory from config.yml or default
CONFIG_DIR="${HOME}/.sting-ce/conf"
if [ -f "${CONFIG_DIR}/config.yml" ]; then
    MODELS_DIR=$(grep -E '^[[:space:]]*models_dir:' "${CONFIG_DIR}/config.yml" | head -n1 | cut -d: -f2- | tr -d ' "')
    MODELS_DIR="${MODELS_DIR/#\~/$HOME}"  # Expand tilde if present
else
    # Default location on macOS
    if [[ "$(uname)" == "Darwin" ]]; then
        MODELS_DIR="${HOME}/Downloads/llm_models"
    else
        MODELS_DIR="/opt/models"
    fi
fi

echo "Using models directory: $MODELS_DIR"
mkdir -p "$MODELS_DIR"

# Download each model directly using huggingface_hub
for model in "llama3" "phi3" "zephyr"; do
    echo "Downloading model: $model"
    python3 -c "
import os
import sys
from huggingface_hub import snapshot_download, login

# Model configurations
MODELS = {
    'llama3': {'repo_id': 'meta-llama/Llama-3.1-8B', 'target_dir': 'llama-3-8b'},
    'phi3': {'repo_id': 'microsoft/Phi-3-medium-128k-instruct', 'target_dir': 'phi-3-medium-128k-instruct'},
    'zephyr': {'repo_id': 'HuggingFaceH4/zephyr-7b-beta', 'target_dir': 'zephyr-7b'}
}

model = '$model'
if model not in MODELS:
    print(f'Unknown model: {model}')
    sys.exit(1)

config = MODELS[model]
models_dir = '$MODELS_DIR'
target_dir = os.path.join(models_dir, config['target_dir'])
os.makedirs(target_dir, exist_ok=True)

# Login if token available
token = os.environ.get('HF_TOKEN')
if token:
    print(f'Using HF_TOKEN from environment')
    login(token=token)
else:
    print('No HF_TOKEN available, attempting anonymous download')

# Download directly to target_dir
try:
    snapshot_download(
        repo_id=config['repo_id'],
        local_dir=target_dir,
        token=token,
        resume_download=True,
        retry=3
    )
    print(f'Successfully downloaded {model} to {target_dir}')
except Exception as e:
    print(f'Error downloading {model}: {e}')
    sys.exit(1)
"
    if [ $? -eq 0 ]; then
        echo "✅ Successfully downloaded $model"
    else
        echo "❌ Failed to download $model"
    fi
done

# Deactivate the virtualenv
deactivate

echo "Model download completed!"
echo "Models are stored in: $MODELS_DIR"
ls -la "$MODELS_DIR"
EOF

chmod +x download_models_directly.sh

echo "================================================================"
echo "Fixes applied! You can now try one of these approaches:"
echo ""
echo "1. Run the direct model download script (most reliable):"
echo "   ./download_models_directly.sh"
echo ""
echo "2. Try the installation again:"
echo "   ./manage_sting.sh start"
echo ""
echo "3. If you still have issues, make sure your HF_TOKEN is valid:"
echo "   ./set_hf_token.sh your_token_here"
echo "================================================================"