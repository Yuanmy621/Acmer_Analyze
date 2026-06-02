from __future__ import annotations

"""analyze 阶段的 LLM 配置读取与 HTTP 调用封装。"""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

DEFAULT_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
DEFAULT_MODEL = "gpt-5.4"


class LlmConfigError(RuntimeError):
    """LLM 配置缺失或非法。"""


class LlmRequestError(RuntimeError):
    """LLM 请求失败或响应不可解析。"""


@dataclass(slots=True)
class LlmConfig:
    """analyze 阶段调用大模型所需的最小配置。"""

    base_url: str
    auth_token: str
    model: str
    settings_path: str | None = None


def _load_settings_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_llm_config(settings_path: str | None = None, model_override: str | None = None) -> LlmConfig:
    """按优先级读取 LLM 配置。

    优先级：
    1. 指定 settings 文件
    2. ~/.claude/settings.json
    3. 进程环境变量
    """
    env_base_url = os.environ.get("ANTHROPIC_BASE_URL")
    env_auth_token = os.environ.get("ANTHROPIC_AUTH_TOKEN")
    env_model = os.environ.get("ANTHROPIC_MODEL")

    resolved_settings_path: Path | None = None
    settings_payload: dict[str, Any] = {}
    candidate_path = Path(settings_path).expanduser() if settings_path else DEFAULT_SETTINGS_PATH
    if candidate_path.exists():
        resolved_settings_path = candidate_path
        settings_payload = _load_settings_file(candidate_path)

    settings_env = settings_payload.get("env", {}) if isinstance(settings_payload.get("env", {}), dict) else {}
    base_url = settings_env.get("ANTHROPIC_BASE_URL") or env_base_url
    auth_token = settings_env.get("ANTHROPIC_AUTH_TOKEN") or env_auth_token
    model = model_override or settings_env.get("ANTHROPIC_MODEL") or settings_payload.get("model") or env_model or DEFAULT_MODEL

    if not base_url:
        raise LlmConfigError("missing ANTHROPIC_BASE_URL")
    if not auth_token:
        raise LlmConfigError("missing ANTHROPIC_AUTH_TOKEN")

    return LlmConfig(
        base_url=str(base_url).rstrip("/"),
        auth_token=str(auth_token),
        model=str(model),
        settings_path=None if resolved_settings_path is None else str(resolved_settings_path),
    )


def _chat_endpoint(base_url: str) -> str:
    """根据 base_url 推导 OpenAI-compatible chat completions endpoint。"""
    if base_url.endswith("/chat/completions"):
        return base_url
    if base_url.endswith("/v1"):
        return f"{base_url}/chat/completions"
    return f"{base_url}/v1/chat/completions"


def _extract_text_from_response(payload: dict[str, Any]) -> str:
    """从 OpenAI-compatible 或 Anthropic-compatible 响应中提取纯文本。"""
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict) and isinstance(message.get("content"), str):
                text = message["content"].strip()
                if text:
                    return text

    content = payload.get("content")
    if not isinstance(content, list):
        raise LlmRequestError("invalid response: missing choices or content list")

    chunks: list[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            chunks.append(item["text"])
    text = "\n".join(chunk for chunk in chunks if chunk.strip()).strip()
    if not text:
        raise LlmRequestError("invalid response: empty text content")
    return text


def invoke_llm(prompt: str, settings_path: str | None = None, model_override: str | None = None, timeout: int = 60) -> tuple[str, LlmConfig]:
    """调用 LLM 并返回文本结果与实际使用的配置。"""
    config = load_llm_config(settings_path=settings_path, model_override=model_override)
    endpoint = _chat_endpoint(config.base_url)
    request_payload = {
        "model": config.model,
        "max_tokens": 1200,
        "temperature": 0.3,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    body = json.dumps(request_payload, ensure_ascii=False).encode("utf-8")
    request = Request(
        endpoint,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.auth_token}",
            "x-api-key": config.auth_token,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            payload = json.load(response)
    except HTTPError as error:
        detail = error.read().decode("utf-8", "ignore")
        raise LlmRequestError(f"HTTP {error.code} for {endpoint}: {detail}") from error
    except URLError as error:
        raise LlmRequestError(f"network error for {endpoint}: {error}") from error

    return _extract_text_from_response(payload), config
