# GitHub Container Registry Deployment

This guide explains how to deploy Zephyr IPMI using pre-built Docker images from GitHub Container Registry (ghcr.io).

Zephyr IPMI uses a single unified container that contains both the frontend and backend services. Images are automatically built and published by GitHub Actions whenever code is pushed to the repository.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup environment
bash deploy/docker-prod-setup.sh

# Pull and start container
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Access: https://localhost:8443
```

## How It Works

Images are automatically built and published to GitHub Container Registry by GitHub Actions whenever code is pushed to the repository.

- **Repository**: [enigmaoftech/zephyr-ipmi](https://github.com/enigmaoftech/zephyr-ipmi)
- **Image Location**: `ghcr.io/enigmaoftech/zephyr-ipmi:latest`
- **Builds**: Automatic via GitHub Actions on every push

## Image Tags

Images are automatically tagged with:
- `latest` - Latest build from main branch
- `main` - Latest build from main branch
- `v1.0.0` - Semantic version tags (for releases)
- `main-abc1234` - Branch name + commit SHA

## Updating to Latest Version

```bash
# Pull latest image
docker compose -f docker-compose.prod.yml pull

# Restart container
docker compose -f docker-compose.prod.yml up -d
```

## Production Deployment

### Step 1: Clone Repository

```bash
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi
```

### Step 2: Setup Environment

```bash
# Run setup script (creates directories, generates SSL certs, creates .env)
bash deploy/docker-prod-setup.sh
```

The setup script will:
- Create necessary directories (`data/certs`, `data/data`)
- Generate SSL certificates if they don't exist
- Create `.env` file with secure random keys

### Step 3: Configure (Optional)

Edit `.env` if you want to customize:
- `ZEPHYR_SECRET_KEY` - Secret key for session signing
- `ZEPHYR_ENCRYPTION_KEY` - Encryption key for sensitive data

**Important**: Change the default keys in production!

### Step 4: Start Container

```bash
# Pull latest image
docker compose -f docker-compose.prod.yml pull

# Start container
docker compose -f docker-compose.prod.yml up -d
```

### Step 5: Access

Open your browser to: **https://localhost:8443**

You'll see a security warning for the self-signed certificate - this is normal. Click "Advanced" → "Proceed" to continue.

## Docker on Raspberry Pi

```bash
# Install Docker (if not already installed)
curl -fsSL https://get.docker.com | sh

# Clone repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup and start
bash deploy/docker-prod-setup.sh
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### "manifest unknown"

The images haven't been built yet. Check:
1. GitHub Actions workflow ran successfully (check the Actions tab)
2. Images are available in GitHub Container Registry

### "unauthorized: authentication required"

This shouldn't happen for a public repository. If it does:
1. Make sure the repository is public
2. Try logging out: `docker logout ghcr.io`
3. Try pulling again: `docker compose -f docker-compose.prod.yml pull`

### Can't Access Container

```bash
# Check container status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Test API endpoint
curl -k https://localhost:8443/api/auth/status
```

## Data Persistence

All data is stored in Docker volumes mounted from the host:
- **Database**: `./data/data/zephyr.db`
- **SSL Certificates**: `./data/certs/`

These directories persist across container updates and restarts.

## Security Notes

- **Change default keys** in `.env` for production use
- **Use strong, randomly generated keys**: `openssl rand -hex 32`
- Consider using Docker secrets or environment variable management tools for production
- The `.env` file contains sensitive keys - never commit it to version control

## Next Steps

- Configure reverse proxy (Nginx, Traefik) for domain access
- Set up monitoring and logging
- Configure backups for the database
- Review [security documentation](./security.md) for security best practices
