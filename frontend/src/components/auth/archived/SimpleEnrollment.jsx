import React from 'react';
import { useNavigate } from 'react-router-dom';

const SimpleEnrollment = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="max-w-md p-8 bg-gray-800 rounded-lg">
        <h1 className="text-2xl font-bold text-white mb-4">Password Change Required</h1>
        <p className="text-gray-300 mb-6">
          You need to change your password before continuing.
        </p>
        <button
          onClick={() => {
            console.log('Clicked change password');
            window.location.href = '/dashboard';
          }}
          className="w-full py-2 px-4 bg-blue-600 text-white rounded hover:bg-blue-700"
        >
          Change Password (Testing)
        </button>
      </div>
    </div>
  );
};

export default SimpleEnrollment;