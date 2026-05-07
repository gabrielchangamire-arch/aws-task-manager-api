import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import init_db
from app.logging_config import configure_logging
from app.routers import health, tasks

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    log.info("api.started env=%s", settings.app_env)
    yield
    log.info("api.stopped")


app = FastAPI(
    title="AWS Task Manager API",
    description="Simple task manager backed by SQLAlchemy with optional S3 attachments.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health.router)
app.include_router(tasks.router)


@app.exception_handler(RequestValidationError)
async def validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.exception_handler(Exception)
async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    log.exception("unhandled error: %s", exc)
    return JSONResponse(status_code=500, content={"detail": "internal server error"})
