from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class HookContext:
    event_name: str
    timestamp: str
    run_id: str | None = None
    canonical_id: str | None = None
    stage_name: str | None = None
    artifact_path: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
