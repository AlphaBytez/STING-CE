# STING Authentication Testing Guide

This guide provides comprehensive instructions for testing the authentication system in STING, including common troubleshooting steps and curl examples.

## Quick Start

Use the automated test script:
```bash
./test_auth_suite.sh
```

To clean up test users after testing:
```bash
./test_auth_suite.sh --cleanup
```

## Manual Testing with Curl

### 1. Registration Flow

```bash
# Step 1: Create registration flow
FLOW_JSON=$(curl -s -k https://localhost:4433/self-service/registration/api)
FLOW_ID=$(echo $FLOW_JSON | jq -r '.id')
echo "Flow ID: $FLOW_ID"

# Step 2: Submit profile data
curl -s -k -X POST \
  "https://localhost:4433/self-service/registration?flow=$FLOW_ID" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -d "method=profile&traits.email=user@example.com&traits.name.first=John&traits.name.last=Doe"

# Step 3: Complete with password
curl -s -k -X POST \
  "https://localhost:4433/self-service/registration?flow=$FLOW_ID" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -d "method=password&password=SecurePassword123!&traits.email=user@example.com&traits.name.first=John&traits.name.last=Doe"
```

### 2. Login Flow

```bash
# Step 1: Create login flow
FLOW_JSON=$(curl -s -k https://localhost:4433/self-service/login/api)
FLOW_ID=$(echo $FLOW_JSON | jq -r '.id')

# Step 2: Submit credentials
curl -s -k -X POST \
  "https://localhost:4433/self-service/login?flow=$FLOW_ID" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Accept: application/json" \
  -d "method=password&identifier=user@example.com&password=SecurePassword123!"
```

### 3. Session Management

```bash
# Check current session
SESSION_TOKEN="ory_st_xxxxx"  # From login/registration response
curl -s -k \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  https://localhost:4433/sessions/whoami | jq '.'

# Logout
curl -s -k -X DELETE \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  https://localhost:4433/self-service/logout/api
```

## Common Issues and Solutions

### 1. JSON Decoding Errors

**Problem**: "Unable to decode form as JSON"

**Solution**: Use `application/x-www-form-urlencoded` instead of JSON:
```bash
# Wrong
-H "Content-Type: application/json" \
-d '{"method": "password", "password": "test"}'

# Correct
-H "Content-Type: application/x-www-form-urlencoded" \
-d "method=password&password=test"
```

### 2. CSRF Token Issues

**Problem**: "CSRF token missing or invalid"

**Solution**: Always use API endpoints (`/api` suffix) for curl testing:
```bash
# Browser endpoint (requires CSRF)
https://localhost:4433/self-service/registration

# API endpoint (no CSRF required)
https://localhost:4433/self-service/registration/api
```

### 3. Flow Expired

**Problem**: "Flow expired" errors

**Solution**: Flows expire after 1 hour by default. Always create a fresh flow:
```bash
# Don't reuse old flow IDs
# Always get a new flow before submitting
FLOW_ID=$(curl -s -k https://localhost:4433/self-service/registration/api | jq -r '.id')
```

### 4. Certificate Errors

**Problem**: SSL certificate verification failed

**Solution**: Use `-k` flag with curl to skip certificate verification:
```bash
curl -k https://localhost:4433/...
```

## Testing Different Authentication Methods

### Password Authentication
- Default method
- Requires strong password (min 8 chars, mix of upper/lower/numbers/symbols)

### WebAuthn/Passkeys (Future)
- Not yet implemented in current configuration
- Will require HTTPS and proper domain setup

### Email/SMS OTP (Future)
- Code method needs to be enabled in Kratos config
- Requires SMTP configuration

## Email Testing with Mailpit

Check emails sent by Kratos:
```bash
# List all messages
curl -s http://localhost:8025/api/v1/messages | jq '.messages[] | {from, to, subject}'

# Get specific message
MESSAGE_ID=$(curl -s http://localhost:8025/api/v1/messages | jq -r '.messages[0].ID')
curl -s http://localhost:8025/api/v1/messages/$MESSAGE_ID | jq '.'

# Clear all messages
curl -s -X DELETE http://localhost:8025/api/v1/messages
```

## Debugging Authentication Issues

### 1. Check Kratos Logs
```bash
docker logs sting-ce-kratos --tail 50
```

### 2. Verify Identity Schema
```bash
# Check current schema
curl -k -s https://localhost:4434/admin/schemas | jq '.'

# Validate identity schema
docker exec sting-ce-kratos kratos validate identity-schema /etc/config/kratos/identity.schema.json
```

### 3. List Identities (Admin)
```bash
# List all identities
curl -k -s https://localhost:4434/admin/identities | jq '.'

# Get specific identity
IDENTITY_ID="xxxx-xxxx-xxxx-xxxx"
curl -k -s https://localhost:4434/admin/identities/$IDENTITY_ID | jq '.'
```

## Integration Testing

### Testing with Frontend
1. Open https://localhost:8443
2. Click "Sign Up" or "Login"
3. Monitor network tab for API calls
4. Check console for errors

### Testing with Backend API
```bash
# Test protected endpoint
SESSION_TOKEN="ory_st_xxxxx"
curl -k -s \
  -H "Authorization: Bearer $SESSION_TOKEN" \
  https://localhost:5050/api/auth/me | jq '.'
```

## Performance Testing

Basic load test for registration:
```bash
# Create 10 test users
for i in {1..10}; do
  echo "Creating user $i..."
  ./test_auth_suite.sh &
  sleep 1
done
wait
```

## Troubleshooting Checklist

- [ ] All services running? (`docker ps`)
- [ ] Kratos config valid? (`docker exec sting-ce-kratos kratos validate`)
- [ ] Database accessible? (`docker exec sting-ce-db pg_isready`)
- [ ] Mailpit receiving emails? (http://localhost:8025)
- [ ] Frontend can reach Kratos? (Check browser console)
- [ ] Correct flow type? (registration vs login)
- [ ] Fresh flow ID? (not expired)
- [ ] Correct content type? (form-encoded for API)
- [ ] SSL issues? (use -k flag)

## Additional Resources

- [Ory Kratos Documentation](https://www.ory.sh/docs/kratos)
- [STING Auth Architecture](./architecture/auth.md)
- [Kratos Configuration Reference](https://www.ory.sh/docs/kratos/reference/configuration)