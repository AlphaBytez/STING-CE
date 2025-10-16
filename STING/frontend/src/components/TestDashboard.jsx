import React from 'react';

/**
 * Test Dashboard with a VERY distinctive appearance
 * This is just to verify routing and component loading
 * Last updated: ${new Date().toISOString()}
 */
const TestDashboard = () => {
  return (
    <div style={{
      padding: '20px',
      background: 'linear-gradient(to right, #ff0000, #00ff00)',
      height: '100vh',
      color: 'white',
      textAlign: 'center'
    }}>
      <h1 style={{ fontSize: '48px', marginBottom: '40px' }}>
        TEST DASHBOARD - DISTINCTIVE DESIGN
      </h1>
      
      <div style={{ 
        background: 'rgba(0,0,0,0.7)', 
        padding: '30px', 
        borderRadius: '15px',
        maxWidth: '800px',
        margin: '0 auto',
        boxShadow: '0 10px 20px rgba(0,0,0,0.5)'
      }}>
        <h2 style={{ fontSize: '32px', marginBottom: '20px' }}>
          If you can see this, component loading is working!
        </h2>
        
        <p style={{ fontSize: '20px' }}>
          This test confirms the dashboard component is correctly rendered and not being overridden.
        </p>
        
        <p style={{ fontSize: '20px', color: 'yellow', marginTop: '20px' }}>
          Timestamp: {new Date().toLocaleString()}
        </p>
        
        <div style={{ marginTop: '40px' }}>
          <button style={{
            background: 'yellow',
            color: 'black',
            padding: '15px 30px',
            fontSize: '24px',
            borderRadius: '50px',
            border: 'none',
            cursor: 'pointer'
          }}>
            Test Button
          </button>
        </div>
      </div>
    </div>
  );
};

export default TestDashboard;