from __future__ import annotations

"""主流水线调度器。"""

from src.analyzer.insight_generator import run_analyze
from src.collector.dispatcher import run_collect
from src.identity.resolver import run_team_identity
from src.metrics.builder import run_compute_metrics
from src.normalize.normalizer import run_normalize
from src.orchestrator.context import PipelineContext, STAGE_SEQUENCE
from src.report.markdown_report import run_report
from src.visualize.chart_data import run_visualize
from src.validation.validator import run_validate_final
from src.history.builder import run_build_history


RUN_BEFORE_START = "run.before_start"
RUN_AFTER_FINISH = "run.after_finish"
RUN_ON_ERROR = "run.on_error"
STAGE_BEFORE = "stage.before"
STAGE_AFTER = "stage.after"
STAGE_ERROR = "stage.error"


def run_pipeline(
    context: PipelineContext,
    start_stage: str | None = None,
    end_stage: str | None = None,
    skip_analyze: bool = False,
    skip_visualize: bool = False,
) -> list[str]:
    """按既定顺序执行 pipeline，并返回实际执行过的阶段列表。"""
    executed: list[str] = []
    hook_manager = context.hook_manager()
    hook_manager.emit_safe(
        RUN_BEFORE_START,
        context.new_hook_context(
            RUN_BEFORE_START,
            payload={
                "start_stage": start_stage,
                "end_stage": end_stage,
                "skip_analyze": skip_analyze,
                "skip_visualize": skip_visualize,
            },
        ),
    )

    try:
        for stage_name in STAGE_SEQUENCE:
            # 支持从任意阶段开始或提前截断，便于局部重跑。
            if not context.stage_enabled(stage_name, start_stage, end_stage):
                continue
            if stage_name == "analyze" and skip_analyze:
                continue
            if stage_name == "visualize" and skip_visualize:
                continue

            hook_manager.emit_safe(
                STAGE_BEFORE,
                context.new_hook_context(STAGE_BEFORE, stage_name=stage_name, payload={"executed": list(executed)}),
            )

            try:
                # 这里保持显式分发，便于快速看清每个 stage 对应的实现入口。
                if stage_name == "collect":
                    run_collect(context)
                elif stage_name == "normalize":
                    run_normalize(context)
                elif stage_name == "team_identity":
                    run_team_identity(context)
                elif stage_name == "build_history":
                    run_build_history(context)
                elif stage_name == "compute_metrics":
                    run_compute_metrics(context)
                elif stage_name == "analyze":
                    run_analyze(context)
                elif stage_name == "report":
                    run_report(context)
                elif stage_name == "visualize":
                    run_visualize(context)
                elif stage_name == "validate_final":
                    run_validate_final(context)
                else:
                    raise ValueError(f"unknown stage: {stage_name}")
            except Exception as error:
                hook_manager.emit_safe(
                    STAGE_ERROR,
                    context.new_hook_context(STAGE_ERROR, stage_name=stage_name, error=str(error)),
                )
                raise

            executed.append(stage_name)
            hook_manager.emit_safe(
                STAGE_AFTER,
                context.new_hook_context(STAGE_AFTER, stage_name=stage_name, payload={"executed": list(executed)}),
            )
    except Exception as error:
        hook_manager.emit_safe(
            RUN_ON_ERROR,
            context.new_hook_context(RUN_ON_ERROR, payload={"executed": list(executed)}, error=str(error)),
        )
        raise

    hook_manager.emit_safe(
        RUN_AFTER_FINISH,
        context.new_hook_context(RUN_AFTER_FINISH, payload={"executed": list(executed)}),
    )
    return executed
