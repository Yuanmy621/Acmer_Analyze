from __future__ import annotations

"""pipeline 运行上下文与阶段顺序定义。"""

from dataclasses import dataclass
from pathlib import Path

from src.models.schemas import AnalysisTask

# 统一定义主流水线阶段顺序，供 orchestrator 与局部重跑逻辑共享。
STAGE_SEQUENCE = [
    "collect",
    "normalize",
    "team_identity",
    "build_history",
    "compute_metrics",
    "analyze",
    "report",
    "visualize",
    "validate_final",
]


@dataclass(slots=True)
class PipelineContext:
    """封装一次分析任务在运行期所需的最小上下文。

    当前上下文只持有仓库根目录与任务配置，其他阶段依赖的数据
    统一通过 artifact 文件读写，避免跨阶段直接共享内存对象。
    """

    root_dir: Path
    task: AnalysisTask

    @property
    def fixture_dir(self) -> Path:
        """返回 fixture 数据目录的绝对路径。"""
        return (self.root_dir / self.task.fixture_dir).resolve()

    @property
    def canonical_id(self) -> str:
        """基于目标队伍名称生成跨阶段稳定使用的 canonical_id。"""
        base = self.task.target_team.strip().lower().replace(" ", "_").replace("-", "_")
        return f"team_{base}"

    def path(self, relative: str) -> Path:
        """把仓库内相对路径转换为绝对路径。"""
        return self.root_dir / relative

    def stage_enabled(self, stage_name: str, start_stage: str | None, end_stage: str | None) -> bool:
        """判断某个阶段是否位于本次运行的执行区间内。"""
        start_index = STAGE_SEQUENCE.index(start_stage) if start_stage else 0
        end_index = STAGE_SEQUENCE.index(end_stage) if end_stage else len(STAGE_SEQUENCE) - 1
        current_index = STAGE_SEQUENCE.index(stage_name)
        return start_index <= current_index <= end_index
