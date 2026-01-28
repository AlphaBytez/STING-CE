import React from 'react';
import { Outlet } from 'react-router-dom';
import MobileHeader from './MobileHeader';
import MobileBottomNav from './MobileBottomNav';
import '../../styles/mobile.css';

/**
 * MobileLayout - Main mobile app shell
 * Contains header, content area (Outlet), and bottom navigation
 * 
 * DEBUG MODE: Using inline styles to bypass potential CSS loading issues on iOS Safari
 */
const MobileLayout = () => {
  // Inline styles for iOS Safari debugging
  const layoutStyle = {
    display: 'flex',
    flexDirection: 'column',
    minHeight: '100vh',
    background: '#161922',
    color: '#f1f5f9',
    position: 'relative',
  };

  const contentStyle = {
    flex: 1,
    marginTop: '48px',  // header height
    marginBottom: '60px', // nav height
    overflowY: 'auto',
    overflowX: 'hidden',
    WebkitOverflowScrolling: 'touch',
    padding: '16px',
    position: 'relative',
    minHeight: '100px',
    // DEBUG: Add visible background to confirm content area renders
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
