#!/bin/bash
# Script to fix model path issues by ensuring STING_MODELS_DIR points to the correct directory

set -e

echo "=== STING Model Path Fix ==="
echo "This script will update your model directory configuration to use the correct path."

# Get the absolute path to the models directory
CORRECT_MODEL_DIR="$HOME/Downloads/llm_models"
echo "Correct model directory: $CORRECT_MODEL_DIR"

# Check if the correct directory exists and has models
if [ ! -d "$CORRECT_MODEL_DIR" ]; then
  echo "ERROR: The correct model directory $CORRECT_MODEL_DIR does not exist!"
  exit 1
fi

# Count model files to verify it's the right directory
MODEL_FILES=$(find "$CORRECT_MODEL_DIR" -type f | wc -l)
if [ "$MODEL_FILES" -lt 10 ]; then
  echo "WARNING: The model directory $CORRECT_MODEL_DIR might not have all required files (only $MODEL_FILES files found)."
  echo "Do you want to continue anyway? (y/n)"
  read -r response
  if [[ ! "$response" =~ ^[Yy]$ ]]; then
    echo "Operation cancelled by user."
    exit 1
  fi
fi

echo "Updating config.yml to use the correct models directory..."
sed -i'.bak.modelpath' 's|models_dir:.*|models_dir: '"$CORRECT_MODEL_DIR"'|g' ./conf/config.yml

# Create a .env file to ensure the model path is set
echo "Creating/updating .env file with correct STING_MODELS_DIR..."
if [ -f "$HOME/.sting-ce/.env" ]; then
  # Update existing .env file
  if grep -q "STING_MODELS_DIR=" "$HOME/.sting-ce/.env"; then
    sed -i'.bak.modelpath' 's|STING_MODELS_DIR=.*|STING_MODELS_DIR='"$CORRECT_MODEL_DIR"'|g' "$HOME/.sting-ce/.env"
  else
    echo "STING_MODELS_DIR=$CORRECT_MODEL_DIR" >> "$HOME/.sting-ce/.env"
  fi
else
  # Create new .env file
  mkdir -p "$HOME/.sting-ce"
  echo "STING_MODELS_DIR=$CORRECT_MODEL_DIR" > "$HOME/.sting-ce/.env"
fi

# Export for current session
export STING_MODELS_DIR="$CORRECT_MODEL_DIR"

echo "Setting environment variable for current session: STING_MODELS_DIR=$STING_MODELS_DIR"

# Also update service environment files if they exist
if [ -d "./env" ]; then
  echo "Updating model paths in service environment files..."
  
  # Update llama3.env
  if [ -f "./env/llama3.env" ]; then
    sed -i'.bak.modelpath' 's|MODEL_PATH=.*|MODEL_PATH=/app/models/llama-3-8b|g' ./env/llama3.env
  fi
  
  # Update phi3.env
  if [ -f "./env/phi3.env" ]; then
    sed -i'.bak.modelpath' 's|MODEL_PATH=.*|MODEL_PATH=/app/models/phi-3-medium-128k-instruct|g' ./env/phi3.env
  fi
  
  # Update zephyr.env
  if [ -f "./env/zephyr.env" ]; then
    sed -i'.bak.modelpath' 's|MODEL_PATH=.*|MODEL_PATH=/app/models/zephyr-7b|g' ./env/zephyr.env
  fi
fi

echo "Model path configuration updated successfully!"
echo "Please restart the STING services with: ./manage_sting.sh restart"
echo ""
echo "To verify the correct model directory is being used, run:"
echo "docker exec sting-llm-gateway-1 ls -la /app/models"
echo ""
echo "You should see populated model directories for llama-3-8b, phi-3-medium-128k-instruct, and zephyr-7b"