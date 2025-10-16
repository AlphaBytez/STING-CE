import React from 'react';
import { Alert, AlertTitle } from '@mui/material';
import { Mail as MailIcon } from '@mui/icons-material';

const AdminNotice = () => {
  // Show passwordless admin notice
  return (
    <Alert 
      severity="info" 
      icon={<MailIcon />}
      sx={{ 
        mb: 3,
        backgroundColor: 'rgba(33, 150, 243, 0.12)',
        color: '#2196f3',
        border: '2px solid #2196f3',
        '& .MuiAlert-icon': {
          color: '#2196f3'
        }
      }}
    >
      <AlertTitle sx={{ fontWeight: 'bold', fontSize: '1.1rem' }}>
        🔐 Passwordless Authentication Enabled
      </AlertTitle>
      <div style={{ marginTop: '10px' }}>
        <div style={{ marginBottom: '8px' }}>
          <strong>Default Admin:</strong> <code style={{ 
            backgroundColor: 'rgba(0,0,0,0.3)', 
            padding: '2px 6px', 
            borderRadius: '4px',
            fontSize: '0.95rem'
          }}>admin@sting.local</code>
        </div>
        <div style={{ 
          fontSize: '0.9rem', 
          color: '#1976d2',
          marginTop: '12px'
        }}>
          💡 Enter your email address to receive a magic link for login
        </div>
      </div>
    </Alert>
  );
};

export default AdminNotice;