# Nectar Bot Chat - Quick Start Guide

Get your Nectar Bots chatting in 5 minutes! ⚡

## 🚀 Quick Setup

### Step 1: Run Database Migration

```bash
cd /Users/captain-wolf/Documents/GitHub/STING-CE/STING

# Run migration to add slug field
python3 scripts/db_migrations/002_add_nectar_bot_slug.py
```

Expected output:
```
🔄 Starting migration 002: Add slug field to nectar_bots
  ➜ Adding slug column...
  ✅ Slug column added
  ➜ Generating slugs for existing bots...
    • Demo Bot -> demo-bot-8a7f92c3
  ✅ Generated slugs for 1 bots
  ➜ Making slug column NOT NULL...
  ✅ Slug column set to NOT NULL
  ➜ Adding unique constraint on slug...
  ✅ Unique constraint added
  ➜ Adding index on slug...
  ✅ Index created
✅ Migration 002 completed successfully!
```

### Step 2: Update Services

```bash
# Update backend (app service)
./manage_sting.sh update app

# Update frontend
./manage_sting.sh update frontend
```

### Step 3: Create a Test Public Bot

#### Option A: Via Web UI

1. Navigate to https://localhost:8443/dashboard/nectar-bots
2. Click "Create New Bot"
3. Fill in:
   - **Name**: "Test Support Bot"
   - **Description**: "Quick test bot"
   - **✅ Public**: Check this box!
   - **System Prompt**: "You are a helpful assistant."
4. Click Save
5. **Copy public URL** from bot card

#### Option B: Via API

```bash
curl -k -X POST https://localhost:5050/api/nectar-bots \
  -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Support Bot",
    "description": "Quick test bot for POC",
    "is_public": true,
    "system_prompt": "You are a helpful AI assistant. Answer questions clearly and concisely.",
    "honey_jar_ids": [],
    "handoff_enabled": true,
    "handoff_keywords": ["help", "human", "agent"]
  }'
```

Response will include:
```json
{
  "bot": {
    "slug": "test-support-bot-abc12345",
    "public_url": "/bot/test-support-bot-abc12345",
    "embed_url": "/bot/test-support-bot-abc12345/embed"
  }
}
```

### Step 4: Test It!

**Open the public URL in your browser:**
```
https://localhost:8443/bot/test-support-bot-abc12345
```

**Or test the API:**
```bash
# Chat with the bot
curl -k -X POST https://localhost:5050/api/nectar-bots/public/test-support-bot-abc12345/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello! Can you help me?"
  }'
```

## 🎯 POC Demo Scenario

### Create a "STING Support Bot"

```bash
# 1. Create bot with STING knowledge
curl -k -X POST https://localhost:5050/api/nectar-bots \
  -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "STING Support Bot",
    "description": "Get help with STING features and setup",
    "is_public": true,
    "system_prompt": "You are a helpful STING support assistant. Help users understand STING features like Nectar Bots, Honey Jars, authentication, and security. Be friendly and concise.",
    "honey_jar_ids": [],
    "handoff_enabled": true,
    "handoff_keywords": ["developer", "technical support", "bug", "error"]
  }'

# 2. Copy the slug from response
# Example: sting-support-bot-f3a8c291

# 3. Share the URL
echo "Public URL: https://localhost:8443/bot/sting-support-bot-f3a8c291"

# 4. Test with sample questions
curl -k -X POST https://localhost:5050/api/nectar-bots/public/sting-support-bot-f3a8c291/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What are Nectar Bots?"}'
```

## 🔧 Troubleshooting

### Migration Fails

**Error**: `sqlalchemy.exc.OperationalError`

**Fix**:
```bash
# Ensure database is running
./manage_sting.sh status

# Check database connection
docker exec -it sting-ce-postgres psql -U sting_user -d sting_app -c '\dt'

# Retry migration
python3 scripts/db_migrations/002_add_nectar_bot_slug.py
```

### Bot Returns 404

**Error**: `{"error": "Public bot not found"}`

**Causes**:
1. Bot is not public (`is_public = False`)
2. Bot is not active (`status != 'active'`)
3. Wrong slug

**Fix**:
```bash
# Check bot in database
docker exec -it sting-ce-postgres psql -U sting_user -d sting_app \
  -c "SELECT id, name, slug, is_public, status FROM nectar_bots;"

# Make bot public
curl -k -X PUT https://localhost:5050/api/nectar-bots/<BOT_ID> \
  -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
  -H "Content-Type: application/json" \
  -d '{"is_public": true}'
```

### Chat Service Unavailable

**Error**: `{"error": "Chat service connection failed"}`

**Fix**:
```bash
# Check services
./manage_sting.sh status

# Restart chatbot service
./manage_sting.sh restart chatbot

# Check logs
docker logs sting-ce-chatbot --tail 100
```

### Rate Limit Exceeded

**Error**: `{"error": "Rate limit exceeded"}` (429)

**Cause**: Too many requests from same IP

**Fix**:
```bash
# Wait for rate limit to reset (1 hour)
# OR increase bot rate limits

curl -k -X PUT https://localhost:5050/api/nectar-bots/<BOT_ID> \
  -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
  -H "Content-Type: application/json" \
  -d '{
    "rate_limit_per_hour": 1000,
    "rate_limit_per_day": 10000
  }'
```

## 📊 Quick Verification

### Check Everything Works

```bash
# 1. Database migration applied?
docker exec -it sting-ce-postgres psql -U sting_user -d sting_app \
  -c "\d nectar_bots" | grep slug
# Should show: slug | character varying(255) | not null

# 2. Backend routes registered?
docker logs sting-ce-app --tail 100 | grep "nectar-bots"
# Should show route registrations

# 3. Frontend component loaded?
curl -k https://localhost:8443/bot/test-bot-123 2>&1 | grep "PublicBotChat"
# Should NOT return 404

# 4. Create and test bot
BOT_SLUG=$(curl -k -X POST https://localhost:5050/api/nectar-bots \
  -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
  -H "Content-Type: application/json" \
  -d '{"name":"Quick Test","is_public":true,"system_prompt":"Hi!"}' \
  | grep -o '"slug":"[^"]*"' | cut -d'"' -f4)

echo "Testing bot: $BOT_SLUG"

curl -k -X POST "https://localhost:5050/api/nectar-bots/public/$BOT_SLUG/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}' | jq .response

# Should return bot's response
```

## 🎨 Customization Ideas

### Create Specialized Bots

**Customer Support Bot:**
```json
{
  "name": "Customer Support",
  "system_prompt": "You are a friendly customer support agent. Help users with common questions about products, shipping, and returns.",
  "honey_jar_ids": ["faq-jar", "product-catalog-jar"],
  "handoff_keywords": ["refund", "urgent", "manager", "complaint"]
}
```

**Technical Documentation Bot:**
```json
{
  "name": "Developer Helper",
  "system_prompt": "You are a technical documentation assistant. Help developers find API references, code examples, and troubleshooting guides.",
  "honey_jar_ids": ["api-docs-jar", "code-examples-jar"],
  "handoff_keywords": ["bug", "doesn't work", "error", "broken"]
}
```

**Sales Assistant Bot:**
```json
{
  "name": "Sales Assistant",
  "system_prompt": "You are a knowledgeable sales assistant. Help customers find the right products and answer questions about features and pricing.",
  "honey_jar_ids": ["product-catalog-jar", "pricing-jar"],
  "handoff_keywords": ["buy now", "purchase", "quote", "pricing"]
}
```

## 📱 Sharing Your Bot

### Direct Link
```
https://your-domain.com/bot/your-bot-slug-abc123
```

### QR Code
Generate at: https://qr-code-generator.com
- Enter: `https://your-domain.com/bot/your-bot-slug`
- Download and share!

### Embed (Future)
```html
<iframe
  src="https://your-domain.com/bot/your-bot-slug/embed"
  width="400"
  height="600"
  frameborder="0"
></iframe>
```

## 🚀 Next Steps

1. ✅ **Set up complete** - Migration run, services updated
2. ✅ **Test bot created** - Public URL working
3. 📝 **Create real bots** - Add honey jars, customize prompts
4. 📊 **Monitor analytics** - Check Nectar Bots page for stats
5. 🔗 **Share URLs** - Give access to real users
6. 🎯 **Gather feedback** - See what works for POC

## 📚 Additional Resources

- **Full Documentation**: `docs/platform/nectar-bots/NECTAR_BOT_CHAT_AND_PUBLIC_URLS.md`
- **Implementation Summary**: `docs/platform/nectar-bots/IMPLEMENTATION_SUMMARY_CHAT.md`
- **Main Dev Guide**: `CLAUDE.md`

---

**Ready to chat with your bots!** 🤖💬

Need help? Check the troubleshooting section or review the full documentation.
