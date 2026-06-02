#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGET_TEAM_PATHS = [
    "data/intermediate/team_identity/{canonical_id}.json",
    "data/intermediate/team_history/{canonical_id}.json",
    "data/derived/team_metrics/{canonical_id}.json",
    "outputs/insights/{canonical_id}.json",
    "outputs/reports/{canonical_id}.md",
    "outputs/reports/{canonical_id}.html",
    "outputs/reports/{canonical_id}.artifact.json",
    "outputs/visualizations/{canonical_id}.json",
    "outputs/visualizations/{canonical_id}.html",
    "outputs/visualizations/{canonical_id}.artifact.json",
    "outputs/validation/{canonical_id}.json",
]

ALL_PATTERNS = [
    "data/raw/contests/*.json",
    "data/raw/problems/*.json",
    "data/raw/standings/*.json",
    "data/raw/bridge_imports/*.json",
    "data/normalized/contests/*.json",
    "data/normalized/problems/*.json",
    "data/normalized/standings/*.json",
    "data/intermediate/team_identity/*.json",
    "data/intermediate/team_history/*.json",
    "data/derived/team_metrics/*.json",
    "outputs/insights/*.json",
    "outputs/reports/*",
    "outputs/visualizations/*",
    "outputs/validation/*.json",
    "outputs/bridge_runs/*.json",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="清理 acmer_analyze 的分析产物")
    parser.add_argument("--target-team", help="按队伍清理对应 artifact")
    parser.add_argument("--all", action="store_true", help="全量清理 data/ 与 outputs/ 下的分析产物")
    parser.add_argument("--dry-run", action="store_true", help="只预览，不实际删除")
    parser.add_argument(
        "--include-bridge-runs",
        action="store_true",
        help="按队伍清理时，额外删除 outputs/bridge_runs 中与该队伍相关的 run summary",
    )
    return parser


def _repo_root() -> Path:
    return Path.cwd().resolve()


def _canonical_id_for_target(target_team: str) -> str:
    base = target_team.strip().lower().replace(" ", "_").replace("-", "_")
    return f"team_{base}"


def _delete_path(path: Path, dry_run: bool) -> None:
    if not dry_run:
        path.unlink()



def _collect_target_team_paths(root_dir: Path, canonical_id: str, include_bridge_runs: bool) -> list[Path]:
    paths = [root_dir / pattern.format(canonical_id=canonical_id) for pattern in TARGET_TEAM_PATHS]

    if include_bridge_runs:
        bridge_runs_dir = root_dir / "outputs" / "bridge_runs"
        if bridge_runs_dir.exists():
            for file_path in bridge_runs_dir.glob("*.json"):
                try:
                    payload = json.loads(file_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                report_path = payload.get("report_path")
                visualization_path = payload.get("visualization_path")
                if report_path and canonical_id in str(report_path):
                    paths.append(file_path)
                elif visualization_path and canonical_id in str(visualization_path):
                    paths.append(file_path)

    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for item in paths:
        if item not in seen:
            unique_paths.append(item)
            seen.add(item)
    return unique_paths



def _collect_all_paths(root_dir: Path) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for pattern in ALL_PATTERNS:
        for item in root_dir.glob(pattern):
            if item.is_file() and item.name != ".gitkeep" and item not in seen:
                paths.append(item)
                seen.add(item)
    return paths



def clear_target_team(root_dir: Path, target_team: str, dry_run: bool, include_bridge_runs: bool) -> dict:
    canonical_id = _canonical_id_for_target(target_team)
    candidates = _collect_target_team_paths(root_dir, canonical_id, include_bridge_runs)

    deleted: list[str] = []
    missing: list[str] = []
    for path in candidates:
        relative = str(path.relative_to(root_dir))
        if not path.exists():
            missing.append(relative)
            continue
        _delete_path(path, dry_run=dry_run)
        deleted.append(relative)

    return {
        "mode": "target_team",
        "target_team": target_team,
        "canonical_id": canonical_id,
        "dry_run": dry_run,
        "deleted": deleted,
        "missing": missing,
    }



def clear_all(root_dir: Path, dry_run: bool) -> dict:
    candidates = _collect_all_paths(root_dir)
    deleted: list[str] = []
    for path in candidates:
        _delete_path(path, dry_run=dry_run)
        deleted.append(str(path.relative_to(root_dir)))

    return {
        "mode": "all",
        "dry_run": dry_run,
        "deleted": deleted,
        "missing": [],
    }



def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    root_dir = _repo_root()

    if args.all == bool(args.target_team):
        raise SystemExit("必须且只能选择 --all 或 --target-team 其中一种模式")

    if args.all:
        payload = clear_all(root_dir=root_dir, dry_run=args.dry_run)
    else:
        payload = clear_target_team(
            root_dir=root_dir,
            target_team=args.target_team,
            dry_run=args.dry_run,
            include_bridge_runs=args.include_bridge_runs,
        )

    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
