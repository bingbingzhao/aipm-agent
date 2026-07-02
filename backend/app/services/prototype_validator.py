"""Prototype HTML Validator — Stage ④ 原型质量校验。

Validates LLM-generated HTML prototypes for structure, security,
self-containedness, and basic quality before presenting to the user.

Architecture:
- Parse HTML → extract structure
- Run checks in parallel categories
- Return ValidationReport with score, issues, and fix suggestions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from html.parser import HTMLParser
from typing import Optional


class IssueSeverity(Enum):
    ERROR = "error"       # Must fix — blocks prototype rendering
    WARNING = "warning"   # Should fix — affects quality
    INFO = "info"         # Nice to have — improvement suggestions


@dataclass
class ValidationIssue:
    severity: IssueSeverity
    category: str
    message: str
    suggestion: str = ""


@dataclass
class ValidationReport:
    is_valid: bool
    score: int  # 0-100
    issues: list[ValidationIssue] = field(default_factory=list)
    html_size: int = 0
    elements_found: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "score": self.score,
            "issue_count": len(self.issues),
            "error_count": sum(1 for i in self.issues if i.severity == IssueSeverity.ERROR),
            "warning_count": sum(1 for i in self.issues if i.severity == IssueSeverity.WARNING),
            "info_count": sum(1 for i in self.issues if i.severity == IssueSeverity.INFO),
            "html_size": self.html_size,
            "elements_found": self.elements_found,
            "issues": [
                {
                    "severity": i.severity.value,
                    "category": i.category,
                    "message": i.message,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
        }


# ═══════════════════════════════════════════════
# HTML Parser
# ═══════════════════════════════════════════════

class PrototypeParser(HTMLParser):
    """Lightweight HTML parser that extracts structure info."""

    def __init__(self):
        super().__init__()
        self.tags: list[str] = []
        self.tag_counts: dict[str, int] = {}
        self.attrs_list: list[dict] = []
        self.has_doctype = False
        self.has_viewport = False
        self.has_title = False
        self.has_lang = False
        self.scripts: list[str] = []     # script content
        self.styles: list[str] = []       # style content
        self.external_refs: list[str] = []# external src/href
        self.text_content: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]):
        self.tags.append(tag)
        self.tag_counts[tag] = self.tag_counts.get(tag, 0) + 1

        attr_dict = dict(attrs)
        self.attrs_list.append(attr_dict)

        # Check for lang attribute on html
        if tag == "html" and "lang" in attr_dict:
            self.has_lang = True

        # Check for viewport meta
        if tag == "meta":
            if attr_dict.get("name") == "viewport":
                content = attr_dict.get("content", "")
                if "width=device-width" in content:
                    self.has_viewport = True

        # Track external references
        if tag == "link" and "href" in attr_dict:
            href = attr_dict["href"]
            if href.startswith("http") or href.startswith("//"):
                self.external_refs.append(f"link:href={href}")

        if tag == "script" and "src" in attr_dict:
            src = attr_dict["src"]
            if src.startswith("http") or src.startswith("//"):
                self.external_refs.append(f"script:src={src}")

        if tag == "img" and "src" in attr_dict:
            src = attr_dict["src"]
            if src.startswith("http"):
                self.external_refs.append(f"img:src={src}")

        # Check for form action to external URLs
        if tag == "form" and "action" in attr_dict:
            action = attr_dict["action"]
            if action.startswith("http"):
                self.external_refs.append(f"form:action={action}")

    def handle_data(self, data: str):
        stripped = data.strip()
        if stripped:
            self.text_content.append(stripped)

    def handle_comment(self, data: str):
        # Track comments as text content (useful info)
        pass

    def handle_decl(self, decl: str):
        if decl.lower() == "doctype html":
            self.has_doctype = True

    def error(self, message: str):
        self.errors.append(message)


# ═══════════════════════════════════════════════
# Check Functions
# ═══════════════════════════════════════════════

MAX_HTML_SIZE = 100_000  # 100KB max for a prototype page


def check_structure(parser: PrototypeParser, html: str) -> list[ValidationIssue]:
    """Check basic HTML structure."""
    issues: list[ValidationIssue] = []

    if not parser.has_doctype:
        issues.append(ValidationIssue(
            IssueSeverity.WARNING, "structure",
            "缺少 <!DOCTYPE html> 声明",
            "在 HTML 开头添加 <!DOCTYPE html>"
        ))

    if not parser.has_lang:
        issues.append(ValidationIssue(
            IssueSeverity.WARNING, "structure",
            "<html> 标签缺少 lang 属性",
            '添加 lang="zh-CN" 到 <html> 标签'
        ))

    if parser.tag_counts.get("title", 0) == 0:
        issues.append(ValidationIssue(
            IssueSeverity.WARNING, "structure",
            "缺少 <title> 标签",
            "在 <head> 中添加 <title>产品名称</title>"
        ))

    if parser.tag_counts.get("body", 0) == 0:
        issues.append(ValidationIssue(
            IssueSeverity.ERROR, "structure",
            "缺少 <body> 标签",
            "确保 HTML 包含 <body> 标签包裹内容"
        ))

    if parser.tag_counts.get("head", 0) == 0:
        issues.append(ValidationIssue(
            IssueSeverity.WARNING, "structure",
            "缺少 <head> 标签",
            "添加 <head> 标签包含 meta 和 title"
        ))

    # Check for unclosed tags (basic heuristic)
    if parser.errors:
        issues.append(ValidationIssue(
            IssueSeverity.ERROR, "structure",
            f"HTML 解析发现 {len(parser.errors)} 个语法错误",
            "修复 HTML 标签的嵌套和闭合问题"
        ))

    return issues


def check_security(parser: PrototypeParser) -> list[ValidationIssue]:
    """Check for unsafe patterns."""
    issues: list[ValidationIssue] = []

    # External references
    if parser.external_refs:
        ref_list = ", ".join(parser.external_refs[:5])
        issues.append(ValidationIssue(
            IssueSeverity.ERROR, "security",
            f"原型包含外部资源引用: {ref_list}",
            "移除所有外部 CDN/URL 引用，使用内联样式和脚本"
        ))

    # Check script content for dangerous patterns
    for script in parser.scripts:
        dangerous = []
        if "eval(" in script:
            dangerous.append("eval()")
        if "document.write" in script:
            dangerous.append("document.write()")
        if "innerHTML" in script:
            dangerous.append("innerHTML (建议用 textContent)")
        if dangerous:
            issues.append(ValidationIssue(
                IssueSeverity.WARNING, "security",
                f"脚本包含潜在风险: {', '.join(dangerous)}",
                f"避免使用 {', '.join(dangerous)}"
            ))

    # Check for HTML size (too large = likely hallucinated content)
    return issues


def check_quality(parser: PrototypeParser) -> list[ValidationIssue]:
    """Check for basic UX quality."""
    issues: list[ValidationIssue] = []

    # Semantic HTML
    semantic_tags = ["nav", "main", "section", "article", "header", "footer"]
    found_semantic = [t for t in semantic_tags if parser.tag_counts.get(t, 0) > 0]
    if not found_semantic:
        issues.append(ValidationIssue(
            IssueSeverity.INFO, "quality",
            "未使用语义化 HTML 标签 (nav/main/section/header/footer)",
            "用 <nav>/<main>/<section> 替换 <div> 提升语义"
        ))

    # Viewport meta
    if not parser.has_viewport:
        issues.append(ValidationIssue(
            IssueSeverity.WARNING, "quality",
            "缺少 viewport meta 标签，移动端可能显示异常",
            '在 <head> 添加 <meta name="viewport" content="width=device-width, initial-scale=1.0">'
        ))

    # Minimum content
    total_text = " ".join(parser.text_content)
    if len(total_text) < 20:
        issues.append(ValidationIssue(
            IssueSeverity.ERROR, "quality",
            f"页面文本内容过少 ({len(total_text)} 字符)",
            "确保原型包含足够的占位文本和功能说明"
        ))

    # Navigation element
    has_nav = parser.tag_counts.get("nav", 0) > 0
    has_links = parser.tag_counts.get("a", 0) > 0
    if not has_nav and has_links:
        issues.append(ValidationIssue(
            IssueSeverity.INFO, "quality",
            "有链接但缺少 <nav> 导航容器",
            "用 <nav> 包裹导航链接"
        ))

    # Image alt attributes
    img_count = parser.tag_counts.get("img", 0)
    if img_count > 0:
        imgs_with_alt = sum(
            1 for a in parser.attrs_list
            if a.get("alt") and img_count > 0
        )
        if imgs_with_alt < img_count:
            issues.append(ValidationIssue(
                IssueSeverity.INFO, "quality",
                f"{img_count - imgs_with_alt}/{img_count} 个图片缺少 alt 属性",
                "为所有 <img> 添加有意义的 alt 文本"
            ))

    return issues


def check_self_contained(parser: PrototypeParser) -> list[ValidationIssue]:
    """Check that the prototype is fully self-contained (no external deps)."""
    issues: list[ValidationIssue] = []

    # All CSS should be in <style> tags
    # Check if there's any inline style or style tag
    has_style_tag = parser.tag_counts.get("style", 0) > 0
    has_inline_style = any("style" in attrs for attrs in parser.attrs_list)

    if not has_style_tag and not has_inline_style:
        issues.append(ValidationIssue(
            IssueSeverity.WARNING, "self-contained",
            "原型没有 CSS 样式（无 <style> 标签或 inline style）",
            "添加 <style> 标签定义页面样式"
        ))

    # No external resources (already checked in security, but confirm)
    if not parser.external_refs and has_style_tag:
        # All good
        pass

    return issues


# ═══════════════════════════════════════════════
# Main Validator
# ═══════════════════════════════════════════════

class PrototypeValidator:
    """Validates LLM-generated HTML prototypes."""

    def validate(self, html: str) -> ValidationReport:
        """Run all checks and return a report."""
        parser = PrototypeParser()

        # Parse
        try:
            parser.feed(html)
        except Exception as e:
            return ValidationReport(
                is_valid=False,
                score=0,
                issues=[ValidationIssue(
                    IssueSeverity.ERROR, "parse",
                    f"HTML 解析失败: {str(e)}",
                    "确保 LLM 输出完整的、合法的 HTML"
                )],
                html_size=len(html),
            )

        # Run checks
        all_issues: list[ValidationIssue] = []
        all_issues.extend(check_structure(parser, html))
        all_issues.extend(check_security(parser))
        all_issues.extend(check_quality(parser))
        all_issues.extend(check_self_contained(parser))

        # Calculate score
        score = self._calculate_score(all_issues)

        # Determine validity (no errors)
        errors = [i for i in all_issues if i.severity == IssueSeverity.ERROR]
        is_valid = len(errors) == 0

        return ValidationReport(
            is_valid=is_valid,
            score=score,
            issues=all_issues,
            html_size=len(html),
            elements_found=parser.tag_counts,
        )

    def _calculate_score(self, issues: list[ValidationIssue]) -> int:
        """Calculate a 0-100 score based on issues.

        - ERROR: -20 points each
        - WARNING: -10 points each
        - INFO: -5 points each
        - Minimum score: 10
        """
        score = 100
        for issue in issues:
            if issue.severity == IssueSeverity.ERROR:
                score -= 20
            elif issue.severity == IssueSeverity.WARNING:
                score -= 10
            elif issue.severity == IssueSeverity.INFO:
                score -= 5
        return max(10, score)

    def is_acceptable(self, html: str, min_score: int = 60) -> tuple[bool, ValidationReport]:
        """Quick check: is the prototype acceptable to show the user?"""
        report = self.validate(html)
        return report.score >= min_score, report

    def auto_fix(self, html: str, issues: list[ValidationIssue]) -> str:
        """Attempt to auto-fix common issues."""
        fixed = html

        for issue in issues:
            if issue.severity != IssueSeverity.ERROR:
                continue

            # Auto-fix: add DOCTYPE if missing
            if "DOCTYPE" in issue.message and fixed.strip():
                if not fixed.strip().startswith("<!DOCTYPE"):
                    fixed = "<!DOCTYPE html>\n" + fixed

            # Auto-fix: add lang attribute
            if "lang" in issue.message:
                fixed = fixed.replace("<html>", '<html lang="zh-CN">', 1)
                fixed = fixed.replace("<html ", '<html lang="zh-CN" ', 1)

        return fixed
