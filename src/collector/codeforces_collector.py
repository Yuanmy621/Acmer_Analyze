from __future__ import annotations

"""Codeforces 数据抓取与 raw artifact 组装逻辑。"""

from datetime import datetime, timezone

from src.collector.codeforces_client import CodeforcesClient
from src.models.serde import write_json
from src.orchestrator.context import PipelineContext


def _to_iso8601(timestamp_seconds: int | None) -> str:
    """把 Codeforces 的 Unix 时间戳转换为统一的 ISO8601 字符串。"""
    if timestamp_seconds is None:
        return datetime.fromtimestamp(0, tz=timezone.utc).isoformat()
    return datetime.fromtimestamp(timestamp_seconds, tz=timezone.utc).isoformat()


def _build_contest_id(contest_id: int) -> str:
    """生成标准化 contest_id，避免不同 source 的 ID 冲突。"""
    return f"cf_{contest_id}"


def _build_problem_id(contest_id: int, index: str) -> str:
    """生成标准化 problem_id。"""
    return f"cf_{contest_id}_{index}"


def _derive_team_raw_name(party: dict) -> str:
    """从 Codeforces party 结构中推导 team_raw_name。"""
    team_name = party.get("teamName")
    if team_name:
        return str(team_name)
    members = party.get("members", [])
    handles = [member.get("handle") for member in members if member.get("handle")]
    if handles:
        return " ".join(handles)
    participant_id = party.get("participantId")
    if participant_id is not None:
        return f"party_{participant_id}"
    return "unknown_party"


def _pick_contest_ids(context: PipelineContext, client: CodeforcesClient) -> list[int]:
    """决定本次需要抓取哪些 contest。

    若任务显式提供 contest_ids，则优先使用；否则根据 handle 的 rating 历史反推。
    """
    if context.task.contest_ids:
        return list(dict.fromkeys(int(item) for item in context.task.contest_ids))
    if not context.task.codeforces_handle:
        raise ValueError("source=codeforces 时必须提供 codeforces_handle 或 contest_ids")

    history = client.get_user_rating(context.task.codeforces_handle)
    if not history:
        raise ValueError(f"Codeforces handle has no rating history: {context.task.codeforces_handle}")

    # rating 历史由旧到新排列，这里 reverse 后优先抓取最近比赛。
    contest_ids = [int(item["contestId"]) for item in reversed(history)]
    if context.task.max_contests is not None:
        contest_ids = contest_ids[: context.task.max_contests]
    return list(dict.fromkeys(contest_ids))


def _build_contest_payload(contest_meta: dict, contest_snapshot: dict) -> dict:
    """把 contest 元信息转换成 raw/normalized 兼容的统一结构。"""
    contest_id = int(contest_snapshot["id"])
    return {
        "contest_id": _build_contest_id(contest_id),
        "source": "codeforces",
        "title": contest_snapshot.get("name") or contest_meta.get("name") or f"Codeforces Contest {contest_id}",
        "start_time": _to_iso8601(contest_snapshot.get("startTimeSeconds") or contest_meta.get("startTimeSeconds")),
        "duration_seconds": int(contest_snapshot.get("durationSeconds") or contest_meta.get("durationSeconds") or 0),
        "type": contest_snapshot.get("type") or contest_meta.get("type"),
        "url": f"https://codeforces.com/contest/{contest_id}",
    }


def _build_problem_payload(contest_id: int, problems: list[dict]) -> list[dict]:
    """把题目列表转换为标准问题结构。"""
    payload: list[dict] = []
    for item in problems:
        index = item["index"]
        payload.append(
            {
                "problem_id": _build_problem_id(contest_id, index),
                "contest_id": _build_contest_id(contest_id),
                "label": index,
                "title": item["name"],
                "tags": item.get("tags", []),
                "difficulty": item.get("rating"),
            }
        )
    return payload


def _build_problem_results(contest_id: int, problem_indices: list[str], results: list[dict]) -> tuple[list[dict], int]:
    """把榜单中的 problemResults 转换为统一的题目作答结果。"""
    payload: list[dict] = []
    solved_count = 0
    for index, result in zip(problem_indices, results, strict=False):
        points = float(result.get("points", 0.0) or 0.0)
        accepted = points > 0
        if accepted:
            solved_count += 1
        best_submission_seconds = result.get("bestSubmissionTimeSeconds")
        payload.append(
            {
                "problem_id": _build_problem_id(contest_id, index),
                "accepted": accepted,
                # Codeforces 榜单里 rejectedAttemptCount 不包含通过那一发，这里补 1 统一成总尝试次数。
                "attempts": int(result.get("rejectedAttemptCount", 0)) + (1 if accepted else 0),
                "first_ac_time": None if best_submission_seconds is None else int(best_submission_seconds // 60),
            }
        )
    return payload, solved_count


def _build_standings_payload(contest_id: int, problems: list[dict], rows: list[dict]) -> list[dict]:
    """把 Codeforces standings rows 展开为统一 standings 列表。"""
    problem_indices = [item["index"] for item in problems]
    standings: list[dict] = []
    for row in rows:
        party = row.get("party", {})
        problem_results, solved_count = _build_problem_results(contest_id, problem_indices, row.get("problemResults", []))
        standings.append(
            {
                "contest_id": _build_contest_id(contest_id),
                "team_raw_name": _derive_team_raw_name(party),
                "rank": int(row["rank"]),
                "solved_count": solved_count,
                "penalty": row.get("penalty"),
                "problem_results": problem_results,
            }
        )
    return standings


def run_collect_codeforces(context: PipelineContext) -> None:
    """抓取 Codeforces 数据并写入 raw artifacts。"""
    client = CodeforcesClient()
    contest_ids = _pick_contest_ids(context, client)
    contest_list = client.get_contest_list(include_gym=context.task.include_gym)
    contest_index = {int(item["id"]): item for item in contest_list}

    contests: list[dict] = []
    problems: list[dict] = []
    standings: list[dict] = []

    for contest_id in contest_ids:
        standings_result = client.get_contest_standings(contest_id)
        contest_snapshot = standings_result["contest"]
        contest_meta = contest_index.get(contest_id, {})
        contests.append(_build_contest_payload(contest_meta, contest_snapshot))
        problems.extend(_build_problem_payload(contest_id, standings_result.get("problems", [])))
        standings.extend(_build_standings_payload(contest_id, standings_result.get("problems", []), standings_result.get("rows", [])))

    write_json(context.path("data/raw/contests/contests.json"), contests)
    write_json(context.path("data/raw/problems/problems.json"), problems)
    write_json(context.path("data/raw/standings/standings.json"), standings)
