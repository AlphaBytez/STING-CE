#!/bin/bash
# Script to check all possible HF_TOKEN locations and diagnose issues

set -e

echo "=== Checking all HF_TOKEN locations ==="

# Define all possible token locations
ROOT_DIR="$(dirname "$0")/.."
cd "$ROOT_DIR"

INSTALL_DIR="${HOME}/.sting-ce"
SOURCE_DIR="$(pwd)"

TOKEN_LOCATIONS=(
    # Project root locations
    "${SOURCE_DIR}/.env"
    
    # Installation locations
    "${INSTALL_DIR}/.env"
    "${INSTALL_DIR}/env/hf_token.env"
    "${INSTALL_DIR}/env/llm-gateway.env"
    "${INSTALL_DIR}/env/llama3.env"
    "${INSTALL_DIR}/env/phi3.env"
    "${INSTALL_DIR}/env/zephyr.env"
    
    # Configuration locations
    "${INSTALL_DIR}/conf/env/hf_token.env"
    "${INSTALL_DIR}/conf/config.yml"
    
    # Local environment
    "${HOME}/.sting-ce/env/hf_token.env"
)

# Check each location
found_token=false
for location in "${TOKEN_LOCATIONS[@]}"; do
    if [ -f "$location" ]; then
        if grep -q "HF_TOKEN" "$location" 2>/dev/null; then
            token_value=$(grep "HF_TOKEN" "$location" | cut -d'=' -f2 | tr -d '"' | tr -d "'" | tr -d ' ')
            masked=""
            if [ -n "$token_value" ]; then
                length=${#token_value}
                if [ $length -gt 8 ]; then
                    masked="${token_value:0:4}...${token_value: -4}"
                else
                    masked="[too short to mask]"
                fi
                echo "✅ Found token in $location: $masked ($length chars)"
                found_token=true
            else
                echo "❌ Token entry exists in $location but is empty"
            fi
        else
            echo "❌ No token found in $location"
        fi
    else
        echo "🔶 File does not exist: $location"
    fi
done

# Check environment variable
if [ -n "${HF_TOKEN:-}" ]; then
    length=${#HF_TOKEN}
    masked="${HF_TOKEN:0:4}...${HF_TOKEN: -4}"
    echo "✅ HF_TOKEN environment variable is set: $masked ($length chars)"
else
    echo "❌ HF_TOKEN environment variable is not set"
fi

# Diagnose install directory structure
echo -e "\n=== Installation Directory Structure ==="
if [ -d "${INSTALL_DIR}" ]; then
    echo "✅ Installation directory exists: ${INSTALL_DIR}"
    
    # Check important subdirectories
    for dir in "env" "conf" "conf/env"; do
        if [ -d "${INSTALL_DIR}/$dir" ]; then
            echo "✅ Directory exists: ${INSTALL_DIR}/$dir"
        else
            echo "❌ Directory missing: ${INSTALL_DIR}/$dir"
        fi
    done
else
    echo "❌ Installation directory does not exist: ${INSTALL_DIR}"
fi

# Check model directory
echo -e "\n=== Model Directory Check ==="
if [ -f "${INSTALL_DIR}/conf/config.yml" ]; then
    models_dir=$(grep -E '^[[:space:]]*models_dir:' "${INSTALL_DIR}/conf/config.yml" | head -n1 | cut -d: -f2- | tr -d ' "')
    models_dir="${models_dir/#\~/$HOME}"  # Expand tilde if present
    
    if [ -n "$models_dir" ]; then
        echo "Found models_dir in config.yml: $models_dir"
        
        if [ -d "$models_dir" ]; then
            echo "✅ Models directory exists"
            echo "Contents:"
            ls -la "$models_dir"
        else
            echo "❌ Models directory does not exist: $models_dir"
        fi
    else
        echo "❌ No models_dir found in config.yml"
    fi
else
    echo "❌ config.yml not found at ${INSTALL_DIR}/conf/config.yml"
fi

echo -e "\n=== Environment File Check ==="
for env_file in "${SOURCE_DIR}/.env" "${INSTALL_DIR}/.env"; do
    if [ -f "$env_file" ]; then
        echo "Contents of $env_file:"
        # Print contents without displaying full token values
        sed 's/\(HF_TOKEN=\)[^[:space:]]*/\1[masked]/g' "$env_file"
    else
        echo "❌ Environment file not found: $env_file"
    fi
done

echo -e "\n=== Diagnostic Complete ==="
if [ "$found_token" = true ]; then
    echo "✅ HF_TOKEN found in at least one location"
    echo "To ensure it's used correctly, try:"
    echo "  export HF_TOKEN=\"your_token_here\""
    echo "  ./manage_sting.sh start"
else
    echo "❌ No valid HF_TOKEN found in any location"
    echo "Please set your HF_TOKEN with:"
    echo "  echo \"HF_TOKEN=your_token_here\" > .env"
    echo "  export HF_TOKEN=\"your_token_here\""
    echo "  ./manage_sting.sh start"
fi