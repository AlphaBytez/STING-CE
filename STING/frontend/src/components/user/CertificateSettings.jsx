import React, { useState, useEffect } from 'react';
import { Download, CheckCircle, AlertCircle, Server, FileText, Terminal } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';

const CertificateSettings = () => {
  const { themeColors } = useTheme();
  const [certInfo, setCertInfo] = useState(null);
  const [certHealth, setCertHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Detect user's platform
  const [userPlatform, setUserPlatform] = useState('unknown');

  useEffect(() => {
    // Detect platform
    const platform = navigator.platform.toLowerCase();
    if (platform.includes('win')) {
      setUserPlatform('windows');
    } else if (platform.includes('mac')) {
      setUserPlatform('mac');
    } else if (platform.includes('linux')) {
      setUserPlatform('linux');
    }

    // Fetch certificate info
    fetchCertInfo();
    checkCertHealth();
  }, []);

  const fetchCertInfo = async () => {
    try {
      const response = await fetch('/api/config/cert/info');
      const data = await response.json();
      if (data.success) {
        setCertInfo(data);
      } else {
        setError(data.error || 'Failed to load certificate info');
      }
    } catch (err) {
      setError('Failed to connect to server');
    } finally {
      setLoading(false);
    }
  };

  const checkCertHealth = async () => {
    try {
      const response = await fetch('/api/config/cert/health');
      const data = await response.json();
      setCertHealth(data);
    } catch (err) {
      setCertHealth({ trusted: false, error: 'Could not verify certificate' });
    }
  };

  const handleDownload = async (url, filename) => {
    try {
      // Use fetch to download the file (works better with untrusted certs)
      const response = await fetch(url, {
        credentials: 'include', // Include cookies for authentication
      });

      if (!response.ok) {
        throw new Error(`Download failed: ${response.statusText}`);
      }

      // Get the file content as a blob
      const blob = await response.blob();

      // Create a download link
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = filename;
      document.body.appendChild(link);
      link.click();

      // Cleanup
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      console.error('Download error:', err);
      // Fallback: Open in new tab (user can save manually)
      window.open(url, '_blank');
    }
  };

  if (loading) {
    return (
      <div className="text-center py-8">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-yellow-500 mx-auto"></div>
        <p className="text-slate-400 mt-4">Loading certificate information...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-400" />
          <p className="text-red-400">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Certificate Management</h2>
        <p className="text-slate-400">
          Download and install the STING CA certificate to enable passkey/WebAuthn functionality
        </p>
      </div>

      {/* Certificate Health Status - Only show when certificates are available */}
      {certHealth && certInfo && certInfo.cert_available && (
        <div className={`rounded-lg p-4 border ${
          certHealth.trusted
            ? 'bg-green-500/10 border-green-500/50'
            : 'bg-amber-500/10 border-amber-500/50'
        }`}>
          <div className="flex items-start gap-3">
            {certHealth.trusted ? (
              <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
            ) : (
              <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            )}
            <div className="flex-1">
              <h3 className={`font-semibold ${certHealth.trusted ? 'text-green-400' : 'text-amber-400'}`}>
                {certHealth.trusted ? 'HTTPS Connection Active' : 'Certificate Not Trusted'}
              </h3>
              <p className={certHealth.trusted ? 'text-green-300' : 'text-amber-300'}>
                {certHealth.trusted
                  ? 'You are connected via HTTPS. If you see browser security warnings, install the CA certificate below to enable full passkey support.'
                  : 'Your browser does not trust the STING certificate. Download and install it below to enable passkeys.'}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Server Information */}
      {certInfo && (
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 mb-3">
            <Server className="w-5 h-5 text-yellow-400" />
            <h3 className="font-semibold text-white">Server Information</h3>
          </div>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-slate-400">Hostname:</span>
              <span className="text-white font-mono">{certInfo.hostname}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">IP Address:</span>
              <span className="text-white font-mono">{certInfo.ip_address}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Certificate Status:</span>
              <span className={certInfo.cert_available ? 'text-green-400' : 'text-red-400'}>
                {certInfo.cert_available ? 'Available' : 'Not Available'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Certificate Not Available Message */}
      {certInfo && !certInfo.cert_available && (
        <div className="bg-amber-500/10 border border-amber-500/50 rounded-lg p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="font-semibold text-amber-400 mb-2">Certificates Not Exported</h3>
              <p className="text-sm text-amber-200 mb-3">
                The client certificates haven't been exported yet. You need to run the export command on the STING server first.
              </p>
              <div className="bg-slate-800 rounded px-3 py-2 font-mono text-sm text-green-400 mb-2">
                msting export-certs
              </div>
              <p className="text-xs text-amber-300">
                Run this command on the server hosting STING (not in your browser). After exporting, refresh this page to download the certificates.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Download Section */}
      {certInfo && certInfo.cert_available && (
        <div className="bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-2 mb-4">
            <Download className="w-5 h-5 text-yellow-400" />
            <h3 className="font-semibold text-white">Download Certificate</h3>
          </div>

          <div className="space-y-3">
            {/* CA Certificate */}
            <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
              <div className="flex items-center gap-3">
                <FileText className="w-5 h-5 text-blue-400" />
                <div>
                  <p className="text-white font-medium">CA Certificate</p>
                  <p className="text-xs text-slate-400">sting-ca.pem</p>
                </div>
              </div>
              <button
                onClick={() => handleDownload('/api/config/cert/download', 'sting-ca.pem')}
                className="px-4 py-2 bg-yellow-500 hover:bg-yellow-600 text-black font-medium rounded-lg transition-colors"
              >
                Download
              </button>
            </div>

            {/* Platform-specific installers */}
            <div className="border-t border-slate-600 pt-3 mt-3">
              <p className="text-sm text-slate-400 mb-3">Platform-Specific Installers:</p>

              {/* Windows Installer */}
              <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg mb-2">
                <div className="flex items-center gap-3">
                  <Terminal className="w-5 h-5 text-blue-400" />
                  <div>
                    <p className="text-white font-medium">Windows Installer</p>
                    <p className="text-xs text-slate-400">PowerShell script (.ps1)</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDownload('/api/config/cert/installer/windows', 'install-ca-windows.ps1')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    userPlatform === 'windows'
                      ? 'bg-yellow-500 hover:bg-yellow-600 text-black'
                      : 'bg-slate-600 hover:bg-slate-500 text-slate-300'
                  }`}
                >
                  {userPlatform === 'windows' && '⭐ '}Download
                </button>
              </div>

              {/* macOS Installer */}
              <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg mb-2">
                <div className="flex items-center gap-3">
                  <Terminal className="w-5 h-5 text-blue-400" />
                  <div>
                    <p className="text-white font-medium">macOS Installer</p>
                    <p className="text-xs text-slate-400">Shell script (.sh)</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDownload('/api/config/cert/installer/mac', 'install-ca-mac.sh')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    userPlatform === 'mac'
                      ? 'bg-yellow-500 hover:bg-yellow-600 text-black'
                      : 'bg-slate-600 hover:bg-slate-500 text-slate-300'
                  }`}
                >
                  {userPlatform === 'mac' && '⭐ '}Download
                </button>
              </div>

              {/* Linux Installer */}
              <div className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg">
                <div className="flex items-center gap-3">
                  <Terminal className="w-5 h-5 text-blue-400" />
                  <div>
                    <p className="text-white font-medium">Linux Installer</p>
                    <p className="text-xs text-slate-400">Shell script (.sh)</p>
                  </div>
                </div>
                <button
                  onClick={() => handleDownload('/api/config/cert/installer/linux', 'install-ca-linux.sh')}
                  className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                    userPlatform === 'linux'
                      ? 'bg-yellow-500 hover:bg-yellow-600 text-black'
                      : 'bg-slate-600 hover:bg-slate-500 text-slate-300'
                  }`}
                >
                  {userPlatform === 'linux' && '⭐ '}Download
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Installation Instructions */}
      <div className="bg-blue-500/10 border border-blue-500/30 rounded-lg p-4">
        <h3 className="font-semibold text-blue-300 mb-3">Installation Instructions</h3>
        <div className="space-y-3 text-sm text-blue-200">
          <div>
            <p className="font-medium text-blue-100 mb-1">Windows:</p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Download the Windows installer script</li>
              <li>Right-click and select "Run with PowerShell"</li>
              <li>Follow the prompts to install the certificate</li>
              <li>Restart your browser</li>
            </ol>
          </div>
          <div>
            <p className="font-medium text-blue-100 mb-1">macOS:</p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Download the macOS installer script</li>
              <li>Open Terminal and navigate to the download folder</li>
              <li>Run: <code className="bg-slate-800 px-2 py-0.5 rounded">bash install-ca-mac.sh</code></li>
              <li>Enter your password when prompted</li>
              <li>Restart your browser</li>
            </ol>
          </div>
          <div>
            <p className="font-medium text-blue-100 mb-1">Linux:</p>
            <ol className="list-decimal list-inside space-y-1 ml-2">
              <li>Download the Linux installer script</li>
              <li>Open Terminal and navigate to the download folder</li>
              <li>Run: <code className="bg-slate-800 px-2 py-0.5 rounded">bash install-ca-linux.sh</code></li>
              <li>Enter your password when prompted</li>
              <li>Restart your browser</li>
            </ol>
          </div>
        </div>
      </div>

      {/* Why This is Needed */}
      <div className="bg-amber-500/10 border border-amber-500/30 rounded-lg p-4">
        <h3 className="font-semibold text-amber-300 mb-2">Why is this needed?</h3>
        <p className="text-sm text-amber-200">
          STING uses self-signed certificates for secure HTTPS communication. WebAuthn/passkey functionality
          requires a trusted HTTPS connection. Installing the STING CA certificate tells your browser to trust
          connections to STING, enabling full passkey support.
        </p>
        <p className="text-sm text-amber-200 mt-2">
          <strong>Note:</strong> You only need to install this certificate on devices where you want to use passkeys
          with STING. Email-based passwordless login works without certificate installation.
        </p>
      </div>
    </div>
  );
};

export default CertificateSettings;
