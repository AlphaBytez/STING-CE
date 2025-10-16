"""
Simplified generate_bee_response function using BeePromptConfig
This replaces the existing function in bee_server.py
"""

from chatbot.prompts.bee_prompt_config import BeePromptConfig
import httpx
import logging

logger = logging.getLogger(__name__)

async def generate_bee_response(
    message: str, 
    conversation_id: str,
    user_id: str,
    user_role: UserRole,
    sentiment: Optional[Dict[str, float]],
    tools_used: List[Dict[str, Any]]
) -> str:
    """Generate response using LLM with enhanced Bee personality and context"""
    
    # Determine sentiment category from sentiment scores
    sentiment_category = "neutral"
    if sentiment:
        if sentiment.get('anger', 0) > 0.5 or sentiment.get('negative', 0) > 0.6:
            sentiment_category = "frustrated"
        elif sentiment.get('question', 0) > 0.7:
            sentiment_category = "confused"
        elif sentiment.get('positive', 0) > 0.7:
            sentiment_category = "satisfied"
        elif sentiment.get('urgency', 0) > 0.7:
            sentiment_category = "urgent"
    
    # Get conversation history for context
    conversation_history = await conversation_manager.get_conversation_history(
        conversation_id, limit=5
    )
    
    # Build previous context string
    previous_context = ""
    if conversation_history:
        for msg in conversation_history[-3:]:
            previous_context += f"{msg['role']}: {msg['content'][:100]}...\n"
    
    # Generate the complete prompt using BeePromptConfig
    prompt = BeePromptConfig.generate_prompt(
        user_role=user_role.value,
        sentiment=sentiment_category,
        conversation_mode="support" if "help" in message.lower() else "general",
        security_level="high" if any(word in message.lower() for word in ["password", "security", "encrypt"]) else "standard",
        conversation_id=conversation_id,
        previous_context=previous_context
    )
    
    # Add feature-specific context
    feature_context = BeePromptConfig.get_feature_context(message)
    if feature_context:
        prompt += f"\n\n{feature_context}"
    
    # Add tool results if any
    if tools_used:
        prompt += "\n\nTool Results:"
        for tool in tools_used:
            prompt += f"\n- {tool['name']}: {tool.get('result', tool.get('summary', 'Completed'))}"
    
    # Add the current message
    prompt += f"\n\nUser: {message}\nBee: "
    
    # Try to get response from LLM
    try:
        # Try multiple endpoints
        endpoints = [
            "http://host.docker.internal:8086",  # Native service
            "http://llm-gateway:8086"             # Docker service
        ]
        
        for endpoint in endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{endpoint}/generate",
                        json={
                            "message": prompt,
                            "model": "tinyllama",
                            "max_tokens": 500,
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "stop": ["\nUser:", "\nHuman:"]
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        text = data.get('text', data.get('response', ''))
                        
                        if text and text.strip():
                            # Clean and enhance the response
                            text = text.strip()
                            
                            # Remove any role prefixes
                            for prefix in ["Bee:", "Assistant:", "AI:"]:
                                if text.startswith(prefix):
                                    text = text[len(prefix):].strip()
                            
                            # Apply sentiment enhancements
                            return BeePromptConfig.enhance_response(text, sentiment_category)
                    
            except Exception as e:
                logger.error(f"Error with {endpoint}: {e}")
                continue
        
        # If all endpoints fail, use enhanced fallback
        return generate_enhanced_fallback(message, sentiment_category, tools_used)
        
    except Exception as e:
        logger.error(f"Error in generate_bee_response: {e}")
        return generate_enhanced_fallback(message, sentiment_category, tools_used)


def generate_enhanced_fallback(message: str, sentiment: str, tools: List[Dict]) -> str:
    """Smart fallback responses when LLM is unavailable"""
    
    # Detect intent
    msg_lower = message.lower()
    
    if any(w in msg_lower for w in ["hello", "hi", "hey"]):
        base = "Hi! I'm Bee. How can I help?"
    elif any(w in msg_lower for w in ["help", "how", "what", "explain"]):
        base = "I'd be happy to help! STING offers secure messaging, passkey authentication, and AI assistance. What would you like to know more about?"
    elif any(w in msg_lower for w in ["security", "encrypt", "safe"]):
        base = "STING prioritizes security with end-to-end encryption, local AI models, and passkey authentication. Your data never leaves your control."
    elif any(w in msg_lower for w in ["error", "problem", "issue", "broken"]):
        base = "I understand you're experiencing an issue. Let me help troubleshoot. Could you describe what's happening?"
    else:
        base = "I'm here to assist with STING's features. Could you tell me more about what you're trying to do?"
    
    # Apply sentiment adjustments
    prefixes = {
        "frustrated": "I understand this might be frustrating. ",
        "confused": "Let me clarify this for you. ",
        "urgent": "I'll help you quickly. ",
        "satisfied": "Great! "
    }
    
    return prefixes.get(sentiment, "") + base