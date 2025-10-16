# Bee Chat & Messaging Architecture

## Overview

Bee Chat is STING's intelligent messaging system that enables secure, context-aware communication between users, teams, and AI assistants. This document outlines the architecture for both current capabilities and future enterprise features.

## Core Concepts

### 🐝 **Bee Chat**
Individual conversations with B. STING, providing:
- AI-powered assistance
- Context from Honey Jars
- Secure data discussions
- Task automation

### 🐝🐝 **Swarm Chat** (Enterprise)
Group conversations enabling:
- Team collaboration
- Shared AI assistance
- Project-based discussions
- Role-based access

### 💃 **Waggles** (Notification System)
Named after the bee waggle dance, Waggles are intelligent notifications that:
- Alert users to important events
- Provide context-aware updates
- Can be customized per data type
- Support local or cloud deployment

## Architecture

### Current State (MVP)

```yaml
Messaging Core:
  Backend: 
    - WebSocket for real-time
    - Redis for message queue
    - PostgreSQL for history
  
  Features:
    - 1:1 chat with Bee
    - Basic notifications
    - Message history
    - File attachments
```

### Phase 1: Enhanced Messaging (3-6 months)

```yaml
Enhanced Features:
  Swarm Chat:
    - Group conversations
    - @mentions
    - Thread support
    - Message reactions
  
  Waggles v1:
    - Email notifications
    - In-app alerts
    - Basic webhooks
    - Priority levels
```

### Phase 2: Enterprise Integration (6-12 months)

```yaml
Enterprise Features:
  Third-Party Integration:
    - Slack connector
    - Microsoft Teams
    - Discord
    - Custom webhooks
  
  Advanced Waggles:
    - Data-type specific alerts
    - Custom waggle creation
    - ML-powered routing
    - Cross-platform sync
```

## Waggles - Intelligent Notification System

### Concept
Just as bees perform waggle dances to communicate important information about resources, STING's Waggles communicate important events and insights to users.

### Waggle Types

```yaml
System Waggles:
  - report_complete: "Your report is ready!"
  - data_anomaly: "Unusual pattern detected"
  - security_alert: "Suspicious access attempt"
  - performance_warning: "Processing slowdown"

Data Waggles:
  - threshold_breach: "Sales exceeded target"
  - pattern_match: "Similar to previous issue"
  - compliance_violation: "PII detected in logs"
  - insight_discovery: "New trend identified"

Collaboration Waggles:
  - mention_alert: "@user mentioned you"
  - task_assigned: "New task from @manager"
  - approval_needed: "Report awaits approval"
  - team_update: "Project milestone reached"
```

### Waggle Configuration

```python
class WaggleConfig:
    """Configuration for custom Waggles"""
    
    def __init__(self, name: str, waggle_type: str):
        self.name = name
        self.type = waggle_type
        self.conditions = []
        self.actions = []
        self.recipients = []
    
    def when(self, condition: Dict[str, Any]):
        """Define trigger conditions"""
        self.conditions.append(condition)
        return self
    
    def notify(self, recipients: List[str]):
        """Define who gets notified"""
        self.recipients.extend(recipients)
        return self
    
    def via(self, channels: List[str]):
        """Define notification channels"""
        self.channels = channels
        return self

# Example: Custom Sales Waggle
sales_waggle = WaggleConfig("high_value_sale", "data_waggle")
    .when({"field": "sale_amount", "operator": ">", "value": 10000})
    .notify(["sales_manager", "ceo"])
    .via(["email", "slack", "in_app"])
```

### Local Waggle Installation

```yaml
Local Waggles:
  Purpose: "Process data without cloud dependency"
  
  Installation:
    - Download waggle package
    - Configure data connections
    - Set notification preferences
    - Deploy to local Worker Bee
  
  Benefits:
    - No data leaves premises
    - Customizable logic
    - Fast processing
    - Compliance friendly
```

## Messaging Security

### Zero Trust with Convenience

```yaml
Security Layers:
  Authentication:
    Primary: WebAuthn/Passkeys (strongly recommended)
    Fallback: TOTP + Password
    Session: Secure, httpOnly cookies
  
  Authorization:
    - Message-level permissions
    - Channel-based access
    - Time-limited shares
    - Audit trail
  
  Encryption:
    - E2E for sensitive chats
    - TLS for transport
    - At-rest encryption
    - Key rotation
```

### Device Trust Levels

```yaml
Trust Levels:
  Fully Trusted (WebAuthn):
    - Full access to all features
    - Can view sensitive data
    - Extended session timeout
    - Offline access
  
  Partially Trusted (TOTP):
    - Limited sensitive data access
    - Shorter session timeout
    - No offline access
    - Additional verification for critical ops
  
  Untrusted (Password only):
    - Basic access only
    - Frequent re-authentication
    - No sensitive operations
    - Limited API access
```

## Third-Party Integration Architecture

### Slack Integration

```python
class SlackConnector:
    """Slack integration for STING"""
    
    async def setup_workspace(self, workspace_id: str):
        """Initial workspace setup"""
        # OAuth flow
        # Channel mapping
        # User synchronization
        # Permission mapping
    
    async def forward_waggle(self, waggle: Waggle, channel: str):
        """Forward Waggle to Slack channel"""
        slack_message = self.transform_waggle(waggle)
        await self.slack_client.post_message(channel, slack_message)
    
    async def handle_slash_command(self, command: str, args: List[str]):
        """Handle Slack slash commands"""
        if command == "/sting-report":
            return await self.generate_report(args)
        elif command == "/sting-query":
            return await self.query_honey_jar(args)
```

### Microsoft Teams Integration

```yaml
Teams Connector:
  Features:
    - Adaptive cards for rich content
    - Bot framework integration
    - Channel synchronization
    - File sharing support
  
  Commands:
    - "@sting help" - Get assistance
    - "@sting report [type]" - Generate report
    - "@sting status" - Check system status
    - "@sting query [data]" - Query Honey Jars
```

## Implementation Roadmap

### Phase 1: Core Messaging (Current)
- [x] Basic 1:1 chat with Bee
- [x] Message history
- [x] Simple notifications
- [ ] File attachments

### Phase 2: Waggles v1 (Next 3 months)
- [ ] Waggle configuration UI
- [ ] Email notifications
- [ ] Basic webhook support
- [ ] Priority levels

### Phase 3: Swarm Chat (3-6 months)
- [ ] Group chat creation
- [ ] User mentions
- [ ] Thread support
- [ ] Message search

### Phase 4: Enterprise Integration (6-9 months)
- [ ] Slack connector
- [ ] Teams connector
- [ ] Custom Waggle creation
- [ ] Advanced routing

### Phase 5: Advanced Features (9-12 months)
- [ ] ML-powered insights
- [ ] Voice/video support
- [ ] Mobile apps
- [ ] Offline sync

## API Examples

### Create Custom Waggle

```javascript
POST /api/v1/waggles
{
  "name": "inventory_low",
  "type": "data_waggle",
  "conditions": {
    "field": "inventory_count",
    "operator": "<",
    "value": 100
  },
  "actions": [
    {
      "type": "notify",
      "channels": ["email", "slack"],
      "recipients": ["inventory_manager"]
    },
    {
      "type": "create_task",
      "assignee": "purchasing_team",
      "title": "Reorder inventory"
    }
  ]
}
```

### Send Swarm Message

```javascript
POST /api/v1/swarms/{swarm_id}/messages
{
  "content": "Check out this insight from the sales data",
  "attachments": [
    {
      "type": "honey_jar_query",
      "jar_id": "sales_2024",
      "query": "top_customers_by_revenue"
    }
  ],
  "mentions": ["@sales_team", "@ceo"]
}
```

### Configure Slack Integration

```javascript
POST /api/v1/integrations/slack
{
  "workspace_id": "T1234567",
  "channel_mappings": {
    "sales_waggles": "#sales-alerts",
    "security_waggles": "#security",
    "general": "#sting-notifications"
  },
  "waggle_forwarding": {
    "enabled": true,
    "filter": {
      "priority": ["high", "critical"],
      "types": ["security_alert", "compliance_violation"]
    }
  }
}
```

## Security Considerations

### Message Privacy
- End-to-end encryption for sensitive discussions
- Automatic PII detection in messages
- Message retention policies
- Audit trail for compliance

### Integration Security
- OAuth 2.0 for third-party apps
- Scoped permissions per integration
- API rate limiting
- Webhook signature verification

### Device Security
```yaml
WebAuthn Enforcement:
  Recommended For:
    - Admin users
    - Users with Honey Jar access
    - Financial data handlers
    - Healthcare workers
  
  Benefits:
    - Phishing resistant
    - No passwords to steal
    - Biometric convenience
    - Hardware security
```

## Best Practices

### For Administrators
1. **Enable WebAuthn** for all users handling sensitive data
2. **Configure Waggles** for critical business events
3. **Set up integrations** with existing communication tools
4. **Monitor message patterns** for security anomalies

### For Users
1. **Use WebAuthn devices** for best security/convenience balance
2. **Create custom Waggles** for your workflow
3. **Leverage Swarm Chat** for team collaboration
4. **Keep sensitive data** in Honey Jars, not messages

### For Developers
1. **Use Waggle APIs** for custom notifications
2. **Implement proper error handling** in integrations
3. **Follow rate limits** to ensure system stability
4. **Test Waggles locally** before deployment

## Future Vision

### Intelligent Communication
- AI-suggested responses based on context
- Automatic meeting summaries
- Smart routing of questions to experts
- Predictive notifications

### Unified Workspace
- Single pane for all communications
- Integrated task management
- Seamless file sharing
- Cross-platform synchronization

### Advanced Analytics
- Communication pattern analysis
- Team collaboration metrics
- Response time optimization
- Knowledge flow visualization

---

*The future of enterprise communication is intelligent, secure, and seamlessly integrated. Bee Chat and Waggles make that future a reality.*

*Last Updated: January 2025*