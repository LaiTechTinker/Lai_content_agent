from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.db.database import init_db
from app.api.routes import router as router1
from app.api.content_review import router as router2
from app.api.publish import router as router3


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up application...")

    init_db()
   
    print("Application startup complete!")
    yield
    print("Shutting down application...")
    print("Shutdown complete")

app = FastAPI(title="Lai_agent", description="my personal content agent", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router1, prefix="/api")
app.include_router(router2, prefix="/api")
app.include_router(router3, prefix="/api")

app.get("/health")
def health_check():
    return {"status": "ok","message": "Lai_agent is running"}
