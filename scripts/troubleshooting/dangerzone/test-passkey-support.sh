#!/bin/bash
# Script to test WebAuthn/Passkey support in the browser

echo "🔐 Testing WebAuthn/Passkey support..."

# Ensure the test HTML file exists
if [ ! -f "frontend/public/passkey-test.html" ]; then
  echo "📝 Creating WebAuthn test file..."
  
  cat > frontend/public/passkey-test.html << EOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WebAuthn/Passkey Test</title>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
      line-height: 1.6;
      max-width: 800px;
      margin: 0 auto;
      padding: 20px;
      background-color: #1a1a1a;
      color: #fff;
    }
    h1, h2, h3 {
      color: #ffd700;
    }
    .section {
      background-color: #2a2a2a;
      padding: 20px;
      border-radius: 8px;
      margin-bottom: 20px;
    }
    button {
      background-color: #4CAF50;
      color: white;
      border: none;
      padding: 10px 15px;
      margin: 10px 0;
      border-radius: 4px;
      cursor: pointer;
      font-size: 16px;
    }
    button:hover {
      background-color: #45a049;
    }
    pre {
      background-color: #333;
      color: #eee;
      padding: 10px;
      border-radius: 4px;
      overflow-x: auto;
      white-space: pre-wrap;
    }
    .success {
      color: #4CAF50;
    }
    .error {
      color: #f44336;
    }
    .warning {
      color: #ff9800;
    }
    #log {
      height: 200px;
      overflow-y: auto;
      padding: 10px;
      background-color: #333;
      border-radius: 4px;
      margin-top: 10px;
    }
    /* Styles for certificate check */
    #certificate {
      margin-top: 20px;
      padding: 15px;
      background-color: #333;
      border-radius: 8px;
    }
    /* Status indicators */
    .status-indicator {
      display: inline-block;
      width: 10px;
      height: 10px;
      border-radius: 50%;
      margin-right: 8px;
    }
    .status-green {
      background-color: #4CAF50;
    }
    .status-red {
      background-color: #f44336;
    }
    .status-yellow {
      background-color: #ff9800;
    }
  </style>
</head>
<body>
  <h1>WebAuthn/Passkey Support Test</h1>
  
  <div class="section">
    <h2>Environment Check</h2>
    <div id="environment-check">Loading...</div>
  </div>
  
  <div class="section">
    <h2>WebAuthn API Test</h2>
    <button id="test-webauthn">Test WebAuthn Support</button>
    <div id="webauthn-result"></div>
  </div>
  
  <div class="section">
    <h2>Secure Context Check</h2>
    <div id="secure-context"></div>
  </div>
  
  <div class="section">
    <h2>SSL Certificate Check</h2>
    <div id="certificate">
      <p>Chrome/Edge requires that WebAuthn only works on:</p>
      <ul>
        <li>localhost (any port, HTTP or HTTPS)</li>
        <li>HTTPS sites with valid certificates</li>
      </ul>
      <p>Current URL: <span id="current-url"></span></p>
    </div>
  </div>
  
  <div class="section">
    <h2>Debug Log</h2>
    <div id="log"></div>
  </div>
  
  <div class="section">
    <h2>Return to Application</h2>
    <p>
      <a href="/" style="color: #ffd700;">Return to Home</a> | 
      <a href="/debug" style="color: #ffd700;">Go to Debug Page</a>
    </p>
  </div>
  
  <script>
    // Log function
    function log(message, type = 'info') {
      const logElement = document.getElementById('log');
      const entry = document.createElement('div');
      entry.className = type;
      const timestamp = new Date().toLocaleTimeString();
      entry.textContent = \`[\${timestamp}] \${message}\`;
      logElement.appendChild(entry);
      logElement.scrollTop = logElement.scrollHeight;
      console.log(\`[\${type}] \${message}\`);
    }
    
    // Check environment
    function checkEnvironment() {
      const envElement = document.getElementById('environment-check');
      const checks = [];
      
      // Check if running in a secure context
      const isSecureContext = window.isSecureContext;
      checks.push(\`<p><span class="status-indicator \${isSecureContext ? 'status-green' : 'status-red'}"></span> Secure Context: \${isSecureContext ? 'Yes ✅' : 'No ❌'}</p>\`);
      
      // Check if WebAuthn API is available
      const hasWebAuthn = typeof PublicKeyCredential !== 'undefined';
      checks.push(\`<p><span class="status-indicator \${hasWebAuthn ? 'status-green' : 'status-red'}"></span> WebAuthn API: \${hasWebAuthn ? 'Available ✅' : 'Not Available ❌'}</p>\`);
      
      // Check if Credentials API is available
      const hasCredentials = typeof navigator.credentials !== 'undefined';
      checks.push(\`<p><span class="status-indicator \${hasCredentials ? 'status-green' : 'status-red'}"></span> Credentials API: \${hasCredentials ? 'Available ✅' : 'Not Available ❌'}</p>\`);
      
      // Browser information
      checks.push(\`<p>Browser: \${navigator.userAgent}</p>\`);
      
      // Origin information
      const origin = window.location.origin;
      checks.push(\`<p>Origin: \${origin}</p>\`);
      
      // Protocol information
      const isHttps = window.location.protocol === 'https:';
      checks.push(\`<p><span class="status-indicator \${isHttps ? 'status-green' : 'status-yellow'}"></span> Protocol: \${window.location.protocol}</p>\`);
      
      // Render all checks
      envElement.innerHTML = checks.join('');
    }
    
    // Test WebAuthn Support
    async function testWebAuthnSupport() {
      const resultElement = document.getElementById('webauthn-result');
      resultElement.innerHTML = '<p>Testing WebAuthn support...</p>';
      
      try {
        if (typeof PublicKeyCredential === 'undefined') {
          throw new Error('WebAuthn API is not available in this browser');
        }
        
        log('Checking if platform authenticator is available...');
        const available = await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
        
        if (available) {
          resultElement.innerHTML = \`
            <p class="success">✅ Platform authenticator is available</p>
            <p>Your device supports WebAuthn and can use platform authenticators (like Touch ID, Face ID, Windows Hello)</p>
          \`;
          log('Platform authenticator is available! Passkeys should work.', 'success');
        } else {
          resultElement.innerHTML = \`
            <p class="warning">⚠️ Platform authenticator is not available</p>
            <p>Your device may not support biometric authentication, but could still use security keys.</p>
          \`;
          log('Platform authenticator is not available. May need to use security keys instead.', 'warning');
        }
      } catch (error) {
        resultElement.innerHTML = \`
          <p class="error">❌ WebAuthn test failed</p>
          <p>Error: \${error.message}</p>
        \`;
        log(\`WebAuthn test failed: \${error.message}\`, 'error');
      }
    }
    
    // Check secure context
    function checkSecureContext() {
      const secureContextElement = document.getElementById('secure-context');
      
      if (window.isSecureContext) {
        secureContextElement.innerHTML = \`
          <p class="success">✅ This page is running in a secure context</p>
          <p>WebAuthn should work properly as long as the browser supports it.</p>
        \`;
        log('Page is running in a secure context', 'success');
      } else {
        secureContextElement.innerHTML = \`
          <p class="error">❌ This page is NOT running in a secure context</p>
          <p>WebAuthn requires a secure context (HTTPS or localhost). Either:</p>
          <ul>
            <li>Use HTTPS with a valid certificate</li>
            <li>Use localhost (which is considered secure even with HTTP)</li>
          </ul>
        \`;
        log('Page is NOT running in a secure context. WebAuthn will not work!', 'error');
      }
    }
    
    // Show current URL
    function showCurrentUrl() {
      const urlElement = document.getElementById('current-url');
      urlElement.textContent = window.location.href;
      
      // Determine if the URL is compatible with WebAuthn
      const isHttps = window.location.protocol === 'https:';
      const isLocalhost = window.location.hostname === 'localhost';
      
      log(\`URL check: Protocol: \${window.location.protocol}, Hostname: \${window.location.hostname}\`);
      
      if (isLocalhost) {
        log('Running on localhost - WebAuthn should work', 'success');
      } else if (isHttps) {
        log('Running on HTTPS - WebAuthn should work if certificate is valid', 'success');
      } else {
        log('WARNING: Not running on localhost or HTTPS - WebAuthn will not work!', 'error');
      }
    }
    
    // Initialize everything when the page loads
    window.addEventListener('DOMContentLoaded', () => {
      log('Page loaded, running WebAuthn tests...');
      checkEnvironment();
      checkSecureContext();
      showCurrentUrl();
      
      // Add click handler for the test button
      document.getElementById('test-webauthn').addEventListener('click', testWebAuthnSupport);
    });
  </script>
</body>
</html>
EOF
  
  echo "✅ WebAuthn test file created."
else
  echo "✅ WebAuthn test file already exists."
fi

echo "📋 To test passkey support, open:"
echo "https://localhost:3000/passkey-test.html"
echo ""
echo "This test will check if your browser supports WebAuthn/passkeys"
echo "and will help diagnose why passkeys might not be working."