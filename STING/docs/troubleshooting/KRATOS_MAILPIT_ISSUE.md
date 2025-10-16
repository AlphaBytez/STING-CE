# Kratos v1.3.1 STARTTLS Issue with Mailpit

## Problem
Kratos v1.3.1 enforces STARTTLS even when explicitly disabled, causing this error:
```
gomail: MandatoryStartTLS required, but SMTP server does not support STARTTLS
```

## Attempted Solutions
1. ✅ Updated SMTP configuration in kratos.yml
2. ✅ Set environment variables: `SMTP_CONNECTION_URI` and `COURIER_SMTP_DISABLE_STARTTLS`  
3. ✅ Added `?disable_starttls=true` to connection URI
4. ✅ Tried `?skip_ssl_verify=true` parameter
5. ✅ Started courier with `--watch-courier` flag
6. ❌ All attempts still result in STARTTLS enforcement

## Root Cause
This appears to be a known issue in Kratos v1.3.1 where the SMTP client (gomail) enforces STARTTLS regardless of configuration. This is likely a security feature that cannot be disabled.

## Workarounds

### Option 1: Use SMTP Server with TLS
Replace mailpit with an SMTP server that supports STARTTLS:
- Postfix with TLS configured
- MailHog (though you mentioned similar issues)
- smtp4dev with TLS support

### Option 2: Use External SMTP Service
For immediate testing, use a real SMTP service:
```yaml
courier:
  smtp:
    connection_uri: smtp://username:password@smtp.gmail.com:587/
```

### Option 3: Downgrade Kratos
Use an older version of Kratos that respects the disable_starttls flag:
```yaml
image: oryd/kratos:v1.0.0
```

### Option 4: Custom SMTP Relay
Create a simple SMTP relay that accepts non-TLS connections from Kratos and forwards to mailpit:
```python
# Simple SMTP proxy that handles TLS negotiation
```

### Option 5: Use Kratos Cloud
Kratos Cloud handles email delivery automatically without needing local SMTP configuration.

## Current State
- Recovery flow works (creates recovery codes)
- Emails are queued in database
- Courier attempts to send but fails due to STARTTLS
- Mailpit is working correctly (tested with direct SMTP)

## Recommendation
For development, the quickest solution is to:
1. Use a test email service (like Mailtrap or Ethereal)
2. Or set up a local Postfix with TLS enabled
3. Or use Kratos v1.0.0 which has more flexible SMTP handling

For production, use a proper email service provider with TLS support.