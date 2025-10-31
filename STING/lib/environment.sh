#!/bin/bash
# environment.sh - Environment setup and management functions

# Source dependencies
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/core.sh"
source "${SCRIPT_DIR}/logging.sh"

# Note: setup_python_venv() function removed - using containerized approach
# All Python operations now use the utils container instead of host Python

# Source service environment files
source_service_envs() {
    # Load each KEY=VALUE pair from service-specific env files, stripping quotes
    if [ -d "${INSTALL_DIR}/env" ]; then
        for ev in "${INSTALL_DIR}/env"/*.env; do
            [ -f "$ev" ] || continue
            # Read lines like KEY=VALUE
            while IFS='=' read -r key value; do
                # Skip empty or comment lines
                [[ "$key" =~ ^[[:space:]]*# ]] && continue
                [[ -z "$key" ]] && continue
                # Trim whitespace from key
                key="${key// /}"
                # Strip surrounding double or single quotes from value
                value="${value#\"}"; value="${value%\"}"
                value="${value#\'}"; value="${value%\'}"
                # Export the variable
                export "${key}=${value}"
            done < <(grep -E '^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*=' "$ev" 2>/dev/null || true)
        done
    fi
}

# Load a single environment file
load_env_file() {
    if [ -f "$INSTALL_DIR/conf/.env" ]; then
        log_message "Loading .env file"
        # Use grep to extract variables and export them safely
        while IFS='=' read -r key value; do
            # Skip empty lines and comments
            if [[ -z "$key" || "$key" =~ ^# ]]; then
                continue
            fi
            # Remove quotes and handle special characters
            value=$(echo "$value" | sed -e 's/^["\x27]//' -e 's/["\x27]$//')
            # Export the variable
            export "$key"="$value"
        done < <(grep -v '^#' "$INSTALL_DIR/conf/.env")
        log_message ".env file loaded successfully"
    else
        log_message "WARNING: .env file not found in $INSTALL_DIR"
    fi
}

# Load multiple environment files
load_env_files() {
    log_message "Loading environment variables from configuration files..."
    
    # Load each environment file
    local env_files=("db" "app" "frontend" "vault" "kratos")
    for env_file in "${env_files[@]}"; do
        local file_path="${INSTALL_DIR}/env/${env_file}.env"
        
        if [ -f "$file_path" ]; then
            log_message "Loading $env_file environment from $file_path"
            
            # Use this safer approach to load variables instead of 'source'
            while IFS='=' read -r key value || [[ -n "$key" ]]; do
                # Skip comments and empty lines
                [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
                
                # Remove surrounding quotes if present
                value=$(echo "$value" | sed -e 's/^["\x27]//' -e 's/["\x27]$//')
                
                # Export the variable
                export "$key=$value"
                
            done < <(grep -v '^#' "$file_path")
        else
            log_message "WARNING: Environment file not found: $file_path"
        fi
    done
    # If not on macOS, allow project config override for models_dir
    if [[ "$(uname)" != "Darwin" ]] && [ -z "${STING_MODELS_DIR:-}" ] && [ -f "${CONFIG_DIR}/config.yml" ]; then
        STING_MODELS_DIR=$(grep -E '^[[:space:]]*models_dir:' "${CONFIG_DIR}/config.yml" | head -n1 | cut -d: -f2- | tr -d ' "')
        export STING_MODELS_DIR
        log_message "Detected STING_MODELS_DIR override from config: ${STING_MODELS_DIR}"
    fi

    # Create .env file for Docker Compose (rest of the function remains unchanged)
    log_message "Creating Docker Compose .env file..."
    cat > "${INSTALL_DIR}/.env" << EOF
INSTALL_DIR=${INSTALL_DIR}
CONFIG_DIR=${INSTALL_DIR}/conf
POSTGRESQL_USER=${POSTGRESQL_USER:-postgres}
POSTGRESQL_PASSWORD=${POSTGRESQL_PASSWORD}
POSTGRESQL_DATABASE_NAME=${POSTGRESQL_DATABASE_NAME:-sting_app}
POSTGRES_USER=${POSTGRESQL_USER:-postgres}
POSTGRES_PASSWORD=${POSTGRESQL_PASSWORD}
POSTGRES_DB=${POSTGRESQL_DATABASE_NAME:-sting_app}
VAULT_TOKEN=${VAULT_TOKEN:-root}
ST_API_KEY=${ST_API_KEY}
ST_DASHBOARD_API_KEY=${ST_DASHBOARD_API_KEY}
HF_TOKEN=${HF_TOKEN:-}
STING_MODELS_DIR=${STING_MODELS_DIR:-${DEFAULT_MODELS_DIR}}
EOF

    # Set COMPOSE_BAKE based on application environment mode
    local app_env="development"
    if [ -f "${CONFIG_DIR}/config.yml" ] && command -v python3 >/dev/null 2>&1; then
        # Extract application.env from config.yml
        app_env=$(python3 -c "
import yaml
import sys
try:
    with open('${CONFIG_DIR}/config.yml', 'r') as f:
        config = yaml.safe_load(f)
    print(config.get('application', {}).get('env', 'development'))
except Exception:
    print('development')
" 2>/dev/null || echo "development")
    fi
    
    # Enable COMPOSE_BAKE for production mode only
    if [ "$app_env" = "production" ]; then
        echo "COMPOSE_BAKE=true" >> "${INSTALL_DIR}/.env"
        log_message "Production mode detected - enabled COMPOSE_BAKE for optimized builds"
    else
        echo "COMPOSE_BAKE=false" >> "${INSTALL_DIR}/.env"
        log_message "Development mode detected - disabled COMPOSE_BAKE for stable builds"
    fi
    chmod 600 "${INSTALL_DIR}/.env"
    
    log_message "Environment variables loaded successfully"
    
    # Generate Kratos config from template
    generate_kratos_config || {
        log_message "Failed to generate Kratos configuration" "ERROR"
        return 1
    }
    return 0
}

# Load LLM-specific environment files
load_llm_env_files() {
    log_message "Loading LLM variables from configuration files..."

    # Define base names or full names
    local env_files_to_load=("llm" "llm_gateway" "llama3" "phi3" "zephyr") # Use base names

    for base_name in "${env_files_to_load[@]}"; do
        # Construct the expected full path
        local file_path="${INSTALL_DIR}/env/${base_name}.env"

        if [ -f "$file_path" ]; then
            log_message "Loading $base_name environment from $file_path"

            while IFS='=' read -r key value || [[ -n "$key" ]]; do
                [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
                value=$(echo "$value" | sed -e 's/^["\x27]//' -e 's/["\x27]$//')
                export "$key=$value"
                # Optional: Debug log for HF_TOKEN specifically
                # if [ "$key" == "HF_TOKEN" ]; then
                #    log_message "DEBUG (load_llm_env_files): Exporting HF_TOKEN=[$value] from $file_path"
                # fi
            done < <(grep -v '^#' "$file_path")
        else
            log_message "WARNING: Environment file not found: $file_path"
        fi
    done

    log_message "LLM variables loaded successfully"
    return 0
}

# Load service-specific environment
load_service_env() {
    local service="$1"
    local env_file
    # Source configuration.sh to get get_env_file_path function
    source "${SCRIPT_DIR}/configuration.sh"
    env_file=$(get_env_file_path "$service" "$INSTALL_DIR")
    
    if [ -f "$env_file" ]; then
        log_message "Loading environment for $service from $env_file"
        while IFS='=' read -r key value; do
            [[ -z "$key" || "$key" =~ ^# ]] && continue
            value=$(echo "$value" | sed -e 's/^"//' -e 's/"$//')
            export "$key=$value"
        done < "$env_file"
        return 0
    else
        log_message "ERROR: Environment file not found for $service: $env_file"
        return 1
    fi
}

# Setup the complete environment
setup_environment() {
    log_message "Setting up environment with loaded configuration..."
    
    # Generate SSL certificates if needed
    if [ ! -f "${INSTALL_DIR}/certs/server.crt" ]; then
        # Source security.sh to get generate_ssl_certs function
        source "${SCRIPT_DIR}/security.sh"
        generate_ssl_certs
    fi
    
    # Ensure certificates are in Docker volume (source services.sh for the function)
    source "${SCRIPT_DIR}/services.sh"
    ensure_ssl_certificates
    
    # Set proper permissions
    find "${INSTALL_DIR}" -type f -exec chmod 644 {} \;
    find "${INSTALL_DIR}" -type d -exec chmod 755 {} \;
    find "${INSTALL_DIR}/env" -type f -exec chmod 600 {} \;
    
    # Select appropriate Dockerfile based on NODE_ENV
    if [ "$NODE_ENV" = "development" ]; then
        export DOCKERFILE="Dockerfile.react-dev"
    else
        export DOCKERFILE="Dockerfile.react"
    fi
    
    # # Setup models directory and symlinks
    # if [ -f "${INSTALL_DIR}/setup-model-symlinks.sh" ]; then
    #     log_message "Setting up model symlinks..."
    #     bash "${INSTALL_DIR}/setup-model-symlinks.sh"
    # else
    #     log_message "Model symlink script not found. Skipping model setup." "WARNING"
    # fi
    
    log_message "Environment setup completed successfully"
    return 0
}

# Verify environment dependencies
verify_environment() {
    log_message "Verifying system environment..."

    # Check Python
    if ! command -v python3 >/dev/null 2>&1; then
        log_message "ERROR: Python 3 is required but not installed"
        return 1
    fi

    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log_message "ERROR: Docker is required but not installed"
        return 1
    fi

    # Check Docker Compose
    if ! command -v docker compose>/dev/null 2>&1; then
        log_message "ERROR: Docker Compose is required but not installed"
        return 1
    fi

    return 0
}

# Ensure Python virtual environment is activated
ensure_venv_activated() {
    if check_dev_container; then
        docker compose exec -T dev bash -c '
            if [[ "$VIRTUAL_ENV" != "/app/venv" ]]; then
                source "/app/venv/bin/activate"
            fi
        '
    fi
}

# Create a new Python virtual environment
create_virtual_environment() {
    log_message "Creating virtual environment at $VENV_DIR..."
    if [ -d "$VENV_DIR" ]; then
        log_message "Virtual environment already exists. Skipping creation."
        return 0
    fi

    # Ensure parent directory exists
    mkdir -p "$(dirname "$VENV_DIR")"

    if command -v python3 &> /dev/null; then
        python3 -m venv "$VENV_DIR"
    elif command -v python &> /dev/null; then
        python -m venv "$VENV_DIR"
    else
        log_message "Error: Python 3 is not installed or not in PATH."
        return 1
    fi

    if [ ! -f "$VENV_DIR/bin/activate" ]; then
        log_message "Error: Virtual environment creation failed."
        return 1
    fi

    log_message "Virtual environment created successfully."
    return 0
}

# Prepare basic environment structure
prepare_basic_environment() {
    log_message "Preparing basic environment structure..."

    # Check if Docker network exists, create if not
    if ! docker network inspect sting_local >/dev/null 2>&1; then
        log_message "Creating Docker network: sting_local"
        if ! docker network create sting_local >/dev/null; then
            log_message "ERROR: Failed to create Docker network sting_local"
            return 1
        fi
        log_message "Docker network sting_local created successfully"
    else
        log_message "Docker network sting_local already exists"
    fi

    # Create necessary directories
    log_message "Creating essential directories..."
    mkdir -p "${INSTALL_DIR}/config_data" \
             "${INSTALL_DIR}/postgres_data" \
             "${INSTALL_DIR}/vault_data" \
             "${INSTALL_DIR}/vault_file" \
             "${INSTALL_DIR}/vault_persistent" \
             "${INSTALL_DIR}/vault_logs" \
             "${INSTALL_DIR}/certs" \
             "${INSTALL_DIR}/uploads" \
             "${INSTALL_DIR}/logs/llm" \
             "${STING_MODELS_DIR:-/tmp/sting_models}"

    log_message "Basic environment structure prepared successfully"
    return 0
}




