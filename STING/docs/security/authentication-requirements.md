# STING Authentication Security Requirements

## Overview

This document outlines the security requirements for authentication in STING, with a focus on protecting sensitive data and ensuring strong authentication for critical functions.

## Core Requirements

### 1. Passkey Enforcement for Reporting Functions

**Requirement**: ALL reporting functions MUST enforce passkey authentication.

**Rationale**: Reports often contain aggregated sensitive data and PII (Personally Identifiable Information). Passkey authentication provides the strongest level of security for these operations.

**Implementation**:
- Before accessing any reporting endpoint, verify user has an active passkey
- If no passkey exists, redirect to passkey enrollment
- No fallback to password-only authentication for reports
- Applies to:
  - Report generation
  - Report viewing
  - Report export/download
  - Report template management
  - Report scheduling

### 2. Multi-Factor Authentication for Additional Passkeys

**Requirement**: Adding additional passkeys after the initial passkey setup MUST require at least 2FA (email + password verification).

**Rationale**: Prevents unauthorized passkey enrollment if a device is compromised. Once a user has one passkey, adding more requires proving ownership of both something they know (password) and something they have (email access).

**Implementation**:
- When user attempts to add a second or subsequent passkey:
  1. Require password re-authentication
  2. Send verification code to registered email
  3. Only allow passkey enrollment after both verifications pass
- Session must be recent (< 5 minutes) for passkey operations

### 3. PII Access Protection

**Requirement**: Any authentication method that has potential to view or interact with PII MUST require either:
- Passkey authentication, OR
- Traditional authentication WITH enforced 2FA (TOTP/SMS/Email)

**Rationale**: PII requires the highest level of protection. Single-factor authentication is insufficient for accessing sensitive personal data.

**Affected Areas**:
- User profile data access
- Honey jar documents containing PII
- Report generation with user data
- Administrative functions
- Data export operations
- API endpoints returning personal information

## Authentication Hierarchy

1. **Level 3 - Highest Security** (Passkey Required)
   - Report generation and viewing
   - Administrative functions
   - Bulk data operations
   - Security settings changes

2. **Level 2 - Enhanced Security** (Passkey OR Password+2FA)
   - PII access
   - Document viewing/editing
   - Profile management
   - Team management

3. **Level 1 - Standard Security** (Password)
   - Dashboard access
   - Non-sensitive data viewing
   - General navigation

## Implementation Guidelines

### Frontend
- Check authentication level before rendering sensitive components
- Redirect to appropriate authentication upgrade flow
- Clear indication of security requirements to users
- Progressive enhancement (offer passkey upgrade after password login)

### Backend
- Middleware to enforce authentication levels per endpoint
- Decorators for easy security level assignment
- Audit logging for all high-security operations
- Session management with appropriate timeouts

### User Experience
- Clear communication about why enhanced authentication is required
- Smooth upgrade paths from password to passkey
- Fallback options for lost passkeys (with appropriate verification)
- Remember device options for trusted environments

## Enrollment Flow

1. **Initial Setup** (New Users)
   - Password creation (enforced complexity)
   - Mandatory passkey setup for admins
   - Optional but encouraged passkey setup for regular users
   - Clear explanation of security benefits

2. **Progressive Security** (Existing Users)
   - Prompt for passkey when accessing Level 3 features
   - Offer passkey setup after successful password+2FA login
   - Periodic reminders for security upgrade

## Emergency Access

In case of passkey loss:
1. Require password + email verification + admin approval
2. Temporary access with limited permissions
3. Mandatory passkey re-enrollment within 24 hours
4. Audit trail of emergency access

## Compliance Considerations

- GDPR: Strong authentication for PII access
- HIPAA: Multi-factor authentication for health data
- SOC 2: Demonstrable access controls
- Industry best practices for zero-trust security