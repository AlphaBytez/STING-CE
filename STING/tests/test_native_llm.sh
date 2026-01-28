#!/bin/bash
# test_native_llm.sh - Tests for native LLM module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_native_llm"
export CONFIG_DIR="/tmp/test_sting_native_llm/conf"
export LOG_FILE="/tmp/test_sting_native_llm.log"
export STING_MODELS_DIR="/tmp/test_models"

# Mock log_message function for tests
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Source the module
source ../lib/native_llm.sh

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
    mkdir -p "$INSTALL_DIR/run"
    mkdir -p "$INSTALL_DIR/llm_service"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$STING_MODELS_DIR"
    
    # Create mock PID file
    echo "12345" > "$NATIVE_LLM_PID_FILE"
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR" "$STING_MODELS_DIR"
}

# Mock commands
python3() {
    case "$*" in
        *"server.py"*) 
            echo "Mock Python LLM server started"
            # Simulate background process
            echo $$ > "$NATIVE_LLM_PID_FILE"
            return 0
            ;;
        *) echo "Mock python3 $*"; return 0 ;;
    esac
}

kill() {
    case "$*" in
        *"12345"*) echo "Mock kill $*"; return 0 ;;
        *) echo "Mock kill $*"; return 1 ;;
    esac
}

ps() {
    case "$*" in
        *"12345"*) echo "12345 python3 server.py"; return 0 ;;
        *) echo ""; return 1 ;;
    esac
}

curl() {
    case "$*" in
        *"localhost:8085/health"*) echo '{"status": "healthy"}'; return 0 ;;
        *) echo "Mock curl response"; return 0 ;;
    esac
}

sleep() {
    # Speed up tests
    return 0
}

# Test is_native_llm_running with running service
test_is_native_llm_running_true() {
    is_native_llm_running
}

# Test is_native_llm_running with stopped service
test_is_native_llm_running_false() {
    rm -f "$NATIVE_LLM_PID_FILE"
    ! is_native_llm_running
}

# Test get_native_llm_status
test_get_native_llm_status() {
    local status=$(get_native_llm_status)
    [[ "$status" == *"running"* ]]
}

# Test stop_native_llm_service
test_stop_native_llm_service() {
    stop_native_llm_service
}

# Test start_native_llm_service
test_start_native_llm_service() {
    # Remove PID file first
    rm -f "$NATIVE_LLM_PID_FILE"
    
    start_native_llm_service
}

# Test restart_native_llm_service
test_restart_native_llm_service() {
    restart_native_llm_service
}

# Run all tests
echo "Running native LLM module tests..."
echo "=================================="

setup_test_env

run_test "is_native_llm_running_true" test_is_native_llm_running_true
run_test "is_native_llm_running_false" test_is_native_llm_running_false
run_test "get_native_llm_status" test_get_native_llm_status
run_test "stop_native_llm_service" test_stop_native_llm_service
run_test "start_native_llm_service" test_start_native_llm_service
run_test "restart_native_llm_service" test_restart_native_llm_service

cleanup_test_env

echo "=================================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed