# STING Platform Installation Guide

## System Requirements

### Minimum Requirements
- **Operating System**: macOS 11+ (Apple Silicon recommended) or Linux (Ubuntu 20.04+)
- **Memory**: 16GB RAM minimum (32GB+ recommended for production)
- **Storage**: 50GB free disk space (models require additional 10-50GB)
- **Docker**: Docker Desktop 4.0+ with Docker Compose
- **Network**: Internet connection for initial setup and model downloads

### Recommended Configuration

#### Small Deployment (1-5 users, <1000 documents)
- **CPU**: Apple M1/M2/M3 or Intel/AMD with 8+ cores
- **Memory**: 16GB RAM (optimized allocation uses 75% efficiently)
- **Storage**: 100GB SSD
- **Network**: 100 Mbps connection
- **Docker Resources**: Optimized limits prevent resource conflicts

#### Medium Deployment (5-20 users, 1000-10000 documents)  
- **CPU**: Apple M2 Pro/M3 or Intel/AMD with 12+ cores
- **Memory**: 32GB RAM (allows headroom for growth)
- **Storage**: 250GB SSD (NVMe preferred)
- **Network**: 1 Gbps connection
- **Additional**: Consider dedicated ChromaDB instance

#### Large Deployment (20+ users, 10000+ documents)
- **CPU**: Apple M2 Max/M3 Max or Intel/AMD with 16+ cores
- **Memory**: 64GB+ RAM (enables multiple knowledge workers)
- **Storage**: 500GB+ SSD with high IOPS
- **Network**: 10 Gbps connection  
- **Additional**: Redis cluster, separate knowledge processing workers
- **GPU**: Metal Performance Shaders (macOS) or CUDA-compatible (Linux)

## Pre-Installation Setup

### Minimal Requirements

STING installer is designed to **automatically handle most dependencies**. You only need:

**Required (Manual Install):**
- **Git**: For cloning the repository
- **Internet Connection**: For downloading Docker and dependencies

**Auto-Installed by STING:**
- Docker Engine (apt-based, replaces snap if detected)
- Docker Compose plugin
- jq (JSON processor)
- All Python dependencies (runs in containers)

### 1. Install Git (if not already installed)

**macOS:**
```bash
# Install Xcode Command Line Tools (includes git)
xcode-select --install

# OR install via Homebrew
brew install git
```

**Linux (Ubuntu/Debian):**
```bash
# Update system packages
sudo apt update

# Install git
sudo apt install -y git

# OPTIONAL: Install curl (usually pre-installed)
sudo apt install -y curl
```

**Note:** The STING installer will automatically:
- Detect and fix snap Docker installations
- Install proper apt-based Docker if missing
- Install Docker Compose plugin
- Install jq and other utilities
- Handle all Python dependencies in containers

### 2. Clone Repository

```bash
# Clone STING repository
git clone https://github.com/your-org/sting-platform.git
cd sting-platform

# Verify you're in the correct directory
ls -la  # Should show manage_sting.sh, conf/, frontend/, etc.
```

### 3. Run Installation

The STING installer handles all system preparation automatically:

```bash
# Run the installer (handles all dependencies automatically)
sudo bash install_sting.sh

# The installer will automatically:
# - Detect and fix snap Docker (replaces with apt version)
# - Install Docker if not present
# - Install required utilities (jq, etc.)
# - Create installation directory (/opt/sting-ce or ~/.sting-ce)
# - Generate configuration files
# - Build and start all services
```

**Expected Output:**
```
✓ Detected snap Docker - automatically replacing with apt version
✓ Docker Engine installed successfully
✓ System dependencies installed
✓ Configuration files generated
✓ Network connectivity confirmed
✓ Disk space sufficient (XX GB available)
```

## AI Model Setup

### Option 1: Ollama (Recommended)

1. Install Ollama from [ollama.com](https://ollama.com)
2. Pull recommended models:
   ```bash
   ollama pull phi3:mini
   ollama pull deepseek-r1
   ```

### Option 2: External AI Providers

Configure API keys in the External AI settings for:
- OpenAI
- Anthropic Claude
- Google Gemini
- Other providers

### Option 3: Legacy Models (Optional)

HuggingFace tokens are only needed for legacy model support (phi3, llama3, zephyr).
The modern Ollama/External AI stack does not require HuggingFace tokens.

### 2. Configure Token

```bash
# Interactive token setup
./setup_hf_token.sh

# Follow prompts to enter your HuggingFace token
# Token will be securely stored in HashiCorp Vault
```

**Alternative Manual Setup:**
```bash
# Set environment variable
export HF_TOKEN="hf_your_token_here"

# Add to your shell profile for persistence
echo 'export HF_TOKEN="hf_your_token_here"' >> ~/.bashrc
source ~/.bashrc
```

## Installation Process

### 1. Full Installation

```bash
# Install STING with debug output
./install_sting.sh install --debug

# Installation process includes:
# - Environment validation
# - Docker network creation
# - Service image building
# - Configuration generation
# - Database initialization
# - Model preparation
# - Service startup
```

**Installation Progress:**
```
[1/8] Validating environment...                ✓
[2/8] Building Docker images...                ✓
[3/8] Initializing databases...                ✓
[4/8] Configuring services...                  ✓
[5/8] Starting core services...                ✓
[6/8] Setting up authentication...             ✓
[7/8] Preparing AI models...                   ✓
[8/8] Final health checks...                   ✓

🎉 STING Platform installed successfully!
```

### 2. Service Startup

```bash
# Start all services
./manage_sting.sh start

# Check service status
./manage_sting.sh status

# View logs (optional)
./manage_sting.sh logs
```

### 3. CLI Installation (Optional)

```bash
# Install msting command globally
sudo ln -sf $(pwd)/sting_installer/msting /usr/local/bin/msting

# Verify installation
msting --help
```

## Post-Installation Configuration

### 1. Access Verification

**Test Frontend Access:**
```bash
# Open browser to frontend
open https://localhost:3010  # Production
# or
open https://localhost:8443  # Development

# Accept self-signed certificate warning
```

**Test API Access:**
```bash
# Check API health
curl -k https://localhost:5050/api/auth/health

# Expected response: {"status": "healthy", "timestamp": "..."}
```

### 2. Create First User

1. Navigate to `https://localhost:3010`
2. Click "Register" to create your first account
3. Enter email and password
4. Complete email verification (check Mailpit at `http://localhost:8025`)
5. Log in to access the dashboard

### 3. Test Chatbot

1. Navigate to the Chat interface
2. Send a test message: "Hello, what is STING?"
3. Verify Bee responds appropriately
4. Check that Phi-3 model is being used (no reasoning artifacts)

## Advanced Configuration

### 1. Custom Model Configuration

**Edit Configuration:**
```bash
# Edit main configuration file
vim conf/config.yml

# Key sections to customize:
# - llm_service.models: Enable/disable specific models
# - chatbot.model: Change default model
# - performance.profile: Adjust for your hardware
```

**Example Customization:**
```yaml
# conf/config.yml
llm_service:
  default_model: phi3
  models:
    phi3:
      enabled: true
      max_tokens: 4096
    deepseek-1.5b:
      enabled: false  # Disable to save memory
```

### 2. Database Configuration

**PostgreSQL Access:**
```bash
# Connect to database directly
psql -h localhost -p 5433 -U postgres -d sting_app

# View database credentials
cat /Users/$(whoami)/.sting-ce/env/db.env
```

### 3. SSL Certificate Setup

**Development (Self-Signed):**
```bash
# Certificates are auto-generated during installation
# Location: ~/.sting-ce/certs/
ls -la ~/.sting-ce/certs/
```

**Production (Let's Encrypt):**
```bash
# Update configuration for your domain
vim conf/config.yml

# Set your domain and email
application:
  ssl:
    domain: "your-domain.com"
    email: "admin@your-domain.com"

# Reinstall with new configuration
./manage_sting.sh restart
```

## Resource Optimization

### Docker Resource Allocation

STING includes optimized Docker resource limits designed for the 16GB minimum requirement:

```yaml
# Optimized allocations (docker-compose.yml)
knowledge:     3GB memory, 1.5 CPU    # Increased for better performance  
chroma:        2GB memory, 1.0 CPU    # Vector operations need dedicated resources
app:           1GB memory, 1.0 CPU    # Core application
database:      1GB memory, 1.0 CPU    # PostgreSQL
frontend:      512MB memory, 0.5 CPU  # Nginx + React
vault:         512MB memory, 0.25 CPU # Secrets management
messaging:     256MB memory, 0.25 CPU # Message queue
redis:         512MB memory, 0.5 CPU  # Caching
```

**Total Resource Usage:**
- **Reserved**: ~4GB (25% of 16GB minimum)
- **Maximum**: ~12GB (75% of 16GB minimum)
- **System Buffer**: 4GB for OS and other processes

### Performance Monitoring

**Check Resource Usage:**
```bash
# Monitor all containers
docker stats --no-stream

# Check specific service
docker stats sting-ce-knowledge --no-stream

# View resource limits
docker inspect sting-ce-knowledge | grep -A 10 "Memory"
```

**Resource Scaling Recommendations:**

**When to increase Knowledge Service (3GB → 4GB):**
- Processing >1000 documents daily
- Multiple concurrent users uploading
- Complex document formats (large PDFs)

**When to increase ChromaDB (2GB → 3GB):**
- Vector database >10,000 documents  
- Frequent similarity searches
- Multiple knowledge bases active

**When to separate ChromaDB:**
```yaml
# For deployments >50k documents
chroma-production:
  image: chromadb/chroma:latest
  deploy:
    resources:
      limits:
        memory: 8G
        cpus: '4.0'
  volumes:
    - chroma-production:/chroma/chroma
```

### Knowledge System Optimization

**ChromaDB Configuration:**
- Uses `all-MiniLM-L6-v2` model (90MB, 384 dimensions)
- Efficient semantic search with minimal memory overhead
- Scales well up to 100,000 documents per collection

**Document Processing:**
- **Chunking**: 1000-1500 characters with 200-300 overlap
- **Background Processing**: Queue-based uploads prevent memory spikes  
- **Incremental Updates**: Only processes changed documents
- **Batch Uploads**: Process multiple documents efficiently

**Performance Metrics:**
- **Search Response**: <2 seconds for most queries
- **Document Upload**: <30 seconds per 10MB file  
- **Bee Response**: <5 seconds with knowledge context
- **Memory Growth**: ~1MB per document indexed

### Hardware Upgrade Guidelines

**Memory Pressure Indicators:**
- Container restarts due to OOM
- High swap usage (>2GB)
- Slow search responses (>5 seconds)
- Upload timeouts

**CPU Bottleneck Signs:**
- High load average (>CPU cores)
- Slow document processing
- Delayed background tasks
- UI responsiveness issues

**Storage Optimization:**
- Use SSD for ChromaDB persistence
- Regular cleanup of old logs
- Monitor knowledge storage growth
- Consider compression for archived data

### Scaling Architecture

**Horizontal Scaling Options:**

```yaml
# Separate knowledge processing workers
knowledge-worker:
  build: ./knowledge_service
  environment:
    - WORKER_MODE=true
    - WORKER_QUEUE=document_processing
  deploy:
    replicas: 3
    resources:
      limits:
        memory: 2G
        cpus: '1.0'

# Dedicated search service  
knowledge-search:
  build: ./knowledge_service
  environment:
    - SERVICE_MODE=search_only
  deploy:
    resources:
      limits:
        memory: 4G
        cpus: '2.0'
```

This optimized configuration ensures STING runs efficiently on minimum specification systems while providing clear upgrade paths for organizational growth.

## Troubleshooting

### Common Issues

**1. Docker Service Failures**
```bash
# Check Docker status
docker ps -a

# Restart Docker Desktop (macOS)
killall Docker && open -a Docker

# Check Docker logs
docker compose -f ~/.sting-ce/docker-compose.yml logs [service]
```

**2. Port Conflicts**
```bash
# Check port usage
lsof -i :3010  # Frontend
lsof -i :5050  # API
lsof -i :8086  # LLM Service

# Kill conflicting processes
sudo kill -9 [PID]
```

**3. Model Loading Issues**
```bash
# Check model status
./sting-llm status

# Manually download models
./sting-llm download phi3

# Check available disk space
df -h ~/.sting-ce/models
```

**4. Memory Issues**
```bash
# Check memory usage
./sting-llm memory

# Reduce loaded models
vim conf/config.yml
# Set model_lifecycle.max_loaded_models: 1

# Restart LLM service
./sting-llm restart
```

### Log Analysis

**Service Logs:**
```bash
# View all logs
./manage_sting.sh logs

# View specific service logs
./manage_sting.sh logs chatbot
./manage_sting.sh logs llm-gateway
./manage_sting.sh logs frontend

# Follow logs in real-time
./manage_sting.sh logs -f
```

**Log Locations:**
```
~/.sting-ce/logs/
├── manage_sting.log      # Installation and management
├── llm-gateway.log       # AI model service
├── chatbot.log           # Bee chatbot service
└── frontend.log          # React application
```

### Health Diagnostics

```bash
# Comprehensive health check
./manage_sting.sh health

# Individual service health
curl -k https://localhost:5050/api/auth/health
curl -k http://localhost:8086/health
curl -k http://localhost:8888/health
```

### Recovery Procedures

**Soft Reset:**
```bash
# Restart all services
./manage_sting.sh restart

# Regenerate configuration
./manage_sting.sh regenerate-config
```

**Full Reset:**
```bash
# Stop services
./manage_sting.sh stop

# Remove containers (preserves data)
docker compose -f ~/.sting-ce/docker-compose.yml down

# Restart installation
./manage_sting.sh start
```

**Complete Uninstall:**
```bash
# Remove all data (DESTRUCTIVE)
./manage_sting.sh uninstall --force

# Remove installation directory
rm -rf ~/.sting-ce

# Reinstall from scratch
./install_sting.sh install
```

## Performance Optimization

### 1. Model Selection

**For Limited Resources (8-16GB RAM):**
```yaml
# Use smaller models
llm_service:
  default_model: deepseek-1.5b
  max_loaded_models: 1
```

**For Ample Resources (32GB+ RAM):**
```yaml
# Use enterprise models
llm_service:
  default_model: phi3
  max_loaded_models: 3
```

### 2. Hardware Acceleration

**macOS (Metal):**
```yaml
# Enabled by default
llm_service:
  hardware:
    device: "mps"
    precision: "fp16"
```

**Linux (CUDA):**
```yaml
# For NVIDIA GPUs
llm_service:
  hardware:
    device: "cuda"
    precision: "fp16"
```

### 3. Database Tuning

**PostgreSQL Configuration:**
```bash
# Edit PostgreSQL settings
vim ~/.sting-ce/conf/postgresql.conf

# Key settings for performance:
# shared_buffers = 256MB
# effective_cache_size = 1GB
# work_mem = 4MB
```

## Security Hardening

### 1. Production Deployment

**Change Default Passwords:**
```bash
# Generate new secrets
./manage_sting.sh regenerate-secrets

# Update database password
vim ~/.sting-ce/env/db.env
```

**Firewall Configuration:**
```bash
# Block unnecessary ports
sudo ufw enable
sudo ufw deny 5433  # PostgreSQL (internal only)
sudo ufw deny 8200  # Vault (admin only)
sudo ufw allow 443  # HTTPS
sudo ufw allow 80   # HTTP (redirect to HTTPS)
```

### 2. SSL/TLS Configuration

**Production Certificates:**
```bash
# Install certbot
sudo apt install certbot

# Generate Let's Encrypt certificate
sudo certbot certonly --standalone -d your-domain.com

# Update STING configuration
vim conf/config.yml
# Point to /etc/letsencrypt/live/your-domain.com/
```

This installation guide provides comprehensive coverage for deploying STING in both development and production environments. Follow the steps carefully and refer to the troubleshooting section if you encounter any issues.