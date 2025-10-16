# Mailpit Email Configuration for STING-CE

## Overview
Mailpit is configured as the development email catcher for STING-CE. It intercepts all emails sent by the application and provides a web UI for viewing them.

## Current Status
- ✅ Mailpit service is running and healthy
- ✅ SMTP server accessible on port 1025
- ✅ Web UI accessible at http://localhost:8026
- ✅ Network connectivity between Kratos and Mailpit confirmed
- ✅ Email configuration added to kratos.yml (from_address, from_name, templates)
- ✅ Recovery methods enabled (link and code)
- ⚠️ Email verification is disabled in Kratos
- ⚠️ Recovery flow returns 404 error - API endpoint appears disabled

## Configuration

### Docker Compose (docker-compose.yml)
```yaml
mailpit:
  container_name: sting-ce-mailpit
  image: axllent/mailpit:latest
  ports:
    - "127.0.0.1:1026:1025"  # SMTP port - localhost only
    - "127.0.0.1:8026:8025"  # Web UI port - localhost only
  environment:
    - MP_SMTP_AUTH_ACCEPT_ANY=1
    - MP_SMTP_AUTH_ALLOW_INSECURE=1
```

### Kratos Configuration (kratos/kratos.yml)
```yaml
courier:
  smtp:
    connection_uri: smtp://mailpit:1025
    from_address: noreply@sting.local
    from_name: "STING Platform"
  template_override_path: /etc/config/kratos/courier-templates/

# Recovery methods added:
methods:
  link:
    enabled: true
    config:
      lifespan: 1h
  
  code:
    enabled: true
    config:
      lifespan: 15m
```

## Why Emails Might Not Be Sending

### 1. API Endpoint Disabled
The recovery API endpoint returns a 404 error with message:
```
"This endpoint was disabled by system administrator"
```

This suggests the recovery flow might be disabled at the API level or there's a configuration issue preventing the recovery submission.

### 2. Email Verification Disabled
Currently in `kratos.yml`:
```yaml
verification:
  enabled: false
```

This means:
- User registration doesn't require email verification
- Recovery might require verified emails to work

### 3. Recovery Flow Requirements
Kratos only sends recovery emails when:
- The email address exists in the system
- The identity is active
- The recovery API endpoint is accessible
- The proper recovery method is configured

### 4. Current Issues & Solutions

#### Enable Email Verification
```yaml
verification:
  enabled: true
  ui_url: https://localhost:8443/verification
  lifespan: 1h
```

#### Test with a Verified Account
1. Ensure admin@sting.local exists and is active
2. Manually set the email as verified in the database
3. Test recovery flow again

## Testing Email Functionality

### 1. Direct SMTP Test
```bash
# Test SMTP connection
docker exec sting-ce-kratos sh -c "nc -zv mailpit 1025"
```

### 2. Check Mailpit UI
- Open: http://localhost:8026
- All intercepted emails appear here
- No authentication required

### 3. Check Kratos Logs
```bash
# Check for email/courier related logs
docker logs sting-ce-kratos 2>&1 | grep -i "courier\|smtp\|email"
```

### 4. Manual Email Test
You can manually trigger an email by:
1. Enabling email verification
2. Creating a new user
3. Checking mailpit for verification email

## Production Configuration

For production, replace the mailpit configuration with real SMTP:

```yaml
courier:
  smtp:
    connection_uri: smtps://username:password@smtp.example.com:465/
    from_address: noreply@yourdomain.com
    from_name: "Your Platform Name"
```

### Environment Variables
Add to your production `.env`:
```bash
SMTP_CONNECTION_URI=smtps://username:password@smtp.example.com:465/
SMTP_FROM_ADDRESS=noreply@yourdomain.com
SMTP_FROM_NAME="Your Platform Name"
```

### Security Considerations
1. Use SMTP over TLS (smtps://) in production
2. Store SMTP credentials in environment variables
3. Use a dedicated email service (SendGrid, AWS SES, etc.)
4. Configure SPF/DKIM/DMARC for deliverability

## Troubleshooting

### No Emails in Mailpit
1. Check if email verification is enabled
2. Verify the email address exists in Kratos
3. Check Kratos logs for courier errors
4. Ensure recovery flow is completing successfully

### Connection Errors
1. Verify mailpit container is running: `docker ps | grep mailpit`
2. Check network connectivity: `docker exec sting-ce-kratos ping mailpit`
3. Verify SMTP port is open: `docker exec sting-ce-kratos nc -zv mailpit 1025`

### Template Issues
1. Verify templates are mounted: `docker exec sting-ce-kratos ls /etc/config/kratos/courier-templates/`
2. Check template syntax in courier-templates directory
3. Look for template parsing errors in Kratos logs

## Next Steps

1. **Enable Email Verification** (if desired):
   - Update kratos.yml to set `verification.enabled: true`
   - Create verification page in frontend
   - Test full email flow

2. **Test Recovery with Existing User**:
   - Ensure user exists with verified email
   - Navigate to /recovery
   - Submit recovery form
   - Check mailpit

3. **Production Planning**:
   - Choose email service provider
   - Configure production SMTP settings
   - Test email deliverability
   - Set up monitoring/alerts for email failures