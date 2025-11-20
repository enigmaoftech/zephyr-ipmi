"""Middleware to redirect HTTP requests to HTTPS."""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse

from app.core.config import get_settings


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect HTTP requests to HTTPS when SSL is enabled."""

    def __init__(self, app, https_port: int = 8443):
        super().__init__(app)
        self.https_port = https_port
        self.settings = get_settings()

    async def dispatch(self, request: Request, call_next):
        # Only redirect if SSL is enabled
        if not self.settings.ssl_enabled:
            return await call_next(request)

        # Check if request is HTTP (not HTTPS)
        # Check X-Forwarded-Proto header (from reverse proxy) or scheme
        scheme = request.headers.get("X-Forwarded-Proto", request.url.scheme)
        
        if scheme == "http":
            # Build HTTPS URL
            host = request.headers.get("X-Forwarded-Host", request.headers.get("Host", "localhost"))
            # Remove port if present
            host = host.split(":")[0]
            
            # Construct HTTPS URL with port
            https_url = f"https://{host}:{self.https_port}{request.url.path}"
            if request.url.query:
                https_url += f"?{request.url.query}"
            
            return RedirectResponse(url=https_url, status_code=301)

        return await call_next(request)

