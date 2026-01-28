import React from 'react';
import { Spin } from 'antd';
import '../../styles/mobile.css';

/**
 * MobileLoadingSpinner - Loading state for mobile pages
 * Uses consistent styling with the mobile design system
 */
const MobileLoadingSpinner = () => {
  return (
    <div className="mobile-loading-spinner" style={{ background: 'var(--mobile-bg)', minHeight: '100%' }}>
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--mobile-space-xl)',
      }}>
        <Spin size="large" style={{ color: 'var(--mobile-primary)' }} />
        <span className="loading-text" style={{
          marginTop: 'var(--mobile-space-md)',
          fontSize: 'var(--mobile-font-md)',
          color: 'var(--mobile-text-secondary)',
        }}>
          Loading...
        </span>
      </div>
    </div>
  );
};

export default MobileLoadingSpinner;
