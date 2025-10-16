# STING Assistant CE: Secure Trusted Intelligence and Networking Guardian Assistant

<div align="center">
  <img src="../assets/sting-logo copy.png" alt="STING Logo" width="200"/>
  <br/>
  <p><i>Unleashing secure, private, and powerful language models for enterprise applications</i></p>
</div>

---

## 🐝 About STING Assistant CE

STING (Secure Trusted Intelligence and Networking Guardian Assistant) Community Edition is a comprehensive platform designed to provide enterprises with secure, private access to language model capabilities. It combines state-of-the-art LLM technology with robust authentication, privacy controls, and a user-friendly interface.

### Key Features

- 🔒 **Enterprise-grade security** with Ory Kratos authentication
- 🤖 **Multiple LLM support** including Llama 3, Phi-3, and Zephyr
- 🔐 **Passkey authentication** for passwordless security
- 🔍 **Content filtering** to prevent data leakage and toxic outputs
- 📊 **Intelligent routing** based on query content type
- 🔧 **Modular architecture** for easy customization and extension
- 🐳 **Docker-based deployment** for simplified installation and management
- 🌐 **Integrated RESTful API** for easy integration with existing systems

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Node.js 14+
- 8+ GB RAM (16+ GB recommended for optimal performance)
- (Optional) GPU for accelerated model inference

### Installation

1. **Clone the repository**

```bash
git clone https://github.com/yourusername/STING-CE.git
cd STING-CE/STING
```

2. **Run pre-installation setup**

```bash
./pre_install.sh
```

3. **Install STING**

```bash
./install_sting.sh install --debug
```

4. **Set up Hugging Face token** (required for model access)

```bash
./setup_hf_token.sh
```

5. **Verify LLM services' health**

```bash
./check_llm_health.sh
```

### Managing Services

- **Start all services**: `./manage_sting.sh start`
- **Stop services**: `./manage_sting.sh stop`
- **Restart specific service**: `./manage_sting.sh restart [service]`
- **Check logs**: `./manage_sting.sh logs [service]`

## 🏗️ Architecture

STING employs a microservices architecture with the following components:

1. **Frontend** (React): User interface for interacting with the system
2. **Backend API** (Flask): Core business logic and API endpoints
3. **Authentication** (Ory Kratos): Identity, authentication, and user management
4. **LLM Gateway**: Routes requests to appropriate model services
5. **Model Services**: Run specific LLM models (Llama 3, Phi-3, Zephyr)
6. **Database** (PostgreSQL): Stores user data, conversations, and configuration
7. **Vault**: Securely manages secrets and credentials
8. **Knowledge Service**: Honey jar knowledge management with vector search
9. **Bee Assistant**: AI-powered chatbot with context awareness

### Component Diagram

```
┌─────────────┐     ┌────────────┐     ┌───────────────┐
│   Frontend  │────▶│  Backend   │────▶│  LLM Gateway  │
└─────────────┘     └────────────┘     └───────┬───────┘
       │                   │                    │
       │                   │                    ▼
       │                   │           ┌────────────────┐
       │                   │           │  Model Services │
       ▼                   ▼           └────────────────┘
┌─────────────┐     ┌────────────┐
│   Kratos    │     │  Database  │
└─────────────┘     └────────────┘
```

## 🛠️ Development

### Running in Development Mode

1. Start all services in debug mode
   ```bash
   ./manage_sting.sh start -d
   ```

2. Run React development server
   ```bash
   cd frontend
   npm run start
   ```

### Accessing Services

- Frontend: https://localhost:8443
- Backend API: https://localhost:5050
- LLM Gateway: http://localhost:8080
- Kratos Admin: https://localhost:4434
- Kratos Public: https://localhost:4433

## 🔧 Configuration

STING provides comprehensive configuration options through a central configuration file:

- **Main configuration**: `/conf/config.yml`
- **Environment variables**: Generated from configuration to `.env` files
- **📚 Full Guide**: See [Configuration Management Guide](./CONFIGURATION_MANAGEMENT.md)

### Key Configuration Areas

1. **System Configuration**: [Configuration Management Guide](./CONFIGURATION_MANAGEMENT.md)
2. **Honey Jar Access Control**: [Access Control Documentation](./HONEY_JAR_ACCESS_CONTROL.md)
3. **Authentication Setup**: [Kratos Integration Guide](./KRATOS_INTEGRATION_GUIDE.md)
4. **Admin Setup**: [Admin Setup Guide](./ADMIN_SETUP.md)

### Configure LLM Models

Edit `/conf/config.yml` to modify LLM-related settings:

```yaml
llm_service:
  default_model: "llama3"
  models:
    llama3:
      enabled: true
      max_tokens: 1024
      temperature: 0.7
    phi3:
      enabled: true
      max_tokens: 1024
      temperature: 0.7
    zephyr:
      enabled: true
      max_tokens: 1024
      temperature: 0.7
```

### Content Filtering

Adjust content filtering settings in the configuration:

```yaml
llm_service:
  filtering:
    toxicity:
      enabled: true
      threshold: 0.7
    data_leakage:
      enabled: true
```

## 📄 Setting Up Hugging Face Token

For optimal performance with the LLM services, it's recommended to set up a Hugging Face token:

1. Sign up for a free account at [Hugging Face](https://huggingface.co)
2. Create a token at https://huggingface.co/settings/tokens (read access is sufficient)
3. Set up your token using our helper script:

```bash
./setup_hf_token.sh
# Or provide the token directly:
./setup_hf_token.sh YOUR_TOKEN_HERE
```

Benefits of using a Hugging Face token:
- Faster model downloads
- Access to gated models
- Higher rate limits
- No anonymous download restrictions

## 🔄 API Endpoints

STING exposes the following API endpoints:

### Authentication Endpoints

- `POST /api/auth/register`: Register new user
- `POST /api/auth/login`: Login user
- `POST /api/auth/refresh`: Refresh authentication token
- `POST /api/auth/logout`: Logout user

### LLM Endpoints

- `POST /api/llm/generate`: Generate text from LLM
- `GET /api/llm/models`: List available models
- `GET /api/llm/health`: Check LLM services health

## 🔍 Testing Ory Kratos Independently

If you need to iterate on Kratos configuration without running the full STING stack:

1. Install `envsubst` (part of the `gettext` package) on your host.
2. Set the required environment variables:
   ```bash
   export DSN=postgresql://postgres:postgres@db:5432/sting_app
   export KRATOS_PUBLIC_URL=http://localhost:4433
   export KRATOS_ADMIN_URL=http://localhost:4434
   export FRONTEND_URL=https://localhost:8443
   export IDENTITY_DEFAULT_SCHEMA_URL=file:///etc/config/kratos/identity.schema.json
   export LOGIN_UI_URL=https://localhost:8443/login
   export REGISTRATION_UI_URL=https://localhost:8443/register
   export SESSION_SECRET=your-session-secret
   ```
3. Generate a test config from the minimal template:
   ```bash
   envsubst < kratos/minimal.kratos.yml > kratos/test-kratos.yml
   ```
4. Launch the isolated Postgres+Kratos stack:
   ```bash
   docker compose -f docker-compose.kratos-test.yml up --build
   ```
5. Inspect Kratos logs on ports 4433/4434, tweak `kratos/minimal.kratos.yml`, and repeat until Kratos boots without errors.

## 🔒 Security Features

STING implements several security features:

1. **Authentication**: Modern authentication using Ory Kratos
2. **Passkeys**: WebAuthn/FIDO2 support for passwordless authentication
3. **Environment isolation**: All services run in isolated Docker containers
4. **Secure secrets**: Vault integration for secret management
5. **Content filtering**: Toxicity and data leakage detection
6. **HTTPS**: Secure communication between services
7. **Input validation**: Thorough validation on all API endpoints

## 📚 Documentation

### Configuration & Administration
- [**⚙️ Configuration Management Guide**](CONFIGURATION_MANAGEMENT.md) - Complete guide to STING configuration via config.yml
- [**🔐 Honey Jar Access Control**](HONEY_JAR_ACCESS_CONTROL.md) - Configure permissions and access control for knowledge bases
- [**👤 Admin Setup Guide**](ADMIN_SETUP.md) - Setting up admin users and managing permissions
- [**🐝👑 Queen's Hive Domain Setup**](QUEENS_HIVE_DOMAIN.md) - Configure custom domain for consistent development experience

### Core Features
- [Passkey Implementation Guide](PASSKEY_IMPLEMENTATION_GUIDE.md)
- [Passkey Users Guide](PASSKEY_USERS_GUIDE.md)
- [STING Chatbot Integration](STING_CHATBOT_INTEGRATION.md)
- [Email Verification Testing](EMAIL_VERIFICATION_TESTING.md)
- [Kratos Integration Guide](KRATOS_INTEGRATION_GUIDE.md)
- [Kratos Login Guide](KRATOS_LOGIN_GUIDE.md)
- [LLM Health Check](LLM_HEALTH_CHECK.md)

### Performance & Administration
- [**🚀 Performance Administration Guide**](PERFORMANCE_ADMIN_GUIDE.md) - Complete guide for optimizing STING performance
- [**🐝 Cache Buzzer Admin Guide**](CACHE_BUZZER_GUIDE.md) - Fix Docker cache issues and ensure truly fresh container builds
- [**⚡ Performance Quick Reference**](PERFORMANCE_QUICK_REFERENCE.md) - Quick commands and troubleshooting for admins

## 🗺️ Roadmap

- [ ] Advanced role-based access control
- [ ] Multi-tenant isolation
- [ ] Fine-tuning capabilities for custom models
- [ ] Conversation memory and history
- [ ] Document upload and processing
- [ ] Advanced analytics dashboard
- [ ] Plugin architecture for customization

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Llama 3](https://ai.meta.com/llama/) by Meta AI
- [Phi-3](https://www.microsoft.com/en-us/research/blog/phi-3-mini-the-worlds-most-efficient-open-small-language-model/) by Microsoft
- [Zephyr](https://huggingface.co/HuggingFaceH4/zephyr-7b-beta) by HuggingFace
- [Ory Kratos](https://www.ory.sh/kratos/) for authentication
- [FastAPI](https://fastapi.tiangolo.com/) for API development
- [React](https://reactjs.org/) for frontend development
- [Docker](https://www.docker.com/) for containerization

---

<div align="center">
  <p>Built with ❤️ for secure, private AI applications</p>
</div>