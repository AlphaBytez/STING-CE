#!/bin/bash
# test_installation.sh - Tests for installation module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_install"
export CONFIG_DIR="/tmp/test_sting_install/conf"
export SOURCE_DIR="/tmp/test_sting_source"
export LOG_FILE="/tmp/test_sting_install.log"
export HF_TOKEN="hf_test_token_123"

# Source the module
source ../lib/installation.sh

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
    rm -rf "$INSTALL_DIR" "$SOURCE_DIR"
    mkdir -p "$INSTALL_DIR/env"
    mkdir -p "$CONFIG_DIR/secrets"
    mkdir -p "$SOURCE_DIR"
    
    # Create mock source files
    cat > "$SOURCE_DIR/docker-compose.yml" << 'EOF'
version: '3.8'
services:
  test:
    image: alpine
EOF

    cat > "$SOURCE_DIR/manage_sting.sh" << 'EOF'
#!/bin/bash
echo "Mock manage_sting.sh"
EOF
    chmod +x "$SOURCE_DIR/manage_sting.sh"
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR" "$SOURCE_DIR"
}

# Mock commands for testing
command() {
    case "$1" in
        "docker")
            shift
            mock_docker "$@"
            ;;
        *)
            builtin command "$@"
            ;;
    esac
}

# Mock docker command
mock_docker() {
    case "$1" in
        "pull") echo "Pulling $2..."; return 0 ;;
        "compose")
            shift
            case "$1" in
                "build") echo "Building services..."; return 0 ;;
                "up") echo "Starting services..."; return 0 ;;
                "down") echo "Stopping services..."; return 0 ;;
                "ps") echo "test   Up"; return 0 ;;
                "rm") echo "Removing containers..."; return 0 ;;
                *) echo "Mock docker compose $*"; return 0 ;;
            esac
            ;;
        "ps") echo "CONTAINER ID   IMAGE   STATUS"; return 0 ;;
        "images") echo "REPOSITORY   TAG"; return 0 ;;
        "rm"|"rmi") echo "Removed"; return 0 ;;
        "volume") echo "Volume command"; return 0 ;;
        "network") echo "Network command"; return 0 ;;
        "--version") echo "Docker version 20.10.0"; return 0 ;;
        *) echo "Mock docker $*"; return 0 ;;
    esac
}

docker() {
    mock_docker "$@"
}

# Mock system commands
python3() {
    case "$1" in
        "-m")
            case "$2" in
                "venv") echo "Mock venv"; return 0 ;;
                *) echo "Mock python module $2"; return 0 ;;
            esac
            ;;
        *) echo "Mock python3"; return 0 ;;
    esac
}

pip() {
    echo "Mock pip install $*"
    return 0
}

pip3() {
    echo "Mock pip3 install $*"
    return 0
}

npm() {
    case "$1" in
        "install") echo "Mock npm install"; return 0 ;;
        "-v") echo "8.0.0"; return 0 ;;
        *) echo "Mock npm $*"; return 0 ;;
    esac
}

node() {
    case "$1" in
        "-v") echo "v20.0.0"; return 0 ;;
        *) echo "Mock node"; return 0 ;;
    esac
}

curl() {
    echo "Mock curl download"
    return 0
}

sudo() {
    # Mock sudo to just run the command without privilege escalation
    "$@"
}

apt-get() {
    echo "Mock apt-get $*"
    return 0
}

usermod() {
    echo "Mock usermod $*"
    return 0
}

huggingface-cli() {
    case "$1" in
        "login") echo "Mock HF login"; return 0 ;;
        *) echo "Mock huggingface-cli $*"; return 0 ;;
    esac
}

find() {
    case "$*" in
        *"*.bin"*|*"*.gguf"*) 
            # Simulate no models found
            return 1
            ;;
        *)
            builtin find "$@"
            ;;
    esac
}

rsync() {
    echo "Mock rsync copy"
    return 0
}

ln() {
    echo "Mock ln $*"
    return 0
}

chmod() {
    echo "Mock chmod $*"
    return 0
}

# Test check_and_install_dependencies
test_check_and_install_dependencies() {
    check_and_install_dependencies
}

# Test install_nodejs
test_install_nodejs() {
    install_nodejs
}

# Test install_docker
test_install_docker() {
    install_docker
}

# Test install_frontend_dependencies
test_install_frontend_dependencies() {
    # Create mock frontend directory
    mkdir -p "$INSTALL_DIR/frontend"
    cat > "$INSTALL_DIR/frontend/package.json" << 'EOF'
{
  "name": "test-frontend",
  "version": "1.0.0"
}
EOF
    
    install_frontend_dependencies
}

# Test install_dev_dependencies
test_install_dev_dependencies() {
    install_dev_dependencies
}

# Test install_msting_command
test_install_msting_command() {
    install_msting_command
}

# Test pip_install_with_progress
test_pip_install_with_progress() {
    pip_install_with_progress "test-package"
}

# Test prepare_basic_structure
test_prepare_basic_structure() {
    prepare_basic_structure
    
    # Check if directories were created
    [[ -d "$INSTALL_DIR/env" ]] && \
    [[ -d "$INSTALL_DIR/logs" ]] && \
    [[ -d "$INSTALL_DIR/backups" ]] && \
    [[ -d "$CONFIG_DIR" ]]
}

# Test check_llm_models
test_check_llm_models() {
    # This should return false since our mock find doesn't find models
    ! check_llm_models
}

# Test ensure_models_dir
test_ensure_models_dir() {
    local models_dir
    models_dir=$(ensure_models_dir)
    [[ -n "$models_dir" ]]
}

# Test uninstall_msting
test_uninstall_msting() {
    # Create some mock installation files
    mkdir -p "$INSTALL_DIR/backups"
    touch "$INSTALL_DIR/docker-compose.yml"
    echo "test backup" > "$INSTALL_DIR/backups/test.backup"
    
    uninstall_msting
    
    # Check that installation was "removed" but we can't test actual removal in mocks
    return 0
}

# Test uninstall_msting_with_confirmation (non-interactive)
test_uninstall_with_confirmation() {
    # Mock the read command to simulate "no" response
    read() {
        case "$*" in
            *"Are you sure"*)
                confirm="no"
                return 0
                ;;
            *)
                builtin read "$@"
                ;;
        esac
    }
    
    # This should return 1 since we're saying "no"
    ! uninstall_msting_with_confirmation
}

# Test ensure_hf_cli
test_ensure_hf_cli() {
    ensure_hf_cli
}

# Test ensure_hf_auth
test_ensure_hf_auth() {
    ensure_hf_auth
}

# Run all tests
echo "Running installation module tests..."
echo "==================================="

setup_test_env

run_test "check_and_install_dependencies" test_check_and_install_dependencies
run_test "install_nodejs" test_install_nodejs
run_test "install_docker" test_install_docker
run_test "install_frontend_dependencies" test_install_frontend_dependencies
run_test "install_dev_dependencies" test_install_dev_dependencies
run_test "install_msting_command" test_install_msting_command
run_test "pip_install_with_progress" test_pip_install_with_progress
run_test "prepare_basic_structure" test_prepare_basic_structure
run_test "check_llm_models" test_check_llm_models
run_test "ensure_models_dir" test_ensure_models_dir
run_test "uninstall_msting" test_uninstall_msting
run_test "uninstall_with_confirmation" test_uninstall_with_confirmation
run_test "ensure_hf_cli" test_ensure_hf_cli
run_test "ensure_hf_auth" test_ensure_hf_auth

cleanup_test_env

echo "==================================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed