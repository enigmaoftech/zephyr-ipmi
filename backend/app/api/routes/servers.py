"""Server configuration endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, get_secret_manager
from app.core.security import SecretManager
from app.models.user import User
from app.schemas.server import ServerCreate, ServerRead, ServerUpdate
from app.models.alert import ActiveAlert
from app.schemas.alert import ActiveAlertRead
from app.services import servers as server_service
from app.services.ipmi import IPMIClient, IPMICommandError
from app.services.scheduler import _clear_alert_if_active, schedule_poll_job


def _server_to_read(server, secret_manager: SecretManager) -> ServerRead:
    """Convert ServerTarget model to ServerRead schema with decrypted metadata."""
    from app.services.servers import _decrypt_metadata
    
    server_dict = {
        "id": server.id,
        "name": server.name,
        "vendor": server.vendor,
        "bmc_host": server.bmc_host,
        "bmc_port": server.bmc_port,
        "poll_interval_seconds": server.poll_interval_seconds,
        "fan_defaults": server.fan_defaults,
        "notification_channel_ids": server.notification_channel_ids,
        "alert_config": server.alert_config,
        "offline_alert_threshold_minutes": server.offline_alert_threshold_minutes,
        "created_at": server.created_at,
        "fan_overrides": server.fan_overrides,
        "metadata": _decrypt_metadata(server, secret_manager),
    }
    return ServerRead.model_validate(server_dict)

router = APIRouter(prefix="/servers", tags=["servers"])


@router.get("/", response_model=list[ServerRead])
async def list_servers(
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> list[ServerRead]:
    servers = await server_service.list_servers(session)
    return [_server_to_read(server, secret_manager) for server in servers]


@router.post("/", response_model=ServerRead, status_code=status.HTTP_201_CREATED)
async def create_server(
    payload: ServerCreate,
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> ServerRead:
    server = await server_service.create_server(session, payload, secret_manager)
    await session.commit()
    schedule_poll_job(server)
    return _server_to_read(server, secret_manager)


@router.get("/{server_id}", response_model=ServerRead)
async def get_server(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> ServerRead:
    server = await server_service.get_server(session, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    return _server_to_read(server, secret_manager)


@router.put("/{server_id}", response_model=ServerRead)
async def update_server(
    server_id: int,
    payload: ServerUpdate,
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> ServerRead:
    try:
        server = await server_service.update_server(session, server_id, payload, secret_manager)
        await session.commit()
        schedule_poll_job(server)  # Reschedule with updated interval
        return _server_to_read(server, secret_manager)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/{server_id}")
async def delete_server(
    server_id: int,
    response: Response,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> None:
    try:
        # Remove scheduled job before deleting server
        from app.services.scheduler import get_scheduler
        scheduler = get_scheduler()
        job_id = f"poll-server-{server_id}"
        try:
            scheduler.remove_job(job_id)
        except Exception:
            pass  # Job might not exist
        await server_service.delete_server(session, server_id)
        await session.commit()
        response.status_code = status.HTTP_204_NO_CONTENT
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{server_id}/test", status_code=status.HTTP_200_OK)
async def test_server_connection(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    secret_manager: SecretManager = Depends(get_secret_manager),
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    """Test IPMI connection to a server."""
    server = await server_service.get_server(session, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")

    try:
        client = IPMIClient(server, secret_manager)
        # Try to query temperatures as a connectivity test
        await client.query_temperatures()
        return {
            "status": "success",
            "message": f"Successfully connected to {server.name} at {server.bmc_host}:{server.bmc_port}"
        }
    except IPMICommandError as e:
        error_msg = str(e)
        if "Unable to establish" in error_msg or "Connection refused" in error_msg:
            return {
                "status": "error",
                "message": f"Connection failed: Unable to reach {server.bmc_host}:{server.bmc_port}. Check network connectivity and BMC settings."
            }
        elif "Invalid user name" in error_msg or "authentication" in error_msg.lower():
            return {
                "status": "error",
                "message": "Authentication failed: Invalid username or password. Please check your BMC credentials."
            }
        else:
            return {
                "status": "error",
                "message": f"Connection test failed: {error_msg}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Unexpected error: {str(e)}"
        }


@router.get("/{server_id}/alerts", response_model=list[ActiveAlertRead])
async def get_server_alerts(
    server_id: int,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ActiveAlertRead]:
    """Get all active alerts for a server."""
    server = await server_service.get_server(session, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    
    from sqlalchemy import select
    
    result = await session.execute(
        select(ActiveAlert)
        .where(
            ActiveAlert.server_id == server_id,
            ActiveAlert.cleared_at.is_(None),  # Only active (not cleared) alerts
        )
        .order_by(ActiveAlert.first_triggered_at.desc())
    )
    alerts = result.scalars().all()
    return [ActiveAlertRead.model_validate(alert) for alert in alerts]


@router.post("/{server_id}/alerts/{alert_type}/clear", status_code=status.HTTP_200_OK)
async def clear_server_alert(
    server_id: int,
    alert_type: str,
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict[str, str]:
    """Manually clear an active alert for a server."""
    server = await server_service.get_server(session, server_id)
    if not server:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Server not found")
    
    # Clear the alert
    await _clear_alert_if_active(session, server, alert_type, "manual")
    await session.commit()
    
    return {
        "status": "success",
        "message": f"Alert '{alert_type}' cleared for server {server.name}"
    }


@router.get("/alerts/all", response_model=list[ActiveAlertRead])
async def get_all_alerts(
    session: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[ActiveAlertRead]:
    """Get all active alerts across all servers."""
    from sqlalchemy import select
    
    result = await session.execute(
        select(ActiveAlert)
        .where(ActiveAlert.cleared_at.is_(None))  # Only active (not cleared) alerts
        .order_by(ActiveAlert.first_triggered_at.desc())
    )
    alerts = result.scalars().all()
    return [ActiveAlertRead.model_validate(alert) for alert in alerts]
