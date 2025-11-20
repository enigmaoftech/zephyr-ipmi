#!/bin/bash
# Start Zephyr IPMI backend server with optional HTTPS

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERT_DIR="${BACKEND_DIR}/certs"
CERT_FILE="${CERT_DIR}/zephyr-ipmi.crt"
KEY_FILE="${CERT_DIR}/zephyr-ipmi.key"

cd "${BACKEND_DIR}"

# Check if SSL is enabled
if [ "${ZEPHYR_SSL_ENABLED:-false}" = "true" ] || [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    echo "🔒 HTTPS mode enabled"
    
    # Generate certs if they don't exist
    if [ ! -f "${CERT_FILE}" ] || [ ! -f "${KEY_FILE}" ]; then
        echo "📜 Generating self-signed SSL certificate..."
        "${SCRIPT_DIR}/generate_ssl_cert.sh"
    fi
    
    export ZEPHYR_SSL_ENABLED=true
    export ZEPHYR_SSL_CERT_FILE="${CERT_FILE}"
    export ZEPHYR_SSL_KEY_FILE="${KEY_FILE}"
    export ZEPHYR_SESSION_COOKIE_SECURE=true
    
    SSL_ARGS="--ssl-keyfile \"${KEY_FILE}\" --ssl-certfile \"${CERT_FILE}\""
    DEFAULT_PORT=8443
    echo "✓ Starting server with HTTPS on port ${DEFAULT_PORT}"
    echo "  Certificate: ${CERT_FILE}"
    echo "  Private Key: ${KEY_FILE}"
    echo ""
    echo "⚠️  Browser will show security warning for self-signed certificate"
    echo "   This is normal - click 'Advanced' and 'Proceed' to continue"
    echo ""
else
    echo "🔓 HTTP mode (no SSL)"
    SSL_ARGS=""
    DEFAULT_PORT=8000
fi

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Start server
if [ -n "${SSL_ARGS}" ]; then
    echo "🔒 Starting HTTPS server on port ${DEFAULT_PORT}..."
    echo "   Web UI: https://localhost:${DEFAULT_PORT}"
    echo "   API: https://localhost:${DEFAULT_PORT}/api"
    echo ""
    # Start HTTPS server in foreground
    exec python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${ZEPHYR_PORT:-${DEFAULT_PORT}} \
        --ssl-keyfile "${KEY_FILE}" \
        --ssl-certfile "${CERT_FILE}" \
        "$@"
else
    echo "🔓 Starting HTTP server on port ${DEFAULT_PORT}..."
    exec python -m uvicorn app.main:app \
        --host 0.0.0.0 \
        --port ${ZEPHYR_PORT:-${DEFAULT_PORT}} \
        "$@"
fi

