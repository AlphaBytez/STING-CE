import React, { useState, useEffect } from 'react';

const DemoTourGuide = ({ onClose }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [isVisible, setIsVisible] = useState(true);

  const steps = [
    {
      title: "Welcome to STING! 👋",
      content: "Let's take a quick tour of what STING can do. Click Next to continue, or Skip to explore on your own.",
      icon: "🐝",
    },
    {
      title: "🍯 Honey Jars",
      content: "Honey Jars are your private knowledge bases. Store documents, configure embeddings with ChromaDB, and build searchable repositories of your knowledge.",
      icon: "🍯",
      highlight: "sidebar-section",
    },
    {
      title: "🐝 Bee AI Assistant",
      content: "Bee connects to your Honey Jars to provide contextual, intelligent responses. Chat with AI about your documents in a secure, private environment.",
      icon: "🐝",
      highlight: "chat-section",
    },
    {
      title: "🔐 Enterprise Security",
      content: "STING runs entirely on your infrastructure. Ory Kratos handles authentication with support for WebAuthn/passkeys and TOTP MFA.",
      icon: "🔐",
    },
    {
      title: "🛡️ PII Protection",
      content: "Automatic detection and protection of personally identifiable information. STING can identify and mask sensitive data before AI processing.",
      icon: "🛡️",
    },
    {
      title: "Ready to Deploy? 🚀",
      content: "STING is open source and free to use! Get started by following the installation guide in our documentation.",
      icon: "✨",
      cta: true,
    },
  ];

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    } else {
      handleClose();
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleClose = () => {
    setIsVisible(false);
    setTimeout(onClose, 200);
  };

  const currentStepData = steps[currentStep];

  useEffect(() => {
    // Prevent body scroll when modal is open
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = 'auto';
    };
  }, []);

  if (!isVisible) return null;

  const styles = {
    overlay: {
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'rgba(0, 0, 0, 0.7)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      animation: 'fadeIn 0.2s ease-out',
    },
    modal: {
      background: 'linear-gradient(180deg, #1e293b 0%, #0f172a 100%)',
      border: '1px solid #334155',
      borderRadius: '16px',
      padding: '32px',
      maxWidth: '480px',
      width: '90%',
      position: 'relative',
      animation: 'slideUp 0.3s ease-out',
    },
    icon: {
      fontSize: '48px',
      textAlign: 'center',
      marginBottom: '16px',
    },
    title: {
      fontSize: '24px',
      fontWeight: '700',
      color: '#f8fafc',
      marginBottom: '12px',
      textAlign: 'center',
    },
    content: {
      fontSize: '16px',
      color: '#94a3b8',
      lineHeight: '1.6',
      textAlign: 'center',
      marginBottom: '24px',
    },
    progressBar: {
      display: 'flex',
      gap: '8px',
      justifyContent: 'center',
      marginBottom: '24px',
    },
    progressDot: {
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      background: '#334155',
      transition: 'all 0.2s',
    },
    progressDotActive: {
      background: '#f59e0b',
      width: '24px',
      borderRadius: '4px',
    },
    buttons: {
      display: 'flex',
      gap: '12px',
      justifyContent: 'center',
    },
    button: {
      padding: '12px 24px',
      borderRadius: '8px',
      border: 'none',
      fontSize: '14px',
      fontWeight: '600',
      cursor: 'pointer',
      transition: 'all 0.2s',
    },
    buttonPrimary: {
      background: 'linear-gradient(135deg, #f59e0b, #d97706)',
      color: '#0f172a',
    },
    buttonSecondary: {
      background: 'transparent',
      border: '1px solid #475569',
      color: '#94a3b8',
    },
    skipButton: {
      position: 'absolute',
      top: '16px',
      right: '16px',
      background: 'none',
      border: 'none',
      color: '#64748b',
      cursor: 'pointer',
      fontSize: '14px',
    },
  };

  return (
    <div style={styles.overlay}>
      <div style={styles.modal}>
        <button style={styles.skipButton} onClick={handleClose}>
          Skip →
        </button>

        <div style={styles.icon}>{currentStepData.icon}</div>
        <h2 style={styles.title}>{currentStepData.title}</h2>
        <p style={styles.content}>{currentStepData.content}</p>

        {/* Progress Bar */}
        <div style={styles.progressBar}>
          {steps.map((_, i) => (
            <div
              key={i}
              style={{
                ...styles.progressDot,
                ...(i === currentStep ? styles.progressDotActive : {}),
              }}
            />
          ))}
        </div>

        {/* Navigation */}
        <div style={styles.buttons}>
          <button
            style={{
              ...styles.button,
              ...styles.buttonSecondary,
              opacity: currentStep === 0 ? 0.5 : 1,
            }}
            onClick={handlePrev}
            disabled={currentStep === 0}
          >
            ← Back
          </button>
          <button
            style={{
              ...styles.button,
              ...styles.buttonPrimary,
            }}
            onClick={handleNext}
          >
            {currentStep === steps.length - 1 ? 'Get Started →' : 'Next →'}
          </button>
        </div>

        {/* CTA Button for final step */}
        {currentStepData.cta && (
          <div style={{ ...styles.buttons, marginTop: '16px', flexDirection: 'column' }}>
            <a
              href="https://docs.sting.alphabytez.dev/getting-started/fresh-install-guide"
              style={{
                ...styles.button,
                ...styles.buttonPrimary,
                display: 'block',
                textAlign: 'center',
                textDecoration: 'none',
              }}
            >
              Install STING
            </a>
            <a
              href="mailto:sales@stingassistant.com"
              style={{
                ...styles.button,
                ...styles.buttonSecondary,
                display: 'block',
                textAlign: 'center',
                textDecoration: 'none',
              }}
            >
              Contact Sales
            </a>
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes slideUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
};

export default DemoTourGuide;
