#!/bin/bash
# Script to clean up model download directories and temporary files

set -e

echo "=== Cleaning up model download directories ==="

# Get the correct model directory from config.yml
cd "$(dirname "$0")/.."
CONFIG_DIR="${HOME}/.sting-ce/conf"
if [ -f "${CONFIG_DIR}/config.yml" ]; then
    MODELS_DIR=$(grep -E '^[[:space:]]*models_dir:' "${CONFIG_DIR}/config.yml" | head -n1 | cut -d: -f2- | tr -d ' "')
    MODELS_DIR="${MODELS_DIR/#\~/$HOME}"  # Expand tilde if present
else
    # Default location on macOS
    MODELS_DIR="${HOME}/Downloads/llm_models"
fi

echo "Using models directory: $MODELS_DIR"

# Check for alternate/misspelled model directories
ALTERNATE_DIRS=(
    "${HOME}/Downloads/llm-models"
    "${HOME}/Downloads/LLM_models"
    "${HOME}/Downloads/LLM-models"
    "${HOME}/Downloads/llm models"
)

for dir in "${ALTERNATE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Found alternate model directory: $dir"
        
        # Check if it's empty or has content
        if [ "$(ls -A "$dir" 2>/dev/null)" ]; then
            SIZE=$(du -sh "$dir" | cut -f1)
            echo "Directory contains files ($SIZE)"
            
            read -p "Do you want to delete this directory? (y/n): " CONFIRM
            if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
                echo "Deleting directory: $dir"
                rm -rf "$dir"
                echo "Directory deleted."
            else
                echo "Skipping deletion."
            fi
        else
            echo "Directory is empty, removing it."
            rmdir "$dir"
        fi
    fi
done

# Clean up temporary download directories
TEMP_DIRS=(
    "/tmp/model_downloads"
    "${MODELS_DIR}/.tmp_downloads"
)

for dir in "${TEMP_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "Found temporary download directory: $dir"
        echo "Cleaning up temporary directory..."
        rm -rf "$dir"
        echo "Temporary directory cleaned."
    fi
done

# Check for any duplicate model directories
echo "Checking for duplicate model directories within $MODELS_DIR..."
if [ -d "$MODELS_DIR" ]; then
    for model_dir in "$MODELS_DIR"/*; do
        if [ -d "$model_dir" ]; then
            BASE_NAME=$(basename "$model_dir")
            SIMILAR_DIRS=$(find "$MODELS_DIR" -type d -iname "$BASE_NAME*" | grep -v "^$model_dir$" || true)
            
            if [ -n "$SIMILAR_DIRS" ]; then
                echo "Found potentially duplicate directories for $(basename "$model_dir"):"
                echo "$SIMILAR_DIRS"
                
                for dup_dir in $SIMILAR_DIRS; do
                    SIZE=$(du -sh "$dup_dir" | cut -f1)
                    echo "Duplicate directory: $dup_dir ($SIZE)"
                    
                    read -p "Do you want to delete this directory? (y/n): " CONFIRM
                    if [[ "$CONFIRM" =~ ^[Yy]$ ]]; then
                        echo "Deleting directory: $dup_dir"
                        rm -rf "$dup_dir"
                        echo "Directory deleted."
                    else
                        echo "Skipping deletion."
                    fi
                done
            fi
        fi
    done
fi

echo ""
echo "=== Cleanup complete ==="
echo "Current model directory size:"
du -sh "$MODELS_DIR"

echo ""
echo "Model directories remaining:"
ls -la "$MODELS_DIR"