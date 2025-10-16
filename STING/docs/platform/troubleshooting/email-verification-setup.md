# Email Verification Setup Guide for STING

This guide helps you configure email verification for your STING installation.

## Overview

Email verification is crucial for:
- Confirming user email addresses
- Password recovery flows
- Two-factor authentication
- Important notifications

## MVP Testing Setup (Development)

For MVP testing, you can use **Mailpit** which is already installed:

```yaml
# Current setup in config.yml
kratos:
  courier:
    smtp:
      connection_uri: "smtp://mailpit:1025"
```

This works out of the box! Access emails at: http://localhost:8025

## Production Setup Options

### Option 1: Gmail SMTP (Quick Start)

1. Update `conf/config.yml`:

```yaml
email_service:
  provider: "smtp"
  smtp:
    host: "smtp.gmail.com"
    port: 587
    username: "your-email@gmail.com"
    password: "your-app-password"  # NOT your regular password!
    from_address: "noreply@yourdomain.com"

kratos:
  courier:
    smtp:
      connection_uri: "smtp://your-email@gmail.com:your-app-password@smtp.gmail.com:587"
```

2. Enable 2FA on your Gmail account
3. Generate an App Password: https://myaccount.google.com/apppasswords
4. Use the app password in the config

### Option 2: SendGrid (Recommended for Production)

1. Sign up for SendGrid: https://sendgrid.com
2. Create an API key
3. Update `conf/config.yml`:

```yaml
email_service:
  provider: "sendgrid"
  sendgrid:
    api_key: "${SENDGRID_API_KEY}"
    from_address: "noreply@yourdomain.com"
    from_name: "STING Platform"

kratos:
  courier:
    smtp:
      connection_uri: "smtp://apikey:${SENDGRID_API_KEY}@smtp.sendgrid.net:587"
```

### Option 3: AWS SES (Enterprise)

1. Set up AWS SES in your region
2. Verify your domain
3. Update `conf/config.yml`:

```yaml
email_service:
  provider: "aws_ses"
  aws_ses:
    region: "us-east-1"
    access_key_id: "${AWS_ACCESS_KEY_ID}"
    secret_access_key: "${AWS_SECRET_ACCESS_KEY}"
    from_address: "noreply@yourdomain.com"

kratos:
  courier:
    smtp:
      connection_uri: "smtp://${AWS_SMTP_USERNAME}:${AWS_SMTP_PASSWORD}@email-smtp.us-east-1.amazonaws.com:587"
```

## Enabling Email Verification in Kratos

Add to your Kratos configuration:

```yaml
kratos:
  selfservice:
    flows:
      verification:
        enabled: true
        ui_url: "https://localhost:8443/verification"
        lifespan: "1h"
        after:
          default_browser_return_url: "https://localhost:8443/dashboard"
      
      recovery:
        enabled: true
        ui_url: "https://localhost:8443/recovery"
        lifespan: "1h"
    
    methods:
      link:
        enabled: true
      code:
        enabled: true
```

## Environment Variables

Create `.env` file or update existing:

```bash
# For Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com

# For SendGrid
SENDGRID_API_KEY=SG.xxxxxxxxxxxxx

# For AWS SES
AWS_ACCESS_KEY_ID=AKIAXXXXXXXXX
AWS_SECRET_ACCESS_KEY=xxxxxxxxxx
AWS_SMTP_USERNAME=AKIAXXXXXXXXX
AWS_SMTP_PASSWORD=xxxxxxxxxx
```

## Testing Email Verification

1. **Development (Mailpit)**:
   ```bash
   # Check Mailpit UI
   open http://localhost:8025
   
   # API check
   curl http://localhost:8025/api/v1/messages | jq '.'
   ```

2. **Production Testing**:
   ```bash
   # Run auth test suite
   ./scripts/troubleshooting/test_auth_suite.sh
   
   # Check Kratos logs
   docker logs sting-ce-kratos --tail 50 | grep -i email
   ```

## Email Templates

Kratos uses default templates. To customize:

1. Create template directory:
   ```bash
   mkdir -p conf/kratos/courier/templates
   ```

2. Add custom templates:
   - `verification.valid.email.body.gotmpl`
   - `verification.valid.email.subject.gotmpl`
   - `recovery.valid.email.body.gotmpl`
   - `recovery.valid.email.subject.gotmpl`

3. Mount in docker-compose:
   ```yaml
   kratos:
     volumes:
       - ./conf/kratos/courier:/etc/config/courier:ro
   ```

## Troubleshooting

### No Emails Received

1. Check Kratos logs:
   ```bash
   docker logs sting-ce-kratos | grep -i courier
   ```

2. Verify SMTP connection:
   ```bash
   docker exec -it sting-ce-kratos sh
   telnet smtp.gmail.com 587
   ```

3. Check email queue:
   ```bash
   docker exec sting-ce-db psql -U postgres -d kratos -c "SELECT * FROM courier_messages ORDER BY created_at DESC LIMIT 5;"
   ```

### Gmail Specific Issues

- Enable "Less secure app access" (not recommended)
- Use App Passwords (recommended)
- Check if 2FA is enabled
- Verify SMTP settings in Google Account

### Domain Requirements

For production:
1. **SPF Record**: `v=spf1 include:_spf.google.com ~all`
2. **DKIM**: Set up via your email provider
3. **DMARC**: `v=DMARC1; p=none; rua=mailto:dmarc@yourdomain.com`

## Quick Start Commands

```bash
# Regenerate Kratos config with email settings
cd conf && python3 config_loader.py config.yml --mode production

# Restart Kratos to apply changes
docker-compose restart kratos

# Test email sending
./scripts/troubleshooting/test_auth_suite.sh

# Monitor email logs
docker logs -f sting-ce-kratos | grep -i "courier\|email"
```

## Next Steps

1. Choose your email provider based on scale:
   - Development: Keep Mailpit
   - Small scale: Gmail SMTP
   - Medium scale: SendGrid
   - Enterprise: AWS SES

2. Configure environment variables
3. Update `conf/config.yml`
4. Restart services
5. Test registration flow

For MVP testing, **you're already set up** with Mailpit!