# STING Platform Overview

## What is STING?

STING (Secure Trusted Intelligence and Networking Guardian) is a comprehensive, enterprise-ready platform for secure, private LLM deployment with advanced knowledge management capabilities. It combines secure AI deployment with innovative knowledge management, built for enterprises who demand privacy, security, and scalability without compromising on AI capabilities.

## Core Features

Based on the comprehensive documentation in `docs/STING_TECHNICAL_WHITEPAPER.md` and related guides:

### 🍯 Honey Jars (Knowledge Collections)
- **Intelligent knowledge containers** that store, organize, and make documents searchable through AI-powered semantic search
- **Multi-format Support**: Upload PDF, Word, Markdown, JSON, HTML, and text files
- **Vector Embeddings**: Documents converted to AI-understandable formats for semantic search
- **Export Options**: HJX format (STING proprietary), JSON, or TAR archives
- **Role-based Access**: Public, private, team, and restricted permission levels
- See: `docs/features/HONEY_JAR_USER_GUIDE.md` for complete details

### 🤖 Bee Chat (AI Assistant)
- **Context-aware chat** with natural language processing
- **Microsoft Phi-3 Medium (14B)** and other enterprise-grade LLMs
- **Hardware acceleration** via Metal Performance Shaders (macOS) or GPU
- **Dynamic model loading** with intelligent memory management
- **Integration with Honey Jars** for knowledge-enhanced responses
- See: `docs/BEE_IMPLEMENTATION_GUIDE.md` for technical details

### 🛡️ Enterprise Security & Authentication
- **Passwordless authentication** with Ory Kratos
- **WebAuthn/FIDO2 support** for biometric and hardware keys
- **AAL1/AAL2 security levels** for different access requirements
- **PII detection and scrubbing** with compliance profiles (GDPR, HIPAA, CCPA)
- **HashiCorp Vault** for secrets management
- See: `docs/features/PASSWORDLESS_AUTHENTICATION.md` and `docs/security/authentication-requirements.md`

### 🏗️ Advanced Architecture
- **Microservices platform** with Docker Compose orchestration
- **React 18 frontend** with Material-UI and Tailwind CSS
- **Flask/Python backend** with PostgreSQL database separation
- **Vector database** with Chroma for semantic search
- **Redis caching** and session management
- See: `docs/ARCHITECTURE.md` and `docs/architecture/system-architecture.md`

## Getting Started

### 1. Create Your First Honey Jar
1. Navigate to the "Hive Manager" in your dashboard
2. Click "Create New Honey Jar"
3. Choose a descriptive name and category
4. Upload your first documents

### 2. Chat with Your Documents
1. Go to the "Bee Chat" section
2. Select your honey jar from the context bar
3. Ask questions about your documents
4. Get intelligent answers with source citations

### 3. Generate Reports
1. Visit the "Bee Reports" page
2. Choose from available report templates
3. Select your data sources (honey jars)
4. Generate comprehensive reports automatically

## Account Types

### Community Edition (Free)
- Up to 5 honey jars
- 1GB storage per user
- Basic AI features
- Standard support

### Professional Edition
- Unlimited honey jars
- 10GB storage per user
- Advanced AI capabilities
- Priority support
- Custom report templates

### Enterprise Edition
- Unlimited storage
- Advanced security features
- Custom integrations
- Dedicated support team
- On-premises deployment options

## Best Practices

### Document Organization
- Use descriptive names for your honey jars
- Add relevant tags to improve searchability
- Regularly review and update document metadata
- Archive outdated documents to maintain performance

### Security Guidelines
- Enable two-factor authentication (2FA)
- Regularly review user permissions
- Use private honey jars for sensitive documents
- Monitor security audit logs

### AI Chat Optimization
- Ask specific questions for better results
- Reference document names when seeking specific information
- Use follow-up questions to dive deeper into topics
- Provide feedback to improve AI responses

## Support & Documentation

- **User Guide**: Comprehensive documentation for all features
- **API Documentation**: For developers and integrations
- **Community Forum**: Connect with other STING users
- **Support Portal**: Submit tickets and get help

## Contact Information

- **Website**: https://alphabytez.com
- **Support Email**: support@alphabytez.com
- **Community**: GitHub Issues and Discussions
- **Documentation**: Built-in help system and online docs

STING is developed by AlphaBytez, a forward-thinking company specializing in AI-powered security platforms and privacy-preserving technologies.