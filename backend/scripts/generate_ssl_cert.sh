#!/bin/bash
# Generate self-signed SSL certificate for Zephyr IPMI

set -e

CERT_DIR="${CERT_DIR:-./certs}"
CERT_FILE="${CERT_DIR}/zephyr-ipmi.crt"
KEY_FILE="${CERT_DIR}/zephyr-ipmi.key"

# Create certs directory if it doesn't exist
mkdir -p "${CERT_DIR}"

# Generate self-signed certificate with modern TLS settings
openssl req -x509 -newkey rsa:4096 \
    -keyout "${KEY_FILE}" \
    -out "${CERT_FILE}" \
    -days 3650 \
    -nodes \
    -subj "/C=US/ST=State/L=City/O=Zephyr IPMI/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,DNS:*.local,IP:127.0.0.1,IP:0.0.0.0" \
    -addext "extendedKeyUsage=serverAuth" \
    -addext "keyUsage=digitalSignature,keyEncipherment"

# Set secure permissions
chmod 600 "${KEY_FILE}"
chmod 644 "${CERT_FILE}"

echo "✓ SSL certificate generated successfully!"
echo "  Certificate: ${CERT_FILE}"
echo "  Private Key: ${KEY_FILE}"
echo ""
echo "To use HTTPS, set these environment variables:"
echo "  export ZEPHYR_SSL_ENABLED=true"
echo "  export ZEPHYR_SSL_CERT_FILE=${CERT_FILE}"
echo "  export ZEPHYR_SSL_KEY_FILE=${KEY_FILE}"

