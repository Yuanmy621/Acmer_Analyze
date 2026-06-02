from __future__ import annotations

"""基于本地 fixture 的 collect 实现。"""

from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext

RAW_GROUPS = {
    "contests": "contests.json",
    "problems": "problems.json",
    "standings": "standings.json",
}


def run_collect_fixture(context: PipelineContext) -> None:
    """把示例 fixture 拷贝到 raw artifact 目录。

    该模式主要用于本地联调与测试，不涉及外部网络请求。
    """
    for group_name, file_name in RAW_GROUPS.items():
        source_path = context.fixture_dir / file_name
        if not source_path.exists():
            raise FileNotFoundError(f"missing fixture file: {source_path}")
        payload = read_json(source_path)
        target_path = context.path(f"data/raw/{group_name}/{file_name}")
        write_json(target_path, payload)


def run_collect(context: PipelineContext) -> None:
    """保留一个与其他 collect 模块一致的兼容入口。"""
    run_collect_fixture(context)
