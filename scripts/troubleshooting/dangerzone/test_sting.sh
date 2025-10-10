#!/bin/bash

# Enable debug output
set -x

# Set strict error handling
set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Initialize counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Debug function
debug() {
    echo "[DEBUG] $1" >&2
}

debug "Script starting..."

# Set up paths
INSTALL_DIR="/opt/sting-ce"
CONFIG_DIR="${INSTALL_DIR}/conf"
CONFIG_FILE="${CONFIG_DIR}/config.yml"
CONFIG_LOADER="${CONFIG_DIR}/config_loader.py"

debug "Checking directories..."
debug "INSTALL_DIR: $INSTALL_DIR"
debug "CONFIG_DIR: $CONFIG_DIR"
debug "CONFIG_FILE: $CONFIG_FILE"
debug "CONFIG_LOADER: $CONFIG_LOADER"

# Directory checks
for dir in "$INSTALL_DIR" "$CONFIG_DIR"; do
    if [ ! -d "$dir" ]; then
        echo -e "${RED}Error: Directory not found: $dir${NC}"
        ls -la "$(dirname "$dir")"
        exit 1
    else
        debug "Directory exists: $dir"
        ls -la "$dir"
    fi
done

# File checks
for file in "$CONFIG_FILE" "$CONFIG_LOADER"; do
    if [ ! -f "$file" ]; then
        echo -e "${RED}Error: File not found: $file${NC}"
        ls -la "$(dirname "$file")"
        exit 1
    else
        debug "File exists: $file"
        ls -la "$file"
    fi
done

log_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
    debug "Test passed: $1"
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $1"
    if [ -n "${2:-}" ]; then
        echo -e "${RED}Error: $2${NC}"
        debug "Test failed: $1 with error: $2"
    fi
}

run_test() {
    local test_name="$1"
    local test_command="$2"
    ((TESTS_RUN++))
    
    debug "Running test: $test_name"
    debug "Command: $test_command"
    
    log_test "Running: $test_name"
    
    if eval "$test_command"; then
        log_success "$test_name"
        return 0
    else
        local exit_code=$?
        log_failure "$test_name" "Command failed with exit code $exit_code"
        return 1
    fi
}

test_prerequisites() {
    debug "Testing prerequisites..."
    echo -e "\nTesting Prerequisites..."
    
    # Check virtual environment
    if [ ! -d "${INSTALL_DIR}/venv" ]; then
        debug "Virtual environment not found, creating it..."
        python3 -m venv "${INSTALL_DIR}/venv"
    fi
    
    # Activate virtual environment
    debug "Activating virtual environment..."
    source "${INSTALL_DIR}/venv/bin/activate"
    
    # Install required packages
    debug "Installing required packages..."
    pip install pyyaml hvac cerberus >/dev/null 2>&1 || {
        debug "Failed to install required packages"
        return 1
    }
    
    log_success "Prerequisites Check"
    return 0
}

test_configuration() {
    debug "Testing configuration..."
    echo -e "\nTesting Configuration Management..."
    
    # Ensure virtual environment is activated
    if [ -z "${VIRTUAL_ENV:-}" ]; then
        debug "Activating virtual environment..."
        source "${INSTALL_DIR}/venv/bin/activate"
    fi
    
    # Test config.yml syntax
    debug "Testing YAML syntax..."
    run_test "Config YAML Syntax" "python3 -c 'import yaml; yaml.safe_load(open(\"$CONFIG_FILE\"))'"
    
    # Test config loader
    debug "Testing config loader..."
    run_test "Config Loader" "python3 $CONFIG_LOADER $CONFIG_FILE"
    
    # Test environment file generation
    debug "Testing environment file..."
    run_test "Environment File" "[ -f ${CONFIG_DIR}/.env ]"
    
    if [ -f "${CONFIG_DIR}/.env" ]; then
        debug "Loading environment file..."
        set -a
        source "${CONFIG_DIR}/.env"
        set +a
    fi
}

test_docker() {
    debug "Testing Docker..."
    echo -e "\nTesting Docker Environment..."
    
    run_test "Docker Installation" "docker --version"
    run_test "Docker Compose" "docker-compose --version"
    run_test "Docker Network" "docker network inspect sting_local >/dev/null 2>&1 || docker network create sting_local"
}

cleanup() {
    debug "Running cleanup..."
    if [ -n "${VIRTUAL_ENV:-}" ]; then
        debug "Deactivating virtual environment..."
        deactivate 2>/dev/null || true
    fi
    
    if [ -d "${TEST_TMP_DIR:-}" ]; then
        debug "Removing temp directory..."
        rm -rf "$TEST_TMP_DIR"
    fi
}

main() {
    debug "Starting main function..."
    
    # Create temp directory for test artifacts
    export TEST_TMP_DIR=$(mktemp -d)
    debug "Created temp directory: $TEST_TMP_DIR"
    trap cleanup EXIT
    
    echo -e "${GREEN}Starting STING Test Suite${NC}"
    echo "================================"
    
    # Reset counters
    TESTS_RUN=0
    TESTS_PASSED=0
    
    # Run tests
    if ! test_prerequisites; then
        echo -e "\n${RED}Prerequisites check failed. Please ensure STING is properly installed.${NC}"
        exit 1
    fi
    
    test_docker || true
    test_configuration || true
    
    # Print test summary
    echo -e "\nTest Summary"
    echo "==========="
    
    # Assuming you have variables total_tests, passed_tests, and failed_tests
    total_tests=$TESTS_RUN
    passed_tests=$TESTS_PASSED
    failed_tests=$((total_tests - passed_tests))

    # Ensure failed_tests is not negative
    if [ $failed_tests -lt 0 ]; then
        failed_tests=0
    fi

    echo ===========
    echo "Total Tests: $total_tests"
    echo -e "\033[0;32mPassed: $passed_tests\033[0m"
    echo -e "\033[0;31mFailed: $failed_tests\033[0m"

    if [ $failed_tests -eq 0 ]; then
        echo -e "\n\033[0;32mAll tests passed.\033[0m"
        return 0
    else
        echo -e "\n\033[0;31mSome tests failed. Please check the output above.\033[0m"
        return 1
    fi
}

# Run main function
debug "Calling main function..."
main "$@"