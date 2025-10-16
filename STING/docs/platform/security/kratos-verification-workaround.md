# Kratos Verification Workaround

If you're having issues with email verification in the STING application, here are some workarounds:

## Option 1: Temporarily Disable Verification (Development Only)

For development purposes, you can modify the Kratos configuration to skip email verification:

1. Edit `/kratos/main.kratos.yml`:

```yaml
selfservice:
  flows:
    registration:
      after:
        password:
          hooks:
            - hook: session
            # Comment out the verification hook
            # - hook: show_verification_ui
```

2. Restart Kratos:
```bash
./manage_sting.sh restart kratos
```

## Option 2: Manually Mark Identity as Verified

You can use the Kratos admin API to mark an identity as verified:

1. Find your identity ID (either in the database or by using the admin API)
2. Use the following command to mark it as verified:

```bash
curl -k -X PATCH https://localhost:4434/admin/identities/YOUR-IDENTITY-ID \
  -H "Content-Type: application/json" \
  -d '{
    "traits": {"email": "your-email@example.com", "name": {"first": "Your", "last": "Name"}},
    "verifiable_addresses": [{
      "value": "your-email@example.com",
      "verified": true,
      "via": "email"
    }]
  }'
```

## Option 3: Directly Check the Mailpit API

If the Mailpit UI isn't working, you can still check for verification emails through the API:

```bash
# Get the list of emails
curl http://localhost:8025/mail
```

Look for the verification link in the response, and manually copy-paste it into your browser.

## Option 4: Debug the SMTP Connection

You can test the SMTP connection directly:

```bash
# Using netcat
nc -v localhost 1025
# Then type:
HELO localhost
MAIL FROM: <test@example.com>
RCPT TO: <your-email@example.com>
DATA
Subject: Test Email

This is a test email.
.
QUIT
```

Then check http://localhost:8025/mail to see if your test email was received.

## Option 5: Use a Different Email Provider for Testing

You can configure Kratos to use a different email testing service like Mailtrap:

1. Sign up for a free account at Mailtrap.io
2. Get your SMTP credentials
3. Update the Kratos configuration:

```yaml
courier:
  smtp:
    connection_uri: smtps://YOUR_USERNAME:YOUR_PASSWORD@smtp.mailtrap.io:2525/?skip_ssl_verify=true
```

4. Restart Kratos