from __future__ import annotations

"""面向 artifact 的基础序列化工具。"""

import json
from pathlib import Path
from typing import Any


def read_json(path: str | Path) -> Any:
    """读取 JSON 文件并返回反序列化结果。"""
    with Path(path).open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json(path: str | Path, payload: Any) -> None:
    """把对象写入 JSON 文件，并自动创建父目录。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def write_text(path: str | Path, content: str) -> None:
    """把文本写入文件，并自动创建父目录。"""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
