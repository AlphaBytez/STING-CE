#!/bin/bash
# test_health.sh - Tests for health module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_health"
export CONFIG_DIR="/tmp/test_sting_health/conf"
export LOG_FILE="/tmp/test_sting_health.log"
export STING_MODELS_DIR="/tmp/test_models"
export POSTGRES_USER="test_user"
export POSTGRES_PASSWORD="test_pass"
export POSTGRES_DB="test_db"

# Source the module
source ../lib/health.sh

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
    mkdir -p "$INSTALL_DIR/docker-entrypoint-initdb.d"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$STING_MODELS_DIR"
    
    # Create mock init file
    cat > "$CONFIG_DIR/init_db.sql" << 'EOF'
-- Mock database initialization
CREATE TABLE test_table (id SERIAL PRIMARY KEY);
EOF
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR" "$STING_MODELS_DIR"
}

# Mock commands
curl() {
    case "$*" in
        *"localhost:3567/health"*) echo "OK" ;;
        *) echo "Mock curl response" ;;
    esac
    return 0
}

docker() {
    case "$1" in
        "compose")
            shift
            case "$1" in
                "exec")
                    case "$3" in
                        "db")
                            case "$4" in
                                "pg_isready") return 0 ;;
                                "psql")
                                    if [[ "$*" == *"pg_database"* ]]; then
                                        echo "1"  # Database exists
                                    elif [[ "$*" == *"information_schema.tables"* ]]; then
                                        echo "5"  # 5 tables found
                                    fi
                                    ;;
                                *) echo "Mock db command" ;;
                            esac
                            ;;
                        *) echo "Mock compose exec" ;;
                    esac
                    return 0
                    ;;
                "ps")
                    case "$2" in
                        "db"|"vault"|"kratos"|"app"|"frontend") echo "$2   Up 5 minutes" ;;
                        *) echo "SERVICE   STATUS\ndb        Up\nvault     Up" ;;
                    esac
                    ;;
                *) echo "Mock docker compose $*"; return 0 ;;
            esac
            ;;
        *) echo "Mock docker $*"; return 0 ;;
    esac
}

find() {
    case "$*" in
        *"mindepth 1 -maxdepth 1 -type d"*)
            # Simulate models found in directory
            echo "/tmp/test_models/tinyllama"
            ;;
        *) command find "$@" ;;
    esac
}

grep() {
    case "$*" in
        "-q .") return 0 ;;  # Simulate match found
        *) command grep "$@" ;;
    esac
}

df() {
    case "$*" in
        "-h "*) echo "Filesystem      Size  Used Avail Use% Mounted on\n/dev/disk1     100G   50G   50G  50% /" ;;
        *) command df "$@" ;;
    esac
}

awk() {
    case "$*" in
        *"NR==2 {print \$4}"*) echo "50G" ;;
        *) command awk "$@" ;;
    esac
}

sed() {
    case "$*" in
        *"s/G.*//"*) echo "50" ;;
        *) command sed "$@" ;;
    esac
}

vm_stat() {
    echo "Pages free:                    1000000."
}

free() {
    case "$*" in
        "-m") echo "              total        used        free      shared  buff/cache   available\nMem:           8192        2048        6144           0        1024        4096" ;;
        *) command free "$@" ;;
    esac
}

netstat() {
    case "$*" in
        "-tuln")
            echo "Proto Recv-Q Send-Q Local Address           Foreign Address         State"
            echo "tcp        0      0 0.0.0.0:3000            0.0.0.0:*               LISTEN"
            echo "tcp        0      0 0.0.0.0:5050            0.0.0.0:*               LISTEN"
            echo "tcp        0      0 0.0.0.0:5432            0.0.0.0:*               LISTEN"
            ;;
        *) command netstat "$@" ;;
    esac
}

cp() {
    echo "Mock cp $*"
    command cp "$@" 2>/dev/null || true
}

chmod() {
    echo "Mock chmod $*"
    return 0
}

sleep() {
    # Speed up tests by reducing sleep time
    return 0
}

# Test check_supertokens_health
test_check_supertokens_health() {
    check_supertokens_health
}

# Test check_llm_models with models present
test_check_llm_models_present() {
    # Create a model directory to simulate models being present
    mkdir -p "$STING_MODELS_DIR/tinyllama"
    
    check_llm_models
}

# Test check_llm_models with no models
test_check_llm_models_missing() {
    # Override find to return no directories
    find() {
        case "$*" in
            *"mindepth 1 -maxdepth 1 -type d"*) return 1 ;;  # No directories
            *) command find "$@" ;;
        esac
    }
    
    # This should fail (return 1)
    ! check_llm_models
}

# Test verify_db_credentials
test_verify_db_credentials() {
    verify_db_credentials
}

# Test verify_db_schema
test_verify_db_schema() {
    verify_db_schema
}

# Test check_db_init_files
test_check_db_init_files() {
    check_db_init_files
}

# Test check_system_health
test_check_system_health() {
    # Create model directory for this test
    mkdir -p "$STING_MODELS_DIR/tinyllama"
    
    check_system_health
}

# Test check_database_connection
test_check_database_connection() {
    check_database_connection
}

# Test check_services_health
test_check_services_health() {
    check_services_health
}

# Test check_disk_space
test_check_disk_space() {
    check_disk_space
}

# Test check_memory_usage
test_check_memory_usage() {
    # Mock uname to test Linux path
    uname() {
        echo "Linux"
    }
    
    check_memory_usage
}

# Test check_port_availability
test_check_port_availability() {
    check_port_availability "3000" "frontend"
}

# Test check_required_ports
test_check_required_ports() {
    check_required_ports
}

# Run all tests
echo "Running health module tests..."
echo "============================="

setup_test_env

run_test "check_supertokens_health" test_check_supertokens_health
run_test "check_llm_models_present" test_check_llm_models_present
run_test "check_llm_models_missing" test_check_llm_models_missing
run_test "verify_db_credentials" test_verify_db_credentials
run_test "verify_db_schema" test_verify_db_schema
run_test "check_db_init_files" test_check_db_init_files
run_test "check_system_health" test_check_system_health
run_test "check_database_connection" test_check_database_connection
run_test "check_services_health" test_check_services_health
run_test "check_disk_space" test_check_disk_space
run_test "check_memory_usage" test_check_memory_usage
run_test "check_port_availability" test_check_port_availability
run_test "check_required_ports" test_check_required_ports

cleanup_test_env

echo "============================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed