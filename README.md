# Zephyr IPMI

Zephyr IPMI is a home-lab oriented controller for IPMI-enabled servers (Supermicro, Dell, HP) that manages fan curves, monitors sensors, and delivers alerts. Deploy via Docker on Raspberry Pi, servers, or any Docker-capable system.

## Features

- 🔒 Secure credential storage (Argon2 password hashing, Fernet encryption for secrets)
- 🌡️ Vendor-aware IPMI command abstraction with customizable fan targets
- ⚡ Background scheduler for per-server polling and fan adjustments
- 📢 Notification system for Slack, Teams, Discord, and Telegram
- 🖥️ Web UI with form-based authentication and per-fan overrides
- 🔔 Configurable alerts for connectivity, memory, power supply, intrusion, voltage, system events, and critical temperature

## Quick Start

### Docker Deployment (Recommended)

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

### Local Development

```bash
# Clone the repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup environment
bash deploy/docker-setup.sh

# Start container
docker compose up -d

# Access: https://localhost:8443
```

## Project Layout

- `docs/` – All documentation (deployment guides, architecture, quick start)
- `backend/` – FastAPI service for authentication, server orchestration, scheduling, and notifications
- `frontend/` – React web UI
- `deploy/` – Deployment scripts (docker-setup.sh, docker-prod-setup.sh, nginx.conf)

## Documentation

- **[Quick Start](docs/quickstart.md)** - Get up and running quickly
- **[Docker Deployment](docs/docker.md)** - Complete Docker deployment guide
- **[GitHub Container Registry](docs/github-setup.md)** - Using pre-built Docker images
- **[Security](docs/security.md)** - Security implementation details
- **[Architecture](docs/architecture.md)** - System architecture and design

## Docker on Raspberry Pi

```bash
# Install Docker on Raspberry Pi (if not already installed)
curl -fsSL https://get.docker.com | sh

# Clone the repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup and start
bash deploy/docker-prod-setup.sh
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## Access

- **Web UI**: https://localhost:8443
- **API**: https://localhost:8443/api/*

**Note**: Self-signed SSL certificates are used by default. You'll see a security warning in your browser - this is normal. Click "Advanced" → "Proceed" to continue.

## Requirements

- Docker Engine 20.10+ and Docker Compose v2.0+
- Network access to your IPMI-enabled servers (Supermicro, Dell iDRAC, HP iLO)
- `ipmitool` (included in Docker image)
