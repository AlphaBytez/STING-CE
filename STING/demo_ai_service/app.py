#!/usr/bin/env python3
"""
Demo AI Service - Lightweight stub for demo mode
Returns contextual placeholder messages instead of calling LLM
"""

import os
import sys
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

# Note: Demo service is self-contained, no external imports needed
try:
    import yaml
except ImportError:
    yaml = None

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Demo responses configuration
DEMO_RESPONSES = {
    "greeting": [
        "Hey there! 👋 Welcome to the STING demo! I'm Bee, and I'm excited to show you around. What would you like to explore first?",
        "Hi! 🐝 I'm Bee, your STING demo assistant. This is a great place to explore what STING can do!",
        "Welcome! I'm Bee - let's explore STING's private AI capabilities together!"
    ],
    "help": [
        "Great question! In STING, you can:\n\n🐝 **Bee** - Chat with AI about your documents\n🍯 **Honey Jars** - Organize your knowledge base\n🔒 **Private & Secure** - Everything runs on your infrastructure\n\nWant me to show you around?",
        "STING is your private AI workspace! Here's what you can do:\n\n• Create Honey Jars with your documents\n• Chat with Bee about your knowledge base\n• Everything stays on your servers\n\nWhat interests you most?"
    ],
    "capabilities": [
        "STING is your private AI workspace! Here's what it offers:\n\n🍯 **Honey Jars** - Containerized knowledge bases with ChromaDB vector search\n🐝 **Bee AI Assistant** - Conversational AI connected to your documents\n🔐 **Enterprise Auth** - Ory Kratos with WebAuthn/passkeys and MFA\n🛡️ **Security** - Automatic PII detection and HashiCorp Vault secrets management",
        "STING combines several powerful capabilities:\n\n1. **Knowledge Management** - Store documents in Honey Jars\n2. **AI Assistant** - Bee answers questions about your data\n3. **Enterprise Security** - Your data never leaves your infrastructure\n4. **Open Source** - Community Edition is free to use!"
    ],
    "pricing": [
        "STING has two editions:\n\n🍯 **Community Edition (CE)** - Free, open-source, self-hosted\n🏢 **Enterprise** - Contact sales@stingassistant.com for pricing\n\nThe Community Edition has everything you need to run STING on your own infrastructure. Enterprise adds advanced features like Teams, SSO, and priority support.",
        "Great question! STING CE is completely free and open source. For Enterprise features (Teams, SSO, advanced security), contact our team:\n\n📧 sales@stingassistant.com\n\nWould you like a link to the installation guide?"
    ],
    "security": [
        "STING runs entirely on your infrastructure - no data ever leaves your servers! Here's the security stack:\n\n• **Ory Kratos** - Identity and session management\n• **WebAuthn/Passkeys** - Passwordless authentication\n• **TOTP MFA** - Two-factor authentication\n• **HashiCorp Vault** - Secrets management\n• **Automatic PII Detection** - Protects sensitive data",
        "Security is built into STING's DNA:\n\n🔐 All authentication runs through Ory Kratos\n🔑 Your documents stay on your servers\n🛡️ PII is automatically detected and masked\n🔧 Secrets are managed via HashiCorp Vault\n\nThis is why enterprises trust STING for their AI deployments!"
    ],
    "installation": [
        "Getting STING running is straightforward!\n\n1. Clone the repo: `git clone https://github.com/AlphaBytez/STING-CE`\n2. Run the bootstrap: `bash bootstrap.sh`\n3. Follow the web wizard\n\nThe installer handles Docker, dependencies, and SSL certificates. Want me to point you to the documentation?",
        "STING can be installed on:\n\n• Ubuntu/Debian Linux\n• macOS (with Docker Desktop)\n• Windows WSL2\n\nThe quick install is one command:\n\n```bash\nbash -c \"$(curl -fsSL https://raw.githubusercontent.com/AlphaBytez/STING-CE/main/bootstrap.sh)\"\n```\n\n[Check the docs](https://docs.sting.alphabytez.dev) for full details!"
    ],
    "demo": [
        "This is the STING demo environment! Here you can explore the interface and learn about features without installing anything.\n\n🐝 **Bee** would normally connect to your knowledge base\n🍯 **Honey Jars** would store your documents\n🔐 **Auth** would be handled by Ory Kratos\n\nSince this is a demo, I provide informational responses instead of real AI answers. Ready to try the full version?",
        "You're in the STING demo! This public demo lets you experience the platform without installation.\n\n**What you're seeing:**\n- The STING interface and navigation\n- How Honey Jars organize knowledge\n- The Bee AI chat interface\n\n**What's different from full STING:**\n- No real AI (I'm showing informational responses)\n- No document uploads\n- Sessions expire after 30 minutes\n\n[Get started with STING](https://docs.sting.alphabytez.dev) to experience the real thing!"
    ],
    "contact": [
        "I'd love to help you learn more about STING!\n\n📧 **Sales**: sales@stingassistant.com\n📖 **Docs**: docs.sting.alphabytez.dev\n💻 **GitHub**: github.com/AlphaBytez/STING-CE\n\nWhat would you like to know more about?",
        "Thanks for your interest in STING!\n\nFor sales inquiries: 📧 sales@stingassistant.com\nFor technical questions: 📖 Check the docs\nFor bugs/features: 💻 Open an issue on GitHub\n\nHow can we help you get started?"
    ],
    "default": [
        "That's a great question! In a live STING instance, I'd connect to your knowledge base and provide personalized answers based on your documents.\n\nFor now, I'm here to show you what's possible! Want to explore STING's features?",
        "I appreciate that question! In a real STING deployment, Bee would search your Honey Jars and give you contextual answers.\n\nSince this is a demo, let me connect you with our team who can show you the full capabilities:\n\n📧 sales@stingassistant.com",
        "I wish I could answer that with your data! In STING, Bee connects to your documents to provide personalized responses.\n\nThis demo shows the interface - to see real AI in action, you'd need to install STING. [Ready to try?](https://docs.sting.alphabytez.dev)"
    ]
}


def load_demo_config():
    """Load demo configuration"""
    config_path = os.environ.get('INSTALL_DIR', '/opt/sting-ce') + '/conf/config.demo.yml'
    config = {
        'demo_ai': {
            'enabled': True,
            'mode': 'informational',
            'responses': {}
        }
    }

    # Try to load from YAML
    try:
        import yaml
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                yaml_config = yaml.safe_load(f)
                if yaml_config and 'demo_ai' in yaml_config:
                    config['demo_ai'] = yaml_config['demo_ai']
    except ImportError:
        pass

    return config


def get_response_for_intent(message, intent=None):
    """Get demo response based on message content or intent"""
    config = load_demo_config()
    responses = config.get('demo_ai', {}).get('responses', DEMO_RESPONSES)

    message_lower = message.lower()

    # Detect intent from message
    if any(w in message_lower for w in ['hello', 'hi', 'hey', 'start', 'begin']):
        category = 'greeting'
    elif any(w in message_lower for w in ['help', 'how', 'what can', 'what does', 'explain']):
        category = 'help'
    elif any(w in message_lower for w in ['capabilit', 'feature', 'what is sting', 'tell me about']):
        category = 'capabilities'
    elif any(w in message_lower for w in ['price', 'cost', 'pricing', 'how much', 'free', 'edition']):
        category = 'pricing'
    elif any(w in message_lower for w in ['security', 'safe', 'private', 'encrypt', 'data']):
        category = 'security'
    elif any(w in message_lower for w in ['install', 'deploy', 'setup', 'run', 'get started']):
        category = 'installation'
    elif any(w in message_lower for w in ['demo', 'this is', 'what am i', 'explain demo']):
        category = 'demo'
    elif any(w in message_lower for w in ['contact', 'email', 'talk to', 'sales', 'support']):
        category = 'contact'
    else:
        category = 'default'

    # Get responses for category
    category_responses = responses.get(category, DEMO_RESPONSES.get(category, DEMO_RESPONSES['default']))

    # Return first response (could randomize in future)
    response_text = category_responses[0] if isinstance(category_responses, list) else category_responses

    return response_text, category


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    config = load_demo_config()
    return jsonify({
        'status': 'healthy',
        'service': 'demo-ai',
        'demo_mode': True,
        'enabled': config.get('demo_ai', {}).get('enabled', True),
        'mode': config.get('demo_ai', {}).get('mode', 'informational'),
        'timestamp': datetime.utcnow().isoformat()
    })


@app.route('/status', methods=['GET'])
def status():
    """Status endpoint for service discovery"""
    config = load_demo_config()
    return jsonify({
        'service': 'demo-ai',
        'version': '1.0.0',
        'demo_mode': True,
        'capabilities': list(DEMO_RESPONSES.keys()),
        'config': {
            'enabled': config.get('demo_ai', {}).get('enabled', True),
            'mode': config.get('demo_ai', {}).get('mode', 'informational')
        }
    })


@app.route('/bee/chat', methods=['POST'])
def bee_chat():
    """
    Demo chat endpoint - returns contextual placeholder responses
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({
                'error': 'No data provided',
                'message': 'Please send a message'
            }), 400

        message = data.get('message', '').strip()
        conversation_history = data.get('history', [])

        if not message:
            return jsonify({
                'error': 'Empty message',
                'message': 'Please send a non-empty message'
            }), 400

        # Get contextual response
        response_text, category = get_response_for_intent(message)

        # Build response (compatible with real Bee chat format)
        response = {
            'success': True,
            'response': response_text,
            'category': category,
            'demo_mode': True,
            'meta': {
                'model': 'demo-informational',
                'tokens_used': len(response_text.split()),
                'response_time_ms': 50
            }
        }

        logger.info(f"Demo chat response: category={category}, message_length={len(message)}")

        return jsonify(response)

    except Exception as e:
        logger.error(f"Error in demo chat: {str(e)}")
        return jsonify({
            'error': 'Internal error',
            'message': 'Demo service encountered an error',
            'demo_mode': True
        }), 500


@app.route('/bee/chat/stream', methods=['POST'])
def bee_chat_stream():
    """
    Streaming chat endpoint - returns response in chunks for demo
    """
    try:
        data = request.get_json()
        message = data.get('message', '').strip() if data else ''

        if not message:
            return jsonify({
                'error': 'Empty message',
                'message': 'Please send a non-empty message'
            }), 400

        response_text, category = get_response_for_intent(message)

        # For demo, simulate streaming by sending the full response
        # In a real implementation, this would chunk the response
        return jsonify({
            'success': True,
            'response': response_text,
            'category': category,
            'demo_mode': True,
            'stream': False,  # Demo doesn't actually stream
            'meta': {
                'model': 'demo-informational',
                'tokens_used': len(response_text.split())
            }
        })

    except Exception as e:
        logger.error(f"Error in demo chat stream: {str(e)}")
        return jsonify({
            'error': 'Internal error',
            'message': 'Demo service encountered an error',
            'demo_mode': True
        }), 500


@app.route('/ollama/models', methods=['GET'])
def list_models():
    """List available models - demo returns placeholder"""
    return jsonify({
        'models': [
            {
                'id': 'demo-informational',
                'name': 'Demo Informational',
                'size': '0',
                'modified_at': datetime.utcnow().isoformat(),
                'digest': 'demo',
                'details': {
                    'format': 'demo',
                    'family': 'informational',
                    'families': ['informational'],
                    'parameter_size': 'demo',
                    'quantization_level': 'N/A'
                }
            }
        ],
        'demo_mode': True
    })


@app.route('/ollama/status', methods=['GET'])
def ollama_status():
    """Ollama status - demo returns ready"""
    return jsonify({
        'status': 'ready',
        'demo_mode': True,
        'message': 'Demo mode active - informational responses enabled'
    })


# Analytics endpoint for demo session tracking
@app.route('/analytics/event', methods=['POST'])
def track_event():
    """Track demo usage events"""
    try:
        data = request.get_json()
        event_type = data.get('type', 'unknown')
        properties = data.get('properties', {})

        logger.info(f"Demo analytics event: {event_type}, properties: {properties}")

        return jsonify({
            'success': True,
            'event': event_type
        })
    except Exception as e:
        logger.error(f"Error tracking event: {str(e)}")
        return jsonify({'success': False}), 500


if __name__ == '__main__':
    port = int(os.environ.get('DEMO_AI_PORT', 8095))
    host = os.environ.get('DEMO_AI_HOST', '0.0.0.0')

    logger.info(f"Starting Demo AI Service on {host}:{port}")
    logger.info("Demo mode active - serving informational responses")

    app.run(host=host, port=port, debug=False)
