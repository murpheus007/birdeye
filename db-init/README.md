# Solana Trading Dashboard - Local Development

When initializing the database schema for PostgreSQL, use:
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
```

## Useful Commands

### Docker Management
```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs -f [service-name]

# Rebuild images
docker-compose build --no-cache

# Remove volumes (destructive)
docker-compose down -v
```

### Database
```bash
# Access PostgreSQL
docker exec -it birdeye-postgres psql -U birdeye -d birdeye_db

# Run migrations
docker exec birdeye-backend /app/.venv/bin/flask db upgrade

# Reset database (destructive)
docker volume rm birdeye_postgres_data
```

### Redis
```bash
# Access Redis CLI
docker exec -it birdeye-redis redis-cli

# Check Redis connection
docker exec birdeye-redis redis-cli ping
```

### Troubleshooting
```bash
# Check service health
docker-compose ps

# Inspect service logs
docker-compose logs --tail=50 [service-name]

# Rebuild a specific service
docker-compose build --no-cache [service-name]
```
