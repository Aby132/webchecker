"""FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import dashboard, logs, projects, settings, websites
from app.config import get_settings
from app.services import create_services, get_services

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("webmonitor")


@asynccontextmanager
async def lifespan(app: FastAPI):
    cfg = get_settings()
    logger.info("Data directory: %s", cfg.data_path)
    services = create_services()
    await services.scheduler.start()
    logger.info("Web Monitor started")
    yield
    await services.scheduler.stop()
    logger.info("Web Monitor shut down")


app = FastAPI(
    title="Web Monitor",
    description="Self-hosted website uptime monitoring (filesystem storage, no database)",
    version="1.0.0",
    lifespan=lifespan,
)

cfg = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(websites.router)
app.include_router(dashboard.router)
app.include_router(logs.router)
app.include_router(settings.router)


@app.get("/")
def root():
    state = get_services().state.read()
    return {
        "name": "Web Monitor",
        "version": "1.0.0",
        "storage": "filesystem",
        "engine_running": bool(state.get("engine_running")),
    }
