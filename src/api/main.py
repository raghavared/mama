"""FastAPI application factory."""
from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from typing import Set

import structlog
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from prometheus_client import make_asgi_app

from src.config import get_settings
from src.utils.logging import configure_logging
from src.database import Base, engine, AsyncSessionLocal
from .routers import jobs, health, auth, dashboard, schedule, config, users
from .routers.auth import _decode_token, seed_admin

logger = structlog.get_logger(__name__)


# ─── WebSocket connection manager ────────────────────────────────────────────

class ConnectionManager:
    def __init__(self):
        self.active: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active.discard(websocket)

    async def broadcast(self, message: dict):
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.discard(ws)


ws_manager = ConnectionManager()


# ─── Startup / Shutdown ──────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create DB tables and seed admin on startup."""
    configure_logging()
    logger.info("Creating database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ready")

    # Seed admin user
    async with AsyncSessionLocal() as session:
        await seed_admin(session)

    yield

    await engine.dispose()
    logger.info("Database engine disposed")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MAMA — Marketing Agent Multi-Agent Architecture",
        description="AI-powered marketing content generation and publishing pipeline",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else [],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Prometheus metrics endpoint
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

    # Static media file serving
    try:
        os.makedirs("./media_assets", exist_ok=True)
        app.mount("/media", StaticFiles(directory="./media_assets"), name="media")
    except Exception as e:
        logger.warning("Could not mount media_assets static directory", error=str(e))

    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
    app.include_router(schedule.router, prefix="/api/v1", tags=["schedule"])
    app.include_router(config.router, prefix="/api/v1", tags=["config"])
    app.include_router(users.router, prefix="/api/v1", tags=["users"])

    # ─── WebSocket endpoint ──────────────────────────────────────────────

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket, token: str = Query("")):
        # Validate JWT token (self-validating, no DB lookup needed)
        user_id = _decode_token(token)
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return

        await ws_manager.connect(websocket)
        try:
            await websocket.send_text(json.dumps({
                "type": "connected",
                "payload": {"user_id": user_id},
                "timestamp": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc
                ).isoformat(),
            }))
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "payload": {},
                            "timestamp": __import__("datetime").datetime.now(
                                __import__("datetime").timezone.utc
                            ).isoformat(),
                        }))
                except json.JSONDecodeError:
                    pass
        except WebSocketDisconnect:
            ws_manager.disconnect(websocket)

    return app
