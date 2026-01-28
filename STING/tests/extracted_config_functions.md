# Configuration Functions Extracted from manage_sting.sh

## Function Locations and Complete Code

### 1. validate_configuration() (Lines 791-814)

```bash
validate_configuration() {
    local mode="${mode:-runtime}"
    log_message "Validating configuration..."

    # Build config container first
    docker build -t sting-config -f Dockerfile.config .

    # Use config container for validation
    local config_container="sting-config"
    if docker run --rm \
        -v config_data:/app/conf \
        --network sting_local \
        -e INIT_MODE="${mode}" \
        -e VALIDATE_ONLY=true \
        $config_container; then
        
        log_message "Configuration validation complete."
        validation_complete=true
        return 0
    fi

    log_message "ERROR: Configuration validation failed"
    return 1
}
```

### 2. validate_critical_vars() (Lines 817-839)

```bash
validate_critical_vars() {
    local required_vars=(
        "APP_ENV"
        "DATABASE_URL"
        "POSTGRESQL_USER"
        "POSTGRESQL_PASSWORD"
        "ST_API_KEY"
    )

    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -ne 0 ]; then
        log_message "Error: Missing required environment variables: ${missing_vars[*]}"
        return 1
    fi

    return 0
}
```

### 3. validate_domain_settings() (Lines 3214-3236)

```bash
validate_domain_settings() {
    # Set development defaults if not in production
    if [ "${APP_ENV:-development}" = "development" ]; then
        export DOMAIN_NAME="${DOMAIN_NAME:-localhost}"
        export CERTBOT_EMAIL="${CERTBOT_EMAIL:-dev@localhost}"
        return 0
    fi

    # Production validation
    if [ -z "${DOMAIN_NAME}" ] || [ "${DOMAIN_NAME}" = "localhost" ]; then
        log_message "Setting up with default development domain configuration"
        export DOMAIN_NAME="localhost"
        export CERTBOT_EMAIL="dev@localhost"
    fi

    # Update configuration
    if [ -f "${CONFIG_DIR}/.env" ]; then
        sed -i.bak "/^DOMAIN_NAME=/d" "${CONFIG_DIR}/.env"
        sed -i.bak "/^CERTBOT_EMAIL=/d" "${CONFIG_DIR}/.env"
        echo "DOMAIN_NAME=${DOMAIN_NAME}" >> "${CONFIG_DIR}/.env"
        echo "CERTBOT_EMAIL=${CERTBOT_EMAIL}" >> "${CONFIG_DIR}/.env"
    fi
}
```

### 4. generate_initial_configuration() (Lines 1381-1465)

```bash
generate_initial_configuration() {
    log_message "Generating initial configuration..."

    # Build configuration container
    docker build -t sting-config -f "${INSTALL_DIR}/Dockerfile.config" "${INSTALL_DIR}" \
        --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
        --build-arg VERSION="${SCRIPT_VERSION}"

    # Run the container to generate initial configuration
    # Pass HF_TOKEN into the config loader so it takes precedence over any stale token in config.yml
    # Ensure no services are running that might output logs
    log_message "Preparing configuration environment..."
    docker compose stop llm-gateway >/dev/null 2>&1 || true
    
    # Mount config_data to env directory so generated .env files persist
    log_message "Generating configuration files..."
    docker run --rm \
        -v config_data:/app/env \
        --network sting_local \
        -e INIT_MODE="initialize" \
        sting-config python3 /app/conf/config_loader.py /app/conf/config.yml --mode initialize 2>&1 | \
        grep -v "Starting LLM service" | \
        grep -v "Model.*not found" | \
        grep -v "Starting server on port" | \
        grep -v "DeprecationWarning" | \
        grep -v "Uvicorn running" | \
        grep -v "INFO:.*" || true

    # Extract generated env files to local installation
    # Use alpine:3.19 to ensure we get a clean alpine image without any contamination
    docker run --rm -v config_data:/app/env alpine:3.19 /bin/sh -c "ls -la /app/env" 2>/dev/null || true
    
    # CRITICAL: Ensure no LLM services are outputting logs
    # This is a safety measure to prevent installation from hanging
    {
        docker stop sting-ce-llm-gateway 2>/dev/null || true
        docker stop sting-llm-gateway 2>/dev/null || true
        docker rm sting-ce-llm-gateway 2>/dev/null || true
        docker rm sting-llm-gateway 2>/dev/null || true
        pkill -f "python.*server.py" 2>/dev/null || true
        pkill -f "uvicorn" 2>/dev/null || true
    } &
    
    # Wait briefly to ensure any processes are stopped
    sleep 2
    
    # Create directory for legacy env files
    mkdir -p "${INSTALL_DIR}/env"
    
    # Extract each core environment file
    local env_files=("db" "app" "frontend" "vault" "kratos")
    for env_file in "${env_files[@]}"; do
        log_message "Extracting ${env_file}.env file..."
        
        # Extract the file and process it to handle quoted values
        docker run --rm -v config_data:/app/env alpine:3.19 /bin/sh -c "cat /app/env/${env_file}.env" | \
        awk -F= '{
            # Extract key and value parts
            key=$1;
            val=substr($0, length($1)+2);
            # Remove surrounding quotes if present
            if (val ~ /^".*"$/) {
                val=substr(val, 2, length(val)-2);
            }
            # Print in key=value format
            print key"="val
        }' > "${INSTALL_DIR}/env/${env_file}.env"
        
        # Check if the file has content
        if [ -s "${INSTALL_DIR}/env/${env_file}.env" ]; then
            log_message "${env_file}.env file extracted successfully with content"
        else
            log_message "WARNING: ${env_file}.env file is empty after extraction"
        fi
        
        chmod 600 "${INSTALL_DIR}/env/${env_file}.env"
    done

    
    # Generate LLM environment files
    generate_llm_env
    
    log_message "Initial configuration generated successfully"
    return 0
}
```

### 5. generate_default_env() (Lines 3195-3212)

```bash
generate_default_env() {
    local env_file="${INSTALL_DIR}/conf/.env"
    
    # Create default environment variables
    cat > "$env_file" << EOF
POSTGRESQL_USER=postgres
POSTGRESQL_PASSWORD=default_password
POSTGRESQL_DATABASE_NAME=sting_app
APP_ENV=development
FLASK_DEBUG=1
VAULT_TOKEN=dev-only-token
ST_API_KEY=default-key
ST_DASHBOARD_API_KEY=default-key
EOF

    chmod 600 "$env_file"
    log_message "Generated default .env file at ${env_file}"
}
```

### 6. generate_kratos_config() (Lines 2949-2981)

```bash
generate_kratos_config() {
    log_message "Generating Kratos configuration dynamically..."
    local kratos_conf_dir="${CONFIG_DIR}/kratos"
    local output_file="$kratos_conf_dir/kratos.yml"
    mkdir -p "$kratos_conf_dir"
    cat > "$output_file" << EOF
dsn: ${DSN}

serve:
  public:
    base_url: ${KRATOS_PUBLIC_URL}
  admin:
    base_url: ${KRATOS_ADMIN_URL}

identity:
  schemas:
    - id: default
      url: ${IDENTITY_DEFAULT_SCHEMA_URL}

selfservice:
  default_browser_return_url: ${FRONTEND_URL}
  flows:
    login:
      ui_url: ${FRONTEND_URL}/login
      enabled: true
    registration:
      ui_url: ${FRONTEND_URL}/register
      enabled: true
EOF
    chmod 600 "$output_file"
    log_message "Generated Kratos config at $output_file"
    return 0
}
```

### 7. ask_for_hf_token() (Lines 1264-1333)

```bash
ask_for_hf_token() {
    # Check sources in order of precedence:
    # 1. Environment variable (already set)
    # 2. Project root .env file
    # 3. Config file
    # 4. User prompt

    # If HF_TOKEN is already set in the environment, use it and skip prompting
    if [ -n "${HF_TOKEN:-}" ]; then
        log_message "HF_TOKEN already set in environment, skipping prompt"
        return
    fi
    
    # Check project root .env file
    local project_env_file="${SOURCE_DIR}/.env"
    if [ -f "$project_env_file" ]; then
        log_message "Checking for Hugging Face token in .env file: $project_env_file"
        # Handle different formats of HF_TOKEN (with or without quotes)
        local env_token
        env_token=$(grep -E '^[[:space:]]*HF_TOKEN=' "$project_env_file" | cut -d'=' -f2- | tr -d "'\""| tr -d ' ')
        if [ -n "$env_token" ]; then
            export HF_TOKEN="$env_token"
            log_message "Using Hugging Face token from .env file"
            # Also save to our centralized location
            save_hf_token "$env_token"
            return
        fi
    fi
    
    # Check config.yml
    local config_file="${INSTALL_DIR}/conf/config.yml"
    log_message "Checking for Hugging Face token in configuration file: $config_file"
    # Extract token from config if present
    local existing_token=""
    if [ -f "$config_file" ]; then
        existing_token=$(grep -A1 "huggingface:" "$config_file" | grep "token:" | cut -d':' -f2 | tr -d ' "')
    fi
    # If config.yml has a valid token, use it
    if [ -n "$existing_token" ] && [ "$existing_token" != "<REDACTED>" ]; then
        export HF_TOKEN="$existing_token"
        log_message "Using Hugging Face token from configuration file"
        # Also save to our centralized location
        save_hf_token "$existing_token"
        return
    fi
    
    # No valid token found, prompt the user
    echo ""
    echo "======== Hugging Face Token Configuration ========"
    echo "Some LLM models (like Llama 3) require a Hugging Face token."
    echo "This improves download speeds and allows access to gated models."
    echo ""
    echo "To get a token:"
    echo "1. Sign up for a free account at https://huggingface.co"
    echo "2. Go to https://huggingface.co/settings/tokens"
    echo "3. Create a new token with 'read' scope"
    echo ""
    read -p "Do you want to configure your Hugging Face token now? (y/N): " configure_token
    if [[ "$configure_token" =~ ^[Yy]$ ]]; then
        read -p "Enter your Hugging Face token: " hf_token
        if [ -n "$hf_token" ]; then
            export HF_TOKEN="$hf_token"
            log_message "Hugging Face token set for this session"
            # Save the token to all necessary locations
            save_hf_token "$hf_token"
        fi
    else
        log_message "No Hugging Face token provided. Some models may not be available."
    fi
}
```

### 8. save_hf_token() (Lines 1336-1378)

```bash
save_hf_token() {
    local token="$1"
    
    # 1. Save to project root .env file
    local env_file="${SOURCE_DIR}/.env"
    if [ -f "$env_file" ]; then
        # Update existing token
        if grep -q "^HF_TOKEN=" "$env_file"; then
            sed -i.bak "s/^HF_TOKEN=.*$/HF_TOKEN=${token}/" "$env_file"
            # Remove backup file if on macOS
            [ -f "${env_file}.bak" ] && rm -f "${env_file}.bak"
        else
            # Append token to existing file
            echo "HF_TOKEN=${token}" >> "$env_file"
        fi
    else
        # Create new .env file with token
        echo "HF_TOKEN=${token}" > "$env_file"
    fi
    chmod 600 "$env_file"
    
    # 2. Save to install env directory for Docker containers
    mkdir -p "${INSTALL_DIR}/env"
    echo "HF_TOKEN=${token}" > "${INSTALL_DIR}/env/hf_token.env"
    chmod 600 "${INSTALL_DIR}/env/hf_token.env"
    
    # 3. Save to home .sting-ce env directory to ensure it's always found
    mkdir -p "${HOME}/.sting-ce/env"
    echo "HF_TOKEN=${token}" > "${HOME}/.sting-ce/env/hf_token.env"
    chmod 600 "${HOME}/.sting-ce/env/hf_token.env"
    
    # 4. Persist for config_loader in env
    mkdir -p "${INSTALL_DIR}/env"
    echo "HF_TOKEN=${token}" > "${INSTALL_DIR}/env/.hf_token"
    chmod 600 "${INSTALL_DIR}/env/.hf_token"
    
    # 5. Save to conf directory for good measure
    mkdir -p "${INSTALL_DIR}/conf/env"
    echo "HF_TOKEN=${token}" > "${INSTALL_DIR}/conf/env/hf_token.env"
    chmod 600 "${INSTALL_DIR}/conf/env/hf_token.env"
    
    log_message "Hugging Face token saved to all configuration locations"
}
```

### 9. get_env_file_path() (Lines 2707-2720)

```bash
get_env_file_path() {
    local service="$1"
    local install_dir="$2"
    
    case "$service" in
        "db") echo "${install_dir}/env/db.env" ;;
        # "supertokens") echo "${install_dir}/env/supertokens.env" ;;
        "app") echo "${install_dir}/env/app.env" ;;
        "frontend") echo "${install_dir}/env/frontend.env" ;;
        "kratos") echo "${install_dir}/env/kratos.env" ;;
        "vault") echo "${install_dir}/env/vault.env" ;;
        *) echo "" ;;
    esac
}
```

## Function Dependencies

### Dependencies Used by These Functions:
- `log_message()` - Used by all functions for logging
- `generate_llm_env()` - Called by `generate_initial_configuration()`
- Global variables used:
  - `INSTALL_DIR`
  - `SOURCE_DIR` 
  - `CONFIG_DIR`
  - `SCRIPT_VERSION`
  - Various environment variables (APP_ENV, DATABASE_URL, etc.)

### Functions Not Found:
None of the requested functions were missing. All 9 functions were found and extracted successfully.

## Summary

All requested configuration-related functions have been successfully located and extracted from `manage_sting.sh`. The functions handle:

1. **Configuration Validation**: `validate_configuration()`, `validate_critical_vars()`, `validate_domain_settings()`
2. **Configuration Generation**: `generate_initial_configuration()`, `generate_default_env()`, `generate_kratos_config()`
3. **HuggingFace Token Management**: `ask_for_hf_token()`, `save_hf_token()`
4. **Utility Functions**: `get_env_file_path()`

These functions work together to manage the STING platform's complex configuration system, including Docker container-based config generation, environment file management, and secure token handling.