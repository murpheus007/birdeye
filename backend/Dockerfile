FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create and activate virtual environment
RUN python -m venv .venv && \
    .venv/bin/pip install --upgrade pip setuptools wheel && \
    .venv/bin/pip install -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD .venv/bin/python -c "import requests; requests.get('http://localhost:5000/health')"

# Run gunicorn (CMD can be overridden by docker-compose)
CMD [".venv/bin/gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app:app"]
