"""Project ORM model."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class ProjectStage:
    IDEA = "idea"
    THINKING = "thinking"
    STRUCTURE = "structure"
    PROTOTYPE = "prototype"
    PRD = "prd"
    DELIVERY = "delivery"


class ProjectStatus:
    ACTIVE = "active"
    ARCHIVED = "archived"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    stage: Mapped[str] = mapped_column(
        String(20), default=ProjectStage.IDEA
    )
    status: Mapped[str] = mapped_column(
        String(20), default=ProjectStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relations
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    requirement_card: Mapped[Optional[dict]] = mapped_column(
        JSON, name="requirement_card", nullable=True, default=None
    )
    # Stores outputs from each stage:
    # { idea: {requirement_card}, thinking: {report}, prototype: {html, validation} }
    stage_outputs: Mapped[Optional[dict]] = mapped_column(
        JSON, name="stage_outputs", nullable=True, default=None
    )

    def __repr__(self):
        return f"<Project(id={self.id}, title={self.title}, stage={self.stage})>"


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[Optional[dict]] = mapped_column(
        JSON, name="metadata", nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    # Relations
    project: Mapped["Project"] = relationship(back_populates="conversations")

    def __repr__(self):
        return f"<Conversation(id={self.id}, role={self.role})>"
