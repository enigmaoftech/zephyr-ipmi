#!/bin/bash
# Start Zephyr IPMI frontend dev server with HTTP to HTTPS redirect

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FRONTEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERT_DIR="${FRONTEND_DIR}/certs"
CERT_FILE="${CERT_DIR}/zephyr-frontend.crt"
KEY_FILE="${CERT_DIR}/zephyr-frontend.key"

cd "${FRONTEND_DIR}"

# Check if SSL certificates exist
if [ -f "${CERT_FILE}" ] && [ -f "${KEY_FILE}" ]; then
    echo "🔒 HTTPS mode enabled"
    echo "✓ SSL certificates found"
    echo ""
    
    # Cleanup function
    cleanup() {
        if [ -n "${REDIRECT_PID}" ]; then
            echo ""
            echo "Stopping HTTP redirect server (PID: $REDIRECT_PID)..."
            kill $REDIRECT_PID 2>/dev/null || true
        fi
    }

    trap cleanup EXIT INT TERM

    # Start HTTP redirect server
    echo "🔄 Starting HTTP redirect server on port 5174..."
    node "${SCRIPT_DIR}/http_redirect_server.js" 5174 > /dev/null 2>&1 &
    REDIRECT_PID=$!
    echo "✓ HTTP redirect server started (PID: $REDIRECT_PID)"
    echo "   All HTTP traffic on port 5174 will redirect to HTTPS on port 5173"
    echo ""
    
    # Start Vite dev server (HTTPS)
    echo "🔒 Starting HTTPS frontend dev server on port 5173..."
    echo ""
    npm run dev
else
    echo "🔓 HTTP mode (no SSL certificates found)"
    echo "   To enable HTTPS, run: bash scripts/generate_ssl_cert.sh"
    echo ""
    npm run dev
fi

