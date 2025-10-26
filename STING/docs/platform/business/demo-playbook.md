# STING-CE Interactive Demo Playbook 🎭
*Your Guide to Delivering Impactful STING Demonstrations*

## Purpose
This playbook provides structured scenarios, talking points, and troubleshooting guides for presenting STING-CE effectively to different audiences.

---

## 🎬 Pre-Demo Setup Checklist

### Technical Preparation
```bash
# 1. Verify all services are healthy
msting status

# 2. Clear any stale data
msting clean --cache

# 3. Import fresh demo data
./scripts/import_demo_data.sh

# 4. Start attack simulator (background)
./scripts/simulate_attacks.sh --subtle &

# 5. Pre-load AI models
curl -X POST http://localhost:8086/preload -d '{"model": "phi3"}'
```

### Environment Setup
- [ ] External monitor connected and mirrored
- [ ] Browser zoom at 125% for visibility
- [ ] Terminal with larger font (16pt+)
- [ ] Notifications disabled
- [ ] Desktop cleaned of sensitive items
- [ ] Backup demo environment ready

---

## 🎯 Audience-Specific Demos

### For Security Teams (Technical)

**Opening Hook** (30 seconds):
> \"How many hours does your team spend manually analyzing honey jar logs? What if AI could do that instantly?\"

**Flow**:
1. Start with live attack dashboard
2. Show real-time threat detection
3. Deep dive into Bee's analysis capabilities
4. Demonstrate API integration

**Key Points**:
- Emphasize automation of tedious tasks
- Show correlation across multiple honey jars
- Highlight custom rule creation
- Demonstrate threat hunting queries

**Bee Questions to Demo**:
```
"Show me all SQL injection attempts in the last 24 hours"
"Which attacks are using known CVE exploits?"
"Generate a YARA rule for this attack pattern"
"What's the geographic distribution of threats?"
```

### For Executives (Strategic)

**Opening Hook** (30 seconds):
> \"STING transforms honey jars from passive sensors into active intelligence agents, reducing threat analysis time by 90%.\"

**Flow**:
1. Dashboard overview - focus on metrics
2. Show automated threat reports
3. Demonstrate cost savings through automation
4. Preview roadmap features

**Key Points**:
- ROI and time savings
- Reduced false positives
- Compliance and audit trails
- Competitive advantages

**Bee Questions to Demo**:
```
"Generate an executive summary of this week's threats"
"What's our security posture score?"
\"Show ROI metrics for honey jar deployment\"
"What threats require immediate attention?"
```

### For Developers (Technical Integration)

**Opening Hook** (30 seconds):
> "STING provides a complete API-first platform with built-in AI, so you can integrate threat intelligence into your applications in minutes."

**Flow**:
1. Quick UI tour
2. Jump to API documentation
3. Live API calls via curl
4. Show webhook integrations

**Key Points**:
- RESTful API design
- WebSocket real-time streams
- SDK availability
- Plugin architecture

**Code Snippets to Demo**:
```bash
# Query Bee via API
curl -X POST https://localhost:5050/api/bee/query \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "latest threats"}'

# Stream honey jar events
wscat -c wss://localhost:5050/api/events/stream
```

---

## 📚 Scenario Scripts

### Scenario 1: "The Friday Afternoon Attack"
**Setup**: Simulated SSH brute force attack
**Duration**: 3 minutes

**Script**:
1. \"It's Friday afternoon, and your honey jar just detected unusual activity...\"
2. Navigate to honey jar dashboard
3. "Instead of digging through logs, let's ask Bee what's happening"
4. Ask Bee: "Analyze the SSH attacks from the last 5 minutes"
5. "Bee instantly identifies this as a coordinated botnet attack"
6. Ask Bee: "Block these attackers and notify the team"
7. Show automated response execution

**Talking Points**:
- Traditional method: 30-60 minutes of analysis
- With STING: Instant insights and response
- Bee learns from each incident

### Scenario 2: "The Unknown Threat"
**Setup**: Novel attack pattern not in signatures
**Duration**: 3 minutes

**Script**:
1. \"Your honey jar captured something unusual...\"
2. Show honey jar log with obfuscated payload
3. Ask Bee: "What is this encoded payload trying to do?"
4. Bee deobfuscates and explains the attack
5. Ask Bee: "Have we seen similar techniques before?"
6. Bee correlates with historical data
7. "Let's create a detection rule"
8. Ask Bee: "Generate a detection rule for this pattern"

**Talking Points**:
- AI understands context beyond signatures
- Automatic correlation with threat intelligence
- Proactive defense creation

### Scenario 3: "The Compliance Audit"
**Setup**: Auditor needs security reports
**Duration**: 2 minutes

**Script**:
1. "An auditor just asked for last month's security incidents..."
2. Ask Bee: "Generate a compliance report for last month"
3. Show professional PDF generation
4. "They want specifics about data protection..."
5. Ask Bee: "Show our data encryption and retention policies"
6. Navigate to automated audit logs

**Talking Points**:
- Compliance-ready reporting
- Complete audit trails
- Automated documentation

---

## 🔧 Troubleshooting Live Demo Issues

### Issue: Bee Shows "Offline"
**Quick Fix**:
```bash
# Check LLM service
msting status llm

# Restart if needed
msting restart chatbot
```
**Backup Plan**: Use the test endpoint that bypasses auth

### Issue: No Attack Data Showing
**Quick Fix**:
```bash
# Inject sample attacks
./scripts/quick_demo_attacks.sh
```
**Backup Plan**: Have screenshots ready

### Issue: Slow AI Responses
**Quick Fix**:
- Switch to smaller model: "Let me switch to our speed-optimized model"
- Pre-submit the query before demo
**Backup Plan**: Explain first-load latency is normal

### Issue: Authentication Problems
**Quick Fix**:
- Use backup admin account
- Demo with test user
**Backup Plan**: Focus on features, mention "enterprise SSO integration"

---

## 💡 Power Tips

### Engagement Techniques
1. **Ask the audience**: \"What's your biggest honey jar challenge?\"
2. **Make it interactive**: "What would you ask Bee?"
3. **Relate to their pain**: "How long does this take you today?"

### Handling Questions

**"Is the AI really running locally?"**
> "Absolutely. Let me disconnect from the internet..." [disable wifi] "...and Bee still works perfectly. Your data never leaves your infrastructure."

**"How accurate is the AI?"**
> "Bee combines multiple models with your threat intelligence. It's continuously learning from your specific environment, making it more accurate than generic solutions."

**"What about false positives?"**
> "Great question. Bee learns from corrections. Let me show you..." [demonstrate feedback loop]

**"Can it integrate with our SIEM?"**
> "Yes! We have webhooks, syslog, and API integration. Here's a Splunk integration example..."

### Memorable Moments
1. **The "Wow" Query**: Ask Bee to explain a complex encoded attack
2. **The Time Saver**: Generate a month's report in seconds
3. **The Integration**: Show real-time Slack alerts
4. **The Learning**: Correct Bee and show it immediately improves

---

## 📊 Metrics to Emphasize

- **90% reduction** in threat analysis time
- **24/7 intelligent monitoring** without human intervention
- **Zero false positives** after training period
- **100% on-premise** - complete data sovereignty
- **5-minute deployment** for new honey jars

---

## 🎁 Leave-Behinds

After your demo, provide:

1. **Quick Start Guide** - Single page setup instructions
2. **API Examples** - Postman collection or curl scripts
3. **ROI Calculator** - Spreadsheet showing time/cost savings
4. **Trial License** - 30-day full access
5. **Custom Demo Recording** - Personalized for their use case

---

## 📝 Demo Feedback Form

Always gather feedback:

```markdown
## STING Demo Feedback

**What impressed you most?**
[ ] AI-powered analysis
[ ] Ease of use
[ ] Integration capabilities
[ ] Security features
[ ] Real-time responses

**What concerns do you have?**
[ ] Technical complexity
[ ] Resource requirements
[ ] Integration effort
[ ] Training needs
[ ] Cost

**Next steps interest:**
[ ] Technical deep dive
[ ] Proof of concept
[ ] Pricing discussion
[ ] Reference calls
[ ] Trial deployment
```

---

## 🚀 Post-Demo Actions

### Immediate (Same Day)
1. Send thank you with demo recording
2. Share relevant documentation links
3. Answer any outstanding questions
4. Schedule follow-up meeting

### Follow-up (Within Week)
1. Provide custom integration examples
2. Share success stories from similar organizations
3. Offer technical workshop
4. Introduce implementation team

---

## 🎯 Success Metrics

Track your demo effectiveness:
- **Engagement**: Questions asked during demo
- **Interest**: Follow-up meetings scheduled
- **Technical**: POC requests
- **Business**: Budget discussions initiated

---

*Remember: Every demo is an opportunity to show how STING transforms cybersecurity from reactive to proactive. Make it memorable!*

**Demo with confidence! 🐝💪**