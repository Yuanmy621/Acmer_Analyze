from __future__ import annotations

"""构建目标队伍历史参赛记录。"""

import logging
from collections import defaultdict

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext

logger = logging.getLogger(__name__)


def run_build_history(context: PipelineContext) -> None:
    """从 normalized standings 中抽取目标队伍历史记录。"""
    logger.info("[build_history] 开始构建队伍历史")
    identity = read_json(context.path(f"data/intermediate/team_identity/{context.canonical_id}.json"))
    standings = read_json(context.path("data/normalized/standings/standings.json"))

    matched_names = set(identity["matched_names"])
    contest_team_counts: dict[str, int] = defaultdict(int)
    for item in standings:
        contest_team_counts[item["contest_id"]] += 1

    records: list[dict] = []
    for item in standings:
        if item["team_raw_name"] not in matched_names:
            continue
        total_teams = contest_team_counts[item["contest_id"]]
        # percentile_rank 越高表示名次越靠前，便于不同规模比赛横向比较。
        percentile_rank = 1 - ((item["rank"] - 1) / total_teams) if total_teams else 0.0
        records.append(
            {
                "contest_id": item["contest_id"],
                "rank": item["rank"],
                "solved_count": item["solved_count"],
                "total_teams": total_teams,
                "percentile_rank": round(percentile_rank, 4),
                "problem_results": item.get("problem_results", []),
            }
        )

    # 当前以 contest_id 排序作为稳定输出；后续若引入更可靠时间字段可再调整。
    records.sort(key=lambda item: item["contest_id"])
    payload = {
        "canonical_id": identity["canonical_id"],
        "contest_records": records,
    }
    write_json(context.path(f"data/intermediate/team_history/{context.canonical_id}.json"), payload)
    logger.info("[build_history] 历史构建完成: %d 场比赛记录", len(records))
