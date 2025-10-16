# 🔗 Headscale Community Support - Free Secure Tunnels

STING-CE now includes **free, self-hosted secure tunnels** using Headscale for community support! No external accounts needed, completely free, perfect for secure diagnostic bundle delivery.

## 🎯 **Why Headscale for STING-CE?**

### **✅ Perfect for Community Edition:**
- **100% Free** - No subscription costs ever
- **Self-Hosted** - Fits STING's privacy-first approach  
- **No External Dependencies** - Everything runs on your infrastructure
- **Enterprise Scalable** - Can upgrade to Tailscale SaaS later

### **✅ Community Support Benefits:**
- **Secure Bundle Delivery** - Encrypted tunnels for diagnostic data
- **Volunteer Helper Access** - Community members can securely assist
- **Temporary Access** - 30-minute ephemeral sessions with auto-cleanup
- **Full Audit Trail** - Complete log of support activities

## 🚀 **How It Works**

### **The Magic Flow:**
```
Customer Problem → Bee Analysis → Support Ticket → Secure Tunnel → Community Help
     (Chat)           (AI)         (Auto)           (Headscale)      (Volunteers)
```

### **Detailed Workflow:**
```
1. Customer: "@bee I need help with authentication issues"

2. Bee: "I've analyzed this as an authentication issue and created 
   diagnostic bundle ST-2025-001. Would you like me to create a 
   secure tunnel for community volunteer assistance?"

3. Customer: "GRANT_COMMUNITY_ACCESS"

4. System: 
   ✅ Creates Headscale user: support-st-2025-001
   ✅ Generates ephemeral auth key (expires in 30 min)
   ✅ Posts to community #urgent-help channel
   ✅ Provides volunteers secure access credentials

5. Community Volunteer:
   ✅ Installs Tailscale client
   ✅ Joins support network: tailscale up --login-server=http://customer.domain:8070 --authkey=...
   ✅ Securely accesses customer STING system
   ✅ Reviews diagnostic bundle and provides assistance
   
6. Auto-Cleanup:
   ✅ Tunnel expires after 30 minutes
   ✅ Volunteer access automatically revoked
   ✅ Complete audit report generated
```

## ⚙️ **Implementation Details**

### **Headscale Service (Port 8070)**
```yaml
# Added to docker-compose.yml
headscale:
  container_name: sting-ce-headscale
  image: headscale/headscale:0.23.0
  ports:
    - "8070:8070"  # Web interface (avoiding 8080 conflict)
    - "9090:9090"  # Metrics endpoint
  volumes:
    - ./conf/headscale:/etc/headscale:ro
    - headscale_data:/var/lib/headscale
  environment:
    - HEADSCALE_EPHEMERAL_NODE_INACTIVITY_TIMEOUT=30m
    - HEADSCALE_BASE_DOMAIN=support.sting.local
  profiles:
    - support-tunnels
    - full
```

### **Configuration Integration**
```yaml
# Added to config.yml
headscale:
  enabled: true
  server:
    port: 8070  # Avoiding 8080 conflict
    base_domain: "support.sting.local"
  support_sessions:
    default_duration: "30m"  # Community support
    max_duration: "4h"       # Enterprise support
    max_concurrent: 5
  security:
    ephemeral_node_timeout: "30m"
    enable_routing: false  # Don't route customer networks
```

### **New CLI Commands**
```bash
# Support tunnel management
./manage_sting.sh support tunnel create ST-2025-001     # 30min tunnel
./manage_sting.sh support tunnel create ST-2025-002 4h  # 4hr tunnel  
./manage_sting.sh support tunnel list                   # List active
./manage_sting.sh support tunnel status ST-2025-001     # Check status
./manage_sting.sh support tunnel close ST-2025-001      # Close tunnel
./manage_sting.sh support tunnel headscale-status       # Service health
```

## 🔒 **Security Model**

### **Access Control (policy.hujson)**
```json
{
  "groups": {
    "group:community-helpers": [],  // Community volunteers
    "group:sting-support": []       // Official support team
  },
  "acls": [
    {
      "comment": "Community helpers can access customer STING systems",
      "action": "accept",
      "src": ["group:community-helpers"],
      "dst": [
        "tag:customer-device:22",    // SSH for troubleshooting
        "tag:customer-device:8888"   // Bee Chat for guided support
      ]
    },
    {
      "comment": "Deny access to customer internal networks", 
      "action": "deny",
      "src": ["group:community-helpers"],
      "dst": ["!tag:customer-device"]
    }
  ]
}
```

### **Ephemeral Sessions**
- **30-minute default** for community support
- **Auto-expiration** - no manual cleanup needed
- **No persistent access** - users deleted after session
- **Scoped permissions** - SSH to STING containers only

## 💼 **Community Support Scenarios**

### **Scenario 1: Authentication Help**
```
Customer: "@bee I can't login after the Kratos update"

Bee: "I've identified this as an authentication issue affecting 
Kratos and app services. I've created diagnostic bundle 
ST-2025-123 with auth-focused logs.

The community #auth-help channel has volunteers who specialize 
in Kratos troubleshooting. Would you like me to create a secure 
tunnel so they can help you directly?"

Customer: "Yes, create secure access"

Bee: "🔐 Community Volunteer Access Setup:
I need authorization for temporary system access.

This will:
• Create 30-minute encrypted tunnel
• Allow community volunteer secure SSH access
• Provide access to diagnostic bundle
• Auto-expire after session
• Full audit trail

⚠️ This grants temporary system access to community volunteer
Type 'GRANT_COMMUNITY_ACCESS' to authorize."

Customer: "GRANT_COMMUNITY_ACCESS"

Bee: "✅ Community Support Tunnel Active
🔗 Tunnel: support-st-2025-123.support.sting.local
👥 Posted to #auth-help channel with access details
⏰ Auto-expires in 30 minutes

Community volunteer can now:
• Securely SSH to your STING containers
• Review diagnostic bundle with auth logs  
• Test authentication flows safely
• Provide real-time troubleshooting assistance

I'll notify you when someone connects to help!"
```

### **Scenario 2: Performance Investigation**
```
Customer: "@bee Dashboard is extremely slow, need community help"

Bee: "Performance issue detected. I've created a comprehensive 
diagnostic bundle with resource metrics and service logs.

Our community performance experts can help investigate:
• Database query optimization
• Container resource tuning
• Frontend build optimization
• Network connectivity issues

Should I create a secure tunnel for expert community assistance?"

[Community volunteer connects via Headscale tunnel]

Volunteer: "I can see from your diagnostic bundle that the database
is missing an index. Let me check your actual query patterns..."

[Direct SSH access to containers for live debugging]

Volunteer: "Found it! Your user_sessions table needs an index on 
expires_at. I can apply the fix now if you'd like."

Customer: "Yes please!"

[Issue resolved in 10 minutes with direct access]
```

## 🎯 **Deployment and Testing**

### **Enable Headscale Support**
```bash
# 1. Start Headscale service
./manage_sting.sh start --profile support-tunnels

# 2. Check Headscale status
./manage_sting.sh support tunnel headscale-status

# 3. Create test tunnel
./manage_sting.sh support tunnel create ST-TEST-001

# 4. List active tunnels
./manage_sting.sh support tunnel list
```

### **Community Volunteer Setup**
```bash
# For community helpers who want to provide support:

# 1. Install Tailscale client
# macOS: brew install tailscale
# Linux: curl -fsSL https://tailscale.com/install.sh | sh

# 2. Join customer support network (using provided auth key)
tailscale up --login-server=http://customer.domain:8070 --authkey=CUSTOMER_PROVIDED_KEY

# 3. SSH to customer system
tailscale ssh support-st-2025-001

# 4. Access diagnostic bundles
ls ~/.sting-ce/support_bundles/

# 5. Help with troubleshooting!
```

## 📊 **Benefits Analysis**

### **For Customers:**
- **Free secure access** for community support
- **No external accounts** or subscriptions needed
- **Privacy preserved** - all self-hosted infrastructure
- **Expert community help** with direct system access
- **Auto-security** - temporary access with cleanup

### **For Community Volunteers:**
- **Secure environment** to provide assistance
- **Direct system access** for effective troubleshooting
- **Rich diagnostic data** from AI-generated bundles
- **Safe testing** in customer's actual environment
- **Clear session boundaries** with automatic expiration

### **For STING Project:**
- **Enhanced community support** through better tools
- **Competitive advantage** over other self-hosted platforms
- **Enterprise path** clearly demonstrated
- **No hosting costs** - customers run their own infrastructure

## 🚀 **Future Enhancements**

### **Community Integration**
- **Discord/Slack Bots** - Auto-post tunnel access to help channels
- **Forum Integration** - One-click tunnel access from forum posts
- **GitHub Issues** - Attach tunnel access to reproducible bugs
- **Community Reputation** - Track helpful volunteers

### **Enterprise Upgrade Path**
- **Longer Sessions** - 4+ hour tunnels for complex issues
- **Priority Access** - Skip community queue for paying customers
- **Official Support** - STING team access via same infrastructure
- **Tailscale SaaS** - Option for managed coordination servers

## 🎉 **Ready to Deploy**

The Headscale Community Support system is ready for testing! This provides:

✅ **Free secure tunnels** for volunteer community support
✅ **Self-hosted infrastructure** maintaining STING's privacy principles  
✅ **Professional-grade security** with ephemeral access and audit trails
✅ **Clear enterprise path** using the same infrastructure
✅ **Zero external dependencies** or subscription costs

**Start testing:**
```bash
./manage_sting.sh start --profile support-tunnels
./manage_sting.sh support tunnel headscale-status  
./manage_sting.sh bee support create "test issue for tunnel"
```

This transforms STING community support from forum-based help to **secure, direct troubleshooting** - all while staying completely free and self-hosted! 🔥