# STING Admin Guide

## Overview

This guide covers administrative features and workflows for STING administrators, including user management, document approval, and system configuration.

## Admin Access

Admin users have additional privileges including:
- Access to the Admin Panel via the sidebar
- Ability to approve/reject pending documents
- Direct upload to any honey jar without approval
- User management capabilities (coming soon)
- System-wide honey jar management

## Document Approval Workflow

### Understanding the Approval System

STING implements a document approval workflow to maintain quality and security in public knowledge bases:

1. **Admin Users**: Can upload documents directly to any honey jar
2. **Honey Jar Owners**: Can upload directly to their own honey jars
3. **Regular Users**: 
   - Can upload to public honey jars, but documents go to a pending queue
   - Documents require admin or owner approval before becoming available
   - Users receive feedback that their uploads are pending approval

### Managing Pending Documents

1. **Access the Admin Panel**:
   - Look for the "Admin" tab in the sidebar (only visible to admin users)
   - Click to open the Admin Panel

2. **Review Pending Documents**:
   - Select "Pending Documents" tab
   - Choose a honey jar from the dropdown to see its pending documents
   - View document details including:
     - Filename and type
     - Uploader information
     - Upload date and time
     - File size

3. **Approve Documents**:
   - Click the green "Approve" button next to a document
   - The document will be immediately moved to the honey jar
   - The uploader's contribution is recorded

4. **Reject Documents**:
   - Click the red "Reject" button
   - Optionally provide a rejection reason
   - The document will be deleted and not added to the honey jar

### Best Practices for Document Review

1. **Review Content Type**: Ensure documents are appropriate for the honey jar
2. **Check File Size**: Large files may impact performance
3. **Verify Relevance**: Ensure documents match the honey jar's purpose
4. **Security Review**: Check for potentially sensitive information
5. **Provide Feedback**: When rejecting, give helpful reasons

## User Roles and Permissions

### Current Role System

STING uses a role-based access control system synchronized with Ory Kratos:

1. **Admin Role** (`role: admin`):
   - Full system access
   - Can manage all honey jars
   - Access to admin panel
   - Can approve/reject documents
   - Can promote other users (coming soon)

2. **User Role** (`role: user`):
   - Default role for new registrations
   - Can create private honey jars
   - Can upload to public honey jars (pending approval)
   - Can query all accessible honey jars

3. **Moderator Role** (`role: moderator`) - Future:
   - Can approve documents for specific honey jars
   - Limited admin capabilities

4. **Support Role** (`role: support`) - Future:
   - Can view system diagnostics
   - Can assist users with issues

### Managing User Roles

Currently, user roles are set in the Kratos identity schema. To change a user's role:

1. **Via Kratos Admin API**:
   ```bash
   # Update user traits to set admin role
   curl -X PATCH https://localhost:4434/admin/identities/{identity_id} \
     -H "Content-Type: application/json" \
     -d '{
       "traits": {
         "email": "user@example.com",
         "name": {"first": "John", "last": "Doe"},
         "role": "admin"
       }
     }'
   ```

2. **Future Admin Panel Features**:
   - User list with role management
   - One-click role promotion/demotion
   - Bulk user operations

## Honey Jar Management

### Admin Honey Jar Privileges

Admins can:
- View all honey jars regardless of visibility settings
- Upload documents to any honey jar without approval
- Delete any document from any honey jar
- Export any honey jar
- Modify honey jar permissions

### Creating System Honey Jars

System-wide honey jars for documentation or shared resources:

1. Create a new honey jar
2. Set type to "Public"
3. Upload foundational documents
4. These become available to all users immediately

### Managing Permissions

Future permission features will include:
- Group-based access control
- Team honey jar management
- Granular permission settings
- Access audit logs

## Security Considerations

### Document Security

1. **Review Uploads**: Always review documents from untrusted users
2. **PII Protection**: Check for personally identifiable information
3. **Malware Scanning**: Future versions will include automatic scanning
4. **Access Logs**: All document operations are logged for audit

### API Security

Admin API endpoints require:
- Valid session with admin role
- CSRF protection for state-changing operations
- Rate limiting to prevent abuse

## Admin Dashboard (Coming Soon)

Future admin dashboard features:
- System statistics and metrics
- User activity monitoring
- Honey jar usage analytics
- Performance monitoring
- Security alerts

## Troubleshooting Admin Issues

### Common Issues

**"Admin tab not visible"**:
- Verify your account has admin role
- Try logging out and back in
- Check browser console for errors

**"Cannot approve documents"**:
- Ensure you're accessing owned honey jars or have admin role
- Check knowledge service is running: `./manage_sting.sh status knowledge`
- Review logs: `./manage_sting.sh logs knowledge`

**"Pending documents not loading"**:
- Verify honey jar has pending documents
- Check network requests in browser developer tools
- Ensure proper authentication cookies are sent

### Debug Commands

```bash
# Check user role in Kratos
curl -k https://localhost:4433/sessions/whoami \
  -H "Cookie: ory_kratos_session=YOUR_SESSION_COOKIE"

# View knowledge service logs
./manage_sting.sh logs knowledge -f

# Check pending documents via API
curl -k https://localhost:8443/api/knowledge/honey-jars/{id}/pending-documents \
  -H "Cookie: your-session-cookie"
```

## Best Practices

1. **Regular Reviews**: Check pending documents daily
2. **Clear Guidelines**: Establish document standards for public honey jars
3. **User Communication**: Provide feedback when rejecting documents
4. **Backup Important Data**: Regularly export critical honey jars
5. **Monitor Usage**: Track which users contribute most

## Future Enhancements

Planned admin features:
- Email notifications for pending documents
- Bulk approval/rejection operations
- Auto-approval rules based on user trust level
- Content moderation AI assistance
- Advanced user management interface
- System configuration UI
- Audit log viewer
- Performance analytics dashboard

## Getting Help

For admin-specific support:
- Check the STING CE documentation
- Review the Claude.md file for technical details
- Contact the development team
- Submit issues on GitHub

## Related Documentation

- [Honey Jar User Guide](./features/HONEY_JAR_USER_GUIDE.md)
- [Honey Jar Technical Reference](./features/HONEY_JAR_TECHNICAL_REFERENCE.md)
- [Authentication Setup](./ADMIN_SETUP.md)
- [API Reference](./API_REFERENCE.md)