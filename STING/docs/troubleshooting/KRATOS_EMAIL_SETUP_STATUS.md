# Kratos Email Setup Status

## Current State

### ✅ What's Working:
1. **Mailpit service** - Running and accepting emails on port 1025
2. **Email templates** - Properly mounted in Kratos container
3. **Recovery flow** - Successfully creates recovery codes/links
4. **Frontend** - Recovery UI properly implemented
5. **Database** - Courier messages are queued in database

### ⚠️ Known Issue:
**Kratos v1.3.1 enforces STARTTLS** even when disabled in connection string. This causes emails to fail with:
```
gomail: MandatoryStartTLS required, but SMTP server does not support STARTTLS
```

### 📧 Configuration Applied:
```yaml
courier:
  smtp:
    connection_uri: smtp://mailpit:1025/?disable_starttls=true
    from_address: noreply@sting.local
    from_name: "STING Platform"
  template_override_path: /etc/config/kratos/courier-templates/
```

## Temporary Workaround

Until the STARTTLS issue is resolved, you can manually start the courier worker:

### Option 1: Run Courier in Container
```bash
# Start courier worker in Kratos container
docker exec sting-ce-kratos sh -c "kratos courier watch --config /etc/config/kratos/kratos.yml > /tmp/courier.log 2>&1 &"

# Check courier logs
docker exec sting-ce-kratos cat /tmp/courier.log
```

### Option 2: Test Recovery Flow
1. Navigate to https://localhost:8443/recovery
2. Enter email: admin@sting.local
3. Submit form (uses 'code' method)
4. Check database for queued messages:
   ```bash
   docker exec sting-ce-db psql -U postgres -d sting_app -c "SELECT * FROM courier_messages ORDER BY created_at DESC LIMIT 5;"
   ```

### Option 3: Direct SMTP Test
```bash
# Test SMTP directly (bypassing Kratos)
python3 scripts/test_smtp_direct.py
# Then check http://localhost:8026
```

## Permanent Solutions

### 1. Update Docker Compose (Recommended)
Add courier worker as a separate service or update Kratos command:
```yaml
command: sh -c "kratos migrate sql -e --yes && kratos serve all --dev --watch-courier --config /etc/config/kratos/kratos.yml"
```

### 2. Use Different SMTP Server
Some SMTP servers that work better with Kratos:
- MailHog (similar to Mailpit but different TLS handling)
- Local Postfix with TLS properly configured
- Cloud SMTP services (SendGrid, AWS SES)

### 3. Downgrade/Upgrade Kratos
- Check if newer versions fix the STARTTLS enforcement
- Or use older version that respects disable_starttls flag

## Production Configuration

For production, use a proper SMTP service:
```yaml
courier:
  smtp:
    connection_uri: smtps://username:password@smtp.sendgrid.net:465/
    from_address: noreply@yourdomain.com
    from_name: "Your Platform"
```

## Testing Email Flow

### Manual Test Steps:
1. Clear mailpit: `curl -X DELETE http://localhost:8026/api/v1/messages`
2. Trigger recovery: `python3 scripts/test_recovery_form.py`
3. Start courier: `docker exec sting-ce-kratos sh -c "kratos courier watch --config /etc/config/kratos/kratos.yml &"`
4. Check mailpit UI: http://localhost:8026

### What to Expect:
- Recovery flow returns "sent_email" state
- Message queued in courier_messages table
- Courier worker processes queue
- Email appears in Mailpit UI

## Next Steps

1. **For Development**: Use the workaround above or switch to MailHog
2. **For Production**: Configure proper SMTP with TLS support
3. **Long-term**: File issue with Kratos about STARTTLS enforcement or find configuration that works

## Related Files
- `/kratos/kratos.yml` - Main configuration
- `/docker-compose.yml` - Service definitions
- `/scripts/test_recovery_form.py` - Recovery testing
- `/scripts/test_smtp_direct.py` - Direct SMTP test
- `MAILPIT_CONFIGURATION.md` - Detailed mailpit setup