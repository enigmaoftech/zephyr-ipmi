#!/bin/bash
# Setup script for Docker deployment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "🐳 Setting up Zephyr IPMI Docker environment..."

cd "${PROJECT_DIR}"

# Create necessary directories
mkdir -p backend/data backend/certs frontend/certs

# Generate SSL certificates if they don't exist
if [ ! -f "backend/certs/zephyr-ipmi.crt" ] || [ ! -f "backend/certs/zephyr-ipmi.key" ]; then
    echo "📜 Generating backend SSL certificates..."
    cd backend
    bash scripts/generate_ssl_cert.sh
    cd ..
fi

if [ ! -f "frontend/certs/zephyr-frontend.crt" ] || [ ! -f "frontend/certs/zephyr-frontend.key" ]; then
    echo "📜 Generating frontend SSL certificates..."
    cd frontend
    bash scripts/generate_ssl_cert.sh
    cd ..
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "🔐 Creating .env file with secure keys..."
    cat > .env << EOF
# Secret key for session signing (generate a strong random string)
ZEPHYR_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || openssl rand -base64 32)

# Encryption key for sensitive data (generate a Fernet key)
ZEPHYR_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || openssl rand -base64 32)
EOF
    echo "✅ Created .env file"
    echo "⚠️  IMPORTANT: Review and secure .env file - it contains encryption keys!"
fi

echo ""
echo "✅ Docker environment setup complete!"
echo ""
echo "To start the services:"
echo "  docker-compose up -d"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop:"
echo "  docker-compose down"

