#!/bin/bash
# test_docker.sh - Tests for docker module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_docker"
export CONFIG_DIR="/tmp/test_sting_docker/conf"
export LOG_FILE="/tmp/test_sting_docker.log"
export COMPOSE_CMD="echo docker compose"
export COMPOSE_PROJECT_NAME="test-sting"
export DOCKER_NETWORK="test_network"

# Source the module
source ../lib/docker.sh

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
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    
    # Create mock docker-compose.yml
    cat > "$INSTALL_DIR/docker-compose.yml" << 'EOF'
version: '3.8'
services:
  test:
    image: alpine
    command: sleep 3600
  dev:
    image: ubuntu
    command: sleep 3600
EOF

    # Create mock mac compose file
    cat > "$INSTALL_DIR/docker-compose.mac.yml" << 'EOF'
version: '3.8'
services:
  test:
    platform: linux/arm64
EOF

    # Create mock config_loader.py
    cat > "$CONFIG_DIR/config_loader.py" << 'EOF'
#!/usr/bin/env python3
import sys
print("Mock config loader")
sys.exit(0)
EOF
    chmod +x "$CONFIG_DIR/config_loader.py"
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR"
}

# Mock command function to override system commands
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

# Mock docker command for testing
mock_docker() {
    case "$1" in
        "compose")
            shift
            case "$1" in
                "ps")
                    if [ "$2" = "utils" ]; then
                        echo "utils   Up 5 minutes   0.0.0.0:8080->80/tcp"
                    else
                        echo "SERVICE   STATUS"
                        echo "utils       Up"
                        echo "test      Up (healthy)"
                    fi
                    ;;
                "up")
                    echo "Starting services..."
                    return 0
                    ;;
                "down")
                    echo "Stopping services..."
                    return 0
                    ;;
                "build")
                    echo "Building services..."
                    return 0
                    ;;
                "exec")
                    case "$2" in
                        "-T")
                            case "$3" in
                                "utils")
                                    case "$4" in
                                        "bash") echo "Mock bash execution"; return 0 ;;
                                        *) return 0 ;;
                                    esac
                                    ;;
                                *) return 0 ;;
                            esac
                            ;;
                        *) return 0 ;;
                    esac
                    ;;
                "logs")
                    echo "Mock logs for $2"
                    return 0
                    ;;
                *) 
                    echo "Mock docker compose $*"
                    return 0
                    ;;
            esac
            ;;
        "network")
            case "$2" in
                "inspect") 
                    if [ "$3" = "test_network" ]; then
                        return 1  # Network doesn't exist
                    else
                        return 0  # Network exists
                    fi
                    ;;
                "create") 
                    echo "Network created: $4"
                    return 0
                    ;;
                "prune")
                    echo "Networks pruned"
                    return 0
                    ;;
                *) return 0 ;;
            esac
            ;;
        "info")
            echo "Docker daemon is running"
            return 0
            ;;
        "buildx")
            case "$2" in
                "version") echo "buildx version 1.0.0"; return 0 ;;
                "inspect") return 1 ;;  # Builder doesn't exist
                "create") echo "Builder created"; return 0 ;;
                "build") echo "Building with buildx..."; return 0 ;;
                *) return 0 ;;
            esac
            ;;
        "image")
            case "$2" in
                "prune") echo "Images pruned"; return 0 ;;
                *) return 0 ;;
            esac
            ;;
        "version")
            echo "Docker version 20.10.0"
            return 0
            ;;
        *)
            echo "Mock docker command: $*"
            return 0
            ;;
    esac
}

# Override docker function for testing
docker() {
    mock_docker "$@"
}

# Mock python3 command
python3() {
    case "$1" in
        "${CONFIG_DIR}/config_loader.py")
            echo "Mock config loader executed"
            return 0
            ;;
        *)
            echo "Mock python3"
            return 0
            ;;
    esac
}

# Mock uname for platform testing
uname() {
    case "$1" in
        "-m") echo "x86_64" ;;
        *) echo "Darwin" ;;  # Default to macOS for testing
    esac
}

# Test docker wrapper function
test_docker_wrapper() {
    # Test regular docker command
    local output1
    output1=$(docker version)
    [[ "$output1" == *"Docker version"* ]] || return 1
    
    # Test docker compose command on macOS (should use mac compose file)
    local output2
    output2=$(docker compose ps)
    [[ "$output2" == *"SERVICE"* ]] || return 1
}

# Test check_docker_compose_file
test_check_docker_compose_file() {
    check_docker_compose_file
}

# Test build_docker_services
test_build_docker_services() {
    # Test building all services
    build_docker_services && \
    # Test building specific service
    build_docker_services "test" && \
    # Test building with no-cache
    build_docker_services "test" "true"
}

# Test check_or_create_docker_network
test_check_or_create_docker_network() {
    check_or_create_docker_network
}

# Test ensure_dev_container
test_ensure_dev_container() {
    # Create mock .env file to simulate loaded config
    touch "$INSTALL_DIR/.env"
    ensure_dev_container
}

# Test run_in_dev_container
test_run_in_dev_container() {
    run_in_dev_container "echo hello"
}

# Test check_dev_container
test_check_dev_container() {
    check_dev_container
}

# Test get_docker_platform
test_get_docker_platform() {
    local platform
    platform=$(get_docker_platform)
    [[ "$platform" == "linux/amd64" ]] || [[ "$platform" == "linux/arm64" ]]
}

# Test check_docker_prerequisites
test_check_docker_prerequisites() {
    check_docker_prerequisites
}

# Test cleanup_docker_resources
test_cleanup_docker_resources() {
    cleanup_docker_resources
}

# Test get_container_logs
test_get_container_logs() {
    get_container_logs "test" && \
    get_container_logs "test" "100"
}

# Test check_container_health
test_check_container_health() {
    check_container_health "test"
}

# Run all tests
echo "Running docker module tests..."
echo "=============================="

setup_test_env

run_test "docker_wrapper" test_docker_wrapper
run_test "check_docker_compose_file" test_check_docker_compose_file
run_test "build_docker_services" test_build_docker_services
run_test "check_or_create_docker_network" test_check_or_create_docker_network
run_test "ensure_dev_container" test_ensure_dev_container
run_test "run_in_dev_container" test_run_in_dev_container
run_test "check_dev_container" test_check_dev_container
run_test "get_docker_platform" test_get_docker_platform
run_test "check_docker_prerequisites" test_check_docker_prerequisites
run_test "cleanup_docker_resources" test_cleanup_docker_resources
run_test "get_container_logs" test_get_container_logs
run_test "check_container_health" test_check_container_health

cleanup_test_env

echo "=============================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed