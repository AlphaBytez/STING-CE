#!/bin/bash
# Script to ensure proper model directory setup and cleanup temporary files

set -e

echo "=== Ensuring proper model directory setup ==="

# Navigate to STING directory
cd "$(dirname "$0")/.."

# Get the model directory from config.yml
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

echo "Current model directory: $MODELS_DIR"

# Make sure the models directory exists
if [ ! -d "$MODELS_DIR" ]; then
    echo "Creating models directory: $MODELS_DIR"
    mkdir -p "$MODELS_DIR"
fi

# Clean up any temporary download directories
TEMP_DIRS=(
    "/tmp/model_downloads"
    "/tmp/sting_model_downloads"
    "${MODELS_DIR}/.tmp_downloads"
)

for dir in "${TEMP_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Found temporary download directory: $dir"
        echo "Cleaning up..."
        rm -rf "$dir"
        echo "Temporary directory cleaned."
    fi
done

# Check for case sensitivity issues
if [[ "$(uname)" == "Darwin" ]]; then
    base_dir=$(dirname "$MODELS_DIR")
    dir_name=$(basename "$MODELS_DIR")
    
    # macOS bash doesn't support uppercase/lowercase conversion with ^^/,,
    # So we'll use explicit variants
    possible_variants=("$dir_name" "llm_models" "llm-models" "LLM_MODELS" "LLM-MODELS" "llm_Models" "Llm_models")
    
    for variant in "${possible_variants[@]}"; do
        variant_path="$base_dir/$variant"
        if [ -d "$variant_path" ] && [ "$variant_path" != "$MODELS_DIR" ]; then
            echo "Found case variant directory: $variant_path"
            size=$(du -sh "$variant_path" 2>/dev/null | cut -f1)
            echo "Directory size: $size"
            
            read -p "This directory might contain duplicate models. Do you want to delete it? (y/n): " CONFIRM
            if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
                echo "Deleting directory: $variant_path"
                rm -rf "$variant_path"
                echo "Directory deleted."
            fi
        fi
    done
fi

# Update config.yml to ensure correct path
if [ -f "${CONFIG_DIR}/config.yml" ]; then
    echo "Updating config.yml to use canonical path: $MODELS_DIR"
    sed -i.bak "s|^[[:space:]]*models_dir:.*|  models_dir: $MODELS_DIR|" "${CONFIG_DIR}/config.yml"
fi

# Update Docker Compose configuration to use the correct volume mapping
echo "Ensuring docker-compose.yml uses the correct model path..."
if [ -f "docker-compose.yml" ]; then
    # First check if llm_model_data volume is being used
    if grep -q "llm_model_data:" docker-compose.yml; then
        echo "Found llm_model_data volume in docker-compose.yml"
        echo "Removing redundant volume..."
        sed -i.bak 's|llm_model_data:.*|# Removed llm_model_data volume - models are directly mapped from host STING_MODELS_DIR instead|' docker-compose.yml
    fi
fi

echo "Ensure environment variables are set correctly"
ENV_FILE="${HOME}/.sting-ce/.env"
if [ -f "$ENV_FILE" ]; then
    if grep -q "STING_MODELS_DIR=" "$ENV_FILE"; then
        sed -i.bak "s|STING_MODELS_DIR=.*|STING_MODELS_DIR=$MODELS_DIR|" "$ENV_FILE"
    else
        echo "STING_MODELS_DIR=$MODELS_DIR" >> "$ENV_FILE"
    fi
    echo "Updated $ENV_FILE with STING_MODELS_DIR=$MODELS_DIR"
fi

echo "Setting permissions on model directory..."
chmod -R 755 "$MODELS_DIR" 2>/dev/null || echo "Warning: Could not set permissions on model directory"

echo ""
echo "=== Setup complete ==="
echo "Model directory: $MODELS_DIR"
echo ""
echo "To start installation with the correct model path:"
echo "  export STING_MODELS_DIR=\"$MODELS_DIR\""
echo "  ./manage_sting.sh start"
echo ""
echo "The system has been configured to use the canonical model path."