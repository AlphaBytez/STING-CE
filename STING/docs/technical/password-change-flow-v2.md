# Password Change Flow V2 - Database-Based Solution

## Overview

This document describes the V2 implementation of the password change flow that uses a Flask database table instead of Kratos identity traits. This approach was implemented to solve redirect loop issues caused by Kratos schema validation rejecting custom fields.

## Problem Statement

The original implementation attempted to store `force_password_change` and `role` fields in Kratos identity traits. However:
1. The default Kratos identity schema doesn't allow these custom fields
2. Creating a custom schema file led to mounting and path resolution issues
3. Schema validation failures caused redirect loops during authentication

## Solution Architecture

### 1. UserSettings Model (`app/models/user_settings.py`)
- Stores user settings in a Flask-managed database table
- Fields include:
  - `user_id` - Kratos identity ID
  - `email` - User email
  - `force_password_change` - Boolean flag
  - `password_changed_at` - Timestamp
  - `role` - User role (admin, user, etc.)

### 2. Force Password Change Middleware V2 (`app/middleware/force_password_change_v2.py`)
- Checks UserSettings table instead of Kratos traits
- Applied as Flask before_request middleware
- Allows specific endpoints without password change
- Returns appropriate JSON/redirect responses

### 3. Default Admin Setup V2 (`app/utils/default_admin_setup_v2.py`)
- Creates admin user in Kratos with standard fields only
- Creates corresponding UserSettings entry with:
  - `role='admin'`
  - `force_password_change=True`
- Generates secure random password
- Stores password in filesystem for initial login

### 4. Updated Authentication Flow
```
1. User attempts login
2. Kratos validates credentials
3. Flask session created
4. Middleware checks UserSettings.force_password_change
5. If true, redirects to password change page
6. After password change:
   - Kratos password updated via Admin API
   - UserSettings.force_password_change set to false
   - User can access all features
```

## Database Migration

Run the migration to create the user_settings table:
```sql
-- See migrations/add_user_settings_table.sql
CREATE TABLE user_settings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    force_password_change BOOLEAN DEFAULT FALSE,
    password_changed_at TIMESTAMP,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation Files

1. **Models**:
   - `/app/models/user_settings.py` - UserSettings model

2. **Middleware**:
   - `/app/middleware/force_password_change_v2.py` - V2 middleware using database

3. **Utils**:
   - `/app/utils/default_admin_setup_v2.py` - V2 admin setup using database

4. **Routes**:
   - `/app/routes/auth_routes.py` - Updated to use UserSettings.mark_password_changed()

5. **App Initialization**:
   - `/app/__init__.py` - Uses V2 middleware and admin setup

## Benefits

1. **No Schema Conflicts**: Kratos uses standard schema, custom fields in separate table
2. **Flexible Storage**: Can add new user settings without modifying Kratos
3. **Better Control**: Direct database queries instead of Kratos API calls
4. **Reliability**: Avoids schema validation issues and redirect loops

## Migration from V1

To migrate from the original implementation:

1. Run the database migration to create user_settings table
2. Update app service to use new code
3. Restart the app service
4. Existing admin users will need to be migrated manually or recreated

## Testing

1. Fresh install should create admin with force_password_change=true
2. Login with admin credentials should redirect to password change
3. After password change, flag should be cleared
4. Regular navigation should work without redirects

## Future Enhancements

1. Add more user preferences to UserSettings table
2. Create admin UI for managing user settings
3. Add bulk operations for user management
4. Consider migrating other Kratos traits to this table