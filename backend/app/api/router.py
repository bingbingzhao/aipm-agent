"""API router aggregation."""

from fastapi import APIRouter

from app.api.projects import router as projects_router
from app.api.conversations import router as conversations_router
from app.api.aat_export import router as aat_router
from app.api.prototype import router as prototype_router
from app.api.pipeline import router as pipeline_router

api_router = APIRouter()
api_router.include_router(projects_router)
api_router.include_router(conversations_router)
api_router.include_router(aat_router)
api_router.include_router(prototype_router)
api_router.include_router(pipeline_router)
