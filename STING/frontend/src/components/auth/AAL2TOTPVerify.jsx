import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

const AAL2TOTPVerify = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [totpCode, setTotpCode] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [userEmail, setUserEmail] = useState('');
  const totpInputRef = useRef(null);

  // Get return URL from params or default to dashboard
  const returnTo = searchParams.get('return_to') || '/dashboard';

  // Get user email on component mount
  useEffect(() => {
    const fetchUserEmail = async () => {
      try {
        const response = await fetch('/api/auth/me', {
          credentials: 'include'
        });
        if (response.ok) {
          const data = await response.json();
          // Try multiple possible locations for email based on Flask session format
          const email = data.identity?.traits?.email || 
                       data.user?.email || 
                       data.email || 
                       'user@example.com';
          setUserEmail(email);
          console.log('🔐 Retrieved user email for AAL2:', email);
        } else {
          console.log('🔐 Failed to fetch user email:', response.status, response.statusText);
        }
      } catch (error) {
        console.log('Could not fetch user email:', error);
        setUserEmail('user@example.com');
      }
    };
    
    fetchUserEmail();
  }, []);

  // Auto-focus TOTP input
  useEffect(() => {
    if (totpInputRef.current) {
      totpInputRef.current.focus();
    }
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      console.log('🔐 Starting AAL2 TOTP flow...');
      
      // Initialize AAL2 flow (same pattern as TOTPAuth.jsx)
      const flowResponse = await fetch(`/.ory/self-service/login/browser?aal=aal2&refresh=true`, {
        headers: { 'Accept': 'application/json' },
        credentials: 'include'
      });
      
      if (!flowResponse.ok) {
        throw new Error('Failed to initialize AAL2 flow');
      }
      
      const flowData = await flowResponse.json();
      console.log('🔐 AAL2 flow initialized:', flowData.id);
      
      // Prepare TOTP form data
      const formData = new URLSearchParams();
      formData.append('totp_code', totpCode.trim());
      formData.append('method', 'totp');
      
      const csrfToken = flowData.ui.nodes.find(
        n => n.attributes?.name === 'csrf_token'
      )?.attributes?.value;
      if (csrfToken) {
        formData.append('csrf_token', csrfToken);
      }
      
      // Submit TOTP to Kratos flow
      const totpActionUrl = flowData.ui.action.replace(/https?:\/\/[^\/]+/, '');
      console.log('🔐 Submitting TOTP to:', totpActionUrl);
      
      const response = await fetch(totpActionUrl, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/x-www-form-urlencoded'
        },
        credentials: 'include',
        body: formData.toString()
      });
      
      const responseData = await response.json();
      console.log('🔐 TOTP response:', response.status, responseData?.state);
      
      if (response.ok || responseData?.state === 'passed_challenge') {
        console.log('✅ AAL2 TOTP ceremony successful! Using Flask AAL2 elevation...');
        
        // Use Flask AAL2 elevation for consistency with WebAuthn flow
        try {
          const completeResponse = await fetch('/api/aal2/challenge/complete', {
            method: 'POST',
            headers: { 
              'Content-Type': 'application/json',
              'Accept': 'application/json'
            },
            credentials: 'include',
            body: JSON.stringify({
              verification_method: 'totp',
              trusted_ceremony: true,
              kratos_native: true  // TOTP works natively but using Flask for consistency
            })
          });
          
          if (completeResponse.ok) {
            const completeData = await completeResponse.json();
            console.log('✅ Flask AAL2 elevation successful (TOTP)!', completeData);
          } else {
            console.log('⚠️ Flask AAL2 elevation failed, but TOTP succeeded');
          }
        } catch (error) {
          console.log('⚠️ Flask AAL2 update error:', error);
        }
        
        // Redis AAL2 verification handled automatically by Flask backend
        
        // Redirect to return URL (dashboard by default)
        console.log('🔐 TOTP authentication complete, redirecting to:', returnTo);
        window.location.href = returnTo;
      } else {
        // Extract error from Kratos response
        const errorMsg = responseData?.ui?.messages?.find(m => m.type === 'error')?.text;
        throw new Error(errorMsg || 'TOTP verification failed');
      }

    } catch (error) {
      console.error('❌ AAL2 TOTP verification failed:', error);
      setError(error.message || 'Authentication failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleCodeChange = (e) => {
    const value = e.target.value.replace(/\D/g, ''); // Only digits
    if (value.length <= 6) {
      setTotpCode(value);
      setError('');
    }
  };

  const handleBack = () => {
    navigate('/security-upgrade' + (returnTo !== '/dashboard' ? `?return_to=${encodeURIComponent(returnTo)}` : ''));
  };

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center p-4">
      <div className="sting-glass-card sting-glass-default sting-elevation-medium p-8 w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <img src="/sting-logo.png" alt="STING" className="w-20 h-20 mx-auto mb-4" />
          <h1 className="text-3xl font-bold text-white mb-2">
            Authenticator Verification
          </h1>
          <p className="text-gray-300 mb-4">
            Enter the 6-digit code from your authenticator app
          </p>
          {userEmail && (
            <p className="text-sm text-blue-300">
              Verifying AAL2 for: {userEmail}
            </p>
          )}
        </div>

        {/* Error Display */}
        {error && (
          <div className="sting-glass-subtle border border-red-500/50 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* TOTP Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          <div>
            <label htmlFor="totpCode" className="block text-sm font-medium text-gray-300 mb-2">
              Authenticator Code
            </label>
            <input
              ref={totpInputRef}
              type="text"
              id="totpCode"
              value={totpCode}
              onChange={handleCodeChange}
              placeholder="123456"
              className="w-full px-4 py-3 text-center text-2xl tracking-widest bg-slate-800/50 border border-slate-600 rounded-lg text-white placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/25 focus:outline-none"
              maxLength="6"
              pattern="[0-9]{6}"
              required
              disabled={loading}
            />
            <p className="text-xs text-gray-500 mt-2 text-center">
              Enter the 6-digit code from Google Authenticator, Authy, or similar app
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || totpCode.length !== 6}
            className="w-full py-3 px-4 bg-green-600 hover:bg-green-500 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors focus:ring-2 focus:ring-green-500/25 focus:outline-none"
          >
            {loading ? (
              <span className="flex items-center justify-center">
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                Verifying...
              </span>
            ) : (
              'Verify & Continue'
            )}
          </button>
        </form>

        {/* Back Button */}
        <div className="mt-6 text-center">
          <button
            onClick={handleBack}
            className="text-gray-400 hover:text-white text-sm underline"
            disabled={loading}
          >
            ← Back to security options
          </button>
        </div>

        {/* Development Mode Info */}
        {process.env.NODE_ENV === 'development' && (
          <div className="mt-6 p-3 sting-glass-subtle border border-purple-500/50 rounded-lg">
            <p className="text-purple-300 text-xs text-center">
              🔧 Dev: AAL2 TOTP Verification Page
              <br />
              Standalone authentication without AuthProvider dependencies
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default AAL2TOTPVerify;