# SuperTokens Deprecation and Removal

## Overview

STING has migrated from SuperTokens to Ory Kratos for authentication. This document outlines the changes made to remove SuperTokens references and prevent potential issues.

## Recently Discovered Issues

During the migration from SuperTokens to Kratos, we identified two related issues:

1. **Routing Conflict**: After login, the dashboard wasn't displaying its original design because:
   - `AuthenticationWrapper.jsx` directly rendered `Dashboard` at `/dashboard`
   - `AppRoutes.js` rendered `MainInterface` at `/dashboard/*`
   - This caused inconsistent component loading depending on the authentication path

2. **SuperTokens Environment File**: Despite being deprecated, the system was still generating a `supertokens.env` file with syntactically invalid content, causing errors when running `msting update frontend`.

## Changes Made

1. **Modified `conf/config_loader.py`**:
   - Removed the generation of the `supertokens.env` file
   - Added deprecation notices to SuperTokens-related methods and classes
   - Prevented future generation of SuperTokens environment files
   - Added runtime guards to check for `.no_supertokens` file
   - Explicitly commented out any reference to supertokens.env in the service_configs dictionary

2. **Updated `troubleshooting/fix_supertokens_env.sh`**:
   - Removes existing `supertokens.env` file from the user's environment
   - Updates config.yml to comment out SuperTokens sections if present
   - Modifies configuration loader code to skip SuperTokens env file generation
   - Creates a `.no_supertokens` guard file to permanently prevent regeneration
   - Added more robust error handling and detection methods

3. **Fixed routing conflict in `auth/AuthenticationWrapper.jsx`**:
   - Changed `/dashboard` route to `/dashboard/*` to match AppRoutes.js
   - Replaced direct rendering of Dashboard with MainInterface
   - Ensured consistent routing between authentication systems

4. **Updated `troubleshooting/README.md`**:
   - Added documentation for the new fix script
   - Updated the common issues reference table

## Docker Compose Changes

The SuperTokens service was already commented out in `docker-compose.yml`, but the environment file was still being generated, causing errors with the `msting update frontend` command.

## How to Fix SuperTokens Issues

If you encounter errors related to SuperTokens, particularly with the `msting update frontend` command failing with a syntax error in the supertokens.env file, use the following fix:

```bash
# Run the fix script
./troubleshooting/fix_supertokens_env.sh

# Restart services
./manage_sting.sh restart
```

## Migration to Kratos

STING now uses Ory Kratos for authentication, which provides:
- WebAuthn/passkey support
- Multiple authentication methods
- Improved security and flexibility

The SuperTokens-related code is kept for backward compatibility but is marked as deprecated and won't generate files anymore.

## Component Migration Summary (May 15, 2025)

All authentication-related components have been migrated from SuperTokens to Kratos:

1. **User Settings Components**
   - AccountDeletion.jsx - Now uses useKratos hook instead of Passwordless recipe
   - EmailSettings.jsx - Uses Kratos identity for email verification
   - PasswordSettings.jsx - Compatible with Kratos password change
   - PreferenceSettings.jsx - Updated from Session to useKratos
   - SecuritySettings.jsx - Uses Kratos API for WebAuthn and sessions

2. **Authentication Wrapper**
   - Fixed routing conflicts between AppRoutes.js and AuthenticationWrapper.jsx
   - Updated AuthenticationWrapper to use MainInterface for dashboard route
   - Aligned route paths to use `/dashboard/*` for consistent routing

3. **Dashboard Component**
   - Verified working with Kratos authentication
   - Maintained original design while integrating with Kratos

## Technical Details

The specific issue that was fixed was in the `~/.sting-ce/env/supertokens.env` file, which contained a malformed line:

```
SUPERTOKENS_WEBAUTHN_RP_ORIGINS=["http://localhost:8443", "https://${HOSTNAME:-your-production-domain.com}"]
```

This syntax with unescaped square brackets caused shell parsing errors when the file was sourced.

Rather than fixing the specific line, we chose to completely remove SuperTokens as it is no longer used by the application.