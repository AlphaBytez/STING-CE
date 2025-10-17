# Ollama Setup Guide for STING

Complete guide for configuring LLM backends with STING-CE, including Ollama, LM Studio, and other OpenAI-compatible endpoints.

## Table of Contents

- [Overview](#overview)
- [Installation Options](#installation-options)
- [Network Configuration](#network-configuration)
- [Wizard Setup](#wizard-setup)
- [Alternative LLM Backends](#alternative-llm-backends)
- [Troubleshooting](#troubleshooting)
- [Advanced Configuration](#advanced-configuration)

---

## Overview

STING-CE requires an LLM backend to power the Worker Bee AI assistant. The system supports:

- **Ollama** (local, free) - Recommended for most users
- **LM Studio** (local, free) - Great for Mac users and advanced configurations
- **vLLM** (local, free) - High-performance inference server
- **Any OpenAI-compatible API** - Works with most modern LLM servers

All of these use the same OpenAI-compatible API format, making them interchangeable.

---

## Installation Options

### Option 1: Ollama on Linux/WSL2 (Recommended)

**Best for**: Linux users, Ubuntu VMs, WSL2 environments

```bash
# Install Ollama
curl -fsSL https://ollama.ai/install.sh | sudo sh

# Start Ollama service (will run in foreground)
ollama serve &

# Pull recommended models
ollama pull phi3:mini           # Fast, lightweight (2.3GB)
ollama pull deepseek-r1:latest  # Advanced reasoning (varies by version)

# Verify installation
curl http://localhost:11434/api/tags
```

**Auto-start on boot** (Linux):
```bash
# Create systemd service
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama LLM Service
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/ollama serve
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl enable ollama
sudo systemctl start ollama
sudo systemctl status ollama
```

### Option 2: Ollama on Windows Host (for WSL2 users)

**Best for**: WSL2 users who want Ollama running on Windows

1. Download Ollama for Windows from https://ollama.ai/download
2. Install and run Ollama on Windows (starts automatically)
3. Open PowerShell and pull models:
   ```powershell
   ollama pull phi3:mini
   ollama pull deepseek-r1:latest
   ```
4. In STING wizard, use endpoint: `http://host.docker.internal:11434`

**Why this works**: WSL2 Docker containers can access Windows localhost via `host.docker.internal`

### Option 3: Ollama on Mac

**Best for**: macOS users running STING natively

```bash
# Install via Homebrew
brew install ollama

# Or download from https://ollama.ai/download

# Start Ollama (runs as background service)
ollama serve &

# Pull models
ollama pull phi3:mini
ollama pull deepseek-r1:latest

# Verify
curl http://localhost:11434/api/tags
```

In STING wizard, use endpoint: `http://localhost:11434`

### Option 4: LM Studio (All Platforms)

**Best for**: Users who want a GUI, Mac users, advanced model management

1. Download LM Studio from https://lmstudio.ai/
2. Launch LM Studio and download models via the GUI:
   - **Phi-3 Mini 3.8B** (fast, small)
   - **DeepSeek-R1** (advanced reasoning)
   - **Microsoft Phi-4 Mini** (latest, high quality)
3. Click "Local Server" tab
4. Click "Start Server" (default port: 1234)
5. Note the server URL shown (e.g., `http://localhost:1234`)

In STING wizard, use endpoint: `http://localhost:1234` (or `http://host.docker.internal:1234` for WSL2)

**LM Studio Advantages**:
- User-friendly GUI for model management
- Advanced configuration options (context size, GPU layers, etc.)
- Built-in chat interface for testing
- Works great on Apple Silicon Macs

---

## Network Configuration

### Local Installation (Same Machine)

If STING and your LLM backend are on the same machine:

**Docker STING → Host LLM backend**:
```
Endpoint: http://host.docker.internal:11434  (Ollama)
Endpoint: http://host.docker.internal:1234   (LM Studio)
```

**Native STING (no Docker)**:
```
Endpoint: http://localhost:11434  (Ollama)
Endpoint: http://localhost:1234   (LM Studio)
```

### Remote LLM Server

If your LLM backend is on a different machine (recommended for VMs):

#### Using Tailscale (Recommended for VPNs)

**Scenario**: You're running STING in a VM and want to use Ollama on your host machine or another server on your Tailscale network.

1. **Install Tailscale on both machines**:
   ```bash
   # On Ubuntu VM (where STING runs)
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up

   # On LLM server (where Ollama/LM Studio runs)
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```

2. **Get Tailscale IP of LLM server**:
   ```bash
   # On the LLM server
   tailscale ip -4
   # Example output: 100.103.191.31
   ```

3. **Configure Ollama to listen on Tailscale interface**:
   ```bash
   # Set environment variable before starting Ollama
   export OLLAMA_HOST=0.0.0.0:11434  # Listen on all interfaces
   ollama serve

   # For systemd service, edit /etc/systemd/system/ollama.service:
   [Service]
   Environment="OLLAMA_HOST=0.0.0.0:11434"
   ```

4. **Test connectivity from STING VM**:
   ```bash
   curl http://100.103.191.31:11434/api/tags
   ```

5. **In STING wizard, use**:
   ```
   Endpoint: http://100.103.191.31:11434
   ```

**Security Note**: Tailscale creates an encrypted mesh network, so this is secure even without HTTPS.

#### Using Direct IP (Local Network)

If both machines are on the same local network:

1. **Get LLM server's local IP**:
   ```bash
   # Linux/Mac
   ip addr show | grep "inet " | grep -v 127.0.0.1
   # or
   hostname -I | awk '{print $1}'
   ```

2. **Configure firewall to allow port 11434** (Ollama) or **1234** (LM Studio):
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 11434/tcp

   # Or for LM Studio
   sudo ufw allow 1234/tcp
   ```

3. **Test connectivity from STING machine**:
   ```bash
   curl http://192.168.1.100:11434/api/tags
   ```

4. **In STING wizard, use**:
   ```
   Endpoint: http://192.168.1.100:11434
   ```

---

## Wizard Setup

When you run `./install_sting.sh`, the wizard will guide you through LLM configuration.

### Step 4: LLM Backend Configuration

#### Test Your Endpoint First

**Before starting the wizard**, verify your LLM endpoint is accessible:

```bash
# For Ollama
curl http://localhost:11434/api/tags
# Should return: {"models": [...]}

# For LM Studio
curl http://localhost:1234/v1/models
# Should return: {"data": [...]}

# For Tailscale remote
curl http://100.103.191.31:11434/api/tags
```

#### Wizard Configuration

1. **LLM Endpoint URL**: Enter your endpoint (examples below)
2. **Default Model**: Enter the model name exactly as it appears

**Endpoint Examples**:

| Scenario | Endpoint URL |
|----------|-------------|
| Ollama on same machine (Docker STING) | `http://host.docker.internal:11434` |
| Ollama on same machine (native STING) | `http://localhost:11434` |
| LM Studio on same machine (Docker) | `http://host.docker.internal:1234` |
| LM Studio on same machine (native) | `http://localhost:1234` |
| Ollama on Tailscale network | `http://100.103.191.31:11434` |
| Ollama on local network | `http://192.168.1.100:11434` |

**Model Examples**:

| LLM Backend | Model Name | Notes |
|-------------|------------|-------|
| Ollama | `phi3:mini` | Fast, lightweight |
| Ollama | `deepseek-r1:latest` | Advanced reasoning |
| Ollama | `phi4:latest` | Latest Microsoft model |
| LM Studio | `microsoft/phi-4-mini-reasoning` | Full model identifier |
| LM Studio | `deepseek-ai/DeepSeek-R1-Distill-Qwen-7B-GGUF` | Full path shown in LM Studio |

**How to find your model name**:

```bash
# Ollama
ollama list
# Copy the NAME column exactly

# LM Studio
# Check the "Local Server" tab - it shows loaded model name

# Via API
curl http://localhost:11434/api/tags | jq '.models[].name'
curl http://localhost:1234/v1/models | jq '.data[].id'
```

#### Test Connection in Wizard

After entering your endpoint and model:

1. Click **"Test Connection"** button
2. Wait for response (may take 5-10 seconds for first request)
3. Success indicators:
   - "Connected (OpenAI-compatible)" - LM Studio, vLLM
   - "Connected (Ollama)" - Ollama server
   - Shows number of available models
4. If test fails, see [Troubleshooting](#troubleshooting)

---

## Alternative LLM Backends

### vLLM (High-Performance Inference)

**Best for**: Advanced users, GPU servers, high throughput

```bash
# Install vLLM
pip install vllm

# Start server with a model
vllm serve microsoft/Phi-3-mini-4k-instruct \
  --host 0.0.0.0 \
  --port 8000

# In STING wizard:
# Endpoint: http://localhost:8000
# Model: microsoft/Phi-3-mini-4k-instruct
```

### Ollama with Custom Models

```bash
# Import a custom GGUF model
ollama create my-model -f Modelfile

# Example Modelfile:
echo 'FROM ./my-model.gguf' > Modelfile
ollama create my-custom-model -f Modelfile

# Use in STING:
# Model: my-custom-model
```

### Text Generation WebUI (oobabooga)

```bash
# Start server with OpenAI API extension
python server.py \
  --model TheBloke/Phi-3-mini-4k-instruct-GGUF \
  --api \
  --extensions openai

# In STING wizard:
# Endpoint: http://localhost:5000/v1
# Model: (check API /v1/models endpoint)
```

---

## Troubleshooting

### Connection Test Fails: "Connection refused"

**Symptoms**: Wizard shows "Failed to connect to LLM endpoint"

**Cause**: LLM server not running or not accessible

**Solutions**:
```bash
# 1. Check if Ollama is running
ps aux | grep ollama
# If not running:
ollama serve &

# 2. Check if port is listening
sudo netstat -tlnp | grep 11434
# or
sudo lsof -i :11434

# 3. Test from terminal
curl -v http://localhost:11434/api/tags

# 4. If using Tailscale, verify IP
tailscale ip -4
ping 100.103.191.31

# 5. Check firewall
sudo ufw status
sudo ufw allow 11434/tcp
```

### Connection Test Fails: "No route to host"

**Symptoms**: Can't reach remote LLM server

**Cause**: Network connectivity or firewall blocking

**Solutions**:
```bash
# 1. Verify network connectivity
ping 100.103.191.31  # or your LLM server IP

# 2. Check if Tailscale is connected
tailscale status

# 3. On LLM server, verify Ollama is listening on correct interface
sudo netstat -tlnp | grep 11434
# Should show: 0.0.0.0:11434 (not 127.0.0.1:11434)

# 4. Restart Ollama with correct binding
export OLLAMA_HOST=0.0.0.0:11434
ollama serve
```

### Models Not Listed

**Symptoms**: Test succeeds but no models shown

**Cause**: No models pulled yet

**Solutions**:
```bash
# Ollama - pull models
ollama pull phi3:mini
ollama pull deepseek-r1:latest
ollama list  # Verify

# LM Studio - download via GUI
# 1. Open LM Studio
# 2. Click "Discover" tab
# 3. Search for "phi-3" or "deepseek"
# 4. Click download
```

### Wrong Model Name

**Symptoms**: Installation completes but Bee doesn't respond

**Cause**: Model name mismatch between config and available models

**Solutions**:
```bash
# 1. Check what models are actually available
curl http://localhost:11434/api/tags | jq '.models[].name'
# Output example: "phi3:mini", "deepseek-r1:latest"

# 2. Update config.yml with exact name
vim /opt/sting-ce/conf/config.yml
# Find llm_service.ollama.default_model
# Change to match exact name from step 1

# 3. Regenerate environment files
cd /opt/sting-ce
./manage_sting.sh regenerate-env

# 4. Restart services
./manage_sting.sh restart external-ai chatbot
```

### WSL2 "host.docker.internal" Not Working

**Symptoms**: Can't connect to Windows host from WSL2 containers

**Cause**: WSL2 networking issue

**Solutions**:
```bash
# 1. Get Windows host IP from WSL2
ip route show | grep -i default | awk '{ print $3}'
# Example output: 172.18.224.1

# 2. Test connectivity to Windows Ollama
curl http://172.18.224.1:11434/api/tags

# 3. If that works, use that IP in wizard instead of host.docker.internal
# Endpoint: http://172.18.224.1:11434
```

### Slow Response Times

**Symptoms**: Bee takes 30+ seconds to respond

**Cause**: Model too large for available RAM/VRAM, or CPU inference

**Solutions**:
```bash
# 1. Use smaller model
ollama pull phi3:mini  # Only 2.3GB

# 2. Check system resources
free -h  # Check RAM
nvidia-smi  # Check GPU (if available)

# 3. For LM Studio, reduce context size
# Settings → Context Length → 2048 (instead of 4096+)

# 4. For Ollama, limit concurrent requests
export OLLAMA_NUM_PARALLEL=1
ollama serve
```

### Mac: "Ollama not found"

**Symptoms**: `ollama` command not in PATH after installation

**Solutions**:
```bash
# 1. If installed via Homebrew
brew link ollama

# 2. If installed via .dmg
# Add to PATH in ~/.zshrc or ~/.bash_profile
export PATH="/Applications/Ollama.app/Contents/MacOS:$PATH"
source ~/.zshrc

# 3. Or use absolute path
/Applications/Ollama.app/Contents/MacOS/ollama serve
```

---

## Advanced Configuration

### Using Multiple Models

Edit `conf/config.yml` after installation:

```yaml
llm_service:
  ollama:
    default_model: "phi3:mini"
    models_to_install:
      - "phi3:mini"           # Fast responses
      - "deepseek-r1:latest"  # Complex reasoning
      - "phi4:latest"         # Latest features
```

Then regenerate and restart:
```bash
./manage_sting.sh regenerate-env
./manage_sting.sh restart external-ai chatbot
```

### Custom Ollama Parameters

Create a custom Modelfile:

```dockerfile
# Modelfile
FROM phi3:mini

# Set custom parameters
PARAMETER temperature 0.7
PARAMETER top_p 0.9
PARAMETER top_k 40
PARAMETER num_ctx 4096

# Set system prompt
SYSTEM You are a helpful assistant for STING-CE.
```

Create and use:
```bash
ollama create sting-phi3 -f Modelfile
# Update config.yml default_model to "sting-phi3"
```

### Monitoring LLM Usage

Check logs:
```bash
# STING External AI service
./manage_sting.sh logs external-ai

# Bee chatbot
./manage_sting.sh logs chatbot

# Ollama (if using systemd)
sudo journalctl -u ollama -f
```

### Performance Tuning

**For GPU acceleration** (NVIDIA):
```bash
# Install NVIDIA container toolkit
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

# Configure Ollama to use GPU
# Ollama auto-detects GPU, just verify:
ollama run phi3:mini --verbose
# Look for "Using GPU: NVIDIA ..." in output
```

**For Apple Silicon Macs**:
- Ollama and LM Studio automatically use Metal acceleration
- No additional configuration needed
- Verify in Activity Monitor → GPU usage

**For CPU-only systems**:
```bash
# Use smaller quantized models
ollama pull phi3:mini  # Already optimized for CPU

# Limit parallel requests
export OLLAMA_NUM_PARALLEL=1
export OLLAMA_MAX_LOADED_MODELS=1
ollama serve
```

### API Reference

**Ollama Endpoints**:
```bash
# List models
GET http://localhost:11434/api/tags

# Generate completion
POST http://localhost:11434/api/generate
{
  "model": "phi3:mini",
  "prompt": "Hello",
  "stream": false
}

# Chat completion
POST http://localhost:11434/api/chat
{
  "model": "phi3:mini",
  "messages": [{"role": "user", "content": "Hello"}]
}
```

**OpenAI-Compatible Endpoints** (LM Studio, vLLM):
```bash
# List models
GET http://localhost:1234/v1/models

# Chat completion
POST http://localhost:1234/v1/chat/completions
{
  "model": "phi-3-mini",
  "messages": [{"role": "user", "content": "Hello"}],
  "temperature": 0.7
}
```

---

## Additional Resources

- **Ollama Documentation**: https://github.com/ollama/ollama/blob/main/docs/api.md
- **LM Studio**: https://lmstudio.ai/docs
- **Tailscale Setup**: https://tailscale.com/kb/1017/install
- **STING LLM Architecture**: See `docs/platform/architecture/ai-ml-architecture.md`
- **Model Registry**: https://ollama.ai/library (Ollama models)
- **HuggingFace Models**: https://huggingface.co/models (for LM Studio)

---

## Quick Reference

| Task | Command |
|------|---------|
| Install Ollama (Linux) | `curl -fsSL https://ollama.ai/install.sh \| sudo sh` |
| Start Ollama | `ollama serve` |
| Pull model | `ollama pull phi3:mini` |
| List models | `ollama list` |
| Test Ollama | `curl http://localhost:11434/api/tags` |
| Check STING LLM status | `./manage_sting.sh llm-status` |
| View External AI logs | `./manage_sting.sh logs external-ai` |
| View Bee logs | `./manage_sting.sh logs chatbot` |
| Restart LLM services | `./manage_sting.sh restart external-ai chatbot` |

---

**Need Help?**

- Check the [Troubleshooting](#troubleshooting) section above
- View logs: `./manage_sting.sh logs external-ai chatbot`
- Create diagnostic bundle: `./manage_sting.sh buzz collect --llm-focus`
- Open an issue: https://github.com/anthropics/sting-ce/issues