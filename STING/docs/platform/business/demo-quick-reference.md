# STING Demo Quick Reference Card 🎯

## 🚀 Quick URLs
- **Dashboard**: https://localhost:8443
- **API Docs**: https://localhost:5050/api/docs
- **Bee Direct**: http://localhost:8888/docs
- **Mailpit**: http://localhost:8025

## 🔑 Demo Credentials
```
Admin User: demo@sting-ce.com
Password: DemoPass123!
API Token: demo-token-2024
```

## 🐝 Essential Bee Queries

### Quick Wins
```
"What's happening right now?"
"Show me today's threats"
"Am I under attack?"
"Generate a security summary"
```

### Technical Deep Dives
```
"Analyze SSH attacks from the last hour"
"Find all SQL injection attempts"
"Which IPs are most malicious?"
"Show me attack patterns by country"
"Generate detection rules for recent threats"
```

### Executive Queries
```
"What's our security score?"
"Show me this week's threat summary"
"What are my top risks?"
"Generate a compliance report"
"Calculate time saved through automation"
```

## ⚡ Quick Commands

### Service Management
```bash
# Check all services
msting status

# Restart a service
msting restart bee

# View logs
msting logs bee --tail 50

# Clear caches
msting clean --cache
```

### Demo Data
```bash
# Import demo data
./scripts/import_demo_data.sh

# Start attack simulator
./scripts/simulate_attacks.sh --subtle

# Generate burst attack
./scripts/simulate_attacks.sh --interval 1
```

## 🎪 Demo Flow Cheatsheet

### 5-Minute Lightning Demo
1. Dashboard overview (30s)
2. Create honey jar (1m)
3. Show live attacks (1m)
4. Ask Bee for analysis (1.5m)
5. Generate report (1m)

### 10-Minute Standard Demo
1. Login & navigation (1m)
2. Honey Jar creation (2m)
3. Live attack monitoring (2m)
4. Bee AI analysis (3m)
5. Security features (1m)
6. Q&A (1m)

### 30-Minute Technical Deep Dive
1. Architecture overview (5m)
2. Full honey jar setup (5m)
3. AI capabilities demo (10m)
4. API integration (5m)
5. Custom scenarios (5m)

## 🔧 Troubleshooting

### Bee Offline
```bash
msting restart chatbot
# Wait 10 seconds
curl http://localhost:8888/health
```

### No Attack Data
```bash
# Quick fix
curl -X POST http://localhost:5050/api/demo/attacks
```

### Slow Responses
```bash
# Pre-load model
curl -X POST http://localhost:8086/models/load \
  -d '{"model": "tinyllama"}'
```

## 💡 Talking Points

### Security Teams
- "Reduces alert fatigue by 90%"
- "AI understands context, not just signatures"
- "Automated threat correlation"

### Executives  
- "ROI within 30 days"
- "24/7 intelligent monitoring"
- "Compliance-ready reporting"

### Developers
- "RESTful API for everything"
- "Webhooks for real-time events"
- "Open plugin architecture"

## 🎯 Memorable Demos

### The "Wow" Moment
Ask Bee: "Decode this base64 payload and explain the attack"
```
echo "cm0gLXJmIC8qICYmIGN1cmwgaHR0cDovL21hbHdhcmUuY29tL2JvdC5zaCA+IC90bXAvYiAmJiBzaCAvdG1wL2I=" | base64 -d
```

### The Time Saver
"Generate last month's security audit report" - Watch it appear in seconds

### The Integration
Show Slack notification for critical threat

## 📱 Mobile Demo
- Use tablet for better visibility
- Pre-load all pages
- Have mobile hotspot backup
- Screenshot backup ready

## 🎬 Screen Recording
```bash
# Start recording (macOS)
Cmd+Shift+5

# Best settings:
- 1920x1080 resolution
- Show touches enabled
- Microphone on
- 30 fps
```

## 🔗 Share After Demo
1. Demo recording link
2. Trial account credentials
3. Documentation: https://docs.sting-ce.com
4. GitHub: https://github.com/sting-ce
5. Support: support@sting-ce.com

---
*Keep this card handy during demos! Last updated: $(date)*