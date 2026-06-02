from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable

HookCallable = Callable[[Any], None]


class HookManager:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root
        self.hooks_root = repo_root / ".claude" / "hooks"
        self.config = self._load_config()
        self.strict_events = set(self.config.get("strict_events", []))
        self.cache: dict[str, HookCallable] = {}

    def _load_config(self) -> dict[str, Any]:
        config_path = self.hooks_root / "hooks.json"
        if not config_path.exists():
            return {"enabled": False, "bindings": {}, "strict_events": []}
        return json.loads(config_path.read_text(encoding="utf-8"))

    @property
    def enabled(self) -> bool:
        return bool(self.config.get("enabled", False))

    def _resolve_hook(self, hook_name: str) -> HookCallable:
        if hook_name in self.cache:
            return self.cache[hook_name]

        if not hook_name.startswith("builtin."):
            raise ValueError(f"unsupported hook namespace: {hook_name}")
        module_name = hook_name.split(".", 1)[1]
        module_path = self.hooks_root / "builtin" / f"{module_name}.py"
        spec = importlib.util.spec_from_file_location(f"claude_hooks_{module_name}", module_path)
        if spec is None or spec.loader is None:
            raise ValueError(f"cannot load hook module: {hook_name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"claude_hooks_{module_name}"] = module
        spec.loader.exec_module(module)
        hook_fn = getattr(module, "handle_hook", None)
        if hook_fn is None:
            raise ValueError(f"hook module missing handle_hook: {hook_name}")
        self.cache[hook_name] = hook_fn
        return hook_fn

    def emit(self, event_name: str, context: Any, strict: bool = False) -> None:
        if not self.enabled:
            return
        hook_names = self.config.get("bindings", {}).get(event_name, [])
        for hook_name in hook_names:
            hook_fn = self._resolve_hook(hook_name)
            try:
                hook_fn(context)
            except Exception:
                if strict or event_name in self.strict_events:
                    raise

    def emit_safe(self, event_name: str, context: Any) -> None:
        self.emit(event_name, context, strict=False)

    def emit_strict(self, event_name: str, context: Any) -> None:
        self.emit(event_name, context, strict=True)
