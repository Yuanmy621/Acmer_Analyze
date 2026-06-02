from __future__ import annotations

import json
from pathlib import Path
from typing import Any

HOOKS_ROOT = Path(__file__).resolve().parents[2] / '.claude' / 'hooks'
HOOKS_OUTPUTS = HOOKS_ROOT / 'outputs'


def read_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def _maybe_emit_artifact_hook(event_name: str, artifact_path: Path, payload: dict[str, Any]) -> None:
    manager_path = HOOKS_ROOT / 'common' / 'manager.py'
    context_path = HOOKS_ROOT / 'common' / 'context.py'
    if not manager_path.exists() or not context_path.exists():
        return

    import importlib.util
    import sys
    from datetime import datetime, timezone

    manager_spec = importlib.util.spec_from_file_location('acmer_claude_hooks_manager_serde', manager_path)
    context_spec = importlib.util.spec_from_file_location('acmer_claude_hooks_context_serde', context_path)
    if manager_spec is None or manager_spec.loader is None or context_spec is None or context_spec.loader is None:
        return

    manager_module = importlib.util.module_from_spec(manager_spec)
    context_module = importlib.util.module_from_spec(context_spec)
    sys.modules['acmer_claude_hooks_manager_serde'] = manager_module
    sys.modules['acmer_claude_hooks_context_serde'] = context_module
    context_spec.loader.exec_module(context_module)
    manager_spec.loader.exec_module(manager_module)

    repo_root = Path(__file__).resolve().parents[2]
    manager = manager_module.HookManager(repo_root)
    try:
        relative_path = str(artifact_path.relative_to(repo_root)) if artifact_path.is_absolute() else str(artifact_path)
    except ValueError:
        relative_path = str(artifact_path)
    hook_context = context_module.HookContext(
        event_name=event_name,
        timestamp=datetime.now(timezone.utc).isoformat(),
        run_id=None,
        canonical_id=None,
        stage_name=None,
        artifact_path=relative_path,
        payload=payload,
        error=None,
    )
    manager.emit_safe(event_name, hook_context)


def write_json(path: str | Path, payload: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _maybe_emit_artifact_hook('artifact.before_write', target, {'format': 'json'})
    with target.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")
    _maybe_emit_artifact_hook('artifact.after_write', target, {'format': 'json'})


def write_text(path: str | Path, content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    _maybe_emit_artifact_hook('artifact.before_write', target, {'format': 'text'})
    target.write_text(content, encoding="utf-8")
    _maybe_emit_artifact_hook('artifact.after_write', target, {'format': 'text'})
