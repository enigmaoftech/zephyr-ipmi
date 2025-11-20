#!/bin/bash
# Production Docker setup script for Zephyr IPMI
# Single container deployment from GitHub Container Registry

set -e

echo "🚀 Zephyr IPMI Production Docker Setup (Single Container)"
echo ""

# Repository is hardcoded for public repo
GITHUB_REPO=enigmaoftech/zephyr-ipmi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p data/certs
mkdir -p data/data
echo "✅ Directories created"
echo ""

# Generate SSL certificates if they don't exist
echo "🔒 Checking SSL certificates..."

if [ ! -f "data/certs/zephyr-ipmi.crt" ] || [ ! -f "data/certs/zephyr-ipmi.key" ]; then
    echo "   Generating SSL certificates..."
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout data/certs/zephyr-ipmi.key \
        -out data/certs/zephyr-ipmi.crt \
        -subj "/C=US/ST=State/L=City/O=Zephyr/CN=localhost"
    echo "   ✅ Certificates generated"
else
    echo "   ✅ Certificates already exist"
fi
echo ""

# Check for .env file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Security Keys (generate with: openssl rand -hex 32)
ZEPHYR_SECRET_KEY=$(openssl rand -hex 32)
ZEPHYR_ENCRYPTION_KEY=$(openssl rand -hex 32)
EOF
    echo "   ✅ .env file created with generated keys"
    echo "   ⚠️  IMPORTANT: Review and change keys in .env for production use!"
else
    echo "   ✅ .env file already exists"
fi
echo ""

# Login to GitHub Container Registry if needed
if [ -n "$GITHUB_TOKEN" ]; then
    echo "🔐 Logging in to GitHub Container Registry..."
    echo "$GITHUB_TOKEN" | docker login ghcr.io -u "$GITHUB_USER" --password-stdin
    echo "   ✅ Logged in to GitHub Container Registry"
    echo ""
fi

echo "✅ Production Docker environment setup complete!"
echo ""
echo "Next steps:"
echo "  1. Review .env file and change keys for production use"
echo "  2. Pull and start container:"
echo "     docker compose -f docker-compose.prod.yml pull"
echo "     docker compose -f docker-compose.prod.yml up -d"
echo ""
echo "To view logs:"
echo "  docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "Access:"
echo "  Web UI & API: https://localhost:8443"
echo ""
