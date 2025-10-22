"""
SMS Mock Service for Development
Captures and displays SMS messages sent by Kratos for testing
"""

from flask import Flask, request, jsonify, render_template_string
from datetime import datetime
import uuid
import json
import os

app = Flask(__name__)

# Store messages in memory (for development only)
messages = []

# HTML template for viewing messages
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>SMS Mock Service - STING</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background-color: #1a1a1a;
            color: #e0e0e0;
            margin: 0;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        h1 {
            color: #fbbf24;
            margin-bottom: 30px;
        }
        .stats {
            background-color: #2d2d2d;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
        }
        .message {
            background-color: #2d2d2d;
            border: 1px solid #404040;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 15px;
        }
        .message-header {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            color: #9ca3af;
        }
        .phone {
            color: #60a5fa;
            font-weight: 600;
        }
        .timestamp {
            color: #6b7280;
            font-size: 0.875rem;
        }
        .message-body {
            background-color: #1a1a1a;
            padding: 15px;
            border-radius: 4px;
            white-space: pre-wrap;
            font-family: monospace;
        }
        .code {
            color: #fbbf24;
            font-weight: bold;
            font-size: 1.2em;
        }
        .clear-btn {
            background-color: #ef4444;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        .clear-btn:hover {
            background-color: #dc2626;
        }
        .refresh-btn {
            background-color: #3b82f6;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
            margin-left: 10px;
        }
        .refresh-btn:hover {
            background-color: #2563eb;
        }
        .api-info {
            background-color: #1e293b;
            border: 1px solid #334155;
            padding: 15px;
            border-radius: 4px;
            margin-top: 30px;
        }
        .api-info code {
            background-color: #0f172a;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: monospace;
        }
    </style>
    <script>
        function clearMessages() {
            if (confirm('Clear all messages?')) {
                fetch('/api/clear', { method: 'POST' })
                    .then(() => location.reload());
            }
        }
        
        // Auto-refresh every 5 seconds
        setInterval(() => {
            fetch('/api/messages')
                .then(r => r.json())
                .then(data => {
                    if (data.length !== {{ messages|length }}) {
                        location.reload();
                    }
                });
        }, 5000);
    </script>
</head>
<body>
    <div class="container">
        <h1>🔔 SMS Mock Service</h1>
        
        <div class="stats">
            <strong>Total Messages:</strong> {{ messages|length }}<br>
            <strong>Status:</strong> <span style="color: #10b981;">● Active</span>
        </div>
        
        <div style="margin-bottom: 20px;">
            <button onclick="clearMessages()" class="clear-btn">Clear All</button>
            <button onclick="location.reload()" class="refresh-btn">Refresh</button>
        </div>
        
        {% if messages %}
            {% for msg in messages|reverse %}
            <div class="message">
                <div class="message-header">
                    <span class="phone">To: {{ msg.to }}</span>
                    <span class="timestamp">{{ msg.timestamp }}</span>
                </div>
                <div class="message-body">{{ msg.message | highlight_code }}</div>
                <div style="margin-top: 10px; color: #6b7280; font-size: 0.75rem;">
                    ID: {{ msg.id }}
                </div>
            </div>
            {% endfor %}
        {% else %}
            <div class="message">
                <p style="text-align: center; color: #6b7280;">No messages yet. Waiting for SMS...</p>
            </div>
        {% endif %}
        
        <div class="api-info">
            <h3>API Endpoints</h3>
            <p><strong>Send SMS:</strong> <code>POST /api/sms</code></p>
            <p><strong>List Messages:</strong> <code>GET /api/messages</code></p>
            <p><strong>Clear Messages:</strong> <code>POST /api/clear</code></p>
            <p style="margin-top: 15px;">
                <strong>Kratos Configuration:</strong><br>
                <code>COURIER_SMS_PROVIDER=generic</code><br>
                <code>COURIER_SMS_REQUEST_CONFIG_URL=http://sms-mock:8030/api/sms</code>
            </p>
        </div>
    </div>
</body>
</html>
"""

@app.template_filter('highlight_code')
def highlight_code(text):
    """Highlight verification codes in the message"""
    import re
    # Match 4-8 digit codes
    return re.sub(r'\b(\d{4,8})\b', r'<span class="code">\1</span>', text)

@app.route('/')
def index():
    """Web UI to view SMS messages"""
    return render_template_string(HTML_TEMPLATE, messages=messages)

@app.route('/api/sms', methods=['POST'])
def send_sms():
    """Endpoint that Kratos calls to send SMS"""
    try:
        data = request.json
        
        # Create message record
        message = {
            'id': str(uuid.uuid4()),
            'to': data.get('to', 'Unknown'),
            'message': data.get('message', ''),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'raw': data
        }
        
        messages.append(message)
        
        # Log to console
        print(f"[SMS] To: {message['to']}")
        print(f"[SMS] Message: {message['message']}")
        print("-" * 50)
        
        # Return success response
        return jsonify({
            'success': True,
            'id': message['id'],
            'status': 'sent'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Get all messages (API endpoint)"""
    return jsonify(messages)

@app.route('/api/clear', methods=['POST'])
def clear_messages():
    """Clear all messages"""
    global messages
    messages = []
    return jsonify({'success': True})

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'messages_count': len(messages)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8030))
    debug = os.environ.get('LOG_LEVEL', 'info').lower() == 'debug'
    
    print(f"Starting SMS Mock Service on port {port}")
    print(f"Web UI: http://localhost:{port}")
    print(f"API: http://localhost:{port}/api/sms")
    
    app.run(host='0.0.0.0', port=port, debug=debug)