#!/bin/bash
# test_configuration.sh - Tests for configuration module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_config"
export CONFIG_DIR="/tmp/test_sting_config/conf"
export SOURCE_DIR="/tmp/test_sting_source"
export LOG_FILE="/tmp/test_sting_config.log"
export POSTGRESQL_PASSWORD="test_password"
export DOMAIN="test.example.com"
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USER="test@example.com"
export EMAIL_FROM="noreply@example.com"

# Source the module
source ../lib/configuration.sh

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
    mkdir -p "$CONFIG_DIR/kratos"
    mkdir -p "$SOURCE_DIR/conf"
    
    # Create a default config template
    cat > "$SOURCE_DIR/conf/config.yml.default" << EOF
# Default STING Configuration
domain: localhost
database:
  password: changeme
EOF
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR" "$SOURCE_DIR"
}

# Test validate_critical_vars
test_validate_critical_vars() {
    # Test with all required vars set
    export INSTALL_DIR="/tmp/test_sting_config"
    export CONFIG_DIR="/tmp/test_sting_config/conf" 
    export POSTGRESQL_PASSWORD="test_password"
    
    validate_critical_vars
}

# Test validate_domain_settings
test_validate_domain_settings() {
    # Test with valid domain settings
    export DOMAIN="test.example.com"
    export SMTP_HOST="smtp.example.com"
    export SMTP_PORT="587"
    export SMTP_USER="test@example.com"
    export EMAIL_FROM="noreply@example.com"
    
    validate_domain_settings
}

# Test validate_domain_settings with localhost
test_validate_domain_localhost() {
    # Test with localhost (should pass with warning)
    export DOMAIN="localhost"
    
    validate_domain_settings
}

# Test generate_default_env
test_generate_default_env() {
    generate_default_env
    
    # Check if .env file was created
    [[ -f "$INSTALL_DIR/.env" ]]
}

# Test save_hf_token
test_save_hf_token() {
    local test_token="hf_test_token_1234567890abcdef"
    
    # Create env files first
    mkdir -p "$INSTALL_DIR/env"
    touch "$INSTALL_DIR/env/llm.env"
    touch "$INSTALL_DIR/env/llama3.env"
    
    save_hf_token "$test_token"
    
    # Check if token was saved to secrets
    [[ -f "$CONFIG_DIR/secrets/hf_token.txt" ]] && \
    [[ "$(cat "$CONFIG_DIR/secrets/hf_token.txt")" == "$test_token" ]] && \
    [[ "$HF_TOKEN" == "$test_token" ]]
}

# Test get_env_file_path
test_get_env_file_path() {
    local db_path=$(get_env_file_path "db" "$INSTALL_DIR")
    local app_path=$(get_env_file_path "app" "$INSTALL_DIR")
    local frontend_path=$(get_env_file_path "frontend" "$INSTALL_DIR")
    local unknown_path=$(get_env_file_path "unknown" "$INSTALL_DIR")
    
    [[ "$db_path" == "$INSTALL_DIR/env/db.env" ]] && \
    [[ "$app_path" == "$INSTALL_DIR/env/app.env" ]] && \
    [[ "$frontend_path" == "$INSTALL_DIR/env/frontend.env" ]] && \
    [[ -z "$unknown_path" ]]
}

# Test generate_kratos_config
test_generate_kratos_config() {
    # Set required variables
    export DSN="postgresql://test:test@localhost:5432/test"
    export KRATOS_PUBLIC_URL="http://localhost:4433"
    export KRATOS_ADMIN_URL="http://localhost:4434"
    export IDENTITY_DEFAULT_SCHEMA_URL="file:///etc/config/kratos/identity.schema.json"
    export FRONTEND_URL="http://localhost:3000"
    
    generate_kratos_config
    
    # Check if config was created
    [[ -f "$CONFIG_DIR/kratos/kratos.yml" ]]
}

# Test generate_initial_configuration
test_generate_initial_configuration() {
    # This test will use the default config template we created
    generate_initial_configuration
    
    # Check if config.yml was copied from default
    [[ -f "$CONFIG_DIR/config.yml" ]]
}

# Test ask_for_hf_token (non-interactive test)
test_save_hf_token_validation() {
    # Test with empty token
    ! save_hf_token ""
    
    # Test with valid token
    save_hf_token "hf_valid_token_123"
}

# Mock docker commands for testing
docker() {
    case "$1" in
        "network")
            case "$2" in
                "ls") echo "bridge" ;;
                "create") return 0 ;;
            esac
            ;;
        "run")
            # Mock successful validation
            return 0
            ;;
    esac
}

# Run all tests
echo "Running configuration module tests..."
echo "===================================="

setup_test_env

run_test "validate_critical_vars" test_validate_critical_vars
run_test "validate_domain_settings" test_validate_domain_settings
run_test "validate_domain_localhost" test_validate_domain_localhost
run_test "generate_default_env" test_generate_default_env
run_test "save_hf_token" test_save_hf_token
run_test "get_env_file_path" test_get_env_file_path
run_test "generate_kratos_config" test_generate_kratos_config
run_test "generate_initial_configuration" test_generate_initial_configuration
run_test "save_hf_token_validation" test_save_hf_token_validation

cleanup_test_env

echo "===================================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed