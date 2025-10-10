# Secure Kratos Configuration with HTTPS

## The Issue

There's a mismatch in protocol configuration:
- Kratos is configured to use HTTP in its `base_url` settings
- The frontend expects Kratos to be available via HTTPS
- STING generates self-signed certificates by default

## Solution: Configure Kratos with HTTPS

### Option 1: Use HTTPS Directly in Kratos

Update the Kratos configuration to use HTTPS with the self-signed certificates:

1. Modify the `main.kratos.yml` file:

```yaml
serve:
  public:
    base_url: https://localhost:4433
    tls:
      cert:
        path: /etc/certs/server.crt
      key:
        path: /etc/certs/server.key
    cors:
      enabled: true
      allowed_origins:
        - https://localhost:8443
      # Other CORS settings...
      
  admin:
    base_url: https://localhost:4434
    tls:
      cert:
        path: /etc/certs/server.crt
      key:
        path: /etc/certs/server.key
```

2. Mount certificates in `docker-compose.yml`:

```yaml
kratos:
  image: oryd/kratos:latest
  # Other settings...
  volumes:
    # Existing volumes...
    - ./certs/server.crt:/etc/certs/server.crt:ro
    - ./certs/server.key:/etc/certs/server.key:ro
```

### Option 2: Configure a Reverse Proxy (Recommended for Production)

Use Nginx or another reverse proxy to handle SSL termination:

1. Keep Kratos configuration with HTTP internally
2. Configure Nginx to use HTTPS and proxy requests to Kratos
3. Update the frontend to connect to the secure Nginx endpoint

Example Nginx configuration:

```nginx
server {
    listen 443 ssl;
    server_name localhost;

    ssl_certificate /etc/nginx/ssl/server.crt;
    ssl_certificate_key /etc/nginx/ssl/server.key;

    location /kratos/ {
        proxy_pass http://kratos:4433/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Development Environment Testing

For testing in development with self-signed certificates:

1. Make sure the browser allows self-signed certificates:
   - Navigate directly to https://localhost:4433 and accept the certificate warning
   - Use Chrome flag: `--ignore-certificate-errors` for testing

2. Update frontend development code to handle certificate validation:
   - In API clients, add proper error handling for certificate issues
   - For development only, use a configuration option to ignore certificate errors

## Checking Current Status

To verify your current setup:

```bash
# Check if Kratos has TLS configured
docker exec kratos-kratos-1 kratos version

# Verify connectivity
curl -k https://localhost:4433/health/ready
```

## Security Reminder

Always use HTTPS for authentication services, even in development. The small overhead in configuration is worth the security benefits and avoids exposing sensitive credentials.