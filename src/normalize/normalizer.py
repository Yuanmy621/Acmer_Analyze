from __future__ import annotations

"""raw artifact 到 normalized artifact 的标准化逻辑。"""

from datetime import datetime, timezone

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext


def _to_iso8601(value: str | int | None) -> str:
    """把多种时间表示统一成 ISO8601 字符串。"""
    if isinstance(value, str):
        return value
    if isinstance(value, int):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return datetime.fromtimestamp(0, tz=timezone.utc).isoformat()


def _normalize_contests(payload: list[dict]) -> list[dict]:
    """标准化 contests 结构与字段类型。"""
    normalized: list[dict] = []
    for item in payload:
        normalized.append(
            {
                "contest_id": item["contest_id"],
                "source": item["source"],
                "title": item["title"],
                "start_time": _to_iso8601(item.get("start_time")),
                "duration_seconds": int(item["duration_seconds"]),
                "type": item.get("type"),
                "url": item.get("url"),
            }
        )
    return normalized


def _normalize_problems(payload: list[dict]) -> list[dict]:
    """标准化 problems 结构。"""
    normalized: list[dict] = []
    for item in payload:
        normalized.append(
            {
                "problem_id": item["problem_id"],
                "contest_id": item["contest_id"],
                "label": item["label"],
                "title": item["title"],
                "tags": item.get("tags", []),
                "difficulty": item.get("difficulty"),
            }
        )
    return normalized


def _normalize_standings(payload: list[dict]) -> list[dict]:
    """标准化 standings 结构，并收敛嵌套 problem_results 的字段类型。"""
    normalized: list[dict] = []
    for item in payload:
        normalized.append(
            {
                "contest_id": item["contest_id"],
                "team_raw_name": item["team_raw_name"],
                "rank": int(item["rank"]),
                "solved_count": int(item["solved_count"]),
                "penalty": item.get("penalty"),
                "problem_results": [
                    {
                        "problem_id": result["problem_id"],
                        "accepted": bool(result["accepted"]),
                        "attempts": result.get("attempts"),
                        "first_ac_time": result.get("first_ac_time"),
                    }
                    for result in item.get("problem_results", [])
                ],
            }
        )
    return normalized


def run_normalize(context: PipelineContext) -> None:
    """读取 raw artifacts，输出统一字段协议下的 normalized artifacts。"""
    contests = read_json(context.path("data/raw/contests/contests.json"))
    problems = read_json(context.path("data/raw/problems/problems.json"))
    standings = read_json(context.path("data/raw/standings/standings.json"))

    write_json(context.path("data/normalized/contests/contests.json"), _normalize_contests(contests))
    write_json(context.path("data/normalized/problems/problems.json"), _normalize_problems(problems))
    write_json(context.path("data/normalized/standings/standings.json"), _normalize_standings(standings))
