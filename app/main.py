from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.core.database import SessionLocal, engine
from app.core.observability import configure_logging, get_logger
from app.core.observability.middleware import CorrelationIdMiddleware
from app.core.startup_validation import validate_database_consistency, validate_environment

logger = get_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.log_level)
    env = validate_environment()
    if not env.ok:
        logger.error("application_startup_failed", extra={"errors": env.errors})
    async with SessionLocal() as db:
        db_report = await validate_database_consistency(db)
        if db_report.warnings:
            logger.warning("startup_db_warnings", extra={"warnings": db_report.warnings})
    logger.info("application_starting", extra={"maintenance_mode": settings.maintenance_mode})
    yield
    logger.info("application_shutting_down")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
async def readiness_check() -> dict[str, str]:
    async with SessionLocal() as db:
        await db.execute(text("SELECT 1"))
    return {"status": "ready"}
