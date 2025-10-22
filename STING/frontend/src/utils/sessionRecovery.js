/**
 * Session Recovery Utility
 * Helps diagnose and recover from lost session issues
 */

import axios from 'axios';

class SessionRecovery {
  constructor() {
    this.retryAttempts = 0;
    this.maxRetries = 3;
  }

  /**
   * Check if user has a valid session
   */
  async checkSession() {
    try {
      console.log('🔍 SessionRecovery: Checking session...');
      console.log('🔍 Current cookies:', document.cookie);
      
      const response = await axios.get('/.ory/sessions/whoami', {
        withCredentials: true,
        timeout: 10000 // 10 second timeout
      });

      console.log('✅ SessionRecovery: Valid session found:', {
        identity: response.data?.identity?.traits?.email,
        aal: response.data?.authenticator_assurance_level,
        active: response.data?.active
      });

      return {
        valid: true,
        session: response.data,
        aal: response.data?.authenticator_assurance_level || 'aal1'
      };

    } catch (error) {
      console.error('❌ SessionRecovery: Session check failed:', {
        status: error.response?.status,
        message: error.message,
        cookies: document.cookie
      });

      return {
        valid: false,
        error: error.response?.status || 'unknown',
        needsLogin: error.response?.status === 401
      };
    }
  }

  /**
   * Attempt to recover a lost session
   */
  async recoverSession() {
    console.log('🔄 SessionRecovery: Attempting session recovery...');
    
    // Check if we have any session data in localStorage as backup
    const backupSessionData = localStorage.getItem('backup_session_data');
    if (backupSessionData) {
      console.log('🔍 Found backup session data');
      try {
        const parsedData = JSON.parse(backupSessionData);
        console.log('📝 Backup session:', parsedData);
      } catch (e) {
        console.error('❌ Failed to parse backup session data');
      }
    }

    // Try to refresh the session
    try {
      const refreshResponse = await axios.get('/.ory/sessions/whoami', {
        withCredentials: true,
        headers: {
          'Cache-Control': 'no-cache',
          'Pragma': 'no-cache'
        }
      });

      if (refreshResponse.data?.active) {
        console.log('✅ Session recovery successful');
        return { recovered: true, session: refreshResponse.data };
      }
    } catch (error) {
      console.error('❌ Session recovery failed:', error);
    }

    return { recovered: false };
  }

  /**
   * Clear any stale session data
   */
  clearStaleSession() {
    console.log('🧹 SessionRecovery: Clearing stale session data...');
    
    // Clear any stored session backup
    localStorage.removeItem('backup_session_data');
    
    // Clear any AAL2 flow storage that might be stale
    sessionStorage.removeItem('aal2_passkey_setup');
    sessionStorage.removeItem('aal2_return_to');
    sessionStorage.removeItem('aal2_passkey_created');
    
    console.log('✅ Stale session data cleared');
  }

  /**
   * Enhanced redirect that preserves session context
   */
  safeRedirect(url, reason = 'unknown') {
    console.log(`🔀 SessionRecovery: Safe redirect to ${url} (reason: ${reason})`);
    
    // Store current session state as backup
    this.checkSession().then(sessionCheck => {
      if (sessionCheck.valid) {
        localStorage.setItem('backup_session_data', JSON.stringify({
          timestamp: Date.now(),
          session: sessionCheck.session,
          reason: reason,
          from: window.location.href
        }));
      }
      
      // Perform the redirect
      window.location.href = url;
    }).catch(error => {
      console.error('❌ Failed to backup session before redirect:', error);
      // Redirect anyway
      window.location.href = url;
    });
  }

  /**
   * Monitor session during page lifecycle
   */
  startSessionMonitoring() {
    console.log('👀 SessionRecovery: Starting session monitoring...');
    
    // Check session on page visibility change
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) {
        console.log('👀 Page became visible, checking session...');
        this.checkSession();
      }
    });

    // Check session on focus
    window.addEventListener('focus', () => {
      console.log('👀 Window focused, checking session...');
      this.checkSession();
    });
  }

  /**
   * Get detailed cookie diagnostics
   */
  getCookieDiagnostics() {
    const allCookies = document.cookie;
    const kratosCookie = allCookies.split(';').find(c => c.trim().startsWith('ory_kratos_session='));
    
    return {
      hasCookies: !!allCookies,
      hasKratosCookie: !!kratosCookie,
      allCookies: allCookies,
      kratosCookie: kratosCookie?.trim(),
      cookieCount: allCookies ? allCookies.split(';').length : 0,
      domain: window.location.hostname,
      port: window.location.port,
      protocol: window.location.protocol,
      userAgent: navigator.userAgent.substring(0, 100) + '...'
    };
  }
}

// Export singleton instance
const sessionRecovery = new SessionRecovery();
export default sessionRecovery;