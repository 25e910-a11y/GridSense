import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.database import Base, engine
from app.models import (
    College,
    Block,
    Floor,
    Device,
    Telemetry,
    Relay,
    Fault,
    User,
    Notification,
    WorkOrder,
    WorkAttempt,
    AuditLog,
)
from app.api.auth import router as auth_router
from app.api.telemetry import router as telemetry_router
from app.api.locations import router as locations_router
from app.api.devices import router as devices_router
from app.api.relays import router as relays_router
from app.api.faults import router as faults_router
from app.api.dashboard import router as dashboard_router
from app.api.maintenance import router as maintenance_router
from app.api.notifications import router as notifications_router
from app.api.audit import router as audit_router

logger = logging.getLogger("app.main")

is_production = settings.ENVIRONMENT.lower() in {"production", "prod", "staging"}

app = FastAPI(
    title="IoT-Based Power Monitoring and Fault Identification System",
    description="Backend API for IoT-Based Power Monitoring and Fault Identification System",
    version="1.0.0",
    docs_url=None if is_production else "/docs",
    redoc_url=None if is_production else "/redoc",
    openapi_url=None if is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

try:
    from app.db.database import SessionLocal
    from app.core.security import ensure_initial_admin

    with SessionLocal() as _init_db:
        ensure_initial_admin(_init_db)
except ValueError as exc:
    logger.error("Administrator provisioning configuration error: %s", exc)
    raise RuntimeError(f"Application startup halted: {exc}") from exc
except Exception as exc:
    logger.warning("Could not complete administrator verification at startup: %s", exc)

app.include_router(auth_router)
app.include_router(telemetry_router)
app.include_router(locations_router)
app.include_router(devices_router)
app.include_router(relays_router)
app.include_router(faults_router)
app.include_router(dashboard_router)
app.include_router(maintenance_router)
app.include_router(notifications_router)
app.include_router(audit_router)


@app.get("/")
def root():
    return {
        "system": "IoT-Based Power Monitoring and Fault Identification System",
        "status": "online",
    }


@app.get("/health")
def health():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "database": "connected",
        }

    except Exception as exc:
        logger.error("Health check failure: %s", exc)
        return {
            "status": "unhealthy",
            "database": "disconnected",
        }
