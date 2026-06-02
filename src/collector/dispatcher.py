from __future__ import annotations

"""collect 阶段的 source 分发入口。"""

from src.collector.codeforces_collector import run_collect_codeforces
from src.collector.bridge_collector import run_collect_bridge
from src.collector.fixture_collector import run_collect_fixture
from src.orchestrator.context import PipelineContext


def run_collect(context: PipelineContext) -> None:
    """根据任务 source 选择对应的数据采集实现。"""
    if context.task.source == "fixture":
        run_collect_fixture(context)
        return
    if context.task.source == "codeforces":
        run_collect_codeforces(context)
        return
    if context.task.source == "browser_bridge":
        run_collect_bridge(context)
        return
    raise ValueError(f"unsupported collect source: {context.task.source}")
