import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import DemoAuthForm from '../components/demo/DemoAuthForm';
import DemoFeatures from '../components/demo/DemoFeatures';

const DemoLanding = () => {
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  // Check if already authenticated
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/demo/status', {
          credentials: 'include'
        });
        const data = await response.json();
        if (data.is_authenticated) {
          setIsAuthenticated(true);
          navigate('/demo/dashboard');
        }
      } catch (error) {
        console.error('Auth check failed:', error);
      } finally {
        setLoading(false);
      }
    };

    checkAuth();
  }, [navigate]);

  const handleAuthSuccess = () => {
    setIsAuthenticated(true);
    navigate('/demo/dashboard');
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.wrapper}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.logo}>
            <span style={styles.logoIcon}>🐝</span>
            <span style={styles.logoText}>STING</span>
          </div>
          <nav style={styles.nav}>
            <a href="https://docs.sting.alphabytez.dev" style={styles.navLink}>Docs</a>
            <a href="https://github.com/AlphaBytez/STING-CE" style={styles.navLink}>GitHub</a>
            <a href="https://stingassistant.com" style={styles.navLink}>Website</a>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section style={styles.hero}>
        <div style={styles.heroContent}>
          <div style={styles.heroText}>
            <span style={styles.badge}>✨ Public Demo Available</span>
            <h1 style={styles.title}>
              Your Private AI Workspace
            </h1>
            <p style={styles.subtitle}>
              Experience STING without installation. Chat with Bee, explore Honey Jars,
              and discover how private AI can transform your workflow.
            </p>
            <div style={styles.heroActions}>
              <DemoAuthForm onSuccess={handleAuthSuccess} compact={false} />
            </div>
            <p style={styles.disclaimer}>
              🔒 Demo sessions are free and require no account. No data is saved.
            </p>
          </div>
          <div style={styles.heroVisual}>
            <div style={styles.previewCard}>
              <div style={styles.previewHeader}>
                <div style={styles.previewDots}>
                  <span style={{...styles.previewDot, background: '#ff5f57'}}></span>
                  <span style={{...styles.previewDot, background: '#ffbd2e'}}></span>
                  <span style={{...styles.previewDot, background: '#28c940'}}></span>
                </div>
                <span style={styles.previewTitle}>STING Demo</span>
              </div>
              <div style={styles.previewContent}>
                <div style={styles.chatPreview}>
                  <div style={styles.chatMessageUser}>
                    What can STING do?
                  </div>
                  <div style={styles.chatMessageBot}>
                    🐝 Great question! STING offers...
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section style={styles.features}>
        <div style={styles.featuresContent}>
          <h2 style={styles.sectionTitle}>What You'll Explore</h2>
          <DemoFeatures />
        </div>
      </section>

      {/* CTA Section */}
      <section style={styles.cta}>
        <div style={styles.ctaContent}>
          <h2 style={styles.ctaTitle}>Ready to Deploy?</h2>
          <p style={styles.ctaText}>
            Get STING running on your own infrastructure today.
          </p>
          <div style={styles.ctaButtons}>
            <a href="https://docs.sting.alphabytez.dev/getting-started/fresh-install-guide" style={styles.ctaButtonPrimary}>
              Get Started
            </a>
            <a href="mailto:sales@stingassistant.com" style={styles.ctaButtonSecondary}>
              Contact Sales
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={styles.footer}>
        <div style={styles.footerContent}>
          <div style={styles.footerLogo}>
            <span style={styles.logoIcon}>🐝</span>
            <span style={styles.logoText}>STING</span>
          </div>
          <p style={styles.footerText}>
            Open-source enterprise AI platform by AlphaBytez
          </p>
          <div style={styles.footerLinks}>
            <a href="https://docs.sting.alphabytez.dev" style={styles.footerLink}>Documentation</a>
            <a href="https://github.com/AlphaBytez/STING-CE" style={styles.footerLink}>GitHub</a>
            <a href="mailto:hello@stingassistant.com" style={styles.footerLink}>Contact</a>
          </div>
        </div>
      </footer>
    </div>
  );
};

const styles = {
  wrapper: {
    minHeight: '100vh',
    background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
    color: '#f8fafc',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '100vh',
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
    padding: '20px 0',
    borderBottom: '1px solid #334155',
  },
  headerContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '0 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  logo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '24px',
    fontWeight: '700',
  },
  logoIcon: {
    fontSize: '28px',
  },
  logoText: {
    background: 'linear-gradient(135deg, #f59e0b, #fbbf24)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  nav: {
    display: 'flex',
    gap: '24px',
  },
  navLink: {
    color: '#94a3b8',
    textDecoration: 'none',
    fontSize: '14px',
    transition: 'color 0.2s',
  },
  hero: {
    padding: '80px 24px',
  },
  heroContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '60px',
    alignItems: 'center',
  },
  heroText: {
    maxWidth: '540px',
  },
  badge: {
    display: 'inline-block',
    padding: '6px 12px',
    background: 'rgba(245, 158, 11, 0.2)',
    border: '1px solid rgba(245, 158, 11, 0.3)',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#fbbf24',
    marginBottom: '16px',
  },
  title: {
    fontSize: '48px',
    fontWeight: '800',
    lineHeight: '1.1',
    marginBottom: '20px',
    background: 'linear-gradient(135deg, #f8fafc, #94a3b8)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
  },
  subtitle: {
    fontSize: '18px',
    lineHeight: '1.6',
    color: '#94a3b8',
    marginBottom: '32px',
  },
  heroActions: {
    marginBottom: '16px',
  },
  disclaimer: {
    fontSize: '13px',
    color: '#64748b',
  },
  heroVisual: {
    display: 'flex',
    justifyContent: 'center',
  },
  previewCard: {
    width: '100%',
    maxWidth: '420px',
    background: '#1e293b',
    borderRadius: '12px',
    border: '1px solid #334155',
    overflow: 'hidden',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
  },
  previewHeader: {
    padding: '12px 16px',
    background: '#0f172a',
    borderBottom: '1px solid #334155',
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  previewDots: {
    display: 'flex',
    gap: '6px',
  },
  previewDot: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
  },
  previewTitle: {
    fontSize: '12px',
    color: '#94a3b8',
  },
  previewContent: {
    padding: '16px',
  },
  chatPreview: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  chatMessageUser: {
    alignSelf: 'flex-end',
    background: '#f59e0b',
    color: '#0f172a',
    padding: '10px 14px',
    borderRadius: '16px',
    borderBottomRightRadius: '4px',
    fontSize: '14px',
    maxWidth: '80%',
  },
  chatMessageBot: {
    alignSelf: 'flex-start',
    background: '#334155',
    color: '#f8fafc',
    padding: '10px 14px',
    borderRadius: '16px',
    borderBottomLeftRadius: '4px',
    fontSize: '14px',
    maxWidth: '80%',
  },
  features: {
    padding: '80px 24px',
    background: '#0f172a',
  },
  featuresContent: {
    maxWidth: '1200px',
    margin: '0 auto',
  },
  sectionTitle: {
    textAlign: 'center',
    fontSize: '32px',
    fontWeight: '700',
    marginBottom: '48px',
  },
  cta: {
    padding: '80px 24px',
  },
  ctaContent: {
    maxWidth: '800px',
    margin: '0 auto',
    textAlign: 'center',
  },
  ctaTitle: {
    fontSize: '32px',
    fontWeight: '700',
    marginBottom: '16px',
  },
  ctaText: {
    fontSize: '18px',
    color: '#94a3b8',
    marginBottom: '32px',
  },
  ctaButtons: {
    display: 'flex',
    gap: '16px',
    justifyContent: 'center',
    flexWrap: 'wrap',
  },
  ctaButtonPrimary: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '14px 28px',
    background: 'linear-gradient(135deg, #f59e0b, #d97706)',
    color: '#0f172a',
    textDecoration: 'none',
    borderRadius: '8px',
    fontWeight: '600',
    fontSize: '16px',
    transition: 'transform 0.2s, box-shadow 0.2s',
  },
  ctaButtonSecondary: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '14px 28px',
    background: 'transparent',
    color: '#f8fafc',
    textDecoration: 'none',
    borderRadius: '8px',
    fontWeight: '600',
    fontSize: '16px',
    border: '1px solid #475569',
    transition: 'background 0.2s',
  },
  footer: {
    padding: '40px 24px',
    borderTop: '1px solid #334155',
  },
  footerContent: {
    maxWidth: '1200px',
    margin: '0 auto',
    textAlign: 'center',
  },
  footerLogo: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    fontSize: '20px',
    fontWeight: '700',
    marginBottom: '12px',
  },
  footerText: {
    color: '#64748b',
    fontSize: '14px',
    marginBottom: '16px',
  },
  footerLinks: {
    display: 'flex',
    gap: '24px',
    justifyContent: 'center',
  },
  footerLink: {
    color: '#64748b',
    textDecoration: 'none',
    fontSize: '14px',
  },
};

// Add keyframe animation for spinner
const styleSheet = document.createElement('style');
styleSheet.textContent = `
  @keyframes spin {
    to { transform: rotate(360deg); }
  }
`;
document.head.appendChild(styleSheet);

export default DemoLanding;
