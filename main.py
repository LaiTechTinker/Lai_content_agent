from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.db.database import init_db
from contextlib import asynccontextmanager
from app.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up application...")

    await init_db()
   
    print("Application startup complete!")
    yield
    print("Shutting down application...")
    print("Shutdown complete")

app=FastAPI(title="Lai_agent", description="my personal content agent", version="1.0.0" )

app.include_router(router, prefix="/api")
app.get("/health")
def health_check():
    return {"status": "ok","message": "Lai_agent is running"}
