#!/bin/bash
# configuration.sh - Configuration management and validation functions

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"

# Validate configuration using utils container (centralized approach)
validate_configuration() {
    log_message "Validating configuration..."
    
    # Load config utils for centralized validation
    if [ -f "${SCRIPT_DIR}/config_utils.sh" ]; then
        source "${SCRIPT_DIR}/config_utils.sh"
        
        # Use utils container for validation instead of separate docker run
        if ensure_utils_container; then
            if exec_in_utils "cd /app/conf && python3 config_loader.py config.yml --validate" 60; then
                log_message "Configuration validation passed" "SUCCESS"
                return 0
            else
                log_message "Configuration validation failed" "ERROR"
                return 1
            fi
        else
            log_message "Failed to ensure utils container for validation" "ERROR"
            return 1
        fi
    else
        log_message "Config utils not available, skipping validation" "WARNING"
        return 0
    fi
}

# Check for required environment variables
validate_critical_vars() {
    log_message "Validating critical environment variables..."
    
    local critical_vars=("INSTALL_DIR" "CONFIG_DIR" "POSTGRESQL_PASSWORD")
    local missing_vars=()

    for var in "${critical_vars[@]}"; do
        # Use :- with indirect expansion to avoid "unbound variable" error in strict mode
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        log_message "ERROR: Missing critical variables: ${missing_vars[*]}" "ERROR"
        return 1
    fi
    
    log_message "All critical variables are set" "SUCCESS"
    return 0
}

# Validate domain and email settings
validate_domain_settings() {
    log_message "Validating domain and email settings..."

    # Check if domain is set and not default
    # Use parameter expansion with default to avoid "unbound variable" error
    if [ -z "${DOMAIN:-}" ] || [ "${DOMAIN:-}" = "localhost" ]; then
        log_message "WARNING: Using localhost domain. This is only suitable for development"
        return 0
    fi

    # Validate email settings if domain is not localhost
    if [ -z "${SMTP_HOST:-}" ] || [ -z "${SMTP_PORT:-}" ] || [ -z "${SMTP_USER:-}" ]; then
        log_message "ERROR: SMTP settings are required when using a custom domain" "ERROR"
        return 1
    fi
    
    # Check email format
    if [[ ! "$EMAIL_FROM" =~ ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$ ]]; then
        log_message "ERROR: Invalid email format: $EMAIL_FROM" "ERROR"
        return 1
    fi
    
    log_message "Domain and email settings are valid" "SUCCESS"
    return 0
}

# Generate initial configuration files
generate_initial_configuration() {
    local mode="${1:-bootstrap}"  # Default to bootstrap mode for fresh installs
    log_message "Generating initial configuration files in $mode mode..."
    
    # Ensure config directory exists
    mkdir -p "${CONFIG_DIR}"

    # Copy configuration if it doesn't exist
    # Priority: 1. Wizard config, 2. Default template
    if [ ! -f "${CONFIG_DIR}/config.yml" ]; then
        # Check for wizard-generated config first
        if [ -f "/tmp/sting-setup-state/config.yml" ]; then
            cp "/tmp/sting-setup-state/config.yml" "${CONFIG_DIR}/config.yml"
            log_message "✅ Using wizard-configured config.yml"
        elif [ -f "${SOURCE_DIR}/conf/config.yml.default" ]; then
            cp "${SOURCE_DIR}/conf/config.yml.default" "${CONFIG_DIR}/config.yml"
            log_message "Created default config.yml"
        else
            log_message "ERROR: No config template found" "ERROR"
            return 1
        fi
    fi
    
    # Generate environment files using utils container (Docker-first approach)
    log_message "Generating environment files from configuration using utils container..."
    
    # Ensure utils container is available
    if [ -f "${CONFIG_DIR}/config_loader.py" ]; then
        # Export INSTALL_DIR for docker-compose to use
        export INSTALL_DIR="${INSTALL_DIR}"
        
        # Create placeholder env files to avoid docker-compose validation errors
        mkdir -p "${INSTALL_DIR}/env"
        for env_file in app db vault frontend kratos chatbot knowledge profile messaging observability headscale external-ai nectar-worker; do
            touch "${INSTALL_DIR}/env/${env_file}.env"
        done

        # Fix permissions immediately so docker build can access them
        # On native Linux, Docker needs to read these files during build validation
        chmod 755 "${INSTALL_DIR}/env"
        chmod 644 "${INSTALL_DIR}/env"/*.env

        # Start utils container if not running and wait for readiness
        # Use --profile installation since utils is in that profile
        if ! docker compose --profile installation ps utils 2>/dev/null | grep -q "Up"; then
            log_message "Starting utils container for config generation..."
            
            # Check if utils image exists, build it if not
            if ! docker images | grep -q "sting-ce-utils"; then
                # In OVA mode, images should be pre-built - don't try to build
                if [ -f "/opt/sting-ce-source/.ova-prebuild" ]; then
                    log_message "OVA mode: Utils image not found but should be pre-built!" "ERROR"
                    log_message "Available images:" "ERROR"
                    docker images --format "{{.Repository}}:{{.Tag}}" | head -20
                    log_message "This may indicate Docker storage issue. Try: sudo systemctl restart docker" "ERROR"
                    return 1
                fi
                log_message "Utils image not found, building it first..."
                if ! docker compose --profile installation build utils; then
                    log_message "Failed to build utils container" "ERROR"
                    return 1
                fi
            fi
            
            if ! docker compose --profile installation up -d utils; then
                log_message "Failed to start utils container for config generation" "ERROR"
                return 1
            fi
        fi
        
        # Wait for container to be ready with very generous timeout
        local max_attempts=90  # 3 minutes total for slow systems/first install
        local attempt=1
        local container_ready=false
        
        log_message "Waiting for utils container to become ready..."
        log_message "This may take up to 3 minutes on first run while dependencies are installed..."
        
        while [ $attempt -le $max_attempts ]; do
            # Check if container is still running - use docker directly as fallback
            local container_running=false
            if docker compose --profile installation ps utils 2>/dev/null | grep -q "Up"; then
                container_running=true
            elif docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "sting-ce-utils.*Up" >/dev/null 2>&1; then
                container_running=true
            fi
            
            if [ "$container_running" != "true" ]; then
                log_message "Utils container stopped unexpectedly, restarting..." "WARNING"
                docker compose --profile installation up -d utils 2>/dev/null || docker start sting-ce-utils 2>/dev/null
                sleep 5
                attempt=$((attempt + 1))
                continue
            fi
            
            # Try simpler check first - just Python availability
            # Try docker compose first, then fall back to direct docker exec
            if docker compose --profile installation exec utils python3 --version >/dev/null 2>&1 || \
               docker exec sting-ce-utils python3 --version >/dev/null 2>&1; then
                # If Python works, try the dependency check
                if docker compose --profile installation exec utils python3 -c "import hvac; import yaml; import requests" >/dev/null 2>&1 || \
                   docker exec sting-ce-utils python3 -c "import hvac; import yaml; import requests" >/dev/null 2>&1; then
                    log_message "Utils container is ready with all dependencies installed" "SUCCESS"
                    container_ready=true
                    break
                fi
            fi
            
            # Progress logging every 15 seconds (every 7-8 attempts)
            if [ $((attempt % 8)) -eq 0 ]; then
                local elapsed=$((attempt * 2))
                local remaining=$((max_attempts - attempt))
                log_message "Still waiting for utils container... (${elapsed}s elapsed, ${remaining} attempts remaining)"
                
                # Show basic status
                if docker compose --profile installation exec utils python3 --version >/dev/null 2>&1 || \
                   docker exec sting-ce-utils python3 --version >/dev/null 2>&1; then
                    log_message "  → Python is ready, installing dependencies..."
                else
                    log_message "  → Container starting up..."
                fi
            fi
            
            sleep 2
            attempt=$((attempt + 1))
        done
        
        if [ "$container_ready" != "true" ]; then
            log_message "Utils container did not become ready in time (waited 3 minutes)" "ERROR"
            log_message "Attempting to provide diagnostic information..." "ERROR"
            
            # Show container status
            log_message "Container status:" "ERROR"
            docker compose --profile installation ps utils 2>/dev/null || echo "Failed to get container status"
            
            # Show recent logs
            log_message "Container logs (last 20 lines):" "ERROR"
            docker logs sting-ce-utils --tail 20 2>/dev/null || echo "Failed to get container logs"
            
            # Test basic connectivity
            log_message "Testing basic container connectivity:" "ERROR"
            if docker compose --profile installation exec utils echo "Container accessible" 2>/dev/null; then
                echo "✓ Container is accessible"
                docker compose --profile installation exec utils python3 --version 2>/dev/null || echo "✗ Python not available"
            else
                echo "✗ Cannot connect to container"
            fi
            
            log_message "You can manually test with: docker compose --profile installation exec utils python3 -c 'import hvac; import yaml; import requests'" "ERROR"
            return 1
        fi
        
        
        # Helper function to execute in utils container with fallback
        exec_in_utils() {
            local cmd="$1"
            if docker compose --profile installation exec utils bash -c "$cmd" 2>/dev/null; then
                return 0
            elif docker exec sting-ce-utils bash -c "$cmd" 2>/dev/null; then
                return 0
            else
                return 1
            fi
        }
        
        # Ensure env directory exists in container for config generation
        exec_in_utils "mkdir -p /app/env"
        
        # Run config generation in utils container using bash for reliable path handling
        log_message "Running config generation with mode: $mode"
        if exec_in_utils "cd /app/conf && INSTALL_DIR=/app python3 config_loader.py config.yml --mode $mode"; then
            log_message "Environment files generated successfully using utils container" "SUCCESS"
            
            # Check if SOURCE_DIR is set (needed for copy operation)
            if [ -z "${SOURCE_DIR:-}" ]; then
                log_message "SOURCE_DIR not set - attempting auto-detection" "WARNING"
                # Try to find the env directory
                if [ -d "${STING_ROOT_DIR:-$(pwd)}/env" ]; then
                    export SOURCE_DIR="${STING_ROOT_DIR:-$(pwd)}"
                    log_message "Auto-detected SOURCE_DIR: ${SOURCE_DIR}" "SUCCESS"
                else
                    log_message "Cannot locate environment files" "ERROR"
                    return 1
                fi
            fi
            
            # Determine if copy is needed based on directory structure
            # Normalize paths for comparison (resolve symlinks, remove trailing slashes)
            local normalized_source
            local normalized_install
            normalized_source="$(cd "${SOURCE_DIR}" 2>/dev/null && pwd)" || normalized_source="${SOURCE_DIR}"
            normalized_install="$(cd "${INSTALL_DIR}" 2>/dev/null && pwd)" || normalized_install="${INSTALL_DIR}"
            
            # Check if we're running from the project directory (development/codespace mode)
            if [ "${normalized_source}" = "${normalized_install}" ]; then
                log_message "Development mode detected: SOURCE_DIR and INSTALL_DIR are the same" "INFO"
                log_message "Environment files already in correct location at ${INSTALL_DIR}/env" "SUCCESS"
                local env_files_created
                env_files_created=$(find "${INSTALL_DIR}/env" -name "*.env" -type f 2>/dev/null | wc -l)
                log_message "Verified $env_files_created environment files in place"
            elif [ -d "${SOURCE_DIR}/env" ]; then
                # Production mode: copy from project directory to install directory
                log_message "Production mode: Copying env files from ${SOURCE_DIR}/env to ${INSTALL_DIR}/env..."
                
                # Ensure target directory exists (use sudo if needed on Linux)
                if [ ! -d "${INSTALL_DIR}/env" ]; then
                    if mkdir -p "${INSTALL_DIR}/env" 2>/dev/null; then
                        log_message "Created ${INSTALL_DIR}/env directory" "SUCCESS"
                    elif sudo -n mkdir -p "${INSTALL_DIR}/env" 2>/dev/null; then
                        sudo -n chown -R "$USER:$(id -gn)" "${INSTALL_DIR}/env" 2>/dev/null
                        log_message "Created ${INSTALL_DIR}/env directory with sudo" "SUCCESS"
                    else
                        log_message "Failed to create ${INSTALL_DIR}/env directory" "ERROR"
                        return 1
                    fi
                fi
                
                if cp "${SOURCE_DIR}/env/"*.env "${INSTALL_DIR}/env/" 2>/dev/null; then
                    log_message "Environment files copied successfully" "SUCCESS"
                    
                    # Verify env files were created  
                    local env_files_created
                    env_files_created=$(find "${INSTALL_DIR}/env" -name "*.env" -type f 2>/dev/null | wc -l)
                    log_message "Created $env_files_created environment files in install directory"
                else
                    log_message "Failed to copy environment files to install directory" "ERROR"
                    log_message "Source: ${SOURCE_DIR}/env/" "INFO"
                    log_message "Target: ${INSTALL_DIR}/env/" "INFO"
                    log_message "Checking if files exist in source directory..." "WARNING"
                    if ls -la "${SOURCE_DIR}/env/"*.env 2>/dev/null; then
                        log_message "Files exist in source but copy failed - check permissions" "ERROR"
                    else
                        log_message "No .env files found in ${SOURCE_DIR}/env/" "ERROR"
                    fi
                    return 1
                fi
            else
                log_message "Project env directory ${SOURCE_DIR}/env does not exist" "ERROR"
                return 1
            fi
        else
            log_message "Failed to generate environment files using utils container" "ERROR"
            log_message "Checking container file system for debugging..." "WARNING"
            
            # Debug: Check what files are available
            exec_in_utils "echo 'Contents of /app/conf:'; ls -la /app/conf/ | head -10"
            exec_in_utils "echo 'Contents of /app/env:'; ls -la /app/env/ 2>/dev/null || echo 'env directory does not exist'"
            exec_in_utils "echo 'Environment variables:'; env | grep -E 'INSTALL_DIR|CONFIG_DIR'"
            exec_in_utils "echo 'Python version:'; python3 --version"
            
            log_message "Config generation failed. Check the debug output above." "ERROR"
            return 1
        fi
    else
        log_message "Config loader not found, creating basic environment files"
        generate_default_env
    fi
    
    
    # Set proper permissions
    find "${CONFIG_DIR}" -type f -exec chmod 644 {} \;
    find "${INSTALL_DIR}/env" -type f -exec chmod 600 {} \; 2>/dev/null || true
    
    log_message "Initial configuration generation completed"
    return 0
}

# Generate Kratos configuration
generate_kratos_config() {
    log_message "Generating Kratos configuration dynamically..."
    local kratos_conf_dir="${CONFIG_DIR}/kratos"
    local output_file="$kratos_conf_dir/kratos.yml"
    mkdir -p "$kratos_conf_dir"
    
    # Platform-specific SMTP configuration
    local smtp_uri
    if [[ "$(uname)" == "Darwin" ]]; then
        # Mac: Use specific configuration that works with Docker Desktop
        smtp_uri="smtp://mailpit:1025/?skip_ssl_verify=true&disable_starttls=true"
        log_message "Detected macOS - using Mac-specific SMTP configuration"
    else
        # Linux/WSL2: Standard container-to-container communication
        smtp_uri="smtp://mailpit:1025"
        log_message "Detected Linux/WSL2 - using standard SMTP configuration"
    fi
    
    # Override with environment variable if set
    smtp_uri="${SMTP_CONNECTION_URI:-$smtp_uri}"
    
    # Extract AAL2 session timeout from config.yml
    local aal2_timeout="4h"  # Default
    if command -v python3 >/dev/null 2>&1 && [ -f "${CONFIG_DIR}/config.yml" ]; then
        aal2_timeout=$(python3 -c "
import yaml
try:
    with open('${CONFIG_DIR}/config.yml', 'r') as f:
        config = yaml.safe_load(f)
    timeout = config.get('security', {}).get('authentication', {}).get('aal2_session_timeout', '4h')
    print(timeout)
except:
    print('4h')
" 2>/dev/null || echo "4h")
    fi
    
    # Allow environment variable override
    aal2_timeout="${AAL2_SESSION_TIMEOUT:-$aal2_timeout}"
    log_message "Using AAL2 session timeout: $aal2_timeout"
    
    # Build allowed origins list based on domain configuration
    local allowed_origins=""
    if [ -n "${STING_DOMAIN}" ] && [ "${STING_DOMAIN}" != "localhost" ]; then
        allowed_origins="        - ${STING_PROTOCOL:-https}://${STING_DOMAIN}:${FRONTEND_PORT:-8443}
        - ${STING_PROTOCOL:-https}://${STING_DOMAIN}:${KRATOS_PORT:-4433}"
    fi
    
    cat > "$output_file" << EOF
version: v1.3.1

dsn: ${DSN}

log:
  level: debug

serve:
  public:
    base_url: ${KRATOS_PUBLIC_URL}
    tls:
      cert:
        path: /etc/certs/server.crt
      key:
        path: /etc/certs/server.key
    cors:
      enabled: true
      allowed_origins:
        - https://localhost:8443
        - http://localhost:8443
        - https://127.0.0.1:8443
        - http://127.0.0.1:8443
        - https://localhost:4433
        - http://localhost:4433
${allowed_origins}
      allowed_methods:
        - GET
        - POST
        - PUT
        - PATCH
        - DELETE
        - OPTIONS
      allowed_headers:
        - Authorization
        - Content-Type
        - X-Session-Token
        - Cookie
        - "*"
      exposed_headers:
        - Content-Type
        - Set-Cookie
      allow_credentials: true
  admin:
    base_url: ${KRATOS_ADMIN_URL}
    tls:
      cert:
        path: /etc/certs/server.crt
      key:
        path: /etc/certs/server.key

identity:
  default_schema_id: default
  schemas:
    - id: default
      url: ${IDENTITY_DEFAULT_SCHEMA_URL}

selfservice:
  default_browser_return_url: ${FRONTEND_URL}
  flows:
    settings:
      ui_url: ${FRONTEND_URL}/settings
      privileged_session_max_age: ${aal2_timeout}
      required_aal: aal2
    login:
      ui_url: ${FRONTEND_URL}/login
      lifespan: ${LOGIN_LIFESPAN:-1h}
      after:
        default_browser_return_url: ${FRONTEND_URL}/dashboard
    registration:
      ui_url: ${FRONTEND_URL}/register
      lifespan: ${REGISTRATION_LIFESPAN:-1h}
      after:
        password:
          hooks:
            - hook: session
            - hook: show_verification_ui
        default_browser_return_url: ${FRONTEND_URL}/dashboard
    verification:
      enabled: true
      ui_url: ${FRONTEND_URL}/verification
      lifespan: ${VERIFICATION_LIFESPAN:-1h}
      after:
        default_browser_return_url: ${FRONTEND_URL}/dashboard
    recovery:
      enabled: true
      ui_url: ${FRONTEND_URL}/recovery
      lifespan: ${RECOVERY_LIFESPAN:-1h}
  methods:
    password:
      enabled: ${PASSWORD_ENABLED:-true}
      config:
        haveibeenpwned_enabled: false
        identifier_similarity_check_enabled: false
    webauthn:
      enabled: ${WEBAUTHN_ENABLED:-true}
      config:
        passwordless: true
        rp:
          id: ${WEBAUTHN_RP_ID:-localhost}
          display_name: ${WEBAUTHN_RP_DISPLAY_NAME:-STING Authentication}
          origin: ${WEBAUTHN_RP_ORIGIN:-${FRONTEND_URL}}
    link:
      enabled: true
      config:
        lifespan: 1h
    code:
      enabled: true
      config:
        lifespan: 15m

secrets:
  cookie:
    - ${SESSION_SECRET:-$(openssl rand -hex 16)}
  cipher:
    - $(openssl rand -hex 16)

session:
  cookie:
    name: ory_kratos_session
    domain: ${WEBAUTHN_RP_ID:-localhost}
    path: /
    same_site: Lax

  lifespan: 24h
  earliest_possible_extend: 1h

hashers:
  algorithm: bcrypt
  bcrypt:
    cost: 12

courier:
  smtp:
    connection_uri: ${smtp_uri}
    from_address: noreply@sting.local
    from_name: "STING Platform"
  template_override_path: /etc/config/kratos/courier-templates/
EOF
    chmod 600 "$output_file"
    log_message "Generated Kratos config at $output_file"
    
    # No longer copying to main.kratos.yml - docker-compose uses generated config directly
    
    return 0
}

# Get environment file path for a service
get_env_file_path() {
    local service="$1"
    local install_dir="$2"
    
    case "$service" in
        "db") echo "${install_dir}/env/db.env" ;;
        "app") echo "${install_dir}/env/app.env" ;;
        "frontend") echo "${install_dir}/env/frontend.env" ;;
        "kratos") echo "${install_dir}/env/kratos.env" ;;
        "vault") echo "${install_dir}/env/vault.env" ;;
        *) echo "" ;;
    esac
}

# Create default environment file
generate_default_env() {
    log_message "Generating default environment configuration..."
    
    # Ensure env directory exists
    mkdir -p "${INSTALL_DIR}/env"
    
    # Generate basic .env file
    cat > "${INSTALL_DIR}/.env" << EOF
# STING Environment Configuration
INSTALL_DIR=${INSTALL_DIR}
CONFIG_DIR=${CONFIG_DIR}
POSTGRESQL_PASSWORD=${POSTGRESQL_PASSWORD:-$(openssl rand -hex 16)}
VAULT_TOKEN=${VAULT_TOKEN:-root}
NODE_ENV=${NODE_ENV:-production}
EOF
    
    chmod 600 "${INSTALL_DIR}/.env"
    log_message "Default environment file created"
    return 0
}

# Prompt for HuggingFace token
ask_for_hf_token() {
    # Check if HF_TOKEN is already set
    if [ -n "$HF_TOKEN" ]; then
        log_message "HuggingFace token already configured, skipping prompt"
        return 0
    fi
    
    # Check if token exists in saved locations
    local saved_token=""
    if [ -f "${CONFIG_DIR}/secrets/hf_token.txt" ]; then
        saved_token=$(cat "${CONFIG_DIR}/secrets/hf_token.txt" 2>/dev/null | tr -d '\n\r ')
        if [ -n "$saved_token" ]; then
            log_message "Found existing HuggingFace token, loading from saved location"
            export HF_TOKEN="$saved_token"
            return 0
        fi
    fi
    
    local token=""
    local confirm_token=""
    
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🤗 HuggingFace Token Configuration"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "NOTE: HuggingFace token is ONLY needed for legacy model support."
    echo "The modern Ollama/External AI stack does NOT require a HuggingFace token."
    echo ""
    echo "Press Enter to skip this step (recommended), or provide a token if you"
    echo "need legacy model support (phi3, llama3, zephyr)."
    echo ""
    
    while true; do
        echo -n "Enter your HuggingFace token (or press Enter to skip): "
        read -r token
        
        # Allow skipping
        if [ -z "$token" ]; then
            echo "✓ Skipping HuggingFace token configuration"
            return 0
        fi
        
        if [[ ! "$token" =~ ^hf_ ]]; then
            echo "❌ Invalid token format. HuggingFace tokens start with 'hf_'"
            echo "   Please check your token and try again."
            continue
        fi
        
        if [ ${#token} -lt 10 ]; then
            echo "❌ Token appears too short. Please check and try again."
            continue
        fi
        
        # Confirm token
        echo -n "Confirm your token: "
        read -r confirm_token
        
        if [ "$token" = "$confirm_token" ]; then
            break
        else
            echo "❌ Tokens don't match. Please try again."
            echo ""
        fi
    done
    
    # Save the token
    if save_hf_token "$token"; then
        echo ""
        echo "✅ HuggingFace token configured successfully!"
        echo ""
        return 0
    else
        echo ""
        echo "❌ Failed to save HuggingFace token. Please try again."
        echo ""
        return 1
    fi
}

# Save HuggingFace token to multiple locations
save_hf_token() {
    local token="$1"
    
    if [ -z "$token" ]; then
        log_message "ERROR: No token provided to save_hf_token" "ERROR"
        return 1
    fi
    
    log_message "Saving HuggingFace token to configuration..."
    
    # Save to secrets directory
    mkdir -p "${CONFIG_DIR}/secrets"
    echo "$token" > "${CONFIG_DIR}/secrets/hf_token.txt"
    chmod 600 "${CONFIG_DIR}/secrets/hf_token.txt"
    
    # Export for current session
    export HF_TOKEN="$token"
    
    # Update environment files
    local env_files=(
        "${INSTALL_DIR}/env/llm.env"
        "${INSTALL_DIR}/env/llm_gateway.env"
        "${INSTALL_DIR}/env/llama3.env"
        "${INSTALL_DIR}/env/phi3.env"
        "${INSTALL_DIR}/env/zephyr.env"
    )
    
    for env_file in "${env_files[@]}"; do
        if [ -f "$env_file" ]; then
            # Remove existing HF_TOKEN line and add new one
            grep -v "^HF_TOKEN=" "$env_file" > "${env_file}.tmp" 2>/dev/null || touch "${env_file}.tmp"
            echo "HF_TOKEN=$token" >> "${env_file}.tmp"
            mv "${env_file}.tmp" "$env_file"
            chmod 600 "$env_file"
            log_message "Updated HF_TOKEN in $(basename "$env_file")"
        fi
    done
    
    # Update main .env file
    if [ -f "${INSTALL_DIR}/.env" ]; then
        grep -v "^HF_TOKEN=" "${INSTALL_DIR}/.env" > "${INSTALL_DIR}/.env.tmp" 2>/dev/null || touch "${INSTALL_DIR}/.env.tmp"
        echo "HF_TOKEN=$token" >> "${INSTALL_DIR}/.env.tmp"
        mv "${INSTALL_DIR}/.env.tmp" "${INSTALL_DIR}/.env"
        chmod 600 "${INSTALL_DIR}/.env"
    fi
    
    log_message "HuggingFace token saved successfully" "SUCCESS"
    return 0
}

# Validate that all critical environment files exist
validate_env_files() {
    log_message "Validating environment files for all services..."
    
    local missing_files=()
    local env_dir="${INSTALL_DIR}/env"
    local config_loader="${SOURCE_DIR}/conf/config_loader.py"
    
    # Extract all env files defined in config_loader.py service_configs
    # This is the authoritative source of what env files should exist
    
    local required_env_files
    required_env_files=$(grep -E "'\w+\.env':" "$config_loader" 2>/dev/null | \
                              sed "s/.*'\\(.*\\.env\\)'.*/\\1/" | \
                              sort -u)
    
    # If we couldn't extract from config_loader, fall back to a known list
    if [ -z "$required_env_files" ]; then
        log_message "Warning: Could not extract env files from config_loader.py, using fallback list" "WARNING"
        required_env_files="app.env db.env vault.env frontend.env kratos.env chatbot.env knowledge.env profile.env messaging.env observability.env headscale.env"
    fi
    
    # Check each required env file
    for env_file in $required_env_files; do
        if [ ! -f "${env_dir}/${env_file}" ]; then
            missing_files+=("$env_file")
        fi
    done
    
    # Also check for any additional env files referenced in docker-compose.yml
    # but not in config_loader (in case of manual additions)
    local compose_env_files
    compose_env_files=$(grep -A1 "env_file:" "${SOURCE_DIR}/docker-compose.yml" 2>/dev/null | \
                             grep -v "env_file:" | \
                             grep -v "^--$" | \
                             sed 's/.*\///' | \
                             sed 's/^[[:space:]]*-[[:space:]]*//' | \
                             sort -u)
    
    for env_file in $compose_env_files; do
        if [ -n "$env_file" ] && [ ! -f "${env_dir}/${env_file}" ] && [[ ! " ${missing_files[*]} " =~  ${env_file}  ]]; then
            missing_files+=("$env_file")
        fi
    done
    
    # Report results
    if [ ${#missing_files[@]} -eq 0 ]; then
        log_message "✅ All required environment files are present" "SUCCESS"
        
        # List found env files for confirmation
        log_message "Found environment files:" "INFO"
        for env_file in $required_env_files; do
            if [ -f "${env_dir}/${env_file}" ]; then
                log_message "   ✓ $env_file" "SUCCESS"
            fi
        done
        return 0
    else
        log_message "❌ Missing required environment files:" "ERROR"
        for file in "${missing_files[@]}"; do
            log_message "   - $file" "ERROR"
        done
        log_message "" "ERROR"
        log_message "These files are required for services to start properly." "ERROR"
        log_message "Run: ./manage_sting.sh sync-config to regenerate them via utils container" "ERROR"
        return 1
    fi
}



