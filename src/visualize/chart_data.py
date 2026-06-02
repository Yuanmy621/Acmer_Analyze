from __future__ import annotations

"""从指标与洞察中整理前端可消费的可视化数据。"""

import json
from datetime import datetime, timezone
from html import escape

from src.models.serde import read_json, write_json, write_text
from src.orchestrator.context import PipelineContext

VISUALIZE_AFTER_GENERATE = "visualize.after_generate"


def _build_line_chart_svg(items: list[dict]) -> str:
    """使用 SVG 生成数据看板中的趋势图。"""
    if not items:
        return "<div class=\"empty\">暂无趋势数据</div>"

    width = 820
    height = 280
    padding_x = 56
    padding_y = 30
    plot_width = width - padding_x * 2
    plot_height = height - padding_y * 2
    count = max(len(items) - 1, 1)
    points: list[tuple[float, float, dict]] = []
    for index, item in enumerate(items):
        x = padding_x + plot_width * index / count
        y = padding_y + (1 - float(item["percentile_rank"])) * plot_height
        points.append((x, y, item))

    path = " ".join(
        [f"M {points[0][0]:.2f} {points[0][1]:.2f}"]
        + [f"L {x:.2f} {y:.2f}" for x, y, _ in points[1:]]
    )
    dots = "".join(
        f'<g><circle cx="{x:.2f}" cy="{y:.2f}" r="5"></circle><text x="{x:.2f}" y="{y - 14:.2f}" text-anchor="middle">{item["rank"]}</text></g>'
        for x, y, item in points
    )
    axis = "".join(
        f'<text x="{x:.2f}" y="{height - 8:.2f}" text-anchor="middle">{escape(item["contest_id"])}</text>'
        for x, _, item in points
    )
    return f"""
    <svg class="viz-trend" viewBox="0 0 {width} {height}" role="img" aria-label="排名趋势图">
      <defs>
        <linearGradient id="vizTrendStroke" x1="0%" x2="100%" y1="0%" y2="0%">
          <stop offset="0%" stop-color="#f2d492"></stop>
          <stop offset="100%" stop-color="#7cc6ff"></stop>
        </linearGradient>
      </defs>
      <path class="viz-trend-path" d="{path}"></path>
      {dots}
      {axis}
    </svg>
    """


def _render_tag_rows(tag_distribution: dict[str, dict]) -> str:
    """把标签分布渲染成条带。"""
    ranked = sorted(tag_distribution.items(), key=lambda item: (-item[1]["solve_rate"], -item[1]["attempted"], item[0]))
    rows: list[str] = []
    for tag, data in ranked:
        rows.append(
            f"""
            <div class="metric-row">
              <div>
                <strong>{escape(tag)}</strong>
                <span>{int(data['solved'])}/{int(data['attempted'])} solved</span>
              </div>
              <div class="metric-bar"><span data-width="{float(data['solve_rate']) * 100:.2f}"></span></div>
            </div>
            """
        )
    return "".join(rows) if rows else "<div class=\"empty\">暂无题型数据</div>"


def _render_badges(items: list[str], class_name: str) -> str:
    """把优势或短板渲染成胶囊标签。"""
    return "".join(f'<li class="{class_name}">{escape(item)}</li>' for item in items) or "<li class=\"ghost\">暂无内容</li>"


def _render_html_dashboard(context: PipelineContext, chart_payload: dict, insight: dict, metrics: dict) -> str:
    """生成独立 HTML 可视化页面。"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(context.task.target_team)} · Visual Analysis Board</title>
  <style>
    :root {{
      --bg: #f5f0e7;
      --paper: rgba(255,255,255,0.78);
      --ink: #171311;
      --muted: #6a625a;
      --line: rgba(23,19,17,0.12);
      --gold: #b88137;
      --blue: #376d94;
      --mint: #4f8471;
      --rose: #b86b78;
      --serif: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
      --sans: "Avenir Next", "Helvetica Neue", "PingFang SC", "Hiragino Sans GB", sans-serif;
      --shadow: 0 28px 70px rgba(51, 39, 27, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      font-family: var(--sans);
      background:
        radial-gradient(circle at top left, rgba(184,129,55,0.10), transparent 26%),
        radial-gradient(circle at bottom right, rgba(55,109,148,0.09), transparent 22%),
        linear-gradient(180deg, #f8f4ed 0%, #f1ebe0 100%);
    }}
    .board {{ width: min(1280px, calc(100vw - 40px)); margin: 0 auto; padding: 30px 0 44px; }}
    .masthead {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
      margin-bottom: 18px;
    }}
    .sheet {{
      background: var(--paper);
      border: 1px solid rgba(255,255,255,0.6);
      backdrop-filter: blur(14px);
      box-shadow: var(--shadow);
      border-radius: 28px;
      padding: 28px;
      position: relative;
      overflow: hidden;
    }}
    .sheet::before {{
      content: "";
      position: absolute;
      inset: 0;
      background: linear-gradient(140deg, rgba(255,255,255,0.42), transparent 36%);
      pointer-events: none;
    }}
    .eyebrow {{
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.26em;
      color: var(--blue);
      margin-bottom: 16px;
    }}
    h1 {{
      margin: 0 0 14px;
      font-family: var(--serif);
      font-size: clamp(38px, 5vw, 72px);
      line-height: 0.95;
      max-width: 8ch;
      font-weight: 600;
    }}
    .lede {{ color: var(--muted); line-height: 1.9; max-width: 60ch; }}
    .meta-stack {{ display: grid; gap: 12px; align-content: start; }}
    .meta-box {{ border: 1px solid var(--line); border-radius: 20px; padding: 18px 18px 16px; background: rgba(255,255,255,0.45); }}
    .meta-box span {{ display: block; font-size: 12px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.18em; margin-bottom: 10px; }}
    .meta-box strong {{ font-size: 20px; font-family: var(--serif); font-weight: 600; }}
    .layout {{ display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 18px; }}
    .stack {{ display: grid; gap: 18px; }}
    .section-title {{ display: flex; justify-content: space-between; gap: 12px; align-items: baseline; margin-bottom: 18px; }}
    .section-title h2 {{ margin: 0; font-family: var(--serif); font-size: 26px; font-weight: 600; }}
    .section-title small {{ color: var(--muted); font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; }}
    .viz-trend {{ width: 100%; height: auto; display: block; }}
    .viz-trend-path {{ fill: none; stroke: url(#vizTrendStroke); stroke-width: 5; stroke-linecap: round; stroke-linejoin: round; }}
    .viz-trend circle {{ fill: white; stroke: var(--gold); stroke-width: 3; }}
    .viz-trend text {{ fill: rgba(23,19,17,0.74); font-size: 11px; }}
    .score-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; }}
    .score-card {{ border: 1px solid var(--line); border-radius: 20px; padding: 18px; background: rgba(255,255,255,0.42); }}
    .score-card span {{ display: block; color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: 0.18em; margin-bottom: 10px; }}
    .score-card strong {{ font-family: var(--serif); font-size: 34px; font-weight: 600; }}
    .score-card p {{ margin: 10px 0 0; color: var(--muted); line-height: 1.7; font-size: 13px; }}
    .metric-row + .metric-row {{ margin-top: 16px; }}
    .metric-row strong {{ display: block; font-size: 15px; margin-bottom: 3px; }}
    .metric-row span {{ color: var(--muted); font-size: 12px; }}
    .metric-bar {{ margin-top: 10px; width: 100%; height: 14px; border-radius: 999px; background: rgba(23,19,17,0.08); overflow: hidden; }}
    .metric-bar > span {{ display: block; height: 100%; width: 0; border-radius: inherit; background: linear-gradient(90deg, var(--gold), var(--blue)); transition: width 1.2s cubic-bezier(.2,.8,.2,1); }}
    .tag-cloud {{ list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 10px; }}
    .strength-badge, .weakness-badge, .ghost {{ padding: 11px 15px; border-radius: 999px; border: 1px solid var(--line); font-size: 14px; }}
    .strength-badge {{ background: rgba(79,132,113,0.12); }}
    .weakness-badge {{ background: rgba(184,107,120,0.12); }}
    .ghost {{ color: var(--muted); background: rgba(255,255,255,0.3); }}
    .editorial-block {{ color: var(--muted); line-height: 1.9; font-size: 15px; }}
    .empty {{ color: var(--muted); padding: 16px 0; }}
    @media (max-width: 980px) {{
      .masthead, .layout {{ grid-template-columns: 1fr; }}
    }}
    @media (max-width: 640px) {{
      .board {{ width: min(100vw - 20px, 1280px); padding-top: 12px; }}
      .sheet {{ padding: 18px; border-radius: 22px; }}
      .score-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="board">
    <section class="masthead">
      <article class="sheet">
        <div class="eyebrow">Visual Analysis Board</div>
        <h1>{escape(context.task.target_team)}</h1>
        <p class="lede">{escape(str(insight.get('summary') or '暂无分析摘要'))}</p>
      </article>
      <aside class="meta-stack">
        <div class="meta-box"><span>canonical_id</span><strong>{escape(context.canonical_id)}</strong></div>
        <div class="meta-box"><span>model_used</span><strong>{escape(str(insight.get('model_used') or 'unknown'))}</strong></div>
        <div class="meta-box"><span>generated_at</span><strong>{escape(str(insight.get('generated_at') or 'N/A'))}</strong></div>
      </aside>
    </section>

    <section class="layout">
      <div class="stack">
        <article class="sheet">
          <div class="section-title"><h2>排名趋势图</h2><small>Rank / percentile</small></div>
          {_build_line_chart_svg(chart_payload.get('rank_trend', []))}
        </article>
        <article class="sheet">
          <div class="section-title"><h2>题型能力分布</h2><small>Tag performance bars</small></div>
          {_render_tag_rows(chart_payload.get('tag_distribution', {}))}
        </article>
      </div>
      <div class="stack">
        <article class="sheet">
          <div class="section-title"><h2>关键指标</h2><small>Core metrics</small></div>
          <div class="score-grid">
            <div class="score-card"><span>stability</span><strong>{float(metrics.get('stability_score', 0.0)):.4f}</strong><p>比赛表现越稳定，数值越接近 1。</p></div>
            <div class="score-card"><span>growth</span><strong>{'N/A' if metrics.get('growth_score') is None else f"{float(metrics['growth_score']):.4f}"}</strong><p>首尾表现变化的粗粒度估计。</p></div>
            <div class="score-card"><span>avg first ac</span><strong>{float(metrics['solve_pace'].get('avg_first_ac_minute', 0.0)):.2f}</strong><p>平均首过时间，单位分钟。</p></div>
            <div class="score-card"><span>late solve ratio</span><strong>{float(metrics['solve_pace'].get('late_stage_solve_ratio', 0.0)):.4f}</strong><p>后半程解题占比，反映追分能力。</p></div>
          </div>
        </article>
        <article class="sheet">
          <div class="section-title"><h2>优势标签</h2><small>Strengths</small></div>
          <ul class="tag-cloud">{_render_badges(chart_payload.get('strengths', []), 'strength-badge')}</ul>
        </article>
        <article class="sheet">
          <div class="section-title"><h2>短板标签</h2><small>Weaknesses</small></div>
          <ul class="tag-cloud">{_render_badges(chart_payload.get('weaknesses', []), 'weakness-badge')}</ul>
        </article>
        <article class="sheet">
          <div class="section-title"><h2>阶段复盘</h2><small>Editorial note</small></div>
          <div class="editorial-block">{escape(str(insight.get('stage_analysis') or '暂无阶段分析'))}</div>
        </article>
      </div>
    </section>
  </main>
  <script>
    const payload = {json.dumps(chart_payload, ensure_ascii=False)};
    document.querySelectorAll('.metric-bar > span').forEach((node) => {{
      requestAnimationFrame(() => {{
        node.style.width = `${{node.dataset.width || 0}}%`;
      }});
    }});
  </script>
</body>
</html>
"""


def run_visualize(context: PipelineContext) -> None:
    """生成图表数据 JSON、HTML 看板及对应 artifact 索引。"""
    metrics = read_json(context.path(f"data/derived/team_metrics/{context.canonical_id}.json"))
    insight_path = context.path(f"outputs/insights/{context.canonical_id}.json")
    insight = read_json(insight_path) if insight_path.exists() else {"strengths": [], "weaknesses": [], "stage_analysis": ""}

    chart_payload = {
        "canonical_id": context.canonical_id,
        "rank_trend": metrics["rank_trend"],
        "tag_distribution": metrics["tag_distribution"],
        # strengths / weaknesses 一并输出，方便可视化层直接展示摘要标签。
        "strengths": insight.get("strengths", []),
        "weaknesses": insight.get("weaknesses", []),
    }
    chart_path = context.path(f"outputs/visualizations/{context.canonical_id}.json")
    chart_html_path = context.path(f"outputs/visualizations/{context.canonical_id}.html")
    write_json(chart_path, chart_payload)
    write_text(chart_html_path, _render_html_dashboard(context, chart_payload, insight, metrics))

    artifact = {
        "canonical_id": context.canonical_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "format": "html",
        "path": str(chart_html_path.relative_to(context.root_dir)),
        "chart_keys": ["rank_trend", "tag_distribution", "strengths", "weaknesses"],
        "alternate_paths": [str(chart_path.relative_to(context.root_dir))],
    }
    write_json(context.path(f"outputs/visualizations/{context.canonical_id}.artifact.json"), artifact)

    hook_manager = context.hook_manager()
    hook_manager.emit_safe(
        VISUALIZE_AFTER_GENERATE,
        context.new_hook_context(
            VISUALIZE_AFTER_GENERATE,
            payload={
                "visualization_path": str(chart_html_path.relative_to(context.root_dir)),
                "artifact_path": f"outputs/visualizations/{context.canonical_id}.artifact.json",
            },
        ),
    )
