#!/bin/bash
# Test script for core.sh module

# Set up test environment
export INSTALL_DIR="/tmp/sting_test"
export LOG_DIR="$INSTALL_DIR/logs"
export CONFIG_DIR="$INSTALL_DIR/conf"
export LOG_FILE="$LOG_DIR/test.log"

# Source the modules
source "$(dirname "$0")/../lib/logging.sh"
source "$(dirname "$0")/../lib/core.sh"

# Initialize logging for tests
init_logging

echo "=== Testing Core Module ==="

# Test 1: check_root
echo -n "Testing check_root... "
if check_root; then
    echo "PASS (allowed on current platform)"
else
    echo "FAIL (should have passed on macOS or as root)"
fi

# Test 2: get_app_env
echo -n "Testing get_app_env... "
mkdir -p "$CONFIG_DIR"
echo "APP_ENV: testing" > "$CONFIG_DIR/config.yml"
result=$(get_app_env)
if [ "$result" = "testing" ]; then
    echo "PASS"
else
    echo "FAIL (expected 'testing', got '$result')"
fi

# Test 3: create_checksum and verify_checksum
echo -n "Testing checksum functions... "
test_file="$INSTALL_DIR/test.txt"
echo "test content" > "$test_file"
if create_checksum "$test_file"; then
    if verify_checksum "$test_file"; then
        echo "PASS"
    else
        echo "FAIL (verify failed)"
    fi
else
    echo "FAIL (create failed)"
fi

# Test 4: check_disk_space
echo -n "Testing check_disk_space... "
MIN_DISK_SPACE_MB=1 check_disk_space
if [ $? -eq 0 ]; then
    echo "PASS"
else
    echo "FAIL"
fi

# Cleanup
rm -rf "$INSTALL_DIR"

echo "=== Core Module Tests Complete ==="