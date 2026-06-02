from __future__ import annotations

"""最终产物的结构化验收逻辑。"""

from datetime import datetime, timezone

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext

VALIDATION_AFTER_VALIDATE = "validation.after_validate"

REQUIRED_REPORT_SECTIONS = {"overview", "trend", "topics", "strengths", "weaknesses", "advice"}
REQUIRED_CHART_KEYS = {"rank_trend", "tag_distribution", "strengths", "weaknesses"}


def run_validate_final(context: PipelineContext) -> None:
    """检查关键指标、报告段落与可视化 artifact 是否齐全。"""
    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))
    report_artifact = read_json(context.path(f"outputs/reports/{context.canonical_id}.artifact.json"))

    errors: list[str] = []
    warnings: list[str] = []

    if not metrics.get("rank_trend"):
        errors.append("missing rank_trend")
    if not metrics.get("tag_distribution"):
        errors.append("missing tag_distribution")
    if "stability_score" not in metrics:
        errors.append("missing stability_score")

    sections_present = set(report_artifact.get("sections_present", []))
    missing_sections = sorted(REQUIRED_REPORT_SECTIONS - sections_present)
    if missing_sections:
        errors.append(f"missing report sections: {', '.join(missing_sections)}")

    report_path = context.path(f"outputs/reports/{context.canonical_id}.html")
    if not report_path.exists():
        errors.append("report html not found")

    insight_path = context.path(f"outputs/insights/{context.canonical_id}.json")
    if insight_path.exists():
        insight = read_json(insight_path)
        if not insight.get("summary"):
            errors.append("missing insight summary")
    else:
        # analyze 阶段允许跳过，因此这里仅给 warning。
        warnings.append("insight artifact not found")

    visualization_artifact_path = context.path(f"outputs/visualizations/{context.canonical_id}.artifact.json")
    if visualization_artifact_path.exists():
        visualization_artifact = read_json(visualization_artifact_path)
        chart_keys = set(visualization_artifact.get("chart_keys", []))
        missing_chart_keys = sorted(REQUIRED_CHART_KEYS - chart_keys)
        if missing_chart_keys:
            errors.append(f"missing chart keys: {', '.join(missing_chart_keys)}")
    else:
        warnings.append("visualization artifact not found")

    visualization_html_path = context.path(f"outputs/visualizations/{context.canonical_id}.html")
    if not visualization_html_path.exists():
        errors.append("visualization html not found")

    payload = {
        "canonical_id": context.canonical_id,
        "passed": not errors,
        "errors": errors,
        "warnings": warnings,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    validation_path = context.path(f"outputs/validation/{context.canonical_id}.json")
    write_json(validation_path, payload)

    hook_manager = context.hook_manager()
    hook_manager.emit_safe(
        VALIDATION_AFTER_VALIDATE,
        context.new_hook_context(
            VALIDATION_AFTER_VALIDATE,
            payload={
                "validation_path": str(validation_path.relative_to(context.root_dir)),
                "passed": payload["passed"],
                "error_count": len(errors),
                "warning_count": len(warnings),
            },
        ),
    )
