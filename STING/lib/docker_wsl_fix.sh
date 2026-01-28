#!/bin/bash
# docker_wsl_fix.sh - Fix Docker credential helper issues in WSL2

# Function to detect if we're running in WSL2
is_wsl2() {
    if [ -f /proc/sys/kernel/osrelease ]; then
        grep -qi "microsoft" /proc/sys/kernel/osrelease
        return $?
    fi
    return 1
}

# Function to fix Docker credential helper in WSL2
fix_docker_credential_helper() {
    # Only apply fix if we're in WSL2
    if ! is_wsl2; then
        return 0
    fi

    # Check if Docker config exists and has desktop.exe credential store
    if [ -f ~/.docker/config.json ]; then
        if grep -q '"credsStore".*"desktop.exe"' ~/.docker/config.json 2>/dev/null; then
            log_message "Detected Docker Desktop credential helper in WSL2 - applying fix..."
            
            # Create a backup of the original config
            cp ~/.docker/config.json ~/.docker/config.json.backup.$(date +%Y%m%d_%H%M%S)
            
            # Remove the credsStore line to use default Docker credentials
            # This allows Docker to pull images without requiring desktop.exe
            if command -v jq >/dev/null 2>&1; then
                jq 'del(.credsStore)' ~/.docker/config.json > ~/.docker/config.json.tmp && \
                    mv ~/.docker/config.json.tmp ~/.docker/config.json
            else
                # Fallback: use sed to remove the credsStore line
                sed -i.bak '/"credsStore"/d' ~/.docker/config.json
                # Clean up any trailing commas
                sed -i 's/,\([[:space:]]*}\)/\1/g' ~/.docker/config.json
            fi
            
            log_message "Docker credential helper fix applied for WSL2"
            return 0
        fi
    fi
    
    return 0
}

# Function to restore Docker credential helper (if needed for Docker Desktop integration)
restore_docker_credential_helper() {
    # Only apply if we're in WSL2
    if ! is_wsl2; then
        return 0
    fi

    # Check if backup exists
    local latest_backup=$(ls -t ~/.docker/config.json.backup.* 2>/dev/null | head -1)
    if [ -n "$latest_backup" ]; then
        log_message "Restoring Docker credential helper from backup: $latest_backup"
        cp "$latest_backup" ~/.docker/config.json
        log_message "Docker credential helper restored"
        return 0
    else
        log_message "No Docker config backup found to restore"
        return 1
    fi
}

# Alternative: Create a wrapper for docker-credential-desktop.exe
create_credential_helper_wrapper() {
    # Only apply if we're in WSL2
    if ! is_wsl2; then
        return 0
    fi

    # Create a directory for our wrapper if it doesn't exist
    local wrapper_dir="$HOME/.local/bin"
    mkdir -p "$wrapper_dir"
    
    # Create wrapper script
    cat > "$wrapper_dir/docker-credential-desktop.exe" << 'EOF'
#!/bin/bash
# Wrapper for docker-credential-desktop.exe in WSL2
# This prevents errors when Docker tries to use Windows credential helper
# Simply exit with success to allow Docker operations to continue
exit 0
EOF
    
    chmod +x "$wrapper_dir/docker-credential-desktop.exe"
    
    # Ensure wrapper directory is in PATH
    if ! echo "$PATH" | grep -q "$wrapper_dir"; then
        export PATH="$wrapper_dir:$PATH"
        # Add to .bashrc for persistence
        echo "export PATH=\"$wrapper_dir:\$PATH\"" >> ~/.bashrc
    fi
    
    log_message "Created Docker credential helper wrapper for WSL2"
    return 0
}

# Export functions for use in other scripts
export -f is_wsl2
export -f fix_docker_credential_helper
export -f restore_docker_credential_helper
export -f create_credential_helper_wrapper