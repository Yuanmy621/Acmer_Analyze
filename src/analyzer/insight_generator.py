from __future__ import annotations

"""基于 LLM 生成队伍高层洞察。"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

from src.analyzer.llm_client import LlmRequestError, invoke_llm
from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext

logger = logging.getLogger(__name__)

# prompt 总字符数上限（约 120k 字符 ≈ 40k~60k tokens，留足余量）。
_MAX_PROMPT_CHARS = 120_000
# 单条 tutorial 最大字符数。
_MAX_TUTORIAL_CHARS = 1500


def _estimate_tokens(text: str) -> int:
    """粗略估算 token 数。中文约 2 字符/token，英文约 4 字符/token。"""
    cn_chars = sum(1 for c in text if '一' <= c <= '鿿')
    other_chars = len(text) - cn_chars
    return cn_chars // 2 + other_chars // 4


def _truncate_tutorials(tutorials: list[dict], max_total_chars: int) -> list[dict]:
    """截断 tutorials 内容，使总字符数不超过 max_total_chars。"""
    truncated: list[dict] = []
    total = 0
    for t in tutorials:
        content = t.get("content", "")
        if len(content) > _MAX_TUTORIAL_CHARS:
            content = content[:_MAX_TUTORIAL_CHARS] + "…(已截断)"
        entry = {**t, "content": content}
        entry_chars = len(content)
        if total + entry_chars > max_total_chars:
            break
        truncated.append(entry)
        total += entry_chars
    return truncated


def _build_llm_prompt(
    context: PipelineContext,
    identity: dict,
    history: dict,
    metrics: dict,
    tutorials: list[dict] | None = None,
) -> str:
    """构造要求模型返回 JSON 的 analyze prompt。"""
    # 估算非 tutorial 部分的大小，将剩余空间分配给 tutorials。
    base_payload = {
        "task": {
            "target_team": context.task.target_team,
            "canonical_id": context.canonical_id,
            "school": context.task.school,
            "region": context.task.region,
            "time_range": context.task.time_range,
        },
        "identity": identity,
        "history": history,
        "metrics": metrics,
    }
    base_chars = len(json.dumps(base_payload, ensure_ascii=False))

    # 为 tutorials 预留空间，但不超过总上限。
    available_for_tutorials = max(0, _MAX_PROMPT_CHARS - base_chars - 2000)  # 2000 留给指令文本
    effective_tutorials = tutorials or []
    if effective_tutorials and available_for_tutorials > 0:
        effective_tutorials = _truncate_tutorials(effective_tutorials, available_for_tutorials)
        if len(effective_tutorials) < len(tutorials):
            logger.info(
                "Tutorial 截断: %d → %d 条 (可用空间 %d 字符)",
                len(tutorials), len(effective_tutorials), available_for_tutorials,
            )

    prompt_payload = {
        **base_payload,
        "tutorials": effective_tutorials,
        "output_schema": {
            "summary": "string",
            "strengths": ["string"],
            "weaknesses": ["string"],
            "training_advice": ["string"],
            "stage_analysis": "string",
        },
    }
    tutorial_instruction = ""
    if effective_tutorials:
        tutorial_instruction = (
            "5. 输入中的 tutorials 包含各题的官方题解（Tutorial），请结合题解内容分析队伍的算法能力特点。\n"
            "   例如：队伍在某类算法上通过率高但题解显示该类题目难度较低，说明基础扎实但进阶不足；\n"
            "   队伍未通过的高难题目若涉及特定算法领域，可在 training_advice 中给出针对性建议。\n"
            "   如果 tutorials 为空，则仅基于 tags 和 metrics 进行分析。\n"
        )
    prompt = (
        "你是 ACM / 竞赛编程队伍分析助手。\n"
        "请基于给定的结构化数据，为目标队伍生成高层分析。\n"
        "要求：\n"
        "1. 只使用输入中能支持的事实，不要编造不存在的比赛或标签。\n"
        "2. 输出必须是一个 JSON object，不要输出 Markdown、代码块或额外解释。\n"
        "3. strengths / weaknesses / training_advice 各给出 2 到 4 条中文结论。\n"
        "4. summary 和 stage_analysis 需要是中文完整句子。\n"
        f"{tutorial_instruction}"
        "输入数据如下：\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
    )
    logger.info("Prompt 构建完成: %d 字符, 约 %d tokens", len(prompt), _estimate_tokens(prompt))
    return prompt


def _parse_llm_response(raw_text: str) -> dict[str, Any]:
    """解析模型返回的 JSON，并校验必要字段。

    支持处理：
    - 纯 JSON 文本
    - 带 Markdown 代码块的 JSON（如 ```json ... ```）
    - 带前后缀说明文字的 JSON
    """
    text = raw_text.strip()

    # 尝试提取 Markdown 代码块中的 JSON
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()

    # 如果文本不是以 { 开头，尝试找到第一个 { 和最后一个 }
    if not text.startswith("{"):
        first_brace = text.find("{")
        last_brace = text.rfind("}")
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            text = text[first_brace:last_brace + 1]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise LlmRequestError(f"failed to parse llm response as JSON: {error}") from error

    required_fields = ["summary", "strengths", "weaknesses", "training_advice", "stage_analysis"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise LlmRequestError(f"missing fields in llm response: {', '.join(missing)}")
    for field in ["strengths", "weaknesses", "training_advice"]:
        if not isinstance(payload[field], list):
            raise LlmRequestError(f"invalid llm response field type: {field}")
    return payload


def _build_llm_insight(
    context: PipelineContext,
    identity: dict,
    history: dict,
    metrics: dict,
    tutorials: list[dict] | None = None,
) -> dict[str, Any]:
    """调用 LLM 生成 insight。"""
    prompt = _build_llm_prompt(context, identity, history, metrics, tutorials)
    raw_text, config = invoke_llm(
        prompt=prompt,
        settings_path=context.task.llm_settings_path,
        model_override=context.task.llm_model,
    )
    parsed = _parse_llm_response(raw_text)
    return {
        "canonical_id": metrics["canonical_id"],
        "strengths": [str(item) for item in parsed["strengths"]],
        "weaknesses": [str(item) for item in parsed["weaknesses"]],
        "summary": str(parsed["summary"]),
        "training_advice": [str(item) for item in parsed["training_advice"]],
        "stage_analysis": str(parsed["stage_analysis"]),
        "model_used": config.model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "llm_provider": "openai-compatible",
        "llm_settings_path": config.settings_path,
    }


def run_analyze(context: PipelineContext) -> None:
    """读取 team_metrics，调用 LLM 生成 insights artifact。"""
    logger.info("[analyze] 开始 LLM 分析 (team=%s)", context.canonical_id)

    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))
    identity = read_json(context.path(f"data/intermediate/team_identity/{context.canonical_id}.json"))
    history = read_json(context.path(f"data/intermediate/team_history/{context.canonical_id}.json"))

    # 读取 Tutorial 题解数据（可选，缺失时不影响分析）。
    tutorials_path = context.path("data/raw/tutorials/tutorials.json")
    tutorials: list[dict] = []
    if os.path.exists(tutorials_path):
        tutorials = read_json(tutorials_path)
        logger.info("[analyze] 读取到 %d 条 Tutorial 题解", len(tutorials))

    payload = _build_llm_insight(context, identity, history, metrics, tutorials)
    write_json(context.path(f"outputs/insights/{context.canonical_id}.json"), payload)
    logger.info("[analyze] LLM 分析完成，结果已写入 insights artifact")
