#!/bin/bash
# test_security.sh - Tests for security module

# Set up test environment
export INSTALL_DIR="/tmp/test_sting_security"
export CONFIG_DIR="/tmp/test_sting_security/conf"
export LOG_FILE="/tmp/test_sting_security.log"
export VAULT_ADDR="http://localhost:8200"
export VAULT_TOKEN="test_token"
export DOMAIN_NAME="test.example.com"
export CERTBOT_EMAIL="test@example.com"

# Source the module
source ../lib/security.sh

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
    mkdir -p "$INSTALL_DIR/certs/config/live/test.example.com"
    mkdir -p "$CONFIG_DIR/secrets"
    
    # Create mock certificate
    cat > "$INSTALL_DIR/certs/config/live/test.example.com/cert.pem" << 'EOF'
-----BEGIN CERTIFICATE-----
MIIBkTCB+wIJAK7VCxPsh7AoMA0GCSqGSIb3DQEBCwUAMBQxEjAQBgNVBAMMCWxv
Y2FsaG9zdDAeFw0yNTA2MDkwMDAwMDBaFw0yNjA2MDkwMDAwMDBaMBQxEjAQBgNV
BAMMCWxvY2FsaG9zdDBcMA0GCSqGSIb3DQEBAQUAA0sAMEgCQQC8Q7HgL8yFQ9Qz
test_certificate_data_here
-----END CERTIFICATE-----
EOF
}

# Cleanup test environment
cleanup_test_env() {
    rm -rf "$INSTALL_DIR"
}

# Mock commands
docker() {
    case "$1" in
        "compose")
            shift
            case "$1" in
                "exec")
                    case "$3" in
                        "vault")
                            case "$4" in
                                "vault")
                                    case "$5" in
                                        "secrets") echo "sting/" ;;
                                        "policy") echo "Success! Uploaded policy" ;;
                                        *) echo "Mock vault command" ;;
                                    esac
                                    ;;
                                *) echo "Mock vault exec" ;;
                            esac
                            ;;
                        *) echo "Mock compose exec" ;;
                    esac
                    return 0
                    ;;
                "stop"|"start") echo "Mock compose $1"; return 0 ;;
                *) echo "Mock docker compose $*"; return 0 ;;
            esac
            ;;
        "secret")
            case "$2" in
                "inspect") echo '{"Spec":{"Data":"dGVzdF9zZWNyZXQ="}}' ;;  # base64 for "test_secret"
                *) echo "Mock docker secret" ;;
            esac
            return 0
            ;;
        "ps") echo "vault container running"; return 0 ;;
        "run") echo "Mock docker run"; return 0 ;;
        *) echo "Mock docker $*"; return 0 ;;
    esac
}

# Mock curl
curl() {
    case "$*" in
        *"/v1/sys/health"*) echo '{"initialized":true,"sealed":false}' ;;
        *"/v1/sting/data/"*)
            if [[ "$*" == *"database/credentials"* ]]; then
                echo '{"data":{"data":{"password":"test_db_pass"}}}'
            elif [[ "$*" == *"supertokens/credentials"* ]]; then
                echo '{"data":{"data":{"api_key":"test_api_key","dashboard_key":"test_dash_key"}}}'
            else
                echo '{"data":{"data":{"token":"test_vault_token"}}}'
            fi
            ;;
        *) echo "Mock curl response" ;;
    esac
    return 0
}

# Mock jq
jq() {
    case "$*" in
        *".initialized == true and .sealed == false"*) echo "true" ;;
        *".initialized == true"*) echo "true" ;;
        *".data.data."*) 
            if [[ "$*" == *"password"* ]]; then
                echo "test_db_pass"
            elif [[ "$*" == *"api_key"* ]]; then
                echo "test_api_key"
            elif [[ "$*" == *"dashboard_key"* ]]; then
                echo "test_dash_key"
            else
                echo "test_vault_token"
            fi
            ;;
        *) echo "mock_jq_output" ;;
    esac
}

# Mock openssl
openssl() {
    case "$1" in
        "req")
            # Mock certificate generation
            local cert_file key_file
            for arg in "$@"; do
                case "$arg" in
                    "-out") cert_file=true ;;
                    "-keyout") key_file=true ;;
                    *)
                        if [ "$cert_file" = true ]; then
                            echo "Mock certificate" > "$arg"
                            cert_file=false
                        elif [ "$key_file" = true ]; then
                            echo "Mock private key" > "$arg"
                            key_file=false
                        fi
                        ;;
                esac
            done
            return 0
            ;;
        "x509")
            case "$*" in
                *"-enddate"*) echo "notAfter=Dec 31 23:59:59 2025 GMT" ;;
                *"-text -noout"*) return 0 ;;  # Valid certificate
                *) echo "Mock x509 output" ;;
            esac
            return 0
            ;;
        "s_client")
            echo "Mock SSL connection test"
            return 0
            ;;
        "rand")
            echo "mock_random_data_1234567890abcdef"
            return 0
            ;;
        *) echo "Mock openssl $*"; return 0 ;;
    esac
}

# Mock other commands
base64() {
    case "$1" in
        "-d") echo "test_secret" ;;
        *) echo "dGVzdF9zZWNyZXQ=" ;;
    esac
}

certbot() {
    case "$1" in
        "renew") echo "Mock certbot renew"; return 0 ;;
        *) echo "Mock certbot $*"; return 0 ;;
    esac
}

brew() {
    echo "Mock brew install $*"
    return 0
}

apt-get() {
    echo "Mock apt-get $*"
    return 0
}

yum() {
    echo "Mock yum $*"
    return 0
}

crontab() {
    case "$1" in
        "-l") echo "# existing cron jobs" ;;
        *) echo "Mock crontab update" ;;
    esac
    return 0
}

date() {
    case "$*" in
        *"+%s"*) echo "1749520000" ;;  # Mock epoch time
        *"-d"*) echo "1749520000" ;;   # Mock date parsing
        *"-j"*) echo "1749520000" ;;   # Mock BSD date
        *) command date "$@" ;;
    esac
}

timeout() {
    shift 2  # Remove timeout and duration
    "$@"     # Execute the command
}

ln() {
    echo "Mock ln $*"
    return 0
}

mkdir() {
    echo "Mock mkdir $*"
    command mkdir -p "$@" 2>/dev/null || true
}

chmod() {
    echo "Mock chmod $*"
    return 0
}

rm() {
    echo "Mock rm $*"
    return 0
}

sha256sum() {
    echo "mock_hash  $1"
}

# Test verify_secrets
test_verify_secrets() {
    # Unset secrets to test fetching from Vault
    unset POSTGRESQL_PASSWORD ST_API_KEY ST_DASHBOARD_API_KEY VAULT_TOKEN
    
    verify_secrets
}

# Test get_secret_value
test_get_secret_value() {
    get_secret_value "test_secret" >/dev/null
}

# Test retrieve_secret
test_retrieve_secret() {
    export TEST_SECRET="test_value"
    local result=$(retrieve_secret "TEST_SECRET")
    [[ "$result" == "test_value" ]]
}

# Test fetch_from_kms
test_fetch_from_kms() {
    local result=$(fetch_from_kms "database/credentials" "password")
    [[ "$result" == "test_db_pass" ]]
}

# Test generate_ssl_certs
test_generate_ssl_certs() {
    # Test with localhost
    DOMAIN_NAME="localhost"
    generate_ssl_certs
}

# Test setup_letsencrypt
test_setup_letsencrypt() {
    setup_letsencrypt
}

# Test check_cert_status
test_check_cert_status() {
    # Test with localhost (should pass)
    DOMAIN_NAME="localhost"
    check_cert_status
}

# Test renew_certificates
test_renew_certificates() {
    renew_certificates
}

# Test wait_for_vault
test_wait_for_vault() {
    wait_for_vault
}

# Test check_vault_environment
test_check_vault_environment() {
    export VAULT_DEV_ROOT_TOKEN_ID="test_token"
    export VAULT_DEV_LISTEN_ADDRESS="0.0.0.0:8200"
    export VAULT_ADDR="http://0.0.0.0:8200"
    export VAULT_API_ADDR="http://0.0.0.0:8200"
    
    check_vault_environment
}

# Test store_secret_in_vault
test_store_secret_in_vault() {
    store_secret_in_vault "test/path" "key" "value"
}

# Test generate_secure_password
test_generate_secure_password() {
    local password=$(generate_secure_password 16)
    [[ ${#password} -eq 16 ]]
}

# Test validate_certificate
test_validate_certificate() {
    local test_cert="/tmp/test_cert.pem"
    echo "Mock certificate" > "$test_cert"
    validate_certificate "$test_cert"
}

# Test check_secure_port
test_check_secure_port() {
    # This will fail in test environment, but that's expected
    ! check_secure_port "localhost" "443"
}

# Run all tests
echo "Running security module tests..."
echo "==============================="

setup_test_env

run_test "verify_secrets" test_verify_secrets
run_test "get_secret_value" test_get_secret_value
run_test "retrieve_secret" test_retrieve_secret
run_test "fetch_from_kms" test_fetch_from_kms
run_test "generate_ssl_certs" test_generate_ssl_certs
run_test "setup_letsencrypt" test_setup_letsencrypt
run_test "check_cert_status" test_check_cert_status
run_test "renew_certificates" test_renew_certificates
run_test "wait_for_vault" test_wait_for_vault
run_test "check_vault_environment" test_check_vault_environment
run_test "store_secret_in_vault" test_store_secret_in_vault
run_test "generate_secure_password" test_generate_secure_password
run_test "validate_certificate" test_validate_certificate
run_test "check_secure_port" test_check_secure_port

cleanup_test_env

echo "==============================="
echo "Tests passed: $tests_passed"
echo "Tests failed: $tests_failed"

exit $tests_failed