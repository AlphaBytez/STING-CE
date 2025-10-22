# STING-CE Fresh Installation Guide

## Prerequisites

1. **Docker Desktop** installed and running
2. **Python 3.8+** installed
3. **Internet connectivity** for downloading Docker images
4. **Hugging Face account** with API token (optional but recommended)
5. **At least 20GB free disk space** (10GB for models, 10GB for Docker images)

## Installation Steps

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-repo/STING-CE.git
cd STING-CE/STING
```

### Step 2: Download LLM Models (REQUIRED)
Before running the installer, you MUST download the LLM models:

```bash
# For testing/development (recommended - ~5GB)
./download_small_models.sh

# OR for production use (~15GB)
./download_optimized_models.sh
```

Models will be downloaded to: `~/Downloads/llm_models/`

### Step 3: Set Hugging Face Token (Optional)
```bash
export HF_TOKEN="your_huggingface_token_here"
```

### Step 4: Run the Installer
```bash
./manage_sting.sh install
```

## What the Installer Does

1. **Checks Prerequisites**
   - Verifies Docker is running
   - Checks network connectivity
   - Verifies LLM models are pre-downloaded

2. **Builds Docker Images**
   - Creates base images for all services
   - Configures networking and volumes

3. **Starts Core Services**
   - PostgreSQL database
   - Vault for secrets management
   - Kratos for authentication
   - Frontend and backend services

4. **Configures LLM Services**
   - On macOS: Starts native Metal-accelerated service
   - On Linux: Starts Docker-based LLM services
   - Uses pre-downloaded models (no download during install)

## Troubleshooting

### Network Issues
If you see DNS resolution errors:
1. Check your internet connection
2. Check Docker's DNS settings
3. Restart Docker Desktop
4. Try using a different DNS server

### Model Download Issues
If models fail to download:
1. Ensure you have a valid HF_TOKEN
2. Check disk space in `~/Downloads/`
3. Try downloading models manually
4. Check firewall/proxy settings

### Installation Hangs
If installation appears stuck:
1. Check `~/.sting-ce/logs/manage_sting.log`
2. Ensure models were pre-downloaded
3. Check Docker container logs
4. Verify no conflicting services on required ports

## Post-Installation

After successful installation:
1. Access the frontend at: https://localhost:8443
2. Register a new account
3. Check service status: `./manage_sting.sh status`

## Required Ports

Ensure these ports are available:
- 8443: Frontend
- 5050: Backend API
- 5432: PostgreSQL
- 8200: Vault
- 8080: LLM Gateway
- 8081: Chatbot Service
- 8086: Native LLM Service (macOS)

## Default Model Configuration

The system now defaults to TinyLlama for better compatibility:
- Model: TinyLlama-1.1B-Chat
- Path: ~/Downloads/llm_models/TinyLlama-1.1B-Chat
- Size: ~2.2GB

You can change models after installation using:
```bash
./sting-llm load <model_name>
```