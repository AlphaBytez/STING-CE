# Database Separation Architecture

## Overview
STING CE uses a separated database architecture for improved security, scalability, and maintainability. Each service uses its own database or schema with dedicated database users.

## Database Structure

### 1. **kratos** Database
- **Purpose**: Authentication and identity management
- **User**: `kratos_user`
- **Service**: Ory Kratos
- **Tables**: 
  - identities
  - identity_credentials
  - identity_credential_types
  - identity_credential_identifiers
  - sessions
  - selfservice_* (login, registration, recovery flows)
  - courier_messages

### 2. **sting_app** Database
- **Purpose**: Core application data
- **User**: `app_user`
- **Services**: Flask app, report-worker
- **Tables**:
  - app_users (legacy, being phased out)
  - app_sessions
  - app_settings
  - passkeys (custom WebAuthn implementation)
  - user_settings
  - api_keys
  - compliance_profiles
  - report_templates
  - reports
  - audit_logs

### 3. **sting_messaging** Database
- **Purpose**: Message queue and notifications
- **User**: `app_user`
- **Service**: Messaging service
- **Tables**:
  - message_queue
  - notifications
  - message_history

## Security Benefits

### Principle of Least Privilege
- Each service only has access to its required database
- Database users have minimal necessary permissions
- No cross-database access between services

### Isolation
- Authentication data isolated from application data
- Compromise of one service doesn't expose all data
- Different backup and recovery strategies per database

## Connection Strings

### Kratos Service
```
DSN=postgresql://kratos_user:${KRATOS_DB_PASSWORD}@db:5432/kratos?sslmode=disable
```

### Application Services
```
DATABASE_URL=postgresql://app_user:${APP_DB_PASSWORD}@db:5432/sting_app?sslmode=disable
```

### Messaging Service
```
DATABASE_URL=postgresql://app_user:${APP_DB_PASSWORD}@db:5432/sting_messaging?sslmode=disable
```

## Migration from Shared Database

### For Existing Installations
If you have an existing installation using a shared database, you can migrate:

1. **Export Kratos data** from sting_app:
```bash
docker exec sting-ce-db pg_dump -U postgres -d sting_app \
  -t identities \
  -t identity_credentials \
  -t identity_credential_types \
  -t identity_credential_identifiers \
  -t identity_verifiable_addresses \
  -t identity_recovery_addresses \
  -t selfservice_* \
  -t courier_messages \
  -t sessions \
  > kratos_data_export.sql
```

2. **Import into kratos database**:
```bash
docker exec -i sting-ce-db psql -U postgres -d kratos < kratos_data_export.sql
```

3. **Update docker-compose.yml** with new connection strings

4. **Restart services**:
```bash
./manage_sting.sh restart kratos app
```

### For Fresh Installations
Fresh installations will automatically use the separated database architecture.

## Database Initialization Order

1. **01-init.sql** - Creates sting_app database and core tables
2. **02-database-users.sql** - Creates database users with proper permissions
3. **03-messaging-database.sql** - Creates messaging database
4. **kratos.sql** - Creates kratos database
5. **chatbot_memory.sql** - Creates chatbot memory tables

## Environment Variables

### Required for Production
```bash
# Database passwords (change from defaults!)
KRATOS_DB_PASSWORD=secure_password_here
APP_DB_PASSWORD=secure_password_here

# Database hosts (if not using Docker networking)
KRATOS_DB_HOST=db
APP_DB_HOST=db
MESSAGING_DB_HOST=db
```

## Backup Strategy

### Individual Database Backups
```bash
# Backup Kratos database
docker exec sting-ce-db pg_dump -U postgres -d kratos > kratos_backup.sql

# Backup application database
docker exec sting-ce-db pg_dump -U postgres -d sting_app > sting_app_backup.sql

# Backup messaging database
docker exec sting-ce-db pg_dump -U postgres -d sting_messaging > sting_messaging_backup.sql
```

### Restore from Backup
```bash
# Restore Kratos database
docker exec -i sting-ce-db psql -U postgres -d kratos < kratos_backup.sql

# Restore application database
docker exec -i sting-ce-db psql -U postgres -d sting_app < sting_app_backup.sql

# Restore messaging database
docker exec -i sting-ce-db psql -U postgres -d sting_messaging < sting_messaging_backup.sql
```

## Performance Considerations

### Connection Pooling
- Each database has its own connection pool
- Kratos: 50 max connections
- App: 100 max connections
- Messaging: 50 max connections

### Scaling Options
With separated databases, you can:
- Put databases on different servers
- Use read replicas for specific databases
- Apply different performance tuning per database
- Use different PostgreSQL versions if needed

## Troubleshooting

### Common Issues

1. **Permission Denied Errors**
   - Ensure database users are created before services start
   - Check that permissions are granted correctly

2. **Connection Refused**
   - Verify database is running: `docker ps | grep db`
   - Check connection strings in docker-compose.yml

3. **Migration Issues**
   - Ensure all Kratos tables are properly exported
   - Check for foreign key constraints

### Health Checks
```bash
# Check database connections
docker exec sting-ce-db psql -U kratos_user -d kratos -c "SELECT 1;"
docker exec sting-ce-db psql -U app_user -d sting_app -c "SELECT 1;"
docker exec sting-ce-db psql -U app_user -d sting_messaging -c "SELECT 1;"
```

## Future Improvements

- [ ] Implement database connection encryption
- [ ] Add automatic password rotation
- [ ] Implement database-level audit logging
- [ ] Add support for external database servers
- [ ] Implement automatic backup scheduling