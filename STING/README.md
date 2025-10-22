# STING Platform
### Secure Trusted Intelligence and Networking Guardian

**A comprehensive, enterprise-ready platform for secure, private LLM deployment with advanced knowledge management capabilities.**

---

## 🚀 **Platform Overview**

STING is a cutting-edge microservices platform that combines secure AI deployment with innovative knowledge management. Built for enterprises who demand privacy, security, and scalability without compromising on AI capabilities.

### **Core Value Propositions**

- **🔒 Enterprise Security**: Complete data sovereignty with on-premises deployment
- **🧠 Advanced AI**: Microsoft Phi-3 Medium and other enterprise-grade LLMs
- **🍯 Knowledge Management**: Revolutionary "Honey Jar" system for organizational knowledge
- **🐝 Intelligent Documentation**: Version-aware Bee Brain system with auto-updating AI knowledge
- **🔌 Seamless Integration**: Modern React frontend with robust Flask backend
- **📈 Scalable Architecture**: Docker-based microservices with HashiCorp Vault security

---

## 🏗️ **Architecture & Technology Stack**

### **Frontend Layer**
- **React 18** with Material-UI and Tailwind CSS
- **HTTPS-enabled development** with self-signed certificates
- **Real-time chat interface** with "Bee" AI assistant
- **Knowledge management UI** with marketplace integration

### **Backend Services**
- **Flask/Python API** with PostgreSQL database (port 5050)
- **Ory Kratos Authentication** with WebAuthn support (ports 4433/4434)
- **LLM Gateway Services** with native macOS Metal acceleration (port 8086)
- **Chroma Vector Database** for semantic search capabilities
- **Redis** for caching and session management

### **AI & Machine Learning**
- **Microsoft Phi-3 Medium (14B)** - Primary enterprise model
- **Dynamic Model Loading** with intelligent memory management
- **Hardware Acceleration** via Metal Performance Shaders (macOS)
- **Content Filtering** and enterprise safety controls
- **Bee Brain System** - Version-aware AI knowledge base with automatic updates

### **Infrastructure**
- **Docker Compose** orchestration with health monitoring
- **HashiCorp Vault** for secrets management
- **Nginx** reverse proxy with SSL termination
- **Mailslurper** for development email testing

---

## 🍯 **Honey Jar Knowledge System**

### **Revolutionary Knowledge Management**

STING introduces the "Honey Jar" concept - containerized knowledge bases that organizations can create, share, and monetize:

#### **Key Features**
- **Document Ingestion**: PDF, DOCX, HTML, JSON, Markdown, TXT support
- **Vector Embeddings**: Semantic search using sentence transformers
- **Marketplace Integration**: Buy, sell, and distribute knowledge bases
- **Encryption Support**: Secure proprietary knowledge with enterprise-grade encryption
- **Role-Based Access**: Queen/Worker/Drone hierarchy for team management
- **Honey Combs** 🏗️: Pre-configured data source templates for instant connectivity

#### **Honey Combs - Rapid Data Connectivity**
Connect to any data source in minutes with pre-built templates:
- **Database Combs**: PostgreSQL, MySQL, MongoDB, Snowflake, and more
- **API Combs**: REST, GraphQL, SOAP with OAuth2/API key authentication
- **File System Combs**: S3, Google Drive, SharePoint, FTP
- **Stream Combs**: Kafka, RabbitMQ, Kinesis for real-time data
- **Built-in Scrubbing**: Automatic PII detection and removal for compliance

#### **Business Applications**
- **Training Materials**: Create searchable company handbooks
- **Technical Documentation**: API references and code repositories
- **Compliance Knowledge**: Regulatory and policy information
- **Industry Expertise**: Monetize specialized knowledge through marketplace
- **Database Snapshots**: Generate Honey Jars from production data (with scrubbing)
- **API Archives**: Package third-party API data into knowledge bases

---

## 🐝 **Bee Brain - Intelligent AI Documentation System**

### **Version-Aware Knowledge Management**

STING's Bee AI Assistant is powered by the **Bee Brain** system - a revolutionary approach to AI documentation that ensures accurate, version-specific guidance for every STING installation.

#### **Why Bee Brain Matters**
Unlike generic chatbots that provide outdated or incorrect information, Bee Brain:

- 🎯 **Knows Your Version**: Automatically detects and loads documentation matching your exact STING version
- 🔄 **Always Current**: Updates automatically via webhooks when documentation changes
- 🧠 **Optimized for AI**: Structured JSON format for lightning-fast retrieval and accurate responses
- 🛡️ **Version Safety**: Major version compatibility prevents incompatible documentation (1.x docs never load on 2.x)
- 📦 **Lightweight**: ~3MB per version with 300+ documentation files indexed

#### **Key Features**

**🚀 One-Line Updates**
```bash
curl -fsSL https://raw.githubusercontent.com/AlphaBytez/STING-CE-Public/main/STING/scripts/update_bee_brain.sh | sudo bash
```

**📊 Admin Control**
```bash
# Check status
curl http://localhost:5050/api/admin/bee-brain/status

# Force update
curl -X POST http://localhost:5050/api/admin/bee-brain/update
```

**🔗 GitHub Webhook Integration**
Automatically regenerates knowledge base when:
- New STING releases are tagged
- Documentation changes are pushed to main branch

**🎨 Custom Knowledge**
Add your own documentation to `/opt/sting-ce/docs/` and regenerate - Bee instantly knows about it!

#### **Technical Innovation**

Bee Brain packages **348 documentation files** (2.8 MB) into:
- Hierarchical JSON structure preserving directory organization
- Core knowledge sections for instant system awareness
- Metadata including checksums, version compatibility, and creation timestamps
- Fast keyword and semantic search capabilities

**Compatibility Example:**
| Your STING | Bee Brain Used | Reason |
|------------|----------------|---------|
| 1.0.0 | bee_brain_v1.0.0.json | Exact match |
| 1.2.5 | bee_brain_v1.2.0.json | Latest compatible 1.x |
| 2.0.0 | bee_brain_v2.0.0.json | Major version enforced |

**Learn More:** See [Bee Brain Documentation](./docs/bee-brain.md) for complete guide

---

## 🚀 **Quick Start Guide**

### **System Requirements**
- **macOS** (Apple Silicon recommended) or **Linux**
- **16GB RAM minimum** (32GB+ recommended for multiple models)
- **Docker Desktop** and **Docker Compose**
- **Python 3.9+** with virtual environment support

### **Installation**

⚠️ **Important**: Before installing, decide how you'll access STING:
- **Single machine only?** Use the default localhost configuration
- **Multiple machines/devices?** See [Passkey Quick Start Guide](./PASSKEY_QUICKSTART.md) first!

```bash
# 1. System Setup
./pre_install.sh

# 2. Configure HuggingFace Token (required for models)
./setup_hf_token.sh

# 3. Install STING Platform with Admin Setup (Recommended)
./install_sting.sh install --debug

# Alternative: Install without admin prompts
./install_sting.sh install --no-prompt --no-admin
```

### **Admin User Setup**

STING now automatically prompts for admin user creation during fresh installations. This provides immediate access to admin features like:

- **🐝 LLM Settings**: Model management with progress tracking
- **👥 User Management**: Promote users and manage permissions  
- **⚙️ System Administration**: Advanced configuration and monitoring

#### **Admin Setup Options**

```bash
# Automatic admin setup (default for fresh installs)
./install_sting.sh install                    # Prompts for admin creation

# Pre-specify admin email for automation  
./install_sting.sh install --admin-email=admin@company.com

# Skip admin setup entirely
./install_sting.sh install --no-admin

# Manual admin setup after installation
./setup_first_admin.sh                       # Interactive setup
python3 create_admin.py --email admin@company.com --temp-password
```

#### **Security Best Practices**

- ✅ **Use temporary passwords** for initial admin accounts
- ✅ **Force password changes** on first login
- ✅ **Create admin accounts programmatically** for production deployments
- ✅ **Regularly audit admin user list** with `python3 check_admin.py`

### **Access Points**
- **Frontend**: https://localhost:3010 (production) or :8443 (development)
- **API Documentation**: https://localhost:5050/api/
- **Admin Authentication**: https://localhost:4433/
- **Vault UI**: http://localhost:8200/

---

## 💼 **Enterprise Features**

### **Security & Compliance**
- ✅ **Data Sovereignty**: All processing happens on-premises
- ✅ **Zero External Dependencies**: No cloud API calls required
- ✅ **Audit Logging**: Complete conversation and action tracking
- ✅ **Role-Based Access Control**: Granular permissions management
- ✅ **Encryption at Rest**: Vault-managed secrets and encrypted storage

### **Authentication & Identity**
- ✅ **Passwordless Authentication**: WebAuthn/FIDO2 passkey support
- ✅ **Multi-Factor Authentication**: TOTP/Authenticator app support
- ✅ **Enterprise SSO Ready**: Ory Kratos identity management
- ✅ **Session Management**: Secure session handling with automatic expiry
- ✅ **Cross-Device Support**: Passkeys work across all your devices (with proper configuration)

### **Scalability & Performance**
- ✅ **Microservices Architecture**: Independent scaling of components
- ✅ **Load Balancing**: Multiple model instances for high availability
- ✅ **Caching Strategy**: Redis-based session and response caching
- ✅ **Health Monitoring**: Comprehensive service health checks

### **AI Capabilities**
- ✅ **Multiple Model Support**: Phi-3, DeepSeek, TinyLlama, and more
- ✅ **Dynamic Loading**: Models loaded on-demand to optimize memory
- ✅ **Content Filtering**: Enterprise-safe AI responses
- ✅ **Context Management**: Conversation persistence and retrieval
- ✅ **Version-Aware Documentation**: Bee Brain system ensures accurate, compatible guidance
- ✅ **Auto-Updating Knowledge**: GitHub webhooks for instant documentation synchronization

---

## 🎯 **Use Cases & Market Applications**

### **Enterprise Deployment**
- **Legal Firms**: Secure document analysis and research
- **Healthcare**: HIPAA-compliant patient data processing
- **Financial Services**: Regulatory compliance and risk analysis
- **Government**: Classified information processing with air-gapped deployment

### **Knowledge Monetization**
- **Consulting Firms**: Package expertise into sellable Honey Pots
- **Educational Institutions**: Create and distribute course materials
- **Technical Organizations**: Monetize documentation and best practices
- **Industry Experts**: Build subscription-based knowledge services

### **Development & DevOps**
- **Code Documentation**: Searchable API references and examples
- **Incident Response**: Historical troubleshooting knowledge bases
- **Onboarding**: Interactive training systems for new employees
- **Process Automation**: AI-assisted workflow documentation

---

## 🛠️ **Development & Management**

### **Command Line Interface**

```bash
# Service Management
./manage_sting.sh start          # Start all services
./manage_sting.sh stop           # Stop services  
./manage_sting.sh restart        # Restart services
./manage_sting.sh status         # Check service health
./manage_sting.sh logs [service] # View logs

# Model Management  
./sting-llm start               # Start native LLM service
./sting-llm preload phi3        # Preload specific model
./sting-llm status              # Check model status

# Development
cd frontend && npm start         # React development server
cd frontend && npm test          # Run frontend tests
msting update [service]         # Update specific service
```

### **Configuration Management**

All configuration is centralized in `/conf/config.yml`:
- **Service endpoints** and port assignments
- **Model selection** and performance tuning
- **Security settings** and authentication methods
- **Feature flags** for optional components

---

## 📊 **Performance & Specifications**

### **Model Performance**
- **Phi-3 Medium**: ~8GB memory, 14B parameters, enterprise-grade responses
- **Response Times**: <2 seconds for typical queries with Metal acceleration
- **Concurrent Users**: 10-50+ depending on hardware configuration
- **Model Switching**: Dynamic loading in 3-8 seconds

### **System Resources**
- **Base Installation**: ~5GB disk space
- **Model Storage**: 3-15GB per model (automatically managed)
- **Runtime Memory**: 8-16GB for typical workloads
- **Database**: PostgreSQL with automatic backup and recovery

---

## 🔄 **Roadmap & Future Development**

### **Immediate Priorities** (Q1 2025)
- [ ] Enhanced knowledge service API integration
- [ ] Marketplace payment processing and user management
- [ ] Advanced encryption for proprietary Honey Jars
- [ ] Honey Combs connector library expansion (30+ data sources)
- [ ] Automated PII scrubbing for GDPR/CCPA compliance
- [ ] WebAuthn passwordless authentication rollout

### **Medium-term Goals** (Q2-Q3 2025)
- [ ] Multi-tenant deployment capabilities
- [ ] Kubernetes orchestration support
- [ ] Advanced analytics and usage dashboards
- [ ] Plugin ecosystem for third-party integrations

### **Long-term Vision** (Q4 2025+)
- [ ] Blockchain-based knowledge verification
- [ ] AI model fine-tuning capabilities
- [ ] Global knowledge marketplace federation
- [ ] Edge deployment for IoT and mobile

---

## 🔍 **Debugging & Troubleshooting**

### **Debug Interface**
STING includes comprehensive debugging tools for development and troubleshooting:

- **Debug Dashboard**: Access at https://localhost:8443/debug
- **Service Health Monitoring**: Real-time status of all platform services
- **API Testing Interface**: Interactive testing of authentication endpoints
- **Container Status**: Docker health checks and logs

### **Quick Debugging Commands**
```bash
# Check all service health
curl -s http://localhost:5050/api/debug/service-statuses | jq

# View service logs
docker logs sting-ce-knowledge -f
docker logs sting-ce-app-1 -f

# Test specific services
curl http://localhost:8090/health  # Knowledge service
curl http://localhost:8888/health  # Chatbot service
```

### **macOS Permission Issues**
On macOS, you may encounter permission errors with the `msting` command after installation or updates:
```bash
# Quick fix for permission issues
./fix_permissions.sh

# Or manually fix permissions
chmod +x ~/.sting-ce/manage_sting.sh
find ~/.sting-ce -name "*.sh" -type f -exec chmod +x {} \;
```
See [macOS Permissions Guide](docs/MACOS_PERMISSIONS.md) for detailed information.

### **Documentation**
- **[Admin Guide](docs/ADMIN_GUIDE.md)**: Administrative features and document approval workflow
- **[Honey Jar User Guide](docs/features/HONEY_JAR_USER_GUIDE.md)**: Complete guide to knowledge management
- **[Debugging Guide](docs/DEBUGGING.md)**: Comprehensive debugging documentation
- **[Service Health Monitoring](docs/SERVICE_HEALTH_MONITORING.md)**: Health check reference
- **[Troubleshooting Guide](troubleshooting/README.md)**: Common issues and fixes
- **[Authentication Debugging](kratos/LOGIN_TROUBLESHOOTING.md)**: Auth-specific issues

---

## 💰 **Investment & Business Opportunity**

### **Market Positioning**
STING addresses the critical gap between powerful AI capabilities and enterprise security requirements. As organizations increasingly demand on-premises AI solutions, STING provides:

- **Immediate Revenue**: Knowledge marketplace transactions and licensing
- **Recurring Revenue**: Enterprise subscriptions and support services  
- **Scalable Growth**: Platform network effects as more organizations contribute knowledge
- **Strategic Moats**: First-mover advantage in containerized knowledge management

### **Competitive Advantages**
- **Technical Innovation**: Unique "Honey Jar" knowledge containerization
- **Security First**: Built from ground-up for enterprise security requirements
- **User Experience**: Consumer-grade interface with enterprise-grade capabilities
- **Ecosystem Approach**: Platform creates value for both consumers and producers of knowledge

---

## 📞 **Contact & Support**

### **Getting Started**
- **Documentation**: See `docs/` directory for detailed guides
- **Community**: GitHub Discussions and issue tracking
- **Enterprise Support**: Contact for dedicated support packages

### **Contributing**
- **Development**: See `CONTRIBUTING.md` for guidelines
- **Bug Reports**: Use GitHub issues with detailed reproduction steps  
- **Feature Requests**: Community voting and roadmap integration

---

## 📝 **License & Legal**

### STING Platform License

**STING Platform** - Proprietary software with enterprise licensing options.

- **Development License**: Free for non-commercial use (see [LICENSE](./LICENSE))
- **Enterprise License**: Contact for commercial deployment terms
- **Knowledge Marketplace**: Revenue sharing with knowledge contributors

### Open Source Components

STING is built on the foundation of many excellent open source projects:

- **Third-Party Licenses**: See [LICENSE-THIRD-PARTY.md](./LICENSE-THIRD-PARTY.md) for complete list
- **Credits & Acknowledgments**: See [CREDITS.md](./CREDITS.md) for detailed acknowledgments
- **License Compatibility**: All dependencies are carefully selected for license compatibility

### License Management

- **Automated Auditing**: Run `python scripts/audit-licenses.py` to scan all dependencies
- **Compliance**: All open source components are used in accordance with their licenses
- **Attribution**: Proper attribution is maintained in documentation and source code

*For licensing inquiries and partnership opportunities, please contact our business development team at licensing@stingplatform.com*

---

**Built with ❤️ and 🐝 for the future of enterprise AI**

*STING Platform - Where Security Meets Intelligence*

## Known Issues

### Login Issues After Service Restart
If you experience CSRF errors or login loops after restarting services:
1. Run: python3 scripts/remove_force_password_change.py
2. Clear browser cookies
3. Login again

See CLAUDE.md for detailed troubleshooting.
