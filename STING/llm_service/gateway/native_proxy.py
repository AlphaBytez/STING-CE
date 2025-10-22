"""
Native LLM Service Proxy
Routes requests from Docker containers to the native LLM service running on the host
"""
import os
import httpx
import logging
from fastapi import HTTPException
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class NativeLLMProxy:
    """Proxy to native LLM service running on host machine"""
    
    def __init__(self):
        # Try native service port first, then fallback ports
        self.native_ports = [
            int(os.getenv('NATIVE_LLM_PORT', '8086')),
            8086,  # Default native port
            8085,  # Legacy port
        ]
        self.host = 'host.docker.internal'  # Docker's way to access host
        
    async def check_service_health(self, port: int) -> bool:
        """Check if service is healthy on given port"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://{self.host}:{port}/health",
                    timeout=2.0
                )
                return response.status_code == 200
        except:
            return False
    
    async def get_active_port(self) -> Optional[int]:
        """Find which port the native service is running on"""
        for port in self.native_ports:
            if await self.check_service_health(port):
                logger.info(f"Native LLM service found on port {port}")
                return port
        return None
    
    async def forward_request(self, endpoint: str, method: str = "POST", **kwargs) -> Dict[str, Any]:
        """Forward request to native LLM service"""
        port = await self.get_active_port()
        
        if not port:
            # No native service found, return None to allow fallback
            logger.warning("No native LLM service found on any port")
            return None
            
        url = f"http://{self.host}:{port}{endpoint}"
        
        try:
            async with httpx.AsyncClient() as client:
                if method == "POST":
                    response = await client.post(url, **kwargs)
                elif method == "GET":
                    response = await client.get(url, **kwargs)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Native service returned {response.status_code}: {response.text}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error forwarding to native service: {e}")
            return None
    
    async def generate(self, message: str, model: str = None, **kwargs) -> Optional[Dict[str, Any]]:
        """Generate text using native LLM service"""
        # Prepare the request payload
        payload = {
            "message": message,
            **kwargs
        }
        
        # Add model if specified
        if model:
            payload["model"] = model
            
        result = await self.forward_request(
            "/generate",
            json=payload,
            timeout=60.0
        )
        
        # Return the full result dictionary to match expected format
        return result
    
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> Optional[Dict[str, Any]]:
        """Chat completion using native LLM service"""
        result = await self.forward_request(
            "/chat",
            json={
                "messages": messages,
                **kwargs
            },
            timeout=60.0
        )
        
        return result

# Singleton instance
native_proxy = NativeLLMProxy()