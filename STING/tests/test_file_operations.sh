#!/bin/bash
# test_file_operations.sh - Tests for file operations module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_file_ops"
export CONFIG_DIR="/tmp/test_sting_file_ops/conf"
export LOG_FILE="/tmp/test_sting_file_ops.log"
export PWD="/tmp/test_source"
export SOURCE_DIR="/tmp/test_source"

# Mock log_message function for tests
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Source the module
source ../lib/file_operations.sh

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
    rm -rf "$INSTALL_DIR" "/tmp/test_source"
    mkdir -p "$INSTALL_DIR/logs"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "/tmp/test_source"
    
    # Create test files in source directory
    echo "test content" > "/tmp/test_source/test.txt"
    echo "config content" > "/tmp/test_source/config.yml"
    mkdir -p "/tmp/test_source/frontend"
    mkdir -p "/tmp/test_source/app"
    mkdir -p "/tmp/test_source/authentication"
    
    # Create test env files
    echo "DB_HOST=localhost" > "$CONFIG_DIR/db.env"
    echo "APP_HOST=localhost" > "$CONFIG_DIR/app.env"
    echo "AUTH_HOST=localhost" > "$CONFIG_DIR/authentication.env"
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR" "/tmp/test_source"
}

# Mock commands
rsync() {
    echo "Mock rsync $*"
    # Create some mock copied files
    mkdir -p "$INSTALL_DIR"
    echo "mock content" > "$INSTALL_DIR/test.txt"
    return 0
}

ln() {
    echo "Mock ln $*"
    return 0
}

chown() {
    echo "Mock chown $*"
    return 0
}

chmod() {
    echo "Mock chmod $*"
    return 0
}

whoami() {
    echo "testuser"
}

# Test ensure_directory with new directory
test_ensure_directory_new() {
    ensure_directory "/tmp/test_new_dir"
}

# Test ensure_directory with existing directory
test_ensure_directory_existing() {
    mkdir -p "/tmp/test_existing_dir"
    ensure_directory "/tmp/test_existing_dir"
}

# Test safe_remove_directory with valid path
test_safe_remove_directory_valid() {
    mkdir -p "/tmp/test_remove_dir"
    safe_remove_directory "/tmp/test_remove_dir"
}

# Test safe_remove_directory with invalid path (should fail safely)
test_safe_remove_directory_invalid() {
    ! safe_remove_directory "/etc"  # Should refuse to remove system directory
}

# Test cleanup_failed_installation
test_cleanup_failed_installation() {
    # Create mock installation directory
    mkdir -p "$INSTALL_DIR"
    echo "test" > "$INSTALL_DIR/test.txt"
    
    cleanup_failed_installation
}

# Test copy_files_to_install_dir with incremental mode
test_copy_files_incremental() {
    export INCREMENTAL_UPDATES="true"
    copy_files_to_install_dir
}

# Test copy_files_to_install_dir with full mode
test_copy_files_full() {
    unset INCREMENTAL_UPDATES
    copy_files_to_install_dir
}

# Test symlink_env_to_main_components
test_symlink_env_components() {
    # Create target directories
    mkdir -p "$INSTALL_DIR/frontend"
    mkdir -p "$INSTALL_DIR/app"
    mkdir -p "$INSTALL_DIR/authentication"
    
    symlink_env_to_main_components
}

# Test copy_files_to_install_dir with missing source
test_copy_files_missing_source() {
    export PWD="/nonexistent/path"
    ! copy_files_to_install_dir  # Should fail
}

# Run all tests
echo "Running file operations module tests..."
echo "======================================"

setup_test_env

run_test "ensure_directory_new" test_ensure_directory_new
run_test "ensure_directory_existing" test_ensure_directory_existing
run_test "safe_remove_directory_valid" test_safe_remove_directory_valid
run_test "safe_remove_directory_invalid" test_safe_remove_directory_invalid
run_test "cleanup_failed_installation" test_cleanup_failed_installation
run_test "copy_files_incremental" test_copy_files_incremental
run_test "copy_files_full" test_copy_files_full
run_test "symlink_env_components" test_symlink_env_components
run_test "copy_files_missing_source" test_copy_files_missing_source

cleanup_test_env

echo "======================================"
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed