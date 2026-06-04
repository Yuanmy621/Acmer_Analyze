#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.models.schemas import AnalysisTask
from src.orchestrator.context import PipelineContext, STAGE_SEQUENCE
from src.orchestrator.pipeline import run_pipeline
from src.orchestrator.task import load_task


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="运行 acmer_analyze 最小可用流水线")
    parser.add_argument("--task-file", help="任务配置 JSON 文件路径")
    parser.add_argument("--source", choices=["fixture", "codeforces", "browser_bridge"], help="数据源")
    parser.add_argument("--target-team", help="目标队伍标识")
    parser.add_argument("--aliases", nargs="*", default=[], help="目标队伍别名列表")
    parser.add_argument("--time-range", help="时间范围描述")
    parser.add_argument("--fixture-dir", help="fixture 数据目录")
    parser.add_argument("--codeforces-handle", help="Codeforces handle")
    parser.add_argument("--contest-ids", nargs="*", type=int, default=[], help="指定 contest id 列表")
    parser.add_argument("--max-contests", type=int, help="最近比赛数量")
    parser.add_argument("--include-gym", action="store_true", help="是否包含 gym")
    parser.add_argument("--bridge-import-id", help="bridge 导入批次 ID")
    parser.add_argument("--bridge-metadata-path", help="bridge 导入 metadata 文件路径")
    parser.add_argument("--bridge-payload-path", help="bridge 原始 payload 文件路径")
    parser.add_argument("--school", help="学校")
    parser.add_argument("--region", help="地区")
    parser.add_argument("--llm-model", help="覆盖默认 LLM model")
    parser.add_argument("--llm-settings-path", help="指定 LLM 设置文件路径")
    parser.add_argument("--start-stage", choices=STAGE_SEQUENCE, help="指定起始 stage")
    parser.add_argument("--end-stage", choices=STAGE_SEQUENCE, help="指定结束 stage")
    parser.add_argument("--skip-analyze", action="store_true", help="跳过 analyze 阶段")
    parser.add_argument("--skip-visualize", action="store_true", help="跳过 visualize 阶段")
    return parser


def build_task_from_args(args: argparse.Namespace) -> AnalysisTask:
    if not args.target_team:
        raise ValueError("动态模式下必须提供 --target-team")
    source = args.source or "fixture"
    if source == "codeforces" and not args.codeforces_handle and not args.contest_ids:
        raise ValueError("source=codeforces 时必须提供 --codeforces-handle 或 --contest-ids")
    if source == "browser_bridge" and not args.bridge_import_id and not args.bridge_metadata_path:
        raise ValueError("source=browser_bridge 时必须提供 --bridge-import-id 或 --bridge-metadata-path")

    aliases = list(args.aliases or [])
    if source == "codeforces" and args.codeforces_handle and args.codeforces_handle not in aliases:
        aliases.append(args.codeforces_handle)

    return AnalysisTask(
        target_team=args.target_team,
        aliases=aliases,
        source=source,
        time_range=args.time_range,
        fixture_dir=args.fixture_dir or "examples/sample_fixture",
        codeforces_handle=args.codeforces_handle,
        contest_ids=args.contest_ids or [],
        max_contests=args.max_contests,
        include_gym=args.include_gym,
        bridge_import_id=args.bridge_import_id,
        bridge_metadata_path=args.bridge_metadata_path,
        bridge_payload_path=args.bridge_payload_path,
        generate_visualize=not args.skip_visualize,
        generate_insight=not args.skip_analyze,
        llm_model=args.llm_model,
        llm_settings_path=args.llm_settings_path,
        school=args.school,
        region=args.region,
    )


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    # 配置日志：默认 INFO 级别，格式包含时间与 stage 信息。
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )

    if args.task_file:
        task = load_task(args.task_file)
    else:
        try:
            task = build_task_from_args(args)
        except ValueError as error:
            print(f"错误: {error}", file=sys.stderr)
            return 1

    context = PipelineContext(root_dir=ROOT_DIR, task=task)

    print(f"开始分析队伍: {task.target_team} (canonical_id={context.canonical_id})", file=sys.stderr)

    try:
        executed = run_pipeline(
            context=context,
            start_stage=args.start_stage,
            end_stage=args.end_stage,
            skip_analyze=args.skip_analyze,
            skip_visualize=args.skip_visualize,
        )
    except Exception as error:
        print(f"\n流水线执行失败: {error}", file=sys.stderr)
        return 1

    print(f"\n分析完成！共执行 {len(executed)} 个阶段: {' → '.join(executed)}", file=sys.stderr)
    print(f"报告路径: outputs/reports/{context.canonical_id}.md", file=sys.stderr)
    print(f"可视化:   outputs/visualizations/{context.canonical_id}.html", file=sys.stderr)

    print(
        json.dumps(
            {
                "target_team": task.target_team,
                "canonical_id": context.canonical_id,
                "executed_stages": executed,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
