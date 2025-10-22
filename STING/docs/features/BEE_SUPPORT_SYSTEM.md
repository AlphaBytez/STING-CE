# 🐝 Bee-Powered Support System

The Bee-Powered Support System revolutionizes how users get help with STING-CE by combining AI intelligence, automated diagnostics, and secure delivery channels for seamless support experiences.

## Overview

Instead of manually gathering logs and system information, users can simply chat with Bee about their problems and get professional-grade support bundles with secure delivery to the support team.

### Key Features

- 🤖 **AI-Powered Issue Analysis**: Bee understands STING architecture and correlates issues with services
- 🎯 **Intelligent Diagnostics**: Automated honey jar creation with targeted log collection
- 💬 **Conversational Interface**: Natural language support requests via Bee Chat
- 🔒 **Secure Delivery**: Tailscale ephemeral tunnels for safe diagnostic transfer
- 🔐 **Permission Management**: Admin-only access with confirmation workflows
- 📋 **Ticket Management**: Full lifecycle support request tracking

## How It Works

### 1. User Reports Issue via Chat

```
User: "@bee I'm having login issues after the update"

Bee: "I understand you're experiencing authentication problems. This appears to be 
related to the Kratos authentication service and app middleware. Let me analyze 
the situation and create a targeted diagnostic bundle.

Should I:
1. Capture Kratos and app service logs from the last hour
2. Include startup logs to check for update-related issues  
3. Focus on authentication flows and session management

What would you prefer?"
```

### 2. AI-Guided Diagnostic Collection

Bee intelligently maps issues to services and suggests relevant diagnostic focuses:

- **Authentication Issues** → Kratos + App services, `--auth-focus` flag
- **UI Problems** → Frontend + Nginx services, startup logs
- **API Errors** → App + Database services, connection logs
- **AI Chat Issues** → Chatbot + External AI services, `--llm-focus` flag
- **Performance Problems** → All services, `--performance` metrics

### 3. Automated Honey Jar Creation

Bee creates optimized diagnostic bundles based on issue analysis:

```
Bee: "Creating authentication-focused diagnostic bundle:
✅ Capturing Kratos logs (last 60 minutes)
✅ Capturing app service logs (last 60 minutes)  
✅ Including startup logs for update analysis
✅ Running AAL2 flow diagnostics
🔄 Creating sanitized honey jar...
```

### 4. Secure Support Delivery

For Professional and Enterprise tiers, Bee establishes secure Tailscale tunnels:

```
Bee: "Diagnostic bundle ready (2.3MB, fully sanitized).
Would you like me to establish a secure connection for support team access?
This creates a temporary encrypted tunnel."

User: "Yes, create secure connection"

Bee: "I need admin confirmation for support access. 
Please type 'GRANT_SUPPORT_ACCESS' to authorize."

User: "GRANT_SUPPORT_ACCESS"

Bee: "✅ Support ticket #ST-2025-001 created
✅ Tailscale tunnel established (expires in 24h)
✅ Support team notified
📧 Email confirmation sent"
```

## Command Reference

### Bee Chat Commands

#### Natural Language Support Requests
```
"@bee help with database connection errors"
"@bee create ticket for slow performance"
"@bee my frontend won't load after update"
"@bee authentication is broken"
"@bee chat/ai services not responding"
```

#### Administrative Commands
```
"@bee show support tickets"
"@bee connect me to support for ticket #ST-123"
"@bee end support session"
"@bee what logs should I collect for [issue]?"
"@bee grant support access"  # Requires admin confirmation
```

#### Status and Management
```
"@bee support status"
"@bee list active support sessions"
"@bee check system health"
"@bee analyze current issues"
```

### CLI Commands

#### Support Management
```bash
# AI-guided support requests
./manage_sting.sh bee support --analyze
./manage_sting.sh bee support --create "issue description"
./manage_sting.sh bee support --suggest
./manage_sting.sh bee support --status

# Enhanced diagnostics with AI
./manage_sting.sh buzz collect --ai-guided
./manage_sting.sh buzz smart-collect "authentication issues"

# Support session management
./manage_sting.sh support list
./manage_sting.sh support connect ST-2025-001
./manage_sting.sh support disconnect
```

#### Traditional Honey Jar Commands (Still Available)
```bash
# Manual diagnostic collection
./manage_sting.sh buzz collect
./manage_sting.sh buzz collect --auth-focus
./manage_sting.sh buzz collect --llm-focus --performance
./manage_sting.sh buzz collect --hours 48 --ticket ST-123
```

## Architecture Integration

### Bee System Knowledge

Bee maintains comprehensive knowledge of STING architecture:

- **Service Dependencies**: Understands which services work together
- **Log Correlation**: Knows which logs to capture for specific issues
- **Common Patterns**: Recognizes frequent problems and their signatures
- **Troubleshooting Flows**: Guides users through systematic problem solving

### Service Mappings

| Issue Type | Primary Services | Diagnostic Focus | Log Sources |
|------------|------------------|------------------|-------------|
| Authentication | Kratos, App | `--auth-focus` | kratos, app, db |
| Frontend Loading | Frontend, Nginx | Startup logs | frontend, nginx |
| API Errors | App, Database | Connection logs | app, db |
| AI Chat Issues | Chatbot, External-AI | `--llm-focus` | chatbot, external-ai |
| Performance | All Services | `--performance` | All services |

### Permission Framework

#### Access Levels
- **Community**: Chat-based diagnostics + manual honey jar delivery
- **Professional**: + Tailscale ephemeral access + priority support
- **Enterprise**: + Dedicated tunnels + on-call support

#### Security Model
- Admin-only support request creation
- Confirmation required for secure access grants
- Full audit trail of all support actions
- Automatic session cleanup and data retention

## Configuration

### Support System Settings (`config.yml`)

```yaml
support_system:
  enabled: true
  
  # Bee integration settings
  bee_integration:
    chat_support_requests: true
    architecture_awareness: true
    intelligent_log_capture: true
    max_log_lines: 30
    auto_service_correlation: true
    
  # Permission management
  permissions:
    require_admin: true
    confirmation_required: true
    audit_all_actions: true
    
  # Support tiers
  tiers:
    community:
      honey_jar_delivery: "manual"
      response_time: "48h"
    professional:
      honey_jar_delivery: "tailscale"
      ephemeral_access_duration: "24h"
      response_time: "4h"
    enterprise:
      honey_jar_delivery: "wireguard"
      dedicated_tunnel: true
      response_time: "1h"
      
  # Secure delivery (Professional/Enterprise)
  tailscale:
    enabled: true
    support_subnet: "support"
    auth_key_duration: "1h"
    max_concurrent_sessions: 5
    
  # Chat flow customization
  chat_flow:
    interactive_wizard: true
    progress_updates: true
    approval_workflow: true
```

### Bee Knowledge Integration

Bee's system architecture knowledge is stored in `/chatbot/knowledge/sting_architecture.yml`:

- Service dependency mappings
- Issue-to-service correlations
- Log pattern recognition
- Common troubleshooting flows
- Response templates for support scenarios

## Database Schema

### Support Tickets
```sql
CREATE TABLE support_tickets (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    issue_type VARCHAR(100),
    status VARCHAR(50) DEFAULT 'open',
    priority VARCHAR(20) DEFAULT 'normal',
    support_tier VARCHAR(50),
    honey_jar_refs TEXT[],
    chat_transcript JSONB,
    tailscale_session_id VARCHAR(255),
    bee_analysis JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Support Sessions
```sql
CREATE TABLE support_sessions (
    id UUID PRIMARY KEY,
    ticket_id UUID REFERENCES support_tickets(id),
    session_type VARCHAR(50), -- 'tailscale', 'wireguard', 'manual'
    connection_details JSONB,
    access_granted_by UUID REFERENCES users(id),
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status VARCHAR(50) DEFAULT 'active',
    audit_log JSONB
);
```

## Implementation Status

### Phase 1: Foundation (✅ Complete)
- [x] STING architecture knowledge base for Bee
- [x] Enhanced buzz system integration
- [x] Basic CLI support commands

### Phase 2: Bee Chat Integration (🔄 In Progress)
- [ ] Support request chat commands
- [ ] Issue analysis and service correlation
- [ ] Intelligent honey jar creation
- [ ] Permission validation system

### Phase 3: Secure Delivery (📋 Planned)
- [ ] Tailscale service integration
- [ ] Ephemeral tunnel management
- [ ] Support session tracking
- [ ] Automated cleanup workflows

### Phase 4: Advanced Features (📋 Future)
- [ ] MCP integration for real-time collaboration
- [ ] Proactive issue detection
- [ ] Advanced analytics and reporting
- [ ] Mobile-optimized support interface

## Benefits

### For Users
- **Intuitive**: Just chat about problems naturally
- **Fast**: AI creates targeted diagnostics instantly
- **Secure**: Encrypted delivery with temporary access
- **Comprehensive**: Full system context in every support request

### For Support Teams
- **Rich Context**: Complete system state and user conversation history
- **Sanitized Data**: PII-compliant diagnostic bundles
- **Secure Access**: Temporary tunnels for hands-on troubleshooting
- **Efficient Triage**: AI pre-analysis speeds resolution

### For Organizations
- **Reduced Overhead**: Automated diagnostic collection
- **Better Security**: No need to expose systems or share credentials
- **Faster Resolution**: Context-rich support requests
- **Compliance Ready**: Built-in data sanitization and audit trails

## Future Roadmap

- **Worker Bee Architecture**: Distributed diagnostic collection
- **Predictive Support**: Proactive issue detection and prevention
- **Integration Ecosystem**: Third-party support tool connections
- **Advanced Analytics**: Support trend analysis and optimization
- **Mobile-First UI**: Native mobile app for support requests

## Getting Started

1. **Enable the Support System** in your `config.yml`
2. **Configure Bee Integration** settings
3. **Set Up Support Tiers** based on your organization needs
4. **Train Admins** on chat-based support workflows
5. **Test** with sample support scenarios

The Bee-Powered Support System transforms STING support from a technical challenge into a conversational experience, making expert-level diagnostics accessible to all users while maintaining enterprise-grade security and compliance.