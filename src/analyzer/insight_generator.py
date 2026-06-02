from __future__ import annotations

"""基于 LLM 生成队伍高层洞察。"""

import json
from datetime import datetime, timezone
from typing import Any

from src.analyzer.llm_client import LlmRequestError, invoke_llm
from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext


def _build_llm_prompt(context: PipelineContext, identity: dict, history: dict, metrics: dict) -> str:
    """构造要求模型返回 JSON 的 analyze prompt。"""
    prompt_payload = {
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
        "output_schema": {
            "summary": "string",
            "strengths": ["string"],
            "weaknesses": ["string"],
            "training_advice": ["string"],
            "stage_analysis": "string",
        },
    }
    return (
        "你是 ACM / 竞赛编程队伍分析助手。\n"
        "请基于给定的结构化数据，为目标队伍生成高层分析。\n"
        "要求：\n"
        "1. 只使用输入中能支持的事实，不要编造不存在的比赛或标签。\n"
        "2. 输出必须是一个 JSON object，不要输出 Markdown、代码块或额外解释。\n"
        "3. strengths / weaknesses / training_advice 各给出 2 到 4 条中文结论。\n"
        "4. summary 和 stage_analysis 需要是中文完整句子。\n"
        "输入数据如下：\n"
        f"{json.dumps(prompt_payload, ensure_ascii=False, indent=2)}"
    )


def _parse_llm_response(raw_text: str) -> dict[str, Any]:
    """解析模型返回的 JSON，并校验必要字段。"""
    payload = json.loads(raw_text)
    required_fields = ["summary", "strengths", "weaknesses", "training_advice", "stage_analysis"]
    missing = [field for field in required_fields if field not in payload]
    if missing:
        raise LlmRequestError(f"missing fields in llm response: {', '.join(missing)}")
    for field in ["strengths", "weaknesses", "training_advice"]:
        if not isinstance(payload[field], list):
            raise LlmRequestError(f"invalid llm response field type: {field}")
    return payload


def _build_llm_insight(context: PipelineContext, identity: dict, history: dict, metrics: dict) -> dict[str, Any]:
    """调用 LLM 生成 insight。"""
    prompt = _build_llm_prompt(context, identity, history, metrics)
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
    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))
    identity = read_json(context.path(f"data/intermediate/team_identity/{context.canonical_id}.json"))
    history = read_json(context.path(f"data/intermediate/team_history/{context.canonical_id}.json"))

    payload = _build_llm_insight(context, identity, history, metrics)
    write_json(context.path(f"outputs/insights/{context.canonical_id}.json"), payload)
