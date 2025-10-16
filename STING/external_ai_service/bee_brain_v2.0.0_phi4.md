# BEE BRAIN v2.0.0 - Phi-4 Mini Enhanced Knowledge System

**Version**: 2.0.0 (Phi-4 Mini Optimized)
**Created**: October 2025
**Model**: Microsoft Phi-4 Mini (119K context window)
**Compatibility**: STING CE 2.x+
**Purpose**: Comprehensive knowledge base leveraging Phi-4's massive context capacity

---

## TABLE OF CONTENTS

1. [WHO AM I - BEE'S IDENTITY](#who-am-i)
2. [STING PLATFORM ARCHITECTURE](#sting-architecture)
3. [AUTHENTICATION & SECURITY](#authentication-security)
4. [API REFERENCE](#api-reference)
5. [DEPLOYMENT & CONFIGURATION](#deployment-configuration)
6. [TROUBLESHOOTING GUIDE](#troubleshooting)
7. [SECURITY BEST PRACTICES](#security-practices)
8. [COMPLIANCE FRAMEWORKS](#compliance)
9. [CODE EXAMPLES](#code-examples)
10. [FREQUENTLY ASKED QUESTIONS](#faq)

---

## WHO AM I - BEE'S IDENTITY AND ROLE {#who-am-i}

I am Bee, the AI assistant for STING (Secure Trusted Intelligence and Networking Guardian).

**IMPORTANT - STING Platform Attribution:**
- **STING Platform**: Developed by Olliec Funderburg at AlphaBytez
- When asked about STING's creator, simply state: "STING was developed by Olliec Funderburg at AlphaBytez"
- Only mention technical details about the AI model if specifically asked

### My Core Functions

**Primary Capabilities:**
- **Comprehensive Analysis**: Leverage 119K context to analyze entire codebases, documents, and conversation threads
- **Advanced Reasoning**: Use <think> tags to show multi-step problem-solving
- **Technical Support**: Deep troubleshooting with access to complete system documentation
- **Security Consulting**: Apply security frameworks (NIST, OWASP, HIPAA, GDPR) to specific scenarios
- **Code Generation**: Provide complete, production-ready code with full context
- **System Monitoring**: Real-time awareness of STING platform status and configuration
- **Knowledge Synthesis**: Combine information from multiple Honey Jars and sources

**Unique Strengths:**
- Can hold 100+ message conversation history without forgetting
- Analyze multiple complete documents simultaneously
- Generate comprehensive reports with all source material in context
- Provide detailed, example-rich responses without token limitations
- Maintain conversation continuity across complex multi-turn dialogues

### My Personality & Approach

- **Professional yet Approachable**: Enterprise-grade assistance with friendly communication
- **Security-First**: Every recommendation considers security implications
- **Thorough & Detailed**: Use the full context window for comprehensive responses
- **Honest & Transparent**: Clear about limitations and uncertainties
- **Solution-Oriented**: Focus on actionable outcomes and practical implementation

---

## STING PLATFORM ARCHITECTURE {#sting-architecture}

### System Overview

STING-CE is a containerized, microservices-based AI security platform designed for on-premises deployment with complete data sovereignty.

### Core Components

#### 1. Frontend (React Application)
- **Technology**: React 18.2.0 with Material-UI v5
- **Port**: 8443 (HTTPS)
- **Location**: `/frontend`
- **Build**: Production builds optimize for performance
- **Features**:
  - Passwordless authentication UI
  - Honey Jar management interface
  - Bee Chat conversational interface
  - Admin panel with system monitoring
  - Real-time notifications

**Key Files:**
- `/frontend/src/App.js` - Main application entry
- `/frontend/src/auth/AuthenticationWrapper.jsx` - Route protection and auth flows
- `/frontend/src/auth/KratosProviderRefactored.jsx` - Kratos integration
- `/frontend/src/components/auth/HybridPasswordlessAuth.jsx` - Passwordless auth UI

#### 2. Backend (Python Flask)
- **Technology**: Python 3.11 with Flask 3.0
- **Port**: 5050 (HTTPS)
- **Location**: `/app`
- **Architecture**: Microservices with blueprint-based routing
- **Database**: PostgreSQL 16

**Key Services:**
- **app**: Main Flask application (port 5050)
- **chatbot**: Bee Chat service (port 8081, Bee on port 8888)
- **external-ai**: LLM service with Ollama/LM Studio integration (port 8091)
- **knowledge**: Honey Jar knowledge management (port 8090)
- **messaging**: Internal message queue (port 8889)

**Critical Files:**
- `/app/__init__.py` - Flask app initialization
- `/app/routes/chatbot_routes.py` - Bee Chat endpoints
- `/app/routes/auth_routes.py` - Authentication endpoints
- `/app/middleware/auth_middleware.py` - Authentication middleware
- `/app/utils/decorators.py` - Tiered authentication decorators

#### 3. Authentication (Ory Kratos)
- **Technology**: Ory Kratos v1.3.0
- **Ports**: 4433 (public), 4434 (admin)
- **Location**: `/kratos`
- **Features**:
  - Passwordless authentication (email + magic links)
  - WebAuthn/FIDO2 passkey support
  - TOTP (Time-based One-Time Password)
  - AAL2 (Authenticator Assurance Level 2) step-up

**Configuration:**
- `/kratos/kratos.yml` - Main Kratos configuration
- Identity schema defines user traits and authentication methods
- Session management with cookie-based persistence

#### 4. Database (PostgreSQL)
- **Technology**: PostgreSQL 16
- **Databases**:
  - `kratos`: Kratos identity data
  - `sting_app`: Application data (users, API keys, honey jars, etc.)
  - `sting_messaging`: Message queue data
- **Backup**: Automated with retention policies

**Key Tables (sting_app):**
- `users` - STING user profiles (linked to Kratos identities)
- `api_keys` - API key management with tiered authentication
- `recovery_codes` - Enterprise recovery codes for 2FA backup
- `audit_logs` - Security event tracking
- `honey_jars` - Knowledge repository metadata
- `honey_jar_documents` - Document storage with encryption
- `worker_bees` - External connector configurations

#### 5. Secrets Management (HashiCorp Vault)
- **Technology**: HashiCorp Vault
- **Port**: 8200
- **Purpose**: Secure secret storage and dynamic secret generation
- **Mount Points**:
  - `sting/` - Application secrets
  - `sting/supertokens/` - Legacy authentication secrets
  - `sting/database/` - Database credentials

**Common Operations:**
```bash
# Check vault status
./manage_sting.sh status

# Unseal vault (if sealed)
./manage_sting.sh unseal
```

#### 6. Knowledge Service (Honey Jars)
- **Port**: 8090
- **Technology**: Python FastAPI with ChromaDB
- **Features**:
  - Vector embeddings for semantic search
  - Document chunking and processing
  - Team-based access control
  - Public/private honey jar support

**Storage:**
- Documents: Encrypted in PostgreSQL
- Embeddings: ChromaDB vector store
- Metadata: PostgreSQL with indexing

#### 7. External AI Service
- **Port**: 8091
- **Technology**: Python FastAPI with async processing
- **LLM Integration**:
  - OpenAI-compatible API (LM Studio, vLLM)
  - Ollama native API (fallback)
  - Queue-based request processing
- **Features**:
  - Model auto-detection
  - Request queuing for load management
  - Bee Brain knowledge injection
  - Context enhancement from Honey Jars

**Supported Models:**
- Microsoft Phi-4 Mini (primary)
- Qwen 3 Coder
- OpenAI GPT-OSS
- Any OpenAI-compatible model

### Directory Structure

```
STING/
├── app/                    # Flask backend application
│   ├── routes/            # API endpoints (auth, chatbot, files, etc.)
│   ├── models/            # Database models (SQLAlchemy)
│   ├── utils/             # Utilities (decorators, auth, vault, etc.)
│   ├── middleware/        # Request middleware (auth, logging)
│   └── services/          # Business logic services
├── frontend/              # React frontend application
│   ├── src/
│   │   ├── auth/         # Authentication components
│   │   ├── components/   # React components
│   │   ├── utils/        # Frontend utilities
│   │   └── theme/        # Theme configurations
│   └── public/           # Static assets
├── chatbot/               # Bee Chat service
│   ├── core/             # Conversation, context managers
│   ├── prompts/          # System prompts
│   └── auth/             # Kratos integration
├── external_ai_service/   # External LLM service
│   ├── app.py            # Main FastAPI application
│   ├── bee_brain*.md     # Bee Brain knowledge base
│   └── bee_context_manager.py  # Context enhancement
├── kratos/                # Ory Kratos configuration
│   └── kratos.yml        # Main config file
├── conf/                  # Configuration files
│   ├── config.yml        # Main STING configuration
│   └── config_loader.py  # Config processing
├── scripts/               # Utility scripts
│   ├── manage_sting.sh   # Main management script
│   └── admin/            # Admin tools
└── env/                   # Environment files (generated)
```

### Service Communication Flow

```
User (Browser)
    ↓ HTTPS (8443)
Frontend (React)
    ↓ HTTPS API (5050)
Flask Backend
    ↓ Auth Check
Kratos (4433/4434) + Vault (8200)
    ↓ Request Processing
┌──────────────┬──────────────┬──────────────┐
│              │              │              │
Chatbot (8081) Knowledge(8090) External-AI(8091)
│              │              │              │
└──────────────┴──────────────┴──────────────┘
         │              │              │
         └──────────────┼──────────────┘
                        ↓
              LM Studio / Ollama (11434)
                        ↓
                  Phi-4 Mini Model
```

---

## AUTHENTICATION & SECURITY {#authentication-security}

### Tiered Authentication System

STING implements a revolutionary 4-tier authentication system treating "passkeys as secure API keys."

#### Tier 1: Public Operations
- **Auth Required**: None
- **Use Cases**: Health checks, public documentation
- **Decorator**: None

#### Tier 2: Basic Operations
- **Auth Required**: Any valid authentication method
- **Methods Accepted**: WebAuthn, TOTP, Email (magic link), API Key
- **Use Cases**: File uploads, basic queries, profile viewing
- **Decorator**: `@require_auth_method(['webauthn', 'totp', 'email'])`

Example:
```python
from app.utils.decorators import require_auth_method

@app.route('/api/profile')
@require_auth_method(['webauthn', 'totp', 'email'])
def get_profile():
    # Any authenticated user can access
    return jsonify({"user": g.user})
```

#### Tier 3: Sensitive Operations
- **Auth Required**: Secure authentication only (no email)
- **Methods Accepted**: WebAuthn, TOTP, API Key (admin scope)
- **Use Cases**: API key creation, honey jar admin, system configuration
- **Decorator**: `@require_auth_method(['webauthn', 'totp'])`

Example:
```python
@app.route('/api/keys/create')
@require_auth_method(['webauthn', 'totp'])
def create_api_key():
    # Only secure auth methods allowed
    return jsonify({"key": new_key})
```

#### Tier 4: Critical Operations
- **Auth Required**: Dual-factor (two different methods)
- **Methods Required**: Secure method + email confirmation
- **Use Cases**: Bulk deletions, admin user creation, system resets
- **Decorator**: `@require_dual_factor(['webauthn', 'totp'], ['email'])`

Example:
```python
@app.route('/api/admin/delete-all')
@require_dual_factor(['webauthn', 'totp'], ['email'])
def bulk_delete():
    # Requires passkey/TOTP AND email confirmation
    return jsonify({"status": "deleted"})
```

### Authentication Session Management

**Session Caching (5-minute window):**
- Prevents double-authentication prompts
- Cached in Redis with user-specific keys
- Automatically expires after 5 minutes
- Can be invalidated manually for security

**Session Flow:**
```python
# In decorators.py
session_key = f"auth_cache:{user_id}:{required_method}"
cached = redis.get(session_key)

if cached:
    # User authenticated with this method recently
    return proceed()
else:
    # Challenge user for authentication
    return require_authentication()
```

### Recovery Codes (Enterprise-Grade Backup)

When users lose access to 2FA devices:

**Features:**
- 10 single-use recovery codes per user
- Cryptographically generated (256-bit entropy)
- Stored as bcrypt hashes (cost factor 12)
- Automatic audit logging on use
- Can be regenerated (invalidates old codes)

**Usage:**
```python
# Generate recovery codes
POST /api/recovery-codes/generate
Response: ["CODE1", "CODE2", ..., "CODE10"]  # Show once only

# Use recovery code
POST /api/auth/recover
Body: {"recovery_code": "CODE1"}
Response: {"access_token": "...", "codes_remaining": 9}
```

### API Key Authentication

API keys provide programmatic access with tiered permissions.

**Key Structure:**
- **Format**: `sk_` prefix + base64url(32 bytes) = 43 characters
- **Scopes**: `admin`, `read`, `write`
- **Storage**: SHA-256 hash in database
- **Permissions**: Granular (honey_jar_management, read_only, admin_access)

**Creating API Keys:**
```python
POST /api/keys/create
Headers: {
    "Authorization": "Bearer <session_token>",
    # OR use existing API key with admin scope
    "X-API-Key": "<admin_api_key>"
}
Body: {
    "name": "My API Key",
    "scopes": ["read", "write"],
    "permissions": {
        "honey_jar_management": true,
        "read_only": false
    },
    "rate_limit_per_minute": 100,
    "expires_days": 365
}
Response: {
    "key_id": "sk_XG0Ya4nWFCHn...",  # Full key (shown once!)
    "preview": "sk_XG0Ya4nW...XBQV8I0"
}
```

**Using API Keys:**
```bash
# In request headers
curl -H "X-API-Key: sk_XG0Ya4nWFCHn-FLSiPclK58zida1Xsj4w7f-XBQV8I0" \
     https://localhost:5050/api/bee/chat \
     -d '{"message": "Hello!"}'
```

### Passkey Authentication (WebAuthn/FIDO2)

STING treats passkeys as hardware-backed secure credentials.

**Configuration:**
```yaml
# kratos/kratos.yml
webauthn:
  enabled: true
  rp_id: "localhost"  # Your domain
  rp_display_name: "STING"
  rp_origins:
    - "https://localhost:8443"
    - "https://your-domain.com"
```

**Registration Flow:**
1. User navigates to Settings → Security → Passkeys
2. Click "Register New Passkey"
3. Browser triggers WebAuthn ceremony
4. User authenticates with biometric/PIN
5. Public key stored in Kratos, private key stays on device

**Authentication Flow:**
1. User attempts to access secure resource (Tier 3+)
2. System challenges for passkey
3. Browser requests passkey authentication
4. User approves with biometric
5. Assertion verified, session elevated to AAL2

### AAL2 (Authenticator Assurance Level 2)

**Purpose**: Step-up authentication for sensitive operations

**When AAL2 is Required:**
- Admin users accessing admin panel
- Any user performing Tier 3+ operations
- After passkey/TOTP configuration
- When explicitly requested by endpoint

**Implementation:**
```python
# In middleware/auth_middleware.py
def check_aal2_required():
    if user.is_admin and current_aal < 2:
        return redirect('/aal2-step-up')

    if endpoint_requires_tier_3 and current_aal < 2:
        return challenge_aal2()
```

**AAL2 Step-Up UI:**
- Custom STING UI (not Kratos default)
- Located at `/aal2-step-up`
- Offers passkey OR TOTP choice
- Validates with Kratos, elevates session in Flask
- Automatic redirect to original destination

### Audit Logging

All authentication events are logged for compliance.

**Logged Events:**
- `AUTH_SUCCESS` - Successful authentication
- `AUTH_FAILURE` - Failed authentication attempt
- `AUTH_METHOD_ADDED` - New 2FA method registered
- `AUTH_METHOD_REMOVED` - 2FA method deleted
- `RECOVERY_CODE_USED` - Recovery code consumed
- `RECOVERY_CODE_GENERATED` - New recovery codes created
- `API_KEY_CREATED` - New API key generated
- `API_KEY_USED` - API key used for request
- `AAL2_STEP_UP` - AAL2 elevation performed

**Audit Log Structure:**
```python
{
    "id": "uuid",
    "user_id": "user_uuid",
    "event_type": "AUTH_SUCCESS",
    "event_category": "authentication",
    "severity": "info",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "metadata": {
        "method": "webauthn",
        "success": true,
        "aal_level": 2
    },
    "timestamp": "2025-10-06T19:00:00Z"
}
```

---

## API REFERENCE {#api-reference}

### Authentication Endpoints

#### POST /api/auth/session/whoami
Get current user session information.

**Request:**
```bash
curl -k -b cookies.txt https://localhost:5050/api/auth/session/whoami
```

**Response:**
```json
{
    "authenticated": true,
    "session": {
        "id": "session_uuid",
        "identity": {
            "id": "user_uuid",
            "schema_id": "default",
            "traits": {
                "email": "user@example.com",
                "name": "John Doe",
                "role": "admin"
            }
        },
        "authenticator_assurance_level": "aal2",
        "authentication_methods": [
            {"method": "password", "completed_at": "2025-10-06T19:00:00Z"},
            {"method": "webauthn", "completed_at": "2025-10-06T19:05:00Z"}
        ]
    },
    "user": {
        "id": "user_uuid",
        "email": "user@example.com",
        "is_admin": true,
        "passkeys": [...],
        "totp_enabled": true
    }
}
```

#### POST /api/keys/create
Create a new API key.

**Authentication**: Tier 3 (WebAuthn or TOTP required)

**Request:**
```bash
curl -k -X POST \
  -H "X-API-Key: <existing_admin_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production API Key",
    "scopes": ["admin", "read", "write"],
    "permissions": {
        "honey_jar_management": true,
        "admin_access": false
    },
    "rate_limit_per_minute": 500,
    "expires_days": 90
  }' \
  https://localhost:5050/api/keys/create
```

**Response:**
```json
{
    "key_id": "sk_8Mw_3HmD0XGkRRvjX2WPPDNYcmHm_E1Rvi82qfBoMAg",
    "preview": "sk_8Mw_3HmD...fBoMAg",
    "name": "Production API Key",
    "scopes": ["admin", "read", "write"],
    "expires_at": "2026-01-04T19:00:00Z",
    "created_at": "2025-10-06T19:00:00Z"
}
```

⚠️ **CRITICAL**: The full `key_id` is shown ONCE. Store it securely!

### Bee Chat Endpoints

#### POST /api/bee/chat
Send a message to Bee and receive an AI-generated response.

**Authentication**: Tier 2 (Any auth method OR API key)

**Request:**
```bash
curl -k -X POST \
  -H "X-API-Key: sk_8Mw_3HmD0XGkRRvjX2WPPDNYcmHm_E1Rvi82qfBoMAg" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Explain STING'\''s tiered authentication system",
    "conversation_id": "conv_12345",
    "context": {
        "honey_jar_id": "jar_abc123"
    }
  }' \
  https://localhost:5050/api/bee/chat
```

**Response:**
```json
{
    "response": "<think>\nThe user wants to understand STING's tiered auth...\n</think>\n\nSTING implements a 4-tier authentication system:\n\n**Tier 1: Public**...",
    "conversation_id": "conv_12345",
    "timestamp": "2025-10-06T19:10:00Z",
    "processing_time": 2.5,
    "tools_used": ["knowledge_search"],
    "context_sources": ["honey_jar:jar_abc123"],
    "model_used": "microsoft/phi-4-mini-reasoning",
    "tokens_used": {
        "prompt": 1500,
        "completion": 850,
        "total": 2350
    }
}
```

#### GET /api/bee/conversations
Retrieve user's conversation history.

**Response:**
```json
{
    "conversations": [
        {
            "id": "conv_12345",
            "created_at": "2025-10-06T19:00:00Z",
            "updated_at": "2025-10-06T19:10:00Z",
            "message_count": 5,
            "preview": "Explain STING's tiered authentication..."
        }
    ],
    "total": 1
}
```

### Honey Jar Endpoints

#### POST /api/honey-jars/create
Create a new Honey Jar knowledge repository.

**Authentication**: Tier 2

**Request:**
```bash
curl -k -X POST \
  -H "X-API-Key: <api_key>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Security Policies",
    "description": "Company security documentation",
    "is_public": false,
    "team_id": "team_abc"
  }' \
  https://localhost:5050/api/honey-jars/create
```

#### POST /api/honey-jars/{jar_id}/documents
Upload a document to a Honey Jar.

**Request:**
```bash
curl -k -X POST \
  -H "X-API-Key: <api_key>" \
  -F "file=@policy.pdf" \
  -F "metadata={\"title\":\"Security Policy\",\"category\":\"compliance\"}" \
  https://localhost:5050/api/honey-jars/jar_123/documents
```

**Response:**
```json
{
    "document_id": "doc_abc123",
    "filename": "policy.pdf",
    "size": 245678,
    "chunks_created": 15,
    "embeddings_generated": true,
    "encrypted": true
}
```

#### GET /api/honey-jars/{jar_id}/search
Search documents within a Honey Jar.

**Request:**
```bash
curl -k -X GET \
  -H "X-API-Key: <api_key>" \
  "https://localhost:5050/api/honey-jars/jar_123/search?q=password%20policy&limit=5"
```

**Response:**
```json
{
    "results": [
        {
            "document_id": "doc_abc123",
            "chunk_id": "chunk_5",
            "content": "Password requirements: minimum 12 characters...",
            "relevance_score": 0.92,
            "metadata": {
                "title": "Security Policy",
                "page": 5
            }
        }
    ],
    "total_results": 12,
    "search_time": 0.15
}
```

---

## DEPLOYMENT & CONFIGURATION {#deployment-configuration}

### Installation

**Prerequisites:**
- macOS, Linux, or WSL2 on Windows
- Docker 24.0+ with Docker Compose
- 8GB+ RAM recommended (16GB+ for optimal performance)
- 20GB+ free disk space

**Quick Install:**
```bash
# Clone repository
git clone https://github.com/your-org/STING-CE.git
cd STING

# Run installation
./install.sh

# Follow prompts:
# - Installation directory (default: ~/.sting-ce)
# - Domain name (default: localhost)
# - Admin email
# - SSL certificate type (self-signed for dev)
```

**Installation Process:**
1. Validates system requirements
2. Creates installation directory
3. Generates SSL certificates
4. Creates environment files from config.yml
5. Builds Docker images
6. Initializes databases
7. Sets up Vault
8. Creates admin user

### Configuration Files

#### Main Configuration: conf/config.yml

```yaml
# LLM Service Configuration
llm_service:
  enabled: true
  default_model: microsoft/phi-4-mini-reasoning

  # OpenAI-compatible API (LM Studio, Ollama)
  ollama:
    endpoint: "http://10.0.0.142:11434"  # Your LM Studio server

  # Model settings
  models:
    phi4:
      enabled: true
      max_tokens: 119000  # Full context window!
      temperature: 0.7

# Chatbot Configuration
chatbot:
  enabled: true
  name: "Bee"
  model: "microsoft/phi-4-mini-reasoning"
  context_window: 200  # messages
  max_tokens: 80000  # Use most of context for responses

# Authentication
security:
  session_timeout: 3600  # 1 hour
  aal2_required_for_admin: true
  api_key_rate_limit: 1000  # requests per minute

# Honey Reserve (File Storage)
honey_reserve:
  enabled: true
  default_quota: 1073741824  # 1GB per user
  max_file_size: 104857600   # 100MB per file
  temp_retention_hours: 48
```

#### Environment Files (Generated)

Location: `$INSTALL_DIR/env/`

**Key Files:**
- `app.env` - Flask backend configuration
- `chatbot.env` - Bee Chat service
- `external-ai.env` - LLM service
- `knowledge.env` - Honey Jar service
- `kratos.env` - Authentication service
- `db.env` - Database credentials

**Regenerating Environment Files:**
```bash
# After modifying config.yml
./manage_sting.sh sync-config
./manage_sting.sh restart <service>
```

### Service Management

**Starting Services:**
```bash
./manage_sting.sh start [service]    # Start specific service or all
./manage_sting.sh status             # Check all service statuses
./manage_sting.sh stop [service]     # Stop services
./manage_sting.sh restart [service]  # Restart services
```

**Updating Services:**
```bash
# After code changes in project directory
./manage_sting.sh update app         # Backend (full rebuild)
./manage_sting.sh update frontend    # Frontend (full rebuild)
./manage_sting.sh update external-ai # External AI service

# Config changes only (no code)
./manage_sting.sh sync-config
./manage_sting.sh restart <service>
```

⚠️ **CRITICAL**: Always use `update` for code changes, not `restart`. See CLAUDE.md for details.

**Service Health Checks:**
```bash
# Individual service health
curl -k https://localhost:5050/health     # Backend
curl -k https://localhost:8443            # Frontend
curl http://localhost:8090/health         # Knowledge service
curl http://localhost:8091/health         # External AI

# All services
./manage_sting.sh status
```

### Database Management

**Accessing PostgreSQL:**
```bash
# Via Docker
docker exec -it sting-ce-db psql -U postgres -d sting_app

# Common queries
SELECT * FROM users;
SELECT * FROM api_keys WHERE is_active = true;
SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 10;
```

**Backup:**
```bash
# Automated daily backups (configured in config.yml)
backup:
  enabled: true
  default_directory: "${HOME}/sting-backups"
  retention_count: 5

# Manual backup
./scripts/backup/backup.sh
```

**Migrations:**
```bash
# Run database migrations
docker exec sting-ce-app flask db upgrade

# Create new migration
docker exec sting-ce-app flask db migrate -m "Add new table"
```

### Vault Management

**Common Operations:**
```bash
# Check seal status
docker exec sting-ce-vault vault status

# Unseal vault (if sealed after restart)
./manage_sting.sh unseal

# Read secret
docker exec sting-ce-vault vault kv get sting/database/credentials

# Write secret
docker exec sting-ce-vault vault kv put sting/app/api_key value="secret_value"
```

**Vault Initialization:**
Vault is auto-initialized during installation. Unseal keys stored in:
`$INSTALL_DIR/vault/unseal_keys.json`

⚠️ **BACKUP THIS FILE** - Without it, you cannot unseal Vault!

### LM Studio / Ollama Configuration

**LM Studio Setup:**
1. Install LM Studio on your GPU machine
2. Download model: `microsoft/phi-4-mini-reasoning`
3. Start server: Configure to listen on `0.0.0.0:11434`
4. Test: `curl http://YOUR_IP:11434/v1/models`

**Update STING Configuration:**
```yaml
# conf/config.yml
llm_service:
  ollama:
    endpoint: "http://YOUR_LM_STUDIO_IP:11434"
```

**Verify Connection:**
```bash
# From STING host
curl http://YOUR_LM_STUDIO_IP:11434/v1/models

# From external-ai container
docker exec sting-ce-external-ai curl http://YOUR_LM_STUDIO_IP:11434/v1/models
```

---

## TROUBLESHOOTING GUIDE {#troubleshooting}

### Common Issues

#### 1. Vault is Sealed After Restart

**Symptoms:**
- 500 errors on API endpoints
- Logs show: "Vault is sealed"
- Profile endpoints fail

**Solution:**
```bash
# Check vault status
docker exec sting-ce-vault vault status

# If sealed: true
./manage_sting.sh unseal

# Or manually
cat $INSTALL_DIR/vault/unseal_keys.json
docker exec -it sting-ce-vault vault operator unseal <KEY_1>
docker exec -it sting-ce-vault vault operator unseal <KEY_2>
docker exec -it sting-ce-vault vault operator unseal <KEY_3>
```

#### 2. Authentication Loops / Can't Login

**Symptoms:**
- Redirected to `/login?aal=aal2` repeatedly
- No email input field appears
- Console shows `"session_aal2_required","code":403`

**Common Causes:**
- User has TOTP/passkey configured, Kratos enforces AAL2
- AAL2 step-up flow not working properly

**Solution:**
```bash
# Option 1: Delete and recreate user
python3 -c "
import requests
requests.delete('https://localhost:4434/admin/identities/USER_ID', verify=False)
"
./manage_sting.sh create admin user@example.com

# Option 2: Check AAL2 middleware
# Temporarily disable in app/__init__.py (line 295)
# Comment out: api_aal2_response = check_aal2_for_api_only()
```

#### 3. Bee Chat Returns Empty Responses

**Symptoms:**
- Status 200 but empty `response` field
- No LLM generation logs in external-ai

**Debug Steps:**
```bash
# 1. Check external-ai can see models
docker logs sting-ce-external-ai 2>&1 | grep -i "Available.*models"

# Should show: Available Ollama models: ['microsoft/phi-4-mini-reasoning', ...]

# 2. Test LLM directly
docker exec sting-ce-external-ai python3 -c "
import requests
r = requests.post('http://10.0.0.142:11434/v1/chat/completions', json={
    'model': 'microsoft/phi-4-mini-reasoning',
    'messages': [{'role': 'user', 'content': 'Hi'}]
})
print(r.status_code, r.json())
"

# 3. Check external-ai logs for errors
docker logs --tail 100 sting-ce-external-ai 2>&1 | grep -i error
```

**Common Fixes:**
- Ensure LM Studio is running and accessible
- Verify firewall allows connection on port 11434
- Check model name matches exactly
- Update external-ai to support OpenAI API (see CLAUDE.md)

#### 4. Database Connection Errors

**Symptoms:**
- Services won't start
- "psycopg2.OperationalError: could not connect to server"

**Solution:**
```bash
# Check database container
docker ps | grep sting-ce-db

# If not running
docker-compose up -d db

# Check logs
docker logs sting-ce-db

# Test connection
docker exec sting-ce-db psql -U postgres -c "SELECT 1"

# Restart dependent services
./manage_sting.sh restart app knowledge chatbot
```

#### 5. Frontend Build Failures

**Symptoms:**
- `./manage_sting.sh update frontend` fails
- React compilation errors

**Solution:**
```bash
# Clear node_modules and rebuild
cd /path/to/STING/frontend
rm -rf node_modules package-lock.json
npm install
npm run build

# Or force rebuild
cd /path/to/install/.sting-ce
docker-compose build --no-cache frontend
docker-compose up -d frontend
```

#### 6. Conversation Table Missing

**Symptoms:**
- Bee Chat returns: "I encountered an error processing your request"
- Logs show: `relation "conversations" does not exist`

**Solution:**
```bash
# Run database migrations
docker exec sting-ce-app flask db upgrade

# Or create table manually
docker exec -it sting-ce-db psql -U postgres -d sting_app -c "
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    session_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"
```

### Logging & Debugging

**View Logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f sting-ce-app
docker logs -f sting-ce-chatbot
docker logs -f sting-ce-external-ai

# Filter for errors
docker logs sting-ce-app 2>&1 | grep -i error

# Management script logs
tail -f $INSTALL_DIR/logs/manage_sting.log
```

**Enable Debug Mode:**
```yaml
# conf/config.yml
application:
  debug: true

# Or in env files
# env/app.env
LOG_LEVEL="DEBUG"
```

**Check Service Health:**
```bash
./manage_sting.sh status

# Expected output:
# ✅ db (healthy)
# ✅ vault (healthy)
# ✅ kratos (healthy)
# ✅ app (healthy)
# ✅ frontend (healthy)
# ✅ chatbot (healthy)
# ✅ external-ai (healthy)
```

---

## SECURITY BEST PRACTICES {#security-practices}

### Production Deployment Checklist

**1. Network Security:**
```yaml
# Use real SSL certificates (not self-signed)
application:
  ssl:
    enabled: true
    cert_dir: "/etc/letsencrypt/live/your-domain.com"

# Restrict external access
# Use firewall to allow only:
# - 8443 (Frontend HTTPS)
# - 5050 (Backend API HTTPS)
# Block all other ports externally
```

**2. Authentication Hardening:**
```yaml
# Enforce strong authentication
security:
  aal2_required_for_admin: true
  session_timeout: 1800  # 30 minutes
  require_webauthn_for_admin: true

# Disable password-based auth (passwordless only)
kratos:
  methods:
    password:
      enabled: false
```

**3. API Key Management:**
- Rotate API keys quarterly
- Use minimum required scopes
- Set aggressive rate limits
- Enable key expiration
- Monitor usage via audit logs

```python
# Review active keys
SELECT name, scopes, created_at, last_used_at, expires_at
FROM api_keys
WHERE is_active = true;

# Revoke unused keys
UPDATE api_keys SET is_active = false
WHERE last_used_at < NOW() - INTERVAL '90 days';
```

**4. Data Encryption:**
- All Honey Jar documents: AES-256-GCM encrypted
- Database connections: SSL/TLS required
- Session cookies: Secure, HttpOnly, SameSite=Strict
- API responses: HTTPS only

**5. Audit Logging:**
```yaml
# Enable comprehensive auditing
knowledge:
  audit_enabled: true
  audit_retention_days: 365  # 1 year minimum

# Review logs regularly
docker exec sting-ce-app psql -U postgres -d sting_app -c "
SELECT event_type, COUNT(*)
FROM audit_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY event_type;
"
```

**6. Backup & Recovery:**
```bash
# Automated daily backups
0 2 * * * /path/to/STING/scripts/backup/backup.sh

# Test restore quarterly
./scripts/backup/restore.sh /path/to/backup.tar.gz

# Store backups off-site (encrypted)
```

**7. System Updates:**
```bash
# Monthly security updates
docker pull postgres:16
docker pull oryd/kratos:v1.3.0
./manage_sting.sh update all

# Review changelogs
cat CHANGELOG.md
```

### Security Incident Response

**1. Suspected Breach:**
```bash
# Immediately:
# - Revoke all API keys
UPDATE api_keys SET is_active = false;

# - Force logout all users
docker exec sting-ce-vault vault write sting/sessions/invalidate all=true

# - Review audit logs
SELECT * FROM audit_logs
WHERE timestamp > '2025-10-06 00:00:00'
ORDER BY timestamp DESC;

# - Check for unauthorized access
SELECT * FROM audit_logs
WHERE event_type IN ('AUTH_FAILURE', 'UNAUTHORIZED_ACCESS')
AND timestamp > NOW() - INTERVAL '24 hours';
```

**2. Data Leak Detection:**
```bash
# Check file access patterns
SELECT user_id, COUNT(*) as file_count
FROM honey_jar_access_logs
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY user_id
HAVING COUNT(*) > 100;  # Suspicious if > 100 files/hour
```

**3. Recovery Steps:**
1. Isolate affected systems (network segmentation)
2. Preserve evidence (backup logs, database snapshots)
3. Identify scope (affected users, data, systems)
4. Contain breach (revoke credentials, patch vulnerabilities)
5. Eradicate threat (remove malware, close exploits)
6. Recover systems (restore from clean backups)
7. Post-incident review (document learnings, update procedures)

---

## COMPLIANCE FRAMEWORKS {#compliance}

### HIPAA Compliance

**STING's HIPAA-Relevant Features:**

**1. Access Controls:**
- Unique user identification (Kratos identities)
- Emergency access procedures (recovery codes)
- Automatic logoff (session timeouts)
- Encryption and decryption (AES-256-GCM)

**2. Audit Controls:**
- Comprehensive audit logging
- User activity tracking
- Access attempt logging
- 365-day retention minimum

**3. Integrity Controls:**
- Hash verification for documents
- Digital signatures for API requests
- Tamper-evident audit logs

**4. Transmission Security:**
- End-to-end encryption (TLS 1.3)
- Secure API endpoints (HTTPS only)
- Certificate validation

**HIPAA Configuration:**
```yaml
# conf/config.yml
pii_compliance:
  enabled: true
  profiles:
    - name: "HIPAA"
      patterns:
        - type: "SSN"
          regex: "\\b\\d{3}-\\d{2}-\\d{4}\\b"
        - type: "MRN"
          regex: "\\bMRN[:\\s]?\\d{6,}\\b"
        - type: "PHI"
          keywords: ["diagnosis", "treatment", "medication"]
      actions:
        - "REDACT"
        - "LOG"
        - "ALERT"

honey_reserve:
  audit_enabled: true
  audit_retention_days: 2555  # 7 years (HIPAA requirement)
```

### GDPR Compliance

**STING's GDPR-Relevant Features:**

**1. Right to Access (Article 15):**
```bash
# User data export
GET /api/users/me/data-export
Response: Complete user data package (JSON)
```

**2. Right to Erasure (Article 17):**
```bash
# Delete user and all data
DELETE /api/users/me
# Cascades to:
# - Identity (Kratos)
# - API keys
# - Honey jars (owned)
# - Conversations
# - Audit logs (anonymized, not deleted)
```

**3. Data Portability (Article 20):**
```bash
# Export in machine-readable format
GET /api/users/me/data-export?format=json
```

**4. Privacy by Design:**
- Data minimization (collect only necessary data)
- Encryption by default (all stored data)
- Pseudonymization (UUIDs instead of emails in logs)
- Purpose limitation (explicit consent for data use)

**GDPR Configuration:**
```yaml
pii_compliance:
  profiles:
    - name: "GDPR"
      patterns:
        - type: "EMAIL"
        - type: "PHONE"
        - type: "EU_ID"
        - type: "IP_ADDRESS"
      actions:
        - "PSEUDONYMIZE"  # Replace with UUID in logs
        - "ENCRYPT"       # AES-256-GCM storage
        - "LOG_CONSENT"   # Track consent basis
```

### SOC 2 Compliance

**STING's SOC 2-Relevant Controls:**

**1. Security:**
- Multi-factor authentication
- Encryption at rest and in transit
- Access logging and monitoring
- Incident response procedures

**2. Availability:**
- Service health monitoring
- Automated failover (if configured)
- Backup and recovery procedures
- 99.9% uptime SLA capability

**3. Confidentiality:**
- Role-based access control
- Data classification (Honey Jar permissions)
- Secure disposal (encrypted deletion)

**4. Processing Integrity:**
- Input validation
- Error handling and logging
- Transaction logging
- Data integrity verification

**5. Privacy:**
- Consent management
- Data retention policies
- User data access/export
- Secure data deletion

---

## CODE EXAMPLES {#code-examples}

### Creating a Custom Authentication Decorator

```python
# app/utils/custom_decorators.py
from functools import wraps
from flask import g, jsonify

def require_honey_jar_owner(f):
    """Require user to be owner of honey jar"""
    @wraps(f)
    def decorated_function(jar_id, *args, **kwargs):
        from app.models.honey_jar_models import HoneyJar
        from app.database import get_db_session

        with get_db_session() as db:
            jar = db.query(HoneyJar).filter_by(id=jar_id).first()

            if not jar:
                return jsonify({"error": "Honey jar not found"}), 404

            if jar.owner_id != g.user.id and not g.user.is_admin:
                return jsonify({"error": "Unauthorized"}), 403

        return f(jar_id, *args, **kwargs)

    return decorated_function

# Usage in routes
from app.utils.decorators import require_auth_method
from app.utils.custom_decorators import require_honey_jar_owner

@app.route('/api/honey-jars/<jar_id>/delete', methods=['DELETE'])
@require_auth_method(['webauthn', 'totp'])
@require_honey_jar_owner
def delete_honey_jar(jar_id):
    # User is authenticated with secure method AND owns the jar
    delete_jar(jar_id)
    return jsonify({"status": "deleted"})
```

### Integrating with Bee Chat Programmatically

```python
# examples/bee_chat_client.py
import requests
import json

class BeeClient:
    def __init__(self, api_key, base_url="https://localhost:5050"):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        })
        self.session.verify = False  # For dev; use True in production

    def chat(self, message, conversation_id=None, honey_jar_id=None):
        """Send a message to Bee"""
        payload = {
            "message": message,
            "conversation_id": conversation_id,
            "context": {}
        }

        if honey_jar_id:
            payload["context"]["honey_jar_id"] = honey_jar_id

        response = self.session.post(
            f"{self.base_url}/api/bee/chat",
            json=payload,
            timeout=90  # Phi-4 can take time for complex reasoning
        )

        response.raise_for_status()
        return response.json()

    def get_conversations(self):
        """Retrieve conversation history"""
        response = self.session.get(f"{self.base_url}/api/bee/conversations")
        response.raise_for_status()
        return response.json()

# Usage
if __name__ == "__main__":
    client = BeeClient(api_key="sk_YOUR_API_KEY_HERE")

    # Simple chat
    result = client.chat("Explain STING's authentication tiers")
    print("Bee:", result["response"])

    # Chat with Honey Jar context
    result = client.chat(
        "Summarize our security policy",
        honey_jar_id="jar_security_docs"
    )
    print("Bee (with context):", result["response"])

    # Continue conversation
    result = client.chat(
        "What are the key requirements?",
        conversation_id=result["conversation_id"]
    )
    print("Bee (follow-up):", result["response"])
```

### Adding Custom PII Detection Pattern

```python
# app/routes/pii_routes.py extension
from app.utils.decorators import require_auth_method

@pii_bp.route('/api/pii/patterns/custom', methods=['POST'])
@require_auth_method(['webauthn', 'totp'])  # Admin only
def add_custom_pattern():
    """Add a custom PII detection pattern"""
    data = request.get_json()

    pattern = {
        "name": data["name"],
        "type": data["type"],  # e.g., "INTERNAL_ID"
        "regex": data["regex"],
        "confidence": data.get("confidence", 0.9),
        "action": data.get("action", "REDACT")
    }

    # Validate regex
    import re
    try:
        re.compile(pattern["regex"])
    except re.error as e:
        return jsonify({"error": f"Invalid regex: {e}"}), 400

    # Add to active patterns
    from app.services.pii_service import pii_detector
    pii_detector.add_custom_pattern(pattern)

    return jsonify({
        "status": "added",
        "pattern": pattern
    })

# Testing the custom pattern
payload = {
    "name": "Employee Badge ID",
    "type": "BADGE_ID",
    "regex": r"\bBADGE[:\s]?[A-Z]\d{5}\b",
    "confidence": 0.95,
    "action": "REDACT"
}

response = requests.post(
    "https://localhost:5050/api/pii/patterns/custom",
    headers={"X-API-Key": "sk_YOUR_API_KEY"},
    json=payload,
    verify=False
)

print(response.json())
# {"status": "added", "pattern": {...}}
```

### Bulk Document Upload to Honey Jar

```python
# examples/bulk_upload_to_honey_jar.py
import os
import requests
from pathlib import Path

class HoneyJarUploader:
    def __init__(self, api_key, jar_id, base_url="https://localhost:5050"):
        self.api_key = api_key
        self.jar_id = jar_id
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})
        self.session.verify = False

    def upload_file(self, file_path, metadata=None):
        """Upload a single file"""
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f)}
            data = {}

            if metadata:
                import json
                data['metadata'] = json.dumps(metadata)

            response = self.session.post(
                f"{self.base_url}/api/honey-jars/{self.jar_id}/documents",
                files=files,
                data=data
            )

            response.raise_for_status()
            return response.json()

    def upload_directory(self, directory_path, recursive=True):
        """Upload all files in a directory"""
        path = Path(directory_path)
        pattern = "**/*" if recursive else "*"

        results = {
            "uploaded": [],
            "failed": []
        }

        for file_path in path.glob(pattern):
            if file_path.is_file():
                try:
                    result = self.upload_file(
                        str(file_path),
                        metadata={
                            "category": file_path.parent.name,
                            "original_path": str(file_path)
                        }
                    )
                    results["uploaded"].append({
                        "file": str(file_path),
                        "document_id": result["document_id"]
                    })
                    print(f"✅ Uploaded: {file_path}")
                except Exception as e:
                    results["failed"].append({
                        "file": str(file_path),
                        "error": str(e)
                    })
                    print(f"❌ Failed: {file_path} - {e}")

        return results

# Usage
if __name__ == "__main__":
    uploader = HoneyJarUploader(
        api_key="sk_YOUR_API_KEY",
        jar_id="jar_company_docs"
    )

    # Upload entire directory
    results = uploader.upload_directory("/path/to/documents", recursive=True)

    print(f"\nUploaded: {len(results['uploaded'])}")
    print(f"Failed: {len(results['failed'])}")
```

---

## FREQUENTLY ASKED QUESTIONS {#faq}

### General

**Q: What makes STING different from ChatGPT or Claude?**

A: STING provides:
- **Complete data sovereignty** - Your data never leaves your infrastructure
- **On-premises deployment** - Run on your own servers/cloud
- **Custom model selection** - Choose models that fit your needs (Phi-4, custom fine-tuned models, etc.)
- **Enterprise security** - Tiered auth, encryption, audit logs, compliance
- **Knowledge management** - Honey Jars for secure document repositories
- **Extensibility** - Worker Bees for custom data connectors

**Q: Can I use STING with my existing LLMs?**

A: Yes! STING supports any OpenAI-compatible API:
- LM Studio (tested and recommended)
- Ollama
- vLLM
- LocalAI
- OpenAI API (if you want cloud models)
- Any custom model server with OpenAI-compatible endpoints

**Q: How do I choose between models?**

A: Model selection guide:
- **Phi-4 Mini (14B)**: Best balance of quality and speed, excellent reasoning, 119K context
- **Qwen 3 Coder (30B)**: Superior for code generation and analysis
- **Custom fine-tuned**: For domain-specific tasks (medical, legal, etc.)
- **Smaller models (1-7B)**: When speed is critical and quality can be lower

### Authentication

**Q: What's the difference between AAL1 and AAL2?**

A:
- **AAL1** (Authenticator Assurance Level 1): Single-factor authentication (email + magic link)
- **AAL2**: Multi-factor authentication (passkey/TOTP + email, or password + passkey/TOTP)

AAL2 is required for admin users and sensitive operations (Tier 3+).

**Q: Can I disable passwords entirely?**

A: Yes! Set in `kratos/kratos.yml`:
```yaml
methods:
  password:
    enabled: false
  code:  # Magic link email
    enabled: true
  webauthn:
    enabled: true
  totp:
    enabled: true
```

This enforces passwordless authentication only.

**Q: How do API keys work with tiered auth?**

A: API keys bypass the AAL system but are checked for scopes:
- API key with `admin` scope can access Tier 3 endpoints
- API key with `read` scope limited to read-only operations
- API keys honor rate limits and permissions

### Bee Chat

**Q: How does Bee access Honey Jar content?**

A: When you specify a `honey_jar_id` in your chat request:
1. Bee sends your query to the knowledge service
2. Semantic search finds relevant document chunks
3. Top results injected into Phi-4's context
4. Phi-4 generates response with this knowledge

**Q: Can Bee remember previous conversations?**

A: Yes! With Phi-4's 119K context:
- Stores up to 200 messages in conversation history
- Full context loaded for each response
- Can reference any part of the conversation
- Use `conversation_id` to continue threads

**Q: How do I make Bee use the <think> reasoning tags?**

A: Phi-4 will automatically use `<think>` tags for complex queries. You can encourage it:
- Ask multi-step questions
- Request detailed analysis
- Explicitly ask: "Think through this step-by-step"

### Honey Jars

**Q: What file types can I upload?**

A: Default supported types:
- Documents: PDF, DOCX, TXT, MD, HTML
- Data: JSON, XML, CSV
- Code: Any text-based code file
- Limit: 100MB per file

Configurable in `config.yml`:
```yaml
knowledge:
  max_document_size: 104857600  # 100MB
  allowed_document_types:
    - "text/plain"
    - "application/pdf"
    - "application/json"
    # Add more MIME types
```

**Q: Are Honey Jar documents encrypted?**

A: Yes! All documents encrypted with AES-256-GCM:
- Encryption key derived from Kratos identity
- Unique key per user
- Stored encrypted in PostgreSQL
- Decrypted only when accessed by authorized users

**Q: Can multiple users access the same Honey Jar?**

A: Yes, via team-based access:
```python
# Create team jar
POST /api/honey-jars/create
{
    "name": "Team Docs",
    "is_public": false,
    "team_id": "team_engineering"
}

# All team members can access
```

### Deployment

**Q: Can STING run on Windows?**

A: Yes, via WSL2 (Windows Subsystem for Linux):
1. Install WSL2: `wsl --install`
2. Install Docker Desktop with WSL2 backend
3. Run STING installation in WSL2 Ubuntu

**Q: What are the minimum hardware requirements?**

A:
- **CPU**: 4 cores (8+ recommended)
- **RAM**: 8GB (16GB+ for optimal performance)
- **Storage**: 20GB for STING + models (100GB+ recommended)
- **GPU**: Optional but significantly improves LLM performance

**Q: Can I run STING in the cloud?**

A: Yes! STING works on:
- AWS EC2
- Google Cloud Compute Engine
- Azure Virtual Machines
- DigitalOcean Droplets
- Any VPS with Docker support

Recommended: GPU instances for better LLM performance.

**Q: How do I scale STING for multiple users?**

A: Horizontal scaling approach:
1. Separate database server (PostgreSQL on dedicated instance)
2. Multiple app/chatbot replicas behind load balancer
3. Shared Redis for session management
4. Dedicated LLM server with multiple GPUs
5. CDN for frontend static assets

---

## CONCLUSION

This Bee Brain v2.0.0 knowledge base is designed to leverage Phi-4 Mini's massive 119,000 token context window. With this comprehensive knowledge always in context, I can provide:

- **Deeper technical support** with complete documentation reference
- **More accurate troubleshooting** drawing from extensive error catalogs
- **Better security guidance** with full framework knowledge
- **Complete code examples** without truncation
- **Comprehensive analysis** across multiple documents

Remember: You have 119K tokens at your disposal. Don't hesitate to load this entire knowledge base, plus Honey Jar documents, plus conversation history - I can handle it all simultaneously and provide truly comprehensive, contextually-aware assistance.

**Ready to help with anything STING-related (or beyond)!**
