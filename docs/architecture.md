# Zephyr IPMI Architecture Overview

## Goals
- Manage fan curves and telemetry over IPMI for Supermicro, Dell, and HP servers.
- Provide a secure, web-based UI with form-based authentication.
- Run on Raspberry Pi (ARM64/ARMv7), bare-metal Linux servers, and within Docker containers.
- Allow per-server monitoring thresholds and per-fan overrides, with sane defaults for home labs.
- Offer encrypted storage for all sensitive configuration values.
- Deliver notifications when connectivity or hardware health issues are detected.

## High-Level Components
1. **API & Service Layer (Backend)**
   - Implemented with FastAPI (Python 3.11) for async request handling and great ARM/Docker support.
   - Exposes REST and WebSocket endpoints for configuration, monitoring, and real-time updates.
   - Handles authentication, authorization, notification delivery, scheduling, and IPMI orchestration.
2. **Web UI (Frontend)**
   - Built with React + Vite for a lightweight, fast SPA served by the backend.
   - Uses component library (e.g., Mantine) for accessible form controls and dashboards.
   - Communicates with backend via secure HTTPS (TLS) REST and WebSocket APIs.
3. **Scheduler & Worker Subsystem**
   - Uses APScheduler to run periodic jobs per server (default 5-minute checks) including Raspberry Pi safe frequencies.
   - Offloads long-running IPMI commands to background workers (ThreadPoolExecutor) to keep API responsive.
4. **Persistence Layer**
   - SQLite database (with optional PostgreSQL) via SQLAlchemy for configuration, audit, and telemetry history.
   - Sensitive fields stored encrypted-at-rest using Fernet (symmetric encryption) with per-installation master key.
5. **Secret Management**
   - Master key stored in OS keyring or `.env` file with instructions for secure storage.
   - Secrets include IPMI credentials, notification webhooks, SMTP tokens, etc.
   - Passwords hashed using Argon2id via `passlib`, salts generated per user.
6. **Notification Engine**
   - Modular providers: email, Microsoft Teams, Slack, Discord, Telegram.
   - Configurable retry/backoff and per-alert routing rules.
7. **IPMI Control Module**
   - Abstracts vendor differences (Supermicro, Dell iDRAC, HP iLO).
   - Uses `ipmitool` via subprocess (lanplus) with per-vendor command templates.
   - Supports querying fan inventory, temperatures, and sending raw commands.

## Data Model (Initial)
- `User`: username, password_hash, role, MFA secret (future), created_at.
- `ServerTarget`: name, vendor, BMC host/IP, port, username (encrypted), password (encrypted), polling_interval, fan_profile.
- `FanProfile`: references server, default curve settings, per-fan overrides.
- `FanOverride`: fan identifier, min_rpm, max_rpm, temperature_thresholds.
- `TelemetrySample`: server_id, timestamp, cpu_temp, fan_rpm, status_flags.
- `NotificationChannel`: type (teams/slack/discord/telegram), endpoint (encrypted), enabled.
- `AlertRule`: trigger (connectivity, intrusion, lockout, memory_error), threshold, channel mapping.
- `JobLog`: job_id, server_id, start/end, status, message.

## IPMI Fan Control Logic
- Default polling interval: 5 minutes.
- For Supermicro defaults: if CPU temp ≤ 50 °C and any fan RPM > 2050, send raw command `0x30 0x70 0x66 0x01 0x00 0x00 0x18` to lower to ~1800 RPM.
- Leave fans unchanged when CPU temp ≥ 50 °C.
- Allow user-defined thresholds per server/fan with validation.
- Adaptive safeguards: enforce minimum RPMs per vendor recommendations; log warnings when user overrides exceed safe ranges.

## Security Considerations
- All API endpoints require HTTPS and authenticated sessions (server-side signed cookies + CSRF tokens).
- Rate limiting and brute-force protection at login.
- Secrets encrypted with per-installation key and salted before storage.
- Audit trail for configuration changes and IPMI commands issued.
- Optional 2FA (TOTP) planned for later iteration.

## Deployment Targets
- **Raspberry Pi**: Provide install script (Python venv + systemd service). Build for ARM using multi-arch Docker images.
- **Docker**: Multi-stage Dockerfile (backend + frontend build), docker-compose example with persistent volumes.
- **Bare Metal**: systemd unit files and instructions for Ubuntu/Debian.

## Monitoring & Notifications
- Background job monitors communication health; triggers alerts if IPMI polls fail `N` times (configurable, default 3).
- Additional sensor queries: chassis intrusion, account lockouts, memory errors, power supply alerts (vendor-specific raw commands/Sensor Data Records).
- Notifications dispatched via provider-specific webhooks/APIs with templated messages.

## Next Steps
1. Define detailed API schema (Pydantic models) and authentication flow.
2. Scaffold FastAPI project with SQLAlchemy models and Alembic migrations.
3. Implement IPMI adapter layer with vendor-specific command sets and simulation mode for development.
4. Build React UI skeleton: auth pages, server list, fan profile editor, notification settings.
5. Package deployment artifacts (Dockerfile, compose, systemd units) and document hardware prerequisites.
