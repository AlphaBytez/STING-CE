# STING-CE Profile Service Guide

## Overview

The STING-CE Profile Service is a microservice that handles user profile management, file uploads, and extended user data. It integrates with Kratos for authentication and Vault for secure file storage.

## Architecture

### Service Components

```
profile_service/
├── api/                    # REST API endpoints
│   └── profile_api.py     # Profile management routes
├── auth/                   # Authentication integration
│   └── profile_auth.py    # Kratos session validation
├── core/                   # Business logic
│   └── profile_manager.py # Profile operations
├── models/                 # Data models
│   └── profile_models.py  # Database models
├── migrations/             # Database migrations
│   └── create_profile_tables.sql
├── Dockerfile             # Container configuration
├── requirements.txt       # Python dependencies
└── server.py              # Main application entry point
```

### Integration Points

- **Kratos**: Authentication and identity management
- **Vault**: Secure file storage for profile pictures
- **PostgreSQL**: Profile metadata and relationships
- **File Service**: Shared file management utilities

## Features

### Core Features

1. **Profile Management**
   - Create, read, update, delete user profiles
   - Extended profile fields beyond Kratos identity
   - Automatic profile completion calculation

2. **Profile Pictures**
   - Secure upload via Vault storage
   - Image validation and processing
   - Automatic thumbnail generation

3. **Profile Extensions**
   - Custom profile fields (skills, social links, etc.)
   - Public/private visibility controls
   - Extensible JSON-based data storage

4. **Activity Tracking**
   - Profile change history
   - User activity logging
   - IP and user agent tracking

5. **Search and Discovery**
   - Profile search by name/display name
   - Privacy-aware search results
   - Pagination support

### Security Features

- **Authentication**: Kratos session validation
- **Authorization**: Owner-based access control
- **File Security**: Vault encryption for sensitive files
- **Privacy Controls**: Configurable profile visibility
- **Input Validation**: Comprehensive data validation

## API Reference

### Base URL
```
http://localhost:8092/api/profile
```

### Authentication
All endpoints require a valid Kratos session cookie (`ory_kratos_session`).

### Endpoints

#### Profile Management

**Get Current User Profile**
```http
GET /api/profile/
```

**Create Profile**
```http
POST /api/profile/
Content-Type: application/json

{
  "display_name": "John Doe",
  "first_name": "John",
  "last_name": "Doe",
  "bio": "Software developer",
  "location": "San Francisco, CA",
  "website": "https://johndoe.com",
  "timezone": "America/Los_Angeles",
  "preferences": {
    "theme": "dark",
    "notifications": true
  }
}
```

**Update Profile**
```http
PUT /api/profile/
Content-Type: application/json

{
  "bio": "Updated bio",
  "location": "New York, NY"
}
```

**Get User Profile by ID**
```http
GET /api/profile/{user_id}
```

**Delete Profile**
```http
DELETE /api/profile/
```

#### Profile Pictures

**Upload Profile Picture**
```http
POST /api/profile/picture
Content-Type: multipart/form-data

file: [image file]
```

**Get Current User's Profile Picture**
```http
GET /api/profile/picture
```

**Get User's Profile Picture**
```http
GET /api/profile/{user_id}/picture
```

#### Search

**Search Profiles**
```http
GET /api/profile/search?q=john&limit=20
```

### Response Format

**Success Response**
```json
{
  "success": true,
  "profile": {
    "id": "uuid",
    "user_id": "uuid",
    "display_name": "John Doe",
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "bio": "Software developer",
    "location": "San Francisco, CA",
    "website": "https://johndoe.com",
    "profile_picture_file_id": "uuid",
    "timezone": "America/Los_Angeles",
    "language": "en",
    "profile_completion": "complete",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
}
```

**Error Response**
```json
{
  "success": false,
  "error": "Error message",
  "code": "ERROR_CODE"
}
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROFILE_SERVICE_ENABLED` | Enable profile service | `true` |
| `PROFILE_SERVICE_PORT` | Service port | `8092` |
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `VAULT_ADDR` | Vault server address | `http://vault:8200` |
| `VAULT_TOKEN` | Vault authentication token | `root` |
| `KRATOS_PUBLIC_URL` | Kratos public API URL | `https://localhost:4433` |
| `KRATOS_ADMIN_URL` | Kratos admin API URL | `http://kratos:4434` |
| `PROFILE_MAX_FILE_SIZE` | Maximum file upload size | `52428800` (50MB) |
| `PROFILE_ALLOWED_IMAGE_TYPES` | Allowed image MIME types | `image/jpeg,image/png,image/webp` |

### Configuration File

Add to `conf/config.yml.default`:

```yaml
profile_service:
  enabled: true
  port: 8092
  max_file_size: 52428800  # 50MB
  allowed_image_types:
    - "image/jpeg"
    - "image/png"
    - "image/webp"
  image_processing:
    max_width: 1024
    max_height: 1024
    quality: 85
  features:
    profile_pictures: true
    profile_extensions: true
    activity_logging: true
    search: true
  privacy:
    default_visibility: "private"
    allow_public_profiles: true
```

## Database Schema

### Tables

#### user_profiles
Extended user profile data that complements Kratos identity.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `user_id` | UUID | Links to Kratos identity ID |
| `display_name` | VARCHAR(100) | User's display name |
| `first_name` | VARCHAR(50) | First name |
| `last_name` | VARCHAR(50) | Last name |
| `bio` | TEXT | User biography |
| `location` | VARCHAR(100) | User location |
| `website` | VARCHAR(255) | Personal website |
| `phone` | VARCHAR(20) | Phone number |
| `profile_picture_file_id` | UUID | Links to file_assets table |
| `timezone` | VARCHAR(50) | User timezone |
| `language` | VARCHAR(10) | Preferred language |
| `preferences` | JSONB | User preferences |
| `privacy_settings` | JSONB | Privacy settings |
| `profile_completion` | VARCHAR(20) | Completion status |
| `last_activity` | TIMESTAMP | Last activity time |
| `created_at` | TIMESTAMP | Creation time |
| `updated_at` | TIMESTAMP | Last update time |
| `deleted_at` | TIMESTAMP | Soft deletion time |

#### profile_extensions
Custom profile fields and extensions.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `profile_id` | UUID | Links to user_profiles |
| `extension_type` | VARCHAR(50) | Type of extension |
| `extension_data` | JSONB | Extension data |
| `is_public` | BOOLEAN | Public visibility |
| `sort_order` | VARCHAR(10) | Display order |

#### profile_activities
Profile activity and change tracking.

| Column | Type | Description |
|--------|------|-------------|
| `id` | UUID | Primary key |
| `profile_id` | UUID | Links to user_profiles |
| `activity_type` | VARCHAR(50) | Type of activity |
| `activity_data` | JSONB | Activity details |
| `ip_address` | VARCHAR(45) | User IP address |
| `user_agent` | TEXT | User agent string |
| `created_at` | TIMESTAMP | Activity time |

## Deployment

### Docker Compose

The profile service is included in the main `docker-compose.yml`:

```yaml
profile:
  container_name: sting-ce-profile
  build:
    context: ./profile_service
    dockerfile: Dockerfile
  environment:
    - DATABASE_URL=postgresql://postgres:postgres@db:5432/sting_app?sslmode=disable
    - VAULT_ADDR=http://vault:8200
    - VAULT_TOKEN=${VAULT_TOKEN:-root}
  ports:
    - "8092:8092"
  depends_on:
    - vault
    - db
    - kratos
```

### Database Migration

Run the database migration to create required tables:

```bash
python run_profile_migration.py
```

### Health Checks

The service provides health check endpoints:

```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "database": "healthy",
  "vault": "healthy",
  "service": "profile-service",
  "version": "1.0.0"
}
```

## Development

### Local Development

1. **Set up environment**:
   ```bash
   export DATABASE_URL="postgresql://postgres:postgres@localhost:5433/sting_app"
   export VAULT_ADDR="http://localhost:8200"
   export VAULT_TOKEN="root"
   ```

2. **Install dependencies**:
   ```bash
   cd profile_service
   pip install -r requirements.txt
   ```

3. **Run migrations**:
   ```bash
   python ../run_profile_migration.py
   ```

4. **Start the service**:
   ```bash
   python server.py
   ```

### Testing

The service can be tested using the provided test scripts or curl commands:

```bash
# Test health endpoint
curl http://localhost:8092/health

# Test profile creation (requires authentication)
curl -X POST http://localhost:8092/api/profile/ \
  -H "Content-Type: application/json" \
  -H "Cookie: ory_kratos_session=your_session_cookie" \
  -d '{"display_name": "Test User"}'
```

## Integration with Frontend

### React Integration

The profile service integrates with the React frontend through the existing ProfileContext:

```javascript
// Update ProfileContext to use profile service
const ProfileContext = createContext();

export const ProfileProvider = ({ children }) => {
  const [profile, setProfile] = useState(null);
  
  const fetchProfile = async () => {
    const response = await fetch('/api/profile/', {
      credentials: 'include'
    });
    const data = await response.json();
    if (data.success) {
      setProfile(data.profile);
    }
  };
  
  const updateProfile = async (profileData) => {
    const response = await fetch('/api/profile/', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(profileData)
    });
    const data = await response.json();
    if (data.success) {
      setProfile(data.profile);
    }
    return data;
  };
  
  return (
    <ProfileContext.Provider value={{ profile, fetchProfile, updateProfile }}>
      {children}
    </ProfileContext.Provider>
  );
};
```

### Profile Picture Integration

```javascript
const uploadProfilePicture = async (file) => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch('/api/profile/picture', {
    method: 'POST',
    credentials: 'include',
    body: formData
  });
  
  return response.json();
};
```

## Security Considerations

### Authentication
- All endpoints require valid Kratos session
- Session validation through Kratos public API
- Automatic session expiry handling

### Authorization
- Users can only access their own profiles
- Admin users can access all profiles
- Public profile data available to authenticated users

### File Security
- Profile pictures stored in encrypted Vault
- File type validation and size limits
- Malicious file detection

### Privacy
- Configurable profile visibility
- Private data filtering for non-owners
- Activity logging for audit trails

## Troubleshooting

### Common Issues

**Service won't start**
- Check database connectivity
- Verify Vault is running and accessible
- Ensure Kratos is healthy

**Profile pictures not uploading**
- Check file size limits
- Verify allowed file types
- Check Vault connectivity

**Authentication errors**
- Verify Kratos session cookies
- Check Kratos public URL configuration
- Ensure CORS settings allow credentials

### Logs

Service logs are available in:
- Container logs: `docker logs sting-ce-profile`
- Volume logs: `/var/log/profile-service/`

### Debug Mode

Enable debug mode for detailed logging:
```bash
export FLASK_ENV=development
```

## Future Enhancements

### Planned Features
- **Profile Templates**: Pre-defined profile layouts
- **Social Features**: Following/followers system
- **Profile Verification**: Identity verification badges
- **Advanced Search**: Skills, location-based search
- **Profile Analytics**: View statistics and insights
- **Bulk Operations**: Admin bulk profile management

### API Versioning
Future API versions will be available at:
- `/api/v2/profile/` - Next major version
- Backward compatibility maintained for v1

---

*This guide covers the complete STING-CE Profile Service implementation. For additional support, refer to the main STING documentation or create an issue in the project repository.*