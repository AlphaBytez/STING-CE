/**
 * SimpleWebAuthnSetup - Reliable WebAuthn setup using backend API
 * Eliminates frontend credential processing complexity
 */

import React, { useState } from 'react';
import { Fingerprint, Shield, AlertCircle, Smartphone } from 'lucide-react';
import { startRegistration } from '@simplewebauthn/browser';
import axios from 'axios';

const SimpleWebAuthnSetup = ({ onSetupComplete, onCancel }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [deviceName, setDeviceName] = useState('');
  const [step, setStep] = useState('name'); // name, register, complete

  /**
   * Start passkey registration using backend API
   */
  const startPasskeyRegistration = async () => {
    if (!deviceName.trim()) {
      setError('Please enter a device name');
      return;
    }
    
    setIsLoading(true);
    setError('');
    setStep('register');
    
    try {
      console.log('🔐 Starting passkey registration via backend API...');
      
      // Get registration options from backend
      const optionsResponse = await axios.post('/api/webauthn-enrollment/setup/begin', {
        device_name: deviceName
      }, {
        withCredentials: true,
        headers: { 'Accept': 'application/json' }
      });
      
      if (!optionsResponse.data.success) {
        throw new Error(optionsResponse.data.error || 'Failed to get registration options');
      }
      
      const { options } = optionsResponse.data;
      console.log('🔐 WebAuthn options received, starting browser registration...');
      
      // Use @simplewebauthn/browser to handle the ceremony
      const credential = await startRegistration(options.publicKey);
      console.log('✅ WebAuthn credential created successfully');
      
      // Send credential to backend for verification and storage
      console.log('🔐 Sending credential to backend for verification...');
      const completeResponse = await axios.post('/api/webauthn-enrollment/setup/complete', {
        credential: credential
      }, {
        withCredentials: true,
        headers: { 'Accept': 'application/json' }
      });
      
      if (completeResponse.data.success) {
        console.log('✅ Passkey registration completed successfully');
        setStep('complete');
        
        // Call completion callback
        if (onSetupComplete) {
          setTimeout(() => {
            onSetupComplete('webauthn', { 
              hasPasskey: true, 
              method: 'backend-api',
              deviceName: deviceName,
              credentialId: completeResponse.data.credential_id
            });
          }, 1000);
        }
      } else {
        throw new Error(completeResponse.data.error || 'Passkey registration failed');
      }
      
    } catch (error) {
      console.error('❌ Passkey registration failed:', error);
      
      if (error.name === 'NotAllowedError') {
        setError('Passkey registration was cancelled or not allowed');
      } else if (error.name === 'AbortError') {
        setError('Passkey registration was aborted');
      } else if (error.response?.data?.error) {
        setError(error.response.data.error);
      } else {
        setError('Passkey registration failed. Please try again.');
      }
      
      setStep('name'); // Back to name entry
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-500/20 border border-red-500/50 text-red-200 px-4 py-3 rounded-lg flex items-start space-x-3">
          <AlertCircle className="h-5 w-5 text-red-400 mt-0.5 flex-shrink-0" />
          <div>
            <p className="font-medium">Registration Error</p>
            <p className="text-sm opacity-90">{error}</p>
          </div>
        </div>
      )}

      {step === 'name' && (
        <div>
          <div className="text-center mb-6">
            <Fingerprint className="w-12 h-12 text-blue-400 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-white">Set Up Passkey</h3>
            <p className="text-gray-400 text-sm">
              Secure your account with biometric authentication
            </p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Device Name (for your reference)
              </label>
              <input
                type="text"
                value={deviceName}
                onChange={(e) => setDeviceName(e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400"
                placeholder="e.g., My iPhone, Work Laptop"
                disabled={isLoading}
                autoFocus
              />
            </div>

            <button
              onClick={startPasskeyRegistration}
              disabled={isLoading || !deviceName.trim()}
              className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white font-medium rounded-lg transition-colors flex items-center justify-center space-x-2"
            >
              {isLoading ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-t-2 border-b-2 border-white"></div>
                  <span>Setting up...</span>
                </>
              ) : (
                <>
                  <Fingerprint className="w-4 h-4" />
                  <span>Create Passkey</span>
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {step === 'register' && (
        <div className="text-center">
          <Smartphone className="w-12 h-12 text-blue-400 mx-auto mb-4 animate-pulse" />
          <h3 className="text-lg font-semibold text-white mb-2">Complete on Your Device</h3>
          <p className="text-gray-400 text-sm mb-4">
            Follow the prompts on your device to create your passkey
          </p>
          <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-blue-400 mx-auto"></div>
          <p className="text-gray-500 text-xs mt-2">Waiting for device interaction...</p>
        </div>
      )}

      {step === 'complete' && (
        <div className="text-center">
          <Shield className="w-12 h-12 text-green-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Passkey Setup Complete!</h3>
          <p className="text-gray-400">
            Device "{deviceName}" has been registered successfully.
          </p>
        </div>
      )}
    </div>
  );
};

export default SimpleWebAuthnSetup;