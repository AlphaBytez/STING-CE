import React, { useState, useEffect } from 'react';

const DemoAuthForm = ({ onSuccess, compact = true }) => {
  const [step, setStep] = useState('email'); // 'email', 'verify', 'success'
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [privacyAcknowledged, setPrivacyAcknowledged] = useState(false);

  // Check if already authenticated on mount
  useEffect(() => {
    const checkAuth = async () => {
      try {
        const response = await fetch('/api/demo/status', {
          credentials: 'include'
        });
        const data = await response.json();
        if (data.is_authenticated) {
          onSuccess();
        }
      } catch (error) {
        // Silently fail - user not authenticated
      }
    };

    checkAuth();
  }, [onSuccess]);

  const handleRequestCode = async (e) => {
    e.preventDefault();
    if (!email) {
      setError('Please enter your email');
      return;
    }
    if (!privacyAcknowledged) {
      setError('Please acknowledge the privacy notice');
      return;
    }

    setLoading(true);
    setError('');
    setMessage('');

    try {
      const response = await fetch('/api/demo/request-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
        credentials: 'include'
      });

      const data = await response.json();

      if (data.success) {
        setStep('verify');
        setMessage(data.message);
      } else {
        setError(data.message || 'Failed to send verification code');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyCode = async (e) => {
    e.preventDefault();
    if (!code) {
      setError('Please enter the verification code');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/demo/verify-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
        credentials: 'include'
      });

      const data = await response.json();

      if (data.success) {
        setStep('success');
        setMessage(data.message);
        setTimeout(() => {
          onSuccess();
        }, 1500);
      } else {
        setError(data.message || 'Invalid verification code');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendCode = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/demo/request-code', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
        credentials: 'include'
      });

      const data = await response.json();

      if (data.success) {
        setMessage('New code sent! Check your email.');
      } else {
        setError(data.message || 'Failed to resend code');
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const styles = compact ? compactStyles : fullStyles;

  if (step === 'verify') {
    return (
      <div style={styles.form}>
        <h3 style={styles.title}>Check Your Email</h3>
        <p style={styles.subtitle}>
          We sent a verification code to <strong>{email}</strong>
        </p>

        {error && <div style={styles.error}>{error}</div>}
        {message && <div style={styles.success}>{message}</div>}

        <form onSubmit={handleVerifyCode}>
          <input
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            placeholder="Enter 6-digit code"
            style={styles.input}
            maxLength={6}
            autoFocus
          />
          <button
            type="submit"
            style={styles.button}
            disabled={loading || code.length !== 6}
          >
            {loading ? 'Verifying...' : 'Enter Demo'}
          </button>
        </form>

        <p style={styles.linkText}>
          Didn't receive the code?{' '}
          <button onClick={handleResendCode} style={styles.linkButton}>
            Resend
          </button>
        </p>

        <button onClick={() => setStep('email')} style={styles.backButton}>
          ← Back
        </button>
      </div>
    );
  }

  if (step === 'success') {
    return (
      <div style={styles.form}>
        <div style={styles.successIcon}>✓</div>
        <h3 style={styles.title}>Welcome!</h3>
        <p style={styles.subtitle}>{message}</p>
        <p style={styles.redirectText}>Redirecting to demo...</p>
      </div>
    );
  }

  return (
    <div style={styles.form}>
      <h3 style={styles.title}>Try STING Free</h3>
      <p style={styles.subtitle}>
        Enter your email to access the live demo
      </p>

      {error && <div style={styles.error}>{error}</div>}
      {message && <div style={styles.success}>{message}</div>}

      <form onSubmit={handleRequestCode}>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="your@email.com"
          style={styles.input}
          required
        />

        <label style={styles.checkboxLabel}>
          <input
            type="checkbox"
            checked={privacyAcknowledged}
            onChange={(e) => setPrivacyAcknowledged(e.target.checked)}
            style={styles.checkbox}
          />
          <span style={styles.checkboxText}>
            I agree to the{' '}
            <a href="https://docs.sting.alphabytez.dev" target="_blank" rel="noopener noreferrer" style={styles.linkButton}>
              privacy notice
            </a>
          </span>
        </label>

        <button
          type="submit"
          style={styles.button}
          disabled={loading || !privacyAcknowledged}
        >
          {loading ? 'Sending Code...' : 'Continue to Demo →'}
        </button>
      </form>
    </div>
  );
};

const compactStyles = {
  form: {
    background: 'rgba(30, 41, 59, 0.8)',
    backdropFilter: 'blur(10px)',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '24px',
    maxWidth: '380px',
  },
  title: {
    fontSize: '20px',
    fontWeight: '700',
    marginBottom: '8px',
    color: '#f8fafc',
  },
  subtitle: {
    fontSize: '14px',
    color: '#94a3b8',
    marginBottom: '16px',
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
  button: {
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
  error: {
    padding: '10px 14px',
    borderRadius: '8px',
    background: 'rgba(239, 68, 68, 0.2)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fca5a5',
    fontSize: '13px',
    marginBottom: '12px',
  },
  success: {
    padding: '10px 14px',
    borderRadius: '8px',
    background: 'rgba(34, 197, 94, 0.2)',
    border: '1px solid rgba(34, 197, 94, 0.3)',
    color: '#86efac',
    fontSize: '13px',
    marginBottom: '12px',
  },
  linkText: {
    marginTop: '12px',
    fontSize: '13px',
    color: '#94a3b8',
    textAlign: 'center',
  },
  linkButton: {
    background: 'none',
    border: 'none',
    color: '#f59e0b',
    cursor: 'pointer',
    textDecoration: 'underline',
    padding: 0,
    fontSize: '13px',
  },
  backButton: {
    marginTop: '16px',
    background: 'none',
    border: 'none',
    color: '#94a3b8',
    cursor: 'pointer',
    fontSize: '13px',
    width: '100%',
  },
  checkboxLabel: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    marginBottom: '16px',
    cursor: 'pointer',
  },
  checkbox: {
    marginTop: '2px',
  },
  checkboxText: {
    fontSize: '12px',
    color: '#94a3b8',
    lineHeight: '1.4',
  },
  successIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #22c55e, #16a34a)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
    margin: '0 auto 16px',
  },
  redirectText: {
    fontSize: '14px',
    color: '#94a3b8',
    textAlign: 'center',
  },
};

const fullStyles = {
  ...compactStyles,
  form: {
    ...compactStyles.form,
    maxWidth: '420px',
  },
};

export default DemoAuthForm;
