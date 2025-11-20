# Multi-stage build for unified Zephyr IPMI container
# This builds both frontend and backend into a single container

# Stage 1: Build frontend
FROM node:18-alpine as frontend-builder

WORKDIR /app

# Copy package files
COPY frontend/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build production frontend
RUN npm run build

# Stage 2: Build backend dependencies
FROM python:3.11-slim as backend-builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copy dependency files
COPY backend/pyproject.toml backend/poetry.lock* ./

# Configure Poetry to not create virtual environment (we're in Docker)
RUN poetry config virtualenvs.create false

# Install dependencies (only production, excluding dev, skip project install)
RUN poetry install --without dev --no-root --no-interaction --no-ansi || poetry install --no-root --no-interaction --no-ansi

# Stage 3: Production container
FROM python:3.11-slim

# Install runtime dependencies (ipmitool is needed for IPMI commands)
RUN apt-get update && apt-get install -y \
    ipmitool \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r zephyr && useradd -r -g zephyr zephyr

# Create app directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin

# Copy backend application code
COPY backend/app/ ./app/
COPY backend/scripts/ ./scripts/

# Copy frontend static files from builder
COPY --from=frontend-builder /app/dist ./static

# Create entrypoint script inline
RUN echo '#!/bin/bash\n\
set -e\n\
cd /app\n\
# Generate certs if they dont exist and SSL is enabled\n\
if [ "${ZEPHYR_SSL_ENABLED:-false}" = "true" ] && [ ! -f "certs/zephyr-ipmi.crt" ]; then\n\
    echo "📜 Generating SSL certificates..."\n\
    bash scripts/generate_ssl_cert.sh\n\
fi\n\
# Start server using the startup script\n\
export ZEPHYR_SSL_ENABLED=${ZEPHYR_SSL_ENABLED:-true}\n\
exec bash scripts/start_server.sh\n\
' > /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Create necessary directories and set permissions
RUN mkdir -p certs data static && \
    chown -R zephyr:zephyr /app

# Make scripts executable
RUN chmod +x scripts/*.sh scripts/*.py

# Set working directory
WORKDIR /app

# Expose port
EXPOSE 8443

# Switch to non-root user
USER zephyr

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f -k https://localhost:8443/api/auth/status || exit 1

# Start command
ENTRYPOINT ["/app/docker-entrypoint.sh"]

