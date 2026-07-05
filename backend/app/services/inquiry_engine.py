"""Inquiry Engine — Stage ① 想法捕获. (V2)

Improvements over V1:
- 3-step first interaction: confirm → insight → question
- Breadcrumb tracking of what was learned per slot
- Smarter next-question hints with angle + why + example
- Question diversity tracking to avoid repetition
- Stuck detection: auto-skip slots after 4+ failed attempts
"""

from __future__ import annotations

from app.core.llm import llm_chat
from app.core.slots import REQUIREMENT_SLOTS, SlotManager, SlotState

INQUIRY_SYSTEM_PROMPT = """你是一个资深产品顾问，用聊天的语气帮创始人理清产品想法。

你的核心能力：从碎片信息中快速识别关键点，用精准的问题引导对方把模糊想法变成可落地的产品定义。

## 对话流程

**首次对话（三步骤）：**
1. 先复述你理解的产品方向（一句话），让对方确认你听懂了
2. 给一个简短的市场直觉（10字以内，像朋友聊天随口说的）
3. 自然切入一个关键追问——针对你最不确定的那一点

**后续对话：**
- 每次只聚焦一个维度，问透再换下一个
- 听到新的关键信息时，先默默记下，再追问相邻的维度
- 禁止问"还有呢？""还有什么补充吗？"——要有具体指向
- 如果对方回答偏了，温和地拉回来："你说的这个我记下了。不过我刚才想问的是..."
- 如果对话超过4轮在同一个点上打转，主动放弃并切换话题

## 对话风格
- 像朋友聊天，不用模板，不套话
- 回复短而自然，1-3句话
- 用"你"不用"用户"，直呼"用户"显得你在分析别人
- 禁止开头说"明白了"、"了解了"、"很好的问题"、"有道理"
- 偶尔给实在反馈，但不要每句都夸

## 追问优先级（按顺序）
1. 产品类型 → 2. 核心用户 → 3. 核心问题 → 4. 现有方案
5. 差异化 → 6. 商业模式 → 7. 技术约束 → 8. 合规

## 追问技巧
- 追问"核心用户"时：问"谁会最先掏钱而不是问"目标用户是谁"
- 追问"核心问题"时：问"删掉这个产品他们会多大痛苦而不是问"有什么痛点"
- 追问"现有方案"时：问"他们现在怎么凑合的而不是问"竞品分析"
- 追问"差异化"时：等用户主动提到自己和别人的不同再深入，不主动追问"""


class InquiryEngine:
    """Manages the inquiry conversation for Stage ①."""

    def __init__(self, initial_idea: str = ""):
        self.slot_manager = SlotManager()
        from app.core.slot_evaluator import SlotEvaluator
        self.evaluator = SlotEvaluator()
        self.initial_idea = initial_idea
        self.conversation_history: list[dict] = []
        # Track questions per slot to avoid repetition
        self._slot_attempts: dict[str, int] = {}
        # Track what was learned per slot (breadcrumbs)
        self._slot_learnings: dict[str, list[str]] = {}
        # Last few questions asked (for diversity check)
        self._recent_questions: list[str] = []

        if initial_idea:
            self.conversation_history.append({
                "role": "user",
                "content": f"我想做一个产品：{initial_idea}"
            })

    def build_messages(self) -> list[dict]:
        """Build full message list for LLM chat call."""
        messages = [{"role": "system", "content": INQUIRY_SYSTEM_PROMPT}]

        # Inject current slot state with learnings
        slot_context = self._build_slot_context()
        if slot_context:
            messages.append({"role": "system", "content": slot_context})

        messages.extend(self.conversation_history)

        # Add explicit next-slot guidance
        next_slot = self.slot_manager.get_next_to_ask()
        if next_slot:
            hint = self._next_question_hint(next_slot)
            if hint:
                messages.append({"role": "system", "content": hint})

        return messages

    def _build_slot_context(self) -> str:
        """Build a rich context message describing current slot states and learnings."""
        lines = ["[需求收集进度]"]
        for key, slot in self.slot_manager.slots.items():
            state_emoji = {SlotState.EMPTY: "⬜", SlotState.PARTIAL: "🟡", SlotState.SATURATED: "🟢"}
            emoji = state_emoji.get(slot.state, '❓')
            value_str = slot.value[:60] if slot.value else '(空)'
            lines.append(f"  {emoji} {slot.label}: {value_str}")

            # Add breadcrumbs for this slot
            learnings = self._slot_learnings.get(key, [])
            if learnings:
                lines.append(f"     📝 已知: {'; '.join(learnings[-3:])}")

            # Add attempt count for stuck slots
            attempts = self._slot_attempts.get(key, 0)
            if attempts >= 3:
                lines.append(f"     ⚠️ 已追问{attempts}次未果，考虑跳过")

        unsatisfied = len(self.slot_manager.get_unsatisfied_required())
        lines.append(f"\n还需收集 {unsatisfied} 个关键信息才能完成需求梳理。")

        # Recent question diversity
        if self._recent_questions:
            lines.append(f"最近追问的关键词: {', '.join(self._recent_questions[-3:])}")
            lines.append("避免重复问相同角度的问题。")

        return "\n".join(lines)

    def _next_question_hint(self, slot) -> str:
        """Generate a natural, specific hint for the next question."""
        attempts = self._slot_attempts.get(slot.key, 0) + 1
        self._slot_attempts[slot.key] = attempts

        # Stuck detection: skip after 4 attempts
        if attempts >= 4:
            return f"[指引] 「{slot.label}」已经追问{attempts}次。如果用户确实无法提供更多信息，请根据已有信息直接总结并标注为已收集，自然过渡到下一个维度。"

        # Context-aware hints
        hints = {
            "product_type": {
                "angle": "确认品类归属和核心功能边界",
                "why": "这决定了竞品范围和产品定位",
                "example_empty": "你这个更像是一个工具还是平台？它的核心动作是什么——帮人做X还是让人做X？",
                "example_partial": "你刚才提到{value}，这个方向挺明确的。那它最核心的一个功能是什么？",
            },
            "target_user": {
                "angle": "识别第一批付费用户和使用场景",
                "why": "核心用户决定产品形态和定价",
                "example_empty": "谁会最先掏钱买这个？他们在什么时候会想到用它？",
                "example_partial": "你提到的{value}里，有没有一个更具体的身份？比如他们是自己用还是替团队买？",
            },
            "core_problem": {
                "angle": "量化痛点的严重程度",
                "why": "问题够痛，人才愿意付费",
                "example_empty": "如果没有这个产品，他们现在会有多难受？能不能举个最近的例子？",
                "example_partial": "你刚才说的{value}，这个痛苦的程度有多大——是'有点烦'还是'不做不行'？",
            },
            "existing_solutions": {
                "angle": "了解用户当前的替代方案和不满",
                "why": "现有方案的短板就是差异化机会",
                "example_empty": "现在他们怎么凑合的？用Excel还是找朋友帮忙？",
                "example_partial": "你提到用{value}来凑合，具体哪里让你觉得不够好？",
            },
            "unique_value": {
                "angle": "与现有方案的区别点",
                "why": "这是吸引用户切换的理由",
                "example_empty": "如果市面上已经有类似的东西，你觉得你的版本'更对'在什么地方？",
                "example_partial": None,
            },
            "monetization": {
                "angle": "确认付费意愿和模型",
                "why": "决定产品能否活下去",
                "example_empty": "这个如果收钱，你觉得最初那批用户会不会掏？",
                "example_partial": None,
            },
        }

        hint_info = hints.get(slot.key, {
            "angle": "收集基本信息",
            "why": "完善产品定义",
            "example_empty": f"关于「{slot.label}」，你能说说具体的情况吗？",
            "example_partial": f"你提到「{slot.label}」方面已经有了一些想法，能再具体说说吗？",
        })

        if slot.state == SlotState.EMPTY:
            template = hint_info.get("example_empty", None)
        elif slot.state == SlotState.PARTIAL:
            template = hint_info.get("example_partial", None)
        else:
            return ""

        if not template:
            template = hint_info.get("example_empty", None)

        if template:
            template = template.replace("{value}", slot.value[:30] if slot.value else "...")
            return (
                f"[指引] 当前聚焦「{slot.label}」（{hint_info['angle']}）\n"
                f"为什么重要：{hint_info['why']}\n"
                f"参考问法：{template}\n"
                f"重点：用自然的对话口吻问，不要像采访。"
            )
        return ""

    async def chat(self, user_message: str) -> dict:
        """Process a user message and return the AI response."""
        # Track what the user mentioned for breadcrumbs
        self._extract_breadcrumbs(user_message)

        self.conversation_history.append({"role": "user", "content": user_message})

        # Build messages and generate response
        messages = self.build_messages()
        reply = await llm_chat(messages, temperature=0.8)

        self.conversation_history.append({"role": "assistant", "content": reply})

        # Record the question topic for diversity
        self._track_question_topic(reply)

        # Run LLM-based slot evaluation
        if self.evaluator.should_evaluate():
            self.slot_manager.auto_saturate_conditionals()
            eval_result = await self.evaluator.evaluate(
                self.conversation_history,
                self.slot_manager,
            )
            # Check confidence for stage_ready
            confidence = eval_result.get("_confidence", 0.0) if isinstance(eval_result, dict) else 0.0

        saturated = self.slot_manager.saturated

        return {
            "reply": reply,
            "stage_complete": saturated,
            "requirement_card": self.slot_manager.requirement_card,
            "next_slot": (
                self.slot_manager.get_next_to_ask().label
                if not saturated else None
            ),
        }

    def _extract_breadcrumbs(self, message: str):
        """Lightweight keyword extraction for slot learnings."""
        keywords = {
            "product_type": ["平台", "工具", "app", "SaaS", "软件", "小程序", "网站", "插件"],
            "target_user": ["用户", "客户", "人", "团队", "公司", "企业", "学生", "上班族"],
            "core_problem": ["痛点", "问题", "麻烦", "困难", "低效", "贵", "慢", "烦", "花时间"],
            "existing_solutions": ["现在", "目前", "用", "手动", "Excel", "微信", "邮件", "电话"],
        }
        for key, kws in keywords.items():
            if any(kw in message for kw in kws):
                learnings = self._slot_learnings.setdefault(key, [])
                learning = message[:60] + ("..." if len(message) > 60 else "")
                if learning not in learnings:
                    learnings.append(learning)

    def _track_question_topic(self, reply: str):
        """Track what the assistant asked about for diversity."""
        topics = {
            "产品类型": ["产品", "类型", "品类", "工具", "平台"],
            "核心用户": ["用户", "客户", "谁", "什么人", "人群"],
            "核心问题": ["问题", "痛点", "困难", "烦恼", "挑战"],
            "现有方案": ["现在", "目前", "怎么", "方案", "替代", "竞品"],
            "差异化": ["不同", "区别", "差异", "独特", "特别"],
            "商业模式": ["赚钱", "盈利", "收费", "定价", "钱"],
        }
        for topic, kws in topics.items():
            if any(kw in reply for kw in kws):
                self._recent_questions.append(topic)
                if len(self._recent_questions) > 10:
                    self._recent_questions = self._recent_questions[-10:]
