#!/usr/bin/env python3
"""
Simplified Bee server for testing LLM integration
"""
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import httpx
import logging
import time
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Test Bee Server")

class ChatRequest(BaseModel):
    message: str
    user_id: Optional[str] = "test-user"

class ChatResponse(BaseModel):
    response: str
    timestamp: float
    llm_used: bool = False
    error: Optional[str] = None

@app.get("/")
async def root():
    return {"service": "Test Bee Server", "status": "ready"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/chat")
async def chat(request: ChatRequest):
    """Test chat endpoint that calls LLM service"""
    start_time = time.time()
    
    # Try to call the LLM service
    llm_url = "http://host.docker.internal:8086"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{llm_url}/generate",
                json={
                    "message": request.message,
                    "model": "tinyllama",
                    "max_tokens": 200
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                llm_response = data.get('text', data.get('response', 'No response from LLM'))
                return ChatResponse(
                    response=llm_response,
                    timestamp=time.time() - start_time,
                    llm_used=True
                )
            else:
                return ChatResponse(
                    response=f"LLM returned status {response.status_code}",
                    timestamp=time.time() - start_time,
                    llm_used=False,
                    error=f"Status {response.status_code}: {response.text[:200]}"
                )
                
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        return ChatResponse(
            response="Error connecting to LLM service",
            timestamp=time.time() - start_time,
            llm_used=False,
            error=str(e)
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8888)