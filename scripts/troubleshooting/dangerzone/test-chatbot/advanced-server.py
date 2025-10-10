#!/usr/bin/env python3
"""
Advanced Test Chatbot Server for STING platform
Communicates directly with the LLM Gateway
"""

import os
import sys
import time
import json
import http.server
import socketserver
import urllib.request
import urllib.error
from datetime import datetime
from urllib.parse import parse_qs, urlparse

# Configure settings
PORT = int(os.environ.get("PORT", 8083))
HOST = os.environ.get("HOST", "0.0.0.0")
LLM_GATEWAY_URL = os.environ.get("LLM_GATEWAY_URL", "http://sting-ce-llm-gateway-1:8080")

# Memory store for conversations
conversations = {}

print(f"Starting advanced test chatbot server with LLM Gateway URL: {LLM_GATEWAY_URL}")

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
                "service": "ADVANCED Test Chatbot",
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
        
        # Log request details
        client_address = self.client_address[0]
        print(f"\n==== New Request from {client_address} to {self.path} ====")
        print(f"Headers: {self.headers}")
        
        try:
            request_json = json.loads(post_data.decode('utf-8'))
            print(f"Request data: {json.dumps(request_json)}")
            
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
            "timestamp": datetime.now().isoformat()
        })
        
        # Generate a response
        start_time = time.time()
        
        # Try to use the LLM Gateway
        try:
            llm_response = self._call_llm_gateway(message)
            if llm_response and not llm_response.startswith("Failed to connect"):
                response = llm_response
                # Log the successful response
                print(f"Successful LLM response: {response[:100]}...")
            else:
                # If we got an error message from the LLM Gateway attempt
                response = f"DIAGNOSTIC MODE: {llm_response}"
                print(f"Using diagnostic error response")
        except Exception as e:
            print(f"Error calling LLM Gateway: {str(e)}")
            # Fallback with detailed error
            response = f"DIAGNOSTIC ERROR: {str(e)}\n\n{self._generate_fallback_response(message)}"
        
        # Track response
        conversations[user_id].append({
            "role": "assistant",
            "content": response,
            "timestamp": datetime.now().isoformat()
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
            "timestamp": datetime.now().isoformat()
        }
        self.wfile.write(json.dumps(response_data).encode())
    
    def _call_llm_gateway(self, message):
        """Call the LLM Gateway API and return the response"""
        # First, let's test the health endpoint
        try:
            health_url = f"{LLM_GATEWAY_URL}/health"
            print(f"Testing LLM Gateway health at {health_url}")
            
            health_req = urllib.request.Request(health_url, method='GET')
            try:
                with urllib.request.urlopen(health_req, timeout=5) as response:
                    health_data = json.loads(response.read().decode('utf-8'))
                    print(f"Health check response: {json.dumps(health_data)}")
            except Exception as health_e:
                print(f"Health check failed: {str(health_e)}")
        except Exception as e:
            print(f"Error setting up health check: {str(e)}")
            
        # Now let's try multiple endpoint variants
        endpoints = [
            f"{LLM_GATEWAY_URL}/generate",  # Standard endpoint
            "http://localhost:8085/generate",  # Try local port mapping
            "http://localhost:8080/generate",  # Try default port
            "http://host.docker.internal:8085/generate",  # Try host.docker.internal
            "http://sting-llm-gateway-1:8080/generate",  # Try container name without prefix
            "http://sting-ce-llm-gateway-1:8080/generate",  # Try container name with prefix
            "http://172.18.0.12:8080/generate"  # Try direct IP address
        ]
        
        error_details = []
        
        for url in endpoints:
            try:
                print(f"\nAttempting LLM Gateway at {url} with message: {message}")
                
                headers = {'Content-Type': 'application/json'}
                data = json.dumps({
                    "message": message,
                    "max_tokens": 150,
                    "temperature": 0.7,
                    "model": "llama3"
                }).encode('utf-8')
                
                req = urllib.request.Request(url, data=data, headers=headers, method='POST')
                
                try:
                    with urllib.request.urlopen(req, timeout=10) as response:
                        print(f"Success! Status code: {response.status}")
                        response_data = json.loads(response.read().decode('utf-8'))
                        return response_data.get('response', '')
                except urllib.error.HTTPError as he:
                    error_body = he.read().decode('utf-8')
                    print(f"HTTP Error {he.code}: {he.reason}")
                    print(f"Response body: {error_body}")
                    error_details.append(f"{url} - HTTP {he.code}: {error_body}")
                except urllib.error.URLError as ue:
                    print(f"URL Error: {str(ue.reason)}")
                    error_details.append(f"{url} - Connection Error: {str(ue.reason)}")
                except Exception as req_e:
                    print(f"Request Error: {str(req_e)}")
                    error_details.append(f"{url} - Request Error: {str(req_e)}")
            except Exception as e:
                print(f"Setup Error for {url}: {str(e)}")
                error_details.append(f"{url} - Setup Error: {str(e)}")
        
        # If we reach here, all direct connection attempts failed
        # Try using curl as a last resort
        print("\nTrying curl as a last resort...")
        try:
            import subprocess
            curl_endpoints = [
                f"{LLM_GATEWAY_URL}/generate",
                "http://172.18.0.12:8080/generate",
                "http://sting-ce-llm-gateway-1:8080/generate"
            ]
            
            for url in curl_endpoints:
                try:
                    cmd = [
                        "curl", "-s", "-X", "POST", 
                        "-H", "Content-Type: application/json", 
                        "-d", f'{{"message": "{message}", "max_tokens": 150, "temperature": 0.7, "model": "llama3"}}',
                        url
                    ]
                    print(f"Executing: {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    print(f"Curl exit code: {result.returncode}")
                    print(f"Curl stdout: {result.stdout}")
                    print(f"Curl stderr: {result.stderr}")
                    
                    if result.returncode == 0 and result.stdout.strip():
                        try:
                            curl_response = json.loads(result.stdout)
                            if "response" in curl_response:
                                return curl_response["response"]
                        except:
                            pass
                except Exception as ce:
                    print(f"Curl attempt failed for {url}: {str(ce)}")
        except Exception as se:
            print(f"Subprocess error: {str(se)}")
            
        # If we reach here, all attempts failed
        error_summary = "\n".join(error_details)
        print(f"All LLM Gateway attempts failed:\n{error_summary}")
        return f"Failed to connect to LLM Gateway after trying multiple endpoints and curl. Error details: {error_summary}"
    
    def _generate_fallback_response(self, message):
        """Generate a fallback response if the LLM Gateway is unavailable"""
        # Simple pattern matching
        message = message.lower()
        if "hello" in message or "hi" in message:
            return "Hello! I'm the Advanced Test Chatbot (fallback mode). How can I help you today?"
        elif "how are you" in message:
            return "I'm functioning in fallback mode as the LLM Gateway is unavailable. Thanks for asking!"
        elif "model" in message or "llm" in message:
            return "I normally use the LLM Gateway, but it seems to be unavailable at the moment."
        elif "test" in message:
            return "Yes, this is the advanced test chatbot service in fallback mode. It's working correctly!"
        else:
            return f"I received your message: '{message}'. LLM Gateway is unavailable, so I'm responding in fallback mode."
    
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
    print(f"Starting advanced test chatbot server on {HOST}:{PORT}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Server stopped")

if __name__ == "__main__":
    run_server()