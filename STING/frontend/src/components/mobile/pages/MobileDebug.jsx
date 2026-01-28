import React from 'react';

const MobileDebug = () => {
  const [info, setInfo] = React.useState({});
  
  React.useEffect(() => {
    const cookies = document.cookie;
    const localStorage_keys = Object.keys(window.localStorage || {});
    const sessionStorage_keys = Object.keys(window.sessionStorage || {});
    
    setInfo({
      cookies: cookies || 'none',
      localStorage: localStorage_keys,
      sessionStorage: sessionStorage_keys,
      userAgent: navigator.userAgent,
      url: window.location.href,
      timestamp: new Date().toISOString()
    });
  }, []);

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: '#00ff00',
      color: '#000',
      padding: '20px',
      fontSize: '12px',
      overflow: 'auto',
      fontFamily: 'monospace',
      zIndex: 99999
    }}>
      <h1>🐛 Mobile Debug</h1>
      <h2>If you see this, routing works!</h2>
      <pre>{JSON.stringify(info, null, 2)}</pre>
      <button 
        onClick={() => window.location.href = '/login'}
        style={{padding: '10px', fontSize: '16px', marginTop: '10px'}}
      >
        Go to Login
      </button>
      <button 
        onClick={() => window.location.href = '/m/'}
        style={{padding: '10px', fontSize: '16px', marginTop: '10px', marginLeft: '10px'}}
      >
        Go to /m/
      </button>
    </div>
  );
};

export default MobileDebug;
