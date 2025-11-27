import axios from 'axios';

// Bee Chatbot API client for chat history
// Note: Using chatbot service instead of messaging service because
// messaging service uses in-memory storage, while chatbot uses PostgreSQL
const BEE_API_URL = window.env?.REACT_APP_BEE_API_URL ||
                    process.env.REACT_APP_BEE_API_URL ||
                    '/api/bee';  // Use proxy route to chatbot

const messagingClient = axios.create({
    baseURL: BEE_API_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Note: Authentication is handled via HttpOnly cookies
// The ory_kratos_session cookie is automatically included by the browser
// and passed to the backend via Nginx proxy_set_header Cookie $http_cookie
// No need for JavaScript-based token extraction since HttpOnly cookies
// cannot be accessed by document.cookie (this is a security feature)

// Add logging for debug purposes
if (process.env.NODE_ENV === 'development' || window.env?.NODE_ENV === 'development') {
    console.log('Bee API URL (for chat history):', BEE_API_URL);
    
    messagingClient.interceptors.response.use(
        response => {
            console.log('Messaging API response:', response.status, response.config.url);
            return response;
        },
        error => {
            console.error('Messaging API error:', error.message, error.config?.url);
            if (error.response) {
                console.error('Response data:', error.response.data);
                console.error('Response status:', error.response.status);
            }
            return Promise.reject(error);
        }
    );
}

// Chat History API functions
export const chatHistoryApi = {
    // Get chat conversation history for a user
    getChatHistory: async (userId, limit = 50, offset = 0) => {
        const response = await messagingClient.get(`/users/${userId}/conversations?limit=${limit}&offset=${offset}`);
        return response.data;
    },

    // Get messages in a specific conversation
    getConversationMessages: async (conversationId, limit = 100, offset = 0) => {
        const response = await messagingClient.get(`/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`);
        return response.data;
    },

    // Save a chat message
    saveChatMessage: async (conversationId, messageData) => {
        // Chatbot saves messages automatically during chat, this is a no-op for now
        // Messages are saved via the /chat endpoint in bee_server.py
        console.log('saveChatMessage called - messages are automatically saved during chat');
        return { success: true };
    },

    // Create a new chat conversation
    createChatConversation: async (userId, title = null) => {
        // Conversations are created automatically on first message in bee_server.py
        // Return a temporary ID that will be replaced when first message is sent
        console.log('createChatConversation called - conversation will be created on first message');
        return {
            conversation_id: `temp_${Date.now()}`,
            title: title || 'New Chat',
            created_at: new Date().toISOString()
        };
    },

    // Delete/archive a conversation (if needed later)
    archiveConversation: async (conversationId) => {
        // This would need to be implemented in the backend
        console.warn('archiveConversation not yet implemented in bee_server');
        return { success: false };
    }
};

// Health check
export const messagingHealthApi = {
    checkHealth: async () => {
        const response = await messagingClient.get('/health');
        return response.data;
    }
};

export default messagingClient;