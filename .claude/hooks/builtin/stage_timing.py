from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_append_jsonl():
    hooks_root = Path(__file__).resolve().parents[1]
    module_path = hooks_root / 'common' / 'utils.py'
    spec = importlib.util.spec_from_file_location('claude_hooks_utils_stage_timing', module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load hook utils from {module_path}')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.append_jsonl


append_jsonl = _load_append_jsonl()


def handle_hook(context) -> None:
    outputs_root = Path.cwd() / '.claude' / 'hooks' / 'outputs' / 'stage_logs'
    append_jsonl(outputs_root / 'stage_events.jsonl', context.to_dict())
