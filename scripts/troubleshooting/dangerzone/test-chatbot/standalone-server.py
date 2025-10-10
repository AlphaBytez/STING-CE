#!/usr/bin/env python3
"""
Standalone Test Chatbot Server for STING platform
Simple implementation that works without dependencies
"""

import os
import time
import datetime
import json
import http.server
import socketserver
from urllib.parse import parse_qs, urlparse

# Configure settings
PORT = int(os.environ.get("PORT", 8082))
HOST = os.environ.get("HOST", "0.0.0.0")

# Memory store for conversations
conversations = {}

class ChatbotHandler(http.server.BaseHTTPRequestHandler):
    def _set_headers(self, status_code=200):
        self.send_response(status_code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self._set_headers()
        
    def do_GET(self):
        # Handle GET requests (health check and root)
        if self.path == '/health':
            self._set_headers()
            response = {
                "status": "healthy",
                "server_running": True,
                "service_initialized": True,
                "error": None,
                "timestamp": str(time.time())
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/':
            self._set_headers()
            response = {
                "service": "STANDALONE Test Chatbot",
                "version": "0.1.0",
                "endpoints": [
                    {"path": "/chat/message", "method": "POST", "description": "Process a chat message"},
                    {"path": "/chat/clear", "method": "POST", "description": "Clear conversation history"},
                    {"path": "/health", "method": "GET", "description": "Health check"}
                ]
            }
            self.wfile.write(json.dumps(response).encode())
        else:
            self._set_headers(404)
            self.wfile.write(json.dumps({"error": "Not found"}).encode())
    
    def do_POST(self):
        # Handle POST requests (chat message, clear)
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            request_json = json.loads(post_data.decode('utf-8'))
            
            if self.path == '/chat/message':
                self._handle_chat_message(request_json)
            elif self.path == '/chat/clear':
                self._handle_clear_conversation(request_json)
            else:
                self._set_headers(404)
                self.wfile.write(json.dumps({"error": "Not found"}).encode())
        except json.JSONDecodeError:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Invalid JSON"}).encode())
    
    def _handle_chat_message(self, request):
        # Process a chat message
        user_id = request.get('user_id', 'anonymous')
        message = request.get('message', '')
        
        print(f"Received message from {user_id}: {message}")
        
        # Track the message
        if user_id not in conversations:
            conversations[user_id] = []
        
        conversations[user_id].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        # Generate a response
        start_time = time.time()
        time.sleep(0.5)  # Simulate processing time
        
        # Simple pattern matching
        message = message.lower()
        if "hello" in message or "hi" in message:
            response = "Hello! I'm the Standalone Test Chatbot. How can I help you today?"
        elif "how are you" in message:
            response = "I'm functioning perfectly as a standalone test chatbot. Thanks for asking!"
        elif "model" in message or "llm" in message:
            response = "I'm a simple rule-based test chatbot, not using any LLM models."
        elif "test" in message:
            response = "Yes, this is the standalone test chatbot service. It's working correctly!"
        else:
            response = f"I received your message: '{message}'. This is a test response from the standalone chatbot."
        
        # Track response
        conversations[user_id].append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
        processing_time = time.time() - start_time
        
        # Send response
        self._set_headers()
        response_data = {
            "response": response,
            "conversation_id": user_id,
            "tools_used": [],
            "processing_time": processing_time,
            "filtered": False,
            "filter_reason": None,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response_data).encode())
    
    def _handle_clear_conversation(self, request):
        # Clear a conversation
        user_id = request.get('user_id', 'anonymous')
        
        if user_id in conversations:
            conversations[user_id] = []
        
        # Send response
        self._set_headers()
        response_data = {
            "status": "success",
            "message": "Conversation cleared"
        }
        self.wfile.write(json.dumps(response_data).encode())

def run_server():
    server_address = (HOST, PORT)
    httpd = socketserver.TCPServer(server_address, ChatbotHandler)
    print(f"Starting standalone test chatbot server on {HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Server stopped")

if __name__ == "__main__":
    run_server()