import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DemoChat from './DemoChat';
import DemoTourGuide from './DemoTourGuide';

const DemoDashboard = () => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTour, setShowTour] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/demo/status', {
          credentials: 'include'
        });
        const data = await response.json();

        if (!data.is_authenticated) {
          navigate('/demo');
          return;
        }

        setUser({ email: data.email });
      } catch (error) {
        console.error('Auth check failed:', error);
        navigate('/demo');
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [navigate]);

  const handleLogout = async () => {
    try {
      await fetch('/api/demo/logout', {
        method: 'POST',
        credentials: 'include'
      });
      navigate('/demo');
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const handleStartTour = () => {
    setShowTour(true);
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p>Loading demo...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.wrapper}>
      {/* Demo Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.logo}>
            <span style={styles.logoIcon}>🐝</span>
            <span style={styles.logoText}>STING Demo</span>
          </div>
          <div style={styles.headerActions}>
            <button onClick={handleStartTour} style={styles.tourButton}>
              🎯 Start Tour
            </button>
            <button onClick={handleLogout} style={styles.logoutButton}>
              Exit Demo
            </button>
          </div>
        </div>
      </header>

      {/* Demo Banner */}
      <div style={styles.demoBanner}>
        <span style={styles.demoIcon}>✨</span>
        <span>You're in Demo Mode - Exploring STING without installation</span>
        <a href="https://docs.sting.alphabytez.dev/getting-started/fresh-install-guide" style={styles.demoLink}>
          Get STING →
        </a>
      </div>

      {/* Main Content */}
      <main style={styles.main}>
        <div style={styles.sidebar}>
          {/* Demo Honey Jar Preview */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>🍯 Honey Jar (Demo)</h3>
            <div style={styles.demoContent}>
              <p style={styles.demoText}>
                In a real STING instance, this would be your private knowledge base.
              </p>
              <div style={styles.docList}>
                <div style={styles.docItem}>
                  <span style={styles.docIcon}>📄</span>
                  <span>getting-started.pdf</span>
                </div>
                <div style={styles.docItem}>
                  <span style={styles.docIcon}>📄</span>
                  <span>architecture.md</span>
                </div>
                <div style={styles.docItem}>
                  <span style={styles.docIcon}>📄</span>
                  <span>api-reference.pdf</span>
                </div>
              </div>
              <p style={styles.demoNote}>
                💡 Documents are pre-loaded for demo purposes
              </p>
            </div>
          </div>

          {/* Features List */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Features</h3>
            <ul style={styles.featureList}>
              <li style={styles.featureItem}>
                <span>🍯</span> Knowledge Management
              </li>
              <li style={styles.featureItem}>
                <span>🐝</span> AI Assistant (Demo Mode)
              </li>
              <li style={styles.featureItem}>
                <span>🔐</span> Enterprise Auth
              </li>
              <li style={styles.featureItem}>
                <span>🛡️</span> PII Detection
              </li>
            </ul>
          </div>

          {/* CTAs */}
          <div style={styles.section}>
            <h3 style={styles.sectionTitle}>Ready to Deploy?</h3>
            <div style={styles.ctaButtons}>
              <a href="https://docs.sting.alphabytez.dev/getting-started/fresh-install-guide" style={styles.ctaButtonPrimary}>
                Get Started
              </a>
              <a href="mailto:sales@stingassistant.com" style={styles.ctaButtonSecondary}>
                Contact Sales
              </a>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div style={styles.content}>
          <DemoChat />
        </div>
      </main>

      {/* Tour Guide Modal */}
      {showTour && (
        <DemoTourGuide onClose={() => setShowTour(false)} />
      )}
    </div>
  );
};

const styles = {
  wrapper: {
    minHeight: '100vh',
    background: '#0f172a',
    color: '#f8fafc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
    background: '#0f172a',
  },
  loading: {
    textAlign: 'center',
    color: '#94a3b8',
  },
  spinner: {
    width: '40px',
    height: '40px',
    border: '3px solid #334155',
    borderTopColor: '#f59e0b',
    borderRadius: '50%',
    animation: 'spin 1s linear infinite',
    margin: '0 auto 16px',
  },
  header: {
    padding: '16px 24px',
    borderBottom: '1px solid #334155',
    background: 'rgba(15, 23, 42, 0.8)',
    backdropFilter: 'blur(10px)',
  },
  headerContent: {
    maxWidth: '1400px',
    margin: '0 auto',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '20px',
    fontWeight: '700',
  },
  logoIcon: {
    fontSize: '24px',
  },
  logoText: {
    background: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  headerActions: {
    display: 'flex',
    gap: '12px',
  },
  tourButton: {
    padding: '8px 16px',
    background: 'rgba(245, 158, 11, 0.2)',
    border: '1px solid rgba(245, 158, 11, 0.3)',
    borderRadius: '6px',
    color: '#fbbf24',
    fontSize: '14px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  logoutButton: {
    padding: '8px 16px',
    background: 'transparent',
    border: '1px solid #475569',
    borderRadius: '6px',
    color: '#94a3b8',
    fontSize: '14px',
    cursor: 'pointer',
  },
  demoBanner: {
    padding: '12px 24px',
    background: 'linear-gradient(90deg, rgba(245, 158, 11, 0.1), rgba(34, 197, 94, 0.1))',
    borderBottom: '1px solid #334155',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    fontSize: '14px',
    color: '#94a3b8',
  },
  demoIcon: {
    fontSize: '16px',
  },
  demoLink: {
    marginLeft: 'auto',
    color: '#f59e0b',
    textDecoration: 'none',
    fontWeight: '500',
  },
  main: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '24px',
    display: 'grid',
    gridTemplateColumns: '320px 1fr',
    gap: '24px',
  },
  sidebar: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  section: {
    background: 'rgba(30, 41, 59, 0.6)',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '20px',
  },
  sectionTitle: {
    fontSize: '16px',
    fontWeight: '600',
    marginBottom: '16px',
    color: '#f8fafc',
  },
  demoContent: {
    fontSize: '14px',
  },
  demoText: {
    color: '#94a3b8',
    marginBottom: '16px',
    lineHeight: '1.5',
  },
  docList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    marginBottom: '12px',
  },
  docItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 12px',
    background: 'rgba(15, 23, 42, 0.5)',
    borderRadius: '6px',
    fontSize: '13px',
    color: '#cbd5e1',
  },
  docIcon: {
    fontSize: '14px',
  },
  demoNote: {
    fontSize: '12px',
    color: '#64748b',
    fontStyle: 'italic',
  },
  featureList: {
    listStyle: 'none',
    padding: 0,
    margin: 0,
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  featureItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    color: '#cbd5e1',
  },
  ctaButtons: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  ctaButtonPrimary: {
    display: 'block',
    textAlign: 'center',
    padding: '10px 16px',
    background: 'linear-gradient(135deg, #f59e0b, #d97706)',
    color: '#0f172a',
    textDecoration: 'none',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '14px',
  },
  ctaButtonSecondary: {
    display: 'block',
    textAlign: 'center',
    padding: '10px 16px',
    background: 'transparent',
    color: '#f8fafc',
    textDecoration: 'none',
    borderRadius: '6px',
    fontWeight: '600',
    fontSize: '14px',
    border: '1px solid #475569',
  },
  content: {
    minHeight: '500px',
  },
};

const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);

export default DemoDashboard;
