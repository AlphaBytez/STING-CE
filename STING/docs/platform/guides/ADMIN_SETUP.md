# STING Admin User Setup Guide

This guide covers how to create and manage admin users in STING.

## Quick Setup

### Step 1: Set Up Custom Domain (Optional but Recommended)

For a consistent development experience, set up a custom domain:

```bash
# Default setup with queen.hive domain
sudo ./setup_custom_domain.sh

# Or set up with your own domain
sudo CUSTOM_DOMAIN=mysting.local ./setup_custom_domain.sh
```

This will configure your system to access STING at:
- 🌐 **Main App**: `https://queen.hive:8443` (or your custom domain)
- 🔐 **Auth Service**: `https://auth.queen.hive:4433`
- 🔧 **API**: `https://api.queen.hive:5050`

### Step 2: Create First Admin User

#### Option 1: Automated First Admin Setup (Recommended)
```bash
# Run the setup script for first admin with temporary password
./setup_first_admin.sh
```

#### Option 2: Manual Admin Creation
```bash
# Create admin with temporary password
python3 create_admin.py --email admin@yourcompany.com --temp-password

# Create admin with custom password
python3 create_admin.py --email admin@yourcompany.com
```

#### Option 3: First User Auto-Promotion
- Simply register the first user through the UI
- They will automatically be promoted to super admin

## Verification

### Check Admin Status
```bash
# Check current admin users
python3 check_admin.py
```

### Browser Console Debugging
Open browser developer tools and check console for role loading messages:
- `🔍 Loading user role...`
- `👑 User is super admin` or `🛡️ User is admin`

## Admin Features

### What Admins Can Access
1. **🐝 LLM Settings Tab** - Appears in Settings page for admins only
2. **Model Management** - Change, restart, and monitor LLM models
3. **Progress Tracking** - Real-time model loading with terminal output
4. **User Management** - Promote other users (super admin only)

### LLM Settings Location
- **Path**: Settings → 🐝 LLM Settings tab
- **URL**: `https://localhost:8443/dashboard/settings`
- **Features**: Model selection, service restart, progress tracking

## Security Features

### Automatic Protections
- First user is auto-promoted to super admin
- Admin tabs only visible to admin users
- API endpoints require admin authentication
- Temporary passwords force change on first login

### Manual Security Steps
1. **Change temporary passwords immediately**
2. **Use strong passwords for admin accounts**
3. **Regularly review admin user list**
4. **Monitor admin activities in logs**

## Troubleshooting

### Admin Tab Not Visible
1. **Check user role in browser console**:
   ```javascript
   // In browser console
   localStorage.getItem('user-role') // Check stored role
   ```

2. **Verify admin status**:
   ```bash
   python3 check_admin.py
   ```

3. **Check backend user data**:
   ```bash
   # In browser console, check network tab for /api/users/me response
   ```

### User Not Auto-Promoted
- Ensure they're the first user: `python3 check_admin.py`
- Check Flask logs for promotion messages
- Manually promote: `python3 create_admin.py --email user@email.com`

### API Endpoints Not Working
- Verify user is authenticated (check browser session)
- Check Flask blueprint registration
- Ensure user endpoints are enabled

## Admin Management

### Promote Existing User
```python
# Via Python script (future enhancement)
from app.services.user_service import UserService
UserService.promote_user_to_admin(user_id, admin_user_id)
```

### Demote Admin User
```python
# Via database/Python (future enhancement)
user.demote_from_admin()
```

## API Endpoints

### User Role Endpoints
- `GET /api/users/me` - Get current user info with admin flags
- `GET /api/users/stats` - Admin user statistics
- `POST /api/users/<id>/promote` - Promote user to admin

### LLM Management (Admin Only)
- `POST /api/llm/load` - Start model loading with progress tracking
- `GET /api/llm/progress/<id>` - Get loading progress
- `POST /api/llm/restart` - Restart LLM service

## Files Created/Modified

### New Scripts
- `create_admin.py` - Programmatic admin creation
- `setup_first_admin.sh` - Quick setup script
- `check_admin.py` - Admin status verification

### Enhanced Components
- `UserSettings.jsx` - Added admin-only LLM Settings tab
- `RoleContext.jsx` - Fixed for Kratos authentication
- `User model` - Added admin promotion methods
- `user_routes.py` - Added `/api/users/me` endpoint

### Progress Tracking
- `BeeSettings.jsx` - Enhanced with progress modal
- `ProgressBar.jsx` - Visual progress component
- `TerminalOutput.jsx` - Live terminal component
- `llm_routes.py` - Async loading with progress

## Custom Domain and Network Access

### Default Development Domain

STING can be configured with a custom domain for consistent development experience. The recommended default is `queen.hive`:

```bash
# Set up default queen.hive domain
sudo ./setup_custom_domain.sh

# Access STING at:
# https://queen.hive:8443
```

### Network Access from Other Devices

To allow access from other devices on your network:

1. **Find your local IP address**:
   ```bash
   # macOS
   ifconfig | grep 'inet ' | grep -v 127.0.0.1
   
   # Linux
   ip addr show | grep 'inet ' | grep -v 127.0.0.1
   ```

2. **Configure STING for network access**:
   ```bash
   # Update config.yml to use your IP
   sed -i 's/localhost/YOUR_LOCAL_IP/g' conf/config.yml
   
   # Regenerate environment files
   ./manage_sting.sh regenerate-env
   
   # Restart services
   ./manage_sting.sh restart
   ```

3. **Share access URL**:
   - Share: `https://YOUR_LOCAL_IP:8443`
   - Users must accept the self-signed certificate warning

### Production Domain Setup

For production deployments:

1. **Use a real domain with proper SSL certificates**
2. **Update `conf/config.yml` with production domain**
3. **Configure proper SSL certificates (not self-signed)**
4. **Set up reverse proxy (nginx/traefik) for clean URLs**

## Best Practices

1. **Always use programmatic admin creation** for production
2. **Generate temporary passwords** for initial admin setup
3. **Force password changes** on first login
4. **Monitor admin activities** through logs
5. **Regularly audit admin user list**
6. **Use principle of least privilege** - don't give everyone admin
7. **Use custom domains** for consistent experience across environments

## Example Workflow

1. **Fresh Installation**:
   ```bash
   ./install_sting.sh install
   ./setup_first_admin.sh  # Creates admin with temp password
   ```

2. **Admin logs in and changes password**

3. **Admin accesses LLM settings**:
   - Go to Settings → 🐝 LLM Settings
   - Select different model
   - Watch progress tracking
   - Use terminal output for debugging

4. **Admin creates additional admins**:
   ```bash
   python3 create_admin.py --email newadmin@company.com --temp-password
   ```

This provides a robust, secure admin system for your STING MVP! 🎯