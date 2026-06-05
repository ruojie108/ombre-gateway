"""Gateway configuration helpers for Ombre Memory Gateway.

网关配置读取：只从环境变量读取运行时敏感配置，避免把 key 写入仓库。
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name, "")
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name, "")
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass(frozen=True)
class GatewayConfig:
    enabled: bool
    auth_token: str
    mock_llm: bool

    auto_recall_enabled: bool
    recent_turns: int
    max_memories: int
    max_tokens: int
    pinned_limit: int
    include_pinned: bool
    include_related: bool
    include_floating: bool
    debug: bool

    main_provider: str
    main_base_url: str
    main_api_key: str
    main_model_name: str
    anthropic_version: str
    request_timeout: float


def load_gateway_config() -> GatewayConfig:
    provider = os.environ.get("OMBRE_MAIN_MODEL_PROVIDER", "anthropic").strip().lower() or "anthropic"
    default_base = "https://api.anthropic.com" if provider == "anthropic" else "https://api.openai.com"
    return GatewayConfig(
        enabled=_env_bool("OMBRE_GATEWAY_ENABLED", True),
        auth_token=os.environ.get("OMBRE_GATEWAY_AUTH_TOKEN", "").strip(),
        mock_llm=_env_bool("OMBRE_GATEWAY_MOCK_LLM", False),
        auto_recall_enabled=_env_bool("OMBRE_AUTO_RECALL_ENABLED", True),
        recent_turns=_env_int("OMBRE_AUTO_RECALL_RECENT_TURNS", 6),
        max_memories=_env_int("OMBRE_AUTO_RECALL_MAX_MEMORIES", 8),
        max_tokens=_env_int("OMBRE_AUTO_RECALL_MAX_TOKENS", 3000),
        pinned_limit=_env_int("OMBRE_AUTO_RECALL_PINNED_LIMIT", 5),
        include_pinned=_env_bool("OMBRE_AUTO_RECALL_INCLUDE_PINNED", True),
        include_related=_env_bool("OMBRE_AUTO_RECALL_INCLUDE_RELATED", True),
        include_floating=_env_bool("OMBRE_AUTO_RECALL_INCLUDE_FLOATING", False),
        debug=_env_bool("OMBRE_AUTO_RECALL_DEBUG", False),
        main_provider=provider,
        main_base_url=os.environ.get("OMBRE_MAIN_MODEL_BASE_URL", default_base).strip().rstrip("/"),
        main_api_key=os.environ.get("OMBRE_MAIN_MODEL_API_KEY", "").strip(),
        main_model_name=os.environ.get("OMBRE_MAIN_MODEL_NAME", "").strip(),
        anthropic_version=os.environ.get("OMBRE_MAIN_MODEL_VERSION", "2023-06-01").strip(),
        request_timeout=float(os.environ.get("OMBRE_GATEWAY_REQUEST_TIMEOUT", "120") or "120"),
    )


def require_gateway_auth(headers, cfg: GatewayConfig) -> bool:
    """Return True when request is authorized. If no token configured, allow local/dev access."""
    if not cfg.auth_token:
        return True
    auth = headers.get("authorization", "") or headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        if auth.split(" ", 1)[1].strip() == cfg.auth_token:
            return True
    x_api_key = headers.get("x-api-key", "") or headers.get("X-API-Key", "")
    return x_api_key.strip() == cfg.auth_token
