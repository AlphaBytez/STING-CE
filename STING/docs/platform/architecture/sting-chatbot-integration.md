# STING Chatbot Integration Guide

This document provides an overview of the current LLM infrastructure in STING and recommendations for implementing a robust, functional chatbot integration that aligns with STING's security and flexibility requirements.

## Current LLM Infrastructure

### Architecture Overview

STING's current LLM implementation follows a microservices architecture with the following components:

1. **LLM Gateway Service**
   - Entry point for all LLM interactions
   - Routes requests to appropriate model services
   - Implements content filtering (toxicity, data leakage)
   - Located in `/llm_service/gateway/`
   - Exposes a `/generate` endpoint for message processing

2. **Model Services**
   - Individual model implementations (Llama 3, Phi-3, Zephyr)
   - Each runs in a separate container
   - Handles prompt formatting based on model type
   - Configurable parameters (temperature, token limits)
   - Located in `/llm_service/`

3. **Content Filtering System**
   - Toxicity filter to detect harmful content
   - Data leakage filter to prevent exposure of sensitive information
   - Extensible with custom filters
   - Located in `/llm_service/filtering/`

4. **Frontend Chat Components**
   - Simple chat interface in `/frontend/src/components/chat/`
   - Basic message display and input components
   - Connects to LLM Gateway via REST API

5. **Rasa Integration (Partial)**
   - Basic Rasa setup for conversational AI
   - Action definitions for routing queries to LLM models
   - Located in `/rasa/`

### Data Flow

The current implementation follows this flow:

1. User inputs a message in the frontend chat interface
2. Message is sent to the LLM Gateway's `/generate` endpoint
3. Gateway selects the appropriate model and forwards the request
4. Model service formats the prompt according to model requirements
5. Model generates text response
6. Response passes through content filters
7. Filtered or unfiltered response is returned to frontend
8. Frontend displays the response in the chat UI

### Strengths of Current Implementation

- **Modular Design**: Separation of concerns between gateway, models, and filtering
- **Flexible Model Support**: Multiple models available (Llama 3, Phi-3, Zephyr)
- **Security-Focused**: Content filtering to prevent harmful or sensitive outputs
- **Configuration-Driven**: Easy to adjust models and parameters via config files

### Limitations in Current Implementation

- **Basic Conversation Management**: No built-in conversation history or context management
- **Limited Tool Integration**: No mechanism for the LLM to use external tools/actions
- **Simple UI**: Basic chat interface without advanced features
- **No Memory**: Each interaction is stateless, no persistent memory between requests
- **Limited Routing Logic**: Simple model selection without sophisticated query analysis

## Recommended Chatbot Integration

Based on STING's architecture and requirements, we recommend enhancing the system with a modern, flexible chatbot integration that preserves security while adding powerful functionality.

### Recommended Approach: LlamaIndex with Optional LangChain Integration

We recommend adopting LlamaIndex as the primary framework for chatbot development with optional LangChain integration for more complex agent behaviors. This approach offers several advantages:

1. **Efficient Data Retrieval**: LlamaIndex excels at indexing and retrieving relevant information
2. **Flexible Agent Development**: Support for building tools and agents that can interact with STING's services
3. **Security Compatibility**: Works well with STING's existing content filtering system
4. **Modern Implementation**: Represents current best practices in LLM application development
5. **Open Source**: Fully open source with active community support
6. **Minimal External Dependencies**: Can be deployed within STING's containerized environment

### Implementation Plan

#### Phase 1: Enhanced Chat Backend

1. **Install Required Dependencies**
   ```python
   # In llm_service/requirements.common.txt
   llama-index>=0.10.0
   langchain>=0.1.0  # Optional for more complex agent behaviors
   ```

2. **Create Chat Service Component**
   - Implement a new service in `/llm_service/chat/` to handle conversations
   - Use LlamaIndex for conversation management and context handling
   - Integrate with existing LLM Gateway for model access

3. **Implement Conversation Context Management**
   - Store conversation history for improved contextual responses
   - Implement memory mechanisms to maintain state between messages
   - Configure context window size based on model capabilities

4. **Build Tool Integration**
   - Create a tool registry for LLM to access system capabilities
   - Implement basic tools for data retrieval, summarization, etc.
   - Add hooks for admin-defined custom tools

#### Phase 2: Admin Configurability

1. **Configuration Extensions**
   - Extend `config.yml` to include chatbot-specific settings
   - Add tool configurations for admin customization
   - Example configuration extension:

   ```yaml
   # Add to config.yml
   chatbot:
     enabled: true
     name: "Bee"
     context_window: 10  # Number of messages to retain as context
     default_system_prompt: "You are Bee, a helpful assistant..."
     tools:
       enabled: true
       allow_custom: true
       allowed_tools:
         - search
         - summarize
         - analyze
     security:
       require_authentication: true
       log_conversations: true
       content_filter_level: "strict"  # strict, moderate, minimal
   ```

2. **Admin Interface**
   - Add configuration panel for chatbot settings
   - Enable creation and management of custom tools
   - Provide conversation monitoring capabilities

#### Phase 3: Enhanced Frontend

1. **Improved Chat UI**
   - Enhance `/frontend/src/components/chat/` components
   - Add support for different message types (text, actions, system)
   - Implement loading indicators and error handling

2. **Tool Feedback Display**
   - Show when tools are being used by the chatbot
   - Display results in user-friendly formats
   - Allow user feedback on tool usage

### Code Examples

#### Chat Service Implementation

```python
# llm_service/chat/chat_service.py
from typing import List, Dict, Any
from llama_index import VectorStoreIndex, SimpleDirectoryReader
from llama_index.llms import OpenAI
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.agent.openai import OpenAIAgent
import logging

logger = logging.getLogger("chat-service")

class STINGChatService:
    def __init__(self, config):
        self.config = config
        self.context = {}
        self.llm = OpenAI(model="gpt-4") # Can be configured to use local models
        self.tools = self._initialize_tools()
        self.agent = self._initialize_agent()
        
    def _initialize_tools(self):
        """Initialize available tools for the agent"""
        tools = []
        
        # Example tool: search documents
        if "search" in self.config["chatbot"]["tools"]["allowed_tools"]:
            # This could connect to your document store or database
            tools.append(QueryEngineTool(
                name="search_documents",
                description="Search through corporate documents and policies",
                query_engine=None  # Would be initialized with actual engine
            ))
            
        # Add other tools as needed
        return tools
    
    def _initialize_agent(self):
        """Initialize the chatbot agent with tools"""
        agent = OpenAIAgent.from_tools(
            self.tools,
            llm=self.llm,
            system_prompt=self.config["chatbot"]["default_system_prompt"],
            verbose=True
        )
        return agent
    
    def process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """Process a user message and return a response"""
        # Get or create user context
        if user_id not in self.context:
            self.context[user_id] = []
            
        # Add message to context
        self.context[user_id].append({"role": "user", "content": message})
        
        # Limit context window
        context_window = self.config["chatbot"]["context_window"]
        if len(self.context[user_id]) > context_window * 2:  # *2 for pairs of messages
            self.context[user_id] = self.context[user_id][-context_window*2:]
        
        try:
            # Get response from agent
            response = self.agent.chat(message)
            
            # Add response to context
            self.context[user_id].append({"role": "assistant", "content": str(response)})
            
            return {
                "response": str(response),
                "tools_used": [],  # Would include tools if used
                "filtered": False
            }
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {
                "response": "I'm sorry, I encountered an error processing your request.",
                "error": str(e),
                "filtered": False
            }
```

#### Gateway Integration

```python
# Example addition to gateway/app.py
from ..chat.chat_service import STINGChatService

# Initialize chat service
chat_service = STINGChatService(config)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Chat endpoint that maintains conversation context"""
    user_id = request.user_id
    message = request.message
    
    # Process through chat service
    result = chat_service.process_message(user_id, message)
    
    # Apply content filters if configured
    if config.get("filtering", {}).get("chat_enabled", True):
        response_text = result["response"]
        is_toxic, toxic_reason = toxicity_filter.check(response_text)
        has_leakage, leakage_reason = data_leakage_filter.check(response_text)
        
        if is_toxic or has_leakage:
            filter_reason = toxic_reason or leakage_reason
            result["filtered"] = True
            result["filter_reason"] = filter_reason
            result["response"] = "I apologize, but I cannot provide a response to that query as it may contain sensitive information or violate content policies."
    
    return ChatResponse(**result)
```

#### Frontend Enhancement

```jsx
// Enhanced Chat.jsx component
import React, { useState, useRef, useEffect } from 'react';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import ToolUsageIndicator from './ToolUsageIndicator';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [activeTool, setActiveTool] = useState(null);
  const messagesEndRef = useRef(null);
  
  // Get user ID from auth context
  const userId = "user123"; // Replace with actual user ID from auth
  
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = (message) => {
    if (!message.trim()) return;

    const userMessage = {
      id: Date.now(),
      sender: "User",
      text: message,
      timestamp: new Date(),
      status: 'sent'
    };

    setMessages(prev => [...prev, userMessage]);
    setNewMessage("");
    setIsTyping(true);
    
    const llmUrl = process.env.REACT_APP_LLM_GATEWAY_URL || 'http://localhost:8080';
    
    // Use enhanced chat endpoint instead of generate
    fetch(`${llmUrl}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ 
        message,
        user_id: userId
      }),
    })
      .then(async res => {
        if (!res.ok) throw new Error('Chat request failed');
        const data = await res.json();
        
        // Handle tool usage if any
        if (data.tools_used && data.tools_used.length > 0) {
          setActiveTool(data.tools_used[0]);
          // Add tool usage messages
          const toolMessage = {
            id: Date.now() + 0.5,
            sender: 'System',
            text: `Using tool: ${data.tools_used[0].name}`,
            timestamp: new Date(),
            status: 'tool',
            tool: data.tools_used[0]
          };
          setMessages(prev => [...prev, toolMessage]);
        }
        
        const botMessage = {
          id: Date.now() + 1,
          sender: 'Bee',
          text: data.response,
          timestamp: new Date(),
          status: data.filtered ? 'filtered' : 'received',
          filter_reason: data.filter_reason
        };
        setMessages(prev => [...prev, botMessage]);
        setActiveTool(null);
      })
      .catch(err => {
        console.error('Chat error:', err);
        const errorMsg = {
          id: Date.now() + 1,
          sender: 'Bee',
          text: 'Error processing your message',
          timestamp: new Date(),
          status: 'error',
        };
        setMessages(prev => [...prev, errorMsg]);
      })
      .finally(() => setIsTyping(false));
  };

  return (
    <div className="p-6 h-full flex flex-col">
      <div className="bg-white p-4 rounded-t-lg shadow-sm">
        <h2 className="text-2xl font-bold">Bee Chat</h2>
        {isTyping && (
          <p className="text-sm text-gray-600">Bee is typing...</p>
        )}
        {activeTool && (
          <ToolUsageIndicator tool={activeTool} />
        )}
      </div>
      
      <div className="flex-grow border rounded-lg overflow-y-auto bg-gray-100 p-4">
        {messages.map((msg) => (
          <ChatMessage key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        value={newMessage}
        onChange={(e) => setNewMessage(e.target.value)}
        onSend={() => sendMessage(newMessage)}
      />
    </div>
  );
};

export default Chat;
```

### Advanced Features for Future Consideration

1. **Document Retrieval and RAG**
   - Use LlamaIndex's efficient document retrieval capabilities
   - Implement Retrieval-Augmented Generation for grounding responses in company data
   - Help reduce hallucinations and improve accuracy

2. **Multi-Modal Support**
   - Add capabilities to process and respond to images
   - Implement file upload and processing features

3. **Structured Output**
   - Enable the generation of structured data (JSON, CSV)
   - Support for charts, graphs, and other visualizations

4. **Knowledge Graph Integration**
   - Build knowledge graphs from corporate data
   - Enable more sophisticated reasoning based on entity relationships

5. **Fine-Tuning Workflow**
   - Process for fine-tuning models on company-specific data
   - Feedback mechanism for continuous improvement

## Alternative Frameworks Considered

While we recommend LlamaIndex with optional LangChain integration, we also evaluated several alternatives:

1. **Rasa (Current Partial Implementation)**
   - **Pros**: Strong NLU capabilities, well-established
   - **Cons**: More complex to set up, less integrated with modern LLMs

2. **Botpress**
   - **Pros**: Visual builder, good for non-technical users
   - **Cons**: Less flexibility for deep customization

3. **Haystack**
   - **Pros**: Good for search and QA applications
   - **Cons**: Less focused on agent behaviors than LlamaIndex/LangChain

4. **AutoGPT/BabyAGI**
   - **Pros**: Advanced autonomous capabilities
   - **Cons**: Excessive complexity for most use cases, less stable

5. **Custom Implementation**
   - **Pros**: Complete control over all aspects
   - **Cons**: Requires significant development effort

The LlamaIndex recommendation balances flexibility, security, and implementation effort for STING's needs.

## Conclusion

Enhancing STING with a robust chatbot implementation based on LlamaIndex would significantly improve the platform's capabilities while maintaining the security and flexibility that makes STING valuable. The recommended approach builds on the existing LLM infrastructure while adding conversational intelligence and tool usage capabilities.

By implementing this integration in phases, STING can quickly deliver enhanced chat capabilities to users while continuing to evolve the system's capabilities over time. The modular approach ensures that administrators can control the feature set and security parameters to match their organization's needs.