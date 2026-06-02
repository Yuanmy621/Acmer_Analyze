from __future__ import annotations

"""任务载入与 payload 到 AnalysisTask 的转换逻辑。"""

from src.models.schemas import AnalysisTask
from src.models.serde import read_json


def load_task(task_file: str) -> AnalysisTask:
    """从 task-file 读取 JSON，并构造成统一的任务对象。"""
    payload = read_json(task_file)
    return build_task_from_payload(payload)


def build_task_from_payload(payload: dict) -> AnalysisTask:
    """把外部输入 payload 规范化为 AnalysisTask。

    这里会补齐默认值，并在 Codeforces 场景下把 handle 自动加入 aliases，
    方便后续 team_identity 阶段做名称匹配。
    """
    source = payload.get("source", "fixture")
    aliases = list(payload.get("aliases", []))
    codeforces_handle = payload.get("codeforces_handle")
    if source == "codeforces" and codeforces_handle and codeforces_handle not in aliases:
        aliases.append(codeforces_handle)

    return AnalysisTask(
        target_team=payload["target_team"],
        aliases=aliases,
        source=source,
        time_range=payload.get("time_range"),
        fixture_dir=payload.get("fixture_dir", "examples/sample_fixture"),
        codeforces_handle=codeforces_handle,
        contest_ids=payload.get("contest_ids", []),
        max_contests=payload.get("max_contests"),
        include_gym=payload.get("include_gym", False),
        bridge_import_id=payload.get("bridge_import_id"),
        bridge_metadata_path=payload.get("bridge_metadata_path"),
        bridge_payload_path=payload.get("bridge_payload_path"),
        generate_visualize=payload.get("generate_visualize", True),
        generate_insight=payload.get("generate_insight", True),
        enable_llm_insight=payload.get("enable_llm_insight", True),
        llm_model=payload.get("llm_model"),
        llm_settings_path=payload.get("llm_settings_path"),
        llm_fallback_to_rule=payload.get("llm_fallback_to_rule", True),
        school=payload.get("school"),
        region=payload.get("region"),
    )
