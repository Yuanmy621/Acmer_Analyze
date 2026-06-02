#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
HOOKS_ROOT = BASE_DIR / '.claude' / 'hooks'
COMMON_FILES = [
    HOOKS_ROOT / 'common' / 'context.py',
    HOOKS_ROOT / 'common' / 'events.py',
    HOOKS_ROOT / 'common' / 'manager.py',
]


def main() -> int:
    config_path = HOOKS_ROOT / 'hooks.json'
    if not config_path.exists():
        print('[check-hooks-health] hooks.json not found')
        return 1

    config = json.loads(config_path.read_text(encoding='utf-8'))
    missing: list[str] = []

    for file_path in COMMON_FILES:
        if not file_path.exists():
            missing.append(str(file_path.relative_to(BASE_DIR)))

    bindings = config.get('bindings', {})
    for _, hook_names in bindings.items():
        for hook_name in hook_names:
            if not hook_name.startswith('builtin.'):
                missing.append(f'unsupported hook namespace: {hook_name}')
                continue
            module_name = hook_name.split('.', 1)[1]
            module_path = HOOKS_ROOT / 'builtin' / f'{module_name}.py'
            if not module_path.exists():
                missing.append(str(module_path.relative_to(BASE_DIR)))

    if missing:
        print('[check-hooks-health] missing or invalid hook files:')
        for item in missing:
            print('-', item)
        return 1

    print('[check-hooks-health] hooks ok')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
