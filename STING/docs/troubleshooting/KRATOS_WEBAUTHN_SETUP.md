# Kratos WebAuthn Setup Guide

## The Issue

You were seeing two different passkey IDs because:
1. One was from the OLD custom WebAuthn system (stored in PostgreSQL)
2. The browser was trying to use this old passkey
3. But the backend handler was disabled, so authentication failed

## Solution

### Step 1: Clear Browser Passkeys (REQUIRED!)

**YES, you MUST delete the passkey on the client side!** The browser has cached the old passkey and will keep offering it even though the backend can't handle it.

1. **Chrome/Edge**: 
   - Go to `chrome://settings/passkeys` or `edge://settings/passkeys`
   - Find ALL entries for `localhost` (there may be multiple)
   - Delete each one
   - Alternative: Settings → Autofill → Password Manager → Search "localhost" → Delete all

2. **Clear all site data**:
   - Open https://localhost:8443
   - Press F12 for Developer Tools
   - Go to Application → Storage
   - Click "Clear site data"
   - Close and reopen the browser

**Why this is necessary**: The frontend code checks if WebAuthn is available in the browser (`navigator.credentials`), NOT whether you have valid Kratos passkeys. So it shows the passkey button even though the old passkeys won't work.

### Step 2: Clean Database (Already Done)

The old passkeys have been removed from the database.

### Step 3: Set Up New Kratos Passkey

1. **Login with password**:
   - Go to https://localhost:8443/login
   - Use `admin@sting.local` and your password

2. **Navigate to Settings**:
   - Click on your user menu
   - Go to "Account Settings" or "Security Settings"

3. **Add Passkey**:
   - Look for "Passkeys" or "Security Keys" section
   - Click "Add Passkey" or similar
   - Follow browser prompts to create a new passkey

4. **Test**:
   - Logout
   - Try logging in with your new passkey

### Important Notes

- The passkey flow requires the identifier (email) to be submitted first
- Only passkeys created through Kratos will work now
- Old custom passkeys are incompatible with Kratos WebAuthn

### Troubleshooting

If passkey login still doesn't work:

1. Check browser console for errors
2. Ensure WebAuthn script loads: `window.__oryWebAuthnInitialized` should be `true`
3. Check that form submission happens after passkey selection
4. Visit `/debug/passkey` for detailed debugging

### Technical Details

The issue was that:
- Custom WebAuthn used credential ID: `bkGb1QZBuxLldhdEMEowuS7uPV7a6T8o8IGtpGPm1YM`
- This was stored in the `passkeys` table
- Browser cached this credential
- But `/api/webauthn/*` routes were disabled
- So authentication failed with no POST request

Now:
- Only Kratos WebAuthn is active
- Passkeys are stored in Kratos identity credentials
- Authentication goes through Kratos flows