# Quick Start Guide

## 🚀 Getting Started

### Option 1: Production (GitHub Container Registry)

**Recommended for most users**

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

### Option 2: Local Development (Build from Source)

```bash
# Clone the repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup and start
bash deploy/docker-setup.sh
docker compose up -d

# Access: https://localhost:8443
```

### Option 3: Docker on Raspberry Pi

Same as Option 1, but run on Raspberry Pi:

```bash
# Install Docker on Raspberry Pi (if needed)
curl -fsSL https://get.docker.com | sh

# Clone repository
git clone https://github.com/enigmaoftech/zephyr-ipmi.git
cd zephyr-ipmi

# Setup and start
bash deploy/docker-prod-setup.sh
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

## First Time Setup

1. **Access the web UI**: https://localhost:8443
2. **Accept the SSL warning**: Click "Advanced" → "Proceed" (self-signed certificate)
3. **Create admin user**: First user automatically becomes admin
4. **Add your servers**: Configure IPMI credentials and fan curves

## 📚 Documentation

- **[Docker Deployment](docker.md)** - Complete Docker deployment guide
- **[GitHub Container Registry](github-setup.md)** - Using pre-built images
- **[Security](security.md)** - Security implementation details
- **[Architecture](architecture.md)** - System architecture and design

## 🆘 Troubleshooting

### Self-Signed Certificate Warning
This is normal. Click "Advanced" → "Proceed" in your browser.

### Port Already in Use
Change ports in `docker-compose.yml` or `docker-compose.prod.yml`.

### Can't Access
- Check containers are running: `docker compose ps`
- Check logs: `docker compose logs -f`
- Verify ports are accessible: `curl -k https://localhost:8443/api/auth/status`
