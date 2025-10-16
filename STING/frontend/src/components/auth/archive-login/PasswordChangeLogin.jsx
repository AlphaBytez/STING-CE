import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Lock, AlertCircle, Shield, CheckCircle } from 'lucide-react';
import { useTheme } from '../../context/ThemeContext';
import axios from 'axios';

const PasswordChangeLogin = () => {
    const navigate = useNavigate();
    const { themeColors } = useTheme();
    
    const [step, setStep] = useState('login'); // login or change-password
    const [email, setEmail] = useState('');
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState(false);
    const [sessionData, setSessionData] = useState(null);
    
    // Password strength checker
    const checkPasswordStrength = (password) => {
        const criteria = {
            length: password.length >= 12,
            uppercase: /[A-Z]/.test(password),
            lowercase: /[a-z]/.test(password),
            numbers: /\d/.test(password),
            special: /[!@#$%^&*(),.?":{}|<>]/.test(password)
        };
        
        const strength = Object.values(criteria).filter(Boolean).length;
        return { criteria, strength };
    };
    
    const handleInitialLogin = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');
        
        try {
            // First, try to login normally
            const loginResponse = await axios.post('/api/auth/login', {
                email,
                password: currentPassword,
                password_change_flow: true
            });
            
            // If we get a PASSWORD_CHANGE_REQUIRED error, that's expected
            setSessionData(loginResponse.data);
            setStep('change-password');
            
        } catch (err) {
            if (err.response?.data?.code === 'PASSWORD_CHANGE_REQUIRED') {
                // Expected - move to password change step
                setStep('change-password');
            } else if (err.response?.status === 403 && err.response?.data?.code === 'PASSWORD_CHANGE_REQUIRED') {
                // Also expected - the middleware caught it
                setStep('change-password');
            } else {
                setError(err.response?.data?.error || 'Login failed. Please check your credentials.');
            }
        } finally {
            setLoading(false);
        }
    };
    
    const handlePasswordChange = async (e) => {
        e.preventDefault();
        
        if (newPassword !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }
        
        const { strength } = checkPasswordStrength(newPassword);
        if (strength < 4) {
            setError('Password does not meet security requirements');
            return;
        }
        
        setLoading(true);
        setError('');
        
        try {
            // Change the password
            const response = await axios.post('/api/auth/change-password', {
                current_password: currentPassword,
                new_password: newPassword
            }, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true
            });
            
            if (response.data.success) {
                setSuccess(true);
                // Wait a moment to show success, then redirect
                setTimeout(() => {
                    navigate('/dashboard');
                }, 2000);
            }
        } catch (err) {
            setError(err.response?.data?.error || 'Failed to change password');
        } finally {
            setLoading(false);
        }
    };
    
    const passwordStrength = checkPasswordStrength(newPassword);
    
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-900 px-4">
            <div className="max-w-md w-full space-y-8">
                <div className="text-center">
                    <div className="flex justify-center mb-4">
                        <div className="p-3 bg-yellow-500/10 rounded-full">
                            <Shield className="w-12 h-12 text-yellow-500" />
                        </div>
                    </div>
                    <h2 className="text-3xl font-extrabold text-white">
                        {step === 'login' ? 'Security Login' : 'Password Update Required'}
                    </h2>
                    <p className="mt-2 text-gray-400">
                        {step === 'login' 
                            ? 'Please login to update your password'
                            : 'Your password must be changed before continuing'
                        }
                    </p>
                </div>
                
                {success ? (
                    <div className="bg-green-500/10 border border-green-500 rounded-lg p-6 text-center">
                        <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                        <h3 className="text-xl font-semibold text-green-400 mb-2">
                            Password Changed Successfully!
                        </h3>
                        <p className="text-gray-300">
                            Redirecting to dashboard...
                        </p>
                    </div>
                ) : (
                    <>
                        {error && (
                            <div className="bg-red-500/10 border border-red-500 text-red-400 px-4 py-3 rounded-lg flex items-start">
                                <AlertCircle className="w-5 h-5 mr-2 flex-shrink-0 mt-0.5" />
                                <span>{error}</span>
                            </div>
                        )}
                        
                        {step === 'login' ? (
                            <form className="mt-8 space-y-6" onSubmit={handleInitialLogin}>
                                <div className="space-y-4">
                                    <div>
                                        <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-1">
                                            Email
                                        </label>
                                        <input
                                            id="email"
                                            type="email"
                                            value={email}
                                            onChange={(e) => setEmail(e.target.value)}
                                            required
                                            className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                                            placeholder="admin@sting.local"
                                        />
                                    </div>
                                    
                                    <div>
                                        <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-1">
                                            Current Password
                                        </label>
                                        <input
                                            id="password"
                                            type="password"
                                            value={currentPassword}
                                            onChange={(e) => setCurrentPassword(e.target.value)}
                                            required
                                            className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                                            placeholder="Enter your current password"
                                        />
                                    </div>
                                </div>
                                
                                <button
                                    type="submit"
                                    disabled={loading}
                                    className="w-full py-3 px-4 bg-yellow-500 hover:bg-yellow-400 disabled:bg-yellow-600 disabled:cursor-not-allowed text-black font-semibold rounded-lg transition-colors flex items-center justify-center"
                                >
                                    {loading ? (
                                        <>
                                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-black mr-2"></div>
                                            Verifying...
                                        </>
                                    ) : (
                                        <>
                                            <Lock className="w-5 h-5 mr-2" />
                                            Continue to Password Change
                                        </>
                                    )}
                                </button>
                            </form>
                        ) : (
                            <form className="mt-8 space-y-6" onSubmit={handlePasswordChange}>
                                <div className="space-y-4">
                                    <div>
                                        <label htmlFor="new-password" className="block text-sm font-medium text-gray-300 mb-1">
                                            New Password
                                        </label>
                                        <input
                                            id="new-password"
                                            type="password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            required
                                            className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                                            placeholder="Enter new password"
                                        />
                                    </div>
                                    
                                    <div>
                                        <label htmlFor="confirm-password" className="block text-sm font-medium text-gray-300 mb-1">
                                            Confirm New Password
                                        </label>
                                        <input
                                            id="confirm-password"
                                            type="password"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            required
                                            className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-yellow-500 focus:border-transparent"
                                            placeholder="Confirm new password"
                                        />
                                    </div>
                                    
                                    {newPassword && (
                                        <div className="bg-gray-800 rounded-lg p-4 space-y-2">
                                            <p className="text-sm font-medium text-gray-300 mb-2">
                                                Password Requirements:
                                            </p>
                                            <div className="space-y-1">
                                                <RequirementItem met={passwordStrength.criteria.length} text="At least 12 characters" />
                                                <RequirementItem met={passwordStrength.criteria.uppercase} text="One uppercase letter" />
                                                <RequirementItem met={passwordStrength.criteria.lowercase} text="One lowercase letter" />
                                                <RequirementItem met={passwordStrength.criteria.numbers} text="One number" />
                                                <RequirementItem met={passwordStrength.criteria.special} text="One special character" />
                                            </div>
                                            <div className="mt-3 pt-3 border-t border-gray-700">
                                                <div className="flex items-center justify-between">
                                                    <span className="text-sm text-gray-400">Password Strength:</span>
                                                    <span className={`text-sm font-medium ${
                                                        passwordStrength.strength >= 4 ? 'text-green-400' :
                                                        passwordStrength.strength >= 3 ? 'text-yellow-400' :
                                                        'text-red-400'
                                                    }`}>
                                                        {passwordStrength.strength >= 4 ? 'Strong' :
                                                         passwordStrength.strength >= 3 ? 'Fair' :
                                                         'Weak'}
                                                    </span>
                                                </div>
                                                <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
                                                    <div 
                                                        className={`h-full transition-all duration-300 ${
                                                            passwordStrength.strength >= 4 ? 'bg-green-500' :
                                                            passwordStrength.strength >= 3 ? 'bg-yellow-500' :
                                                            'bg-red-500'
                                                        }`}
                                                        style={{ width: `${(passwordStrength.strength / 5) * 100}%` }}
                                                    />
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                </div>
                                
                                <button
                                    type="submit"
                                    disabled={loading || passwordStrength.strength < 4}
                                    className="w-full py-3 px-4 bg-yellow-500 hover:bg-yellow-400 disabled:bg-gray-600 disabled:cursor-not-allowed text-black font-semibold rounded-lg transition-colors flex items-center justify-center"
                                >
                                    {loading ? (
                                        <>
                                            <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-black mr-2"></div>
                                            Updating Password...
                                        </>
                                    ) : (
                                        <>
                                            <Shield className="w-5 h-5 mr-2" />
                                            Update Password
                                        </>
                                    )}
                                </button>
                            </form>
                        )}
                    </>
                )}
                
                <div className="text-center">
                    <p className="text-sm text-gray-400">
                        Need help? Contact your system administrator.
                    </p>
                </div>
            </div>
        </div>
    );
};

const RequirementItem = ({ met, text }) => (
    <div className="flex items-center space-x-2">
        <div className={`w-4 h-4 rounded-full flex items-center justify-center ${
            met ? 'bg-green-500' : 'bg-gray-600'
        }`}>
            {met && <CheckCircle className="w-3 h-3 text-white" />}
        </div>
        <span className={`text-sm ${met ? 'text-gray-300' : 'text-gray-500'}`}>
            {text}
        </span>
    </div>
);

export default PasswordChangeLogin;