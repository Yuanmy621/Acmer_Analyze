from __future__ import annotations

"""browser bridge 的导入落盘与一键执行辅助逻辑。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.bridge.payloads import BridgeImportPayload, validate_bridge_payload
from src.models.serde import read_json, write_json
from src.orchestrator.context import PipelineContext
from src.orchestrator.pipeline import run_pipeline
from src.orchestrator.task import build_task_from_payload


def write_bridge_import(root_dir: Path, payload: BridgeImportPayload) -> dict[str, str]:
    """把浏览器侧抓取的原始 payload 写入仓库中的 raw artifacts。"""
    import_id = f"bridge_{uuid4().hex[:12]}"

    write_json(root_dir / "data/raw/contests/contests.json", payload.raw_payload["contests"])
    write_json(root_dir / "data/raw/problems/problems.json", payload.raw_payload["problems"])
    write_json(root_dir / "data/raw/standings/standings.json", payload.raw_payload["standings"])

    metadata = {
        "import_id": import_id,
        "source": payload.source,
        "site": payload.site,
        "target_team": payload.target_team,
        "aliases": payload.aliases,
        "captured_at": payload.metadata.get("captured_at") or datetime.now(timezone.utc).isoformat(),
        "page_url": payload.metadata.get("page_url"),
        "collector": payload.metadata.get("collector"),
    }
    metadata_path = root_dir / "data/raw/bridge_imports" / f"{import_id}.json"
    write_json(metadata_path, metadata)

    return {
        "import_id": import_id,
        "metadata_path": str(metadata_path.relative_to(root_dir)),
        # import-only 模式返回可复制执行的 CLI 命令，便于手工串联后续阶段。
        "next_command": f"python3 scripts/run_pipeline.py --source browser_bridge --target-team '{payload.target_team}' --start-stage normalize --bridge-import-id {import_id}",
    }


def _write_run_summary(root_dir: Path, summary: dict[str, Any]) -> str:
    """写入 bridge 一键执行结果摘要。"""
    run_path = root_dir / "outputs/bridge_runs" / f"{summary['run_id']}.json"
    write_json(run_path, summary)
    return str(run_path.relative_to(root_dir))


def run_bridge_pipeline(root_dir: Path, payload_dict: dict[str, Any], start_stage: str = "normalize") -> dict[str, Any]:
    """执行 browser bridge 的 import-and-run 流程。"""
    validated = validate_bridge_payload(payload_dict)
    import_result = write_bridge_import(root_dir, validated)

    run_id = f"run_{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc).isoformat()

    task_payload = {
        "target_team": validated.target_team,
        "aliases": validated.aliases,
        "source": "browser_bridge",
        "bridge_import_id": import_result["import_id"],
        "bridge_metadata_path": import_result["metadata_path"],
        "generate_visualize": True,
        "generate_insight": True,
    }

    try:
        task = build_task_from_payload(task_payload)
        context = PipelineContext(root_dir=root_dir, task=task)
        executed = run_pipeline(context=context, start_stage=start_stage)
        finished_at = datetime.now(timezone.utc).isoformat()
        summary = {
            "run_id": run_id,
            "import_id": import_result["import_id"],
            "status": "completed",
            "target_team": validated.target_team,
            "executed_stages": executed,
            "report_path": f"outputs/reports/{context.canonical_id}.md",
            "visualization_path": f"outputs/visualizations/{context.canonical_id}.json",
            "validation_path": f"outputs/validation/{context.canonical_id}.json",
            "started_at": started_at,
            "finished_at": finished_at,
            "error": None,
            "error_type": None,
        }
    except ValueError as error:
        # 将可预期的数据/参数问题单独标记，便于前端区分展示。
        finished_at = datetime.now(timezone.utc).isoformat()
        summary = {
            "run_id": run_id,
            "import_id": import_result["import_id"],
            "status": "failed",
            "target_team": validated.target_team,
            "executed_stages": [],
            "report_path": None,
            "visualization_path": None,
            "validation_path": None,
            "started_at": started_at,
            "finished_at": finished_at,
            "error": str(error),
            "error_type": "pipeline_validation_error",
        }
    except Exception as error:  # noqa: BLE001
        finished_at = datetime.now(timezone.utc).isoformat()
        summary = {
            "run_id": run_id,
            "import_id": import_result["import_id"],
            "status": "failed",
            "target_team": validated.target_team,
            "executed_stages": [],
            "report_path": None,
            "visualization_path": None,
            "validation_path": None,
            "started_at": started_at,
            "finished_at": finished_at,
            "error": str(error),
            "error_type": "pipeline_runtime_error",
        }

    summary_path = _write_run_summary(root_dir, summary)
    return {
        "ok": summary["status"] == "completed",
        "import_id": import_result["import_id"],
        "metadata_path": import_result["metadata_path"],
        "run_id": run_id,
        "run_summary_path": summary_path,
        "status": summary["status"],
        "report_path": summary["report_path"],
        "visualization_path": summary["visualization_path"],
        "validation_path": summary["validation_path"],
        "error": summary["error"],
        "error_type": summary["error_type"],
    }


def read_run_summary(root_dir: Path, run_id: str) -> dict[str, Any]:
    """读取指定 bridge run 的摘要信息。"""
    return read_json(root_dir / "outputs/bridge_runs" / f"{run_id}.json")
