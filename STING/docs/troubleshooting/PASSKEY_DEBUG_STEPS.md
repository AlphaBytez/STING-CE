# Passkey Authentication Debug Steps

To help debug the passkey authentication issue, please follow these steps:

## 1. Enable Browser Console Debugging

1. Open Chrome DevTools (F12)
2. Go to the Console tab
3. Clear the console
4. Enable "Preserve log" checkbox

## 2. Try Passkey Login

1. Go to https://localhost:8443/passkey-login
2. Enter your email (admin@sting.local)
3. Click "Sign in with Passkey"
4. When it fails, look for:
   - Any JavaScript errors in the console
   - Network tab: Check the requests to `/api/webauthn/authentication/begin` and `/api/webauthn/authentication/complete`
   - The exact error response from the complete endpoint

## 3. Check Network Tab

1. In DevTools, go to Network tab
2. Filter by "webauthn"
3. Look at the authentication/begin request:
   - Status code (should be 200)
   - Response body (should have publicKey object)
4. Look at the authentication/complete request:
   - Status code
   - Request payload (should have credential object)
   - Response body (error details)

## 4. Share the Following Information

Please share:
1. The exact error message shown in the UI
2. Any console errors (red text in Console tab)
3. The response from `/api/webauthn/authentication/complete` endpoint
4. The request payload sent to `/api/webauthn/authentication/complete`

## 5. Alternative Debug Mode

The CustomPasskeyLogin component has a debug mode:
1. On the passkey login page, click "Show Debug Info" at the bottom
2. Try to login again
3. The debug log will show what's happening step by step

## 6. Check App Logs During Authentication

Run this command while attempting to login:
```bash
docker logs sting-ce-app -f 2>&1 | grep -E "PASSKEY|COMPLETE|authentication|verify"
```

This will show real-time logs as you attempt authentication.