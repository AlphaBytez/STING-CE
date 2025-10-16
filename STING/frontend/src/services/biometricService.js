/**
 * Biometric Service - UV Flag Detection and Recording
 * Purpose: Detect biometric authentication (UV flag) and upgrade to AAL2
 * Context: Bridge Kratos AAL limitations for TouchID/FaceID authentication
 */

import axios from 'axios';

class BiometricService {
    constructor() {
        this.biometricDetected = false;
        this.lastCredentialId = null;
    }

    /**
     * Detect UV flag from WebAuthn credential response
     * @param {PublicKeyCredential} credential - WebAuthn credential response
     * @returns {Object} Detection result with UV flag and authenticator type
     */
    detectBiometricAuth(credential) {
        try {
            if (!credential?.response?.authenticatorData) {
                console.warn('🔒 BiometricService: No authenticator data found in credential');
                return { userVerified: false, authenticatorType: 'unknown' };
            }

            // Parse authenticator data to extract flags
            const authData = new Uint8Array(credential.response.authenticatorData);
            
            // Flags are at byte 32 (0-indexed)
            if (authData.length < 33) {
                console.warn('🔒 BiometricService: Authenticator data too short');
                return { userVerified: false, authenticatorType: 'unknown' };
            }

            const flagsByte = authData[32];
            
            // Bit flags (RFC 8812):
            // Bit 0: UP (User Present) - always set
            // Bit 1: Reserved
            // Bit 2: UV (User Verified) - biometric verification
            // Bit 3: Reserved
            // Bit 4: Reserved  
            // Bit 5: Reserved
            // Bit 6: AT (Attested credential data included)
            // Bit 7: ED (Extension data included)
            
            const userPresent = (flagsByte & 0x01) !== 0;  // Bit 0
            const userVerified = (flagsByte & 0x04) !== 0; // Bit 2
            const attestedCredData = (flagsByte & 0x40) !== 0; // Bit 6
            const extensionData = (flagsByte & 0x80) !== 0;   // Bit 7

            console.log('🔒 BiometricService: WebAuthn flags detected', {
                userPresent,
                userVerified,
                attestedCredData,
                extensionData,
                flagsByte: flagsByte.toString(2).padStart(8, '0') // Binary representation
            });

            // Determine authenticator type
            const authenticatorType = this.determineAuthenticatorType(credential);
            
            // Record detection
            this.biometricDetected = userVerified;
            this.lastCredentialId = credential.id;

            return {
                userVerified,
                userPresent,
                authenticatorType,
                credentialId: credential.id,
                timestamp: new Date().toISOString()
            };

        } catch (error) {
            console.error('🔒 BiometricService: Error detecting biometric auth:', error);
            return { userVerified: false, authenticatorType: 'unknown', error: error.message };
        }
    }

    /**
     * Determine authenticator type from credential properties
     * @param {PublicKeyCredential} credential - WebAuthn credential
     * @returns {string} Authenticator type ('platform' or 'cross-platform')
     */
    determineAuthenticatorType(credential) {
        // Check if this is a platform authenticator
        if (credential.authenticatorAttachment) {
            return credential.authenticatorAttachment; // 'platform' or 'cross-platform'
        }

        // Try to infer from user agent and credential properties
        const userAgent = navigator.userAgent;
        
        if (userAgent.includes('Mac') || userAgent.includes('iPhone') || userAgent.includes('iPad')) {
            return 'platform'; // Likely TouchID/FaceID
        }
        
        if (userAgent.includes('Windows')) {
            return 'platform'; // Likely Windows Hello
        }

        // Default fallback
        return 'cross-platform';
    }

    /**
     * Record biometric authentication with backend
     * @param {Object} detectionResult - Result from detectBiometricAuth
     * @param {string} sessionId - Current session ID
     * @returns {Promise<Object>} Recording result
     */
    async recordBiometricAuth(detectionResult, sessionId = null) {
        try {
            console.log('🔒 BiometricService: Recording biometric authentication', detectionResult);

            const response = await axios.post('/api/biometric/record-auth', {
                credential_id: detectionResult.credentialId,
                user_verified: detectionResult.userVerified,
                authenticator_type: detectionResult.authenticatorType,
                session_id: sessionId
            }, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true
            });

            if (response.data.success) {
                console.log('🔒 BiometricService: Successfully recorded biometric auth', {
                    aalUpgraded: response.data.aal_upgraded,
                    effectiveAal: response.data.effective_aal
                });
                
                return {
                    success: true,
                    aalUpgraded: response.data.aal_upgraded,
                    effectiveAal: response.data.effective_aal
                };
            } else {
                console.error('🔒 BiometricService: Failed to record biometric auth:', response.data.error);
                return { success: false, error: response.data.error };
            }

        } catch (error) {
            console.error('🔒 BiometricService: Error recording biometric auth:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Record credential metadata for UI display
     * @param {Object} credentialInfo - Credential information
     * @returns {Promise<Object>} Recording result
     */
    async recordCredentialMetadata(credentialInfo) {
        try {
            console.log('🔒 BiometricService: Recording credential metadata', credentialInfo);

            const response = await axios.post('/api/biometric/record-credential', {
                credential_id: credentialInfo.credentialId,
                credential_name: credentialInfo.name || null,
                is_biometric: credentialInfo.isBiometric || false,
                authenticator_type: credentialInfo.authenticatorType || 'platform'
            }, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true
            });

            return response.data;

        } catch (error) {
            console.error('🔒 BiometricService: Error recording credential metadata:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get user's credentials separated by biometric capability
     * @returns {Promise<Object>} Credentials data
     */
    async getUserCredentials() {
        try {
            const response = await axios.get('/api/biometric/credentials', {
                withCredentials: true
            });

            return response.data;

        } catch (error) {
            console.error('🔒 BiometricService: Error getting user credentials:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get biometric AAL status
     * @returns {Promise<Object>} AAL status including biometric detection
     */
    async getBiometricAALStatus() {
        try {
            const response = await axios.get('/api/biometric/aal-status', {
                withCredentials: true
            });

            return response.data;

        } catch (error) {
            console.error('🔒 BiometricService: Error getting biometric AAL status:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Process credential after WebAuthn operation (registration or authentication)
     * This is the main entry point for biometric detection
     * @param {PublicKeyCredential} credential - WebAuthn credential
     * @param {string} sessionId - Optional session ID
     * @returns {Promise<Object>} Processing result
     */
    async processCredential(credential, sessionId = null) {
        try {
            console.log('🔒 BiometricService: Processing credential for biometric detection');

            // Detect biometric authentication
            const detection = this.detectBiometricAuth(credential);
            
            // Record biometric authentication if UV flag is set
            if (detection.userVerified) {
                const recordResult = await this.recordBiometricAuth(detection, sessionId);
                
                // Also record credential metadata
                await this.recordCredentialMetadata({
                    credentialId: detection.credentialId,
                    isBiometric: true,
                    authenticatorType: detection.authenticatorType,
                    name: `${detection.authenticatorType === 'platform' ? 'TouchID/FaceID' : 'External'} Key`
                });

                return {
                    success: true,
                    biometric: true,
                    detection,
                    recordResult
                };
            } else {
                // Record as non-biometric credential
                await this.recordCredentialMetadata({
                    credentialId: detection.credentialId,
                    isBiometric: false,
                    authenticatorType: detection.authenticatorType,
                    name: `${detection.authenticatorType} Key`
                });

                return {
                    success: true,
                    biometric: false,
                    detection
                };
            }

        } catch (error) {
            console.error('🔒 BiometricService: Error processing credential:', error);
            return { success: false, error: error.message };
        }
    }
}

// Export singleton instance
export const biometricService = new BiometricService();

// Export convenience functions
export const detectBiometric = (credential) => biometricService.detectBiometricAuth(credential);
export const recordBiometric = (detection, sessionId) => biometricService.recordBiometricAuth(detection, sessionId);
export const processCredential = (credential, sessionId) => biometricService.processCredential(credential, sessionId);

export default biometricService;