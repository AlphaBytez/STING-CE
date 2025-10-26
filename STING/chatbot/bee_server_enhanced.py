"""
Enhanced generate_bee_response function with comprehensive prompt configuration
This can replace the existing function in bee_server.py
"""

from chatbot.prompts.bee_prompt_config import BeePromptConfig

async def generate_bee_response(
    message: str, 
    conversation_id: str,
    user_id: str,
    user_role: UserRole,
    sentiment: Optional[Dict[str, float]],
    tools_used: List[Dict[str, Any]]
) -> str:
    """Generate response using LLM with enhanced Bee personality and context"""
    
    # Get conversation history for context
    conversation_history = await conversation_manager.get_conversation_history(
        conversation_id, limit=10
    )
    
    # Determine sentiment category
    sentiment_category = "neutral"
    if sentiment:
        if sentiment.get('anger', 0) > 0.5 or sentiment.get('frustration', 0) > 0.5:
            sentiment_category = "frustrated"
        elif sentiment.get('confusion', 0) > 0.5:
            sentiment_category = "confused"
        elif sentiment.get('joy', 0) > 0.5 or sentiment.get('positive', 0) > 0.7:
            sentiment_category = "satisfied"
        elif sentiment.get('urgency', 0) > 0.7:
            sentiment_category = "urgent"
    
    # Build previous context from conversation history
    previous_context = ""
    if conversation_history:
        recent_messages = conversation_history[-3:]  # Last 3 exchanges
        for msg in recent_messages:
            previous_context += f"{msg['role']}: {msg['content'][:100]}...\n"
    
    # Generate the customized system prompt
    system_prompt = BeePromptConfig.generate_prompt(
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
        system_prompt += f"\n\nRelevant Feature Information:\n{feature_context}"
    
    # Add knowledge base context
    knowledge_context = await knowledge_base.get_relevant_knowledge(message)
    if knowledge_context:
        system_prompt += f"\n\nKnowledge Base Context:\n{knowledge_context}"
    
    # Add tool results if any
    if tools_used:
        system_prompt += "\n\nTool Execution Results:"
        for tool in tools_used:
            system_prompt += f"\n- {tool['name']}: {tool.get('result', 'Completed')}"
            if 'data' in tool and tool['data']:
                # Summarize tool data intelligently
                data_summary = summarize_tool_data(tool['data'])
                system_prompt += f"\n  Summary: {data_summary}"
    
    # Build the conversation prompt
    conversation_prompt = f"{system_prompt}\n\n"
    
    # Add conversation history with proper formatting
    if conversation_history:
        conversation_prompt += "Conversation History:\n"
        for msg in conversation_history[-5:]:  # Include last 5 messages
            role = "User" if msg['role'] == 'user' else "Bee"
            conversation_prompt += f"{role}: {msg['content']}\n"
        conversation_prompt += "\n"
    
    # Add the current user message
    conversation_prompt += f"User: {message}\n"
    conversation_prompt += "Bee: "  # Prime the model to respond as Bee
    
    try:
        # Call LLM with the enhanced prompt
        import httpx
        
        # Try multiple LLM endpoints
        llm_endpoints = [
            {"url": "http://host.docker.internal:8086", "name": "native"},
            {"url": "http://llm-gateway:8086", "name": "docker"}
        ]
        
        last_error = None
        
        for endpoint in llm_endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        f"{endpoint['url']}/generate",
                        json={
                            "message": conversation_prompt,
                            "model": "tinyllama",  # Use configured model
                            "max_tokens": 500,
                            "temperature": 0.7,
                            "top_p": 0.9,
                            "frequency_penalty": 0.3,  # Reduce repetition
                            "presence_penalty": 0.3,   # Encourage variety
                            "stop": ["\nUser:", "\nHuman:", "\n\n"]  # Stop sequences
                        },
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        generated_text = data.get('text', data.get('response', ''))
                        
                        if generated_text and generated_text.strip():
                            # Clean up the response
                            generated_text = generated_text.strip()
                            
                            # Remove any accidental role labels
                            for prefix in ["Bee:", "Assistant:", "AI:"]:
                                if generated_text.startswith(prefix):
                                    generated_text = generated_text[len(prefix):].strip()
                            
                            # Apply sentiment-based enhancements
                            enhanced_response = BeePromptConfig.enhance_response(
                                generated_text, 
                                sentiment_category
                            )
                            
                            logger.info(f"Generated response via {endpoint['name']}: {enhanced_response[:100]}...")
                            return enhanced_response
                    else:
                        last_error = f"{endpoint['name']} returned status {response.status_code}"
                        logger.warning(f"LLM endpoint {endpoint['name']} failed: {last_error}")
                        continue
                        
            except Exception as e:
                last_error = f"{endpoint['name']} error: {str(e)}"
                logger.error(f"Error calling {endpoint['name']}: {e}")
                continue
        
        # If all LLM calls fail, use enhanced fallback
        logger.warning(f"All LLM endpoints failed. Last error: {last_error}")
        return generate_enhanced_fallback_response(message, sentiment_category, tools_used)
        
    except Exception as e:
        logger.error(f"Error in generate_bee_response: {str(e)}")
        return generate_enhanced_fallback_response(message, sentiment_category, tools_used)


def generate_enhanced_fallback_response(message: str, sentiment: str, tools_used: List[Dict[str, Any]]) -> str:
    """Generate an enhanced fallback response when LLM is unavailable"""
    
    base_responses = {
        "greeting": [
            "Hi! I'm Bee. How can I help?",
            "Hi there! I'm B., ready to assist you with STING's secure features.",
            "Welcome! I'm Bee, here to help you navigate STING securely."
        ],
        "help": [
            "I'd be happy to help you with STING. What specific feature would you like to know about - authentication, messaging, or AI models?",
            "I'm here to assist! You can ask me about secure messaging, passkey setup, or any STING feature.",
            "Let me guide you through STING's capabilities. What would you like to explore?"
        ],
        "error": [
            "I'm experiencing a temporary connection issue, but I'm still here to help. Could you tell me more about what you're trying to do?",
            "While I'm having trouble accessing my full capabilities, I can still guide you. What specific task are you working on?",
            "I'm currently in limited mode, but I'll do my best to assist. What's your main concern?"
        ],
        "security": [
            "STING takes security seriously with end-to-end encryption, passkey authentication, and local AI models. What security aspect interests you?",
            "Your security is our priority. We use military-grade encryption and never send data to external services. How can I help with security?",
            "All STING communications are encrypted and models run locally. What security feature would you like to know more about?"
        ],
        "technical": [
            "STING uses a microservices architecture with Docker, Kratos authentication, and multiple AI models. What technical detail would you like to explore?",
            "Our platform runs on React, Flask, and PostgreSQL with local LLM deployment. What technical aspect interests you?",
            "We support REST APIs, WebAuthn, and multiple language models. Which technical feature can I explain?"
        ]
    }
    
    # Detect intent from message
    message_lower = message.lower()
    
    if any(word in message_lower for word in ["hello", "hi", "hey", "greet"]):
        response_type = "greeting"
    elif any(word in message_lower for word in ["help", "assist", "guide", "how"]):
        response_type = "help"
    elif any(word in message_lower for word in ["security", "encrypt", "passkey", "auth"]):
        response_type = "security"
    elif any(word in message_lower for word in ["api", "docker", "technical", "config"]):
        response_type = "technical"
    else:
        response_type = "error"
    
    # Select a response
    import random
    base_response = random.choice(base_responses[response_type])
    
    # Apply sentiment adjustments
    sentiment_prefixes = {
        "frustrated": "I understand this might be frustrating. ",
        "confused": "Let me clarify this for you. ",
        "urgent": "I'll help you quickly. ",
        "satisfied": "Great to hear from you! "
    }
    
    prefix = sentiment_prefixes.get(sentiment, "")
    
    # Add tool context if available
    if tools_used:
        tool_names = [tool['name'] for tool in tools_used]
        base_response += f" I've also checked {', '.join(tool_names)} for you."
    
    return prefix + base_response


def summarize_tool_data(data: Any, max_length: int = 200) -> str:
    """Intelligently summarize tool execution data"""
    if isinstance(data, dict):
        # For dictionaries, show key info
        items = []
        for key, value in list(data.items())[:5]:  # First 5 items
            if isinstance(value, (str, int, float, bool)):
                items.append(f"{key}: {str(value)[:50]}")
            elif isinstance(value, list):
                items.append(f"{key}: [{len(value)} items]")
            elif isinstance(value, dict):
                items.append(f"{key}: {{...}}")
        return ", ".join(items)
    elif isinstance(data, list):
        return f"[{len(data)} items]"
    else:
        return str(data)[:max_length]