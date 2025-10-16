"""
Chat Service for STING
Provides conversation management and integration with LLM models
"""

import os
import time
import logging
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from llama_index.core.llms import LLM
# Import LlamaCPP conditionally to avoid dependency issues
try:
    from llama_index.llms.llama_cpp import LlamaCPP
    LLAMA_CPP_AVAILABLE = True
except ImportError:
    LLAMA_CPP_AVAILABLE = False
    class LlamaCPP:
        """Stub class when llama-cpp is not available"""
        pass

from llama_index.core.tools import BaseTool, FunctionTool
from llama_index.core.agent import ReActAgent

logger = logging.getLogger("chat-service")

class STINGChatService:
    """
    Chat service that manages conversations and tool integrations
    for the STING platform.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the chat service with configuration
        
        Args:
            config: Configuration dictionary from STING's config.yml
        """
        self.config = config
        self.chat_config = config.get("chatbot", {})
        self.conversations = {}  # User conversations storage
        self.tools = self._initialize_tools()
        self.llm = self._initialize_llm()
        self.agent = self._initialize_agent()
        
        # Set up context window size (number of messages to retain)
        self.context_window = self.chat_config.get("context_window", 10)
        
        logger.info(f"Chat service initialized with {len(self.tools)} tools")
    
    def _initialize_llm(self):
        """Initialize the language model based on configuration"""
        model_name = self.chat_config.get("model", "llama3")
        model_config = self.config.get("llm_service", {}).get("models", {}).get(model_name, {})
        
        # Always use the gateway method in this implementation
        # Use endpoint from environment or config, fall back to Docker service name
        gateway_endpoint = os.environ.get("LLM_GATEWAY_URL", "http://llm-gateway:8080")
        endpoint = f"{gateway_endpoint}/generate"
        
        logger.info(f"Initializing LLM for model: {model_name} with endpoint: {endpoint}")
        
        # Using our new simplified GatewayLLM class
        return GatewayLLM(
            endpoint=endpoint,
            model_name=model_name
        )
    
    def _initialize_tools(self) -> List[BaseTool]:
        """Initialize available tools for the agent"""
        tools = []
        
        if not self.chat_config.get("tools", {}).get("enabled", True):
            logger.info("Tools are disabled in configuration")
            return tools
        
        allowed_tools = self.chat_config.get("tools", {}).get("allowed_tools", [])
        
        # Example: Search tool
        if "search" in allowed_tools:
            tools.append(FunctionTool.from_defaults(
                name="search_documents",
                description="Search through corporate documents and knowledge base",
                fn=self._search_documents
            ))
        
        # Example: Summarize tool
        if "summarize" in allowed_tools:
            tools.append(FunctionTool.from_defaults(
                name="summarize_text",
                description="Summarize long text content",
                fn=self._summarize_text
            ))
            
        # Additional tools can be added here
        
        return tools
    
    def _initialize_agent(self):
        """Initialize the chatbot agent with tools"""
        # In this simplified implementation, we're not using agents
        # We're just using the LLM directly for simplicity
        logger.info("Skipping agent initialization, will use direct LLM instead")
        return None
    
    def process_message(self, user_id: str, message: str) -> Dict[str, Any]:
        """
        Process a user message and return a response
        
        Args:
            user_id: Unique identifier for the user
            message: User's message content
            
        Returns:
            Dictionary containing response and metadata
        """
        # Get or create user conversation
        if user_id not in self.conversations:
            self.conversations[user_id] = {
                "messages": [],
                "created_at": datetime.now().isoformat(),
                "last_active": datetime.now().isoformat()
            }
            
        # Add message to conversation history
        self.conversations[user_id]["messages"].append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Update last active timestamp
        self.conversations[user_id]["last_active"] = datetime.now().isoformat()
        
        # Limit conversation history to context window
        if len(self.conversations[user_id]["messages"]) > self.context_window * 2:
            self.conversations[user_id]["messages"] = self.conversations[user_id]["messages"][-self.context_window*2:]
        
        # Prepare the conversation context
        conversation_history = ""
        for msg in self.conversations[user_id]["messages"][-self.context_window*2:]:
            role_name = "User" if msg["role"] == "user" else "Bee"
            conversation_history += f"{role_name}: {msg['content']}\n"
        
        # Process with agent
        try:
            start_time = time.time()
            
            # If there are no tools or tools are disabled or no agent, use direct message passing
            if not self.tools or not self.chat_config.get("tools", {}).get("enabled", True) or self.agent is None:
                logger.info("Using direct LLM for processing (no tools or no agent)")
                llm_response = self._process_with_llm(conversation_history, message)
                response_text = llm_response
                tools_used = []
            else:
                # Process with agent that has access to tools
                logger.info("Processing with agent and tools")
                try:
                    if hasattr(self.agent, 'chat'):
                        # ReAct agent
                        agent_response = self.agent.chat(message)
                        response_text = str(agent_response)
                    else:
                        # LangChain agent
                        agent_response = self.agent.run(message)
                        response_text = str(agent_response)
                    
                    # Extract tools used (implementation depends on agent response format)
                    tools_used = self._extract_tools_from_response(agent_response)
                except Exception as agent_error:
                    logger.error(f"Error with agent processing: {agent_error}, falling back to direct LLM")
                    llm_response = self._process_with_llm(conversation_history, message)
                    response_text = llm_response
                    tools_used = []
            
            processing_time = time.time() - start_time
            
            # Add response to conversation history
            self.conversations[user_id]["messages"].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now().isoformat(),
                "tools_used": tools_used
            })
            
            # Return the response
            return {
                "response": response_text,
                "conversation_id": user_id,
                "tools_used": tools_used,
                "processing_time": processing_time,
                "filtered": False,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.exception(f"Error processing message: {str(e)}")
            return {
                "response": "I'm sorry, I encountered an error processing your request.",
                "error": str(e),
                "conversation_id": user_id,
                "filtered": False,
                "timestamp": datetime.now().isoformat()
            }
    
    def _process_with_llm(self, conversation_history: str, latest_message: str) -> str:
        """Process a message with the LLM without using tools"""
        # Construct prompt with conversation history and system prompt
        system_prompt = self.chat_config.get("default_system_prompt", 
            "You are Bee, a helpful AI assistant for the STING platform.")
        
        full_prompt = f"{system_prompt}\n\nConversation history:\n{conversation_history}\n\nUser: {latest_message}\nBee:"
        
        # Call the LLM directly
        response = self.llm.complete(full_prompt)
        return response.text
    
    def _extract_tools_from_response(self, agent_response) -> List[Dict[str, Any]]:
        """Extract tools used from agent response"""
        # This implementation depends on the agent's response format
        # We need to handle different agent types
        tools_used = []
        
        try:
            # For ReActAgent with sources
            if hasattr(agent_response, "sources") and agent_response.sources:
                for source in agent_response.sources:
                    tools_used.append({
                        "name": source.get("tool", "unknown"),
                        "input": source.get("input", ""),
                        "output": source.get("output", "")
                    })
                return tools_used
                
            # For LangChain agent log
            # This won't work perfectly but it's a reasonable effort
            if hasattr(agent_response, "log") or (isinstance(agent_response, str) and "Action:" in agent_response):
                log = agent_response.log if hasattr(agent_response, "log") else agent_response
                
                # Very simple parsing - in real implementation this would be more sophisticated
                import re
                tool_matches = re.findall(r"Action:\s*(\w+)\s*Action Input:\s*([^\n]+)", str(log))
                
                for name, input_text in tool_matches:
                    tools_used.append({
                        "name": name,
                        "input": input_text,
                        "output": "Output not captured" # We don't have a good way to get this
                    })
                    
            # For LangChain AgentAction objects
            if hasattr(agent_response, "actions") and isinstance(agent_response.actions, list):
                for action in agent_response.actions:
                    tools_used.append({
                        "name": action.tool,
                        "input": action.tool_input,
                        "output": action.log if hasattr(action, "log") else "Output not captured"
                    })
                    
        except Exception as e:
            logger.warning(f"Error extracting tools from response: {e}")
            
        return tools_used
    
    # Tool implementations
    
    def _search_documents(self, query: str) -> str:
        """
        Search through documents with the given query
        This is a placeholder implementation
        """
        logger.info(f"Searching documents for: {query}")
        # In a real implementation, this would connect to a vector database or search service
        return f"Found 3 results for '{query}'. [Placeholder implementation]"
    
    def _summarize_text(self, text: str) -> str:
        """
        Summarize long text
        This is a placeholder implementation
        """
        logger.info(f"Summarizing text of length {len(text)}")
        # In a real implementation, this would use an LLM to summarize
        return f"Summary of text ({len(text)} chars): This is a placeholder summary."
    
    def get_conversation_history(self, user_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get conversation history for a user"""
        if user_id not in self.conversations:
            return []
            
        messages = self.conversations[user_id]["messages"]
        if limit and limit > 0:
            messages = messages[-limit:]
            
        return messages
    
    def clear_conversation(self, user_id: str) -> bool:
        """Clear conversation history for a user"""
        if user_id in self.conversations:
            self.conversations[user_id]["messages"] = []
            return True
        return False


class DirectLLM:
    """A simple, direct LLM implementation that doesn't use complex frameworks"""
    
    def __init__(
        self,
        endpoint: str = "http://llm-gateway:8080/generate",
        model_name: str = "llama3",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ):
        """
        Initialize the Direct LLM
        
        Args:
            endpoint: URL of the LLM Gateway generate endpoint
            model_name: Name of the model to use (llama3, phi3, zephyr)
            temperature: Temperature parameter for generation
            max_tokens: Maximum number of tokens to generate
        """
        self.endpoint = endpoint
        self.model_name = self._get_actual_model_name(model_name)
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        import httpx
        self.client = httpx.Client(timeout=60.0)
        
    def _get_actual_model_name(self, model_name: str) -> str:
        """
        Maps the model name to the actual model name used in the API
        The config uses 'llama3' but the API might use 'meta-llama/Llama-3-8b' or just 'llama-3-8b'
        This is a temporary solution until we fix the configuration
        """
        model_map = {
            "llama3": "llama-3-8b",
            "phi3": "phi-3-medium-128k-instruct",
            "zephyr": "zephyr-7b"
        }
        
        return model_map.get(model_name, model_name)
    
    def call(self, prompt: str, **kwargs) -> str:
        """
        Call the LLM with the given prompt
        
        Args:
            prompt: The prompt to send to the LLM
            **kwargs: Additional arguments to pass to the API
            
        Returns:
            Generated text as string
        """
        import httpx
        import time
        
        # Number of retries
        retries = 3
        delay = 2  # seconds
        
        for attempt in range(retries):
            try:
                # Set up parameters - Fixed to use the format expected by the LLM gateway
                params = {
                    "message": prompt,
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                    "temperature": kwargs.get("temperature", self.temperature)
                }
                
                # Make request to gateway
                logger.info(f"Calling LLM Gateway at {self.endpoint} with model")
                response = self.client.post(
                    self.endpoint,
                    json=params
                )
                
                if response.status_code != 200:
                    error_msg = f"Error from LLM Gateway: {response.text}"
                    logger.error(error_msg)
                    if "Failed to load model" in response.text and attempt < retries - 1:
                        logger.info(f"Model loading error, retrying in {delay} seconds (attempt {attempt+1}/{retries})")
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
                        continue
                    raise ValueError(error_msg)
                    
                result = response.json()
                
                # Return the generated text
                logger.info("Successfully received response from LLM Gateway")
                return result.get("response", "")
                
            except httpx.RequestError as e:
                logger.error(f"Error calling LLM Gateway: {str(e)}")
                if attempt < retries - 1:
                    logger.info(f"Connection error, retrying in {delay} seconds (attempt {attempt+1}/{retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    return "I apologize, but I'm having trouble connecting to the language model service."
            except Exception as e:
                logger.exception(f"Unexpected error in DirectLLM: {str(e)}")
                if attempt < retries - 1:
                    logger.info(f"General error, retrying in {delay} seconds (attempt {attempt+1}/{retries})")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    return "I apologize, but an unexpected error occurred."
        
        return "I apologize, but I was unable to generate a response after multiple attempts."


class GatewayLLM:
    """Simplified LLM class for STING API - no longer uses LlamaIndex base class"""
    
    def __init__(
        self,
        endpoint: str = "http://llm-gateway:8080/generate",
        model_name: str = "llama3",
        temperature: float = 0.7,
        max_tokens: int = 1024,
    ):
        self.endpoint_url = endpoint
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Create a direct LLM
        self._direct_llm = DirectLLM(
            endpoint=endpoint,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    def complete(self, prompt: str, **kwargs) -> Any:
        """
        Complete a prompt using the LLM Gateway
        
        Args:
            prompt: The prompt to complete
            **kwargs: Additional arguments to pass to the API
            
        Returns:
            CompletionResponse object with generated text
        """
        from llama_index.core.llms import CompletionResponse
        
        try:
            # Call the model directly
            result = self._direct_llm.call(prompt, **kwargs)
            
            # Create completion response
            return CompletionResponse(
                text=result,
                raw={"response": result}
            )
            
        except Exception as e:
            logger.exception(f"Unexpected error in GatewayLLM: {str(e)}")
            return CompletionResponse(
                text="I apologize, but an unexpected error occurred.",
                raw={"error": str(e)}
            )
    
    def metadata(self) -> Dict[str, Any]:
        """Get LLM metadata"""
        return {
            "model_name": self.model_name,
            "endpoint": self.endpoint_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "type": "gateway"
        }