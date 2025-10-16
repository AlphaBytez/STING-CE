# Security Policy

## 🔒 Reporting Security Vulnerabilities

Security is our top priority at **AlphaBytez**. We take all security reports seriously and appreciate responsible disclosure.

### Reporting Process

**DO NOT** create public GitHub issues for security vulnerabilities.

Instead, please email security reports to:

**security@alphabytez.dev**

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if you have one)

### What to Expect

1. **Acknowledgment**: Within 48 hours
2. **Initial Assessment**: Within 1 week
3. **Status Updates**: Every 2 weeks
4. **Resolution**: Varies by severity

### Disclosure Timeline

- We aim to resolve critical issues within 30 days
- We will coordinate public disclosure with you
- You will be credited for the discovery (if desired)

## 🛡️ Supported Versions

| Version | Support Status | Security Updates |
| ------- | -------------- | ---------------- |
| 1.x     | ✅ Active      | Yes              |
| < 1.0   | ❌ EOL         | No               |

We strongly recommend always running the latest version.

## 🔐 Security Features

STING-CE includes enterprise-grade security features:

### Authentication & Authorization
- **Passwordless Authentication**: WebAuthn/Passkeys and Magic Links
- **Multi-Factor Authentication**: TOTP, SMS, and biometric options
- **Session Management**: AAL2 (Two-factor) session controls
- **OAuth2/OIDC**: Standard protocol support via Ory Kratos

### Data Protection
- **Vault Integration**: HashiCorp Vault for secrets management
- **PII Protection**: Automatic serialization for sensitive data
- **Encrypted Storage**: All sensitive data encrypted at rest
- **Secure Communication**: TLS/HTTPS enforced

### Security Monitoring
- **Audit Logging**: Comprehensive security event tracking
- **Failed Login Detection**: Rate limiting and blocking
- **Session Monitoring**: Suspicious activity detection
- **Container Security**: Isolated Docker services

### Infrastructure Security
- **Zero-Trust Architecture**: All services isolated and authenticated
- **Network Segmentation**: Docker networks for service isolation
- **Secret Management**: No hardcoded credentials
- **Regular Updates**: Security patches applied promptly

## 🚨 Security Best Practices

### Production Deployment

#### 1. Use HTTPS Everywhere
```yaml
system:
  domain: your-domain.com
  protocol: https  # Always use HTTPS in production
```

#### 2. Enable Multi-Factor Authentication
- Require MFA for all admin accounts
- Enforce MFA for privileged operations
- Use hardware keys for critical accounts

#### 3. Secure Email Configuration
```yaml
email:
  mode: production
  production:
    provider: smtp
    # Use TLS/SSL
    port: 587  # or 465 for SSL
    # Never commit credentials
    username: ${EMAIL_USERNAME}
    password: ${EMAIL_PASSWORD}
```

#### 4. Environment Variables for Secrets
```bash
# NEVER commit these to git
export DATABASE_PASSWORD="strong-password"
export VAULT_TOKEN="vault-token"
export OPENAI_API_KEY="your-api-key"
```

#### 5. Regular Security Updates
```bash
# Update STING-CE regularly
git pull origin main
./manage_sting.sh restart

# Update Docker images
docker compose pull
docker compose up -d
```

#### 6. Monitor Audit Logs
```bash
# Check authentication logs
docker compose logs kratos | grep -i "error\|fail"

# Check API logs
docker compose logs api | grep -i "unauthorized\|forbidden"

# Check Vault logs
docker compose logs vault | grep -i "denied\|error"
```

#### 7. Firewall Configuration
```bash
# Only expose necessary ports
# Production: 443 (HTTPS)
# Development: 8443 (HTTPS), 8025 (Mailpit)

sudo ufw allow 443/tcp
sudo ufw enable
```

#### 8. Database Security
```yaml
database:
  # Use strong passwords
  password: ${DB_PASSWORD}  # From environment
  # Restrict connections
  host: localhost  # Not exposed externally
```

## 🔍 Security Checklist

Before going to production:

### Configuration
- [ ] HTTPS enabled and working
- [ ] Email TLS/SSL configured
- [ ] Strong passwords for all services
- [ ] Environment variables used for secrets
- [ ] No hardcoded credentials in code

### Authentication
- [ ] Admin accounts use MFA
- [ ] Passwordless auth tested and working
- [ ] Session timeout configured
- [ ] Failed login rate limiting enabled

### Infrastructure
- [ ] Firewall configured (only necessary ports open)
- [ ] Docker containers use non-root users
- [ ] Vault unsealed and working
- [ ] Database not exposed externally
- [ ] Redis secured with password

### Monitoring
- [ ] Audit logging enabled
- [ ] Log retention configured
- [ ] Security alerts set up
- [ ] Backup strategy in place

### Compliance
- [ ] Privacy policy updated
- [ ] Terms of service in place
- [ ] Data retention policy defined
- [ ] GDPR/CCPA compliance reviewed (if applicable)

## 🐛 Known Security Considerations

### Development Mode

**Mailpit Email Catcher**: In development mode, emails are caught by Mailpit (http://localhost:8025). This is **NOT secure** for production:
- All emails visible in web UI
- No authentication required
- Use only in development

Production should use a real SMTP provider with TLS.

### Docker Host Access

Some services use `host.docker.internal` to access services on the host machine (e.g., Ollama LLM). Ensure:
- Host firewall rules are strict
- Only necessary services exposed
- Network segmentation in place

## 📚 Security Resources

- **OWASP Top 10**: https://owasp.org/www-project-top-ten/
- **Docker Security**: https://docs.docker.com/engine/security/
- **Ory Kratos Security**: https://www.ory.sh/docs/kratos/security
- **Vault Security**: https://www.vaultproject.io/docs/internals/security

## 🏢 Contact

For security inquiries or questions:

- **Security Issues**: security@alphabytez.dev
- **General Contact**: olliec@alphabytez.dev
- **GitHub Issues**: https://github.com/alphabytez/sting-ce/issues (non-security only)

## 📜 Responsible Disclosure

We follow responsible disclosure practices:

1. **Private Reporting**: Report privately to security@alphabytez.dev
2. **Assessment Period**: Allow time for fix development
3. **Coordinated Disclosure**: Coordinate public disclosure
4. **Credit**: Security researchers credited (if desired)

We appreciate the security community's help in keeping STING-CE secure!

---

**Security is a continuous process. Stay vigilant, stay updated, stay secure.**

Developed by [AlphaBytez](https://github.com/alphabytez)
