# Kratos Authentication Service

This directory contains configuration files and setup for Ory Kratos, which provides authentication services including WebAuthn (passkey) support.

## Configuration

Kratos is configured through the following files:
- `identity.schema.json` - Schema defining user identity properties
- `main.kratos.yml` - Main Kratos configuration (used in production)
- `minimal.kratos.yml` - Minimal configuration for testing 

## Standalone Testing

A standalone test configuration is provided to validate Kratos in isolation:

```bash
# Start the test environment
cd kratos
docker compose -f docker-compose.test.yml up
```

This will start PostgreSQL and Kratos containers with a minimal configuration.

## Health Checks

Kratos provides a health check endpoint at:
- `http://localhost:4434/admin/health/ready`

Docker healthchecks use this endpoint to verify service readiness.

## Key Configurations

- Kratos must run database migrations before starting the server
- The DSN environment variable must point to a valid PostgreSQL instance
- Use the `sh -c "kratos migrate sql -e --yes && kratos serve --dev --config /etc/config/kratos/kratos.yml"` command to run migrations then serve
- Ensure admin and public interfaces are properly configured and exposed

## Troubleshooting

If health checks fail:
1. Verify the PostgreSQL container is running
2. Check that migrations ran successfully
3. Confirm the admin endpoint is accessible
4. Review logs with `docker compose logs kratos`

## Integration with STING

Kratos integrates with the main application through:
- Frontend at port 4433 (public API)
- Backend at port 4434 (admin API)
- Shared PostgreSQL database
- Environment configuration from config.yml