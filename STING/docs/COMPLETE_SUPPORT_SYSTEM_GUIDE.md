# 🚀 Complete STING Support System - User Guide

The complete Bee-powered support system that transforms how users get help with STING-CE, from AI-guided diagnostics to secure bundle sharing.

## 🎯 **Three Ways to Get Support**

### **1. 🗣️ Conversational Support (via Bee Chat)**
```
User: "@bee I can't login after the update"

Bee: "I can see this appears to be an authentication issue. This typically 
involves the Kratos, app services. Let me analyze the situation and create 
a targeted diagnostic bundle.

✅ Issue categorized: Authentication problem
✅ Services identified: Kratos, app, database  
✅ Creating auth-focused diagnostic bundle...
✅ Bundle created: auth-issues-ST-2025-001.tar.gz (1.8MB)
🔒 Fully sanitized - safe for community sharing

**How would you like to get help?**
1. 📧 Email bundle to community support
2. 💬 Post to authentication help forums  
3. 📱 Share in Discord #auth-help channel
4. 📦 Download bundle locally for manual sharing"
```

### **2. ⚙️ Command Line Interface**
```bash
# AI-guided support
./manage_sting.sh bee support create "frontend loading slowly"
./manage_sting.sh bee support analyze
./manage_sting.sh bee support list

# Manual diagnostics  
./manage_sting.sh buzz collect --auth-focus
./manage_sting.sh buzz collect --performance

# Bundle management
./manage_sting.sh bundle list
./manage_sting.sh bundle copy bundle-file.tar.gz ~/Desktop
./manage_sting.sh bundle extract bundle-file.tar.gz
```

### **3. 📦 Local Bundle Access**
```bash
# Download your bundles for manual sharing
./manage_sting.sh bundle list                    # See available bundles
./manage_sting.sh bundle copy auth-ST-001.tar.gz ~/Desktop  # Copy for email
./manage_sting.sh bundle extract perf-ST-002.tar.gz        # Extract for review
./manage_sting.sh bundle package ST-2025-001               # Create shareable package
```

## 🧠 **AI Intelligence Features**

### **Smart Issue Detection:**
- **Authentication Issues** → Targets Kratos, app, database services
- **Frontend Problems** → Focuses on React app, nginx, build processes  
- **AI Chat Issues** → Examines chatbot, external-AI, Ollama services
- **Database Problems** → Analyzes PostgreSQL, connections, migrations
- **Performance Issues** → Comprehensive system resource analysis

### **Intelligent Diagnostics:**
```bash
Input: "can't login with passkey after kratos update"
↓
AI Analysis: 
  ✅ Issue Type: Authentication
  ✅ Target Services: kratos, app, db
  ✅ Diagnostic Flags: --auth-focus --include-startup
  ✅ Bundle Focus: Passkey/WebAuthn flows + update logs
```

## 🔒 **Security & Privacy**

### **Enhanced Log Sanitization:**
```
Original Log:
"2025-01-12 INFO Auth request user admin@company.com password=secret123 api_key=sk_live_abc123 from 192.168.1.100"

Sanitized Log:  
"2025-01-12 INFO Auth request user ***EMAIL_REDACTED*** password=***PASSWORD_REDACTED*** api_key=***API_KEY_REDACTED*** from ***IP_REDACTED***"
```

### **What Gets Removed:**
- ✅ **Passwords & API Keys** - All authentication credentials
- ✅ **Email Addresses** - Personal and organizational emails  
- ✅ **IP Addresses** - Internal and external network info
- ✅ **Database URLs** - Connection strings with credentials
- ✅ **JWT Tokens** - Session and authentication tokens
- ✅ **Certificates** - Private keys and certificate data

### **What Stays (Diagnostic Value):**
- ✅ **Error Messages** - Stack traces and error details
- ✅ **Service Names** - Which services are involved
- ✅ **Timestamps** - When issues occurred
- ✅ **Resource Metrics** - CPU, memory, disk usage
- ✅ **Configuration Structure** - Settings (without secrets)

## 📤 **Flexible Sharing Options**

### **Community Support Channels:**

#### **📧 Email Support**
```bash
# Copy bundle to Desktop for email attachment
./manage_sting.sh bundle copy auth-ST-2025-001.tar.gz ~/Desktop

# Email to: community@sting-support.com
Subject: [STING-CE Support] Authentication Issues - ST-2025-001
Attachment: sting-diagnostic-ST-2025-001-20250112.tar.gz
```

#### **💬 Forum Integration**
```bash
# Create shareable package with documentation
./manage_sting.sh bundle package ST-2025-001

# Upload to community forums:
Title: "Authentication Issues After Kratos Update"
Category: Authentication Help
Attachment: Shareable package with README
Content: AI analysis + bundle + sharing documentation
```

#### **📱 Discord/Slack Sharing**
```bash
# Extract specific logs for chat sharing
./manage_sting.sh bundle extract auth-ST-2025-001.tar.gz
cd ~/.sting-ce/bundle_exports/auth-ST-2025-001/

# Share relevant log snippets in Discord #auth-help
# Full bundle available via secure download link
```

#### **🐛 GitHub Issues**
```bash
# For reproducible bugs
./manage_sting.sh bundle package ST-2025-001

# Create GitHub issue:
Title: "AAL2 redirect loop after Kratos v1.3.0 update"
Labels: bug, authentication, kratos
Attachment: Diagnostic package with reproduction steps
```

## 🏢 **Enterprise Support (Future)**

### **Live Debugging Capabilities:**
```
Enterprise Customer: "@bee CRITICAL: Database down, 1000 users affected"

Bee: "🚨 CRITICAL: Database connectivity failure
✅ Senior DBA Mike Rodriguez assigned (15min response SLA)
✅ 24-hour live debugging tunnel authorized
✅ Direct phone line: +1-555-STING-DB-CRIT

Mike will connect within 15 minutes for:
• Live database analysis and recovery
• Real-time query optimization
• Immediate performance validation
• Root cause analysis with live data"

[Mike connects via Headscale tunnel]
Mike: "Connecting to your database... I can see the connection pool exhaustion. 
Applying fix now... Testing... Fixed! Your system is fully recovered."

Total resolution time: 8 minutes with live access
```

## 📊 **Complete Command Reference**

### **🐝 Bee AI Support**
```bash
./manage_sting.sh bee support analyze           # AI system health analysis
./manage_sting.sh bee support create "issue"    # Intelligent ticket creation
./manage_sting.sh bee support suggest           # Troubleshooting guidance
./manage_sting.sh bee support list              # List support tickets
./manage_sting.sh bee support status            # Support system health
```

### **📦 Bundle Management**  
```bash
./manage_sting.sh bundle list                   # Available bundles
./manage_sting.sh bundle extract BUNDLE         # Extract for review
./manage_sting.sh bundle copy BUNDLE ~/Desktop  # Copy for sharing
./manage_sting.sh bundle inspect BUNDLE         # Preview contents
./manage_sting.sh bundle package TICKET_ID      # Create shareable package
```

### **🔗 Support Tunnels (Enterprise)**
```bash
./manage_sting.sh support tunnel create ST-001  # Create tunnel
./manage_sting.sh support tunnel list           # List active tunnels
./manage_sting.sh support tunnel status ST-001  # Check tunnel status
./manage_sting.sh support tunnel close ST-001   # Close tunnel
```

### **🍯 Traditional Diagnostics**
```bash
./manage_sting.sh buzz collect                  # General bundle
./manage_sting.sh buzz collect --auth-focus     # Authentication focus
./manage_sting.sh buzz collect --llm-focus      # AI service focus
./manage_sting.sh buzz collect --performance    # Performance metrics
```

## 🎉 **Why This System Is Revolutionary**

### **For Community Users:**
```
Old Way:
"Help!" → [Manual log collection] → [Forum post] → [Wait 2-3 days] → [Maybe get help]

New Way:
"@bee help!" → [AI analysis + bundle in 30 seconds] → [Community expert help in 2-4 hours]
```

### **For Enterprise Users:**
```
Old Way:
"CRITICAL!" → [Email logs] → [Back-and-forth] → [Remote guessing] → [4+ hour resolution]

New Way:  
"@bee CRITICAL!" → [AI analysis] → [Senior engineer live access in 15 min] → [Fixed in 10 min]
```

### **For You (STING Support):**
```
Old Way:
[Manual log analysis] → [Email guessing] → [Multiple support rounds] → [Frustrated customers]

New Way:
[Automated upload] → [48h review window] → [Rich diagnostic context] → [Happy customers]
```

## 🎯 **Perfect Balance Achieved**

✅ **Community Edition**: Realistic, secure, bundle-based support
✅ **Enterprise Edition**: Live debugging with clear premium value  
✅ **Your Infrastructure**: Controlled bundle reception with review time
✅ **User Empowerment**: Full local access to their own diagnostic data

This system provides **professional-grade diagnostics for free** while creating a **compelling enterprise upgrade path** based on **live access value**! 🔥

Users can now easily **download, extract, and share their own bundles** while you maintain **complete control** over the support pipeline and review process. Perfect! 🎯