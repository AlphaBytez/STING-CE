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
- **RAM:** 4GB minimum (8GB recommended)
- **Disk:** 20GB minimum

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
   - **Step 4:** LLM backend (test connectivity!)
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

### LLM Backend

STING supports multiple LLM backends:

**Ollama (Recommended):**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull phi4:mini

# Use in wizard:
Endpoint: http://localhost:11434
Model: phi4:mini
```

**LM Studio:**
```
Endpoint: http://localhost:11434
Model: Choose from loaded models
```

**OpenAI-Compatible APIs:**
```
Endpoint: https://api.openai.com/v1
Model: gpt-4
API Key: Your key (configure in Step 4)
```

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

```bash
# Verify Ollama is running
curl http://localhost:11434/api/tags

# Or check LM Studio server status
```

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

---

## 📞 Need Help?

- **Documentation:** Check `/docs` directory
- **Issues:** https://github.com/AlphaBytez/STING-CE/issues
- **CLI Help:** `./manage_sting.sh --help`
- **Wizard Help:** `./install_sting.sh --help`

Happy beekeeping! 🐝🍯
