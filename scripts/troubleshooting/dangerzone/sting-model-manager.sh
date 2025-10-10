#!/bin/bash

# STING Model Manager - Easy switching between model modes
# Usage: ./sting-model-manager.sh [small|performance|status|switch]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Model configurations
SMALL_MODELS="deepseek-1.5b,tinyllama,dialogpt"
PERFORMANCE_MODELS="llama3,phi3,zephyr"

# Function to print colored output
print_color() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check current model mode
check_current_mode() {
    if docker ps | grep -q "deepseek-service\|tinyllama-service"; then
        echo "small"
    elif docker ps | grep -q "llama3-service\|phi3-service"; then
        echo "performance"
    else
        echo "none"
    fi
}

# Function to show status
show_status() {
    local current_mode=$(check_current_mode)
    
    print_color "$BLUE" "=== STING Model Status ==="
    echo ""
    
    if [ "$current_mode" = "none" ]; then
        print_color "$YELLOW" "No model services are currently running."
    else
        print_color "$GREEN" "Current mode: $current_mode"
        echo ""
        print_color "$BLUE" "Running model services:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "service|NAME" | grep -v "kratos\|vault\|db\|app"
    fi
    
    echo ""
    print_color "$BLUE" "Available models in $HOME/Downloads/llm_models:"
    if [ -d "$HOME/Downloads/llm_models" ]; then
        ls -lh "$HOME/Downloads/llm_models" | grep "^d" | awk '{print "  - " $9 " (" $5 ")"}'
    else
        print_color "$YELLOW" "  Models directory not found"
    fi
}

# Function to download small models
download_small_models() {
    print_color "$BLUE" "Downloading small models..."
    if [ -f "./download_optimized_models.sh" ]; then
        ./download_optimized_models.sh
    else
        print_color "$RED" "Error: download_optimized_models.sh not found!"
        exit 1
    fi
}

# Function to switch to small models
switch_to_small() {
    print_color "$BLUE" "Switching to small models mode..."
    
    # Check if models exist
    if [ ! -d "$HOME/Downloads/llm_models/DeepSeek-R1-Distill-Qwen-1.5B" ]; then
        print_color "$YELLOW" "Small models not found. Would you like to download them?"
        read -p "Download small models now? [y/N]: " download_choice
        if [[ $download_choice =~ ^[Yy]$ ]]; then
            download_small_models
        else
            print_color "$RED" "Cannot switch to small models without downloading them first."
            exit 1
        fi
    fi
    
    # Stop current services
    print_color "$YELLOW" "Stopping current services..."
    docker compose down || true
    
    # Start with small models configuration
    print_color "$GREEN" "Starting small model services..."
    docker compose -f docker-compose.yml -f docker-compose.small-models.yml up -d
    
    print_color "$GREEN" "✅ Switched to small models mode!"
}

# Function to switch to performance models
switch_to_performance() {
    print_color "$BLUE" "Switching to performance models mode..."
    
    # Check system resources
    total_ram=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$total_ram" -lt 16 ]; then
        print_color "$YELLOW" "⚠️  Warning: Performance mode requires at least 16GB RAM. You have ${total_ram}GB."
        read -p "Continue anyway? [y/N]: " continue_choice
        if [[ ! $continue_choice =~ ^[Yy]$ ]]; then
            exit 0
        fi
    fi
    
    # Check if models exist
    if [ ! -d "$HOME/Downloads/llm_models/llama-3-8b" ]; then
        print_color "$YELLOW" "Performance models not found. These are large downloads (40-60GB)."
        print_color "$YELLOW" "Please run './manage_sting.sh download_models' to download them."
        exit 1
    fi
    
    # Stop current services
    print_color "$YELLOW" "Stopping current services..."
    docker compose down || true
    
    # Start with performance models configuration
    print_color "$GREEN" "Starting performance model services..."
    docker compose -f docker-compose.yml -f docker-compose.performance-models.yml up -d
    
    print_color "$GREEN" "✅ Switched to performance models mode!"
}

# Function to show help
show_help() {
    print_color "$BLUE" "STING Model Manager"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  small       - Switch to small models (DeepSeek 1.5B, TinyLlama, DialoGPT)"
    echo "  performance - Switch to performance models (Llama3 8B, Phi3 14B, Zephyr 7B)"
    echo "  status      - Show current model mode and available models"
    echo "  download    - Download small models"
    echo "  help        - Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 small      # Switch to small, fast models"
    echo "  $0 status     # Check current mode"
    echo ""
    echo "Model Comparison:"
    echo "  Small Models:       ~5GB total, fast loading, good for development"
    echo "  Performance Models: ~60GB total, best quality, requires 32GB+ RAM"
}

# Main logic
case "${1:-status}" in
    small)
        switch_to_small
        ;;
    performance)
        switch_to_performance
        ;;
    status)
        show_status
        ;;
    download)
        download_small_models
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        print_color "$RED" "Unknown command: $1"
        show_help
        exit 1
        ;;
esac