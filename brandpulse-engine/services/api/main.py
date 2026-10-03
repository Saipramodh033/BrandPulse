"""
BrandPulse FastAPI Application
================================
RESTful API backend for the BrandPulse intelligence engine.

Phase 2.5: Minimal shell — covers company CRUD and idea management.
WebSocket endpoints are added in Phase 7 (with React frontend).
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from services.api.routers import companies, ideas, websockets, dashboard
import asyncio
import json
import redis.asyncio as redis
import os
import logging

# Initialize Celery app to configure the default broker (Redis) for any dispatched tasks
import services.worker.celery_app

logger = logging.getLogger(__name__)

app = FastAPI(
    title="BrandPulse API",
    description="Content ideation engine API for BrandPulse",
    version="0.2.5",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Streamlit and future React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Optional API key authentication middleware
# Set API_KEY in the environment to enforce authentication. Leave empty/unset for open development mode.
API_KEY = os.getenv("API_KEY", "")

@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Require API key if API_KEY env var is set."""
    if API_KEY:  # Auth only active when API_KEY is configured
        # Allow health check and docs without auth
        if request.url.path not in ("/health", "/docs", "/redoc", "/openapi.json"):
            key = request.headers.get("X-API-Key", "")
            if key != API_KEY:
                return JSONResponse(status_code=401, content={"detail": "Invalid or missing API key"})
    return await call_next(request)

# Include routers
app.include_router(companies.router, prefix="/api")
app.include_router(ideas.router, prefix="/api")
app.include_router(websockets.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api/dashboard")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

async def redis_listener():
    """
    Background subscriber task: Listens to Redis pub/sub pattern 'trace:*' and
    broadcasts live agent trace events to connected WebSocket clients per company.
    Includes an outer loop with automatic backoff reconnection on Redis connection loss.
    """
    while True:  # Outer reconnect loop
        try:
            redis_client = redis.from_url(REDIS_URL)
            async with redis_client.pubsub() as pubsub:
                await pubsub.psubscribe("trace:*")
                logger.info("📡 Subscribed to Redis channel pattern: trace:*")
                
                while True:
                    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                    if message is not None:
                        if message["type"] == "pmessage":
                            channel = message["channel"].decode("utf-8")
                            company_id_str = channel.split(":")[-1]
                            try:
                                company_id = int(company_id_str)
                                data = json.loads(message["data"].decode("utf-8"))
                                await websockets.manager.broadcast(company_id, data)
                            except Exception as e:
                                logger.error(f"Error processing redis message: {e}")
                    await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(f"Redis listener failed: {e}. Reconnecting in 5s...")
            await asyncio.sleep(5)

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.5"}
