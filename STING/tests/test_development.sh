#!/bin/bash
# test_development.sh - Tests for development module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_dev"
export CONFIG_DIR="/tmp/test_sting_dev/conf"
export LOG_FILE="/tmp/test_sting_dev.log"

# Source the module
source ../lib/development.sh

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
    mkdir -p "$INSTALL_DIR/authentication/data"
    mkdir -p "$INSTALL_DIR/frontend"
    mkdir -p "$CONFIG_DIR"
    
    # Create mock files
    touch "$INSTALL_DIR/test.tmp"
    touch "$INSTALL_DIR/test.log"
    mkdir -p "$INSTALL_DIR/__pycache__"
    
    cat > "$INSTALL_DIR/frontend/package.json" << 'EOF'
{
  "name": "test-frontend",
  "version": "1.0.0"
}
EOF

    cat > "$INSTALL_DIR/requirements.txt" << 'EOF'
django==4.0.0
pytest==7.0.0
EOF
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR"
}

# Mock commands for testing
docker() {
    case "$1" in
        "compose")
            shift
            case "$1" in
                "exec")
                    case "$3" in
                        "utils")
                            case "$4" in
                                "bash")
                                    if [ "$5" = "-c" ]; then
                                        echo "Mock executing: $6"
                                    else
                                        echo "Mock bash shell"
                                    fi
                                    return 0
                                    ;;
                                *) echo "Mock utils command: $*"; return 0 ;;
                            esac
                            ;;
                        *) echo "Mock exec: $*"; return 0 ;;
                    esac
                    ;;
                "ps")
                    if [ "$2" = "utils" ]; then
                        echo "utils   Up 5 minutes"
                    else
                        echo "SERVICE   STATUS"
                        echo "dev       Up"
                    fi
                    ;;
                "down") echo "Stopping services..."; return 0 ;;
                "rm") echo "Removing containers..."; return 0 ;;
                "build") echo "Building services..."; return 0 ;;
                *) echo "Mock docker compose $*"; return 0 ;;
            esac
            ;;
        "ps")
            case "$*" in
                *"name=sting"*) echo ""; return 1 ;;  # No sting containers
                *) echo "CONTAINER ID   IMAGE   STATUS"; return 0 ;;
            esac
            ;;
        "images")
            case "$*" in
                *"sting-ce_*"*) echo ""; return 1 ;;  # No sting images
                *) echo "REPOSITORY   TAG"; return 0 ;;
            esac
            ;;
        "rm"|"rmi") echo "Removed $*"; return 0 ;;
        "volume")
            case "$2" in
                "ls") echo ""; return 1 ;;  # No volumes
                "rm") echo "Volume removed"; return 0 ;;
                *) return 0 ;;
            esac
            ;;
        "builder")
            case "$2" in
                "prune") echo "Build cache cleaned"; return 0 ;;
                *) return 0 ;;
            esac
            ;;
        *) echo "Mock docker $*"; return 0 ;;
    esac
}

# Mock find command
find() {
    case "$*" in
        *"*.tmp"*) echo "$INSTALL_DIR/test.tmp" ;;
        *"*.log"*) echo "$INSTALL_DIR/test.log" ;;
        *"__pycache__"*) echo "$INSTALL_DIR/__pycache__" ;;
        *"*.pyc"*|*".coverage"*|*".pytest_cache"*|*".mypy_cache"*) echo "" ;;
        *) builtin find "$@" ;;
    esac
}

# Mock rm command
rm() {
    echo "Mock rm $*"
    return 0
}

# Mock cd command
cd() {
    echo "Mock cd to $1"
    return 0
}

# Mock npm command
npm() {
    case "$1" in
        "update") echo "Mock npm update"; return 0 ;;
        "audit") echo "Mock npm audit fix"; return 0 ;;
        *) echo "Mock npm $*"; return 0 ;;
    esac
}

# Mock read command for interactive tests
read() {
    case "$*" in
        *"fresh rebuild"*)
            rebuild="n"
            return 0
            ;;
        *)
            builtin read "$@"
            ;;
    esac
}

# Test run_tests
test_run_tests() {
    run_tests
}

# Test run_linting
test_run_linting() {
    run_linting
}

# Test build_project
test_build_project() {
    build_project
}

# Test cleanup_development
test_cleanup_development() {
    cleanup_development
}

# Test reset_development
test_reset_development() {
    reset_development
}

# Test run_dev_server
test_run_dev_server() {
    run_dev_server
}

# Test run_migrations
test_run_migrations() {
    run_migrations
}

# Test create_migration
test_create_migration() {
    create_migration "test_app" "test_migration"
}

# Test run_dev_shell
test_run_dev_shell() {
    run_dev_shell
}

# Test run_python_shell
test_run_python_shell() {
    run_python_shell
}

# Test install_requirements
test_install_requirements() {
    install_requirements "requirements.txt"
}

# Test generate_requirements
test_generate_requirements() {
    generate_requirements
}

# Test format_code
test_format_code() {
    format_code
}

# Test run_security_checks
test_run_security_checks() {
    run_security_checks
}

# Test run_coverage
test_run_coverage() {
    run_coverage
}

# Test run_type_checks
test_run_type_checks() {
    run_type_checks
}

# Test clean_python_cache
test_clean_python_cache() {
    clean_python_cache
}

# Test update_dependencies
test_update_dependencies() {
    update_dependencies
}

# Run all tests
echo "Running development module tests..."
echo "=================================="

setup_test_env

run_test "run_tests" test_run_tests
run_test "run_linting" test_run_linting
run_test "build_project" test_build_project
run_test "cleanup_development" test_cleanup_development
run_test "reset_development" test_reset_development
run_test "run_dev_server" test_run_dev_server
run_test "run_migrations" test_run_migrations
run_test "create_migration" test_create_migration
run_test "run_dev_shell" test_run_dev_shell
run_test "run_python_shell" test_run_python_shell
run_test "install_requirements" test_install_requirements
run_test "generate_requirements" test_generate_requirements
run_test "format_code" test_format_code
run_test "run_security_checks" test_run_security_checks
run_test "run_coverage" test_run_coverage
run_test "run_type_checks" test_run_type_checks
run_test "clean_python_cache" test_clean_python_cache
run_test "update_dependencies" test_update_dependencies

cleanup_test_env

echo "=================================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed