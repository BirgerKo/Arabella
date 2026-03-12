"""FastAPI application factory.

Wires together the routers, WebSocket endpoint, static file serving,
and application lifecycle (startup / shutdown).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from webdashboard.backend.dependencies import get_hub, init_singletons
from webdashboard.backend.routers import commands, devices, scenarios

log = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_singletons()
    log.info("Webdashboard started")
    yield
    log.info("Webdashboard shutting down")


app = FastAPI(title="Arabella Web Dashboard", lifespan=lifespan)

# Allow the Vite dev server (port 5173) to reach the API during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(devices.router)
app.include_router(commands.router)
app.include_router(scenarios.router)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    hub = get_hub()
    await hub.connect(websocket)
    try:
        while True:
            # Keep the connection alive; the server is the sole sender
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(websocket)


# Serve the built React app in production; otherwise show a dev-mode hint
if _STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_STATIC_DIR), html=True), name="static")
else:
    from fastapi.responses import HTMLResponse

    @app.get("/", response_class=HTMLResponse, include_in_schema=False)
    async def dev_hint():
        return """<!doctype html>
<html><head><title>Arabella — dev mode</title>
<style>body{font-family:monospace;background:#1e1e2e;color:#f8f8f2;padding:40px}
code{background:#313145;padding:2px 6px;border-radius:4px}
pre{background:#313145;padding:16px;border-radius:8px;line-height:1.6}</style>
</head><body>
<h2>Frontend not built yet</h2>
<p>Choose one of:</p>
<h3>Option A — Dev mode (hot reload)</h3>
<pre>cd webdashboard/frontend
npm install
npm run dev        # opens http://localhost:5173</pre>
<h3>Option B — Production build</h3>
<pre>cd webdashboard/frontend
npm install
npm run build      # then refresh this page</pre>
</body></html>"""
