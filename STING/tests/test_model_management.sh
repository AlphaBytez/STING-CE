#!/bin/bash
# test_model_management.sh - Tests for model management module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_models"
export CONFIG_DIR="/tmp/test_sting_models/conf"
export LOG_FILE="/tmp/test_sting_models.log"
export STING_MODELS_DIR="/tmp/test_models"
export HF_TOKEN="test_token"

# Source the module
source ../lib/model_management.sh

# Test counter
tests_passed=0
tests_failed=0

# Test helper
run_test() {
    local test_name="$1"
    local test_command="$2"
    
    echo -n "Testing $test_name... "
    if eval "$test_command"; then
        echo "PASSED"
        ((tests_passed++))
    else
        echo "FAILED"
        ((tests_failed++))
    fi
}

# Setup test environment
setup_test_env() {
    rm -rf "$INSTALL_DIR" "$STING_MODELS_DIR"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$CONFIG_DIR/secrets"
    
    # Create mock HF token file
    echo "test_hf_token_from_file" > "$CONFIG_DIR/secrets/hf_token.txt"
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR" "$STING_MODELS_DIR"
}

# Mock commands
mktemp() {
    case "$*" in
        "-d"*) echo "/tmp/mock_temp_dir_$$" ;;
        *) echo "/tmp/mock_temp_file_$$" ;;
    esac
}

docker() {
    case "$1" in
        "run")
            case "$*" in
                *"download_models"*) 
                    echo "Mock downloading models..."
                    # Create mock model directory
                    mkdir -p "$STING_MODELS_DIR/tinyllama"
                    echo "Mock model files" > "$STING_MODELS_DIR/tinyllama/model.bin"
                    return 0
                    ;;
                *) echo "Mock docker run $*"; return 0 ;;
            esac
            ;;
        *) echo "Mock docker $*"; return 0 ;;
    esac
}

rm() {
    echo "Mock rm $*"
    # Actually remove test directories
    command rm "$@" 2>/dev/null || true
}

mkdir() {
    echo "Mock mkdir $*"
    command mkdir -p "$@" 2>/dev/null || true
}

chmod() {
    echo "Mock chmod $*"
    return 0
}

# Test create_temp_dir
test_create_temp_dir() {
    local temp_dir=$(create_temp_dir)
    [[ -n "$temp_dir" && "$temp_dir" == *"mock_temp_dir"* ]]
}

# Test cleanup_temp_dir
test_cleanup_temp_dir() {
    cleanup_temp_dir "/tmp/mock_test_dir"
}

# Test ensure_models_dir with default
test_ensure_models_dir_default() {
    unset STING_MODELS_DIR
    ensure_models_dir
    [[ -n "$STING_MODELS_DIR" ]]
}

# Test ensure_models_dir with existing
test_ensure_models_dir_existing() {
    export STING_MODELS_DIR="/tmp/test_models"
    ensure_models_dir
    [[ "$STING_MODELS_DIR" == "/tmp/test_models" ]]
}

# Test download_models with small mode
test_download_models_small() {
    ensure_models_dir
    download_models "small"
}

# Test download_models with performance mode
test_download_models_performance() {
    ensure_models_dir
    download_models "performance"
}

# Test download_models with minimal mode
test_download_models_minimal() {
    ensure_models_dir
    download_models "minimal"
}

# Test download_models with invalid mode (should default)
test_download_models_invalid() {
    ensure_models_dir
    download_models "invalid_mode"
}

# Run all tests
echo "Running model management module tests..."
echo "========================================"

setup_test_env

run_test "create_temp_dir" test_create_temp_dir
run_test "cleanup_temp_dir" test_cleanup_temp_dir
run_test "ensure_models_dir_default" test_ensure_models_dir_default
run_test "ensure_models_dir_existing" test_ensure_models_dir_existing
run_test "download_models_small" test_download_models_small
run_test "download_models_performance" test_download_models_performance
run_test "download_models_minimal" test_download_models_minimal
run_test "download_models_invalid" test_download_models_invalid

cleanup_test_env

echo "========================================"
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed