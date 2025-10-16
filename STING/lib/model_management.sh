#!/bin/bash
#
# Model Management Module for STING-CE
# Contains functions for managing LLM model downloads and storage
#
# Dependencies: 
# - lib/logging.sh (for log_message function)
# - Docker (for model downloads)
# - HuggingFace Hub (for model repositories)
#

# Source required dependencies
if [ -z "${SOURCE_DIR}" ]; then
    SOURCE_DIR="$(cd -P "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

# Source logging functions
if [ -f "${SOURCE_DIR}/lib/logging.sh" ]; then
    source "${SOURCE_DIR}/lib/logging.sh"
else
    echo "WARNING: Could not source logging.sh, using fallback logging"
    log_message() {
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    }
fi

# Model management constants and variables
# These should be set by the calling script, but we provide defaults
: "${DEFAULT_MODELS_DIR:=/opt/models}"
: "${CONFIG_DIR:=${SOURCE_DIR}/conf}"
: "${INSTALL_DIR:=/opt/sting-ce}"

# Function to create temporary directories for model operations
create_temp_dir() {
    local temp_dir=$(mktemp -d)
    echo "$temp_dir"
}

# Function to cleanup temporary directories
cleanup_temp_dir() {
    local temp_dir="$1"
    if [ -d "$temp_dir" ]; then
        sudo rm -rf "$temp_dir"
        log_message "Cleaned up temporary directory: $temp_dir"
    fi
}

# Ensure STING_MODELS_DIR is set, falling back to a default if needed
ensure_models_dir() {
    # Try environment first, then project .env, then INSTALL_DIR/.env
    if [ -z "${STING_MODELS_DIR:-}" ]; then
        # Load from project root .env if present
        if [ -f "${SOURCE_DIR}/.env" ]; then
            STING_MODELS_DIR=$(grep -E '^[[:space:]]*STING_MODELS_DIR=' "${SOURCE_DIR}/.env" \
                | head -n1 | cut -d'=' -f2- | tr -d '"')
        fi
    fi
    if [ -z "${STING_MODELS_DIR:-}" ]; then
        # Load from INSTALL_DIR/.env if present
        if [ -f "${INSTALL_DIR}/.env" ]; then
            STING_MODELS_DIR=$(grep -E '^[[:space:]]*STING_MODELS_DIR=' "${INSTALL_DIR}/.env" \
                | head -n1 | cut -d'=' -f2- | tr -d '"')
        fi
    fi
    # Next try CONFIG_DIR/config.yml override
    if [ -z "${STING_MODELS_DIR:-}" ] && [ -f "${CONFIG_DIR}/config.yml" ]; then
        STING_MODELS_DIR=$(grep -E '^[[:space:]]*models_dir:' "${CONFIG_DIR}/config.yml" \
            | head -n1 | cut -d':' -f2- | tr -d ' "')
    fi
    # Fallback to the default models directory if still unset
    if [ -z "${STING_MODELS_DIR:-}" ]; then
        STING_MODELS_DIR="${DEFAULT_MODELS_DIR}"
    fi
    export STING_MODELS_DIR
    log_message "Using STING_MODELS_DIR: ${STING_MODELS_DIR}"
    echo "${STING_MODELS_DIR}"
}

# Function to download models with comprehensive error handling and fallback strategies
# List available and loaded models (restored from legacy)
llm_list_models() {
    log_message "Checking available models..."
    
    # Get service URL based on platform
    local service_url
    if [[ "$(uname)" == "Darwin" ]]; then
        service_url="http://localhost:8086"  # Native service
    else
        service_url="http://localhost:8080"  # Docker gateway
    fi
    
    # Check if LLM service is running
    if ! curl -sf "$service_url/health" >/dev/null 2>&1; then
        log_message "LLM service is not running or not responding" "ERROR"
        log_message "Start the service with: ./sting-llm start" "INFO"
        return 1
    fi
    
    # Get models status
    log_message "Fetching model information from LLM service..."
    local response
    if response=$(curl -sf "$service_url/models" 2>/dev/null); then
        echo -e "\n${GREEN}=== LLM Service Model Status ===${NC}"
        
        # Try to parse JSON response nicely
        if command -v python3 >/dev/null 2>&1; then
            echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        elif command -v jq >/dev/null 2>&1; then
            echo "$response" | jq . 2>/dev/null || echo "$response"
        else
            echo "$response"
        fi
    else
        log_message "Failed to get model information from LLM service" "ERROR"
        log_message "Service URL: $service_url/models" "INFO"
        return 1
    fi
    
    # Also show local model directory contents
    local models_dir="${STING_MODELS_DIR:-$HOME/Downloads/llm_models}"
    if [ -d "$models_dir" ]; then
        echo -e "\n${GREEN}=== Local Model Directory ($models_dir) ===${NC}"
        ls -la "$models_dir" 2>/dev/null || log_message "Cannot list $models_dir" "WARNING"
    else
        log_message "Local model directory not found: $models_dir" "WARNING"
    fi
}

download_models() {
    # Provide progress marker for Rich spinner
    echo "PROGRESS: Downloading LLM models"
    log_message "Downloading models..."
    
    # Skip download if models directory already has content
    if [ -d "${STING_MODELS_DIR}" ] && [ "$(ls -A "${STING_MODELS_DIR}")" ]; then
        log_message "LLM models already present in ${STING_MODELS_DIR}; skipping download"
        echo "PROGRESS: LLM models are already present, skipping download"
        return 0
    fi
    
    # Clean up temporary directories
    log_message "Cleaning up any existing temporary directories"
    local TEMP_DIRS=(
        "/tmp/model_downloads"
        "/tmp/sting_model_downloads"
    )
    
    for dir in "${TEMP_DIRS[@]}"; do
        if [ -d "$dir" ]; then
            log_message "Removing existing temporary directory: $dir"
            rm -rf "$dir"
        fi
        log_message "Creating fresh temporary directory: $dir"
        mkdir -p "$dir"
        chmod 777 "$dir"  # Ensure everyone can write to this directory
    done
    
    # Ensure STING_MODELS_DIR exists
    mkdir -p "${STING_MODELS_DIR}"
    log_message "Using models directory: ${STING_MODELS_DIR}"
    
    # Load HF_TOKEN from all possible sources
    # Priority: 1. Environment variable, 2. .env file, 3. ~/.sting-ce/conf/secrets/hf_token.txt
    if [ -z "${HF_TOKEN}" ]; then
        # Check .env file in current directory
        if [ -f ".env" ]; then
            HF_TOKEN_FROM_ENV=$(grep -E '^HF_TOKEN=' .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ' || echo "")
            if [ -n "$HF_TOKEN_FROM_ENV" ]; then
                log_message "Found HF_TOKEN in .env file, using it for downloads"
                export HF_TOKEN="$HF_TOKEN_FROM_ENV"
            fi
        fi
        
        # Check config secrets directory
        if [ -z "${HF_TOKEN}" ] && [ -f "${CONFIG_DIR}/secrets/hf_token.txt" ]; then
            log_message "Found HF_TOKEN in config secrets, using it for downloads"
            export HF_TOKEN=$(cat "${CONFIG_DIR}/secrets/hf_token.txt" | tr -d '\n')
        fi
    fi
    
    # Show token status (masked for security)
    if [ -n "${HF_TOKEN}" ]; then
        TOKEN_LENGTH=${#HF_TOKEN}
        if [ "$TOKEN_LENGTH" -gt 8 ]; then
            MASKED_TOKEN="${HF_TOKEN:0:4}...${HF_TOKEN: -4}"
            log_message "Using HF_TOKEN: $MASKED_TOKEN (${TOKEN_LENGTH} characters)"
        else
            log_message "Using HF_TOKEN (${TOKEN_LENGTH} characters)"
        fi
    else
        log_message "HF_TOKEN not set - downloads may fail for gated models" "WARNING"
    fi
    
    # Export token for subprocesses
    export HF_TOKEN
    
    # Install required packages directly in the script
    log_message "Installing required Python packages for model downloading..."
    pip install requests tqdm huggingface_hub packaging || \
    python3 -m pip install requests tqdm huggingface_hub packaging || \
    (log_message "WARNING: Failed to install packages with pip, trying system package manager" && \
     (which apt-get >/dev/null && sudo apt-get install -y python3-requests python3-tqdm) || \
     (which brew >/dev/null && brew install python-requests) || \
     log_message "WARNING: Could not install required packages with system package manager")
    
    # Download models
    log_message "Starting model downloads"
    
    # Double-check STING_MODELS_DIR is set and valid
    log_message "Checking STING_MODELS_DIR value: '${STING_MODELS_DIR}'"
    if [ -z "${STING_MODELS_DIR}" ]; then
        log_message "ERROR: STING_MODELS_DIR is empty, using default: ${DEFAULT_MODELS_DIR}" "ERROR"
        export STING_MODELS_DIR="${DEFAULT_MODELS_DIR}"
    fi
    
    # Look for the variable in .env file if still empty
    if [ -z "${STING_MODELS_DIR}" ] && [ -f ".env" ]; then
        log_message "Trying to read STING_MODELS_DIR from .env file"
        MODELS_DIR_FROM_ENV=$(grep -E '^STING_MODELS_DIR=' .env | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ' || echo "")
        if [ -n "$MODELS_DIR_FROM_ENV" ]; then
            log_message "Found STING_MODELS_DIR in .env file: ${MODELS_DIR_FROM_ENV}"
            export STING_MODELS_DIR="$MODELS_DIR_FROM_ENV"
        fi
    fi
    
    # Final fallback to DEFAULT_MODELS_DIR
    if [ -z "${STING_MODELS_DIR}" ]; then
        log_message "STING_MODELS_DIR still empty, using default location"
        export STING_MODELS_DIR="${DEFAULT_MODELS_DIR}"
        
        # Add to .env file if it doesn't already exist
        if [ -f ".env" ] && ! grep -q "^STING_MODELS_DIR=" ".env"; then
            log_message "Adding STING_MODELS_DIR to .env file"
            echo -e "\n# Path to LLM models - this will be used by Docker containers and local development" >> ".env"
            echo "STING_MODELS_DIR=${DEFAULT_MODELS_DIR}" >> ".env"
        fi
    fi
    
    log_message "Models will be downloaded to: ${STING_MODELS_DIR}"
    mkdir -p "${STING_MODELS_DIR}"
    
    # Check for model mode configuration
    local model_mode="${MODEL_MODE:-small}"
    local models=()
    
    # Allow override via environment variable
    if [ -n "${DOWNLOAD_MODELS}" ]; then
        IFS=',' read -ra models <<< "${DOWNLOAD_MODELS}"
        log_message "Using custom model list: ${models[*]}"
    else
        # Default model sets based on mode
        case "${model_mode}" in
            small|default)
                models=("deepseek-1.5b" "tinyllama" "dialogpt")
                log_message "Using small/default model set for better performance"
                ;;
            performance|large)
                models=("llama3" "phi3" "zephyr")
                log_message "Using large/performance model set"
                ;;
            minimal)
                models=("tinyllama")
                log_message "Using minimal model set"
                ;;
            *)
                log_message "Unknown model mode: ${model_mode}, using small models" "WARNING"
                models=("deepseek-1.5b" "tinyllama" "dialogpt")
                ;;
        esac
    fi
    
    local success=true
    
    for model in "${models[@]}"; do
        log_message "Downloading model: $model"
        
        # Show debug info
        log_message "Python path: $(which python3)"
        log_message "Model downloader path: ${INSTALL_DIR}/llm_service/utils/model_downloader.py"
        log_message "Using models directory: ${STING_MODELS_DIR}"
        
        # Use direct curl download for the model files to avoid Python dependency issues
        log_message "Using direct HuggingFace download for model: ${model}"
        
        # Define model configs 
        local repo_id=""
        local target_dir=""
        
        case "${model}" in
            # Small models (default)
            deepseek-1.5b)
                repo_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B"
                target_dir="${STING_MODELS_DIR}/DeepSeek-R1-Distill-Qwen-1.5B"
                ;;
            tinyllama)
                repo_id="TinyLlama/TinyLlama-1.1B-Chat-v1.0"
                target_dir="${STING_MODELS_DIR}/TinyLlama-1.1B-Chat"
                ;;
            dialogpt)
                repo_id="microsoft/DialoGPT-medium"
                target_dir="${STING_MODELS_DIR}/DialoGPT-medium"
                ;;
            # Large models (performance mode)
            llama3)
                repo_id="meta-llama/Llama-3.1-8B"
                target_dir="${STING_MODELS_DIR}/llama-3-8b"
                ;;
            phi3)
                repo_id="microsoft/Phi-3-medium-128k-instruct"
                target_dir="${STING_MODELS_DIR}/phi-3-medium-128k-instruct"
                ;;
            zephyr)
                repo_id="HuggingFaceH4/zephyr-7b-beta"
                target_dir="${STING_MODELS_DIR}/zephyr-7b"
                ;;
            *)
                log_message "Unknown model: ${model}" "ERROR"
                continue
                ;;
        esac
        
        # Create target directory
        mkdir -p "${target_dir}"
        
        # Use a simpler approach - Docker-based downloader
        # This is more reliable than depending on local Python setup
        log_message "Running Docker-based model downloader for ${model}..."
        
        # Apply WSL2 Docker fixes if needed
        if [ -f "${SCRIPT_DIR}/docker_wsl_fix.sh" ]; then
            source "${SCRIPT_DIR}/docker_wsl_fix.sh"
            fix_docker_credential_helper >/dev/null 2>&1
        fi
        
        # Fallback image if needed
        if ! docker images | grep -q "python:3.9-slim"; then
            log_message "Pulling python:3.9-slim image as fallback for model downloads..."
            docker pull python:3.9-slim
        fi
        
        # First try to use the sting-ce-utils container if it's running
        # During installation, the utils service should be running before model downloads
        if docker ps | grep -q "sting-ce-utils"; then
            log_message "Using existing sting-ce-utils container for model downloads"
            
            if docker run --rm \
                -e HF_TOKEN="${HF_TOKEN}" \
                -v "${STING_MODELS_DIR}:/models" \
                sting-ce-utils bash -c "
                    pip install --quiet huggingface_hub tqdm requests && \
                    python -c \"
import os
from huggingface_hub import snapshot_download, login

# Authenticate with Hugging Face
if os.environ.get('HF_TOKEN'):
    login(token=os.environ['HF_TOKEN'])
    print('Authenticated with Hugging Face using token')

# Download the model
print('Downloading ${model} from ${repo_id}')
target_dir = '/models/${target_dir##*/}'
snapshot_download(
    repo_id='${repo_id}',
    local_dir=target_dir,
    token=os.environ.get('HF_TOKEN'),
    resume_download=True
)
print('Successfully downloaded ${model}')
\""; then
                log_message "Successfully downloaded ${model} model using sting-ce-utils container" "SUCCESS"
            else
                log_message "Failed to download ${model} with sting-ce-utils, falling back to python:3.9-slim" "WARNING"
                
                # Fallback to python:3.9-slim if sting-ce-utils fails
                if docker run --rm \
                    -e HF_TOKEN="${HF_TOKEN}" \
                    -v "${STING_MODELS_DIR}:/models" \
                    python:3.9-slim bash -c "
                        pip install huggingface_hub tqdm requests && \
                        python -c \"
import os
from huggingface_hub import snapshot_download, login

# Authenticate with Hugging Face
if os.environ.get('HF_TOKEN'):
    login(token=os.environ['HF_TOKEN'])
    print('Authenticated with Hugging Face using token')

# Download the model
print('Downloading ${model} from ${repo_id}')
target_dir = '/models/${target_dir##*/}'
snapshot_download(
    repo_id='${repo_id}',
    local_dir=target_dir,
    token=os.environ.get('HF_TOKEN'),
    resume_download=True
)
print('Successfully downloaded ${model}')
\""; then
                    log_message "Successfully downloaded model: $model using python:3.9-slim fallback" "SUCCESS"
                else
                    log_message "Failed to download model: $model using fallback" "ERROR"
                    log_message "HF_TOKEN length: ${#HF_TOKEN}"
                    success=false
                fi
            fi
        else
            # If sting-ce-utils is not running, use python:3.9-slim as fallback
            log_message "sting-ce-utils container not found or not running, using python:3.9-slim as fallback"
            
            if docker run --rm \
                -e HF_TOKEN="${HF_TOKEN}" \
                -v "${STING_MODELS_DIR}:/models" \
                python:3.9-slim bash -c "
                    pip install huggingface_hub tqdm requests && \
                    python -c \"
import os
from huggingface_hub import snapshot_download, login

# Authenticate with Hugging Face
if os.environ.get('HF_TOKEN'):
    login(token=os.environ['HF_TOKEN'])
    print('Authenticated with Hugging Face using token')

# Download the model
print('Downloading ${model} from ${repo_id}')
target_dir = '/models/${target_dir##*/}'
snapshot_download(
    repo_id='${repo_id}',
    local_dir=target_dir,
    token=os.environ.get('HF_TOKEN'),
    resume_download=True
)
print('Successfully downloaded ${model}')
\""; then
                log_message "Successfully downloaded model: $model using python:3.9-slim" "SUCCESS"
            else
                log_message "Failed to download model: $model" "ERROR"
                log_message "HF_TOKEN length: ${#HF_TOKEN}"
                success=false
            fi
        fi
    done
    
    # Return success or failure
    if $success; then
        log_message "All models downloaded successfully."
        echo "PROGRESS: LLM models download completed"
        du -sh "${STING_MODELS_DIR}"/* 2>/dev/null || log_message "No models found in ${STING_MODELS_DIR}"
        return 0
    else
        log_message "ERROR: Some models failed to download."
        return 1
    fi
}

# Export functions for use by other scripts
export -f create_temp_dir
export -f cleanup_temp_dir
export -f ensure_models_dir
export -f download_models