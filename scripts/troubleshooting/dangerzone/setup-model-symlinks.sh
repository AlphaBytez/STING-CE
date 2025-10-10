#!/bin/bash
# Script to set up symlinks for the LLM models directory
# This script makes it easy to use model directories efficiently

set -e

# Load environment variables from .env if it exists
if [ -f .env ]; then
    echo "Loading environment from .env file..."
    source .env
fi

# Determine the target models directory
if [ -z "${STING_MODELS_DIR}" ]; then
    if [ -f "./conf/config.yml" ]; then
        # Try to extract from config.yml
        MODELS_DIR=$(grep -E '^[[:space:]]*models_dir:' ./conf/config.yml | head -n1 | sed 's/.*models_dir:[[:space:]]*//' | tr -d '"' | tr -d "'")
        
        # Expand ~ if present
        MODELS_DIR="${MODELS_DIR/#\~/$HOME}"
        
        if [ -n "$MODELS_DIR" ]; then
            echo "Found models_dir in config.yml: $MODELS_DIR"
            STING_MODELS_DIR="$MODELS_DIR"
        fi
    fi
    
    # If still not set, use default for the platform
    if [ -z "${STING_MODELS_DIR}" ]; then
        if [[ "$(uname)" == "Darwin" ]]; then
            # Mac default
            STING_MODELS_DIR="$HOME/Downloads/llm_models"
        else
            # Linux default
            STING_MODELS_DIR="/opt/models"
        fi
    fi
fi

echo "Using models directory: $STING_MODELS_DIR"

# Create models directory if it doesn't exist
mkdir -p "$STING_MODELS_DIR"

# Create a local symlink for convenience
if [ ! -e ./models ] || [ ! -L ./models ]; then
    echo "Creating symlink from ./models to $STING_MODELS_DIR"
    ln -sf "$STING_MODELS_DIR" ./models
else
    # Update existing symlink if it's pointing to a different location
    CURRENT_TARGET=$(readlink ./models)
    if [ "$CURRENT_TARGET" != "$STING_MODELS_DIR" ]; then
        echo "Updating symlink from $CURRENT_TARGET to $STING_MODELS_DIR"
        rm ./models
        ln -sf "$STING_MODELS_DIR" ./models
    else
        echo "Symlink already exists and is pointing to the correct location"
    fi
fi

# Update .env file if needed
if [ -f .env ]; then
    if grep -q "STING_MODELS_DIR=" .env; then
        # Update existing entry
        sed -i.bak "s|STING_MODELS_DIR=.*|STING_MODELS_DIR=$STING_MODELS_DIR|" .env
    else
        # Add new entry
        echo "STING_MODELS_DIR=$STING_MODELS_DIR" >> .env
    fi
    echo "Updated STING_MODELS_DIR in .env file"
fi

echo "Setup complete!"
echo "Models directory is set to: $STING_MODELS_DIR"
echo "Local symlink ./models points to this directory"
echo ""
echo "For Docker Compose, this directory will be mounted as a volume at /app/models"
echo ""
echo "Remember to restart your containers if they are already running:"
echo "  docker compose down && docker compose up -d"