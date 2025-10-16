/**
 * WebAuthn Utility Functions
 * 
 * Handles conversion between base64url strings and ArrayBuffers for WebAuthn API.
 * The backend returns WebAuthn options with challenge and user.id as base64url strings,
 * but navigator.credentials.create() expects ArrayBuffers.
 */

/**
 * Convert base64url string to ArrayBuffer
 * @param {string} base64url - Base64url encoded string
 * @returns {ArrayBuffer} - Decoded ArrayBuffer
 */
export const base64urlToArrayBuffer = (base64url) => {
  if (!base64url) {
    throw new Error('base64url string is required');
  }

  // Add padding if needed (base64url removes padding)
  const padding = '='.repeat((4 - (base64url.length % 4)) % 4);
  
  // Convert base64url to base64
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + padding;
  
  // Decode base64 to binary string
  const binaryString = atob(base64);
  
  // Convert binary string to ArrayBuffer
  const bytes = new Uint8Array(binaryString.length);
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  
  return bytes.buffer;
};

/**
 * Convert ArrayBuffer to base64url string
 * @param {ArrayBuffer} buffer - ArrayBuffer to encode
 * @returns {string} - Base64url encoded string
 */
export const arrayBufferToBase64url = (buffer) => {
  if (!buffer) {
    throw new Error('ArrayBuffer is required');
  }

  const bytes = new Uint8Array(buffer);
  let binaryString = '';
  
  for (let i = 0; i < bytes.length; i++) {
    binaryString += String.fromCharCode(bytes[i]);
  }
  
  // Convert to base64 and then to base64url
  const base64 = btoa(binaryString);
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
};

/**
 * Process WebAuthn PublicKeyCredentialCreationOptions from backend
 * Converts base64url strings to ArrayBuffers where required by WebAuthn API
 * @param {Object} options - Raw options from backend
 * @returns {Object} - Processed options ready for navigator.credentials.create()
 */
export const processWebAuthnOptions = (options) => {
  if (!options) {
    throw new Error('WebAuthn options are required');
  }

  console.log('🔧 Processing WebAuthn options for ArrayBuffer conversion');
  
  try {
    const processedOptions = {
      ...options,
      // Convert challenge from base64url string to ArrayBuffer
      challenge: base64urlToArrayBuffer(options.challenge),
      user: {
        ...options.user,
        // Convert user.id from base64url string to ArrayBuffer
        id: base64urlToArrayBuffer(options.user.id)
      }
    };

    console.log('✅ WebAuthn options processed successfully');
    console.log('   - Challenge converted to ArrayBuffer:', processedOptions.challenge);
    console.log('   - User ID converted to ArrayBuffer:', processedOptions.user.id);

    return processedOptions;
  } catch (error) {
    console.error('❌ Error processing WebAuthn options:', error);
    throw new Error(`Failed to process WebAuthn options: ${error.message}`);
  }
};

/**
 * Process WebAuthn PublicKeyCredential response for backend submission
 * Converts ArrayBuffers to base64url strings and formats for backend
 * @param {PublicKeyCredential} credential - Raw credential from navigator.credentials.create()
 * @returns {Object} - Processed credential ready for backend submission
 */
export const processCredentialForBackend = (credential) => {
  if (!credential) {
    throw new Error('WebAuthn credential is required');
  }

  console.log('🔧 Processing credential for backend submission');

  try {
    const processedCredential = {
      id: credential.id,
      rawId: Array.from(new Uint8Array(credential.rawId)),
      response: {
        attestationObject: Array.from(new Uint8Array(credential.response.attestationObject)),
        clientDataJSON: Array.from(new Uint8Array(credential.response.clientDataJSON))
      },
      type: credential.type
    };

    console.log('✅ Credential processed for backend submission');

    return processedCredential;
  } catch (error) {
    console.error('❌ Error processing credential for backend:', error);
    throw new Error(`Failed to process credential: ${error.message}`);
  }
};