from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    base64url_to_bytes
)
import base64
from webauthn.helpers.cose import COSEAlgorithmIdentifier
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    AuthenticatorAttachment,
    ResidentKeyRequirement
)
from flask import current_app
import json
import logging

logger = logging.getLogger(__name__)

class WebAuthnManager:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.rp_id = app.config['WEBAUTHN_RP_ID']
        self.rp_name = app.config['WEBAUTHN_RP_NAME']
        self.rp_origins = app.config['WEBAUTHN_RP_ORIGINS']

    def generate_registration_options(self, user_id, username):
        """Generate options for registering a new passkey."""
        try:
            # Ensure user_id is bytes and not too long (max 64 bytes for WebAuthn)
            if isinstance(user_id, str):
                # Truncate user_id if it's too long and ensure it's valid
                if len(user_id) > 64:
                    user_id = user_id[:32]  # Keep it reasonable
                user_id_bytes = user_id.encode('utf-8')
            else:
                user_id_bytes = user_id
            
            # Ensure user_id_bytes is not longer than 64 bytes
            if len(user_id_bytes) > 64:
                user_id_bytes = user_id_bytes[:64]
            
            logger.debug(f"Generating registration options for user_id: {user_id}, username: {username}")
            logger.debug(f"RP ID: {self.rp_id}, RP Name: {self.rp_name}")
            
            options = generate_registration_options(
                rp_id=self.rp_id,
                rp_name=self.rp_name,
                user_id=user_id_bytes,
                user_name=username,
                user_display_name=username,  # Add explicit display name
                authenticator_selection=AuthenticatorSelectionCriteria(
                    authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                    resident_key=ResidentKeyRequirement.REQUIRED,
                    user_verification=UserVerificationRequirement.REQUIRED
                ),
                supported_pub_key_algs=[
                    COSEAlgorithmIdentifier.ECDSA_SHA_256,  # ES256 - Required by Chrome
                    COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,  # RS256 - Required by Chrome
                    COSEAlgorithmIdentifier.RSASSA_PSS_SHA_256,  # Additional support
                    COSEAlgorithmIdentifier.ECDSA_SHA_512,  # ES512 - Additional support
                ],
                exclude_credentials=[],  # Add empty exclude list
                timeout=60000  # 60 seconds timeout
            )
            
            # Convert to dict manually
            result = {
                'challenge': base64.urlsafe_b64encode(options.challenge).decode('utf-8').rstrip('='),
                'rp': {'id': options.rp.id, 'name': options.rp.name},
                'user': {
                    'id': base64.urlsafe_b64encode(options.user.id).decode('utf-8').rstrip('='),
                    'name': options.user.name,
                    'displayName': options.user.display_name or options.user.name
                },
                'pubKeyCredParams': [{'type': 'public-key', 'alg': param.alg} for param in options.pub_key_cred_params],
                'authenticatorSelection': {
                    'authenticatorAttachment': options.authenticator_selection.authenticator_attachment.value if options.authenticator_selection and options.authenticator_selection.authenticator_attachment else 'platform',
                    'userVerification': options.authenticator_selection.user_verification.value if options.authenticator_selection else 'required',
                    'residentKey': options.authenticator_selection.resident_key.value if options.authenticator_selection and options.authenticator_selection.resident_key else 'required'
                },
                'timeout': options.timeout,
                'attestation': options.attestation.value if options.attestation else 'none',
                'excludeCredentials': []  # Add empty exclude credentials
            }
            
            logger.debug(f"Generated registration options successfully: {json.dumps(result, default=str)}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate registration options: {str(e)}", exc_info=True)
            raise

    def verify_registration(self, credential_data, expected_challenge):
        """Verify the registration response from the client."""
        try:
            logger.debug(f"Received credential data: {json.dumps(credential_data, default=str)}")
            
            # Convert frontend array format to webauthn library format
            processed_credential = self._process_credential_data(credential_data)
            logger.debug(f"Processed credential data: {json.dumps(processed_credential, default=str)}")
            
            verification = verify_registration_response(
                credential=processed_credential,
                expected_challenge=base64url_to_bytes(expected_challenge),
                expected_origin=self.rp_origins,
                expected_rp_id=self.rp_id
            )
            logger.info("Registration verification successful")
            return {
                'verified': True,
                'credential_id': verification.credential_id,
                'public_key': verification.credential_public_key
            }
        except Exception as e:
            logger.error(f"Registration verification failed: {str(e)}")
            return {'verified': False, 'error': str(e)}

    def generate_authentication_options(self, credential_ids=None, user_verification="preferred"):
        """Generate options for authenticating with a passkey."""
        # Convert credential_ids to PublicKeyCredentialDescriptor objects if needed
        allow_credentials = None
        if credential_ids:
            from webauthn.helpers.structs import PublicKeyCredentialDescriptor
            allow_credentials = []
            for cred_id in credential_ids:
                # Handle both base64 strings and raw bytes
                if isinstance(cred_id, str):
                    cred_id_bytes = base64.b64decode(cred_id)
                else:
                    cred_id_bytes = cred_id
                    
                allow_credentials.append(
                    PublicKeyCredentialDescriptor(
                        id=cred_id_bytes,
                        type='public-key'
                    )
                )
        
        # Convert string parameter to enum
        user_verification_enum = UserVerificationRequirement.PREFERRED
        if user_verification == "required":
            user_verification_enum = UserVerificationRequirement.REQUIRED
        elif user_verification == "discouraged":
            user_verification_enum = UserVerificationRequirement.DISCOURAGED
        
        options = generate_authentication_options(
            rp_id=self.rp_id,
            allow_credentials=allow_credentials,
            user_verification=user_verification_enum
        )
        
        # Convert to dict manually - format for @simplewebauthn/browser v13
        # The library expects the options wrapped in publicKey object
        return {
            'publicKey': {
                'challenge': base64.urlsafe_b64encode(options.challenge).decode('utf-8').rstrip('='),
                'rpId': options.rp_id,
                'allowCredentials': [
                    {
                        'type': 'public-key',
                        'id': base64.urlsafe_b64encode(cred.id).decode('utf-8').rstrip('='),
                        'transports': ['usb', 'nfc', 'ble', 'internal']  # Support all transport types
                    } for cred in options.allow_credentials
                ] if options.allow_credentials else [],
                'userVerification': options.user_verification.value,
                'timeout': options.timeout or 60000
            }
        }

    def verify_authentication(self, credential_data, expected_challenge, stored_public_key):
        """Verify the authentication response from the client."""
        try:
            # Convert frontend array format to webauthn library format
            processed_credential = self._process_authentication_credential_data(credential_data)
            
            verification = verify_authentication_response(
                credential=processed_credential,
                expected_challenge=base64url_to_bytes(expected_challenge),
                expected_origin=self.rp_origins,
                expected_rp_id=self.rp_id,
                credential_public_key=stored_public_key,
                credential_current_sign_count=0
            )
            return {'verified': True, 'counter': verification.new_sign_count}
        except Exception as e:
            return {'verified': False, 'error': str(e)}

    def _process_credential_data(self, credential_data):
        """
        Convert credential data from frontend format (arrays of integers) 
        to the format expected by the webauthn library.
        
        Frontend sends:
        - rawId: [165, 185, 133, 152, ...]
        - response.attestationObject: [123, 45, 67, ...]
        - response.clientDataJSON: [123, 34, 116, ...]
        
        WebAuthn library expects:
        - rawId: base64url encoded string
        - response.attestationObject: base64url encoded string
        - response.clientDataJSON: base64url encoded string
        """
        try:
            logger.debug(f"Processing credential data with rawId type: {type(credential_data.get('rawId'))}")
            
            processed = {
                'id': credential_data.get('id'),
                'type': credential_data.get('type', 'public-key')
            }
            
            # Convert rawId from array to base64url string
            if credential_data.get('rawId'):
                if isinstance(credential_data['rawId'], list):
                    # Convert array of integers to bytes, then to base64url
                    raw_id_bytes = bytes(credential_data['rawId'])
                    processed['rawId'] = base64.urlsafe_b64encode(raw_id_bytes).decode('utf-8').rstrip('=')
                else:
                    # Already in correct format
                    processed['rawId'] = credential_data['rawId']
            
            # Process response object
            if credential_data.get('response'):
                processed['response'] = {}
                
                # Convert attestationObject
                if credential_data['response'].get('attestationObject'):
                    if isinstance(credential_data['response']['attestationObject'], list):
                        # Convert array of integers to bytes, then to base64url
                        attestation_bytes = bytes(credential_data['response']['attestationObject'])
                        processed['response']['attestationObject'] = base64.urlsafe_b64encode(attestation_bytes).decode('utf-8').rstrip('=')
                    else:
                        processed['response']['attestationObject'] = credential_data['response']['attestationObject']
                
                # Convert clientDataJSON
                if credential_data['response'].get('clientDataJSON'):
                    if isinstance(credential_data['response']['clientDataJSON'], list):
                        # Convert array of integers to bytes, then to base64url
                        client_data_bytes = bytes(credential_data['response']['clientDataJSON'])
                        processed['response']['clientDataJSON'] = base64.urlsafe_b64encode(client_data_bytes).decode('utf-8').rstrip('=')
                    else:
                        processed['response']['clientDataJSON'] = credential_data['response']['clientDataJSON']
            
            return processed
            
        except Exception as e:
            raise Exception(f"Failed to process credential data: {str(e)}")

    def _process_authentication_credential_data(self, credential_data):
        """
        Convert authentication credential data from frontend format (arrays of integers) 
        to the format expected by the webauthn library.
        
        Frontend sends:
        - rawId: [165, 185, 133, 152, ...]
        - response.authenticatorData: [123, 45, 67, ...]
        - response.clientDataJSON: [123, 34, 116, ...]
        - response.signature: [89, 123, 45, ...]
        
        WebAuthn library expects:
        - rawId: base64url encoded string
        - response.authenticatorData: base64url encoded string
        - response.clientDataJSON: base64url encoded string
        - response.signature: base64url encoded string
        """
        try:
            processed = {
                'id': credential_data.get('id'),
                'type': credential_data.get('type', 'public-key')
            }
            
            # Convert rawId from array to base64url string
            if credential_data.get('rawId'):
                if isinstance(credential_data['rawId'], list):
                    # Convert array of integers to bytes, then to base64url
                    raw_id_bytes = bytes(credential_data['rawId'])
                    processed['rawId'] = base64.urlsafe_b64encode(raw_id_bytes).decode('utf-8').rstrip('=')
                else:
                    # Already in correct format
                    processed['rawId'] = credential_data['rawId']
            
            # Process response object
            if credential_data.get('response'):
                processed['response'] = {}
                
                # Convert authenticatorData
                if credential_data['response'].get('authenticatorData'):
                    if isinstance(credential_data['response']['authenticatorData'], list):
                        # Convert array of integers to bytes, then to base64url
                        auth_data_bytes = bytes(credential_data['response']['authenticatorData'])
                        processed['response']['authenticatorData'] = base64.urlsafe_b64encode(auth_data_bytes).decode('utf-8').rstrip('=')
                    else:
                        processed['response']['authenticatorData'] = credential_data['response']['authenticatorData']
                
                # Convert clientDataJSON
                if credential_data['response'].get('clientDataJSON'):
                    if isinstance(credential_data['response']['clientDataJSON'], list):
                        # Convert array of integers to bytes, then to base64url
                        client_data_bytes = bytes(credential_data['response']['clientDataJSON'])
                        processed['response']['clientDataJSON'] = base64.urlsafe_b64encode(client_data_bytes).decode('utf-8').rstrip('=')
                    else:
                        processed['response']['clientDataJSON'] = credential_data['response']['clientDataJSON']
                
                # Convert signature
                if credential_data['response'].get('signature'):
                    if isinstance(credential_data['response']['signature'], list):
                        # Convert array of integers to bytes, then to base64url
                        signature_bytes = bytes(credential_data['response']['signature'])
                        processed['response']['signature'] = base64.urlsafe_b64encode(signature_bytes).decode('utf-8').rstrip('=')
                    else:
                        processed['response']['signature'] = credential_data['response']['signature']
                
                # Handle userHandle if present
                if credential_data['response'].get('userHandle'):
                    if isinstance(credential_data['response']['userHandle'], list):
                        # Convert array of integers to bytes, then to base64url
                        user_handle_bytes = bytes(credential_data['response']['userHandle'])
                        processed['response']['userHandle'] = base64.urlsafe_b64encode(user_handle_bytes).decode('utf-8').rstrip('=')
                    else:
                        processed['response']['userHandle'] = credential_data['response']['userHandle']
            
            return processed
            
        except Exception as e:
            raise Exception(f"Failed to process authentication credential data: {str(e)}")
# Create a singleton instance
webauthn_manager = WebAuthnManager()
