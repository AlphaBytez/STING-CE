# STING CE Developer Preview - Quick Start

## 🚀 Get Started in 5 Minutes

### Prerequisites Check

```bash
# Check Docker
docker --version
# Should be 20.10+

# Check Docker Compose
docker compose version
# Should be 2.0+

# Check Python (optional, for local dev)
python --version
# Should be 3.9+
```

### Quick Start Commands

```bash
# 1. Navigate to the directory
cd /mnt/c/DevWorld/STING-CE/sting-ce-dev-preview

# 2. Review configuration (optional)
cat conf/env/app.env

# 3. Build services (first time only)
./manage_sting_dev.sh build

# 4. Start all services
./manage_sting_dev.sh start

# 5. Check status
./manage_sting_dev.sh status

# 6. View logs
./manage_sting_dev.sh logs
```

## 📦 What's Included

### Core Services
- ✅ Backend API (Port 5050)
- ✅ PostgreSQL Database (Port 5433)
- ✅ Ory Kratos Auth (Ports 4433, 4434)
- ✅ Knowledge Service (Port 8090)
- ✅ Chroma Vector DB (Port 8000)
- ✅ Chatbot Service (Port 8888)
- ✅ External AI Service (Port 8091)
- ✅ Messaging Service (Port 8889)
- ✅ Redis Cache (Port 6379)

### Optional Services
- 🔧 Mailpit (Port 8025) - Development email testing
- 📊 Grafana (Future) - Monitoring dashboard
- 📝 Loki (Future) - Log aggregation

## 🛠️ Management Commands

```bash
# Start services
./manage_sting_dev.sh start

# Stop services
./manage_sting_dev.sh stop

# Restart all services
./manage_sting_dev.sh restart

# Restart specific service
./manage_sting_dev.sh restart app

# Check status
./manage_sting_dev.sh status

# View logs (all services)
./manage_sting_dev.sh logs

# View logs (specific service)
./manage_sting_dev.sh logs app

# Rebuild service
./manage_sting_dev.sh update app

# Build all services
./manage_sting_dev.sh build
```

## 🧪 Testing Services

### Backend API
```bash
curl http://localhost:5050/health
# Should return: {"status": "healthy"}
```

### Knowledge Service
```bash
curl http://localhost:8090/health
# Should return: {"status": "healthy"}
```

### Chatbot Service
```bash
curl http://localhost:8888/health
# Should return: {"status": "healthy"}
```

### External AI Service
```bash
curl http://localhost:8091/health
# Should return: {"status": "healthy"}
```

### Chroma Vector DB
```bash
curl http://localhost:8000/api/v1/heartbeat
# Should return: heartbeat timestamp
```

### PostgreSQL
```bash
docker exec -it sting-ce-dev-db psql -U postgres -d sting_app -c "SELECT version();"
```

### Redis
```bash
docker exec -it sting-ce-dev-redis redis-cli ping
# Should return: PONG
```

## 📝 Common Tasks

### View Service Logs
```bash
# All services
docker compose -f docker-compose.dev.yml logs -f

# Specific service
docker compose -f docker-compose.dev.yml logs -f app
```

### Access Database
```bash
# PostgreSQL
docker exec -it sting-ce-dev-db psql -U postgres -d sting_app

# Common queries
\dt                           # List tables
\d users                      # Describe users table
SELECT * FROM users LIMIT 5;  # Query users
```

### Execute Command in Container
```bash
# Backend app
docker exec -it sting-ce-dev-app bash

# Database
docker exec -it sting-ce-dev-db bash
```

### Clear All Data (Reset)
```bash
# Stop services
./manage_sting_dev.sh stop

# Remove volumes
docker compose -f docker-compose.dev.yml down -v

# Restart
./manage_sting_dev.sh start
```

## 🐛 Troubleshooting

### Services Won't Start

1. **Check if ports are already in use:**
   ```bash
   netstat -tuln | grep -E '5050|5433|4433|8090|8000'
   ```

2. **Check Docker resources:**
   ```bash
   docker system df
   docker system prune  # If low on space
   ```

3. **View specific service logs:**
   ```bash
   ./manage_sting_dev.sh logs <service-name>
   ```

### Database Connection Issues

```bash
# Check if DB is running
docker ps | grep sting-ce-dev-db

# Check DB logs
docker logs sting-ce-dev-db

# Test connection
docker exec -it sting-ce-dev-db pg_isready -U postgres
```

### Service Health Check Failing

```bash
# Check container status
docker ps -a | grep sting-ce-dev

# Inspect specific service
docker inspect sting-ce-dev-app

# Check logs for errors
docker logs sting-ce-dev-app --tail 100
```

### Port Conflicts

Edit `docker-compose.dev.yml` and change the host port:

```yaml
ports:
  - "5051:5050"  # Changed from 5050:5050
```

Then restart:
```bash
./manage_sting_dev.sh restart
```

## 📚 Next Steps

1. **Read the Documentation**
   - [Developer Preview Guide](docs/guides/DEVELOPER_PREVIEW_GUIDE.md)
   - [API Overview](docs/api/API_OVERVIEW.md)
   - [Features](docs/features/FEATURES.md)

2. **Explore the Services**
   - Try the API endpoints
   - Upload a document to Honey Jar
   - Chat with Bee assistant
   - Create a Nectar Bot API key

3. **Start Developing**
   - Read [CONTRIBUTING.md](CONTRIBUTING.md)
   - Set up your development environment
   - Pick an issue to work on
   - Submit your first PR!

## 🆘 Getting Help

- **Documentation**: Check `docs/` directory
- **Issues**: Open an issue on GitHub
- **Logs**: Check service logs for errors
- **Community**: Join our Discord/Slack

## 🎯 Key URLs

Once services are running:

- Backend API: http://localhost:5050
- Knowledge Service: http://localhost:8090
- Chatbot: http://localhost:8888
- External AI: http://localhost:8091
- Messaging: http://localhost:8889
- Kratos Public: http://localhost:4433
- Kratos Admin: http://localhost:4434
- PostgreSQL: localhost:5433
- Redis: localhost:6379
- Chroma: http://localhost:8000

## ⚡ Pro Tips

1. **Use Docker Compose directly for advanced operations:**
   ```bash
   docker compose -f docker-compose.dev.yml ps
   docker compose -f docker-compose.dev.yml exec app bash
   ```

2. **Monitor resource usage:**
   ```bash
   docker stats
   ```

3. **View all container IPs:**
   ```bash
   docker network inspect sting-ce-dev-preview_sting_local
   ```

4. **Backup database:**
   ```bash
   docker exec sting-ce-dev-db pg_dump -U postgres sting_app > backup.sql
   ```

5. **Restore database:**
   ```bash
   docker exec -i sting-ce-dev-db psql -U postgres sting_app < backup.sql
   ```

Happy coding! 🚀
