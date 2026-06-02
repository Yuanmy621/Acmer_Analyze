from __future__ import annotations

"""从指标与洞察中整理前端可消费的可视化数据。"""

from datetime import datetime, timezone

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext


def run_visualize(context: PipelineContext) -> None:
    """生成图表数据 JSON 及对应 artifact 索引。"""
    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))
    insight_path = context.path(f"outputs/insights/{context.canonical_id}.json")
    insight = read_json(insight_path) if insight_path.exists() else {"strengths": [], "weaknesses": []}

    chart_payload = {
        "canonical_id": context.canonical_id,
        "rank_trend": metrics["rank_trend"],
        "tag_distribution": metrics["tag_distribution"],
        # strengths / weaknesses 一并输出，方便可视化层直接展示摘要标签。
        "strengths": insight.get("strengths", []),
        "weaknesses": insight.get("weaknesses", []),
    }
    chart_path = context.path(f"outputs/visualizations/{context.canonical_id}.json")
    write_json(chart_path, chart_payload)

    artifact = {
        "canonical_id": context.canonical_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": "json",
        "path": str(chart_path.relative_to(context.root_dir)),
        "chart_keys": ["rank_trend", "tag_distribution", "strengths", "weaknesses"],
    }
    write_json(context.path(f"outputs/visualizations/{context.canonical_id}.artifact.json"), artifact)
