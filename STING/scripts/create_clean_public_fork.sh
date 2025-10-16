#!/usr/bin/env bash

#################################################
# STING-CE Clean Public Fork Creation Script
# Creates a minimal, clean public repository
# Removes deprecated services and sensitive files
#################################################

set -euo pipefail

# Configuration
SOURCE_DIR="/mnt/c/DevWorld/STING-CE/STING"
TARGET_DIR="/mnt/c/DevWorld/STING-CE-Public"
GITHUB_USERNAME="${GITHUB_USERNAME:-your-github-username}"
GITHUB_REPO="${GITHUB_REPO:-sting-ce}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $*"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*"
}

log_section() {
    echo ""
    echo -e "${CYAN}========== $* ==========${NC}"
    echo ""
}

# Service categorization
declare -A SERVICE_STATUS=(
    # Core Services (KEEP)
    ["app"]="core"
    ["frontend"]="core"
    ["kratos"]="core"
    ["vault"]="core"
    ["db"]="core"
    ["redis"]="core"
    ["mailpit"]="core"

    # AI Services (KEEP - Core to STING)
    ["chatbot"]="core"
    ["external_ai_service"]="core"
    ["knowledge_service"]="core"
    ["llm_service"]="core"
    ["public_bee"]="core"
    ["chroma"]="core"

    # Workers (KEEP)
    ["report_worker"]="core"
    ["profile_sync_worker"]="core"

    # Optional Services (KEEP but can be disabled)
    ["nectar_worker"]="optional"
    ["messaging_service"]="optional"

    # Monitoring (OPTIONAL - Remove for minimal)
    ["loki"]="remove"
    ["grafana"]="remove"
    ["promtail"]="remove"
    ["observability"]="remove"

    # VPN (OPTIONAL - Remove for public)
    ["headscale"]="remove"

    # Deprecated (REMOVE)
    ["supertokens"]="remove"
    ["archive"]="remove"
    ["sting_installer"]="remove"
    ["dist"]="remove"
    ["build"]="remove"
)

# Check if target already exists
if [ -d "$TARGET_DIR" ]; then
    log_warning "Target directory $TARGET_DIR already exists!"
    read -p "Do you want to remove it and start fresh? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Removing existing directory..."
        rm -rf "$TARGET_DIR"
    else
        log_error "Aborting. Please rename or remove $TARGET_DIR first."
        exit 1
    fi
fi

log_section "Creating Clean Public Fork of STING-CE"
log_info "Source: $SOURCE_DIR"
log_info "Target: $TARGET_DIR"

# Step 1: Create initial copy with basic exclusions
log_section "Step 1: Initial Copy"
rsync -av --progress \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='venv' \
    --exclude='.venv' \
    --exclude='node_modules' \
    "$SOURCE_DIR/" "$TARGET_DIR/"

cd "$TARGET_DIR"

# Step 2: Remove deprecated and unnecessary directories
log_section "Step 2: Removing Deprecated Components"

# Remove entire directories
REMOVE_DIRS=(
    "archive"
    "sting_installer"
    "sting_installer.egg-info"
    "dist"
    "build"
    "observability"
    "grafana-dashboards"
    "scripts/archive"
    "scripts/troubleshooting/dangerzone"
    "web-setup/venv"
)

for dir in "${REMOVE_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        log_info "Removing $dir..."
        rm -rf "$dir"
        log_success "Removed $dir"
    fi
done

# Step 3: Clean sensitive and test files
log_section "Step 3: Cleaning Sensitive Files"

# Remove sensitive files
find . -name "*.key" -type f -delete 2>/dev/null || true
find . -name "*.pem" -type f -delete 2>/dev/null || true
find . -name "*.crt" -type f -delete 2>/dev/null || true
find . -name "*.env" -type f -delete 2>/dev/null || true
find . -name ".env.*" -type f -delete 2>/dev/null || true
find . -name "*secret*" -type f -delete 2>/dev/null || true
find . -name "*token*.py" -type f -delete 2>/dev/null || true
find . -name "debug-*.sh" -type f -delete 2>/dev/null || true
find . -name "cookies*.txt" -type f -delete 2>/dev/null || true
find . -name "*_cookies.txt" -type f -delete 2>/dev/null || true
find . -name "flow*.json" -type f -delete 2>/dev/null || true

# Remove test/debug files
rm -f test-*.html 2>/dev/null || true
rm -rf tests/screenshots/ 2>/dev/null || true
rm -f .claude/settings.local.json 2>/dev/null || true
rm -f conf/.init.env 2>/dev/null || true
rm -f conf/config.yml.old-backup-* 2>/dev/null || true

# Remove backup files
find . -name "*.backup" -type f -delete 2>/dev/null || true
find . -name "*.bak" -type f -delete 2>/dev/null || true
find . -name "*.old" -type f -delete 2>/dev/null || true

log_success "Sensitive files cleaned"

# Step 4: Clean SuperTokens references
log_section "Step 4: Removing SuperTokens References"

# Remove SuperTokens specific files
rm -f scripts/troubleshooting/*/fix_supertokens*.sh 2>/dev/null || true
rm -f scripts/troubleshooting/*/test_supertokens*.py 2>/dev/null || true

# Files that need SuperTokens references cleaned
FILES_TO_CLEAN=(
    "conf/config_loader.py"
    "conf/config.yml.default"
    "lib/services.sh"
    "lib/installation.sh"
    "vault/scripts/init_secrets.py"
)

for file in "${FILES_TO_CLEAN[@]}"; do
    if [ -f "$file" ]; then
        log_info "Cleaning SuperTokens from $file..."
        # Comment out or remove SuperTokens references
        sed -i 's/.*supertokens.*/#&  # DEPRECATED/gI' "$file"
        sed -i 's/.*SuperTokens.*/#&  # DEPRECATED/gI' "$file"
    fi
done

log_success "SuperTokens references cleaned"

# Step 5: Create minimal docker-compose.yml
log_section "Step 5: Creating Minimal Docker Compose"

# Backup original
cp docker-compose.yml docker-compose.full.yml

# Create a script to generate minimal docker-compose
cat > generate_minimal_compose.py << 'PYTHON_SCRIPT'
#!/usr/bin/env python3
import yaml

# Load the full compose file
with open('docker-compose.full.yml', 'r') as f:
    compose = yaml.safe_load(f)

# Services to keep for minimal setup
KEEP_SERVICES = [
    # Core
    'vault', 'db', 'kratos', 'app', 'frontend', 'redis',
    # Auth & Email
    'mailpit',
    # AI Core
    'chroma', 'knowledge', 'external-ai', 'chatbot', 'public-bee',
    'llm-gateway-proxy',
    # Workers
    'report-worker', 'profile-sync-worker',
    # Utils
    'utils', 'messaging'
]

# Remove optional/monitoring services
REMOVE_SERVICES = [
    'loki', 'grafana', 'promtail', 'headscale', 'nectar-worker',
    'registry', 'log-forwarder'
]

# Filter services
filtered_services = {}
for service, config in compose.get('services', {}).items():
    # Check if service should be kept
    keep = False
    for keeper in KEEP_SERVICES:
        if keeper in service:
            keep = True
            break

    # Check if service should be removed
    for remover in REMOVE_SERVICES:
        if remover in service:
            keep = False
            break

    if keep:
        filtered_services[service] = config
        # Remove references to removed services
        if 'depends_on' in config:
            config['depends_on'] = [
                dep for dep in config['depends_on']
                if not any(rem in dep for rem in REMOVE_SERVICES)
            ]

# Update compose structure
compose['services'] = filtered_services

# Remove unused volumes
if 'volumes' in compose:
    used_volumes = set()
    for service in filtered_services.values():
        if 'volumes' in service:
            for vol in service['volumes']:
                if ':' in vol:
                    vol_name = vol.split(':')[0]
                    if not vol_name.startswith('/') and not vol_name.startswith('.'):
                        used_volumes.add(vol_name)

    filtered_volumes = {
        vol: config for vol, config in compose['volumes'].items()
        if vol in used_volumes or 'vault' in vol or 'postgres' in vol or 'redis' in vol
    }
    compose['volumes'] = filtered_volumes

# Write minimal compose
with open('docker-compose.yml', 'w') as f:
    yaml.dump(compose, f, default_flow_style=False, sort_keys=False)

print("✓ Created minimal docker-compose.yml")
PYTHON_SCRIPT

python3 generate_minimal_compose.py
rm generate_minimal_compose.py

log_success "Created minimal docker-compose.yml"

# Step 6: Update default configuration
log_section "Step 6: Updating Default Configuration"

# Create clean config.yml.default
cat > conf/config.yml.default << 'CONFIG_END'
# STING-CE Configuration
# Community Edition - Minimal Setup

# System Configuration
system:
  domain: localhost
  protocol: https
  ports:
    frontend: 8443
    api: 5050
    kratos: 4433

# Edition
edition:
  type: ce  # Community Edition
  hide_enterprise_ui: true

# Core Application
application:
  env: production
  debug: false
  host: 0.0.0.0
  port: 5050
  install_dir: "${INSTALL_DIR}"
  models_dir: "${MODELS_DIR:-${INSTALL_DIR}/models}"
  ssl:
    enabled: true
    cert_dir: "${INSTALL_DIR}/certs"

# Database
database:
  host: db
  port: 5432
  name: sting_app
  user: postgres
  connection_timeout: 30
  max_connections: 100

# Security
security:
  authentication:
    aal2_session_timeout: "8h"
  message_pii_protection:
    enabled: true
    serialization:
      enabled: true
      redis_db: 3
      cache_ttl:
        default: 300
        on_error: 3600

# Vault Configuration
vault:
  host: vault
  port: 8200
  scheme: http
  auth_method: token
  kv_mount: kv
  transit_mount: transit

# Authentication (Kratos)
kratos:
  public_url: https://localhost:4433
  admin_url: http://kratos:4434
  browser_url: https://localhost:8443

# Redis Cache
redis:
  host: redis
  port: 6379
  databases:
    cache: 0
    sessions: 1
    queue: 2
    pii_cache: 3

# Email Configuration
email:
  mode: "${EMAIL_MODE:-development}"
  development:
    provider: "mailpit"
    host: "mailpit"
    port: 1025
  production:
    provider: "${SMTP_PROVIDER:-smtp}"
    host: "${SMTP_HOST}"
    port: "${SMTP_PORT:-587}"
    use_tls: true
    username: "${SMTP_USERNAME}"
    from_address: "${SMTP_FROM_ADDRESS}"

# AI Services Configuration
ai:
  # Default LLM Configuration
  llm:
    enabled: true
    provider: "${LLM_PROVIDER:-ollama}"
    endpoint: "${LLM_ENDPOINT:-http://host.docker.internal:11434}"
    model: "${LLM_MODEL:-llama3.2}"
    timeout: 120

  # Knowledge Base (ChromaDB)
  knowledge:
    enabled: true
    host: chroma
    port: 8000
    collection: "sting_knowledge"

  # BEE Assistant
  bee:
    enabled: true
    name: "B.E.E."
    description: "Bee Enhanced Entity - Your AI Security Assistant"
    personality: "helpful"

# Feature Flags
features:
  passwordless: true
  webauthn: true
  mfa: true
  magic_links: true
  audit_logging: true

# Logging
logging:
  level: "${LOG_LEVEL:-INFO}"
  format: "json"
  output: "stdout"
CONFIG_END

log_success "Created minimal config.yml.default"

# Step 7: Clean config_loader.py
log_section "Step 7: Cleaning Config Loader"

if [ -f "conf/config_loader.py" ]; then
    # Create a backup
    cp conf/config_loader.py conf/config_loader.py.original

    # Remove SuperTokens and other deprecated service configurations
    python3 << 'CLEAN_LOADER'
import re

with open('conf/config_loader.py', 'r') as f:
    content = f.read()

# Remove or comment SuperTokens sections
content = re.sub(r'.*supertokens.*\n', '', content, flags=re.IGNORECASE)
content = re.sub(r'.*SUPERTOKENS.*\n', '', content, flags=re.IGNORECASE)

# Remove Headscale references
content = re.sub(r'.*headscale.*\n', '', content, flags=re.IGNORECASE)

# Remove monitoring stack references (but keep basic logging)
content = re.sub(r'.*loki.*\n', '', content, flags=re.IGNORECASE)
content = re.sub(r'.*grafana.*\n', '', content, flags=re.IGNORECASE)
content = re.sub(r'.*promtail.*\n', '', content, flags=re.IGNORECASE)

with open('conf/config_loader.py', 'w') as f:
    f.write(content)

print("✓ Cleaned config_loader.py")
CLEAN_LOADER

    # Remove backup
    rm conf/config_loader.py.original
fi

log_success "Config loader cleaned"

# Step 8: Create repository documentation
log_section "Step 8: Creating Repository Documentation"

# Create comprehensive .gitignore
cat > .gitignore << 'GITIGNORE_END'
# Security - Never commit
*.key
*.pem
*.crt
*.env
.env.*
secrets/
credentials/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
dist/
*.egg-info/
venv/
.venv/

# Node
node_modules/
npm-debug.log*
yarn-error.log*

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Docker
docker-compose.override.yml

# Logs
logs/
*.log

# Testing
.coverage
.pytest_cache/
htmlcov/

# Local config
*.local
config.local.yml

# Models
*.gguf
*.bin
*.safetensors
models/

# Temp
tmp/
temp/
*.tmp
*.bak
*.backup
GITIGNORE_END

# Create LICENSE
cat > LICENSE << 'LICENSE_END'
MIT License

Copyright (c) 2024 STING-CE Community

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
LICENSE_END

# Create minimal README
cat > README.md << 'README_END'
# STING-CE (Community Edition)

> **Secure Trusted Intelligence and Networking Guardian**

A comprehensive security and authentication platform with AI-powered assistance.

## Features

- 🔐 **Multi-Factor Authentication** - TOTP, WebAuthn, Magic Links
- 🤖 **AI Assistant (B.E.E.)** - Intelligent security companion
- 🚀 **Passwordless Authentication** - Modern, secure auth flows
- 📧 **Email Verification** - Built-in email handling
- 🔒 **Vault Integration** - Secure secrets management
- 📊 **Audit Logging** - Comprehensive security logs
- 🐳 **Docker-Based** - Easy deployment and scaling

## Quick Start

### Prerequisites

- Docker & Docker Compose
- 8GB RAM minimum
- Ubuntu 20.04+ or similar Linux distribution

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/sting-ce.git
cd sting-ce

# Run the installer
./install_sting.sh

# Start services
./manage_sting.sh start

# Access the application
# Frontend: https://localhost:8443
# API: https://localhost:5050
```

### Configuration

1. Copy the example configuration:
   ```bash
   cp conf/config.yml.default conf/config.yml
   ```

2. Edit `conf/config.yml` with your settings

3. For production, set environment variables for sensitive values

## Documentation

See the `/docs` directory for detailed documentation:

- [Installation Guide](docs/INSTALL.md)
- [Configuration](docs/CONFIG.md)
- [API Documentation](docs/API.md)
- [Security](docs/SECURITY.md)

## Development

```bash
# Run in development mode
./manage_sting.sh start --dev

# Run tests
./scripts/run_tests.sh

# Check logs
./manage_sting.sh logs
```

## Community

- Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/sting-ce/issues)
- Discussions: [GitHub Discussions](https://github.com/YOUR_USERNAME/sting-ce/discussions)

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## Security

For security issues, please see [SECURITY.md](SECURITY.md).
README_END

# Create CONTRIBUTING.md
cat > CONTRIBUTING.md << 'CONTRIBUTING_END'
# Contributing to STING-CE

Thank you for your interest in contributing!

## How to Contribute

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Code Style

- Python: Follow PEP 8
- JavaScript: ESLint configuration
- Docker: Best practices for layers

## Testing

Run tests before submitting:
```bash
./scripts/run_tests.sh
```

## Pull Request Process

1. Update documentation
2. Add tests for new features
3. Ensure all tests pass
4. Update CHANGELOG.md
CONTRIBUTING_END

# Create SECURITY.md
cat > SECURITY.md << 'SECURITY_END'
# Security Policy

## Reporting Security Issues

**DO NOT** create public issues for security vulnerabilities.

Email: security@sting-ce.org

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x     | ✅ Active          |
| < 1.0   | ❌ Not Supported   |

## Security Best Practices

1. Use HTTPS in production
2. Enable MFA for admins
3. Regular security updates
4. Monitor audit logs
5. Use environment variables for secrets
SECURITY_END

log_success "Documentation created"

# Step 9: Create test preparation script
log_section "Step 9: Creating VM Test Script"

cat > test_in_vm.sh << 'VM_TEST_SCRIPT'
#!/bin/bash

#################################################
# STING-CE VM Testing Script
# Prepares and tests installation in clean VM
#################################################

set -e

echo "STING-CE VM Test Preparation"
echo "============================"
echo ""
echo "This script helps test STING-CE in a clean Ubuntu VM"
echo ""

# Check system requirements
echo "Checking system..."
echo "- OS: $(lsb_release -d | cut -f2)"
echo "- RAM: $(free -h | awk '/^Mem:/ {print $2}')"
echo "- Disk: $(df -h / | awk 'NR==2 {print $4}' ) available"
echo "- Docker: $(docker --version 2>/dev/null || echo 'Not installed')"
echo ""

# Install dependencies if needed
if ! command -v docker &> /dev/null; then
    echo "Docker not found. Install it? (y/n)"
    read -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker $USER
        echo "Docker installed. Please logout and login again."
        exit 0
    fi
fi

# Test installation
echo "Ready to test STING-CE installation."
echo ""
echo "Steps:"
echo "1. Run: ./install_sting.sh"
echo "2. Follow the setup wizard"
echo "3. Access https://localhost:8443"
echo ""
echo "Press any key to start installation..."
read -n 1

# Run installer
./install_sting.sh
VM_TEST_SCRIPT

chmod +x test_in_vm.sh

log_success "VM test script created"

# Step 10: Calculate final size
log_section "Step 10: Final Statistics"

# Initialize git repo (no commit yet)
git init -q

# Show statistics
ORIGINAL_SIZE=$(du -sh "$SOURCE_DIR" | cut -f1)
FINAL_SIZE=$(du -sh "$TARGET_DIR" | cut -f1)
FILE_COUNT=$(find . -type f | wc -l)
DIR_COUNT=$(find . -type d | wc -l)

echo "Repository Statistics:"
echo "====================="
echo "Original size: $ORIGINAL_SIZE"
echo "Final size: $FINAL_SIZE"
echo "Files: $FILE_COUNT"
echo "Directories: $DIR_COUNT"
echo ""

# List remaining services
echo "Included Services:"
echo "=================="
ls -d */ 2>/dev/null | grep -E "(app|frontend|vault|kratos|chatbot|knowledge|llm_service)" | sed 's|/||g' | sort | sed 's/^/  ✓ /'
echo ""

echo "Removed Components:"
echo "==================="
echo "  ✗ SuperTokens (deprecated auth)"
echo "  ✗ Archive directories"
echo "  ✗ Monitoring stack (Loki/Grafana/Promtail)"
echo "  ✗ Headscale VPN"
echo "  ✗ Build artifacts"
echo "  ✗ Virtual environments"
echo "  ✗ Sensitive files (.env, .key, .pem)"
echo ""

# Final message
log_section "✅ Clean Fork Created Successfully!"

echo "📁 Location: $TARGET_DIR"
echo "📊 Size: $FINAL_SIZE (reduced from $ORIGINAL_SIZE)"
echo ""
echo "Next Steps:"
echo "==========="
echo ""
echo "1. TEST IN VM FIRST:"
echo "   cd $TARGET_DIR"
echo "   # Copy to Ubuntu VM and run:"
echo "   ./test_in_vm.sh"
echo ""
echo "2. After successful VM test:"
echo "   cd $TARGET_DIR"
echo "   git add ."
echo '   git commit -m "Initial commit: STING-CE Community Edition"'
echo "   git remote add origin https://github.com/$GITHUB_USERNAME/$GITHUB_REPO.git"
echo "   git push -u origin main"
echo ""
echo "3. GitHub Setup:"
echo "   - Enable Issues & Discussions"
echo "   - Add topics: security, authentication, mfa, docker"
echo "   - Create v1.0.0-ce release"
echo ""
echo "⚠️  IMPORTANT: Test thoroughly in VM before making public!"
echo ""