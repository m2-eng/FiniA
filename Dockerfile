# Multi-stage build for FiniA
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code and version metadata
# cfg/ is NOT copied - it's mounted as a volume at runtime (see docker-compose.yml)
# This prevents overwriting config and allows live updates
COPY VERSION ./VERSION
COPY src/ ./src/
COPY db/migrations ./db/migrations/

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose the API port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/docs').getcode() == 200" || exit 1

# Default command: start the API server
CMD ["python3", "src/main.py"]
