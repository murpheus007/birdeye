# Birdeye Radar - Solana Trading Dashboard

A comprehensive multi-container trading dashboard for Solana blockchain analysis with real-time price feeds, Discord bot notifications, and a modern web interface.

## 🚀 Overview

Birdeye Radar is an open-source platform designed for Solana traders to monitor market activity, track token performance, and receive real-time alerts via Discord. It integrates data from the Birdeye API and provides a seamless experience across web and social channels.

### Key Features
- **Real-time Monitoring:** Track Solana tokens with live price updates and volume analysis.
- **Discord Integration:** Set price alerts and receive notifications directly in your Discord server or DMs.
- **Cache-First Architecture:** Optimized for performance and reduced API costs using Redis caching.
- **Dockerized Environment:** Easy local setup and deployment using Docker Compose.
- **Modern Tech Stack:** Built with React, Vite, Flask, PostgreSQL, and Redis.

---

## 🛠️ Tech Stack

- **Frontend:** React, Vite, TypeScript, Tailwind CSS, Zustand, Recharts
- **Backend:** Flask, Gunicorn, SQLAlchemy (PostgreSQL), Alembic (Migrations)
- **Discord Bot:** discord.py
- **Infrastructure:** Docker, Docker Compose, Nginx, Redis

---

## 📁 Project Structure

```text
birdeyeradar/
├── backend/            # Flask REST API
│   ├── routes/         # API endpoints
│   ├── models/         # SQLAlchemy ORM models
│   ├── services/       # Business logic (Solana RPC, Birdeye API)
│   └── alembic/        # Database migrations
├── frontend/           # React + Vite web application
│   ├── src/
│   │   ├── components/ # Reusable UI components
│   │   ├── pages/      # View components
│   │   ├── stores/     # Zustand state management
│   │   └── services/   # API client services
├── discord-bot/        # Discord.py bot implementation
│   ├── cogs/           # Modular bot commands
│   └── services/       # Bot-specific business logic
├── db-init/            # SQL scripts for database initialization
├── .nginx/             # Nginx reverse proxy configuration
└── docker-compose.yml  # Container orchestration
```

---

## 🚀 Quick Start

### Prerequisites
- [Docker](https://www.docker.com/get-started) & Docker Compose
- Git

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/birdeyeradar.git
   cd birdeyeradar
   ```

2. **Setup Environment Variables:**
   Copy the example environment file and fill in your keys:
   ```bash
   cp .env.example .env
   ```
   *Required keys:* `BIRDEYE_API_KEY`, `DISCORD_TOKEN`, `SOLANA_RPC_URL`.

3. **Start the application:**
   ```bash
   # Start all services in the background
   docker compose up -d
   ```

4. **Verify services are running:**
   ```bash
   docker compose ps
   ```

5. **Access the application:**
   - **Web Interface:** [http://localhost:3000](http://localhost:3000)
   - **Backend API:** [http://localhost:5000/api/v1/health](http://localhost:5000/api/v1/health)

---

## 🔧 Development

### Useful Commands (Makefile)
The project includes a `Makefile` for common tasks:
- `make up`: Start all services
- `make down`: Stop all services
- `make build`: Rebuild images
- `make logs`: View logs from all services
- `make db-shell`: Access PostgreSQL shell
- `make test`: Run backend and frontend tests

### Local Development Mode
For a development environment with hot-reloading:
```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## 📡 API Endpoints


### Backend Tests
```bash
docker exec birdeye-backend /app/.venv/bin/pytest
docker exec birdeye-backend /app/.venv/bin/pytest --cov
```

### Frontend Tests
```bash
docker exec birdeye-frontend npm run test
```

## 🛑 Stopping and Cleanup

### Stop Services
```bash
# Keep volumes (data persists)
docker-compose down

# Remove volumes (destroy data)
docker-compose down -v
```

### Clean Everything
```bash
docker-compose down -v --rmi all
```

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Solana RPC API](https://docs.solana.com/api/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [React Documentation](https://react.dev/)
- [discord.py Documentation](https://discordpy.readthedocs.io/)

## 🤝 Contributing

1. Create feature branch: `git checkout -b feature/MyFeature`
2. Commit changes: `git commit -m 'Add MyFeature'`
3. Push to branch: `git push origin feature/MyFeature`
4. Open Pull Request

---

**Last Updated:** 2026-04-25
**Version:** 1.0.0
