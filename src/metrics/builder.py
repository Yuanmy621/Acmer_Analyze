from __future__ import annotations

"""基于历史记录计算确定性指标。"""

from collections import defaultdict
from statistics import pstdev

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext


def _build_problem_index(problems: list[dict]) -> dict[str, dict]:
    """按 problem_id 建立题目信息索引，供标签聚合复用。"""
    return {item["problem_id"]: item for item in problems}


def _build_rank_trend(records: list[dict]) -> list[dict]:
    """抽取报告与可视化所需的排名趋势字段。"""
    return [
        {
            "contest_id": item["contest_id"],
            "rank": item["rank"],
            "percentile_rank": item["percentile_rank"],
        }
        for item in records
    ]


def _build_tag_distribution(records: list[dict], problem_index: dict[str, dict]) -> dict[str, dict[str, float | int]]:
    """按题目标签聚合尝试数、通过数与通过率。"""
    stats: dict[str, dict[str, float | int]] = defaultdict(lambda: {"attempted": 0, "solved": 0, "solve_rate": 0.0})
    for record in records:
        for result in record.get("problem_results", []):
            problem = problem_index.get(result["problem_id"], {})
            tags = problem.get("tags", []) or ["unknown"]
            for tag in tags:
                stats[tag]["attempted"] += 1
                if result.get("accepted"):
                    stats[tag]["solved"] += 1
    for tag, item in stats.items():
        attempted = int(item["attempted"])
        solved = int(item["solved"])
        item["solve_rate"] = round((solved / attempted), 4) if attempted else 0.0
    return dict(sorted(stats.items()))


def _build_stability_score(records: list[dict]) -> float:
    """基于 percentile_rank 的波动程度估算稳定性。

    分数越接近 1，说明不同比赛间的表现越稳定。
    """
    percentiles = [item["percentile_rank"] for item in records]
    if len(percentiles) <= 1:
        return 1.0
    score = 1 - pstdev(percentiles)
    return round(max(0.0, min(1.0, score)), 4)


def _build_growth_score(records: list[dict]) -> float | None:
    """比较首尾比赛 percentile_rank，粗略估算成长趋势。"""
    if len(records) < 2:
        return None
    first = records[0]["percentile_rank"]
    last = records[-1]["percentile_rank"]
    delta = (last - first + 1) / 2
    return round(max(0.0, min(1.0, delta)), 4)


def _build_solve_pace(records: list[dict]) -> dict[str, float]:
    """统计首过时间均值与后半程解题占比。"""
    first_ac_times: list[int] = []
    late_stage_count = 0
    solved_count = 0
    for record in records:
        for result in record.get("problem_results", []):
            if not result.get("accepted"):
                continue
            solved_count += 1
            first_ac_time = result.get("first_ac_time")
            if first_ac_time is not None:
                first_ac_times.append(first_ac_time)
                if first_ac_time >= 90:
                    late_stage_count += 1
    avg_first_ac = round(sum(first_ac_times) / len(first_ac_times), 2) if first_ac_times else 0.0
    late_ratio = round(late_stage_count / solved_count, 4) if solved_count else 0.0
    return {
        "avg_first_ac_minute": avg_first_ac,
        "late_stage_solve_ratio": late_ratio,
    }


def run_compute_metrics(context: PipelineContext) -> None:
    """读取 team_history 与 problems，生成 team_metrics artifact。"""
    history = read_json(context.path(f"data/intermediate/team_history/{context.canonical_id}.json"))
    problems = read_json(context.path("data/normalized/problems/problems.json"))

    records = history["contest_records"]
    problem_index = _build_problem_index(problems)

    payload = {
        "canonical_id": history["canonical_id"],
        "rank_trend": _build_rank_trend(records),
        "tag_distribution": _build_tag_distribution(records, problem_index),
        "stability_score": _build_stability_score(records),
        "growth_score": _build_growth_score(records),
        "solve_pace": _build_solve_pace(records),
    }
    write_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"), payload)
