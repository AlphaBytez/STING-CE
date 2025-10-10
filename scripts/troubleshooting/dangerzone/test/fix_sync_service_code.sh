#!/bin/bash
# Fixed sync_service_code function with proper venv exclusion

sync_service_code() {
    local service="$1"
    
    # Common exclusions for all services
    local COMMON_EXCLUDES=(
        --exclude='venv'
        --exclude='**/venv'
        --exclude='.venv'
        --exclude='**/.venv'
        --exclude='__pycache__'
        --exclude='**/__pycache__'
        --exclude='*.pyc'
        --exclude='*.pyo'
        --exclude='*.pyd'
        --exclude='.git'
        --exclude='.pytest_cache'
        --exclude='*.log'
        --exclude='.DS_Store'
        --exclude='*.egg-info'
        --exclude='**/*.egg-info'
    )
    
    case "$service" in
        frontend)
            rsync -av --delete "$PROJECT_DIR/frontend/" "$INSTALL_DIR/frontend/" \
                "${COMMON_EXCLUDES[@]}" \
                --exclude='node_modules' \
                --exclude='**/node_modules' \
                --exclude='build' \
                --exclude='dist' \
                --exclude='.next' \
                --exclude='coverage'
            ;;
        chatbot)
            rsync -av "$PROJECT_DIR/chatbot/" "$INSTALL_DIR/chatbot/" \
                "${COMMON_EXCLUDES[@]}"
            # Also copy llm_service/chat for shared code
            mkdir -p "$INSTALL_DIR/llm_service"
            rsync -av "$PROJECT_DIR/llm_service/chat/" "$INSTALL_DIR/llm_service/chat/" \
                "${COMMON_EXCLUDES[@]}"
            rsync -av "$PROJECT_DIR/llm_service/filtering/" "$INSTALL_DIR/llm_service/filtering/" \
                "${COMMON_EXCLUDES[@]}"
            ;;
        llm-gateway)
            rsync -av "$PROJECT_DIR/llm_service/" "$INSTALL_DIR/llm_service/" \
                "${COMMON_EXCLUDES[@]}" \
                --exclude='models' \
                --exclude='*.bin' \
                --exclude='*.safetensors'
            ;;
        app)
            rsync -av "$PROJECT_DIR/app/" "$INSTALL_DIR/app/" \
                "${COMMON_EXCLUDES[@]}" \
                --exclude='instance' \
                --exclude='flask_session'
            ;;
        messaging)
            rsync -av "$PROJECT_DIR/messaging_service/" "$INSTALL_DIR/messaging_service/" \
                "${COMMON_EXCLUDES[@]}"
            ;;
        kratos)
            rsync -av "$PROJECT_DIR/kratos/" "$INSTALL_DIR/kratos/" \
                "${COMMON_EXCLUDES[@]}"
            ;;
        vault)
            rsync -av "$PROJECT_DIR/vault/" "$INSTALL_DIR/vault/" \
                "${COMMON_EXCLUDES[@]}"
            ;;
        database)
            rsync -av "$PROJECT_DIR/database/" "$INSTALL_DIR/database/" \
                "${COMMON_EXCLUDES[@]}"
            rsync -av "$PROJECT_DIR/docker-entrypoint-initdb.d/" "$INSTALL_DIR/docker-entrypoint-initdb.d/" \
                "${COMMON_EXCLUDES[@]}"
            ;;
        web-server)
            rsync -av "$PROJECT_DIR/web-server/" "$INSTALL_DIR/web-server/" \
                "${COMMON_EXCLUDES[@]}"
            ;;
        *)
            log_message "Unknown service: $service" "WARNING"
            return 1
            ;;
    esac
    
    return 0
}

# Alternative: Create a global rsync wrapper
rsync_with_excludes() {
    local args=()
    local has_excludes=false
    
    # Check if excludes are already provided
    for arg in "$@"; do
        if [[ "$arg" == "--exclude"* ]]; then
            has_excludes=true
            break
        fi
    done
    
    # If no excludes, add our standard ones
    if [ "$has_excludes" = false ]; then
        # Find where source/dest args are (usually last two)
        local num_args=$#
        local dest="${!num_args}"
        local src="${@:$((num_args-1)):1}"
        local other_args=("${@:1:$((num_args-2))}")
        
        # Run rsync with our excludes
        rsync "${other_args[@]}" \
            --exclude='venv' \
            --exclude='**/venv' \
            --exclude='.venv' \
            --exclude='**/.venv' \
            --exclude='__pycache__' \
            --exclude='**/__pycache__' \
            --exclude='*.pyc' \
            --exclude='.git' \
            --exclude='node_modules' \
            --exclude='**/node_modules' \
            "$src" "$dest"
    else
        # Run rsync as-is
        rsync "$@"
    fi
}