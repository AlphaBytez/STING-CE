import React, { useEffect, useState } from 'react';

/**
 * EmergencyReset - Nuclear option to clear all client state
 * Access via /reset-state to break out of auth loops
 */
const EmergencyReset = () => {
  const [status, setStatus] = useState('Clearing all state...');
  const [done, setDone] = useState(false);

  useEffect(() => {
    const clearAll = async () => {
      try {
        // Clear sessionStorage
        setStatus('Clearing sessionStorage...');
        sessionStorage.clear();
        
        // Clear localStorage (except preferences we want to keep)
        setStatus('Clearing localStorage...');
        const keysToRemove = [];
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          // Keep theme preference but clear auth-related stuff
          if (key && !key.includes('theme')) {
            keysToRemove.push(key);
          }
        }
        keysToRemove.forEach(key => localStorage.removeItem(key));
        
        // Clear cookies by setting them to expire
        setStatus('Clearing cookies...');
        document.cookie.split(';').forEach(cookie => {
          const name = cookie.split('=')[0].trim();
          document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;`;
          document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/; domain=${window.location.hostname}`;
        });

        setStatus('All state cleared! Redirecting to login...');
        setDone(true);
        
        // Redirect after a short delay
        setTimeout(() => {
          window.location.href = '/login';
        }, 2000);
      } catch (err) {
        setStatus(`Error: ${err.message}. Try clearing browser data manually.`);
      }
    };

    clearAll();
  }, []);

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      background: '#161922',
      color: '#f1f5f9',
      padding: '20px',
      textAlign: 'center',
    }}>
      <h1 style={{ marginBottom: '20px', color: '#eab308' }}>🔄 Emergency Reset</h1>
      <p style={{ marginBottom: '20px', fontSize: '18px' }}>{status}</p>
      {done && (
        <p style={{ color: '#22c55e' }}>
          ✅ State cleared! Redirecting...
        </p>
      )}
      {!done && (
        <div style={{
          width: '40px',
          height: '40px',
          border: '3px solid #3a4356',
          borderTop: '3px solid #eab308',
          borderRadius: '50%',
          animation: 'spin 1s linear infinite',
        }} />
      )}
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default EmergencyReset;
