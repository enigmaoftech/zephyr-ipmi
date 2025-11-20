# HTTPS Setup for Zephyr IPMI

Zephyr IPMI supports HTTPS with self-signed certificates for secure communication, even without a reverse proxy. Both the backend and frontend can run with HTTPS enabled.

## Quick Start

### Backend HTTPS

1. **Generate SSL Certificate** (one-time setup):
   ```bash
   cd backend
   bash scripts/generate_ssl_cert.sh
   ```

2. **Start Server with HTTPS**:
   ```bash
   export ZEPHYR_SSL_ENABLED=true
   bash scripts/start_server.sh
   ```

   Or use the automatic detection (if certs exist):
   ```bash
   bash scripts/start_server.sh
   ```

The backend will start:
- **HTTP redirect server** on **port 8000** - automatically redirects all requests to HTTPS
- **HTTPS server** on **port 8443** - serves the actual application

### Frontend HTTPS

1. **Generate SSL Certificate** (one-time setup):
   ```bash
   cd frontend
   bash scripts/generate_ssl_cert.sh
   ```

2. **Start Frontend Dev Server with HTTP Redirect**:
   ```bash
   npm run dev:secure
   ```
   
   Or manually:
   ```bash
   bash scripts/start_dev.sh
   ```

   Or start without redirect (HTTPS only):
   ```bash
   npm run dev
   ```

The frontend will start:
- **HTTP redirect server** on **port 5174** - automatically redirects all requests to HTTPS
- **HTTPS server** on **port 5173** - serves the actual application

**Note**: Both frontend and backend will show browser security warnings for self-signed certificates. This is normal - click "Advanced" and "Proceed" to continue.

## Certificate Details

- **Location**: `backend/certs/zephyr-ipmi.crt` and `backend/certs/zephyr-ipmi.key`
- **Validity**: 10 years (3650 days)
- **Subject Alternative Names**: 
  - `localhost`
  - `*.local`
  - `127.0.0.1`
  - `0.0.0.0`
- **Key Size**: 4096-bit RSA
- **TLS Version**: Modern TLS (1.2+)

## Browser Security Warning

Since this is a self-signed certificate, browsers will show a security warning. This is **normal and expected**:

1. Click **"Advanced"** or **"Show Details"**
2. Click **"Proceed to localhost (unsafe)"** or **"Accept the Risk and Continue"**

The connection is still encrypted and secure - the warning is just because the certificate isn't signed by a trusted Certificate Authority.

## Environment Variables

- `ZEPHYR_SSL_ENABLED=true` - Enable HTTPS mode
- `ZEPHYR_SSL_CERT_FILE=./certs/zephyr-ipmi.crt` - Path to certificate file
- `ZEPHYR_SSL_KEY_FILE=./certs/zephyr-ipmi.key` - Path to private key file
- `ZEPHYR_PORT=8443` - Port to listen on (default: 8443 for HTTPS, 8000 for HTTP)
- `ZEPHYR_SESSION_COOKIE_SECURE=true` - Force secure cookies (automatically set with HTTPS)

## HTTP to HTTPS Redirect

### Backend Redirect

When HTTPS is enabled, two servers run:
- **Port 8000 (HTTP)**: Redirects all requests to HTTPS (port 8443)
- **Port 8443 (HTTPS)**: Serves the actual application

Any requests to `http://localhost:8000` will automatically redirect to `https://localhost:8443` with a 301 (Permanent Redirect) status code.

### Frontend Redirect

When using `npm run dev:secure` or `scripts/start_dev.sh`, two servers run:
- **Port 5174 (HTTP)**: Redirects all requests to HTTPS (port 5173)
- **Port 5173 (HTTPS)**: Serves the actual frontend application

Any requests to `http://localhost:5174` will automatically redirect to `https://localhost:5173` with a 301 (Permanent Redirect) status code.

**Note**: If you just run `npm run dev`, only the HTTPS server runs (no redirect). Use `npm run dev:secure` for automatic HTTP→HTTPS redirect.

## Frontend Configuration

The frontend is already configured to:
- Automatically enable HTTPS if certificates exist in `frontend/certs/`
- Proxy API requests to the HTTPS backend on port 8443
- Allow self-signed certificates for both frontend and backend
- Support HTTP to HTTPS redirect (when using `npm run dev:secure`)

### Quick Start:

1. Generate frontend certificates: `cd frontend && bash scripts/generate_ssl_cert.sh`
2. Start with redirect: `npm run dev:secure`
3. Access at: **https://localhost:5173** (or **http://localhost:5174** for auto-redirect)

### Manual Configuration (if needed)

If you need to customize the backend URL, update your frontend `.env` file:

```env
VITE_API_BASE_URL=https://localhost:8443/api
```

The Vite proxy in `vite.config.ts` is already configured to:
- Use HTTPS for the backend
- Allow self-signed certificates (`secure: false`)
- Rewrite `/api` paths correctly

## Security Notes

- Self-signed certificates provide encryption but not identity verification
- For production behind a reverse proxy (nginx, Traefik, etc.), use a proper CA-signed certificate (Let's Encrypt, etc.)
- The private key (`zephyr-ipmi.key`) should be kept secure with `chmod 600` permissions
- Certificate files are gitignored by default - regenerate on each deployment if needed

## Troubleshooting

**Certificate not found:**
```bash
bash scripts/generate_ssl_cert.sh
```

**Port already in use:**
```bash
export ZEPHYR_PORT=9443
bash scripts/start_server.sh
```

**Frontend can't connect:**
- Ensure `VITE_API_BASE_URL` points to `https://localhost:8443/api`
- Check browser console for CORS or certificate errors
- Accept the browser security warning first

