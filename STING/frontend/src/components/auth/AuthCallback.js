import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

const AuthCallback = () => {
    const navigate = useNavigate();
    
    useEffect(() => {
        // After successful auth, redirect to dashboard
        navigate('/dashboard');
    }, []);
    
    return null;
};
