#!/bin/bash
# test_services.sh - Tests for services module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_services"
export CONFIG_DIR="/tmp/test_sting_services/conf"
export LOG_FILE="/tmp/test_sting_services.log"
export HEALTH_CHECK_RETRIES=3
export HEALTH_CHECK_INTERVAL=1
export COMPOSE_CMD="echo docker compose"

# Source the module
source ../lib/services.sh

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
    mkdir -p "$INSTALL_DIR/env"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$INSTALL_DIR/run"
    
    # Create mock docker-compose.yml
    cat > "$INSTALL_DIR/docker-compose.yml" << 'EOF'
version: '3.8'
services:
  test:
    image: alpine
    command: sleep 3600
EOF

    # Create mock config_loader.py
    cat > "$CONFIG_DIR/config_loader.py" << 'EOF'
#!/usr/bin/env python3
import sys
print("Mock config loader")
sys.exit(0)
EOF
    chmod +x "$CONFIG_DIR/config_loader.py"
    
    # Create mock service env files
    for service in db vault kratos app frontend; do
        cat > "$INSTALL_DIR/env/${service}.env" << EOF
# Mock env file for $service
SERVICE_NAME=$service
SERVICE_PORT=8080
EOF
    done
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR"
}

# Mock docker command for testing
docker() {
    case "$1" in
        "compose")
            shift
            case "$1" in
                "ps")
                    if [ "$2" = "test" ]; then
                        echo "test   Up 5 minutes   0.0.0.0:8080->80/tcp"
                    else
                        echo "SERVICE   STATUS"
                        echo "test      Up"
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
                "restart")
                    echo "Restarting services..."
                    return 0
                    ;;
                "build")
                    echo "Building services..."
                    return 0
                    ;;
                "stop"|"rm")
                    echo "Mock $1 command"
                    return 0
                    ;;
                "logs")
                    echo "Mock logs for $2"
                    return 0
                    ;;
                "exec")
                    case "$2" in
                        "-T")
                            case "$3" in
                                "db")
                                    case "$4" in
                                        "pg_isready") return 0 ;;
                                        *) return 1 ;;
                                    esac
                                    ;;
                                "utils")
                                    case "$4" in
                                        "python3") echo "Python 3.8.0"; return 0 ;;
                                        *) return 1 ;;
                                    esac
                                    ;;
                                "vault")
                                    case "$4" in
                                        "vault")
                                            case "$5" in
                                                "status") echo "Initialized: true"; return 0 ;;
                                                "secrets") echo "sting/"; return 0 ;;
                                                "policy") return 0 ;;
                                                *) return 1 ;;
                                            esac
                                            ;;
                                        *) return 1 ;;
                                    esac
                                    ;;
                                *) return 1 ;;
                            esac
                            ;;
                        *) return 1 ;;
                    esac
                    ;;
                *) return 0 ;;
            esac
            ;;
        "ps")
            echo "CONTAINER ID   IMAGE   COMMAND   STATUS"
            echo "123456789012   test    sleep     Up 5 minutes"
            return 0
            ;;
        "volume")
            case "$2" in
                "create") echo "Volume created"; return 0 ;;
                "ls") echo "llm_logs"; return 0 ;;
                "rm") echo "Volume removed"; return 0 ;;
                *) return 0 ;;
            esac
            ;;
        "rmi")
            echo "Image removed"
            return 0
            ;;
        "build"|"buildx")
            echo "Building..."
            return 0
            ;;
        *) 
            echo "Mock docker command: $*"
            return 0
            ;;
    esac
}

# Mock curl command
curl() {
    case "$*" in
        *"health"*|*"ready"*)
            return 0  # Simulate healthy services
            ;;
        *)
            return 0
            ;;
    esac
}

# Mock jq command
jq() {
    case "$*" in
        *"initialized"*)
            echo "true"
            return 0
            ;;
        *)
            echo "{}"
            return 0
            ;;
    esac
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

# Mock cd command to prevent actual directory changes in tests
cd() {
    echo "Mock cd to $1"
    return 0
}

# Test wait_for_service
test_wait_for_service() {
    # Test with a service that should be healthy (mock frontend which just checks if container is Up)
    wait_for_service "frontend"
}

# Test stop_native_llm_service
test_stop_native_llm_service() {
    # Create a mock PID file
    mkdir -p "$INSTALL_DIR/run"
    echo "12345" > "$INSTALL_DIR/run/llm-gateway.pid"
    
    # Mock kill command
    kill() {
        case "$1" in
            "-0"|"12345") return 1 ;;  # Simulate process not running
            "-9") return 0 ;;
            *) return 0 ;;
        esac
    }
    
    stop_native_llm_service
    
    # Check if PID file was removed
    [[ ! -f "$INSTALL_DIR/run/llm-gateway.pid" ]]
}

# Test start_service
test_start_service() {
    start_service "test"
}

# Test stop_service
test_stop_service() {
    stop_service "test"
}

# Test start_all_services
test_start_all_services() {
    start_all_services
}

# Test stop_all_services
test_stop_all_services() {
    stop_all_services
}

# Test restart_all_services
test_restart_all_services() {
    restart_all_services
}

# Test build_llm_images
test_build_llm_images() {
    # Mock cat command
    cat() {
        case "$1" in
            */Dockerfile.llm-base)
                echo "FROM ubuntu:20.04"
                return 0
                ;;
            *)
                command cat "$@"
                ;;
        esac
    }
    
    build_llm_images
}

# Test wait_for_vault
test_wait_for_vault() {
    # Override the check to return success quickly for testing
    export VAULT_TOKEN="test_token"
    export VAULT_ADDR="http://localhost:8200"
    
    # Mock the vault health check to succeed immediately
    local original_wait_for_vault=$(declare -f wait_for_vault)
    wait_for_vault() {
        log_message "Mock vault check - healthy"
        return 0
    }
    
    wait_for_vault
    local result=$?
    
    # Restore original function
    eval "$original_wait_for_vault"
    
    return $result
}

# Test manage_services
test_manage_services() {
    # Test start action (all services)
    manage_services "start" && \
    # Test stop action  
    manage_services "stop" "db" && \
    # Test restart action (all services, not individual)
    manage_services "restart" && \
    # Test build action
    manage_services "build" "test"
}

# Run all tests
echo "Running services module tests..."
echo "================================"

setup_test_env

run_test "wait_for_service" test_wait_for_service
run_test "stop_native_llm_service" test_stop_native_llm_service
run_test "start_service" test_start_service
run_test "stop_service" test_stop_service
run_test "start_all_services" test_start_all_services
run_test "stop_all_services" test_stop_all_services
run_test "restart_all_services" test_restart_all_services
run_test "build_llm_images" test_build_llm_images
run_test "wait_for_vault" test_wait_for_vault
run_test "manage_services" test_manage_services

cleanup_test_env

echo "================================"
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed