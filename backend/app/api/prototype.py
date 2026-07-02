"""Prototype generation and validation API."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.project import ChatRequest
from app.services.prototype import PrototypeGenerator
from app.services.prototype_validator import PrototypeValidator

router = APIRouter(prefix="/api/prototype", tags=["prototype"])


class PrototypeGenerateRequest(BaseModel):
    description: str = Field(..., min_length=1, description="产品描述")


class PrototypeIterateRequest(BaseModel):
    current_html: str = Field(..., alias="currentHtml", min_length=1)
    feedback: str = Field(..., min_length=1)

    model_config = {"populate_by_name": True}


class PrototypeValidateRequest(BaseModel):
    html: str = Field(..., min_length=1)


generator = PrototypeGenerator()
validator = PrototypeValidator()


@router.post("/generate")
async def generate_prototype(request: PrototypeGenerateRequest) -> dict:
    """Generate an HTML prototype from a product description."""
    html = await generator.generate(request.description)
    report = validator.validate(html)

    return {
        "html": html,
        "validation": report.to_dict(),
    }


@router.post("/iterate")
async def iterate_prototype(request: PrototypeIterateRequest) -> dict:
    """Iterate on an existing prototype based on feedback."""
    html = await generator.iterate(request.current_html, request.feedback)
    report = validator.validate(html)

    return {
        "html": html,
        "validation": report.to_dict(),
    }


@router.post("/validate")
async def validate_prototype(request: PrototypeValidateRequest) -> dict:
    """Validate an HTML prototype and return a report."""
    report = validator.validate(request.html)
    return report.to_dict()
