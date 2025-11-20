"""Background scheduler for polling IPMI targets."""
from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import SecretManager
from app.db.session import get_session
from app.models.alert import ActiveAlert
from app.models.notification import NotificationChannel
from app.models.server import ServerTarget
from app.services.ipmi import IPMIClient, IPMICommandError
from app.services.notifications import (
    DiscordProvider,
    NotificationMessage,
    SlackProvider,
    TelegramProvider,
    TeamsProvider,
    notify,
)

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def start_scheduler() -> None:
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def schedule_poll_job(server: ServerTarget) -> None:
    settings = get_settings()
    scheduler = get_scheduler()
    trigger = IntervalTrigger(seconds=server.poll_interval_seconds or settings.default_poll_interval_seconds)
    job_id = f"poll-server-{server.id}"
    scheduler.add_job(_poll_server, trigger=trigger, id=job_id, args=[server.id], replace_existing=True)
    logger.info("Scheduled poll job %s every %s seconds", job_id, trigger.interval.total_seconds())


def schedule_offline_check_job() -> None:
    """Schedule a periodic job to check for offline servers."""
    scheduler = get_scheduler()
    # Check every 5 minutes for offline servers
    trigger = IntervalTrigger(seconds=300)
    job_id = "check-offline-servers"
    scheduler.add_job(_check_offline_servers, trigger=trigger, id=job_id, replace_existing=True)
    logger.info("Scheduled offline server check job every 5 minutes")


async def _check_offline_servers() -> None:
    """Check all servers for offline status and send alerts if needed."""
    async with get_session() as session:
        result = await session.execute(select(ServerTarget))
        servers = result.scalars().all()
        
        now = datetime.now(timezone.utc)
        for server in servers:
            # Skip if connectivity alerts are disabled
            if not _is_alert_enabled(server, "connectivity"):
                continue
            
            # Skip if no notification channels configured
            if not server.notification_channel_ids:
                continue
            
            # Check if server is offline
            threshold_minutes = server.offline_alert_threshold_minutes or 15
            threshold_timedelta = timedelta(minutes=threshold_minutes)
            
            if server.last_successful_poll is None:
                # Never successfully polled - check if enough time has passed since creation
                created_at = server.created_at
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)
                time_since_creation = now - created_at
                if time_since_creation >= threshold_timedelta:
                    # Server has been around long enough to expect at least one successful poll
                    await _activate_alert(
                        session,
                        server,
                        "connectivity",
                        f"Server has not responded since creation ({time_since_creation.total_seconds() / 60:.1f} minutes ago).\n\nCheck network connectivity and BMC settings.",
                    )
            else:
                # Check if last successful poll is too old
                last_poll = server.last_successful_poll
                if last_poll.tzinfo is None:
                    last_poll = last_poll.replace(tzinfo=timezone.utc)
                time_since_last_poll = now - last_poll
                if time_since_last_poll >= threshold_timedelta:
                    minutes_offline = time_since_last_poll.total_seconds() / 60
                    await _activate_alert(
                        session,
                        server,
                        "connectivity",
                        f"Server has been offline for {minutes_offline:.1f} minutes (threshold: {threshold_minutes} minutes).\n\nLast successful poll: {server.last_successful_poll}",
                    )
                else:
                    # Server is back online (within threshold), clear offline alert
                    await _clear_alert_if_active(session, server, "connectivity", "auto")


async def _poll_server(server_id: int) -> None:
    logger.debug("Polling server %s", server_id)
    secret_manager = SecretManager()
    async with get_session() as session:
        server = await _load_server(session, server_id)
        if not server:
            logger.warning("Server %s removed before poll", server_id)
            return
        client = IPMIClient(server, secret_manager)
        try:
            temperatures = await client.query_temperatures()
            fans = await client.query_fans()
            logger.debug("Temperatures: %s", temperatures)
            logger.debug("Fans: %s", fans)
            
            # Parse CPU temperature and apply fan control
            cpu_temp = _parse_cpu_temperature(temperatures)
            if cpu_temp is not None:
                logger.info("Server %s CPU temperature: %s°C", server.name, cpu_temp)
                
                # Calculate base RPM from zones (for fans without overrides)
                base_rpm = _calculate_target_rpm(server, cpu_temp)
                
                if base_rpm is not None:
                    # Get first zone threshold to determine when overrides stop applying
                    first_zone_threshold = _get_first_zone_threshold(server)
                    
                    # Set base fan speed for all fans
                    logger.info("Setting base fan speed to %s RPM for server %s (CPU: %s°C)", base_rpm, server.name, cpu_temp)
                    await client.set_fan_speed(base_rpm)
                    
                    # Apply per-fan overrides if configured
                    if server.fan_overrides:
                        for override in server.fan_overrides:
                            if not override.fan_identifier or override.min_rpm is None:
                                continue
                            
                            # Use override RPM if temp is below first zone threshold
                            # Otherwise, use normal zone-based RPM
                            if first_zone_threshold is not None and cpu_temp <= first_zone_threshold:
                                override_rpm = override.min_rpm
                                logger.info(
                                    "Applying override RPM %s for fan %s on server %s (CPU: %s°C <= %s°C)",
                                    override_rpm, override.fan_identifier, server.name, cpu_temp, first_zone_threshold
                                )
                                await client.set_fan_speed(override_rpm, fan_identifier=override.fan_identifier)
                            else:
                                # Use normal zone-based RPM for this fan too
                                logger.debug(
                                    "Fan %s on server %s using normal zone RPM %s (CPU: %s°C > %s°C)",
                                    override.fan_identifier, server.name, base_rpm, cpu_temp, first_zone_threshold
                                )
                                await client.set_fan_speed(base_rpm, fan_identifier=override.fan_identifier)
                else:
                    logger.debug("No fan control action needed for server %s (CPU: %s°C)", server.name, cpu_temp)
                
                # Check for critical temperature if alert enabled
                if _is_alert_enabled(server, "temperature_critical"):
                    if cpu_temp >= 80:  # Critical threshold
                        await _activate_alert(session, server, "temperature_critical", f"CPU temperature critical: {cpu_temp}°C")
                    else:
                        await _clear_alert_if_active(session, server, "temperature_critical", "auto")
            else:
                logger.warning("Could not parse CPU temperature for server %s", server.name)
            
            # Check for other alerts if enabled
            await _check_alerts(session, server, client)
            
            # Update last successful poll timestamp
            server.last_successful_poll = datetime.now(timezone.utc)
            await session.commit()
                
        except IPMICommandError as exc:
            # Connection/authentication failure
            error_msg = str(exc)
            if "Unable to establish" in error_msg or "Connection refused" in error_msg or "timeout" in error_msg.lower():
                logger.error("Server %s unreachable: %s", server.name, error_msg)
                if _is_alert_enabled(server, "connectivity"):
                    await _activate_alert(session, server, "connectivity", f"Server unreachable: {error_msg}\n\nCheck network connectivity and BMC settings.")
            else:
                logger.exception("IPMI command error for server %s: %s", server.name, exc)
                if _is_alert_enabled(server, "connectivity"):
                    await _activate_alert(session, server, "connectivity", f"IPMI communication error: {error_msg}")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to poll server %s: %s", server.name, exc)
            if _is_alert_enabled(server, "connectivity"):
                await _activate_alert(session, server, "connectivity", f"Unexpected error during poll: {str(exc)}")
        else:
            # If poll succeeded, clear connectivity alert if it was active
            if _is_alert_enabled(server, "connectivity"):
                await _clear_alert_if_active(session, server, "connectivity", "auto")


def _parse_cpu_temperature(temperature_output: str) -> float | None:
    """Parse CPU temperature from IPMI SDR output.
    
    Example output:
    CPU Temp     | 04h | ok  |  7.1 | 50 degrees C
    CPU1 Temp    | 04h | ok  |  7.1 | 50 degrees C
    """
    if not temperature_output:
        return None
    
    lines = temperature_output.strip().split('\n')
    for line in lines:
        line = line.strip()
        if 'CPU' in line.upper() and 'TEMP' in line.upper():
            # Look for temperature value (usually at the end: "50 degrees C")
            parts = line.split('|')
            if len(parts) >= 5:
                temp_str = parts[-1].strip()
                # Extract number before "degrees C"
                if 'degrees C' in temp_str.lower() or 'degrees' in temp_str.lower():
                    temp_value = temp_str.split()[0]
                    try:
                        return float(temp_value)
                    except ValueError:
                        continue
            # Alternative: look for temperature pattern in the line
            match = re.search(r'(\d+(?:\.\d+)?)\s*degrees?\s*C', line, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except ValueError:
                    continue
    
    # Fallback: try to extract any temperature value
    matches = re.findall(r'(\d+(?:\.\d+)?)\s*degrees?\s*C', temperature_output, re.IGNORECASE)
    if matches:
        try:
            # Return the highest temperature (likely CPU)
            temps = [float(m) for m in matches]
            return max(temps)
        except ValueError:
            pass
    
    return None


def _get_first_zone_threshold(server: ServerTarget) -> float | None:
    """Get the second zone temperature threshold (first zone where fans ramp up from base).
    
    This is used to determine when fan overrides should stop applying
    and fans should follow normal zones. Overrides apply until this threshold.
    
    Example: Zones are 50°C (1800 RPM), 52°C (3500 RPM), 70°C (5000 RPM)
    Returns: 52°C - override fans use their custom RPM until 52°C, then follow zones.
    """
    if not server.fan_defaults or 'zones' not in server.fan_defaults:
        return None
    
    zones = server.fan_defaults.get('zones', [])
    if not zones or len(zones) < 2:
        return None
    
    # Sort zones by temperature threshold (ascending)
    sorted_zones = sorted(zones, key=lambda z: z.get('temp_threshold', 0))
    
    # Return the second zone's threshold (first ramp-up threshold)
    # This is where fans transition from base/low RPM to higher RPM
    return float(sorted_zones[1].get('temp_threshold', 0))


def _calculate_target_rpm(server: ServerTarget, cpu_temp: float) -> int | None:
    """Calculate target RPM based on CPU temperature and configured fan zones.
    
    Zones are sorted by temperature threshold. The target RPM is selected based on
    which zone the current temperature falls into.
    """
    if not server.fan_defaults or 'zones' not in server.fan_defaults:
        logger.debug("No fan zones configured for server %s", server.name)
        return None
    
    zones = server.fan_defaults.get('zones', [])
    if not zones:
        logger.debug("No fan zones configured for server %s", server.name)
        return None
    
    # Sort zones by temperature threshold (ascending)
    sorted_zones = sorted(zones, key=lambda z: z.get('temp_threshold', 0))
    
    # Find the appropriate zone for current temperature
    target_rpm = None
    for zone in sorted_zones:
        threshold = zone.get('temp_threshold', 0)
        rpm = zone.get('target_rpm', 0)
        
        # For the first zone (lowest temp), use if temp is below threshold
        if sorted_zones.index(zone) == 0:
            if cpu_temp <= threshold:
                target_rpm = rpm
                break
        # For subsequent zones, use if temp is above previous threshold and below/at current
        else:
            prev_threshold = sorted_zones[sorted_zones.index(zone) - 1].get('temp_threshold', 0)
            if prev_threshold < cpu_temp <= threshold:
                target_rpm = rpm
                break
    
    # If temp is above all thresholds, use the highest zone's RPM
    if target_rpm is None and sorted_zones:
        highest_zone = sorted_zones[-1]
        target_rpm = highest_zone.get('target_rpm', 0)
    
    # If target RPM is 0, that means full speed
    if target_rpm == 0:
        logger.debug("Target RPM is 0 (full speed) for server %s", server.name)
        return 0
    
    return target_rpm


async def _load_server(session: AsyncSession, server_id: int) -> ServerTarget | None:
    result = await session.get(ServerTarget, server_id)
    return result


def _is_alert_enabled(server: ServerTarget, alert_type: str) -> bool:
    """Check if a specific alert type is enabled for the server."""
    if not server.alert_config:
        return False
    return server.alert_config.get(alert_type, False)


async def _check_alerts(session: AsyncSession, server: ServerTarget, client: IPMIClient) -> None:
    """Check for various IPMI alerts and send notifications if enabled.
    
    Only sends alerts when transitioning from clear to active.
    Checks if previously active alerts have cleared and sends cleared notifications.
    """
    if not server.notification_channel_ids:
        return  # No notification channels configured
    
    # Track current alert states
    current_alerts: dict[str, bool] = {}
    
    # Check memory errors
    if _is_alert_enabled(server, "memory_errors"):
        try:
            memory_status = await client.query_memory_status()
            has_errors = memory_status and _has_errors(memory_status, ["ns", "nc", "cr", "nr"])
            current_alerts["memory_errors"] = has_errors
            if has_errors:
                await _activate_alert(session, server, "memory_errors", f"Memory errors detected:\n{memory_status}")
            else:
                await _clear_alert_if_active(session, server, "memory_errors", "auto")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not check memory status for server %s: %s", server.name, exc)
    
    # Check power supply failures
    if _is_alert_enabled(server, "power_failure"):
        try:
            power_status = await client.query_power_supply_status()
            has_errors = power_status and _has_errors(power_status, ["ns", "nc", "cr", "nr"])
            current_alerts["power_failure"] = has_errors
            if has_errors:
                await _activate_alert(session, server, "power_failure", f"Power supply issue detected:\n{power_status}")
            else:
                await _clear_alert_if_active(session, server, "power_failure", "auto")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not check power supply status for server %s: %s", server.name, exc)
    
    # Check chassis intrusion
    if _is_alert_enabled(server, "intrusion"):
        try:
            intrusion_status = await client.query_chassis_intrusion()
            has_intrusion = intrusion_status and _has_intrusion(intrusion_status)
            current_alerts["intrusion"] = has_intrusion
            if has_intrusion:
                await _activate_alert(session, server, "intrusion", f"Chassis intrusion detected:\n{intrusion_status}")
            else:
                await _clear_alert_if_active(session, server, "intrusion", "auto")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not check chassis intrusion for server %s: %s", server.name, exc)
    
    # Check voltage issues
    if _is_alert_enabled(server, "voltage_issues"):
        try:
            voltage_status = await client.query_voltage_status()
            has_errors = voltage_status and _has_errors(voltage_status, ["ns", "nc", "cr", "nr"])
            current_alerts["voltage_issues"] = has_errors
            if has_errors:
                await _activate_alert(session, server, "voltage_issues", f"Voltage issues detected:\n{voltage_status}")
            else:
                await _clear_alert_if_active(session, server, "voltage_issues", "auto")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not check voltage status for server %s: %s", server.name, exc)
    
    # Check system events (SEL)
    if _is_alert_enabled(server, "system_events"):
        try:
            system_events = await client.query_system_events(limit=5)
            has_events = system_events and _has_critical_events(system_events)
            current_alerts["system_events"] = has_events
            if has_events:
                await _activate_alert(session, server, "system_events", f"Critical system events detected:\n{system_events}")
            else:
                await _clear_alert_if_active(session, server, "system_events", "auto")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Could not check system events for server %s: %s", server.name, exc)


def _has_errors(status_output: str, error_indicators: list[str]) -> bool:
    """Check if SDR output contains error indicators.
    
    IPMI SDR format: name | hex_id | status | value | reading
    Example: "12V | 30h | ok | 7.18 | 12.24 Volts"
    
    We check the status column (3rd field) - if it's not "ok", there's an error.
    Also check for error indicators in the status column.
    """
    if not status_output:
        return False
    
    lines = status_output.strip().split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Parse the SDR format: name | hex | status | value | reading
        parts = [p.strip() for p in line.split('|')]
        if len(parts) >= 3:
            status = parts[2].lower()
            # If status is not "ok", there's an error
            if status != "ok":
                # Check if it matches error indicators
                for indicator in error_indicators:
                    if indicator in status:
                        return True
                # If status is not "ok" and doesn't match known indicators, still consider it an error
                return True
    
    return False


def _has_intrusion(intrusion_output: str) -> bool:
    """Check if chassis intrusion is detected."""
    if not intrusion_output:
        return False
    output_lower = intrusion_output.lower()
    # Look for intrusion indicators
    intrusion_keywords = ["intrusion", "chassis open", "ns", "nc", "cr"]
    return any(keyword in output_lower for keyword in intrusion_keywords)


def _has_critical_events(events_output: str) -> bool:
    """Check if system event log contains critical events."""
    if not events_output:
        return False
    events_lower = events_output.lower()
    # Look for critical event types
    critical_indicators = ["critical", "non-recoverable", "nr", "cr", "error"]
    return any(indicator in events_lower for indicator in critical_indicators)


async def _activate_alert(
    session: AsyncSession,
    server: ServerTarget,
    alert_type: str,
    message: str,
) -> None:
    """Activate an alert if not already active and send notification."""
    # Check if alert is already active
    result = await session.execute(
        select(ActiveAlert).where(
            ActiveAlert.server_id == server.id,
            ActiveAlert.alert_type == alert_type,
            ActiveAlert.cleared_at.is_(None),  # Not cleared
        )
    )
    existing_alert = result.scalar_one_or_none()
    
    if existing_alert:
        # Alert already active, just update last_updated_at
        existing_alert.last_updated_at = datetime.now(timezone.utc)
        await session.commit()
        return  # Don't send duplicate notification
    
    # Create new active alert
    active_alert = ActiveAlert(
        server_id=server.id,
        alert_type=alert_type,
        message=message,
        first_triggered_at=datetime.now(timezone.utc),
        last_updated_at=datetime.now(timezone.utc),
    )
    session.add(active_alert)
    await session.commit()
    
    # Send notification
    await _send_alert_notification(session, server, alert_type, message, is_cleared=False)


async def _clear_alert_if_active(
    session: AsyncSession,
    server: ServerTarget,
    alert_type: str,
    cleared_by: str,
) -> None:
    """Clear an alert if it's currently active and send cleared notification."""
    result = await session.execute(
        select(ActiveAlert).where(
            ActiveAlert.server_id == server.id,
            ActiveAlert.alert_type == alert_type,
            ActiveAlert.cleared_at.is_(None),  # Not already cleared
        )
    )
    active_alert = result.scalar_one_or_none()
    
    if not active_alert:
        return  # Alert not active, nothing to clear
    
    # Mark alert as cleared
    active_alert.cleared_at = datetime.now(timezone.utc)
    active_alert.cleared_by = cleared_by
    active_alert.last_updated_at = datetime.now(timezone.utc)
    await session.commit()
    
    # Send cleared notification
    await _send_alert_notification(session, server, alert_type, active_alert.message, is_cleared=True)


async def _send_alert_notification(
    session: AsyncSession,
    server: ServerTarget,
    alert_type: str,
    message: str,
    is_cleared: bool = False,
) -> None:
    """Send alert notification to configured channels."""
    if not server.notification_channel_ids:
        return
    
    # Load notification channels
    result = await session.execute(
        select(NotificationChannel).where(
            NotificationChannel.id.in_(server.notification_channel_ids),
            NotificationChannel.enabled == True,  # noqa: E712
        )
    )
    channels = result.scalars().all()
    
    if not channels:
        logger.debug("No enabled notification channels for server %s", server.name)
        return
    
    secret_manager = SecretManager()
    alert_subjects = {
        "connectivity": "Server Connectivity Alert",
        "memory_errors": "Memory Error Alert",
        "power_failure": "Power Supply Failure",
        "intrusion": "Chassis Intrusion Alert",
        "voltage_issues": "Voltage Issue Alert",
        "system_events": "Critical System Event",
        "temperature_critical": "Critical Temperature Alert",
    }
    
    # Format alert type for display (e.g., "chassis_intrusion" -> "Intrusion")
    alert_type_label = alert_subjects.get(alert_type, alert_type.replace('_', ' ').title())
    
    if is_cleared:
        subject = f"{alert_type_label} Cleared"
        body = f"Server: {server.name}"
    else:
        subject = alert_type_label
        # Format message with better spacing
        body = f"Server: {server.name}\n\n{alert_type.replace('_', ' ').title()}:\n{message}"
    
    notification = NotificationMessage(
        subject=subject,
        body=body,
        metadata={"server_id": str(server.id), "alert_type": alert_type, "is_cleared": str(is_cleared)},
    )
    
    # Send to all configured channels
    for channel in channels:
        try:
            if channel.type == "slack":
                provider = SlackProvider(channel.endpoint_encrypted, secret_manager)
            elif channel.type == "teams":
                provider = TeamsProvider(channel.endpoint_encrypted, secret_manager)
            elif channel.type == "discord":
                provider = DiscordProvider(channel.endpoint_encrypted, secret_manager)
            elif channel.type == "telegram":
                chat_id = channel.channel_metadata.get("chat_id", "") if channel.channel_metadata else ""
                if not chat_id:
                    logger.warning("Telegram channel %s missing chat_id", channel.name)
                    continue
                provider = TelegramProvider(channel.endpoint_encrypted, chat_id, secret_manager)
            else:
                logger.warning("Unsupported notification channel type: %s", channel.type)
                continue
            
            await notify(provider, notification)
            logger.info("Sent %s %s for server %s to channel %s", alert_type, "cleared" if is_cleared else "alert", server.name, channel.name)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to send alert to channel %s: %s", channel.name, exc)
