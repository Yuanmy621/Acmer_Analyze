from __future__ import annotations

"""基于规则模板或 LLM 生成队伍高层洞察。"""

import json
from datetime import datetime, timezone
from typing import Any

from src.analyzer.llm_client import LlmConfigError, LlmRequestError, invoke_llm
from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext


def _pick_strengths(tag_distribution: dict[str, dict]) -> list[str]:
    """从标签分布中挑选通过率较高的题型作为优势。"""
    ranked = sorted(tag_distribution.items(), key=lambda item: (-item[1]["solve_rate"], -item[1]["solved"], item[0]))
    strengths: list[str] = []
    for tag, data in ranked:
        if int(data["attempted"]) == 0:
            continue
        strengths.append(f"{tag} 题通过率较高（{data['solve_rate']:.2f}）")
        if len(strengths) >= 2:
            break
    return strengths or ["当前样本较少，暂未识别出稳定优势标签"]


def _pick_weaknesses(tag_distribution: dict[str, dict]) -> list[str]:
    """从标签分布中挑选通过率偏低的题型作为短板。"""
    ranked = sorted(tag_distribution.items(), key=lambda item: (item[1]["solve_rate"], -item[1]["attempted"], item[0]))
    weaknesses: list[str] = []
    for tag, data in ranked:
        if int(data["attempted"]) == 0:
            continue
        weaknesses.append(f"{tag} 题通过率偏低（{data['solve_rate']:.2f}）")
        if len(weaknesses) >= 2:
            break
    return weaknesses or ["当前样本较少，暂未识别出明确短板标签"]


def _build_summary(target_team: str, metrics: dict) -> tuple[str, str, list[str]]:
    """根据稳定性与成长性指标生成摘要和训练建议。"""
    stability = metrics["stability_score"]
    growth = metrics.get("growth_score")
    if stability >= 0.85:
        stability_text = "整体表现较稳定"
        advice = "继续保持稳定发挥，并逐步提高高价值题目的突破能力"
    elif stability >= 0.7:
        stability_text = "整体表现中等稳定"
        advice = "建议通过复盘波动较大的比赛，提升发挥一致性"
    else:
        stability_text = "比赛表现波动较明显"
        advice = "建议优先加强赛时策略与中后程稳定性训练"

    if growth is None:
        growth_text = "当前历史样本较少，成长趋势仍需继续观察"
    elif growth >= 0.6:
        growth_text = "近阶段呈现一定上升趋势"
    elif growth >= 0.45:
        growth_text = "近阶段整体变化不大"
    else:
        growth_text = "近阶段存在一定回落压力"

    summary = f"{target_team} 的历史表现显示，{stability_text}，{growth_text}。"
    return summary, growth_text, [advice]


def _build_rule_based_insight(context: PipelineContext, metrics: dict, fallback_reason: str | None = None) -> dict[str, Any]:
    """使用本地规则模板生成 insight。"""
    summary, stage_analysis, training_advice = _build_summary(context.task.target_team, metrics)
    if fallback_reason:
        training_advice = [*training_advice, f"LLM 调用失败，已回退到规则模板：{fallback_reason}"]

    payload = {
        "canonical_id": metrics["canonical_id"],
        "strengths": _pick_strengths(metrics["tag_distribution"]),
        "weaknesses": _pick_weaknesses(metrics["tag_distribution"]),
        "summary": summary,
        "training_advice": training_advice,
        "stage_analysis": stage_analysis,
        "model_used": "rule-based-template",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if fallback_reason:
        payload["fallback_reason"] = fallback_reason
    return payload


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
        "llm_provider": "anthropic-compatible",
        "llm_settings_path": config.settings_path,
    }


def run_analyze(context: PipelineContext) -> None:
    """读取 team_metrics，生成规则模板版或 LLM 版 insights artifact。"""
    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))

    if not context.task.enable_llm_insight:
        payload = _build_rule_based_insight(context, metrics)
        write_json(context.path(f"outputs/insights/{context.canonical_id}.json"), payload)
        return

    identity = read_json(context.path(f"data/intermediate/team_identity/{context.canonical_id}.json"))
    history = read_json(context.path(f"data/intermediate/team_history/{context.canonical_id}.json"))

    try:
        payload = _build_llm_insight(context, identity, history, metrics)
    except (LlmConfigError, LlmRequestError, json.JSONDecodeError) as error:
        if not context.task.llm_fallback_to_rule:
            raise
        payload = _build_rule_based_insight(context, metrics, fallback_reason=str(error))

    write_json(context.path(f"outputs/insights/{context.canonical_id}.json"), payload)
