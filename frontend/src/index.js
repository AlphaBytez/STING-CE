import React from 'react';
import ReactDOM from 'react-dom/client';
// Authentication now handled by Ory Kratos and Ory Elements
import './index.css';
import './styles/animations.css';
import App from './App';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
    <React.StrictMode>
        <App />
    </React.StrictMode>
);