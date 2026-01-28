import React, { useState, useEffect } from 'react';

/**
 * MobileTest - Diagnostic component for iOS Safari debugging
 * Shows device info, auth state, and environment details
 */
const MobileTest = () => {
  const [diagnostics, setDiagnostics] = useState({
    userAgent: '',
    screenWidth: 0,
    screenHeight: 0,
    pixelRatio: 0,
    isMobile: false,
    isIOS: false,
    isSafari: false,
    pathname: '',
    timestamp: '',
  });

  useEffect(() => {
    if (typeof window !== 'undefined') {
      const ua = navigator.userAgent || '';
      setDiagnostics({
        userAgent: ua,
        screenWidth: window.innerWidth,
        screenHeight: window.innerHeight,
        pixelRatio: window.devicePixelRatio || 1,
        isMobile: /Mobile|Android|iPhone|iPad/i.test(ua),
        isIOS: /iPhone|iPad|iPod/i.test(ua),
        isSafari: /Safari/i.test(ua) && !/Chrome|CriOS/i.test(ua),
        pathname: window.location.pathname,
        timestamp: new Date().toISOString(),
      });
    }
  }, []);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: '#ff6600',
      color: '#ffffff',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'flex-start',
      fontSize: '14px',
      fontFamily: 'system-ui, -apple-system, sans-serif',
      zIndex: 99999,
      padding: '20px',
      textAlign: 'left',
      overflow: 'auto',
    }}>
      <div style={{ fontSize: '32px', marginBottom: '10px' }}>🔶 MOBILE TEST 🔶</div>
      <div style={{ fontSize: '18px', marginBottom: '20px', textAlign: 'center' }}>
        If you see this, React is rendering correctly!
      </div>
      
      <div style={{
        background: 'rgba(0,0,0,0.3)',
        padding: '15px',
        borderRadius: '8px',
        width: '100%',
        maxWidth: '400px',
      }}>
        <div style={{ marginBottom: '10px', fontWeight: 'bold', fontSize: '16px' }}>
          📱 Device Diagnostics:
        </div>
        <div style={{ marginBottom: '5px' }}>
          <strong>Screen:</strong> {diagnostics.screenWidth} x {diagnostics.screenHeight} @{diagnostics.pixelRatio}x
        </div>
        <div style={{ marginBottom: '5px' }}>
          <strong>Mobile:</strong> {diagnostics.isMobile ? '✅ Yes' : '❌ No'}
        </div>
        <div style={{ marginBottom: '5px' }}>
          <strong>iOS:</strong> {diagnostics.isIOS ? '✅ Yes' : '❌ No'}
        </div>
        <div style={{ marginBottom: '5px' }}>
          <strong>Safari:</strong> {diagnostics.isSafari ? '✅ Yes' : '❌ No'}
        </div>
        <div style={{ marginBottom: '5px' }}>
          <strong>Path:</strong> {diagnostics.pathname}
        </div>
        <div style={{ marginBottom: '5px', fontSize: '10px', wordBreak: 'break-all' }}>
          <strong>UA:</strong> {diagnostics.userAgent}
        </div>
        <div style={{ fontSize: '10px', opacity: 0.7 }}>
          {diagnostics.timestamp}
        </div>
      </div>

      <div style={{ marginTop: '20px', textAlign: 'center' }}>
        <a href="/m/" style={{ color: '#fff', textDecoration: 'underline', marginRight: '15px' }}>
          → Go to /m/
        </a>
        <a href="/login" style={{ color: '#fff', textDecoration: 'underline' }}>
          → Go to /login
        </a>
      </div>
    </div>
  );
};

export default MobileTest;
