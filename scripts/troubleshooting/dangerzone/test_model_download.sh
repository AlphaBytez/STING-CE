#!/bin/bash
# Script to test model downloading independently of the full installation

set -e

# Navigate to STING directory
cd "$(dirname "$0")/.."

# Source common functions from manage_sting.sh
source_function() {
    local file="$1"
    local fn="$2"
    local pattern="^$fn[[:space:]]*\(\)"
    
    # Extract the function and all its dependencies
    awk "/$pattern/,/^}/" "$file"
}

# Define a simplified log function
log_message() {
    local msg="$1"
    local level="${2:-INFO}"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] - $level: $msg"
}

# Clean up any temporary directories
clean_temp_dirs() {
    for dir in "/tmp/model_downloads" "/tmp/sting_model_downloads"; do
        if [ -d "$dir" ]; then
            log_message "Cleaning up temporary directory: $dir"
            rm -rf "$dir"
        fi
    done
}

# Check which models to download
if [ $# -eq 0 ]; then
    MODELS=("llama3")  # Default to just llama3 for testing
else
    MODELS=("$@")  # Use command line arguments
fi

# Default models directory
if [[ "$(uname)" == "Darwin" ]]; then
    DEFAULT_MODELS_DIR="$HOME/Downloads/llm_models"
else
    DEFAULT_MODELS_DIR="/opt/models"
fi

# Get models directory from config or environment
CONFIG_DIR="${HOME}/.sting-ce/conf"
if [ -f "${CONFIG_DIR}/config.yml" ]; then
    CONFIG_MODELS_DIR=$(grep -E '^[[:space:]]*models_dir:' "${CONFIG_DIR}/config.yml" | head -n1 | cut -d: -f2- | tr -d ' "')
    if [ -n "$CONFIG_MODELS_DIR" ]; then
        MODELS_DIR="${CONFIG_MODELS_DIR/#\~/$HOME}"  # Expand tilde if present
    fi
fi

# Environment variable takes precedence
if [ -n "${STING_MODELS_DIR:-}" ]; then
    MODELS_DIR="$STING_MODELS_DIR"
else
    MODELS_DIR="${MODELS_DIR:-$DEFAULT_MODELS_DIR}"
fi

log_message "Using models directory: $MODELS_DIR"

# Create the directory if it doesn't exist
if [ ! -d "$MODELS_DIR" ]; then
    log_message "Creating models directory: $MODELS_DIR"
    mkdir -p "$MODELS_DIR"
fi

# Set up Python environment
VENV_DIR="${HOME}/.sting-ce/venv"
if [ ! -d "$VENV_DIR" ]; then
    log_message "Python virtual environment not found, creating..."
    python3 -m venv "$VENV_DIR"
fi

# Activate the virtualenv and install dependencies
source "$VENV_DIR/bin/activate"

# Install required packages for model downloading
log_message "Installing required Python packages..."
pip install --upgrade pip
pip install requests tqdm huggingface_hub

# Test each model download
for model in "${MODELS[@]}"; do
    log_message "Testing download of model: $model"
    
    # Clean up any existing temporary directories
    clean_temp_dirs
    
    # Check for HF_TOKEN in .env file in the project root
    if [ -z "${HF_TOKEN}" ] && [ -f ".env" ]; then
        HF_TOKEN_FROM_ENV=$(grep -E '^HF_TOKEN=' .env | cut -d'=' -f2 | tr -d '"' || echo "")
        if [ -n "$HF_TOKEN_FROM_ENV" ]; then
            log_message "Found HF_TOKEN in .env file, using it for downloads"
            export HF_TOKEN="$HF_TOKEN_FROM_ENV"
        fi
    fi
    
    # Show token status (masked for security)
    if [ -n "${HF_TOKEN}" ]; then
        TOKEN_LENGTH=${#HF_TOKEN}
        MASKED_TOKEN="${HF_TOKEN:0:4}...${HF_TOKEN: -4}"
        log_message "Using HF_TOKEN: $MASKED_TOKEN (${TOKEN_LENGTH} characters)"
    else
        log_message "HF_TOKEN not set - downloads may fail for gated models" "WARNING"
    fi
    
    # Run the model_downloader.py script directly
    python3 llm_service/utils/model_downloader.py --download "$model" --dir "$MODELS_DIR" --verbose
    
    if [ $? -eq 0 ]; then
        log_message "Successfully downloaded model: $model" "SUCCESS"
    else
        log_message "Failed to download model: $model" "ERROR"
    fi
done

# Deactivate the virtualenv
deactivate

log_message "Model download test completed!"
log_message "Models directory: $MODELS_DIR"
du -sh "$MODELS_DIR"/*