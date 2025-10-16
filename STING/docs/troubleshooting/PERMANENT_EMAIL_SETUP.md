# Permanent Email Setup for STING-CE

## Summary of Changes

We've successfully implemented a flexible email configuration system for STING-CE that supports both development and production environments.

### What Was Done

1. **Updated Configuration System** (`conf/config_loader.py`):
   - Added `_generate_email_env_vars()` method to process email configuration
   - Integrated email configuration with Kratos environment variables
   - Support for both development (Mailpit) and production (external SMTP) modes

2. **Enhanced Configuration Templates** (`conf/config.yml.default` and `.mac`):
   - Added structured email configuration with development/production sections
   - Environment variable support for easy deployment
   - Clear documentation of provider-specific settings

3. **Docker Compose Updates** (`docker-compose.yml`):
   - Made Mailpit conditional using Docker profiles
   - Removed hardcoded SMTP settings from Kratos service
   - Email configuration now loaded from generated env files

4. **Documentation and Tools**:
   - Created comprehensive `EMAIL_CONFIGURATION.md` guide
   - Added `scripts/test_email_config.py` for testing email setup
   - Added `scripts/switch_email_mode.sh` for easy mode switching

### How It Works

#### Development Mode (Default)
- Uses Mailpit as email catcher
- No configuration needed
- Access emails at http://localhost:8026
- Perfect for testing without sending real emails

#### Production Mode
- Connects to external SMTP services
- Supports Gmail, SendGrid, AWS SES, Office 365, etc.
- Configured via environment variables
- Full TLS/STARTTLS support

### Quick Start

1. **Development Mode** (default):
   ```bash
   docker-compose --profile development up -d
   ```

2. **Production Mode**:
   ```bash
   # Set environment variables
   export EMAIL_MODE=production
   export SMTP_HOST=smtp.gmail.com
   export SMTP_PORT=587
   export SMTP_USERNAME=your-email@gmail.com
   export SMTP_PASSWORD=your-app-password
   
   # Start without development profile
   docker-compose up -d
   ```

3. **Switch Modes**:
   ```bash
   ./scripts/switch_email_mode.sh
   ```

4. **Test Configuration**:
   ```bash
   python3 scripts/test_email_config.py
   ```

### Environment Variables

For production email, set these variables:

```bash
EMAIL_MODE=production
SMTP_HOST=your.smtp.host
SMTP_PORT=587
SMTP_USERNAME=your-username
SMTP_PASSWORD=your-password
SMTP_FROM=noreply@yourdomain.com
SMTP_FROM_NAME="Your Platform Name"
SMTP_TLS_ENABLED=true
SMTP_STARTTLS_ENABLED=true
```

### Integration with Kratos

The email configuration automatically integrates with Ory Kratos for:
- Account verification
- Password recovery
- Login notifications
- Account updates

Kratos uses the generated SMTP connection URI based on your configuration.

### Benefits

1. **Flexibility**: Easy switching between development and production
2. **Security**: Credentials stored in environment variables
3. **Simplicity**: Mailpit requires no configuration for development
4. **Compatibility**: Works with all major email providers
5. **Testing**: Built-in test tools to verify configuration

### Next Steps

1. Review `EMAIL_CONFIGURATION.md` for detailed setup instructions
2. Configure your production SMTP settings when ready
3. Use the test script to verify everything works
4. Monitor Kratos logs for any email delivery issues

The email system is now permanently configured and ready for both development and production use!