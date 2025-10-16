import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Mail, CheckCircle, ArrowRight, RefreshCw } from 'lucide-react';

const EmailVerificationPrompt = ({ email, onResend }) => {
  const navigate = useNavigate();

  return (
    <div className="p-6 bg-yellow-900/20 border border-yellow-800 rounded-lg">
      <div className="flex items-start space-x-3">
        <Mail className="w-6 h-6 text-yellow-500 mt-1" />
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-yellow-100 mb-2">
            Verify Your Email
          </h3>
          <p className="text-gray-300 mb-4">
            Your account has been created successfully! To access all features, 
            please verify your email address: <strong className="text-white">{email}</strong>
          </p>
          
          <div className="space-y-3">
            <button
              onClick={() => navigate('/verification')}
              className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-yellow-600 hover:bg-yellow-700 text-white rounded-lg transition-colors"
            >
              <CheckCircle className="w-5 h-5" />
              <span>Verify Email Now</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            
            {onResend && (
              <button
                onClick={onResend}
                className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-lg transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                <span>Resend Verification Email</span>
              </button>
            )}
          </div>
          
          <p className="text-sm text-gray-400 mt-4">
            You can still use basic features, but some functionality requires a verified email.
          </p>
        </div>
      </div>
    </div>
  );
};

export default EmailVerificationPrompt;