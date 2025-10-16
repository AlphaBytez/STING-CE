#!/bin/bash
# STING Management Script - Native LLM Service Module
# This module provides native LLM service management functions

# This module depends on logging functions being available
# The main manage_sting.sh script should have already initialized logging

# Constants for native LLM service
export NATIVE_LLM_PID_FILE="$HOME/.sting-ce/run/llm-gateway.pid"
export NATIVE_LLM_LOG_FILE="$LOG_DIR/llm-gateway.log"
export NATIVE_LLM_PORT=8086

# Health check constants (with defaults if not set)
export HEALTH_CHECK_RETRIES=${HEALTH_CHECK_RETRIES:-30}
export HEALTH_CHECK_INTERVAL=${HEALTH_CHECK_INTERVAL:-5s}

# Default models directory (platform-dependent)
if [[ "$(uname)" == "Darwin" ]]; then
    # On macOS, use a user-friendly Downloads location to avoid permission and sandbox issues
    export DEFAULT_MODELS_DIR="${DEFAULT_MODELS_DIR:-$HOME/Downloads/llm_models}"
else
    export DEFAULT_MODELS_DIR="${DEFAULT_MODELS_DIR:-/opt/models}"
fi

# Function to stop native LLM service
stop_native_llm_service() {
    # Use the new sting-llm binary
    if [ -f "${SOURCE_DIR}/sting-llm" ]; then
        "${SOURCE_DIR}/sting-llm" stop
        log_message "Native LLM service stopped"
    else
        # Fallback to old method if sting-llm not found
        local pid_file="$NATIVE_LLM_PID_FILE"
        
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if kill -0 "$pid" 2>/dev/null; then
                log_message "Stopping native LLM service (PID: $pid)"
                kill "$pid" 2>/dev/null || true
                sleep 2
                # Force kill if still running
                if kill -0 "$pid" 2>/dev/null; then
                    kill -9 "$pid" 2>/dev/null || true
                fi
            fi
            rm -f "$pid_file"
            log_message "Native LLM service stopped"
        fi
    fi
}


# Function to start native LLM service with MPS support
start_native_llm_service() {
    log_message "Starting native LLM service with modern stack..."
    
    # Use the new sting-llm binary
    if [ -f "${SOURCE_DIR}/sting-llm" ]; then
        chmod +x "${SOURCE_DIR}/sting-llm" || {
            log_message "Failed to set execute permissions on sting-llm" "WARNING"
        }
        
        # Start using sting-llm
        if "${SOURCE_DIR}/sting-llm" start; then
            log_message "Native LLM service started successfully"
            return 0
        else
            log_message "Failed to start native LLM service" "ERROR"
            return 1
        fi
    else
        log_message "sting-llm binary not found" "ERROR"
        return 1
    fi
    
    # Set up environment for native execution
    export PYTHONPATH="${PYTHONPATH}:$(pwd)/llm_service"
    # Use HuggingFace models directly - no local path needed
    export MODEL_NAME="phi3"  # Use stable phi3 model
    export DEVICE_TYPE="auto"  # Will auto-detect MPS
    export TORCH_DEVICE="auto"
    export PERFORMANCE_PROFILE="gpu_accelerated"
    export QUANTIZATION="8bit"  # Light quantization for memory efficiency
    export PORT="$NATIVE_LLM_PORT"
    export HF_TOKEN="${HF_TOKEN:-dummy}"
    export PYTORCH_ENABLE_MPS_FALLBACK=1
    
    # phi3 Memory optimizations
    export TORCH_MEMORY_FRACTION="0.75"
    export MODEL_CACHE_SIZE="1"
    export MAX_MEMORY_PER_MODEL="4G"
    export PHI3_OPTIMIZATION="true"
    export PYTORCH_CUDA_ALLOC_CONF="max_split_size_mb:256"
    export MODEL_PERSISTENCE="true"
    export MODEL_CLEANUP_INTERVAL="600"  # 10 minutes
    
    # Check if port 8086 is already in use
    if lsof -i :$NATIVE_LLM_PORT >/dev/null 2>&1; then
        log_message "Port $NATIVE_LLM_PORT is already in use - checking if it's Docker LLM gateway..." "WARNING"
        
        # Check if it's the Docker LLM gateway container
        if docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -q "sting-ce-llm-gateway.*$NATIVE_LLM_PORT"; then
            log_message "Stopping Docker LLM gateway to avoid port conflict..."
            docker stop sting-ce-llm-gateway >/dev/null 2>&1 || true
            sleep 2
        else
            log_message "Port $NATIVE_LLM_PORT is in use by another service - cannot start native LLM service" "ERROR"
            return 1
        fi
    fi
    
    # Skip local model check since we're using HuggingFace models
    log_message "Using HuggingFace models - will download automatically on first use"
    
    # Create PID file directory
    mkdir -p "$INSTALL_DIR/run"
    local pid_file="$NATIVE_LLM_PID_FILE"
    
    # Stop any existing native LLM service
    if [ -f "$pid_file" ]; then
        local old_pid=$(cat "$pid_file")
        if kill -0 "$old_pid" 2>/dev/null; then
            log_message "Stopping existing native LLM service (PID: $old_pid)"
            kill "$old_pid" 2>/dev/null || true
            sleep 2
        fi
        rm -f "$pid_file"
    fi
    
    # Check for venv and create if missing (like legacy version)
    local python_cmd="python3"
    local pip_cmd="pip3"
    local venv_path="${INSTALL_DIR}/.venv"
    
    if [ ! -d "$venv_path" ]; then
        log_message "Creating virtual environment at $venv_path..."
        if python3 -m venv "$venv_path"; then
            # Ensure proper permissions for the venv
            chmod -R u+rwx "$venv_path/bin" 2>/dev/null || true
            log_message "Virtual environment created successfully"
        else
            log_message "Failed to create virtual environment" "ERROR"
            return 1
        fi
    fi
    
    if [ -f "$venv_path/bin/activate" ]; then
        log_message "Activating virtual environment..."
        source "$venv_path/bin/activate"
        python_cmd="$venv_path/bin/python3"
        pip_cmd="$venv_path/bin/pip"
    else
        log_message "Virtual environment activation failed" "ERROR"
        return 1
    fi
    
    # Check and install Python dependencies using our comprehensive checker
    log_message "Checking Python dependencies..."
    
    # First run our dependency checker script
    if [ -f "${SOURCE_DIR}/scripts/check_llm_dependencies.sh" ]; then
        log_message "Running comprehensive dependency check for macOS LLM support..."
        INSTALL_DIR="$INSTALL_DIR" bash "${SOURCE_DIR}/scripts/check_llm_dependencies.sh" || {
            log_message "Dependency checker reported issues - attempting fallback installation" "WARNING"
        }
    fi
    
    # Verify critical dependencies are available
    if ! $python_cmd -c "import torch, fastapi, transformers" 2>/dev/null; then
        log_message "Critical Python dependencies still missing after check. Installing..." "WARNING"
        log_message "This may take several minutes on first install..."
        
        # Install from requirements files if they exist (like legacy)
        local requirements_installed=false
        for req_file in "${INSTALL_DIR}/llm_service/requirements.txt" \
                       "${INSTALL_DIR}/llm_service/requirements.common.txt" \
                       "${INSTALL_DIR}/llm_service/requirements.gateway.txt"; do
            if [ -f "$req_file" ]; then
                log_message "Installing from $req_file..."
                if $pip_cmd install --quiet -r "$req_file"; then
                    requirements_installed=true
                else
                    log_message "Failed to install from $req_file" "WARNING"
                fi
            fi
        done
        
        # Fallback to basic packages if requirements files not found
        if [ "$requirements_installed" = "false" ]; then
            log_message "Requirements files not found, installing basic packages..."
            if ! $pip_cmd install torch torchvision transformers accelerate fastapi uvicorn sentencepiece protobuf safetensors huggingface_hub; then
                log_message "Failed to install Python dependencies" "ERROR"
                log_message "Please install manually: $pip_cmd install torch torchvision transformers accelerate fastapi uvicorn sentencepiece protobuf safetensors huggingface_hub" "ERROR"
                return 1
            fi
        fi
        
        # Verify installation
        if ! $python_cmd -c "import torch, fastapi, transformers" 2>/dev/null; then
            log_message "Dependency installation verification failed" "ERROR"
            return 1
        fi
        
        log_message "Python dependencies installed successfully"
    else
        log_message "Python dependencies already installed"
    fi
    
    # Kill any existing processes on the port
    if lsof -ti:$PORT >/dev/null 2>&1; then
        log_message "Killing existing processes on port $PORT..."
        lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
        sleep 2
    fi
    
    # Start the service in background
    log_message "Starting LLM service on port $PORT..."
    local original_pwd="$(pwd)"
    cd llm_service || {
        log_message "Failed to change to llm_service directory" "ERROR"
        return 1
    }
    # Use venv python if available
    local python_exec="python3"
    if [ -f "${INSTALL_DIR}/.venv/bin/python3" ]; then
        python_exec="${INSTALL_DIR}/.venv/bin/python3"
    fi
    
    # Load phi3 environment variables as default model
    if [ -f "${INSTALL_DIR}/env/phi3.env" ]; then
        log_message "Loading phi3 environment variables..."
        export $(grep -v '^#' "${INSTALL_DIR}/env/phi3.env" | xargs)
    # Fallback to tinyllama if phi3 not available
    elif [ -f "${INSTALL_DIR}/env/tinyllama.env" ]; then
        log_message "Loading tinyllama environment variables as fallback..."
        export $(grep -v '^#' "${INSTALL_DIR}/env/tinyllama.env" | xargs)
    fi
    
    # Ensure server binds to all interfaces for Docker connectivity
    export HOST="0.0.0.0"
    export PORT="${NATIVE_LLM_PORT:-8086}"
    
    nohup "$python_exec" server.py > "$NATIVE_LLM_LOG_FILE" 2>&1 &
    local llm_pid=$!
    echo $llm_pid > "$pid_file"
    cd "$original_pwd" || log_message "Failed to return to original directory" "WARNING"
    
    # Give it a moment to start
    sleep 5
    
    # Check if it's running
    if kill -0 "$llm_pid" 2>/dev/null; then
        log_message "Native LLM service started successfully (PID: $llm_pid)" "SUCCESS"
        log_message "Logs available at: $NATIVE_LLM_LOG_FILE"
        return 0
    else
        log_message "Native LLM service failed to start" "ERROR"
        rm -f "$pid_file"
        return 1
    fi
}

# Function to check if native LLM service is running
is_native_llm_running() {
    local pid_file="$NATIVE_LLM_PID_FILE"
    
    # First check if we have a valid PID file
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Running
        else
            # PID file exists but process is dead, clean up
            rm -f "$pid_file"
        fi
    fi
    
    # If no valid PID file, check if service is responding on the port
    if curl -sf "http://localhost:${NATIVE_LLM_PORT:-8086}/health" >/dev/null 2>&1; then
        # Service is running but no PID file - try to find and record the PID
        local running_pid=$(lsof -ti :${NATIVE_LLM_PORT:-8086} 2>/dev/null | head -1)
        if [ -n "$running_pid" ]; then
            # Create PID file for future checks
            mkdir -p "$(dirname "$pid_file")"
            echo "$running_pid" > "$pid_file"
        fi
        return 0  # Running
    fi
    
    return 1  # Not running
}

# Function to get native LLM service status
get_native_llm_status() {
    if is_native_llm_running; then
        local pid=$(cat "$NATIVE_LLM_PID_FILE")
        echo "Native LLM service is running (PID: $pid)"
        echo "Port: $NATIVE_LLM_PORT"
        echo "Logs: $NATIVE_LLM_LOG_FILE"
        return 0
    else
        echo "Native LLM service is not running"
        return 1
    fi
}

# Function to restart native LLM service
restart_native_llm_service() {
    log_message "Restarting native LLM service..."
    # Use the new sting-llm binary
    if [ -f "${SOURCE_DIR}/sting-llm" ]; then
        "${SOURCE_DIR}/sting-llm" restart
    else
        # Fallback to old method
        stop_native_llm_service
        sleep 2
        start_native_llm_service
    fi
}

# Function to automatically setup native LLM service on macOS during installation
setup_native_llm_for_macos() {
    if [[ "$(uname)" != "Darwin" ]]; then
        return 0  # Not macOS, skip
    fi
    
    log_message "Setting up native LLM service for macOS installation..."
    
    # 1. Run dependency checker first to ensure all requirements are met
    if [ -f "${SOURCE_DIR}/scripts/check_llm_dependencies.sh" ]; then
        log_message "Checking and installing LLM dependencies for macOS..."
        INSTALL_DIR="$INSTALL_DIR" bash "${SOURCE_DIR}/scripts/check_llm_dependencies.sh" || {
            log_message "Dependency check reported issues - continuing with setup" "WARNING"
        }
    fi
    
    # 2. Stop Docker LLM gateway if running
    if docker ps --format "table {{.Names}}" | grep -q "sting-ce-llm-gateway"; then
        log_message "Stopping Docker LLM gateway for macOS native setup..."
        docker stop sting-ce-llm-gateway >/dev/null 2>&1 || true
    fi
    
    # 3. Use the setup script if available
    if [ -f "${SOURCE_DIR}/setup-native-llm-mac.sh" ]; then
        log_message "Running native LLM setup script..."
        bash "${SOURCE_DIR}/setup-native-llm-mac.sh" || {
            log_message "Native LLM setup script failed, falling back to manual setup" "WARNING"
        }
        return $?
    fi
    
    # 3. Fallback: Use sting-llm script directly
    if [ -f "${SOURCE_DIR}/sting-llm" ]; then
        log_message "Starting native LLM service with sting-llm script..."
        bash "${SOURCE_DIR}/sting-llm" start || {
            log_message "Failed to start native LLM service" "WARNING"
            return 1
        }
        
        # 4. Verify nginx proxy configuration exists
        local proxy_conf="${SOURCE_DIR}/nginx-llm-proxy.conf"
        if [ ! -f "$proxy_conf" ]; then
            log_message "nginx-llm-proxy.conf not found - proxy may not work correctly" "WARNING"
        else
            log_message "Nginx proxy configuration found"
        fi
        
        log_message "Native LLM service setup completed for macOS" "SUCCESS"
        return 0
    else
        log_message "sting-llm script not found, skipping native setup" "WARNING"
        return 1
    fi
}