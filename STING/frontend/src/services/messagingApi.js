import axios from 'axios';

// Messaging Service API client for chat history
const MESSAGING_API_URL = window.env?.REACT_APP_MESSAGING_API_URL || 
                         process.env.REACT_APP_MESSAGING_API_URL || 
                         '/api/messaging';  // Use proxy route instead of direct port

const messagingClient = axios.create({
    baseURL: MESSAGING_API_URL,
    withCredentials: true,
    headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
});

// Add logging for debug purposes
if (process.env.NODE_ENV === 'development' || window.env?.NODE_ENV === 'development') {
    console.log('Messaging API URL:', MESSAGING_API_URL);
    
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
        const response = await messagingClient.get(`/chat/history/${userId}?limit=${limit}&offset=${offset}`);
        return response.data;
    },

    // Get messages in a specific conversation
    getConversationMessages: async (conversationId, limit = 100, offset = 0) => {
        const response = await messagingClient.get(`/chat/conversations/${conversationId}/messages?limit=${limit}&offset=${offset}`);
        return response.data;
    },

    // Save a chat message
    saveChatMessage: async (conversationId, messageData) => {
        const response = await messagingClient.post(`/chat/conversations/${conversationId}/messages`, messageData);
        return response.data;
    },

    // Create a new chat conversation
    createChatConversation: async (userId, title = null) => {
        const response = await messagingClient.post('/chat/conversations', null, {
            params: { user_id: userId, title }
        });
        return response.data;
    },

    // Delete/archive a conversation (if needed later)
    archiveConversation: async (conversationId) => {
        // This would need to be implemented in the backend
        const response = await messagingClient.patch(`/chat/conversations/${conversationId}`, {
            is_archived: true
        });
        return response.data;
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