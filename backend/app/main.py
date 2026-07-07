"""FastAPI application entry point."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.api.ws import router as ws_router
from app.config import settings
from app.core.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast on unsafe production config
    settings.validate_production()
    await init_db()
    yield


app = FastAPI(
    title="AIPM Agent",
    description="AI Product Manager Agent — From idea to PRD",
    version="0.1.0",
    lifespan=lifespan,
    # Disable interactive API docs in production
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router)
app.include_router(ws_router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}
