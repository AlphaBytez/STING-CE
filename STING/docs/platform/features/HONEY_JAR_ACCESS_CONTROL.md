# Honey Jar Access Control Documentation

## Overview

STING's Knowledge Service implements a comprehensive access control system for honey jars (knowledge repositories). This system ensures that sensitive information is properly protected while allowing flexible sharing within teams and organizations.

## Configuration

All access control settings can be configured through the `config.yml` file. Here's a complete reference:

```yaml
# Knowledge Service Configuration
knowledge_service:
  # Authentication settings
  authentication:
    # Development mode - bypasses authentication checks
    # WARNING: Only use this for development/testing!
    development_mode: false
    
    # Mock user for development mode
    development_user:
      id: "dev-user"
      email: "dev@sting.local"
      role: "admin"
      name:
        first: "Dev"
        last: "User"
  
  # Access control settings
  access_control:
    # Default permissions for new honey jars
    default_permissions:
      public:
        read: true
        write: false
      private:
        read: false
        write: false
    
    # Roles that can create honey jars
    creation_roles:
      - "admin"
      - "support"
      - "moderator"
      - "editor"
    
    # Enable team-based access control
    team_based_access: true
    
    # Enable passkey requirement for sensitive jars
    passkey_protection:
      enabled: false  # Set to true when implementing passkey auth
      sensitivity_levels:
        - "confidential"
        - "restricted"
        - "secret"
```

## Permission Model

### 1. **Role-Based Access Control (RBAC)**

Users are assigned roles that determine their base permissions:

- **admin**: Full access to all honey jars and system functions
- **support**: Can create and manage honey jars, limited admin functions
- **moderator**: Can create honey jars and moderate content
- **editor**: Can create and edit honey jars
- **user**: Basic user, read-only access to public jars by default

### 2. **Honey Jar Types**

Each honey jar has a type that affects its default permissions:

- **public**: Readable by all authenticated users
- **private**: Only accessible to owner and explicitly granted users/roles
- **premium**: Special access tier (future feature)

### 3. **Permission Levels**

For each honey jar, users can have different permission levels:

- **read**: View honey jar contents and search
- **write**: Upload documents and edit metadata
- **delete**: Remove the honey jar (owner/admin only)

### 4. **Access Control Rules**

Access is granted based on a hierarchy of rules:

1. **Owner Access**: The creator of a honey jar always has full access
2. **Admin Override**: Administrators can access all honey jars
3. **Explicit Permissions**: Users/roles explicitly granted access
4. **Team Permissions**: Members of allowed teams get access
5. **Public Access**: For public jars, all authenticated users get read access

## API Endpoints and Permissions

| Endpoint | Method | Required Permission | Description |
|----------|--------|-------------------|-------------|
| `/honey-jars` | GET | Authenticated | Lists only accessible honey jars |
| `/honey-jars` | POST | Creation Role | Create new honey jar |
| `/honey-jars/{id}` | GET | Read Access | View honey jar details |
| `/honey-jars/{id}` | DELETE | Delete Access | Remove honey jar |
| `/honey-jars/{id}/documents` | GET | Read Access | List documents |
| `/honey-jars/{id}/documents` | POST | Write Access | Upload documents |
| `/honey-jars/{id}/export` | GET | Read Access | Export honey jar |
| `/search` | POST | Authenticated | Search accessible jars |

## Setting Permissions

### When Creating a Honey Jar

```python
# Example: Create a team-restricted honey jar
{
    "name": "Marketing Campaign Data",
    "description": "Q4 2024 campaign materials",
    "type": "private",
    "tags": ["marketing", "campaigns"],
    "permissions": {
        "allowed_roles": ["marketing", "admin"],
        "allowed_teams": ["marketing-team"],
        "allowed_users": ["john@company.com", "jane@company.com"]
    }
}
```

### Permission Structure

```python
permissions = {
    # Public access flags
    "public_read": False,      # Allow all users to read
    "public_write": False,     # Allow all users to write (rare)
    
    # Role-based access
    "allowed_roles": [],       # Roles with read access
    "edit_roles": [],          # Roles with write access
    
    # User-specific access
    "allowed_users": [],       # Users with read access
    "edit_users": [],          # Users with write access
    "delete_users": [],        # Users who can delete
    
    # Team-based access
    "allowed_teams": [],       # Teams with read access
    "edit_teams": []           # Teams with write access
}
```

## Development Mode

For development and testing, you can enable development mode which bypasses authentication:

1. **In config.yml**:
   ```yaml
   knowledge_service:
     authentication:
       development_mode: true
   ```

2. **Via Environment Variable**:
   ```bash
   export KNOWLEDGE_DEV_MODE=true
   ```

⚠️ **WARNING**: Never enable development mode in production!

## Audit Logging

All access attempts are logged for security auditing:

- Successful and failed access attempts
- User identity and timestamp
- Resource accessed and action performed
- Additional context (IP address, session ID, etc.)

Configure audit settings in config.yml:

```yaml
knowledge_service:
  audit:
    enabled: true
    retention_days: 90
    log_actions:
      - "create"
      - "read"
      - "update"
      - "delete"
      - "export"
      - "search"
      - "upload"
```

## Testing Access Control

Use the provided test script to verify access control:

```bash
# Run full access control test suite
python test_honey_jar_access_control.py

# Quick test with admin user
python test_honey_jar_access_control.py quick
```

The test script will:
1. Test different user roles (admin, marketing, basic user)
2. Verify creation permissions
3. Test access to different honey jar types
4. Verify document upload permissions
5. Test search result filtering

## Best Practices

1. **Principle of Least Privilege**: Grant only the minimum necessary permissions
2. **Use Teams**: Organize users into teams for easier permission management
3. **Regular Audits**: Review access logs and permissions regularly
4. **Document Sensitivity**: Mark sensitive honey jars appropriately
5. **Test Permissions**: Always test access control after configuration changes

## Troubleshooting

### Common Issues

1. **"Access denied" errors**:
   - Check user's role and team membership
   - Verify honey jar permissions
   - Check if development mode is accidentally enabled

2. **Can't create honey jars**:
   - Verify user has a creation role
   - Check `creation_roles` configuration

3. **Search not filtering results**:
   - Ensure authentication is working
   - Check if user session is valid
   - Verify honey jar permissions are set correctly

### Debug Mode

Enable debug logging to troubleshoot access issues:

```python
# In knowledge_service/app.py
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

1. **Passkey Protection**: Require passkey authentication for sensitive honey jars
2. **Time-based Access**: Temporary access grants with expiration
3. **Approval Workflows**: Request/approve access for restricted jars
4. **Access Analytics**: Dashboard showing access patterns
5. **Fine-grained Permissions**: Document-level access control