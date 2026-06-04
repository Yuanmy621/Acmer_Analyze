from __future__ import annotations

"""Codeforces API 的最小客户端封装。"""

import json
import ssl
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class CodeforcesApiError(RuntimeError):
    """Codeforces API 调用失败。"""


class CodeforcesClient:
    """对 Codeforces 官方 API 的轻量访问封装。"""

    BASE_URL = "https://codeforces.com/api"

    def __init__(self, timeout: int = 30) -> None:
        self.timeout = timeout

    def _request(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """发送请求并统一处理网络错误与 API 错误。"""
        query = urlencode({key: value for key, value in (params or {}).items() if value is not None}, doseq=True)
        url = f"{self.BASE_URL}/{path}"
        if query:
            url = f"{url}?{query}"
        request = Request(url, headers={"User-Agent": "acmer-analyze/0.1"})
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        last_error: Exception | None = None
        for _ in range(3):
            try:
                with urlopen(request, timeout=self.timeout, context=ssl_context) as response:
                    payload = json.load(response)
                break
            except HTTPError as error:
                body = error.read().decode("utf-8", "ignore")
                raise CodeforcesApiError(f"HTTP {error.code} for {url}: {body}") from error
            except URLError as error:
                last_error = error
                time.sleep(0.5)
        else:
            raise CodeforcesApiError(f"Network error for {url}: {last_error}") from last_error

        if payload.get("status") != "OK":
            raise CodeforcesApiError(f"API failed for {url}: {payload.get('comment', 'unknown error')}")
        return payload.get("result")

    def get_contest_list(self, include_gym: bool = False) -> list[dict[str, Any]]:
        """获取比赛列表，可选包含 Gym。"""
        return self._request("contest.list", {"gym": str(include_gym).lower()})

    def get_user_info(self, handles: list[str]) -> list[dict[str, Any]]:
        """批量获取用户信息。"""
        return self._request("user.info", {"handles": ";".join(handles)})

    def get_user_rating(self, handle: str) -> list[dict[str, Any]]:
        """获取用户 rating 历史，用于推导参赛 contest 列表。"""
        return self._request("user.rating", {"handle": handle})

    def get_contest_standings(self, contest_id: int) -> dict[str, Any]:
        """获取指定比赛的榜单与题目快照。"""
        return self._request("contest.standings", {"contestId": contest_id})

    def fetch_page(self, url: str) -> str | None:
        """抓取指定 URL 的 HTML 内容，失败时返回 None。

        用于获取 Tutorial 等非核心页面，失败不影响主流程。
        """
        request = Request(url, headers={"User-Agent": "acmer-analyze/0.1"})
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        for _ in range(2):
            try:
                with urlopen(request, timeout=10, context=ssl_context) as response:
                    return response.read().decode("utf-8", errors="replace")
            except (HTTPError, URLError, OSError):
                time.sleep(0.5)
        return None
