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
                log_message "[+] Created with sudo: $dir_path"
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
                log_message "[+] Removed with sudo: $path"
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
                log_message "[+] Set permissions with sudo: $perms on $path"
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
# Supports non-interactive mode for web wizard installation
install_mkcert() {
    log_message "Installing mkcert for locally-trusted certificates..."

    if command -v mkcert &> /dev/null; then
        log_message "mkcert already installed"
        return 0
    fi

    # Detect if running non-interactively (no TTY or NO_PROMPT set)
    local interactive=true
    if [ ! -t 0 ] || [ -n "$NO_PROMPT" ] || [ -n "$WIZARD_CONFIG_PATH" ]; then
        interactive=false
        log_message "Running in non-interactive mode"
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
            # Use DEBIAN_FRONTEND=noninteractive to prevent any prompts
            export DEBIAN_FRONTEND=noninteractive

            # Use sudo with -n flag for non-interactive, but fall back to regular sudo
            # (parent install_sting.sh should have established sudo credentials)
            sudo apt-get update -qq
            sudo apt-get install -y -qq wget libnss3-tools

            # Download and install mkcert
            local mkcert_version="v1.4.4"
            wget -q -O /tmp/mkcert "https://github.com/FiloSottile/mkcert/releases/download/${mkcert_version}/mkcert-${mkcert_version}-linux-amd64"
            chmod +x /tmp/mkcert
            sudo mv /tmp/mkcert /usr/local/bin/mkcert

            # mkcert -install adds CA to system trust store
            # CAROOT can be set to control where CA is stored
            mkcert -install
        elif command -v yum &> /dev/null; then
            # RHEL/CentOS
            sudo yum install -y -q wget nss-tools

            # Download and install mkcert
            local mkcert_version="v1.4.4"
            wget -q -O /tmp/mkcert "https://github.com/FiloSottile/mkcert/releases/download/${mkcert_version}/mkcert-${mkcert_version}-linux-amd64"
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
    # Check for wizard SSL configuration first (Let's Encrypt preference)
    local wizard_ssl_type=""
    local wizard_le_domain=""
    local wizard_le_email=""
    local wizard_custom_cert=""

    # Read wizard metadata from staged config if present
    if [ -f "/tmp/sting-setup-state/config.yml" ]; then
        wizard_ssl_type=$(grep '_wizard_metadata' -A 15 "/tmp/sting-setup-state/config.yml" 2>/dev/null | grep 'ssl_type:' | head -1 | cut -d: -f2 | tr -d ' "' || true)
        wizard_le_domain=$(grep '_wizard_metadata' -A 15 "/tmp/sting-setup-state/config.yml" 2>/dev/null | grep 'letsencrypt_domain:' | head -1 | cut -d: -f2 | tr -d ' "' || true)
        wizard_le_email=$(grep '_wizard_metadata' -A 15 "/tmp/sting-setup-state/config.yml" 2>/dev/null | grep 'letsencrypt_email:' | head -1 | cut -d: -f2 | tr -d ' "' || true)
        wizard_custom_cert=$(grep '_wizard_metadata' -A 15 "/tmp/sting-setup-state/config.yml" 2>/dev/null | grep 'custom_cert_upload:' | head -1 | cut -d: -f2 | tr -d ' "' || true)

        if [ -n "$wizard_ssl_type" ]; then
            log_message "Wizard SSL configuration detected: type=$wizard_ssl_type"
        fi
    fi

    # Also check installed config
    if [ -z "$wizard_ssl_type" ] && [ -f "${CONFIG_DIR}/config.yml" ]; then
        wizard_ssl_type=$(grep '_wizard_metadata' -A 15 "${CONFIG_DIR}/config.yml" 2>/dev/null | grep 'ssl_type:' | head -1 | cut -d: -f2 | tr -d ' "' || true)
        wizard_le_domain=$(grep '_wizard_metadata' -A 15 "${CONFIG_DIR}/config.yml" 2>/dev/null | grep 'letsencrypt_domain:' | head -1 | cut -d: -f2 | tr -d ' "' || true)
        wizard_le_email=$(grep '_wizard_metadata' -A 15 "${CONFIG_DIR}/config.yml" 2>/dev/null | grep 'letsencrypt_email:' | head -1 | cut -d: -f2 | tr -d ' "' || true)
        wizard_custom_cert=$(grep '_wizard_metadata' -A 15 "${CONFIG_DIR}/config.yml" 2>/dev/null | grep 'custom_cert_upload:' | head -1 | cut -d: -f2 | tr -d ' "' || true)
    fi

    # Check for custom uploaded certificates from wizard
    local staged_certs_dir="/tmp/sting-setup-state/staged-certs"
    if [ "$wizard_ssl_type" = "upload" ] || [ "$wizard_custom_cert" = "true" ]; then
        if [ -f "${staged_certs_dir}/server.crt" ] && [ -f "${staged_certs_dir}/server.key" ]; then
            log_message "Custom certificate upload detected from wizard"
            log_message "Using uploaded certificates from: $staged_certs_dir"
            
            # Validate the certificates before using
            if openssl x509 -in "${staged_certs_dir}/server.crt" -noout -subject 2>/dev/null; then
                # Create certs directory if needed
                if ! safe_mkdir "${INSTALL_DIR}/certs" "true"; then
                    log_message "CRITICAL: Cannot create certificate directory" "ERROR"
                    return 1
                fi
                
                # Copy the uploaded certificates
                cp "${staged_certs_dir}/server.crt" "${INSTALL_DIR}/certs/server.crt" || {
                    log_message "ERROR: Failed to copy uploaded certificate" "ERROR"
                    return 1
                }
                cp "${staged_certs_dir}/server.key" "${INSTALL_DIR}/certs/server.key" || {
                    log_message "ERROR: Failed to copy uploaded key" "ERROR"
                    return 1
                }
                
                # Set permissions
                chmod 644 "${INSTALL_DIR}/certs/server.crt"
                chmod 600 "${INSTALL_DIR}/certs/server.key"
                
                # Get cert info for logging
                local cert_subject=$(openssl x509 -in "${INSTALL_DIR}/certs/server.crt" -noout -subject 2>/dev/null | sed 's/subject=//')
                local cert_expiry=$(openssl x509 -in "${INSTALL_DIR}/certs/server.crt" -noout -enddate 2>/dev/null | sed 's/notAfter=//')
                
                log_message "[+] Custom certificates installed successfully!"
                log_message "    Subject: $cert_subject"
                log_message "    Expires: $cert_expiry"
                
                # Copy to Docker volume if it exists
                if [ -d "/var/lib/docker/volumes/sting_certs/_data" ]; then
                    cp "${INSTALL_DIR}/certs/server.crt" "/var/lib/docker/volumes/sting_certs/_data/server.crt" 2>/dev/null || true
                    cp "${INSTALL_DIR}/certs/server.key" "/var/lib/docker/volumes/sting_certs/_data/server.key" 2>/dev/null || true
                    log_message "[+] Custom certificates copied to Docker volume"
                fi
                
                return 0
            else
                log_message "ERROR: Uploaded certificate is invalid" "ERROR"
                return 1
            fi
        else
            log_message "WARNING: Custom cert upload selected but no certificates found at $staged_certs_dir" "WARNING"
            log_message "Falling back to self-signed certificates"
        fi
    fi

    # Try multiple sources to detect domain, prioritizing actual configuration
    local domain=""
    # If wizard specified Let's Encrypt with a domain, use that domain
    if [ "$wizard_ssl_type" = "letsencrypt" ] && [ -n "$wizard_le_domain" ]; then
        domain="$wizard_le_domain"
        log_message "Using Let's Encrypt domain from wizard: $domain"
    elif [ -n "$STING_HOSTNAME" ]; then
        domain="$STING_HOSTNAME"
    elif [ -n "$DOMAIN_NAME" ]; then
        domain="$DOMAIN_NAME"
    elif [ -f "${INSTALL_DIR}/.sting_domain" ]; then
        domain=$(cat "${INSTALL_DIR}/.sting_domain" 2>/dev/null)
        if [ -n "$domain" ]; then
            log_message "Using domain from .sting_domain: $domain"
        fi
    fi

    # If still no domain, try to detect from system hostname
    if [ -z "$domain" ]; then
        local sys_hostname=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")
        if [ -n "$sys_hostname" ] && [ "$sys_hostname" != "localhost" ]; then
            # If hostname doesn't have a TLD, add .local
            if [[ ! "$sys_hostname" =~ \. ]]; then
                domain="${sys_hostname}.local"
            else
                domain="$sys_hostname"
            fi
            log_message "Detected domain from system hostname: $domain"
        else
            domain="localhost"
            log_message "WARNING: Using localhost as fallback domain" "WARNING"
        fi
    fi

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
        # Local custom domain (e.g., sting-ce.local) - use mkcert for browser trust
        log_message "Detected local custom domain: $domain"
        log_message "Using mkcert to generate locally-trusted certificates..."

        # Install mkcert if not present
        if ! command -v mkcert &> /dev/null; then
            log_message "mkcert not found, installing..."

            # Check if running interactively (TTY available)
            if [ -t 0 ] && [ -z "$NO_PROMPT" ] && [ -z "$WIZARD_CONFIG_PATH" ]; then
                # Interactive mode - prompt user
                log_message "[!]  IMPORTANT: You will be prompted for your sudo password to install mkcert"
                log_message "    This is required to add the local Certificate Authority to your system trust store"
                echo ""
                echo "Press ENTER to continue with mkcert installation (you will be prompted for sudo password)..."
                read -r
            else
                # Non-interactive mode (web wizard) - proceed automatically
                log_message "Installing mkcert automatically (non-interactive mode)..."
            fi

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
            log_message "[+] Generated locally-trusted certificates with mkcert"
            log_message "NOTE: These certificates are trusted by your system's browsers"
        else
            log_message "ERROR: mkcert not found after installation" "ERROR"
            return 1
        fi

    else
        # Public domain - check if Let's Encrypt was requested via wizard
        log_message "Detected public domain: $domain"

        if [ "$wizard_ssl_type" = "letsencrypt" ] && [ -n "$wizard_le_domain" ]; then
            log_message "Let's Encrypt requested via wizard for domain: $wizard_le_domain"
            log_message "Email for certificate notifications: ${wizard_le_email:-not provided}"

            # Attempt to get Let's Encrypt certificate
            local le_email="${wizard_le_email:-}"

            if setup_letsencrypt_ssl "$wizard_le_domain" "$le_email"; then
                log_message "[+] Let's Encrypt certificate obtained successfully!"

                # Copy Let's Encrypt certs to STING cert directory
                local le_cert="/etc/letsencrypt/live/$wizard_le_domain/fullchain.pem"
                local le_key="/etc/letsencrypt/live/$wizard_le_domain/privkey.pem"

                if [ -f "$le_cert" ] && [ -f "$le_key" ]; then
                    cp "$le_cert" "${temp_cert_dir}/server.crt" || {
                        log_message "ERROR: Failed to copy Let's Encrypt certificate" "ERROR"
                        return 1
                    }
                    cp "$le_key" "${temp_cert_dir}/server.key" || {
                        log_message "ERROR: Failed to copy Let's Encrypt key" "ERROR"
                        return 1
                    }
                    log_message "[+] Let's Encrypt certificates ready for installation"
                else
                    log_message "ERROR: Let's Encrypt certificate files not found" "ERROR"
                    log_message "Expected: $le_cert and $le_key" "ERROR"
                    return 1
                fi
            else
                log_message "ERROR: Let's Encrypt setup failed" "ERROR"
                log_message "Please check:" "ERROR"
                log_message "  1. Domain DNS points to this server" "ERROR"
                log_message "  2. Port 80 is accessible from the internet" "ERROR"
                log_message "  3. No firewall blocking HTTP traffic" "ERROR"
                return 1
            fi
        else
            # No Let's Encrypt requested - fall back to self-signed and warn user
            log_message "Setting up certificates for production domain..."
            log_message "WARNING: Let's Encrypt was not selected in wizard"
            log_message "Generating self-signed certificates as fallback..."
            log_message "For production, run: msting setup-ssl $domain your-email@example.com"

            openssl req -x509 -newkey rsa:4096 -nodes \
                -out "${temp_cert_dir}/server.crt" \
                -keyout "${temp_cert_dir}/server.key" \
                -days 365 \
                -subj "/C=US/ST=State/L=City/O=STING/CN=${domain}"
        fi
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
        log_message " Copying certificates to install directory for web UI access..."
        safe_mkdir "${install_cert_dir}" "true" || {
            log_message "[!]  Warning: Could not create ${install_cert_dir}" "WARNING"
        }

        if [ -d "${install_cert_dir}" ]; then
            cp -f "${output_dir}"/* "${install_cert_dir}/" 2>/dev/null || {
                log_message "[!]  Warning: Could not copy certificates to ${install_cert_dir}" "WARNING"
            }

            if [ -f "${install_cert_dir}/sting-ca.pem" ]; then
                log_message "[+] Certificates copied to: ${install_cert_dir}/"
                log_message "   These are now accessible via the STING web UI"
            fi
        fi
    fi

    log_message "[+] CA certificate exported to: ${output_dir}/"
    log_message "📋 Files created:"
    log_message "   - sting-ca.pem (CA certificate)"
    log_message "   - install-ca-mac.sh (macOS installer)"
    log_message "   - install-ca-linux.sh (Linux installer)"
    log_message "   - install-ca-windows.ps1 (Windows installer)"
    log_message ""
    log_message "TIP: Share the ${output_dir} folder with client machines"
    log_message "   Clients can run the appropriate install script for their OS"
    log_message "   Or download them from the web UI: Certificate Management page"

    return 0
}

# Create installation scripts for client platforms
create_client_install_scripts() {
    local output_dir="$1"

    # Try multiple sources to detect domain, prioritizing actual configuration
    local domain=""
    if [ -n "$STING_HOSTNAME" ]; then
        domain="$STING_HOSTNAME"
    elif [ -n "$DOMAIN_NAME" ]; then
        domain="$DOMAIN_NAME"
    elif [ -f "${INSTALL_DIR}/.sting_domain" ]; then
        domain=$(cat "${INSTALL_DIR}/.sting_domain" 2>/dev/null)
    else
        # Last resort: try to detect from system hostname with .local suffix
        local sys_hostname=$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo "")
        if [ -n "$sys_hostname" ] && [ "$sys_hostname" != "localhost" ]; then
            # If hostname doesn't have a TLD, add .local
            if [[ ! "$sys_hostname" =~ \. ]]; then
                domain="${sys_hostname}.local"
            else
                domain="$sys_hostname"
            fi
        else
            # Absolute fallback - but this shouldn't happen in normal operation
            domain="CONFIGURE_YOUR_DOMAIN.local"
            log_message "WARNING: Could not detect hostname, using placeholder" "WARNING"
        fi
    fi

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
    echo "[-] Error: \$CA_FILE not found"
    echo "Please run this script from the directory containing the CA certificate"
    exit 1
fi

# Install CA certificate
echo "📋 Installing CA certificate..."
sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "\$CA_FILE"
echo "[+] CA certificate installed successfully"

# Add domain to hosts file if needed
echo ""
echo "🌐 Setting up domain resolution..."
if ! grep -q "\$DOMAIN" /etc/hosts; then
    echo "Adding \$DOMAIN to /etc/hosts..."
    echo "\$VM_IP \$DOMAIN" | sudo tee -a /etc/hosts > /dev/null
    echo "[+] Domain added to /etc/hosts"
else
    echo "[+] Domain already in /etc/hosts"
fi

echo ""
echo " Installation complete!"
echo "You can now access STING securely at: https://\$DOMAIN:8443"
echo "[!]  Please restart your browser to load the new certificate"
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
    echo "[-] Error: \$CA_FILE not found"
    echo "Please run this script from the directory containing the CA certificate"
    exit 1
fi

# Detect Linux distribution and install CA certificate
echo "📋 Installing CA certificate..."
if [ -d "/etc/ssl/certs" ] && [ -d "/usr/local/share/ca-certificates" ]; then
    # Ubuntu/Debian
    sudo cp "\$CA_FILE" /usr/local/share/ca-certificates/sting-ca.crt
    sudo update-ca-certificates
    echo "[+] CA certificate installed (Ubuntu/Debian)"
elif [ -d "/etc/pki/ca-trust/source/anchors" ]; then
    # RHEL/CentOS/Fedora
    sudo cp "\$CA_FILE" /etc/pki/ca-trust/source/anchors/sting-ca.crt
    sudo update-ca-trust
    echo "[+] CA certificate installed (RHEL/CentOS/Fedora)"
elif [ -d "/usr/share/ca-certificates" ]; then
    # Generic approach
    sudo cp "\$CA_FILE" /usr/share/ca-certificates/sting-ca.crt
    echo "sting-ca.crt" | sudo tee -a /etc/ca-certificates.conf
    sudo update-ca-certificates
    echo "[+] CA certificate installed (Generic Linux)"
else
    echo "[!]  Unsupported Linux distribution"
    echo "Please manually add \$CA_FILE to your system's certificate store"
fi

# Add domain to hosts file if needed
echo ""
echo "🌐 Setting up domain resolution..."
if ! grep -q "\$DOMAIN" /etc/hosts; then
    echo "Adding \$DOMAIN to /etc/hosts..."
    echo "\$VM_IP \$DOMAIN" | sudo tee -a /etc/hosts > /dev/null
    echo "[+] Domain added to /etc/hosts"
else
    echo "[+] Domain already in /etc/hosts"
fi

echo ""
echo " Installation complete!"
echo "You can now access STING securely at: https://\$DOMAIN:8443"
echo "[!]  Please restart your browser to load the new certificate"
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
    Write-Host "[-] Error: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if CA file exists
if (-not (Test-Path \$CAFile)) {
    Write-Host "[-] Error: \$CAFile not found" -ForegroundColor Red
    Write-Host "Please run this script from the directory containing the CA certificate" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Install CA certificate
Write-Host "📋 Installing CA certificate..." -ForegroundColor Yellow
try {
    Import-Certificate -FilePath \$CAFile -CertStoreLocation Cert:\LocalMachine\Root
    Write-Host "[+] CA certificate installed successfully" -ForegroundColor Green
} catch {
    Write-Host "[-] Error installing certificate: \$_" -ForegroundColor Red
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
    Write-Host "[+] Domain added to hosts file" -ForegroundColor Green
} else {
    Write-Host "[+] Domain already in hosts file" -ForegroundColor Green
}

Write-Host ""
Write-Host " Installation complete!" -ForegroundColor Green
Write-Host "You can now access STING securely at: https://\$Domain:8443" -ForegroundColor Cyan
Write-Host "[!]  Please restart your browser to load the new certificate" -ForegroundColor Yellow
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
        log_message "[-] Target host and remote path required"
        log_message ""
        log_message "📋 Usage: msting copy-certs <user@host> <remote_path> [source_dir]"
        log_message ""
        log_message " Available certificate sources:"
        [[ -d "./sting-certs-export" ]] && log_message "  • ./sting-certs-export (default)"
        [[ -f "/opt/sting-ce/certs/server.crt" ]] && log_message "  • /opt/sting-ce/certs/ (server certificates)"
        [[ -f "/opt/sting-ce/sting-ca.pem" ]] && log_message "  • /opt/sting-ce/ (CA certificate)"
        log_message ""
        log_message "TIP: Examples:"
        log_message "  msting copy-certs user@hostname.local /home/user/certs"
        log_message "  msting copy-certs user@192.168.1.100 /opt/certs ./sting-certs-export"
        log_message ""
        log_message "[*]  Run 'msting export-certs' first to create certificate bundle"
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
            log_message "[+] Certificates copied successfully using rsync"
        else
            log_message "[-] rsync failed, falling back to scp..."
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
        log_message "[+] Certificates copied successfully using scp"
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

# =============================================================================
# Let's Encrypt SSL Certificate Setup
# =============================================================================

# Function to check if Let's Encrypt certificates are valid
check_letsencrypt_certs() {
    local domain="${1:-$DOMAIN}"

    if [ -z "$domain" ]; then
        log_message "[-] Domain not configured" "ERROR"
        return 1
    fi

    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"
    local key_path="/etc/letsencrypt/live/$domain/privkey.pem"

    if [ -f "$cert_path" ] && [ -f "$key_path" ]; then
        # Check if cert is not expired
        if openssl x509 -enddate -noout -in "$cert_path" 2>/dev/null | grep -q "notAfter="; then
            local expiry_date=$(openssl x509 -enddate -noout -in "$cert_path" 2>/dev/null | cut -d= -f2)
            log_message "[+] Let's Encrypt certificates found (expires: $expiry_date)" "SUCCESS"
            return 0
        fi
    fi

    return 1
}

# Function to check certbot availability
check_certbot() {
    if command -v certbot &> /dev/null; then
        log_message "[+] certbot is installed: $(certbot --version 2>&1)" "SUCCESS"
        return 0
    fi

    log_message "[-] certbot is not installed" "WARNING"
    log_message "Installing certbot..."

    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install certbot
        else
            log_message "[-] Homebrew not found. Install certbot manually:" "ERROR"
            log_message "   brew install certbot" "INFO"
            return 1
        fi
    else
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt-get update && sudo apt-get install -y certbot python3-certbot-nginx
        elif command -v yum &> /dev/null; then
            sudo yum install -y certbot python3-certbot-nginx
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y certbot python3-certbot-nginx
        else
            log_message "[-] Unable to install certbot. Please install manually." "ERROR"
            return 1
        fi
    fi

    command -v certbot &> /dev/null || return 1
    return 0
}

# Function to stop services that use port 80 for Let's Encrypt validation
stop_services_for_ssl() {
    log_message "Stopping services that may use port 80..."

    # Load services module
    if [ -f "${SCRIPT_DIR}/services.sh" ]; then
        source "${SCRIPT_DIR}/services.sh"
    fi

    # Stop nginx container (it binds port 80/443)
    docker stop sting-ce-frontend-1 2>/dev/null || true
    docker stop sting-ce-nginx-1 2>/dev/null || true

    # Give a moment for ports to be released
    sleep 2

    # Verify port 80 is free
    if command -v lsof &> /dev/null; then
        if lsof -i :80 2>/dev/null | grep -q LISTEN; then
            log_message "[!] Port 80 is still in use. Attempting to identify process..." "WARNING"
            lsof -i :80 2>/dev/null | grep LISTEN || true
        fi
    fi

    return 0
}

# Function to start services after SSL setup
start_services_after_ssl() {
    log_message "Starting services..."

    # Load services module
    if [ -f "${SCRIPT_DIR}/services.sh" ]; then
        source "${SCRIPT_DIR}/services.sh"
    fi

    # Start nginx/frontend
    docker start sting-ce-nginx-1 2>/dev/null || true
    docker start sting-ce-frontend-1 2>/dev/null || true

    return 0
}

# Main function to set up Let's Encrypt SSL
setup_letsencrypt_ssl() {
    local domain="${1:-$DOMAIN}"
    local email="${2:-}"
    local staging="${3:-false}"

    log_message "=========================================="
    log_message "  Let's Encrypt SSL Certificate Setup"
    log_message "=========================================="
    log_message ""

    # Validate domain
    if [ -z "$domain" ]; then
        log_message "[-] Domain not configured. Set DOMAIN in config.yml" "ERROR"
        log_message "TIP: Run './msting config' to configure your domain" "INFO"
        return 1
    fi

    log_message "Domain: $domain"
    log_message "Email: ${email:-not provided (will be prompted)}"

    # Check if we already have valid Let's Encrypt certs
    if check_letsencrypt_certs "$domain"; then
        log_message ""
        log_message "[*] Valid Let's Encrypt certificates already exist" "INFO"
        log_message "    Certificate path: /etc/letsencrypt/live/$domain/"
        log_message ""
        log_message "To renew: msting renew-ssl"
        log_message "To check: msting ssl-status"
        return 0
    fi

    # Check certbot
    log_message ""
    log_message "Checking certbot installation..."
    if ! check_certbot; then
        log_message "[-] certbot installation failed" "ERROR"
        return 1
    fi

    # Stop services that use port 80
    log_message ""
    log_message "Preparing for Let's Encrypt validation..."
    stop_services_for_ssl

    # Build certbot command
    local certbot_cmd="certbot certonly --standalone"
    certbot_cmd="$certbot_cmd --non-interactive"
    certbot_cmd="$certbot_cmd --agree-tos"

    if [ -n "$email" ]; then
        certbot_cmd="$certbot_cmd --email $email"
    else
        certbot_cmd="$certbot_cmd --register-unsafely-without-email"
    fi

    if [ "$staging" = "true" ]; then
        certbot_cmd="$certbot_cmd --staging"
    fi

    certbot_cmd="$certbot_cmd -d $domain"

    # Add www subdomain if domain doesn't start with www
    if [[ "$domain" != www.* ]]; then
        certbot_cmd="$certbot_cmd -d www.$domain"
    fi

    log_message ""
    log_message "Running certbot..."
    log_message "Command: $certbot_cmd"
    log_message ""

    # Run certbot
    if eval "$certbot_cmd"; then
        log_message "[+] SSL certificate obtained successfully!" "SUCCESS"
    else
        log_message "[-] Failed to obtain SSL certificate" "ERROR"
        log_message ""
        log_message "Common issues:"
        log_message "  1. Domain DNS not pointing to this server"
        log_message "  2. Port 80 is blocked by firewall"
        log_message "  3. Another service is using port 80"
        log_message ""
        log_message "Solutions:"
        log_message "  - Ensure DNS A record points to this server's IP"
        log_message "  - Open port 80 (HTTP) in firewall"
        log_message "  - Run: sudo ufw allow 80/tcp"
        start_services_after_ssl
        return 1
    fi

    # Verify certificates were created
    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"
    local key_path="/etc/letsencrypt/live/$domain/privkey.pem"

    if [ -f "$cert_path" ] && [ -f "$key_path" ]; then
        log_message ""
        log_message "[+] Certificate files created:"
        log_message "    Certificate: $cert_path"
        log_message "    Private Key: $key_path"

        # Set proper permissions
        sudo chmod 644 "$cert_path" 2>/dev/null || true
        sudo chmod 600 "$key_path" 2>/dev/null || true

        # Copy to STING certs directory if needed
        local sting_certs_dir="${INSTALL_DIR}/certs/live/$domain"
        if [ -d "$sting_certs_dir" ] || mkdir -p "$sting_certs_dir" 2>/dev/null; then
            sudo cp "$cert_path" "$sting_certs_dir/" 2>/dev/null || true
            sudo cp "$key_path" "$sting_certs_dir/" 2>/dev/null || true
            log_message "    Copies also at: $sting_certs_dir/"
        fi

        # Set up auto-renewal cron
        log_message ""
        log_message "Setting up auto-renewal..."
        setup_ssl_renewal_cron "$domain"

        # Start services
        log_message ""
        log_message "Starting services..."
        start_services_after_ssl

        log_message ""
        log_message "=========================================="
        log_message "  SSL Setup Complete!"
        log_message "=========================================="
        log_message ""
        log_message "Your domain '$domain' now has valid SSL certificates."
        log_message "Certificates will auto-renew before expiration."
        log_message ""
        log_message "Next steps:"
        log_message "  - Restart STING services: msting restart"
        log_message "  - Check status: msting ssl-status"
        log_message "  - Test renewal: certbot renew --dry-run"
    else
        log_message "[-] Certificate files not found after certbot completed" "ERROR"
        start_services_after_ssl
        return 1
    fi

    return 0
}

# Function to set up SSL renewal cron job
setup_ssl_renewal_cron() {
    local domain="${1:-$DOMAIN}"

    # Create renewal script
    local renewal_script="/etc/letsencrypt/renewal-hooks/post/sting-renew.sh"
    sudo mkdir -p "$(dirname "$renewal_script")"

    cat > "$renewal_script" << 'RENEWALEOF'
#!/bin/bash
# STING SSL Renewal Post-Hook
# Copies renewed certificates to STING certs directory

STING_CERTS_DIR="${INSTALL_DIR:-/opt/sting-ce}/certs/live/${DOMAIN:-yourdomain.com}"

if [ -d "/etc/letsencrypt/live/${DOMAIN:-yourdomain.com}" ]; then
    mkdir -p "$STING_CERTS_DIR"
    cp /etc/letsencrypt/live/${DOMAIN:-yourdomain.com}/fullchain.pem "$STING_CERTS_DIR/" 2>/dev/null || true
    cp /etc/letsencrypt/live/${DOMAIN:-yourdomain.com}/privkey.pem "$STING_CERTS_DIR/" 2>/dev/null || true
    echo "[$(date)] SSL certificates renewed and copied to STING directory" >> /var/log/sting-ssl-renewal.log
fi
RENEWALEOF

    sudo chmod +x "$renewal_script"

    # Add to crontab if not already present
    local cron_entry="0 2 * * * /usr/bin/certbot renew --quiet"

    if ! sudo grep -q "certbot renew" /etc/crontab 2>/dev/null; then
        echo "$cron_entry" | sudo tee -a /etc/crontab >/dev/null
        log_message "[+] Auto-renewal cron job added (runs daily at 2 AM)"
    else
        log_message "[+] Auto-renewal already configured"
    fi

    # Also add to user's crontab for systems without root
    (crontab -l 2>/dev/null | grep -v "certbot renew"; echo "0 2 * * * /usr/bin/certbot renew --quiet") | crontab -
    log_message "[+] Added renewal to user crontab as backup"
}

# Function to check SSL certificate status
ssl_status() {
    local domain="${1:-$DOMAIN}"

    if [ -z "$domain" ]; then
        log_message "[-] Domain not configured" "ERROR"
        return 1
    fi

    log_message "=========================================="
    log_message "  SSL Certificate Status for $domain"
    log_message "=========================================="
    echo ""

    local cert_path="/etc/letsencrypt/live/$domain/fullchain.pem"
    local self_signed_cert="${INSTALL_DIR}/certs/server.crt"

    # Check Let's Encrypt certificates
    if [ -f "$cert_path" ]; then
        log_message "Let's Encrypt Certificates:" "INFO"
        echo ""

        # Show certificate details
        openssl x509 -in "$cert_path" -noout -dates 2>/dev/null && echo ""

        # Check days until expiration
        local expiry=$(openssl x509 -enddate -noout -in "$cert_path" 2>/dev/null | cut -d= -f2)
        local expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo "0")
        local now_epoch=$(date +%s)
        local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

        if [ "$days_left" -gt 0 ]; then
            log_message "Days until expiration: $days_left" "INFO"
        else
            log_message "Certificate has expired!" "ERROR"
        fi

        echo ""
        log_message "Certificate source: /etc/letsencrypt/live/$domain/" "INFO"
        echo ""

    # Check self-signed certificate
    elif [ -f "$self_signed_cert" ]; then
        log_message "Self-Signed Certificate (Development):" "WARNING"
        echo ""

        openssl x509 -in "$self_signed_cert" -noout -dates 2>/dev/null && echo ""

        echo ""
        log_message "For production use, run: msting setup-ssl <domain> <email>" "INFO"
        echo ""

    else
        log_message "No SSL certificates found!" "ERROR"
        echo ""
        log_message "To set up Let's Encrypt:"
        log_message "  msting setup-ssl yourdomain.com admin@yourdomain.com" "INFO"
        echo ""
    fi

    return 0
}

# Function to renew Let's Encrypt certificates
renew_letsencrypt_ssl() {
    local domain="${1:-$DOMAIN}"
    local staging="${2:-false}"

    if [ -z "$domain" ]; then
        log_message "[-] Domain not configured" "ERROR"
        return 1
    fi

    log_message "=========================================="
    log_message "  Renewing SSL Certificates for $domain"
    log_message "=========================================="
    echo ""

    # Stop services that use port 80
    stop_services_for_ssl

    # Build certbot command
    local certbot_cmd="certbot renew"

    if [ "$staging" = "true" ]; then
        certbot_cmd="$certbot_cmd --staging"
    fi

    log_message "Running certificate renewal..."
    echo ""

    if eval "$certbot_cmd"; then
        log_message "[+] Certificates renewed successfully!" "SUCCESS"

        # Run post-renewal hooks
        local renewal_hook="/etc/letsencrypt/renewal-hooks/post/sting-renew.sh"
        if [ -f "$renewal_hook" ]; then
            "$renewal_hook"
        fi

        # Start services
        start_services_after_ssl

        log_message ""
        log_message "Services restarted with new certificates."
    else
        log_message "[-] Certificate renewal failed" "ERROR"
        start_services_after_ssl
        return 1
    fi

    return 0
}