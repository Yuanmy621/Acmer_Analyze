from __future__ import annotations

"""browser bridge 导入后的 collect 校验逻辑。"""

from src.models.serde import read_json
from src.orchestrator.context import PipelineContext


def run_collect_bridge(context: PipelineContext) -> None:
    """校验 bridge 导入元数据是否与当前任务匹配。

    browser bridge 的原始 contests / problems / standings 数据已经在导入时落盘，
    因此这里不再重复写 raw 数据，只负责确认当前任务引用的是正确导入。
    """
    if not context.task.bridge_import_id and not context.task.bridge_metadata_path:
        raise ValueError("source=browser_bridge 时必须提供 bridge_import_id 或 bridge_metadata_path")

    if context.task.bridge_metadata_path:
        metadata = read_json(context.path(context.task.bridge_metadata_path))
    else:
        metadata = read_json(context.path(f"data/raw/bridge_imports/{context.task.bridge_import_id}.json"))

    if metadata.get("target_team") != context.task.target_team:
        raise ValueError(
            f"bridge import target mismatch: expected {context.task.target_team}, got {metadata.get('target_team')}"
        )
