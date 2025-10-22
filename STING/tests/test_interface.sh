#!/bin/bash
# test_interface.sh - Tests for interface module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_interface"
export CONFIG_DIR="/tmp/test_sting_interface/conf"
export LOG_FILE="/tmp/test_sting_interface.log"

# Source the module
source ../lib/interface.sh

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
    rm -rf "$INSTALL_DIR"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$CONFIG_DIR"
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR"
}

# Mock functions for testing
docker() {
    echo "Mock docker $*"
    return 0
}

# Test show_help
test_show_help() {
    # Capture output to verify it contains expected help text
    local help_output=$(show_help 2>&1)
    [[ "$help_output" == *"Usage: $0"* && "$help_output" == *"Commands:"* ]]
}

# Test main function with help argument
test_main_help() {
    # Test that main shows help for --help flag
    local output=$(main --help 2>&1)
    [[ "$output" == *"Usage:"* ]]
}

# Test main function with invalid command
test_main_invalid_command() {
    # Test that main shows help for invalid commands
    local output=$(main invalid_command 2>&1)
    [[ "$output" == *"Unknown command"* ]]
}

# Test main function with start command (mock)
test_main_start_command() {
    # Mock the start_services function
    start_services() {
        echo "Mock start services"
        return 0
    }
    
    # Test start command
    local output=$(main start 2>&1)
    [[ "$output" == *"Mock start services"* ]]
}

# Test main function with version flag
test_main_version() {
    # Test version display
    local output=$(main --version 2>&1)
    [[ "$output" == *"STING"* ]]
}

# Run all tests
echo "Running interface module tests..."
echo "================================="

setup_test_env

run_test "show_help" test_show_help
run_test "main_help" test_main_help
run_test "main_invalid_command" test_main_invalid_command
run_test "main_start_command" test_main_start_command
run_test "main_version" test_main_version

cleanup_test_env

echo "================================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed