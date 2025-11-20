"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.middleware.https_redirect import HTTPSRedirectMiddleware
from app.services.scheduler import get_scheduler, start_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    start_scheduler()
    
    # Schedule jobs for all existing servers
    import logging
    from app.db.session import get_session
    from app.models.server import ServerTarget
    from app.services.scheduler import schedule_offline_check_job, schedule_poll_job
    from sqlalchemy import select
    
    logger = logging.getLogger(__name__)
    async with get_session() as session:
        result = await session.execute(select(ServerTarget))
        servers = result.scalars().all()
        for server in servers:
            schedule_poll_job(server)
        if servers:
            logger.info("Scheduled polling jobs for %d existing server(s)", len(servers))
    
    # Schedule offline check job
    schedule_offline_check_job()
    
    try:
        yield
    finally:
        scheduler = get_scheduler()
        if scheduler.running:
            scheduler.shutdown(wait=False)


app = FastAPI(title=settings.app_name, lifespan=lifespan)

# Add HTTPS redirect middleware first (before CORS)
# Only active when SSL is enabled
if settings.ssl_enabled:
    app.add_middleware(HTTPSRedirectMiddleware, https_port=8443)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

# Serve static files (frontend) if static directory exists
static_dir = Path(__file__).parent.parent.parent / "static"
if static_dir.exists() and static_dir.is_dir():
    # Mount static files at root, but API routes take precedence
    # The order matters: include_router before mount ensures API routes are checked first
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="static")
