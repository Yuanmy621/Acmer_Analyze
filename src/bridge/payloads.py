from __future__ import annotations

"""browser bridge 请求 payload 的校验与结构化封装。"""

from dataclasses import dataclass
from typing import Any


REQUIRED_TOP_LEVEL_FIELDS = {"source", "site", "target_team", "raw_payload"}
REQUIRED_RAW_GROUPS = {"contests", "problems", "standings"}


@dataclass(slots=True)
class BridgeImportPayload:
    """browser bridge 导入请求在服务端的结构化表示。"""

    source: str
    site: str
    target_team: str
    aliases: list[str]
    raw_payload: dict[str, list[dict[str, Any]]]
    metadata: dict[str, Any]


def validate_bridge_payload(payload: dict[str, Any]) -> BridgeImportPayload:
    """校验 bridge payload 的必填字段与基本数据形状。"""
    missing = sorted(REQUIRED_TOP_LEVEL_FIELDS - set(payload.keys()))
    if missing:
        raise ValueError(f"missing bridge payload fields: {', '.join(missing)}")

    raw_payload = payload.get("raw_payload")
    if not isinstance(raw_payload, dict):
        raise ValueError("raw_payload must be an object")

    missing_groups = sorted(REQUIRED_RAW_GROUPS - set(raw_payload.keys()))
    if missing_groups:
        raise ValueError(f"missing raw payload groups: {', '.join(missing_groups)}")

    for group_name in REQUIRED_RAW_GROUPS:
        if not isinstance(raw_payload[group_name], list):
            raise ValueError(f"raw_payload.{group_name} must be a list")

    aliases = payload.get("aliases", [])
    if not isinstance(aliases, list):
        raise ValueError("aliases must be a list")

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("metadata must be an object")

    return BridgeImportPayload(
        source=str(payload["source"]),
        site=str(payload["site"]),
        target_team=str(payload["target_team"]),
        aliases=[str(item) for item in aliases],
        raw_payload={key: list(value) for key, value in raw_payload.items()},
        metadata=metadata,
    )
