#!/usr/bin/env python3
"""
Simplified Bee server for testing LLM integration
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
import logging
import datetime
from datetime import timezone
import time
import httpx
import uvicorn
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def filter_thinking_tags(text):
    """Extract clean response from DeepSeek reasoning output"""
    original_text = text
    
    # Remove complete think blocks
    if "<think>" in text and "</think>" in text:
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    
    # Handle partial thinking content (common with DeepSeek-R1)
    if "</think>" in text:
        text = re.sub(r'^.*?</think>\s*', '', text, flags=re.DOTALL)
    
    # Remove orphaned think tags
    text = text.replace("<think>", "").replace("</think>", "")
    
    # DeepSeek-R1 specific: if response starts with reasoning language, try to extract the actual response
    reasoning_indicators = [
        r'^(Okay|Alright|So|Well|I need to|I should|Let me|The user)',
        r'(I need to|I should|I\'ll|I will|I would|I can|I must)',
        r'(figure out|respond|answer|tell|explain|say)',
        r'(what I\'ve read|from what I know|I know that)'
    ]
    
    # Check if this looks like reasoning text
    is_reasoning = any(re.search(pattern, text, re.IGNORECASE) for pattern in reasoning_indicators)
    
    if is_reasoning:
        # Try to extract factual content after reasoning
        # Look for direct statements about STING
        factual_patterns = [
            r'STING is (.+?)(?:\.|$)',
            r'STING (.+?)(?:\.|$)',
            r'platform (.+?)(?:\.|$)',
            r'features? (.+?)(?:\.|$)'
        ]
        
        for pattern in factual_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                factual_content = match.group(1).strip()
                if len(factual_content) > 10:
                    return f"STING is {factual_content}."
        
        # If no factual extraction worked, provide a direct response based on the prompt
        if "what is sting" in original_text.lower():
            return "STING is a secure messaging and collaboration platform with end-to-end encryption, passkey authentication, local AI models, and self-hosted deployment options."
        elif any(word in original_text.lower() for word in ["hello", "hi", "hey"]):
            return "Hi! I'm Bee. How can I help?"
    
    # Clean up extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    # If we end up with very short or empty text, try a fallback
    if len(text) < 10 or not text:
        # Try to extract the last sentence that looks like a response
        sentences = original_text.split('.')
        for sentence in reversed(sentences):
            sentence = sentence.strip()
            if len(sentence) > 15 and not any(word in sentence.lower() for word in ['need to', 'should', 'i think', 'let me']):
                return sentence + '.'
        
        # Ultimate fallback
        return "I'm here to help with STING! Could you please be more specific about what you'd like to know?"
    
    return text

# Configuration
BEE_PORT = int(os.getenv('BEE_PORT', '8888'))
BEE_HOST = os.getenv('BEE_HOST', '0.0.0.0')
NATIVE_LLM_URL = os.getenv('NATIVE_LLM_URL', 'http://localhost:8086')

class BeeRequest(BaseModel):
    """Request model for Bee chat interactions"""
    message: str
    user_id: str
    conversation_id: Optional[str] = None

class BeeResponse(BaseModel):
    """Response model for Bee chat interactions"""
    response: str
    conversation_id: str
    processing_time: float
    timestamp: str
    model_used: str = "deepseek-1.5b"

# Create FastAPI app
app = FastAPI(
    title="Bee - STING AI Assistant (Simplified)",
    description="Simplified AI-powered chat assistant",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Bee - STING AI Assistant (Simplified)",
        "version": "1.0.0",
        "status": "buzzing",
        "llm_endpoint": NATIVE_LLM_URL
    }

@app.get("/health")
async def health_check():
    """Health check"""
    # Check LLM service
    llm_healthy = False
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NATIVE_LLM_URL}/health", timeout=5.0)
            llm_healthy = response.status_code == 200
    except:
        pass
    
    return {
        "status": "healthy" if llm_healthy else "degraded",
        "service": "bee",
        "llm_service": llm_healthy,
        "timestamp": datetime.datetime.now(timezone.utc).isoformat()
    }

@app.post("/chat/test", response_model=BeeResponse)
async def test_chat(request: BeeRequest):
    """Test chat endpoint"""
    start_time = time.time()
    
    # Generate conversation ID if not provided
    conversation_id = request.conversation_id or f"test-{int(time.time())}"
    
    try:
        # Prepare STING system prompt
        system_prompt = """You are Bee, a helpful and friendly AI assistant for the STING platform. 
STING is a secure messaging and collaboration platform with advanced security features including:
- End-to-end encryption
- Passkey authentication  
- Local AI models for privacy
- Self-hosted deployment options

Respond directly to users without explaining your thought process. Be concise, helpful and professional."""
        
        # Conservative token limits for DeepSeek speed
        msg_lower = request.message.lower()
        if any(word in msg_lower for word in ["how", "explain", "tutorial", "guide", "steps"]):
            max_tokens = 60   # Much shorter for speed
        elif any(word in msg_lower for word in ["what", "who", "when", "where"]):
            max_tokens = 40   # Very short factual
        else:
            max_tokens = 30   # Ultra short for greetings
        
        # Call LLM service
        async with httpx.AsyncClient() as client:
            llm_response = await client.post(
                f"{NATIVE_LLM_URL}/generate",
                json={
                    "message": f"System: {system_prompt}\n\nUser: {request.message}\nBee: ",
                    "model": "deepseek-1.5b",
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "stop": ["\nUser:", "\nHuman:", "</think>", "\n\n"]
                },
                timeout=12.0  # Conservative timeout for DeepSeek
            )
            
            if llm_response.status_code == 200:
                data = llm_response.json()
                response_text = data.get('text', '').strip()
                
                # Clean up response - remove DeepSeek thinking tags
                response_text = filter_thinking_tags(response_text)
                
                # Remove role prefixes
                if response_text.startswith("Bee:"):
                    response_text = response_text[4:].strip()
                
                if not response_text:
                    response_text = "I'm here to help! Could you please rephrase your question?"
            else:
                logger.error(f"LLM service error: {llm_response.status_code}")
                response_text = "I apologize, but I'm having trouble processing your request. Please try again."
                
    except httpx.TimeoutException:
        logger.error("LLM service timeout")
        response_text = "I'm taking a bit longer to think. Please try again in a moment."
    except Exception as e:
        logger.error(f"Error calling LLM: {str(e)}")
        response_text = "I'm here to help with STING! What would you like to know about our secure messaging platform?"
    
    return BeeResponse(
        response=response_text,
        conversation_id=conversation_id,
        processing_time=time.time() - start_time,
        timestamp=datetime.datetime.now(timezone.utc).isoformat(),
        model_used="deepseek-1.5b"
    )

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize Bee on startup"""
    logger.info(f"🐝 Bee (Simplified) is starting up on {BEE_HOST}:{BEE_PORT}")
    logger.info(f"🐝 LLM service endpoint: {NATIVE_LLM_URL}")
    
    # Check LLM service
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{NATIVE_LLM_URL}/health", timeout=5.0)
            if response.status_code == 200:
                logger.info("🐝 LLM service is available!")
            else:
                logger.warning("⚠️  LLM service returned non-200 status")
    except Exception as e:
        logger.warning(f"⚠️  Could not reach LLM service: {e}")
    
    logger.info("🐝 Bee is ready to buzz!")

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=BEE_HOST,
        port=BEE_PORT,
        log_level="info"
    )