"""LLM proxy clients for gateway endpoints.

第一版支持非流式转发，并提供 mock 模式用于无 API Key 本地跑通。
"""

from __future__ import annotations

import time
import uuid
from typing import Any

import httpx

from gateway_config import GatewayConfig


def _mock_anthropic_response(payload: dict[str, Any], memory_used: bool = False) -> dict[str, Any]:
    model = payload.get("model") or "mock-anthropic"
    return {
        "id": f"msg_mock_{uuid.uuid4().hex[:12]}",
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": [
            {
                "type": "text",
                "text": "[MOCK] 网关已收到 Anthropic-compatible 请求，并完成记忆自动召回与注入。"
                + ("本轮有注入记忆。" if memory_used else "本轮没有可注入记忆。"),
            }
        ],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


def _mock_openai_response(payload: dict[str, Any], memory_used: bool = False) -> dict[str, Any]:
    model = payload.get("model") or "mock-openai"
    return {
        "id": f"chatcmpl-mock-{uuid.uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "[MOCK] 网关已收到 OpenAI-compatible 请求，并完成记忆自动召回与注入。"
                    + ("本轮有注入记忆。" if memory_used else "本轮没有可注入记忆。"),
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    }


async def call_anthropic(payload: dict[str, Any], cfg: GatewayConfig, memory_used: bool = False) -> dict[str, Any]:
    if cfg.mock_llm:
        return _mock_anthropic_response(payload, memory_used=memory_used)
    if not cfg.main_api_key:
        raise RuntimeError("OMBRE_MAIN_MODEL_API_KEY is required when mock mode is disabled")

    url = f"{cfg.main_base_url}/v1/messages"
    headers = {
        "content-type": "application/json",
        "x-api-key": cfg.main_api_key,
        "anthropic-version": cfg.anthropic_version,
    }
    async with httpx.AsyncClient(timeout=cfg.request_timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()


async def call_openai_compatible(payload: dict[str, Any], cfg: GatewayConfig, memory_used: bool = False) -> dict[str, Any]:
    if cfg.mock_llm:
        return _mock_openai_response(payload, memory_used=memory_used)
    if not cfg.main_api_key:
        raise RuntimeError("OMBRE_MAIN_MODEL_API_KEY is required when mock mode is disabled")

    url = f"{cfg.main_base_url}/v1/chat/completions"
    headers = {
        "content-type": "application/json",
        "authorization": f"Bearer {cfg.main_api_key}",
    }
    async with httpx.AsyncClient(timeout=cfg.request_timeout) as client:
        resp = await client.post(url, json=payload, headers=headers)
        resp.raise_for_status()
        return resp.json()