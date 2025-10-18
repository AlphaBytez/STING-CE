# Installing STING Community Edition

## 🚀 Quick Start (Recommended)

STING now includes a beautiful web-based setup wizard for easy installation!

```bash
git clone https://github.com/AlphaBytez/STING-CE.git
cd STING-CE
./install_sting.sh
```

This will:
1. ✅ Check system dependencies
2. ✅ Launch the setup wizard at **http://localhost:8080**
3. ✅ Guide you through configuration in 7 easy steps
4. ✅ Install and start STING automatically

**Just open your browser to http://localhost:8080 and follow the wizard!** 🐝

---

## 📋 Installation Options

### Option 1: Web Setup Wizard (Recommended) ⭐

**Best for:** First-time users, VM deployments, visual configuration

```bash
./install_sting.sh          # Launch wizard (default)
```

The wizard provides a user-friendly interface for:
- 🏠 System configuration (hostname, timezone)
- 💾 Data disk setup (optional separate disk)
- 👤 Admin account creation (passwordless)
- 🤖 LLM backend configuration (Ollama, LM Studio, etc.)
- 📧 Email/SMTP settings (optional)
- 🔒 SSL/TLS configuration
- ✅ Review and apply

**Features:**
- ✨ Beautiful bee-themed UI
- ✅ Real-time configuration validation
- 🧪 Test LLM endpoints before installing
- 📊 Live installation progress with logs
- 🔐 Passwordless admin setup with magic links

### Option 2: CLI Installation (Advanced)

**Best for:** Automation, scripts, experienced users

```bash
./install_sting.sh --cli    # CLI mode
```

Or use the full management script directly:

```bash
./manage_sting.sh install
```

---

## 🎯 Prerequisites

- **OS:** Ubuntu 20.04+, macOS, or WSL2
- **Python:** 3.8+
- **Docker:** 20.10+
- **RAM:**
  - 4GB minimum (external LLM API only)
  - 16GB minimum (local LLM with small models)
  - 32GB+ recommended (local LLM production)
- **Disk:** 20GB base + 10-50GB per local LLM model
- **LLM Backend:** One of:
  - Ollama (recommended for self-hosting)
  - LM Studio
  - OpenAI/Anthropic/other API keys

> ⚠️ **Note for Traditional Server Deployments**
>
> STING's AI features require significantly more resources than typical web applications:
> - **Local LLM**: 16-32GB RAM, 8+ CPU cores (for data sovereignty)
> - **External API**: 4-8GB RAM, 2-4 CPU cores (but requires API access)
>
> For budget-constrained deployments, consider:
> 1. Using external LLM APIs (OpenAI, etc.) to reduce hardware costs
> 2. Starting with small models (phi3:mini, deepseek-r1) on modest hardware
> 3. Scaling up as usage grows

---

## 🐝 Using the Web Wizard

### Step-by-Step:

1. **Run the installer:**
   ```bash
   ./install_sting.sh
   ```

2. **Open your browser:**
   ```
   http://localhost:8080
   ```

3. **Complete the 7 steps:**
   - **Step 1:** System basics (hostname, timezone)
   - **Step 2:** Data disk (optional - for separate storage)
   - **Step 3:** Admin email (passwordless account)
   - **Step 4:** LLM backend (REQUIRED - choose local or API, test connectivity!)
   - **Step 5:** Email settings (optional - for notifications)
   - **Step 6:** SSL configuration (self-signed or custom)
   - **Step 7:** Review and apply

4. **Watch the installation:**
   - Real-time logs stream in your browser
   - Progress bar shows installation status
   - Takes 15-30 minutes depending on your system

5. **Access STING:**
   - Automatic redirect to https://localhost:8443
   - Login with your admin email
   - Check email for magic link verification

---

## 📝 Configuration

### 🤖 LLM Backend Requirement

**STING requires an LLM backend** for AI features (Bee chat, knowledge search, semantic analysis, etc.)

#### System Requirements by Deployment Type

| Component | External API Only | Local LLM (Small Models) | Local LLM (Large Models) |
|-----------|------------------|--------------------------|--------------------------|
| **RAM** | 4-8GB | 16-24GB | 32-64GB |
| **CPU** | 2-4 cores | 8+ cores | 12-16+ cores |
| **Disk** | 20GB | 50-100GB | 100-250GB |
| **GPU** | Not required | Optional (faster) | Highly recommended |
| **Use Case** | Testing, low volume | Small teams, privacy-focused | Production, high volume |
| **Cost** | Pay-per-use API fees | No API fees, higher hardware | No API fees, highest hardware |

#### Choose Your LLM Backend

STING supports multiple LLM backends:

**Option A: Ollama (Recommended for Self-Hosting)**
Best for: Complete data sovereignty, no API costs, privacy-sensitive data

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a small model (4GB RAM+)
ollama pull phi3:mini

# Or pull a larger model (16GB RAM+)
ollama pull deepseek-r1

# Use in wizard:
Endpoint: http://localhost:11434
Model: phi3:mini
```

**Option B: LM Studio**
Best for: Desktop users, GUI preference, testing different models

```
Endpoint: http://localhost:11434
Model: Choose from loaded models
Requirements: 16GB+ RAM for most models
```

**Option C: External APIs (Minimal Hardware)**
Best for: Testing, low volume, budget-constrained hardware

```
Endpoint: https://api.openai.com/v1
Model: gpt-4
API Key: Your key (configure in Step 4)
Requirements: Just 4-8GB RAM
```

**Option D: Hybrid (Recommended for Production)**
Best for: Privacy + performance balance

- Use Ollama for privacy-sensitive queries
- Use external API for complex analysis
- Configure both in Step 4 of wizard

### Default Ports

After installation, STING runs on:

- **Frontend:** https://localhost:8443
- **API:** https://localhost:5050
- **Auth (Kratos):** https://localhost:4433
- **Setup Wizard:** http://localhost:8080 (first-run only)

---

## 🔧 Advanced: CLI Installation

For automated deployments or scripts:

```bash
# Create config file first
cp conf/config.yml.default conf/config.yml
nano conf/config.yml

# Run CLI installer
./install_sting.sh --cli
```

Or use the full management script:

```bash
./manage_sting.sh install

# Other commands:
./manage_sting.sh start
./manage_sting.sh stop
./manage_sting.sh uninstall
./manage_sting.sh status
```

---

## 📚 Post-Installation

### Create Additional Admin Accounts

```bash
./manage_sting.sh create admin newadmin@example.com
```

### Access Points

- **Dashboard:** https://localhost:8443
- **Bee Chat:** https://localhost:8443/bee-chat
- **Honey Jars:** https://localhost:8443/honey-jars
- **API Docs:** https://localhost:5050/docs

### First Login

1. Go to https://localhost:8443/login
2. Enter your admin email
3. Click the magic link sent to your email (check Mailpit if testing: http://localhost:8025)
4. Set up TOTP authenticator
5. (Optional) Add passkey/biometric auth

---

## 🐛 Troubleshooting

### Wizard won't start

```bash
# Check Python
python3 --version  # Should be 3.8+

# Install wizard dependencies manually
cd web-setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

### LLM endpoint test fails

**For Ollama:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not running, start it
ollama serve &

# Check available models
ollama list

# Pull a model if none available
ollama pull phi3:mini
```

**For LM Studio:**
- Ensure LM Studio is running
- Check that a model is loaded
- Verify the local server is enabled (port 11434)

**For External APIs:**
- Verify API key is correct
- Check network connectivity: `curl https://api.openai.com`
- Ensure API endpoint URL is correct

**Common Issues:**
- **Port conflict**: Ollama/LM Studio both use 11434 by default
- **Firewall**: Check firewall isn't blocking localhost:11434
- **Model not loaded**: Ollama requires `ollama pull` first
- **Insufficient RAM**: 4GB+ for small models, 16GB+ for larger ones

### Installation hangs

- Check Docker is running: `docker ps`
- View logs in the wizard (real-time streaming)
- Check disk space: `df -h`

### Need to start over?

```bash
# Uninstall completely
./manage_sting.sh uninstall --purge

# Run installer again
./install_sting.sh
```

---

## 🎓 Next Steps

After installation:

1. **Complete Security Setup:** TOTP + Passkey
2. **Configure LLM Backend:** Add AI models
3. **Explore Bee Chat:** AI-powered conversations with PII protection
4. **Try Honey Jars:** Secure data repositories
5. **Read the Docs:** Full documentation at `/docs`

---

## 💡 Tips

- **For VM deployments:** The wizard is perfect! Just boot the VM and open the wizard URL.
- **For development:** Use the wizard in dev mode (`DEV_MODE=true`) to test configuration without actually installing.
- **For production:** Always use real SMTP (not Mailpit) and proper SSL certificates.
- **For automation:** Use `--cli` flag and pre-create `conf/config.yml`.
- **For limited resources:** Start with external LLM APIs (4-8GB RAM) then migrate to local Ollama as you scale.
- **For data sovereignty:** Use local Ollama with small models (phi3:mini) even on modest hardware (16GB RAM).

---

## 📞 Need Help?

- **Documentation:** Check `/docs` directory
- **Issues:** https://github.com/AlphaBytez/STING-CE/issues
- **CLI Help:** `./manage_sting.sh --help`
- **Wizard Help:** `./install_sting.sh --help`

Happy beekeeping! 🐝🍯
