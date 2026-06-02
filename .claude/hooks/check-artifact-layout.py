#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
REQUIRED_PATHS = [
    BASE_DIR / 'data' / 'raw',
    BASE_DIR / 'data' / 'normalized',
    BASE_DIR / 'data' / 'intermediate',
    BASE_DIR / 'data' / 'derived',
    BASE_DIR / 'outputs' / 'insights',
    BASE_DIR / 'outputs' / 'reports',
    BASE_DIR / 'outputs' / 'visualizations',
    BASE_DIR / 'outputs' / 'validation',
    BASE_DIR / '.claude' / 'hooks' / 'outputs',
]
REQUIRED_FILES = [
    BASE_DIR / 'data' / 'README.md',
    BASE_DIR / 'outputs' / 'README.md',
    BASE_DIR / '.claude' / 'hooks' / 'README.md',
    BASE_DIR / '.claude' / 'hooks' / 'hooks.json',
]


def main() -> int:
    missing: list[str] = []
    for path in REQUIRED_PATHS:
        if not path.exists():
            missing.append(str(path.relative_to(BASE_DIR)))
    for file_path in REQUIRED_FILES:
        if not file_path.exists():
            missing.append(str(file_path.relative_to(BASE_DIR)))

    if missing:
        print('[check-artifact-layout] missing required paths:')
        for item in missing:
            print('-', item)
        return 1

    print('[check-artifact-layout] layout ok')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
