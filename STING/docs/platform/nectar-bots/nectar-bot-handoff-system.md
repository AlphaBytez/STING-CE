# Nectar Bot Handoff System

## Overview

The Nectar Bot Handoff System enables seamless escalation from AI-powered chatbots to human agents when conversations require human intervention. This system differentiates STING CE from Enterprise editions while providing a solid foundation for advanced integrations.

## Architecture

### CE Edition: Internal Handoff
- **Target**: Internal team notifications
- **Method**: STING messaging system
- **Notifications**: In-app alerts to admin users
- **Context Transfer**: Full conversation history included

### Enterprise Edition: External Integration
- **Target**: External helpdesk and communication platforms
- **Method**: Webhook integrations and API calls
- **Supported Platforms**: Slack, Microsoft Teams, PagerDuty, Zendesk, ServiceNow
- **Advanced Features**: Priority routing, skill-based assignment, SLA tracking

## Handoff Triggers

### Automatic Triggers
1. **Confidence Threshold**: AI confidence below configured threshold
2. **Keyword Detection**: Specific phrases indicating need for human help
3. **Escalation Requests**: User explicitly asks for human assistance
4. **Error Patterns**: Repeated failed interactions
5. **Complex Queries**: Multi-step problems beyond AI capability

### Manual Triggers
1. **Admin Override**: Manual escalation by admin users
2. **Bot Command**: Specific commands to trigger handoff
3. **Time-based**: Automatic escalation after extended conversation

## CE Edition Implementation

### Internal Messaging Flow
```
Nectar Bot → Handoff Request → Messaging Service → Admin Notifications
```

### Components
- **Handoff Detector**: Analyzes conversation for handoff triggers
- **Context Collector**: Gathers conversation history and metadata
- **Notification Router**: Sends alerts to appropriate admin users
- **Status Tracker**: Monitors handoff status and responses

### Configuration
```yaml
nectar_bots:
  handoff:
    enabled: true
    mode: "ce_internal"
    triggers:
      confidence_threshold: 0.6
      keywords: ["human help", "speak to person", "escalate"]
      max_conversation_length: 20
    notifications:
      target_roles: ["admin"]
      notification_types: ["in_app", "email"]
      urgency_levels:
        low: "info"
        medium: "warning"
        high: "critical"
```

## Handoff Process

### 1. Detection Phase
```python
def should_trigger_handoff(conversation, bot_response):
    # Check confidence levels
    if bot_response.confidence < config.confidence_threshold:
        return True, "low_confidence"
    
    # Check keyword patterns
    for keyword in config.handoff_keywords:
        if keyword.lower() in conversation.last_message.lower():
            return True, "keyword_detected"
    
    # Check conversation length
    if len(conversation.messages) > config.max_conversation_length:
        return True, "conversation_too_long"
    
    return False, None
```

### 2. Context Collection
```python
def collect_handoff_context(conversation, bot_config):
    return {
        "bot_id": bot_config.id,
        "bot_name": bot_config.name,
        "conversation_id": conversation.id,
        "user_info": conversation.user,
        "messages": conversation.messages,
        "handoff_reason": conversation.handoff_reason,
        "urgency": determine_urgency(conversation),
        "honey_jars_used": conversation.knowledge_sources,
        "timestamp": datetime.utcnow()
    }
```

### 3. Notification Dispatch (CE)
```python
async def notify_admins(handoff_context):
    # Send in-app notification
    await messaging_service.send_notification(
        recipient_role="admin",
        notification_type="nectar_bot_handoff",
        data=handoff_context,
        urgency=handoff_context["urgency"]
    )
    
    # Optional email notification
    if config.email_notifications_enabled:
        await send_handoff_email(handoff_context)
```

## Admin Interface Features

### Handoff Dashboard
- **Active Handoffs**: List of pending human interventions
- **Response Actions**: Accept, delegate, or resolve handoffs
- **Context View**: Full conversation history with AI confidence scores
- **Quick Responses**: Pre-configured response templates
- **Status Updates**: Mark handoffs as in-progress or resolved

### Bot Configuration
- **Handoff Settings**: Configure triggers and thresholds per bot
- **Notification Preferences**: Choose notification methods and recipients
- **Response Templates**: Create standardized handoff responses
- **Analytics**: Track handoff frequency and resolution times

## Enterprise Edition Extensions

### External Platform Integration
```yaml
nectar_bots:
  handoff:
    mode: "enterprise_external"
    integrations:
      slack:
        webhook_url: "${SLACK_WEBHOOK_URL}"
        channel: "#customer-support"
        mention_groups: ["@support-team"]
      
      teams:
        webhook_url: "${TEAMS_WEBHOOK_URL}"
        channel: "Customer Support"
      
      zendesk:
        api_endpoint: "${ZENDESK_API_URL}"
        api_key: "${ZENDESK_API_KEY}"
        ticket_priority: "normal"
        
      pagerduty:
        integration_key: "${PAGERDUTY_KEY}"
        severity: "warning"
```

### Advanced Features
- **Skill-based Routing**: Route to specific agent types
- **Priority Queuing**: Urgent handoffs get immediate attention
- **SLA Tracking**: Monitor response times and compliance
- **Multi-channel**: Support across email, chat, phone
- **Escalation Paths**: Multi-tier support structures

## Implementation Guide

### 1. Enable Handoff System
```bash
# Update configuration
vim conf/config.yml

# Add nectar_bots.handoff section
# Restart services
./manage_sting.sh restart messaging
./manage_sting.sh restart public-bee
```

### 2. Configure Bot Handoff
```python
# Via Admin Panel UI
POST /api/nectar-bots/{bot_id}/handoff
{
    "enabled": true,
    "triggers": {
        "confidence_threshold": 0.6,
        "keywords": ["help", "human", "support"]
    },
    "notification_settings": {
        "methods": ["in_app", "email"],
        "urgency": "medium"
    }
}
```

### 3. Monitor Handoffs
```bash
# View active handoffs
GET /api/nectar-bots/handoffs?status=active

# Get handoff analytics
GET /api/nectar-bots/analytics/handoffs
```

## Best Practices

### For CE Edition
1. **Configure Appropriate Thresholds**: Balance automation vs human intervention
2. **Train Admin Users**: Ensure team knows how to handle handoffs effectively
3. **Monitor Response Times**: Track how quickly handoffs are addressed
4. **Refine Triggers**: Continuously improve handoff detection accuracy

### For Enterprise Planning
1. **Integration Testing**: Test webhook endpoints before production
2. **Escalation Paths**: Define clear routing rules for different scenarios
3. **SLA Definition**: Set clear response time expectations
4. **Multi-channel Support**: Plan for various communication platforms

## Troubleshooting

### Common Issues
1. **Handoffs Not Triggering**: Check confidence thresholds and keyword patterns
2. **Notifications Not Received**: Verify messaging service and admin user roles
3. **Context Not Transferred**: Ensure conversation history is properly stored
4. **High False Positives**: Adjust trigger sensitivity settings

### Debugging Commands
```bash
# Check handoff configuration
./manage_sting.sh logs public-bee | grep handoff

# Test notification service
curl -X POST https://localhost:5050/api/messaging/test-notification

# View handoff history
./manage_sting.sh exec db psql -d sting_app -c "SELECT * FROM nectar_bot_handoffs;"
```

## Security Considerations

### Data Protection
- **Conversation Encryption**: All handoff data encrypted in transit and at rest
- **Access Control**: Only authorized admins can view handoff details
- **Audit Logging**: All handoff activities logged for compliance
- **PII Scrubbing**: Sensitive data filtered before external integrations

### Integration Security
- **Webhook Validation**: Verify webhook signatures for external platforms
- **API Key Management**: Secure storage of third-party credentials
- **Rate Limiting**: Prevent abuse of handoff mechanisms
- **Network Security**: Encrypt all external communications

---

**Next Steps**: Configure your first Nectar Bot with handoff capability through the Admin Panel → Nectar Bots tab.

**Enterprise Upgrade**: Contact sales for advanced handoff integrations and priority support routing.