"""Prototype Generation — Stage ④ 原型.

from __future__ import annotations

Generates interactive HTML/CSS prototypes from product structure.
"""

from app.core.llm import llm_chat

PROTOTYPE_SYSTEM_PROMPT = """你是一个高级前端开发工程师。根据产品需求描述，生成一个完整的、可交互的 HTML 原型页面。

要求：
1. 使用纯 HTML + CSS + 内联 JavaScript（单文件）
2. 设计风格现代、简洁、专业
3. 包含导航、主要内容区、基本的交互元素
4. 响应式设计（适配桌面和移动端）
5. 不要使用外部 CDN 资源，所有样式内联
6. 不要包含不符合实际功能的假数据表单
7. 重点展示核心页面的布局和信息架构

输出格式：
- 直接输出完整的 HTML 文件内容
- 在 HTML 注释中标注每个区域的功能说明
"""


class PrototypeGenerator:
    """Generates interactive HTML prototypes."""

    async def generate(self, product_description: str) -> str:
        """Generate a prototype HTML page."""

        messages = [
            {"role": "system", "content": PROTOTYPE_SYSTEM_PROMPT},
            {"role": "user", "content": f"请为以下产品生成原型页面：\n\n{product_description}\n\n输出完整 HTML。"}
        ]

        return await llm_chat(messages, temperature=0.4)

    async def iterate(self, current_html: str, feedback: str) -> str:
        """Iterate on existing prototype based on feedback."""

        messages = [
            {"role": "system", "content": PROTOTYPE_SYSTEM_PROMPT},
            {"role": "user", "content": f"当前原型 HTML：\n\n{current_html}\n\n请根据以下反馈修改：\n{feedback}\n\n输出完整 HTML。"}
        ]

        return await llm_chat(messages, temperature=0.5)
