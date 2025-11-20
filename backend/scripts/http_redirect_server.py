#!/usr/bin/env python3
"""Simple HTTP server that redirects all requests to HTTPS."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, Request
from starlette.responses import RedirectResponse
from uvicorn import run

app = FastAPI(title="Zephyr IPMI HTTP Redirect")


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def redirect_to_https(request: Request, path: str = ""):
    """Redirect all HTTP requests to HTTPS."""
    https_port = 8443
    host = request.headers.get("Host", "localhost").split(":")[0]
    
    # Build HTTPS URL
    https_url = f"https://{host}:{https_port}{request.url.path}"
    if request.url.query:
        https_url += f"?{request.url.query}"
    
    return RedirectResponse(url=https_url, status_code=301)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run(app, host="0.0.0.0", port=port, log_level="info")

