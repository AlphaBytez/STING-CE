# 🐝 STING CE Clean Install Checklist

## Pre-Install Preparation ✅

### 1. Backup Important Data (if needed)
```bash
# Backup any custom configurations
cp -r ~/.sting-ce/custom_configs ~/sting-backup/ 2>/dev/null || true

# Backup any custom honey jars data
docker exec sting-ce-knowledge-service tar -czf /tmp/honey_jars_backup.tar.gz /app/data/ 2>/dev/null || true
docker cp sting-ce-knowledge-service:/tmp/honey_jars_backup.tar.gz ~/sting-backup/ 2>/dev/null || true
```

### 2. Clean Uninstall
```bash
# Use the enhanced uninstall script
./uninstall.sh

# Verify complete cleanup
docker system prune -a
docker volume prune -f
rm -rf ~/.sting-ce/
```

## Fresh Install Process 🚀

### 3. Pull Latest Changes
```bash
git pull origin main
```

### 4. Fresh Install
```bash
./install.sh
```

### 5. Wait for Services to Stabilize
```bash
# Monitor service startup
./manage_sting.sh status

# Wait until all services are healthy (may take 2-3 minutes)
# Look for all services showing "healthy" status
```

## Post-Install Authentication Setup 🔐

### 6. Verify Admin Account Creation
```bash
# Run the diagnostic to confirm admin was created properly
./scripts/diagnose_admin_status.sh
```

### 7. Initial Admin Login & Password Change
```bash
# Get admin password
cat ~/.sting-ce/admin_password.txt

# Login at: https://localhost:3000/login
# Email: admin@sting.local
# Password: [from file above]

# You should be redirected to change password
# Choose a strong password and confirm
```

### 8. **MANDATORY TOTP Setup**
After password change, you should be redirected to TOTP setup:
- Scan QR code with authenticator app (Google Authenticator, Authy, 1Password, etc.)
- Enter TOTP code to verify
- **Dashboard access will be blocked until TOTP is configured**

### 9. Verify Full Authentication Flow
- Logout
- Login with new password
- Enter TOTP code when prompted
- Confirm dashboard access works

## Feature Testing 🧪

### 10. Test Core Features
```bash
# Test PII Configuration (Admin Panel → PII Configuration Manager)
# Test Honey Jars creation and access
# Test Bee Chat functionality
# Test user management (if needed)
```

### 11. Configure PII Compliance Profiles
- Navigate to Admin Panel → PII Configuration Manager
- Click on "Compliance Profiles" tab
- Click the ⚙️ (settings) button on any profile
- Explore the comprehensive settings framework

### 12. Set Up Reporting (Future)
- Verify reporting health check
- Test report generation
- Configure LLM integration options

## Security Verification ✅

### 13. Confirm Security Measures
- [ ] Admin password changed from default
- [ ] TOTP is configured and working
- [ ] No force_password_change loops
- [ ] Session management working properly
- [ ] PII compliance settings accessible

### 14. Performance Check
```bash
# Verify all services are healthy
./manage_sting.sh status

# Check resource usage
docker stats --no-stream
```

## Troubleshooting 🔧

### Common Issues After Fresh Install

**Admin Login Issues:**
```bash
# Check admin status
./scripts/diagnose_admin_status.sh

# If needed, recover admin account
./scripts/recover_admin_account.sh
```

**Service Startup Issues:**
```bash
# Restart specific service
./manage_sting.sh restart [service-name]

# Check service logs
./manage_sting.sh logs [service-name]
```

**TOTP Not Working:**
- Ensure time sync between server and authenticator app
- Try regenerating TOTP in Security Settings
- Use backup codes if available

## Success Criteria ✅

Fresh install is successful when:
- [ ] All services running and healthy
- [ ] Admin can login with new password + TOTP
- [ ] Dashboard fully accessible
- [ ] PII configuration manager works
- [ ] No authentication loops or errors
- [ ] Honey jars can be created/accessed
- [ ] Bee Chat responds properly

---

## Next Steps After Clean Install

1. **Configure PII compliance** for your use case
2. **Set up reporting features** and admin panel enhancements  
3. **Implement LLM integration** (local + external APIs)
4. **Test comprehensive workflows** end-to-end

## Emergency Recovery

If something goes wrong during install:
```bash
# Nuclear option - complete cleanup and retry
./uninstall.sh
docker system prune -a -f
docker volume prune -f
rm -rf ~/.sting-ce/
git pull origin main
./install.sh
```