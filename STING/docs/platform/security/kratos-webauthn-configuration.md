# Kratos WebAuthn Configuration for STING

## Current Situation

We have a dual authentication system:
1. **Kratos**: Handles password authentication with WebAuthn configured but not for passwordless
2. **Custom Flask Implementation**: Handles passkey authentication separately

## Why This Happened

After investigation, it appears that:

1. **Kratos v1.3.1** supports WebAuthn but the `passwordless` configuration option and dedicated `passkey` method may not be available in this version
2. The custom implementation was created to provide passkey-first authentication when Kratos didn't fully support it
3. The implementation works but creates complexity with dual session management

## Options Moving Forward

### Option 1: Keep Dual System (Current State)
**Pros:**
- Already working
- Provides passkey-first experience
- No migration needed

**Cons:**
- Complex session management
- Maintenance overhead
- Potential security gaps between systems

### Option 2: Use Kratos WebAuthn with Password Requirement
**Pros:**
- Single authentication system
- Battle-tested Kratos implementation
- Simpler session management

**Cons:**
- Users must set password first
- Not truly passwordless
- Less ideal UX for passkey-first approach

### Option 3: Upgrade Kratos to Latest Version
Check if newer Kratos versions support true passwordless WebAuthn/passkeys.

**Pros:**
- Get latest features
- Potentially native passkey support
- Future-proof solution

**Cons:**
- May require migration
- Testing needed
- Potential breaking changes

## Recommended Approach

Given that you want to use Kratos's native implementation and highlight passkeys primarily:

1. **Short Term**: Configure Kratos WebAuthn to work alongside passwords
   - Users register with email/password
   - Immediately prompt to add passkey
   - Login screen offers passkey as primary option with password fallback

2. **Long Term**: Investigate Kratos roadmap for passwordless support
   - Check if newer versions support true passwordless
   - Plan migration when feature is stable

## Configuration for Passkey-Primary Experience

Even with password requirement, we can create a passkey-first UX:

1. **Registration Flow**:
   ```
   Email → Password (can be auto-generated) → Immediate Passkey Setup
   ```

2. **Login Flow**:
   ```
   Email → Check for Passkeys → Show Passkey Button → Password Fallback
   ```

3. **Frontend Changes**:
   - Modify login to check if user has passkeys
   - Show large "Sign in with Passkey" button
   - Small "Use password instead" link below

This provides the passkey-first experience while using Kratos's native WebAuthn support.