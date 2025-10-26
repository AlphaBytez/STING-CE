#!/bin/bash
# Test script for logging.sh module

# Set up test environment
export INSTALL_DIR="/tmp/sting_test_logging"
export LOG_DIR="$INSTALL_DIR/logs"
export LOG_FILE="$LOG_DIR/test.log"

# Source the logging module
source "$(dirname "$0")/../lib/logging.sh"

echo "=== Testing Logging Module ==="

# Test 1: init_logging
echo -n "Testing init_logging... "
init_logging
if [ -f "$LOG_FILE" ]; then
    echo "PASS"
else
    echo "FAIL (log file not created)"
fi

# Test 2: log_message
echo -n "Testing log_message... "
log_message "Test message"
if grep -q "Test message" "$LOG_FILE"; then
    echo "PASS"
else
    echo "FAIL (message not logged)"
fi

# Test 3: log levels
echo -n "Testing log levels... "
log_message "Success test" "SUCCESS" >/dev/null 2>&1
log_message "Error test" "ERROR" >/dev/null 2>&1
if grep -q "Success test" "$LOG_FILE" && grep -q "Error test" "$LOG_FILE"; then
    echo "PASS"
else
    echo "FAIL (log levels not working)"
fi

# Test 4: ensure_log_directory
echo -n "Testing ensure_log_directory... "
rm -rf "$LOG_DIR"
ensure_log_directory
if [ -d "$LOG_DIR" ] && [ -f "$LOG_FILE" ]; then
    echo "PASS"
else
    echo "FAIL (directory/file not created)"
fi

# Test 5: rotate_log_file
echo -n "Testing rotate_log_file... "
# Create a large log file
for i in {1..1000}; do
    echo "Line $i - This is a test line to make the log file larger" >> "$LOG_FILE"
done
LOG_MAX_SIZE_MB=1 rotate_log_file  # Force rotation with 1MB limit
if ls "${LOG_FILE}".* >/dev/null 2>&1; then
    echo "PASS"
else
    echo "FAIL (log not rotated)"
fi

# Cleanup
rm -rf "$INSTALL_DIR"

echo "=== Logging Module Tests Complete ==="