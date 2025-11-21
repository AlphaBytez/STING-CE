#!/bin/bash
# security.sh - Security, secrets, and certificate management functions

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"

# Security constants
MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-2}

# Safe file system operation helpers
# These functions handle permission issues gracefully with proper error reporting

# Safe directory creation with permission handling
safe_mkdir() {
    local dir_path="$1"
    local critical="${2:-false}"  # Set to "true" for critical paths
    
    if ! mkdir -p "$dir_path" 2>/dev/null; then
        if [ "$critical" = "true" ]; then
            log_message "ERROR: Failed to create critical directory: $dir_path" "ERROR"
            log_message "Attempting with elevated permissions..." "ERROR"
            if sudo mkdir -p "$dir_path" 2>/dev/null; then
                log_message "✓ Created with sudo: $dir_path"
                return 0
            else
                log_message "CRITICAL: Cannot create required directory: $dir_path" "ERROR"
                log_message "Installation cannot continue." "ERROR"
                return 1
            fi
        else
            log_message "WARNING: Failed to create directory: $dir_path"
            return 1
        fi
    fi
    return 0
}

# Safe file removal with permission handling
safe_rm() {
    local path="$1"
    local critical="${2:-false}"  # Set to "true" for critical operations
    
    if [ ! -e "$path" ]; then
        return 0  # Already gone, success
    fi
    
    if ! rm -rf "$path" 2>/dev/null; then
        if [ "$critical" = "true" ]; then
            log_message "ERROR: Failed to remove critical path: $path" "ERROR"
            log_message "Attempting with elevated permissions..." "ERROR"
            if sudo rm -rf "$path" 2>/dev/null; then
                log_message "✓ Removed with sudo: $path"
                return 0
            else
                log_message "CRITICAL: Cannot remove required path: $path" "ERROR"
                log_message "Installation cannot continue." "ERROR"
                return 1
            fi
        else
            log_message "WARNING: Failed to remove path: $path (skipping)"
            return 1
        fi
    fi
    return 0
}

# Safe chmod with permission handling
safe_chmod() {
    local perms="$1"
    local path="$2"
    local critical="${3:-false}"  # Set to "true" for critical operations
    
    if ! chmod "$perms" "$path" 2>/dev/null; then
        if [ "$critical" = "true" ]; then
            log_message "ERROR: Failed to set permissions $perms on: $path" "ERROR"
            log_message "Attempting with elevated permissions..." "ERROR"
            if sudo chmod "$perms" "$path" 2>/dev/null; then
                log_message "✓ Set permissions with sudo: $perms on $path"
                return 0
            else
                log_message "CRITICAL: Cannot set required permissions on: $path" "ERROR"
                log_message "Installation cannot continue." "ERROR"
                return 1
            fi
        else
            log_message "WARNING: Failed to set permissions $perms on: $path"
            return 1
        fi
    fi
    return 0
}

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


# Install mkcert for locally-trusted certificates
install_mkcert() {
    log_message "Installing mkcert for locally-trusted certificates..."

    if command -v mkcert &> /dev/null; then
        log_message "mkcert already installed"
        return 0
    fi

    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS installation
        if command -v brew &> /dev/null; then
            brew install mkcert nss
            mkcert -install
        else
            log_message "ERROR: Homebrew not found. Please install mkcert manually from: https://github.com/FiloSottile/mkcert"
            return 1
        fi
    else
        # Linux installation
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            sudo apt-get update
            sudo apt-get install -y wget libnss3-tools

            # Download and install mkcert
            local mkcert_version="v1.4.4"
            wget -O /tmp/mkcert "https://github.com/FiloSottile/mkcert/releases/download/${mkcert_version}/mkcert-${mkcert_version}-linux-amd64"
            chmod +x /tmp/mkcert
            sudo mv /tmp/mkcert /usr/local/bin/mkcert
            mkcert -install
        elif command -v yum &> /dev/null; then
            # RHEL/CentOS
            sudo yum install -y wget nss-tools

            # Download and install mkcert
            local mkcert_version="v1.4.4"
            wget -O /tmp/mkcert "https://github.com/FiloSottile/mkcert/releases/download/${mkcert_version}/mkcert-${mkcert_version}-linux-amd64"
            chmod +x /tmp/mkcert
            sudo mv /tmp/mkcert /usr/local/bin/mkcert
            mkcert -install
        else
            log_message "ERROR: Package manager not found. Please install mkcert manually from: https://github.com/FiloSottile/mkcert"
            return 1
        fi
    fi

    log_message "mkcert installed successfully"
    return 0
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
    safe_mkdir "${cert_base}/config" "true" || return 1
    safe_mkdir "${cert_base}/work" "true" || return 1
    safe_mkdir "${cert_base}/logs" "true" || return 1
    safe_chmod "-R 755" "${cert_base}" "true" || return 1

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

# Detect if domain is a local custom domain (not publicly routable)
is_local_domain() {
    local domain="$1"

    # Check for common local TLDs
    if [[ "$domain" =~ \.(local|localhost|test|internal|lan)$ ]]; then
        return 0
    fi

    # Check if domain is in /etc/hosts (indicates local override)
    if grep -q "^[^#]*[[:space:]]${domain}[[:space:]]*$" /etc/hosts 2>/dev/null; then
        return 0
    fi

    # Check if it's a bare hostname without dots (local machine name)
    if [[ ! "$domain" =~ \. ]]; then
        return 0
    fi

    return 1
}

# Generate SSL certificates
generate_ssl_certs() {
    # Use STING_HOSTNAME (set during installation) or fallback to DOMAIN_NAME or localhost
    local domain="${STING_HOSTNAME:-${DOMAIN_NAME:-localhost}}"
    local email="${CERTBOT_EMAIL:-your-email@example.com}"
    local temp_cert_dir="/tmp/sting_certs"

    log_message "Setting up SSL certificates for domain: $domain"

    # Create temp directory and ensure it's clean
    # Handle permission issues on Ubuntu where Docker may have created this with root ownership
    if [ -d "${temp_cert_dir}" ]; then
        if ! safe_rm "${temp_cert_dir}"; then
            log_message "WARNING: Could not clean ${temp_cert_dir}, trying alternative location..."
            temp_cert_dir="/tmp/sting_certs_$(date +%s)"
        fi
    fi
    
    # Create directories - these are critical for certificate generation
    if ! safe_mkdir "${temp_cert_dir}" "true"; then
        log_message "CRITICAL: Cannot create temp certificate directory" "ERROR"
        return 1
    fi
    
    if ! safe_mkdir "${INSTALL_DIR}/certs" "true"; then
        log_message "CRITICAL: Cannot create certificate directory" "ERROR"
        return 1
    fi

    # Set trap to cleanup temp directory on exit/error
    trap "safe_rm '${temp_cert_dir}' || true" RETURN ERR

    # Determine certificate generation method based on domain type
    if [ "$domain" == "localhost" ]; then
        # Standard localhost - use self-signed (browsers have exception for localhost)
        log_message "Generating self-signed certificates for localhost..."
        openssl req -x509 -newkey rsa:4096 -nodes \
            -out "${temp_cert_dir}/server.crt" \
            -keyout "${temp_cert_dir}/server.key" \
            -days 365 \
            -subj "/C=US/ST=State/L=City/O=STING/CN=localhost"

    elif is_local_domain "$domain"; then
        # Local custom domain (e.g., sting.local) - use mkcert for browser trust
        log_message "Detected local custom domain: $domain"
        log_message "Using mkcert to generate locally-trusted certificates..."

        # Install mkcert if not present
        if ! command -v mkcert &> /dev/null; then
            log_message "mkcert not found, installing..."
            log_message "⚠️  IMPORTANT: You will be prompted for your sudo password to install mkcert"
            log_message "    This is required to add the local Certificate Authority to your system trust store"
            echo ""
            echo "Press ENTER to continue with mkcert installation (you will be prompted for sudo password)..."
            read -r

            install_mkcert || {
                log_message "ERROR: mkcert installation failed" "ERROR"
                log_message "WebAuthn/Passkeys REQUIRE trusted certificates for local domains like '$domain'" "ERROR"
                log_message "" "ERROR"
                log_message "Installation cannot continue. Please either:" "ERROR"
                log_message "  1. Install mkcert manually: brew install mkcert && mkcert -install" "ERROR"
                log_message "  2. Use 'localhost' instead of '$domain' (self-signed certs work for localhost)" "ERROR"
                return 1
            }
        fi

        # Verify mkcert is properly installed and CA is trusted
        if command -v mkcert &> /dev/null; then
            # Check if mkcert CA is installed
            if ! mkcert -CAROOT &> /dev/null; then
                log_message "ERROR: mkcert CA not installed properly" "ERROR"
                log_message "Please run: mkcert -install" "ERROR"
                return 1
            fi

            # Generate locally-trusted certificates with mkcert
            cd "${temp_cert_dir}"
            mkcert -cert-file server.crt -key-file server.key "$domain" "*.${domain}" localhost || {
                log_message "ERROR: mkcert certificate generation failed"
                return 1
            }
            log_message "✅ Generated locally-trusted certificates with mkcert"
            log_message "NOTE: These certificates are trusted by your system's browsers"
        else
            log_message "ERROR: mkcert not found after installation" "ERROR"
            return 1
        fi

    else
        # Public domain - use Let's Encrypt
        log_message "Detected public domain: $domain"
        log_message "Setting up Let's Encrypt for production certificates..."

        # Note: Let's Encrypt setup requires additional configuration
        # For now, fall back to self-signed and warn user
        log_message "WARNING: Let's Encrypt requires additional setup (DNS, port 80 access)"
        log_message "Generating self-signed certificates as fallback..."
        log_message "For production, please configure Let's Encrypt manually"

        openssl req -x509 -newkey rsa:4096 -nodes \
            -out "${temp_cert_dir}/server.crt" \
            -keyout "${temp_cert_dir}/server.key" \
            -days 365 \
            -subj "/C=US/ST=State/L=City/O=STING/CN=${domain}"
    fi

    # Verify files exist before copying
    if [ ! -f "${temp_cert_dir}/server.crt" ] || [ ! -f "${temp_cert_dir}/server.key" ]; then
        log_message "ERROR: Certificate generation failed"
        return 1
    fi

    # Copy to install directory first
    cp "${temp_cert_dir}/server.crt" "${INSTALL_DIR}/certs/" || {
        log_message "ERROR: Failed to copy certificate file" "ERROR"
        return 1
    }
    cp "${temp_cert_dir}/server.key" "${INSTALL_DIR}/certs/" || {
        log_message "ERROR: Failed to copy key file" "ERROR"
        return 1
    }
    
    # Set proper permissions - critical for security
    safe_chmod 644 "${INSTALL_DIR}/certs/server.crt" "true" || return 1
    safe_chmod 600 "${INSTALL_DIR}/certs/server.key" "true" || return 1
    log_message "SSL certificates copied to ${INSTALL_DIR}/certs"

    # Apply WSL2 Docker fixes if needed before pulling alpine image
    if [ -f "${SCRIPT_DIR}/docker_wsl_fix.sh" ]; then
        source "${SCRIPT_DIR}/docker_wsl_fix.sh"
        fix_docker_credential_helper >/dev/null 2>&1
    fi

    # Copy files to Docker volume with proper ownership for Kratos (UID 10000)
    # Use INSTALL_DIR/certs since we already copied files there
    # Note: Using 644 for server.key since it's in a protected Docker volume
    # and Kratos may run with different GID than file ownership
    docker run --rm -v sting_certs:/certs -v "${INSTALL_DIR}/certs":/source alpine sh -c \
        "mkdir -p /certs && \
         cp /source/server.crt /certs/ && \
         cp /source/server.key /certs/ && \
         chmod 644 /certs/server.crt && \
         chmod 644 /certs/server.key && \
         chown -R 10000:10000 /certs/"
    log_message "SSL certificates copied to Docker volume"

    # Verify the copy worked
    docker run --rm -v sting_certs:/certs alpine ls -la /certs

    # Cleanup - non-critical operation
    safe_rm "${temp_cert_dir}" || log_message "Note: Temp directory cleanup skipped: ${temp_cert_dir}"
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

    # First try docker exec vault status (most reliable method)
    if docker ps | grep -q "sting.*vault" && \
       docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Initialized.*true"; then
        log_message "Vault is initialized (verified via docker exec)"

        # Set environment variables for Vault
        export VAULT_TOKEN="root"
        export VAULT_ADDR="$vault_addr"

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

    # Fallback: Try HTTP health check
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

            # Try docker exec vault status (more reliable than HTTP API)
            if docker exec sting-ce-vault vault status 2>/dev/null | grep -q "Initialized.*true"; then
                log_message "Vault is initialized (verified via docker exec)"

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

            # Fallback: Try HTTP health check
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

# Export mkcert CA certificate for client installation
export_ca_certificate() {
    local output_dir="${1:-./client-certs}"
    local ca_root_dir
    
    log_message "Exporting mkcert CA certificate for client installation..."
    
    # Find mkcert CA root directory
    if command -v mkcert &> /dev/null; then
        ca_root_dir=$(mkcert -CAROOT 2>/dev/null)
    else
        log_message "ERROR: mkcert not found" "ERROR"
        return 1
    fi
    
    if [ ! -f "${ca_root_dir}/rootCA.pem" ]; then
        log_message "ERROR: mkcert CA certificate not found at ${ca_root_dir}/rootCA.pem" "ERROR"
        log_message "Run: mkcert -install" "ERROR"
        return 1
    fi
    
    # Create output directory
    safe_mkdir "${output_dir}" "true" || return 1
    
    # Copy CA certificate
    cp "${ca_root_dir}/rootCA.pem" "${output_dir}/sting-ca.pem" || {
        log_message "ERROR: Failed to copy CA certificate" "ERROR"
        return 1
    }
    
    # Generate installation scripts for different platforms
    create_client_install_scripts "${output_dir}"

    # Copy certificates to install directory for web UI access
    local install_cert_dir="${INSTALL_DIR}/client-certs"
    if [ -d "${INSTALL_DIR}" ]; then
        log_message "📦 Copying certificates to install directory for web UI access..."
        safe_mkdir "${install_cert_dir}" "true" || {
            log_message "⚠️  Warning: Could not create ${install_cert_dir}" "WARNING"
        }

        if [ -d "${install_cert_dir}" ]; then
            cp -f "${output_dir}"/* "${install_cert_dir}/" 2>/dev/null || {
                log_message "⚠️  Warning: Could not copy certificates to ${install_cert_dir}" "WARNING"
            }

            if [ -f "${install_cert_dir}/sting-ca.pem" ]; then
                log_message "✅ Certificates copied to: ${install_cert_dir}/"
                log_message "   These are now accessible via the STING web UI"
            fi
        fi
    fi

    log_message "✅ CA certificate exported to: ${output_dir}/"
    log_message "📋 Files created:"
    log_message "   - sting-ca.pem (CA certificate)"
    log_message "   - install-ca-mac.sh (macOS installer)"
    log_message "   - install-ca-linux.sh (Linux installer)"
    log_message "   - install-ca-windows.ps1 (Windows installer)"
    log_message ""
    log_message "💡 Share the ${output_dir} folder with client machines"
    log_message "   Clients can run the appropriate install script for their OS"
    log_message "   Or download them from the web UI: Certificate Management page"

    return 0
}

# Create installation scripts for client platforms
create_client_install_scripts() {
    local output_dir="$1"
    local domain="${DOMAIN_NAME:-$(cat ${INSTALL_DIR}/.sting_domain 2>/dev/null || echo 'CONFIGURE_YOUR_DOMAIN.local')}"
    local vm_ip="${VM_IP:-$(ip route get 1 | awk '{print $7; exit}' 2>/dev/null || echo '192.168.1.100')}"
    
    # macOS installation script
    cat > "${output_dir}/install-ca-mac.sh" << EOF
#!/bin/bash
# STING-CE CA Certificate Installer for macOS
set -e

CA_FILE="sting-ca.pem"
DOMAIN="${domain}"
VM_IP="${vm_ip}"

echo "🔐 STING-CE Certificate Authority Installer for macOS"
echo "=================================================="
echo ""

# Check if CA file exists
if [ ! -f "\$CA_FILE" ]; then
    echo "❌ Error: \$CA_FILE not found"
    echo "Please run this script from the directory containing the CA certificate"
    exit 1
fi

# Install CA certificate
echo "📋 Installing CA certificate..."
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "\$CA_FILE"
echo "✅ CA certificate installed successfully"

# Add domain to hosts file if needed
echo ""
echo "🌐 Setting up domain resolution..."
if ! grep -q "\$DOMAIN" /etc/hosts; then
    echo "Adding \$DOMAIN to /etc/hosts..."
    echo "\$VM_IP \$DOMAIN" | sudo tee -a /etc/hosts > /dev/null
    echo "✅ Domain added to /etc/hosts"
else
    echo "✅ Domain already in /etc/hosts"
fi

echo ""
echo "🎉 Installation complete!"
echo "You can now access STING securely at: https://\$DOMAIN:8443"
echo "⚠️  Please restart your browser to load the new certificate"
EOF

    # Linux installation script
    cat > "${output_dir}/install-ca-linux.sh" << EOF
#!/bin/bash
# STING-CE CA Certificate Installer for Linux
set -e

CA_FILE="sting-ca.pem"
DOMAIN="${domain}"
VM_IP="${vm_ip}"

echo "🔐 STING-CE Certificate Authority Installer for Linux"
echo "================================================="
echo ""

# Check if CA file exists
if [ ! -f "\$CA_FILE" ]; then
    echo "❌ Error: \$CA_FILE not found"
    echo "Please run this script from the directory containing the CA certificate"
    exit 1
fi

# Detect Linux distribution and install CA certificate
echo "📋 Installing CA certificate..."
if [ -d "/etc/ssl/certs" ] && [ -d "/usr/local/share/ca-certificates" ]; then
    # Ubuntu/Debian
    sudo cp "\$CA_FILE" /usr/local/share/ca-certificates/sting-ca.crt
    sudo update-ca-certificates
    echo "✅ CA certificate installed (Ubuntu/Debian)"
elif [ -d "/etc/pki/ca-trust/source/anchors" ]; then
    # RHEL/CentOS/Fedora
    sudo cp "\$CA_FILE" /etc/pki/ca-trust/source/anchors/sting-ca.crt
    sudo update-ca-trust
    echo "✅ CA certificate installed (RHEL/CentOS/Fedora)"
elif [ -d "/usr/share/ca-certificates" ]; then
    # Generic approach
    sudo cp "\$CA_FILE" /usr/share/ca-certificates/sting-ca.crt
    echo "sting-ca.crt" | sudo tee -a /etc/ca-certificates.conf
    sudo update-ca-certificates
    echo "✅ CA certificate installed (Generic Linux)"
else
    echo "⚠️  Unsupported Linux distribution"
    echo "Please manually add \$CA_FILE to your system's certificate store"
fi

# Add domain to hosts file if needed
echo ""
echo "🌐 Setting up domain resolution..."
if ! grep -q "\$DOMAIN" /etc/hosts; then
    echo "Adding \$DOMAIN to /etc/hosts..."
    echo "\$VM_IP \$DOMAIN" | sudo tee -a /etc/hosts > /dev/null
    echo "✅ Domain added to /etc/hosts"
else
    echo "✅ Domain already in /etc/hosts"
fi

echo ""
echo "🎉 Installation complete!"
echo "You can now access STING securely at: https://\$DOMAIN:8443"
echo "⚠️  Please restart your browser to load the new certificate"
EOF

    # Windows PowerShell installation script
    cat > "${output_dir}/install-ca-windows.ps1" << EOF
# STING-CE CA Certificate Installer for Windows
# Run this script as Administrator

param(
    [string]\$CAFile = "sting-ca.pem",
    [string]\$Domain = "${domain}",
    [string]\$VMIP = "${vm_ip}"
)

Write-Host "🔐 STING-CE Certificate Authority Installer for Windows" -ForegroundColor Green
Write-Host "======================================================" -ForegroundColor Green
Write-Host ""

# Check if running as administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ Error: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if CA file exists
if (-not (Test-Path \$CAFile)) {
    Write-Host "❌ Error: \$CAFile not found" -ForegroundColor Red
    Write-Host "Please run this script from the directory containing the CA certificate" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Install CA certificate
Write-Host "📋 Installing CA certificate..." -ForegroundColor Yellow
try {
    Import-Certificate -FilePath \$CAFile -CertStoreLocation Cert:\LocalMachine\Root
    Write-Host "✅ CA certificate installed successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ Error installing certificate: \$_" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Add domain to hosts file if needed
Write-Host ""
Write-Host "🌐 Setting up domain resolution..." -ForegroundColor Yellow
\$hostsFile = "\$env:SystemRoot\System32\drivers\etc\hosts"
\$hostsContent = Get-Content \$hostsFile -ErrorAction SilentlyContinue
if (\$hostsContent -notmatch \$Domain) {
    Write-Host "Adding \$Domain to hosts file..." -ForegroundColor Yellow
    Add-Content -Path \$hostsFile -Value "\$VMIP \$Domain"
    Write-Host "✅ Domain added to hosts file" -ForegroundColor Green
} else {
    Write-Host "✅ Domain already in hosts file" -ForegroundColor Green
}

Write-Host ""
Write-Host "🎉 Installation complete!" -ForegroundColor Green
Write-Host "You can now access STING securely at: https://\$Domain:8443" -ForegroundColor Cyan
Write-Host "⚠️  Please restart your browser to load the new certificate" -ForegroundColor Yellow
Read-Host "Press Enter to exit"
EOF

    # Make scripts executable
    chmod +x "${output_dir}/install-ca-mac.sh"
    chmod +x "${output_dir}/install-ca-linux.sh"
}

# Copy exported certificates to remote hosts
copy_certs_to_host() {
    local target_host="$1"
    local remote_path="$2"
    local source_dir="$3"
    
    if [[ -z "$target_host" || -z "$remote_path" ]]; then
        log_message "❌ Target host and remote path required"
        log_message ""
        log_message "📋 Usage: msting copy-certs <user@host> <remote_path> [source_dir]"
        log_message ""
        log_message "🔍 Available certificate sources:"
        [[ -d "./sting-certs-export" ]] && log_message "  • ./sting-certs-export (default)"
        [[ -f "/opt/sting-ce/certs/server.crt" ]] && log_message "  • /opt/sting-ce/certs/ (server certificates)"
        [[ -f "/opt/sting-ce/sting-ca.pem" ]] && log_message "  • /opt/sting-ce/ (CA certificate)"
        log_message ""
        log_message "💡 Examples:"
        log_message "  msting copy-certs user@hostname.local /home/user/certs"
        log_message "  msting copy-certs user@192.168.1.100 /opt/certs ./sting-certs-export"
        log_message ""
        log_message "ℹ️  Run 'msting export-certs' first to create certificate bundle"
        return 1
    fi
    
    # Default source directory to last export or create new one
    if [[ -z "$source_dir" ]]; then
        source_dir="./sting-certs-export"
        if [[ ! -d "$source_dir" ]]; then
            log_message "📋 No source directory specified and ./sting-certs-export not found"
            log_message "Exporting certificates first..."
            export_ca_certificate "$source_dir" || return 1
        fi
    fi
    
    # Verify source directory exists and has required files
    if [[ ! -d "$source_dir" ]]; then
        log_message "ERROR: Source directory not found: $source_dir"
        return 1
    fi
    
    if [[ ! -f "$source_dir/sting-ca.pem" ]]; then
        log_message "ERROR: Certificate files not found in $source_dir"
        log_message "Run 'export-certs' first to generate certificate bundle"
        return 1
    fi
    
    log_message "📤 Copying certificates to $target_host:$remote_path"
    
    # Check if rsync is available (preferred)
    if command -v rsync &> /dev/null; then
        log_message "Using rsync for secure copy..."
        if rsync -avz --progress "$source_dir/" "$target_host:$remote_path/"; then
            log_message "✅ Certificates copied successfully using rsync"
        else
            log_message "❌ rsync failed, falling back to scp..."
            scp -r "$source_dir" "$target_host:$remote_path/" || {
                log_message "ERROR: Failed to copy certificates to remote host"
                return 1
            }
        fi
    else
        # Fall back to scp
        log_message "Using scp for secure copy..."
        scp -r "$source_dir" "$target_host:$remote_path/" || {
            log_message "ERROR: Failed to copy certificates to remote host"
            return 1
        }
        log_message "✅ Certificates copied successfully using scp"
    fi
    
    log_message ""
    log_message "📋 Next steps for the remote host:"
    log_message "   1. SSH to $target_host"
    log_message "   2. Navigate to $remote_path/$(basename "$source_dir")"
    log_message "   3. Run the appropriate installer:"
    log_message "      - macOS: ./install-ca-mac.sh"
    log_message "      - Linux: ./install-ca-linux.sh"
    log_message "      - Windows: install-ca-windows.ps1"
    log_message ""
    
    return 0
}