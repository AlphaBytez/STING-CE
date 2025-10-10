import React, { useState, useEffect } from 'react';
import {
  Shield,
  Download,
  RefreshCw,
  Trash2,
  Eye,
  EyeOff,
  AlertCircle,
  CheckCircle,
  Copy,
  Lock
} from 'lucide-react';
import axios from 'axios';
import {
  handleReturnFromAuth,
  checkOperationAuth,
  clearAuthMarker,
  OPERATIONS
} from '../../utils/tieredAuth';

// Define operations for recovery codes
const RECOVERY_OPERATIONS = {
  GENERATE_CODES: {
    name: 'GENERATE_RECOVERY_CODES',
    tier: 3,
    description: 'Generate new recovery codes'
  },
  REVOKE_CODES: {
    name: 'REVOKE_RECOVERY_CODES',
    tier: 4,
    description: 'Revoke all recovery codes'
  },
  VIEW_CODES: {
    name: 'VIEW_RECOVERY_CODES',
    tier: 2,
    description: 'View recovery codes status'
  }
};

const RecoveryCodesSettings = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [generatedCodes, setGeneratedCodes] = useState(null);
  const [showCodes, setShowCodes] = useState(false);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    // Handle return from authentication flow
    const justAuthenticatedGenerate = handleReturnFromAuth(RECOVERY_OPERATIONS.GENERATE_CODES.name);
    const justAuthenticatedRevoke = handleReturnFromAuth(RECOVERY_OPERATIONS.REVOKE_CODES.name);

    if (justAuthenticatedGenerate || justAuthenticatedRevoke) {
      setError(null);
    }

    // Load initial status
    loadStatus();
  }, []);

  const loadStatus = async () => {
    try {
      setLoading(true);
      const response = await axios.get('/api/recovery/codes/status', {
        withCredentials: true
      });
      setStatus(response.data.status);
      setError(null);
    } catch (err) {
      console.error('Failed to load recovery codes status:', err);
      setError('Failed to load recovery codes status');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateCodes = async () => {
    // Check authentication BEFORE generating codes
    const canProceed = await checkOperationAuth(
      RECOVERY_OPERATIONS.GENERATE_CODES.name,
      RECOVERY_OPERATIONS.GENERATE_CODES.tier
    );

    if (!canProceed) {
      // User was redirected to security-upgrade
      return;
    }

    try {
      console.log('🔄 Generating recovery codes (authentication pre-verified)');

      const response = await axios.post('/api/recovery/codes/generate', {
        count: 10
      }, {
        withCredentials: true
      });

      setGeneratedCodes(response.data.codes);
      setShowCodes(true);

      // Clear auth markers since operation succeeded
      clearAuthMarker(RECOVERY_OPERATIONS.GENERATE_CODES.name);

      // Reload status
      await loadStatus();

    } catch (err) {
      console.error('❌ Recovery codes generation failed:', err);
      setError(err.response?.data?.error || 'Failed to generate recovery codes');
    }
  };

  const handleRevokeCodes = async () => {
    if (!window.confirm('Are you sure you want to revoke all recovery codes? This cannot be undone.')) {
      return;
    }

    // Check authentication for critical operation
    const canProceed = await checkOperationAuth(
      RECOVERY_OPERATIONS.REVOKE_CODES.name,
      RECOVERY_OPERATIONS.REVOKE_CODES.tier
    );

    if (!canProceed) {
      // User was redirected to security-upgrade
      return;
    }

    try {
      console.log('🔄 Revoking recovery codes (authentication pre-verified)');

      await axios.post('/api/recovery/codes/revoke', {}, {
        withCredentials: true
      });

      // Clear auth markers since operation succeeded
      clearAuthMarker(RECOVERY_OPERATIONS.REVOKE_CODES.name);

      // Reload status
      await loadStatus();

      setGeneratedCodes(null);
      setShowCodes(false);

    } catch (err) {
      console.error('❌ Recovery codes revocation failed:', err);
      setError(err.response?.data?.error || 'Failed to revoke recovery codes');
    }
  };

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy to clipboard:', err);
    }
  };

  const copyAllCodes = () => {
    if (generatedCodes) {
      const codesText = generatedCodes.join('\n');
      copyToClipboard(codesText);
    }
  };

  const downloadCodes = () => {
    if (generatedCodes) {
      const codesText = generatedCodes.join('\n');
      const blob = new Blob([codesText], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'sting-recovery-codes.txt';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-yellow-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
        <div className="flex items-center gap-3 mb-4">
          <Shield className="w-6 h-6 text-yellow-400" />
          <h2 className="text-xl font-semibold text-white">Recovery Codes</h2>
        </div>

        <p className="text-gray-300 mb-6">
          Recovery codes are backup authentication methods that allow you to access your account
          if you lose access to your primary authentication methods (passkey, TOTP).
        </p>

        {error && (
          <div className="bg-red-900/20 border border-red-800/50 rounded-lg p-4 mb-6">
            <div className="flex items-center gap-2 text-red-300">
              <AlertCircle className="w-4 h-4" />
              <span className="font-medium">Error</span>
            </div>
            <p className="text-sm text-red-400 mt-2">{error}</p>
            <button
              onClick={() => setError(null)}
              className="text-red-400 underline text-xs mt-2"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Status Display */}
        {status && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-white">{status.valid_codes}</div>
              <div className="text-sm text-gray-400">Valid Codes</div>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-orange-400">{status.used_codes}</div>
              <div className="text-sm text-gray-400">Used Codes</div>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-red-400">{status.expired_codes}</div>
              <div className="text-sm text-gray-400">Expired Codes</div>
            </div>
            <div className="bg-slate-700 rounded-lg p-4">
              <div className="text-2xl font-bold text-blue-400">{status.total_codes}</div>
              <div className="text-sm text-gray-400">Total Generated</div>
            </div>
          </div>
        )}

        {/* Status Indicator */}
        {status && (
          <div className="mb-6">
            {status.valid_codes > 0 ? (
              <div className="flex items-center gap-2 text-green-400">
                <CheckCircle className="w-5 h-5" />
                <span>You have {status.valid_codes} valid recovery codes</span>
              </div>
            ) : (
              <div className="flex items-center gap-2 text-yellow-400">
                <AlertCircle className="w-5 h-5" />
                <span>No valid recovery codes - generate some for backup access</span>
              </div>
            )}
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-3 mb-6">
          <button
            onClick={handleGenerateCodes}
            className="px-4 py-2 bg-yellow-500 text-black rounded-lg hover:bg-yellow-400 transition-colors font-medium flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            Generate New Codes
          </button>

          {status?.valid_codes > 0 && (
            <button
              onClick={handleRevokeCodes}
              className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium flex items-center gap-2"
            >
              <Trash2 className="w-4 h-4" />
              Revoke All Codes
            </button>
          )}
        </div>

        {/* Security Tiers Info */}
        <div className="bg-blue-900/20 border border-blue-800/50 rounded-lg p-4">
          <h4 className="text-blue-300 font-medium mb-2 flex items-center gap-2">
            <Lock className="w-4 h-4" />
            Security Requirements
          </h4>
          <div className="text-sm text-blue-200 space-y-1">
            <div>• Generate codes: <span className="font-mono">Tier 3</span> (Passkey or TOTP required)</div>
            <div>• Revoke codes: <span className="font-mono">Tier 4</span> (Dual-factor authentication required)</div>
            <div>• View status: <span className="font-mono">Tier 2</span> (Any authentication method)</div>
          </div>
        </div>
      </div>

      {/* Generated Codes Display */}
      {generatedCodes && (
        <div className="bg-slate-800 rounded-lg p-6 border border-slate-700">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Your Recovery Codes</h3>
            <button
              onClick={() => setShowCodes(!showCodes)}
              className="text-gray-400 hover:text-white transition-colors"
            >
              {showCodes ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
            </button>
          </div>

          <div className="bg-yellow-900/20 border border-yellow-800/50 rounded-lg p-4 mb-4">
            <div className="flex items-center gap-2 text-yellow-300 mb-2">
              <AlertCircle className="w-4 h-4" />
              <span className="font-medium">Important</span>
            </div>
            <p className="text-sm text-yellow-200">
              Save these codes in a secure location. They will not be shown again and can be used only once each.
            </p>
          </div>

          {showCodes && (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {generatedCodes.map((code, index) => (
                  <div key={index} className="bg-slate-700 rounded p-3 font-mono text-sm">
                    <div className="flex justify-between items-center">
                      <span className="text-white">{code}</span>
                      <button
                        onClick={() => copyToClipboard(code)}
                        className="text-gray-400 hover:text-white transition-colors"
                      >
                        <Copy className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="flex gap-3">
                <button
                  onClick={copyAllCodes}
                  className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-500 transition-colors flex items-center gap-2"
                >
                  <Copy className="w-4 h-4" />
                  {copied ? 'Copied!' : 'Copy All'}
                </button>
                <button
                  onClick={downloadCodes}
                  className="px-4 py-2 bg-slate-600 text-white rounded-lg hover:bg-slate-500 transition-colors flex items-center gap-2"
                >
                  <Download className="w-4 h-4" />
                  Download
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default RecoveryCodesSettings;