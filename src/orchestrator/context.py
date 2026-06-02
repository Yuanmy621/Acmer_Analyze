from __future__ import annotations

"""pipeline 运行上下文与阶段顺序定义。"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import importlib.util
from pathlib import Path
import sys
from types import ModuleType
from typing import Any
from uuid import uuid4

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

_HOOK_MANAGER_CLASS: type | None = None
_HOOK_CONTEXT_CLASS: type | None = None


def _load_module(module_name: str, file_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module from {file_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(slots=True)
class PipelineContext:
    """封装一次分析任务在运行期所需的最小上下文。

    当前上下文只持有仓库根目录与任务配置，其他阶段依赖的数据
    统一通过 artifact 文件读写，避免跨阶段直接共享内存对象。
    """

    root_dir: Path
    task: AnalysisTask
    run_id: str = field(default_factory=lambda: f"run_{uuid4().hex[:12]}")
    _hook_manager: Any | None = field(default=None, init=False, repr=False)

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

    def hook_manager(self) -> Any:
        """懒加载 .claude/hooks 下的 HookManager。"""
        global _HOOK_MANAGER_CLASS
        if self._hook_manager is not None:
            return self._hook_manager
        if _HOOK_MANAGER_CLASS is None:
            manager_module = _load_module(
                "acmer_claude_hooks_manager",
                self.root_dir / ".claude" / "hooks" / "common" / "manager.py",
            )
            _HOOK_MANAGER_CLASS = manager_module.HookManager
        self._hook_manager = _HOOK_MANAGER_CLASS(self.root_dir)
        return self._hook_manager

    def new_hook_context(
        self,
        event_name: str,
        *,
        stage_name: str | None = None,
        artifact_path: str | None = None,
        payload: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Any:
        """基于 .claude/hooks/common/context.py 构造 HookContext。"""
        global _HOOK_CONTEXT_CLASS
        if _HOOK_CONTEXT_CLASS is None:
            context_module = _load_module(
                "acmer_claude_hooks_context",
                self.root_dir / ".claude" / "hooks" / "common" / "context.py",
            )
            _HOOK_CONTEXT_CLASS = context_module.HookContext
        return _HOOK_CONTEXT_CLASS(
            event_name=event_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id=self.run_id,
            canonical_id=self.canonical_id,
            stage_name=stage_name,
            artifact_path=artifact_path,
            payload=payload or {},
            error=error,
        )
