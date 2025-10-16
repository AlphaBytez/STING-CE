# STING-CE Demo Walkthrough 🐝
*Your 10-Minute Journey Through AI-Powered Honey Jar Intelligence*

## Overview
This walkthrough demonstrates STING-CE's core capabilities as a fully functional MVP for honey jar management and AI-powered threat intelligence. Perfect for demos, training, or self-guided exploration.

**Duration**: ~10 minutes  
**Prerequisites**: STING-CE installed and running  
**Key Features**: Honey Jar management, AI chat assistant, knowledge integration, security analytics

---

## 🚀 Quick Start (2 minutes)

### 1. Access STING Dashboard
1. Open your browser to `https://localhost:8443`
2. Accept the self-signed certificate warning (development only)
3. You'll see the modern login page with passkey support

### 2. Login Options
- **Admin Login**: Use credentials created during setup
- **Passkey Authentication**: Click "Sign in with Passkey" for passwordless auth
- **Demo Mode**: Use test credentials if configured

### 3. First Impressions
Upon login, notice:
- 🎨 **Clean, modern UI** with yellow/blue theme
- 📊 **Real-time dashboard** showing system status
- 🐝 **Bee AI Assistant** indicator in the corner
- 🔒 **Security status** showing encrypted connections

---

## 🍯 Honey Jar Management (3 minutes)

### Create Your First Honey Jar
1. Navigate to **"Honey Pots"** in the sidebar
2. Click **"Create New Honey Jar"**
3. Fill in details:
   ```
   Name: SSH Attack Intelligence
   Description: Captures SSH brute force attempts
   Type: SSH Honey Jar
   Tags: ssh, authentication, brute-force
   ```
4. Click **"Deploy"** - Notice the real-time deployment status

### Explore Honey Jar Features
- **Live Monitoring**: See connection attempts in real-time
- **Attack Patterns**: AI automatically categorizes threats
- **Integration Ready**: Data flows to knowledge base instantly

**💡 Demo Tip**: Show how quickly threats are detected and categorized without manual intervention.

---

## 🤖 AI-Powered Intelligence with Bee (3 minutes)

### Activate Bee Chat
1. Click the **Bee icon** (🐝) in the bottom right
2. Notice the status indicator - should show "Online"
3. Try these demo questions:

#### Sample Question 1: Threat Analysis
```
"What SSH attacks have we seen in the last hour?"
```
**Expected Response**: Bee will query the knowledge base and provide:
- Attack count and types
- Source IPs and patterns
- Recommended actions

#### Sample Question 2: Security Recommendations
```
"How can I improve my SSH honey jar configuration?"
```
**Expected Response**: Context-aware suggestions based on:
- Current honey jar settings
- Recent attack patterns
- Best practices from knowledge base

#### Sample Question 3: Knowledge Integration
```
"Show me similar attacks from our threat intelligence database"
```
**Expected Response**: Bee searches across:
- Local honey jar data
- Shared threat intelligence
- Historical patterns

### Key Bee Features to Highlight
- ✅ **Contextual Awareness**: Knows your current honey jar configuration
- ✅ **Real-time Integration**: Pulls live data from active honey jars
- ✅ **Actionable Intelligence**: Provides specific recommendations
- ✅ **Natural Language**: No need for complex queries

---

## 🔐 Security & Advanced Features (2 minutes)

### 1. Authentication Showcase
- Click **Settings → Security**
- Show **Passkey Management** - add a new passkey
- Demonstrate **2FA options** available
- Highlight **Session management** features

### 2. Knowledge Base Integration
- Navigate to **Knowledge → Honey Pots**
- Show the **STING Documentation** knowledge base
- Click **"Search"** and query: "honey jar best practices"
- Demonstrate how documentation is AI-searchable

### 3. Real-time Analytics
- Go to **Dashboard → Analytics**
- Show **live threat map** (if configured)
- Highlight **attack trends** visualization
- Point out **automated reporting** capabilities

### 4. LLM Model Management
- Navigate to **Settings → 🐝 LLM Settings** (admin only)
- Show available models (phi3, zephyr, etc.)
- Demonstrate **model switching** in real-time
- Highlight **on-premise AI** - no data leaves your infrastructure

---

## 🎯 Key Differentiators to Emphasize

### 1. **Integrated AI Assistant**
Unlike traditional honey jars, STING provides instant AI analysis without manual log review.

### 2. **Knowledge-Driven**
Every attack enriches the knowledge base, making the system smarter over time.

### 3. **Privacy-First Architecture**
- All AI processing happens locally
- No external API dependencies
- Your threat data stays yours

### 4. **Modern Security**
- Passkey authentication (cutting-edge)
- End-to-end encryption
- Zero-trust architecture

### 5. **Developer-Friendly**
- RESTful APIs for everything
- Webhook integrations
- Extensible architecture

---

## 🎪 Demo Scenarios

### Scenario 1: Active Attack Response (2 mins)
1. Trigger a simulated SSH attack (use included scripts)
2. Watch real-time detection in honey jar dashboard
3. Ask Bee: "What just happened with my SSH honey jar?"
4. Show automated response recommendations

### Scenario 2: Threat Hunting (2 mins)
1. Ask Bee: "Find all attacks from IP range 192.168.x.x"
2. Navigate to the suggested honey jar logs
3. Create a new rule based on findings
4. Show how the rule immediately takes effect

### Scenario 3: Knowledge Building (1 min)
1. Upload a threat intelligence report (PDF/TXT)
2. Ask Bee about the report contents
3. Show how it's instantly searchable and integrated

---

## 💬 Powerful Questions for Bee

Demonstrate Bee's capabilities with these queries:

**Threat Analysis**:
- "What are the top 5 attack vectors this week?"
- "Are there any anomalies in today's traffic?"
- "Which honey jar is most active right now?"

**Security Posture**:
- "How secure is my current configuration?"
- "What vulnerabilities should I prioritize?"
- "Suggest improvements for my honey jar network"

**Operational Intelligence**:
- "Generate a security report for the last 24 hours"
- "What patterns indicate coordinated attacks?"
- "Help me configure a web application honey jar"

---

## 🎁 Bonus Features (If Time Permits)

### Advanced Capabilities
1. **Multi-honey jar Correlation**: Show attacks across different honey jars
2. **Custom AI Training**: Demonstrate uploading custom threat data
3. **API Integration**: Quick curl command to query Bee programmatically
4. **Automated Responses**: Show webhook configuration for alerts

### Community Features
1. **Marketplace Preview**: Browse available honey jar templates
2. **Threat Intelligence Sharing**: (If configured) Show community feeds
3. **Plugin System**: Demonstrate adding a custom analyzer

---

## 🚨 Common Demo Issues & Solutions

**Bee Shows Offline**:
- Refresh the page (Ctrl+F5)
- Check LLM service: `msting status llm`

**No Attack Data**:
- Run attack simulator: `./scripts/simulate_attacks.sh`
- Import sample data: `./scripts/import_demo_data.sh`

**Slow AI Responses**:
- First query loads the model (normal)
- Subsequent queries are much faster
- Switch to a smaller model (tinyllama) for demos

---

## 📝 Post-Demo Follow-up

### For Technical Audiences
- Show the API documentation
- Demonstrate custom integration possibilities
- Discuss architecture and deployment options

### For Security Teams
- Emphasize compliance features
- Show audit logs and reporting
- Discuss threat intelligence sharing

### For Executives
- ROI: Automated threat analysis saves hours
- Risk reduction through AI-powered insights
- Future roadmap and enterprise features

---

## 🔗 Resources

- **Full Documentation**: `/docs/README.md`
- **API Reference**: `https://localhost:8443/api/docs`
- **Community**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Support**: `support@sting-ce.com`

---

*Remember: This is a prototype demonstrating the future of AI-powered honey jar intelligence. Your feedback shapes the production release!*

## 🎯 Quick Demo Checklist

- [ ] System is running (`msting status`)
- [ ] Admin account created
- [ ] At least one honey jar deployed
- [ ] Bee chat is online
- [ ] Sample attack data available
- [ ] Browser accepts self-signed cert
- [ ] Presenter mode ready (larger fonts)

**Happy Demonstrating! 🐝✨**