# 🐝 Getting Support with Bee - User Guide

Getting help with STING just got incredibly easy! Instead of manually collecting logs or trying to figure out what's wrong, just chat with Bee about your problem and let AI handle the technical details.

## Quick Start: Getting Help

### Method 1: Chat with Bee (Recommended)

Open Bee Chat and describe your problem in natural language:

```
"@bee I can't log in after the update"
"@bee The dashboard is loading slowly"
"@bee My AI chat isn't responding"
"@bee Help with database connection errors"
```

Bee will:
1. **Analyze** your issue and identify relevant services
2. **Suggest** diagnostic approaches
3. **Create** a targeted diagnostic bundle
4. **Establish** secure support access (if needed)
5. **Track** your support request progress

### Method 2: Traditional CLI

If the web interface is down, use command line:

```bash
# Quick AI-guided support
./manage_sting.sh bee support --create "describe your issue"

# Manual diagnostic collection
./manage_sting.sh buzz collect --auth-focus
```

## Common Support Scenarios

### 🔐 Authentication Problems

**Symptoms**: Can't log in, redirect loops, session errors

**Chat with Bee**:
```
"@bee I'm having login issues"
```

**What Bee does**:
- Checks Kratos authentication service logs
- Analyzes app service session coordination
- Looks for AAL2 step-up problems
- Creates auth-focused diagnostic bundle
- Suggests common fixes

### 🌐 Frontend Not Loading

**Symptoms**: Blank page, build errors, routing issues

**Chat with Bee**:
```
"@bee The dashboard won't load"
```

**What Bee does**:
- Examines frontend service logs
- Checks build compilation status
- Reviews nginx proxy configuration
- Captures startup sequence logs
- Identifies API connection problems

### 🤖 AI Chat Not Working

**Symptoms**: Bee not responding, chat errors, slow responses

**Chat with Bee** (if basic chat still works):
```
"@bee My AI chat isn't working properly"
```

**Or use CLI**:
```bash
./manage_sting.sh bee support --create "AI chat issues"
```

**What happens**:
- Analyzes chatbot service health
- Checks external AI service connectivity
- Reviews Ollama model status
- Captures LLM processing logs
- Tests knowledge base access

### 🗄️ Database Issues

**Symptoms**: Connection errors, slow queries, data problems

**Chat with Bee**:
```
"@bee I'm getting database connection errors"
```

**What Bee does**:
- Checks PostgreSQL service status
- Reviews connection pool health
- Analyzes recent database logs
- Tests service connectivity
- Captures migration status

### 🐌 Performance Problems

**Symptoms**: Slow responses, high memory usage, timeouts

**Chat with Bee**:
```
"@bee Everything is running slowly"
```

**What Bee does**:
- Collects performance metrics
- Reviews resource usage patterns
- Captures container statistics
- Analyzes response times
- Identifies bottlenecks

## Understanding Support Tiers

### Community Tier (Free)
- **Access**: Chat-based diagnostics
- **Delivery**: Manual honey jar download
- **Response Time**: 48-72 hours
- **Support**: Community forums + email

**What you get**:
```
Bee: "✅ Diagnostic bundle created (honey-jar-auth-2025-01-12.tar.gz)
📧 Please email this bundle to community@sting-support.com
📋 Reference ticket: #ST-2025-001"
```

### Professional Tier
- **Access**: All Community features + secure tunnels
- **Delivery**: Automated Tailscale tunnels
- **Response Time**: 4-8 hours
- **Support**: Priority email + chat

**What you get**:
```
Bee: "✅ Diagnostic bundle created and uploaded securely
🔒 Tailscale tunnel established for support team
⏰ Access expires in 24 hours
📞 Support team will contact you within 4 hours"
```

### Enterprise Tier
- **Access**: All features + dedicated channels
- **Delivery**: Dedicated WireGuard tunnels
- **Response Time**: 1 hour
- **Support**: On-call engineers + phone

**What you get**:
```
Bee: "✅ Enterprise support request created
🔗 Dedicated support channel established
👨‍💻 Senior engineer assigned: Alex Kumar
📞 Direct line: +1-555-STING-1 (ext. 2025)"
```

## Step-by-Step: Complete Support Flow

### Step 1: Describe Your Problem

Start a chat with Bee and describe what's happening:

```
User: "@bee I updated STING last night and now I can't access the dashboard. 
It just shows a loading spinner forever."
```

### Step 2: Bee Analyzes the Issue

```
Bee: "I understand you're having dashboard loading issues after an update. 
This could be related to several services:

1. Frontend service (build/compilation issues)
2. App service (API communication problems)  
3. Database migrations (update-related changes)

Let me run some diagnostics. I'll check:
✓ Frontend service logs for build errors
✓ App service logs for API connectivity
✓ Database logs for migration issues
✓ Nginx proxy configuration

Should I create a comprehensive diagnostic bundle focusing on post-update issues?"
```

### Step 3: Confirm Diagnostic Approach

```
User: "Yes, please create the diagnostic bundle"

Bee: "Perfect! Creating post-update diagnostic bundle:

🔄 Capturing frontend logs (last 2 hours)
🔄 Capturing app service logs (last 2 hours)  
🔄 Checking database migration status
🔄 Testing service connectivity
🔄 Analyzing configuration changes
🔄 Running health checks on all services

This may take 30-60 seconds..."
```

### Step 4: Review Findings

```
Bee: "✅ Diagnostic analysis complete! Here's what I found:

🚨 Issue Identified: Frontend build compilation failed
📋 Root Cause: Missing environment variable after update
🔧 Quick Fix Available: Yes

Diagnostic bundle created: dashboard-loading-ST-2025-001.tar.gz (1.2MB)

Would you like me to:
1. Try the quick fix automatically
2. Create a support ticket with this analysis  
3. Establish secure access for support team review

What would you prefer?"
```

### Step 5: Choose Your Path

**Option A - Try Quick Fix:**
```
User: "Try the quick fix"

Bee: "🔧 Applying fix: Regenerating frontend environment variables...
✅ Environment variables regenerated
🔄 Restarting frontend service...
✅ Frontend service restarted successfully
🧪 Testing dashboard access...
✅ Dashboard is now accessible!

The issue has been resolved. Your dashboard should be working normally now."
```

**Option B - Create Support Ticket:**
```
User: "Create a support ticket"

Bee: "I need to verify your admin permissions before creating support tickets.
Please confirm you have authorization to submit support requests."

User: "Yes, I'm an admin"

Bee: "✅ Creating support ticket with analysis:

📋 Ticket ID: #ST-2025-001
📦 Diagnostic Bundle: Attached (1.2MB, sanitized)  
🤖 AI Analysis: Frontend compilation failure post-update
⏰ Created: 2025-01-12 14:30:00 UTC
🎯 Priority: Normal (UI issue, workaround available)

[Professional/Enterprise tiers only:]
🔒 Would you like me to establish secure access for the support team?
This creates a temporary encrypted tunnel for hands-on troubleshooting."
```

### Step 6: Secure Access (Pro/Enterprise)

```
User: "Yes, create secure access"

Bee: "🔐 Setting up secure support access:

I need explicit confirmation to grant external access to your system.
This is a security-critical operation that:

• Creates a temporary Tailscale tunnel  
• Allows support team secure access
• Expires automatically in 24 hours
• Is fully audited and logged

Type 'GRANT_SUPPORT_ACCESS' to confirm:"

User: "GRANT_SUPPORT_ACCESS"

Bee: "✅ Secure support access established!

🔗 Tailscale tunnel: ts-support-ST2025001.tail-net.com
⏰ Access expires: 2025-01-13 14:30:00 UTC  
👨‍💻 Support engineer notified: Sarah Chen
📧 Email confirmation sent to your admin address
📞 Expected contact: Within 4 hours (Professional tier)

I'll notify you when the support engineer connects."
```

## Tips for Better Support

### 🎯 Be Specific About Timing
```
Good: "@bee Login stopped working after yesterday's update"
Better: "@bee Login was fine at 2pm, started failing around 4pm after restart"
```

### 🔍 Include Error Messages  
```
Good: "@bee Getting database errors"
Better: "@bee Getting 'connection refused' errors when accessing user settings"
```

### 📊 Mention Performance Details
```
Good: "@bee System is slow"
Better: "@bee Dashboard takes 30+ seconds to load, used to be instant"
```

### 🔄 Describe Recent Changes
```
Good: "@bee AI chat not working"  
Better: "@bee AI chat stopped working after I changed models from phi3 to llama"
```

## Advanced Features

### Check Support Status Anytime
```
"@bee What's the status of my support tickets?"
"@bee Show me active support sessions"  
"@bee When does my support access expire?"
```

### Proactive Health Checks
```
"@bee Check system health"
"@bee Analyze current performance"
"@bee Are there any issues I should know about?"
```

### Administrative Commands
```
"@bee Show all support tickets for this organization"
"@bee End support session for ticket ST-123"
"@bee Generate weekly support analytics"
```

## Security & Privacy

### What Information is Collected
- Service logs (last 30 lines by default)
- System health metrics
- Configuration snapshots (secrets removed)  
- Error patterns and stack traces
- Resource usage statistics

### What is NOT Collected
- User data or file contents
- Passwords or API keys
- Personal information
- Database records
- Private conversations (except support chat)

### Data Sanitization
All diagnostic bundles are automatically processed through "Pollen Filters" that remove:
- API keys and passwords
- Email addresses and personal info
- Database connection strings
- Certificate data
- Custom sensitive patterns

### Access Controls
- Only admins can create support requests
- Secure tunnels require explicit confirmation
- All access is temporary and audited
- Support sessions auto-expire
- Complete audit trail maintained

## Troubleshooting the Support System

### Bee Chat Not Responding
```bash
# Check chatbot service
./manage_sting.sh status chatbot
./manage_sting.sh logs chatbot

# Restart if needed
./manage_sting.sh restart chatbot
```

### CLI Support Commands Not Found
```bash
# Sync latest management scripts
./manage_sting.sh sync-config

# Verify command availability  
./manage_sting.sh --help | grep "bee support"
```

### Permission Errors
```bash
# Check your user role
./manage_sting.sh user info

# Admin users only can create support tickets
```

## Getting Help with the Support System

If you're having trouble with the support system itself:

1. **Check service status**: `./manage_sting.sh status`
2. **Review logs**: `./manage_sting.sh logs chatbot`  
3. **Try CLI fallback**: `./manage_sting.sh bee support --analyze`
4. **Manual diagnostics**: `./manage_sting.sh buzz collect`
5. **Community help**: Post in community forums with diagnostic bundle

The Bee-Powered Support System makes getting help with STING feel like talking to a knowledgeable colleague rather than wrestling with technical logs. Just describe your problem naturally and let Bee handle the technical complexity!