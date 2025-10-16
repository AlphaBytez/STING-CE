import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Card, Form, Input, Button, Alert, Typography } from 'antd';
import { UserOutlined, LockOutlined } from '@ant-design/icons';
import { useKratosSDK } from '../../auth/KratosSDKProvider';

const { Title, Text } = Typography;

const SimplifiedKratosLogin = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { initializeLogin, submitFlow, authenticated } = useKratosSDK();
  
  const [flow, setFlow] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Redirect if already authenticated
  useEffect(() => {
    if (authenticated) {
      navigate('/dashboard');
    }
  }, [authenticated, navigate]);
  
  // Initialize flow on mount
  useEffect(() => {
    const flowId = searchParams.get('flow');
    
    const init = async () => {
      try {
        setLoading(true);
        
        if (!flowId) {
          // Create new flow
          const flowData = await initializeLogin();
          setFlow(flowData);
          
          // Update URL with flow ID
          const newUrl = new URL(window.location);
          newUrl.searchParams.set('flow', flowData.id);
          window.history.replaceState({}, '', newUrl);
        }
      } catch (err) {
        setError('Failed to initialize login');
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    
    if (!flowId) {
      init();
    }
  }, [searchParams, initializeLogin]);
  
  const handleSubmit = async (values) => {
    if (!flow) {
      setError('No login flow initialized');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      const result = await submitFlow(flow.id, 'password', {
        identifier: values.email,
        password: values.password,
      });
      
      if (result.session) {
        // Success! Redirect to dashboard
        navigate('/dashboard');
      }
    } catch (err) {
      console.error('Login error:', err);
      setError('Invalid email or password');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
      <Card className="w-full max-w-md">
        <div className="text-center mb-8">
          <Title level={2}>Sign in to STING</Title>
          <Text type="secondary">Simplified Kratos authentication</Text>
        </div>
        
        {error && (
          <Alert
            type="error"
            message={error}
            closable
            onClose={() => setError(null)}
            className="mb-4"
          />
        )}
        
        <Form
          name="login"
          onFinish={handleSubmit}
          layout="vertical"
          size="large"
        >
          <Form.Item
            name="email"
            label="Email"
            rules={[
              { required: true, message: 'Please enter your email' },
              { type: 'email', message: 'Please enter a valid email' }
            ]}
          >
            <Input
              prefix={<UserOutlined />}
              placeholder="admin@sting.local"
              autoComplete="username"
            />
          </Form.Item>
          
          <Form.Item
            name="password"
            label="Password"
            rules={[{ required: true, message: 'Please enter your password' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Password"
              autoComplete="current-password"
            />
          </Form.Item>
          
          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={loading}
              block
            >
              Sign In
            </Button>
          </Form.Item>
          
          <div className="text-center space-y-2">
            <div>
              <Button type="link" onClick={() => navigate('/recovery')}>
                Forgot password?
              </Button>
            </div>
            <div>
              Don't have an account?{' '}
              <Button type="link" onClick={() => navigate('/register')}>
                Sign up
              </Button>
            </div>
          </div>
        </Form>
      </Card>
    </div>
  );
};

export default SimplifiedKratosLogin;