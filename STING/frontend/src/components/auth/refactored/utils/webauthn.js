// WebAuthn utility functions for credential encoding/decoding

/**
 * Convert base64url string to ArrayBuffer
 * @param {string} base64url - Base64url encoded string
 * @returns {ArrayBuffer} - Decoded ArrayBuffer
 */
export function base64urlToArrayBuffer(base64url) {
  // Add padding if needed
  const padding = '='.repeat((4 - base64url.length % 4) % 4);
  const base64 = base64url.replace(/-/g, '+').replace(/_/g, '/') + padding;
  
  // Decode base64 to binary string
  const binaryString = atob(base64);
  
  // Convert binary string to ArrayBuffer
  const buffer = new ArrayBuffer(binaryString.length);
  const view = new Uint8Array(buffer);
  
  for (let i = 0; i < binaryString.length; i++) {
    view[i] = binaryString.charCodeAt(i);
  }
  
  return buffer;
}

/**
 * Convert ArrayBuffer to base64url string
 * @param {ArrayBuffer} buffer - ArrayBuffer to encode
 * @returns {string} - Base64url encoded string
 */
export function arrayBufferToBase64url(buffer) {
  const bytes = new Uint8Array(buffer);
  const binary = String.fromCharCode(...bytes);
  const base64 = btoa(binary);
  
  // Convert base64 to base64url
  return base64.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

/**
 * Convert Uint8Array to base64url string
 * @param {Uint8Array} uint8Array - Uint8Array to encode
 * @returns {string} - Base64url encoded string
 */
export function uint8ArrayToBase64url(uint8Array) {
  return arrayBufferToBase64url(uint8Array.buffer);
}

/**
 * Convert base64url string to Uint8Array
 * @param {string} base64url - Base64url encoded string
 * @returns {Uint8Array} - Decoded Uint8Array
 */
export function base64urlToUint8Array(base64url) {
  const buffer = base64urlToArrayBuffer(base64url);
  return new Uint8Array(buffer);
}