# Nectar Bot Chat & Public URLs

## Overview

This feature enables users to chat with and test Nectar Bots, both privately (authenticated) and publicly (via shareable URLs). It transforms Nectar Bots from configuration-only entities into fully functional, testable chatbots that can be deployed publicly.

## Key Features

### 🔐 Private Bot Chat
- **Authenticated Access**: Bot owners and admins can test bots within STING
- **Bot Selector in Bee Chat**: Switch between Default Bee and user's Nectar Bots
- **Full Integration**: Uses existing Bee Chat infrastructure with bot-specific context

### 🌐 Public Bot URLs
- **Shareable Links**: Each public bot gets a unique, shareable URL
- **No Authentication Required**: Anyone with the URL can chat with the bot
- **Rate Limiting**: IP-based rate limiting prevents abuse
- **DNS Ready**: URLs are designed for custom domain mapping

### 📊 Analytics & Tracking
- **Usage Tracking**: All conversations tracked for analytics
- **Handoff Detection**: Automatic escalation based on confidence/keywords
- **Performance Metrics**: Response time, confidence scores, conversation counts

## Architecture

### Backend Endpoints

#### Authenticated Bot Chat
```
POST /api/nectar-bots/<bot_id>/chat
Authorization: Required (session or API key)
Access: Bot owner or admin only

Request:
{
  "message": "Hello bot!",
  "conversation_id": "uuid-string" // optional
}

Response:
{
  "response": "Bot's response",
  "confidence_score": 0.85,
  "conversation_id": "uuid-string",
  "timestamp": "2025-10-01T12:00:00Z"
}
```

#### Public Bot Endpoints
```
GET /api/nectar-bots/public/<slug>
Authorization: None

Response:
{
  "bot": {
    "id": "uuid",
    "name": "Customer Support Bot",
    "slug": "customer-support-bot-abc123",
    "description": "Helpful customer support assistant",
    "public_url": "/bot/customer-support-bot-abc123",
    "embed_url": "/bot/customer-support-bot-abc123/embed"
  }
}
```

```
POST /api/nectar-bots/public/<slug>/chat
Authorization: None
Rate Limiting: By IP address

Request:
{
  "message": "I need help",
  "conversation_id": "uuid-string" // optional
}

Response:
{
  "response": "How can I assist you?",
  "confidence_score": 0.92,
  "conversation_id": "uuid-string"
}
```

### Frontend Routes

#### Public Bot Pages
- **Full Page**: `/bot/<slug>`
- **Embed Mode**: `/bot/<slug>/embed` or `/bot/<slug>?embed=true`

#### Components
- **PublicBotChat.jsx**: Standalone public bot chat interface
- **NectarBotManager.jsx**: Enhanced with public URL display and test buttons
- **BeeChat.jsx**: (Future) Bot selector dropdown for private bot testing

## Database Schema Updates

### NectarBot Model - New Fields

```python
class NectarBot(db.Model):
    # ... existing fields ...

    slug = Column(String(255), unique=True, nullable=False, index=True)
    # URL-friendly identifier (e.g., "customer-support-bot-abc123")

    @property
    def public_url(self):
        """Returns: /bot/<slug> if public, None if private"""

    @property
    def embed_url(self):
        """Returns: /bot/<slug>/embed if public, None if private"""
```

### Slug Generation
```python
@staticmethod
def generate_slug(name):
    """
    Converts bot name to URL-friendly slug
    Example: "Customer Support Bot" -> "customer-support-bot-abc12345"
    """
    slug = re.sub(r'[^\w\s-]', '', name.lower())
    slug = re.sub(r'[-\s]+', '-', slug).strip('-')
    random_suffix = secrets.token_hex(4)  # 8 char hex
    return f"{slug}-{random_suffix}"
```

## Usage Guide

### Creating a Public Bot

1. **Navigate to Nectar Bots page** (`/dashboard/nectar-bots`)
2. **Create or edit a bot**
3. **Enable "Public" checkbox** in bot configuration
4. **Save bot**
5. **Copy public URL** from bot card

### Testing a Bot

#### Method 1: Test Button (Quick)
1. Click the **Test** button (test tube icon) on bot card
2. For public bots: Opens public chat page in new tab
3. For private bots: Opens alert (future: navigates to Bee Chat with bot selected)

#### Method 2: Bee Chat (Private Bots - Future)
1. Navigate to **Bee Chat**
2. Click **bot selector dropdown** in header
3. Select desired Nectar Bot
4. Chat interface switches to bot persona
5. All messages routed to selected bot

### Sharing a Public Bot

#### Direct URL
```
https://yourdomain.com/bot/customer-support-bot-abc123
```

#### Embed Code (Future)
```html
<iframe
  src="https://yourdomain.com/bot/customer-support-bot-abc123/embed"
  width="400"
  height="600"
  frameborder="0"
></iframe>
```

### Custom Domain Mapping

Public bots are designed for custom domain mapping:

1. **CNAME Setup**:
   ```
   support.yourcompany.com -> sting.yourdomain.com
   ```

2. **Redirect Configuration**:
   ```nginx
   # Nginx example
   location / {
     proxy_pass https://sting.yourdomain.com/bot/customer-support-bot-abc123;
   }
   ```

3. **Result**:
   - Users visit: `support.yourcompany.com`
   - Bot serves: Customer Support Bot
   - STING branding can be hidden in embed mode

## Rate Limiting

### Private Bots (Authenticated)
- **Per User**: Based on user_id from session
- **Hourly Limit**: Configurable per bot (default: 100 req/hour)
- **Daily Limit**: Configurable per bot (default: 1000 req/day)

### Public Bots (Unauthenticated)
- **Per IP Address**: Based on `request.remote_addr`
- **Hourly Limit**: Configurable per bot (default: 100 req/hour)
- **Daily Limit**: Configurable per bot (default: 1000 req/day)
- **429 Response**: Returns when limit exceeded

## Handoff System

When enabled, bots can automatically escalate to human agents:

### Triggers
1. **Low Confidence**: `confidence_score < handoff_confidence_threshold`
2. **Keywords Detected**: User message contains handoff keywords

### Configuration
```python
bot = NectarBot(
    handoff_enabled=True,
    handoff_keywords=["help", "human", "support", "escalate"],
    handoff_confidence_threshold=0.6
)
```

### Handoff Flow
1. Trigger detected during conversation
2. `NectarBotHandoff` record created with:
   - Conversation history
   - Trigger reason
   - Urgency level
   - User info
3. Admin notified (future: email/webhook)
4. Admin can view and resolve in Nectar Bots → Handoffs tab

## Analytics

All bot interactions are tracked in `NectarBotUsage` table:

### Metrics Tracked
- Total conversations
- Total messages
- Average confidence score
- Average response time
- Knowledge matches from honey jars
- Rate limit hits

### Accessing Analytics
1. Navigate to **Nectar Bots** page
2. View **overview analytics** at top
3. Click individual bot for **detailed analytics**

## Security Considerations

### Public Bots
- ✅ **No Authentication Required**: Anyone can use
- ✅ **Rate Limited**: Prevents abuse
- ✅ **No User Data Exposed**: Only bot configuration
- ⚠️ **Honey Jar Access**: Public bots can access configured honey jars
- ⚠️ **System Prompt Visible**: Via API inspection

### Private Bots
- ✅ **Authentication Required**: Session or API key
- ✅ **Owner/Admin Only**: Access controlled
- ✅ **Full STING Integration**: All security features apply

### Best Practices
1. **Public Bots**:
   - Don't include sensitive information in system prompts
   - Use public/sanitized honey jars only
   - Monitor usage analytics regularly
   - Set conservative rate limits

2. **Private Bots**:
   - Can use any honey jars
   - Can include internal context in prompts
   - Full audit trail via user sessions

## Migration Guide

### Adding Slug to Existing Bots

Run migration script:
```bash
cd /path/to/STING
python3 scripts/db_migrations/002_add_nectar_bot_slug.py
```

Migration steps:
1. Adds `slug` column (nullable)
2. Generates slugs for all existing bots
3. Makes `slug` NOT NULL
4. Adds unique constraint
5. Creates index for performance

### Rollback
```bash
python3 scripts/db_migrations/002_add_nectar_bot_slug.py --downgrade
```

## Future Enhancements

### Planned Features
1. **Bee Chat Bot Selector**: Dropdown to switch between bots in Bee Chat
2. **Embeddable Widget**: JavaScript snippet for easy embedding
3. **Custom Branding**: Logo, colors, bot avatar customization
4. **Webhook Notifications**: Real-time handoff alerts
5. **Conversation Export**: Download chat transcripts
6. **A/B Testing**: Test multiple bot configurations
7. **Advanced Analytics**: Conversation flow visualization

### POC Priorities
- ✅ Public bot URLs with chat interface
- ✅ Test button for quick testing
- ✅ Public URL display and copy
- 🔄 Bot selector in Bee Chat (in progress)
- 🔄 Test widget in bot management page (in progress)
- ⏳ Embeddable widget
- ⏳ Custom domain examples

## Troubleshooting

### Bot Not Found (404)
**Symptoms**: Public URL returns 404
**Causes**:
- Bot is not public (`is_public = False`)
- Bot is not active (`status != 'active'`)
- Invalid slug

**Fix**:
1. Check bot status in database
2. Verify `is_public = True` and `status = 'active'`
3. Confirm slug matches URL

### Rate Limit Exceeded (429)
**Symptoms**: Requests return 429 error
**Cause**: IP or user exceeded hourly/daily limits

**Fix**:
1. Wait for rate limit window to reset
2. Increase bot rate limits if legitimate traffic
3. Check for bot abuse in analytics

### Chat Service Unavailable (503)
**Symptoms**: Bot status shows "maintenance" or "error"
**Cause**: External AI service or chatbot service offline

**Fix**:
1. Check service health: `./manage_sting.sh status`
2. Restart services: `./manage_sting.sh restart chatbot`
3. Check service logs: `docker logs sting-ce-chatbot`

## Examples

### Creating a Public Support Bot

```python
# Via API
POST /api/nectar-bots
{
  "name": "Customer Support Bot",
  "description": "24/7 customer support assistant",
  "is_public": true,
  "system_prompt": "You are a helpful customer support representative.",
  "honey_jar_ids": ["public-faq-jar-id"],
  "handoff_enabled": true,
  "handoff_keywords": ["agent", "human", "escalate"]
}

# Response includes
{
  "bot": {
    "slug": "customer-support-bot-8a7f92c3",
    "public_url": "/bot/customer-support-bot-8a7f92c3",
    "embed_url": "/bot/customer-support-bot-8a7f92c3/embed"
  }
}
```

### Testing via cURL

```bash
# Get public bot info
curl https://localhost:8443/api/nectar-bots/public/customer-support-bot-8a7f92c3

# Chat with public bot
curl -X POST https://localhost:8443/api/nectar-bots/public/customer-support-bot-8a7f92c3/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello! I need help with my account"}'
```

## See Also

- [Nectar Bot Implementation Summary](./nectar-bot-implementation-summary.md)
- [Nectar Bot Handoff System](./nectar-bot-handoff-system.md)
- [CLAUDE.md](../../../CLAUDE.md) - Main development guide

---

**Last Updated**: 2025-10-01
**Version**: 1.0.0
**Status**: Production Ready (Pending Testing)
