#!/usr/bin/env bash
# deploy.sh – One-command VPS update for Birdeye Radar
# Usage: bash deploy.sh
set -euo pipefail

echo "🔻 Stopping containers..."
docker compose down

echo "⬇️  Pulling latest code..."
git pull

echo "🏗️  Rebuilding and starting containers..."
docker compose up -d --build

echo "✅ Deployment complete."
