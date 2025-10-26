# Public Bee Service - Setup Guide

**AI-as-a-Service Chat API Platform**

## Overview

The Public Bee service transforms STING into an AI-as-a-Service platform, allowing organizations to create custom chatbots powered by their own knowledge bases (Honey Jars). Think of it as enabling organizations to spin up their own ChatGPT-like interfaces trained on their specific data.

## 🐝 Bee Name Suggestions for Branding

### Current Options:
- **Worker Bee** - Task-focused, reliable assistant
- **Queen Bee** - Premium/enterprise tier bots
- **Nectar** - Sweet, helpful AI assistant  
- **Pollen** - Knowledge spreader
- **Hive Mind** - Collective intelligence service
- **Buzz Bot** - Dynamic, conversational
- **Honey Helper** - Friendly, supportive assistant
- **Scout Bee** - Information discoverer
- **Guard Bee** - Security-focused bots
- **Drone** - Specialized task bots

### Recommended: **"Nectar Bots"**
- Natural extension of Honey Jar terminology
- Implies sweetness, helpfulness, and value
- Easy to brand and market
- Works for both internal and customer-facing contexts

## Use Cases

### Healthcare Office
- **"MedBot"**: Trained on appointment scheduling, insurance policies, procedures
- Answers patient questions 24/7
- Reduces front desk call volume

### Law Firm  
- **"LegalAssist"**: Trained on practice areas, FAQ, legal processes
- Provides initial client guidance
- Streamlines intake processes

### University
- **"CampusGuide"**: Trained on courses, policies, campus information
- Student support chatbot
- Reduces administrative workload

### Corporate IT
- **"TechSupport"**: Trained on troubleshooting docs, company procedures
- First-line support automation
- Knowledge base accessibility

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   STING Admin   │───▶│   Public Bee     │◄───│  End Users      │
│   (Configure)   │    │   API Service    │    │  (Chat)         │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│  Honey Reserve  │    │  Chat Interface  │
│ (Knowledge Base)│    │   (Embeddable)   │
└─────────────────┘    └──────────────────┘
```

## Features

### Core Capabilities
- **Custom Bot Creation**: Name, brand, and configure bots per organization
- **Knowledge Integration**: Select specific Honey Jars for each bot
- **API Access**: RESTful endpoints for integration
- **Embeddable Widgets**: Simple script tags for websites
- **Rate Limiting**: Control usage per API key
- **Analytics**: Usage tracking and conversation metrics

### Security Features
- **API Key Authentication**: Secure access control
- **Rate Limiting**: Prevent abuse and control costs
- **PII Filtering**: Automatic removal of sensitive data
- **Content Filtering**: Profanity and inappropriate content blocking
- **Domain Whitelisting**: Control where widgets can be embedded

### Scaling Features
- **LangChain Integration**: Advanced conversation management
- **Memory Management**: Persistent conversation context
- **Vector Store**: Efficient knowledge retrieval
- **Multi-tenant**: Isolated bot configurations

## Installation

### Prerequisites
- STING CE fully installed and running
- Admin access to STING dashboard
- Docker Compose environment

### Enable Public Bee Service

1. **Update Configuration**:
```yaml
# conf/config.yml
public_bee:
  enabled: true
  port: 8092
  demo_mode: true
  create_demo_bot: true
```

2. **Start Service**:
```bash
./manage_sting.sh update public-bee
```

3. **Verify Installation**:
```bash
curl -k https://localhost:8092/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "public-bee",
  "version": "1.0.0",
  "demo_bot_available": true
}
```

## Quick Start Demo

### Default STING Assistant Bot

Public Bee includes a demo bot pre-configured with STING platform documentation:

- **Bot ID**: `sting-assistant`  
- **Name**: "STING Assistant"
- **Training Data**: STING platform documentation
- **API Key**: Auto-generated (check admin panel)

### Test the Demo Bot

```bash
# Get bot information
curl -k https://localhost:8092/api/public/bots/sting-assistant

# Send a test message
curl -k -X POST https://localhost:8092/api/public/chat/sting-assistant/message \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "How do I install STING?",
    "session_id": "test-session-123"
  }'
```

### Embed on Website

```html
<!-- Add to your website -->
<div id="sting-assistant-chat"></div>
<script src="https://localhost:8092/widget/sting-assistant.js"></script>
<script>
  STINGChat.init({
    apiKey: 'YOUR_API_KEY',
    botId: 'sting-assistant',
    container: 'sting-assistant-chat'
  });
</script>
```

## Admin Configuration

### Access Admin Panel

1. Navigate to STING Dashboard
2. Go to **Admin** → **Public Bots**
3. Create and manage your bots

### Create Custom Bot

1. **Basic Information**:
   - Bot Name: "Customer Support Bot"
   - Description: "Helps customers with product questions"
   - Display Name: "SupportBot"

2. **Knowledge Configuration**:
   - Select relevant Honey Jars
   - Configure system prompt
   - Set response filtering

3. **API Configuration**:
   - Generate API keys
   - Set rate limits
   - Configure domain whitelist

4. **Advanced Settings**:
   - Custom branding
   - Response templates
   - Analytics preferences

## API Reference

### Authentication
All requests require an API key in the header:
```
X-API-Key: your-api-key-here
```

### Core Endpoints

#### Send Message
```bash
POST /api/public/chat/{bot-id}/message
Content-Type: application/json

{
  "message": "How do I reset my password?",
  "session_id": "user-session-123",
  "context": {
    "user_id": "optional-user-id",
    "metadata": {}
  }
}
```

Response:
```json
{
  "success": true,
  "response": "To reset your password, visit the login page and click 'Forgot Password'...",
  "session_id": "user-session-123",
  "bot_id": "support-bot",
  "sources": [
    {
      "document": "password-reset-guide.pdf",
      "relevance": 0.95
    }
  ]
}
```

#### Get Bot Info
```bash
GET /api/public/bots/{bot-id}/info
```

#### List Available Bots (Admin)
```bash
GET /api/public/bots/list
Authorization: Admin-API-Key
```

## Business Model Integration

### Pricing Tiers
- **Basic**: 1,000 messages/month per bot
- **Professional**: 10,000 messages/month + analytics
- **Enterprise**: Unlimited + white-label + priority support

### Usage Tracking
- Message count per API key
- Response time metrics
- User satisfaction ratings
- Knowledge base effectiveness

### Monetization Features
- Pay-per-conversation billing
- Subscription management
- Usage analytics dashboard
- Customer portal integration

## Security Considerations

### API Key Management
- Rotate keys regularly
- Use different keys for different environments
- Monitor key usage patterns

### Content Filtering
- Enable PII detection for compliance
- Configure profanity filters
- Review conversation logs

### Access Control
- Domain whitelist for embeddable widgets
- IP-based access restrictions
- Rate limiting per key/IP combination

## Scaling Recommendations

### For High Volume (1000+ conversations/day)
1. Enable LangChain service
2. Configure Redis for conversation memory
3. Use horizontal pod autoscaling
4. Implement CDN for widget delivery

### For Enterprise Deployment
1. Separate database for Public Bee data
2. Load balancer for multiple instances
3. External monitoring and alerting
4. Backup and disaster recovery

## Troubleshooting

### Common Issues

#### Bot Not Responding
- Check API key validity
- Verify bot is enabled
- Check Honey Jar accessibility
- Review rate limit status

#### Slow Response Times
- Check knowledge service health
- Review Honey Jar size and complexity
- Monitor memory usage
- Consider caching frequently asked questions

#### Widget Not Loading
- Verify domain whitelist configuration
- Check CORS settings
- Ensure HTTPS certificate validity
- Test API key permissions

## Next Steps

1. **Create Your First Bot**: Use the demo as a template
2. **Upload Knowledge Base**: Add your organization's documents to a Honey Jar
3. **Test Integration**: Try the API endpoints with your data
4. **Deploy Widget**: Embed on your website or application
5. **Monitor Usage**: Review analytics and optimize performance

## Support

- **Documentation**: Full API reference available at `/docs`
- **Community**: STING Discord server
- **Enterprise**: Contact support for dedicated assistance

---

*Ready to transform your knowledge into an intelligent chatbot service? Let's get your Public Bee buzzing!* 🐝