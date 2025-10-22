# Testing Email and SMS in STING Development

## Overview

STING now includes comprehensive email and SMS testing capabilities for development:
- **Mailpit** for email testing (modern, cross-platform alternative to mailpit)
- **SMS Mock Service** for SMS/OTP testing

## Quick Start

1. **Start the services**:
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d
   ```

2. **Access the testing UIs**:
   - Email (Mailpit): http://localhost:8025
   - SMS Mock: http://localhost:8030

## Email Testing with Mailpit

### Features
- Catches all emails sent by the application
- Web UI to view emails in real-time
- API for automated testing
- No external dependencies
- **Cross-platform support** (Linux, macOS Intel/ARM64, Windows)
- **Active development** with regular updates
- **Modern UI** with dark mode support

### Viewing Emails
1. Navigate to http://localhost:8025
2. All emails sent by STING will appear here
3. Click on any email to view its contents
4. Use the search feature to find specific emails
5. Mailpit automatically refreshes when new emails arrive

### API Usage
```bash
# Get all messages
curl http://localhost:8025/api/v2/messages

# Get specific message
curl http://localhost:8025/api/v2/messages/{id}

# Delete all messages
curl -X DELETE http://localhost:8025/api/v1/messages
```

## SMS Testing with Mock Service

### Features
- Captures all SMS messages
- Web UI with auto-refresh
- Highlights verification codes
- Simple API for integration

### Viewing SMS Messages
1. Navigate to http://localhost:8030
2. All SMS messages appear with:
   - Recipient phone number
   - Message content with highlighted codes
   - Timestamp
   - Message ID

### API Endpoints
- **Send SMS**: `POST http://localhost:8030/api/sms`
- **Get Messages**: `GET http://localhost:8030/api/messages`
- **Clear Messages**: `POST http://localhost:8030/api/clear`

## Testing OTP Flow

### Email OTP
1. Request login/registration with email
2. Check MailHog at http://localhost:8025
3. Copy the verification code
4. Enter code in the application

### SMS OTP
1. Request login/registration with phone number
2. Check SMS Mock at http://localhost:8030
3. Copy the verification code
4. Enter code in the application

## Testing Scripts

### Test Email OTP
```bash
./kratos/test-passwordless-otp.sh
```

### Manual Testing
```bash
# Initialize login flow
FLOW_ID=$(curl -k -s https://localhost:4433/self-service/login/api | jq -r '.id')

# Request OTP via email
curl -k -X POST https://localhost:4433/self-service/login/flows/$FLOW_ID \
  -H "Content-Type: application/json" \
  -d '{"method": "code", "identifier": "test@example.com"}'

# Check email at http://localhost:8025

# Submit code
curl -k -X POST https://localhost:4433/self-service/login/flows/$FLOW_ID \
  -H "Content-Type: application/json" \
  -d '{"method": "code", "code": "123456"}'
```

## Configuration

### Kratos Configuration
The services are pre-configured in `docker-compose.override.yml`:
- Mailpit SMTP: `smtp://mailpit:1025`
- SMS Mock API: `http://sms-mock:8030/api/sms`

### Custom Templates
Email and SMS templates are located in:
- `kratos/courier-templates/login_code.body.gotmpl`
- `kratos/courier-templates/login_code.body.sms.gotmpl`
- `kratos/courier-templates/registration_code.body.gotmpl`
- `kratos/courier-templates/registration_code.body.sms.gotmpl`

## Troubleshooting

### Emails not appearing in Mailpit
1. Check Kratos logs: `docker logs sting-ce-kratos`
2. Verify SMTP config in Kratos
3. Ensure Mailpit is running: `docker ps | grep mailpit`
4. Check Mailpit logs: `docker logs sting-ce-mailpit`

### SMS not appearing in Mock Service
1. Check SMS Mock logs: `docker logs sting-ce-sms-mock`
2. Verify SMS config in Kratos
3. Test API directly: `curl -X POST http://localhost:8030/api/sms -H "Content-Type: application/json" -d '{"to": "+1234567890", "message": "Test"}'`

### Container connectivity issues
```bash
# Test from Kratos container
docker exec sting-ce-kratos ping mailpit
# For SMS mock on Mac, it uses host.docker.internal
docker exec sting-ce-kratos ping host.docker.internal
```

## Production Considerations

⚠️ **Important**: These services are for development only!

For production, configure real services:
- **Email**: SendGrid, AWS SES, Mailgun, etc.
- **SMS**: Twilio, AWS SNS, MessageBird, etc.

Update Kratos configuration:
```yaml
courier:
  smtp:
    connection_uri: smtps://apikey:SG.xxx@smtp.sendgrid.net:465
  sms:
    # Configure your SMS provider
```