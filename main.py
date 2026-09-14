import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.database import init_db
from app.api.routes import router as router1
from app.api.content_review import router as router2
from app.api.publish import router as router3
from app.api.auth import router as auth_router
from app.api.workflow import router as workflow_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("lai_agent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting %s in %s environment", settings.app_name, settings.environment)

    init_db()
   
    logger.info("Application startup complete")
    yield
    logger.info("Shutting down application")

app = FastAPI(title=settings.app_name, description="my personal content agent", version="1.0.0", lifespan=lifespan, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)

app.include_router(router1, prefix="/api")
app.include_router(router2, prefix="/api")
app.include_router(router3, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(workflow_router, prefix="/api")

app.get("/health")
def health_check():
    return {"status": "ok","message": "Lai_agent is running"}
