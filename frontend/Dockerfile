# Multi-stage build for Zephyr IPMI Frontend
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build production frontend
RUN npm run build

# Production stage with Nginx
FROM nginx:alpine

# Install openssl for certificate generation (optional)
RUN apk add --no-cache openssl

# Copy built frontend from builder
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create cert directory
RUN mkdir -p /app/certs

# Create entrypoint script to generate certs if needed
RUN echo '#!/bin/sh' > /docker-entrypoint.sh && \
    echo 'set -e' >> /docker-entrypoint.sh && \
    echo '# Generate certs if they dont exist' >> /docker-entrypoint.sh && \
    echo 'if [ ! -f "/app/certs/zephyr-frontend.crt" ] || [ ! -f "/app/certs/zephyr-frontend.key" ]; then' >> /docker-entrypoint.sh && \
    echo '    echo "Generating frontend SSL certificates..."' >> /docker-entrypoint.sh && \
    echo '    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \' >> /docker-entrypoint.sh && \
    echo '        -keyout /app/certs/zephyr-frontend.key \' >> /docker-entrypoint.sh && \
    echo '        -out /app/certs/zephyr-frontend.crt \' >> /docker-entrypoint.sh && \
    echo '        -subj "/C=US/ST=State/L=City/O=Zephyr/CN=localhost"' >> /docker-entrypoint.sh && \
    echo 'fi' >> /docker-entrypoint.sh && \
    echo 'exec nginx -g "daemon off;"' >> /docker-entrypoint.sh && \
    chmod +x /docker-entrypoint.sh

# Expose ports
EXPOSE 80 443

# Start Nginx via entrypoint
ENTRYPOINT ["/docker-entrypoint.sh"]

