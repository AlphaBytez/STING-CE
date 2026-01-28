# Solutions for Handling NPM Package Changes in Docker

## The Problem
When you modify `package.json` locally (e.g., `npm install react-icons`), the Docker container rebuild process detects structural changes and requires either:
- A full reinstall: `./manage_sting.sh reinstall`
- A forced update: `./manage_sting.sh update --force`

## Solutions

### 1. **Quick Fix: Install Dependencies in Running Container**
```bash
# Access the running container
docker exec -it sting-ce-frontend sh

# Install the package inside the container
npm install react-icons

# Exit the container
exit
```

### 2. **Recommended: Run NPM Commands Through Docker**
```bash
# Run npm commands directly in the container
docker exec sting-ce-frontend npm install react-icons

# Or for multiple packages
docker exec sting-ce-frontend npm install react-icons axios lodash
```

### 3. **Development Mode: Use Volume-Mounted node_modules**
Since the frontend directory is volume-mounted, you can:
```bash
# Stop the frontend container
docker stop sting-ce-frontend

# Install packages locally
cd frontend
npm install react-icons

# Start the container with the local node_modules
docker start sting-ce-frontend
```

### 4. **Force Update (When Needed)**
If the container needs rebuilding:
```bash
# Force update to rebuild with new dependencies
./manage_sting.sh update frontend --force

# Or do a full reinstall (cleanest option)
./manage_sting.sh reinstall
```

### 5. **Hybrid Approach: Local Development**
For active development, run the frontend locally while keeping backend in Docker:
```bash
# Start all services except frontend
docker-compose up -d db vault app kratos

# Run frontend locally
cd frontend
npm install
npm start
```

## Best Practices

1. **For Single Package Additions**: Use `docker exec` method
2. **For Multiple Changes**: Do a force update or reinstall
3. **For Active Development**: Consider running frontend locally
4. **Always Commit**: Both `package.json` and `package-lock.json`

## Quick Commands Reference
```bash
# Add a package without rebuild
docker exec sting-ce-frontend npm install <package-name>

# Check installed packages
docker exec sting-ce-frontend npm list

# Update all dependencies
docker exec sting-ce-frontend npm update

# Clean install (if issues arise)
docker exec sting-ce-frontend rm -rf node_modules package-lock.json
docker exec sting-ce-frontend npm install
```

## Why This Happens
- Docker builds create isolated environments
- `npm ci` in Dockerfile uses `package-lock.json` for reproducible builds
- Volume mounts share code but not `node_modules` by default
- The manage script detects structural changes for safety