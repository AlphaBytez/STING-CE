import React, { useState, useEffect, useRef } from 'react';

const DemoChat = () => {
  const [messages, setMessages] = useState([
    {
      id: 1,
      role: 'bot',
      text: "👋 Hey there! Welcome to the STING demo! I'm Bee, and I'm excited to show you around. What would you like to explore first?",
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessage = {
      id: Date.now(),
      role: 'user',
      text: input,
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/bee/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message: input,
          conversation_id: 'demo-conversation'
        }),
      });

      const data = await response.json();

      if (data.success) {
        const botMessage = {
          id: Date.now() + 1,
          role: 'bot',
          text: data.response,
          timestamp: new Date(),
          demo_mode: true,
        };
        setMessages(prev => [...prev, botMessage]);
      } else {
        const errorMessage = {
          id: Date.now() + 1,
          role: 'bot',
          text: "I'm having trouble responding right now. In a live STING instance, I'd connect to your knowledge base. For now, let me connect you with our team! 📧 sales@stingassistant.com",
          timestamp: new Date(),
        };
        setMessages(prev => [...prev, errorMessage]);
      }
    } catch (error) {
      const errorMessage = {
        id: Date.now() + 1,
        role: 'bot',
        text: "I appreciate that question! In a real STING deployment, Bee would search your Honey Jars and give you contextual answers. Since this is a demo, I'm here to show you what's possible. Want to explore STING's features?",
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const suggestedQuestions = [
    "What can STING do?",
    "How does security work?",
    "What are Honey Jars?",
    "How much does it cost?",
  ];

  const handleSuggestedQuestion = (question) => {
    setInput(question);
  };

  const styles = {
    container: {
      background: 'rgba(30, 41, 59, 0.6)',
      border: '1px solid #334155',
      borderRadius: '16px',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      height: '600px',
    },
    header: {
      padding: '16px 20px',
      borderBottom: '1px solid #334155',
      background: 'rgba(15, 23, 42, 0.5)',
    },
    headerTitle: {
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
    },
    botIcon: {
      width: '36px',
      height: '36px',
      borderRadius: '50%',
      background: 'linear-gradient(135deg, #f59e0b, #d97706)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontSize: '18px',
    },
    botInfo: {
      display: 'flex',
      flexDirection: 'column',
    },
    botName: {
      fontSize: '16px',
      fontWeight: '600',
      color: '#f8fafc',
    },
    botStatus: {
      fontSize: '12px',
      color: '#22c55e',
      display: 'flex',
      alignItems: 'center',
      gap: '4px',
    },
    statusDot: {
      width: '6px',
      height: '6px',
      borderRadius: '50%',
      background: '#22c55e',
    },
    messagesContainer: {
      flex: 1,
      overflowY: 'auto',
      padding: '20px',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
    },
    message: {
      display: 'flex',
      flexDirection: 'column',
      maxWidth: '85%',
    },
    messageUser: {
      alignSelf: 'flex-end',
      alignItems: 'flex-end',
    },
    messageBot: {
      alignSelf: 'flex-start',
    },
    messageBubble: {
      padding: '12px 16px',
      borderRadius: '16px',
      fontSize: '14px',
      lineHeight: '1.5',
    },
    messageBubbleUser: {
      background: '#f59e0b',
      color: '#0f172a',
      borderBottomRightRadius: '4px',
    },
    messageBubbleBot: {
      background: '#334155',
      color: '#f8fafc',
      borderBottomLeftRadius: '4px',
    },
    demoBadge: {
      fontSize: '10px',
      color: '#f59e0b',
      marginTop: '4px',
      fontStyle: 'italic',
    },
    inputArea: {
      padding: '16px 20px',
      borderTop: '1px solid #334155',
      background: 'rgba(15, 23, 42, 0.5)',
    },
    inputForm: {
      display: 'flex',
      gap: '12px',
      marginBottom: '12px',
    },
    input: {
      flex: 1,
      padding: '12px 16px',
      borderRadius: '8px',
      border: '1px solid #475569',
      background: '#0f172a',
      color: '#f8fafc',
      fontSize: '14px',
      outline: 'none',
    },
    sendButton: {
      padding: '12px 20px',
      borderRadius: '8px',
      border: 'none',
      background: 'linear-gradient(135deg, #f59e0b, #d97706)',
      color: '#0f172a',
      fontWeight: '600',
      fontSize: '14px',
      cursor: 'pointer',
      opacity: loading ? 0.6 : 1,
    },
    suggestedQuestions: {
      display: 'flex',
      flexWrap: 'wrap',
      gap: '8px',
    },
    suggestedButton: {
      padding: '6px 12px',
      borderRadius: '16px',
      border: '1px solid #475569',
      background: 'transparent',
      color: '#94a3b8',
      fontSize: '12px',
      cursor: 'pointer',
      transition: 'all 0.2s',
    },
    emptyState: {
      flex: 1,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      color: '#64748b',
      fontSize: '14px',
    },
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerTitle}>
          <div style={styles.botIcon}>🐝</div>
          <div style={styles.botInfo}>
            <span style={styles.botName}>Bee</span>
            <span style={styles.botStatus}>
              <span style={styles.statusDot}></span>
              Demo Mode
            </span>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div style={styles.messagesContainer}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              ...styles.message,
              ...(msg.role === 'user' ? styles.messageUser : styles.messageBot),
            }}
          >
            <div
              style={{
                ...styles.messageBubble,
                ...(msg.role === 'user' ? styles.messageBubbleUser : styles.messageBubbleBot),
              }}
            >
              {msg.text.split('\n').map((line, i) => (
                <span key={i}>
                  {line}
                  {i < msg.text.split('\n').length - 1 && <br />}
                </span>
              ))}
            </div>
            {msg.demo_mode && (
              <span style={styles.demoBadge}>Demo mode - informational response</span>
            )}
          </div>
        ))}
        {loading && (
          <div style={{ ...styles.message, ...styles.messageBot }}>
            <div style={{ ...styles.messageBubble, ...styles.messageBubbleBot }}>
              Thinking...
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div style={styles.inputArea}>
        {messages.length <= 2 && (
          <div style={styles.suggestedQuestions}>
            {suggestedQuestions.map((q, i) => (
              <button
                key={i}
                style={styles.suggestedButton}
                onClick={() => handleSuggestedQuestion(q)}
              >
                {q}
              </button>
            ))}
          </div>
        )}
        <form style={styles.inputForm} onSubmit={handleSend}>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask me anything about STING..."
            style={styles.input}
            disabled={loading}
          />
          <button
            type="submit"
            style={styles.sendButton}
            disabled={loading || !input.trim()}
          >
            {loading ? '...' : 'Send'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default DemoChat;
