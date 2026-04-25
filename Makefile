.PHONY: help up down restart logs build clean ps test

COMPOSE := $(shell if docker compose version >/dev/null 2>&1; then echo "docker compose"; elif command -v docker-compose >/dev/null 2>&1; then echo "docker-compose"; else echo "docker compose"; fi)

help:
	@echo "Birdeye Trading Dashboard - Available Commands"
	@echo ""
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make restart         - Restart all services"
	@echo "  make logs            - View logs from all services"
	@echo "  make build           - Build all Docker images"
	@echo "  make ps              - Show running services"
	@echo "  make clean           - Stop services and remove volumes"
	@echo "  make test            - Run tests"
	@echo "  make backend-logs    - Show backend logs"
	@echo "  make frontend-logs   - Show frontend logs"
	@echo "  make db-logs         - Show database logs"
	@echo "  make redis-logs      - Show Redis logs"
	@echo "  make bot-logs        - Show Discord bot logs"
	@echo "  make db-shell        - Access PostgreSQL shell"
	@echo "  make redis-shell     - Access Redis CLI"
	@echo "  make backend-shell   - Access backend container"

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f

build:
	$(COMPOSE) build

ps:
	$(COMPOSE) ps

clean:
	$(COMPOSE) down -v

test:
	$(COMPOSE) exec backend /app/.venv/bin/pytest
	$(COMPOSE) exec frontend npm test

backend-logs:
	$(COMPOSE) logs -f backend

frontend-logs:
	$(COMPOSE) logs -f frontend

db-logs:
	$(COMPOSE) logs -f postgres

redis-logs:
	$(COMPOSE) logs -f redis

bot-logs:
	$(COMPOSE) logs -f discord-bot

db-shell:
	docker exec -it birdeye-postgres psql -U birdeye -d birdeye_db

redis-shell:
	docker exec -it birdeye-redis redis-cli

backend-shell:
	docker exec -it birdeye-backend /bin/sh

format-backend:
	docker exec birdeye-backend /app/.venv/bin/black .
	docker exec birdeye-backend /app/.venv/bin/isort .

lint-backend:
	docker exec birdeye-backend /app/.venv/bin/flake8 .

migrate-db:
	docker exec birdeye-backend /app/.venv/bin/alembic -c alembic.ini upgrade head
