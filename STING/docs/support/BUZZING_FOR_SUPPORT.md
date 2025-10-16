# 🐝 Buzzing for Support - STING Hive Diagnostics

> When your hive needs help, just buzz! STING's intelligent diagnostics system makes getting support as natural as bees communicating in their hive.

## 🍯 What is "Buzzing for Support"?

Just like bees use buzzing to communicate important information throughout the hive, STING's **Hive Diagnostics** system lets you quickly gather and share comprehensive system information when you need assistance. 

**"Buzzing"** creates a **Honey Jar** - a secure, sanitized bundle of diagnostic data that support teams can use to quickly understand and resolve your issues.

## 🚀 Quick Start - Get Help in 30 Seconds

```bash
# Create a diagnostic honey jar
./manage_sting.sh buzz --collect

# View what's in your hive
./manage_sting.sh buzz --hive-status

# Clean up old honey jars  
./manage_sting.sh buzz --clean
```

## 🏠 How the Hive Diagnostics Work

### 🐝 The Worker Bees (Data Collection)
Your STING system has many "worker bees" - services that generate logs and diagnostic data:

- **App Bees**: Flask backend logs and health data
- **Frontend Bees**: React application logs and performance metrics  
- **LLM Bees**: Model service logs and inference data
- **Database Bees**: PostgreSQL connection and query logs
- **Guardian Bees**: Kratos authentication and security logs
- **Knowledge Bees**: Honey Jar system and vector database logs

### 🍯 The Honey Collection Process
When you "buzz" for support, our **Honey Collector** gathers "nectar" (log data) from all your worker bees:

1. **Nectar Gathering**: Collects recent logs (default: 24-48 hours)
2. **Pollen Filtering**: Removes sensitive data (keys, passwords, PII)
3. **Honey Creation**: Compresses everything into a portable "honey jar"
4. **Hive Labeling**: Adds system info and timestamps

### 🧹 The Pollen Filter (Privacy Protection)
Our **Pollen Filter** automatically removes sensitive information:

- ✅ **Filtered Out**: API keys, passwords, tokens, email addresses, phone numbers
- ✅ **Kept Safe**: Error patterns, timing data, service health, configuration structure
- ✅ **Configurable**: Adjust filtering rules for your organization's needs

## 🎯 When to Buzz for Support

### 🚨 Perfect Times to Buzz:
- **Service won't start**: `./manage_sting.sh buzz --collect --include-startup`
- **Performance issues**: `./manage_sting.sh buzz --collect --performance`  
- **Authentication problems**: `./manage_sting.sh buzz --collect --auth-focus`
- **LLM/Chatbot issues**: `./manage_sting.sh buzz --collect --llm-focus`
- **Before major changes**: `./manage_sting.sh buzz --collect --baseline`

### 📊 What Gets Included:
- Recent service logs (sanitized)
- Docker container health status
- System resource usage
- Configuration snapshots (secrets removed)
- Database schema info (no actual data)
- Network connectivity tests
- Recent error patterns

## 🔧 Advanced Buzzing Options

### Time Windows
```bash
# Last 24 hours (default)
./manage_sting.sh buzz --collect

# Last 48 hours  
./manage_sting.sh buzz --collect --hours 48

# Specific time range
./manage_sting.sh buzz --collect --from "2024-01-01 10:00" --to "2024-01-01 15:00"
```

### Focus Areas
```bash
# Focus on authentication issues
./manage_sting.sh buzz --collect --auth-focus

# Focus on LLM performance  
./manage_sting.sh buzz --collect --llm-focus

# Include startup and initialization logs
./manage_sting.sh buzz --collect --include-startup

# Performance and resource analysis
./manage_sting.sh buzz --collect --performance
```

### Bundle Management
```bash
# List existing honey jars
./manage_sting.sh buzz --list

# View bundle contents (without extracting)
./manage_sting.sh buzz --inspect honey_jar_20240101_120000.tar.gz

# Test pollen filtering rules
./manage_sting.sh buzz --filter-test

# Clean bundles older than 7 days
./manage_sting.sh buzz --clean --older-than 7d
```

## 🌐 Sharing Your Honey Jar

### Via Dashboard (Recommended)
1. Navigate to **Dashboard → Hive Diagnostics**
2. Click **"Generate Honey Jar"**
3. Select time range and focus areas
4. Download the generated bundle
5. Share with your support team

### Via Command Line
```bash
# Generate and find your honey jar
./manage_sting.sh buzz --collect
ls -la ${INSTALL_DIR}/support_bundles/

# Copy to shared location
cp ${INSTALL_DIR}/support_bundles/honey_jar_*.tar.gz /path/to/share/
```

### Via Support Portal
```bash
# Generate bundle with ticket reference
./manage_sting.sh buzz --collect --ticket ABC123

# Upload directly (if configured)
./manage_sting.sh buzz --upload --ticket ABC123
```

## 🔐 Privacy & Security

### What's Automatically Filtered:
- **API Keys**: `api_key=***`, `token=***`
- **Passwords**: `password=***`, `pwd=***`  
- **Database URLs**: `postgresql://user:***@host/db`
- **Email Addresses**: `user@domain.com` → `user@[FILTERED]`
- **Phone Numbers**: `+1-555-123-4567` → `[PHONE-FILTERED]`
- **IP Addresses**: `192.168.1.100` → `[IP-FILTERED]` (optional)
- **Certificates**: PEM data → `[CERT-FILTERED]`

### Retention Policy:
- Honey jars auto-delete after **30 days**
- Configurable via `conf/config.yml`
- Manual cleanup: `./manage_sting.sh buzz --clean`

### License Features:
- **Community**: 24-48 hour windows, basic filtering
- **Professional**: Extended time windows, advanced filtering
- **Enterprise**: Custom filtering rules, automated uploads

## 🎨 Marketing the Buzz

### For End Users:
*"Having issues? Don't struggle alone - just **buzz** for support! Our Hive Diagnostics instantly gather everything our support team needs to help you, while keeping your sensitive data safe."*

### For IT Teams:
*"Skip the back-and-forth diagnostic requests. STING's **Buzzing** system generates comprehensive, sanitized diagnostic bundles that give support teams immediate insight into your environment."*

### For Sales:
*"Unlike other platforms where troubleshooting means exposing sensitive data, STING's **Hive Diagnostics** automatically sanitize bundles while providing comprehensive insights. Your security team will love it, your support team will get faster resolutions."*

## 🐛 Troubleshooting the Buzzing System

### Common Issues:

**Honey Collector won't start:**
```bash
# Check permissions
ls -la lib/hive_diagnostics/
chmod +x lib/hive_diagnostics/*.sh

# Check disk space
df -h ${INSTALL_DIR}/support_bundles/
```

**Filtering seems incomplete:**
```bash
# Test filter rules
./manage_sting.sh buzz --filter-test
./manage_sting.sh buzz --filter-test --verbose
```

**Bundle too large:**
```bash
# Reduce time window
./manage_sting.sh buzz --collect --hours 12

# Focus on specific services
./manage_sting.sh buzz --collect --services app,llm
```

## 📞 Getting Support

When you need help with STING:

1. **🐝 Buzz first**: `./manage_sting.sh buzz --collect`
2. **📋 Include details**: What were you doing when the issue occurred?
3. **🏷️ Tag it**: Use `--ticket` if you have a support ticket number
4. **📤 Share**: Upload your honey jar to our support portal or attach to your ticket

## 🚀 What's Next?

Future buzzing features in development:
- **Smart Filtering**: AI-powered sensitive data detection
- **Swarm Mode**: Multi-node STING deployment diagnostics  
- **Bee Analytics**: Trend analysis across honey jars
- **Royal Jelly**: Premium diagnostic features for enterprise customers

---

*Remember: In the STING ecosystem, we're all part of the same hive. When you buzz for support, you're helping make the entire platform better for everyone!* 🐝✨