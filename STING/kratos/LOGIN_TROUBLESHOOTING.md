# Troubleshooting "Failed to load login form" Error

If you're seeing a "Failed to load login form" error in the browser, follow these steps to diagnose and fix the issue.

## 1. Check Kratos Service Status

```bash
# Check if Kratos is running
docker compose ps kratos

# Check Kratos logs for errors
docker compose logs kratos

# Verify Kratos health endpoint
curl http://localhost:4434/admin/health/ready
```

## 2. Check Frontend Configuration

The frontend needs proper configuration to connect to Kratos:

```bash
# Check environment variables in frontend
grep -r "KRATOS" ./frontend/.env*

# Verify browser console for CORS or connection errors
# Open browser dev tools (F12) and check console tab
```

Common frontend issues:
- Incorrect Kratos URL in environment variables
- CORS configuration errors
- Network connectivity between frontend and Kratos

## 3. Inspect Kratos Login Flow

Test the Kratos login flow directly:

```bash
# Initiate a login flow and check the response
curl -s http://localhost:4433/self-service/login/browser | jq .

# Visit the flow URL directly in your browser:
# http://localhost:4433/self-service/login/flows?id=FLOW_ID
# (Replace FLOW_ID with the ID from the curl response)
```

## 4. Check Frontend UI Components

The STING frontend should be properly configured to handle Kratos flows:

1. Examine `frontend/src/components/auth/LoginKratos.jsx` file
2. Verify it's correctly fetching and processing the login flow
3. Check for error handling in the login component

## 5. Common Solutions

### Fix Kratos Configuration

Ensure your Kratos YAML configuration has:

```yaml
serve:
  public:
    base_url: http://localhost:4433
    cors:
      enabled: true
      allowed_origins:
        - http://localhost:8443
        - https://localhost:8443
```

### Restart Services

```bash
# Stop all services
./manage_sting.sh stop

# Start services in the correct order
./manage_sting.sh start
```

### Check Browser Console

Common errors in the browser console:
- CORS errors: Check Kratos CORS configuration
- Network errors: Check Kratos is accessible at expected URL
- JavaScript errors: Check frontend code handling Kratos flows

### Reset Database

If Kratos migrations or database is corrupted:

```bash
# Down all services and volumes
docker compose down -v

# Rebuild and restart
./manage_sting.sh build
./manage_sting.sh start
```

## 6. Advanced Debugging

### Manual Flow Testing

You can manually test the login flow API:

```bash
# 1. Initialize a login flow
FLOW_ID=$(curl -s http://localhost:4433/self-service/login/browser | jq -r '.id')

# 2. Get the flow (as the frontend would)
curl -s http://localhost:4433/self-service/login/flows?id=$FLOW_ID | jq .

# 3. Submit credentials (example)
curl -s -X POST http://localhost:4433/self-service/login?flow=$FLOW_ID \
  -H "Content-Type: application/json" \
  -d '{"method":"password","password":"your-password","password_identifier":"user@example.com"}'
```

### Network Monitoring

Monitor the network requests between frontend and Kratos:

```bash
# Terminal 1: Monitor frontend requests
cd frontend && npm start

# Terminal 2: Watch Kratos logs
docker compose logs -f kratos
```

## 7. Kratos Direct URL Test

Sometimes it helps to test Kratos directly:

```bash
# Create a simple test HTML file
cat > kratos_test.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
  <title>Kratos Login Test</title>
  <script>
    window.onload = async function() {
      try {
        // Start login flow
        const resp = await fetch('http://localhost:4433/self-service/login/browser');
        const flow = await resp.json();
        
        // Display flow data
        document.getElementById('flow-id').textContent = flow.id;
        document.getElementById('flow-data').textContent = JSON.stringify(flow, null, 2);
        
        // Update form action
        document.getElementById('login-form').action = 
          `http://localhost:4433/self-service/login?flow=${flow.id}`;
      } catch (error) {
        document.getElementById('error').textContent = error.toString();
      }
    }
  </script>
</head>
<body>
  <h1>Kratos Login Test</h1>
  <div id="error" style="color: red;"></div>
  <p>Flow ID: <span id="flow-id">Loading...</span></p>
  <form id="login-form" method="POST">
    <input type="hidden" name="method" value="password" />
    <div>
      <label>Email: <input name="password_identifier" type="email" /></label>
    </div>
    <div>
      <label>Password: <input name="password" type="password" /></label>
    </div>
    <button type="submit">Login</button>
  </form>
  <pre id="flow-data"></pre>
</body>
</html>
EOF

# Open the file in your browser
open kratos_test.html
```

This will help identify if the issue is in the Kratos service or in the frontend integration.