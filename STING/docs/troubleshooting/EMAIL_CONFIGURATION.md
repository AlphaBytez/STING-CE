# Email Configuration Guide for STING-CE

This guide explains how to configure email services in STING-CE for both development and production environments.

## Overview

STING-CE supports flexible email configuration with two modes:
- **Development Mode** (default): Uses Mailpit email catcher for testing
- **Production Mode**: Connects to external SMTP services (Gmail, SendGrid, AWS SES, etc.)

## Configuration Structure

Email settings are configured in `conf/config.yml` under the `email_service` section:

```yaml
email_service:
  # Email mode: development or production
  mode: "${EMAIL_MODE:-development}"
  
  # Development settings (uses mailpit email catcher)
  development:
    provider: "mailpit"
    host: "mailpit"
    port: 1025
    tls_enabled: false
    
  # Production settings (external SMTP/email service)
  production:
    provider: "${EMAIL_PROVIDER:-smtp}"
    smtp:
      host: "${SMTP_HOST}"
      port: "${SMTP_PORT:-587}"
      username: "${SMTP_USERNAME}"
      password: "${SMTP_PASSWORD}"
      from_address: "${SMTP_FROM:-noreply@yourdomain.com}"
      from_name: "${SMTP_FROM_NAME:-STING Platform}"
      tls_enabled: "${SMTP_TLS_ENABLED:-true}"
      starttls_enabled: "${SMTP_STARTTLS_ENABLED:-true}"
```

## Development Mode (Default)

In development mode, STING-CE uses Mailpit to catch all outgoing emails. This is perfect for testing email functionality without sending real emails.

### Accessing Mailpit

When running in development mode:
- SMTP Server: `localhost:1026`
- Web UI: http://localhost:8026

To view captured emails, open the Mailpit web interface in your browser.

### Running with Mailpit

```bash
# Start STING with development profile (includes Mailpit)
docker-compose --profile development up -d

# Or set EMAIL_MODE explicitly
EMAIL_MODE=development docker-compose --profile development up -d
```

## Production Mode

To send real emails in production, configure your SMTP settings.

### Environment Variables

Set these environment variables or add them to a `.env` file:

```bash
# Set email mode to production
EMAIL_MODE=production

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com
SMTP_FROM_NAME="Your Platform Name"
SMTP_TLS_ENABLED=true
SMTP_STARTTLS_ENABLED=true
```

### Provider-Specific Settings

#### Gmail
1. Enable 2-factor authentication
2. Generate an app-specific password
3. Use the app password as `SMTP_PASSWORD`

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-specific-password
```

#### SendGrid
1. Create a SendGrid API key
2. Use the API key as the password

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USERNAME=apikey
SMTP_PASSWORD=your-sendgrid-api-key
```

#### AWS SES
1. Verify your domain/email in AWS SES
2. Create SMTP credentials in AWS SES console

```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
```

#### Office 365
```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@yourdomain.com
SMTP_PASSWORD=your-password
```

### Running in Production

```bash
# Start STING without development profile (excludes Mailpit)
EMAIL_MODE=production docker-compose up -d

# Or with environment file
docker-compose --env-file production.env up -d
```

## Switching Between Modes

### From Development to Production
1. Set `EMAIL_MODE=production` in your environment
2. Configure SMTP settings (host, port, credentials)
3. Restart services: `msting restart`

### From Production to Development
1. Set `EMAIL_MODE=development` or remove it (defaults to development)
2. Restart services with development profile: `docker-compose --profile development up -d`

## Testing Email Configuration

### Test in Development Mode
1. Access Mailpit UI at http://localhost:8026
2. Trigger an email action (password reset, registration, etc.)
3. Check Mailpit for the captured email

### Test in Production Mode
1. Configure your SMTP settings
2. Use the test script:
   ```bash
   python3 scripts/test_email_config.py
   ```
3. Check your inbox for the test email

## Troubleshooting

### Common Issues

#### Emails not appearing in Mailpit
- Ensure Mailpit is running: `docker ps | grep mailpit`
- Check Kratos logs: `docker logs sting-ce-kratos`
- Verify EMAIL_MODE is set to "development"

#### SMTP Authentication Failed
- Double-check credentials
- For Gmail: Use app-specific password, not regular password
- For SendGrid: Use "apikey" as username
- Ensure credentials are properly escaped in environment variables

#### Connection Timeout
- Check firewall rules for SMTP ports
- Verify SMTP host and port
- Some providers require specific ports:
  - Port 587: STARTTLS (most common)
  - Port 465: SSL/TLS
  - Port 25: Plain (often blocked)

#### TLS/SSL Errors
- For development: TLS is disabled for Mailpit
- For production: Ensure TLS settings match provider requirements
- Try toggling `SMTP_STARTTLS_ENABLED` based on your provider

### Debug Commands

```bash
# Check current email configuration
docker exec sting-ce-kratos env | grep -E "(EMAIL|SMTP|COURIER)"

# View Kratos logs
docker logs sting-ce-kratos --tail 50 -f

# Test SMTP connection
docker exec sting-ce-kratos nc -zv $SMTP_HOST $SMTP_PORT
```

## Security Best Practices

1. **Never commit credentials**: Use environment variables or `.env` files (git-ignored)
2. **Use app-specific passwords**: Don't use your main account password
3. **Enable TLS/SSL**: Always use encrypted connections in production
4. **Verify sender domain**: Use a from address that matches your verified domain
5. **Monitor usage**: Set up alerts for unusual email activity

## Integration with Ory Kratos

The email configuration automatically integrates with Ory Kratos for:
- Account verification emails
- Password recovery emails
- Login notifications
- Account update confirmations

Kratos uses the SMTP settings configured through this system, with the connection URI automatically generated based on your settings.

## Advanced Configuration

### Custom Email Providers

To add support for custom email providers, extend the configuration in `config_loader.py`:

1. Add provider-specific logic in `_generate_email_env_vars()`
2. Generate appropriate connection URI for Kratos
3. Document provider-specific requirements

### Email Templates

Email templates are managed by Kratos and can be customized in the Kratos configuration files.

## Summary

- **Development**: Automatic with Mailpit, no configuration needed
- **Production**: Set EMAIL_MODE=production and configure SMTP settings
- **Switching**: Change EMAIL_MODE and restart services
- **Testing**: Use Mailpit UI in dev, test scripts in production
- **Security**: Use environment variables, app passwords, and TLS