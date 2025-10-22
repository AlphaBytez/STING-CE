# Email Testing Services for STING Development

## Current Setup: Mailpit
- Connection: `smtps://test:test@mailpit:1025/?skip_ssl_verify=true`
- Limitations: Basic functionality, no SMS support

## Alternative Email Testing Services

### 1. **MailHog** (Recommended for Development)
- **Pros**: 
  - Easy Docker setup
  - Web UI for viewing emails
  - API for automated testing
  - Supports SMTP authentication
  - No external dependencies
- **Docker Setup**:
  ```yaml
  mailhog:
    image: mailhog/mailhog:latest
    container_name: sting-ce-mailhog
    ports:
      - 1025:1025  # SMTP server
      - 8025:8025  # Web UI
    networks:
      - sting_local
  ```
- **Kratos Config**: `smtp://mailhog:1025`

### 2. **Mailtrap** (Cloud Service)
- **Pros**:
  - Cloud-based, no local setup
  - Team collaboration features
  - Email templates preview
  - Spam score analysis
  - Free tier available (500 emails/month)
- **Cons**: 
  - Requires internet connection
  - API key needed
- **Kratos Config**: `smtps://[username]:[password]@smtp.mailtrap.io:2525`

### 3. **MailCatcher**
- **Pros**:
  - Ruby-based, lightweight
  - Simple web interface
  - Catches all emails sent to it
- **Docker Setup**:
  ```yaml
  mailcatcher:
    image: schickling/mailcatcher:latest
    container_name: sting-ce-mailcatcher
    ports:
      - 1025:1025  # SMTP
      - 1080:1080  # Web UI
    networks:
      - sting_local
  ```

### 4. **Inbucket** (Modern Alternative)
- **Pros**:
  - Written in Go, very fast
  - REST API and Web UI
  - Supports email retention policies
  - POP3 support
- **Docker Setup**:
  ```yaml
  inbucket:
    image: inbucket/inbucket:latest
    container_name: sting-ce-inbucket
    ports:
      - 2500:2500  # SMTP
      - 9000:9000  # Web UI
      - 1100:1100  # POP3
    networks:
      - sting_local
  ```

### 5. **smtp4dev** (Windows-friendly)
- **Pros**:
  - .NET Core based
  - Modern web UI
  - IMAP support
  - Email forwarding rules
- **Docker Setup**:
  ```yaml
  smtp4dev:
    image: rnwood/smtp4dev:latest
    container_name: sting-ce-smtp4dev
    ports:
      - 5000:80    # Web UI
      - 25:25      # SMTP
      - 143:143    # IMAP
    networks:
      - sting_local
  ```

## SMS Testing Services

### 1. **Twilio Test Credentials** (Recommended)
- **Pros**:
  - Free test numbers
  - No charges for test messages
  - Realistic API experience
- **Setup**:
  - Use test credentials from Twilio console
  - Test phone numbers that always succeed/fail
  - Magic numbers for testing different scenarios

### 2. **TextMagic Sandbox**
- **Pros**:
  - API sandbox environment
  - Free testing
  - Good documentation

### 3. **Mock SMS Service** (Local)
- **Custom Implementation**:
  ```python
  # Simple Flask app to mock SMS sending
  @app.route('/api/sms', methods=['POST'])
  def send_sms():
      data = request.json
      # Log SMS to file/database
      # Return success response
      return jsonify({"status": "sent", "id": str(uuid4())})
  ```

## Recommended Setup for STING

For comprehensive testing with both email and SMS:

```yaml
# docker-compose.override.yml
services:
  # Email testing
  mailhog:
    image: mailhog/mailhog:latest
    container_name: sting-ce-mailhog
    ports:
      - 1025:1025  # SMTP server
      - 8025:8025  # Web UI at http://localhost:8025
    networks:
      - sting_local
    restart: unless-stopped

  # SMS mock service
  sms-mock:
    image: sting/sms-mock:latest
    build:
      context: ./services/sms-mock
      dockerfile: Dockerfile
    container_name: sting-ce-sms-mock
    ports:
      - 8030:8030  # API and Web UI
    environment:
      - LOG_LEVEL=debug
    volumes:
      - sms_logs:/app/logs
    networks:
      - sting_local
    restart: unless-stopped

  kratos:
    environment:
      # Override email config
      - COURIER_SMTP_CONNECTION_URI=smtp://mailhog:1025
      # Custom SMS provider config
      - COURIER_SMS_PROVIDER=generic
      - COURIER_SMS_REQUEST_CONFIG_URL=http://sms-mock:8030/api/sms
      - COURIER_SMS_REQUEST_CONFIG_METHOD=POST
      - COURIER_SMS_REQUEST_CONFIG_BODY='{"to": "{{ .To }}", "message": "{{ .Body }}"}'
```

## Implementation Steps

1. **Replace Mailpit with MailHog**:
   - Better UI
   - API for automated testing
   - More reliable

2. **Add SMS Mock Service**:
   - Create simple service to log SMS
   - Integrate with Kratos courier

3. **Update Kratos Config**:
   - Configure email templates
   - Set up SMS templates
   - Test both channels

4. **Create Debug UI**:
   - Add email viewer to debug page
   - Show SMS logs
   - Test sending capabilities