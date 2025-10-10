import pytest
from flask import url_for
from supertokens_python.recipe.webauthn import WebAuthnRecipe

@pytest.fixture
def mock_webauthn_credential():
    return {
        'id': 'test-credential-id',
        'type': 'public-key',
        'rawId': 'test-raw-id',
        'response': {
            'clientDataJSON': 'test-client-data',
            'attestationObject': 'test-attestation'
        }
    }

def test_webauthn_endpoints(client):
    """Test WebAuthn endpoints are accessible"""
    endpoints = [
        '/api/auth/webauthn/register',
        '/api/auth/webauthn/authenticate',
        '/api/auth/webauthn/authentication-attempt'
    ]
    
    for endpoint in endpoints:
        response = client.get(endpoint)
        assert response.status_code in [200, 405]  # 405 is valid for POST-only endpoints

def test_webauthn_health(client):
    """Verify WebAuthn is enabled in health check"""
    response = client.get('/api/auth/health')
    assert response.status_code == 200
    assert response.json['webauthn'] == 'enabled'

def test_webauthn_full_flow(client, mock_webauthn_credential):
    """Test complete WebAuthn registration and authentication cycle"""
    # Test registration
    register_response = client.post('/api/auth/webauthn/register', 
                                  json={'credential': mock_webauthn_credential})
    assert register_response.status_code == 200
    
    # Test authentication attempt
    auth_attempt = client.get('/api/auth/webauthn/authentication-attempt')
    assert auth_attempt.status_code == 200
    assert 'challenge' in auth_attempt.json
    
    # Test authentication
    auth_response = client.post('/api/auth/webauthn/authenticate',
                              json={'credential': mock_webauthn_credential})
    assert auth_response.status_code == 200

def test_webauthn_config(app):
    """Verify WebAuthn configuration"""
    assert app.config['supertokens']['webauthn_config']['enabled'] == True
    assert 'rp_id' in app.config['supertokens']['webauthn_config']