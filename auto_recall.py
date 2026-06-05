"""Automatic memory recall helpers.

自动召回层：从聊天 messages 构造检索 query，调用 Ombre 原 breath 逻辑，格式化为可注入上下文。
"""

from __future__ import annotations

from typing import Any

from utils import count_tokens_approx


def _content_to_text(content: Any) -> str:
    """Normalize OpenAI/Anthropic message content into plain text for recall query."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    parts.append(item["text"])
                elif isinstance(item.get("content"), str):
                    parts.append(item["content"])
            elif isinstance(item, str):
                parts.append(item)
        return "\n".join(p for p in parts if p)
    return str(content)


def build_recall_query(messages: list[dict[str, Any]], recent_turns: int = 6) -> str:
    """Build a compact query from the latest conversation turns."""
    if not messages:
        return ""
    recent = messages[-max(1, recent_turns):]
    lines = ["以下是最近对话片段，用于检索长期记忆："]
    for msg in recent:
        role = msg.get("role", "unknown")
        text = _content_to_text(msg.get("content", "")).strip()
        if not text:
            continue
        if len(text) > 1200:
            text = text[-1200:]
        lines.append(f"{role}: {text}")
    return "\n".join(lines).strip()


def build_memory_context(recalled_text: str, token_budget: int = 3000) -> str:
    """Wrap raw breath output into a system-injectable memory block."""
    text = (recalled_text or "").strip()
    if not text or text in {"未找到相关记忆。", "权重池平静，没有需要处理的记忆。"}:
        return ""

    header = (
        "[长期记忆召回]\n"
        "以下记忆由系统自动召回，可能与当前对话相关。请自然参考，不要机械复述；"
        "如果某条明显无关，请忽略。不要向用户暴露内部检索过程，除非用户主动询问。\n\n"
    )
    footer = "\n[/长期记忆召回]"
    budget = max(200, token_budget - count_tokens_approx(header + footer))

    # Crude token-budget truncation, enough for first pass.
    if count_tokens_approx(text) > budget:
        max_chars = budget * 4
        text = text[:max_chars].rstrip() + "\n...[因 token 预算截断]"
    return header + text + footer


async def auto_recall(
    *,
    messages: list[dict[str, Any]],
    breath_func,
    recent_turns: int = 6,
    max_memories: int = 8,
    max_tokens: int = 3000,
    include_related: bool = True,
    include_floating: bool = False,
    debug: bool = False,
) -> dict[str, Any]:
    """Run Ombre breath as a background recall step and return injectable context."""
    query = build_recall_query(messages, recent_turns=recent_turns)
    parts: list[str] = []
    errors: list[str] = []

    if include_related and query:
        try:
            related = await breath_func(query=query, max_tokens=max_tokens, max_results=max_memories)
            if related and "未找到相关记忆" not in related:
                parts.append("=== 本轮相关记忆 ===\n" + related)
        except Exception as e:  # pragma: no cover - defensive for gateway stability
            errors.append(f"related_recall_failed: {e}")

    if include_floating:
        try:
            floating = await breath_func(query="", max_tokens=max_tokens, max_results=max_memories)
            if floating and "权重池平静" not in floating:
                parts.append(floating)
        except Exception as e:  # pragma: no cover
            errors.append(f"floating_recall_failed: {e}")

    raw_text = "\n\n---\n\n".join(parts).strip()
    memory_context = build_memory_context(raw_text, token_budget=max_tokens)
    result = {
        "query": query,
        "memory_context": memory_context,
        "raw_recall": raw_text,
        "used": bool(memory_context),
        "token_estimate": count_tokens_approx(memory_context),
    }
    if debug:
        result["debug"] = {
            "recent_turns": recent_turns,
            "max_memories": max_memories,
            "max_tokens": max_tokens,
            "include_related": include_related,
            "include_floating": include_floating,
            "errors": errors,
        }
    return result