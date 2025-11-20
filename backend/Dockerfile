# Multi-stage build for Zephyr IPMI Backend
FROM python:3.11-slim as builder

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
COPY pyproject.toml poetry.lock* ./

# Configure Poetry to not create virtual environment (we're in Docker)
RUN poetry config virtualenvs.create false

# Install dependencies (only production, excluding dev, skip project install)
RUN poetry install --without dev --no-root --no-interaction --no-ansi || poetry install --no-root --no-interaction --no-ansi

# Production stage
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
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY app/ ./app/
COPY scripts/ ./scripts/

# Create entrypoint script inline
RUN echo '#!/bin/bash\n\
set -e\n\
cd /app\n\
# Generate certs if they dont exist and SSL is enabled\n\
if [ "${ZEPHYR_SSL_ENABLED:-false}" = "true" ] && [ ! -f "certs/zephyr-ipmi.crt" ]; then\n\
    echo "📜 Generating backend SSL certificates..."\n\
    bash scripts/generate_ssl_cert.sh\n\
fi\n\
# Start server using the startup script\n\
export ZEPHYR_SSL_ENABLED=${ZEPHYR_SSL_ENABLED:-true}\n\
exec bash scripts/start_server.sh\n\
' > /app/docker-entrypoint.sh && chmod +x /app/docker-entrypoint.sh

# Create necessary directories and set permissions
RUN mkdir -p certs data && \
    chown -R zephyr:zephyr /app

# Make scripts executable
RUN chmod +x scripts/*.sh scripts/*.py

# Set working directory
WORKDIR /app

# Expose ports
EXPOSE 8443 8000

# Switch to non-root user
USER zephyr

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f -k https://localhost:8443/api/auth/status || exit 1

# Start command
ENTRYPOINT ["/app/docker-entrypoint.sh"]

