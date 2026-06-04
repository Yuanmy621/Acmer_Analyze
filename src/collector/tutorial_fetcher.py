from __future__ import annotations

"""Codeforces Tutorial 页面抓取与题解文本解析。

Codeforces 每场比赛通常在 /contest/{id}/tutorial 提供官方题解。
本模块负责抓取该页面并按题号提取每道题的题解文本。
"""

import re
from typing import Any

from src.collector.codeforces_client import CodeforcesClient

# 单题题解最大字符数，避免 prompt 过长。
_MAX_CONTENT_LENGTH = 2000

# Tutorial 页面 URL 模板。
_TUTORIAL_URL_TEMPLATE = "https://codeforces.com/contest/{contest_id}/tutorial"


def _strip_html_tags(html: str) -> str:
    """将 HTML 文本粗略转换为纯文本。

    保留基本的段落分隔，移除标签与多余空白。
    """
    # 将 <br> 和块级标签转换为换行。
    text = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    text = re.sub(r"</(?:p|div|li|h[1-6]|tr)>", "\n", text, flags=re.IGNORECASE)
    # 移除所有 HTML 标签。
    text = re.sub(r"<[^>]+>", "", text)
    # 处理常见 HTML 实体。
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"&#?\w+;", "", text)
    # 收敛连续空行。
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_ttypography(html: str) -> str | None:
    """提取 <div class="ttypography"> 内的主体内容。"""
    match = re.search(
        r'<div\s+class="ttypography"[^>]*>(.*)</div>\s*(?:</div>|<div\s+class="roundbox")',
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if match:
        return match.group(1)
    # 降级：尝试直接匹配 ttypography 到页面尾部。
    match = re.search(r'<div\s+class="ttypography"[^>]*>(.*)', html, flags=re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1)
    return html


def _parse_tutorial_html(html: str) -> dict[str, str]:
    """从 Tutorial HTML 中按题号提取题解内容。

    返回 {题号（如 "A"）: 题解纯文本} 映射。

    Codeforces Tutorial 页面的典型结构：
    - 主体在 <div class="ttypography"> 内
    - 每道题的标题格式为 <div class="title">A. 题目名</div>
    - 题解文本紧跟在标题后面的 <p> 等标签中
    """
    body = _extract_ttypography(html)
    if not body:
        return {}

    # 策略 1：按 <div class="title"> 标签切分题目区块。
    results = _split_by_title_div(body)
    if results:
        return results

    # 策略 2：按 <h2> 或 <h3> 标题切分。
    results = _split_by_heading(body)
    if results:
        return results

    # 策略 3：整个页面作为单个题解（适用于只有一道题的比赛）。
    plain = _strip_html_tags(body)
    if plain and len(plain) > 20:
        return {"_all": plain[:_MAX_CONTENT_LENGTH]}
    return {}


def _split_by_title_div(body: str) -> dict[str, str]:
    """按 <div class="title"> 标签切分题目区块。"""
    # 匹配 "A." 或 "A -" 或 "A:" 等格式的题目标签。
    pattern = re.compile(
        r'<div\s+class="title"[^>]*>\s*([A-Z])[.:\-\s]',
        flags=re.IGNORECASE,
    )
    matches = list(pattern.finditer(body))
    if not matches:
        return {}

    results: dict[str, str] = {}
    for i, match in enumerate(matches):
        label = match.group(1).upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end]
        plain = _strip_html_tags(chunk)
        if plain:
            results[label] = plain[:_MAX_CONTENT_LENGTH]
    return results


def _split_by_heading(body: str) -> dict[str, str]:
    """按 <h2> 或 <h3> 标题切分题目区块。"""
    pattern = re.compile(
        r"<h[23][^>]*>\s*([A-Z])[.:\-\s]",
        flags=re.IGNORECASE,
    )
    matches = list(pattern.finditer(body))
    if not matches:
        return {}

    results: dict[str, str] = {}
    for i, match in enumerate(matches):
        label = match.group(1).upper()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        chunk = body[start:end]
        plain = _strip_html_tags(chunk)
        if plain:
            results[label] = plain[:_MAX_CONTENT_LENGTH]
    return results


def fetch_tutorials(
    client: CodeforcesClient,
    contest_id: int,
) -> dict[str, str] | None:
    """获取指定比赛的 Tutorial 页面，返回 {题号: 题解文本} 映射。

    失败时返回 None（页面不存在、网络异常、解析失败等）。
    """
    url = _TUTORIAL_URL_TEMPLATE.format(contest_id=contest_id)
    html = client.fetch_page(url)
    if not html:
        return None

    # 快速检查页面是否包含有效内容。
    if "ttypography" not in html and "title" not in html.lower():
        return None

    try:
        result = _parse_tutorial_html(html)
        return result if result else None
    except Exception:
        return None
