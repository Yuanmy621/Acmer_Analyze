from __future__ import annotations

"""把指标与洞察渲染为 Markdown 与 HTML 报告。"""

import math
from datetime import datetime, timezone
from html import escape

from src.models.serde import read_json, write_json, write_text
from src.orchestrator.context import PipelineContext

REPORT_AFTER_GENERATE = "report.after_generate"

REPORT_SECTIONS = ["overview", "trend", "topics", "strengths", "weaknesses", "advice"]


def _format_score(value: float | None, digits: int = 4) -> str:
    """统一格式化可选数值。"""
    if value is None:
        return "N/A"
    return f"{value:.{digits}f}"


def _render_rank_trend(items: list[dict]) -> str:
    """把排名趋势渲染成 Markdown 表格。"""
    lines = ["| contest_id | rank | percentile_rank |", "| --- | ---: | ---: |"]
    for item in items:
        lines.append(f"| {item['contest_id']} | {item['rank']} | {item['percentile_rank']:.4f} |")
    return "\n".join(lines)


def _render_tag_distribution(tag_distribution: dict[str, dict]) -> str:
    """把题型分布渲染成 Markdown 表格。"""
    lines = ["| tag | attempted | solved | solve_rate |", "| --- | ---: | ---: | ---: |"]
    for tag, data in tag_distribution.items():
        lines.append(
            f"| {tag} | {int(data['attempted'])} | {int(data['solved'])} | {data['solve_rate']:.4f} |"
        )
    return "\n".join(lines)


def _build_line_chart_svg(items: list[dict]) -> str:
    """使用 SVG 生成排名趋势折线图。"""
    if not items:
        return '<div class="empty-chart">暂无排名趋势数据</div>'

    width = 760
    height = 280
    padding_x = 56
    padding_y = 28
    plot_width = width - padding_x * 2
    plot_height = height - padding_y * 2
    count = max(len(items) - 1, 1)

    points: list[tuple[float, float, dict]] = []
    for index, item in enumerate(items):
        x = padding_x + (plot_width * index / count)
        percentile = float(item["percentile_rank"])
        y = padding_y + (1 - percentile) * plot_height
        points.append((x, y, item))

    path = " ".join(
        [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
        + [f"L {x:.2f} {y:.2f}" for x, y, _ in points[1:]]
    )
    area_path = (
        f"M {points[0][0]:.2f} {height - padding_y:.2f} "
        + " ".join(f"L {x:.2f} {y:.2f}" for x, y, _ in points)
        + f" L {points[-1][0]:.2f} {height - padding_y:.2f} Z"
    )

    labels = []
    for x, y, item in points:
        labels.append(
            f"""
            <g class="trend-point">
              <circle cx="{x:.2f}" cy="{y:.2f}" r="6"></circle>
              <text x="{x:.2f}" y="{height - 8:.2f}" text-anchor="middle">{escape(item['contest_id'])}</text>
              <text x="{x:.2f}" y="{y - 14:.2f}" text-anchor="middle">#{item['rank']}</text>
            </g>
            """
        )

    grid = []
    for ratio in [0.0, 0.25, 0.5, 0.75, 1.0]:
        y = padding_y + (1 - ratio) * plot_height
        grid.append(
            f'<line x1="{padding_x}" y1="{y:.2f}" x2="{width - padding_x}" y2="{y:.2f}"></line>'
        )
        grid.append(f'<text x="16" y="{y + 4:.2f}">{ratio:.2f}</text>')

    return f"""
    <svg viewBox="0 0 {width} {height}" class="trend-chart" role="img" aria-label="排名趋势图">
      <defs>
        <linearGradient id="trendStroke" x1="0%" x2="100%" y1="0%" y2="0%">
          <stop offset="0%" stop-color="#8ad7ff"></stop>
          <stop offset="100%" stop-color="#f1b47c"></stop>
        </linearGradient>
        <linearGradient id="trendArea" x1="0%" x2="0%" y1="0%" y2="100%">
          <stop offset="0%" stop-color="rgba(138, 215, 255, 0.32)"></stop>
          <stop offset="100%" stop-color="rgba(138, 215, 255, 0.02)"></stop>
        </linearGradient>
      </defs>
      <g class="trend-grid">{''.join(grid)}</g>
      <path d="{area_path}" fill="url(#trendArea)"></path>
      <path d="{path}" class="trend-line"></path>
      {''.join(labels)}
    </svg>
    """


def _pick_radar_dimensions(tag_distribution: dict[str, dict]) -> list[tuple[str, float, int]]:
    """挑选雷达图维度，优先使用尝试数较高的标签。"""
    ranked = sorted(
        tag_distribution.items(),
        key=lambda item: (-int(item[1]["attempted"]), -float(item[1]["solve_rate"]), item[0]),
    )
    selected = [(tag, float(data["solve_rate"]), int(data["attempted"])) for tag, data in ranked[:5]]
    while len(selected) < 5:
        selected.append((f"reserve_{len(selected) + 1}", 0.0, 0))
    return selected


def _build_radar_chart_svg(tag_distribution: dict[str, dict]) -> str:
    """生成能力轮廓雷达图。"""
    dimensions = _pick_radar_dimensions(tag_distribution)
    if not dimensions:
        return '<div class="empty-chart">暂无能力雷达数据</div>'

    width = 380
    height = 380
    cx = width / 2
    cy = height / 2
    radius = 126
    sides = len(dimensions)

    def point_for(index: int, scale: float) -> tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * index / sides
        return cx + radius * scale * math.cos(angle), cy + radius * scale * math.sin(angle)

    rings = []
    for ratio in [0.25, 0.5, 0.75, 1.0]:
        ring_points = [point_for(index, ratio) for index in range(sides)]
        rings.append(
            '<polygon points="{}"></polygon>'.format(
                " ".join(f"{x:.2f},{y:.2f}" for x, y in ring_points)
            )
        )

    spokes = []
    labels = []
    shape_points = []
    for index, (label, solve_rate, attempted) in enumerate(dimensions):
        outer_x, outer_y = point_for(index, 1.0)
        value_x, value_y = point_for(index, max(0.08, solve_rate))
        label_x, label_y = point_for(index, 1.2)
        shape_points.append((value_x, value_y))
        spokes.append(f'<line x1="{cx:.2f}" y1="{cy:.2f}" x2="{outer_x:.2f}" y2="{outer_y:.2f}"></line>')
        labels.append(
            f"""
            <g class="radar-label">
              <text x="{label_x:.2f}" y="{label_y:.2f}" text-anchor="middle">{escape(label.replace('_', ' '))}</text>
              <text x="{label_x:.2f}" y="{label_y + 16:.2f}" text-anchor="middle">{attempted} attempts</text>
            </g>
            """
        )

    polygon = " ".join(f"{x:.2f},{y:.2f}" for x, y in shape_points)
    dots = "".join(
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.5"></circle>' for x, y in shape_points
    )

    return f"""
    <svg viewBox="0 0 {width} {height}" class="radar-chart" role="img" aria-label="能力雷达图">
      <defs>
        <linearGradient id="radarFill" x1="0%" x2="100%" y1="0%" y2="100%">
          <stop offset="0%" stop-color="rgba(138, 215, 255, 0.42)"></stop>
          <stop offset="100%" stop-color="rgba(241, 180, 124, 0.28)"></stop>
        </linearGradient>
      </defs>
      <g class="radar-rings">{''.join(rings)}</g>
      <g class="radar-spokes">{''.join(spokes)}</g>
      <polygon class="radar-shape" points="{polygon}"></polygon>
      <g class="radar-dots">{dots}</g>
      {''.join(labels)}
    </svg>
    """


def _render_tag_bars_html(tag_distribution: dict[str, dict]) -> str:
    """把题型分布渲染成高密度条形区块。"""
    ranked = sorted(tag_distribution.items(), key=lambda item: (-item[1]["attempted"], item[0]))
    blocks: list[str] = []
    for tag, data in ranked:
        width = max(8.0, float(data["solve_rate"]) * 100)
        blocks.append(
            f"""
            <div class="tag-row">
              <div class="tag-meta">
                <span class="tag-name">{escape(tag)}</span>
                <span class="tag-stats">{int(data['solved'])}/{int(data['attempted'])} · {float(data['solve_rate']):.2f}</span>
              </div>
              <div class="tag-track"><span style="width:{width:.2f}%"></span></div>
            </div>
            """
        )
    return ''.join(blocks) if blocks else '<div class="empty-chart">暂无题型分布数据</div>'


def _render_list_cards(items: list[str], class_name: str) -> str:
    """把文本列表渲染成视觉卡片。"""
    if not items:
        return '<div class="empty-chart">暂无内容</div>'
    return ''.join(f'<li class="{class_name}">{escape(item)}</li>' for item in items)


def _build_training_matrix(metrics: dict, insight: dict) -> list[dict[str, str]]:
    """基于当前指标和洞察生成训练重点矩阵。"""
    stability = float(metrics.get("stability_score", 0.0))
    growth = metrics.get("growth_score")
    late_ratio = float(metrics.get("solve_pace", {}).get("late_stage_solve_ratio", 0.0))
    weaknesses = insight.get("weaknesses", [])

    if stability >= 0.85:
        rhythm_title = "稳定性维护"
        rhythm_text = "当前整体发挥已经具备较高一致性，重点应从“减少失误”转向“提升关键局价值”。"
    elif stability >= 0.7:
        rhythm_title = "波动压缩"
        rhythm_text = "建议优先复盘起伏较大的比赛，围绕赛时分工、罚时控制与中盘节奏进行专项稳定化训练。"
    else:
        rhythm_title = "重建比赛节奏"
        rhythm_text = "当前波动较明显，需要从开局拿分路径、队内协作节奏和赛时决策规则上先做底盘修复。"

    if growth is None:
        growth_title = "继续拉长观察窗"
        growth_text = "当前历史样本仍偏少，建议持续收集跨平台与跨阶段比赛，以便更准确判断成长曲线。"
    elif float(growth) >= 0.6:
        growth_title = "趁势拔高上限"
        growth_text = "近期趋势向上，建议在保持现有稳定得分点的同时，增加对中高难题的针对性突破。"
    else:
        growth_title = "止跌并重塑增量"
        growth_text = "近期趋势未明显抬升，训练中应减少重复舒适区刷题，转向对薄弱标签和后程博弈的高反馈复盘。"

    if late_ratio >= 0.4:
        endgame_title = "强化后程攻坚"
        endgame_text = "队伍具备一定后程追分能力，建议继续训练高压阶段的信息同步与冲刺题目切换。"
    else:
        weakness_hint = weaknesses[0] if weaknesses else "当前短板标签"
        endgame_title = "补足后半程火力"
        endgame_text = f"建议围绕“{weakness_hint}”建立专项训练，并结合 90 分钟后的模拟赛段提升中后程得分能力。"

    return [
        {"kicker": "Pillar A", "title": rhythm_title, "body": rhythm_text},
        {"kicker": "Pillar B", "title": growth_title, "body": growth_text},
        {"kicker": "Pillar C", "title": endgame_title, "body": endgame_text},
    ]


def _render_timeline(records: list[dict]) -> str:
    """渲染比赛时间轴。"""
    if not records:
        return '<div class="empty-chart">暂无比赛时间轴数据</div>'

    cards: list[str] = []
    for index, item in enumerate(records, start=1):
        cards.append(
            f"""
            <article class="timeline-card">
              <div class="timeline-order">{index:02d}</div>
              <div class="timeline-body">
                <h3>{escape(item['contest_id'])}</h3>
                <p>Rank <strong>#{item['rank']}</strong> · Solved <strong>{item['solved_count']}</strong> · Percentile <strong>{float(item['percentile_rank']):.4f}</strong></p>
              </div>
            </article>
            """
        )
    return ''.join(cards)


def _render_html_report(context: PipelineContext, metrics: dict, insight: dict, history: dict) -> str:
    """生成带图文叙事的单页分析站 HTML 报告。"""
    generated_at = escape(str(insight.get("generated_at") or "N/A"))
    model_used = escape(str(insight.get("model_used") or "unknown"))
    summary = escape(str(insight.get("summary") or "暂无总结"))
    stage_analysis = escape(str(insight.get("stage_analysis") or "暂无阶段分析"))
    training_matrix = _build_training_matrix(metrics, insight)
    history_records = history.get("contest_records", []) if isinstance(history, dict) else []

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(context.task.target_team)} · Analysis Bulletin</title>
  <style>
    :root {{
      --bg: #0a0a0b;
      --panel: rgba(20, 24, 31, 0.72);
      --panel-strong: rgba(22, 25, 33, 0.88);
      --line: rgba(255, 255, 255, 0.08);
      --text: #f3efe5;
      --muted: #b6b1a7;
      --accent: #8ad7ff;
      --accent-2: #f1b47c;
      --danger: #ff8b8b;
      --success: #7de1b8;
      --shadow: 0 30px 90px rgba(0, 0, 0, 0.45);
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      --sans: "Avenir Next", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", sans-serif;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      font-family: var(--sans);
      color: var(--text);
      background:
        radial-gradient(circle at 15% 15%, rgba(138, 215, 255, 0.18), transparent 32%),
        radial-gradient(circle at 82% 12%, rgba(241, 180, 124, 0.12), transparent 30%),
        linear-gradient(135deg, #050506 0%, #0c1017 48%, #09090a 100%);
      min-height: 100vh;
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      background:
        linear-gradient(rgba(255,255,255,0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.035) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(to bottom, rgba(0,0,0,0.86), rgba(0,0,0,0.2));
      pointer-events: none;
    }}
    .shell {{
      width: min(1280px, calc(100vw - 48px));
      margin: 0 auto;
      padding: 24px 0 72px;
      position: relative;
      z-index: 1;
    }}
    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 14px;
      margin-bottom: 18px;
      flex-wrap: wrap;
    }}
    .topbar .brand {{ letter-spacing: 0.28em; text-transform: uppercase; color: var(--accent); font-size: 12px; }}
    .topbar nav {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .topbar nav a {{
      color: var(--muted);
      text-decoration: none;
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 999px;
      padding: 8px 14px;
      font-size: 12px;
      transition: 180ms ease;
    }}
    .topbar nav a:hover {{ color: var(--text); border-color: rgba(138,215,255,0.32); transform: translateY(-1px); }}
    .hero {{
      position: relative;
      overflow: hidden;
      border: 1px solid var(--line);
      border-radius: 32px;
      padding: 48px 44px 36px;
      background: linear-gradient(160deg, rgba(17, 20, 27, 0.92), rgba(10, 12, 18, 0.78));
      box-shadow: var(--shadow);
      margin-bottom: 26px;
    }}
    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -12% -35% auto;
      width: 420px;
      height: 420px;
      border-radius: 50%;
      background: radial-gradient(circle, rgba(138,215,255,0.24), transparent 62%);
      pointer-events: none;
    }}
    .hero::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.04), transparent 34%);
      pointer-events: none;
    }}
    .kicker {{
      letter-spacing: 0.3em;
      text-transform: uppercase;
      color: var(--accent);
      font-size: 12px;
      margin-bottom: 18px;
    }}
    h1 {{
      font-family: var(--serif);
      font-size: clamp(42px, 6vw, 88px);
      line-height: 0.9;
      margin: 0 0 16px;
      font-weight: 600;
      max-width: 9ch;
    }}
    .hero-summary {{
      max-width: 780px;
      color: var(--muted);
      font-size: 18px;
      line-height: 1.8;
      margin-bottom: 26px;
    }}
    .hero-meta {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .hero-chip {{
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(255,255,255,0.04);
      color: var(--text);
      border-radius: 999px;
      padding: 10px 16px;
      font-size: 13px;
    }}
    .grid {{ display: grid; grid-template-columns: repeat(12, 1fr); gap: 20px; }}
    .panel {{
      border: 1px solid var(--line);
      background: var(--panel);
      backdrop-filter: blur(18px);
      border-radius: 24px;
      box-shadow: var(--shadow);
      padding: 24px;
      position: relative;
      overflow: hidden;
    }}
    .panel::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(180deg, rgba(255,255,255,0.04), transparent 34%);
      pointer-events: none;
    }}
    .stats {{ grid-column: span 12; display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }}
    .stat-card {{
      padding: 22px 20px;
      border-radius: 22px;
      background: var(--panel-strong);
      border: 1px solid rgba(255,255,255,0.06);
      min-height: 168px;
      transition: 180ms ease;
    }}
    .stat-card:hover {{ transform: translateY(-3px); border-color: rgba(138,215,255,0.24); }}
    .label {{ font-size: 11px; letter-spacing: 0.26em; text-transform: uppercase; color: var(--muted); margin-bottom: 18px; }}
    .value {{ font-family: var(--serif); font-size: clamp(34px, 4vw, 52px); line-height: 0.98; margin-bottom: 12px; }}
    .sub {{ color: var(--muted); font-size: 13px; line-height: 1.6; }}
    .trend-panel {{ grid-column: span 7; }}
    .topic-panel {{ grid-column: span 5; }}
    .radar-panel {{ grid-column: span 5; }}
    .timeline-panel {{ grid-column: span 7; }}
    .insight-panel {{ grid-column: span 6; }}
    .matrix-panel {{ grid-column: span 12; }}
    .advice-panel {{ grid-column: span 12; }}
    .section-title {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 20px; }}
    .section-title h2 {{ margin: 0; font-family: var(--serif); font-size: 30px; font-weight: 600; }}
    .section-title span {{ color: var(--muted); font-size: 13px; }}
    .trend-chart, .radar-chart {{ width: 100%; height: auto; display: block; }}
    .trend-grid line, .radar-rings polygon, .radar-spokes line {{ stroke: rgba(255,255,255,0.08); stroke-dasharray: 3 9; fill: none; }}
    .trend-grid text {{ fill: rgba(255,255,255,0.44); font-size: 11px; }}
    .trend-line {{ fill: none; stroke: url(#trendStroke); stroke-width: 4; stroke-linecap: round; stroke-linejoin: round; filter: drop-shadow(0 0 18px rgba(138,215,255,0.24)); }}
    .trend-point circle {{ fill: #0d1117; stroke: var(--accent-2); stroke-width: 3; }}
    .trend-point text, .radar-label text {{ fill: rgba(243,239,229,0.86); font-size: 11px; }}
    .radar-shape {{ fill: url(#radarFill); stroke: var(--accent-2); stroke-width: 2.4; }}
    .radar-dots circle {{ fill: var(--accent); stroke: rgba(255,255,255,0.7); stroke-width: 1.5; }}
    .tag-row + .tag-row {{ margin-top: 16px; }}
    .tag-meta {{ display: flex; justify-content: space-between; gap: 12px; margin-bottom: 8px; }}
    .tag-name {{ font-weight: 600; font-size: 15px; }}
    .tag-stats {{ color: var(--muted); font-size: 12px; }}
    .tag-track {{ width: 100%; height: 12px; border-radius: 999px; background: rgba(255,255,255,0.06); overflow: hidden; position: relative; }}
    .tag-track span {{ display: block; height: 100%; border-radius: inherit; background: linear-gradient(90deg, var(--accent), var(--accent-2)); box-shadow: 0 0 24px rgba(138,215,255,0.24); }}
    .insight-list {{ list-style: none; margin: 0; padding: 0; display: grid; gap: 12px; }}
    .strength-card, .weakness-card {{ padding: 16px 18px; border-radius: 18px; border: 1px solid rgba(255,255,255,0.08); line-height: 1.7; position: relative; }}
    .strength-card {{ background: linear-gradient(145deg, rgba(125,225,184,0.12), rgba(125,225,184,0.03)); }}
    .weakness-card {{ background: linear-gradient(145deg, rgba(255,139,139,0.12), rgba(255,139,139,0.03)); }}
    .timeline-stack {{ display: grid; gap: 14px; }}
    .timeline-card {{ display: grid; grid-template-columns: 72px 1fr; gap: 16px; align-items: stretch; }}
    .timeline-order {{
      border-radius: 18px;
      background: linear-gradient(180deg, rgba(138,215,255,0.16), rgba(138,215,255,0.04));
      border: 1px solid rgba(138,215,255,0.18);
      display: grid;
      place-items: center;
      font-family: var(--serif);
      font-size: 28px;
    }}
    .timeline-body {{ border: 1px solid rgba(255,255,255,0.08); border-radius: 18px; padding: 16px 18px; background: rgba(255,255,255,0.03); }}
    .timeline-body h3 {{ margin: 0 0 8px; font-size: 17px; font-weight: 600; }}
    .timeline-body p {{ margin: 0; color: var(--muted); line-height: 1.8; }}
    .matrix-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }}
    .matrix-card {{ min-height: 200px; border-radius: 22px; border: 1px solid rgba(255,255,255,0.08); background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); padding: 22px; }}
    .matrix-card strong {{ display: block; font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--accent-2); margin-bottom: 14px; }}
    .matrix-card h3 {{ margin: 0 0 12px; font-family: var(--serif); font-size: 28px; line-height: 1.1; }}
    .matrix-card p {{ margin: 0; color: var(--muted); line-height: 1.8; }}
    .advice-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 18px; }}
    .advice-card {{ min-height: 170px; border-radius: 22px; border: 1px solid rgba(255,255,255,0.08); background: linear-gradient(160deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); padding: 22px; }}
    .advice-card strong {{ display: block; font-size: 14px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--accent-2); margin-bottom: 12px; }}
    .advice-card p {{ margin: 0; color: var(--text); line-height: 1.8; }}
    .stage-box {{ margin-top: 18px; padding: 18px 20px; border-left: 2px solid var(--accent); background: rgba(255,255,255,0.035); color: var(--muted); line-height: 1.9; }}
    .footer-note {{ margin-top: 22px; color: rgba(255,255,255,0.56); font-size: 13px; line-height: 1.8; }}
    .empty-chart {{ color: var(--muted); padding: 16px 0; }}
    .reveal {{ opacity: 0; transform: translateY(22px); animation: reveal 680ms ease forwards; }}
    .delay-1 {{ animation-delay: 80ms; }}
    .delay-2 {{ animation-delay: 160ms; }}
    .delay-3 {{ animation-delay: 240ms; }}
    .delay-4 {{ animation-delay: 320ms; }}
    @keyframes reveal {{ to {{ opacity: 1; transform: translateY(0); }} }}
    @media (max-width: 980px) {{
      .stats {{ grid-template-columns: repeat(2, 1fr); }}
      .trend-panel, .topic-panel, .radar-panel, .timeline-panel, .insight-panel, .matrix-panel, .advice-panel {{ grid-column: span 12; }}
      .advice-grid, .matrix-grid {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      .shell {{ width: min(100vw - 24px, 1280px); padding-top: 14px; }}
      .hero {{ padding: 30px 22px 24px; border-radius: 24px; }}
      .stats {{ grid-template-columns: 1fr; }}
      .panel {{ padding: 18px; border-radius: 20px; }}
      .timeline-card {{ grid-template-columns: 1fr; }}
      h1 {{ max-width: none; }}
      .topbar {{ align-items: flex-start; }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <div class="topbar reveal">
      <div class="brand">Competitive Dossier / Single Page Analysis Site</div>
      <nav>
        <a href="#metrics">指标</a>
        <a href="#trend">趋势</a>
        <a href="#radar">雷达</a>
        <a href="#timeline">时间轴</a>
        <a href="#matrix">训练矩阵</a>
      </nav>
    </div>

    <section class="hero reveal delay-1">
      <div class="kicker">Competitive Team Analysis / HTML Bulletin</div>
      <h1>{escape(context.task.target_team)}</h1>
      <div class="hero-summary">{summary}</div>
      <div class="hero-meta">
        <span class="hero-chip">canonical_id · {escape(context.canonical_id)}</span>
        <span class="hero-chip">model_used · {model_used}</span>
        <span class="hero-chip">generated_at · {generated_at}</span>
      </div>
    </section>

    <section class="grid">
      <div class="stats reveal delay-2" id="metrics">
        <article class="stat-card">
          <div class="label">Stability Score</div>
          <div class="value">{_format_score(metrics.get('stability_score'))}</div>
          <div class="sub">用于表达多场比赛间发挥的一致性，越接近 1 越稳定。</div>
        </article>
        <article class="stat-card">
          <div class="label">Growth Score</div>
          <div class="value">{_format_score(metrics.get('growth_score'))}</div>
          <div class="sub">基于首尾比赛 percentile_rank 的粗粒度成长趋势估计。</div>
        </article>
        <article class="stat-card">
          <div class="label">Avg First AC</div>
          <div class="value">{_format_score(metrics['solve_pace'].get('avg_first_ac_minute'), 2)}<small style="font-size:18px;color:var(--muted);"> min</small></div>
          <div class="sub">平均首过时间，可作为前中期进入状态速度的参考。</div>
        </article>
        <article class="stat-card">
          <div class="label">Late Solve Ratio</div>
          <div class="value">{_format_score(metrics['solve_pace'].get('late_stage_solve_ratio'))}</div>
          <div class="sub">后半程解题占比，反映拉锯战和中后程追分能力。</div>
        </article>
      </div>

      <article class="panel trend-panel reveal delay-2" id="trend">
        <div class="section-title">
          <h2>排名走势</h2>
          <span>Percentile & contest rank</span>
        </div>
        {_build_line_chart_svg(metrics.get('rank_trend', []))}
      </article>

      <article class="panel topic-panel reveal delay-2">
        <div class="section-title">
          <h2>题型热区</h2>
          <span>Attempt / solve distribution</span>
        </div>
        {_render_tag_bars_html(metrics.get('tag_distribution', {}))}
      </article>

      <article class="panel radar-panel reveal delay-3" id="radar">
        <div class="section-title">
          <h2>能力雷达</h2>
          <span>Shape of topic strengths</span>
        </div>
        {_build_radar_chart_svg(metrics.get('tag_distribution', {}))}
      </article>

      <article class="panel timeline-panel reveal delay-3" id="timeline">
        <div class="section-title">
          <h2>比赛时间轴</h2>
          <span>Contest progression timeline</span>
        </div>
        <div class="timeline-stack">{_render_timeline(history_records)}</div>
      </article>

      <article class="panel insight-panel reveal delay-3">
        <div class="section-title">
          <h2>优势总结</h2>
          <span>Strength signals</span>
        </div>
        <ul class="insight-list">{_render_list_cards(insight.get('strengths', []), 'strength-card')}</ul>
      </article>

      <article class="panel insight-panel reveal delay-3">
        <div class="section-title">
          <h2>短板总结</h2>
          <span>Pressure points</span>
        </div>
        <ul class="insight-list">{_render_list_cards(insight.get('weaknesses', []), 'weakness-card')}</ul>
      </article>

      <article class="panel matrix-panel reveal delay-4" id="matrix">
        <div class="section-title">
          <h2>训练重点矩阵</h2>
          <span>Three-pillar action board</span>
        </div>
        <div class="matrix-grid">{''.join(f'<div class="matrix-card"><strong>{escape(item["kicker"])}</strong><h3>{escape(item["title"])}</h3><p>{escape(item["body"])}</p></div>' for item in training_matrix)}</div>
      </article>

      <article class="panel advice-panel reveal delay-4">
        <div class="section-title">
          <h2>训练建议</h2>
          <span>Actionable recommendations</span>
        </div>
        <div class="advice-grid">{''.join(f'<div class="advice-card"><strong>Advice {index + 1:02d}</strong><p>{escape(item)}</p></div>' for index, item in enumerate(insight.get('training_advice', [])) )}</div>
        <div class="stage-box">{stage_analysis}</div>
        <div class="footer-note">本单页分析站由 `report` 阶段直接生成，整合了结构化指标、能力轮廓、比赛时间轴与训练重点矩阵。这样既保留 artifact 可追溯性，也让结果更适合作为正式演示页面交付。</div>
      </article>
    </section>
  </main>
</body>
</html>
"""


def run_report(context: PipelineContext) -> None:
    """生成 Markdown、HTML 报告及其 artifact 索引文件。"""
    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))
    insight_path = context.path(f"outputs/insights/{context.canonical_id}.json")
    if insight_path.exists():
        insight = read_json(insight_path)
    else:
        # 允许 analyze 被跳过，此时报告退化为结构化结果总览。
        insight = {
            "canonical_id": context.canonical_id,
            "strengths": ["本次运行跳过 analyze，暂无高层优势总结"],
            "weaknesses": ["本次运行跳过 analyze，暂无高层短板总结"],
            "summary": "本次运行未生成 AI / 规则式洞察，仅输出结构化结果。",
            "training_advice": ["如需总结与建议，请重新执行 analyze 阶段"],
            "stage_analysis": "未生成 analyze 阶段结果",
        }

    history_path = context.path(f"data/intermediate/team_history/{context.canonical_id}.json")
    history = read_json(history_path) if history_path.exists() else {"contest_records": []}

    markdown = f"""# 队伍分析报告：{context.task.target_team}

## 1. 概览

- `canonical_id`: `{context.canonical_id}`
- 稳定性评分：`{metrics['stability_score']}`
- 成长性评分：`{metrics['growth_score']}`
- 解题平均首过时间：`{metrics['solve_pace']['avg_first_ac_minute']}` 分钟
- 后半程解题占比：`{metrics['solve_pace']['late_stage_solve_ratio']}`

> {insight['summary']}

## 2. 排名趋势

{_render_rank_trend(metrics['rank_trend'])}

## 3. 题型分布

{_render_tag_distribution(metrics['tag_distribution'])}

## 4. 优势总结

"""
    markdown += "\n".join([f"- {item}" for item in insight["strengths"]])
    markdown += "\n\n## 5. 短板总结\n\n"
    markdown += "\n".join([f"- {item}" for item in insight["weaknesses"]])
    markdown += "\n\n## 6. 训练建议\n\n"
    markdown += "\n".join([f"- {item}" for item in insight["training_advice"]])
    markdown += f"\n\n## 7. 阶段分析\n\n{insight['stage_analysis']}\n"

    report_path = context.path(f"outputs/reports/{context.canonical_id}.md")
    report_html_path = context.path(f"outputs/reports/{context.canonical_id}.html")
    write_text(report_path, markdown)
    write_text(report_html_path, _render_html_report(context, metrics, insight, history))

    artifact = {
        "canonical_id": context.canonical_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": "html",
        "path": str(report_html_path.relative_to(context.root_dir)),
        "sections_present": REPORT_SECTIONS,
        "alternate_paths": [str(report_path.relative_to(context.root_dir))],
    }
    write_json(context.path(f"outputs/reports/{context.canonical_id}.artifact.json"), artifact)

    hook_manager = context.hook_manager()
    hook_manager.emit_safe(
        REPORT_AFTER_GENERATE,
        context.new_hook_context(
            REPORT_AFTER_GENERATE,
            payload={
                "report_path": str(report_html_path.relative_to(context.root_dir)),
                "artifact_path": f"outputs/reports/{context.canonical_id}.artifact.json",
            },
        ),
    )
