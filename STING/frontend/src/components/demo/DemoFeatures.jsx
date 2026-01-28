import React, { useState } from 'react';

const DemoFeatures = () => {
  const [activeFeature, setActiveFeature] = useState(null);

  const features = [
    {
      id: 'honey-jars',
      icon: '🍯',
      title: 'Honey Jars',
      shortDesc: 'Containerized knowledge bases',
      description: 'Create and manage knowledge bases with ChromaDB vector search. Store documents, configure embeddings, and build searchable knowledge repositories.',
      capabilities: [
        'Vector search with ChromaDB',
        'Multiple embedding models',
        'Document upload and indexing',
        'Chunking strategies',
      ],
    },
    {
      id: 'bee-chat',
      icon: '🐝',
      title: 'Bee AI Assistant',
      shortDesc: 'Conversational AI for your documents',
      description: 'Chat with AI about your knowledge base. Bee connects to your Honey Jars to provide contextual, intelligent responses.',
      capabilities: [
        'RAG-powered conversations',
        'Context-aware responses',
        'Multiple LLM providers',
        'Conversation history',
      ],
    },
    {
      id: 'security',
      icon: '🔐',
      title: 'Enterprise Auth',
      shortDesc: 'Ory Kratos with MFA',
      description: 'Secure authentication with Ory Kratos. Support for passwords, WebAuthn/passkeys, and TOTP multi-factor authentication.',
      capabilities: [
        'WebAuthn/passkeys',
        'TOTP MFA',
        'Session management',
        'Self-service flows',
      ],
    },
    {
      id: 'pii-detection',
      icon: '🛡️',
      title: 'PII Protection',
      shortDesc: 'Automatic sensitive data detection',
      description: 'Automatic detection and protection of personally identifiable information. Built-in PII scrubber for safe AI interactions.',
      capabilities: [
        'Auto-detection',
        'Multiple PII types',
        'Configurable actions',
        'Audit logging',
      ],
    },
  ];

  const styles = {
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
      gap: '24px',
    },
    card: {
      background: 'rgba(30, 41, 59, 0.6)',
      border: '1px solid #334155',
      borderRadius: '12px',
      padding: '24px',
      cursor: 'pointer',
      transition: 'all 0.2s',
    },
    cardActive: {
      border: '1px solid #f59e0b',
      background: 'rgba(245, 158, 11, 0.1)',
    },
    icon: {
      fontSize: '36px',
      marginBottom: '12px',
    },
    title: {
      fontSize: '18px',
      fontWeight: '600',
      color: '#f8fafc',
      marginBottom: '4px',
    },
    shortDesc: {
      fontSize: '14px',
      color: '#94a3b8',
      marginBottom: '16px',
    },
    description: {
      fontSize: '14px',
      color: '#cbd5e1',
      lineHeight: '1.6',
      marginBottom: '16px',
    },
    capabilities: {
      listStyle: 'none',
      padding: 0,
      margin: 0,
    },
    capability: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      fontSize: '13px',
      color: '#94a3b8',
      marginBottom: '8px',
    },
    checkmark: {
      color: '#22c55e',
      fontSize: '14px',
    },
  };

  return (
    <div>
      <div style={styles.grid}>
        {features.map((feature) => (
          <div
            key={feature.id}
            style={{
              ...styles.card,
              ...(activeFeature === feature.id ? styles.cardActive : {}),
            }}
            onClick={() => setActiveFeature(
              activeFeature === feature.id ? null : feature.id
            )}
          >
            <div style={styles.icon}>{feature.icon}</div>
            <h3 style={styles.title}>{feature.title}</h3>
            <p style={styles.shortDesc}>{feature.shortDesc}</p>

            {activeFeature === feature.id && (
              <div style={{ animation: 'fadeIn 0.2s ease-in' }}>
                <p style={styles.description}>{feature.description}</p>
                <ul style={styles.capabilities}>
                  {feature.capabilities.map((cap, idx) => (
                    <li key={idx} style={styles.capability}>
                      <span style={styles.checkmark}>✓</span>
                      {cap}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ))}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(-10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        div[style*="background: rgba(30, 41, 59, 0.6)"]:hover {
          background: rgba(30, 41, 59, 0.8) !important;
          transform: translateY(-2px);
        }
      `}</style>
    </div>
  );
};

export default DemoFeatures;
