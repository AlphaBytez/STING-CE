# MailSlurper Configuration

This directory contains configuration for the MailSlurper email testing service.

## Accessing the Web UI

You can access the MailSlurper web UI at:

- http://localhost:4436/

## API Endpoint

The MailSlurper API is available at:

- http://localhost:4437/mail

## Sending Test Emails

You can send test emails to MailSlurper using SMTP port 1025:

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Create message
msg = MIMEMultipart()
msg['From'] = 'test@example.com'
msg['To'] = 'recipient@example.com'
msg['Subject'] = 'Test Email'

# Add body
body = 'This is a test email sent to MailSlurper'
msg.attach(MIMEText(body, 'plain'))

# Send the message
server = smtplib.SMTP('localhost', 1025)
text = msg.as_string()
server.sendmail('test@example.com', 'recipient@example.com', text)
server.quit()
```

Or using command line:

```bash
echo "Subject: Test Email" | nc localhost 1025
```

## Troubleshooting

If you encounter errors in the web UI:

1. Make sure you're accessing MailSlurper at http://localhost:4436/ directly
2. Verify that ports 4436 and 4437 are open and accessible
3. If API calls fail, check that the service is running with `docker ps | grep mailslurper`
4. Try restarting the service with `docker compose -p sting-ce restart mailslurper`