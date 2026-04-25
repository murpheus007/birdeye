FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create and activate virtual environment
RUN python -m venv .venv && \
    .venv/bin/pip install --upgrade pip setuptools wheel && \
    .venv/bin/pip install -r requirements.txt

# Copy application code
COPY . .

# Run bot
CMD [".venv/bin/python", "bot.py"]
