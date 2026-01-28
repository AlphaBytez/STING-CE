import React from 'react';
import ReactDOM from 'react-dom/client';
// Authentication now handled by Ory Kratos and Ory Elements
import './index.css';
import './styles/animations.css';
import App from './App';

// Global error handler to suppress non-critical Kratos webauthn.js errors
window.addEventListener('error', (event) => {
  // Suppress the "Cannot set properties of null (setting 'value')" error from webauthn.js
  if (event.message && event.message.includes('Cannot set properties of null')) {
    console.warn('⚠️ Suppressed non-critical webauthn.js DOM error:', event.message);
    event.preventDefault();
    return true;
  }

  // Also catch variations of this error
  if (event.message && (
    event.message.includes('Cannot set property') ||
    event.message.includes('null is not an object') ||
    event.message.includes('Cannot read property') && event.message.includes('null')
  )) {
    // Only suppress if it's related to webauthn
    const stack = event.error?.stack || '';
    if (stack.includes('webauthn') || stack.includes('ory')) {
      console.warn('⚠️ Suppressed non-critical Kratos error:', event.message);
      event.preventDefault();
      return true;
    }
  }
}, true); // Use capture phase to catch errors before they bubble

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);