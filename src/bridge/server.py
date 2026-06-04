from __future__ import annotations

"""browser bridge 本地 HTTP 服务入口。"""

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from src.bridge.handlers import read_run_summary, run_bridge_pipeline, write_bridge_import
from src.bridge.payloads import validate_bridge_payload


def _error_payload(error: str, error_type: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    """统一构造错误响应，便于前端按 error_type 分流处理。"""
    return {
        "ok": False,
        "error": error,
        "error_type": error_type,
        "details": details or {},
    }


class BridgeRequestHandler(BaseHTTPRequestHandler):
    """处理 browser bridge 导入与运行请求的 HTTP handler。"""

    root_dir: Path

    def _json_response(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        """统一输出 JSON 响应，并补充基础 CORS 头。"""
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        """响应浏览器预检请求。"""
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        """查询指定 run_id 的执行摘要，或提供静态文件服务。"""
        # API 端点：查询 run 摘要
        prefix = "/api/bridge/runs/"
        if self.path.startswith(prefix):
            run_id = self.path[len(prefix):]
            try:
                summary = read_run_summary(self.root_dir, run_id)
            except FileNotFoundError:
                self._json_response(
                    HTTPStatus.NOT_FOUND,
                    _error_payload("run summary not found", "run_not_found", {"run_id": run_id}),
                )
                return
            self._json_response(HTTPStatus.OK, {"ok": True, **summary})
            return

        # 静态文件服务：outputs 目录下的文件
        if self.path.startswith("/outputs/"):
            file_path = self.root_dir / self.path.lstrip("/")
            if not file_path.exists() or not file_path.is_file():
                self._json_response(HTTPStatus.NOT_FOUND, _error_payload("file not found", "file_not_found"))
                return

            # 安全检查：只允许访问 outputs 目录
            try:
                file_path.resolve().relative_to((self.root_dir / "outputs").resolve())
            except ValueError:
                self._json_response(HTTPStatus.FORBIDDEN, _error_payload("access denied", "access_denied"))
                return

            # 提供文件下载
            content_type, _ = mimetypes.guess_type(str(file_path))
            if content_type is None:
                content_type = "application/octet-stream"

            try:
                with open(file_path, "rb") as f:
                    content = f.read()
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(content)
            except Exception:
                self._json_response(
                    HTTPStatus.INTERNAL_SERVER_ERROR,
                    _error_payload("failed to read file", "file_read_error"),
                )
            return

        # 未知路径
        self._json_response(HTTPStatus.NOT_FOUND, _error_payload("not found", "route_not_found"))

    def do_POST(self) -> None:  # noqa: N802
        """处理 import 与 import-and-run 两类 bridge 请求。"""
        if self.path not in {"/api/bridge/import", "/api/bridge/import-and-run"}:
            self._json_response(HTTPStatus.NOT_FOUND, _error_payload("not found", "route_not_found"))
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length)
        try:
            payload = json.loads(raw_body.decode("utf-8"))
            if self.path == "/api/bridge/import":
                validated = validate_bridge_payload(payload)
                result = write_bridge_import(self.root_dir, validated)
                response = {"ok": True, **result}
            else:
                response = run_bridge_pipeline(self.root_dir, payload)
        except json.JSONDecodeError as error:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                _error_payload(f"invalid json: {error}", "invalid_json"),
            )
            return
        except ValueError as error:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                _error_payload(str(error), "payload_validation_error"),
            )
            return
        except Exception as error:  # noqa: BLE001
            self._json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                _error_payload(str(error), "bridge_internal_error"),
            )
            return

        self._json_response(HTTPStatus.OK, response)

    def log_message(self, format: str, *args: object) -> None:
        """关闭默认访问日志，保持 CLI 输出简洁。"""
        return


def create_server(root_dir: Path, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """创建绑定到指定仓库根目录的 bridge HTTP 服务。"""
    handler_class = type(
        "ConfiguredBridgeRequestHandler",
        (BridgeRequestHandler,),
        {"root_dir": root_dir},
    )
    return ThreadingHTTPServer((host, port), handler_class)
