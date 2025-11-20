# Security Implementation

This document details how Zephyr IPMI ensures all sensitive data is properly salted and encrypted.

## Overview

Zephyr IPMI implements comprehensive security measures for all sensitive data:
- **User Passwords**: Hashed with Argon2id (salted automatically)
- **IPMI Credentials**: Encrypted with Fernet (symmetric encryption)
- **Notification Webhooks/API Keys**: Encrypted with Fernet
- **Session Cookies**: Signed with itsdangerous (HMAC-based)
- **Metadata/Notes**: Encrypted with Fernet

## User Authentication

### Password Hashing

- **Algorithm**: Argon2id (via `passlib`)
- **Salting**: Automatic (Argon2id includes salt in the hash)
- **Implementation**: `app/core/security.py` → `PasswordHasher`

```python
# Passwords are hashed when created/updated
password_hash = PasswordHasher.hash(password)  # Returns Argon2id hash with salt

# Verification
PasswordHasher.verify(password, password_hash)  # Extracts salt from hash and verifies
```

**Properties**:
- Each password gets a unique random salt (stored with the hash)
- Argon2id is memory-hard and resistant to GPU/ASIC attacks
- Passwords are **never stored in plaintext** - only hashes are stored

### Session Management

- **Signing**: HMAC-SHA256 (via `itsdangerous.URLSafeTimedSerializer`)
- **Salt**: `"zephyr-session"` (custom salt for session signing)
- **Cookie Security**:
  - `HttpOnly`: Prevents JavaScript access
  - `Secure`: Only sent over HTTPS (when `ZEPHYR_SSL_ENABLED=true`)
  - `SameSite=Lax`: CSRF protection
  - Time-based expiration (default: 24 hours)

**Implementation**: `app/core/security.py` → `SessionSigner`

```python
# Session token contains only username, signed with secret key
token = signer.dumps({"sub": user.username})
# Token is tamper-proof - any modification invalidates it
```

## IPMI Credentials Encryption

### Encryption Method

- **Algorithm**: Fernet (symmetric encryption, AES-128 in CBC mode)
- **Key Derivation**: SHA-256 hash of encryption key → base64 URL-safe encoding
- **Implementation**: `app/core/security.py` → `SecretManager`

**What Gets Encrypted**:
- IPMI usernames (`username_encrypted`)
- IPMI passwords (`password_encrypted`)
- Server metadata/notes (`metadata_encrypted`)

**Key Management**:
- Encryption key stored in `.env` file: `ZEPHYR_ENCRYPTION_KEY`
- Key must be a valid Fernet key (32 bytes, base64-encoded)
- Fallback: Uses `ZEPHYR_SECRET_KEY` if encryption key not set
- **Never commit `.env` to version control**

```python
# Credentials encrypted before storage
username_encrypted = secret_manager.encrypt(ipmi_username)
password_encrypted = secret_manager.encrypt(ipmi_password)

# Decrypted only when needed for IPMI commands
username = secret_manager.decrypt(server.username_encrypted)
password = secret_manager.decrypt(server.password_encrypted)
```

## Notification Channel Credentials

### Webhook/API Key Encryption

- **Same Encryption**: Fernet (using `SecretManager`)
- **What Gets Encrypted**:
  - Webhook URLs/endpoints (`endpoint_encrypted`)
  - API tokens (stored in `channel_metadata` and encrypted)

**Implementation**: `app/services/notification_channels.py`

```python
# Webhook URL encrypted
endpoint_encrypted = secret_manager.encrypt(webhook_url)

# Telegram chat_id stored in metadata (also encrypted if sensitive)
```

## Metadata/Notes Encryption

- **Encryption**: Fernet (via `SecretManager`)
- **Format**: JSON string encrypted as a whole
- **Usage**: Server room/notes stored encrypted in `metadata_encrypted`

## Configuration Requirements

### Environment Variables

**Required**:
- `ZEPHYR_SECRET_KEY`: Used for session signing (generate: `openssl rand -hex 32`)
- `ZEPHYR_ENCRYPTION_KEY`: Fernet key for data encryption (generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)

**Optional**:
- `ZEPHYR_SSL_ENABLED=true`: Enables HTTPS and secure cookies
- `ZEPHYR_SESSION_COOKIE_SECURE=true`: Forces secure cookies (HTTPS only)

### Key Generation

On first deployment, generate secure keys:

```bash
# Generate secret key for sessions
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate encryption key for sensitive data
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Add to `.env`:
```bash
ZEPHYR_SECRET_KEY=<generated-secret-key>
ZEPHYR_ENCRYPTION_KEY=<generated-encryption-key>
ZEPHYR_SSL_ENABLED=true
```

## Database Storage

### What's Encrypted in Database

| Field | Type | Encryption |
|-------|------|------------|
| `users.password_hash` | Argon2id hash | Hashed (not encrypted) |
| `server_targets.username_encrypted` | String | Fernet encrypted |
| `server_targets.password_encrypted` | String | Fernet encrypted |
| `server_targets.metadata_encrypted` | String | Fernet encrypted (JSON) |
| `notification_channels.endpoint_encrypted` | String | Fernet encrypted |

### What's NOT Encrypted (by design)

- Server names, BMC host/IP, vendor (not sensitive)
- Fan configuration, alert settings (not sensitive)
- Alert messages, timestamps (not sensitive)

## Security Best Practices

1. **Never commit `.env` file** - Contains encryption keys
2. **Use HTTPS in production** - Protects session cookies and API traffic
3. **Generate strong keys** - Use cryptographically secure random generators
4. **Rotate keys periodically** - Re-encrypt data if keys are compromised
5. **Restrict file permissions** - `.env` should be `chmod 600`
6. **Use separate encryption key** - Don't reuse `ZEPHYR_SECRET_KEY` as encryption key
7. **Backup encryption keys** - Store keys securely (password manager, encrypted backup)

## Verification

To verify security is properly configured:

```bash
# Check .env file exists and has keys
cd backend
cat .env | grep -E "SECRET_KEY|ENCRYPTION_KEY"

# Verify passwords are hashed (not plaintext)
sqlite3 zephyr.db "SELECT username, password_hash FROM users;"
# Should see Argon2id hashes like: $argon2id$v=19$m=65536,t=3,p=4$...

# Verify IPMI credentials are encrypted
sqlite3 zephyr.db "SELECT name, username_encrypted FROM server_targets LIMIT 1;"
# Should see encrypted strings (not plaintext usernames)

# Check SSL is enabled
grep ZEPHYR_SSL_ENABLED .env
```

## Encryption Algorithm Details

### Fernet (Symmetric Encryption)

- **Cipher**: AES-128 in CBC mode
- **Authentication**: HMAC-SHA256
- **Key Size**: 128 bits (32 bytes base64-encoded)
- **IV**: Random per encryption
- **Output**: URL-safe base64 encoded

### Argon2id (Password Hashing)

- **Version**: Argon2id v1.3+
- **Memory Cost**: 65536 KiB (configurable via passlib)
- **Time Cost**: 3 iterations (configurable)
- **Parallelism**: 4 threads (configurable)
- **Output**: Includes algorithm, parameters, salt, and hash

## Key Rotation

If encryption keys need to be rotated:

1. Generate new keys
2. Update `.env` with new keys
3. For IPMI credentials: Re-save each server (will re-encrypt with new key)
4. For notification channels: Re-save each channel (will re-encrypt with new key)
5. Old encrypted data will need to be migrated (decrypt with old key, encrypt with new)

## Summary

✅ **User passwords**: Argon2id hashed (salted automatically)  
✅ **IPMI credentials**: Fernet encrypted  
✅ **Webhook URLs**: Fernet encrypted  
✅ **Metadata/notes**: Fernet encrypted  
✅ **Session cookies**: HMAC-SHA256 signed  
✅ **HTTPS support**: SSL/TLS encryption for transport  

All sensitive data is properly protected at rest (encryption/hashing) and in transit (HTTPS).

