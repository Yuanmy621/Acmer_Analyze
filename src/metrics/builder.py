from __future__ import annotations

"""基于历史记录计算确定性指标。"""

import logging
from collections import defaultdict
from statistics import pstdev

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext

logger = logging.getLogger(__name__)


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

    percentile_rank 本身在 0~1 之间，其 pstdev 通常只有 0.02~0.15，
    直接用 1 - pstdev 会导致分数几乎总是 0.85+，区分度极低。
    这里乘以缩放系数 5，使得 pstdev ≈ 0.10 时稳定性约 0.50，
    pstdev ≈ 0.03 时稳定性约 0.85，更符合直觉。
    """
    percentiles = [item["percentile_rank"] for item in records]
    if len(percentiles) <= 1:
        return 1.0
    score = 1 - 5 * pstdev(percentiles)
    return round(max(0.0, min(1.0, score)), 4)


def _build_growth_score(records: list[dict]) -> float | None:
    """基于线性回归斜率估算成长趋势。

    使用最小二乘法拟合 percentile_rank 随时间的变化趋势，
    比单纯比较首尾两场比赛更能反映真实的成长轨迹。

    返回值 0.5 表示无明显趋势，>0.5 表示上升，<0.5 表示下降。
    """
    n = len(records)
    if n < 2:
        return None

    percentiles = [r["percentile_rank"] for r in records]
    # x 轴为比赛序号 (0, 1, 2, ...)
    x_mean = (n - 1) / 2
    y_mean = sum(percentiles) / n

    # 最小二乘法计算斜率: slope = Σ(xi - x_mean)(yi - y_mean) / Σ(xi - x_mean)²
    numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(percentiles))
    denominator = sum((i - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.5

    slope = numerator / denominator
    # 斜率单位是 percentile_rank / contest，理论范围 [-1, 1]。
    # 将其映射到 [0, 1]：中性点 0.5，每 0.1 的斜率对应 0.25 的分数偏移。
    # 使用 tanh 压缩极端值，使得 slope=0.2 → ~0.75，slope=-0.2 → ~0.25。
    import math
    score = 0.5 + 0.5 * math.tanh(slope * 5)
    return round(max(0.0, min(1.0, score)), 4)


def _build_solve_pace(records: list[dict], contest_durations: dict[str, int] | None = None) -> dict[str, float]:
    """统计首过时间均值与后半程解题占比。

    后半程判定根据比赛实际时长动态计算，而非硬编码阈值。
    contest_durations: {contest_id: duration_seconds}，缺失时默认 180 分钟。
    """
    first_ac_times: list[int] = []
    late_stage_count = 0
    solved_count = 0
    for record in records:
        contest_id = record.get("contest_id", "")
        duration_seconds = (contest_durations or {}).get(contest_id, 10800)
        duration_minutes = max(duration_seconds // 60, 1)
        half_time = duration_minutes / 2

        for result in record.get("problem_results", []):
            if not result.get("accepted"):
                continue
            solved_count += 1
            first_ac_time = result.get("first_ac_time")
            if first_ac_time is not None:
                first_ac_times.append(first_ac_time)
                if first_ac_time >= half_time:
                    late_stage_count += 1
    avg_first_ac = round(sum(first_ac_times) / len(first_ac_times), 2) if first_ac_times else 0.0
    late_ratio = round(late_stage_count / solved_count, 4) if solved_count else 0.0
    return {
        "avg_first_ac_minute": avg_first_ac,
        "late_stage_solve_ratio": late_ratio,
    }


def _build_penalty_efficiency(records: list[dict]) -> dict[str, float]:
    """计算罚时效率指标。

    - avg_penalty_per_solve: 每道通过题的平均罚时（分钟）
    - penalty_per_contest: 每场比赛平均总罚时（分钟）
    """
    total_penalty = 0
    total_solved = 0
    contest_count = len(records)
    for record in records:
        penalty = record.get("penalty") or 0
        total_penalty += penalty
        total_solved += record.get("solved_count", 0)

    avg_per_solve = round(total_penalty / total_solved, 2) if total_solved else 0.0
    avg_per_contest = round(total_penalty / contest_count, 2) if contest_count else 0.0
    return {
        "avg_penalty_per_solve": avg_per_solve,
        "penalty_per_contest": avg_per_contest,
    }


def run_compute_metrics(context: PipelineContext) -> None:
    """读取 team_history 与 problems，生成 team_metrics artifact。"""
    logger.info("[compute_metrics] 开始计算指标 (team=%s)", context.canonical_id)

    history = read_json(context.path(f"data/intermediate/team_history/{context.canonical_id}.json"))
    problems = read_json(context.path("data/normalized/problems/problems.json"))
    contests = read_json(context.path("data/normalized/contests/contests.json"))

    records = history["contest_records"]
    problem_index = _build_problem_index(problems)

    # 构建 contest_id → duration_seconds 映射，供 solve_pace 动态归一化。
    contest_durations: dict[str, int] = {}
    for c in contests:
        cid = c.get("contest_id", "")
        dur = c.get("duration_seconds")
        if cid and dur:
            contest_durations[cid] = int(dur)

    payload = {
        "canonical_id": history["canonical_id"],
        "rank_trend": _build_rank_trend(records),
        "tag_distribution": _build_tag_distribution(records, problem_index),
        "stability_score": _build_stability_score(records),
        "growth_score": _build_growth_score(records),
        "solve_pace": _build_solve_pace(records, contest_durations),
        "penalty_efficiency": _build_penalty_efficiency(records),
    }
    write_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"), payload)
    logger.info(
        "[compute_metrics] 指标计算完成: stability=%.4f, growth=%s, %d 场比赛",
        payload["stability_score"],
        payload["growth_score"],
        len(records),
    )
