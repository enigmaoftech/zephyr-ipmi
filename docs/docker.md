# Docker Deployment Guide

Complete guide for deploying Zephyr IPMI using Docker. Zephyr IPMI uses a **single unified container** that contains both the frontend and backend services.

## Quick Start

### Production Deployment (Recommended)

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

### Local Development (Build from Source)

```bash
# Clone the repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup environment
bash deploy/docker-setup.sh

# Build and start container
docker compose up -d

# Access: https://localhost:8443
```

## Architecture

Zephyr IPMI uses a **single unified container** approach:

- **Frontend**: Built as static files using Vite/React
- **Backend**: FastAPI application that serves both API routes and static files
- **Single Container**: Everything runs in one Docker container
- **Port**: Single port 8443 (HTTPS)
  - Web UI: `https://localhost:8443`
  - API: `https://localhost:8443/api/*`

### Benefits

- ✅ Simpler deployment (one container vs two)
- ✅ Lower resource usage
- ✅ Easier to manage and update
- ✅ Fewer moving parts
- ✅ Simplified networking (no inter-container communication needed)

### How It Works

1. **Build Stage**: Frontend is built into static files (`frontend/dist`)
2. **Container**: Static files are copied to `/app/static` in the backend container
3. **FastAPI**: Serves static files from root (`/`) while API routes are at `/api/*`
4. **Routing**: FastAPI checks API routes first, then falls back to static files

## Configuration

### Environment Variables

The setup script creates a `.env` file with secure keys. You can customize it:

```bash
# Required: Strong secret keys (change in production!)
ZEPHYR_SECRET_KEY=<your-secret-key>
ZEPHYR_ENCRYPTION_KEY=<your-encryption-key>

# Optional: Database URL (default: SQLite)
ZEPHYR_DATABASE_URL=sqlite+aiosqlite:///./data/zephyr.db

# Optional: Use PostgreSQL instead
# ZEPHYR_DATABASE_URL=postgresql+psycopg://user:password@postgres:5432/zephyr
```

**⚠️ IMPORTANT**: Never commit `.env` to version control. It contains encryption keys!

### Port Configuration

Default port (can be changed in `docker-compose.yml`):

- **HTTPS**: 8443 (serves both web UI and API)
  - Web UI: `https://localhost:8443`
  - API: `https://localhost:8443/api/*`

### Volume Mounts

The Docker setup mounts:

- `./data/data` - Database and persistent data
- `./data/certs` - SSL certificates

These directories persist across container updates and restarts.

## Network Configuration

For IPMI to work, the container needs access to your server's BMC network.

### Default Configuration (Bridge Network)

By default, the container uses Docker's bridge network. Ensure your Docker host can reach BMC IPs on your network.

### Host Network (Recommended for IPMI)

For direct access to your BMC network, modify `docker-compose.yml`:

```yaml
services:
  zephyr-ipmi:
    network_mode: "host"
    # Remove ports section when using host network
```

**Pros**: Direct access to BMC network, simpler networking  
**Cons**: Less isolation, port conflicts possible

## Updating

### Update to Latest Version

```bash
# Pull latest image
docker compose -f docker-compose.prod.yml pull

# Restart container
docker compose -f docker-compose.prod.yml up -d
```

### Rebuild After Code Changes

```bash
docker compose up -d --build
```

## Docker on Raspberry Pi

```bash
# Install Docker on Raspberry Pi (if not already installed)
curl -fsSL https://get.docker.com | sh

# Clone repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup and start
bash deploy/docker-prod-setup.sh
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Management Commands

```bash
# Start services
docker compose -f docker-compose.prod.yml up -d

# Stop services
docker compose -f docker-compose.prod.yml down

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Check status
docker compose -f docker-compose.prod.yml ps

# Execute commands in container
docker compose -f docker-compose.prod.yml exec zephyr-ipmi bash
```
```

## Troubleshooting

### Self-Signed Certificate Warning
This is normal. Click "Advanced" → "Proceed" in your browser.

### Port Already in Use
Change port in `docker-compose.prod.yml`:
```yaml
ports:
  - "8444:8443"  # Change 8444 to any available port
```

### Can't Access Container

```bash
# Check container status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f

# Test API endpoint
curl -k https://localhost:8443/api/auth/status
```

### Container Won't Start

```bash
# Check logs for errors
docker compose -f docker-compose.prod.yml logs

# Verify SSL certificates exist
ls -la data/certs/

# Regenerate certificates if needed
bash deploy/docker-prod-setup.sh
```

### IPMI Not Working

- Ensure Docker host can reach BMC IPs on your network
- Check network mode (host vs bridge)
- Verify `ipmitool` is available in container: `docker compose exec zephyr-ipmi which ipmitool`

## Data Persistence

All data is stored in Docker volumes mounted from the host:
- **Database**: `./data/data/zephyr.db`
- **SSL Certificates**: `./data/certs/`

These directories persist across container updates and restarts. To backup:

```bash
# Backup database
cp data/data/zephyr.db zephyr-backup.db

# Backup certificates
tar -czf certs-backup.tar.gz data/certs/
```

## Advanced Configuration

### Custom Port

Edit `docker-compose.prod.yml`:
```yaml
ports:
  - "9443:8443"  # External:Internal
```

### PostgreSQL Database

1. Add PostgreSQL service to `docker-compose.prod.yml`
2. Update `ZEPHYR_DATABASE_URL` in `.env`
3. Restart container

### Custom SSL Certificates

Replace certificates in `data/certs/`:
- `zephyr-ipmi.crt` - SSL certificate
- `zephyr-ipmi.key` - Private key

Container will use your certificates instead of generating new ones.
