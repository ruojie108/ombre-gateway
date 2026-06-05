"""Memory context injection helpers.

把自动召回的 memory_context 注入 Anthropic / OpenAI 兼容请求。
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any


def inject_into_anthropic(payload: dict[str, Any], memory_context: str) -> dict[str, Any]:
    new_payload = deepcopy(payload)
    if not memory_context:
        return new_payload
    system = new_payload.get("system", "")
    if isinstance(system, str):
        new_payload["system"] = (system.rstrip() + "\n\n" + memory_context).strip() if system else memory_context
    elif isinstance(system, list):
        system.append({"type": "text", "text": memory_context})
        new_payload["system"] = system
    else:
        new_payload["system"] = memory_context
    return new_payload


def inject_into_openai(payload: dict[str, Any], memory_context: str) -> dict[str, Any]:
    new_payload = deepcopy(payload)
    if not memory_context:
        return new_payload
    messages = list(new_payload.get("messages") or [])
    insert_at = 0
    for idx, msg in enumerate(messages):
        if msg.get("role") == "system":
            insert_at = idx + 1
    messages.insert(insert_at, {"role": "system", "content": memory_context})
    new_payload["messages"] = messages
    return new_payload


def anthropic_messages_to_openai_messages(system: Any, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    if system:
        converted.append({"role": "system", "content": system if isinstance(system, str) else str(system)})
    converted.extend(messages or [])
    return converted