"""API router aggregator."""
from fastapi import APIRouter

from app.api.routes import auth, notifications, servers

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router)
api_router.include_router(servers.router)
api_router.include_router(notifications.router)

__all__ = ["api_router"]
