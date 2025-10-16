# Email Verification Testing Guide

This guide outlines multiple approaches for testing email verification in the STING application during development.

## Overview

Email verification is an important security feature in production, but during development it can slow down testing. This guide presents several options for handling email verification during development, with varying levels of security.

## Option 1: Disable Verification for Development (Recommended)

The most efficient approach for development is to disable the verification requirement entirely.

### Steps:

1. **Use the development configuration:**
   
   ```bash
   # When starting Kratos, use the dev config
   docker-compose exec kratos kratos serve -c /etc/config/kratos/dev.kratos.yml
   ```

2. **Configuration modifications:**
   
   The development configuration (`dev.kratos.yml`) makes the following changes:
   
   - Removes the `show_verification_ui` hook from the registration flow
   - Uses a modified identity schema that doesn't require email verification

   **Security Note:** This approach should ONLY be used in development environments, never in production.

## Option 2: Use Mailpit for Easy Verification Access

STING already includes Mailpit for email testing. We've added integration to easily access verification emails.

### Steps:

1. **Access the Debug Page:**
   
   Visit https://localhost:8443/debug in your browser

2. **Use the Email Verification section:**
   
   - The MailViewer component shows all emails sent by the system
   - Verification links are automatically extracted and can be clicked directly
   - Emails are refreshed automatically every 5 seconds

3. **Alternative access:**
   
   You can access Mailpit directly at https://localhost:8025

## Option 3: Modify Registration Component for Testing

This approach modifies the registration component to skip verification for test accounts.

### Steps:

1. **Use test domain emails:**
   
   In the DirectPasskeyRegistration component, you can add an automatic verification bypass for development domains:
   
   ```javascript
   // If email ends with @example.com or @test.com, it's a test account
   if (email.endsWith('@example.com') || email.endsWith('@test.com')) {
     // Call verification endpoint directly with admin API
     await axios.post(`${kratosAdminUrl}/identities/${identity.id}/verify`, {
       verified: true
     }, {
       headers: {
         'Authorization': 'Bearer YOUR_ADMIN_KEY'
       }
     });
   }
   ```

   **Security Note:** This requires admin API access which should be restricted in production.

## Option 4: Programmatic API Testing

For automated testing, you can use the Admin API to create pre-verified users.

### Steps:

1. **Create Admin API script:**
   
   ```javascript
   // Create a pre-verified test user
   const createTestUser = async () => {
     const response = await axios.post('https://localhost:4434/admin/identities', {
       schema_id: 'default',
       traits: {
         email: 'test@example.com',
         name: {
           first: 'Test',
           last: 'User'
         }
       },
       credentials: {
         password: {
           config: {
             password: 'Test123456!'
           }
         }
       },
       state: 'active',
       verified: true
     }, {
       headers: {
         'Authorization': 'Bearer YOUR_ADMIN_KEY'
       }
     });
     
     return response.data;
   };
   ```

2. **Use for automated testing:**
   
   Add this to your test setup to create verified users automatically.

## Security Considerations

When choosing an approach for development testing, consider:

1. **Data Separation:** Always use separate databases for development and production
2. **Role Separation:** Admin APIs should have different keys in development and production
3. **Environment Marking:** Clearly mark development instances to avoid confusion
4. **Feature Flags:** Use environment-specific feature flags for verification bypass
5. **Local Testing:** Keep development testing on localhost or private networks

## Best Practices

1. **Config Switching:** Use environment variables to switch between dev/prod configs
2. **Secure Defaults:** Always default to secure options, require explicit bypassing
3. **Production Simulation:** Periodically test with verification enabled to catch issues
4. **Audit Trail:** Log all verification bypasses for security audit purposes
5. **Documentation:** Document all testing approaches in your project

## References

- [Ory Kratos Email and Phone Verification](https://www.ory.sh/docs/kratos/selfservice/flows/verify-email-account-activation)
- [Ory Kratos Admin API](https://www.ory.sh/docs/kratos/reference/api)
- [Mailpit Documentation](https://github.com/mailpit/mailpit/wiki)