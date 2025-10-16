#!/bin/bash
# security.sh - Security, secrets, and certificate management functions

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"

# Security constants
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-2}

# Verify all required secrets are available
verify_secrets() {
    local required_secrets=(
        "POSTGRESQL_PASSWORD"
        "ST_API_KEY"
        "ST_DASHBOARD_API_KEY"
        "VAULT_TOKEN"
    )

    for secret in "${required_secrets[@]}"; do
        if [ -z "${!secret}" ]; then
            # Map environment variables to Vault paths and keys
            local vault_path
            local key
            case "$secret" in
                "POSTGRESQL_PASSWORD")
                    vault_path="database/credentials"
                    key="password"
                    ;;
                "ST_API_KEY")
                    vault_path="supertokens/credentials"
                    key="api_key"
                    ;;
                "ST_DASHBOARD_API_KEY")
                    vault_path="supertokens/credentials"
                    key="dashboard_key"
                    ;;
                "VAULT_TOKEN")
                    vault_path="vault/credentials"
                    key="token"
                    ;;
            esac

            # Fetch from Vault using correct path structure
            local value=$(fetch_from_kms "$vault_path" "$key")
            if [ -n "$value" ]; then
                export "$secret=$value"
                log_message "Retrieved $secret from Vault"
            else
                log_message "Failed to retrieve $secret from Vault"
                return 1
            fi
        fi
    done
    return 0
}

# Get secret value with retry logic
get_secret_value() {
    local secret_name="$1"
    local retries=0

    while [ $retries -lt $MAX_RETRIES ]; do
        local value=$(docker secret inspect --format '{{.Spec.Data}}' "$secret_name" 2>/dev/null | base64 -d)
        if [ -n "$value" ]; then
            echo "$value"
            return 0
        fi
        echo "Retry $((retries+1))/$MAX_RETRIES: Failed to retrieve value for secret $secret_name"
        sleep $RETRY_DELAY
        retries=$((retries+1))
    done

    echo "Error: Failed to retrieve value for secret $secret_name after $MAX_RETRIES attempts." >&2
    return 1
}

# Retrieve secret with fallback mechanisms
retrieve_secret() {
    local secret_name="$1"
    local secret_value=""

    # Attempt to fetch from Vault (KMS)
    if command -v fetch_from_kms > /dev/null 2>&1; then
        fetch_from_kms "$secret_name" && return 0
    else
        log_message "WARNING: KMS fetch function not found. Falling back to environment variables."
    fi

    # Fallback to environment variable
    secret_value="${!secret_name}"
    if [ -z "$secret_value" ]; then
        log_message "ERROR: Secret $secret_name is not set in Vault or environment variables."
        return 1
    fi

    echo "$secret_value"
    return 0
}

# Fetch secrets from KMS/Vault
fetch_from_kms() {
    local secret_path="$1"
    local key="$2"
    local vault_url="${VAULT_ADDR:-http://vault:8200}"
    local max_attempts=30
    local attempt=1

    log_message "Fetching secret from path: sting/$secret_path, key: $key"

    while [ $attempt -le $max_attempts ]; do
        # Determine token based on mode
        local token="${VAULT_DEV_ROOT_TOKEN_ID:-${VAULT_TOKEN}}"

        # Single jq command to extract the specific key
        local secret_value=$(curl -s \
            --header "X-Vault-Token: ${token}" \
            "${vault_url}/v1/sting/data/${secret_path}" \
            | jq -r ".data.data.${key}")

        # Check for valid response
        if [ $? -eq 0 ] && [ -n "$secret_value" ] && [ "$secret_value" != "null" ]; then
            echo "$secret_value"
            return 0
        fi

        log_message "Waiting for Vault... attempt $attempt/$max_attempts"
        sleep 2
        attempt=$((attempt + 1))
    done

    log_message "Failed to retrieve secret from path: $secret_path"
    return 1
}


# Setup Let's Encrypt for production certificates
setup_letsencrypt() {
    log_message "Setting up Let's Encrypt..."
    
    # Install certbot if not present
    if ! command -v certbot &> /dev/null; then
        log_message "Installing certbot..."
        if [[ "$(uname)" == "Darwin" ]]; then
            if command -v brew &> /dev/null; then
                brew install certbot
            else
                log_message "ERROR: Homebrew not found. Please install certbot manually."
                return 1
            fi
        else
            if command -v apt-get &> /dev/null; then
                sudo apt-get update
                sudo apt-get install -y certbot
            elif command -v yum &> /dev/null; then
                sudo yum install -y certbot
            else
                log_message "ERROR: Package manager not found. Please install certbot manually."
                return 1
            fi
        fi
    fi

    # Create required directories with proper permissions
    local cert_base="${INSTALL_DIR}/certs"
    mkdir -p "${cert_base}/config" "${cert_base}/work" "${cert_base}/logs"
    chmod -R 755 "${cert_base}"

    # Set up auto-renewal
    if [[ "$(uname)" != "Darwin" ]]; then
        # Add certbot renewal to crontab with custom paths
        (crontab -l 2>/dev/null; echo "0 0 * * * certbot renew --quiet \
            --config-dir ${cert_base}/config \
            --work-dir ${cert_base}/work \
            --logs-dir ${cert_base}/logs \
            && docker compose -f ${INSTALL_DIR}/docker-compose.yml restart app frontend") | crontab -
    fi
    
    log_message "Let's Encrypt setup completed"
}

# Check certificate status and expiry
check_cert_status() {
    local domain="${DOMAIN_NAME:-localhost}"
    local cert_dir="${INSTALL_DIR}/certs"
    
    if [ "$domain" == "localhost" ]; then
        log_message "Using self-signed certificates for local development"
        return 0
    fi
    
    if [ -f "${cert_dir}/config/live/${domain}/cert.pem" ]; then
        local expiry
        expiry=$(openssl x509 -enddate -noout -in "${cert_dir}/config/live/${domain}/cert.pem" | cut -d= -f2)
        log_message "Certificate for $domain expires on: $expiry"
        
        # Check if renewal is needed (30 days before expiry)
        local expiry_date=$(date -d "${expiry}" +%s 2>/dev/null || date -j -f "%b %d %H:%M:%S %Y %Z" "$expiry" +%s)
        local today=$(date +%s)
        local days_left=$(( (expiry_date - today) / 86400 ))
        
        if [ $days_left -lt 30 ]; then
            log_message "Certificate renewal needed (${days_left} days left)"
            return 1
        fi
        
        log_message "Certificate is valid for ${days_left} more days"
        return 0
    else
        log_message "No certificate found for $domain"
        return 1
    fi
}

# Renew SSL certificates
renew_certificates() {
    local cert_base="${INSTALL_DIR}/certs"
    log_message "Checking and renewing SSL certificates..."
    
    # Stop services that might be using port 80
    docker compose stop app frontend
    
    # Renew certificates
    certbot renew --quiet \
        --config-dir "${cert_base}/config" \
        --work-dir "${cert_base}/work" \
        --logs-dir "${cert_base}/logs"
    
    # Update symlinks if needed
    if [ -n "$DOMAIN_NAME" ] && [ "$DOMAIN_NAME" != "localhost" ]; then
        ln -sf "${cert_base}/config/live/${DOMAIN_NAME}/fullchain.pem" "${cert_base}/server.crt"
        ln -sf "${cert_base}/config/live/${DOMAIN_NAME}/privkey.pem" "${cert_base}/server.key"
    fi
    
    # Restart services
    docker compose start app frontend
    log_message "Certificate renewal complete"
}


# Check Vault environment variables
check_vault_environment() {
    local required_vars=(
        "VAULT_DEV_ROOT_TOKEN_ID"
        "VAULT_DEV_LISTEN_ADDRESS"
        "VAULT_ADDR"
        "VAULT_API_ADDR"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_message "ERROR: Missing required Vault environment variables: ${missing_vars[*]}"
        return 1
    fi
    
    # Verify addresses are properly formatted
    if [[ "$VAULT_DEV_LISTEN_ADDRESS" != "0.0.0.0:8200" ]]; then
        log_message "ERROR: VAULT_DEV_LISTEN_ADDRESS should be 0.0.0.0:8200"
        return 1
    fi
    
    if [[ "$VAULT_ADDR" != "http://0.0.0.0:8200" ]]; then
        log_message "ERROR: VAULT_ADDR should be http://0.0.0.0:8200"
        return 1
    fi
    
    log_message "Vault environment variables are properly configured"
    return 0
}

# Helper function: Store secret in Vault
store_secret_in_vault() {
    local secret_path="$1"
    local key="$2"
    local value="$3"
    local vault_url="${VAULT_ADDR:-http://localhost:8200}"
    
    if [ -z "$secret_path" ] || [ -z "$key" ] || [ -z "$value" ]; then
        log_message "ERROR: Missing parameters for store_secret_in_vault"
        return 1
    fi
    
    log_message "Storing secret in Vault: sting/$secret_path"
    
    local token="${VAULT_DEV_ROOT_TOKEN_ID:-${VAULT_TOKEN}}"
    
    # Store the secret using Vault's KV v2 API
    local response=$(curl -s -w "%{http_code}" \
        --header "X-Vault-Token: ${token}" \
        --header "Content-Type: application/json" \
        --request POST \
        --data "{\"data\":{\"${key}\":\"${value}\"}}" \
        "${vault_url}/v1/sting/data/${secret_path}")
    
    local http_code="${response: -3}"
    if [ "$http_code" = "200" ] || [ "$http_code" = "204" ]; then
        log_message "Secret stored successfully in Vault"
        return 0
    else
        log_message "ERROR: Failed to store secret in Vault (HTTP $http_code)"
        return 1
    fi
}

# Helper function: Generate random password
generate_secure_password() {
    local length="${1:-32}"
    
    if command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
    elif command -v tr >/dev/null 2>&1 && [ -c /dev/urandom ]; then
        tr -dc 'A-Za-z0-9!@#$%^&*()_+=' < /dev/urandom | head -c "$length"
    else
        # Fallback using date and random
        echo "${RANDOM}$(date +%s)${RANDOM}" | sha256sum | head -c "$length"
    fi
}

# Helper function: Validate certificate file
validate_certificate() {
    local cert_file="$1"
    
    if [ ! -f "$cert_file" ]; then
        log_message "Certificate file not found: $cert_file"
        return 1
    fi
    
    # Check if certificate is valid
    if openssl x509 -in "$cert_file" -text -noout >/dev/null 2>&1; then
        log_message "Certificate is valid: $cert_file"
        return 0
    else
        log_message "Invalid certificate: $cert_file"
        return 1
    fi
}

# Generate SSL certificates
generate_ssl_certs() {
    local domain="${DOMAIN_NAME:-localhost}"
    local email="${CERTBOT_EMAIL:-your-email@example.com}"
    local temp_cert_dir="/tmp/sting_certs"
    
    log_message "Setting up SSL certificates..."
    
    # Create temp directory and ensure it's clean
    rm -rf "${temp_cert_dir}"
    mkdir -p "${temp_cert_dir}"
    
    if [ "$domain" == "localhost" ]; then
        log_message "Generating self-signed certificates for local development..."
        # Generate directly with proper names
        openssl req -x509 -newkey rsa:4096 -nodes \
            -out "${temp_cert_dir}/server.crt" \
            -keyout "${temp_cert_dir}/server.key" \
            -days 365 \
            -subj "/C=US/ST=State/L=City/O=STING/CN=localhost"
            
        # Verify files exist before copying
        if [ ! -f "${temp_cert_dir}/server.crt" ] || [ ! -f "${temp_cert_dir}/server.key" ]; then
            log_message "ERROR: Certificate generation failed"
            return 1
        fi
        
        # Copy to install directory first
        mkdir -p "${INSTALL_DIR}/certs"
        cp "${temp_cert_dir}/server.crt" "${INSTALL_DIR}/certs/"
        cp "${temp_cert_dir}/server.key" "${INSTALL_DIR}/certs/"
        chmod 644 "${INSTALL_DIR}/certs/server.crt"
        chmod 600 "${INSTALL_DIR}/certs/server.key"
        log_message "SSL certificates copied to ${INSTALL_DIR}/certs"
        
        # Apply WSL2 Docker fixes if needed before pulling alpine image
        if [ -f "${SCRIPT_DIR}/docker_wsl_fix.sh" ]; then
            source "${SCRIPT_DIR}/docker_wsl_fix.sh"
            fix_docker_credential_helper >/dev/null 2>&1
        fi
        
        # Copy files to Docker volume
        docker run --rm -v sting_certs:/certs -v ${temp_cert_dir}:/source alpine sh -c \
            "mkdir -p /certs && \
             cp /source/server.crt /certs/ && \
             cp /source/server.key /certs/ && \
             chmod 644 /certs/server.crt && \
             chmod 600 /certs/server.key"
        log_message "SSL certificates copied to Docker volume"
    fi
    
    # Verify the copy worked
    docker run --rm -v sting_certs:/certs alpine ls -la /certs
    
    # Cleanup
    rm -rf "${temp_cert_dir}"
    log_message "SSL certificates installation complete"
    return 0
}

# Wait for Vault to be ready and configure it
wait_for_vault() {
    local vault_addr="http://localhost:8200"
    local max_attempts=30
    local attempt=1
    local delay=5
    
    log_message "Waiting for Vault to initialize..."
    
    # First try direct HTTP health check
    if curl -s "$vault_addr/v1/sys/health" | jq -e '.initialized == true and .sealed == false' > /dev/null 2>&1; then
        log_message "Vault API is responsive and ready (HTTP check)"
        
        # Set environment variables for Vault
        export VAULT_TOKEN="root"
        export VAULT_ADDR="$vault_addr"
        
        # Check if vault container is running
        if docker ps | grep -q vault; then
            log_message "Vault container is running"
            
            # Try to apply configuration
            if docker compose exec -T vault vault secrets list 2>/dev/null | grep -q "^sting/"; then
                log_message "Vault is already configured with sting/ secrets engine"
                return 0
            fi
            
            log_message "Configuring Vault..."
            # Enable KV secrets engine
            docker compose exec -T vault vault secrets enable -path=sting kv-v2 || true
            
            # Create policy with UI access
            docker compose exec -T vault vault policy write sting-policy - <<EOF
path "sting/*" {
    capabilities = ["create", "read", "update", "delete", "list"]
}
path "sys/internal/ui/*" {
    capabilities = ["read", "list"]
}
path "sys/mounts/*" {
    capabilities = ["read", "list"]
}
EOF
            
            log_message "Vault is fully initialized and configured"
            return 0
        fi
    fi
    
    # If direct check failed, try container-based check
    while [ $attempt -le $max_attempts ]; do
        # First check: Vault container status
        if docker ps | grep -q "sting.*vault.*healthy"; then
            log_message "Vault container is healthy according to Docker"
            
            # Try direct HTTP health check again
            if curl -s --max-time 2 "$vault_addr/v1/sys/health" | jq -e '.initialized == true' > /dev/null 2>&1; then
                log_message "Vault API is responsive - API health check passed"
                
                # Set environment variables for Vault
                export VAULT_TOKEN="root"
                export VAULT_ADDR="$vault_addr"
                
                # Configure Vault
                docker compose exec -T vault vault secrets enable -path=sting kv-v2 2>/dev/null || true
                
                # Create policy
                docker compose exec -T vault vault policy write sting-policy - <<EOF
path "sting/*" {
    capabilities = ["create", "read", "update", "delete", "list"]
}
path "sys/internal/ui/*" {
    capabilities = ["read", "list"]
}
path "sys/mounts/*" {
    capabilities = ["read", "list"]
}
EOF
                
                log_message "Vault is fully initialized and configured"
                return 0
            fi
        fi
        
        log_message "Waiting for Vault... attempt $attempt/$max_attempts"
        sleep $delay
        attempt=$((attempt + 1))
    done
    
    # Final check to see if the Vault container is at least running
    if docker ps | grep -q "sting.*vault"; then
        log_message "WARNING: Vault container is running but might not be fully initialized. Continuing anyway..."
        return 0
    fi
    
    log_message "ERROR: Vault failed to initialize after $max_attempts attempts"
    return 1
}

# Helper function: Check if port is secure (HTTPS)
check_secure_port() {
    local host="$1"
    local port="$2"
    
    if timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
        if echo | openssl s_client -connect "$host:$port" -verify_return_error >/dev/null 2>&1; then
            log_message "Secure connection verified: $host:$port"
            return 0
        else
            log_message "WARNING: Insecure connection: $host:$port"
            return 1
        fi
    else
        log_message "Cannot connect to: $host:$port"
        return 1
    fi
}