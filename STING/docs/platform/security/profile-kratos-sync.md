# Profile and Kratos Synchronization Architecture

## Overview

STING maintains user profile data in two places:
1. **STING Database**: Application-specific profile data (bio, location, website, profile picture)
2. **Kratos Identity Store**: Core identity traits (email, name, authentication methods)

## Current Implementation

### Profile Updates (YOUR Profile Settings)
- Updates are saved to STING's database via `/api/users/profile`
- Profile data includes: firstName, lastName, displayName, bio, location, website, profilePicture
- These updates do NOT automatically sync to Kratos
- The backend returns `kratos_sync_needed: true` to indicate sync is required

### Kratos Settings (Security/Authentication)
- Directly managed through Kratos self-service flows
- Handles: password changes, email updates, WebAuthn/passkey registration
- Changes here affect authentication but don't sync back to STING profile

## Profile Update Flow

```javascript
// Frontend: ProfileSettings.jsx
const response = await fetch('/api/users/profile', {
  method: 'PUT',
  headers: { 'Content-Type': 'application/json' },
  credentials: 'include',
  body: JSON.stringify({
    firstName, lastName, displayName,
    bio, location, website, profilePicture
  })
});

// Backend: user_routes.py
@user_bp.route('/profile', methods=['PUT'])
def update_user_profile():
    # Updates STING database
    user.first_name = data['firstName']
    user.last_name = data['lastName']
    # ... other fields
    db.session.commit()
    
    # Returns flag indicating Kratos sync needed
    result['kratos_sync_needed'] = True
```

## Authentication Status

The "unauthenticated" console message in KratosSettings likely indicates:
1. The Kratos session cookie might not be properly set
2. CORS issues between frontend and Kratos
3. The flow initialization requires a valid session

## Recommended Sync Strategy

### Option 1: One-Way Sync (STING → Kratos)
```python
# Add to user_routes.py after profile update
if user.first_name or user.last_name:
    # Call Kratos Admin API to update identity traits
    kratos_admin_api.update_identity(
        identity_id=user.kratos_identity_id,
        traits={
            'email': user.email,
            'name': {
                'first': user.first_name,
                'last': user.last_name
            }
        }
    )
```

### Option 2: Unified Profile Management
- Remove name fields from STING profile
- Always use Kratos for core identity data
- Keep only app-specific data in STING (bio, location, website)

### Option 3: Webhook-Based Sync
- Configure Kratos webhooks to notify STING of identity updates
- Implement webhook handler to sync changes back to STING database

## Security Considerations

1. **Session Management**: Ensure Kratos session is valid before allowing profile updates
2. **Data Consistency**: Profile updates should be atomic across both systems
3. **Permission Checks**: Verify user can only update their own profile
4. **Sensitive Data**: Never sync passwords or authentication credentials

## Implementation TODOs

1. Add Kratos Admin API client to Flask backend
2. Store `kratos_identity_id` in User model
3. Implement sync logic in profile update endpoint
4. Add error handling for sync failures
5. Consider adding a background job for async syncing