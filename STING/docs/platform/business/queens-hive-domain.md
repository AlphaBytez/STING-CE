# Queen's Hive Domain Setup 🐝👑

## Overview

STING can be configured with a custom domain for a consistent and memorable development experience. The default recommended domain is `queen.hive`, providing a thematic connection to STING's bee-inspired architecture.

## Quick Setup

```bash
# Set up the default queen.hive domain
sudo ./setup_custom_domain.sh

# Or use your own custom domain
sudo CUSTOM_DOMAIN=mysting.local ./setup_custom_domain.sh
```

## Domain Map

Once configured, you can access STING services at these URLs:

| Service | URL | Purpose |
|---------|-----|---------|
| 🌐 **Main Application** | `https://queen.hive:8443` | Main STING web interface |
| 🔐 **Authentication** | `https://auth.queen.hive:4433` | Ory Kratos authentication service |
| 🔧 **API Gateway** | `https://api.queen.hive:5050` | Backend API endpoints |
| 🍯 **Hive Manager** | `https://hive.queen.hive:8443/dashboard/hive` | Manage honey jars and knowledge bases |
| 🐝 **Bee Chat** | `https://bee.queen.hive:8443/dashboard/bee-chat` | AI assistant interface |
| 🏺 **Honey Jars** | `https://honey.queen.hive:8443/dashboard/honey-pot` | Knowledge base browser |
| 🔒 **Vault UI** | `http://vault.queen.hive:8200` | HashiCorp Vault interface |
| 📧 **Mail Testing** | `http://mail.queen.hive:8025` | Mailpit email testing interface |

## Benefits of Custom Domain

1. **Memorable URLs**: Easy to remember and share with team members
2. **Consistent Experience**: Same URLs across different development environments
3. **Theme Consistency**: Reinforces STING's bee/hive metaphor
4. **Subdomain Organization**: Logical separation of services
5. **Network Testing**: Easier to configure for network-wide access

## Network Access Configuration

### Allow Access from Other Devices

1. **Find your local IP address**:
   ```bash
   # macOS
   ifconfig | grep 'inet ' | grep -v 127.0.0.1
   
   # Linux
   ip addr show | grep 'inet ' | grep -v 127.0.0.1
   ```

2. **Update the domain setup for network access**:
   ```bash
   # Set up with your local IP
   sudo CUSTOM_IP=192.168.1.100 ./setup_custom_domain.sh
   ```

3. **Configure other devices**:
   - Add the same entries to their `/etc/hosts` (Linux/Mac) or `C:\Windows\System32\drivers\etc\hosts` (Windows)
   - Or set up a local DNS server for automatic resolution

## Production Considerations

For production deployments:

1. **Use Real Domain**: Register an actual domain (e.g., `sting.yourcompany.com`)
2. **SSL Certificates**: Use Let's Encrypt or commercial SSL certificates
3. **DNS Configuration**: Set up proper DNS records
4. **Reverse Proxy**: Configure nginx/traefik for clean URLs without ports
5. **Security**: Implement proper firewall rules and access controls

## Troubleshooting

### Certificate Warnings
You'll see SSL certificate warnings because STING uses self-signed certificates in development. This is normal - just accept the certificate exception in your browser.

### Domain Not Resolving
1. Ensure you ran the script with `sudo`
2. Check `/etc/hosts` contains the entries
3. Try flushing DNS cache:
   ```bash
   # macOS
   sudo dscacheutil -flushcache
   
   # Linux
   sudo systemctl restart systemd-resolved
   ```

### Port Conflicts
If you can't access services, ensure no other applications are using the same ports:
```bash
# Check what's using a port
lsof -i :8443
```

## Integration with STING Features

The custom domain setup integrates seamlessly with:

- **Kratos Authentication**: Cookies are properly scoped to the domain
- **WebAuthn/Passkeys**: RP ID can be set to match the domain
- **API CORS**: Configured to accept requests from all subdomains
- **Service Discovery**: Internal Docker networking remains unchanged

## Fun Facts

- **Queen's Hive**: Represents the central command center of STING
- **Bee Metaphor**: Consistent with STING's Worker Bees, Honey Jars, and Nectar Processing
- **Royal Access**: Admin users are like the "Queen Bee" with special privileges
- **Hive Mind**: The collective intelligence of all connected services

---

*"Welcome to the Queen's Hive, where your data is as sweet as honey and as secure as the royal chambers!"* 🐝👑