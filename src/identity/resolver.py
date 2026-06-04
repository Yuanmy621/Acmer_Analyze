from __future__ import annotations

"""目标队伍身份解析与别名匹配逻辑。"""

import logging

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext

logger = logging.getLogger(__name__)


def _normalize_name(value: str) -> str:
    """统一名称匹配规则，降低大小写、连字符与空白差异的影响。"""
    return " ".join(value.lower().replace("-", " ").replace("_", " ").split())


def _build_platform_ids(context: PipelineContext) -> dict[str, str]:
    """根据 source 生成平台侧标识。

    Codeforces 场景优先保留真实 handle，其他 source 先回退到 canonical_id。
    """
    if context.task.source == "codeforces" and context.task.codeforces_handle:
        return {"codeforces": context.task.codeforces_handle}
    return {context.task.source: context.canonical_id}


def run_team_identity(context: PipelineContext) -> None:
    """在标准化 standings 中解析目标队伍的统一身份。"""
    logger.info("[team_identity] 开始解析队伍身份: %s", context.task.target_team)
    standings = read_json(context.path("data/normalized/standings/standings.json"))
    target_names = {context.task.target_team, *context.task.aliases}
    normalized_targets = {_normalize_name(item) for item in target_names}

    matched_names = sorted(
        {
            item["team_raw_name"]
            for item in standings
            if _normalize_name(item["team_raw_name"]) in normalized_targets
        }
    )
    if not matched_names:
        available = sorted({item["team_raw_name"] for item in standings})[:20]
        raise ValueError(
            f"无法在 standings 中找到队伍: {context.task.target_team}\n"
            f"可用的队伍名 (前 20): {available}\n"
            f"提示: 使用 --aliases 指定别名，或检查 --target-team 拼写"
        )

    payload = {
        "canonical_id": context.canonical_id,
        "display_name": context.task.target_team,
        # 统一保留用户输入别名与榜单中真实出现的名称，便于后续追踪。
        "aliases": sorted(set([context.task.target_team, *context.task.aliases, *matched_names])),
        "platform_ids": _build_platform_ids(context),
        "school": context.task.school,
        "region": context.task.region,
        "matched_names": matched_names,
    }
    write_json(context.path(f"data/intermediate/team_identity/{context.canonical_id}.json"), payload)
    logger.info("[team_identity] 身份解析完成: matched_names=%s", matched_names)
