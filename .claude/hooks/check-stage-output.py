#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
STAGE_PATHS = [
    ('raw', BASE_DIR / 'data' / 'raw'),
    ('normalized', BASE_DIR / 'data' / 'normalized'),
    ('intermediate', BASE_DIR / 'data' / 'intermediate'),
    ('derived', BASE_DIR / 'data' / 'derived'),
    ('insights', BASE_DIR / 'outputs' / 'insights'),
    ('reports', BASE_DIR / 'outputs' / 'reports'),
    ('visualizations', BASE_DIR / 'outputs' / 'visualizations'),
    ('validation', BASE_DIR / 'outputs' / 'validation'),
    ('bridge_runs', BASE_DIR / 'outputs' / 'bridge_runs'),
    ('hook_run_logs', BASE_DIR / '.claude' / 'hooks' / 'outputs' / 'run_logs'),
    ('hook_stage_logs', BASE_DIR / '.claude' / 'hooks' / 'outputs' / 'stage_logs'),
    ('hook_artifacts', BASE_DIR / '.claude' / 'hooks' / 'outputs' / 'artifacts'),
    ('hook_bridge', BASE_DIR / '.claude' / 'hooks' / 'outputs' / 'bridge'),
]


def count_files(path: Path) -> int:
    if not path.exists():
        return 0
    return len([p for p in path.rglob('*') if p.is_file() and not p.name.startswith('.')])


def main() -> int:
    status = {name: count_files(path) for name, path in STAGE_PATHS}
    print('[check-stage-output] pipeline status:', json.dumps(status, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
