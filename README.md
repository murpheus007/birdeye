# Birdeye Radar: Advanced Solana Intelligence & Monitoring Platform

[![System Architecture](https://img.shields.io/badge/Architecture-Distributed-blue.svg)](#system-architecture)
[![Tech Stack](https://img.shields.io/badge/Stack-Flask%20%7C%20React%20%7C%20Redis%20%7C%20Postgres-green.svg)](#tech-stack)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Birdeye Radar is a high-performance, distributed monitoring platform engineered for professional Solana traders. It bridges the gap between raw on-chain data and actionable intelligence by providing a low-latency pipeline for market activity, whale tracking, and automated real-time alerting.

---

## 🎯 Utility: Solving the 'Alpha' Gap
In the high-velocity Solana ecosystem, the bottleneck isn't data availability—it's **data latency and relevance**. Birdeye Radar solves this by:
- **Aggregating** multi-dimensional token data (Price, Volume, Market Cap) via Birdeye API.
- **Throttling & Caching** requests to optimize Compute Unit (CU) consumption without sacrificing signal accuracy.
- **Synchronizing** web-based analytics with social-based notifications (Discord) to ensure traders never miss a liquidity event.

---

## 🏗️ System Architecture

Birdeye Radar is architected as a decoupled, multi-container system to ensure scalability, fault isolation, and ease of deployment.

### High-Level Architecture Diagram
```mermaid
graph TD
    Client((Web/Discord)) <--> Nginx[Nginx Reverse Proxy]
    Nginx <--> Frontend[React/Vite SPA]
    Nginx <--> Backend[Flask API]
    Backend <--> Postgres[(PostgreSQL)]
    Backend <--> Redis[Redis Event Bus & Cache]
    Redis <--> Bot[Discord.py Bot]
    Backend -- RPC -- Birdeye((Birdeye API))
```

### Infrastructure Components
- **Nginx (Reverse Proxy):** Handles SSL termination, static asset serving, and request routing to the internal microservices.
- **Docker (Orchestration):** Standardized environment isolation ensures "Write Once, Run Anywhere" consistency from local dev to production VPS.
- **Redis (Pub/Sub & Cache):** Acts as both a high-speed cache for Birdeye API responses and a **real-time message broker** (Pub/Sub) to synchronize alert states between the Flask API and the Discord Bot.
- **PostgreSQL (Persistence):** Robust, relational storage for user configurations, alert rules, and historical tracking data using multi-schema organization (`trading` & `bot`).

---

## 🛠️ Technical Depth & Engineering Excellence

### 1. Schema Evolution with Alembic
We utilize **Alembic** for rigorous database version control. This ensures that schema changes (migrations) are reproducible across all environments, eliminating "it works on my machine" issues and enabling seamless production rollouts.

### 2. Real-Time Event Loop (Flask ↔ Discord)
The platform implements a sophisticated **Redis Pub/Sub architecture** for cross-process communication:
- **Flask** publishes rule changes or detected events to specialized Redis channels.
- **Discord Bot** runs an asynchronous event loop, subscribing to these channels for immediate user notification without the overhead of polling.

### 3. Cache-First Resource Management
To maximize API efficiency, we've implemented an intelligent caching layer:
- **Namespaced TTLs:** Different data types (Price vs. Metadata) have adaptive Time-To-Live (TTL) values.
- **Graceful Degradation:** The system is resilient; if Redis becomes unavailable, the pipeline falls back to direct API fetching, maintaining service uptime.

### 4. Hardened Security
- **Environment Isolation:** Sensitive credentials (API keys, Discord tokens) are managed strictly via environment variables, never committed to source.
- **CORS Protection:** Fine-grained Cross-Origin Resource Sharing policies protect the API from unauthorized frontend access.

---

## 🚀 Quick Start

Ensure you have [Docker](https://www.docker.com/get-started) installed.

### 1. Setup Environment
```bash
git clone https://github.com/your-username/birdeyeradar.git
cd birdeyeradar
cp .env.example .env
```
*Edit `.env` to include your `BIRDEYE_API_KEY`, `DISCORD_TOKEN`, and `SOLANA_RPC_URL`.*

### 2. Launch Platform
```bash
docker compose up -d
```
The platform will automatically initialize the database, run migrations, and start the proxy.

### 3. Access Points
- **Frontend:** [http://localhost:3000](http://localhost:3000)
- **Backend API:** [http://localhost:5000/api/v1/health](http://localhost:5000/api/v1/health)

---

## 📁 Project Structure

```text
birdeyeradar/
├── backend/            # Flask REST API + Gunicorn
│   ├── routes/         # Blueprinted API Endpoints
│   ├── models/         # SQLAlchemy ORM (Postgres)
│   ├── services/       # Core Logic (Redis, Birdeye, Solana)
│   └── alembic/        # Database Migrations
├── frontend/           # React + Vite (TypeScript)
│   ├── src/stores/     # Zustand State Management
│   └── src/services/   # Axios Client + Interceptors
├── discord-bot/        # Discord.py Implementation
│   ├── cogs/           # Modular Command Extensions
│   └── services/       # Async Pub/Sub Listeners
├── .nginx/             # Reverse Proxy Configuration
└── docker-compose.yml  # Distributed Service Orchestration
```

---

## 🤝 Contributing
Engineering leads interested in contributing to the Radar pipeline should follow the standard PR workflow. Ensure all changes are validated against the internal test suite:
- **Backend:** `make test-backend`
- **Frontend:** `make test-frontend`

---

## 📄 License
This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

**Last Updated:** April 2026 | **Version:** 1.0.0
