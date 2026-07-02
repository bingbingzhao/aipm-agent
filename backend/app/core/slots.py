from __future__ import annotations

"""Slot system for the inquiry engine.

Each slot represents a piece of information the engine needs to collect.
Slots have priority (required/important/conditional) and saturation state.
"""

from dataclasses import dataclass, field
from enum import Enum


class SlotPriority(Enum):
    REQUIRED = "required"
    IMPORTANT = "important"
    CONDITIONAL = "conditional"


class SlotState(Enum):
    EMPTY = "empty"
    PARTIAL = "partial"
    SATURATED = "saturated"


@dataclass
class Slot:
    key: str
    label: str
    priority: SlotPriority
    state: SlotState = SlotState.EMPTY
    value: str = ""
    hints: list[str] = field(default_factory=list)
    trigger_condition: str | None = None  # For CONDITIONAL slots


# Default slot definitions
REQUIREMENT_SLOTS: list[Slot] = [
    Slot(key="product_type", label="产品类型", priority=SlotPriority.REQUIRED,
         hints=["这是什么类型的产品？SaaS、工具、内容平台还是别的？"]),
    Slot(key="target_user", label="核心用户", priority=SlotPriority.REQUIRED,
         hints=["谁会使用这个产品？他们的典型特征是什么？"]),
    Slot(key="core_problem", label="核心问题", priority=SlotPriority.REQUIRED,
         hints=["产品要解决什么核心问题？用户现在的方案有什么痛点？"]),
    Slot(key="existing_solutions", label="现有解决方案", priority=SlotPriority.REQUIRED,
         hints=["用户现在怎么解决这个问题的？竞品有哪些？"]),
    Slot(key="unique_value", label="差异化价值", priority=SlotPriority.IMPORTANT,
         hints=["你的方案与现有方案的核心差异是什么？"]),
    Slot(key="monetization", label="商业模式", priority=SlotPriority.IMPORTANT,
         hints=["考虑过如何盈利吗？目标定价策略？"]),
    Slot(key="technical_constraints", label="技术约束", priority=SlotPriority.CONDITIONAL,
         hints=["有没有特别的技术要求或限制？"],
         trigger_condition="产品有特殊技术要求"),
    Slot(key="regulatory_concerns", label="合规要求", priority=SlotPriority.CONDITIONAL,
         hints=["涉及用户数据、金融、医疗等合规场景吗？"],
         trigger_condition="涉及敏感行业或数据"),
]


class SlotManager:
    """Manages slot filling and saturation evaluation."""

    def __init__(self, slots: list[Slot] | None = None):
        self.slots = {s.key: s for s in (slots or REQUIREMENT_SLOTS)}

    def get_unsatisfied_required(self) -> list[Slot]:
        """Return REQUIRED slots that are not SATURATED."""
        return [
            s for s in self.slots.values()
            if s.priority == SlotPriority.REQUIRED and s.state != SlotState.SATURATED
        ]

    def get_next_to_ask(self) -> Slot | None:
        """Pick the next slot to inquire about.
        
        Priority order: REQUIRED → IMPORTANT → CONDITIONAL
        Within same priority: EMPTY before PARTIAL
        """
        for priority in [SlotPriority.REQUIRED, SlotPriority.IMPORTANT, SlotPriority.CONDITIONAL]:
            candidates = [
                s for s in self.slots.values()
                if s.priority == priority and s.state != SlotState.SATURATED
            ]
            # EMPTY before PARTIAL
            candidates.sort(key=lambda s: 0 if s.state == SlotState.EMPTY else 1)
            if candidates:
                return candidates[0]
        return None

    def update_slot(self, key: str, value: str, state: SlotState):
        if key in self.slots:
            self.slots[key].value = value
            self.slots[key].state = state

    @property
    def saturated(self) -> bool:
        """All REQUIRED slots are saturated."""
        return len(self.get_unsatisfied_required()) == 0

    @property
    def fully_saturated(self) -> bool:
        """All slots are saturated."""
        return all(s.state == SlotState.SATURATED for s in self.slots.values())

    @property
    def requirement_card(self) -> dict:
        """Export current state as a structured requirement card."""
        return {
            s.key: {
                "label": s.label,
                "value": s.value,
                "state": s.state.value,
            }
            for s in self.slots.values()
        }
