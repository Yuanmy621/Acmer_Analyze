from __future__ import annotations

"""把指标与洞察渲染为 Markdown 报告。"""

from datetime import datetime, timezone

from src.models.serde import read_json, write_json, write_text
from src.orchestrator.context import PipelineContext


REPORT_SECTIONS = ["overview", "trend", "topics", "strengths", "weaknesses", "advice"]


def _render_rank_trend(items: list[dict]) -> str:
    """把排名趋势渲染成 Markdown 表格。"""
    lines = ["| contest_id | rank | percentile_rank |", "| --- | ---: | ---: |"]
    for item in items:
        lines.append(f"| {item['contest_id']} | {item['rank']} | {item['percentile_rank']:.4f} |")
    return "\n".join(lines)


def _render_tag_distribution(tag_distribution: dict[str, dict]) -> str:
    """把题型分布渲染成 Markdown 表格。"""
    lines = ["| tag | attempted | solved | solve_rate |", "| --- | ---: | ---: | ---: |"]
    for tag, data in tag_distribution.items():
        lines.append(
            f"| {tag} | {int(data['attempted'])} | {int(data['solved'])} | {data['solve_rate']:.4f} |"
        )
    return "\n".join(lines)


def run_report(context: PipelineContext) -> None:
    """生成 Markdown 报告及其 artifact 索引文件。"""
    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))
    insight_path = context.path(f"outputs/insights/{context.canonical_id}.json")
    if insight_path.exists():
        insight = read_json(insight_path)
    else:
        # 允许 analyze 被跳过，此时报告退化为结构化结果总览。
        insight = {
            "canonical_id": context.canonical_id,
            "strengths": ["本次运行跳过 analyze，暂无高层优势总结"],
            "weaknesses": ["本次运行跳过 analyze，暂无高层短板总结"],
            "summary": "本次运行未生成 AI / 规则式洞察，仅输出结构化结果。",
            "training_advice": ["如需总结与建议，请重新执行 analyze 阶段"],
            "stage_analysis": "未生成 analyze 阶段结果",
        }

    markdown = f"""# 队伍分析报告：{context.task.target_team}

## 1. 概览

- `canonical_id`: `{context.canonical_id}`
- 稳定性评分：`{metrics['stability_score']}`
- 成长性评分：`{metrics['growth_score']}`
- 解题平均首过时间：`{metrics['solve_pace']['avg_first_ac_minute']}` 分钟
- 后半程解题占比：`{metrics['solve_pace']['late_stage_solve_ratio']}`

> {insight['summary']}

## 2. 排名趋势

{_render_rank_trend(metrics['rank_trend'])}

## 3. 题型分布

{_render_tag_distribution(metrics['tag_distribution'])}

## 4. 优势总结

"""
    markdown += "\n".join([f"- {item}" for item in insight["strengths"]])
    markdown += "\n\n## 5. 短板总结\n\n"
    markdown += "\n".join([f"- {item}" for item in insight["weaknesses"]])
    markdown += "\n\n## 6. 训练建议\n\n"
    markdown += "\n".join([f"- {item}" for item in insight["training_advice"]])
    markdown += f"\n\n## 7. 阶段分析\n\n{insight['stage_analysis']}\n"

    report_path = context.path(f"outputs/reports/{context.canonical_id}.md")
    write_text(report_path, markdown)

    artifact = {
        "canonical_id": context.canonical_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": "md",
        "path": str(report_path.relative_to(context.root_dir)),
        "sections_present": REPORT_SECTIONS,
    }
    write_json(context.path(f"outputs/reports/{context.canonical_id}.artifact.json"), artifact)
