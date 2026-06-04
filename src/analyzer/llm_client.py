from __future__ import annotations

"""analyze 阶段的 LLM 配置读取与 HTTP 调用封装。"""

import http.client
import json
import os
import ssl
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
    """根据 base_url 推导 chat endpoint。

    支持两种格式：
    - Anthropic Messages API: /v1/messages
    - OpenAI-compatible: /v1/chat/completions
    """
    # 已经是完整 endpoint
    if base_url.endswith("/messages"):
        return base_url
    if base_url.endswith("/chat/completions"):
        return base_url
    # 拼接 Anthropic Messages API 路径
    if base_url.endswith("/v1"):
        return f"{base_url}/messages"
    return f"{base_url}/v1/messages"


def _extract_text_from_response(payload: dict[str, Any]) -> str:
    """从 OpenAI-compatible 或 Anthropic-compatible 响应中提取纯文本。"""
    # OpenAI-compatible 格式: {"choices": [{"message": {"content": "..."}}]}
    choices = payload.get("choices")
    if isinstance(choices, list) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, dict):
            message = first_choice.get("message")
            if isinstance(message, dict):
                content = message.get("content")
                if isinstance(content, str) and content.strip():
                    return content.strip()
                # 有些 API 返回 content 为列表格式
                if isinstance(content, list):
                    chunks = [item.get("text", "") for item in content if isinstance(item, dict) and item.get("type") == "text"]
                    text = "\n".join(chunk for chunk in chunks if chunk.strip()).strip()
                    if text:
                        return text

    # Anthropic Messages API 格式: {"content": [{"type": "text", "text": "..."}]}
    content = payload.get("content")
    if isinstance(content, list):
        chunks: list[str] = []
        thinking_chunks: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                continue
            if item.get("type") == "text" and isinstance(item.get("text"), str):
                chunks.append(item["text"])
            # 处理 thinking 类型的内容（扩展思考功能）
            elif item.get("type") == "thinking" and isinstance(item.get("thinking"), str):
                thinking_chunks.append(item["thinking"])

        # 优先返回 text 内容
        text = "\n".join(chunk for chunk in chunks if chunk.strip()).strip()
        if text:
            return text

        # 如果没有 text 内容，但有 thinking 内容，尝试从 thinking 中提取
        if thinking_chunks:
            return "\n".join(thinking_chunks).strip()

    # 直接包含 text 字段的格式
    if isinstance(payload.get("text"), str) and payload["text"].strip():
        return payload["text"].strip()

    raise LlmRequestError("invalid response: missing or empty text content")


def invoke_llm(prompt: str, settings_path: str | None = None, model_override: str | None = None, timeout: int = 120, max_retries: int = 3) -> tuple[str, LlmConfig]:
    """调用 LLM 并返回文本结果与实际使用的配置。

    Args:
        timeout: 请求超时时间（秒），默认 120 秒
        max_retries: 最大重试次数，默认 3 次
    """
    config = load_llm_config(settings_path=settings_path, model_override=model_override)
    endpoint = _chat_endpoint(config.base_url)
    request_payload = {
        "model": config.model,
        "max_tokens": 4096,
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
            "x-api-key": config.auth_token,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    # 使用 http.client 直接连接，绕过 urllib 的 SSL 问题
    from urllib.parse import urlparse
    parsed = urlparse(endpoint)

    last_error = None
    for attempt in range(max_retries):
        try:
            # 创建宽松的 SSL 上下文
            ssl_context = ssl.create_default_context()
            ssl_context.set_ciphers('DEFAULT:@SECLEVEL=1')
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

            if parsed.scheme == 'https':
                conn = http.client.HTTPSConnection(
                    parsed.hostname,
                    parsed.port or 443,
                    timeout=timeout,
                    context=ssl_context
                )
            else:
                conn = http.client.HTTPConnection(
                    parsed.hostname,
                    parsed.port or 80,
                    timeout=timeout
                )

            conn.request(
                'POST',
                parsed.path,
                body=body,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": config.auth_token,
                    "anthropic-version": "2023-06-01",
                }
            )
            response = conn.getresponse()

            if response.status != 200:
                detail = response.read().decode("utf-8", "ignore")
                raise LlmRequestError(f"HTTP {response.status} for {endpoint}: {detail}")

            payload = json.load(response)
            conn.close()
            return _extract_text_from_response(payload), config
        except (http.client.HTTPException, OSError) as error:
            last_error = error
            if attempt < max_retries - 1:
                import time
                time.sleep(2 ** attempt)  # 指数退避: 1s, 2s, 4s
                continue
            raise LlmRequestError(f"network error for {endpoint} after {max_retries} retries: {last_error}") from last_error
