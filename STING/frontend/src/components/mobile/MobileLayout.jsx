import React from 'react';
import { Outlet } from 'react-router-dom';
import MobileHeader from './MobileHeader';
import MobileBottomNav from './MobileBottomNav';
import '../../styles/mobile.css';

/**
 * MobileLayout - Main mobile app shell
 * Contains header, content area (Outlet), and bottom navigation
 * 
 * Supports iOS safe areas for notched devices (iPhone X+)
 */
const MobileLayout = () => {
  // Inline styles for iOS Safari with safe area support
  const layoutStyle = {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100vh',
    minHeight: '100dvh', // Dynamic viewport height for mobile
    background: '#161922',
    color: '#f1f5f9',
    position: 'relative',
  };

  const contentStyle = {
    flex: 1,
    marginTop: 'calc(48px + env(safe-area-inset-top, 0px))',  // header height + safe area
    marginBottom: 'calc(60px + env(safe-area-inset-bottom, 0px))', // nav height + safe area
    overflowY: 'auto',
    overflowX: 'hidden',
    WebkitOverflowScrolling: 'touch',
    padding: '16px',
    paddingLeft: 'max(16px, env(safe-area-inset-left, 0px))',
    paddingRight: 'max(16px, env(safe-area-inset-right, 0px))',
    position: 'relative',
    minHeight: '100px',
    background: '#1a1f2e',
  };

  return (
    <div className="mobile-layout" style={layoutStyle}>
      {/* Fixed header */}
      <MobileHeader />

      {/* Main content - scrollable area */}
      <main className="mobile-content" style={contentStyle}>
        <Outlet />
      </main>

      {/* Fixed bottom navigation */}
      <MobileBottomNav />
    </div>
  );
};

export default MobileLayout;
