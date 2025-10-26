# Frontend Docker Setup

This frontend now supports two modes to ensure compatibility across all platforms:

## Production Mode (Recommended for Linux/WSL2)
Uses nginx to serve a production build of the React app. This avoids webpack/Create React App issues in Docker.

```bash
# Use the nginx-based frontend (default)
docker-compose -f docker-compose.yml -f docker-compose.frontend-nginx.yml up -d

# Or during installation
./manage_sting.sh install
```

### Benefits:
- ✅ Works reliably on Linux, WSL2, and macOS
- ✅ Fast performance with nginx
- ✅ No webpack/CRA Docker issues
- ✅ Production-optimized build

## Development Mode (For macOS with Hot Reload)
Uses the webpack dev server for hot module replacement during development.

```bash
# Use webpack dev server with hot reload
docker-compose -f docker-compose.yml -f docker-compose.frontend-nginx.yml -f docker-compose.dev-mac.yml up -d

# Or set environment variable
FRONTEND_MODE=dev docker-compose up -d
```

### Benefits:
- ✅ Hot reload for rapid development
- ✅ Source maps for debugging
- ✅ Immediate feedback on changes

## Switching Between Modes

### To use Production Mode (nginx):
```bash
docker-compose down frontend
docker-compose -f docker-compose.yml -f docker-compose.frontend-nginx.yml up -d frontend
```

### To use Development Mode (webpack):
```bash
docker-compose down frontend
docker-compose -f docker-compose.yml -f docker-compose.frontend-nginx.yml -f docker-compose.dev-mac.yml up -d frontend
```

## File Structure
- `Dockerfile.react-nginx` - Production build with nginx
- `Dockerfile.react-dev` - Development server with hot reload
- `nginx.prod.conf` - Nginx configuration for production
- `docker-compose.frontend-nginx.yml` - Nginx frontend service
- `docker-compose.dev-mac.yml` - Override for dev mode

## Troubleshooting

### Frontend not loading?
1. Check logs: `docker logs sting-ce-frontend`
2. Ensure ports are free: `lsof -i :8443`
3. Clear browser cache

### Changes not appearing?
- Production mode: Rebuild with `docker-compose build frontend`
- Dev mode: Check volume mounts are correct

### Certificate errors?
- Ensure certificates are mounted correctly
- Check certificate paths in environment variables