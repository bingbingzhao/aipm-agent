"""Database models — proper relational schema for AIPM Agent.

Replaces the ad-hoc JSON blob approach with normalized tables.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey, Integer, JSON,
    String, Text, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


# ═══ Constants ═══

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


class SlotState:
    EMPTY = "empty"
    PARTIAL = "partial"
    SATURATED = "saturated"


# ═══ Project ═══

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
    slots: Mapped[list["RequirementSlot"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    thinking_reports: Mapped[list["ThinkingReport"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    product_structures: Mapped[list["ProductStructure"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    prototypes: Mapped[list["Prototype"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    prds: Mapped[list["PRD"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    delivery_plans: Mapped[list["DeliveryPlan"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Project(id={self.id[:8]}, title={self.title}, stage={self.stage})>"


# ═══ Stage ①: Requirement Slots ═══

class RequirementSlot(Base):
    """Normalized requirement card — one row per slot per project."""
    __tablename__ = "requirement_slots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(50), nullable=False)       # e.g. "product_type"
    label: Mapped[str] = mapped_column(String(100), nullable=False)    # e.g. "产品类型"
    value: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(
        String(20), default=SlotState.EMPTY
    )
    priority: Mapped[str] = mapped_column(
        String(20), default="required"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="slots")

    def __repr__(self):
        return f"<Slot({self.key}:{self.state})>"


# ═══ Conversations ═══

class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="conversations")

    def __repr__(self):
        return f"<Conversation(role={self.role})>"


# ═══ Stage ②: Thinking Report ═══

class ThinkingReport(Base):
    """Product thinking analysis — one per project per version."""
    __tablename__ = "thinking_reports"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)    # Markdown report
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="thinking_reports")

    def __repr__(self):
        return f"<ThinkingReport(v{self.version})>"


# ═══ Stage ③: Product Structure ═══

class ProductStructure(Base):
    """Product architecture data — modules, routes, features, entities."""
    __tablename__ = "product_structures"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="product_structures")


# ═══ Stage ④: Prototype ═══

class Prototype(Base):
    """Generated HTML prototype with validation scores."""
    __tablename__ = "prototypes"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    html: Mapped[str] = mapped_column(Text, nullable=False)
    validation_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    validation_detail: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="prototypes")


# ═══ Stage ⑤: PRD ═══

class PRD(Base):
    """Product Requirements Document."""
    __tablename__ = "prds"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)     # Markdown
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="prds")


# ═══ Stage ⑥: Delivery Plan ═══

class DeliveryPlan(Base):
    """Delivery plan header with epics, stories, tasks, sprints."""
    __tablename__ = "delivery_plans"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        ForeignKey("projects.id"), nullable=False, index=True
    )
    # Summary
    total_weeks: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    team_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    total_story_points: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # Nested data (epics/stories/tasks/sprints) lives in related tables
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    project: Mapped["Project"] = relationship(back_populates="delivery_plans")
    epics: Mapped[list["DeliveryEpic"]] = relationship(
        back_populates="delivery_plan", cascade="all, delete-orphan"
    )
    sprints: Mapped[list["DeliverySprint"]] = relationship(
        back_populates="delivery_plan", cascade="all, delete-orphan"
    )


class DeliveryEpic(Base):
    __tablename__ = "delivery_epics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    delivery_plan_id: Mapped[str] = mapped_column(
        ForeignKey("delivery_plans.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    delivery_plan: Mapped["DeliveryPlan"] = relationship(back_populates="epics")
    stories: Mapped[list["DeliveryStory"]] = relationship(
        back_populates="epic", cascade="all, delete-orphan"
    )


class DeliveryStory(Base):
    __tablename__ = "delivery_stories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    epic_id: Mapped[str] = mapped_column(
        ForeignKey("delivery_epics.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    as_a: Mapped[str] = mapped_column(Text, default="")
    i_want: Mapped[str] = mapped_column(Text, default="")
    so_that: Mapped[str] = mapped_column(Text, default="")
    story_points: Mapped[int] = mapped_column(Integer, default=1)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    epic: Mapped["DeliveryEpic"] = relationship(back_populates="stories")
    tasks: Mapped[list["DeliveryTask"]] = relationship(
        back_populates="story", cascade="all, delete-orphan"
    )


class DeliveryTask(Base):
    __tablename__ = "delivery_tasks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    story_id: Mapped[str] = mapped_column(
        ForeignKey("delivery_stories.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="fullstack")
    estimate_hours: Mapped[float] = mapped_column(Float, default=0.0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    story: Mapped["DeliveryStory"] = relationship(back_populates="tasks")


class DeliverySprint(Base):
    __tablename__ = "delivery_sprints"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    delivery_plan_id: Mapped[str] = mapped_column(
        ForeignKey("delivery_plans.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, default="")
    duration_weeks: Mapped[int] = mapped_column(Integer, default=2)
    total_points: Mapped[int] = mapped_column(Integer, default=0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)

    delivery_plan: Mapped["DeliveryPlan"] = relationship(back_populates="sprints")
