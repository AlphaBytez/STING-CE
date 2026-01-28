import React, { useState, useEffect } from 'react';
import { Mail, AlertCircle, CheckCircle } from 'lucide-react';
import { useKratos } from '../../auth/KratosProviderRefactored';
import axios from 'axios';

const EmailSettings = () => {
  const { identity, kratosUrl } = useKratos();
  const [currentEmail, setCurrentEmail] = useState('');
  const [newEmail, setNewEmail] = useState('');
  const [isVerified, setIsVerified] = useState(false);
  const [isChanging, setIsChanging] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadEmailSettings = async () => {
      try {
        if (identity) {
          setCurrentEmail(identity.traits.email || '');
          // Check if email is verified from identity data
          setIsVerified(
            identity.verifiable_addresses?.some(addr => addr.verified) || false
          );
        }
      } catch (error) {
        console.error('Error loading email settings:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadEmailSettings();
  }, [identity]);

  const handleEmailChange = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setIsChanging(true);

    try {
      // In a real implementation, you would use Kratos settings flow to update email
      // For example, starting a settings flow for email change
      
      // Example (not implemented here):
      // 1. Initiate settings flow with Kratos
      // 2. Submit the form with the new email
      
      setSuccess('Verification email sent. Please check your inbox.');
      // Don't update currentEmail until it's verified
    } catch (err) {
      setError('Failed to update email. Please try again.');
    } finally {
      setIsChanging(false);
    }
  };

  const resendVerification = async () => {
    console.log('🔍 Resend verification clicked');
    console.log('Current email:', currentEmail);
    
    setError('');
    setSuccess('');

    try {
      // Step 1: Create a new verification flow
      console.log('Creating verification flow...');
      const flowResponse = await axios.get('/.ory/self-service/verification/browser', {
        headers: { 'Accept': 'application/json' },
        withCredentials: true
      });

      console.log('Flow response:', flowResponse.data);
      const flowId = flowResponse.data.id;
      const csrfToken = flowResponse.data.ui.nodes.find(n => n.attributes?.name === 'csrf_token')?.attributes?.value;
      
      console.log('Flow ID:', flowId);
      console.log('CSRF Token:', csrfToken);

      // Step 2: Submit the verification request with the current email
      console.log('Submitting verification request...');
      const submitResponse = await axios.post(`/.ory/self-service/verification?flow=${flowId}`, 
        new URLSearchParams({
          email: currentEmail,
          method: 'code',
          csrf_token: csrfToken
        }),
        {
          headers: { 
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
          },
          withCredentials: true
        }
      );
      
      console.log('Submit response:', submitResponse.data);
      setSuccess('Verification email sent. Please check your inbox.');
    } catch (err) {
      console.error('Verification error:', err);
      console.error('Error response:', err.response?.data);
      console.error('Error status:', err.response?.status);
      setError(err.response?.data?.error?.message || 'Failed to send verification email. Please try again.');
    }
  };

  if (isLoading) {
    return <div>Loading...</div>;
  }

  return (
    <div className="max-w-md mx-auto">
      <h2 className="text-xl font-semibold mb-6">Email Settings</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-900 text-red-300 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-5 h-5" />
          {error}
        </div>
      )}

      {success && (
        <div className="mb-4 p-3 bg-green-900 text-green-300 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-5 h-5" />
          {success}
        </div>
      )}

      <div className="mb-6 p-4 bg-gray-800 rounded-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Mail className="w-5 h-5 text-gray-400" />
            <div>
              <p className="font-medium text-gray-200">{currentEmail}</p>
              <p className="text-sm text-gray-400">Current Email</p>
            </div>
          </div>
          {isVerified ? (
            <span className="px-2 py-1 bg-green-900 text-green-300 text-sm rounded-full">
              Verified
            </span>
          ) : (
            <button
              onClick={resendVerification}
              className="text-yellow-600 hover:text-yellow-700 text-sm"
            >
              Resend Verification
            </button>
          )}
        </div>
      </div>

      <form onSubmit={handleEmailChange} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            New Email Address
          </label>
          <input
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            className="w-full px-4 py-2 border rounded-lg focus:ring-yellow-400 focus:border-yellow-400"
            placeholder="Enter new email address"
            required
          />
        </div>

        <button
          type="submit"
          disabled={isChanging || !newEmail}
          className="w-full bg-yellow-400 text-gray-900 py-2 px-4 rounded-lg hover:bg-yellow-500 
                   disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {isChanging ? 'Updating Email...' : 'Update Email'}
        </button>

        <div className="mt-4 text-sm text-gray-600">
          <h3 className="font-medium text-gray-700 mb-2">Please Note:</h3>
          <ul className="list-disc pl-5 space-y-1">
            <li>You'll need to verify your new email address</li>
            <li>Your current email will remain active until verification</li>
            <li>Important notifications will be sent to your verified email</li>
          </ul>
        </div>
      </form>
    </div>
  );
};

export default EmailSettings;