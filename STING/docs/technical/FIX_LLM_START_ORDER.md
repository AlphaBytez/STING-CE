# Fix for LLM Service Start Order

## Problem
The native LLM service is starting BEFORE:
1. Models are downloaded
2. Docker images are built  
3. Python dependencies are verified

This causes the "Native LLM service failed to start" error you're seeing.

## Root Cause
In `build_and_start_services()` around line 1757, the code tries to start the native LLM service immediately, with the incorrect assumption that it needs to be available during Docker build. This is wrong because:

1. Models aren't downloaded yet at this point
2. The native service can't start without models
3. Docker services don't need the native service during build time

## Solution

### Quick Fix
Move the native LLM service start to the END of `build_and_start_services()`:

```bash
build_and_start_services() {
    # ... existing code ...
    
    # Build Docker images FIRST
    log_message "Building Docker images..."
    docker compose build --parallel
    
    # Start Docker services
    log_message "Starting Docker services..."
    docker compose up -d
    
    # THEN start native LLM service (only on macOS)
    if [[ "$(uname)" == "Darwin" ]]; then
        log_message "Starting native LLM service for macOS..."
        if start_native_llm_service; then
            log_message "Native LLM service started on port 8085"
        else
            log_message "Native LLM fallback to Docker gateway"
        fi
    fi
}
```

### Proper Fix
Add a new function to handle macOS-specific services:

```bash
# Start macOS-specific services after main installation
start_macos_services() {
    if [[ "$(uname)" != "Darwin" ]]; then
        return 0
    fi
    
    log_message "Configuring macOS-specific services..."
    
    # Check if models exist before starting native LLM
    if [ -d "$MODELS_DIR/TinyLlama-1.1B-Chat" ] || [ -d "$HOME/.cache/huggingface/hub" ]; then
        log_message "Models found, starting native LLM service..."
        
        if start_native_llm_service; then
            log_message "✅ Native LLM service started (Metal acceleration enabled)"
            
            # Update config to prefer native service
            export NATIVE_LLM_URL="http://host.docker.internal:8085"
            
            # Test the service
            if curl -s http://localhost:8085/health >/dev/null 2>&1; then
                log_message "✅ Native LLM service is healthy"
            else
                log_message "⚠️  Native LLM service started but health check failed"
            fi
        else
            log_message "⚠️  Native LLM service failed, using Docker fallback"
        fi
    else
        log_message "⚠️  Models not found, skipping native LLM service"
        log_message "Run './manage_sting.sh download_models' to download models"
    fi
}
```

Then call it at the END of the installation process:

```bash
install_msting() {
    # ... existing installation steps ...
    
    # Build and start Docker services
    build_and_start_services
    
    # Start platform-specific services LAST
    start_macos_services
    
    log_message "Installation complete!"
}
```

## Expected Order After Fix

1. ✅ Check system requirements
2. ✅ Download/verify models (`check_llm_models`)
3. ✅ Generate configuration
4. ✅ Build Docker images
5. ✅ Start Docker services
6. ✅ Verify Docker services are healthy
7. ✅ THEN start native LLM service (macOS only)
8. ✅ Final health checks

## Benefits

1. **No more startup failures** - Models exist before LLM service starts
2. **Faster installation** - No 5-second wait for a service that will fail
3. **Better error handling** - Can check for models before attempting start
4. **Cleaner logs** - No confusing error in the middle of installation

## Testing

After applying the fix:
```bash
# Clean reinstall to test
./manage_sting.sh uninstall
./manage_sting.sh install

# You should see:
# - No "Native LLM service failed to start" during Docker builds
# - Native LLM starts at the END after "All services built"
# - Clean installation without mid-process errors
```