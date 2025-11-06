import React, { useState, useEffect } from 'react';
import { AlertTriangle, ExternalLink, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';

/**
 * CertificateWarning - Shows warning when certificates aren't trusted
 * Used in passkey/WebAuthn setup flows to guide users
 */
const CertificateWarning = ({ className = '' }) => {
  const [certStatus, setCertStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkCertStatus = async () => {
      try {
        // Check if we're on localhost - no cert needed
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
          setCertStatus({ needed: false, reason: 'localhost' });
          setLoading(false);
          return;
        }

        // Check if connection is HTTPS
        if (window.location.protocol !== 'https:') {
          setCertStatus({ needed: true, reason: 'no-https', available: false });
          setLoading(false);
          return;
        }

        // Fetch cert info to see if certs are available for download
        const response = await fetch('/api/config/cert/info');
        const data = await response.json();

        if (data.success && data.cert_available) {
          // Certificates are available but we're already on HTTPS
          // Check if user might be seeing browser warnings
          setCertStatus({
            needed: true,
            reason: 'cert-available',
            available: true,
            hostname: data.hostname
          });
        } else {
          // No certs available, needs to run export-certs
          setCertStatus({
            needed: true,
            reason: 'cert-not-exported',
            available: false
          });
        }
      } catch (error) {
        console.error('Error checking cert status:', error);
        setCertStatus({ needed: true, reason: 'unknown', available: false });
      } finally {
        setLoading(false);
      }
    };

    checkCertStatus();
  }, []);

  // Don't show anything while loading
  if (loading) {
    return null;
  }

  // Don't show if certificates aren't needed (localhost)
  if (!certStatus?.needed) {
    return null;
  }

  // Show appropriate warning based on status
  return (
    <div className={`bg-amber-900/30 border border-amber-700 rounded-lg p-4 ${className}`}>
      <div className="flex items-start space-x-3">
        <AlertTriangle className="w-5 h-5 text-amber-500 mt-0.5 flex-shrink-0" />
        <div className="flex-1">
          <p className="font-medium text-amber-300 mb-2 flex items-center gap-2">
            <Shield className="w-4 h-4" />
            Certificate Installation Required for Passkeys
          </p>

          {certStatus.reason === 'no-https' && (
            <>
              <p className="text-sm text-gray-300 mb-3">
                You're not connected via HTTPS. WebAuthn/Passkeys require a secure HTTPS connection.
              </p>
              <p className="text-sm text-gray-400">
                Please access STING via HTTPS to use passkey authentication.
              </p>
            </>
          )}

          {certStatus.reason === 'cert-not-exported' && (
            <>
              <p className="text-sm text-gray-300 mb-3">
                Passkeys require a trusted HTTPS certificate. The server certificates haven't been exported yet.
              </p>
              <div className="bg-slate-800/50 rounded px-3 py-2 font-mono text-sm text-green-400 mb-3">
                msting export-certs
              </div>
              <p className="text-xs text-gray-400">
                Run this command on the STING server to export certificates for client installation.
              </p>
            </>
          )}

          {certStatus.reason === 'cert-available' && (
            <>
              <p className="text-sm text-gray-300 mb-3">
                Passkeys require a trusted HTTPS certificate. If you're seeing browser security warnings,
                you need to install the STING CA certificate on this device.
              </p>
              <ul className="text-sm text-gray-300 mb-3 space-y-1 list-disc list-inside">
                <li>Download and install the CA certificate for your operating system</li>
                <li>Restart your browser after installation</li>
                <li>Return to this page to set up passkeys</li>
              </ul>
              <Link
                to="/settings/certificates"
                className="inline-flex items-center gap-2 text-sm text-amber-300 hover:text-amber-200 font-medium"
              >
                Go to Certificate Settings
                <ExternalLink className="w-4 h-4" />
              </Link>

              <div className="mt-3 pt-3 border-t border-amber-700/50">
                <p className="text-xs text-gray-400">
                  <strong>Alternative:</strong> You can still use TOTP (authenticator app) or email codes
                  for two-factor authentication without installing certificates.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default CertificateWarning;
