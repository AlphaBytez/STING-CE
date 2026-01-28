import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const FirstRun = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [adminExists, setAdminExists] = useState(false);
  const [email, setEmail] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    checkAdminStatus();
  }, []);

  const checkAdminStatus = async () => {
    try {
      const response = await fetch('/api/auth/admin-setup-status');
      const data = await response.json();
      setAdminExists(data.setup_complete);

      if (data.setup_complete) {
        // Admin exists, redirect to login
        navigate('/login');
      }
    } catch (err) {
      // If endpoint fails, assume admin exists (show login)
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateAdmin = async (e) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter an email address');
      return;
    }

    setCreating(true);
    setError('');

    try {
      const response = await fetch('/api/auth/admin-setup-email', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email })
      });

      const data = await response.json();

      if (data.success) {
        // Store email in session and redirect to setup flow
        sessionStorage.setItem('admin_setup_email', email);
        navigate('/admin-setup/verify', { state: { email, step: 'verify' } });
      } else {
        setError(data.error || 'Failed to send verification code');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  const copyCommand = () => {
    const cmd = `sudo msting create admin ${email || 'admin@example.com'}`;
    navigator.clipboard.writeText(cmd);
  };

  if (loading) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>
          <div style={styles.spinner}></div>
          <p>Checking setup status...</p>
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
        </div>
      </header>

      {/* Main Content */}
      <main style={styles.main}>
        <div style={styles.content}>
          <div style={styles.card}>
            <div style={styles.cardHeader}>
              <div style={styles.icon}>🚀</div>
              <h1 style={styles.title}>Welcome to STING</h1>
              <p style={styles.subtitle}>
                Let's set up your administrator account to get started.
              </p>
            </div>

            {error && (
              <div style={styles.error}>
                {error}
              </div>
            )}

            {success ? (
              <div style={styles.success}>
                <div style={styles.successIcon}>✓</div>
                <h3 style={styles.successTitle}>Admin Created!</h3>
                <p>Check your email for the verification code.</p>
                <button
                  style={styles.primaryButton}
                  onClick={() => navigate('/admin-setup/verify')}
                >
                  Continue Setup →
                </button>
              </div>
            ) : (
              <div style={styles.options}>
                {/* Option 1: CLI Command */}
                <div style={styles.option}>
                  <div style={styles.optionHeader}>
                    <span style={styles.optionBadge}>Option 1</span>
                    <h3 style={styles.optionTitle}>Command Line</h3>
                  </div>
                  <p style={styles.optionDesc}>
                    Run this command in your terminal to create an admin:
                  </p>
                  <div style={styles.commandBox}>
                    <code style={styles.command}>
                      sudo msting create admin {email || 'admin@example.com'}
                    </code>
                    <button
                      style={styles.copyButton}
                      onClick={copyCommand}
                      title="Copy command"
                    >
                      📋
                    </button>
                  </div>
                  <p style={styles.commandNote}>
                    Creates an admin and sends a verification email.
                  </p>
                </div>

                <div style={styles.divider}>
                  <span>or</span>
                </div>

                {/* Option 2: Web Form */}
                <div style={styles.option}>
                  <div style={styles.optionHeader}>
                    <span style={styles.optionBadge}>Option 2</span>
                    <h3 style={styles.optionTitle}>Quick Setup</h3>
                  </div>
                  <p style={styles.optionDesc}>
                    Enter your email to create an admin account now:
                  </p>
                  <form onSubmit={handleCreateAdmin}>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="admin@example.com"
                      style={styles.input}
                      required
                    />
                    <button
                      type="submit"
                      style={styles.primaryButton}
                      disabled={creating}
                    >
                      {creating ? 'Sending Code...' : 'Create Admin'}
                    </button>
                  </form>
                </div>
              </div>
            )}
          </div>

          {/* Help Section */}
          <div style={styles.help}>
            <p style={styles.helpText}>
              Need help?{' '}
              <a href="https://docs.sting.alphabytez.dev" style={styles.link}>
                View Documentation
              </a>
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer style={styles.footer}>
        <p style={styles.footerText}>
          Open-source enterprise AI platform by AlphaBytez
        </p>
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
    background: 'linear-gradient(180deg, #0f172a 0%, #1e293b 100%)',
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
  main: {
    padding: '60px 24px',
    display: 'flex',
    justifyContent: 'center',
  },
  content: {
    width: '100%',
    maxWidth: '600px',
  },
  card: {
    background: 'rgba(30, 41, 59, 0.8)',
    backdropFilter: 'blur(10px)',
    border: '1px solid #334155',
    borderRadius: '16px',
    padding: '40px',
  },
  cardHeader: {
    textAlign: 'center',
    marginBottom: '32px',
  },
  icon: {
    fontSize: '48px',
    marginBottom: '16px',
  },
  title: {
    fontSize: '28px',
    fontWeight: '700',
    marginBottom: '8px',
    color: '#f8fafc',
  },
  subtitle: {
    fontSize: '16px',
    color: '#94a3b8',
  },
  error: {
    padding: '12px 16px',
    borderRadius: '8px',
    background: 'rgba(239, 68, 68, 0.2)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    fontSize: '14px',
    marginBottom: '20px',
  },
  success: {
    textAlign: 'center',
    padding: '20px',
  },
  successIcon: {
    width: '64px',
    height: '64px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #22c55e, #16a34a)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '32px',
    margin: '0 auto 16px',
  },
  successTitle: {
    fontSize: '20px',
    fontWeight: '600',
    marginBottom: '8px',
  },
  options: {
    display: 'flex',
    flexDirection: 'column',
    gap: '24px',
  },
  option: {
    padding: '20px',
    background: 'rgba(15, 23, 42, 0.5)',
    borderRadius: '12px',
    border: '1px solid #334155',
  },
  optionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '12px',
  },
  optionBadge: {
    display: 'inline-block',
    padding: '4px 10px',
    background: 'rgba(245, 158, 11, 0.2)',
    border: '1px solid rgba(245, 158, 11, 0.3)',
    borderRadius: '6px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#fbbf24',
  },
  optionTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#f8fafc',
  },
  optionDesc: {
    fontSize: '14px',
    color: '#94a3b8',
    marginBottom: '16px',
  },
  commandBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    background: '#0f172a',
    border: '1px solid #334155',
    borderRadius: '8px',
    padding: '12px',
    marginBottom: '12px',
  },
  command: {
    flex: 1,
    fontFamily: 'monospace',
    fontSize: '13px',
    color: '#22c55e',
    wordBreak: 'break-all',
  },
  copyButton: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    fontSize: '16px',
    padding: '4px',
    opacity: 0.7,
    transition: 'opacity 0.2s',
  },
  commandNote: {
    fontSize: '12px',
    color: '#64748b',
    fontStyle: 'italic',
  },
  divider: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    color: '#64748b',
    fontSize: '14px',
  },
  dividerLine: {
    flex: 1,
    height: '1px',
    background: '#334155',
  },
  input: {
    width: '100%',
    padding: '12px 16px',
    borderRadius: '8px',
    border: '1px solid #475569',
    background: '#0f172a',
    color: '#f8fafc',
    fontSize: '14px',
    marginBottom: '12px',
    boxSizing: 'border-box',
  },
  primaryButton: {
    width: '100%',
    padding: '12px 20px',
    borderRadius: '8px',
    border: 'none',
    background: 'linear-gradient(135deg, #f59e0b, #d97706)',
    color: '#0f172a',
    fontSize: '14px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'opacity 0.2s',
  },
  help: {
    textAlign: 'center',
    marginTop: '24px',
  },
  helpText: {
    fontSize: '14px',
    color: '#64748b',
  },
  link: {
    color: '#f59e0b',
    textDecoration: 'none',
  },
  footer: {
    padding: '24px',
    textAlign: 'center',
    borderTop: '1px solid #334155',
  },
  footerText: {
    fontSize: '14px',
    color: '#64748b',
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

export default FirstRun;
