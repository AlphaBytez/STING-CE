# Ollama Setup Guide for STING

## Current Status
- External AI service is running and configured
- Ollama is NOT installed on the system
- Installation requires sudo privileges

## Installation Steps

### Option 1: Install in WSL2 (Recommended)
```bash
# Run with sudo
sudo ./scripts/install_ollama.sh

# Or install manually:
curl -fsSL https://ollama.ai/install.sh | sudo sh

# Start Ollama service
ollama serve

# Pull required models
ollama pull phi3:mini
ollama pull deepseek-r1:latest
```

### Option 2: Install on Windows Host
1. Download Ollama for Windows from https://ollama.ai/download
2. Install and run Ollama on Windows
3. The WSL2 containers will connect via `host.docker.internal:11434`

## Verify Installation

After installation, check:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Check STING external-ai service
curl http://localhost:8091/ollama/status
curl http://localhost:8091/ollama/models
```

## Testing

Once Ollama is installed with models:
```bash
# Test Ollama directly
ollama run phi3:mini "Hello, how are you?"

# Test through STING external-ai service
curl -X POST http://localhost:8091/ollama/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "phi3:mini",
    "prompt": "Hello, how are you?",
    "options": {}
  }'
```

## Session Logout Fix Status

I've already updated the Kratos configuration:
- ✅ Changed all port references from 3000 to 8443
- ✅ Updated cookie name to 'ory_kratos_session'
- ✅ Restarted Kratos service

To test the logout fix:
1. Clear all browser cookies for localhost
2. Login to https://localhost:8443
3. Click logout
4. Try to access a protected page - you should be redirected to login
5. The session should be properly cleared

## Git Update

There's a pending update with session improvements. To apply:
```bash
# Configure git credentials or SSH
git config --global credential.helper store
# Then pull
git pull origin main
```